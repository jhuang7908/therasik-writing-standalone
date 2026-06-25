"""
VHH FR–CDR /

CDRFR

: 3.0.0
:
  - SAbDab VHH canonical classes (73VHH)
  - IMGT numbering notes
  - VHH
: VHH（Human VH3 VHH-SAFE）
: 
  - : CDR3(≥15aa) + FR3(<38aa) → ERROR
  - :  → WARNING
: （）
"""

from typing import Tuple, Dict, Any

# 
QA_V3_RULES_VERSION = "3.0.0"
QA_V3_RULES_SOURCE = [
    "SAbDab VHH canonical classes",
    "IMGT numbering notes",
    "Internal VHH structure database (73 alpaca VHH cases)",
    "Human VH3 VHH-SAFE template panel statistics"
]
QA_V3_RULES_SCOPE = "VHH humanization (Human VH3 VHH-SAFE template panel)"
QA_V3_RULES_CUSTOMIZABLE = False

# CDR1–FR2 
# : 73VHH，SAbDab canonical classes
# : （WARNING）
ALLOWED_VHH_CDR1_FR2_COMBOS = [
    # (cdr1_len_range, fr2_len_range, note, rule_strength)
    ((5, 8), (15, 19), "canonical_CDR1_short", "weak"),
    ((9, 12), (15, 19), "canonical_CDR1_long", "weak"),
    ((6, 7), (15, 19), "non_canonical_CDR1_short", "weak"),
    ((13, 15), (16, 20), "non_canonical_CDR1_long", "weak"),
]

# CDR3–FR3 
# : 73VHH，
# : 
#   - : CDR3≥15aa + FR3<38aa → ERROR（）
#   - :  → WARNING
ALLOWED_VHH_CDR3_FR3_COMBOS = [
    # (cdr3_len_range, fr3_len_range, note, rule_strength)
    ((2, 14), (35, 42), "cdr3_normal", "weak"),
    ((15, 25), (38, 45), "cdr3_long_needs_long_fr3", "strong"),  # 
    ((26, 35), (40, 50), "cdr3_very_long_needs_very_long_fr3", "strong"),  # 
]

# CDR2–FR2/FR3 （CDR2FR2FR3）
ALLOWED_VHH_CDR2_COMBOS = [
    # (cdr2_len_range, fr2_len_range, fr3_len_range, note)
    ((7, 9), (15, 19), (35, 42), "canonical_CDR2"),
    ((10, 12), (15, 19), (35, 42), "canonical_CDR2_long"),
    ((5, 6), (15, 19), (35, 42), "non_canonical_CDR2_short"),
    ((13, 15), (16, 20), (38, 45), "non_canonical_CDR2_long"),
]


def check_cdr1_fr2_compatibility(cdr1_len: int, fr2_len: int) -> Tuple[bool, str, str]:
    """
    CDR1FR2
    
    Returns:
        (is_compatible, note, rule_strength)
    """
    for (lo1, hi1), (lo2, hi2), note, strength in ALLOWED_VHH_CDR1_FR2_COMBOS:
        if lo1 <= cdr1_len <= hi1 and lo2 <= fr2_len <= hi2:
            return True, note, strength
    return False, "non_typical_combination", "weak"


def check_cdr3_fr3_compatibility(cdr3_len: int, fr3_len: int) -> Tuple[bool, str, str]:
    """
    CDR3FR3
    
    Returns:
        (is_compatible, note, rule_strength)
    """
    for (lo1, hi1), (lo2, hi2), note, strength in ALLOWED_VHH_CDR3_FR3_COMBOS:
        if lo1 <= cdr3_len <= hi1 and lo2 <= fr3_len <= hi2:
            return True, note, strength
    return False, "non_typical_combination", "weak"


def check_cdr2_compatibility(cdr2_len: int, fr2_len: int, fr3_len: int) -> Tuple[bool, str, str]:
    """
    CDR2FR2/FR3
    
    Returns:
        (is_compatible, note, rule_strength)
    """
    for (lo1, hi1), (lo2, hi2), (lo3, hi3), note in ALLOWED_VHH_CDR2_COMBOS:
        if lo1 <= cdr2_len <= hi1 and lo2 <= fr2_len <= hi2 and lo3 <= fr3_len <= hi3:
            return True, note, "weak"
    return False, "non_typical_combination", "weak"

