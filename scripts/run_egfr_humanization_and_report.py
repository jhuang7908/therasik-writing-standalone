#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EGFR VHH

：
1. （QA v3.5）
2. （Markdown + DOCX）
3. 
"""

import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_humanization_with_qa import humanize_vhh_with_qa
from scripts.generate_vhh_report_v1 import generate_report
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
                       help="（: projects/EGFR_7D12_VHH/reports）")
    parser.add_argument("--skip-figures", action="store_true",
                       help="")
    
    args = parser.parse_args()
    
    # 
    if args.output_dir is None:
        output_dir = PROJECT_ROOT / "projects" / PROJECT_ID / "reports"
    else:
        output_dir = args.output_dir
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("EGFR VHH ")
    print("=" * 80)
    print(f"\n: {EGFR_VHH_SEQ[:50]}...")
    print(f": {len(EGFR_VHH_SEQ)} aa")
    print(f": {TARGET}")
    print(f": {args.panel}")
    print(f"QA: {args.qa_version}")
    print(f": {output_dir}")
    print("\n" + "=" * 80)
    
    # 1: 
    print("\n[ 1/3] ...")
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
    
    # 
    qa_ok = result.get("qa", {}).get("ok", False)
    status = result.get("status", "UNKNOWN")
    
    print(f"\n✅ ")
    print(f"   - : {status}")
    print(f"   - QA: {'' if qa_ok else ''}")
    
    if not qa_ok:
        qa_errors = result.get("qa", {}).get("errors", [])
        if qa_errors:
            print(f"   - QA: {len(qa_errors)} ")
            for i, err in enumerate(qa_errors[:3], 1):
                print(f"     {i}. {err}")
    
    # JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_json_path = output_dir / f"result_{timestamp}.json"
    
    with open(result_json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"   - : {result_json_path}")
    
    # 2: 
    print("\n[ 2/3] ...")
    print("-" * 80)
    
    template_path = PROJECT_ROOT / "reports" / "templates" / "vhh_full_report_template.md"
    
    if not template_path.exists():
        print(f"❌ : {template_path}")
        return 1
    
    try:
        report_result = generate_report(
            result_json_path=result_json_path,
            template_path=template_path,
            output_dir=output_dir,
            project_id=PROJECT_ID,
        )
        
        print(f"\n✅ ")
        print(f"   - Markdown: {report_result['markdown']}")
        print(f"   - DOCX: {report_result['docx']}")
        
    except Exception as e:
        print(f"❌ : {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 3: 
    if not args.skip_figures:
        print("\n[ 3/3] ...")
        print("-" * 80)
        
        figures_dir = output_dir / PROJECT_ID / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        
        # plot
        import sys as sys_module
        old_argv = sys_module.argv.copy()
        
        try:
            sys_module.argv = [
                "plot_vhh_report_figures_v1.py",
                "--input", str(result_json_path),
                "--output_dir", str(output_dir),
                "--project-id", PROJECT_ID,
            ]
            
            exit_code = plot_figures_main()
            
            if exit_code == 0:
                print(f"\n✅ ")
                print(f"   - : {figures_dir}")
            else:
                print(f"\n⚠️  （: {exit_code}）")
                
        except Exception as e:
            print(f"❌ : {e}")
            import traceback
            traceback.print_exc()
        finally:
            sys_module.argv = old_argv
    else:
        print("\n[ 3/3] （--skip-figures）")
    
    # 
    print("\n" + "=" * 80)
    print("✅ ！")
    print("=" * 80)
    print(f"\n:")
    print(f"  - JSON: {result_json_path}")
    if not args.skip_figures:
        print(f"  - Markdown: {report_result.get('markdown', 'N/A')}")
        print(f"  - DOCX: {report_result.get('docx', 'N/A')}")
        print(f"  - : {output_dir / PROJECT_ID / 'figures'}")
    print("\n" + "=" * 80)
    
    return 0


if __name__ == "__main__":
    exit(main())

