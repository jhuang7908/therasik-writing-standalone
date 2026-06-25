"""
VHH：

，，
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import math

try:
    from core.affinity_optimization_rules import (
        generate_systematic_mutation_suggestions,
        identify_optimization_sites,
        RESIDUE_SUBSTITUTION_RULES,
        POSITION_SPECIFIC_RULES,
        REGION_SPECIFIC_RULES,
    )
    HAS_RULES_MODULE = True
except ImportError:
    HAS_RULES_MODULE = False


def suggest_affinity_improving_mutations(
    vhh_sequence: str,
    humanized_sequence: str,
    cdr_regions: Dict[str, str],
    framework_identity: float,
    cdr_canonical: Optional[Dict[str, Dict[str, Any]]] = None,
    vhh_imgt_map: Optional[Dict[int, str]] = None,
    humanized_imgt_map: Optional[Dict[int, str]] = None,
    use_systematic_rules: bool = True,
) -> Dict[str, Any]:
    """
    ，
    
    Args:
        vhh_sequence: VHH
        humanized_sequence: 
        cdr_regions: CDR {'CDR1': '...', 'CDR2': '...', 'CDR3': '...'}
        framework_identity: （0-1）
        cdr_canonical: CDR（）
    
    Returns:
        {
            'strategy': str,  # 'targeted'  'conservative'
            'mutations': [
                {
                    'position': int,  # 1-based
                    'from': str,      # 
                    'to': str,        # 
                    'region': str,     # 'CDR1', 'CDR2', 'CDR3', 'FR'
                    'rationale': str, # 
                    'priority': str,  # 'high', 'medium', 'low'
                    'expected_impact': str,  # 'positive', 'neutral', 'unknown'
                }
            ],
            'hotspots': [
                {
                    'position': int,
                    'region': str,
                    'residue': str,
                    'analysis': str,
                    'suggestions': List[str],
                }
            ],
            'framework_restoration': [
                # 
            ],
        }
    """
    mutations = []
    hotspots = []
    framework_restorations = []
    systematic_suggestions = []
    rules_applied = []
    
    # 1：（，）
    if use_systematic_rules and HAS_RULES_MODULE and vhh_imgt_map and humanized_imgt_map:
        try:
            systematic_result = generate_systematic_mutation_suggestions(
                vhh_imgt_map,
                humanized_imgt_map,
                framework_identity
            )
            systematic_suggestions = systematic_result['systematic_suggestions']
            rules_applied = systematic_result['rules_applied']
            mutations.extend(systematic_suggestions)
        except Exception as e:
            print(f"[WARN] : {e}")
    
    # 2：Case by case（）
    # 1. CDR
    cdr_hotspots = _identify_cdr_hotspots(
        cdr_regions, 
        vhh_sequence, 
        humanized_sequence,
        humanized_imgt_map
    )
    hotspots.extend(cdr_hotspots)
    
    # 2. CDR
    framework_impact = _analyze_framework_impact(
        vhh_sequence, 
        humanized_sequence, 
        cdr_regions,
        framework_identity
    )
    
    # 3. CDR（case by case）
    cdr_mutations = _suggest_cdr_mutations(
        cdr_regions,
        cdr_canonical,
        cdr_hotspots
    )
    
    # 4. （identity，systematic）
    if framework_identity < 0.85:
        framework_restorations = _suggest_framework_restorations(
            vhh_sequence,
            humanized_sequence,
            cdr_regions,
            vhh_imgt_map,
            humanized_imgt_map
        )
        # ：systematic，
        systematic_positions = {m['position'] for m in systematic_suggestions}
        framework_restorations = [
            m for m in framework_restorations 
            if m['position'] not in systematic_positions
        ]
        mutations.extend(framework_restorations)
    
    # 5. （case by case）
    charge_mutations = _suggest_charge_optimization(
        cdr_regions,
        humanized_sequence
    )
    mutations.extend(charge_mutations)
    
    # 6. 
    mutations = _prioritize_mutations(mutations, framework_identity)
    
    # 
    strategy = 'systematic' if use_systematic_rules and systematic_suggestions else 'targeted'
    
    return {
        'strategy': strategy,
        'mutations': mutations,
        'systematic_suggestions': systematic_suggestions,
        'case_specific_suggestions': cdr_mutations + charge_mutations,
        'hotspots': hotspots,
        'framework_restoration': framework_restorations,
        'rules_applied': rules_applied,
        'summary': {
            'total_mutations': len(mutations),
            'systematic_count': len(systematic_suggestions),
            'case_specific_count': len(cdr_mutations) + len(charge_mutations),
            'high_priority': sum(1 for m in mutations if m.get('priority') == 'high'),
            'medium_priority': sum(1 for m in mutations if m.get('priority') == 'medium'),
            'low_priority': sum(1 for m in mutations if m.get('priority') == 'low'),
        }
    }


def _identify_cdr_hotspots(
    cdr_regions: Dict[str, str],
    vhh_seq: str,
    humanized_seq: str,
    imgt_map: Optional[Dict[int, str]] = None,
) -> List[Dict[str, Any]]:
    """
    CDR（）
    
    ：，
    """
    hotspots = []
    
    # IMGT
    cdr_boundaries = {
        'CDR1': (27, 38),
        'CDR2': (56, 65),
        'CDR3': (105, 117),  # ，
    }
    
    for cdr_name, cdr_seq in cdr_regions.items():
        if not cdr_seq:
            continue
        
        start_pos, end_pos = cdr_boundaries.get(cdr_name, (0, 0))
        
        # 1. 
        for i, aa in enumerate(cdr_seq):
            # IMGT（）
            if imgt_map:
                # IMGT
                pos = None
                for img_pos in range(start_pos, end_pos + 1):
                    if img_pos in imgt_map and imgt_map[img_pos] == aa:
                        # CDRi
                        cdr_positions = [p for p in range(start_pos, end_pos + 1) if p in imgt_map]
                        if i < len(cdr_positions):
                            pos = cdr_positions[i]
                            break
            else:
                # 
                pos = start_pos + i if start_pos > 0 else None
            
            if not pos:
                continue
            
            # 2. （）
            if aa in 'AILMFWYV':
                hotspots.append({
                    'position': pos,
                    'region': cdr_name,
                    'residue': aa,
                    'analysis': '，',
                    'suggestions': _get_hydrophobic_alternatives(aa),
                })
            
            # 3. （）
            elif aa in 'DERK':
                hotspots.append({
                    'position': pos,
                    'region': cdr_name,
                    'residue': aa,
                    'analysis': '，',
                    'suggestions': _get_charge_alternatives(aa),
                })
            
            # 4. （π-π）
            elif aa in 'FWY':
                hotspots.append({
                    'position': pos,
                    'region': cdr_name,
                    'residue': aa,
                    'analysis': '，π-π',
                    'suggestions': _get_aromatic_alternatives(aa),
                })
    
    return hotspots


def _analyze_framework_impact(
    vhh_seq: str,
    humanized_seq: str,
    cdr_regions: Dict[str, str],
    framework_identity: float
) -> Dict[str, Any]:
    """
    CDR
    """
    # CDR
    key_positions = [26, 55, 104]  # FR1-26, FR2-55, FR3-104
    
    impacts = []
    for pos in key_positions:
        if pos <= len(vhh_seq) and pos <= len(humanized_seq):
            vhh_aa = vhh_seq[pos - 1]  # 0-based
            human_aa = humanized_seq[pos - 1]
            if vhh_aa != human_aa:
                impacts.append({
                    'position': pos,
                    'vhh_aa': vhh_aa,
                    'human_aa': human_aa,
                    'impact': 'CDR',
                })
    
    return {
        'framework_identity': framework_identity,
        'key_position_changes': impacts,
        'risk_level': 'high' if len(impacts) >= 2 else 'medium' if len(impacts) >= 1 else 'low',
    }


def _suggest_cdr_mutations(
    cdr_regions: Dict[str, str],
    cdr_canonical: Optional[Dict[str, Dict[str, Any]]],
    hotspots: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    CDR
    """
    mutations = []
    
    # 
    for hotspot in hotspots:
        if hotspot['region'] in ['CDR1', 'CDR2']:
            # CDR1CDR2
            suggestions = hotspot['suggestions'][:2]  # 2
        else:
            # CDR3
            suggestions = hotspot['suggestions'][:3]
        
        for to_aa in suggestions:
            if to_aa != hotspot['residue']:
                mutations.append({
                    'position': hotspot['position'],
                    'from': hotspot['residue'],
                    'to': to_aa,
                    'region': hotspot['region'],
                    'rationale': f"{hotspot['analysis']}；{hotspot['residue']}→{to_aa}",
                    'priority': 'medium',
                    'expected_impact': 'positive',
                })
    
    return mutations


def _suggest_framework_restorations(
    vhh_seq: str,
    humanized_seq: str,
    cdr_regions: Dict[str, str],
    vhh_imgt_map: Optional[Dict[int, str]] = None,
    humanized_imgt_map: Optional[Dict[int, str]] = None,
) -> List[Dict[str, Any]]:
    """
    
    
    -CDR，CDR
    """
    mutations = []
    
    # ：FR1-26, FR2-55, FR3-104
    # CDR
    key_positions = {
        26: {'region': 'FR1', 'name': 'FR1-26 (CDR1)', 'impact': 'high'},
        55: {'region': 'FR2', 'name': 'FR2-55 (CDR2)', 'impact': 'high'},
        104: {'region': 'FR3', 'name': 'FR3-104 (CDR3)', 'impact': 'medium'},
    }
    
    # （）
    # Vernier zone：27, 29, 30, 48, 49, 71, 73, 78, 94
    vernier_positions = {27, 29, 30, 48, 49, 71, 73, 78, 94}
    
    for pos, info in key_positions.items():
        # IMGT（）
        if vhh_imgt_map and humanized_imgt_map:
            vhh_aa = vhh_imgt_map.get(pos, '')
            human_aa = humanized_imgt_map.get(pos, '')
        else:
            # （）
            if pos <= len(vhh_seq) and pos <= len(humanized_seq):
                vhh_aa = vhh_seq[pos - 1]
                human_aa = humanized_seq[pos - 1]
            else:
                continue
        
        if vhh_aa and human_aa and vhh_aa != human_aa:
            # 
            importance = _assess_residue_change_importance(vhh_aa, human_aa)
            
            mutations.append({
                'position': pos,
                'from': human_aa,
                'to': vhh_aa,
                'region': info['region'],
                'rationale': f"{info['name']}({vhh_aa})，CDR。：{_get_residue_type(vhh_aa)}，：{_get_residue_type(human_aa)}",
                'priority': 'high' if info['impact'] == 'high' or importance == 'high' else 'medium',
                'expected_impact': 'positive',
            })
    
    # Vernier zone（identity）
    if len(vhh_seq) == len(humanized_seq):
        for pos in vernier_positions:
            if pos <= len(vhh_seq):
                vhh_aa = vhh_seq[pos - 1]
                human_aa = humanized_seq[pos - 1]
                
                if vhh_aa != human_aa:
                    # Vernier zoneCDR，
                    importance = _assess_residue_change_importance(vhh_aa, human_aa)
                    if importance == 'high':
                        # 
                        if pos <= 26:
                            region = 'FR1'
                        elif pos <= 55:
                            region = 'FR2'
                        else:
                            region = 'FR3'
                        
                        mutations.append({
                            'position': pos,
                            'from': human_aa,
                            'to': vhh_aa,
                            'region': region,
                            'rationale': f"Vernier zone{pos}({vhh_aa})，CDR",
                            'priority': 'medium',
                            'expected_impact': 'positive',
                        })
    
    return mutations


def _assess_residue_change_importance(aa1: str, aa2: str) -> str:
    """"""
    # 
    hydrophobic = set('AILMFWYV')
    hydrophilic = set('DERKQNST')
    charged_positive = set('KRH')
    charged_negative = set('DE')
    aromatic = set('FWY')
    
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
    """"""
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


def _suggest_charge_optimization(
    cdr_regions: Dict[str, str],
    humanized_seq: str
) -> List[Dict[str, Any]]:
    """
    
    """
    mutations = []
    
    # CDR
    for cdr_name, cdr_seq in cdr_regions.items():
        if not cdr_seq:
            continue
        
        positive_count = sum(1 for aa in cdr_seq if aa in 'KRH')
        negative_count = sum(1 for aa in cdr_seq if aa in 'DE')
        
        # ，
        if abs(positive_count - negative_count) > 2:
            # 
            for i, aa in enumerate(cdr_seq):
                pos = _get_cdr_position_in_full_sequence(cdr_name, i, humanized_seq)
                if not pos:
                    continue
                
                if positive_count > negative_count and aa in 'KRH':
                    # ，
                    alternatives = ['Q', 'N', 'S', 'T']
                    for alt in alternatives:
                        mutations.append({
                            'position': pos,
                            'from': aa,
                            'to': alt,
                            'region': cdr_name,
                            'rationale': f"，",
                            'priority': 'low',
                            'expected_impact': 'neutral',
                        })
                        break  # 
    
    return mutations


def _prioritize_mutations(
    mutations: List[Dict[str, Any]],
    framework_identity: float
) -> List[Dict[str, Any]]:
    """
    
    """
    # ：
    # 1.  > CDR
    # 2. （26, 55, 104）> 
    # 3. CDR1/CDR2 > CDR3（）
    
    def get_priority_score(mut):
        score = 0
        
        # 
        if '' in mut.get('rationale', ''):
            score += 100
        
        # 
        if mut.get('position') in [26, 55, 104]:
            score += 50
        
        # CDR1/CDR2CDR3
        if mut.get('region') in ['CDR1', 'CDR2']:
            score += 20
        elif mut.get('region') == 'CDR3':
            score += 10
        
        # 
        priority_map = {'high': 30, 'medium': 20, 'low': 10}
        score += priority_map.get(mut.get('priority', 'low'), 0)
        
        return score
    
    # （）
    mutations_by_pos = {}
    for mut in mutations:
        pos = mut['position']
        if pos not in mutations_by_pos:
            mutations_by_pos[pos] = mut
        else:
            # 
            if get_priority_score(mut) > get_priority_score(mutations_by_pos[pos]):
                mutations_by_pos[pos] = mut
    
    # 
    sorted_mutations = sorted(
        mutations_by_pos.values(),
        key=get_priority_score,
        reverse=True
    )
    
    return sorted_mutations


def _get_cdr_position_in_full_sequence(
    cdr_name: str,
    cdr_index: int,
    full_sequence: str
) -> Optional[int]:
    """
    CDR（1-based）
    
    ：IMGT，
    IMGT
    """
    # IMGT（）
    cdr_starts = {
        'CDR1': 27,  # IMGT position 27
        'CDR2': 56,  # IMGT position 56
        'CDR3': 105, # IMGT position 105
    }
    
    if cdr_name not in cdr_starts:
        return None
    
    # ：IMGT
    # IMGT
    start_pos = cdr_starts[cdr_name]
    pos = start_pos + cdr_index
    
    # 
    if 1 <= pos <= len(full_sequence):
        return pos
    
    return None


def _get_hydrophobic_alternatives(aa: str) -> List[str]:
    """"""
    alternatives = {
        'A': ['V', 'L', 'I'],
        'V': ['A', 'L', 'I'],
        'L': ['V', 'I', 'A'],
        'I': ['L', 'V', 'A'],
        'M': ['L', 'V'],
        'F': ['Y', 'W', 'L'],
        'W': ['F', 'Y'],
        'Y': ['F', 'W'],
    }
    return alternatives.get(aa, [])


def _get_charge_alternatives(aa: str) -> List[str]:
    """"""
    alternatives = {
        'D': ['E', 'N', 'Q'],
        'E': ['D', 'Q', 'N'],
        'K': ['R', 'Q', 'N'],
        'R': ['K', 'Q', 'N'],
    }
    return alternatives.get(aa, [])


def _get_aromatic_alternatives(aa: str) -> List[str]:
    """"""
    alternatives = {
        'F': ['Y', 'W', 'L'],
        'Y': ['F', 'W', 'H'],
        'W': ['F', 'Y'],
    }
    return alternatives.get(aa, [])


def generate_yeast_display_mutation_library(
    base_sequence: str,
    mutation_suggestions: Dict[str, Any],
    max_mutations: int = 5,
    strategy: str = 'targeted',
    max_variants: int = 20
) -> Dict[str, Any]:
    """
    
    
    ：，
    
    Args:
        base_sequence: （）
        mutation_suggestions: 
        max_mutations: 
        strategy: 'targeted'（） 'combinatorial'（）
        max_variants: 
    
    Returns:
        {
            'library_size': int,
            'variants': [
                {
                    'variant_id': str,
                    'sequence': str,
                    'mutations': List[Dict],
                    'priority': str,
                    'rationale': str,
                }
            ],
            'design_rationale': str,
        }
    """
    mutations = mutation_suggestions.get('mutations', [])
    variants = []
    
    if strategy == 'targeted':
        # ：
        
        # 1. （）
        framework_muts = [m for m in mutations if '' in m.get('rationale', '')]
        if framework_muts:
            # 
            for mut in framework_muts[:3]:  # 3
                seq = list(base_sequence)
                if 1 <= mut['position'] <= len(seq):
                    seq[mut['position'] - 1] = mut['to']
                    variants.append({
                        'variant_id': f"framework_{mut['position']}_{mut['from']}to{mut['to']}",
                        'sequence': ''.join(seq),
                        'mutations': [mut],
                        'priority': 'high',
                        'rationale': f"：{mut['rationale']}",
                    })
            
            # 
            if len(framework_muts) <= max_mutations:
                seq = list(base_sequence)
                framework_list = []
                for mut in framework_muts:
                    if 1 <= mut['position'] <= len(seq):
                        seq[mut['position'] - 1] = mut['to']
                        framework_list.append(mut)
                if framework_list:
                    variants.append({
                        'variant_id': f"framework_restore_all_{len(framework_list)}muts",
                        'sequence': ''.join(seq),
                        'mutations': framework_list,
                        'priority': 'high',
                        'rationale': f"（{len(framework_list)}）",
                    })
        
        # 2. CDR（）
        cdr_mutations = {
            'CDR1': [m for m in mutations if m.get('region') == 'CDR1' and '' not in m.get('rationale', '')],
            'CDR2': [m for m in mutations if m.get('region') == 'CDR2' and '' not in m.get('rationale', '')],
            'CDR3': [m for m in mutations if m.get('region') == 'CDR3' and '' not in m.get('rationale', '')],
        }
        
        # 2.1 CDR1（）
        for mut in cdr_mutations['CDR1'][:3]:  # 3
            seq = list(base_sequence)
            if 1 <= mut['position'] <= len(seq):
                seq[mut['position'] - 1] = mut['to']
                variants.append({
                    'variant_id': f"cdr1_{mut['position']}_{mut['from']}to{mut['to']}",
                    'sequence': ''.join(seq),
                    'mutations': [mut],
                    'priority': 'medium',
                    'rationale': f"CDR1：{mut['rationale']}",
                })
        
        # 2.2 CDR2（）
        for mut in cdr_mutations['CDR2'][:3]:  # 3
            seq = list(base_sequence)
            if 1 <= mut['position'] <= len(seq):
                seq[mut['position'] - 1] = mut['to']
                variants.append({
                    'variant_id': f"cdr2_{mut['position']}_{mut['from']}to{mut['to']}",
                    'sequence': ''.join(seq),
                    'mutations': [mut],
                    'priority': 'medium',
                    'rationale': f"CDR2：{mut['rationale']}",
                })
        
        # 2.3 CDR3（）
        for mut in cdr_mutations['CDR3'][:5]:  # 5
            seq = list(base_sequence)
            if 1 <= mut['position'] <= len(seq):
                seq[mut['position'] - 1] = mut['to']
                variants.append({
                    'variant_id': f"cdr3_{mut['position']}_{mut['from']}to{mut['to']}",
                    'sequence': ''.join(seq),
                    'mutations': [mut],
                    'priority': 'medium',
                    'rationale': f"CDR3：{mut['rationale']}",
                })
        
        # 3. （CDR）
        # CDR1（2）
        if len(cdr_mutations['CDR1']) >= 2:
            combo = cdr_mutations['CDR1'][:2]
            seq = list(base_sequence)
            combo_list = []
            for mut in combo:
                if 1 <= mut['position'] <= len(seq):
                    seq[mut['position'] - 1] = mut['to']
                    combo_list.append(mut)
            if combo_list:
                variants.append({
                    'variant_id': f"cdr1_combo_{len(combo_list)}muts",
                    'sequence': ''.join(seq),
                    'mutations': combo_list,
                    'priority': 'medium',
                    'rationale': f"CDR1（{len(combo_list)}）",
                })
        
        # CDR2（2）
        if len(cdr_mutations['CDR2']) >= 2:
            combo = cdr_mutations['CDR2'][:2]
            seq = list(base_sequence)
            combo_list = []
            for mut in combo:
                if 1 <= mut['position'] <= len(seq):
                    seq[mut['position'] - 1] = mut['to']
                    combo_list.append(mut)
            if combo_list:
                variants.append({
                    'variant_id': f"cdr2_combo_{len(combo_list)}muts",
                    'sequence': ''.join(seq),
                    'mutations': combo_list,
                    'priority': 'medium',
                    'rationale': f"CDR2（{len(combo_list)}）",
                })
        
        # 4. （ + CDR）
        if framework_muts and (cdr_mutations['CDR1'] or cdr_mutations['CDR2']):
            #  + 1CDR
            framework_mut = framework_muts[0]
            cdr_mut = (cdr_mutations['CDR1'] + cdr_mutations['CDR2'])[0] if (cdr_mutations['CDR1'] + cdr_mutations['CDR2']) else None
            
            if cdr_mut:
                seq = list(base_sequence)
                combo_list = []
                for mut in [framework_mut, cdr_mut]:
                    if 1 <= mut['position'] <= len(seq):
                        seq[mut['position'] - 1] = mut['to']
                        combo_list.append(mut)
                if len(combo_list) == 2:
                    variants.append({
                        'variant_id': f"framework_cdr_combo_2muts",
                        'sequence': ''.join(seq),
                        'mutations': combo_list,
                        'priority': 'high',
                        'rationale': f" + CDR",
                    })
    
    else:  # combinatorial
        # ：（）
        variants = []
        # ...
        pass
    
    # 
    variants = variants[:max_variants]
    
    return {
        'library_size': len(variants),
        'variants': variants,
        'design_rationale': f"，{len(variants)}。：，。",
        'strategy': strategy,
    }

