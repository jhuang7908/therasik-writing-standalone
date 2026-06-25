"""
VHH：

，VHH
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass


# ============================================================================
# 
# ============================================================================

@dataclass
class OptimizationRule:
    """"""
    rule_id: str
    rule_name: str
    description: str
    applicable_regions: List[str]  # ['FR1', 'FR2', 'FR3', 'CDR1', 'CDR2', 'CDR3']
    priority: str  # 'high', 'medium', 'low'
    confidence: str  # 'high', 'medium', 'low'


# 1. （，VHH）
FRAMEWORK_RESTORATION_RULES = [
    OptimizationRule(
        rule_id="FR1_26_RESTORE",
        rule_name="FR1-26",
        description="FR1-26，（→），",
        applicable_regions=["FR1"],
        priority="high",
        confidence="high",
    ),
    OptimizationRule(
        rule_id="FR2_55_RESTORE",
        rule_name="FR2-55",
        description="FR2-55，（CDR2）",
        applicable_regions=["FR2"],
        priority="high",
        confidence="high",
    ),
    OptimizationRule(
        rule_id="FR3_104_RESTORE",
        rule_name="FR3-104",
        description="FR3-104，（CDR3）",
        applicable_regions=["FR3"],
        priority="medium",
        confidence="high",
    ),
    OptimizationRule(
        rule_id="VERNIER_ZONE_RESTORE",
        rule_name="Vernier zone",
        description="Vernier zone（27,29,30,48,49,71,73,78,94），，",
        applicable_regions=["FR1", "FR2", "FR3"],
        priority="medium",
        confidence="medium",
    ),
]

# 2. CDR（，）
CDR_OPTIMIZATION_RULES = [
    OptimizationRule(
        rule_id="CDR_HYDROPHOBIC_OPTIMIZE",
        rule_name="CDR",
        description="CDR（AILMFWYV），",
        applicable_regions=["CDR1", "CDR2", "CDR3"],
        priority="medium",
        confidence="medium",
    ),
    OptimizationRule(
        rule_id="CDR_CHARGE_OPTIMIZE",
        rule_name="CDR",
        description="CDR（DERK），（D↔E, K↔R）",
        applicable_regions=["CDR1", "CDR2", "CDR3"],
        priority="medium",
        confidence="medium",
    ),
    OptimizationRule(
        rule_id="CDR_AROMATIC_OPTIMIZE",
        rule_name="CDR",
        description="CDR（FWY）π-π，（F↔Y, F↔W）",
        applicable_regions=["CDR1", "CDR2", "CDR3"],
        priority="medium",
        confidence="medium",
    ),
]

# 3. （IMGT）
POSITION_SPECIFIC_RULES = {
    # FR1
    26: {
        "importance": "high",
        "role": "CDR1",
        "restore_if_changed": True,
        "conservative_only": True,
    },
    # FR2
    37: {
        "importance": "high",
        "role": "VHH hallmark",
        "restore_if_changed": True,
        "conservative_only": False,
    },
    44: {
        "importance": "high",
        "role": "VHH hallmark",
        "restore_if_changed": True,
        "conservative_only": False,
    },
    45: {
        "importance": "high",
        "role": "VHH hallmark",
        "restore_if_changed": True,
        "conservative_only": False,
    },
    47: {
        "importance": "high",
        "role": "VHH hallmark",
        "restore_if_changed": True,
        "conservative_only": False,
    },
    55: {
        "importance": "high",
        "role": "CDR2",
        "restore_if_changed": True,
        "conservative_only": True,
    },
    # FR3
    104: {
        "importance": "medium",
        "role": "CDR3",
        "restore_if_changed": True,
        "conservative_only": True,
    },
    # Vernier zone
    27: {"importance": "medium", "role": "Vernier zone", "restore_if_changed": False},
    29: {"importance": "medium", "role": "Vernier zone", "restore_if_changed": False},
    30: {"importance": "medium", "role": "Vernier zone", "restore_if_changed": False},
    48: {"importance": "medium", "role": "Vernier zone", "restore_if_changed": False},
    49: {"importance": "medium", "role": "Vernier zone", "restore_if_changed": False},
    71: {"importance": "medium", "role": "Vernier zone", "restore_if_changed": False},
    73: {"importance": "medium", "role": "Vernier zone", "restore_if_changed": False},
    78: {"importance": "medium", "role": "Vernier zone", "restore_if_changed": False},
    94: {"importance": "medium", "role": "Vernier zone", "restore_if_changed": False},
}

# 4. （）
RESIDUE_SUBSTITUTION_RULES = {
    # （）
    'A': ['V', 'L', 'I', 'S', 'T'],
    'V': ['A', 'L', 'I'],
    'L': ['V', 'I', 'A', 'M'],
    'I': ['L', 'V', 'A'],
    'M': ['L', 'V'],
    'F': ['Y', 'W', 'L', 'V'],
    'W': ['F', 'Y'],
    'Y': ['F', 'W', 'H'],
    
    # （）
    'D': ['E', 'N', 'Q'],  #  → 
    'E': ['D', 'Q', 'N'],
    'K': ['R', 'Q', 'N'],  #  → 
    'R': ['K', 'Q'],
    'H': ['Y', 'N', 'Q'],
    
    # 
    'S': ['T', 'N', 'A'],
    'T': ['S', 'N', 'A'],
    'N': ['Q', 'S', 'T'],
    'Q': ['N', 'E', 'D'],
    
    # 
    'G': ['A', 'S'],  # ，
    'P': ['A', 'S'],  # ，
    'C': [],  # ，
}

# 5. 
REGION_SPECIFIC_RULES = {
    'FR1': {
        'conservative': True,  # FR1
        'max_mutations': 2,
        'priority': 'high',
    },
    'FR2': {
        'conservative': False,  # FR2VHH hallmark，case by case
        'max_mutations': 3,
        'priority': 'high',
    },
    'FR3': {
        'conservative': True,
        'max_mutations': 2,
        'priority': 'medium',
    },
    'CDR1': {
        'conservative': True,  # CDR1
        'max_mutations': 2,
        'priority': 'medium',
    },
    'CDR2': {
        'conservative': True,  # CDR2
        'max_mutations': 2,
        'priority': 'medium',
    },
    'CDR3': {
        'conservative': False,  # CDR3
        'max_mutations': 5,
        'priority': 'low',  # CDR3，
    },
}


def identify_optimization_sites(
    vhh_imgt_map: Dict[int, str],
    humanized_imgt_map: Dict[int, str],
    framework_identity: float,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    
    
    、，VHH
    
    Args:
        vhh_imgt_map: VHHIMGT
        humanized_imgt_map: IMGT
        framework_identity: 
    
    Returns:
        {
            'framework_restoration': [...],  # 
            'cdr_optimization': [...],       # CDR
            'vernier_zone': [...],           # Vernier zone
        }
    """
    framework_restoration = []
    cdr_optimization = []
    vernier_zone = []
    
    # 1. （）
    for pos, rule_info in POSITION_SPECIFIC_RULES.items():
        if pos not in vhh_imgt_map or pos not in humanized_imgt_map:
            continue
        
        vhh_aa = vhh_imgt_map[pos]
        human_aa = humanized_imgt_map[pos]
        
        if vhh_aa == human_aa:
            continue
        
        # 
        if 1 <= pos <= 26:
            region = 'FR1'
        elif 27 <= pos <= 38:
            region = 'CDR1'
        elif 39 <= pos <= 55:
            region = 'FR2'
        elif 56 <= pos <= 65:
            region = 'CDR2'
        elif 66 <= pos <= 104:
            region = 'FR3'
        elif 105 <= pos <= 117:
            region = 'CDR3'
        else:
            region = 'FR4'
        
        # 
        importance = _assess_residue_change_importance(vhh_aa, human_aa)
        
        suggestion = {
            'position': pos,
            'region': region,
            'from': human_aa,
            'to': vhh_aa,
            'rule_id': f"POS_{pos}_RESTORE",
            'rule_name': rule_info.get('role', ''),
            'importance': rule_info.get('importance', 'medium'),
            'rationale': f"{pos}（{rule_info.get('role', '')}）{human_aa}{vhh_aa}，",
            'priority': 'high' if rule_info.get('importance') == 'high' or importance == 'high' else 'medium',
        }
        
        # 
        if rule_info.get('restore_if_changed', False):
            framework_restoration.append(suggestion)
        elif rule_info.get('role') == 'Vernier zone':
            vernier_zone.append(suggestion)
    
    # 2. CDR（，）
    cdr_regions_imgt = {
        'CDR1': (27, 38),
        'CDR2': (56, 65),
        'CDR3': (105, 117),
    }
    
    for cdr_name, (start, end) in cdr_regions_imgt.items():
        for pos in range(start, end + 1):
            if pos not in humanized_imgt_map:
                continue
            
            aa = humanized_imgt_map[pos]
            
            # 
            if aa in 'AILMFWYV':  # 
                alternatives = RESIDUE_SUBSTITUTION_RULES.get(aa, [])
                if alternatives:
                    cdr_optimization.append({
                        'position': pos,
                        'region': cdr_name,
                        'from': aa,
                        'to_candidates': alternatives[:2],  # 2
                        'rule_id': 'CDR_HYDROPHOBIC_OPTIMIZE',
                        'rule_name': 'CDR',
                        'rationale': f'{pos}（{cdr_name}）{aa}，',
                        'priority': 'medium',
                    })
            elif aa in 'DERK':  # 
                alternatives = RESIDUE_SUBSTITUTION_RULES.get(aa, [])
                if alternatives:
                    cdr_optimization.append({
                        'position': pos,
                        'region': cdr_name,
                        'from': aa,
                        'to_candidates': alternatives[:2],
                        'rule_id': 'CDR_CHARGE_OPTIMIZE',
                        'rule_name': 'CDR',
                        'rationale': f'{pos}（{cdr_name}）{aa}，',
                        'priority': 'medium',
                    })
            elif aa in 'FWY':  # 
                alternatives = RESIDUE_SUBSTITUTION_RULES.get(aa, [])
                if alternatives:
                    cdr_optimization.append({
                        'position': pos,
                        'region': cdr_name,
                        'from': aa,
                        'to_candidates': alternatives[:2],
                        'rule_id': 'CDR_AROMATIC_OPTIMIZE',
                        'rule_name': 'CDR',
                        'rationale': f'{pos}（{cdr_name}）{aa}π-π，',
                        'priority': 'medium',
                    })
    
    return {
        'framework_restoration': framework_restoration,
        'cdr_optimization': cdr_optimization,
        'vernier_zone': vernier_zone,
    }


def _assess_residue_change_importance(aa1: str, aa2: str) -> str:
    """（）"""
    # 
    hydrophobic = set('AILMFWYV')
    hydrophilic = set('DERKQNST')
    charged_positive = set('KRH')
    charged_negative = set('DE')
    
    type1 = _get_residue_type(aa1)
    type2 = _get_residue_type(aa2)
    
    # ，
    if type1 != type2:
        return 'high'
    
    # ，
    if type1 == 'hydrophobic' and type2 == 'hydrophobic':
        size_diff = abs(_get_residue_size(aa1) - _get_residue_size(aa2))
        if size_diff > 2:
            return 'medium'
    
    return 'low'


def _get_residue_type(aa: str) -> str:
    """（）"""
    if aa in 'AILMFWYV':
        return 'hydrophobic'
    elif aa in 'DERKQNST':
        return 'hydrophilic'
    elif aa in 'G':
        return 'glycine'
    elif aa in 'P':
        return 'proline'
    else:
        return 'other'


def _get_residue_size(aa: str) -> int:
    """（）"""
    size_map = {
        'G': 1, 'A': 2, 'S': 3, 'T': 3,
        'C': 3, 'V': 4, 'I': 5, 'L': 5,
        'M': 5, 'P': 4, 'D': 4, 'E': 5,
        'N': 4, 'Q': 5, 'K': 6, 'R': 7,
        'H': 6, 'F': 7, 'Y': 8, 'W': 10,
    }
    return size_map.get(aa, 5)


def generate_systematic_mutation_suggestions(
    vhh_imgt_map: Dict[int, str],
    humanized_imgt_map: Dict[int, str],
    framework_identity: float,
) -> Dict[str, Any]:
    """
    
    
    、，VHH
    
    Args:
        vhh_imgt_map: VHHIMGT
        humanized_imgt_map: IMGT
        framework_identity: 
    
    Returns:
        {
            'systematic_suggestions': [...],  # 
            'rules_applied': [...],           # 
            'summary': {...},
        }
    """
    # 
    sites = identify_optimization_sites(vhh_imgt_map, humanized_imgt_map, framework_identity)
    
    # 
    mutations = []
    rules_applied = set()
    
    # 1. （）
    for site in sites['framework_restoration']:
        mutations.append({
            'position': site['position'],
            'from': site['from'],
            'to': site['to'],
            'region': site['region'],
            'rationale': site['rationale'],
            'priority': site['priority'],
            'rule_id': site['rule_id'],
            'rule_name': site['rule_name'],
            'expected_impact': 'positive',
        })
        rules_applied.add(site['rule_id'])
    
    # 2. Vernier zone
    for site in sites['vernier_zone']:
        # 
        if site['importance'] == 'high':
            mutations.append({
                'position': site['position'],
                'from': site['from'],
                'to': site['to'],
                'region': site['region'],
                'rationale': site['rationale'],
                'priority': 'medium',
                'rule_id': site['rule_id'],
                'rule_name': site['rule_name'],
                'expected_impact': 'positive',
            })
            rules_applied.add(site['rule_id'])
    
    # 3. CDR（）
    for site in sites['cdr_optimization']:
        # 
        for to_aa in site.get('to_candidates', [])[:1]:  # 
            mutations.append({
                'position': site['position'],
                'from': site['from'],
                'to': to_aa,
                'region': site['region'],
                'rationale': site['rationale'],
                'priority': site['priority'],
                'rule_id': site['rule_id'],
                'rule_name': site['rule_name'],
                'expected_impact': 'positive',
            })
            rules_applied.add(site['rule_id'])
    
    # 
    priority_order = {'high': 3, 'medium': 2, 'low': 1}
    mutations.sort(key=lambda m: priority_order.get(m.get('priority', 'low'), 0), reverse=True)
    
    return {
        'systematic_suggestions': mutations,
        'rules_applied': list(rules_applied),
        'summary': {
            'total_suggestions': len(mutations),
            'framework_restoration': len(sites['framework_restoration']),
            'cdr_optimization': len(sites['cdr_optimization']),
            'vernier_zone': len(sites['vernier_zone']),
            'high_priority': sum(1 for m in mutations if m.get('priority') == 'high'),
            'medium_priority': sum(1 for m in mutations if m.get('priority') == 'medium'),
        },
    }


















