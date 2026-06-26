#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 canonical_proxy 
"""

import json
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from core.germline_assets_loader import get_germline_assets_path

#  JSONL（）
jsonl_path = get_germline_assets_path(include_canonical_proxy=True)
print("=" * 80)
print(" JSONL ")
print("=" * 80)

with open(jsonl_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f": {len(lines)}")

# 
record = json.loads(lines[0])
print(f"\n: {record['sequence_id']}")
print(f"CDR1 canonical_proxy: {json.dumps(record.get('canonical_proxy_cdr1'), indent=2, ensure_ascii=False)}")
print(f"CDR2 canonical_proxy: {json.dumps(record.get('canonical_proxy_cdr2'), indent=2, ensure_ascii=False)}")

# 
cdr1_count = sum(1 for line in lines if json.loads(line).get("canonical_proxy_cdr1"))
cdr2_count = sum(1 for line in lines if json.loads(line).get("canonical_proxy_cdr2"))

print(f"\n:")
print(f"  CDR1 : {cdr1_count} / {len(lines)}")
print(f"  CDR2 : {cdr2_count} / {len(lines)}")

#  QC CSV（）
from core.germline_assets_loader import QC_DIR
qc_path = QC_DIR / "canonical_proxy_qc.csv"
print("\n" + "=" * 80)
print(" QC CSV ")
print("=" * 80)

with open(qc_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f": {len(rows)}")
print(f"\n 5 :")
for i, row in enumerate(rows[:5], 1):
    print(f"  {i}. {row['sequence_id']}")
    print(f"     CDR1: {row['cdr1_cluster_id']} (score={row['cdr1_proxy_score']})")
    print(f"     CDR2: {row['cdr2_cluster_id']} (score={row['cdr2_proxy_score']})")

print("\n" + "=" * 80)
print("✅ ！")
print("=" * 80)

