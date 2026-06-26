#!/usr/bin/env python3
"""
VHH （Python）


:
    python scripts/generate_full_report.py [result.json] [output_dir] [project_id]

:
    python scripts/generate_full_report.py result.json reports/output EGFR_7D12_VHH
"""

import sys
import subprocess
from pathlib import Path


def main():
    """"""
    # 
    result_json = sys.argv[1] if len(sys.argv) > 1 else "result.json"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "reports/output"
    project_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    # 
    result_path = Path(result_json)
    if not result_path.exists():
        print(f"❌ :  {result_json}")
        return 1
    
    # ID，JSON
    if not project_id:
        try:
            import json
            with open(result_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            project_id = data.get("project_id", "unknown_project")
        except:
            project_id = "unknown_project"
    
    print("=" * 60)
    print("VHH ")
    print("=" * 60)
    print(f": {result_json}")
    print(f": {output_dir}")
    print(f"ID: {project_id}")
    print("=" * 60)
    print()
    
    #  1: 
    print("📊  1: ...")
    try:
        cmd = [
            sys.executable,
            "scripts/plot_vhh_report_figures_v1.py",
            "--input", str(result_path),
            "--output_dir", output_dir,
        ]
        if project_id:
            cmd.extend(["--project-id", project_id])
        
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ")
        else:
            print("⚠️  ，...")
            if result.stderr:
                print(f"   : {result.stderr[:200]}")
    except Exception as e:
        print(f"⚠️  : {e}，...")
    
    print()
    
    #  2: 
    print("📄  2:  Markdown + DOCX ...")
    try:
        cmd = [
            sys.executable,
            "scripts/generate_vhh_report_v1.py",
            "--input", str(result_path),
            "--output_dir", output_dir,
        ]
        if project_id:
            cmd.extend(["--project-id", project_id])
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ ")
    except subprocess.CalledProcessError as e:
        print(f"❌ : {e}")
        if e.stderr:
            print(f"   : {e.stderr}")
        return 1
    except Exception as e:
        print(f"❌ : {e}")
        return 1
    
    print()
    print("=" * 60)
    print("✅ ！")
    print("=" * 60)
    print()
    print("：")
    output_project_dir = Path(output_dir) / project_id
    print(f"  📄 Markdown: {output_project_dir / 'report_v1.md'}")
    print(f"  📄 DOCX:     {output_project_dir / 'report_v1.docx'}")
    print(f"  📊 :     {output_project_dir / 'figures'}/*.png")
    print()
    print(" / PI /  / ""。")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())

















