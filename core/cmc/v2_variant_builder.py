"""
V2 Variant Builder for CMC Liability Mitigation.

This module generates V2 variants by applying mutations to address
deamidation and isomerization liabilities identified in CMC scanning.
"""

from typing import Dict, List


def generate_v2_variants(seq: str, cmc_info: dict) -> dict:
    """
     V2 ， CMC 。
    
    :
        seq: （，1-based  cmc_info  position）
        cmc_info: CMC ， generic_cmc_scanner.scan_cmc_liabilities ，
                   keys: 'deamidation_sites', 'isomerization_sites', 'oxidation_sites', 'summary'
    
    :
        ， V2 :
        {
            "v2_deamidation_only": {
                "sequence": <str>,
                "mutations": [ { "pos": 82, "from": "N", "to": "Q", "reason": "remove deamidation (NS motif)" }, ... ]
            },
            "v2_isomerization_only": {
                "sequence": <str>,
                "mutations": [ { "pos": 52, "from": "D", "to": "E", "reason": "reduce Asp isomerization (DS motif)" }, ... ]
            },
            "v2_combined": {
                "sequence": <str>,
                "mutations": [...],
            }
        }
    
    :
        1) Deamidation:
            -  deamidation_sites  motif  "N"  ( "NS","NG","NN")
            -  N -> Q (，)
            -  reason: "N{pos}Q to remove deamidation ({motif} motif)"
        
        2) Isomerization:
            -  isomerization_sites  motif  "DP","DS","DG","DT" 
            -  D -> E (， succinimide )
            - reason: "D{pos}E to reduce Asp isomerization ({motif} motif)"
        
        3) v2_deamidation_only:
            -  1) 
        
        4) v2_isomerization_only:
            -  2) 
        
        5) v2_combined:
            -  1) + 2)， deamidation_sites  isomerization_sites，
              （ N->Q ）
    
    :
        -  1-based  0-based ， position-1 
        -  seq ，
        - ，（ mutations ）
        -  docstring 
    """
    # Validate inputs
    if not seq:
        raise ValueError("Sequence cannot be empty")
    
    if not isinstance(cmc_info, dict):
        raise ValueError("cmc_info must be a dictionary")
    
    # Get deamidation and isomerization sites from cmc_info
    deamidation_sites = cmc_info.get('deamidation_sites', [])
    isomerization_sites = cmc_info.get('isomerization_sites', [])
    
    # Build sets of positions for quick lookup (to handle overlaps in v2_combined)
    deamidation_positions = {
        site['position']: site 
        for site in deamidation_sites 
        if isinstance(site, dict) and site.get('motif', '').startswith('N')
    }
    
    isomerization_positions = {
        site['position']: site 
        for site in isomerization_sites 
        if isinstance(site, dict) and site.get('motif', '') in ['DP', 'DS', 'DG', 'DT']
    }
    
    # Generate v2_deamidation_only variant
    v2_deamidation = _apply_deamidation_fixes(seq, deamidation_positions)
    
    # Generate v2_isomerization_only variant
    v2_isomerization = _apply_isomerization_fixes(seq, isomerization_positions)
    
    # Generate v2_combined variant (apply both, but prioritize deamidation if overlap)
    v2_combined = _apply_combined_fixes(seq, deamidation_positions, isomerization_positions)
    
    return {
        "v2_deamidation_only": v2_deamidation,
        "v2_isomerization_only": v2_isomerization,
        "v2_combined": v2_combined
    }


def _apply_deamidation_fixes(seq: str, deamidation_positions: Dict[int, dict]) -> dict:
    """
    ：N -> Q 。
    
    Args:
        seq: 
        deamidation_positions: ，key  1-based position，value  site 
    
    Returns:
         sequence  mutations 
    """
    mutations = []
    seq_list = list(seq)  # Convert to list for mutation
    
    # Sort positions to apply mutations from end to start (to preserve indices)
    sorted_positions = sorted(deamidation_positions.keys(), reverse=True)
    
    for pos in sorted_positions:
        site = deamidation_positions[pos]
        motif = site.get('motif', '')
        
        # Validate: position should be 1-based, convert to 0-based for indexing
        if pos < 1 or pos > len(seq):
            continue
        
        idx = pos - 1  # Convert to 0-based index
        current_aa = seq[idx]
        
        # Only mutate if it's actually 'N'
        if current_aa == 'N':
            seq_list[idx] = 'Q'
            mutations.append({
                "pos": pos,
                "from": "N",
                "to": "Q",
                "reason": f"N{pos}Q to remove deamidation ({motif} motif)"
            })
    
    # Reverse mutations list to have them in ascending position order
    mutations.reverse()
    
    return {
        "sequence": ''.join(seq_list),
        "mutations": mutations
    }


def _apply_isomerization_fixes(seq: str, isomerization_positions: Dict[int, dict]) -> dict:
    """
    ：D -> E 。
    
    Args:
        seq: 
        isomerization_positions: ，key  1-based position，value  site 
    
    Returns:
         sequence  mutations 
    """
    mutations = []
    seq_list = list(seq)  # Convert to list for mutation
    
    # Sort positions to apply mutations from end to start (to preserve indices)
    sorted_positions = sorted(isomerization_positions.keys(), reverse=True)
    
    for pos in sorted_positions:
        site = isomerization_positions[pos]
        motif = site.get('motif', '')
        
        # Validate: position should be 1-based, convert to 0-based for indexing
        if pos < 1 or pos > len(seq):
            continue
        
        idx = pos - 1  # Convert to 0-based index
        current_aa = seq[idx]
        
        # Only mutate if it's actually 'D'
        if current_aa == 'D':
            seq_list[idx] = 'E'
            mutations.append({
                "pos": pos,
                "from": "D",
                "to": "E",
                "reason": f"D{pos}E to reduce Asp isomerization ({motif} motif)"
            })
    
    # Reverse mutations list to have them in ascending position order
    mutations.reverse()
    
    return {
        "sequence": ''.join(seq_list),
        "mutations": mutations
    }


def _apply_combined_fixes(
    seq: str, 
    deamidation_positions: Dict[int, dict], 
    isomerization_positions: Dict[int, dict]
) -> dict:
    """
    ：。
    ，（N->Q）。
    
    Args:
        seq: 
        deamidation_positions: 
        isomerization_positions: 
    
    Returns:
         sequence  mutations 
    """
    mutations = []
    seq_list = list(seq)  # Convert to list for mutation
    
    # Get all positions that need fixing
    all_positions = set(deamidation_positions.keys()) | set(isomerization_positions.keys())
    
    # Sort positions to apply mutations from end to start (to preserve indices)
    sorted_positions = sorted(all_positions, reverse=True)
    
    for pos in sorted_positions:
        # Priority: deamidation first (N->Q takes precedence)
        if pos in deamidation_positions:
            site = deamidation_positions[pos]
            motif = site.get('motif', '')
            
            if pos < 1 or pos > len(seq):
                continue
            
            idx = pos - 1  # Convert to 0-based index
            current_aa = seq[idx]
            
            if current_aa == 'N':
                seq_list[idx] = 'Q'
                mutations.append({
                    "pos": pos,
                    "from": "N",
                    "to": "Q",
                    "reason": f"N{pos}Q to remove deamidation ({motif} motif)"
                })
        
        # Then isomerization (only if not already handled by deamidation)
        elif pos in isomerization_positions:
            site = isomerization_positions[pos]
            motif = site.get('motif', '')
            
            if pos < 1 or pos > len(seq):
                continue
            
            idx = pos - 1  # Convert to 0-based index
            current_aa = seq[idx]
            
            if current_aa == 'D':
                seq_list[idx] = 'E'
                mutations.append({
                    "pos": pos,
                    "from": "D",
                    "to": "E",
                    "reason": f"D{pos}E to reduce Asp isomerization ({motif} motif)"
                })
    
    # Reverse mutations list to have them in ascending position order
    mutations.reverse()
    
    return {
        "sequence": ''.join(seq_list),
        "mutations": mutations
    }










