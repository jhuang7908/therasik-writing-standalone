#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EGFR VHH （v4.1）

：
1. （QA v3.5）
2. JSON
3. Client ReportDeveloper Report（v4.1）
4. （）
"""

import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_humanization_with_qa import humanize_vhh_with_qa
from scripts.generate_dual_report_v4_1 import (
    generate_client_report,
    generate_developer_report,
    _generate_figures_v4_1,
    _generate_report_summary_v4_1,
    _generate_final_evaluation_v4_1,
)

# EGFR VHH
EGFR_VHH_SEQ = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"

PROJECT_ID = "EGFR_7D12_VHH"
TARGET = "EGFR"


def main():
    """："""
    print("=" * 80)
    print("EGFR VHH （v4.1）")
    print("=" * 80)
    print(f"\n: {EGFR_VHH_SEQ[:50]}...")
    print(f": {len(EGFR_VHH_SEQ)} aa")
    print(f": {TARGET}")
    print(f"ID: {PROJECT_ID}")
    print("\n" + "=" * 80)
    
    # 
    output_dir = PROJECT_ROOT / "projects" / PROJECT_ID / "reports_v4_1_latest"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    raw_result_dir = PROJECT_ROOT / "projects" / PROJECT_ID / "cro_report" / "raw"
    raw_result_dir.mkdir(parents=True, exist_ok=True)
    
    # 1: 
    print("\n[ 1/4] ...")
    print("-" * 80)
    
    result = humanize_vhh_with_qa(
        seq=EGFR_VHH_SEQ,
        panel="A",  # A（）
        top_k=5,
        species="alpaca",
        return_all_templates=False,
        enable_safe_mode=True,
        strict_qa=True,
        qa_version="v3.5",
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
    
    # 2: JSON
    print("\n[ 2/4] JSON...")
    print("-" * 80)
    
    # JSON（germline_selection_proofgermline.candidates[].scores.overall）
    from core.json_data_preparer import prepare_json_data
    prepared_result = prepare_json_data(result, "REPORT")
    
    # ：JSONgermline_library_provenancegermline_numbering
    from core.segmentation.json_validator import validate_json_for_delivery
    is_valid, errors = validate_json_for_delivery(prepared_result, strict=True)
    
    if not is_valid:
        print(f"❌ JSON，：")
        for error in errors:
            print(f"  - {error}")
        raise ValueError("JSON：germline_library_provenancegermline_numbering")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # raw（）
    raw_result_path = raw_result_dir / f"raw_result_{timestamp}.json"
    with open(raw_result_path, "w", encoding="utf-8") as f:
        json.dump(prepared_result, f, indent=2, ensure_ascii=False)
    print(f"✅ Raw: {raw_result_path}")
    
    # 
    result_json_path = output_dir / f"result_{timestamp}.json"
    with open(result_json_path, "w", encoding="utf-8") as f:
        json.dump(prepared_result, f, indent=2, ensure_ascii=False)
    print(f"✅ : {result_json_path}")
    
    # 3: 
    print("\n[ 3/4] Client ReportDeveloper Report...")
    print("-" * 80)
    
    try:
        # Client Report（prepared_result）
        print("[INFO] Client Report...")
        client_report_path = generate_client_report(prepared_result, output_dir, PROJECT_ID)
        print(f"✅ Client Report: {client_report_path}")
        
        # Developer Report（prepared_result）
        print("[INFO] Developer Report...")
        developer_report_path = generate_developer_report(prepared_result, output_dir, PROJECT_ID)
        print(f"✅ Developer Report: {developer_report_path}")
        
    except Exception as e:
        print(f"❌ : {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 4: 
    print("\n[ 4/4] ...")
    print("-" * 80)
    
    try:
        figures_success, figures_dir, figures_generated = _generate_figures_v4_1(
            raw_result_path=raw_result_path,  # prepared_result
            output_dir=output_dir,
            project_id=PROJECT_ID,
        )
        
        if figures_success:
            print(f"✅ ")
            print(f"   - : {figures_dir}")
            print(f"   - : {len(figures_generated)}")
            for fig in figures_generated:
                print(f"     - {fig}")
        else:
            print(f"⚠️  ，...")
            
    except Exception as e:
        print(f"⚠️  : {e}，...")
        import traceback
        traceback.print_exc()
    
    # 
    print("\n[INFO] ...")
    try:
        summary_path = _generate_report_summary_v4_1(
            result=prepared_result,  # prepared_result
            output_dir=output_dir,
            project_id=PROJECT_ID,
            raw_result_path=raw_result_path,
        )
        print(f"✅ : {summary_path}")
    except Exception as e:
        print(f"⚠️  : {e}")
    
    # 
    print("\n[INFO] ...")
    try:
        evaluation_path = _generate_final_evaluation_v4_1(
            result=prepared_result,  # prepared_result
            output_dir=output_dir,
            project_id=PROJECT_ID,
        )
        print(f"✅ : {evaluation_path}")
    except Exception as e:
        print(f"⚠️  : {e}")
    
    # 
    print("\n" + "=" * 80)
    print("✅ ！")
    print("=" * 80)
    print(f"\n:")
    print(f"  - JSON: {result_json_path}")
    print(f"  - Raw: {raw_result_path}")
    print(f"  - Client Report: {client_report_path}")
    print(f"  - Developer Report: {developer_report_path}")
    print(f"  - : {output_dir / 'figures'}")
    print(f"\n: {output_dir}")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    exit(main())




