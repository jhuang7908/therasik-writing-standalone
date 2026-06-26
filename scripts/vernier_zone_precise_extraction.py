#!/usr/bin/env python3
"""
 ANARCII  Vernier Zone 
 IMGT 
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter
from anarcii import Anarcii

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Vernier Zone （ Kabat ）
VERNIER_POSITIONS_VH = {
    'VH_2': 2,
    'VH_27': 27,
    'VH_28': 28,
    'VH_29': 29,
    'VH_30': 30,
    'VH_48': 48,
    'VH_49': 49,
    'VH_67': 67,
    'VH_69': 69,
    'VH_71': 71,  # 
    'VH_73': 73,
    'VH_78': 78,
    'VH_93': 93,
    'VH_94': 94,  #  (Arg)
}

VERNIER_POSITIONS_VL = {
    'VL_2': 2,
    'VL_4': 4,
    'VL_36': 36,
    'VL_46': 46,
    'VL_49': 49,
    'VL_69': 69,
    'VL_71': 71,  # 
    'VL_98': 98,
}


def extract_residue_at_kabat_position(numbering_list, target_position):
    """ ANARCII numbering  Kabat 
    
    Args:
        numbering_list: ANARCII  [((pos, ins), aa), ...]
        target_position:  Kabat （）
    """
    for (pos, ins_code), aa in numbering_list:
        if pos == target_position and ins_code.strip() == '':
            if aa != '-':
                return aa
    return 'X'


def get_vernier_zone_residues(sequence, chain_type='H'):
    """ ANARCII (Kabat scheme)  Vernier Zone """
    vernier_dict = {}
    
    try:
        anarcii = Anarcii()
        #  (IMGT)
        result = anarcii.number([(f'{chain_type}_seq', sequence)])
        #  Kabat 
        result = anarcii.to_scheme('kabat')
        
        if not result or f'{chain_type}_seq' not in result:
            return {k: 'X' for k in (VERNIER_POSITIONS_VH if chain_type == 'H' else VERNIER_POSITIONS_VL).keys()}
        
        data = result[f'{chain_type}_seq']
        numbering = data.get('numbering', [])
        
        if not numbering:
            return {k: 'X' for k in (VERNIER_POSITIONS_VH if chain_type == 'H' else VERNIER_POSITIONS_VL).keys()}
        
        #  Vernier Zone 
        positions = VERNIER_POSITIONS_VH if chain_type == 'H' else VERNIER_POSITIONS_VL
        
        # Kabat numbering 
        for name, kabat_pos in positions.items():
            aa = extract_residue_at_kabat_position(numbering, kabat_pos)
            vernier_dict[name] = aa
        
        return vernier_dict
        
    except Exception as e:
        print(f"Error numbering {chain_type} sequence: {e}")
        return {k: 'X' for k in (VERNIER_POSITIONS_VH if chain_type == 'H' else VERNIER_POSITIONS_VL).keys()}


def get_canonical_class_simple(cdr_seq, cdr_name):
    """ Canonical Class （）"""
    length = len(cdr_seq)
    return f"{cdr_name}-{length}"


def main():
    print("=" * 80)
    print(" ANARCII  Vernier Zone ")
    print("=" * 80)
    print()
    
    # 
    data_path = PROJECT_ROOT / "data/humanization_assay/thera_human_igG_germline_analysis.xlsx"
    df = pd.read_excel(data_path)
    
    #  Engineered 
    engineered = df[df['human_origin_mode'] == 'engineered_humanisation'].copy()
    engineered.reset_index(drop=True, inplace=True)
    print(f"Total Engineered antibodies: {len(engineered)}")
    print()
    
    #  Canonical Classes（）
    print("Step 1:  CDR Canonical Classes ()...")
    engineered['H1_Canonical'] = engineered['VH_CDR1'].apply(lambda x: get_canonical_class_simple(str(x), 'H1'))
    engineered['H2_Canonical'] = engineered['VH_CDR2'].apply(lambda x: get_canonical_class_simple(str(x), 'H2'))
    engineered['H3_Canonical'] = engineered['VH_CDR3'].apply(lambda x: get_canonical_class_simple(str(x), 'H3'))
    engineered['L1_Canonical'] = engineered['VL_CDR1'].apply(lambda x: get_canonical_class_simple(str(x), 'L1'))
    engineered['L2_Canonical'] = engineered['VL_CDR2'].apply(lambda x: get_canonical_class_simple(str(x), 'L2'))
    engineered['L3_Canonical'] = engineered['VL_CDR3'].apply(lambda x: get_canonical_class_simple(str(x), 'L3'))
    print("  ✓ Canonical Classes ")
    print()
    
    #  ANARCII  Vernier Zone
    print("Step 2:  ANARCII  Vernier Zone ...")
    print(f"  : ", end='', flush=True)
    
    vernier_results = []
    
    for idx, row in engineered.iterrows():
        if idx % 50 == 0:
            print(f"{idx}...", end='', flush=True)
        
        #  VH Vernier Zone
        vh_vernier = get_vernier_zone_residues(row['VH'], 'H')
        
        #  VL Vernier Zone
        vl_vernier = get_vernier_zone_residues(row['VL'], 'L')
        
        # 
        vernier_row = {
            'Name': row['Name'],
            **vh_vernier,
            **vl_vernier
        }
        vernier_results.append(vernier_row)
    
    print(" !")
    print()
    
    # 
    vernier_df = pd.DataFrame(vernier_results)
    engineered = engineered.merge(vernier_df, on='Name', how='left')
    
    # 
    print("=" * 80)
    print("Step 3: Vernier Zone ")
    print("=" * 80)
    print()
    
    print(" Vernier Zone :")
    print("-" * 40)
    for key_pos in ['VH_71', 'VH_94', 'VH_49', 'VL_71', 'VL_49']:
        dist = engineered[key_pos].value_counts()
        valid_count = (engineered[key_pos] != 'X').sum()
        print(f"{key_pos}: {dict(dist.head(5))} (: {valid_count}/{len(engineered)})")
    
    print()
    print("=" * 80)
    print("Step 4: Germline × Canonical Class × Vernier Zone ")
    print("=" * 80)
    print()
    
    #  Top 3 Germline
    top_germlines = engineered['Best_VH_Germline'].value_counts().head(3)
    
    for germline, count in top_germlines.items():
        subset = engineered[engineered['Best_VH_Germline'] == germline]
        print(f"\n{germline} (n={count}):")
        
        #  H2 Canonical × VH 71
        for canonical in subset['H2_Canonical'].value_counts().head(3).index:
            sub = subset[subset['H2_Canonical'] == canonical]
            vh71_dist = sub['VH_71'].value_counts()
            if len(sub) >= 3:
                print(f"  {canonical}: VH 71 = {dict(vh71_dist.head(3))}")
    
    # 
    output_path = PROJECT_ROOT / "data/humanization_assay/vernier_zone_precise.xlsx"
    engineered.to_excel(output_path, index=False)
    print()
    print(f": {output_path}")
    
    # 
    summary_path = PROJECT_ROOT / "data/humanization_assay/vernier_zone_summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Vernier Zone \n")
        f.write("=" * 80 + "\n\n")
        
        f.write("1. \n")
        f.write("-" * 40 + "\n")
        for pos in ['VH_71', 'VH_94', 'VH_49', 'VL_71', 'VL_49']:
            valid = (engineered[pos] != 'X').sum()
            f.write(f"{pos}: {valid}/{len(engineered)} ({100*valid/len(engineered):.1f}%)\n")
        
        f.write("\n2. \n")
        f.write("-" * 40 + "\n")
        for pos in ['VH_71', 'VH_94', 'VH_49', 'VL_71', 'VL_49']:
            dist = engineered[pos].value_counts().to_dict()
            f.write(f"{pos}: {dist}\n")
    
    print(f": {summary_path}")
    print()
    print("=" * 80)
    print("!")
    print("=" * 80)


if __name__ == "__main__":
    main()
