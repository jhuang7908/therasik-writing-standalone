#!/usr/bin/env python3
"""
 VH-VL Germline  (Pairing Matrix)

 842 （384 natural + 458 engineered） 458 。
：
1. Pairing Matrix CSV (=VH, =VL)
2. Top Pairings Report (Markdown)

：
  python scripts/generate_pairing_matrix.py           # ：842 
  python scripts/generate_pairing_matrix.py --full    # 842 
  python scripts/generate_pairing_matrix.py --engineered  #  458 
"""

import argparse
import json
from pathlib import Path

import pandas as pd

# Input: The source Excel file is the most reliable source for Germline info
PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCEL_PATH = PROJECT_ROOT / "data/humanization_assay/thera_human_igG_germline_analysis.xlsx"
OUT_DIR = PROJECT_ROOT / "data/humanization_assay"


def generate_pairing_matrix(use_full_842: bool = True):
    """use_full_842: True=842(384+458), False=458"""
    if not EXCEL_PATH.exists():
        print(f"Error: {EXCEL_PATH} not found.")
        return

    print(f"Reading {EXCEL_PATH}...")
    df = pd.read_excel(EXCEL_PATH)

    if use_full_842:
        #  842 （384 natural + 458 engineered）
        print(f"Using all {len(df)} clinical antibodies (842 = 384 natural + 458 engineered).")
    else:
        #  458 
        if "human_origin_mode" in df.columns:
            df = df[df["human_origin_mode"] == "engineered_humanisation"].copy()
            print(f"Filtered to {len(df)} engineered antibodies.")
    
    # Columns for Germline: likely 'VH_Germline' and 'VL_Germline' or similar
    # Let's inspect columns if we were interactive, but here we guess standard names.
    # Common names: 'VH_Germline', 'VL_Germline', 'Heavy_V_Gene', 'Light_V_Gene'
    
    vh_col = None
    vl_col = None
    
    candidates = ['VH_Germline', 'Heavy_V_Gene', 'v_call_heavy', 'VH_V_Gene', 'Best_VH_Germline']
    for c in candidates:
        if c in df.columns:
            vh_col = c
            break
            
    candidates = ['VL_Germline', 'Light_V_Gene', 'v_call_light', 'VL_V_Gene', 'Best_VL_Germline']
    for c in candidates:
        if c in df.columns:
            vl_col = c
            break
            
    if not vh_col or not vl_col:
        print(f"Error: Could not identify VH/VL Germline columns. Available: {df.columns.tolist()}")
        return

    # Clean Germline names (remove alleles like *01 if desired, or keep them)
    # Usually family/gene level is enough (e.g. IGHV3-23).
    # Let's keep full gene name but maybe strip allele for grouping.
    
    df['VH_Gene'] = df[vh_col].astype(str).apply(lambda x: x.split('*')[0] if '*' in x else x)
    df['VL_Gene'] = df[vl_col].astype(str).apply(lambda x: x.split('*')[0] if '*' in x else x)
    
    # Crosstab (Matrix)
    matrix = pd.crosstab(df['VH_Gene'], df['VL_Gene'])
    
    # Save Matrix
    matrix_path = OUT_DIR / "vh_vl_pairing_matrix.csv"
    matrix.to_csv(matrix_path)
    print(f"Saved pairing matrix to {matrix_path}")
    
    # Generate Report
    desc = f"{len(df)} " if use_full_842 else f"{len(df)} "
    suffix = "（842 = 384 natural + 458 engineered）" if use_full_842 else ""
    report_lines = [
        "# VH/VL Germline ",
        "",
        f" {desc} 。{suffix}",
        "",
        "## Top 20  (Golden Pairings)",
        "",
        "| Rank | VH Gene | VL Gene | Count | Frequency |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]
    
    # Flatten and sort
    pairs = matrix.stack().reset_index()
    pairs.columns = ['VH', 'VL', 'Count']
    pairs = pairs.sort_values('Count', ascending=False)
    
    total = len(df)
    for i, row in enumerate(pairs.head(20).itertuples(), 1):
        freq = row.Count / total * 100
        report_lines.append(f"| {i} | **{row.VH}** | **{row.VL}** | {row.Count} | {freq:.1f}% |")
        
    report_lines.append("")
    report_lines.append("## ")
    report_lines.append("，。，。")
    
    report_path = OUT_DIR / "vh_vl_pairing_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"Saved report to {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate VH/VL pairing matrix from clinical antibody germline data.")
    parser.add_argument("--engineered", action="store_true", help="Use only 458 engineered antibodies (default: all 842)")
    args = parser.parse_args()
    generate_pairing_matrix(use_full_842=not args.engineered)
