"""


CRO，：
- CDR3 anchor
- FR2 hydrophilic patch
- CDR1 torsion compatibility
- Overall structural feasibility
"""

from typing import Dict, List, Any, Optional

# IMGT（）
IMGT_REGIONS = {
    "FR1": {"start": 1, "end": 26},
    "CDR1": {"start": 27, "end": 38},
    "FR2": {"start": 39, "end": 55},
    "CDR2": {"start": 56, "end": 65},
    "FR3": {"start": 66, "end": 104},
    "CDR3": {"start": 105, "end": 117},
    "FR4": {"start": 118, "end": 128},
}

# VHH hallmark
VHH_HALLMARK_POSITIONS = {
    37: {"region": "FR2", "typical_vhh": ["F", "Y", "V"], "typical_human": ["V", "I", "L"]},
    44: {"region": "FR2", "typical_vhh": ["E", "Q", "D"], "typical_human": ["G"]},
    45: {"region": "FR2", "typical_vhh": ["R", "K"], "typical_human": ["L"]},
    47: {"region": "FR2", "typical_vhh": ["W"], "typical_human": ["W"]},
}


def _get_aa_at_imgt_position(regions: Dict[str, str], imgt_pos: int) -> Optional[str]:
    """IMGTregions"""
    for region_name, bounds in IMGT_REGIONS.items():
        if bounds["start"] <= imgt_pos <= bounds["end"]:
            region_seq = regions.get(region_name, "")
            if not region_seq:
                return None
            local_idx = imgt_pos - bounds["start"]
            if 0 <= local_idx < len(region_seq):
                return region_seq[local_idx]
            return None
    return None


def assess_cdr3_anchor_stability(
    hum_regions: Dict[str, str]
) -> Dict[str, Any]:
    """
    CDR3 anchor（IMGT 101/102）
    
    Returns:
        {
            "stability": "high/medium/low",
            "score": float,  # 0-100
            "details": {...}
        }
    """
    fr3 = hum_regions.get("FR3", "")
    cdr3 = hum_regions.get("CDR3", "")
    
    if not fr3 or not cdr3:
        return {
            "stability": "unknown",
            "score": 0,
            "details": {"error": "Missing FR3 or CDR3"}
        }
    
    # CDR3 anchor（IMGT 101-102，FR3）
    anchor_start_imgt = 101
    anchor_end_imgt = 102
    fr3_start = IMGT_REGIONS["FR3"]["start"]  # 66
    
    anchor_start_in_fr3 = anchor_start_imgt - fr3_start  # 101 - 66 = 35 (0-based)
    anchor_end_in_fr3 = anchor_end_imgt - fr3_start  # 102 - 66 = 36 (0-based)
    
    if len(fr3) < anchor_end_in_fr3 + 1:
        return {
            "stability": "low",
            "score": 30,
            "details": {"error": "FR3 too short to contain anchor residues"}
        }
    
    # anchor
    anchor_seq = fr3[anchor_start_in_fr3:anchor_end_in_fr3 + 1]
    
    # （）
    conservative_aas = {"A", "S", "T", "G", "V", "L", "I"}
    score = 50  # 
    
    # anchor，
    for aa in anchor_seq:
        if aa in conservative_aas:
            score += 20
        elif aa in {"N", "D", "Q", "E"}:  # ，
            score += 10
    
    # 
    high_risk_aas = {"P", "C"}
    for aa in anchor_seq:
        if aa in high_risk_aas:
            score -= 15
    
    score = max(0, min(100, score))
    
    if score >= 80:
        stability = "high"
    elif score >= 60:
        stability = "medium"
    else:
        stability = "low"
    
    return {
        "stability": stability,
        "score": score,
        "details": {
            "anchor_sequence": anchor_seq,
            "anchor_positions": f"IMGT {anchor_start_imgt}-{anchor_end_imgt}",
            "fr3_length": len(fr3)
        }
    }


def assess_fr2_hydrophilic_patch(
    hum_regions: Dict[str, str]
) -> Dict[str, Any]:
    """
    FR2 hydrophilic patch
    
    Returns:
        {
            "retention": "high/medium/low",
            "score": float,  # 0-100
            "details": {...}
        }
    """
    fr2 = hum_regions.get("FR2", "")
    
    if not fr2 or len(fr2) < 10:
        return {
            "retention": "unknown",
            "score": 0,
            "details": {"error": "FR2 too short"}
        }
    
    # VHH hallmark（44, 45）
    hallmark_positions = [44, 45]
    hydrophilic_count = 0
    total_hallmarks = 0
    
    for pos in hallmark_positions:
        aa = _get_aa_at_imgt_position(hum_regions, pos)
        if aa:
            total_hallmarks += 1
            # 
            if aa in {"E", "Q", "D", "N", "R", "K", "S", "T"}:
                hydrophilic_count += 1
    
    if total_hallmarks == 0:
        return {
            "retention": "low",
            "score": 20,
            "details": {"error": "Cannot assess hallmark positions"}
        }
    
    retention_ratio = hydrophilic_count / total_hallmarks
    score = retention_ratio * 100
    
    if score >= 80:
        retention = "high"
    elif score >= 50:
        retention = "medium"
    else:
        retention = "low"
    
    return {
        "retention": retention,
        "score": round(score, 1),
        "details": {
            "hydrophilic_count": hydrophilic_count,
            "total_hallmarks": total_hallmarks,
            "retention_ratio": round(retention_ratio, 2)
        }
    }


def assess_cdr1_torsion_compatibility(
    hum_regions: Dict[str, str],
    cdr1_len: int
) -> Dict[str, Any]:
    """
    CDR1 torsion compatibility
    
    Returns:
        {
            "compatibility": "acceptable/marginal/poor",
            "score": float,  # 0-100
            "details": {...}
        }
    """
    # CDR1FR1/FR2
    fr1 = hum_regions.get("FR1", "")
    fr2 = hum_regions.get("FR2", "")
    cdr1 = hum_regions.get("CDR1", "")
    
    if not fr1 or not fr2 or not cdr1:
        return {
            "compatibility": "unknown",
            "score": 0,
            "details": {"error": "Missing regions"}
        }
    
    score = 50  # 
    
    # CDR1（rule set v3.0）
    if 5 <= cdr1_len <= 12:
        score += 30  # 
    elif 13 <= cdr1_len <= 15:
        score += 15  # 
    else:
        score -= 20  # 
    
    # FR1FR2（torsion）
    fr1_end = fr1[-1] if fr1 else ""
    fr2_start = fr2[0] if fr2 else ""
    
    # 
    compatible_boundary_aas = {"A", "S", "T", "G", "V", "L"}
    if fr1_end in compatible_boundary_aas:
        score += 10
    if fr2_start in compatible_boundary_aas:
        score += 10
    
    score = max(0, min(100, score))
    
    if score >= 70:
        compatibility = "acceptable"
    elif score >= 50:
        compatibility = "marginal"
    else:
        compatibility = "poor"
    
    return {
        "compatibility": compatibility,
        "score": round(score, 1),
        "details": {
            "cdr1_length": cdr1_len,
            "fr1_end": fr1_end,
            "fr2_start": fr2_start,
            "rule_set": "v3.0"
        }
    }


def generate_conformation_risk_summary(
    hum_regions: Dict[str, str],
    qa_v3_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    
    
    Args:
        hum_regions: 
        qa_v3_result: QA v3.0（）
    
    Returns:
        conformation_risk_summary
    """
    # CDR3 anchor
    cdr3_anchor = assess_cdr3_anchor_stability(hum_regions)
    
    # FR2 hydrophilic patch
    fr2_patch = assess_fr2_hydrophilic_patch(hum_regions)
    
    # CDR1 torsion compatibility
    cdr1_len = len(hum_regions.get("CDR1", ""))
    cdr1_torsion = assess_cdr1_torsion_compatibility(hum_regions, cdr1_len)
    
    # Overall structural feasibility
    scores = [
        cdr3_anchor.get("score", 0),
        fr2_patch.get("score", 0),
        cdr1_torsion.get("score", 0)
    ]
    
    # qa_v3，structural_compatgrafting_impact
    if qa_v3_result:
        structural_compat = qa_v3_result.get("checks", {}).get("structural_compat", {})
        grafting_impact = qa_v3_result.get("checks", {}).get("grafting_impact", {})
        
        # structural_compat: error20，warning10
        if structural_compat.get("errors"):
            scores.append(50)  # 
        elif structural_compat.get("warnings"):
            scores.append(70)  # 
        else:
            scores.append(90)  # 
        
        # grafting_impact: 
        impact_norm = grafting_impact.get("impact_score_normalized", 0)
        if impact_norm >= 0.4:
            scores.append(30)  # 
        elif impact_norm >= 0.2:
            scores.append(60)  # 
        else:
            scores.append(90)  # 
    
    overall_score = sum(scores) / len(scores) if scores else 0
    
    return {
        "cdr3_anchor_stability": {
            "assessment": cdr3_anchor.get("stability", "unknown"),
            "score": cdr3_anchor.get("score", 0),
            "details": cdr3_anchor.get("details", {})
        },
        "fr2_hydrophilic_patch": {
            "assessment": fr2_patch.get("retention", "unknown"),
            "score": fr2_patch.get("score", 0),
            "details": fr2_patch.get("details", {})
        },
        "cdr1_torsion_compatibility": {
            "assessment": cdr1_torsion.get("compatibility", "unknown"),
            "score": cdr1_torsion.get("score", 0),
            "details": cdr1_torsion.get("details", {})
        },
        "overall_structural_feasibility": {
            "score": round(overall_score, 1),
            "level": "high" if overall_score >= 80 else "medium" if overall_score >= 60 else "low"
        }
    }

