"""
CDR Canonical Analysis for VHH Classic Panel

CDR1/CDR2（canonical proxy + template compatibility）

Canonical layer is read-only: used for explainability and ranking only; 
it must not modify scaffold choice, sequence_final, or mutation rules in Classic Panel (P0).
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional


def extract_cdr_features(query_norm: Dict[str, Any]) -> Dict[str, Any]:
    """
    normalize_query_schema()CDR
    
    Args:
        query_norm: query，segments
    
    Returns:
        {
            "cdr1_seq": str,
            "cdr2_seq": str,
            "cdr1_len": int,
            "cdr2_len": int,
            "cdr1_proxy_class": str,  #  "L8"
            "cdr2_proxy_class": str,  #  "L8"
        }
    """
    segments = query_norm.get("segments", {})
    
    cdr1_seq = segments.get("CDR1", "")
    cdr2_seq = segments.get("CDR2", "")
    
    cdr1_len = len(cdr1_seq) if cdr1_seq else 0
    cdr2_len = len(cdr2_seq) if cdr2_seq else 0
    
    # Proxy class（：L{length}）
    cdr1_proxy_class = f"L{cdr1_len}" if cdr1_len > 0 else "L0"
    cdr2_proxy_class = f"L{cdr2_len}" if cdr2_len > 0 else "L0"
    
    return {
        "cdr1_seq": cdr1_seq,
        "cdr2_seq": cdr2_seq,
        "cdr1_len": cdr1_len,
        "cdr2_len": cdr2_len,
        "cdr1_proxy_class": cdr1_proxy_class,
        "cdr2_proxy_class": cdr2_proxy_class,
    }


def get_scaffold_canonical_profiles() -> Dict[str, Dict[str, Any]]:
    """
    scaffold canonical
    
    scaffold，。
    ClassChothia。
    
    Returns:
        {
            "IGHV3-23*01": {
                "canonical_system": "Chothia",
                "cdr1_len": int,  # scaffold.cdr1
                "cdr1_class": str,  # "C1", "C2", "C3"
                "cdr2_len": int,  # scaffold.cdr2
                "cdr2_class": str,
                "evidence": str,
            },
            ...
        }
    """
    from core.data.vhh_classic_scaffolds import get_classic_scaffold, get_all_scaffold_ids
    
    profiles = {}
    scaffold_ids = get_all_scaffold_ids()
    
    # Class（Chothia）
    # ：classscaffoldcanonical
    class_mapping = {
        "IGHV3-23*01": {"cdr1_class": "C1", "cdr2_class": "C3"},
        "IGHV3-66*01": {"cdr1_class": "C1", "cdr2_class": "C3"},
        "IGHV3-30*01": {"cdr1_class": "C1", "cdr2_class": "C2"},
        "IGHV3-7*01": {"cdr1_class": "C1", "cdr2_class": "C2"},
    }
    
    for scaffold_id in scaffold_ids:
        scaffold = get_classic_scaffold(scaffold_id)
        
        # scaffold
        cdr1_len = len(scaffold.cdr1) if scaffold.cdr1 else 0
        cdr2_len = len(scaffold.cdr2) if scaffold.cdr2 else 0
        
        # class
        class_info = class_mapping.get(scaffold_id, {"cdr1_class": None, "cdr2_class": None})
        
        profiles[scaffold_id] = {
            "canonical_system": "Chothia",
            "cdr1_len": cdr1_len,
            "cdr1_class": class_info.get("cdr1_class", ""),
            "cdr2_len": cdr2_len,
            "cdr2_class": class_info.get("cdr2_class", ""),
            "evidence": "derived_from_scaffold_sequence_v1",
        }
    
    return profiles


def build_canonical_compatibility(
    query_features: Dict[str, Any],
    scaffold_profiles: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    canonical
    
    scaffold：
    - cdr1_len_match / cdr2_len_match
    - cdr1_class_match / cdr2_class_match（class）
    - risk_level: low/medium/high
    - rationale: 
    
    （、）：
    - ：match → low；match → medium；match → high
    - class：classmatch
    
    Args:
        query_features: extract_cdr_features()
        scaffold_profiles: get_scaffold_canonical_profiles()
    
    Returns:
        {
            "IGHV3-23*01": {
                "cdr1_len_match": bool,
                "cdr2_len_match": bool,
                "cdr1_class_match": Optional[bool],
                "cdr2_class_match": Optional[bool],
                "risk_level": str,  # "low" | "medium" | "high"
                "rationale": str,
            },
            ...
        }
    """
    query_cdr1_len = query_features.get("cdr1_len", 0)
    query_cdr2_len = query_features.get("cdr2_len", 0)
    query_cdr1_class = query_features.get("cdr1_class")  # 
    query_cdr2_class = query_features.get("cdr2_class")  # 
    
    compatibility = {}
    
    for scaffold_id, profile in scaffold_profiles.items():
        scaffold_cdr1_len = profile.get("cdr1_len", 0)
        scaffold_cdr2_len = profile.get("cdr2_len", 0)
        scaffold_cdr1_class = profile.get("cdr1_class")
        scaffold_cdr2_class = profile.get("cdr2_class")
        
        # 
        cdr1_len_match = query_cdr1_len == scaffold_cdr1_len
        cdr2_len_match = query_cdr2_len == scaffold_cdr2_len
        
        # Class（）
        cdr1_class_match = None
        cdr2_class_match = None
        
        if query_cdr1_class and scaffold_cdr1_class:
            cdr1_class_match = query_cdr1_class == scaffold_cdr1_class
        
        if query_cdr2_class and scaffold_cdr2_class:
            cdr2_class_match = query_cdr2_class == scaffold_cdr2_class
        
        # 
        risk_level = "low"
        rationale_parts = []
        
        # （mismatch）
        if cdr1_len_match and cdr2_len_match:
            risk_level = "low"
            rationale_parts.append("CDR1 match; CDR2 match; risk=low")
        elif cdr1_len_match:
            risk_level = "medium"
            rationale_parts.append(
                f"CDR1 match; CDR2 length mismatch: query={query_cdr2_len} vs scaffold={scaffold_cdr2_len}; risk=medium"
            )
        elif cdr2_len_match:
            risk_level = "medium"
            rationale_parts.append(
                f"CDR1 length mismatch: query={query_cdr1_len} vs scaffold={scaffold_cdr1_len}; CDR2 match; risk=medium"
            )
        else:
            risk_level = "high"
            rationale_parts.append(
                f"CDR1 length mismatch: query={query_cdr1_len} vs scaffold={scaffold_cdr1_len}; "
                f"CDR2 length mismatch: query={query_cdr2_len} vs scaffold={scaffold_cdr2_len}; risk=high"
            )
        
        # Class（class）
        if cdr1_class_match is False:
            if risk_level == "low":
                risk_level = "medium"
            elif risk_level == "medium":
                risk_level = "high"
            rationale_parts.append("CDR1 canonical class mismatch")
        
        if cdr2_class_match is False:
            if risk_level == "low":
                risk_level = "medium"
            elif risk_level == "medium":
                risk_level = "high"
            rationale_parts.append("CDR2 canonical class mismatch")
        
        # rationale（）
        rationale = "; ".join(rationale_parts) if rationale_parts else "Canonical compatibility analysis complete"
        
        compatibility[scaffold_id] = {
            "cdr1_len_match": cdr1_len_match,
            "cdr2_len_match": cdr2_len_match,
            "cdr1_class_match": cdr1_class_match,
            "cdr2_class_match": cdr2_class_match,
            "risk_level": risk_level,
            "rationale": rationale,
        }
    
    return compatibility

