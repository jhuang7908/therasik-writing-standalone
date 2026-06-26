#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" germline """

import csv
import json
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#  CSV
csv_path = PROJECT_ROOT / "output" / "germline_numbering_summary.csv"
rows = list(csv.DictReader(open(csv_path, "r", encoding="utf-8")))

print("=" * 80)
print("Germline ")
print("=" * 80)
print(f": {len(rows)}")
print()

# /
success_count = sum(1 for r in rows if r["failure_classification"] == "success")
failure_count = len(rows) - success_count
print(f"✅ : {success_count}")
print(f"❌ : {failure_count}")
print()

# 
failure_counts = Counter(r["failure_classification"] for r in rows)
print(":")
for failure_type, count in sorted(failure_counts.items()):
    print(f"  {failure_type}: {count} ")
print()

# 5
print("5:")
for i, row in enumerate(rows[:5], 1):
    print(f"  {i}. {row['sequence_id']}")
    print(f"     : {row['sequence_length']}, IMGT: {row['imgt_success']}, Kabat: {row['kabat_success']}")
    print(f"     FR1={row['FR1_len']}, CDR1={row['CDR1_len']}, FR2={row['FR2_len']}, CDR2={row['CDR2_len']}, FR3={row['FR3_len']}")
    print(f"     (1-104): {row['coverage_imgt_1_104']}, (1-117): {row['coverage_imgt_1_117']}")
    print(f"     : {row['failure_classification']}")
    print()

#  JSONL
jsonl_path = PROJECT_ROOT / "output" / "germline_numbering_segments.jsonl"
if jsonl_path.exists():
    with open(jsonl_path, "r", encoding="utf-8") as f:
        jsonl_lines = f.readlines()
    print(f"JSONL : {len(jsonl_lines)}")
    print()
    
    #  segments
    if jsonl_lines:
        first_record = json.loads(jsonl_lines[0])
        print(" segments:")
        segments = first_record.get("segments", {})
        for region, seq in segments.items():
            print(f"  {region}: {seq} (len={len(seq)})")

print("=" * 80)













