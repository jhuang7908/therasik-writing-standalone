#!/usr/bin/env python3
"""
Build split clinical ADA database:
  - clinical_ada_db_index.json  (lightweight, sortable, tier A/B/C, skip flags)
  - clinical_ada_db_data.json   (full evidence blobs keyed by record slug)

Union = reliable_merged (108, preferred) + 151 panel entries not in 108 (62) + 19 only in 108 = 170 INNs.
Tier A/B/C uses scripts/ada_tier_utils.py (PMID / FDA accessdata / ClinicalTrials vs other https).
Entries without usable ada_value are still indexed as Tier C with ada_status=unreported.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ada_tier_utils import (
    effective_tier_for_index,
    inn_slug,
    pmids_from_record,
)

RELIABLE_108 = (
    REPO
    / "data"
    / "ADA_reliable_package"
    / "from_openclaw_20260330"
    / "reliable_merged"
    / "reliable_ada_antibodies_database_20260330_231950.json"
)
PANEL_151 = REPO / "data" / "ADA_reliable_package" / "sources" / "151_antibody_evidence_database.json"
MERGED_MULTI = REPO / "data" / "ADA_reliable_package" / "ada_merged_multisource.json"
OUT_DIR = REPO / "data" / "ADA_reliable_package" / "clinical_db"
INDEX_JSON = OUT_DIR / "clinical_ada_db_index.json"
DATA_JSON = OUT_DIR / "clinical_ada_db_data.json"
INDEX_CSV = OUT_DIR / "clinical_ada_db_index.csv"


def _load(path: Path):
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _by_name(antibodies: list) -> dict:
    return {a["antibody_name"]: a for a in antibodies if a.get("antibody_name")}


def main() -> None:
    rel = _load(RELIABLE_108)
    p151 = _load(PANEL_151)
    if not rel:
        raise SystemExit(f"Missing {RELIABLE_108}")
    if not p151:
        raise SystemExit(f"Missing {PANEL_151} (copy from OpenClaw workspace)")

    m108 = _by_name(rel["antibodies"])
    m151 = _by_name(p151["antibodies"])

    multi_map: dict = {}
    mb = _load(MERGED_MULTI)
    if mb:
        for row in mb.get("antibodies", []):
            n = row.get("antibody_name")
            if n:
                multi_map[n] = row.get("supplemental") or {}

    all_names = sorted(set(m108.keys()) | set(m151.keys()))

    index_rows: list[dict] = []
    data_blob: dict = {}

    for name in all_names:
        slug = inn_slug(name)
        record_id = f"inn:{slug}"

        if name in m108:
            primary = json.loads(json.dumps(m108[name]))
            provenance = "reliable_merged_108"
        else:
            primary = json.loads(json.dumps(m151[name]))
            provenance = "panel_151_extended"

        ada_value = str(primary.get("ada_value") or "")
        tier, citation_urls, tier_notes, ada_status = effective_tier_for_index(ada_value, primary)
        pmids = pmids_from_record(primary, citation_urls)

        skip_expand = True
        reason_skip = "catalogued_in_clinical_ada_db"
        if tier == "C" and ada_status == "unreported":
            reason_skip = "catalogued_no_ada_value_tier_C"

        idx = {
            "record_id": record_id,
            "data_record_key": slug,
            "antibody_name": name,
            "evidence_tier": tier,
            "tier_rationale": tier_notes,
            "ada_status": ada_status,
            "ada_value_display": ada_value if ada_status != "unreported" else None,
            "has_numeric_ada": bool(primary.get("has_numeric_ada")),
            "evidence_quality": primary.get("evidence_quality"),
            "source_type": primary.get("source_type"),
            "canonical_provenance": provenance,
            "citation_urls": citation_urls,
            "pmids_extracted": pmids,
            "skip_automatic_ada_expansion": skip_expand,
            "skip_rationale": reason_skip,
        }
        index_rows.append(idx)

        data_blob[slug] = {
            "record_id": record_id,
            "antibody_name": name,
            "canonical_provenance": provenance,
            "primary_record": primary,
            "index_snapshot": {
                "evidence_tier": tier,
                "tier_rationale": tier_notes,
                "ada_status": ada_status,
                "citation_urls": citation_urls,
                "pmids_extracted": pmids,
            },
            "supplemental_multisource": multi_map.get(name) or None,
        }

    counts = {"A": 0, "B": 0, "C": 0}
    for r in index_rows:
        counts[r["evidence_tier"]] = counts.get(r["evidence_tier"], 0) + 1

    meta = {
        "schema_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "description": "Clinical therapeutic antibody ADA catalog: index + split data. Prefer reliable_merged_108 when present.",
        "tier_rules_file": "scripts/ada_tier_utils.py",
        "inputs": {
            "reliable_108": str(RELIABLE_108),
            "panel_151": str(PANEL_151),
            "ada_merged_multisource": str(MERGED_MULTI) if MERGED_MULTI.is_file() else None,
        },
        "counts": {
            "total_indexed_inns": len(index_rows),
            "evidence_tier": counts,
            "ada_status": _count_field(index_rows, "ada_status"),
        },
        "usage": {
            "index": str(INDEX_JSON),
            "data": str(DATA_JSON),
            "lookup": "Load data[data_record_key] after resolving name -> slug via index.",
            "expansion": "skip_automatic_ada_expansion=true for all rows: batch retrievers should exclude these INNs unless manually cleared.",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_JSON.write_text(
        json.dumps({"metadata": meta, "index": index_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    DATA_JSON.write_text(
        json.dumps({"metadata": meta, "records": data_blob}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with INDEX_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        fields = [
            "record_id",
            "antibody_name",
            "evidence_tier",
            "ada_status",
            "ada_value_display",
            "canonical_provenance",
            "evidence_quality",
            "skip_automatic_ada_expansion",
            "citation_urls",
            "pmids_extracted",
            "data_record_key",
        ]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in sorted(index_rows, key=lambda x: x["antibody_name"].lower()):
            row = dict(r)
            row["citation_urls"] = ";".join(row.get("citation_urls") or [])
            row["pmids_extracted"] = ";".join(row.get("pmids_extracted") or [])
            w.writerow({k: row.get(k) for k in fields})

    print(json.dumps(meta["counts"], indent=2))
    print(f"Wrote {INDEX_JSON.name}, {DATA_JSON.name}, {INDEX_CSV.name}")


def _count_field(rows: list[dict], key: str) -> dict[str, int]:
    o: dict[str, int] = {}
    for r in rows:
        v = r.get(key) or "unknown"
        o[v] = o.get(v, 0) + 1
    return o


if __name__ == "__main__":
    main()
