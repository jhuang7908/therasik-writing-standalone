"""
FR

FR（），
：FR，CDR（CDRcase by case）
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
import re


def count_fr_hla_hotspots(framework_seq: str) -> Dict[str, Any]:
    """
    FRHLA hotspot
    
    ，HLA-IImotif
    
    Args:
        framework_seq: （FR1+FR2+FR3+FR4）
    
    Returns:
        {
            'fr_hotspot_count': int,
            'fr_immuno_risk': str,  # 'low', 'medium', 'high'
            'hotspots': List[Dict],  # 
        }
    """
    if not framework_seq:
        return {
            'fr_hotspot_count': 0,
            'fr_immuno_risk': 'low',
            'hotspots': [],
        }
    
    hotspots = []
    
    # HLA-IImotif（9-mer15-mer）
    # HLA-II
    
    # 1. （DERK）
    charged_pattern = re.compile(r'[DERK]{3,}')  # 3
    for match in charged_pattern.finditer(framework_seq):
        hotspots.append({
            'position': match.start() + 1,  # 1-based
            'motif': match.group(),
            'type': 'charged_cluster',
            'risk': 'medium',
        })
    
    # 2. （FWY）
    aromatic_pattern = re.compile(r'[FWY]{2,}')  # 2
    for match in aromatic_pattern.finditer(framework_seq):
        hotspots.append({
            'position': match.start() + 1,
            'motif': match.group(),
            'type': 'aromatic_cluster',
            'risk': 'low',
        })
    
    # 3. HLA-IImotif（）
    # HLA-DR
    known_motifs = [
        (r'[ILV][DERK][ILV]', 'hydrophobic_charged_hydrophobic', 'medium'),
        (r'[DERK][ILV][DERK]', 'charged_hydrophobic_charged', 'medium'),
        (r'[FWY][DERK]', 'aromatic_charged', 'low'),
        (r'[DERK][FWY]', 'charged_aromatic', 'low'),
    ]
    
    for pattern, motif_type, risk in known_motifs:
        for match in re.finditer(pattern, framework_seq):
            # 
            pos = match.start() + 1
            if not any(h['position'] == pos for h in hotspots):
                hotspots.append({
                    'position': pos,
                    'motif': match.group(),
                    'type': motif_type,
                    'risk': risk,
                })
    
    # 
    high_risk_count = sum(1 for h in hotspots if h['risk'] == 'high')
    medium_risk_count = sum(1 for h in hotspots if h['risk'] == 'medium')
    total_count = len(hotspots)
    
    # 
    if total_count == 0:
        fr_immuno_risk = 'low'
    elif high_risk_count >= 2 or total_count >= 5:
        fr_immuno_risk = 'high'
    elif high_risk_count >= 1 or medium_risk_count >= 3:
        fr_immuno_risk = 'medium'
    else:
        fr_immuno_risk = 'low'
    
    return {
        'fr_hotspot_count': total_count,
        'fr_immuno_risk': fr_immuno_risk,
        'hotspots': hotspots[:10],  # 10，
    }


def assess_fr_immunogenicity_risk(framework_seq: str) -> Dict[str, Any]:
    """
    FR（）
    
    ，
    v3_immunogenicity.py
    
    Args:
        framework_seq: 
    
    Returns:
        {
            'fr_hotspot_count': int,
            'fr_immuno_risk': str,  # 'low', 'medium', 'high'
            'hotspots': List[Dict],
            'recommendation': str,
        }
    """
    result = count_fr_hla_hotspots(framework_seq)
    
    # 
    risk = result['fr_immuno_risk']
    if risk == 'low':
        recommendation = 'FR，'
    elif risk == 'medium':
        recommendation = 'FR，'
    else:
        recommendation = 'FR，'
    
    result['recommendation'] = recommendation
    
    return result


















