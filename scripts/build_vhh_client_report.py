#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_vhh_client_report.py

 result_vhh_mvp.json  Client Report 
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from scripts.generate_dual_report_v4_1 import generate_client_report
import json
import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate VHH Client Report from MVP JSON")
    parser.add_argument("--input", required=True, help="Input result_vhh_mvp.json file")
    parser.add_argument("--output", required=True, help="Output Markdown report file")
    parser.add_argument("--project-id", default="VHH_Project", help="Project ID")
    
    args = parser.parse_args()
    
    # Load JSON
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        sys.exit(1)
    
    with open(input_path, "r", encoding="utf-8") as f:
        result = json.load(f)
    
    # Generate report
    output_path = Path(args.output)
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = generate_client_report(result, output_dir, args.project_id)
    
    # Rename to desired output name if different
    if report_path.name != output_path.name:
        final_path = output_dir / output_path.name
        report_path.rename(final_path)
        print(f"[INFO] Report saved as: {final_path}")
    else:
        print(f"[INFO] Report saved as: {report_path}")

if __name__ == "__main__":
    main()
















