"""
Step1-A: EPS (Engineered Protein Scaffold) Route

Industrial-reliable EPS route for VHH humanization.
Generates FR-only replacement candidates using EPS scaffold library.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from .utils import (
    extract_regions_from_dual_map,
    calculate_fr_identity,
    calculate_vernier_identity,
    check_hallmark_status,
    rebuild_sequence_from_regions,
    extract_mutations
)


def load_eps_scaffolds(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load EPS scaffold library
    
    Args:
        db_path: Path to EPS scaffolds JSON file
        
    Returns:
        List of scaffold dictionaries
    """
    if db_path is None:
        db_path = str(Path(__file__).parent.parent / "data" / "eps_scaffolds_vhh.json")
    
    with open(db_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get("scaffolds", [])


def generate_step1a_candidates(
    mapping_result: Dict[str, Any],
    eps_db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate Step1-A candidates using EPS scaffolds
    
    Args:
        mapping_result: Dual map JSON structure with:
            - variable_domain_sequence
            - dual_map
            - imgt_numbering
            - kabat_numbering
        eps_db_path: Optional path to EPS scaffold database
        
    Returns:
        List of candidate dictionaries with required fields:
        - candidate_id
        - route ("A_EPS")
        - template_id
        - fr_identity_total, fr_id_fr1..fr4
        - vernier_identity
        - hallmark_status ("pass"/"conflict")
        - mutation_list (FR-only)
        - sequence_v_region
    """
    dual_map = mapping_result.get("dual_map", [])
    variable_domain_sequence = mapping_result.get("variable_domain_sequence", "")
    
    # Rebuild sequence from dual_map if variable_domain_sequence is missing
    if not variable_domain_sequence and dual_map:
        variable_domain_sequence = "".join(entry.get("aa", "") for entry in dual_map if entry.get("aa") and entry.get("aa") != "-")
    
    # Extract original regions
    orig_regions = extract_regions_from_dual_map(dual_map)
    
    # Load EPS scaffolds
    scaffolds = load_eps_scaffolds(eps_db_path)
    
    candidates = []
    
    for idx, scaffold in enumerate(scaffolds):
        template_id = scaffold.get("template_id", f"EPS_{idx}")
        template_regions = scaffold.get("regions", {})
        
        # Build candidate regions: template FR + original CDR
        candidate_regions = {
            "FR1": template_regions.get("FR1", ""),
            "CDR1": orig_regions.get("CDR1", ""),  # Keep original CDR
            "FR2": template_regions.get("FR2", ""),
            "CDR2": orig_regions.get("CDR2", ""),  # Keep original CDR
            "FR3": template_regions.get("FR3", ""),
            "CDR3": orig_regions.get("CDR3", ""),  # Keep original CDR
            "FR4": template_regions.get("FR4", "")
        }
        
        # Calculate FR identities
        fr_id_fr1 = calculate_fr_identity(orig_regions.get("FR1", ""), candidate_regions["FR1"])
        fr_id_fr2 = calculate_fr_identity(orig_regions.get("FR2", ""), candidate_regions["FR2"])
        fr_id_fr3 = calculate_fr_identity(orig_regions.get("FR3", ""), candidate_regions["FR3"])
        fr_id_fr4 = calculate_fr_identity(orig_regions.get("FR4", ""), candidate_regions["FR4"])
        
        # Calculate total FR identity (weighted average)
        fr_identity_total = (fr_id_fr1 + fr_id_fr2 + fr_id_fr3 + fr_id_fr4) / 4.0
        
        # Calculate vernier identity
        vernier_identity = calculate_vernier_identity(dual_map, template_regions)
        
        # Check hallmark status
        hallmark_status = check_hallmark_status(dual_map, template_regions)
        
        # Extract mutations
        mutation_list = extract_mutations(orig_regions, candidate_regions)
        
        # Rebuild sequence
        sequence_v_region = rebuild_sequence_from_regions(candidate_regions)
        
        candidate = {
            "candidate_id": f"A_EPS_{idx+1:03d}",
            "route": "A_EPS",
            "template_id": template_id,
            "fr_identity_total": round(fr_identity_total, 4),
            "fr_id_fr1": round(fr_id_fr1, 4),
            "fr_id_fr2": round(fr_id_fr2, 4),
            "fr_id_fr3": round(fr_id_fr3, 4),
            "fr_id_fr4": round(fr_id_fr4, 4),
            "vernier_identity": round(vernier_identity, 4),
            "hallmark_status": hallmark_status,
            "mutation_list": mutation_list,
            "sequence_v_region": sequence_v_region
        }
        
        candidates.append(candidate)
    
    return candidates

