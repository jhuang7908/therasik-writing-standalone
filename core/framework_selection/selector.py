#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production-Grade Framework Selection Engine

Selects human antibody frameworks (VH/VL) and FR4/J segments for humanization/CDR grafting.

Scoring Criteria:
1. Primary: FR1–FR3 identity (0.0 to 1.0)
2. Secondary: Canonical envelope match (+0.05 bonus if match)
3. Tertiary: Tags bonus (+0.02 per matching tag, if requested)
4. CDR3 length risk penalty (subtracted, based on framework.cdr3_policy)

Hard Constraints:
- Framework = FR1–FR3 only (CDR3 and FR4 excluded from identity)
- FR4/J selected separately AFTER framework selection (never affects ranking)
- No invention of canonical classes or evidence (use TODO if missing)
- Deterministic ranking (stable sort by score, then framework_id)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_humanization import split_regions


def load_framework_library() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Load VH and VL framework libraries from YAML files.
    
    Returns:
        (vh_frameworks, vl_frameworks) - lists of framework entries
    """
    vh_path = PROJECT_ROOT / "core" / "data" / "framework_library" / "vh_frameworks.yaml"
    vl_path = PROJECT_ROOT / "core" / "data" / "framework_library" / "vl_frameworks.yaml"
    
    vh_frameworks = []
    vl_frameworks = []
    
    if vh_path.exists():
        with open(vh_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            vh_frameworks = data.get("frameworks", [])
    
    if vl_path.exists():
        with open(vl_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            vl_frameworks = data.get("frameworks", [])
    
    return vh_frameworks, vl_frameworks


def compute_query_features(query_numbering: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute query sequence features from ANARCII numbering output.
    
    Args:
        query_numbering: ANARCII numbering output (list of dicts with 'pos', 'aa', etc.)
    
    Returns:
        {
            "cdr_h3_length": int,  # IMGT positions 105-117 count (excluding gaps)
            "predicted_pI": float | "TODO",
            "aggregation_risk": bool | "TODO",
            "format": str | "TODO",  # e.g., "scFv", "bispecific"
            "target_conc_mg_ml": float | "TODO",
            "long_cdr3_flag": bool,
        }
    """
    features: Dict[str, Any] = {
        "cdr_h3_length": 0,
        "predicted_pI": "TODO",
        "aggregation_risk": "TODO",
        "format": "TODO",
        "target_conc_mg_ml": "TODO",
        "long_cdr3_flag": False,
    }
    
    # Extract CDR-H3 length from IMGT positions 105-117
    cdr3_aa_count = 0
    for row in query_numbering:
        pos = row.get("pos")
        if isinstance(pos, int) and 105 <= pos <= 117:
            aa = row.get("aa", "")
            if aa and aa != "-":
                cdr3_aa_count += 1
    
    features["cdr_h3_length"] = cdr3_aa_count
    features["long_cdr3_flag"] = cdr3_aa_count > 18
    
    # TODO: Add pI calculation if function exists
    # TODO: Add aggregation risk assessment if available
    # TODO: Add format detection if provided
    
    return features


def extract_query_fr1_fr3(query_numbering: List[Dict[str, Any]]) -> Optional[str]:
    """
    Extract FR1-FR3 sequence from ANARCII numbering output.
    
    Args:
        query_numbering: ANARCII numbering output (list of dicts with 'pos', 'aa', etc.)
    
    Returns:
        FR1+FR2+FR3 sequence string, or None if extraction fails
    """
    try:
        # Use split_regions if available
        regions = split_regions(query_numbering)
        fr1 = regions.get("FR1", "")
        fr2 = regions.get("FR2", "")
        fr3 = regions.get("FR3", "")
        
        if fr1 and fr2 and fr3:
            return fr1 + fr2 + fr3
    except Exception:
        # Fallback: extract directly from numbering rows
        try:
            fr1_aa = []
            fr2_aa = []
            fr3_aa = []
            
            for row in query_numbering:
                pos = row.get("pos")
                if isinstance(pos, int):
                    aa = row.get("aa", "")
                    if aa and aa != "-":
                        if 1 <= pos <= 26:
                            fr1_aa.append(aa)
                        elif 39 <= pos <= 55:
                            fr2_aa.append(aa)
                        elif 66 <= pos <= 104:
                            fr3_aa.append(aa)
            
            if fr1_aa and fr2_aa and fr3_aa:
                return "".join(fr1_aa) + "".join(fr2_aa) + "".join(fr3_aa)
        except Exception:
            pass
    
    return None


def calculate_fr_identity(seq1: str, seq2: str) -> float:
    """
    Calculate FR1-FR3 identity between two sequences.
    
    Args:
        seq1: First sequence (query FR1-FR3)
        seq2: Second sequence (framework FR1-FR3)
    
    Returns:
        Identity score (0.0 to 1.0)
    """
    if not seq1 or not seq2:
        return 0.0
    
    L = min(len(seq1), len(seq2))
    if L == 0:
        return 0.0
    
    same = sum(1 for i in range(L) if seq1[i] == seq2[i])
    return same / L


def check_canonical_match(
    query_canonical: Optional[Dict[str, str]],
    framework_canonical: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Check if query canonical classes match framework canonical envelope.
    
    Args:
        query_canonical: {"cdr1": "H1-1", "cdr2": "H2-3-2"} or None
        framework_canonical: Framework canonical entry from YAML
    
    Returns:
        (is_match, match_status_string)
    """
    if not query_canonical:
        return False, "TODO (query canonical unavailable)"
    
    fw_cdr1 = framework_canonical.get("cdr1", {})
    fw_cdr2 = framework_canonical.get("cdr2", {})
    
    fw_cdr1_class = fw_cdr1.get("class", "TODO")
    fw_cdr2_class = fw_cdr2.get("class", "TODO")
    
    query_cdr1_class = query_canonical.get("cdr1", "TODO")
    query_cdr2_class = query_canonical.get("cdr2", "TODO")
    
    if fw_cdr1_class == "TODO" or fw_cdr2_class == "TODO":
        return False, "TODO (framework canonical unavailable)"
    
    if query_cdr1_class == "TODO" or query_cdr2_class == "TODO":
        return False, "TODO (query canonical unavailable)"
    
    cdr1_match = query_cdr1_class == fw_cdr1_class
    cdr2_match = query_cdr2_class == fw_cdr2_class
    
    if cdr1_match and cdr2_match:
        return True, "✓ Match"
    elif cdr1_match or cdr2_match:
        return False, "Partial"
    else:
        return False, "No match"


def compute_cdr3_risk_penalty(
    cdr3_length: int,
    cdr3_policy: Dict[str, Any],
) -> float:
    """
    Compute CDR3 length risk penalty based on framework's cdr3_policy.
    
    Args:
        cdr3_length: CDR3 length (e.g., CDR-H3 length for VH)
        cdr3_policy: Framework's cdr3_policy dict with preferred_max, caution_range, high_risk_min
    
    Returns:
        Penalty score (0.0 = no penalty, higher = more risk)
    """
    if not cdr3_policy or isinstance(cdr3_policy, str) and cdr3_policy == "TODO":
        return 0.0  # No penalty if policy unavailable
    
    preferred_max = cdr3_policy.get("preferred_max")
    caution_range = cdr3_policy.get("caution_range")
    high_risk_min = cdr3_policy.get("high_risk_min")
    
    if preferred_max in (None, "TODO") or not isinstance(preferred_max, (int, float)):
        return 0.0
    
    # Preferred range: no penalty
    if cdr3_length <= preferred_max:
        return 0.0
    
    # Caution range: small penalty
    if isinstance(caution_range, list) and len(caution_range) >= 2:
        caution_min, caution_max = caution_range[0], caution_range[1]
        if caution_min <= cdr3_length <= caution_max:
            # Linear penalty from 0.0 to 0.05 within caution range
            range_size = caution_max - caution_min
            if range_size > 0:
                position_in_range = (cdr3_length - caution_min) / range_size
                return 0.05 * position_in_range
            return 0.05
    
    # High risk: larger penalty
    if isinstance(high_risk_min, (int, float)) and cdr3_length >= high_risk_min:
        # Penalty increases with length beyond high_risk_min
        excess = cdr3_length - high_risk_min
        return 0.05 + min(0.10, excess * 0.01)  # Cap at 0.15 total penalty
    
    return 0.0


def score_candidates(
    query_fr1_fr3: str,
    candidates: List[Dict[str, Any]],
    query_canonical: Optional[Dict[str, str]] = None,
    tag_bonus: Optional[List[str]] = None,
    cdr3_length: Optional[int] = None,
) -> List[Tuple[Dict[str, Any], float, Dict[str, Any]]]:
    """
    Score framework candidates based on FR identity, canonical match, tags, and CDR3 risk.
    
    Args:
        query_fr1_fr3: Query FR1-FR3 sequence
        candidates: List of framework entries from library
        query_canonical: Optional query canonical classes {"cdr1": "H1-1", "cdr2": "H2-3-2"}
        tag_bonus: Optional list of tags to give bonus for (e.g., ["high_solubility", "compact"])
        cdr3_length: Optional CDR3 length for risk penalty calculation
    
    Returns:
        List of (candidate, score, score_details) tuples, sorted by score descending
    """
    scored: List[Tuple[Dict[str, Any], float, Dict[str, Any]]] = []
    
    for cand in candidates:
        fw_fr_seq = cand.get("fr_sequence_fr1_fr3", "")
        if fw_fr_seq == "TODO" or not fw_fr_seq:
            # Skip frameworks without FR sequences
            continue
        
        # Primary: FR1-FR3 identity (0.0 to 1.0)
        fr_identity = calculate_fr_identity(query_fr1_fr3, fw_fr_seq)
        
        # Secondary: Canonical envelope match (bonus: +0.05 if match)
        canonical_match, canonical_status = check_canonical_match(
            query_canonical,
            cand.get("canonical", {})
        )
        canonical_bonus = 0.05 if canonical_match else 0.0
        
        # Tertiary: Tags bonus (only if requested, small bonus per tag)
        tags_bonus = 0.0
        if tag_bonus:
            fw_tags = cand.get("tags", [])
            matching_tags = [t for t in tag_bonus if t in fw_tags]
            tags_bonus = 0.02 * len(matching_tags)  # Small bonus per matching tag
        
        # CDR3 length risk penalty (subtracted from score)
        cdr3_penalty = 0.0
        if cdr3_length is not None:
            cdr3_policy = cand.get("cdr3_policy", {})
            cdr3_penalty = compute_cdr3_risk_penalty(cdr3_length, cdr3_policy)
        
        # Combined score (FR identity is primary, penalties subtract)
        total_score = fr_identity + canonical_bonus + tags_bonus - cdr3_penalty
        
        # Ensure score doesn't go negative
        total_score = max(0.0, total_score)
        
        score_details = {
            "fr_identity": fr_identity,
            "canonical_match": canonical_match,
            "canonical_status": canonical_status,
            "canonical_bonus": canonical_bonus,
            "tags_bonus": tags_bonus,
            "cdr3_penalty": cdr3_penalty,
            "cdr3_length": cdr3_length,
            "total_score": total_score,
        }
        
        scored.append((cand, total_score, score_details))
    
    # Sort by total_score descending, then by framework_id for determinism
    scored.sort(key=lambda x: (-x[1], x[0].get("framework_id", "")))
    
    return scored


def evaluate_rule_condition(
    condition: Dict[str, Any],
    features: Dict[str, Any]
) -> bool:
    """
    Evaluate a rule condition against query features.
    
    Args:
        condition: Rule condition dict (from framework_selection_rules.yaml)
        features: Query features dict
    
    Returns:
        True if condition is met, False otherwise
    """
    cond_type = condition.get("type")
    
    if cond_type == "comparison":
        field = condition.get("field")
        op = condition.get("operator")
        value = condition.get("value")
        
        field_value = features.get(field)
        if field_value == "TODO" or field_value is None:
            return False
        
        if op == ">":
            return field_value > value
        elif op == ">=":
            return field_value >= value
        elif op == "<":
            return field_value < value
        elif op == "<=":
            return field_value <= value
        elif op == "==":
            return field_value == value
        elif op == "!=":
            return field_value != value
    
    elif cond_type == "equality":
        field = condition.get("field")
        op = condition.get("operator")
        value = condition.get("value")
        
        field_value = features.get(field)
        if field_value == "TODO" or field_value is None:
            return False
        
        if op == "==":
            return field_value == value
        elif op == "!=":
            return field_value != value
    
    elif cond_type == "membership":
        field = condition.get("field")
        op = condition.get("operator")
        value = condition.get("value")
        
        field_value = features.get(field)
        if field_value == "TODO" or field_value is None:
            return False
        
        if op == "in":
            return field_value in value
        elif op == "not_in":
            return field_value not in value
    
    elif cond_type == "logical_or":
        conditions = condition.get("conditions", [])
        return any(evaluate_rule_condition(c, features) for c in conditions)
    
    elif cond_type == "logical_and" or cond_type == "all":
        conditions = condition.get("conditions", [])
        return all(evaluate_rule_condition(c, features) for c in conditions)
    
    return False


def apply_selection_rules(
    top3_vh: List[Dict[str, Any]],
    top3_vl: List[Dict[str, Any]],
    features: Dict[str, Any],
    rules: Dict[str, Any],
    fr4_segments: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Apply selection rules to determine final framework and FR4/J choices.
    
    Args:
        top3_vh: Top 3 VH candidates
        top3_vl: Top 3 VL candidates
        features: Query features
        rules: Framework selection rules dict
        fr4_segments: FR4/J segments dict
    
    Returns:
        {
            "final_vh": framework_id,
            "final_vl": framework_id,
            "fr4_vh": j_segment_id,
            "fr4_vl": j_segment_id,
            "triggered_rules": [{"id": "...", "reason": "..."}],
            "notes": [...]
        }
    """
    selection_rules = rules.get("framework_selection_rules", {})
    rule_list = selection_rules.get("rules", [])
    
    # Sort rules by priority (lower number = higher priority)
    rule_list.sort(key=lambda r: r.get("priority", 999))
    
    triggered_rules: List[Dict[str, str]] = []
    notes: List[str] = []
    
    # Start with defaults
    default = selection_rules.get("default_success", {})
    default_selection = default.get("selection", {})
    
    final_vh_id = None
    final_vl_id = None
    fr4_vh_id = default_selection.get("fr4", {}).get("heavy_j", {}).get("j_segment_id", "hJH4")
    fr4_vl_id = default_selection.get("fr4", {}).get("light_j", {}).get("j_segment_id", "hJK1")
    
    # Apply conditional rules
    for rule in rule_list:
        condition = rule.get("condition", {})
        if evaluate_rule_condition(condition, features):
            action = rule.get("action", {})
            action_type = action.get("type")
            
            triggered_rules.append({
                "id": rule.get("id", "unknown"),
                "reason": rule.get("reason", "Rule triggered"),
            })
            
            if action_type == "override_fr4":
                fr4 = action.get("fr4", {})
                if fr4.get("heavy_j", {}).get("j_segment_id"):
                    fr4_vh_id = fr4["heavy_j"]["j_segment_id"]
                if fr4.get("light_j", {}).get("j_segment_id"):
                    fr4_vl_id = fr4["light_j"]["j_segment_id"]
            
            elif action_type == "preferences_and_allowances":
                preferences = action.get("preferences", {})
                # Apply tag preferences to re-rank candidates
                vh_prefs = preferences.get("vh", {})
                vl_prefs = preferences.get("vl", {})
                
                if vh_prefs.get("prefer_tags_any"):
                    # Re-rank VH by tags
                    tag_list = vh_prefs["prefer_tags_any"]
                    # This would require re-scoring, simplified for now
                    notes.append(f"VH tag preference: {tag_list}")
                
                if vl_prefs.get("prefer_tags_any"):
                    tag_list = vl_prefs["prefer_tags_any"]
                    notes.append(f"VL tag preference: {tag_list}")
    
    # Select final frameworks (top1 from top3)
    if top3_vh:
        final_vh_id = top3_vh[0].get("framework_id")
    if top3_vl:
        final_vl_id = top3_vl[0].get("framework_id")
    
    return {
        "final_vh": final_vh_id,
        "final_vl": final_vl_id,
        "fr4_vh": fr4_vh_id,
        "fr4_vl": fr4_vl_id,
        "triggered_rules": triggered_rules,
        "notes": notes,
    }


def select_top3_and_final(
    query_numbering: List[Dict[str, Any]],
    rules: Optional[Dict[str, Any]] = None,
    fr4_segments: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """
    Select Top3 candidates and final framework + FR4/J choices.
    
    Args:
        query_numbering: ANARCII numbering output for query sequence
        rules: Framework selection rules (loaded from YAML if None)
        fr4_segments: FR4/J segments (loaded from YAML if None)
    
    Returns:
        {
            "top3_vh": [{"framework_id": "...", "fr_identity": 0.95, ...}, ...],
            "top3_vl": [...],
            "final_choice": {
                "VH": "VH:IGHV3-23*01",
                "VL": "VL:IGKV1-39*01",
                "FR4_VH": "hJH4",
                "FR4_VL": "hJK1"
            },
            "triggered_rules": [...],
            "notes": [...]
        }
    """
    # Load data if not provided
    if rules is None:
        rules_path = PROJECT_ROOT / "core" / "policies" / "framework_selection_rules.yaml"
        if rules_path.exists():
            with open(rules_path, "r", encoding="utf-8") as f:
                rules = yaml.safe_load(f) or {}
        else:
            rules = {}
    
    if fr4_segments is None:
        fr4_path = PROJECT_ROOT / "core" / "data" / "framework_library" / "fr4_j_segments.yaml"
        if fr4_path.exists():
            with open(fr4_path, "r", encoding="utf-8") as f:
                fr4_data = yaml.safe_load(f) or {}
                # Support new format (entries) - FR4 is separate from frameworks
                entries = fr4_data.get("entries", [])
                if entries:
                    vh_segments = [e for e in entries if isinstance(e, dict) and e.get("chain") == "VH"]
                    vl_segments = [e for e in entries if isinstance(e, dict) and e.get("chain") == "VL"]
                    fr4_segments = {"vh": vh_segments, "vl": vl_segments}
                else:
                    # Fallback to old format if needed
                    old_vh = fr4_data.get("fr4_j_segments", {}).get("vh", [])
                    old_vl = fr4_data.get("fr4_j_segments", {}).get("vl", [])
                    fr4_segments = {"vh": old_vh, "vl": old_vl}
        else:
            fr4_segments = {"vh": [], "vl": []}
    
    # Load framework libraries
    vh_frameworks, vl_frameworks = load_framework_library()
    
    # Compute query features
    features = compute_query_features(query_numbering)
    
    # Extract query FR1-FR3
    query_fr1_fr3 = extract_query_fr1_fr3(query_numbering)
    if not query_fr1_fr3:
        return {
            "top3_vh": [],
            "top3_vl": [],
            "final_choice": {"VH": None, "VL": None, "FR4_VH": "hJH4", "FR4_VL": "hJK1"},
            "triggered_rules": [],
            "notes": ["Failed to extract FR1-FR3 from query numbering"],
        }
    
    # Extract query canonical (if available from numbering)
    query_canonical = None  # TODO: Extract from numbering if available
    
    # Extract CDR3 length for risk penalty calculation
    cdr_h3_length = features.get("cdr_h3_length", 0)
    cdr_l3_length = None  # TODO: Extract CDR-L3 length if VL numbering available
    
    # Score and rank candidates (VH uses CDR-H3 length, VL uses CDR-L3 length)
    vh_scored = score_candidates(
        query_fr1_fr3, 
        vh_frameworks, 
        query_canonical,
        cdr3_length=cdr_h3_length if cdr_h3_length > 0 else None
    )
    vl_scored = score_candidates(
        query_fr1_fr3, 
        vl_frameworks, 
        query_canonical,
        cdr3_length=cdr_l3_length
    )
    
    # Get Top3 with score details attached
    top3_vh = []
    for cand, score, details in vh_scored[:3]:
        cand_with_score = cand.copy()
        cand_with_score["_score"] = score
        cand_with_score["_score_details"] = details
        top3_vh.append(cand_with_score)
    
    top3_vl = []
    for cand, score, details in vl_scored[:3]:
        cand_with_score = cand.copy()
        cand_with_score["_score"] = score
        cand_with_score["_score_details"] = details
        top3_vl.append(cand_with_score)
    
    # Apply rules to get final selection
    final_selection = apply_selection_rules(top3_vh, top3_vl, features, rules, fr4_segments)
    
    return {
        "top3_vh": top3_vh,
        "top3_vl": top3_vl,
        "final_choice": {
            "VH": final_selection["final_vh"],
            "VL": final_selection["final_vl"],
            "FR4_VH": final_selection["fr4_vh"],
            "FR4_VL": final_selection["fr4_vl"],
        },
        "triggered_rules": final_selection["triggered_rules"],
        "notes": final_selection["notes"],
    }


def select_frameworks(
    query_numbering: List[Dict[str, Any]],
    query_sequence: Optional[str] = None,
    query_vh_numbering: Optional[List[Dict[str, Any]]] = None,
    query_vl_numbering: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Production-grade framework selection engine.
    
    Main entry point for framework selection. Handles VH and VL separately if provided.
    
    Args:
        query_numbering: ANARCII numbering output (assumed VH if not split)
        query_sequence: Optional full query sequence (for fallback)
        query_vh_numbering: Optional separate VH numbering (if VH/VL are split)
        query_vl_numbering: Optional separate VL numbering (if VH/VL are split)
    
    Returns:
        Complete selection result dict with:
        - top3_vh: Top 3 VH framework candidates with scores
        - top3_vl: Top 3 VL framework candidates with scores
        - final_choice: Selected VH/VL frameworks + FR4/J segments
        - triggered_rules: List of triggered selection rules
        - notes: Additional notes about selection process
    """
    # If separate VH/VL numbering provided, use them; otherwise use combined
    vh_numbering = query_vh_numbering if query_vh_numbering is not None else query_numbering
    vl_numbering = query_vl_numbering if query_vl_numbering is not None else query_numbering
    
    # For now, use the same numbering for both if not split
    # In future, this can be enhanced to handle separate VH/VL chains
    return select_top3_and_final(vh_numbering)
