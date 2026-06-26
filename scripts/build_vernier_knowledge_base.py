#!/usr/bin/env python3
"""
 Vernier Zone  (Knowledge Base)
： + IGHV Germline + CDR Canonical Class + Vernier Zone Profile
"""

import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def classify_target(target):
    """ ()"""
    if pd.isna(target):
        return "Other"
    t = str(target).upper()
    if any(x in t for x in ['PD1', 'PDL1', 'CTLA', 'LAG3', 'TIGIT', 'TIM3']):
        return "Checkpoint"
    elif any(x in t for x in ['HER2', 'EGFR', 'CD20', 'CD19', 'BCMA', 'CLDN']):
        return "Tumor_Marker"
    elif any(x in t for x in ['TNF', 'IL', 'CXCL', 'VEGF', 'ANG', 'BLYS']):
        return "Cytokine/Factor"
    elif any(x in t for x in ['VIRUS', 'COV', 'HIV', 'RSV']):
        return "Viral"
    else:
        return "Other"

def main():
    print("=" * 80)
    print(" Vernier Zone ")
    print("=" * 80)
    
    # 1.  Vernier 
    data_path = PROJECT_ROOT / "data/humanization_assay/vernier_zone_precise.xlsx"
    if not data_path.exists():
        print(f"Error: {data_path} not found.")
        return
        
    df = pd.read_excel(data_path)
    
    # 2. 
    df['Target_Category'] = df['targets_meta'].apply(classify_target)
    
    # 
    main_vernier_pos = ['VH_2', 'VH_27', 'VH_28', 'VH_29', 'VH_30', 'VH_48', 'VH_49', 'VH_67', 'VH_69', 'VH_71', 'VH_73', 'VH_78', 'VH_93', 'VH_94', 'VL_2', 'VL_4', 'VL_36', 'VL_46', 'VL_49', 'VL_69', 'VL_71', 'VL_98']
    
    # 3. 
    # 
    #  [Target_Category, Best_VH_Germline, H2_Canonical] 
    kb_records = []
    
    # 
    group_cols = ['Target_Category', 'Best_VH_Germline', 'H2_Canonical']
    groups = df.groupby(group_cols)
    
    print(f" {len(groups)} ...")
    
    for (target_cat, vh_germ, h2_canon), subset in groups:
        if len(subset) < 2: # ，
            continue
            
        record = {
            'Target_Category': target_cat,
            'VH_Germline': vh_germ,
            'H2_Canonical': h2_canon,
            'Sample_Size': len(subset)
        }
        
        # 
        for pos in main_vernier_pos:
            if pos in subset.columns:
                counts = subset[pos].value_counts()
                top_aa = counts.index[0] if not counts.empty else 'X'
                top_freq = counts.iloc[0] / len(subset) if not counts.empty else 0
                
                # 
                dist_str = ", ".join([f"{aa}:{count}" for aa, count in counts.items()])
                
                record[f"{pos}_Top"] = top_aa
                record[f"{pos}_Freq"] = f"{top_freq:.1%}"
                record[f"{pos}_Distribution"] = dist_str
        
        kb_records.append(record)
    
    kb_df = pd.DataFrame(kb_records)
    
    # 4. 
    output_path = PROJECT_ROOT / "data/humanization_assay/antibody_vernier_knowledge_base.xlsx"
    
    #  Excel ，
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        # ：
        kb_df.to_excel(writer, sheet_name='Vernier_Mapping', index=False)
        
        # ： IGHV3-30 
        v3_30 = kb_df[kb_df['VH_Germline'].str.contains('IGHV3-30', na=False)]
        v3_30.to_excel(writer, sheet_name='IGHV3-30_Plasticity', index=False)
        
        # 
        workbook  = writer.book
        worksheet = writer.sheets['Vernier_Mapping']
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
        for col_num, value in enumerate(kb_df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
    print(f": {output_path}")
    print()
    print("=" * 80)
    print(" (Top 5 ):")
    print(kb_df[['Target_Category', 'VH_Germline', 'H2_Canonical', 'Sample_Size', 'VH_71_Top', 'VH_71_Distribution']].head(5))

if __name__ == "__main__":
    main()
