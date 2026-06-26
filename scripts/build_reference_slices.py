#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/build_reference_slices.py

Build Standard Reference Slices from Antibody Meta-Models.
Slices are reusable filter conditions for canonical/germline/humanization analysis.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def apply_slice_filter(meta_model: Dict[str, Any], slice_definition: Dict[str, Any]) -> bool:
    """
    Apply slice filter conditions to a meta-model.
    
    Args:
        meta_model: Antibody meta-model dictionary
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


def build_slice_definitions() -> Dict[str, Dict[str, Any]]:
    """Define all standard reference slices."""
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


def build_slices(meta_models: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build all reference slices from meta-models."""
    slice_definitions = build_slice_definitions()
    slices_result = {}
    
    for slice_id, slice_def in slice_definitions.items():
        matching_models = []
        
        for meta_model in meta_models:
            if slice_id == "slice_7_exclusion":
                if apply_slice_with_or(meta_model, slice_def):
                    matching_models.append(meta_model)
            else:
                if apply_slice_filter(meta_model, slice_def):
                    matching_models.append(meta_model)
        
        # Extract antibody IDs
        antibody_ids = [m["antibody_id"] for m in matching_models]
        
        slices_result[slice_id] = {
            "name": slice_def["name"],
            "description": slice_def["description"],
            "count": len(matching_models),
            "antibody_ids": antibody_ids,
            "meta_models": matching_models,  # Full data for detailed analysis
        }
        
        # Special handling for slice_5 (group by)
        if slice_id == "slice_5_fc_target_design" and "group_by" in slice_def:
            group_by_stats = defaultdict(int)
            for model in matching_models:
                targets = model.get("target", {}).get("targets", [])
                isotype = model.get("fc", {}).get("isotype_primary", "na")
                
                # Create group key
                targets_str = ";".join(sorted(targets)) if targets else "no_target"
                group_key = f"{targets_str}|{isotype}"
                group_by_stats[group_key] += 1
            
            slices_result[slice_id]["group_by_stats"] = dict(group_by_stats)
    
    return slices_result


def main():
    parser = argparse.ArgumentParser(description="Build Standard Reference Slices from Antibody Meta-Models")
    parser.add_argument("--in_json", required=True, help="Input antibody meta-models JSON file")
    parser.add_argument("--out_json", default="data/thera_sabdab/out/reference_slices.json",
                        help="Output slices JSON file")
    parser.add_argument("--out_summary", help="Output summary text file (optional)")
    parser.add_argument("--export_ids_only", action="store_true",
                        help="Export only antibody ID lists (one file per slice)")
    parser.add_argument("--ids_dir", default="data/thera_sabdab/out/slice_ids",
                        help="Directory for slice ID files (if --export_ids_only)")
    
    args = parser.parse_args()
    
    in_json = Path(args.in_json)
    if not in_json.is_absolute():
        in_json = PROJECT_ROOT / in_json
    
    out_json = Path(args.out_json)
    if not out_json.is_absolute():
        out_json = PROJECT_ROOT / out_json
    
    out_json.parent.mkdir(parents=True, exist_ok=True)
    
    # Load meta-models
    print(f"📖 Loading meta-models: {in_json}")
    with open(in_json, 'r', encoding='utf-8') as f:
        meta_models = json.load(f)
    
    print(f"✅ Loaded {len(meta_models)} antibody meta-models")
    
    # Build slices
    print(f"\n🔬 Building reference slices...")
    slices_result = build_slices(meta_models)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 Reference Slices Summary")
    print("=" * 70)
    
    for slice_id, slice_data in slices_result.items():
        print(f"\n🟦 {slice_data['name']}")
        print(f"   Description: {slice_data['description']}")
        print(f"   Count: {slice_data['count']} antibodies")
        if "group_by_stats" in slice_data:
            print(f"   Group by combinations: {len(slice_data['group_by_stats'])}")
    
    print("\n" + "=" * 70)
    
    # Save full slices JSON
    print(f"\n💾 Saving slices to: {out_json}")
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(slices_result, f, indent=2, ensure_ascii=False)
    
    # Export ID lists if requested
    if args.export_ids_only:
        ids_dir = Path(args.ids_dir)
        if not ids_dir.is_absolute():
            ids_dir = PROJECT_ROOT / ids_dir
        ids_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n💾 Exporting ID lists to: {ids_dir}")
        for slice_id, slice_data in slices_result.items():
            ids_file = ids_dir / f"{slice_id}.txt"
            with open(ids_file, 'w', encoding='utf-8') as f:
                for ab_id in slice_data["antibody_ids"]:
                    f.write(f"{ab_id}\n")
            print(f"   {slice_id}: {len(slice_data['antibody_ids'])} IDs -> {ids_file.name}")
    
    # Save summary text if requested
    if args.out_summary:
        summary_path = Path(args.out_summary)
        if not summary_path.is_absolute():
            summary_path = PROJECT_ROOT / summary_path
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("Reference Slices Summary\n")
            f.write("=" * 70 + "\n\n")
            
            for slice_id, slice_data in slices_result.items():
                f.write(f"🟦 {slice_data['name']}\n")
                f.write(f"   Description: {slice_data['description']}\n")
                f.write(f"   Count: {slice_data['count']} antibodies\n")
                f.write(f"   Slice ID: {slice_id}\n")
                
                if "group_by_stats" in slice_data:
                    f.write(f"   Group by combinations: {len(slice_data['group_by_stats'])}\n")
                    f.write("   Top 10 combinations:\n")
                    sorted_stats = sorted(slice_data['group_by_stats'].items(), 
                                        key=lambda x: x[1], reverse=True)[:10]
                    for key, count in sorted_stats:
                        f.write(f"     {key}: {count}\n")
                
                f.write("\n")
        
        print(f"💾 Summary saved to: {summary_path}")
    
    print(f"\n✅ Generated {len(slices_result)} reference slices")
    print(f"   Output: {out_json}")


if __name__ == "__main__":
    main()
