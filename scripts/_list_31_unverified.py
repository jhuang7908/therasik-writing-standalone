#!/usr/bin/env python3
"""List the 31 unverified entries and their sources."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
idx = json.loads(
    (REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_index.json").read_text(encoding="utf-8")
)
p1 = json.loads(
    (REPO / "data/ADA_reliable_package/verification/full_reverification_report.json").read_text(encoding="utf-8")
)
p1_map = {r["antibody_name"]: r for r in p1["results"]}

unverified = [
    e for e in idx["index"]
    if e.get("verification_status") == "unverified_pct_not_in_abstract_fulltext_needed"
]
print(f"Total unverified_pct_not_in_abstract_fulltext_needed: {len(unverified)}\n")

for e in sorted(unverified, key=lambda x: x["antibody_name"]):
    name = e["antibody_name"]
    ada  = e.get("ada_value_display", "")
    pmids = e.get("pmids_extracted") or []
    urls  = e.get("citation_urls") or []
    es    = e.get("evidence_source", "")
    p1r   = p1_map.get(name, {})
    snip  = p1r.get("text_snippet", "")[:100]
    src   = p1r.get("source_tried", "")
    print(f"[{e.get('class_evidence_tier')}] {name}")
    print(f"  ada_value_display : {ada}")
    print(f"  evidence_source   : {es}")
    print(f"  pmids_extracted   : {pmids}")
    print(f"  citation_urls     : {[u[:70] for u in urls]}")
    print(f"  p1_source_tried   : {src}")
    print(f"  p1_snip           : {snip}")
    print()
