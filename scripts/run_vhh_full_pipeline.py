#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
run_vhh_full_pipeline.py

 Step1  result_vhh_scaffold_match.json，
 variant ：
  - CMC developability 
  - 
 result_vhh_mvp.json，。
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import CMC/Developability analysis
from core.vhh_developability import analyze_developability

# Import Immunogenicity analysis
try:
    from scripts.v3_immunogenicity import analyze_immunogenicity_offline, analyze_immunogenicity_iedb, CORE15_HLA_ALLELES
    from scripts.iedb_client import IEDBError
    IEDB_AVAILABLE = True
except ImportError:
    IEDB_AVAILABLE = False
    print("[WARN] IEDB client not available. Will use offline immunogenicity analysis only.")


def analyze_immunogenicity(sequence: str, use_iedb: bool = False, alleles: List[str] = None) -> Dict[str, Any]:
    """
    
    
    Args:
        sequence: 
        use_iedb:  IEDB API（）
        alleles: HLA （ None， CORE15）
    
    Returns:
        
    """
    if use_iedb and IEDB_AVAILABLE:
        if alleles is None:
            alleles = CORE15_HLA_ALLELES
        try:
            return analyze_immunogenicity_iedb(sequence, alleles)
        except (IEDBError, Exception) as e:
            print(f"[WARN] IEDB analysis failed for sequence (len={len(sequence)}): {e}")
            print(f"[INFO] Falling back to offline analysis")
            return analyze_immunogenicity_offline(sequence)
    else:
        return analyze_immunogenicity_offline(sequence)


def evaluate_variant(variant: Dict[str, Any], use_iedb: bool = False, alleles: List[str] = None) -> Dict[str, Any]:
    """
     variant 
    
    Args:
        variant: variant ， 'sequence' 
        use_iedb:  IEDB API 
        alleles: HLA 
    
    Returns:
         CMC  variant 
    """
    seq = variant.get("sequence", "")
    if not seq:
        print(f"[WARN] Variant {variant.get('variant_id', 'unknown')} has no sequence, skipping")
        return variant
    
    print(f"[INFO] Evaluating variant: {variant.get('variant_id', 'unknown')} (len={len(seq)})")
    
    # 1) CMC / developability
    try:
        cmc_res = analyze_developability(seq)
        print(f"  [CMC] Score: {cmc_res.get('score', 0.0):.3f}, Liabilities: {len(cmc_res.get('liabilities', []))}")
    except Exception as e:
        print(f"  [WARN] CMC analysis failed: {e}")
        cmc_res = {
            'score': 0.0,
            'liabilities': [],
            'fr2_risk': 1.0,
            'fr3_risk': 1.0,
            'cmc_summary': {'risk_level': 'unknown', 'total_flags': 0},
            'notes': f'CMC analysis failed: {e}',
        }
    
    # 2) 
    try:
        immuno_res = analyze_immunogenicity(seq, use_iedb=use_iedb, alleles=alleles)
        method = immuno_res.get('method', 'unknown')
        risk_level = immuno_res.get('risk_level', 'unknown')
        print(f"  [Immuno] Method: {method}, Risk: {risk_level}")
    except Exception as e:
        print(f"  [WARN] Immunogenicity analysis failed: {e}")
        immuno_res = {
            'method': 'error',
            'risk_level': 'unknown',
            'non_human_aa_count': 0,
            'non_human_aa_ratio': 0.0,
            'tcell_epitopes': [],
            'hla_binding_predictions': [],
        }
    
    # 3)  summary，
    #  CMC 
    cmc_hotspots = len(cmc_res.get("liabilities", []))
    cmc_severity = 0.0
    if cmc_res.get("liabilities"):
        # 
        risk_map = {"high": 1.0, "medium": 0.5, "low": 0.2}
        max_risk_val = max(
            risk_map.get(liab.get("risk", "low"), 0.2)
            for liab in cmc_res.get("liabilities", [])
        )
        cmc_severity = max_risk_val
    
    # 
    immuno_max = 0.0
    immuno_high_windows = 0
    
    #  IEDB 
    if immuno_res.get("method") == "iedb_online":
        strong_binders = immuno_res.get("strong_binders", 0)
        if isinstance(strong_binders, int):
            immuno_high_windows = strong_binders
        elif isinstance(strong_binders, list):
            immuno_high_windows = len(strong_binders)
        #  strong_binders  max_score 
        immuno_max = min(1.0, immuno_high_windows / 10.0)  #  0-1
    # 
    elif immuno_res.get("method") == "offline_heuristic":
        non_human_ratio = immuno_res.get("non_human_aa_ratio", 0.0)
        immuno_max = min(1.0, non_human_ratio * 5.0)  #  0-1
        risk_level = immuno_res.get("risk_level", "low")
        if risk_level == "high":
            immuno_high_windows = 3
        elif risk_level == "medium":
            immuno_high_windows = 1
    
    summary = {
        "cmc_hotspots": cmc_hotspots,
        "cmc_max_severity": cmc_severity,
        "cmc_score": cmc_res.get("score", 0.0),  #  CMC score
        "immuno_max_score": immuno_max,
        "immuno_high_windows": immuno_high_windows,
        "immuno_risk_level": immuno_res.get("risk_level", "unknown"),
    }
    
    # 
    out = dict(variant)
    out["cmc_result"] = cmc_res
    out["immunogenicity_result"] = immuno_res
    out["summary_scores"] = summary
    return out


def rank_variants(
    variants: List[Dict[str, Any]],
    selected_scaffold_germline_record: Dict[str, Any] = None,
) -> List[Dict[str, Any]]:
    """
    （ canonical_proxy ）：
      1）CMC hotspot 
      2） max_score 
      3）matching total_score 
      4）canonical_proxy （）
    """
    from core.config import get_config
    from core.scoring.canonical_proxy import canonical_proxy_score_breakdown
    from core.germline_assets_loader import load_all_clean_germline_assets
    
    #  canonical_proxy 
    cfg = get_config()
    variant_ranking_config = cfg.parameters.variant_ranking or {}
    canonical_proxy_config = variant_ranking_config.get("canonical_proxy", {})
    enabled = canonical_proxy_config.get("enabled", True)
    agg_mode = canonical_proxy_config.get("agg_mode", "min")
    weight = canonical_proxy_config.get("weight", 0.10)
    
    #  germline assets（）
    germline_record = selected_scaffold_germline_record
    if enabled and not germline_record:
        #  variant  scaffold_id  germline record
        scaffold_id = None
        for variant in variants:
            if variant.get("scaffold_id"):
                scaffold_id = variant.get("scaffold_id")
                break
        
        if scaffold_id:
            #  scaffold_id  germline （ stage1 ）
            try:
                germline_assets = load_all_clean_germline_assets(include_canonical_proxy=True)
                # ： variant  scaffold_id  germline
                #  stage1  selected_scaffold  germline
                # 
                for asset in germline_assets:
                    # （ scaffold_id ）
                    if scaffold_id and asset.get("sequence_id", "").startswith(scaffold_id.split("_")[-1] if "_" in scaffold_id else ""):
                        germline_record = asset
                        break
            except Exception as e:
                print(f"  ⚠️  Warning:  canonical_proxy : {e}")
    
    #  variant  canonical_proxy 
    variants_with_proxy = []
    for variant in variants:
        #  score_components
        if "score_components" not in variant:
            variant["score_components"] = {}
        if "score_components_detail" not in variant:
            variant["score_components_detail"] = {}
        
        #  canonical_proxy（ germline record）
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
        
        # （）
        s = variant.get("summary_scores", {})
        cmc_hot = s.get("cmc_hotspots", 999)
        immuno_max = s.get("immuno_max_score", 999.0)
        match_total = 0.0
        ms = variant.get("matching_scores")
        if ms:
            match_total = ms.get("total_score", 0.0)
        
        #  total_score_old（）
        # ： match_total 
        total_score_old = match_total
        
        #  canonical_proxy 
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


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Run full VHH pipeline on all variants.")
    parser.add_argument(
        "--input",
        default="result_vhh_scaffold_match.json",
        help="Input JSON from scaffold matching step",
    )
    parser.add_argument(
        "--output",
        default="result_vhh_mvp.json",
        help="Output JSON with CMC + immunogenicity evaluation",
    )
    parser.add_argument(
        "--use-iedb",
        action="store_true",
        help="Use IEDB API for immunogenicity analysis (requires network connection)",
    )
    parser.add_argument(
        "--alleles",
        nargs="+",
        help="Custom HLA alleles list (e.g., --alleles HLA-DRB1*01:01 HLA-DRB1*03:01)",
    )
    args = parser.parse_args()
    
    # Load input JSON
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Error: Input file not found: {input_path}")
    
    print(f"[INFO] Loading input from: {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        base = json.load(f)
    
    variants = base.get("variants", [])
    if not variants:
        raise SystemExit("Error: No variants found in input JSON.")
    
    print(f"[INFO] Found {len(variants)} variants to evaluate")
    
    # Evaluate each variant
    evaluated = []
    for i, variant in enumerate(variants, 1):
        print(f"\n[{i}/{len(variants)}] Processing variant: {variant.get('variant_id', 'unknown')}")
        evaluated_variant = evaluate_variant(
            variant,
            use_iedb=args.use_iedb,
            alleles=args.alleles
        )
        evaluated.append(evaluated_variant)
    
    # Rank variants
    print("\n[INFO] Ranking variants...")
    #  base  selected_scaffold  germline record
    selected_scaffold_germline_record = None
    #  stage1  selected_scaffold  germline record（）
    matching_result = base.get("matching_result", {})
    if matching_result.get("success"):
        best_match = matching_result.get("best_match", {})
        scaffold_id = best_match.get("id", "")
        if scaffold_id:
            #  germline assets 
            try:
                from core.germline_assets_loader import load_all_clean_germline_assets
                germline_assets = load_all_clean_germline_assets(include_canonical_proxy=True)
                # （ scaffold_id ）
                for asset in germline_assets:
                    seq_id = asset.get("sequence_id", "")
                    # （）
                    if scaffold_id in seq_id or seq_id.startswith(scaffold_id.split("_")[-1] if "_" in scaffold_id else ""):
                        selected_scaffold_germline_record = asset
                        break
            except Exception as e:
                print(f"  ⚠️  Warning:  germline assets: {e}")
    
    ranked = rank_variants(evaluated, selected_scaffold_germline_record=selected_scaffold_germline_record)
    
    #  1 /  2（）
    recommended = []
    if ranked:
        recommended.append(ranked[0])
    if len(ranked) > 1:
        recommended.append(ranked[1])
    
    # Build output structure
    out = {
        "input_sequence": base.get("input_sequence", ""),
        "input_length": base.get("input_length", 0),
        "matching_result": base.get("matching_result", {}),
        "variants": ranked,
        "recommended_variants": [v["variant_id"] for v in recommended],
        "analysis_summary": {
            "total_variants": len(ranked),
            "recommended_count": len(recommended),
            "immunogenicity_method": "iedb_online" if args.use_iedb and IEDB_AVAILABLE else "offline_heuristic",
        }
    }
    
    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    
    print(f"\n[INFO] Evaluated {len(variants)} variants, wrote {output_path}")
    print(f"[INFO] Recommended variants: {out['recommended_variants']}")
    
    #  variant ranking debug 
    try:
        from scripts.generate_variant_ranking_debug import generate_variant_ranking_debug
        debug_path = output_path.parent / "variant_rank_with_canonical_proxy_debug.csv"
        generate_variant_ranking_debug(ranked, debug_path)
        print(f"[INFO] Variant ranking debug table saved: {debug_path}")
    except Exception as e:
        print(f"[WARN] Failed to generate variant ranking debug table: {e}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("Evaluation Summary")
    print("=" * 60)
    for i, v in enumerate(ranked[:5], 1):  # 5
        s = v.get("summary_scores", {})
        print(f"\n{i}. {v.get('variant_id', 'unknown')}")
        print(f"   CMC hotspots: {s.get('cmc_hotspots', 0)}, Score: {s.get('cmc_score', 0.0):.3f}")
        print(f"   Immuno risk: {s.get('immuno_risk_level', 'unknown')}, Max score: {s.get('immuno_max_score', 0.0):.3f}")
        if v.get("matching_scores"):
            print(f"   Matching score: {v['matching_scores'].get('total_score', 0.0):.3f}")


if __name__ == "__main__":
    main()




