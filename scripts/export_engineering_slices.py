#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/export_engineering_slices.py

Export engineering-specific slices from Thera-SAbDab Truth Table.
Currently supports: ADC Engineering Set (Slice 8), Fusion Engineering Set (Slice 9), Radiolabeled Engineering Set (Slice 10)

Input: thera_truth_table.xlsx (unified Truth Table)
Output: XLSX files with full data + Summary JSON files with statistics
"""

import sys
import json
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def export_adc_engineering_set(
    truth_table_xlsx: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Export ADC Engineering Set (Slice 8).
    
    Conditions:
    - modality == "ADC"
    - phase_bucket ∈ {"phase_II_plus", "phase_I"}
    - human_origin_mode != "non_human"
    
    Input: Truth Table (thera_truth_table.xlsx)
    Output: XLSX + Summary JSON
    
    Returns:
        Summary statistics dictionary
    """
    print(f"📖 Loading Truth Table: {truth_table_xlsx}")
    df = pd.read_excel(truth_table_xlsx, engine='openpyxl')
    print(f"✅ Loaded {len(df)} records")
    
    # All fields are already in Truth Table, no need to merge
    print("✅ Using Truth Table fields directly")
    
    # Apply filters
    print("\n🔬 Applying ADC Engineering Set filters...")
    filtered = df[
        (df['modality'] == 'ADC') &
        (df['phase_bucket'].isin(['phase_II_plus', 'phase_I'])) &
        (df['human_origin_mode'] != 'non_human')
    ].copy()
    
    print(f"✅ Filtered to {len(filtered)} ADC engineering records")
    
    if len(filtered) == 0:
        print("⚠️  No records match the criteria")
        return {
            "total_records": 0,
            "phase_distribution": {},
            "format_distribution": {},
            "fc_isotype_primary_distribution": {},
            "target_top20": [],
        }
    
    # Calculate statistics (convert to native Python types for JSON)
    phase_distribution = {k: int(v) for k, v in filtered['phase_bucket'].value_counts().items()}
    format_distribution = {k: int(v) for k, v in filtered['format_class_meta'].value_counts().items()}
    isotype_distribution = {k: int(v) for k, v in filtered['fc_isotype_primary'].value_counts().items()}
    
    # Target distribution
    target_counter = Counter()
    for targets_str in filtered['targets_meta']:
        if pd.notna(targets_str) and targets_str:
            # targets_meta is stored as pipe-separated string
            targets = str(targets_str).split('|')
            for target in targets:
                if target and target.strip():
                    target_counter[target.strip()] += 1
    
    target_top20 = [{"target": t, "count": c} for t, c in target_counter.most_common(20)]
    
    summary = {
        "total_records": len(filtered),
        "phase_distribution": phase_distribution,
        "format_distribution": format_distribution,
        "fc_isotype_primary_distribution": isotype_distribution,
        "target_top20": target_top20,
    }
    
    # Prepare output DataFrame (keep all Truth Table columns)
    output_df = filtered.copy()
    
    # Save Excel
    output_dir.mkdir(parents=True, exist_ok=True)
    output_xlsx = output_dir / "thera_slice_ADC_engineering.xlsx"
    print(f"\n💾 Saving to: {output_xlsx}")
    output_df.to_excel(output_xlsx, index=False, engine='openpyxl')
    
    # Save summary JSON
    summary_json = output_dir / "thera_slice_ADC_engineering_summary.json"
    print(f"💾 Saving summary to: {summary_json}")
    with open(summary_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 ADC Engineering Set (Slice 8) Summary")
    print("=" * 60)
    print(f"Total records: {summary['total_records']}")
    print(f"\nPhase distribution:")
    for phase, count in sorted(summary['phase_distribution'].items()):
        print(f"   {phase}: {count}")
    print(f"\nFormat distribution:")
    for fmt, count in sorted(summary['format_distribution'].items()):
        print(f"   {fmt}: {count}")
    print(f"\nFc isotype distribution:")
    for iso, count in sorted(summary['fc_isotype_primary_distribution'].items()):
        print(f"   {iso}: {count}")
    print(f"\nTop 10 targets:")
    for item in summary['target_top20'][:10]:
        print(f"   {item['target']}: {item['count']}")
    print("=" * 60)
    
    return summary


def export_fusion_engineering_set(
    truth_table_xlsx: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Export Fusion Engineering Set (Slice 9).
    
    Conditions:
    - modality == "fusion"
    - phase_bucket ∈ {"phase_II_plus", "phase_I"}
    
    Returns:
        Summary statistics dictionary
    """
    print(f"📖 Loading Truth Table: {truth_table_xlsx}")
    df = pd.read_excel(truth_table_xlsx, engine='openpyxl')
    print(f"✅ Loaded {len(df)} records")
    
    # All fields are already in Truth Table, no need to merge
    print("✅ Using Truth Table fields directly")
    
    # Apply filters
    print("\n🔬 Applying Fusion Engineering Set filters...")
    filtered = df[
        (df['modality'] == 'fusion') &
        (df['phase_bucket'].isin(['phase_II_plus', 'phase_I']))
    ].copy()
    
    print(f"✅ Filtered to {len(filtered)} Fusion engineering records")
    
    if len(filtered) == 0:
        print("⚠️  No records match the criteria")
        return {
            "total_records": 0,
            "phase_distribution": {},
            "format_distribution": {},
            "fc_isotype_primary_distribution": {},
            "target_top20": [],
        }
    
    # Calculate statistics (convert to native Python types for JSON)
    phase_distribution = {k: int(v) for k, v in filtered['phase_bucket'].value_counts().items()}
    format_distribution = {k: int(v) for k, v in filtered['format_class_meta'].value_counts().items()}
    isotype_distribution = {k: int(v) for k, v in filtered['fc_isotype_primary'].value_counts().items()}
    
    # Target distribution
    target_counter = Counter()
    for targets_str in filtered['targets_meta']:
        if pd.notna(targets_str) and targets_str:
            # targets_meta is stored as pipe-separated string
            targets = str(targets_str).split('|')
            for target in targets:
                if target and target.strip():
                    target_counter[target.strip()] += 1
    
    target_top20 = [{"target": t, "count": c} for t, c in target_counter.most_common(20)]
    
    summary = {
        "total_records": len(filtered),
        "phase_distribution": phase_distribution,
        "format_distribution": format_distribution,
        "fc_isotype_primary_distribution": isotype_distribution,
        "target_top20": target_top20,
    }
    
    # Prepare output DataFrame (keep all Truth Table columns)
    output_df = filtered.copy()
    
    # Save Excel
    output_dir.mkdir(parents=True, exist_ok=True)
    output_xlsx = output_dir / "thera_slice_fusion_engineering.xlsx"
    print(f"\n💾 Saving to: {output_xlsx}")
    output_df.to_excel(output_xlsx, index=False, engine='openpyxl')
    
    # Save summary JSON
    summary_json = output_dir / "thera_slice_fusion_engineering_summary.json"
    print(f"💾 Saving summary to: {summary_json}")
    with open(summary_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Fusion Engineering Set (Slice 9) Summary")
    print("=" * 60)
    print(f"Total records: {summary['total_records']}")
    print(f"\nPhase distribution:")
    for phase, count in sorted(summary['phase_distribution'].items()):
        print(f"   {phase}: {count}")
    print(f"\nFormat distribution:")
    for fmt, count in sorted(summary['format_distribution'].items()):
        print(f"   {fmt}: {count}")
    print(f"\nFc isotype distribution:")
    for iso, count in sorted(summary['fc_isotype_primary_distribution'].items()):
        print(f"   {iso}: {count}")
    print(f"\nTop 10 targets:")
    for item in summary['target_top20'][:10]:
        print(f"   {item['target']}: {item['count']}")
    print("=" * 60)
    
    return summary


def export_radiolabeled_engineering_set(
    truth_table_xlsx: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Export Radiolabeled Engineering Set (Slice 10).
    
    Conditions:
    - modality == "radiolabeled"
    - phase_bucket ∈ {"phase_II_plus", "phase_I"}
    
    Input: Truth Table (thera_truth_table.xlsx)
    Output: XLSX + Summary JSON
    
    Returns:
        Summary statistics dictionary
    """
    print(f"📖 Loading Truth Table: {truth_table_xlsx}")
    df = pd.read_excel(truth_table_xlsx, engine='openpyxl')
    print(f"✅ Loaded {len(df)} records")
    
    # All fields are already in Truth Table, no need to merge
    print("✅ Using Truth Table fields directly")
    
    # Apply filters
    print("\n🔬 Applying Radiolabeled Engineering Set filters...")
    filtered = df[
        (df['modality'] == 'radiolabeled') &
        (df['phase_bucket'].isin(['phase_II_plus', 'phase_I']))
    ].copy()
    
    print(f"✅ Filtered to {len(filtered)} Radiolabeled engineering records")
    
    if len(filtered) == 0:
        print("⚠️  No records match the criteria")
        return {
            "total_records": 0,
            "phase_distribution": {},
            "format_distribution": {},
            "fc_isotype_primary_distribution": {},
            "target_top20": [],
        }
    
    # Calculate statistics (convert to native Python types for JSON)
    phase_distribution = {k: int(v) for k, v in filtered['phase_bucket'].value_counts().items()}
    format_distribution = {k: int(v) for k, v in filtered['format_class_meta'].value_counts().items()}
    isotype_distribution = {k: int(v) for k, v in filtered['fc_isotype_primary'].value_counts().items()}
    
    # Target distribution
    target_counter = Counter()
    for targets_str in filtered['targets_meta']:
        if pd.notna(targets_str) and targets_str:
            # targets_meta is stored as pipe-separated string
            targets = str(targets_str).split('|')
            for target in targets:
                if target and target.strip():
                    target_counter[target.strip()] += 1
    
    target_top20 = [{"target": t, "count": c} for t, c in target_counter.most_common(20)]
    
    summary = {
        "total_records": len(filtered),
        "phase_distribution": phase_distribution,
        "format_distribution": format_distribution,
        "fc_isotype_primary_distribution": isotype_distribution,
        "target_top20": target_top20,
    }
    
    # Prepare output DataFrame (keep all Truth Table columns)
    output_df = filtered.copy()
    
    # Save Excel
    output_dir.mkdir(parents=True, exist_ok=True)
    output_xlsx = output_dir / "thera_slice_radiolabeled_engineering.xlsx"
    print(f"\n💾 Saving to: {output_xlsx}")
    output_df.to_excel(output_xlsx, index=False, engine='openpyxl')
    
    # Save summary JSON
    summary_json = output_dir / "thera_slice_radiolabeled_engineering_summary.json"
    print(f"💾 Saving summary to: {summary_json}")
    with open(summary_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Radiolabeled Engineering Set (Slice 10) Summary")
    print("=" * 60)
    print(f"Total records: {summary['total_records']}")
    print(f"\nPhase distribution:")
    for phase, count in sorted(summary['phase_distribution'].items()):
        print(f"   {phase}: {count}")
    print(f"\nFormat distribution:")
    for fmt, count in sorted(summary['format_distribution'].items()):
        print(f"   {fmt}: {count}")
    print(f"\nFc isotype distribution:")
    for iso, count in sorted(summary['fc_isotype_primary_distribution'].items()):
        print(f"   {iso}: {count}")
    print(f"\nTop 10 targets:")
    for item in summary['target_top20'][:10]:
        print(f"   {item['target']}: {item['count']}")
    print("=" * 60)
    
    return summary


def main():
    parser = argparse.ArgumentParser(description="Export all engineering-specific slices")
    parser.add_argument("--truth_table_xlsx", default="data/thera_sabdab/out/thera_truth_table.xlsx",
                        help="Input Truth Table XLSX file (default: thera_truth_table.xlsx)")
    parser.add_argument("--output_dir", default="data/thera_sabdab/slices",
                        help="Output directory for slice files")
    
    args = parser.parse_args()
    
    truth_table_xlsx = Path(args.truth_table_xlsx)
    if not truth_table_xlsx.is_absolute():
        truth_table_xlsx = PROJECT_ROOT / truth_table_xlsx
    
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    
    print("=" * 70)
    print("🚀 Exporting All Engineering Slices")
    print("=" * 70)
    print(f"Truth Table: {truth_table_xlsx}")
    print(f"Output directory: {output_dir}")
    print("=" * 70)
    
    # Export all three engineering slices sequentially
    summaries = {}
    
    print("\n" + "=" * 70)
    print("📦 Slice 8: ADC Engineering Set")
    print("=" * 70)
    summaries['ADC'] = export_adc_engineering_set(truth_table_xlsx, output_dir)
    
    print("\n" + "=" * 70)
    print("📦 Slice 9: Fusion Engineering Set")
    print("=" * 70)
    summaries['Fusion'] = export_fusion_engineering_set(truth_table_xlsx, output_dir)
    
    print("\n" + "=" * 70)
    print("📦 Slice 10: Radiolabeled Engineering Set")
    print("=" * 70)
    summaries['Radiolabeled'] = export_radiolabeled_engineering_set(truth_table_xlsx, output_dir)
    
    # Print final summary
    print("\n" + "=" * 70)
    print("✅ All Engineering Slices Exported Successfully")
    print("=" * 70)
    print(f"\nSummary:")
    print(f"  ADC:          {summaries['ADC']['total_records']:3d} records")
    print(f"  Fusion:       {summaries['Fusion']['total_records']:3d} records")
    print(f"  Radiolabeled: {summaries['Radiolabeled']['total_records']:3d} records")
    print(f"\nTotal:          {summaries['ADC']['total_records'] + summaries['Fusion']['total_records'] + summaries['Radiolabeled']['total_records']:3d} records")
    print(f"\nOutput directory: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
