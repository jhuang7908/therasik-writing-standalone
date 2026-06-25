"""
CDR（Canonical Structure）

CDRCDRcanonical structure

"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# CDR（Chothia/IMGT）
# 

CDR_CANONICAL_RULES = {
    "CDR1": {
        # CDR1（）
        "length_ranges": {
            (8, 10): "canonical_1",   # 
            (11, 12): "canonical_2",
            (13, 15): "canonical_3",
            (6, 7): "non_canonical",  # 
            (16, 20): "non_canonical",  # 
        },
        # （IMGT，CDR1）
        "key_positions": {
            # 26（FR1）27（CDR1）
            # CDR1
        }
    },
    "CDR2": {
        "length_ranges": {
            (7, 9): "canonical_1",   # 
            (10, 12): "canonical_2",
            (13, 15): "canonical_3",
            (5, 6): "non_canonical",
            (16, 20): "non_canonical",
        },
        "key_positions": {
            # 55（FR2）56（CDR2）
        }
    },
    "CDR3": {
        "length_ranges": {
            (3, 7): "short",          # CDR3
            (8, 12): "canonical_1",  # 
            (13, 18): "canonical_2", # 
            (19, 25): "long",        # CDR3
            (26, 35): "very_long",   # CDR3（VHH）
        },
        "key_positions": {
            # CDR3
            # 104（FR3）CDR3
        }
    }
}

# VHHCDR3
VHH_CDR3_FEATURES = {
    "typical_length": (10, 25),  # VHHCDR3
    "cys_pair": "C...C",  # 
    "hydrophobic_patch": True,  # 
}


def get_key_position_residues(pos_map: Dict[int, str]) -> Dict[str, str]:
    """
    CDR
    
    Args:
        pos_map: IMGT
    
    Returns:
        {
            'fr1_26': str,  # FR126（CDR1）
            'cdr1_start': str,  # CDR127
            'fr2_55': str,  # FR255（CDR2）
            'cdr2_start': str,  # CDR256
            'fr3_104': str,  # FR3104（CDR3）
        }
    """
    return {
        'fr1_26': pos_map.get(26, '-'),
        'cdr1_start': pos_map.get(27, '-'),
        'fr2_55': pos_map.get(55, '-'),
        'cdr2_start': pos_map.get(56, '-'),
        'fr3_104': pos_map.get(104, '-'),
    }


def classify_cdr_canonical(cdr_seq: str, cdr_type: str, fr_context: Optional[Dict[str, str]] = None, key_positions: Optional[Dict[str, str]] = None) -> Dict[str, any]:
    """
    CDRcanonical structure
    
    Args:
        cdr_seq: CDR
        cdr_type: CDR（'CDR1', 'CDR2', 'CDR3'）
        fr_context: （，）
    
    Returns:
        {
            'canonical_class': str,      # 
            'length': int,               # CDR
            'confidence': float,          # 
            'features': dict,            # 
        }
    """
    if cdr_type not in CDR_CANONICAL_RULES:
        return {
            'canonical_class': 'unknown',
            'length': len(cdr_seq),
            'confidence': 0.0,
            'features': {}
        }
    
    length = len(cdr_seq)
    rules = CDR_CANONICAL_RULES[cdr_type]
    
    # 
    canonical_class = 'non_canonical'
    confidence = 0.5
    
    for (min_len, max_len), class_name in rules['length_ranges'].items():
        if min_len <= length <= max_len:
            canonical_class = class_name
            # ，
            center = (min_len + max_len) / 2
            confidence = 1.0 - abs(length - center) / (max_len - min_len + 1)
            break
    
    features = {
        'length': length,
        'has_cys': 'C' in cdr_seq,
        'cys_count': cdr_seq.count('C'),
        'hydrophobic_aa': sum(1 for aa in cdr_seq if aa in 'AILMFWYV'),
        'hydrophilic_aa': sum(1 for aa in cdr_seq if aa in 'DERKQNST'),
    }
    
    # VHH（CDR3）
    if cdr_type == 'CDR3':
        if length >= 19:
            features['is_long_cdr3'] = True
            features['vhh_like'] = True
        else:
            features['is_long_cdr3'] = False
            features['vhh_like'] = False
        
        # 
        if 'C' in cdr_seq:
            cys_positions = [i for i, aa in enumerate(cdr_seq) if aa == 'C']
            if len(cys_positions) >= 2:
                # C...C（3-5）
                for i in range(len(cys_positions) - 1):
                    gap = cys_positions[i+1] - cys_positions[i] - 1
                    if 3 <= gap <= 5:
                        features['non_canonical_disulfide'] = True
                        break
    
    # （）
    if key_positions:
        if cdr_type == "CDR1":
            features['key_fr1_26'] = key_positions.get('fr1_26', '-')
            features['key_cdr1_start'] = key_positions.get('cdr1_start', '-')
        elif cdr_type == "CDR2":
            features['key_fr2_55'] = key_positions.get('fr2_55', '-')
            features['key_cdr2_start'] = key_positions.get('cdr2_start', '-')
        elif cdr_type == "CDR3":
            features['key_fr3_104'] = key_positions.get('fr3_104', '-')
    
    return {
        'canonical_class': canonical_class,
        'length': length,
        'confidence': min(1.0, max(0.0, confidence)),
        'features': features,
        'key_positions': key_positions or {}
    }


def classify_all_cdrs(cdr_dict: Dict[str, str], fr_context: Optional[Dict[str, str]] = None, key_positions: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, any]]:
    """
    CDR
    
    Args:
        cdr_dict: {'CDR1': '...', 'CDR2': '...', 'CDR3': '...'}
        fr_context: （）
        key_positions: （）
    
    Returns:
        {
            'CDR1': {...},
            'CDR2': {...},
            'CDR3': {...},
        }
    """
    results = {}
    for cdr_type, cdr_seq in cdr_dict.items():
        if cdr_seq:
            results[cdr_type] = classify_cdr_canonical(cdr_seq, cdr_type, fr_context, key_positions)
        else:
            results[cdr_type] = {
                'canonical_class': 'empty',
                'length': 0,
                'confidence': 0.0,
                'features': {},
                'key_positions': {}
            }
    return results


def check_key_position_compatibility(
    vhh_key_positions: Dict[str, str],
    human_template_key_positions: Dict[str, str]
) -> Dict[str, any]:
    """
    
    
    Args:
        vhh_key_positions: VHH
        human_template_key_positions: Human
    
    Returns:
        {
            'key_position_score': float,  # 0-1
            'matches': Dict[str, bool],
            'warnings': List[str],
        }
    """
    matches = {}
    warnings = []
    score = 1.0
    
    # FR126（CDR1）
    if 'fr1_26' in vhh_key_positions and 'fr1_26' in human_template_key_positions:
        vhh_aa = vhh_key_positions['fr1_26']
        human_aa = human_template_key_positions['fr1_26']
        matches['fr1_26'] = (vhh_aa == human_aa)
        if vhh_aa != human_aa and vhh_aa != '-' and human_aa != '-':
            # 
            score *= 0.95
    
    # FR255（CDR2）
    if 'fr2_55' in vhh_key_positions and 'fr2_55' in human_template_key_positions:
        vhh_aa = vhh_key_positions['fr2_55']
        human_aa = human_template_key_positions['fr2_55']
        matches['fr2_55'] = (vhh_aa == human_aa)
        if vhh_aa != human_aa and vhh_aa != '-' and human_aa != '-':
            score *= 0.95
    
    # FR3104（CDR3）
    if 'fr3_104' in vhh_key_positions and 'fr3_104' in human_template_key_positions:
        vhh_aa = vhh_key_positions['fr3_104']
        human_aa = human_template_key_positions['fr3_104']
        matches['fr3_104'] = (vhh_aa == human_aa)
        if vhh_aa != human_aa and vhh_aa != '-' and human_aa != '-':
            score *= 0.95
    
    return {
        'key_position_score': score,
        'matches': matches,
        'warnings': warnings
    }


def match_canonical_compatibility(
    vhh_cdrs: Dict[str, Dict[str, any]],
    human_template_cdrs: Optional[Dict[str, str]] = None,
    human_template_key_positions: Optional[Dict[str, str]] = None
) -> Dict[str, any]:
    """
    CDR（，）
    
    Args:
        vhh_cdrs: VHHCDR
        human_template_cdrs: HumanCDR（）
        human_template_key_positions: Human（）
    
    Returns:
        {
            'compatibility_score': float,  # 0-1，
            'cdr1_match': bool,
            'cdr2_match': bool,
            'cdr3_match': bool,
            'key_position_score': float,  # 
            'warnings': List[str],
        }
    """
    compatibility = {
        'compatibility_score': 1.0,
        'cdr1_match': True,
        'cdr2_match': True,
        'cdr3_match': True,
        'key_position_score': 1.0,
        'warnings': []
    }
    
    # CDR1CDR2，，CDR
    # CDR3
    
    if 'CDR3' in vhh_cdrs:
        cdr3_info = vhh_cdrs['CDR3']
        length = cdr3_info['length']
        
        # VHHCDR3，
        if length > 25:
            compatibility['warnings'].append(
                f"CDR3({length}aa)，"
            )
            compatibility['compatibility_score'] *= 0.9
        
        if length < 5:
            compatibility['warnings'].append(
                f"CDR3({length}aa)，VHH"
            )
            compatibility['compatibility_score'] *= 0.95
    
    # CDR1CDR2
    for cdr_type in ['CDR1', 'CDR2']:
        if cdr_type in vhh_cdrs:
            length = vhh_cdrs[cdr_type]['length']
            canonical_class = vhh_cdrs[cdr_type]['canonical_class']
            
            if canonical_class == 'non_canonical':
                compatibility['warnings'].append(
                    f"{cdr_type}（{length}aa）"
                )
                compatibility['compatibility_score'] *= 0.95
    
    # 
    if human_template_key_positions:
        vhh_key_positions = {}
        for cdr_type, cdr_info in vhh_cdrs.items():
            if 'key_positions' in cdr_info:
                vhh_key_positions.update(cdr_info['key_positions'])
        
        key_compat = check_key_position_compatibility(vhh_key_positions, human_template_key_positions)
        compatibility['key_position_score'] = key_compat['key_position_score']
        compatibility['key_position_matches'] = key_compat['matches']
        
        # 
        compatibility['compatibility_score'] *= key_compat['key_position_score']
    
    return compatibility

