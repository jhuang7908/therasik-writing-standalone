#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Canonical Proxy  debug 
"""

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
debug_csv = PROJECT_ROOT / "output" / "canonical_proxy_scoring_debug.csv"

print("=" * 120)
print("Canonical Proxy  Debug ")
print("=" * 120)
print()

with open(debug_csv, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f": {len(rows)}")
print()

# 
proxy_agg_matches = sum(1 for row in rows if row["proxy_agg_match"] == "✅")
score_diff_matches = sum(1 for row in rows if row["score_diff_match"] == "✅")
rank_changes = sum(1 for row in rows if row["rank_changed"] == "✅")

print(f":")
print(f"  proxy_agg : {proxy_agg_matches} / {len(rows)}")
print(f"  score_diff : {score_diff_matches} / {len(rows)}")
print(f"  : {rank_changes} / {len(rows)}")
print()

print("=" * 120)
print(" debug ")
print("=" * 120)
print()

for i, row in enumerate(rows, 1):
    seq_id = row["sequence_id"]
    proxy_cdr1 = float(row["proxy_cdr1"])
    proxy_cdr2 = float(row["proxy_cdr2"])
    proxy_agg = float(row["proxy_agg"])
    score_old = float(row["total_score_old"])
    score_new = float(row["total_score_new"])
    score_diff = float(row["score_diff"])
    rank_old = int(row["rank_old"])
    rank_new = int(row["rank_new"])
    rank_changed = row["rank_changed"]
    
    print(f"{i:2}. {seq_id:20} | "
          f"proxy_cdr1={proxy_cdr1:6.4f} proxy_cdr2={proxy_cdr2:6.4f} proxy_agg={proxy_agg:6.4f} | "
          f"score: {score_old:6.4f} -> {score_new:6.4f} (diff={score_diff:6.4f}) | "
          f"rank: {rank_old:2} -> {rank_new:2} {rank_changed}")

print()
print("=" * 120)
print("✅ ！")
print("=" * 120)













