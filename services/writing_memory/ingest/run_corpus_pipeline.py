"""
run_corpus_pipeline.py — Server-side corpus refresh orchestrator.

Runs the full Writing Memory ingest chain in order:
  1. probe PMC hit-rate (PubMed → PMC JATS availability)
  2. merge hit-rate reports → corpus_manifest.json
  3. load_papers (download + JATS parse → papers_raw/)
  4. run_article_profiles (Claude Sonnet → article_profiles/)
  5. aggregate_journal_profiles (Claude Sonnet → journal_profiles/)
  6. embed_chunks (OpenAI embeddings)
  7. build_index (numpy cosine index → _index/)

Designed for unattended VPS runs via systemd timer or cron.
All steps support --resume on their underlying scripts.

Usage (from repo root)
----------------------
    # Full refresh — original research corpus only (current MVP default)
    python services/writing_memory/ingest/run_corpus_pipeline.py

    # Also probe + ingest Review articles (20 per journal)
    python services/writing_memory/ingest/run_corpus_pipeline.py \\
        --article-types research review --target 50 --review-target 20

    # Skip probe (manifest already exists) — re-run profiles + index only
    python services/writing_memory/ingest/run_corpus_pipeline.py \\
        --skip-probe --skip-load

    # Smoke test (fast, ~5 papers total)
    python services/writing_memory/ingest/run_corpus_pipeline.py --smoke

Environment (required on server)
------------------------------
    ANTHROPIC_API_KEY   Claude — article + journal profiles
    OPENAI_API_KEY      OpenAI — embeddings
    NCBI_API_KEY        optional — raises PubMed rate 3→10 req/s
    NCBI_EMAIL          recommended polite-pool contact

Estimated runtime (full, 150 research papers)
---------------------------------------------
    probe + load     ~30–45 min  (NCBI only)
    article profiles ~20–30 min  (Claude Sonnet, 3 workers)
    aggregate        ~3 min       (3 Claude calls)
    embed + index    ~5 min       (OpenAI)
    Total            ~60–90 min
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SERVICE_ROOT = _HERE.parent
_REPO_ROOT = _SERVICE_ROOT.parent.parent
_OUT = _HERE / "_out"

JOURNAL_KEYS = ["pnas", "elife", "plos_med"]

ARTICLE_TYPE_TARGETS = {
    "research":    50,
    "review":      20,
    "case_report": 10,
    "letter":       8,
}


def _run(cmd: list[str], *, label: str) -> None:
    print(f"\n{'='*60}\n▶ {label}\n  {' '.join(cmd)}\n{'='*60}", flush=True)
    result = subprocess.run(cmd, cwd=str(_REPO_ROOT))
    if result.returncode != 0:
        raise SystemExit(f"Step failed ({label}): exit {result.returncode}")


def _probe(
    article_type: str,
    target: int,
    years: int,
    candidates: int,
    smoke: bool,
    strategy: str = "classic",
) -> Path:
    out = _OUT / f"pmc_hitrate_{article_type}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    cmd = [
        sys.executable,
        str(_HERE / "probe_pmc_hitrate.py"),
        "--strategy", strategy,
        "--article-type", article_type,
        "--years", str(years),
        "--target", str(4 if smoke else target),
        "--out", str(out),
    ]
    if candidates:
        cmd.extend(["--candidates", str(candidates if not smoke else max(candidates, 80))])
    if article_type != "research" or smoke:
        cmd.append("--no-fail-on-short")
    _run(cmd, label=f"probe [{article_type}] ({strategy})")
    return out


def _build_manifest(probe_reports: dict[str, Path], article_types: list[str]) -> Path:
    """Build corpus_manifest.json from one probe report per article type."""
    manifest: dict = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "article_types": article_types,
        "sources": {},
        "journals": {},
        "total_qualified": 0,
    }

    for atype in article_types:
        report_path = probe_reports[atype]
        report = json.loads(report_path.read_text(encoding="utf-8"))
        manifest["sources"][atype] = str(report_path)

        for jblock in report.get("journals", []):
            key = jblock["key"]
            slot = manifest["journals"].setdefault(key, {
                "display": jblock["display"],
                "by_article_type": {},
            })
            pmids = jblock.get("qualified_pmids", [])
            slot["by_article_type"][atype] = {
                "qualified_count": len(pmids),
                "qualified_pmids": pmids,
            }
            manifest["total_qualified"] += len(pmids)

    # Backward-compat: flat qualified_pmids for research-only manifests
    if article_types == ["research"]:
        for key in JOURNAL_KEYS:
            if key in manifest["journals"]:
                bt = manifest["journals"][key]["by_article_type"].get("research", {})
                manifest["journals"][key]["qualified_count"] = bt.get("qualified_count", 0)
                manifest["journals"][key]["qualified_pmids"] = bt.get("qualified_pmids", [])

    out = _OUT / "corpus_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ Manifest: {out}  ({manifest['total_qualified']} PMIDs across {len(article_types)} type(s))")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run full Writing Memory corpus pipeline.")
    ap.add_argument(
        "--article-types", nargs="+",
        default=["research"],
        choices=list(ARTICLE_TYPE_TARGETS.keys()),
        help="Which PubMed publication types to ingest (default: research only)",
    )
    ap.add_argument("--target", type=int, default=50,
                    help="Target papers per journal for research (default 50)")
    ap.add_argument("--review-target", type=int, default=20,
                    help="Target per journal for review articles")
    ap.add_argument("--years", type=int, default=5,
                    help="years window when --strategy recent")
    ap.add_argument("--candidates", type=int, default=0,
                    help="PubMed retmax per journal (0=use strategy default, classic=200)")
    ap.add_argument(
        "--strategy",
        default="classic",
        choices=["classic", "recent"],
        help="classic=free PMC full text in older window (MVP default)",
    )
    ap.add_argument("--smoke", action="store_true",
                    help="Fast smoke run (~4 papers per journal per type)")
    ap.add_argument("--skip-probe", action="store_true")
    ap.add_argument("--skip-load", action="store_true")
    ap.add_argument("--skip-profiles", action="store_true")
    ap.add_argument("--skip-aggregate", action="store_true")
    ap.add_argument("--skip-embed", action="store_true")
    ap.add_argument("--skip-index", action="store_true")
    ap.add_argument("--restart-service", action="store_true",
                    help="systemctl restart writing-memory after index rebuild")
    args = ap.parse_args(argv)

    def target_for(atype: str) -> int:
        if atype == "research":
            return args.target
        if atype == "review":
            return args.review_target
        return ARTICLE_TYPE_TARGETS.get(atype, 10)

    probe_reports: dict[str, Path] = {}
    manifest_path = _OUT / "corpus_manifest.json"

    # ── Step 1: Probe ────────────────────────────────────────────────────
    if not args.skip_probe:
        for atype in args.article_types:
            probe_reports[atype] = _probe(
                atype, target_for(atype), args.years, args.candidates, args.smoke,
                strategy=args.strategy,
            )
        manifest_path = _build_manifest(probe_reports, args.article_types)
    elif not manifest_path.exists():
        raise SystemExit(f"--skip-probe but manifest missing: {manifest_path}")

    resume_flag = ["--resume"]
    smoke_flag = ["--smoke"] if args.smoke else []

    # ── Step 2: Load papers ──────────────────────────────────────────────
    if not args.skip_load:
        cmd = [
            sys.executable, str(_HERE / "load_papers.py"),
            "--manifest", str(manifest_path),
            *resume_flag, *smoke_flag,
        ]
        _run(cmd, label="load_papers")

    # ── Step 3: Article profiles (Claude) ────────────────────────────────
    if not args.skip_profiles:
        cmd = [
            sys.executable, str(_HERE / "run_article_profiles.py"),
            *resume_flag, *smoke_flag,
        ]
        _run(cmd, label="run_article_profiles (Claude Sonnet)")

    # ── Step 4: Journal profiles (Claude) ────────────────────────────────
    if not args.skip_aggregate:
        cmd = [sys.executable, str(_HERE / "aggregate_journal_profiles.py")]
        _run(cmd, label="aggregate_journal_profiles (Claude Sonnet)")

    # ── Step 5: Embeddings (OpenAI) ──────────────────────────────────────
    if not args.skip_embed:
        cmd = [
            sys.executable, str(_HERE / "embed_chunks.py"),
            *resume_flag, *smoke_flag,
        ]
        _run(cmd, label="embed_chunks (OpenAI)")

    # ── Step 6: Vector index ───────────────────────────────────────────
    if not args.skip_index:
        cmd = [sys.executable, str(_HERE / "build_index.py")]
        _run(cmd, label="build_index")

    if args.restart_service:
        _run(
            ["systemctl", "restart", "writing-memory"],
            label="restart writing-memory",
        )

    print(f"\n✅ Corpus pipeline complete — {datetime.now(timezone.utc).isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
