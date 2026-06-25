"""
CDR grafting 

FR–CDR，grafting

: 3.0.0
:
  - IMGT numbering scheme (FR–CDR)
  - （FR–CDR interface residues）
  - VHH grafting
:
  - category change (hydrophobic ↔ polar ↔ charged): +2
  - volume change (small ↔ large): +1
  - : impact_score_normalized = impact_score / interface_positions_count
:
  - normalized_score >= 0.4: ERROR
  - normalized_score >= 0.2: WARNING
  - 300VHHbenchmarking
"""

from typing import Dict, List, Tuple, Optional, Any

# 
GRAFTING_IMPACT_VERSION = "3.0.0"
GRAFTING_IMPACT_SOURCE = [
    "IMGT numbering scheme (FR–CDR boundary definition)",
    "Structural biology literature (FR–CDR interface residues)",
    "Internal VHH grafting case statistics (300 cases)"
]
GRAFTING_IMPACT_THRESHOLDS = {
    "error": 0.4,  # normalized score threshold for ERROR
    "warning": 0.2,  # normalized score threshold for WARNING
    "based_on": "Internal benchmarking of 300 VHH cases"
}

# FR–CDR （IMGT）
FR_CDR_INTERFACE_POSITIONS = {
    "CDR1": [25, 26, 27, 28, 29],  # FR1/CDR1 
    "CDR2": [52, 53, 54, 55],      # FR2/CDR2 
    "CDR3": [94, 95, 96, 101, 102] # FR3/CDR3 anchor/
}

# 
HYDROPHOBIC = set("AFILMVWY")
POLAR = set("STNQCY")
CHARGED = set("DEKHR")

# （）
SMALL = set("AGSV")
MEDIUM = set("CDNPTQEHILKM")
LARGE = set("FRWY")


def classify_residue(aa: str) -> str:
    """
    
    
    Returns:
        "hydrophobic", "polar", "charged", "other"
    """
    if aa in HYDROPHOBIC:
        return "hydrophobic"
    if aa in CHARGED:
        return "charged"
    if aa in POLAR:
        return "polar"
    return "other"


def classify_volume(aa: str) -> str:
    """
    
    
    Returns:
        "small", "medium", "large"
    """
    if aa in SMALL:
        return "small"
    if aa in LARGE:
        return "large"
    return "medium"


def has_big_volume_change(aa_o: str, aa_h: str) -> bool:
    """
    
    
    ：G→W, A→R, S→F 
    """
    vol_o = classify_volume(aa_o)
    vol_h = classify_volume(aa_h)
    
    # →  → 
    if (vol_o == "small" and vol_h == "large") or \
       (vol_o == "large" and vol_h == "small"):
        return True
    
    return False


def imgt_pos_to_sequence_index(imgt_pos: int, regions: Dict[str, str]) -> Optional[int]:
    """
    IMGT（0-based）
    
    Args:
        imgt_pos: IMGT（1-based）
        regions: 
    
    Returns:
        （0-based），None
    """
    from core.vhh_qa_validation import IMGT_REGIONS
    
    # 
    for region_name, bounds in IMGT_REGIONS.items():
        if bounds["start"] <= imgt_pos <= bounds["end"]:
            region_seq = regions.get(region_name, "")
            if not region_seq:
                return None
            
            # （0-based）
            local_idx = imgt_pos - bounds["start"]
            if 0 <= local_idx < len(region_seq):
                # 
                # 
                seq_idx = 0
                for prev_region in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]:
                    if prev_region == region_name:
                        seq_idx += local_idx
                        break
                    seq_idx += len(regions.get(prev_region, ""))
                return seq_idx
            return None
    return None


def qa_grafting_impact(
    orig_regions: Dict[str, str],
    hum_regions: Dict[str, str]
) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """
    CDR graftingFR–CDR
    
    Args:
        orig_regions: 
        hum_regions: 
    
    Returns:
        (errors, warnings, impact_details)
        impact_details：
        - impact_score: 
        - interface_changes: 
    """
    errors = []
    warnings = []
    impact_score = 0
    interface_changes = []
    
    # 
    from core.vhh_qa_validation import rebuild_v_region_from_regions
    orig_full = rebuild_v_region_from_regions(orig_regions)
    hum_full = rebuild_v_region_from_regions(hum_regions)
    
    if len(orig_full) != len(hum_full):
        warnings.append(
            f"({len(orig_full)})({len(hum_full)})，"
            "grafting。"
        )
        return errors, warnings, {"impact_score": 0, "interface_changes": []}
    
    # 
    for cdr_name, positions in FR_CDR_INTERFACE_POSITIONS.items():
        for imgt_pos in positions:
            # 
            orig_idx = imgt_pos_to_sequence_index(imgt_pos, orig_regions)
            hum_idx = imgt_pos_to_sequence_index(imgt_pos, hum_regions)
            
            if orig_idx is None or hum_idx is None:
                continue
            
            if orig_idx >= len(orig_full) or hum_idx >= len(hum_full):
                continue
            
            aa_o = orig_full[orig_idx]
            aa_h = hum_full[hum_idx]
            
            if aa_o == aa_h:
                continue  # 
            
            # 
            cat_o = classify_residue(aa_o)
            cat_h = classify_residue(aa_h)
            
            # 
            position_score = 0
            change_type = []
            
            # （）
            if cat_o != cat_h:
                position_score += 2
                change_type.append(f"{cat_o}→{cat_h}")
            
            # （）
            if has_big_volume_change(aa_o, aa_h):
                position_score += 1
                change_type.append("volume_change")
            
            impact_score += position_score
            
            interface_changes.append({
                "cdr": cdr_name,
                "imgt_pos": imgt_pos,
                "from": aa_o,
                "to": aa_h,
                "category_change": cat_o != cat_h,
                "volume_change": has_big_volume_change(aa_o, aa_h),
                "score": position_score,
                "change_type": change_type
            })
    
    # 
    total_interface_positions = sum(len(positions) for positions in FR_CDR_INTERFACE_POSITIONS.values())
    if total_interface_positions > 0:
        impact_score_normalized = impact_score / total_interface_positions
    else:
        impact_score_normalized = 0.0
    
    # （CDR3）
    if impact_score_normalized >= GRAFTING_IMPACT_THRESHOLDS["error"]:
        errors.append(
            f"CDR–FR  (impact_score={impact_score}, "
            f"normalized={impact_score_normalized:.3f})，"
            "，。"
        )
    elif impact_score_normalized >= GRAFTING_IMPACT_THRESHOLDS["warning"]:
        warnings.append(
            f"CDR–FR  (impact_score={impact_score}, "
            f"normalized={impact_score_normalized:.3f})，"
            "。"
        )
    
    impact_details = {
        "impact_score": impact_score,
        "impact_score_normalized": round(impact_score_normalized, 3),
        "interface_changes": interface_changes,
        "total_interface_positions": total_interface_positions,
        "thresholds": GRAFTING_IMPACT_THRESHOLDS
    }
    
    return errors, warnings, impact_details

