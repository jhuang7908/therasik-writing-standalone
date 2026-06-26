#!/usr/bin/env python3
"""
Read-only inventory for Writing Memory article-type cohort MVP.

Scans local papers_raw and article_profiles; compares to target cohort sizes.
Does not download papers or modify data.

Usage (from repo root):
  python scripts/audit_writing_cohort_inventory.py
  python scripts/audit_writing_cohort_inventory.py --out services/writing_memory/data/cohort_inventory.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WM = REPO / "services" / "writing_memory"
PAPERS_RAW = WM / "papers_raw"
PROFILES = WM / "article_profiles"
TYPE_INDEX = WM / "schemas" / "article_types_index.json"
SPECS_DIR = WM / "journal_specs" / "specs"

# MVP targets (proposal — align with docs/ARTICLE_TYPE_COHORT_MVP_V1.md)
COHORT_TARGETS = {
    "original_research": 8,
    "review_narrative": 6,
    "systematic_review": 5,
    "methods_protocols": 6,
    "case_report": 5,
    "brief_communication": 5,
    "perspective": 5,
    "clinical_trial": 5,
    "hypothesis": 5,
    "negative_results": 5,
    "resource_paper": 5,
    "translational_drug_discovery": 5,
}


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def scan_papers_raw() -> dict:
    by_journal: Counter[str] = Counter()
    files: list[str] = []
    for p in PAPERS_RAW.rglob("*.json"):
        if p.name.startswith("."):
            continue
        files.append(str(p.relative_to(WM)))
        data = _load_json(p)
        jk = data.get("journal_key") or p.parent.name
        by_journal[jk] += 1
    return {"total": len(files), "by_journal": dict(by_journal), "paths_sample": files[:5]}


def scan_profiles() -> dict:
    n = 0
    by_journal: Counter[str] = Counter()
    for p in PROFILES.rglob("*.json"):
        if p.name.startswith("_"):
            continue
        n += 1
        data = _load_json(p)
        j = (data.get("source") or {}).get("journal") or p.parent.name
        by_journal[str(j)[:40]] += 1
    return {"total": n, "by_journal": dict(by_journal)}


def cohort_gaps() -> list[dict]:
    # article_type tagging not implemented on papers_raw yet — all gaps = full target
    gaps = []
    for ctype, target in COHORT_TARGETS.items():
        gaps.append({
            "canonical_type": ctype,
            "local_count": 0,
            "target": target,
            "need_download": target,
            "note": "article_type not tagged on papers_raw yet; run Phase B classifier",
        })
    return gaps


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit writing_memory cohort inventory")
    ap.add_argument("--out", type=Path, default=None, help="Write JSON report path")
    args = ap.parse_args()

    idx = _load_json(TYPE_INDEX)
    spec_files = sorted(SPECS_DIR.glob("*.json")) if SPECS_DIR.exists() else []

    report = {
        "mvp_doc": "services/writing_memory/docs/ARTICLE_TYPE_COHORT_MVP_V1.md",
        "papers_raw": scan_papers_raw(),
        "article_profiles": scan_profiles(),
        "journal_specs_count": len(spec_files),
        "journal_specs_keys": [f.stem for f in spec_files],
        "canonical_types": idx.get("canonical_types") or [],
        "cohort_targets": COHORT_TARGETS,
        "cohort_gaps": cohort_gaps(),
        "reference_plugin": "journal_specs/format_reference.py",
    }

    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
