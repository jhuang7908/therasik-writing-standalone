#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Variant Ranking Canonical Proxy 

 proxy_agg  score_diff 。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.germline_assets_loader import load_all_clean_germline_assets
from core.scoring.canonical_proxy import canonical_proxy_score_breakdown


def rank_variants(
    variants: List[Dict[str, Any]],
    selected_scaffold_germline_record: Dict[str, Any] = None,
    canonical_proxy_config: Dict[str, Any] = None,
) -> List[Dict[str, Any]]:
    """
    （ canonical_proxy ）
    """
    # 
    if canonical_proxy_config is None:
        canonical_proxy_config = {
            "enabled": True,
            "agg_mode": "min",
            "weight": 0.10,
        }
    
    enabled = canonical_proxy_config.get("enabled", True)
    agg_mode = canonical_proxy_config.get("agg_mode", "min")
    weight = canonical_proxy_config.get("weight", 0.10)
    
    #  germline assets（）
    germline_record = selected_scaffold_germline_record
    if enabled and not germline_record:
        scaffold_id = None
        for variant in variants:
            if variant.get("scaffold_id"):
                scaffold_id = variant.get("scaffold_id")
                break
        
        if scaffold_id:
            try:
                germline_assets = load_all_clean_germline_assets(include_canonical_proxy=True)
                #  scaffold_id  ID（ "HUMAN_VH3_SCF_10_SAFE_A" -> "HUMAN_VH3_SCF_10"）
                base_scaffold_id = scaffold_id.split("_SAFE_")[0] if "_SAFE_" in scaffold_id else scaffold_id
                #  germline record（）
                for asset in germline_assets:
                    seq_id = asset.get("sequence_id", "")
                    # 
                    if base_scaffold_id in seq_id:
                        germline_record = asset
                        break
            except Exception as e:
                print(f"  ⚠️  Warning:  canonical_proxy : {e}")
    
    #  variant  canonical_proxy 
    variants_with_proxy = []
    for variant in variants:
        if "score_components" not in variant:
            variant["score_components"] = {}
        if "score_components_detail" not in variant:
            variant["score_components_detail"] = {}
        
        proxy_agg = 0.0
        proxy_breakdown = {}
        if enabled and germline_record:
            try:
                proxy_breakdown = canonical_proxy_score_breakdown(
                    germline_record,
                    mode=agg_mode
                )
                proxy_agg = proxy_breakdown.get("proxy_agg", 0.0)
                variant["score_components"]["canonical_proxy"] = proxy_agg
                variant["score_components_detail"]["canonical_proxy"] = proxy_breakdown
            except Exception as e:
                print(f"  ⚠️  Warning:  canonical_proxy : {e}")
        
        s = variant.get("summary_scores", {})
        cmc_hot = s.get("cmc_hotspots", 999)
        immuno_max = s.get("immuno_max_score", 999.0)
        match_total = 0.0
        ms = variant.get("matching_scores")
        if ms:
            match_total = ms.get("total_score", 0.0)
        
        total_score_old = match_total
        
        if enabled:
            variant["total_score_old"] = total_score_old
            variant["total_score"] = total_score_old + weight * proxy_agg
            variant["total_score_new"] = variant["total_score"]
            variant["score_diff"] = variant["total_score"] - total_score_old
        else:
            variant["total_score_old"] = total_score_old
            variant["total_score"] = total_score_old
            variant["total_score_new"] = total_score_old
            variant["score_diff"] = 0.0
        
        variants_with_proxy.append(variant)
    
    # ：，
    def _key_old(v: Dict[str, Any]):
        s = v.get("summary_scores", {})
        cmc_hot = s.get("cmc_hotspots", 999)
        immuno_max = s.get("immuno_max_score", 999.0)
        match_total = 0.0
        ms = v.get("matching_scores")
        if ms:
            match_total = ms.get("total_score", 0.0)
        return (cmc_hot, immuno_max, -match_total)
    
    variants_sorted_old = sorted(variants_with_proxy, key=_key_old)
    for old_rank, v in enumerate(variants_sorted_old, 1):
        v["rank_old"] = old_rank
    
    # （ canonical_proxy）
    if enabled:
        def _key_new(v: Dict[str, Any]):
            s = v.get("summary_scores", {})
            cmc_hot = s.get("cmc_hotspots", 999)
            immuno_max = s.get("immuno_max_score", 999.0)
            total_score = v.get("total_score", 0.0)
            return (cmc_hot, immuno_max, -total_score)
        variants_sorted_new = sorted(variants_with_proxy, key=_key_new)
    else:
        variants_sorted_new = variants_sorted_old
    
    return variants_sorted_new


def validate_variant_ranking_debug(
    debug_csv_path: Path,
    weight: float = 0.10,
) -> Dict[str, Any]:
    """
     variant ranking debug 
    """
    with open(debug_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    proxy_agg_matches = 0
    score_diff_matches = 0
    total_rows = len(rows)
    
    for row in rows:
        proxy_cdr1 = float(row["proxy_cdr1"])
        proxy_cdr2 = float(row["proxy_cdr2"])
        proxy_agg = float(row["proxy_agg"])
        score_diff = float(row["score_diff"])
        total_score_old = float(row["total_score_old"])
        total_score_new = float(row["total_score_new"])
        
        #  proxy_agg = min(proxy_cdr1, proxy_cdr2)
        expected_proxy_agg = min(proxy_cdr1, proxy_cdr2) if proxy_cdr1 > 0 and proxy_cdr2 > 0 else 0.0
        proxy_agg_match = abs(proxy_agg - expected_proxy_agg) < 0.0001
        if proxy_agg_match:
            proxy_agg_matches += 1
        
        #  score_diff = weight * proxy_agg
        expected_score_diff = weight * proxy_agg
        actual_score_diff = total_score_new - total_score_old
        score_diff_match = abs(actual_score_diff - expected_score_diff) < 0.0001
        if score_diff_match:
            score_diff_matches += 1
    
    return {
        "total_rows": total_rows,
        "proxy_agg_matches": proxy_agg_matches,
        "score_diff_matches": score_diff_matches,
        "proxy_agg_pass_rate": proxy_agg_matches / total_rows if total_rows > 0 else 0.0,
        "score_diff_pass_rate": score_diff_matches / total_rows if total_rows > 0 else 0.0,
    }


def generate_variant_ranking_debug(
    variants: List[Dict[str, Any]],
    output_path: Path,
    print_table: bool = True,
) -> None:
    """
     variant ranking debug 
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
        print(f"{'Rank':<5} {'Variant ID':<25} {'Scaffold ID':<30} {'proxy_cdr1':<10} {'proxy_cdr2':<10} {'proxy_agg':<10} {'score_old':<10} {'score_new':<10} {'score_diff':<10} {'rank_old':<8} {'rank_new':<8} {'changed':<8}")
        print("-" * 120)
        
        for i, row in enumerate(debug_rows[:10], 1):
            print(
                f"{i:<5} {row['variant_id']:<25} {row['scaffold_id']:<30} "
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
    parser = argparse.ArgumentParser(description=" Variant Ranking Canonical Proxy ")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "projects" / "EGFR_7D12_VHH" / "vhh_variants.json",
        help=" variant JSON ",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output" / "variant_rank_with_canonical_proxy_debug.csv",
        help=" debug CSV ",
    )
    
    args = parser.parse_args()
    
    print("=" * 120)
    print(" Variant Ranking Canonical Proxy ")
    print("=" * 120)
    print()
    
    # 
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    variants = data.get("variants", [])
    print(f"[1] :")
    print(f"  Variant : {len(variants)}")
    print()
    
    # （ yaml ）
    config_path = PROJECT_ROOT / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = yaml.safe_load(f) or {}
    parameters_config = config_dict.get("parameters", {})
    variant_ranking_config = parameters_config.get("variant_ranking", {})
    canonical_proxy_config = variant_ranking_config.get("canonical_proxy", {})
    weight = float(canonical_proxy_config.get("weight", 0.10))
    agg_mode = canonical_proxy_config.get("agg_mode", "min")
    enabled = canonical_proxy_config.get("enabled", True)
    print(f"[2] :")
    print(f"  canonical_proxy.enabled: {enabled}")
    print(f"  canonical_proxy.weight: {weight}")
    print(f"  canonical_proxy.agg_mode: {agg_mode}")
    print()
    
    #  selected_scaffold  germline record
    selected_scaffold_germline_record = None
    scaffold_id = None
    for variant in variants:
        if variant.get("scaffold_id"):
            scaffold_id = variant.get("scaffold_id")
            break
    
    if scaffold_id:
        print(f"[3]  germline record (scaffold_id: {scaffold_id})...")
        try:
            germline_assets = load_all_clean_germline_assets(include_canonical_proxy=True)
            #  scaffold_id  ID（ "HUMAN_VH3_SCF_10_SAFE_A" -> "HUMAN_VH3_SCF_10"）
            base_scaffold_id = scaffold_id.split("_SAFE_")[0] if "_SAFE_" in scaffold_id else scaffold_id
            
            # ： stage1 ， scaffold  HUMAN_VH3_SCF_10
            #  germline record
            # ： "SCF_10"  germline
            for asset in germline_assets:
                seq_id = asset.get("sequence_id", "")
                # （）
                #  scaffold  member_ids  sequence_id  germline assets 
                if "SCF_10" in base_scaffold_id:
                    #  IGHV3-30  germline（HUMAN_VH3_SCF_10  IGHV3-30）
                    if "IGHV3-30" in seq_id:
                        selected_scaffold_germline_record = asset
                        print(f"  ✅  germline record: {seq_id[:60]}...")
                        break
        except Exception as e:
            print(f"  ⚠️  Warning:  germline assets: {e}")
    
    if not selected_scaffold_germline_record:
        print(f"  ⚠️  Warning:  germline record，canonical_proxy  0")
    print()
    
    #  variants（： ranking， CMC/immuno ）
    print(f"[4]  variants...")
    evaluated = []
    for i, variant in enumerate(variants, 1):
        variant_id = variant.get("variant_id", f"variant_{i}")
        print(f"  [{i}/{len(variants)}] {variant_id}")
        
        # ：
        evaluated_variant = variant.copy()
        evaluated_variant.setdefault("summary_scores", {})
        evaluated_variant.setdefault("matching_scores", {})
        evaluated.append(evaluated_variant)
    print()
    
    # Rank variants
    print(f"[5] Ranking variants（ canonical_proxy）...")
    ranked = rank_variants(
        evaluated,
        selected_scaffold_germline_record=selected_scaffold_germline_record,
        canonical_proxy_config=canonical_proxy_config,
    )
    print(f"  ✅ ， {len(ranked)}  variants")
    print()
    
    #  debug 
    print(f"[6]  debug ...")
    generate_variant_ranking_debug(ranked, args.output, print_table=True)
    print()
    
    # 
    print(f"[7] ...")
    validation_result = validate_variant_ranking_debug(args.output, weight=weight)
    print()
    print("=" * 120)
    print("")
    print("=" * 120)
    print(f" variant : {validation_result['total_rows']}")
    print(f"proxy_agg : {validation_result['proxy_agg_matches']} / {validation_result['total_rows']} ({validation_result['proxy_agg_pass_rate']*100:.1f}%)")
    print(f"score_diff : {validation_result['score_diff_matches']} / {validation_result['total_rows']} ({validation_result['score_diff_pass_rate']*100:.1f}%)")
    print()
    
    #  10 
    print("=" * 120)
    print("Debug  10 （）")
    print("=" * 120)
    print()
    with open(args.output, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f"{'Rank':<5} {'Variant ID':<25} {'Scaffold ID':<30} {'proxy_cdr1':<10} {'proxy_cdr2':<10} {'proxy_agg':<10} {'score_old':<10} {'score_new':<10} {'score_diff':<10} {'rank_old':<8} {'rank_new':<8} {'changed':<8}")
        print("-" * 120)
        for i, row in enumerate(rows[:10], 1):
            print(
                f"{i:<5} {row['variant_id']:<25} {row['scaffold_id']:<30} "
                f"{row['proxy_cdr1']:<10} {row['proxy_cdr2']:<10} {row['proxy_agg']:<10} "
                f"{row['total_score_old']:<10} {row['total_score_new']:<10} {row['score_diff']:<10} "
                f"{row['rank_old']:<8} {row['rank_new']:<8} {row['rank_changed']:<8}"
            )
    print()
    print("=" * 120)
    print("✅ ！")
    print("=" * 120)


if __name__ == "__main__":
    main()
