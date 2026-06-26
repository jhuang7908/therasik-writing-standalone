#!/usr/bin/env python3
"""
Site Integrity Pipeline — pre-deploy validation and safe-repair entrypoint.

QA-strict mode (default for full runs):
  - PMID unrelated to context → HIGH (blocks deploy).
  - ADA rows: ada_display / ada_pct must appear in PubMed (linked PMIDs) OR in
    fetched citation_url body (FDA label PDF, HTML, etc.). See ADA_VALUE_IN_EVIDENCE.

Re-check after repairs:
  - With --apply: always runs one full validation pass after applying repairs.
  - With --qa-loop: repeats validate → apply until gate PASS, or consecutive
    identical unresolved fingerprints (no further auto-fix possible), or --max-rounds.

Outputs:
  reports/site_integrity_report.json
  reports/site_integrity_report.csv
  reports/site_integrity_summary.md

Exit codes:
  0   gate passes (no unresolved HIGH/MEDIUM findings)
  1   gate blocked (unresolved HIGH or MEDIUM findings remain)

Usage:
  python scripts/site_integrity_pipeline.py
  python scripts/site_integrity_pipeline.py --apply --qa-loop
  python scripts/site_integrity_pipeline.py --no-pmid-checks   # skips ADA evidence too unless --ada-evidence

Env:
  NCBI_API_KEY            optional; higher eutils rate limit
  NCBI_CONTACT_EMAIL      optional contact email for eutils
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

# ── repo root ─────────────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.integrity import (
    EntityExtractor,
    Finding,
    IntegrityReporter,
    SafeRepairEngine,
    Severity,
    ValidatorRegistry,
)
from core.integrity.ada_evidence import validate_ada_database

# ── canonical content roots ───────────────────────────────────────────────────
DEFAULT_ROOTS = [
    "docs",
    "insynbio-web-source",
    "therasik-web-source",
]
SITE_TREES = [
    REPO / "insynbio-web-source",
    REPO / "therasik-web-source",
]
DOCS_DIR = REPO / "docs"
REPORTS_DIR = REPO / "reports"
OVERRIDES_FILE = REPO / "config" / "site_integrity_overrides.json"
ADA_JSON = DOCS_DIR / "ada_db_data.json"


def _load_curated_sequences() -> set[str]:
    seqs: set[str] = set()
    sources = [
        REPO / "data" / "ada_master_136_curated.csv",
        REPO / "data" / "immunogenicity_panel_136_master.csv",
    ]
    for src in sources:
        if not src.exists():
            continue
        try:
            with src.open(encoding="utf-8", errors="replace") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    for col in ("sequence", "vh_sequence", "vl_sequence", "vhh_sequence"):
                        v = row.get(col, "").strip()
                        if len(v) >= 30:
                            clean = "".join(v.split()).upper()
                            seqs.add(clean)
        except Exception:
            pass

    for jfile in (REPO / "data").rglob("*.json"):
        try:
            if jfile.stat().st_size > 5_000_000:
                continue
            data = json.loads(jfile.read_text(encoding="utf-8", errors="replace"))
            _collect_seqs_from_obj(data, seqs)
        except Exception:
            pass

    return seqs


def _collect_seqs_from_obj(obj, seqs: set) -> None:
    _SEQ_KEYS = {
        "sequence", "vh_sequence", "vl_sequence", "vhh_sequence",
        "canonical_sequence", "aa_sequence",
    }
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _SEQ_KEYS and isinstance(v, str) and len(v) >= 30:
                clean = "".join(v.split()).upper()
                seqs.add(clean)
            else:
                _collect_seqs_from_obj(v, seqs)
    elif isinstance(obj, list):
        for item in obj:
            _collect_seqs_from_obj(item, seqs)


def _load_overrides() -> dict:
    if not OVERRIDES_FILE.exists():
        return {}
    try:
        data = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
        result = {}
        for entry in data.get("overrides", []):
            check = entry.get("check_id", "")
            value = entry.get("value", "")
            fpath = entry.get("file_path", "*")
            if check and value:
                result[f"{check}|{value}|{fpath}"] = entry
        return result
    except Exception as exc:
        print(f"[WARN] Could not load overrides: {exc}", file=sys.stderr)
        return {}


def _fingerprint_blocking(findings: list[Finding]) -> tuple:
    """Stable hash of unresolved HIGH/MEDIUM findings (for QA convergence)."""
    block = [
        f
        for f in findings
        if f.severity in (Severity.HIGH, Severity.MEDIUM)
        and not f.is_overridden
        and not f.is_auto_repaired
    ]
    parts = []
    for f in sorted(block, key=lambda x: (x.check_id, x.file_path, x.json_path, x.value)):
        parts.append(
            (
                f.check_id,
                f.file_path.replace("\\", "/"),
                f.json_path,
                f.value[:240],
                f.message[:240],
            )
        )
    return tuple(parts)


def _collect_findings(
    args: argparse.Namespace,
    roots: list[Path],
    registry: ValidatorRegistry,
    entities: list,
) -> list[Finding]:
    active_entities = []
    for e in entities:
        if e.entity_type == "pmid" and args.no_pmid_checks:
            continue
        if e.entity_type in ("url", "doi") and args.no_url_checks:
            continue
        if e.entity_type == "pdb_id" and args.no_pdb_checks:
            continue
        if e.entity_type == "sequence" and args.no_seq_checks:
            continue
        active_entities.append(e)

    findings: list[Finding] = list(registry.run_all(active_entities))

    if not args.no_parity:
        findings.extend(registry.run_parity(DOCS_DIR, SITE_TREES))

    run_ada = ADA_JSON.exists() and not args.no_ada_evidence
    if run_ada and (not args.no_pmid_checks or args.ada_evidence):
        ada_f = validate_ada_database(ADA_JSON, registry, REPO)
        registry.apply_overrides(ada_f)
        findings.extend(ada_f)

    return findings


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="InSynBio Site Integrity Pipeline — pre-deploy validation and repair.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--roots",
        nargs="+",
        default=DEFAULT_ROOTS,
        metavar="DIR",
        help="Content root directories relative to repo root.",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Apply safe auto-repairs.",
    )
    p.add_argument(
        "--qa-loop",
        "--until-stable",
        dest="qa_loop",
        action="store_true",
        help="After --apply, re-validate repeatedly until PASS, no progress, or --max-rounds.",
    )
    p.add_argument(
        "--max-rounds",
        type=int,
        default=15,
        metavar="N",
        help="Max QA rounds when using --qa-loop (default 15).",
    )
    p.add_argument("--no-pmid-checks", action="store_true")
    p.add_argument("--no-url-checks", action="store_true")
    p.add_argument("--no-pdb-checks", action="store_true")
    p.add_argument("--no-seq-checks", action="store_true")
    p.add_argument("--no-parity", action="store_true")
    p.add_argument(
        "--no-ada-evidence",
        action="store_true",
        help="Skip ADA_VALUE_IN_EVIDENCE (ada %% must appear in PMID or citation URL).",
    )
    p.add_argument(
        "--ada-evidence",
        action="store_true",
        help="Run ADA evidence check even when --no-pmid-checks (still fetches PubMed for ADA PMIDs).",
    )
    p.add_argument(
        "--relevance-threshold",
        type=float,
        default=0.15,
        metavar="FLOAT",
        help="PMID relevance threshold (default 0.15).",
    )
    p.add_argument(
        "--url-timeout",
        type=int,
        default=15,
        metavar="SEC",
        help="HTTP timeout for URL/PDB/ADA citation fetches (default 15).",
    )
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    print("=" * 70)
    print("InSynBio Site Integrity Pipeline (QA-strict)")
    print("=" * 70)

    roots = [REPO / r for r in args.roots]
    missing = [str(r) for r in roots if not r.exists()]
    if missing:
        print(f"[WARN] Some roots not found (skipping): {missing}", file=sys.stderr)
    roots = [r for r in roots if r.exists()]
    if not roots:
        print("[ERROR] No valid content roots found.", file=sys.stderr)
        return 1

    print(f"\nContent roots: {[str(r.relative_to(REPO)) for r in roots]}")

    overrides = _load_overrides()
    curated_seqs: set[str] = set()
    if not args.no_seq_checks:
        curated_seqs = _load_curated_sequences()
        if args.verbose:
            print(f"Curated sequences loaded: {len(curated_seqs)}")

    registry = ValidatorRegistry(
        overrides=overrides,
        ncbi_api_key=os.environ.get("NCBI_API_KEY"),
        pmid_relevance_threshold=args.relevance_threshold,
        url_timeout=args.url_timeout,
        curated_sequences=curated_seqs if not args.no_seq_checks else None,
        repo_root=REPO,
    )

    from collections import Counter

    round_idx = 0
    prev_fp: tuple | None = None
    all_repairs: list = []
    final_findings: list[Finding] = []
    if args.qa_loop and args.apply:
        max_rounds = max(1, args.max_rounds)
    elif args.apply:
        max_rounds = 3
    else:
        max_rounds = 1

    while round_idx < max_rounds:
        print(f"\n--- QA round {round_idx} ---")

        extractor = EntityExtractor(roots=roots, repo_root=REPO)
        entities = extractor.extract()
        by_type: dict[str, int] = {}
        for e in entities:
            by_type[e.entity_type] = by_type.get(e.entity_type, 0) + 1
        print(f"Entities extracted: {len(entities)} {by_type}")

        findings = _collect_findings(args, roots, registry, entities)
        sev_counts = Counter(f.severity.value for f in findings)
        print(f"Findings: {len(findings)} {dict(sev_counts)}")

        fp = _fingerprint_blocking(findings)
        final_findings = findings

        engine = SafeRepairEngine(repo_root=REPO, apply=args.apply)
        repairs = engine.compute_repairs(findings)
        applied: list = []
        if args.apply and repairs:
            applied = engine.apply_repairs(repairs, findings)
            all_repairs.extend(applied)
            print(f"Repairs applied this round: {len(applied)}")

        reporter = IntegrityReporter(REPORTS_DIR)
        run_meta = {
            "qa_round": round_idx,
            "qa_loop": args.qa_loop,
            "roots": [str(r.relative_to(REPO)) for r in roots],
            "apply": args.apply,
            "no_pmid_checks": args.no_pmid_checks,
            "no_url_checks": args.no_url_checks,
            "no_pdb_checks": args.no_pdb_checks,
            "no_seq_checks": args.no_seq_checks,
            "no_parity": args.no_parity,
            "no_ada_evidence": args.no_ada_evidence,
            "ada_evidence": args.ada_evidence,
            "fingerprint_blocking_count": len(fp),
        }
        reporter.write(findings, repairs, run_meta)

        exit_code = reporter.exit_code(findings)
        if exit_code == 0:
            print(f"\n[Gate] PASS (round {round_idx})")
            return 0

        if not args.apply:
            break

        if applied:
            round_idx += 1
            prev_fp = None
            if not args.qa_loop:
                print("\n[QA] Re-validating once after repairs …")
                continue
            continue

        if args.qa_loop:
            if prev_fp is not None and fp == prev_fp:
                print(
                    f"\n[QA] Consecutive identical blocking fingerprint "
                    f"({len(fp)} items); stopping auto-loop."
                )
                break
            prev_fp = fp
            round_idx += 1
            continue

        break

    reporter = IntegrityReporter(REPORTS_DIR)
    exit_code = reporter.exit_code(final_findings)
    unresolved = [
        f
        for f in final_findings
        if f.severity.value in ("HIGH", "MEDIUM")
        and not f.is_overridden
        and not f.is_auto_repaired
    ]
    print(f"\n[Gate] {'PASS' if exit_code == 0 else 'BLOCKED'}")
    if unresolved:
        print(f"Unresolved HIGH/MEDIUM: {len(unresolved)} — see reports/site_integrity_summary.md")
        if not args.apply:
            print("Tip: --apply for safe auto-fixes; --apply --qa-loop to re-check until stable.")
    print()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
