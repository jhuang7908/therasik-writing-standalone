#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/export_reference_slices.py

Export Reference Slices (1-7) from Truth Table.
Outputs lightweight ID lists with audit manifests.
"""

import sys
import json
import csv
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def truth_table_row_to_meta_model(row: pd.Series) -> Dict[str, Any]:
    """
    Convert a Truth Table row to a meta-model-like structure for filtering.
    
    Maps flat Truth Table fields to nested meta-model structure.
    """
    return {
        "antibody_id": row.get("Name", "") or row.get("INN", ""),
        "clinical": {
            "phase_bucket": row.get("phase_bucket", "unknown"),
        },
        "format": {
            "format_class": row.get("format_class_meta", ""),
            "chain_completeness": row.get("chain_completeness", "VH_VL"),
            "is_bispecific": row.get("is_bispecific_meta", False),
        },
        "genetics": {
            "human_origin_mode": row.get("human_origin_mode", "unknown"),
            "normalized": row.get("genetics_normalized", ""),
        },
        "fc": {
            "isotype_primary": row.get("fc_isotype_primary", "na"),
        },
        "target": {
            "targets": row.get("targets_meta", "").split("|") if pd.notna(row.get("targets_meta", "")) and row.get("targets_meta", "") else [],
        },
    }


def build_slice_definitions() -> Dict[str, Dict[str, Any]]:
    """Define all standard reference slices (same as build_reference_slices.py)."""
    slices = {
        "slice_1_standard_humanized": {
            "name": " IgG ",
            "description": "VH/VL 、canonical 、germline ",
            "conditions": [
                {"field": "clinical.phase_bucket", "operator": "==", "value": "phase_II_plus"},
                {"field": "format.format_class", "operator": "==", "value": "monospecific_IgG_Fab"},
                {"field": "genetics.human_origin_mode", "operator": "==", "value": "engineered_humanisation"},
            ],
        },
        "slice_2_natural_human": {
            "name": "",
            "description": "''",
            "conditions": [
                {"field": "clinical.phase_bucket", "operator": "==", "value": "phase_II_plus"},
                {"field": "format.format_class", "operator": "==", "value": "monospecific_IgG_Fab"},
                {"field": "genetics.human_origin_mode", "operator": "==", "value": "natural_human_repertoire"},
            ],
        },
        "slice_3_vhh_design": {
            "name": "VHH / ",
            "description": "、、FR hallmark ",
            "conditions": [
                {"field": "clinical.phase_bucket", "operator": "IN", "value": ["phase_II_plus", "phase_I"]},
                {"field": "format.format_class", "operator": "==", "value": "VHH"},
                {"field": "genetics.human_origin_mode", "operator": "IN", "value": ["engineered_humanisation", "natural_human_repertoire"]},
            ],
        },
        "slice_4_bispecific_engineering": {
            "name": "",
            "description": " germline / canonical 、",
            "conditions": [
                {"field": "clinical.phase_bucket", "operator": "IN", "value": ["phase_II_plus", "phase_I"]},
                {"field": "format.format_class", "operator": "LIKE", "value": "bispecific_*"},
            ],
        },
        "slice_5_fc_target_design": {
            "name": "Fc–Target ",
            "description": " vs IgG1/IgG4  Fc ",
            "conditions": [
                {"field": "clinical.phase_bucket", "operator": "==", "value": "phase_II_plus"},
                {"field": "format.format_class", "operator": "==", "value": "monospecific_IgG_Fab"},
            ],
            "group_by": ["target.targets", "fc.isotype_primary"],
        },
        "slice_6_phase1_expansion": {
            "name": "Phase I ",
            "description": " Phase ≥ II ",
            "conditions": [
                {"field": "clinical.phase_bucket", "operator": "==", "value": "phase_I"},
                {"field": "format.format_class", "operator": "IN", "value": ["monospecific_IgG_Fab", "VHH", "bispecific_IgG_like"]},
                {"field": "genetics.human_origin_mode", "operator": "!=", "value": "non_human"},
            ],
        },
        "slice_7_exclusion": {
            "name": "（）",
            "description": " ADC、fusion、radiolabeled、、",
            "conditions": [
                {"field": "format.format_class", "operator": "IN", "value": ["ADC", "fusion", "radiolabeled"]},
            ],
            "or_conditions": [
                {"field": "genetics.human_origin_mode", "operator": "==", "value": "non_human"},
                {"field": "format.chain_completeness", "operator": "==", "value": "VL_ONLY"},
            ],
        },
    }
    return slices


def apply_slice_filter(meta_model: Dict[str, Any], slice_definition: Dict[str, Any]) -> bool:
    """
    Apply slice filter conditions to a meta-model.
    
    Args:
        meta_model: Meta-model-like dictionary (from Truth Table row)
        slice_definition: Slice definition with filter conditions
    
    Returns:
        True if meta_model matches the slice conditions
    """
    conditions = slice_definition.get("conditions", [])
    
    for condition in conditions:
        field_path = condition["field"]
        operator = condition["operator"]
        value = condition["value"]
        
        # Navigate to field value
        field_value = meta_model
        for key in field_path.split("."):
            if isinstance(field_value, dict):
                field_value = field_value.get(key)
            else:
                return False
        
        # Apply operator
        if operator == "==":
            if field_value != value:
                return False
        elif operator == "!=":
            if field_value == value:
                return False
        elif operator == "IN":
            if field_value not in value:
                return False
        elif operator == "LIKE":
            # LIKE operator for string matching (e.g., "bispecific_*")
            if not isinstance(field_value, str):
                return False
            if value.endswith("*"):
                prefix = value[:-1]
                if not field_value.startswith(prefix):
                    return False
            else:
                if field_value != value:
                    return False
        elif operator == "NOT_IN":
            if field_value in value:
                return False
        else:
            raise ValueError(f"Unknown operator: {operator}")
    
    return True


def apply_slice_with_or(meta_model: Dict[str, Any], slice_definition: Dict[str, Any]) -> bool:
    """
    Apply slice filter with support for OR conditions.
    
    For slice_7_exclusion, we need OR logic:
    (format_class IN [...]) OR (human_origin_mode == non_human) OR (chain_completeness == VL_ONLY)
    """
    conditions = slice_definition.get("conditions", [])
    or_conditions = slice_definition.get("or_conditions", [])
    
    # Main conditions (AND)
    main_match = True
    for condition in conditions:
        field_path = condition["field"]
        operator = condition["operator"]
        value = condition["value"]
        
        field_value = meta_model
        for key in field_path.split("."):
            if isinstance(field_value, dict):
                field_value = field_value.get(key)
            else:
                main_match = False
                break
        
        if not main_match:
            break
        
        if operator == "==":
            if field_value != value:
                main_match = False
                break
        elif operator == "IN":
            if field_value not in value:
                main_match = False
                break
        elif operator == "LIKE":
            if not isinstance(field_value, str):
                main_match = False
                break
            if value.endswith("*"):
                prefix = value[:-1]
                if not field_value.startswith(prefix):
                    main_match = False
                    break
            else:
                if field_value != value:
                    main_match = False
                    break
    
    # OR conditions
    or_match = False
    if or_conditions:
        for condition in or_conditions:
            field_path = condition["field"]
            operator = condition["operator"]
            value = condition["value"]
            
            field_value = meta_model
            for key in field_path.split("."):
                if isinstance(field_value, dict):
                    field_value = field_value.get(key)
                else:
                    break
            
            if operator == "==":
                if field_value == value:
                    or_match = True
                    break
            elif operator == "IN":
                if field_value in value:
                    or_match = True
                    break
    
    # For slice_7, it's: main_match OR or_match
    if or_conditions:
        return main_match or or_match
    else:
        return main_match


def export_reference_slices(
    truth_table_xlsx: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Export all Reference Slices (1-7) from Truth Table.
    
    Returns:
        Summary dictionary with counts for each slice
    """
    print(f"📖 Loading Truth Table: {truth_table_xlsx}")
    if not truth_table_xlsx.exists():
        raise RuntimeError(f"CRITICAL: Truth Table not found: {truth_table_xlsx}")
    
    df = pd.read_excel(truth_table_xlsx, engine='openpyxl')
    print(f"✅ Loaded {len(df)} records")
    
    slice_definitions = build_slice_definitions()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary_rows = []
    all_slice_results = {}
    
    print("\n" + "=" * 70)
    print("🔬 Building Reference Slices (1-7)")
    print("=" * 70)
    
    for slice_id, slice_def in slice_definitions.items():
        print(f"\n📦 Processing {slice_id}...")
        
        matching_ids = []
        
        # Apply filters to each row
        for idx, row in df.iterrows():
            meta_model = truth_table_row_to_meta_model(row)
            antibody_id = meta_model["antibody_id"]
            
            if not antibody_id:
                continue
            
            # Apply filter
            if slice_id == "slice_7_exclusion":
                if apply_slice_with_or(meta_model, slice_def):
                    matching_ids.append(antibody_id)
            else:
                if apply_slice_filter(meta_model, slice_def):
                    matching_ids.append(antibody_id)
        
        # Deduplicate
        unique_ids = list(set(matching_ids))
        dedup_count = len(matching_ids) - len(unique_ids)
        
        # Sort for consistency
        unique_ids.sort()
        
        # Save ID list
        ids_file = output_dir / f"{slice_id}_ids.txt"
        print(f"  💾 Saving IDs to: {ids_file}")
        with open(ids_file, 'w', encoding='utf-8') as f:
            for ab_id in unique_ids:
                f.write(f"{ab_id}\n")
        
        # Create manifest
        created_at = datetime.now().isoformat()
        manifest = {
            "slice_id": slice_id,
            "slice_name": slice_def["name"],
            "description": slice_def["description"],
            "filter_rules": slice_def.get("conditions", []) + (slice_def.get("or_conditions", []) if slice_def.get("or_conditions") else []),
            "created_from_file": str(truth_table_xlsx),
            "created_at": created_at,
            "count": len(unique_ids),
            "dedup_count": dedup_count,
            "total_matches_before_dedup": len(matching_ids),
        }
        
        # Save manifest
        manifest_file = output_dir / f"{slice_id}_manifest.json"
        print(f"  💾 Saving manifest to: {manifest_file}")
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        # Add to summary
        summary_rows.append({
            "slice_id": slice_id,
            "slice_name": slice_def["name"],
            "count": len(unique_ids),
            "dedup_count": dedup_count,
        })
        
        all_slice_results[slice_id] = {
            "count": len(unique_ids),
            "ids": unique_ids,
        }
        
        print(f"  ✅ {slice_id}: {len(unique_ids)} unique IDs (dedup: {dedup_count})")
    
    # Save summary CSV
    summary_csv = output_dir / "slice_summary.csv"
    print(f"\n💾 Saving summary to: {summary_csv}")
    with open(summary_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["slice_id", "slice_name", "count", "dedup_count"])
        writer.writeheader()
        writer.writerows(summary_rows)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 Reference Slices Summary")
    print("=" * 70)
    total_ids = sum(r["count"] for r in summary_rows)
    for row in summary_rows:
        print(f"  {row['slice_id']:30s}: {row['count']:4d} IDs (dedup: {row['dedup_count']})")
    print(f"\n  Total unique IDs across all slices: {total_ids}")
    print("=" * 70)
    
    return {
        "slices": all_slice_results,
        "summary": summary_rows,
    }


def main():
    parser = argparse.ArgumentParser(description="Export Reference Slices (1-7) from Truth Table")
    parser.add_argument("--truth_table_xlsx", default="data/thera_sabdab/out/thera_truth_table.xlsx",
                        help="Input Truth Table XLSX file")
    parser.add_argument("--output_dir", default="data/thera_sabdab/out/slice_ids",
                        help="Output directory for slice ID files and manifests")
    
    args = parser.parse_args()
    
    truth_table_xlsx = Path(args.truth_table_xlsx)
    if not truth_table_xlsx.is_absolute():
        truth_table_xlsx = PROJECT_ROOT / truth_table_xlsx
    
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    
    print("=" * 70)
    print("🚀 Exporting Reference Slices (1-7)")
    print("=" * 70)
    print(f"Truth Table: {truth_table_xlsx}")
    print(f"Output directory: {output_dir}")
    print("=" * 70)
    
    try:
        results = export_reference_slices(truth_table_xlsx, output_dir)
        print(f"\n✅ Reference Slices exported successfully!")
        print(f"   Output directory: {output_dir}")
        print(f"   Summary CSV: {output_dir / 'slice_summary.csv'}")
    except RuntimeError as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
