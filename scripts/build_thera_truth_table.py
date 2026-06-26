#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/build_thera_truth_table.py

Build unified Truth Table for Thera-SAbDab data.
This is the single source of truth for all Reference Slices (1-7) and Engineering Slices (8-10).
"""

import sys
import json
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_meta_models(meta_models_json: Path) -> Dict[str, Dict[str, Any]]:
    """Load antibody meta-models and index by antibody_id."""
    with open(meta_models_json, 'r', encoding='utf-8') as f:
        meta_models = json.load(f)
    
    # Index by antibody_id
    indexed = {}
    for model in meta_models:
        ab_id = model.get("antibody_id", "")
        if ab_id:
            indexed[ab_id] = model
    
    return indexed


def check_consistency(
    existing_value: Any,
    new_value: Any,
    field_name: str,
    antibody_id: str,
    inconsistencies: List[Dict[str, Any]]
) -> bool:
    """
    Check if existing value is consistent with new value.
    Returns True if consistent, False otherwise.
    """
    # Handle NaN/None
    if pd.isna(existing_value) or existing_value == "" or existing_value is None:
        return True  # Empty is considered consistent (will be filled)
    
    if pd.isna(new_value) or new_value == "" or new_value is None:
        return True  # New value is empty, keep existing
    
    # Convert to comparable types
    existing_str = str(existing_value).strip()
    new_str = str(new_value).strip()
    
    # For lists, convert to sorted string representation
    if isinstance(existing_value, list):
        existing_str = "|".join(sorted(str(x) for x in existing_value if x))
    if isinstance(new_value, list):
        new_str = "|".join(sorted(str(x) for x in new_value if x))
    
    if existing_str != new_str:
        inconsistencies.append({
            "antibody_id": antibody_id,
            "field": field_name,
            "existing": existing_str,
            "new": new_str,
        })
        return False
    
    return True


def build_truth_table(
    input_xlsx: Path,
    meta_models_json: Path,
    output_xlsx: Path,
    qc_json: Path,
) -> Dict[str, Any]:
    """
    Build unified Truth Table from qc_only_pass.xlsx and antibody_meta_models.json.
    
    Returns:
        QC statistics dictionary
    """
    print(f"📖 Loading QC pass data: {input_xlsx}")
    if not input_xlsx.exists():
        raise RuntimeError(f"CRITICAL: Input file not found: {input_xlsx}")
    
    df = pd.read_excel(input_xlsx, engine='openpyxl')
    print(f"✅ Loaded {len(df)} records")
    
    print(f"📖 Loading meta-models: {meta_models_json}")
    if not meta_models_json.exists():
        raise RuntimeError(f"CRITICAL: Meta-models file not found: {meta_models_json}")
    
    meta_models = load_meta_models(meta_models_json)
    print(f"✅ Loaded {len(meta_models)} meta-models")
    
    # Track inconsistencies
    inconsistencies = []
    missing_meta_models = []
    
    # Merge fields from meta-models
    print("\n🔗 Merging meta-model data...")
    
    # Define fields to merge
    merge_fields = {
        "phase_bucket": lambda m: m.get("clinical", {}).get("phase_bucket", "unknown"),
        "format_class_meta": lambda m: m.get("format", {}).get("format_class", ""),
        "is_bispecific_meta": lambda m: m.get("format", {}).get("is_bispecific", False),
        "target_count_meta": lambda m: m.get("target", {}).get("target_count", 0),
        "targets_meta": lambda m: m.get("target", {}).get("targets", []),
        "fc_isotype_primary": lambda m: m.get("fc", {}).get("isotype_primary", "na"),
        "fc_isotype_secondary": lambda m: m.get("fc", {}).get("isotype_secondary", "na"),
        "fc_isotype_set": lambda m: m.get("fc", {}).get("isotype_set", "na"),
        "genetics_normalized": lambda m: m.get("genetics", {}).get("normalized", ""),
        "human_origin_mode": lambda m: m.get("genetics", {}).get("human_origin_mode", "unknown"),
    }
    
    # Merge each field
    for field_name, extractor in merge_fields.items():
        new_values = []
        for idx, row in df.iterrows():
            antibody_id = row.get("Name", "") or row.get("INN", "")
            if not antibody_id:
                new_values.append(None)
                continue
            
            meta_model = meta_models.get(antibody_id)
            if not meta_model:
                missing_meta_models.append(antibody_id)
                new_values.append(None)
                continue
            
            new_value = extractor(meta_model)
            
            # Check consistency if field already exists
            if field_name in df.columns:
                existing_value = row.get(field_name)
                if not check_consistency(existing_value, new_value, field_name, antibody_id, inconsistencies):
                    # Inconsistency found, use new value (will be logged)
                    pass
            
            new_values.append(new_value)
        
        df[field_name] = new_values
    
    # Verify modality field (should already exist from qc_only_pass)
    if "modality" not in df.columns:
        print("⚠️  WARNING: 'modality' field not found in input. Attempting to infer from format_class_meta...")
        # Infer modality from format_class_meta
        def infer_modality_from_format_class(format_class: str) -> str:
            if not format_class or pd.isna(format_class):
                return "other"
            format_lower = str(format_class).lower()
            if "adc" in format_lower:
                return "ADC"
            if "fusion" in format_lower:
                return "fusion"
            if "radiolabeled" in format_lower or "radio" in format_lower:
                return "radiolabeled"
            if "vhv" in format_lower or "nanobody" in format_lower:
                return "other"  # VHH is not a modality
            return "standard"
        
        df["modality"] = df["format_class_meta"].apply(infer_modality_from_format_class)
    else:
        print("✅ 'modality' field found in input")
    
    # Convert targets_meta list to string for Excel compatibility
    if "targets_meta" in df.columns:
        df["targets_meta"] = df["targets_meta"].apply(
            lambda x: "|".join(str(t) for t in x) if isinstance(x, list) else (str(x) if pd.notna(x) else "")
        )
    
    # Fail-fast on inconsistencies
    if inconsistencies:
        print(f"\n❌ CRITICAL: Found {len(inconsistencies)} inconsistencies!")
        print("First 10 inconsistencies:")
        for inc in inconsistencies[:10]:
            print(f"  {inc['antibody_id']}.{inc['field']}: existing='{inc['existing']}' vs new='{inc['new']}'")
        if len(inconsistencies) > 10:
            print(f"  ... and {len(inconsistencies) - 10} more")
        raise RuntimeError(f"CRITICAL: Truth table has {len(inconsistencies)} inconsistencies. Fix data before proceeding.")
    
    # Calculate QC statistics
    print("\n📊 Calculating QC statistics...")
    qc_stats = {
        "total_records": len(df),
        "missing_meta_models": len(missing_meta_models),
        "missing_meta_model_ids": missing_meta_models[:20] if len(missing_meta_models) <= 20 else missing_meta_models[:20] + [f"... and {len(missing_meta_models) - 20} more"],
        "inconsistencies": len(inconsistencies),
        "field_completeness": {},
    }
    
    # Check field completeness
    required_fields = [
        "phase_bucket",
        "format_class_meta",
        "modality",
        "is_bispecific_meta",
        "target_count_meta",
        "targets_meta",
        "fc_isotype_primary",
        "fc_isotype_secondary",
        "fc_isotype_set",
        "genetics_normalized",
        "human_origin_mode",
    ]
    
    for field in required_fields:
        if field in df.columns:
            non_null_count = df[field].notna().sum()
            non_empty_count = (df[field].astype(str).str.strip() != "").sum()
            qc_stats["field_completeness"][field] = {
                "non_null": int(non_null_count),
                "non_empty": int(non_empty_count),
                "null_rate": float(1.0 - non_null_count / len(df)) if len(df) > 0 else 0.0,
                "empty_rate": float(1.0 - non_empty_count / len(df)) if len(df) > 0 else 0.0,
            }
        else:
            qc_stats["field_completeness"][field] = {
                "non_null": 0,
                "non_empty": 0,
                "null_rate": 1.0,
                "empty_rate": 1.0,
            }
    
    # Save Truth Table
    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n💾 Saving Truth Table to: {output_xlsx}")
    df.to_excel(output_xlsx, index=False, engine='openpyxl')
    print(f"✅ Saved {len(df)} records")
    
    # Save QC report
    print(f"💾 Saving QC report to: {qc_json}")
    with open(qc_json, 'w', encoding='utf-8') as f:
        json.dump(qc_stats, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 Truth Table QC Summary")
    print("=" * 70)
    print(f"Total records: {qc_stats['total_records']}")
    print(f"Missing meta-models: {qc_stats['missing_meta_models']}")
    print(f"Inconsistencies: {qc_stats['inconsistencies']}")
    print(f"\nField completeness:")
    for field, stats in qc_stats["field_completeness"].items():
        print(f"  {field}:")
        print(f"    Non-null: {stats['non_null']}/{qc_stats['total_records']} ({100*(1-stats['null_rate']):.1f}%)")
        print(f"    Non-empty: {stats['non_empty']}/{qc_stats['total_records']} ({100*(1-stats['empty_rate']):.1f}%)")
    print("=" * 70)
    
    # Validation gates
    if qc_stats['total_records'] != 1133:
        print(f"\n⚠️  WARNING: Expected 1133 records, got {qc_stats['total_records']}")
    
    if qc_stats['missing_meta_models'] > 0:
        print(f"\n⚠️  WARNING: {qc_stats['missing_meta_models']} records missing meta-models")
    
    critical_fields = ["phase_bucket", "modality", "human_origin_mode"]
    for field in critical_fields:
        if field in qc_stats["field_completeness"]:
            stats = qc_stats["field_completeness"][field]
            if stats["empty_rate"] > 0.01:  # More than 1% missing
                print(f"\n⚠️  WARNING: {field} has {stats['empty_rate']*100:.1f}% missing values")
    
    return qc_stats


def main():
    parser = argparse.ArgumentParser(description="Build unified Truth Table for Thera-SAbDab")
    parser.add_argument("--in_xlsx", default="data/thera_sabdab/out/qc_only_pass.xlsx",
                        help="Input QC pass XLSX file")
    parser.add_argument("--meta_models_json", default="data/thera_sabdab/out/antibody_meta_models.json",
                        help="Input antibody meta-models JSON file")
    parser.add_argument("--out_xlsx", default="data/thera_sabdab/out/thera_truth_table.xlsx",
                        help="Output Truth Table XLSX file")
    parser.add_argument("--qc_json", default="data/thera_sabdab/out/truth_table_qc.json",
                        help="Output QC report JSON file")
    
    args = parser.parse_args()
    
    input_xlsx = Path(args.in_xlsx)
    if not input_xlsx.is_absolute():
        input_xlsx = PROJECT_ROOT / input_xlsx
    
    meta_models_json = Path(args.meta_models_json)
    if not meta_models_json.is_absolute():
        meta_models_json = PROJECT_ROOT / meta_models_json
    
    output_xlsx = Path(args.out_xlsx)
    if not output_xlsx.is_absolute():
        output_xlsx = PROJECT_ROOT / output_xlsx
    
    qc_json = Path(args.qc_json)
    if not qc_json.is_absolute():
        qc_json = PROJECT_ROOT / qc_json
    
    print("=" * 70)
    print("🔨 Building Thera-SAbDab Truth Table")
    print("=" * 70)
    print(f"Input: {input_xlsx}")
    print(f"Meta-models: {meta_models_json}")
    print(f"Output: {output_xlsx}")
    print(f"QC report: {qc_json}")
    print("=" * 70)
    
    try:
        qc_stats = build_truth_table(input_xlsx, meta_models_json, output_xlsx, qc_json)
        print(f"\n✅ Truth Table built successfully!")
        print(f"   Output: {output_xlsx}")
        print(f"   QC report: {qc_json}")
    except RuntimeError as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
