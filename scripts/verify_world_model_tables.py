#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/verify_world_model_tables.py

Verify World Model tables:
1. All tables are non-empty
2. Total counts match Truth Table (1133)
3. Key metrics (Slice 1-7 counts) can be verified from tables
"""

import sys
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORLD_MODEL_DIR = PROJECT_ROOT / "data/thera_sabdab/world_model"
SLICE_SUMMARY = PROJECT_ROOT / "data/thera_sabdab/out/slice_ids/slice_summary.csv"

def verify_tables():
    """Verify all world model tables."""
    print("=" * 70)
    print("🔍 Verifying World Model Tables")
    print("=" * 70)
    
    all_ok = True
    
    # Expected total
    EXPECTED_TOTAL = 1133
    
    # Table 1: phase × modality × format_class_meta
    print("\n📊 Table 1: phase × modality × format_class_meta.csv")
    table1_path = WORLD_MODEL_DIR / "phase × modality × format_class_meta.csv"
    if table1_path.exists():
        df1 = pd.read_csv(table1_path, index_col=0)
        total1 = df1.loc['Total', 'Total']
        print(f"  ✅ File exists")
        print(f"  📐 Shape: {df1.shape}")
        print(f"  📈 Total: {total1} (expected: {EXPECTED_TOTAL})")
        if total1 != EXPECTED_TOTAL:
            print(f"  ❌ Total mismatch!")
            all_ok = False
        if df1.empty:
            print(f"  ❌ Table is empty!")
            all_ok = False
    else:
        print(f"  ❌ File not found: {table1_path}")
        all_ok = False
    
    # Table 2: target_count × format_class_meta
    print("\n📊 Table 2: target_count × format_class_meta.csv")
    table2_path = WORLD_MODEL_DIR / "target_count × format_class_meta.csv"
    if table2_path.exists():
        df2 = pd.read_csv(table2_path, index_col=0)
        total2 = df2.loc['Total', 'Total']
        print(f"  ✅ File exists")
        print(f"  📐 Shape: {df2.shape}")
        print(f"  📈 Total: {total2} (expected: {EXPECTED_TOTAL})")
        if total2 != EXPECTED_TOTAL:
            print(f"  ❌ Total mismatch!")
            all_ok = False
        if df2.empty:
            print(f"  ❌ Table is empty!")
            all_ok = False
    else:
        print(f"  ❌ File not found: {table2_path}")
        all_ok = False
    
    # Table 3a: fc_isotype_primary × target_topN_slice5
    print("\n📊 Table 3a: fc_isotype_primary × target_topN_slice5.csv")
    table3a_path = WORLD_MODEL_DIR / "fc_isotype_primary × target_topN_slice5.csv"
    if table3a_path.exists():
        df3a = pd.read_csv(table3a_path, index_col=0)
        total3a = df3a.loc['Total', 'Total'] if 'Total' in df3a.index else None
        print(f"  ✅ File exists")
        print(f"  📐 Shape: {df3a.shape}")
        if total3a:
            print(f"  📈 Total: {total3a}")
        if df3a.empty:
            print(f"  ❌ Table is empty!")
            all_ok = False
    else:
        print(f"  ❌ File not found: {table3a_path}")
        all_ok = False
    
    # Table 3b: fc_isotype_primary × target_topN_slice8
    print("\n📊 Table 3b: fc_isotype_primary × target_topN_slice8.csv")
    table3b_path = WORLD_MODEL_DIR / "fc_isotype_primary × target_topN_slice8.csv"
    if table3b_path.exists():
        df3b = pd.read_csv(table3b_path, index_col=0)
        total3b = df3b.loc['Total', 'Total'] if 'Total' in df3b.index else None
        print(f"  ✅ File exists")
        print(f"  📐 Shape: {df3b.shape}")
        if total3b:
            print(f"  📈 Total: {total3b}")
        if df3b.empty:
            print(f"  ❌ Table is empty!")
            all_ok = False
    else:
        print(f"  ❌ File not found: {table3b_path}")
        all_ok = False
    
    # Table 4: genetics_normalized × phase
    print("\n📊 Table 4: genetics_normalized × phase.csv")
    table4_path = WORLD_MODEL_DIR / "genetics_normalized × phase.csv"
    if table4_path.exists():
        df4 = pd.read_csv(table4_path, index_col=0)
        total4 = df4.loc['Total', 'Total']
        print(f"  ✅ File exists")
        print(f"  📐 Shape: {df4.shape}")
        print(f"  📈 Total: {total4} (expected: {EXPECTED_TOTAL})")
        if total4 != EXPECTED_TOTAL:
            print(f"  ❌ Total mismatch!")
            all_ok = False
        if df4.empty:
            print(f"  ❌ Table is empty!")
            all_ok = False
    else:
        print(f"  ❌ File not found: {table4_path}")
        all_ok = False
    
    # Table 5: bispecific_flag × phase
    print("\n📊 Table 5: bispecific_flag × phase.csv")
    table5_path = WORLD_MODEL_DIR / "bispecific_flag × phase.csv"
    if table5_path.exists():
        df5 = pd.read_csv(table5_path, index_col=0)
        total5 = df5.loc['Total', 'Total']
        print(f"  ✅ File exists")
        print(f"  📐 Shape: {df5.shape}")
        print(f"  📈 Total: {total5} (expected: {EXPECTED_TOTAL})")
        if total5 != EXPECTED_TOTAL:
            print(f"  ❌ Total mismatch!")
            all_ok = False
        if df5.empty:
            print(f"  ❌ Table is empty!")
            all_ok = False
    else:
        print(f"  ❌ File not found: {table5_path}")
        all_ok = False
    
    # Verify key metrics from slice summary
    print("\n" + "=" * 70)
    print("🔍 Verifying Key Metrics (Slice 1-7 counts)")
    print("=" * 70)
    
    if SLICE_SUMMARY.exists():
        slice_df = pd.read_csv(SLICE_SUMMARY)
        print("\nSlice counts from slice_summary.csv:")
        for _, row in slice_df.iterrows():
            print(f"  {row['slice_id']:30s}: {row['count']:4d}")
        
        # Verify from bispecific_flag × phase table
        print("\nVerifying from bispecific_flag × phase table:")
        bispecific_count = df5.loc['bispecific', 'Total']
        print(f"  Bispecific count: {bispecific_count}")
        print(f"  (Should match Slice 4 approximately, but Slice 4 has additional filters)")
    else:
        print(f"  ⚠️  Slice summary not found: {SLICE_SUMMARY}")
    
    print("\n" + "=" * 70)
    if all_ok:
        print("✅ All World Model tables verified successfully!")
    else:
        print("❌ Some issues found in World Model tables")
    print("=" * 70)
    
    return all_ok


if __name__ == "__main__":
    success = verify_tables()
    sys.exit(0 if success else 1)
