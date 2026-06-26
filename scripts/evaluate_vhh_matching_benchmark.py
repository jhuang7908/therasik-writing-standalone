"""
VHH

humanize_vhh()，Top-1/Top-3
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# 
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_humanization import humanize_vhh
from core.config import get_config


def load_benchmark_gold_standard() -> List[Dict[str, Any]]:
    """
    
    
    Returns:
        ，：
        - vhh_sequence: VHH
        - vhh_id: VHH
        - expected_template_id: ID（）
        - expected_template_ids: ID（Top-3，）
        - should_not_match: ID（）
        - notes: 
    """
    cfg = get_config()
    path = cfg.paths.benchmark_gold_standard
    
    if not path.exists():
        print(f"[WARN] : {path}")
        print("[INFO] ...")
        _create_example_benchmark(path)
        return []
    
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _create_example_benchmark(path: Path):
    """"""
    example = [
        {
            "vhh_id": "EXAMPLE_001",
            "vhh_sequence": "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS",
            "expected_template_id": "HUMAN_VH3_VHH_SAFE_A_01",
            "expected_template_ids": [
                "HUMAN_VH3_VHH_SAFE_A_01",
                "HUMAN_VH3_VHH_SAFE_A_02",
                "HUMAN_VH3_VHH_SAFE_B_01"
            ],
            "should_not_match": [],
            "notes": "VHH，A"
        }
    ]
    
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding='utf-8') as f:
        json.dump(example, f, indent=2, ensure_ascii=False)
    
    print(f"[INFO] : {path}")
    print("[INFO] ，")


def evaluate_single_vhh(
    benchmark_item: Dict[str, Any],
    panel: str = "all",
    top_k: int = 10
) -> Dict[str, Any]:
    """
    VHH
    
    Args:
        benchmark_item: 
        panel: 
        top_k: k
    
    Returns:
        
    """
    vhh_seq = benchmark_item["vhh_sequence"]
    vhh_id = benchmark_item.get("vhh_id", "unknown")
    expected_template_id = benchmark_item.get("expected_template_id")
    expected_template_ids = benchmark_item.get("expected_template_ids", [])
    should_not_match = benchmark_item.get("should_not_match", [])
    
    # 
    result = humanize_vhh(vhh_seq, panel=panel, top_k=top_k)
    
    # ID
    matched_template_ids = []
    if result.get("success"):
        best_match = result.get("best_match", {})
        if best_match:
            template = best_match.get("template", {})
            matched_template_ids.append(template.get("template_id"))
        
        # best_by_plan，
        best_by_plan = result.get("best_by_plan", {})
        for plan_result in best_by_plan.values():
            if plan_result:
                template = plan_result.get("template", {})
                tid = template.get("template_id")
                if tid and tid not in matched_template_ids:
                    matched_template_ids.append(tid)
    
    # 
    top1_hit = False
    top3_hit = False
    if expected_template_id:
        top1_hit = matched_template_ids and matched_template_ids[0] == expected_template_id
        top3_hit = expected_template_id in matched_template_ids[:3]
    
    if expected_template_ids:
        top1_hit = top1_hit or (matched_template_ids and matched_template_ids[0] in expected_template_ids)
        top3_hit = top3_hit or any(tid in matched_template_ids[:3] for tid in expected_template_ids)
    
    # 
    matched_forbidden = [tid for tid in matched_template_ids if tid in should_not_match]
    
    # 
    quality_flags = result.get("quality_flags", {})
    risk_flags = result.get("risk_flags", {})
    has_warnings = bool(quality_flags or risk_flags)
    
    return {
        "vhh_id": vhh_id,
        "success": result.get("success", False),
        "matched_template_ids": matched_template_ids,
        "top1_hit": top1_hit,
        "top3_hit": top3_hit,
        "matched_forbidden": matched_forbidden,
        "has_warnings": has_warnings,
        "quality_flags": quality_flags,
        "risk_flags": risk_flags,
        "error": result.get("error") if not result.get("success") else None,
    }


def evaluate_benchmark(
    benchmark: List[Dict[str, Any]],
    panel: str = "all",
    top_k: int = 10
) -> Dict[str, Any]:
    """
    
    
    Args:
        benchmark: 
        panel: 
        top_k: k
    
    Returns:
        
    """
    results = []
    
    for item in benchmark:
        print(f"[INFO] : {item.get('vhh_id', 'unknown')}")
        result = evaluate_single_vhh(item, panel=panel, top_k=top_k)
        results.append(result)
    
    # 
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    top1_hits = sum(1 for r in results if r["top1_hit"])
    top3_hits = sum(1 for r in results if r["top3_hit"])
    with_warnings = sum(1 for r in results if r["has_warnings"])
    matched_forbidden = sum(1 for r in results if r["matched_forbidden"])
    
    stats = {
        "total": total,
        "successful": successful,
        "success_rate": successful / total if total > 0 else 0,
        "top1_hits": top1_hits,
        "top1_hit_rate": top1_hits / total if total > 0 else 0,
        "top3_hits": top3_hits,
        "top3_hit_rate": top3_hits / total if total > 0 else 0,
        "with_warnings": with_warnings,
        "warning_rate": with_warnings / total if total > 0 else 0,
        "matched_forbidden": matched_forbidden,
        "forbidden_match_rate": matched_forbidden / total if total > 0 else 0,
        "detailed_results": results,
    }
    
    return stats


def print_evaluation_report(stats: Dict[str, Any]):
    """"""
    print("\n" + "=" * 60)
    print("VHH Humanization Benchmark Evaluation Report")
    print("=" * 60)
    print()
    
    print(f"Total Test Cases: {stats['total']}")
    print(f"Successful Humanizations: {stats['successful']} ({stats['success_rate']*100:.1f}%)")
    print()
    
    print("Template Matching:")
    print(f"  Top-1 Hit Rate: {stats['top1_hits']}/{stats['total']} ({stats['top1_hit_rate']*100:.1f}%)")
    print(f"  Top-3 Hit Rate: {stats['top3_hits']}/{stats['total']} ({stats['top3_hit_rate']*100:.1f}%)")
    print()
    
    print("Warning Detection:")
    print(f"  Cases with Warnings: {stats['with_warnings']}/{stats['total']} ({stats['warning_rate']*100:.1f}%)")
    print()
    
    if stats['matched_forbidden'] > 0:
        print(f"⚠️  Forbidden Matches: {stats['matched_forbidden']}/{stats['total']} ({stats['forbidden_match_rate']*100:.1f}%)")
        print()
    
    # 
    print("Detailed Results:")
    print("-" * 60)
    for result in stats['detailed_results']:
        status = "✅" if result['top1_hit'] else ("⚠️" if result['top3_hit'] else "❌")
        print(f"{status} {result['vhh_id']}: ", end="")
        if result['success']:
            print(f"Matched: {result['matched_template_ids'][:3]}")
            if result['has_warnings']:
                print(f"  Warnings: {result['quality_flags']}, {result['risk_flags']}")
        else:
            print(f"Failed: {result['error']}")
    
    print("=" * 60)


def main():
    """"""
    import argparse
    
    parser = argparse.ArgumentParser(description="VHH")
    parser.add_argument(
        "--benchmark",
        type=Path,
        help="（config）"
    )
    parser.add_argument(
        "--panel",
        choices=["A", "B", "C", "all"],
        default="all",
        help=""
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="k"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="JSON"
    )
    
    args = parser.parse_args()
    
    # 
    if args.benchmark:
        with open(args.benchmark, encoding='utf-8') as f:
            benchmark = json.load(f)
    else:
        benchmark = load_benchmark_gold_standard()
    
    if not benchmark:
        print("[ERROR] ，")
        return 1
    
    print(f"[INFO] : {len(benchmark)} ")
    
    # 
    stats = evaluate_benchmark(benchmark, panel=args.panel, top_k=args.top_k)
    
    # 
    print_evaluation_report(stats)
    
    # 
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"\n[INFO] : {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


















