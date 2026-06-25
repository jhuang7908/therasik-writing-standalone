#!/usr/bin/env python3
"""
 VH (Heavy Chain)  VL (Light Chain) 
 Natural vs Engineered 
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def get_family(germline):
    if pd.isna(germline) or str(germline) == 'None':
        return "Unknown"
    return str(germline).split('-')[0].split('*')[0]

def main():
    print("=" * 80)
    print(" VH  VL ")
    print("=" * 80)
    
    # 1. 
    data_path = PROJECT_ROOT / "data/humanization_assay/thera_human_igG_germline_analysis.xlsx"
    df = pd.read_excel(data_path)
    
    # 2. 
    df['VH_Family'] = df['Best_VH_Germline'].apply(get_family)
    df['VL_Family'] = df['Best_VL_Germline'].apply(get_family)
    
    output_excel = PROJECT_ROOT / "data/humanization_assay/vh_vl_pairing_detailed.xlsx"
    writer = pd.ExcelWriter(output_excel, engine='xlsxwriter')
    
    #  Natural  Engineered
    for mode in ['natural_human_repertoire', 'engineered_humanisation']:
        subset = df[df['human_origin_mode'] == mode]
        mode_label = "Natural" if "natural" in mode else "Engineered"
        
        print(f"\n>>>  {mode_label}  (n={len(subset)})")
        
        # A. VH Family -> VL Family 
        vh_fam_vl_fam = pd.crosstab(subset['VH_Family'], subset['VL_Family'], normalize='index') * 100
        vh_fam_vl_fam.to_excel(writer, sheet_name=f'{mode_label}_Fam_Mapping')
        
        # B.  VH Germline -> VL Family  ( VH)
        vh_counts = subset['Best_VH_Germline'].value_counts()
        top_vh = vh_counts[vh_counts >= 5].index.tolist()
        
        detail_records = []
        for vh in top_vh:
            vh_sub = subset[subset['Best_VH_Germline'] == vh]
            vl_dist = vh_sub['VL_Family'].value_counts(normalize=True) * 100
            
            record = {'VH_Germline': vh, 'Total_Samples': len(vh_sub)}
            for vl_fam, perc in vl_dist.items():
                record[vl_fam] = f"{perc:.1f}%"
            detail_records.append(record)
            
        detailed_df = pd.DataFrame(detail_records).fillna('0.0%')
        detailed_df.to_excel(writer, sheet_name=f'{mode_label}_VH_to_VL_Fam', index=False)
        
        # C. ：Top 10 VH  VL Family  ()
        if len(top_vh) > 0:
            top_10 = vh_counts.head(10).index
            plot_df = pd.crosstab(subset[subset['Best_VH_Germline'].isin(top_10)]['Best_VH_Germline'], 
                                 subset['VL_Family'], normalize='index') * 100
            
            plt.figure(figsize=(12, 6))
            plot_df.plot(kind='bar', stacked=True, colormap='tab20')
            plt.title(f"VL Family Distribution per Top VH Germline ({mode_label})")
            plt.ylabel("Percentage (%)")
            plt.xlabel("VH Germline")
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title="VL Family")
            plt.tight_layout()
            
            img_name = f"vl_dist_per_vh_{mode_label.lower()}.png"
            plt.savefig(PROJECT_ROOT / "data/humanization_assay" / img_name)
            plt.savefig(Path(r"C:\Users\NextVivo\.gemini\antigravity\brain\328e287e-c9ab-48fa-8799-4534421dcf87") / img_name)
            plt.close()

    writer.close()
    print(f"\n Excel : {output_excel}")
    print(" artifacts 。")

if __name__ == "__main__":
    main()
