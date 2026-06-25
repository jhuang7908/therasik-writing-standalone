#!/usr/bin/env python3
"""Deep check of suspicious or high-ADA entries in the verifiable database."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IDX_PATH = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_index.json"
DATA_PATH = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_data.json"

TARGETS = [
    "Favezelimab",
    "Toripalimab",
    "Satralizumab",
    "Rilonacept",
    "Dinutuximab",
    "Bimekizumab",
    "Vedolizumab",
    "Nivolumab",
    "Mepolizumab",
    "Reslizumab",
    "Ozoralizumab",
]

idx = json.loads(IDX_PATH.read_text(encoding="utf-8"))
data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
records = data["records"]
name_to_key = {r["antibody_name"]: r["data_record_key"] for r in idx["index"]}

for name in TARGETS:
    key = name_to_key.get(name)
    if not key:
        print(f"{name}: NOT IN INDEX\n")
        continue
    rec = records.get(key, {})
    pr = rec.get("primary_record", {})
    print(f"=== {name} ===")
    print(f"  ada_value_display : {pr.get('ada_value_display', '')}")
    print(f"  evidence_source   : {pr.get('evidence_source', '')}")
    pmids = pr.get("pmids") or []
    print(f"  pmids             : {pmids}")
    urls = pr.get("citation_urls") or pr.get("source_urls") or []
    print(f"  urls              : {str(urls)[:200]}")
    chain = str(pr.get("evidence_chain", ""))[:400]
    print(f"  evidence_chain    : {chain}")
    print()
