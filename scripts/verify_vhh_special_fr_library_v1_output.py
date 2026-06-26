#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH Special FR Library v1 

。
"""

from __future__ import annotations

import json
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    jsonl_path = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_special_fr_library_v1.jsonl"
    qc_csv_path = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "qc" / "vhh_special_fr_library_v1_summary.csv"
    
    print("=" * 80)
    print(" VHH Special FR Library v1 ")
    print("=" * 80)
    print()
    
    #  JSONL
    if not jsonl_path.exists():
        print(f"❌ JSONL : {jsonl_path}")
        return
    
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    
    print(f"JSONL : {len(records)}")
    
    # 
    required_fields = ["fr_id", "template_type", "source_sequence_id", "fr_sequence", 
                      "segments", "vhh_hallmark", "canonical_proxy"]
    
    all_valid = True
    for field in required_fields:
        count = sum(1 for r in records if field in r)
        status = "✅" if count == len(records) else "❌"
        print(f"  {status}  {field}: {count} / {len(records)}")
        if count != len(records):
            all_valid = False
    
    # 
    if records:
        example = records[0]
        print()
        print(" ():")
        print(f"  fr_id: {example.get('fr_id')}")
        print(f"  template_type: {example.get('template_type')}")
        print(f"  fr_sequence : {len(example.get('fr_sequence', ''))}")
        print(f"  canonical_proxy.agg: {example.get('canonical_proxy', {}).get('agg')}")
    
    print()
    
    #  QC CSV
    if not qc_csv_path.exists():
        print(f"❌ QC CSV : {qc_csv_path}")
        return
    
    qc_records = []
    with open(qc_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qc_records.append(row)
    
    print(f"QC CSV : {len(qc_records)}")
    
    if len(records) == len(qc_records):
        print("✅ JSONL  QC CSV ")
    else:
        print(f"❌ : JSONL={len(records)}, QC CSV={len(qc_records)}")
    
    print()
    print("=" * 80)
    
    if all_valid and len(records) == len(qc_records):
        print("✅ ！")
    else:
        print("❌ ！")

if __name__ == "__main__":
    main()










