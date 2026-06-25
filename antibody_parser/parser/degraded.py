"""
parser/degraded.py

（fallback）
"""

from typing import Dict, Optional


def fallback_segmentation(sequence: str, chain_type_hint: Optional[str] = None) -> Dict[str, str]:
    """
    FR/CDR。
    
    ，。
    
    Args:
        sequence: V
        chain_type_hint: 
    
    Returns:
        
    """
    n = len(sequence)
    regions = {
        "FR1": "",
        "CDR1": "",
        "FR2": "",
        "CDR2": "",
        "FR3": "",
        "CDR3": "",
        "FR4": "",
    }
    
    if chain_type_hint and chain_type_hint.upper == "H":
        # （VH/VHH）（IMGT，）
        boundaries = {
            "FR1": (0, 25),
            "CDR1": (26, 37),
            "FR2": (38, 54),
            "CDR2": (55, 64),
            "FR3": (65, 103),
            "CDR3": (104, 116),
            "FR4": (117, n - 1),
        }
    else:
        # （VL/VK）（IMGT，）
        boundaries = {
            "FR1": (0, 22),
            "CDR1": (23, 33),
            "FR2": (34, 48),
            "CDR2": (49, 55),
            "FR3": (56, 87),
            "CDR3": (88, 96),
            "FR4": (97, n - 1),
        }
    
    # 
    for region, (start, end) in boundaries.items:
        start = max(0, min(start, n - 1))
        end = max(start, min(end, n - 1))
        if start < n and end < n:
            regions[region] = sequence[start:end + 1]
    
    return regions





















