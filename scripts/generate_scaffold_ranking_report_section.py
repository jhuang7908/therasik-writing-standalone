#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Scaffold 

 canonical_proxy 。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def generate_scaffold_ranking_table(
    ranked_top10: List[Dict[str, Any]],
    canonical_proxy_config: Dict[str, Any],
) -> str:
    """
     scaffold （ canonical_proxy ）
    
    Args:
        ranked_top10:  top 10 
        canonical_proxy_config: canonical_proxy 
    
    Returns:
        Markdown 
    """
    lines = []
    lines.append("## Scaffold （ Canonical Proxy ）")
    lines.append("")
    lines.append("### ")
    lines.append("")
    agg_mode = canonical_proxy_config.get("agg_mode", "min")
    weight = canonical_proxy_config.get("weight", 0.10)
    lines.append(
        f"canonical_proxy  canonical ，"
        f" scaffold ；"
        f" agg={agg_mode}， {weight}。"
    )
    lines.append("")
    lines.append("### Top 10  Scaffold")
    lines.append("")
    lines.append("| Rank | Scaffold ID | Framework Identity | proxy_cdr1 | proxy_cdr2 | proxy_agg | canonical_proxy_weight | score_diff | total_score_old | total_score_new | rank_old | rank_new | rank_changed |")
    lines.append("|------|-------------|-------------------|------------|------------|-----------|----------------------|------------|-----------------|----------------|----------|----------|--------------|")
    
    for item in ranked_top10:
        rank = item.get("rank", 0)
        scaffold_id = item.get("scaffold_id", "")
        framework_identity = item.get("framework_identity", 0.0)
        
        canonical_proxy = item.get("canonical_proxy", {})
        proxy_cdr1 = canonical_proxy.get("proxy_cdr1", 0.0)
        proxy_cdr2 = canonical_proxy.get("proxy_cdr2", 0.0)
        proxy_agg = canonical_proxy.get("proxy_agg", 0.0)
        
        total_score_old = item.get("total_score_old", framework_identity)
        total_score_new = item.get("total_score", framework_identity)
        score_diff = total_score_new - total_score_old
        
        rank_old = item.get("rank_old", rank)
        rank_new = rank
        rank_changed = "✅" if rank_old != rank_new else "-"
        
        lines.append(
            f"| {rank} | {scaffold_id} | {framework_identity:.4f} | "
            f"{proxy_cdr1:.4f} | {proxy_cdr2:.4f} | {proxy_agg:.4f} | "
            f"{weight} | {score_diff:.4f} | {total_score_old:.4f} | "
            f"{total_score_new:.4f} | {rank_old} | {rank_new} | {rank_changed} |"
        )
    
    lines.append("")
    lines.append("### ")
    lines.append("")
    lines.append("- **proxy_agg**: CDR canonical  = min(proxy_cdr1, proxy_cdr2)（）")
    lines.append(f"- **canonical_proxy_weight**: {weight}（10% ）")
    lines.append("- **score_diff**: total_score_new - total_score_old = weight × proxy_agg")
    lines.append("- **rank_changed**: ✅ ")
    lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=" Scaffold ")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "output" / "result_stage12.json",
        help=" result_stage12.json ",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output" / "scaffold_ranking_report_section.md",
        help=" Markdown ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" Scaffold ")
    print("=" * 80)
    print()
    
    #  JSON
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    stage1 = data.get("stage1", {})
    ranked_top10 = stage1.get("ranked_top10", [])
    canonical_proxy_config = stage1.get("canonical_proxy_config", {
        "enabled": True,
        "agg_mode": "min",
        "weight": 0.10,
    })
    
    print(f":")
    print(f"  Top 10 : {len(ranked_top10)}")
    print(f"  Canonical Proxy : {canonical_proxy_config}")
    print()
    
    # 
    report_section = generate_scaffold_ranking_table(ranked_top10, canonical_proxy_config)
    
    # 
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report_section)
    
    print(f"✅ : {args.output}")
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()













