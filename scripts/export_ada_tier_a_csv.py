#!/usr/bin/env python3
"""
Export ada_curated_tier_A.json (primary reliable ADA set) to CSV for Excel / pipelines.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_JSON = (
    REPO
    / "data"
    / "ADA_reliable_package"
    / "curated"
    / "ada_curated_tier_A.json"
)
DEFAULT_CSV = REPO / "data" / "ADA_reliable_package" / "ada_curated_tier_A.csv"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--output", type=Path, default=DEFAULT_CSV)
    ap.add_argument(
        "--omit-evidence-chain",
        action="store_true",
        help="Exclude long evidence_chain column (URLs + summary still exported).",
    )
    args = ap.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"Missing {args.input}; run scripts/build_ada_reliable_database.py first.")

    with args.input.open(encoding="utf-8") as f:
        bundle = json.load(f)

    rows = bundle.get("antibodies", [])
    fieldnames = [
        "antibody_name",
        "ada_value",
        "has_numeric_ada",
        "evidence_quality",
        "source_type",
        "source_url_field",
        "pmids_extracted",
        "citation_urls",
        "evidence_source",
        "evidence_tier",
        "evidence_tier_notes",
        "needs_retrieval",
        "suggested_pubmed_query",
    ]
    if not args.omit_evidence_chain:
        fieldnames.append("evidence_chain")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for ab in sorted(rows, key=lambda x: (x.get("antibody_name") or "").lower()):
            row = {k: ab.get(k) for k in fieldnames}
            p = ab.get("pmids_extracted") or []
            row["pmids_extracted"] = ";".join(str(x) for x in p)
            u = ab.get("citation_urls") or []
            row["citation_urls"] = ";".join(str(x) for x in u)
            w.writerow(row)

    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
