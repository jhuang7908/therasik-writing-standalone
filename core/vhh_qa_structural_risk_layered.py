"""
VHH

：
1. FR2 hydrophilic patch
2. Graftinginterface
3. CDR3 anchor residues
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

# IMGT（v3.3）
IMGT_REGIONS = {
    "FR1": {"start": 1, "end": 26},
    "CDR1": {"start": 27, "end": 38},
    "FR2": {"start": 39, "end": 55},
    "CDR2": {"start": 56, "end": 65},
    "FR3": {"start": 66, "end": 104},
    "CDR3": {"start": 105, "end": 117},
    "FR4": {"start": 118, "end": 128},
}

# VHH hallmark（IMGT）— FR2 only; pos37 is CDR1 (IMGT 27-38), not a hallmark
VHH_HALLMARK_POSITIONS = [44, 45, 47]

# CDR3 anchor（IMGT）
CDR3_ANCHOR_POSITIONS = [95, 96, 101, 102]


@dataclass
class StructuralRiskComponents:
    """"""
    fr2_hydrophilic_patch_risk: float  # 0~1, FR2 hydrophilic patch
    grafting_interface_risk: float      # 0~1, Graftinginterface
    cdr3_anchor_risk: float            # 0~1, CDR3 anchor residues
    
    @property
    def total_risk(self) -> float:
        """
        （，）
        
        ：
        - FR2 risk: 0.3
        - Grafting risk: 0.3
        - CDR3 anchor risk: 0.4
        """
        weighted_sum = (
            0.3 * self.fr2_hydrophilic_patch_risk +
            0.3 * self.grafting_interface_risk +
            0.4 * self.cdr3_anchor_risk
        )
        # （grafting_risk=1.0），
        max_single = max(
            self.fr2_hydrophilic_patch_risk,
            self.grafting_interface_risk,
            self.cdr3_anchor_risk
        )
        # ：，
        return max(weighted_sum, max_single * 0.8)
    
    def to_dict(self) -> Dict[str, float]:
        """"""
        return {
            "fr2_hydrophilic_patch_risk": self.fr2_hydrophilic_patch_risk,
            "grafting_interface_risk": self.grafting_interface_risk,
            "cdr3_anchor_risk": self.cdr3_anchor_risk,
            "total_risk": self.total_risk
        }


def compute_layered_structural_risk(
    orig_regions: Dict[str, str],
    hum_regions: Dict[str, str],
    template_info: Optional[Dict[str, Any]] = None
) -> StructuralRiskComponents:
    """
    
    
    Args:
        orig_regions: 
        hum_regions: 
        template_info: （anchor）
    
    Returns:
        StructuralRiskComponents
    """
    # 1. FR2 hydrophilic patch
    fr2_risk = _compute_fr2_hydrophilic_patch_risk(orig_regions, hum_regions)
    
    # 2. Grafting interface
    grafting_risk = _compute_grafting_interface_risk(orig_regions, hum_regions)
    
    # 3. CDR3 anchor（）
    anchor_risk = _compute_cdr3_anchor_risk(orig_regions, hum_regions, template_info)
    
    return StructuralRiskComponents(
        fr2_hydrophilic_patch_risk=fr2_risk,
        grafting_interface_risk=grafting_risk,
        cdr3_anchor_risk=anchor_risk
    )


def _compute_fr2_hydrophilic_patch_risk(
    orig_regions: Dict[str, str],
    hum_regions: Dict[str, str]
) -> float:
    """
    FR2 hydrophilic patch
    
    VHH hallmark：44, 45, 47 (FR2 only; pos37 is CDR1, preserved by graft)
    hydrophilic patch，
    """
    orig_fr2 = orig_regions.get("FR2", "")
    hum_fr2 = hum_regions.get("FR2", "")
    
    if not orig_fr2 or not hum_fr2:
        return 1.0  # FR2，
    
    # FR2IMGT 39
    fr2_start = IMGT_REGIONS["FR2"]["start"]  # 39
    
    # hallmark
    preserved_count = 0
    for pos in VHH_HALLMARK_POSITIONS:
        # FR2（0-based）
        local_idx = pos - fr2_start
        
        if 0 <= local_idx < len(orig_fr2) and 0 <= local_idx < len(hum_fr2):
            orig_aa = orig_fr2[local_idx]
            hum_aa = hum_fr2[local_idx]
            
            # hydrophilic，
            if orig_aa == hum_aa:
                preserved_count += 1
            elif _is_hydrophilic_improvement(orig_aa, hum_aa):
                preserved_count += 1
    
    #  = 1 - 
    risk = 1.0 - (preserved_count / len(VHH_HALLMARK_POSITIONS))
    return max(0.0, min(1.0, risk))


def _compute_grafting_interface_risk(
    orig_regions: Dict[str, str],
    hum_regions: Dict[str, str]
) -> float:
    """
    graftinginterface（ΔΔG proxy）
    
    qa_grafting_impact，0~1
    """
    try:
        from core.vhh_qa_grafting import qa_grafting_impact
        
        _, _, impact_details = qa_grafting_impact(orig_regions, hum_regions)
        impact_normalized = impact_details.get("impact_score_normalized", 0)
        
        # 0~1
        # impact_normalized0~1，1
        risk = min(1.0, impact_normalized / 0.4)  # 0.4error
        return risk
    except ImportError:
        # qa_grafting_impact，
        return 0.5


def _compute_cdr3_anchor_risk(
    orig_regions: Dict[str, str],
    hum_regions: Dict[str, str],
    template_info: Optional[Dict[str, Any]] = None
) -> float:
    """
    CDR3 anchor residues（）
    
    CDR3 anchor：IMGT 95, 96, 101, 102
    FR3，CDR3
    
    101/102，humanized
    structural_risk ≥ 0.7 → fail
    """
    orig_fr3 = orig_regions.get("FR3", "")
    hum_fr3 = hum_regions.get("FR3", "")
    
    if not orig_fr3 or not hum_fr3:
        return 1.0  # FR3，
    
    # FR3IMGT 66
    fr3_start = IMGT_REGIONS["FR3"]["start"]  # 66
    
    # anchor
    mismatches = 0
    critical_mismatches = 0  # 101/102
    
    for pos in CDR3_ANCHOR_POSITIONS:
        local_idx = pos - fr3_start
        
        if 0 <= local_idx < len(orig_fr3) and 0 <= local_idx < len(hum_fr3):
            orig_aa = orig_fr3[local_idx]
            hum_aa = hum_fr3[local_idx]
            
            if orig_aa != hum_aa:
                mismatches += 1
                # 101/102
                if pos in [101, 102]:
                    critical_mismatches += 1
    
    # 
    if critical_mismatches > 0:
        # ，
        risk = 0.7 + (critical_mismatches * 0.15)  # 0.7，mismatch +0.15
    else:
        # ，
        risk = mismatches * 0.2  # mismatch +0.2
    
    # ，anchor
    if template_info:
        template_fr3 = template_info.get("fr3_sequence", "")
        if not template_fr3 and isinstance(template_info, dict):
            # templateFR3
            template_regions = template_info.get("regions", {})
            template_fr3 = template_regions.get("FR3", "")
        
        if template_fr3:
            # 101/102
            for pos in [101, 102]:
                local_idx = pos - fr3_start
                if 0 <= local_idx < len(template_fr3) and 0 <= local_idx < len(hum_fr3):
                    template_aa = template_fr3[local_idx]
                    hum_aa = hum_fr3[local_idx]
                    
                    # humanizedanchor，
                    if template_aa != hum_aa:
                        risk = max(risk, 0.8)

    # VHH: long / stabilised CDR3 loops tolerate FR3 anchor substitution vs VH3 template.
    cdr3_seq = (orig_regions or {}).get("CDR3", "") or ""
    cdr3_len = len(cdr3_seq)
    if cdr3_len >= 20:
        risk *= 0.42
    elif cdr3_len >= 16:
        risk *= 0.58
    elif cdr3_len >= 14:
        risk *= 0.72
    if cdr3_len >= 12 and cdr3_seq.count("C") >= 2:
        risk *= 0.92
    
    return max(0.0, min(1.0, risk))


def _is_hydrophilic_improvement(orig_aa: str, hum_aa: str) -> bool:
    """
    （improvement）
    
    ：
    - ：D, E, K, R, H, N, Q, S, T, Y
    - ：A, V, L, I, M, F, W, P
    """
    hydrophilic = set("DEKRHNQSTY")
    hydrophobic = set("AVLIMFWP")
    
    orig_is_hydrophilic = orig_aa in hydrophilic
    hum_is_hydrophilic = hum_aa in hydrophilic
    
    # ，，improvement
    if orig_aa in hydrophobic and hum_aa in hydrophilic:
        return True
    if orig_aa in hydrophilic and hum_aa in hydrophilic:
        return True
    
    return False

