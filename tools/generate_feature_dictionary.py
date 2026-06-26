#!/usr/bin/env python3
"""
PD-1 Antibody Feature Dictionary v1 Generator

 dual_map JSON 。
 = （list），、、。

：
- imgt_position
- kabat_position
- region (FR/CDR)
- chain_type
- aa (amino acid)
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import re


# IMGT
IMGT_REGIONS = {
    "FR1": {"start": 1, "end": 26},
    "CDR1": {"start": 27, "end": 38},
    "FR2": {"start": 39, "end": 55},
    "CDR2": {"start": 56, "end": 65},
    "FR3": {"start": 66, "end": 104},
    "CDR3": {"start": 105, "end": 117},
    "FR4": {"start": 118, "end": 128}
}

# Vernier Zone positions (VH/VL)
VERNIER_POSITIONS = {
    "VH": [4, 6, 23, 24, 26, 48, 49, 67, 69, 71, 73, 78, 93],
    "VL": [4, 6, 23, 24, 26, 48, 49, 67, 69, 71, 73, 78]
}

# VH Hallmark Framework Positions
VH_HALLMARK_POSITIONS = [42, 49, 50, 52, 54]

# Framework Anchor positions (，，)
FRAMEWORK_ANCHOR_POSITIONS = {
    "FR1": [1, 2, 3, 23, 24, 26],
    "FR2": [39, 41, 45, 55],
    "FR3": [66, 67, 69, 71, 73, 78, 93],
    "FR4": [118, 120, 122, 128]
}

# 
CHEMICALLY_SENSITIVE_RESIDUES = {"N", "D", "G", "M", "W", "C"}


def parse_imgt_position(imgt_pos: str) -> Optional[int]:
    """IMGT，"""
    if not imgt_pos or imgt_pos == "None":
        return None
    # （ "27A" -> 27, "100" -> 100）
    match = re.match(r"^(\d+)", str(imgt_pos))
    if match:
        return int(match.group(1))
    return None


def get_region_from_imgt_pos(imgt_pos: Optional[int]) -> Optional[str]:
    """IMGT"""
    if imgt_pos is None:
        return None
    
    if IMGT_REGIONS["FR1"]["start"] <= imgt_pos <= IMGT_REGIONS["FR1"]["end"]:
        return "FR1"
    elif IMGT_REGIONS["CDR1"]["start"] <= imgt_pos <= IMGT_REGIONS["CDR1"]["end"]:
        return "CDR1"
    elif IMGT_REGIONS["FR2"]["start"] <= imgt_pos <= IMGT_REGIONS["FR2"]["end"]:
        return "FR2"
    elif IMGT_REGIONS["CDR2"]["start"] <= imgt_pos <= IMGT_REGIONS["CDR2"]["end"]:
        return "CDR2"
    elif IMGT_REGIONS["FR3"]["start"] <= imgt_pos <= IMGT_REGIONS["FR3"]["end"]:
        return "FR3"
    elif IMGT_REGIONS["CDR3"]["start"] <= imgt_pos <= IMGT_REGIONS["CDR3"]["end"]:
        return "CDR3"
    elif IMGT_REGIONS["FR4"]["start"] <= imgt_pos <= IMGT_REGIONS["FR4"]["end"]:
        return "FR4"
    return None


def is_vernier_position(imgt_pos: Optional[int], chain_type: str) -> bool:
    """Vernier Zone"""
    if imgt_pos is None:
        return False
    chain_key = "VH" if chain_type == "H" else "VL"
    return imgt_pos in VERNIER_POSITIONS.get(chain_key, [])


def is_vh_hallmark_position(imgt_pos: Optional[int], chain_type: str) -> bool:
    """VH Hallmark"""
    if chain_type != "H" or imgt_pos is None:
        return False
    return imgt_pos in VH_HALLMARK_POSITIONS


def is_framework_anchor(imgt_pos: Optional[int], region: Optional[str]) -> bool:
    """Framework Anchor"""
    if imgt_pos is None or region is None:
        return False
    if region not in FRAMEWORK_ANCHOR_POSITIONS:
        return False
    return imgt_pos in FRAMEWORK_ANCHOR_POSITIONS[region]


def is_cdr_boundary(imgt_pos: Optional[int], region: Optional[str], dual_map: List[Dict]) -> bool:
    """CDR"""
    if imgt_pos is None or region is None:
        return False
    
    # FR -> CDR CDR（CDR）
    if region == "CDR1" and imgt_pos == IMGT_REGIONS["CDR1"]["start"]:
        return True
    if region == "CDR2" and imgt_pos == IMGT_REGIONS["CDR2"]["start"]:
        return True
    if region == "CDR3" and imgt_pos == IMGT_REGIONS["CDR3"]["start"]:
        return True
    
    # CDR -> FR CDR（CDR）
    # 
    if region == "CDR1" and imgt_pos == IMGT_REGIONS["CDR1"]["end"]:
        # dual_map
        for res in dual_map:
            if parse_imgt_position(res.get("imgt_pos", "")) == imgt_pos:
                return True
        return False
    
    if region == "CDR2" and imgt_pos == IMGT_REGIONS["CDR2"]["end"]:
        for res in dual_map:
            if parse_imgt_position(res.get("imgt_pos", "")) == imgt_pos:
                return True
        return False
    
    if region == "CDR3":
        # CDR3：CDR3IMGT
        cdr3_max_pos = IMGT_REGIONS["CDR3"]["end"]
        actual_cdr3_max = None
        for res in dual_map:
            pos = parse_imgt_position(res.get("imgt_pos", ""))
            if pos and IMGT_REGIONS["CDR3"]["start"] <= pos <= IMGT_REGIONS["CDR3"]["end"]:
                if actual_cdr3_max is None or pos > actual_cdr3_max:
                    actual_cdr3_max = pos
        
        # CDR3，
        if actual_cdr3_max and imgt_pos == actual_cdr3_max:
            return True
    
    return False


def is_cdr_core(imgt_pos: Optional[int], region: Optional[str], dual_map: List[Dict]) -> bool:
    """CDR（CDR，）"""
    if imgt_pos is None or region is None:
        return False
    
    if region not in ["CDR1", "CDR2", "CDR3"]:
        return False
    
    # 
    if is_cdr_boundary(imgt_pos, region, dual_map):
        return False
    
    # ：CDR
    region_info = IMGT_REGIONS[region]
    region_length = region_info["end"] - region_info["start"] + 1
    mid_start = region_info["start"] + region_length // 4
    mid_end = region_info["end"] - region_length // 4
    
    return mid_start <= imgt_pos <= mid_end


def is_cdr3_key_position(imgt_pos: Optional[int], region: Optional[str]) -> bool:
    """CDR3（CDR3）"""
    return region == "CDR3" and imgt_pos is not None


def is_chemically_sensitive(aa: str) -> bool:
    """"""
    return aa in CHEMICALLY_SENSITIVE_RESIDUES


def generate_residue_features(
    residue: Dict[str, Any],
    chain_type: str,
    dual_map: List[Dict]
) -> Dict[str, Any]:
    """
    
    
    Args:
        residue: dual_map
        chain_type:  ("H", "K", "L")
        dual_map: dual_map
    
    Returns:
        
    """
    aa = residue.get("aa", "")
    seq_idx = residue.get("seq_idx", -1)
    imgt_pos_str = residue.get("imgt_pos", "")
    kabat_pos = residue.get("kabat_pos")
    
    imgt_pos = parse_imgt_position(imgt_pos_str)
    region = get_region_from_imgt_pos(imgt_pos)
    
    tags = []
    
    # 1. 
    if region:
        tags.append(region)
    
    # 2. Vernier Zone
    if is_vernier_position(imgt_pos, chain_type):
        tags.append("vernier")
    
    # 3. VH Hallmark Framework Positions
    if is_vh_hallmark_position(imgt_pos, chain_type):
        tags.append("vh_hallmark")
    
    # 4. Framework Anchor
    if is_framework_anchor(imgt_pos, region):
        tags.append("framework_anchor")
    
    # 5. CDR
    if is_cdr_boundary(imgt_pos, region, dual_map):
        tags.append("cdr_boundary")
    
    # 6. CDR
    if is_cdr_core(imgt_pos, region, dual_map):
        tags.append("cdr_core")
    
    # 7. CDR3
    if is_cdr3_key_position(imgt_pos, region):
        tags.append("cdr3_key")
    
    # 8. 
    if is_chemically_sensitive(aa):
        tags.append("chem_sensitive")
    
    return {
        "chain": "VH" if chain_type == "H" else ("VL" if chain_type in ["K", "L"] else "UNKNOWN"),
        "residue": aa,
        "index": seq_idx,
        "imgt_position": imgt_pos_str if imgt_pos_str else None,
        "kabat_position": kabat_pos if kabat_pos and kabat_pos != "None" else None,
        "region": region,
        "tags": sorted(tags)  # 
    }


def generate_feature_dictionary(
    dual_map_json_path: str,
    antibody_name: str = "PD-1",
    pdb_id: str = "6JBT",
    species: str = "mouse"
) -> Dict[str, Any]:
    """
    dual_map JSON
    
    Args:
        dual_map_json_path: dual_map JSON
        antibody_name: 
        pdb_id: PDB ID
        species: 
    
    Returns:
        JSON
    """
    with open(dual_map_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    chain_type = data.get("chain_type", "H")
    dual_map = data.get("dual_map", [])
    
    # 
    features = []
    for residue in dual_map:
        feature = generate_residue_features(residue, chain_type, dual_map)
        features.append(feature)
    
    # 
    chain_name = "VH" if chain_type == "H" else ("VL" if chain_type in ["K", "L"] else "UNKNOWN")
    
    result = {
        "antibody": antibody_name,
        "pdb_id": pdb_id,
        "species": species,
        "version": "feature_dict_v1",
        "chains": {
            chain_name: {
                "chain_type": chain_type,
                "features": features
            }
        }
    }
    
    return result


def main:
    parser = argparse.ArgumentParser(
        description="Generate PD-1 Antibody Feature Dictionary v1 from dual_map JSON"
    )
    parser.add_argument(
        "--dual_map_json",
        type=str,
        required=True,
        help="Path to dual_map JSON file"
    )
    parser.add_argument(
        "--out_json",
        type=str,
        required=True,
        help="Output JSON file path"
    )
    parser.add_argument(
        "--antibody",
        type=str,
        default="PD-1",
        help="Antibody name (default: PD-1)"
    )
    parser.add_argument(
        "--pdb_id",
        type=str,
        default="6JBT",
        help="PDB ID (default: 6JBT)"
    )
    parser.add_argument(
        "--species",
        type=str,
        default="mouse",
        help="Species (default: mouse)"
    )
    
    args = parser.parse_args
    
    print(f"📖 Reading dual_map JSON: {args.dual_map_json}")
    feature_dict = generate_feature_dictionary(
        args.dual_map_json,
        antibody_name=args.antibody,
        pdb_id=args.pdb_id,
        species=args.species
    )
    
    # 
    output_path = Path(args.out_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(feature_dict, f, indent=2, ensure_ascii=False)
    
    chain_name = list(feature_dict["chains"].keys)[0]
    num_features = len(feature_dict["chains"][chain_name]["features"])
    
    print(f"✅ Feature dictionary generated: {args.out_json}")
    print(f"   Chain: {chain_name}")
    print(f"   Residues: {num_features}")
    
    # 
    tag_counts = {}
    for feature in feature_dict["chains"][chain_name]["features"]:
        for tag in feature.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    print(f"   Tag statistics:")
    for tag, count in sorted(tag_counts.items):
        print(f"     - {tag}: {count}")


if __name__ == "__main__":
    main








