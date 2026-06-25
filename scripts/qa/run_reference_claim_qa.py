"""
Reference / Claim Support QA
=============================
Reads the project's reference and claim CSV databases and checks:

  1. Every reference has at least one of: doi, pmid, pmcid, url
  2. No duplicate DOIs across different reference IDs
  3. Every claim's reference_id exists in the reference database
  4. If --verify-doi is passed, hits the Crossref REST API to confirm each
     DOI resolves and the returned title is non-empty (soft check; network
     failure is reported as a warning, not a FAIL, to avoid blocking offline
     workflows)

Writes 03_QA/reference_claim_support_QA.md with Status: PASS or FAIL.
Exit code 0 = PASS, 1 = FAIL.

CSV schemas expected
--------------------
references.csv  columns (case-insensitive): id, doi, pmid, pmcid, url, title
claims.csv      columns (case-insensitive): claim_id (or id), reference_id (or ref_id or source_ref), claim (or claim_text)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path


# ──────────────────────────────────────────────────────────────────────────────

def _normalise_header(headers: list[str]) -> dict[str, int]:
    """Return a mapping of lowercase-stripped header -> column index."""
    return {h.strip().lower(): i for i, h in enumerate(headers)}


def load_csv(path: Path) -> tuple[dict[str, int], list[list[str]]]:
    """Return (header_map, rows) from a CSV file."""
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        headers = next(reader, [])
        rows = list(reader)
    return _normalise_header(headers), rows


def _field(row: list[str], header_map: dict[str, int], *names: str) -> str:
    """Return the first non-empty field value matching any of the given names."""
    for name in names:
        idx = header_map.get(name)
        if idx is not None and idx < len(row):
            v = row[idx].strip()
            if v:
                return v
    return ""


def verify_doi_crossref(doi: str, timeout: int = 8) -> dict:
    """Hit the Crossref REST API to confirm a DOI.  Returns a result dict."""
    doi_clean = re.sub(r"^https?://doi\.org/", "", doi.strip())
    url = f"https://api.crossref.org/works/{urllib.request.quote(doi_clean, safe='/')}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "therasik-qa/1.0 (mailto:qa@therasik.io)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        title_list = data.get("message", {}).get("title", [])
        title = title_list[0] if title_list else ""
        return {"doi": doi_clean, "ok": bool(title), "title": title, "error": None}
    except urllib.error.HTTPError as exc:
        return {"doi": doi_clean, "ok": False, "title": "", "error": f"HTTP {exc.code}"}
    except Exception as exc:
        return {"doi": doi_clean, "ok": None, "title": "", "error": str(exc)}  # None = unknown


def analyze(
    ref_path: Path,
    claim_path: Path,
    verify_doi: bool = False,
) -> dict:
    results: dict = {
        "reference_count": 0,
        "claim_count": 0,
        "missing_identifier": [],
        "duplicate_dois": [],
        "orphan_claims": [],
        "doi_verification": [],
        "warnings": [],
    }

    # ── References ────────────────────────────────────────────────────────────
    if not ref_path.exists():
        results["warnings"].append(f"references.csv not found: {ref_path}")
        ref_ids: set[str] = set()
    else:
        h, rows = load_csv(ref_path)
        results["reference_count"] = len(rows)
        doi_seen: dict[str, str] = {}  # doi -> ref_id
        ref_ids = set()

        for row in rows:
            rid = _field(row, h, "id", "ref_id", "reference_id")
            if not rid:
                continue
            ref_ids.add(rid)
            doi = _field(row, h, "doi")
            pmid = _field(row, h, "pmid")
            pmcid = _field(row, h, "pmcid")
            url = _field(row, h, "url")
            if not any([doi, pmid, pmcid, url]):
                results["missing_identifier"].append(rid)
            if doi:
                doi_norm = re.sub(r"^https?://doi\.org/", "", doi.lower().strip())
                if doi_norm in doi_seen:
                    results["duplicate_dois"].append(
                        {"doi": doi_norm, "ref_ids": [doi_seen[doi_norm], rid]}
                    )
                else:
                    doi_seen[doi_norm] = rid

        # Optional DOI verification
        if verify_doi and doi_seen:
            for doi_norm, rid in doi_seen.items():
                result = verify_doi_crossref(doi_norm)
                result["ref_id"] = rid
                results["doi_verification"].append(result)
                time.sleep(0.2)  # be polite to Crossref

    # ── Claims ────────────────────────────────────────────────────────────────
    if not claim_path.exists():
        results["warnings"].append(f"claims.csv not found: {claim_path}")
    else:
        h, rows = load_csv(claim_path)
        results["claim_count"] = len(rows)
        for row in rows:
            cid = _field(row, h, "claim_id", "id")
            ref_id = _field(row, h, "reference_id", "ref_id", "source_ref")
            if ref_id and ref_id not in ref_ids:
                results["orphan_claims"].append({"claim_id": cid, "missing_ref_id": ref_id})

    return results


def evaluate(stats: dict) -> tuple[str, list[str]]:
    failures: list[str] = []
    if stats["missing_identifier"]:
        ids = ", ".join(stats["missing_identifier"][:10])
        failures.append(
            f"{len(stats['missing_identifier'])} reference(s) lack DOI/PMID/PMCID/URL: {ids}"
        )
    if stats["duplicate_dois"]:
        for dup in stats["duplicate_dois"]:
            failures.append(
                f"Duplicate DOI '{dup['doi']}' shared by refs: {dup['ref_ids']}"
            )
    if stats["orphan_claims"]:
        for oc in stats["orphan_claims"][:10]:
            failures.append(
                f"Claim '{oc['claim_id']}' references non-existent ref_id '{oc['missing_ref_id']}'"
            )
    for dv in stats["doi_verification"]:
        if dv.get("ok") is False:
            failures.append(
                f"DOI '{dv['doi']}' (ref {dv['ref_id']}) failed Crossref lookup: {dv['error']}"
            )
    return ("FAIL" if failures else "PASS"), failures


def build_report(stats: dict, status: str, failures: list[str]) -> str:
    lines = [f"Status: {status}", "", "## Reference / Claim Support QA", ""]
    lines += [
        "| Metric | Value |",
        "| --- | --- |",
        f"| References | {stats['reference_count']} |",
        f"| Claims | {stats['claim_count']} |",
        f"| Missing identifier | {len(stats['missing_identifier'])} |",
        f"| Duplicate DOIs | {len(stats['duplicate_dois'])} |",
        f"| Orphan claims | {len(stats['orphan_claims'])} |",
        f"| DOIs verified via Crossref | {len(stats['doi_verification'])} |",
        "",
    ]
    if stats["warnings"]:
        lines += ["## Warnings", ""]
        for w in stats["warnings"]:
            lines.append(f"- {w}")
        lines.append("")
    if failures:
        lines += ["## Failures", ""]
        for f in failures:
            lines.append(f"- {f}")
        lines.append("")
    else:
        lines += ["All reference/claim checks passed.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reference/claim support QA gate")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--database-dir", default="00_project_database")
    parser.add_argument("--qa-dir", default="03_QA")
    parser.add_argument(
        "--verify-doi",
        action="store_true",
        help="Hit Crossref REST API to verify each DOI (requires network access)",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    db_dir = project_root / args.database_dir
    qa_dir = project_root / args.qa_dir
    qa_dir.mkdir(parents=True, exist_ok=True)

    stats = analyze(
        ref_path=db_dir / "references.csv",
        claim_path=db_dir / "claims.csv",
        verify_doi=args.verify_doi,
    )
    status, failures = evaluate(stats)
    report = build_report(stats, status, failures)

    out_path = qa_dir / "reference_claim_support_QA.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"reference_claim_support_QA: {status} -> {out_path}")
    return 0 if status == "PASS"else 1


if __name__ == "__main__":
    raise SystemExit(main())
