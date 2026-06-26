#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Variant Ranking Debug 
"""

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
debug_csv = PROJECT_ROOT / "output" / "variant_rank_with_canonical_proxy_debug.csv"

weight = 0.10

print("=" * 120)
print("（）")
print("=" * 120)
print()

with open(debug_csv, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

proxy_agg_matches = 0
score_diff_matches = 0

for i, row in enumerate(rows, 1):
    variant_id = row["variant_id"]
    proxy_cdr1 = float(row["proxy_cdr1"])
    proxy_cdr2 = float(row["proxy_cdr2"])
    proxy_agg = float(row["proxy_agg"])
    score_diff = float(row["score_diff"])
    total_score_old = float(row["total_score_old"])
    total_score_new = float(row["total_score_new"])
    
    #  proxy_agg = min(proxy_cdr1, proxy_cdr2)
    expected_agg = min(proxy_cdr1, proxy_cdr2) if proxy_cdr1 > 0 and proxy_cdr2 > 0 else 0.0
    agg_match = abs(proxy_agg - expected_agg) < 0.0001
    if agg_match:
        proxy_agg_matches += 1
    
    #  score_diff = weight * proxy_agg
    expected_diff = weight * proxy_agg
    diff_match = abs(score_diff - expected_diff) < 0.0001
    if diff_match:
        score_diff_matches += 1
    
    print(f"{i:2}. {variant_id:25} | "
          f"proxy_agg={proxy_agg:.4f} (expected={expected_agg:.4f}) {'✅' if agg_match else '❌'} | "
          f"score_diff={score_diff:.4f} (expected={expected_diff:.4f}) {'✅' if diff_match else '❌'}")

print()
print("=" * 120)
print("")
print("=" * 120)
print(f" variant : {len(rows)}")
print(f"proxy_agg : {proxy_agg_matches} / {len(rows)} ({proxy_agg_matches/len(rows)*100:.1f}%)")
print(f"score_diff : {score_diff_matches} / {len(rows)} ({score_diff_matches/len(rows)*100:.1f}%)")
print("=" * 120)













