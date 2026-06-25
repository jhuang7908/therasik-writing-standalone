#!/usr/bin/env python3
"""
Find the 51 entries in clinical_ada_db_index that are not in
verifiable_ada_index (116) + verifiable_ada_excluded (3).
These were silently dropped by build_verifiable_classified_ada_db.py.
Classify them and output to three-file export.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

clinical_idx = REPO / "data/ADA_reliable_package/clinical_db/clinical_ada_db_index.json"
clinical_data = REPO / "data/ADA_reliable_package/clinical_db/clinical_ada_db_data.json"
verif_idx    = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_index.json"
verif_excl   = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_excluded.json"

ci_blob = json.loads(clinical_idx.read_text(encoding="utf-8"))
cd_blob = json.loads(clinical_data.read_text(encoding="utf-8"))
vi_blob = json.loads(verif_idx.read_text(encoding="utf-8"))
ex_blob = json.loads(verif_excl.read_text(encoding="utf-8"))

# Names already accounted for
accounted = {e["antibody_name"] for e in vi_blob["index"]}
accounted |= {e["antibody_name"] for e in ex_blob["excluded"]}

ci_index = ci_blob["index"]
records  = cd_blob.get("records", {})

missing = [e for e in ci_index if e["antibody_name"] not in accounted]
print(f"Total in clinical DB       : {len(ci_index)}")
print(f"Accounted for (116+3)      : {len(accounted)}")
print(f"Missing (silently dropped) : {len(missing)}")
print()

# Analyze why each was dropped by examining its properties
ADA_VALUE_SUSPECT = {
    "Atoltivimab", "Depemokimab", "Axatilimab", "Clesrovimab", "Domvanalimab", "Favezelimab"
}
AI_BATCH_PATTERNS = ("", "")

groups: dict[str, list] = {
    "ada_value_suspect":          [],
    "ai_batch_excluded":          [],
    "tier_C_no_anchor":           [],
    "no_traceable_url_pmid":      [],
    "other":                      [],
}

for row in sorted(missing, key=lambda x: x["antibody_name"]):
    name = row["antibody_name"]
    key  = row.get("data_record_key", "")
    primary = (records.get(key) or {}).get("primary_record") or {}
    es   = str(primary.get("evidence_source") or "")
    tier = row.get("evidence_tier", "")
    urls = row.get("citation_urls") or []
    pmids = row.get("pmids_extracted") or []
    ada_display = row.get("ada_value_display", "")

    if name in ADA_VALUE_SUSPECT:
        groups["ada_value_suspect"].append(row)
    elif es == "" or es.startswith(""):
        groups["ai_batch_excluded"].append(row)
    elif tier == "C":
        groups["tier_C_no_anchor"].append(row)
    elif not urls and not pmids:
        groups["no_traceable_url_pmid"].append(row)
    else:
        groups["other"].append(row)

print("=== Why dropped? ===")
for grp, entries in groups.items():
    print(f"\n[{len(entries):2d}] {grp}")
    for e in sorted(entries, key=lambda x: x["antibody_name"]):
        name = e["antibody_name"]
        key  = e.get("data_record_key","")
        primary = (records.get(key) or {}).get("primary_record") or {}
        es   = str(primary.get("evidence_source") or "")[:50]
        ada  = e.get("ada_value_display","")[:40]
        tier = e.get("evidence_tier","?")
        urls = e.get("citation_urls") or []
        pmids = e.get("pmids_extracted") or []
        print(f"    [{tier}] {name:30s}  ada={ada:40s}")
        print(f"          es={es}")
        if urls:
            print(f"          url={urls[0][:70]}")
        if pmids:
            print(f"          pmid={pmids[0]}")
