"""
VHH Developability 

VHHdevelopability（），：
- CMC liabilities（）
- （FR2FR3）
- 
- 
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from core.cmc.generic_cmc_scanner import scan_cmc_liabilities


def grade_developability(score: float, liabilities: List[Dict[str, Any]]) -> str:
    """
    developabilityliabilities
    
    Args:
        score: Developability（0-1）
        liabilities: 
    
    Returns:
        'A', 'B',  'C'
    """
    # liabilities
    high_risk_types = ['deamidation', 'isomerization', 'oxidation']
    high_risk_count = sum(1 for liab in liabilities if liab.get('risk') == 'high' and liab.get('type') in high_risk_types)
    
    # A：dev_score >= 0.8，liabilities
    if score >= 0.8 and high_risk_count == 0:
        return 'A'
    
    # C：dev_score < 0.6 （≥2）
    if score < 0.6 or high_risk_count >= 2:
        return 'C'
    
    # B：0.6 <= dev_score < 0.8，
    return 'B'


def analyze_developability(
    framework_seq: str,
    fr2_seq: Optional[str] = None,
    fr3_seq: Optional[str] = None,
    include_grade: bool = True,
) -> Dict[str, Any]:
    """
    VHHdevelopability
    
    Args:
        framework_seq: （FR1+FR2+FR3+FR4）
        fr2_seq: FR2（，）
        fr3_seq: FR3（，）
    
    Returns:
        {
            'score': float,  # 0-1，
            'liabilities': List[Dict],  # 
            'fr2_risk': float,  # FR2（0-1，）
            'fr3_risk': float,  # FR3（0-1，）
            'notes': str,  # 
        }
    """
    if not framework_seq:
        return {
            'score': 0.0,
            'liabilities': [],
            'fr2_risk': 1.0,
            'fr3_risk': 1.0,
            'notes': 'Empty framework sequence',
        }
    
    # 1. CMC liabilities
    try:
        cmc_result = scan_cmc_liabilities(framework_seq)
    except Exception as e:
        return {
            'score': 0.5,
            'liabilities': [],
            'fr2_risk': 0.5,
            'fr3_risk': 0.5,
            'notes': f'CMC scan failed: {e}',
        }
    
    # 2. liabilities
    liabilities = []
    
    # N-
    for site in cmc_result.get('n_glyc_sites', []):
        liabilities.append({
            'type': 'n_glycosylation',
            'position': site.get('position', 0),
            'motif': site.get('motif', ''),
            'risk': 'medium',
            'description': f"N-glycosylation site: {site.get('motif', '')}",
        })
    
    # 
    for site in cmc_result.get('deamidation_sites', []):
        liabilities.append({
            'type': 'deamidation',
            'position': site.get('position', 0),
            'motif': site.get('motif', ''),
            'risk': 'high',
            'description': f"Deamidation site: {site.get('motif', '')}",
        })
    
    # 
    for site in cmc_result.get('isomerization_sites', []):
        liabilities.append({
            'type': 'isomerization',
            'position': site.get('position', 0),
            'motif': site.get('motif', ''),
            'risk': 'high',
            'description': f"Asp isomerization site: {site.get('motif', '')}",
        })
    
    # 
    for site in cmc_result.get('oxidation_sites', []):
        liabilities.append({
            'type': 'oxidation',
            'position': site.get('position', 0),
            'residue': site.get('residue', ''),
            'risk': 'medium',
            'description': f"Oxidation-prone residue: {site.get('residue', '')}",
        })
    
    # 3. FR2FR3
    fr2_risk = _assess_fr2_risk(fr2_seq if fr2_seq else framework_seq)
    fr3_risk = _assess_fr3_risk(fr3_seq if fr3_seq else framework_seq)
    
    # 4. developability
    # ：0.5，
    base_score = 0.5
    
    # liabilities
    high_risk_count = sum(1 for liab in liabilities if liab.get('risk') == 'high')
    medium_risk_count = sum(1 for liab in liabilities if liab.get('risk') == 'medium')
    
    # （）
    base_score -= high_risk_count * 0.08  # 0.08
    base_score -= medium_risk_count * 0.04  # 0.04
    
    # FR2FR3（）
    base_score -= fr2_risk * 0.15  # FR20.15
    base_score -= fr3_risk * 0.10  # FR30.10
    
    # ：，
    if high_risk_count == 0:
        base_score += 0.2
    if medium_risk_count == 0:
        base_score += 0.1
    
    # ：FR2FR3
    if fr2_risk < 0.3:
        base_score += 0.1
    if fr3_risk < 0.3:
        base_score += 0.05
    
    # 0-1
    final_score = max(0.0, min(1.0, base_score))
    
    # 5. 
    notes_parts = []
    if high_risk_count > 0:
        notes_parts.append(f"{high_risk_count} high-risk liability sites")
    if medium_risk_count > 0:
        notes_parts.append(f"{medium_risk_count} medium-risk liability sites")
    if fr2_risk > 0.5:
        notes_parts.append("Elevated FR2 aggregation risk")
    if fr3_risk > 0.5:
        notes_parts.append("Elevated FR3 aggregation risk")
    
    notes = "; ".join(notes_parts) if notes_parts else "Low risk profile"
    
    return {
        'score': round(final_score, 3),
        'liabilities': liabilities,
        'fr2_risk': round(fr2_risk, 3),
        'fr3_risk': round(fr3_risk, 3),
        'cmc_summary': cmc_result.get('summary', {}),
        'notes': notes,
    }


def _assess_fr2_risk(fr2_seq: str) -> float:
    """
    FR2
    
    Args:
        fr2_seq: FR2
    
    Returns:
        （0-1，）
    """
    if not fr2_seq or len(fr2_seq) < 5:
        return 0.5
    
    risk = 0.0
    
    # 1. （）
    hydrophobic_aas = 'AILMFWYV'
    hydrophobic_count = sum(1 for aa in fr2_seq if aa in hydrophobic_aas)
    hydrophobic_ratio = hydrophobic_count / len(fr2_seq)
    
    if hydrophobic_ratio > 0.6:
        risk += 0.4
    elif hydrophobic_ratio > 0.5:
        risk += 0.25
    elif hydrophobic_ratio > 0.4:
        risk += 0.1
    
    # 2. （patches）
    max_hydrophobic_patch = 0
    current_patch = 0
    for aa in fr2_seq:
        if aa in hydrophobic_aas:
            current_patch += 1
            max_hydrophobic_patch = max(max_hydrophobic_patch, current_patch)
        else:
            current_patch = 0
    
    if max_hydrophobic_patch >= 4:
        risk += 0.3
    elif max_hydrophobic_patch >= 3:
        risk += 0.15
    
    # 3. （）
    positive_aas = 'KRH'
    negative_aas = 'DE'
    
    positive_count = sum(1 for aa in fr2_seq if aa in positive_aas)
    negative_count = sum(1 for aa in fr2_seq if aa in negative_aas)
    
    charge_imbalance = abs(positive_count - negative_count) / len(fr2_seq)
    if charge_imbalance > 0.3:
        risk += 0.2
    elif charge_imbalance > 0.2:
        risk += 0.1
    
    # 4. 
    #  + 
    if 'LLLL' in fr2_seq or 'VVVV' in fr2_seq or 'IIII' in fr2_seq:
        risk += 0.2
    
    return min(1.0, risk)


def _assess_fr3_risk(fr3_seq: str) -> float:
    """
    FR3
    
    Args:
        fr3_seq: FR3
    
    Returns:
        （0-1，）
    """
    if not fr3_seq or len(fr3_seq) < 10:
        return 0.5
    
    risk = 0.0
    
    # FR3FR2，
    # 1. 
    hydrophobic_aas = 'AILMFWYV'
    hydrophobic_count = sum(1 for aa in fr3_seq if aa in hydrophobic_aas)
    hydrophobic_ratio = hydrophobic_count / len(fr3_seq)
    
    if hydrophobic_ratio > 0.55:
        risk += 0.3
    elif hydrophobic_ratio > 0.45:
        risk += 0.15
    
    # 2. 
    max_hydrophobic_patch = 0
    current_patch = 0
    for aa in fr3_seq:
        if aa in hydrophobic_aas:
            current_patch += 1
            max_hydrophobic_patch = max(max_hydrophobic_patch, current_patch)
        else:
            current_patch = 0
    
    if max_hydrophobic_patch >= 5:
        risk += 0.25
    elif max_hydrophobic_patch >= 4:
        risk += 0.15
    
    # 3. 
    positive_aas = 'KRH'
    negative_aas = 'DE'
    
    positive_count = sum(1 for aa in fr3_seq if aa in positive_aas)
    negative_count = sum(1 for aa in fr3_seq if aa in negative_aas)
    
    charge_imbalance = abs(positive_count - negative_count) / len(fr3_seq)
    if charge_imbalance > 0.25:
        risk += 0.15
    
    return min(1.0, risk)

