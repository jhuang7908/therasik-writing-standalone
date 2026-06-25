#!/usr/bin/env python3
"""
Vernier Zone 
、CDRVernier Zone
"""

import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def classify_target(target):
    """"""
    if pd.isna(target):
        return "Other"
    t = str(target).upper()
    if any(x in t for x in ['PD1', 'PDL1', 'CTLA', 'LAG3', 'TIGIT', 'TIM3']):
        return "Checkpoint"
    elif any(x in t for x in ['HER2', 'EGFR', 'CD20', 'CD19', 'BCMA', 'CLDN']):
        return "Tumor_Marker"
    elif any(x in t for x in ['TNF', 'IL', 'CXCL', 'VEGF', 'ANG']):
        return "Cytokine/Factor"
    elif any(x in t for x in ['VIRUS', 'COV', 'HIV', 'RSV']):
        return "Viral"
    else:
        return "Other"

def analyze_distribution(df, group_cols, value_col):
    """"""
    #  'X' ()
    df_valid = df[df[value_col] != 'X']
    
    # 
    counts = df_valid.groupby(group_cols)[value_col].value_counts().unstack(fill_value=0)
    
    # 
    counts['Total'] = counts.sum(axis=1)
    
    #  >= 3 
    counts = counts[counts['Total'] >= 3]
    
    #  (，)
    return counts

def main():
    print("=" * 80)
    print("Vernier Zone ")
    print("=" * 80)
    
    # 
    input_path = PROJECT_ROOT / "data/humanization_assay/vernier_zone_precise.xlsx"
    df = pd.read_excel(input_path)
    
    # 
    df['Target_Category'] = df['targets_meta'].apply(classify_target)
    
    # 
    required_cols = ['Best_VH_Germline', 'H2_Canonical', 'Target_Category', 'VH_71', 'VH_94']
    for col in required_cols:
        if col not in df.columns:
            print(f"Error: Missing column {col}")
            # 
            if col == 'Best_VH_Germline' and 'VH_germline' in df.columns:
                df['Best_VH_Germline'] = df['VH_germline']
    
    excel_writer = pd.ExcelWriter(PROJECT_ROOT / "data/humanization_assay/vernier_zone_analysis_report.xlsx", engine='xlsxwriter')
    
    #  1: Germline × H2 Canonical → VH 71
    print("\n 1: Germline × H2 Canonical → VH 71")
    table1 = analyze_distribution(df, ['Best_VH_Germline', 'H2_Canonical'], 'VH_71')
    table1.to_excel(excel_writer, sheet_name='Germline_H2_VH71')
    
    #  (Main Germlines)
    top_germlines = df['Best_VH_Germline'].value_counts().head(5).index
    print(f"Top Germlines: {list(top_germlines)}")
    
    #  2: Target Category × Germline → VH 71
    print("\n 2: Target Category × Germline → VH 71")
    table2 = analyze_distribution(df, ['Target_Category', 'Best_VH_Germline'], 'VH_71')
    table2.to_excel(excel_writer, sheet_name='Target_Germline_VH71')
    
    #  3: Germline × VH 94 ()
    print("\n 3: Germline → VH 94")
    table3 = analyze_distribution(df, ['Best_VH_Germline'], 'VH_94')
    table3.to_excel(excel_writer, sheet_name='Germline_VH94')
    
    #  4: Target × H2 Canonical → VH 71 ( Germline)
    print("\n 4: Target × H2 Canonical → VH 71")
    table4 = analyze_distribution(df, ['Target_Category', 'H2_Canonical'], 'VH_71')
    table4.to_excel(excel_writer, sheet_name='Target_H2_VH71')
    
    excel_writer.close()
    print(f"\n: {PROJECT_ROOT}/data/humanization_assay/vernier_zone_analysis_report.xlsx")
    
    # 
    summary_path = PROJECT_ROOT / "data/humanization_assay/vernier_analysis_summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("Vernier Zone \n")
        f.write("="*40 + "\n\n")
        
        # 1. VH 71  Top Germlines 
        f.write("1. VH 71 (H2 Canonical Determinant) :\n")
        f.write("-"*40 + "\n")
        for germline in top_germlines:
            sub = df[df['Best_VH_Germline'] == germline]
            if len(sub) > 0:
                dist = sub['VH_71'].value_counts().to_dict()
                top_aa = max(dist, key=dist.get)
                pct = dist[top_aa] / len(sub) * 100
                f.write(f"- {germline}:  {top_aa} ({pct:.1f}%), : {dist}\n")
                
                #  Canonical Class 
                for canon in sub['H2_Canonical'].unique():
                    sub_c = sub[sub['H2_Canonical'] == canon]
                    if len(sub_c) >= 5:
                        d = sub_c['VH_71'].value_counts().to_dict()
                        f.write(f"  * {canon}: {d}\n")
            f.write("\n")
            
        # 2. VH 94 (H3 Salt Bridge)
        f.write("2. VH 94 (H3 Salt Bridge Base):\n")
        f.write("-"*40 + "\n")
        r_count = (df['VH_94'] == 'R').sum()
        f.write(f"Arg (R) : {r_count}/{len(df)} ({r_count/len(df)*100:.1f}%)\n")
        
        #  R 
        non_r = df[df['VH_94'] != 'R']['VH_94'].value_counts().head(3).to_dict()
        f.write(f" R : {non_r}\n\n")
        
        # 3. Target Specific Preferences
        f.write("3.  (Target Specific Preferences):\n")
        f.write("-"*40 + "\n")
        for cat in ['Checkpoint', 'Tumor_Marker', 'Cytokine/Factor']:
            sub = df[df['Target_Category'] == cat]
            if len(sub) > 10:
                # Top Germline
                top_g = sub['Best_VH_Germline'].value_counts().head(1).index[0]
                # Top VH 71
                top_v71 = sub['VH_71'].value_counts().head(1).index[0]
                f.write(f"- {cat}:  {top_g}, VH 71  {top_v71}\n")

    print(f": {summary_path}")

if __name__ == "__main__":
    main()
