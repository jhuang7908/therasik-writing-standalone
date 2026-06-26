#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Canonical Proxy 

 scaffold  debug ，。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.stage12_germline_selection import stage1_select_scaffold, read_fasta
from core.scoring.canonical_proxy import canonical_proxy_agg, canonical_proxy_score_breakdown


def main():
    parser = argparse.ArgumentParser(description=" Canonical Proxy ")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help=" FASTA ",
    )
    parser.add_argument(
        "--scaffold",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds" / "human_vh3_scaffolds.json",
        help="Scaffold ",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output" / "canonical_proxy_scoring_debug.csv",
        help=" debug CSV ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" Canonical Proxy ")
    print("=" * 80)
    print()
    
    # 
    print("[1] ...")
    sequence_id, sequence = read_fasta(args.input)
    print(f"  ✅ ID: {sequence_id}")
    print(f"  ✅ : {len(sequence)} aa")
    print()
    
    # Stage 1: Scaffold （ canonical_proxy ）
    print("[2] Stage 1: Scaffold （ canonical_proxy ）...")
    stage1_result = stage1_select_scaffold(
        query_seq=sequence,
        scaffold_library_path=str(args.scaffold),
        scheme="imgt",
        method="anarcii",
        mask_regions=("CDR1", "CDR2", "CDR3"),
        min_vh_len=75,
        top_k=10,
    )
    
    ranked_top10 = stage1_result["stage1"]["ranked_top10"]
    print(f"  ✅ Top 10 : {len(ranked_top10)}")
    print()
    
    #  debug 
    print("[3]  debug ...")
    debug_rows = []
    
    for item in ranked_top10:
        scaffold_id = item["scaffold_id"]
        framework_identity = item["framework_identity"]
        total_score_old = item.get("total_score_old", framework_identity)
        total_score_new = item.get("total_score", framework_identity)
        rank_old = item.get("rank_old", item["rank"])
        rank_new = item["rank"]
        
        #  canonical_proxy 
        canonical_proxy_info = item.get("canonical_proxy", {})
        proxy_cdr1 = canonical_proxy_info.get("proxy_cdr1", 0.0)
        proxy_cdr2 = canonical_proxy_info.get("proxy_cdr2", 0.0)
        proxy_agg = canonical_proxy_info.get("proxy_agg", 0.0)
        
        #  proxy_agg = min(proxy_cdr1, proxy_cdr2)
        expected_proxy_agg = min(proxy_cdr1, proxy_cdr2) if proxy_cdr1 > 0 and proxy_cdr2 > 0 else 0.0
        proxy_agg_match = abs(proxy_agg - expected_proxy_agg) < 0.0001
        
        #  total_score_new - total_score_old = 0.10 * proxy_agg
        expected_score_diff = 0.10 * proxy_agg
        actual_score_diff = total_score_new - total_score_old
        score_diff_match = abs(actual_score_diff - expected_score_diff) < 0.0001
        
        debug_rows.append({
            "sequence_id": scaffold_id,  #  scaffold_id 
            "proxy_cdr1": round(proxy_cdr1, 4),
            "proxy_cdr2": round(proxy_cdr2, 4),
            "proxy_agg": round(proxy_agg, 4),
            "proxy_agg_expected": round(expected_proxy_agg, 4),
            "proxy_agg_match": "✅" if proxy_agg_match else "❌",
            "total_score_old": round(total_score_old, 4),
            "total_score_new": round(total_score_new, 4),
            "score_diff": round(actual_score_diff, 4),
            "score_diff_expected": round(expected_score_diff, 4),
            "score_diff_match": "✅" if score_diff_match else "❌",
            "rank_old": rank_old,
            "rank_new": rank_new,
            "rank_changed": "✅" if rank_old != rank_new else "-",
        })
    
    #  CSV
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "sequence_id", "proxy_cdr1", "proxy_cdr2", "proxy_agg", "proxy_agg_expected",
            "proxy_agg_match", "total_score_old", "total_score_new", "score_diff",
            "score_diff_expected", "score_diff_match", "rank_old", "rank_new", "rank_changed"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(debug_rows)
    
    print(f"  ✅ : {args.output}")
    print()
    
    # 
    proxy_agg_matches = sum(1 for row in debug_rows if row["proxy_agg_match"] == "✅")
    score_diff_matches = sum(1 for row in debug_rows if row["score_diff_match"] == "✅")
    rank_changes = sum(1 for row in debug_rows if row["rank_changed"] == "✅")
    
    print("=" * 80)
    print("")
    print("=" * 80)
    print(f": {len(debug_rows)}")
    print(f"proxy_agg : {proxy_agg_matches} / {len(debug_rows)}")
    print(f"score_diff : {score_diff_matches} / {len(debug_rows)}")
    print(f": {rank_changes} / {len(debug_rows)}")
    print()
    
    #  5 
    print(" 5 :")
    for i, row in enumerate(debug_rows[:5], 1):
        print(f"  {i}. {row['sequence_id']}")
        print(f"     proxy_cdr1={row['proxy_cdr1']}, proxy_cdr2={row['proxy_cdr2']}, proxy_agg={row['proxy_agg']}")
        print(f"     total_score: {row['total_score_old']} -> {row['total_score_new']} (diff={row['score_diff']})")
        print(f"     rank: {row['rank_old']} -> {row['rank_new']}")
        print(f"     : proxy_agg={row['proxy_agg_match']}, score_diff={row['score_diff_match']}")
        print()
    
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()













