#!/usr/bin/env python3
"""
Canonical Class + Vernier Zone 
 Engineered  CDR Canonical Classes  Vernier Zone 
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ============================================================================
# Canonical Class  ( Chothia 1987, 1989)
# ============================================================================

def get_canonical_class_H1(cdr_seq, fr1_seq):
    """ CDR-H1  Canonical Class
    
    ：
    1. CDR-H1 
    2. FR1 26 (Kabat ， IMGT 26)
    """
    length = len(cdr_seq)
    
    #  FR1 26（IMGT， FR1 ）
    # ： FR1 ，5
    if len(fr1_seq) >= 5:
        pos_26 = fr1_seq[-5]
    else:
        pos_26 = 'X'
    
    # Canonical Class （）
    if length == 13:
        return "H1-13-1"  # 
    elif length == 10:
        return "H1-10-1"
    elif length == 11:
        return "H1-11-1"
    elif length == 12:
        return "H1-12-1"
    else:
        return f"H1-{length}-?"


def get_canonical_class_H2(cdr_seq, vh_71):
    """ CDR-H2  Canonical Class
    
    ：VH 71 （Kabat = IMGT 80）
    """
    length = len(cdr_seq)
    
    # Canonical Class （）
    if length == 10:
        if vh_71 in ['A', 'V']:
            return "H2-10-1"  # 
        else:
            return "H2-10-2"
    elif length == 9:
        return "H2-9-1"
    elif length == 12:
        return "H2-12-1"
    else:
        return f"H2-{length}-?"


def get_canonical_class_L1(cdr_seq):
    """ CDR-L1  Canonical Class
    
    
    """
    length = len(cdr_seq)
    
    if length == 11:
        return "L1-11-1"  # kappa 
    elif length == 12:
        return "L1-12-1"
    elif length == 13:
        return "L1-13-1"  # lambda 
    elif length == 10:
        return "L1-10-1"
    else:
        return f"L1-{length}-?"


def get_canonical_class_L2(cdr_seq):
    """ CDR-L2  Canonical Class
    
    L2 
    """
    length = len(cdr_seq)
    
    if length == 7:
        return "L2-7-1"  # 
    elif length == 8:
        return "L2-8-1"
    else:
        return f"L2-{length}-?"


def get_canonical_class_L3(cdr_seq):
    """ CDR-L3  Canonical Class
    
    
    """
    length = len(cdr_seq)
    
    if length == 9:
        return "L3-9-1"  # 
    elif length == 10:
        return "L3-10-1"
    elif length == 11:
        return "L3-11-1"
    elif length == 8:
        return "L3-8-1"
    else:
        return f"L3-{length}-?"


# ============================================================================
# Vernier Zone （ IMGT ， FR ）
# ============================================================================

def extract_vernier_positions_vh(row):
    """ VH  FR  Vernier Zone 
    
    IMGT ：
    - VH 2: FR1 2
    - VH 27-30: FR1 4（CDR1）
    - VH 48, 49: FR2
    - VH 67, 69, 71: FR3（IMGT 76, 78, 80）
    - VH 73, 78: FR3（IMGT 82, 91)
    - VH 93, 94: FR3 （IMGT 103, 104）
    """
    vernier = {}
    
    fr1 = str(row.get('VH_FR1', ''))
    fr2 = str(row.get('VH_FR2', ''))
    fr3 = str(row.get('VH_FR3', ''))
    
    # FR1: IMGT 1-26
    if len(fr1) >= 2:
        vernier['VH_2'] = fr1[1]  # IMGT 2
    if len(fr1) >= 4:
        # IMGT 27-30  FR1  CDR1 
        vernier['VH_27'] = fr1[-4] if len(fr1) >= 4 else 'X'
        vernier['VH_28'] = fr1[-3] if len(fr1) >= 3 else 'X'
        vernier['VH_29'] = fr1[-2] if len(fr1) >= 2 else 'X'
        vernier['VH_30'] = fr1[-1] if len(fr1) >= 1 else 'X'
    
    # FR2: IMGT 39-55
    # Kabat 48 ≈ IMGT 53, Kabat 49 ≈ IMGT 54
    if len(fr2) >= 15:
        vernier['VH_48'] = fr2[13] if len(fr2) > 13 else 'X'  # 
        vernier['VH_49'] = fr2[14] if len(fr2) > 14 else 'X'
    
    # FR3: IMGT 66-104
    # Kabat 67 ≈ IMGT 76, Kabat 69 ≈ IMGT 78, Kabat 71 ≈ IMGT 80
    # Kabat 73 ≈ IMGT 82, Kabat 78 ≈ IMGT 91
    # Kabat 93 ≈ IMGT 103, Kabat 94 ≈ IMGT 104
    if len(fr3) >= 39:
        vernier['VH_71'] = fr3[14] if len(fr3) > 14 else 'X'  # IMGT 80 ≈ FR3[14]
        vernier['VH_94'] = fr3[-1] if len(fr3) >= 1 else 'X'  # IMGT 104  FR3 
    
    return vernier


def extract_vernier_positions_vl(row):
    """ VL  FR  Vernier Zone 
    
    IMGT ：
    - VL 2, 4: FR1
    - VL 36: FR2（IMGT 42）
    - VL 46, 49: FR2（IMGT 51, 54）
    - VL 69, 71: FR3（IMGT 78, 80）
    - VL 98: FR4（IMGT 118）
    """
    vernier = {}
    
    fr1 = str(row.get('VL_FR1', ''))
    fr2 = str(row.get('VL_FR2', ''))
    fr3 = str(row.get('VL_FR3', ''))
    fr4 = str(row.get('VL_FR4', ''))
    
    # FR1: IMGT 1-26
    if len(fr1) >= 4:
        vernier['VL_2'] = fr1[1]  # IMGT 2
        vernier['VL_4'] = fr1[3]  # IMGT 4
    
    # FR2: IMGT 39-55
    if len(fr2) >= 16:
        vernier['VL_36'] = fr2[3] if len(fr2) > 3 else 'X'  # 
        vernier['VL_46'] = fr2[11] if len(fr2) > 11 else 'X'
        vernier['VL_49'] = fr2[14] if len(fr2) > 14 else 'X'
    
    # FR3: IMGT 66-104
    if len(fr3) >= 20:
        vernier['VL_71'] = fr3[14] if len(fr3) > 14 else 'X'  # IMGT 80
    
    # FR4: IMGT 105-128
    if len(fr4) >= 1:
        vernier['VL_98'] = fr4[0]  # IMGT 118  FR4 
    
    return vernier


# ============================================================================
# 
# ============================================================================

def main():
    print("=" * 80)
    print("Canonical Class + Vernier Zone ")
    print("=" * 80)
    print()
    
    # （ Germline ）
    data_path = PROJECT_ROOT / "data/humanization_assay/thera_human_igG_germline_analysis.xlsx"
    df = pd.read_excel(data_path)
    
    #  Engineered 
    engineered = df[df['human_origin_mode'] == 'engineered_humanisation'].copy()
    print(f"Total Engineered antibodies: {len(engineered)}")
    print()
    
    #  Canonical Classes
    print("Step 1:  CDR Canonical Classes...")
    
    def safe_get_canonical_h1(row):
        try:
            return get_canonical_class_H1(row['VH_CDR1'], row['VH_FR1'])
        except:
            return "Unknown"
    
    def safe_get_canonical_h2(row):
        try:
            vernier = extract_vernier_positions_vh(row)
            vh_71 = vernier.get('VH_71', 'X')
            return get_canonical_class_H2(row['VH_CDR2'], vh_71)
        except:
            return "Unknown"
    
    engineered['H1_Canonical'] = engineered.apply(safe_get_canonical_h1, axis=1)
    engineered['H2_Canonical'] = engineered.apply(safe_get_canonical_h2, axis=1)
    engineered['L1_Canonical'] = engineered['VL_CDR1'].apply(lambda x: get_canonical_class_L1(str(x)))
    engineered['L2_Canonical'] = engineered['VL_CDR2'].apply(lambda x: get_canonical_class_L2(str(x)))
    engineered['L3_Canonical'] = engineered['VL_CDR3'].apply(lambda x: get_canonical_class_L3(str(x)))
    
    print(f"  H1 Canonical Classes identified: {engineered['H1_Canonical'].nunique()}")
    print(f"  H2 Canonical Classes identified: {engineered['H2_Canonical'].nunique()}")
    print()
    
    #  Vernier Zone 
    print("Step 2:  Vernier Zone ...")
    
    vh_vernier_list = []
    vl_vernier_list = []
    
    for idx, row in engineered.iterrows():
        vh_v = extract_vernier_positions_vh(row)
        vl_v = extract_vernier_positions_vl(row)
        vh_v['Name'] = row['Name']
        vl_v['Name'] = row['Name']
        vh_vernier_list.append(vh_v)
        vl_vernier_list.append(vl_v)
    
    vh_vernier_df = pd.DataFrame(vh_vernier_list)
    vl_vernier_df = pd.DataFrame(vl_vernier_list)
    
    # 
    engineered = engineered.merge(vh_vernier_df, on='Name', how='left')
    engineered = engineered.merge(vl_vernier_df, on='Name', how='left')
    
    print(f"  Vernier Zone ")
    print()
    
    # 
    print("Step 3: ...")
    print()
    
    #  1：Germline × Canonical Class → Vernier Zone 
    print("=" * 80)
    print(" 1: IGHV Germline × H2 Canonical Class → VH 71 ")
    print("=" * 80)
    
    top_vh_germlines = engineered['Best_VH_Germline'].value_counts().head(5).index
    
    for germline in top_vh_germlines:
        subset = engineered[engineered['Best_VH_Germline'] == germline]
        print(f"\n{germline} (n={len(subset)}):")
        
        for canonical in subset['H2_Canonical'].unique():
            sub = subset[subset['H2_Canonical'] == canonical]
            if len(sub) >= 3:  # 3
                vh71_dist = sub['VH_71'].value_counts()
                print(f"  {canonical}: {dict(vh71_dist.head(3))}")
    
    print()
    print("=" * 80)
    print(" 2: Target Category × Germline → Vernier Zone")
    print("=" * 80)
    
    # 
    def classify_target_simple(target):
        if pd.isna(target):
            return "Other"
        t = str(target).upper()
        if any(x in t for x in ['PD1', 'PDL1', 'CTLA', 'LAG3']):
            return "Checkpoint"
        elif any(x in t for x in ['HER2', 'EGFR', 'CD20']):
            return "Tumor_Marker"
        elif any(x in t for x in ['TNF', 'IL', 'CXCL']):
            return "Cytokine"
        else:
            return "Other"
    
    engineered['Target_Category'] = engineered['targets_meta'].apply(classify_target_simple)
    
    for category in ['Checkpoint', 'Tumor_Marker', 'Cytokine']:
        subset = engineered[engineered['Target_Category'] == category]
        if len(subset) >= 10:
            print(f"\n{category} (n={len(subset)}):")
            top_germline = subset['Best_VH_Germline'].value_counts().head(1).index[0]
            sub = subset[subset['Best_VH_Germline'] == top_germline]
            vh71_dist = sub['VH_71'].value_counts()
            vh94_dist = sub['VH_94'].value_counts()
            print(f"  Top VH Germline: {top_germline}")
            print(f"  VH 71: {dict(vh71_dist.head(3))}")
            print(f"  VH 94: {dict(vh94_dist.head(3))}")
    
    # 
    output_path = PROJECT_ROOT / "data/humanization_assay/canonical_vernier_analysis.xlsx"
    engineered.to_excel(output_path, index=False)
    print()
    print(f": {output_path}")
    print()
    
    # 
    summary_path = PROJECT_ROOT / "data/humanization_assay/canonical_vernier_summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Canonical Class + Vernier Zone \n")
        f.write("=" * 80 + "\n\n")
        
        f.write("1. Canonical Class \n")
        f.write("-" * 40 + "\n")
        f.write(f"H1 Classes: {engineered['H1_Canonical'].value_counts().to_dict()}\n\n")
        f.write(f"H2 Classes: {engineered['H2_Canonical'].value_counts().to_dict()}\n\n")
        f.write(f"L1 Classes: {engineered['L1_Canonical'].value_counts().to_dict()}\n\n")
        
        f.write("\n2.  Vernier Zone \n")
        f.write("-" * 40 + "\n")
        f.write(f"VH 71: {engineered['VH_71'].value_counts().to_dict()}\n")
        f.write(f"VH 94: {engineered['VH_94'].value_counts().to_dict()}\n")
        f.write(f"VL 71: {engineered['VL_71'].value_counts().to_dict()}\n")
    
    print(f": {summary_path}")


if __name__ == "__main__":
    main()
