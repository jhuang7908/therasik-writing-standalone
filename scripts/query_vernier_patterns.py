#!/usr/bin/env python3
"""
Vernier Zone 
， Germline  Vernier 。
"""

import pandas as pd
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def query_patterns(germline=None, target=None):
    kb_path = PROJECT_ROOT / "data/humanization_assay/antibody_vernier_knowledge_base.xlsx"
    if not kb_path.exists():
        print(": ， build_vernier_knowledge_base.py")
        return

    df = pd.read_excel(kb_path, sheet_name='Vernier_Mapping')
    
    # 
    results = df.copy()
    if germline:
        results = results[results['VH_Germline'].str.contains(germline, case=False, na=False)]
    if target:
        results = results[results['Target_Category'].str.contains(target, case=False, na=False)]
        
    if results.empty:
        print(f" (Germline: {germline}, Target: {target})")
        return

    print(f"\n {len(results)} :\n")
    for _, row in results.iterrows():
        print("-" * 60)
        print(f": {row['Target_Category']}")
        print(f"VH :  {row['VH_Germline']}")
        print(f"H2 :  {row['H2_Canonical']}")
        print(f":   {row['Sample_Size']}")
        print("-" * 20)
        print(f" (Top Residues):")
        print(f"  VH 71 (H2 Det): {row.get('VH_71_Top', 'X')} (: {row.get('VH_71_Freq', '0%')})")
        print(f"  VH 94 (Bridge): {row.get('VH_94_Top', 'X')} (: {row.get('VH_94_Freq', '0%')})")
        print(f"  VH 49:          {row.get('VH_49_Top', 'X')} (: {row.get('VH_49_Freq', '0%')})")
        print(f"  VL 71:          {row.get('VL_71_Top', 'X')} (: {row.get('VL_71_Freq', '0%')})")
        print(f"\n:")
        print(f"  VH 71 : {row.get('VH_71_Distribution', 'N/A')}")
        print(f"  VH 94 : {row.get('VH_94_Distribution', 'N/A')}")
        print(f"  VL 71 : {row.get('VL_71_Distribution', 'N/A')}")
        print("\n")

def main():
    parser = argparse.ArgumentParser(description="Vernier Zone ")
    parser.add_argument("--germline", type=str, help=" ( IGHV3-30)")
    parser.add_argument("--target", type=str, help=" ( Checkpoint, Tumor_Marker)")
    
    args = parser.parse_args()
    
    if not args.germline and not args.target:
        print(": --germline <name>  --target <name>")
        print(": python query_vernier_patterns.py --germline IGHV3-30 --target Checkpoint")
        return
        
    query_patterns(args.germline, args.target)

if __name__ == "__main__":
    main()
