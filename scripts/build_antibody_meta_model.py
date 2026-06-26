#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/build_antibody_meta_model.py

Build Antibody Meta-Model: Map antibody records to structured state vectors.
"""

import sys
import json
import yaml
import hashlib
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_sequence_hash(seq: str) -> Optional[str]:
    """Get SHA256 hash of stripped sequence for deduplication."""
    if not seq or not isinstance(seq, str):
        return None
    seq_clean = seq.strip().upper().replace("-", "").replace(" ", "")
    if not seq_clean:
        return None
    return hashlib.sha256(seq_clean.encode('utf-8')).hexdigest()


def normalize_phase(phase_raw: str) -> str:
    """Normalize phase to bucket."""
    if not phase_raw or pd.isna(phase_raw):
        return "unknown"
    
    phase_upper = str(phase_raw).strip().upper()
    
    # Phase ≥ II
    if any(keyword in phase_upper for keyword in [
        "PHASE-II", "PHASE II", "PHASE_II", "PHASE2",
        "PHASE-III", "PHASE III", "PHASE_III", "PHASE3",
        "PHASE-I/II", "PHASE I/II", "PHASE_I/II", "PHASE1/2",
        "PHASE-II/III", "PHASE II/III", "PHASE_II/III", "PHASE2/3",
        "APPROVED", "MARKETED", "LAUNCHED",
    ]):
        return "phase_II_plus"
    
    # Phase I
    if "PHASE-I" in phase_upper or phase_upper == "PHASE I" or phase_upper == "PHASE_I" or phase_upper == "PHASE1":
        if "PHASE-I/II" not in phase_upper and "PHASE I/II" not in phase_upper:
            return "phase_I"
    
    # Preclinical
    if any(keyword in phase_upper for keyword in [
        "PRECLINICAL", "PRE-CLINICAL", "PRECLINIC",
        "TBC", "TO BE CONFIRMED",
        "IND", "INVESTIGATIONAL",
        "DISCOVERY", "RESEARCH",
    ]):
        return "preclinical"
    
    return "unknown"


def normalize_format(format_raw: str, chain_completeness: str) -> Tuple[str, bool]:
    """
    Normalize format to format_class and is_bispecific.
    
    Returns:
        (format_class, is_bispecific)
    """
    if not format_raw or pd.isna(format_raw):
        format_raw = ""
    
    format_upper = str(format_raw).strip().upper()
    
    # Check for bispecific indicators
    is_bispecific = any(keyword in format_upper for keyword in [
        "BISPECIFIC", "BI-SPECIFIC", "BISPEC", "BI-SPEC",
        "DUAL", "TANDEM", "TWO-TARGET",
    ])
    
    # Check for specific format classes
    if "VHH" in format_upper or "NANOBODY" in format_upper or "SINGLE DOMAIN" in format_upper:
        return ("VHH", False)
    
    if "ADC" in format_upper or "ANTIBODY-DRUG CONJUGATE" in format_upper:
        return ("ADC", is_bispecific)
    
    if "FUSION" in format_upper or "IMMUNOFUSION" in format_upper:
        return ("fusion", is_bispecific)
    
    if "RADIOLABELED" in format_upper or "RADIO" in format_upper:
        return ("radiolabeled", is_bispecific)
    
    if "SCFV" in format_upper or "SINGLE-CHAIN" in format_upper:
        if is_bispecific:
            return ("bispecific_scFv_like", True)
        else:
            return ("monospecific_IgG_Fab", False)  # scFv as monospecific
    
    if is_bispecific:
        return ("bispecific_IgG_like", True)
    
    # Default based on chain completeness
    if chain_completeness == "VH_VL":
        return ("monospecific_IgG_Fab", False)
    elif chain_completeness == "VH_ONLY":
        return ("VHH", False)
    else:
        return ("other_engineered", False)


def normalize_isotype(isotype_raw: str) -> Tuple[str, str, str, bool]:
    """
    Normalize isotype.
    
    Returns:
        (isotype_primary, isotype_secondary, isotype_set, engineered)
    """
    if not isotype_raw or pd.isna(isotype_raw):
        return ("na", "na", "na|na", False)
    
    isotype_str = str(isotype_raw).strip().upper()
    
    # Check for engineered indicators
    engineered = any(keyword in isotype_str for keyword in [
        "ENGINEERED", "MUTANT", "MUTATED", "MODIFIED",
        "SILENCED", "NULL", "KNOCKOUT",
    ])
    
    # Parse isotype (e.g., "G1", "G1|G1", "G1/G1")
    parts = isotype_str.replace("|", "/").split("/")
    parts = [p.strip() for p in parts if p.strip()]
    
    if not parts:
        return ("na", "na", "na|na", engineered)
    
    primary = parts[0]
    secondary = parts[1] if len(parts) > 1 else "na"
    
    # Normalize isotype values
    isotype_map = {
        "G1": "G1", "G2": "G2", "G3": "G3", "G4": "G4",
        "A": "A", "M": "M", "E": "E",
        "NA": "na", "N/A": "na", "": "na",
    }
    
    primary_norm = isotype_map.get(primary.upper(), primary.upper())
    secondary_norm = isotype_map.get(secondary.upper(), secondary.upper()) if secondary != "na" else "na"
    
    isotype_set = f"{primary_norm}|{secondary_norm}"
    
    return (primary_norm, secondary_norm, isotype_set, engineered)


def normalize_genetics(genetics_raw: str) -> Tuple[List[str], str, str]:
    """
    Normalize genetics information.
    
    Returns:
        (chain_level, normalized, human_origin_mode)
    """
    if not genetics_raw or pd.isna(genetics_raw):
        return ([], "unknown", "unknown")
    
    genetics_str = str(genetics_raw).strip()
    genetics_upper = genetics_str.upper()
    
    # First, check for multiple types in the string (e.g., "Chimeric and Humanised")
    has_murine = "MURINE" in genetics_upper or "MOUSE" in genetics_upper
    has_chimeric = "CHIMERIC" in genetics_upper
    has_humanised = "HUMANISED" in genetics_upper or "HUMANIZED" in genetics_upper
    has_human = "HUMAN" in genetics_upper and not has_humanised
    
    # Build normalized_chain_levels from detected types
    normalized_chain_levels = []
    if has_murine:
        normalized_chain_levels.append("murine")
    if has_chimeric:
        normalized_chain_levels.append("chimeric")
    if has_humanised:
        normalized_chain_levels.append("humanised")
    if has_human:
        normalized_chain_levels.append("genetically_human")
    
    # If no types detected, try splitting by semicolon for bispecifics
    if not normalized_chain_levels:
        chain_levels = [g.strip() for g in genetics_str.split(";") if g.strip()]
        for level in chain_levels:
            level_upper = level.upper()
            if "MURINE" in level_upper or "MOUSE" in level_upper:
                normalized_chain_levels.append("murine")
            elif "CHIMERIC" in level_upper:
                normalized_chain_levels.append("chimeric")
            elif "HUMANISED" in level_upper or "HUMANIZED" in level_upper:
                normalized_chain_levels.append("humanised")
            elif "HUMAN" in level_upper:
                normalized_chain_levels.append("genetically_human")
            else:
                normalized_chain_levels.append("other")
    
    if not normalized_chain_levels:
        return ([], "unknown", "unknown")
    
    # Remove duplicates while preserving order
    seen = set()
    normalized_chain_levels = [x for x in normalized_chain_levels if not (x in seen or seen.add(x))]
    
    # Determine normalized (overall)
    if len(normalized_chain_levels) == 1:
        normalized = normalized_chain_levels[0]
    else:
        # Mixed - determine normalized
        if "genetically_human" in normalized_chain_levels and "humanised" in normalized_chain_levels:
            normalized = "humanised_engineered"
        elif "humanised" in normalized_chain_levels:
            normalized = "humanised_engineered"
        else:
            normalized = "mixed"
    
    # Determine human_origin_mode
    if normalized == "genetically_human":
        human_origin_mode = "natural_human_repertoire"
    elif normalized in ["humanised", "humanised_engineered"]:
        human_origin_mode = "engineered_humanisation"
    elif normalized == "murine":
        human_origin_mode = "non_human"
    else:
        human_origin_mode = "mixed"
    
    return (normalized_chain_levels, normalized, human_origin_mode)


def parse_targets(target_raw: str) -> Tuple[int, List[str]]:
    """Parse target information."""
    if not target_raw or pd.isna(target_raw):
        return (0, [])
    
    target_str = str(target_raw).strip()
    
    # Split by common delimiters
    targets = []
    for delimiter in [";", ",", "/", "|"]:
        if delimiter in target_str:
            targets = [t.strip() for t in target_str.split(delimiter) if t.strip()]
            break
    
    if not targets:
        targets = [target_str] if target_str else []
    
    return (len(targets), targets)


def determine_engineering_level(
    format_class: str,
    isotype_engineered: bool,
    genetics_normalized: str,
    is_bispecific: bool,
) -> str:
    """Determine engineering level."""
    if is_bispecific or format_class in ["ADC", "fusion", "radiolabeled"]:
        return "heavily_engineered"
    
    if format_class in ["bispecific_IgG_like", "bispecific_scFv_like"]:
        return "heavily_engineered"
    
    if isotype_engineered:
        return "fc_engineered"
    
    if format_class == "scFv":
        return "format_engineered"
    
    if genetics_normalized in ["humanised", "humanised_engineered"]:
        return "minimal"  # Humanization is considered minimal
    
    return "minimal"


def build_antibody_meta_model(
    entry: Dict[str, Any],
    qc_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build antibody meta-model from raw entry and optional QC result.
    
    Args:
        entry: Raw Thera-SAbDab entry
        qc_result: Optional QC result from prepare_thera_dataset.py
    
    Returns:
        Structured antibody meta-model
    """
    # Get basic info
    antibody_id = entry.get("Therapeutic", "") or entry.get("INN", "") or entry.get("Name", "")
    name = antibody_id
    
    # Clinical
    phase_raw = entry.get("Highest_Clin_Trial (Feb '25)", "") or entry.get("Phase", "") or ""
    phase_bucket = normalize_phase(phase_raw)
    
    # Format
    format_raw = entry.get("Format", "") or ""
    chain_completeness = qc_result.get("chain_completeness", "VH_VL") if qc_result else "VH_VL"
    format_class, is_bispecific = normalize_format(format_raw, chain_completeness)
    
    # FC
    isotype_raw = entry.get("CH1 Isotype", "") or ""
    isotype_primary, isotype_secondary, isotype_set, isotype_engineered = normalize_isotype(isotype_raw)
    
    # Effector intent (heuristic)
    if isotype_engineered:
        effector_intent = "silenced" if "NULL" in str(isotype_raw).upper() or "SILENCED" in str(isotype_raw).upper() else "unknown"
    else:
        effector_intent = "ADCC_high" if isotype_primary in ["G1", "G3"] else "unknown"
    
    # Genetics
    genetics_raw = entry.get("Genetics (Bispecifics delimited with semicolon)", "") or ""
    chain_level, genetics_normalized, human_origin_mode = normalize_genetics(genetics_raw)
    
    # Target
    target_raw = entry.get("Target", "") or ""
    target_count, targets = parse_targets(target_raw)
    
    # Engineering
    engineering_level = determine_engineering_level(
        format_class, isotype_engineered, genetics_normalized, is_bispecific
    )
    notes_raw = entry.get("Notes", "")
    notes = "" if (not notes_raw or pd.isna(notes_raw) or str(notes_raw).strip().upper() in ["NA", "N/A", "NAN", ""]) else str(notes_raw).strip()
    
    # Sequence
    heavy_seq = entry.get("HeavySequence", "") or ""
    light_seq = entry.get("LightSequence", "") or ""
    has_heavy = bool(heavy_seq and str(heavy_seq).strip() and str(heavy_seq).strip().upper() not in ["NA", "N/A", ""])
    has_light = bool(light_seq and str(light_seq).strip() and str(light_seq).strip().upper() not in ["NA", "N/A", ""])
    
    # Use QC result hashes if available, otherwise compute
    if qc_result:
        heavy_hash = qc_result.get("heavy_hash", get_sequence_hash(heavy_seq))
        light_hash = qc_result.get("light_hash", get_sequence_hash(light_seq))
    else:
        heavy_hash = get_sequence_hash(heavy_seq)
        light_hash = get_sequence_hash(light_seq)
    
    # Build meta-model
    meta_model = {
        "antibody_id": antibody_id,
        "name": name,
        "source_db": "thera_sabdab",
        "clinical": {
            "phase_bucket": phase_bucket,
            "phase_raw": str(phase_raw) if phase_raw else "",
        },
        "format": {
            "format_class": format_class,
            "chain_completeness": chain_completeness,
            "is_bispecific": is_bispecific,
            "format_raw": format_raw,
        },
        "fc": {
            "isotype_primary": isotype_primary,
            "isotype_secondary": isotype_secondary,
            "isotype_set": isotype_set,
            "engineered": isotype_engineered,
            "effector_intent": effector_intent,
        },
        "genetics": {
            "chain_level": chain_level,
            "normalized": genetics_normalized,
            "human_origin_mode": human_origin_mode,
            "genetics_raw": genetics_raw,
        },
        "target": {
            "target_count": target_count,
            "targets": targets,
            "target_raw": str(target_raw) if target_raw else "",
        },
        "engineering": {
            "engineering_level": engineering_level,
            "notes": str(notes) if notes else "",
        },
        "sequence": {
            "has_heavy": has_heavy,
            "has_light": has_light,
            "heavy_hash": heavy_hash or "",
            "light_hash": light_hash or "",
        },
    }
    
    return meta_model


def main():
    parser = argparse.ArgumentParser(description="Build Antibody Meta-Model from Thera-SAbDab data")
    parser.add_argument("--in_xlsx", required=True, help="Input Thera-SAbDab export XLSX file")
    parser.add_argument("--qc_pass_xlsx", help="QC pass XLSX from prepare_thera_dataset.py (optional)")
    parser.add_argument("--out_json", default="data/thera_sabdab/out/antibody_meta_models.json",
                        help="Output JSON file")
    parser.add_argument("--out_yaml", help="Output YAML file (optional)")
    parser.add_argument("--limit", type=int, help="Limit processing to first N entries (for testing)")
    
    args = parser.parse_args()
    
    in_xlsx = Path(args.in_xlsx)
    if not in_xlsx.is_absolute():
        in_xlsx = PROJECT_ROOT / in_xlsx
    
    out_json = Path(args.out_json)
    if not out_json.is_absolute():
        out_json = PROJECT_ROOT / out_json
    
    out_json.parent.mkdir(parents=True, exist_ok=True)
    
    # Load raw data
    print(f"📖 Loading: {in_xlsx}")
    df = pd.read_excel(in_xlsx, engine='openpyxl')
    
    if args.limit and args.limit > 0:
        df = df.head(args.limit)
        print(f"⚠️  Limited to first {len(df)} entries")
    
    # Load QC results if provided
    qc_results = {}
    if args.qc_pass_xlsx:
        qc_path = Path(args.qc_pass_xlsx)
        if not qc_path.is_absolute():
            qc_path = PROJECT_ROOT / qc_path
        
        if qc_path.exists():
            print(f"📖 Loading QC results: {qc_path}")
            qc_df = pd.read_excel(qc_path, engine='openpyxl')
            for _, row in qc_df.iterrows():
                name = row.get("Name", "") or row.get("INN", "")
                if name:
                    qc_results[name] = {
                        "chain_completeness": row.get("chain_completeness", "VH_VL"),
                        "format_type": row.get("format_type", ""),
                        "heavy_hash": row.get("heavy_hash", ""),
                        "light_hash": row.get("light_hash", ""),
                    }
    
    # Build meta-models
    print(f"\n🔬 Building meta-models for {len(df)} entries...")
    meta_models = []
    
    for idx, row in df.iterrows():
        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(df)}...")
        
        entry = row.to_dict()
        name = entry.get("Therapeutic", "") or entry.get("INN", "") or ""
        qc_result = qc_results.get(name, {})
        
        meta_model = build_antibody_meta_model(entry, qc_result)
        meta_models.append(meta_model)
    
    # Save JSON
    print(f"\n💾 Saving to: {out_json}")
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(meta_models, f, indent=2, ensure_ascii=False)
    
    # Save YAML if requested
    if args.out_yaml:
        out_yaml = Path(args.out_yaml)
        if not out_yaml.is_absolute():
            out_yaml = PROJECT_ROOT / out_yaml
        out_yaml.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"💾 Saving to: {out_yaml}")
        with open(out_yaml, 'w', encoding='utf-8') as f:
            yaml.safe_dump(meta_models, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n✅ Generated {len(meta_models)} antibody meta-models")
    print(f"   Output: {out_json}")


if __name__ == "__main__":
    main()
