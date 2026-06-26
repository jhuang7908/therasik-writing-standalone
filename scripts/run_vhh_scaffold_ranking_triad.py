#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VHH Scaffold Ranking Triad

 stage1_select_scaffold，：
1. VHH scaffold library (264)
2. Human VH3 scaffold library
3. VHH special FR templates (82，scaffold)

：
- output/vhh_triad_ranking_debug.csv
- output/vhh_triad_ranking_summary.md
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# EGFR VHH 
EGFR_VHH_SEQ = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"


def convert_fr_template_to_scaffold(template: Dict[str, Any]) -> Dict[str, Any]:
    """
     FR-only  scaffold 
    
    Args:
        template: FR（fr_id, segments, fr_sequence）
    
    Returns:
        scaffold 
    """
    segments = template.get("segments", {})
    fr1 = segments.get("FR1", "")
    fr2 = segments.get("FR2", "")
    fr3 = segments.get("FR3", "")
    fr4 = ""  # VHHFR4
    
    framework_full = fr1 + fr2 + fr3 + fr4
    
    scaffold = {
        "scaffold_id": template.get("fr_id", "UNKNOWN"),
        "n_members": 1,
        "member_ids": [template.get("source_sequence_id", "")],
        "consensus": {
            "fr1": fr1,
            "fr2": fr2,
            "fr3": fr3,
            "fr4": fr4,
            "framework_full": framework_full,
        },
        # VHH
        "vhh_hallmark": template.get("vhh_hallmark"),
        "canonical_proxy_cdr1": template.get("canonical_proxy", {}).get("cdr1"),
        "canonical_proxy_cdr2": template.get("canonical_proxy", {}).get("cdr2"),
        # 
        "source_library": "special_fr_templates",
        "template_type": template.get("template_type", "vhh_special_fr"),
    }
    
    return scaffold


def load_fr_templates_as_scaffolds(templates_path: Path) -> List[Dict[str, Any]]:
    """
    FRscaffold
    
    Args:
        templates_path: FRJSONL
    
    Returns:
        scaffold
    """
    scaffolds = []
    with open(templates_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                template = json.loads(line)
                scaffold = convert_fr_template_to_scaffold(template)
                scaffolds.append(scaffold)
    
    return scaffolds


def run_case(
    case_name: str,
    query_seq: str,
    scaffold_library_path: Path | None = None,
    scaffold_library_list: List[Dict[str, Any]] | None = None,
    germline_db: str = "v1_clean",
    vhh_hallmark_weight: float = 0.15,
    top_k: int = 20,
) -> Dict[str, Any]:
    """
    casescaffold ranking
    
    Args:
        case_name: case（）
        query_seq: 
        scaffold_library_path: scaffold（）
        scaffold_library_list: scaffold（，）
        germline_db: germline
        vhh_hallmark_weight: VHH hallmark
        top_k: top K
    
    Returns:
        ranking
    """
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.stage12_germline_selection import stage1_select_scaffold
    
    # scaffold_library_list，
    if scaffold_library_list is not None:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            for scaffold in scaffold_library_list:
                f.write(json.dumps(scaffold, ensure_ascii=False) + "\n")
            temp_path = Path(f.name)
        
        try:
            result = stage1_select_scaffold(
                query_seq=query_seq,
                scaffold_library_path=str(temp_path),
                germline_db=germline_db,
                vhh_hallmark_weight=vhh_hallmark_weight,
                top_k=top_k,
            )
        finally:
            # 
            if temp_path.exists():
                temp_path.unlink()
    else:
        result = stage1_select_scaffold(
            query_seq=query_seq,
            scaffold_library_path=str(scaffold_library_path) if scaffold_library_path else None,
            germline_db=germline_db,
            vhh_hallmark_weight=vhh_hallmark_weight,
            top_k=top_k,
        )
    
    # case
    result["case_name"] = case_name
    return result


def calculate_scores(
    framework_identity: float,
    canonical_proxy_agg: float,
    vhh_hallmark_score: float | None,
) -> tuple[int, float, float, str]:
    """
    fixednorm
    
    Args:
        framework_identity: Framework identity
        canonical_proxy_agg: Canonical proxy
        vhh_hallmark_score: VHH hallmark（None）
    
    Returns:
        (hallmark_available, total_score_fixed, total_score_norm, score_mode_used)
    """
    # 
    w_id = 0.75
    w_proxy = 0.10
    w_hallmark = 0.15
    
    # hallmark
    hallmark_available = 1 if vhh_hallmark_score is not None else 0
    hallmark_score = vhh_hallmark_score if vhh_hallmark_score is not None else 0.0
    
    # Fixed：hallmark0
    total_score_fixed = (
        framework_identity * w_id +
        canonical_proxy_agg * w_proxy +
        hallmark_score * w_hallmark
    )
    
    # Norm：hallmark，
    if hallmark_available == 0:
        # ：idproxy
        w_id_norm = w_id / (w_id + w_proxy)
        w_proxy_norm = w_proxy / (w_id + w_proxy)
        total_score_norm = (
            framework_identity * w_id_norm +
            canonical_proxy_agg * w_proxy_norm
        )
        score_mode_used = "norm"
    else:
        # hallmark，norm = fixed
        total_score_norm = total_score_fixed
        score_mode_used = "fixed"
    
    return (hallmark_available, total_score_fixed, total_score_norm, score_mode_used)


def extract_ranking_data(result: Dict[str, Any], source_library: str) -> List[Dict[str, Any]]:
    """
    stage1ranking
    
    Args:
        result: stage1_select_scaffold
        source_library: 
    
    Returns:
        ranking
    """
    ranking_data = []
    # ranked_top10stage1
    ranked = result.get("stage1", {}).get("ranked_top10", [])
    
    for idx, candidate in enumerate(ranked, 1):
        scaffold_id = candidate.get("scaffold_id", "")
        framework_identity = candidate.get("framework_identity", 0.0)
        canonical_proxy = candidate.get("canonical_proxy", {})
        # Case B  proxy_agg  None，
        canonical_proxy_agg = canonical_proxy.get("proxy_agg", None) if isinstance(canonical_proxy, dict) else None
        vhh_hallmark = candidate.get("vhh_hallmark", {})
        vhh_hallmark_score = vhh_hallmark.get("score", None) if isinstance(vhh_hallmark, dict) and vhh_hallmark else None
        
        # fixednorm（proxy_agg  None  0.0）
        proxy_agg_value = canonical_proxy_agg if canonical_proxy_agg is not None else 0.0
        hallmark_available, total_score_fixed, total_score_norm, score_mode_used = calculate_scores(
            framework_identity,
            proxy_agg_value,
            vhh_hallmark_score,
        )
        
        # 
        notes = ""
        if source_library == "special_fr_templates":
            notes = "FR-only converted to scaffold"
        
        ranking_data.append({
            "source_library": source_library,
            "rank": idx,
            "scaffold_id": scaffold_id,
            "framework_identity": round(framework_identity, 4),
            "proxy_agg": round(canonical_proxy_agg, 4) if canonical_proxy_agg is not None else "",
            "vhh_hallmark_score": round(vhh_hallmark_score, 4) if vhh_hallmark_score is not None else "",
            "total_score": round(candidate.get("total_score", 0.0), 4),  # total_score
            "hallmark_available": hallmark_available,
            "total_score_fixed": round(total_score_fixed, 4),
            "total_score_norm": round(total_score_norm, 4),
            "score_mode_used": score_mode_used,
            "notes": notes,
        })
    
    return ranking_data


def main():
    parser = argparse.ArgumentParser(
        description="VHH Scaffold Ranking Triad"
    )
    parser.add_argument(
        "--query_fasta",
        type=Path,
        default=None,
        help="FASTA（，EGFR VHH）",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="",
    )
    parser.add_argument(
        "--top_k",
        type=int,
        default=20,
        help="top K",
    )
    
    args = parser.parse_args()
    
    # 
    if args.query_fasta and args.query_fasta.exists():
        with open(args.query_fasta, "r", encoding="utf-8") as f:
            query_seq = "".join([line.strip() for line in f if not line.startswith(">")])
    else:
        query_seq = EGFR_VHH_SEQ
        print(f"EGFR VHH（: {len(query_seq)} aa）")
    
    print("=" * 80)
    print("VHH Scaffold Ranking Triad")
    print("=" * 80)
    print()
    print(f": {query_seq[:50]}...")
    print(f": {len(query_seq)} aa")
    print()
    
    # 
    vhh_scaffold_library = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_scaffold_library_v1.jsonl"
    human_vh3_scaffolds = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds" / "human_vh3_scaffolds.json"
    vhh_fr_templates = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_special_fr_templates_v1.jsonl"
    
    # case
    all_ranking_data = []
    case_results = {}
    
    # Case A: VHH scaffold library (264)
    # Case A  VHH （）
    print("[Case A] VHH scaffold library (264)...")
    if vhh_scaffold_library.exists():
        try:
            result_a = run_case(
                case_name="Case A",
                query_seq=query_seq,
                scaffold_library_path=vhh_scaffold_library,
                germline_db="vhh_v1",
                vhh_hallmark_weight=0.15,
                top_k=args.top_k,
            )
            case_results["Case A"] = result_a
            ranking_data_a = extract_ranking_data(result_a, "vhh_scaffold_library")
            
            # Case A ： topK，，
            if len(ranking_data_a) < args.top_k:
                print(f"  ⚠️ :  {len(ranking_data_a)} （: {args.top_k}），")
            
            all_ranking_data.extend(ranking_data_a)
            print(f"  ✅ : {len(ranking_data_a)} ")
        except Exception as e:
            print(f"  ❌ : {e}")
            case_results["Case A"] = {"error": str(e), "ranked": []}
    else:
        print(f"  ❌ : {vhh_scaffold_library}")
        case_results["Case A"] = {"error": "", "ranked": []}
    print()
    
    # Case B: Human VH3 scaffold library
    # Case B  hallmark ， framework_identity  proxy_agg
    print("[Case B] Human VH3 scaffold library...")
    if human_vh3_scaffolds.exists():
        try:
            result_b = run_case(
                case_name="Case B",
                query_seq=query_seq,
                scaffold_library_path=human_vh3_scaffolds,
                germline_db="v1_clean",
                vhh_hallmark_weight=0.0,  # Human VH3VHH hallmark，hallmark
                top_k=args.top_k,
            )
            case_results["Case B"] = result_b
            ranking_data_b = extract_ranking_data(result_b, "human_vh3_scaffolds")
            
            # Case B ： topK，，
            if len(ranking_data_b) < args.top_k:
                print(f"  ⚠️ :  {len(ranking_data_b)} （: {args.top_k}），")
            
            all_ranking_data.extend(ranking_data_b)
            print(f"  ✅ : {len(ranking_data_b)} ")
        except Exception as e:
            print(f"  ❌ : {e}")
            import traceback
            traceback.print_exc()
            case_results["Case B"] = {"error": str(e), "ranked": []}
    else:
        print(f"  ❌ : {human_vh3_scaffolds}")
        case_results["Case B"] = {"error": "", "ranked": []}
    print()
    
    # Case C: VHH special FR templates (82，scaffold)
    # Case C  VHH （）
    print("[Case C] VHH special FR templates (82，scaffold)...")
    if vhh_fr_templates.exists():
        try:
            # FRscaffold
            fr_scaffolds = load_fr_templates_as_scaffolds(vhh_fr_templates)
            print(f"  ✅ : {len(fr_scaffolds)} FR")
            
            result_c = run_case(
                case_name="Case C",
                query_seq=query_seq,
                scaffold_library_list=fr_scaffolds,
                germline_db="vhh_v1",
                vhh_hallmark_weight=0.15,
                top_k=args.top_k,
            )
            case_results["Case C"] = result_c
            ranking_data_c = extract_ranking_data(result_c, "special_fr_templates")
            
            # Case C ： topK，，
            if len(ranking_data_c) < args.top_k:
                print(f"  ⚠️ :  {len(ranking_data_c)} （: {args.top_k}），")
            
            all_ranking_data.extend(ranking_data_c)
            print(f"  ✅ : {len(ranking_data_c)} ")
        except Exception as e:
            print(f"  ❌ : {e}")
            import traceback
            traceback.print_exc()
            case_results["Case C"] = {"error": str(e), "ranked": []}
    else:
        print(f"  ❌ : {vhh_fr_templates}")
        case_results["Case C"] = {"error": "", "ranked": []}
    print()
    
    # debug CSV
    args.output_dir.mkdir(parents=True, exist_ok=True)
    debug_csv_path = args.output_dir / "vhh_triad_ranking_debug.csv"
    
    print(f"[] debug CSV: {debug_csv_path}")
    with open(debug_csv_path, "w", newline="", encoding="utf-8") as f:
        if all_ranking_data:
            writer = csv.DictWriter(f, fieldnames=[
                "source_library", "rank", "scaffold_id", "framework_identity",
                "proxy_agg", "vhh_hallmark_score", "total_score",
                "hallmark_available", "total_score_fixed", "total_score_norm", "score_mode_used", "notes"
            ])
            writer.writeheader()
            writer.writerows(all_ranking_data)
        else:
            # ，header
            writer = csv.DictWriter(f, fieldnames=[
                "source_library", "rank", "scaffold_id", "framework_identity",
                "proxy_agg", "vhh_hallmark_score", "total_score",
                "hallmark_available", "total_score_fixed", "total_score_norm", "score_mode_used", "notes"
            ])
            writer.writeheader()
    
    print(f"  ✅  {len(all_ranking_data)} ")
    print()
    
    # hallmark_available
    print("=" * 80)
    print("Hallmark")
    print("=" * 80)
    for case_name, result in case_results.items():
        if "error" not in result:
            ranked = result.get("stage1", {}).get("ranked_top10", [])
            if ranked:
                hallmark_available_count = 0
                for candidate in ranked:
                    vhh_hallmark = candidate.get("vhh_hallmark", {})
                    if isinstance(vhh_hallmark, dict) and vhh_hallmark:
                        hallmark_available_count += 1
                
                proportion = hallmark_available_count / len(ranked) * 100
                print(f"{case_name}: {hallmark_available_count}/{len(ranked)} ({proportion:.1f}%)")
    print()
    
    # Case ACase CTop1（）
    if "Case A" in case_results and "Case C" in case_results:
        case_a_result = case_results["Case A"]
        case_c_result = case_results["Case C"]
        if "error" not in case_a_result and "error" not in case_c_result:
            ranked_a = case_a_result.get("stage1", {}).get("ranked_top10", [])
            ranked_c = case_c_result.get("stage1", {}).get("ranked_top10", [])
            if ranked_a and ranked_c:
                top1_a = ranked_a[0]
                top1_c = ranked_c[0]
                
                # 
                a_fi = top1_a.get("framework_identity", 0.0)
                a_proxy = top1_a.get("canonical_proxy", {}).get("proxy_agg", 0.0) if isinstance(top1_a.get("canonical_proxy", {}), dict) else 0.0
                a_hallmark = top1_a.get("vhh_hallmark", {}).get("score", None) if isinstance(top1_a.get("vhh_hallmark", {}), dict) and top1_a.get("vhh_hallmark", {}) else None
                
                c_fi = top1_c.get("framework_identity", 0.0)
                c_proxy = top1_c.get("canonical_proxy", {}).get("proxy_agg", 0.0) if isinstance(top1_c.get("canonical_proxy", {}), dict) else 0.0
                c_hallmark = top1_c.get("vhh_hallmark", {}).get("score", None) if isinstance(top1_c.get("vhh_hallmark", {}), dict) and top1_c.get("vhh_hallmark", {}) else None
                
                # （）
                scores_match = (
                    abs(a_fi - c_fi) < 0.0001 and
                    abs(a_proxy - c_proxy) < 0.0001 and
                    ((a_hallmark is None and c_hallmark is None) or 
                     (a_hallmark is not None and c_hallmark is not None and abs(a_hallmark - c_hallmark) < 0.0001))
                )
                
                if scores_match:
                    print("=" * 80)
                    print("")
                    print("=" * 80)
                    print("✅ Case A Top1  Case C Top1 ")
                    print(f"   Case A Top1: {top1_a.get('scaffold_id', 'N/A')}")
                    print(f"   Case C Top1: {top1_c.get('scaffold_id', 'N/A')}")
                    print(f"   : FI={a_fi:.4f}, Proxy={a_proxy:.4f}, Hallmark={a_hallmark if a_hallmark is not None else 'N/A'}")
                    print("   : special FR templates (82) ' VHH '，")
                    print("          264。")
                    print()
    
    # Case Bproxy
    if "Case B" in case_results:
        case_b_result = case_results["Case B"]
        if "error" not in case_b_result:
            ranked_b = case_b_result.get("stage1", {}).get("ranked_top10", [])
            if ranked_b:
                top1_b = ranked_b[0]
                canonical_proxy = top1_b.get("canonical_proxy", {})
                proxy_agg = canonical_proxy.get("proxy_agg", 0.0) if isinstance(canonical_proxy, dict) else 0.0
                vhh_hallmark = top1_b.get("vhh_hallmark", {})
                has_hallmark = isinstance(vhh_hallmark, dict) and vhh_hallmark
                
                if proxy_agg > 0.9 and not has_hallmark:
                    print("=" * 80)
                    print("")
                    print("=" * 80)
                    print("✅ Case B (VH3)  proxy ， hallmark ")
                    print(f"   Case B Top1 Proxy Agg: {proxy_agg:.4f}")
                    print("   : VH humanization， VHH ；")
                    print("         'VH3→VHH hallmark '。")
                    print()
    
    # summary MD
    summary_md_path = args.output_dir / "vhh_triad_ranking_summary.md"
    print(f"[] summary MD: {summary_md_path}")
    
    with open(summary_md_path, "w", encoding="utf-8") as f:
        f.write("# VHH Scaffold Ranking Triad Summary\n\n")
        f.write(f"****: {query_seq[:50]}... (: {len(query_seq)} aa)\n\n")
        f.write("## \n\n")
        f.write("scaffoldranking：\n\n")
        f.write("1. **VHH scaffold library** (264): VHHscaffold\n")
        f.write("2. **Human VH3 scaffold library**: VH3 scaffold\n")
        f.write("3. **VHH special FR templates** (82): FR-only（scaffold）\n\n")
        f.write("## \n\n")
        f.write("**Case B (VH3) lacks hallmark; compare using total_score_norm.**\n\n")
        f.write("**Case B hallmark， total_score_norm**\n\n")
        f.write("**total_score_fixed （ hallmark  0）**\n\n")
        f.write("**triad Top5  fixed  norm**\n\n")
        f.write("---\n\n")
        
        # casetop5
        for case_name, result in case_results.items():
            f.write(f"## {case_name}\n\n")
            
            if "error" in result:
                f.write(f"****: ❌ \n\n")
                f.write(f"****: {result['error']}\n\n")
            else:
                ranked = result.get("stage1", {}).get("ranked_top10", [])
                if not ranked:
                    f.write(f"****: ⚠️ \n\n")
                else:
                    f.write(f"****: ✅  ({len(ranked)} )\n\n")
                    
                    # topK，
                    if len(ranked) < args.top_k:
                        f.write(f"****:  {len(ranked)} （: {args.top_k}）")
                        if case_name == "Case B":
                            f.write("，。\n\n")
                        else:
                            f.write("，。\n\n")
                    
                    # Top 5（5）
                    top5_count = min(5, len(ranked))
                    f.write(f"### Top {top5_count} \n\n")
                    f.write("| Rank | Scaffold ID | Framework Identity | Proxy Agg | VHH Hallmark | Total Score (Fixed) | Total Score (Norm) |\n")
                    f.write("|------|-------------|-------------------|-----------|--------------|---------------------|---------------------|\n")
                    
                    for idx, candidate in enumerate(ranked[:top5_count], 1):
                        scaffold_id = candidate.get("scaffold_id", "")
                        framework_identity = candidate.get("framework_identity", 0.0)
                        canonical_proxy = candidate.get("canonical_proxy", {})
                        canonical_proxy_agg = canonical_proxy.get("proxy_agg", None) if isinstance(canonical_proxy, dict) else None
                        vhh_hallmark = candidate.get("vhh_hallmark", {})
                        vhh_hallmark_score = vhh_hallmark.get("score", None) if isinstance(vhh_hallmark, dict) and vhh_hallmark else None
                        
                        # fixednorm
                        proxy_agg_value = canonical_proxy_agg if canonical_proxy_agg is not None else 0.0
                        _, total_score_fixed, total_score_norm, _ = calculate_scores(
                            framework_identity,
                            proxy_agg_value,
                            vhh_hallmark_score,
                        )
                        
                        vhh_hallmark_display = f"{vhh_hallmark_score:.4f}" if vhh_hallmark_score is not None else "N/A"
                        proxy_agg_display = f"{canonical_proxy_agg:.4f}" if canonical_proxy_agg is not None else "N/A"
                        
                        f.write(f"| {idx} | {scaffold_id[:40]} | {framework_identity:.4f} | "
                               f"{proxy_agg_display} | {vhh_hallmark_display} | {total_score_fixed:.4f} | {total_score_norm:.4f} |\n")
                    
                    # 
                    if ranked:
                        best = ranked[0]
                        f.write("\n### \n\n")
                        f.write(f"**Scaffold ID**: {best.get('scaffold_id', 'N/A')}\n\n")
                        f.write(f"**Total Score**: {best.get('total_score', 0.0):.4f}\n\n")
                        f.write(f"- Framework Identity: {best.get('framework_identity', 0.0):.4f} "
                               f"(: 0.75)\n")
                        
                        canonical_proxy = best.get("canonical_proxy", {})
                        canonical_proxy_agg = canonical_proxy.get("proxy_agg", None) if isinstance(canonical_proxy, dict) else None
                        if canonical_proxy_agg is not None:
                            f.write(f"- Canonical Proxy: {canonical_proxy_agg:.4f} (: 0.10)\n")
                        else:
                            f.write(f"- Canonical Proxy: N/A ()\n")
                        
                        vhh_hallmark = best.get("vhh_hallmark", {})
                        if vhh_hallmark and isinstance(vhh_hallmark, dict):
                            vhh_hallmark_score = vhh_hallmark.get("score", 0.0)
                            f.write(f"- VHH Hallmark: {vhh_hallmark_score:.4f} (: 0.15)\n")
                        
                        f.write("\nframework identity、canonical proxyVHH hallmark。\n\n")
            
            f.write("---\n\n")
        
        f.write("## \n\n")
        f.write("ranking `vhh_triad_ranking_debug.csv`。\n\n")
    
    print(f"  ✅ summary")
    print()
    
    # ：rows_written  hallmark_available_ratio
    print("=" * 80)
    print("")
    print("=" * 80)
    
    case_row_counts = {}
    case_hallmark_ratios = {}
    
    for case_name, result in case_results.items():
        if "error" not in result:
            ranked = result.get("stage1", {}).get("ranked_top10", [])
            if ranked:
                rows_written = len(ranked)
                hallmark_available_count = sum(
                    1 for candidate in ranked
                    if isinstance(candidate.get("vhh_hallmark", {}), dict) and candidate.get("vhh_hallmark", {})
                )
                hallmark_available_ratio = hallmark_available_count / rows_written if rows_written > 0 else 0.0
                
                case_row_counts[case_name] = rows_written
                case_hallmark_ratios[case_name] = hallmark_available_ratio
                
                print(f"{case_name}:")
                print(f"  rows_written = {rows_written}")
                print(f"  hallmark_available_ratio = {hallmark_available_ratio:.4f} ({hallmark_available_count}/{rows_written})")
            else:
                case_row_counts[case_name] = 0
                case_hallmark_ratios[case_name] = 0.0
                print(f"{case_name}:")
                print(f"  rows_written = 0")
                print(f"  hallmark_available_ratio = 0.0000 (0/0)")
        else:
            case_row_counts[case_name] = 0
            case_hallmark_ratios[case_name] = 0.0
            print(f"{case_name}:")
            print(f"  rows_written = 0 (: {result.get('error', 'unknown')})")
            print(f"  hallmark_available_ratio = N/A")
    
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)
    print(f":")
    print(f"  - {debug_csv_path}")
    print(f"  - {summary_md_path}")


if __name__ == "__main__":
    main()










