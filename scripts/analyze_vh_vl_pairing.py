#!/usr/bin/env python3
"""
 (VH/VL) 
 (Natural)  (Engineered) 
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def get_family(germline):
    """ Germline ， IGHV3-23*01 -> IGHV3"""
    if pd.isna(germline) or str(germline) == 'None':
        return "Unknown"
    return str(germline).split('-')[0].split('*')[0]

def main():
    print("=" * 80)
    print(" VH/VL ")
    print("=" * 80)
    
    # 1. 
    data_path = PROJECT_ROOT / "data/humanization_assay/thera_human_igG_germline_analysis.xlsx"
    df = pd.read_excel(data_path)
    
    # 
    report_path = PROJECT_ROOT / "data/humanization_assay/pairing_results.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("VH/VL \n")
        f.write("=" * 60 + "\n")
    
    # 2. 
    df['VH_Family'] = df['Best_VH_Germline'].apply(get_family)
    df['VL_Family'] = df['Best_VL_Germline'].apply(get_family)
    
    # 3. ：Natural vs Engineered
    for mode in ['natural_human_repertoire', 'engineered_humanisation']:
        subset = df[df['human_origin_mode'] == mode]
        mode_label = " (Natural)" if "natural" in mode else " (Engineered)"
        
        print(f"\n>>> : {mode_label} (n={len(subset)})")
        with open(report_path, 'a', encoding='utf-8') as f:
            f.write(f"\n>>> : {mode_label} (n={len(subset)})\n")
        
        # 
        pairing = pd.crosstab(subset['VH_Family'], subset['VL_Family'], normalize='all') * 100
        
        #  Top 5 
        flat_pairing = pd.crosstab(subset['VH_Family'], subset['VL_Family']).stack().sort_values(ascending=False).head(5)
        print("\nTop 5  (VH + VL):")
        with open(report_path, 'a', encoding='utf-8') as f:
            f.write("\nTop 5  (VH + VL):\n")
        
        for (vh, vl), count in flat_pairing.items():
            line = f"  - {vh} + {vl}: {count}  ({count/len(subset)*100:.1f}%)"
            print(line)
            with open(report_path, 'a', encoding='utf-8') as f:
                f.write(line + "\n")
            
        #  Germline 
        germline_pairing = pd.crosstab(subset['Best_VH_Germline'], subset['Best_VL_Germline']).stack().sort_values(ascending=False).head(5)
        print("\nTop 5  Germline :")
        with open(report_path, 'a', encoding='utf-8') as f:
            f.write("\nTop 5  Germline :\n")
        
        for (vh, vl), count in germline_pairing.items():
            line = f"  - {vh} + {vl}: {count} "
            print(line)
            with open(report_path, 'a', encoding='utf-8') as f:
                f.write(line + "\n")

        #  Heatmap
        plt.figure(figsize=(10, 8))
        sns.heatmap(pairing, annot=True, fmt=".1f", cmap="YlGnBu")
        plt.title(f"VH/VL Family Pairing Probability (%) - {mode_label}")
        plt.xlabel("VL Family")
        plt.ylabel("VH Family")
        plt.tight_layout()
        
        img_name = f"vh_vl_pairing_{mode.split('_')[0]}.png"
        plt.savefig(PROJECT_ROOT / "data/humanization_assay" / img_name)
        print(f"  []: {img_name}")
        plt.close()

    # 4.  ( IGHV3 )
    print("\n" + "=" * 80)
    print(":")
    v3_kappa = df[(df['VH_Family'] == 'IGHV3') & (df['VL_Family'].str.startswith('IGKV'))]
    v3_lambda = df[(df['VH_Family'] == 'IGHV3') & (df['VL_Family'].str.startswith('IGLV'))]
    print(f"IGHV3 : {len(df[df['VH_Family'] == 'IGHV3'])}")
    print(f"  -  Kappa: {len(v3_kappa)} ({len(v3_kappa)/len(df[df['VH_Family'] == 'IGHV3'])*100:.1f}%)")
    print(f"  -  Lambda: {len(v3_lambda)} ({len(v3_lambda)/len(df[df['VH_Family'] == 'IGHV3'])*100:.1f}%)")

if __name__ == "__main__":
    main()
