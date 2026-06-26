#!/usr/bin/env python3
"""
 Vernier Zone Tier 
 Tier 
"""

import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

#  Tier  ( vernier_zone_weights.md)
TIERS = {
    'Tier 1 (Critical)': ['VH_71', 'VH_94', 'VL_71', 'VL_49'],
    'Tier 2 (Major)': ['VH_27', 'VH_28', 'VH_29', 'VH_30', 'VH_48', 'VH_93', 'VL_2', 'VL_4', 'VL_36', 'VL_46'],
    'Tier 3 (Minor)': ['VH_2', 'VH_49', 'VH_67', 'VH_69', 'VH_73', 'VH_78', 'VL_69', 'VL_98']
}

def main():
    data_path = PROJECT_ROOT / "data/humanization_assay/vernier_zone_precise.xlsx"
    df = pd.read_excel(data_path)
    
    #  'X' ()
    df = df.replace('X', np.nan)
    
    results = []
    
    for tier_name, positions in TIERS.items():
        for pos in positions:
            if pos in df.columns:
                #  (Unique AA counts)
                unique_aa = df[pos].dropna().nunique()
                #  Top 1  ()
                counts = df[pos].value_counts()
                top_freq = counts.iloc[0] / counts.sum() if not counts.empty else 0
                
                results.append({
                    'Tier': tier_name,
                    'Position': pos,
                    'Unique_AA': unique_aa,
                    'Conservation': top_freq,
                    'Top_AA': counts.index[0] if not counts.empty else 'N/A'
                })
    
    res_df = pd.DataFrame(results)
    
    #  Tier 
    summary = res_df.groupby('Tier').agg({
        'Unique_AA': 'mean',
        'Conservation': 'mean'
    }).round(3)
    
    print("="*60)
    print("Vernier Zone Tier ")
    print("="*60)
    print(summary)
    print("\n:")
    print(res_df.sort_values(['Tier', 'Conservation'], ascending=[True, False]))
    
    # 
    res_df.to_excel(PROJECT_ROOT / "data/humanization_assay/vernier_tier_validation.xlsx", index=False)

if __name__ == "__main__":
    main()
