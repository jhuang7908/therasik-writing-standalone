#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/build_world_model_tables.py

Build "World Model" tables for multi-dimensional pattern analysis.
These tables capture key relationships without requiring canonical structure analysis.

Outputs 5 tables:
1. phase × modality × format_class_meta.csv
2. target_count × format_class_meta.csv
3. fc_isotype_primary × target_topN.csv (for Slice 5 and Slice 8 separately)
4. genetics_normalized × phase.csv
5. bispecific_flag × phase.csv
"""

import sys
import json
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_slice_ids(slice_ids_file: Path) -> Set[str]:
    """Load antibody IDs from a slice ID file."""
    if not slice_ids_file.exists():
        return set()
    
    ids = set()
    with open(slice_ids_file, 'r', encoding='utf-8') as f:
        for line in f:
            ab_id = line.strip()
            if ab_id:
                ids.add(ab_id)
    return ids


def get_antibody_id_from_row(row: pd.Series) -> str:
    """Extract antibody_id from a Truth Table row."""
    return row.get("Name", "") or row.get("INN", "") or row.get("Therapeutic", "") or ""


def build_phase_modality_format_table(
    df: pd.DataFrame,
    output_path: Path,
) -> pd.DataFrame:
    """
    Build phase × modality × format_class_meta cross-tabulation.
    
    Returns:
        DataFrame with phase as index, modality × format_class_meta as columns
    """
    print("\n📊 Building phase × modality × format_class_meta table...")
    
    # Create a combined column for modality × format_class_meta
    df['modality_format'] = df['modality'].astype(str) + " × " + df['format_class_meta'].astype(str)
    
    # Create cross-tabulation
    crosstab = pd.crosstab(
        df['phase_bucket'],
        df['modality_format'],
        margins=True,
        margins_name="Total"
    )
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crosstab.to_csv(output_path, encoding='utf-8')
    print(f"  💾 Saved to: {output_path}")
    print(f"  📐 Shape: {crosstab.shape}")
    
    return crosstab


def build_target_count_format_table(
    df: pd.DataFrame,
    output_path: Path,
) -> pd.DataFrame:
    """
    Build target_count × format_class_meta cross-tabulation.
    
    Returns:
        DataFrame with target_count as index, format_class_meta as columns
    """
    print("\n📊 Building target_count × format_class_meta table...")
    
    # Create cross-tabulation
    crosstab = pd.crosstab(
        df['target_count_meta'],
        df['format_class_meta'],
        margins=True,
        margins_name="Total"
    )
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crosstab.to_csv(output_path, encoding='utf-8')
    print(f"  💾 Saved to: {output_path}")
    print(f"  📐 Shape: {crosstab.shape}")
    
    return crosstab


def build_fc_isotype_target_table(
    df: pd.DataFrame,
    output_path: Path,
    slice_name: str = "",
    top_n: int = 20,
) -> pd.DataFrame:
    """
    Build fc_isotype_primary × target_topN cross-tabulation.
    
    Args:
        df: Filtered DataFrame
        output_path: Output CSV path
        slice_name: Name of the slice (for logging)
        top_n: Number of top targets to include
    
    Returns:
        DataFrame with fc_isotype_primary as index, top targets as columns
    """
    print(f"\n📊 Building fc_isotype_primary × target_top{top_n} table{(' for ' + slice_name) if slice_name else ''}...")
    
    # Count targets
    target_counter = Counter()
    for targets_str in df['targets_meta']:
        if pd.notna(targets_str) and targets_str:
            targets = str(targets_str).split('|')
            for target in targets:
                if target and target.strip():
                    target_counter[target.strip()] += 1
    
    # Get top N targets
    top_targets = [t for t, _ in target_counter.most_common(top_n)]
    print(f"  🎯 Top {len(top_targets)} targets: {', '.join(top_targets[:5])}...")
    
    # Create a copy to avoid SettingWithCopyWarning
    df_work = df.copy()
    
    # Create binary columns for each top target
    for target in top_targets:
        df_work[f'target_{target}'] = df_work['targets_meta'].apply(
            lambda x: 1 if (pd.notna(x) and target in str(x)) else 0
        )
    
    # Build cross-tabulation: fc_isotype_primary × top targets
    target_cols = [f'target_{t}' for t in top_targets]
    crosstab_data = []
    
    for isotype in sorted(df_work['fc_isotype_primary'].unique()):
        isotype_df = df_work[df_work['fc_isotype_primary'] == isotype]
        row = {'fc_isotype_primary': isotype}
        for target_col in target_cols:
            row[target_col.replace('target_', '')] = int(isotype_df[target_col].sum())
        crosstab_data.append(row)
    
    crosstab = pd.DataFrame(crosstab_data)
    crosstab = crosstab.set_index('fc_isotype_primary')
    
    # Add totals
    crosstab.loc['Total'] = crosstab.sum()
    crosstab['Total'] = crosstab.sum(axis=1)
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crosstab.to_csv(output_path, encoding='utf-8')
    print(f"  💾 Saved to: {output_path}")
    print(f"  📐 Shape: {crosstab.shape}")
    
    return crosstab


def build_genetics_phase_table(
    df: pd.DataFrame,
    output_path: Path,
) -> pd.DataFrame:
    """
    Build genetics_normalized × phase cross-tabulation.
    
    Returns:
        DataFrame with genetics_normalized as index, phase_bucket as columns
    """
    print("\n📊 Building genetics_normalized × phase table...")
    
    # Create cross-tabulation
    crosstab = pd.crosstab(
        df['genetics_normalized'],
        df['phase_bucket'],
        margins=True,
        margins_name="Total"
    )
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crosstab.to_csv(output_path, encoding='utf-8')
    print(f"  💾 Saved to: {output_path}")
    print(f"  📐 Shape: {crosstab.shape}")
    
    return crosstab


def build_bispecific_phase_table(
    df: pd.DataFrame,
    output_path: Path,
) -> pd.DataFrame:
    """
    Build bispecific_flag × phase cross-tabulation.
    
    Returns:
        DataFrame with is_bispecific_meta as index, phase_bucket as columns
    """
    print("\n📊 Building bispecific_flag × phase table...")
    
    # Convert boolean to string for better readability
    df['bispecific_flag'] = df['is_bispecific_meta'].apply(
        lambda x: "bispecific" if x else "monospecific"
    )
    
    # Create cross-tabulation
    crosstab = pd.crosstab(
        df['bispecific_flag'],
        df['phase_bucket'],
        margins=True,
        margins_name="Total"
    )
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crosstab.to_csv(output_path, encoding='utf-8')
    print(f"  💾 Saved to: {output_path}")
    print(f"  📐 Shape: {crosstab.shape}")
    
    return crosstab


def build_world_model_tables(
    truth_table_xlsx: Path,
    output_dir: Path,
    slice_ids_dir: Optional[Path] = None,
    top_n_targets: int = 20,
) -> Dict[str, Any]:
    """
    Build all world model tables.
    
    Args:
        truth_table_xlsx: Path to Truth Table XLSX
        output_dir: Output directory for world model tables
        slice_ids_dir: Optional directory containing slice ID files
        top_n_targets: Number of top targets to include in fc_isotype × target table
    
    Returns:
        Summary dictionary
    """
    print("=" * 70)
    print("🌍 Building World Model Tables")
    print("=" * 70)
    
    # Load Truth Table
    print(f"\n📖 Loading Truth Table: {truth_table_xlsx}")
    if not truth_table_xlsx.exists():
        raise RuntimeError(f"CRITICAL: Truth Table not found: {truth_table_xlsx}")
    
    df = pd.read_excel(truth_table_xlsx, engine='openpyxl')
    print(f"✅ Loaded {len(df)} records")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # Table 1: phase × modality × format_class_meta
    table1_path = output_dir / "phase × modality × format_class_meta.csv"
    results['phase_modality_format'] = build_phase_modality_format_table(df, table1_path)
    
    # Table 2: target_count × format_class_meta
    table2_path = output_dir / "target_count × format_class_meta.csv"
    results['target_count_format'] = build_target_count_format_table(df, table2_path)
    
    # Table 3: fc_isotype_primary × target_topN (for Slice 5)
    if slice_ids_dir:
        slice5_ids_file = slice_ids_dir / "slice_5_fc_target_design_ids.txt"
        if slice5_ids_file.exists():
            slice5_ids = load_slice_ids(slice5_ids_file)
            df_slice5 = df[df.apply(lambda row: get_antibody_id_from_row(row) in slice5_ids, axis=1)]
            print(f"\n  📦 Filtered to {len(df_slice5)} records from Slice 5")
            
            table3_slice5_path = output_dir / "fc_isotype_primary × target_topN_slice5.csv"
            results['fc_isotype_target_slice5'] = build_fc_isotype_target_table(
                df_slice5, table3_slice5_path, slice_name="Slice 5", top_n=top_n_targets
            )
        else:
            print(f"\n  ⚠️  Slice 5 IDs file not found: {slice5_ids_file}")
    
    # Table 3b: fc_isotype_primary × target_topN (for Slice 8 - ADC)
    if slice_ids_dir:
        # Load ADC slice from engineering slices summary or filter directly
        # For now, filter directly from Truth Table using same conditions as export_engineering_slices.py
        df_slice8 = df[
            (df['modality'] == 'ADC') &
            (df['phase_bucket'].isin(['phase_II_plus', 'phase_I'])) &
            (df['human_origin_mode'] != 'non_human')
        ].copy()
        print(f"\n  📦 Filtered to {len(df_slice8)} records from Slice 8 (ADC)")
        
        table3_slice8_path = output_dir / "fc_isotype_primary × target_topN_slice8.csv"
        results['fc_isotype_target_slice8'] = build_fc_isotype_target_table(
            df_slice8, table3_slice8_path, slice_name="Slice 8 (ADC)", top_n=top_n_targets
        )
    
    # Table 4: genetics_normalized × phase
    table4_path = output_dir / "genetics_normalized × phase.csv"
    results['genetics_phase'] = build_genetics_phase_table(df, table4_path)
    
    # Table 5: bispecific_flag × phase
    table5_path = output_dir / "bispecific_flag × phase.csv"
    results['bispecific_phase'] = build_bispecific_phase_table(df, table5_path)
    
    # Print summary
    print("\n" + "=" * 70)
    print("✅ World Model Tables Generated")
    print("=" * 70)
    print(f"\nOutput directory: {output_dir}")
    print("\nGenerated tables:")
    print(f"  1. phase × modality × format_class_meta.csv")
    print(f"  2. target_count × format_class_meta.csv")
    if 'fc_isotype_target_slice5' in results:
        print(f"  3a. fc_isotype_primary × target_topN_slice5.csv")
    if 'fc_isotype_target_slice8' in results:
        print(f"  3b. fc_isotype_primary × target_topN_slice8.csv")
    print(f"  4. genetics_normalized × phase.csv")
    print(f"  5. bispecific_flag × phase.csv")
    print("=" * 70)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Build World Model tables for pattern analysis")
    parser.add_argument("--truth_table_xlsx", default="data/thera_sabdab/out/thera_truth_table.xlsx",
                        help="Input Truth Table XLSX file")
    parser.add_argument("--output_dir", default="data/thera_sabdab/world_model",
                        help="Output directory for world model tables")
    parser.add_argument("--slice_ids_dir", default="data/thera_sabdab/out/slice_ids",
                        help="Directory containing slice ID files (optional)")
    parser.add_argument("--top_n_targets", type=int, default=20,
                        help="Number of top targets to include in fc_isotype × target table (default: 20)")
    
    args = parser.parse_args()
    
    truth_table_xlsx = Path(args.truth_table_xlsx)
    if not truth_table_xlsx.is_absolute():
        truth_table_xlsx = PROJECT_ROOT / truth_table_xlsx
    
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    
    slice_ids_dir = None
    if args.slice_ids_dir:
        slice_ids_dir = Path(args.slice_ids_dir)
        if not slice_ids_dir.is_absolute():
            slice_ids_dir = PROJECT_ROOT / slice_ids_dir
        if not slice_ids_dir.exists():
            print(f"⚠️  Slice IDs directory not found: {slice_ids_dir}")
            slice_ids_dir = None
    
    try:
        results = build_world_model_tables(
            truth_table_xlsx,
            output_dir,
            slice_ids_dir=slice_ids_dir,
            top_n_targets=args.top_n_targets,
        )
        print(f"\n✅ World Model tables built successfully!")
    except RuntimeError as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
