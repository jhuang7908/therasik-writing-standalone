#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Scaffold Ranking Debug （VHH ）

 stage1_select_scaffold  debug ，：
- framework_identity
- canonical_proxy 
- vhh_hallmark （）
- total_score
- 
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def generate_scaffold_ranking_debug(
    stage1_result: Dict[str, Any],
    output_path: Path,
    top_n: int = 10,
) -> None:
    """
     scaffold ranking debug 
    
    Args:
        stage1_result: stage1_select_scaffold 
        output_path:  CSV 
        top_n:  N 
    """
    ranked_top10 = stage1_result.get("stage1", {}).get("ranked_top10", [])
    
    if not ranked_top10:
        print("⚠️ : ranked_top10 ")
        return
    
    debug_rows = []
    
    for rank_info in ranked_top10:
        rank = rank_info.get("rank", 0)
        scaffold_id = rank_info.get("scaffold_id", "")
        framework_identity = rank_info.get("framework_identity", 0.0)
        
        #  canonical_proxy 
        canonical_proxy = rank_info.get("canonical_proxy", {})
        proxy_cdr1 = canonical_proxy.get("proxy_cdr1", 0.0)
        proxy_cdr2 = canonical_proxy.get("proxy_cdr2", 0.0)
        proxy_agg = canonical_proxy.get("proxy_agg", 0.0)
        
        #  VHH hallmark 
        vhh_hallmark = rank_info.get("vhh_hallmark")
        hallmark_score = vhh_hallmark.get("score", 0.0) if vhh_hallmark else None
        hallmark_label = vhh_hallmark.get("label", "") if vhh_hallmark else ""
        
        # 
        score_components = rank_info.get("score_components", {})
        total_score = rank_info.get("total_score", framework_identity)
        total_score_old = rank_info.get("total_score_old", framework_identity)
        rank_old = rank_info.get("rank_old", rank)
        
        # 
        rank_changed = "✅" if rank_old != rank else "-"
        score_diff = total_score - total_score_old
        
        debug_rows.append({
            "rank": rank,
            "rank_old": rank_old,
            "rank_changed": rank_changed,
            "scaffold_id": scaffold_id,
            "framework_identity": round(framework_identity, 4),
            "proxy_cdr1": round(proxy_cdr1, 4),
            "proxy_cdr2": round(proxy_cdr2, 4),
            "proxy_agg": round(proxy_agg, 4),
            "vhh_hallmark_score": round(hallmark_score, 4) if hallmark_score is not None else None,
            "vhh_hallmark_label": hallmark_label,
            "total_score_old": round(total_score_old, 4),
            "total_score": round(total_score, 4),
            "score_diff": round(score_diff, 4),
        })
    
    #  CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "rank", "rank_old", "rank_changed", "scaffold_id",
            "framework_identity",
            "proxy_cdr1", "proxy_cdr2", "proxy_agg",
            "vhh_hallmark_score", "vhh_hallmark_label",
            "total_score_old", "total_score", "score_diff",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(debug_rows)
    
    #  N 
    print("=" * 150)
    print(f"Scaffold Ranking Debug （ {min(top_n, len(debug_rows))} ）")
    print("=" * 150)
    print()
    
    # 
    header = (
        f"{'Rank':<5} {'Old':<5} {'Chg':<4} {'Scaffold ID':<30} "
        f"{'FR_ID':<8} {'proxy_cdr1':<10} {'proxy_cdr2':<10} {'proxy_agg':<10} "
        f"{'hallmark':<10} {'label':<12} {'score_old':<10} {'score_new':<10} {'diff':<10}"
    )
    print(header)
    print("-" * 150)
    
    # 
    for row in debug_rows[:top_n]:
        hallmark_score_str = f"{row['vhh_hallmark_score']:.4f}" if row['vhh_hallmark_score'] is not None else "N/A"
        hallmark_label_str = row['vhh_hallmark_label'] or "N/A"
        
        line = (
            f"{row['rank']:<5} {row['rank_old']:<5} {row['rank_changed']:<4} {row['scaffold_id']:<30} "
            f"{row['framework_identity']:<8.4f} {row['proxy_cdr1']:<10.4f} {row['proxy_cdr2']:<10.4f} {row['proxy_agg']:<10.4f} "
            f"{hallmark_score_str:<10} {hallmark_label_str:<12} {row['total_score_old']:<10.4f} {row['total_score']:<10.4f} {row['score_diff']:<10.4f}"
        )
        print(line)
    
    print()
    print("=" * 150)
    print(f"✅ : {output_path}")
    print(f" scaffold : {len(debug_rows)}")
    
    # 
    stage1_config = stage1_result.get("stage1", {})
    canonical_proxy_config = stage1_config.get("canonical_proxy_config", {})
    vhh_hallmark_config = stage1_config.get("vhh_hallmark_config", {})
    
    print()
    print(":")
    print(f"  Canonical Proxy: enabled={canonical_proxy_config.get('enabled', False)}, "
          f"weight={canonical_proxy_config.get('weight', 0.0)}, "
          f"agg_mode={canonical_proxy_config.get('agg_mode', 'min')}")
    print(f"  VHH Hallmark: enabled={vhh_hallmark_config.get('enabled', False)}, "
          f"weight={vhh_hallmark_config.get('weight', 0.0)}")
    print(f"  Germline DB: {stage1_config.get('germline_asset_version', 'unknown')}")
    print("=" * 150)


def main():
    parser = argparse.ArgumentParser(
        description=" Scaffold Ranking Debug （VHH ）"
    )
    parser.add_argument(
        "--input_json",
        type=Path,
        help=" stage1  JSON ",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output" / "scaffold_ranking_debug_vhh.csv",
        help=" CSV ",
    )
    parser.add_argument(
        "--top_n",
        type=int,
        default=10,
        help=" N （ 10）",
    )
    
    args = parser.parse_args()
    
    if args.input_json:
        #  JSON 
        if not args.input_json.exists():
            print(f"❌ : {args.input_json}")
            return
        
        with open(args.input_json, "r", encoding="utf-8") as f:
            stage1_result = json.load(f)
    else:
        # ，（）
        print("⚠️  JSON ，...")
        stage1_result = {
            "stage1": {
                "ranked_top10": [],
                "canonical_proxy_config": {
                    "enabled": True,
                    "weight": 0.10,
                    "agg_mode": "min",
                },
                "vhh_hallmark_config": {
                    "enabled": True,
                    "weight": 0.15,
                },
                "germline_asset_version": "vhh_v1",
            }
        }
        print("， ranked_top10 。")
        print(" --input_json  stage1 。")
        return
    
    generate_scaffold_ranking_debug(
        stage1_result,
        args.output,
        top_n=args.top_n,
    )


if __name__ == "__main__":
    main()










