#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Variant Ranking （MD  Excel）
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.report_blocks.canonical_proxy_background import (
    render_canonical_proxy_background_block,
    find_germline_record_by_scaffold_id,
)
from core.germline_assets_loader import load_all_clean_germline_assets

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("  ⚠️  Warning: pandas ， Excel ")


def generate_markdown_report(
    debug_csv_path: Path,
    weight: float = 0.10,
    output_md_path: Path = None,
) -> str:
    """
     Markdown 
    """
    with open(debug_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # 
    proxy_agg_matches = 0
    score_diff_matches = 0
    
    for row in rows:
        proxy_cdr1 = float(row["proxy_cdr1"])
        proxy_cdr2 = float(row["proxy_cdr2"])
        proxy_agg = float(row["proxy_agg"])
        score_diff = float(row["score_diff"])
        
        expected_agg = min(proxy_cdr1, proxy_cdr2) if proxy_cdr1 > 0 and proxy_cdr2 > 0 else 0.0
        if abs(proxy_agg - expected_agg) < 0.0001:
            proxy_agg_matches += 1
        
        expected_diff = weight * proxy_agg
        if abs(score_diff - expected_diff) < 0.0001:
            score_diff_matches += 1
    
    lines = []
    lines.append("# Variant Ranking Canonical Proxy ")
    lines.append("")
    lines.append(f"****: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"****: {weight}")
    lines.append("")
    
    lines.append("## ")
    lines.append("")
    lines.append(f"- ** variant **: {len(rows)}")
    lines.append(f"- **proxy_agg **: {proxy_agg_matches} / {len(rows)} ({proxy_agg_matches/len(rows)*100:.1f}%)")
    lines.append(f"- **score_diff **: {score_diff_matches} / {len(rows)} ({score_diff_matches/len(rows)*100:.1f}%)")
    lines.append("")
    
    lines.append("## ")
    lines.append("")
    lines.append("1. **proxy_agg **: `proxy_agg = min(proxy_cdr1, proxy_cdr2)`")
    lines.append(f"2. **score_diff **: `score_diff = weight × proxy_agg = {weight} × proxy_agg`")
    lines.append("")
    
    #  rank 1  scaffold_id
    rank1_scaffold_id = None
    if rows:
        rank1_row = rows[0]
        rank1_scaffold_id = rank1_row.get("scaffold_id", "")
    
    #  Canonical Proxy 
    canonical_proxy_data = None
    scaffold_library = None
    
    if rank1_scaffold_id:
        try:
            #  germline assets
            germline_assets = load_all_clean_germline_assets(include_canonical_proxy=True)
            
            #  scaffold （）
            scaffold_library_path = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds" / "human_vh3_scaffolds.json"
            if scaffold_library_path.exists():
                with open(scaffold_library_path, "r", encoding="utf-8") as f:
                    scaffold_library = json.load(f)
            
            #  germline record
            germline_record = find_germline_record_by_scaffold_id(
                rank1_scaffold_id,
                germline_assets,
                scaffold_library=scaffold_library,
            )
            
            if germline_record:
                canonical_proxy_data = germline_record
            else:
                print(f"  ⚠️  Warning:  scaffold_id '{rank1_scaffold_id}'  germline record")
        except Exception as e:
            print(f"  ⚠️  Warning:  canonical proxy : {e}")
    else:
        print(f"  ⚠️  Warning: rank 1 variant  scaffold_id， canonical proxy ")
    
    #  Canonical Proxy 
    canonical_proxy_block = render_canonical_proxy_background_block(
        canonical_proxy=canonical_proxy_data,
        agg_mode="min",  # ，
        weight=weight,
    )
    lines.append(canonical_proxy_block)
    
    #  scaffold，
    scaffold_ids = set(row.get("scaffold_id", "") for row in rows if row.get("scaffold_id"))
    if len(scaffold_ids) > 1:
        lines.append(f"* rank=1 scaffold  Canonical Proxy 。*")
        lines.append("")
    
    lines.append("## Debug （）")
    lines.append("")
    lines.append("| Rank | Variant ID | Scaffold ID | proxy_cdr1 | proxy_cdr2 | proxy_agg | total_score_old | total_score_new | score_diff | rank_old | rank_new | rank_changed |")
    lines.append("|------|------------|-------------|------------|------------|-----------|-----------------|-----------------|------------|----------|----------|-------------|")
    
    for i, row in enumerate(rows, 1):
        variant_id = row["variant_id"]
        scaffold_id = row["scaffold_id"] if row["scaffold_id"] else "-"
        proxy_cdr1 = row["proxy_cdr1"]
        proxy_cdr2 = row["proxy_cdr2"]
        proxy_agg = row["proxy_agg"]
        total_score_old = row["total_score_old"]
        total_score_new = row["total_score_new"]
        score_diff = row["score_diff"]
        rank_old = row["rank_old"]
        rank_new = row["rank_new"]
        rank_changed = row["rank_changed"]
        
        lines.append(
            f"| {i} | {variant_id} | {scaffold_id} | {proxy_cdr1} | {proxy_cdr2} | {proxy_agg} | "
            f"{total_score_old} | {total_score_new} | {score_diff} | {rank_old} | {rank_new} | {rank_changed} |"
        )
    
    lines.append("")
    lines.append("## （）")
    lines.append("")
    lines.append("| # | Variant ID | proxy_agg  | score_diff  |")
    lines.append("|---|------------|----------------|------------------|")
    
    for i, row in enumerate(rows, 1):
        variant_id = row["variant_id"]
        proxy_cdr1 = float(row["proxy_cdr1"])
        proxy_cdr2 = float(row["proxy_cdr2"])
        proxy_agg = float(row["proxy_agg"])
        score_diff = float(row["score_diff"])
        
        expected_agg = min(proxy_cdr1, proxy_cdr2) if proxy_cdr1 > 0 and proxy_cdr2 > 0 else 0.0
        agg_match = "✅" if abs(proxy_agg - expected_agg) < 0.0001 else "❌"
        
        expected_diff = weight * proxy_agg
        diff_match = "✅" if abs(score_diff - expected_diff) < 0.0001 else "❌"
        
        lines.append(f"| {i} | {variant_id} | {agg_match} (expected={expected_agg:.4f}) | {diff_match} (expected={expected_diff:.4f}) |")
    
    lines.append("")
    lines.append("## ")
    lines.append("")
    
    #  scaffold  variants
    scaffold_groups = {}
    for row in rows:
        scaffold_id = row["scaffold_id"]
        if scaffold_id:
            if scaffold_id not in scaffold_groups:
                scaffold_groups[scaffold_id] = []
            scaffold_groups[scaffold_id].append(row)
    
    if scaffold_groups:
        lines.append("###  Scaffold  Variants")
        lines.append("")
        for scaffold_id, group_rows in scaffold_groups.items():
            if len(group_rows) > 1:
                proxy_aggs = [float(r["proxy_agg"]) for r in group_rows]
                if len(set(proxy_aggs)) == 1:
                    lines.append(f"- **{scaffold_id}**: {len(group_rows)}  variants， `proxy_agg` （{proxy_aggs[0]:.4f}）✅")
                    lines.append("  - ：variants  FR， CDR1/2， canonical_proxy ")
                else:
                    lines.append(f"- **{scaffold_id}**: {len(group_rows)}  variants，`proxy_agg` （{set(proxy_aggs)}）")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("* `scripts/generate_variant_ranking_report.py` *")
    
    report_content = "\n".join(lines)
    
    if output_md_path:
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"✅ Markdown : {output_md_path}")
    
    return report_content


def generate_excel_report(
    debug_csv_path: Path,
    output_xlsx_path: Path,
) -> None:
    """
     Excel  debug 
    """
    if not PANDAS_AVAILABLE:
        print("  ⚠️  Warning: pandas ， Excel ")
        return
    
    df = pd.read_csv(debug_csv_path)
    
    # 
    weight = 0.10
    df["proxy_agg_expected"] = df.apply(
        lambda row: min(float(row["proxy_cdr1"]), float(row["proxy_cdr2"])) 
        if float(row["proxy_cdr1"]) > 0 and float(row["proxy_cdr2"]) > 0 else 0.0,
        axis=1
    )
    df["proxy_agg_match"] = (abs(df["proxy_agg"] - df["proxy_agg_expected"]) < 0.0001).map({True: "✅", False: "❌"})
    
    df["score_diff_expected"] = weight * df["proxy_agg"]
    df["score_diff_match"] = (abs(df["score_diff"] - df["score_diff_expected"]) < 0.0001).map({True: "✅", False: "❌"})
    
    #  Excel
    output_xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_xlsx_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Variant Ranking Debug', index=False)
    
    print(f"✅ Excel : {output_xlsx_path}")


def main():
    parser = argparse.ArgumentParser(description=" Variant Ranking （MD  Excel）")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "output" / "variant_rank_with_canonical_proxy_debug.csv",
        help=" debug CSV ",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PROJECT_ROOT / "output" / "variant_ranking_acceptance_report.md",
        help=" Markdown ",
    )
    parser.add_argument(
        "--output-xlsx",
        type=Path,
        default=PROJECT_ROOT / "output" / "variant_ranking_acceptance_report.xlsx",
        help=" Excel ",
    )
    parser.add_argument(
        "--weight",
        type=float,
        default=0.10,
        help="canonical_proxy ",
    )
    
    args = parser.parse_args()
    
    print("=" * 120)
    print(" Variant Ranking （MD  Excel）")
    print("=" * 120)
    print()
    
    #  Markdown 
    print("[1]  Markdown ...")
    generate_markdown_report(args.input, weight=args.weight, output_md_path=args.output_md)
    print()
    
    #  Excel 
    if PANDAS_AVAILABLE:
        print("[2]  Excel ...")
        generate_excel_report(args.input, args.output_xlsx)
        print()
    else:
        print("[2]  Excel （pandas ）")
        print()
    
    print("=" * 120)
    print("✅ ！")
    print("=" * 120)


if __name__ == "__main__":
    main()

