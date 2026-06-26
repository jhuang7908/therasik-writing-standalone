#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Fc"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANNOTATED_FILE = PROJECT_ROOT / "data" / "germlines" / "fc_aa" / "annotated" / "human_IGHC_annotated.json"

print("=" * 80)
print("Fc")
print("=" * 80)

with open(ANNOTATED_FILE, encoding='utf-8') as f:
    data = json.load(f)

# Human IgG1*01
igg1 = data['IgG1*01']

print(f"\n：Human IgG1*01")
print("-" * 80)
print(f": {igg1['total_length']}aa")
print(f"CH4: {igg1['has_ch4']}")
print()

print("（1-based）:")
print("-" * 80)
current_pos = 1
for r in igg1['regions']:
    region_name = r['region']
    start = r['start']
    end = r['end']
    length = r['length']
    
    # 
    expected_start = current_pos
    expected_end = current_pos + length - 1
    
    status = "✓" if start == expected_start and end == expected_end else "✗"
    
    print(f"{status} {region_name:12}  {start:3}-{end:3}  {length:3}aa")
    if status == "✗":
        print(f"    : {expected_start}-{expected_end}")
    
    current_pos += length

print()
print(":")
print("-" * 80)
full_seq = igg1['full_sequence']
for r in igg1['regions']:
    region_name = r['region']
    start = r['start'] - 1  # 0-based
    end = r['end']
    region_seq = full_seq[start:end]
    print(f"{region_name:12} [{start+1:3}-{end:3}] {region_seq[:30]}...")

print()
print("=" * 80)
print(":")
print("=" * 80)
print("""
1. ：
   - FASTA header（CH1, CH2, CH3, Hinge）
   - "Unknown"，（<20aa → Hinge, ≥20aa → C_terminal）

2. （1-based）：
   - 1
   - ：CH1 → Hinge → CH2 → CH3 → C_terminal
   - start = end + 1
   - end = start + length - 1

3. ：
   - full_sequence = CH1 + Hinge + CH2 + CH3 + C_terminal
   -  = 

4. Python（0-based）：
   - region_seq = full_sequence[start-1:end]
""")


















