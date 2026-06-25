"""
VHH Classic Panel Gate (Pre-flight Check)

Gatepanel、。
Gateread-only，sequence_finalmutations。
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional
from core.data.vhh_classic_scaffolds import (
    get_classic_scaffold,
    get_all_scaffold_ids,
)


# （MVP）
CDR3_LEN_USE_J6 = 18
CDR3_LEN_ULTRA_LONG = 22
EXTRA_CYS_WARN_THRESHOLD = 2  # total_Cys_count > 2 -> warn
FR_IDENTITY_WARN = 0.60  # best FR-only identity < 0.60 -> warn
FR_IDENTITY_FAIL = 0.50  # best FR-only identity < 0.50 -> fail/manual review


def run_vhh_gate(
    query_norm: Dict[str, Any],
    scaffolds: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    VHH Gate
    
    Gateread-only：scaffold choice、graft/mutation、
    sequence_final。、。
    
    Args:
        query_norm: query，segments（FR1/FR2/FR3/CDR3/FR4）
        scaffolds: scaffold（None，4classic scaffold）
    
    Returns:
        gate，pass_level、flags、metrics、recommendations
    """
    segments = query_norm.get("segments", {})
    
    # ========================================================================
    # 1. 
    # ========================================================================
    
    # 1.1 CDR3
    cdr3_seq = segments.get("CDR3", segments.get("cdr3", ""))
    cdr3_len = len(cdr3_seq) if cdr3_seq else 0
    
    # 1.2 Cys
    # variable_domain，v_region，
    total_cys_count = 0
    if "variable_domain" in query_norm:
        total_cys_count = query_norm["variable_domain"].count("C")
    elif "v_region" in query_norm:
        total_cys_count = query_norm["v_region"].count("C")
    elif "sequence" in query_norm:
        total_cys_count = query_norm["sequence"].count("C")
    else:
        # segments
        full_seq = (
            segments.get("FR1", "") +
            segments.get("CDR1", "") +
            segments.get("FR2", "") +
            segments.get("CDR2", "") +
            segments.get("FR3", "") +
            segments.get("CDR3", "") +
            segments.get("FR4", "")
        )
        total_cys_count = full_seq.count("C")
    
    # 1.3 FR-only identity（scaffold）
    query_fr1 = segments.get("FR1", segments.get("fr1", ""))
    query_fr2 = segments.get("FR2", segments.get("fr2", ""))
    query_fr3 = segments.get("FR3", segments.get("fr3", ""))
    query_fr4 = segments.get("FR4", segments.get("fr4", ""))
    
    # queryFR（FR4，FR1-3）
    if query_fr4:
        query_fr_concatenated = query_fr1 + query_fr2 + query_fr3 + query_fr4
    else:
        query_fr_concatenated = query_fr1 + query_fr2 + query_fr3
    
    # scaffold IDs
    if scaffolds is None:
        scaffold_ids = get_all_scaffold_ids()
    else:
        scaffold_ids = list(scaffolds.keys())
    
    # scaffoldFR identity
    best_fr_identity = 0.0
    best_scaffold_id = None
    length_mismatch = False
    
    for scaffold_id in scaffold_ids:
        if scaffolds is None:
            scaffold = get_classic_scaffold(scaffold_id)
            scaffold_fr1 = scaffold.fr1
            scaffold_fr2 = scaffold.fr2
            scaffold_fr3 = scaffold.fr3
            scaffold_fr4 = ""  # Classic scaffoldFR4
        else:
            scaffold_data = scaffolds[scaffold_id]
            scaffold_fr1 = scaffold_data.get("fr1", "")
            scaffold_fr2 = scaffold_data.get("fr2", "")
            scaffold_fr3 = scaffold_data.get("fr3", "")
            scaffold_fr4 = scaffold_data.get("fr4", "")
        
        # scaffoldFR
        if scaffold_fr4:
            scaffold_fr_concatenated = scaffold_fr1 + scaffold_fr2 + scaffold_fr3 + scaffold_fr4
        else:
            scaffold_fr_concatenated = scaffold_fr1 + scaffold_fr2 + scaffold_fr3
        
        # identity
        identity, has_mismatch = _calculate_identity(
            query_fr_concatenated,
            scaffold_fr_concatenated
        )
        
        if identity > best_fr_identity:
            best_fr_identity = identity
            best_scaffold_id = scaffold_id
            length_mismatch = has_mismatch
    
    # ========================================================================
    # 2. flags
    # ========================================================================
    flags = []
    
    if cdr3_len >= CDR3_LEN_ULTRA_LONG:
        flags.append("cdr3_ultra_long")
        flags.append("cdr3_long")  # 
    elif cdr3_len >= CDR3_LEN_USE_J6:
        flags.append("cdr3_long")
    
    if total_cys_count > EXTRA_CYS_WARN_THRESHOLD:
        flags.append("extra_cys")
    
    if best_fr_identity < FR_IDENTITY_WARN:
        flags.append("low_fr_identity")
    
    # ========================================================================
    # 3. pass_level
    # ========================================================================
    if best_fr_identity < FR_IDENTITY_FAIL:
        pass_level = "fail"
    elif flags:  # flag
        pass_level = "warn"
    else:
        pass_level = "pass"
    
    # ========================================================================
    # 4. recommendations
    # ========================================================================
    # 4.1 J region
    if cdr3_len >= CDR3_LEN_USE_J6:
        suggest_j_region = "IGHJ6"
    else:
        suggest_j_region = "IGHJ4"
    
    # 4.2 Scaffold
    default_order = ["IGHV3-23*01", "IGHV3-66*01", "IGHV3-30*01", "IGHV3-7*01"]
    
    # CDR3>=18，IGHV3-7*012
    if cdr3_len >= CDR3_LEN_USE_J6:
        suggest_scaffold_rank = []
        for sid in default_order:
            if sid == "IGHV3-7*01":
                continue
            suggest_scaffold_rank.append({
                "scaffold_id": sid,
                "rationale": "Standard scaffold order"
            })
        # IGHV3-7*012
        suggest_scaffold_rank.insert(1, {
            "scaffold_id": "IGHV3-7*01",
            "rationale": f"Recommended for long CDR3 (length={cdr3_len} >= {CDR3_LEN_USE_J6})"
        })
    else:
        suggest_scaffold_rank = [
            {"scaffold_id": sid, "rationale": "Standard scaffold order"}
            for sid in default_order
        ]
    
    # ========================================================================
    # 5. 
    # ========================================================================
    gate = {
        "version": "v1",
        "thresholds": {
            "CDR3_LEN_USE_J6": CDR3_LEN_USE_J6,
            "CDR3_LEN_ULTRA_LONG": CDR3_LEN_ULTRA_LONG,
            "EXTRA_CYS_WARN_THRESHOLD": EXTRA_CYS_WARN_THRESHOLD,
            "FR_IDENTITY_WARN": FR_IDENTITY_WARN,
            "FR_IDENTITY_FAIL": FR_IDENTITY_FAIL,
        },
        "pass_level": pass_level,
        "flags": flags,
        "metrics": {
            "cdr3_len": cdr3_len,
            "total_cys_count": total_cys_count,
            "best_fr_identity": round(best_fr_identity, 4),
            "best_fr_identity_scaffold_id": best_scaffold_id,
            "length_mismatch": length_mismatch,
        },
        "recommendations": {
            "suggest_j_region": suggest_j_region,
            "suggest_scaffold_rank": suggest_scaffold_rank,
        },
    }
    
    return gate


def _calculate_identity(seq1: str, seq2: str) -> tuple[float, bool]:
    """
    identity
    
    Args:
        seq1: 1
        seq2: 2
    
    Returns:
        (identity, length_mismatch)
        identity:  / 
        length_mismatch: True
    """
    if not seq1 or not seq2:
        return 0.0, True
    
    len1, len2 = len(seq1), len(seq2)
    length_mismatch = (len1 != len2)
    
    # 
    aligned_length = min(len1, len2)
    
    if aligned_length == 0:
        return 0.0, length_mismatch
    
    # 
    matches = sum(1 for i in range(aligned_length) if seq1[i] == seq2[i])
    
    identity = matches / aligned_length
    
    return identity, length_mismatch

