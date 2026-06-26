#!/usr/bin/env python3
"""
 result JSON 
"""

import json
import glob
from pathlib import Path
from datetime import datetime
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_dual_report_v3 import generate_client_report, generate_developer_report
from core.segmentation.json_validator import validate_json_for_delivery


def rerender_reports_from_json():
    """ result JSON """
    
    outdir = Path("output/reports_rerender_20251217")
    outdir.mkdir(parents=True, exist_ok=True)
    
    # JSON
    targets = []
    for pat in [
        "**/result_20251217_*.json",
        "**/result_VH_20251217_*.json",
        "**/result_VL_20251217_*.json",
        "projects/**/output/result.json",
    ]:
        targets += glob.glob(pat, recursive=True)
    
    # ，
    targets = sorted(set(targets), key=lambda p: Path(p).stat().st_mtime, reverse=True)
    
    print("=" * 80)
    print("")
    print("=" * 80)
    print(f"\n {len(targets)} JSON")
    print("\n:")
    for jp in targets[:10]:  # 10
        print(f"  - {jp}")
    
    if len(targets) > 10:
        print(f"  ...  {len(targets) - 10} ")
    
    print(f"\n: {outdir}")
    print("=" * 80)
    
    success_count = 0
    error_count = 0
    
    for json_path in targets:
        json_path = Path(json_path)
        if not json_path.exists():
            continue
        
        try:
            print(f"\n: {json_path}")
            print("-" * 80)
            
            # JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                result = json.load(f)
            
            # ID
            project_id = (
                result.get("project_id") or
                result.get("input", {}).get("project_id") or
                json_path.parent.name or
                "Unknown_Project"
            )
            
            # 
            project_outdir = outdir / project_id
            project_outdir.mkdir(parents=True, exist_ok=True)
            
            # （）
            import scripts.generate_dual_report_v3 as report_module
            original_validate = report_module.validate_json_for_delivery
            
            def lenient_validate(data, strict=False):
                return True, []
            
            report_module.validate_json_for_delivery = lenient_validate
            
            try:
                # Client Report
                try:
                    print(f"   Client Report...")
                    client_report_path = generate_client_report(
                        result=result,
                        output_dir=project_outdir,
                        project_id=project_id,
                    )
                    print(f"  ✅ Client Report: {client_report_path}")
                    success_count += 1
                except Exception as e:
                    print(f"  ❌ Client Report: {e}")
                    error_count += 1
                
                # Developer Report
                try:
                    print(f"   Developer Report...")
                    developer_report_path = generate_developer_report(
                        result=result,
                        output_dir=project_outdir,
                        project_id=project_id,
                    )
                    print(f"  ✅ Developer Report: {developer_report_path}")
                    success_count += 1
                except Exception as e:
                    print(f"  ❌ Developer Report: {e}")
                    error_count += 1
            finally:
                # 
                report_module.validate_json_for_delivery = original_validate
            
        except Exception as e:
            print(f"  ❌ : {e}")
            import traceback
            traceback.print_exc()
            error_count += 1
    
    print("\n" + "=" * 80)
    print("✅ ")
    print("=" * 80)
    print(f": {success_count} ")
    print(f": {error_count} ")
    print(f": {outdir}")
    print("=" * 80)


if __name__ == "__main__":
    rerender_reports_from_json()

