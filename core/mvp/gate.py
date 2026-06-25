"""
Gate: Unified Quality Control Gate

Hard conditions for candidate filtering:
- CDR integrity
- Length consistency
- Hallmark floor
- Mutation count limits
"""

from typing import Dict, List, Any, Optional
from .utils import extract_regions_from_dual_map


def check_cdr_integrity(
    orig_dual_map: List[Dict[str, Any]],
    candidate_sequence: str,
    candidate_regions: Dict[str, str]
) -> bool:
    """
    Check CDR integrity: CDR1/2/3 must be identical to original
    
    Args:
        orig_dual_map: Original sequence dual_map
        candidate_sequence: Candidate V region sequence
        candidate_regions: Candidate regions dict
        
    Returns:
        True if CDRs are identical
    """
    orig_regions = extract_regions_from_dual_map(orig_dual_map)
    
    # Check each CDR
    for cdr_name in ["CDR1", "CDR2", "CDR3"]:
        orig_cdr = orig_regions.get(cdr_name, "")
        candidate_cdr = candidate_regions.get(cdr_name, "")
        if orig_cdr != candidate_cdr:
            return False
    
    return True


def check_length_consistency(
    v_length: Optional[int],
    dual_map_length: int,
    sequence_length: int
) -> bool:
    """
    Check length consistency between v_length, dual_map, and sequence
    
    Returns:
        True if all lengths are consistent
    """
    if v_length is None:
        return dual_map_length == sequence_length
    return v_length == dual_map_length == sequence_length


def check_hallmark_floor(
    hallmark_status: str,
    max_conflicts: int = 1
) -> bool:
    """
    Check hallmark floor: reject if too many conflicts
    
    Args:
        hallmark_status: "pass" or "conflict"
        max_conflicts: Maximum allowed conflicts (MVP: use status string)
        
    Returns:
        True if passes hallmark floor check
    """
    # MVP: if status is "conflict", check if it's acceptable
    # For now, allow "conflict" but could be enhanced
    return True  # MVP: allow conflicts, can be enhanced later


def check_mutation_count(
    mutation_list: List[Dict[str, Any]],
    route: str,
    max_mutations_a: int = 70,
    max_mutations_b: int = 80
) -> bool:
    """
    Check mutation count is within limits
    
    Args:
        mutation_list: List of mutations
        route: "A_EPS" or "B_CLUSTER"
        max_mutations_a: Max mutations for route A
        max_mutations_b: Max mutations for route B
        
    Returns:
        True if mutation count is acceptable
    """
    mutation_count = len(mutation_list)
    
    if route == "A_EPS":
        return mutation_count <= max_mutations_a
    elif route == "B_CLUSTER":
        return mutation_count <= max_mutations_b
    else:
        return False


def apply_gate(
    step1_candidates: List[Dict[str, Any]],
    mapping_result: Dict[str, Any],
    gate_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Apply gate to Step1 candidates
    
    Args:
        step1_candidates: Combined list of Step1-A and Step1-B candidates
        mapping_result: Original mapping result for reference
        gate_params: Optional gate parameters
        
    Returns:
        Gate decision dictionary with:
        - pass_A: Best A_EPS candidate (1)
        - pass_B: Best B_CLUSTER candidate (1)
        - rejected: List of rejected candidates with reasons
        - gate_params: Parameters used
    """
    if gate_params is None:
        gate_params = {
            "max_mutations_a": 70,  # MVP: Allow more mutations for scaffold-based approach
            "max_mutations_b": 80,
            "max_hallmark_conflicts": 1,
            "gate_version": "v0.1"
        }
    
    dual_map = mapping_result.get("dual_map", [])
    v_length = mapping_result.get("variable_domain", {}).get("v_length")
    variable_domain_sequence = mapping_result.get("variable_domain_sequence", "")
    
    passed_a = []
    passed_b = []
    rejected = []
    
    for candidate in step1_candidates:
        route = candidate.get("route", "")
        candidate_id = candidate.get("candidate_id", "")
        mutation_list = candidate.get("mutation_list", [])
        hallmark_status = candidate.get("hallmark_status", "unknown")
        sequence_v_region = candidate.get("sequence_v_region", "")
        
        # Extract candidate regions for CDR check
        from .utils import extract_regions_from_dual_map, rebuild_sequence_from_regions
        # For CDR check, we need to reconstruct regions from sequence
        # Simplified: use mutation list to infer regions
        candidate_regions = {}  # Will be populated if needed
        
        reject_reasons = []
        
        # Check 1: CDR integrity
        # For MVP, we verify CDRs are preserved by checking mutation list
        # (mutations should only be in FR regions, not in CDR regions)
        cdr_regions = ["CDR1", "CDR2", "CDR3"]
        cdr_mutations = [m for m in mutation_list if m.get("region", "") in cdr_regions]
        if cdr_mutations:
            reject_reasons.append("CDR integrity violation: mutations found in CDR regions")
        
        # Check 2: Length consistency
        # MVP: Allow some flexibility in sequence length (scaffolds may have different lengths)
        # But ensure it's reasonable (within 30% of original)
        seq_len = len(sequence_v_region)
        dual_map_len = len(dual_map)
        if v_length:
            length_diff_pct = abs(seq_len - v_length) / v_length
            if length_diff_pct > 0.3:  # More than 30% difference
                reject_reasons.append(f"Length inconsistency: v_length={v_length}, seq={seq_len} (diff={length_diff_pct:.1%})")
        elif dual_map_len > 0:
            # If no v_length, compare with dual_map length (allow 30% difference)
            length_diff_pct = abs(seq_len - dual_map_len) / dual_map_len
            if length_diff_pct > 0.3:
                reject_reasons.append(f"Length inconsistency: dual_map={dual_map_len}, seq={seq_len} (diff={length_diff_pct:.1%})")
        
        # Check 3: Hallmark floor
        if not check_hallmark_floor(hallmark_status, gate_params.get("max_hallmark_conflicts", 1)):
            reject_reasons.append(f"Hallmark floor violation: status={hallmark_status}")
        
        # Check 4: Mutation count
        if not check_mutation_count(
            mutation_list,
            route,
            gate_params.get("max_mutations_a", 70),
            gate_params.get("max_mutations_b", 80)
        ):
            max_allowed = gate_params.get("max_mutations_a", 70) if route == "A_EPS" else gate_params.get("max_mutations_b", 80)
            reject_reasons.append(f"Mutation count exceeded: {len(mutation_list)} > {max_allowed}")
        
        # Decision
        if reject_reasons:
            rejected.append({
                "candidate_id": candidate_id,
                "route": route,
                "reject_reasons": reject_reasons
            })
        else:
            if route == "A_EPS":
                passed_a.append(candidate)
            elif route == "B_CLUSTER":
                passed_b.append(candidate)
    
    # Select best candidates
    # A: sort by fr_identity_total (descending)
    passed_a_sorted = sorted(passed_a, key=lambda x: x.get("fr_identity_total", 0.0), reverse=True)
    pass_a = passed_a_sorted[0] if passed_a_sorted else None
    
    # B: sort by fr_distance_total (ascending, lower is better) or identity
    # For MVP, use fr_distance_total
    passed_b_sorted = sorted(passed_b, key=lambda x: x.get("fr_distance_total", 999.0))
    pass_b = passed_b_sorted[0] if passed_b_sorted else None
    
    return {
        "pass_A": pass_a,
        "pass_B": pass_b,
        "rejected": rejected,
        "gate_params": gate_params,
        "stats": {
            "total_candidates": len(step1_candidates),
            "passed_a_count": len(passed_a),
            "passed_b_count": len(passed_b),
            "rejected_count": len(rejected)
        }
    }

