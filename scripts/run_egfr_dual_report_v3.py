#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EGFR VHH （Client + Developer Report v3.0）

：
1. （QA v3.5）
2.  Client Report（）
3.  Developer Report（）
4. 
"""

import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_humanization_with_qa import humanize_vhh_with_qa
from scripts.generate_dual_report_v3 import generate_client_report, generate_developer_report
from scripts.plot_vhh_report_figures_v1 import main as plot_figures_main
import argparse

# EGFR VHH
EGFR_VHH_SEQ = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"

PROJECT_ID = "EGFR_7D12_VHH"
TARGET = "EGFR"


def main():
    """："""
    parser = argparse.ArgumentParser(description="EGFR VHH")
    parser.add_argument("--panel", type=str, default="A", choices=["A", "B", "C", "all"], 
                       help=" (A: , B: , C: VHH, all: )")
    parser.add_argument("--qa-version", type=str, default="v3.5", choices=["v3.4", "v3.5"],
                       help="QA")
    parser.add_argument("--output-dir", type=Path, default=None,
                       help="（: projects/EGFR_7D12_VHH/reports_v3）")
    parser.add_argument("--skip-figures", action="store_true",
                       help="")
    
    args = parser.parse_args()
    
    # 
    if args.output_dir is None:
        output_dir = PROJECT_ROOT / "projects" / PROJECT_ID / "reports_v3"
    else:
        output_dir = args.output_dir
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("EGFR VHH （v3.0）")
    print("=" * 80)
    print(f"\n: {EGFR_VHH_SEQ[:50]}...")
    print(f": {len(EGFR_VHH_SEQ)} aa")
    print(f": {TARGET}")
    print(f": {args.panel}")
    print(f"QA: {args.qa_version}")
    print(f": {output_dir}")
    print("\n" + "=" * 80)
    
    # 1: 
    print("\n[ 1/4] ...")
    print("-" * 80)
    
    result = humanize_vhh_with_qa(
        seq=EGFR_VHH_SEQ,
        panel=args.panel,
        top_k=5,
        species="alpaca",
        return_all_templates=False,
        enable_safe_mode=True,
        strict_qa=True,
        qa_version=args.qa_version,
    )
    
    # 
    result["project_id"] = PROJECT_ID
    result["target"] = TARGET
    result["input"] = result.get("input", {})
    result["input"]["sequence"] = EGFR_VHH_SEQ
    result["input"]["target"] = TARGET
    result["input"]["species"] = "alpaca"
    
    #  JSON
    result_json_path = output_dir / f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"[INFO] : {result_json_path}")
    
    if not result.get("success"):
        print(f"[ERROR] : {result.get('error', 'Unknown error')}")
        return 1
    
    print(f"[INFO] ！: {result.get('status', 'OK')}")
    
    # 2: 
    if not args.skip_figures:
        print("\n[ 2/4] ...")
        print("-" * 80)
        
        figures_dir = output_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        
        # 
        import sys as sys_module
        old_argv = sys_module.argv
        try:
            sys_module.argv = [
                "plot_vhh_report_figures_v1.py",
                "--input", str(result_json_path),
                "--output_dir", str(figures_dir),
                "--project-id", PROJECT_ID,
            ]
            plot_figures_main()
        except Exception as e:
            print(f"[WARN] : {e}")
        finally:
            sys_module.argv = old_argv
    
    # 3:  Client Report
    print("\n[ 3/4]  Client Report...")
    print("-" * 80)
    
    try:
        client_report_path = generate_client_report(
            result=result,
            output_dir=output_dir,
            project_id=PROJECT_ID,
        )
        print(f"[INFO] Client Report : {client_report_path}")
    except Exception as e:
        print(f"[ERROR] Client Report : {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 4:  Developer Report
    print("\n[ 4/4]  Developer Report...")
    print("-" * 80)
    
    try:
        developer_report_path = generate_developer_report(
            result=result,
            output_dir=output_dir,
            project_id=PROJECT_ID,
        )
        print(f"[INFO] Developer Report : {developer_report_path}")
    except Exception as e:
        print(f"[ERROR] Developer Report : {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 
    print("\n" + "=" * 80)
    print("")
    print("=" * 80)
    
    _print_evaluation_summary(result)
    
    print("\n" + "=" * 80)
    print("✅ ！")
    print("=" * 80)
    print(f"\n: {output_dir}")
    print(f"  - Client Report: {client_report_path.name}")
    print(f"  - Developer Report: {developer_report_path.name}")
    print(f"  -  JSON: {result_json_path.name}")
    if not args.skip_figures:
        print(f"  - : figures/")
    
    return 0


def _print_evaluation_summary(result: dict):
    """"""
    print("\n### ")
    success = result.get("success", False)
    status = result.get("status", "UNKNOWN")
    print(f"  - : {'✅' if success else '❌'}")
    print(f"  - : {status}")
    
    if not success:
        error = result.get("error", "Unknown error")
        print(f"  - : {error}")
        return
    
    # QA 
    print("\n### QA ")
    qa = result.get("qa", {})
    qa_v35 = qa.get("v3_5", {}) or qa.get("v3_4", {}) or {}
    qa_ok = qa_v35.get("ok", False)
    print(f"  - QA : {'✅' if qa_ok else '❌'}")
    
    # 
    structural_risk = qa_v35.get("structural_risk_components", {}) or {}
    total_risk = structural_risk.get("total_risk", 0.0)
    print(f"  - : {total_risk:.3f}")
    
    # 
    print("\n### ")
    best_match = result.get("best_match", {})
    template = best_match.get("template", {})
    template_id = template.get("id", "N/A")
    print(f"  -  ID: {template_id}")
    
    # 
    print("\n### ")
    mutations = result.get("mutations", {}).get("list", [])
    print(f"  - : {len(mutations)}")
    
    # （）
    if "tier_classification" in result:
        tiered = result["tier_classification"]
        seq1_muts = len(tiered.get("seq1", {}).get("mutations", []))
        seq2_muts = len(tiered.get("seq2", {}).get("mutations", []))
        seq3_muts = len(tiered.get("seq3", {}).get("mutations", []))
        print(f"  - Seq1 : {seq1_muts}")
        print(f"  - Seq2 : {seq2_muts}")
        print(f"  - Seq3 : {seq3_muts}")


if __name__ == "__main__":
    exit(main())
















