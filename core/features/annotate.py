"""
Feature Annotation Module

 residue-level 。
"""

from typing import Dict, List, Any, Optional
import pandas as pd

from core.features.feature_dict_v1 import (
    parse_imgt_position,
    get_region_from_imgt_pos,
    is_vernier_position,
    is_vh_hallmark_position,
    is_cdr_boundary,
    is_cdr_core,
    is_cdr3_key_position,
    is_chemically_sensitive
)


def annotate_features(mapping_result: Dict[str, Any], chain_name: str) -> Dict[str, Any]:
    """
    mapping
    
    Args:
        mapping_result: dual_map JSON，：
            - variable_domain_sequence: str
            - variable_domain: dict ( v_start, v_end, v_length)
            - dual_map: List[Dict] ( v_length)
            - imgt_numbering: Dict[str, str]
            - kabat_numbering: Dict[str, str]
            - chain_type: str ("H", "K", "L")
        chain_name:  ("VH", "VL")
    
    Returns:
        {
            "chain": str,
            "length": int,
            "residues": [
                {
                    "index": int,
                    "residue": str,
                    "imgt_position": str or None,
                    "kabat_position": str or None,
                    "region": str or None,
                    "tags": List[str]
                },
                ...
            ]
        }
    
    Raises:
        ValueError: 
    """
    variable_domain_sequence = mapping_result.get("variable_domain_sequence", "")
    variable_domain = mapping_result.get("variable_domain", {})
    dual_map = mapping_result.get("dual_map", [])
    chain_type = mapping_result.get("chain_type", "H")
    
    v_length = variable_domain.get("v_length") or variable_domain.get("variable_domain_length")
    
    # 
    if v_length is None:
        raise ValueError("variable_domain.v_length or variable_domain_length is missing")
    
    if len(variable_domain_sequence) != v_length:
        raise ValueError(
            f"Length mismatch: variable_domain_sequence length ({len(variable_domain_sequence)}) != v_length ({v_length})"
        )
    
    if len(dual_map) != v_length:
        raise ValueError(
            f"Length mismatch: dual_map length ({len(dual_map)}) != v_length ({v_length})"
        )
    
    # 
    residues = []
    for i, residue_entry in enumerate(dual_map):
        aa = residue_entry.get("aa", "")
        seq_idx = residue_entry.get("seq_idx", i)
        imgt_pos_str = residue_entry.get("imgt_pos", "")
        kabat_pos = residue_entry.get("kabat_pos")
        
        imgt_pos = parse_imgt_position(imgt_pos_str)
        region = get_region_from_imgt_pos(imgt_pos)
        
        tags = []
        
        # 1. （）
        if region:
            tags.append(region)
        
        # 2. Vernier Zone
        if is_vernier_position(imgt_pos, chain_type):
            tags.append("vernier")
        
        # 3. VH Hallmark Framework Positions
        if is_vh_hallmark_position(imgt_pos, chain_type):
            tags.append("vh_hallmark")
        
        # 4. CDR
        if is_cdr_boundary(imgt_pos, region, dual_map):
            tags.append("cdr_boundary")
        
        # 5. CDR
        if is_cdr_core(imgt_pos, region, dual_map):
            tags.append("cdr_core")
        
        # 6. CDR3
        if is_cdr3_key_position(imgt_pos, region):
            tags.append("cdr3_key")
        
        # 7. 
        if is_chemically_sensitive(aa):
            tags.append("chem_sensitive")
        
        # （）
        tags = sorted(list(set(tags)))
        
        residues.append({
            "index": seq_idx,
            "residue": aa,
            "imgt_position": imgt_pos_str if imgt_pos_str else None,
            "kabat_position": kabat_pos if kabat_pos and kabat_pos != "None" else None,
            "region": region,
            "tags": tags
        })
    
    return {
        "chain": chain_name,
        "length": v_length,
        "residues": residues
    }


def export_feature_matrix(annotated: Dict[str, Any]) -> pd.DataFrame:
    """
    pandas DataFrame（Excel）
    
    Args:
        annotated: annotate_features
    
    Returns:
        pandas DataFrame，：
        - index: 0-based index
        - residue: 
        - imgt_position: IMGT
        - kabat_position: Kabat
        - region: 
        - tags: （ ; ）
    """
    rows = []
    for residue in annotated["residues"]:
        rows.append({
            "index": residue["index"],
            "residue": residue["residue"],
            "imgt_position": residue["imgt_position"] or "",
            "kabat_position": residue["kabat_position"] or "",
            "region": residue["region"] or "",
            "tags": "; ".join(residue["tags"]) if residue["tags"] else ""
        })
    
    return pd.DataFrame(rows)








