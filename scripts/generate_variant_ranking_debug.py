#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Variant Ranking Debug 

 canonical_proxy 。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def generate_variant_ranking_debug(
    variants: List[Dict[str, Any]],
    output_path: Path,
) -> None:
    """
     variant ranking debug 
    
    Args:
        variants:  variant 
        output_path:  CSV 
    """
    debug_rows = []
    
    for i, variant in enumerate(variants, 1):
        variant_id = variant.get("variant_id", f"variant_{i}")
        scaffold_id = variant.get("scaffold_id", "")
        
        #  canonical_proxy 
        score_components_detail = variant.get("score_components_detail", {})
        canonical_proxy_detail = score_components_detail.get("canonical_proxy", {})
        proxy_cdr1 = canonical_proxy_detail.get("proxy_cdr1", 0.0)
        proxy_cdr2 = canonical_proxy_detail.get("proxy_cdr2", 0.0)
        proxy_agg = canonical_proxy_detail.get("proxy_agg", 0.0)
        
        # 
        total_score_old = variant.get("total_score_old", 0.0)
        total_score_new = variant.get("total_score_new", total_score_old)
        score_diff = variant.get("score_diff", 0.0)
        
        # 
        rank_old = variant.get("rank_old", i)
        rank_new = i
        rank_changed = "✅" if rank_old != rank_new else "-"
        
        debug_rows.append({
            "variant_id": variant_id,
            "scaffold_id": scaffold_id if scaffold_id else "",
            "proxy_cdr1": round(proxy_cdr1, 4),
            "proxy_cdr2": round(proxy_cdr2, 4),
            "proxy_agg": round(proxy_agg, 4),
            "total_score_old": round(total_score_old, 4),
            "total_score_new": round(total_score_new, 4),
            "score_diff": round(score_diff, 4),
            "rank_old": rank_old,
            "rank_new": rank_new,
            "rank_changed": rank_changed,
        })
    
    #  CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "variant_id", "scaffold_id", "proxy_cdr1", "proxy_cdr2", "proxy_agg",
            "total_score_old", "total_score_new", "score_diff",
            "rank_old", "rank_new", "rank_changed"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(debug_rows)
    
    #  10 （）
    if print_table:
        print("=" * 120)
        print("Variant Ranking Debug （ 10 ）")
        print("=" * 120)
        print()
        print(f"{'Rank':<5} {'Variant ID':<25} {'Scaffold ID':<25} {'proxy_cdr1':<10} {'proxy_cdr2':<10} {'proxy_agg':<10} {'score_old':<10} {'score_new':<10} {'score_diff':<10} {'rank_old':<8} {'rank_new':<8} {'changed':<8}")
        print("-" * 120)
        
        for i, row in enumerate(debug_rows[:10], 1):
            print(
                f"{i:<5} {row['variant_id']:<25} {row['scaffold_id']:<25} "
                f"{row['proxy_cdr1']:<10.4f} {row['proxy_cdr2']:<10.4f} {row['proxy_agg']:<10.4f} "
                f"{row['total_score_old']:<10.4f} {row['total_score_new']:<10.4f} {row['score_diff']:<10.4f} "
                f"{row['rank_old']:<8} {row['rank_new']:<8} {row['rank_changed']:<8}"
            )
        
        print()
        print("=" * 120)
        print(f"✅ : {output_path}")
        print(f" variant : {len(debug_rows)}")
        print("=" * 120)


def main():
    parser = argparse.ArgumentParser(description=" Variant Ranking Debug ")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "result_vhh_mvp.json",
        help=" result_vhh_mvp.json ",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output" / "variant_rank_with_canonical_proxy_debug.csv",
        help=" debug CSV ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" Variant Ranking Debug ")
    print("=" * 80)
    print()
    
    #  JSON
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    variants = data.get("variants", [])
    print(f":")
    print(f"  Variant : {len(variants)}")
    print()
    
    #  debug 
    generate_variant_ranking_debug(variants, args.output)


if __name__ == "__main__":
    main()

