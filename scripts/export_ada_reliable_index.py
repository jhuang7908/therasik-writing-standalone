#!/usr/bin/env python3
"""
Export the reliable ADA JSON bundle to a flat CSV for review and downstream
structured annotation (target, indication, regimen columns are placeholders).

Primary data: data/ADA_reliable_package/from_openclaw_20260330/reliable_merged/
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_JSON = (
    REPO
    / "data"
    / "ADA_reliable_package"
    / "from_openclaw_20260330"
    / "reliable_merged"
    / "reliable_ada_antibodies_database_20260330_231950.json"
)
DEFAULT_CSV = (
    REPO
    / "data"
    / "ADA_reliable_package"
    / "ada_reliable_index_20260330.csv"
)


def _extract_http_urls(text: str) -> list[str]:
    if not text:
        return []
    return re.findall(r"https?://[^\s\)\]\"']+", text)


def _infer_route_hint(chain: str) -> str:
    if not chain:
        return ""
    lower = chain.lower()
    if "subcutaneous" in lower or "subcut" in lower:
        return "subcutaneous (mentioned in evidence text)"
    if "intravenous" in lower or " i.v." in lower or " iv " in lower:
        return "intravenous (mentioned in evidence text)"
    if "intramuscular" in lower:
        return "intramuscular (mentioned in evidence text)"
    return ""


def main() -> None:
    path = DEFAULT_JSON
    if not path.is_file():
        raise SystemExit(f"Missing database JSON: {path}")

    with path.open(encoding="utf-8") as f:
        bundle = json.load(f)

    rows = []
    for ab in bundle.get("antibodies", []):
        chain = ab.get("evidence_chain") or ""
        urls = _extract_http_urls(chain)
        if ab.get("source_url") and str(ab["source_url"]).startswith("http"):
            urls = [ab["source_url"]] + [u for u in urls if u != ab["source_url"]]
        pmids = ab.get("pmids") or []
        pmid_str = ";".join(str(p) for p in pmids if p)

        rows.append(
            {
                "antibody_name": ab.get("antibody_name", ""),
                "ada_value": ab.get("ada_value", ""),
                "has_numeric_ada": ab.get("has_numeric_ada", ""),
                "source_type": ab.get("source_type", ""),
                "source_url_field": ab.get("source_url", ""),
                "citation_urls_in_chain": ";".join(dict.fromkeys(urls)),
                "pmids": pmid_str,
                "evidence_quality": ab.get("evidence_quality", ""),
                "evidence_source": ab.get("evidence_source", ""),
                "route_admin_hint_from_text": _infer_route_hint(chain),
                "target_gene_or_moiety": "",
                "indication_or_disease": "",
                "dose_regimen_population_cycle": "",
                "value_matches_source_verified_by_human": "",
                "notes": "",
            }
        )

    rows.sort(key=lambda r: r["antibody_name"].lower())

    DEFAULT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {DEFAULT_CSV}")


if __name__ == "__main__":
    main()
