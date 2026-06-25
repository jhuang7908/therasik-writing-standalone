#!/usr/bin/env python3
"""
Full provenance audit: for every entry in the verifiable index, check
whether its evidence_source pattern, citation_urls and pmids are actually
traceable. Flag any that rely solely on 'A' with no real anchor.
"""
import json, re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IDX_PATH = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_index.json"
DATA_PATH = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_data.json"

idx_blob = json.loads(IDX_PATH.read_text(encoding="utf-8"))
data_blob = json.loads(DATA_PATH.read_text(encoding="utf-8"))
records = data_blob["records"]

BATCH_PATTERNS = ["", "", "250", "AI batch"]
TIER_A_DOMAINS = ["accessdata.fda.gov", "clinicaltrials.gov", "pmc.ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov"]

def has_real_anchor(index_row, primary_rec):
    """Return (has_anchor: bool, anchor_type: str)"""
    # PMIDs from index row
    pm_idx = [p for p in (index_row.get("pmids_extracted") or []) if str(p).strip().isdigit()]
    # PMIDs from primary record
    pm_prim = [p for p in (primary_rec.get("pmids") or []) if str(p).strip().isdigit()]
    # URLs from index row
    urls_idx = [u for u in (index_row.get("citation_urls") or []) if isinstance(u, str) and u.startswith("http")]
    # URLs from primary record
    urls_prim = [u for u in (primary_rec.get("citation_urls") or primary_rec.get("source_urls") or []) if isinstance(u, str) and u.startswith("http")]
    
    all_pmids = pm_idx + pm_prim
    all_urls = urls_idx + urls_prim
    
    if all_pmids:
        return True, f"pmid:{all_pmids[0]}"
    # Check for Tier A domain URLs
    for u in all_urls:
        for d in TIER_A_DOMAINS:
            if d in u.lower():
                return True, f"tier_a_url:{d}"
    if all_urls:
        return True, f"url:{all_urls[0][:60]}"
    return False, "NO_ANCHOR"

def is_batch_source(es: str) -> bool:
    for pat in BATCH_PATTERNS:
        if pat in es:
            return True
    return False

print("=== FULL PROVENANCE AUDIT ===\n")

no_anchor_entries = []
batch_no_pmid_entries = []
ok_entries = []

for row in sorted(idx_blob["index"], key=lambda x: x["antibody_name"]):
    name = row["antibody_name"]
    key = row["data_record_key"]
    primary = (records.get(key) or {}).get("primary_record") or {}
    es = str(primary.get("evidence_source") or row.get("evidence_source") or "")
    tier = row.get("class_evidence_tier")
    ada_val = row.get("ada_value_display", "")
    prov = row.get("canonical_provenance", "")
    
    has_anch, anch_type = has_real_anchor(row, primary)
    batch = is_batch_source(es)
    
    if not has_anch:
        no_anchor_entries.append({
            "name": name, "tier": tier, "es": es, "prov": prov, "ada": ada_val,
            "anchor": anch_type
        })
    elif batch:
        batch_no_pmid_entries.append({
            "name": name, "tier": tier, "es": es, "prov": prov, "ada": ada_val,
            "anchor": anch_type
        })
    else:
        ok_entries.append(name)

print(f"PASS (real anchor, non-batch source): {len(ok_entries)}")
print(f"WARN (batch source pattern BUT has URL/PMID): {len(batch_no_pmid_entries)}")
print(f"FAIL (NO traceable anchor found): {len(no_anchor_entries)}")

if batch_no_pmid_entries:
    print("\n--- WARN: Batch-source but has URL/PMID (verify these) ---")
    for e in batch_no_pmid_entries:
        print(f"  [{e['tier']}] {e['name']:30s}  es={e['es'][:40]:40s}  ada={e['ada'][:40]:40s}  anchor={e['anchor']}")

if no_anchor_entries:
    print("\n--- FAIL: No traceable anchor (should be excluded or fixed) ---")
    for e in no_anchor_entries:
        print(f"  [{e['tier']}] {e['name']:30s}  es={e['es'][:40]:40s}  ada={e['ada'][:40]:40s}  prov={e['prov'][:30]}")
