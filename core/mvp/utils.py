"""
Utility functions for MVP Pipeline
"""

from typing import Dict, List, Any, Optional, Tuple
import re

# IMGT region definitions
IMGT_REGIONS = {
    "FR1": {"start": 1, "end": 26},
    "CDR1": {"start": 27, "end": 38},
    "FR2": {"start": 39, "end": 55},
    "CDR2": {"start": 56, "end": 65},
    "FR3": {"start": 66, "end": 104},
    "CDR3": {"start": 105, "end": 117},
    "FR4": {"start": 118, "end": 128}
}

# VHH hallmark positions (IMGT FR2 only; pos37 is CDR1, not a hallmark)
VHH_HALLMARK_POSITIONS = [44, 45, 47]

# Vernier positions (IMGT) for VH
VERNIER_POSITIONS_VH = [4, 6, 23, 24, 26, 48, 49, 67, 69, 71, 73, 78, 93]


def parse_imgt_position(imgt_pos: Optional[str]) -> Optional[int]:
    """Parse IMGT position string to integer"""
    if not imgt_pos or imgt_pos == "None":
        return None
    match = re.match(r"^(\d+)", str(imgt_pos))
    if match:
        return int(match.group(1))
    return None


def extract_regions_from_dual_map(dual_map: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Extract FR and CDR regions from dual_map using IMGT positions
    
    Args:
        dual_map: List of dual_map entries with imgt_pos and aa fields
        
    Returns:
        Dictionary with FR1, CDR1, FR2, CDR2, FR3, CDR3, FR4 sequences
    """
    regions = {
        "FR1": [],
        "CDR1": [],
        "FR2": [],
        "CDR2": [],
        "FR3": [],
        "CDR3": [],
        "FR4": []
    }
    
    for entry in dual_map:
        imgt_pos = parse_imgt_position(entry.get("imgt_pos"))
        aa = entry.get("aa", "")
        
        if imgt_pos is None or not aa or aa == "-":
            continue
        
        # Assign to region based on IMGT position
        if IMGT_REGIONS["FR1"]["start"] <= imgt_pos <= IMGT_REGIONS["FR1"]["end"]:
            regions["FR1"].append(aa)
        elif IMGT_REGIONS["CDR1"]["start"] <= imgt_pos <= IMGT_REGIONS["CDR1"]["end"]:
            regions["CDR1"].append(aa)
        elif IMGT_REGIONS["FR2"]["start"] <= imgt_pos <= IMGT_REGIONS["FR2"]["end"]:
            regions["FR2"].append(aa)
        elif IMGT_REGIONS["CDR2"]["start"] <= imgt_pos <= IMGT_REGIONS["CDR2"]["end"]:
            regions["CDR2"].append(aa)
        elif IMGT_REGIONS["FR3"]["start"] <= imgt_pos <= IMGT_REGIONS["FR3"]["end"]:
            regions["FR3"].append(aa)
        elif IMGT_REGIONS["CDR3"]["start"] <= imgt_pos <= IMGT_REGIONS["CDR3"]["end"]:
            regions["CDR3"].append(aa)
        elif IMGT_REGIONS["FR4"]["start"] <= imgt_pos <= IMGT_REGIONS["FR4"]["end"]:
            regions["FR4"].append(aa)
    
    return {k: "".join(v) for k, v in regions.items()}


def calculate_fr_identity(orig_fr: str, template_fr: str) -> float:
    """Calculate sequence identity between two FR regions"""
    if not orig_fr or not template_fr:
        return 0.0
    min_len = min(len(orig_fr), len(template_fr))
    if min_len == 0:
        return 0.0
    matches = sum(1 for i in range(min_len) if orig_fr[i] == template_fr[i])
    return matches / min_len


def calculate_fr_distance(orig_fr: str, template_fr: str) -> float:
    """Calculate distance (1 - identity) between two FR regions"""
    identity = calculate_fr_identity(orig_fr, template_fr)
    return 1.0 - identity


def calculate_vernier_identity(dual_map: List[Dict[str, Any]], template_regions: Dict[str, str]) -> float:
    """
    Calculate vernier zone identity between original and template
    
    Args:
        dual_map: Original sequence dual_map
        template_regions: Template FR regions
        
    Returns:
        Vernier identity score (0.0-1.0)
    """
    # Build IMGT position -> AA map for original
    orig_map: Dict[int, str] = {}
    for entry in dual_map:
        imgt_pos = parse_imgt_position(entry.get("imgt_pos"))
        aa = entry.get("aa", "")
        if imgt_pos and aa and aa != "-":
            orig_map[imgt_pos] = aa
    
    # Build template IMGT position -> AA map (simplified: assume standard numbering)
    template_map: Dict[int, str] = {}
    template_seq = template_regions.get("FR1", "") + template_regions.get("FR2", "") + template_regions.get("FR3", "")
    
    # Map template sequence to IMGT positions (simplified)
    pos_idx = 0
    for region_name in ["FR1", "FR2", "FR3"]:
        region_seq = template_regions.get(region_name, "")
        region_info = IMGT_REGIONS.get(region_name)
        if region_info:
            for i, aa in enumerate(region_seq):
                imgt_pos = region_info["start"] + i
                if imgt_pos <= region_info["end"]:
                    template_map[imgt_pos] = aa
    
    # Calculate identity at vernier positions
    vernier_matches = 0
    vernier_total = 0
    
    for pos in VERNIER_POSITIONS_VH:
        orig_aa = orig_map.get(pos)
        template_aa = template_map.get(pos)
        if orig_aa and template_aa:
            vernier_total += 1
            if orig_aa == template_aa:
                vernier_matches += 1
    
    return vernier_matches / vernier_total if vernier_total > 0 else 0.0


def check_hallmark_status(dual_map: List[Dict[str, Any]], template_regions: Dict[str, str]) -> str:
    """
    Check hallmark status: pass or conflict
    
    Args:
        dual_map: Original sequence dual_map
        template_regions: Template FR regions
        
    Returns:
        "pass" or "conflict"
    """
    # Build original hallmark map
    orig_hallmarks: Dict[int, str] = {}
    for entry in dual_map:
        imgt_pos = parse_imgt_position(entry.get("imgt_pos"))
        aa = entry.get("aa", "")
        if imgt_pos in VHH_HALLMARK_POSITIONS and aa and aa != "-":
            orig_hallmarks[imgt_pos] = aa
    
    # Build template hallmark map (from FR2)
    template_fr2 = template_regions.get("FR2", "")
    # FR2 starts at IMGT 39, so position 37 is at index -2 (before FR2)
    # Position 44 is at index 5 (44-39=5), 45 at 6, 47 at 8
    template_hallmarks: Dict[int, str] = {}
    if len(template_fr2) > 8:
        # Position 44 (FR2 index 5)
        if len(template_fr2) > 5:
            template_hallmarks[44] = template_fr2[5]
        # Position 45 (FR2 index 6)
        if len(template_fr2) > 6:
            template_hallmarks[45] = template_fr2[6]
        # Position 47 (FR2 index 8)
        if len(template_fr2) > 8:
            template_hallmarks[47] = template_fr2[8]
    
    # Check conflicts (simplified: if any hallmark position differs significantly)
    conflicts = 0
    for pos in VHH_HALLMARK_POSITIONS:
        orig_aa = orig_hallmarks.get(pos)
        template_aa = template_hallmarks.get(pos)
        if orig_aa and template_aa and orig_aa != template_aa:
            conflicts += 1
    
    # MVP: if >1 conflict, mark as conflict
    return "conflict" if conflicts > 1 else "pass"


def rebuild_sequence_from_regions(regions: Dict[str, str]) -> str:
    """Rebuild V region sequence from FR/CDR regions"""
    return "".join([
        regions.get("FR1", ""),
        regions.get("CDR1", ""),
        regions.get("FR2", ""),
        regions.get("CDR2", ""),
        regions.get("FR3", ""),
        regions.get("CDR3", ""),
        regions.get("FR4", "")
    ])


def extract_mutations(orig_regions: Dict[str, str], candidate_regions: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Extract mutation list comparing original and candidate regions
    
    Returns list of mutations in format:
    [{"region": "FR1", "imgt_pos": 5, "orig_aa": "V", "new_aa": "L", "seq_idx": 4}]
    """
    mutations = []
    
    # Build position maps for both sequences
    orig_pos_map: Dict[int, Tuple[str, str]] = {}  # imgt_pos -> (aa, region)
    candidate_pos_map: Dict[int, Tuple[str, str]] = {}
    
    # Map original
    for region_name in ["FR1", "FR2", "FR3", "FR4"]:
        region_seq = orig_regions.get(region_name, "")
        region_info = IMGT_REGIONS.get(region_name)
        if region_info:
            for i, aa in enumerate(region_seq):
                imgt_pos = region_info["start"] + i
                if imgt_pos <= region_info["end"]:
                    orig_pos_map[imgt_pos] = (aa, region_name)
    
    # Map candidate
    for region_name in ["FR1", "FR2", "FR3", "FR4"]:
        region_seq = candidate_regions.get(region_name, "")
        region_info = IMGT_REGIONS.get(region_name)
        if region_info:
            for i, aa in enumerate(region_seq):
                imgt_pos = region_info["start"] + i
                if imgt_pos <= region_info["end"]:
                    candidate_pos_map[imgt_pos] = (aa, region_name)
    
    # Find differences (only in FR regions)
    for imgt_pos in sorted(set(orig_pos_map.keys()) & set(candidate_pos_map.keys())):
        orig_aa, region = orig_pos_map[imgt_pos]
        candidate_aa, _ = candidate_pos_map[imgt_pos]
        
        if orig_aa != candidate_aa and region.startswith("FR"):
            mutations.append({
                "region": region,
                "imgt_pos": imgt_pos,
                "orig_aa": orig_aa,
                "new_aa": candidate_aa
            })
    
    return mutations

