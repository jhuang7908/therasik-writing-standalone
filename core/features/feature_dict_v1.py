"""
Feature Dictionary v1

 tagging-only 。
，、。
"""

from typing import Set, Dict, List, Optional
import re


# IMGT（）
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

# VH Hallmark Framework Positions (VH only)
VH_HALLMARK_POSITIONS = [42, 49, 50, 52, 54]

# 
CHEMICALLY_SENSITIVE_RESIDUES: Set[str] = {"N", "D", "G", "M", "W", "C"}


def parse_imgt_position(imgt_pos: Optional[str]) -> Optional[int]:
    """
    IMGT，（）
    
    Args:
        imgt_pos: IMGT， "27", "27A", "100", "100A"
    
    Returns:
        （int），None
    """
    if not imgt_pos or imgt_pos == "None" or imgt_pos is None:
        return None
    # （ "27A" -> 27, "100" -> 100）
    match = re.match(r"^(\d+)", str(imgt_pos))
    if match:
        return int(match.group(1))
    return None


def get_region_from_imgt_pos(imgt_pos: Optional[int]) -> Optional[str]:
    """
    IMGT
    
    Args:
        imgt_pos: IMGT
    
    Returns:
        （FR1/CDR1/FR2/CDR2/FR3/CDR3/FR4），None
    """
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
    """
    Vernier Zone
    
    Args:
        imgt_pos: IMGT
        chain_type:  ("H", "K", "L")
    
    Returns:
        VernierTrue
    """
    if imgt_pos is None:
        return False
    chain_key = "VH" if chain_type == "H" else "VL"
    return imgt_pos in VERNIER_POSITIONS.get(chain_key, [])


def is_vh_hallmark_position(imgt_pos: Optional[int], chain_type: str) -> bool:
    """
    VH Hallmark（VH only）
    
    Args:
        imgt_pos: IMGT
        chain_type: 
    
    Returns:
        VH HallmarkTrue
    """
    if chain_type != "H" or imgt_pos is None:
        return False
    return imgt_pos in VH_HALLMARK_POSITIONS


def is_cdr_boundary(imgt_pos: Optional[int], region: Optional[str], dual_map: List[Dict]) -> bool:
    """
    CDR
    
    ：
    - FR -> CDR CDR（CDR）
    - CDR -> FR CDR（CDR）
    
    Args:
        imgt_pos: IMGT
        region: 
        dual_map: dual_map（CDR3）
    
    Returns:
        CDRTrue
    """
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
    """
    CDR（CDR，）
    
    ：CDR1-3residue
    - CDR1: （30-35）
    - CDR2: （60-62）
    - CDR3: （110-112，）
    
    Args:
        imgt_pos: IMGT
        region: 
        dual_map: dual_map（）
    
    Returns:
        CDRTrue
    """
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
    """
    CDR3
    
    ：CDR3 residue
    
    Args:
        imgt_pos: IMGT
        region: 
    
    Returns:
        CDR3True
    """
    return region == "CDR3" and imgt_pos is not None


def is_chemically_sensitive(aa: str) -> bool:
    """
    
    
    ： N/D/G/M/W/C
    
    Args:
        aa: 
    
    Returns:
        True
    """
    return aa in CHEMICALLY_SENSITIVE_RESIDUES








