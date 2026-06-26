#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" germline """

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#  clean JSONL
clean_path = PROJECT_ROOT / "data" / "germlines" / "v1_clean" / "germline_assets_clean.jsonl"
with open(clean_path, "r", encoding="utf-8") as f:
    clean_lines = f.readlines()

print(f"Clean : {len(clean_lines)}")
print()

# 
if clean_lines:
    first = json.loads(clean_lines[0])
    print(":")
    print(f"  sequence_id: {first.get('sequence_id')}")
    print(f"  qa_status: {first.get('qa_status')}")
    print(f"  imgt_success: {first.get('imgt_success')}")
    print(f"  kabat_success: {first.get('kabat_success')}")
    print(f"  segments: {list(first.get('segments', {}).keys())}")
    segments = first.get('segments', {})
    for region, seq in segments.items():
        print(f"    {region}: len={len(seq)}")
    print()

#  qa_status
all_have_qa_status = all(
    json.loads(line).get("qa_status") == "PASS_CLEAN"
    for line in clean_lines
)
print(f" qa_status='PASS_CLEAN': {all_have_qa_status}")

