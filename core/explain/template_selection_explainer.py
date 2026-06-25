"""
Template Selection Explainer
：
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys

# 
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def load_policy(policy_path: Optional[Path] = None) -> Dict[str, Any]:
    """"""
    if policy_path is None:
        policy_path = PROJECT_ROOT / "core" / "policy" / "template_selection_policy.yaml"
    
    if not policy_path.exists():
        raise FileNotFoundError(f": {policy_path}")
    
    with open(policy_path, 'r', encoding='utf-8') as f:
        policy = yaml.safe_load(f)
    
    return policy.get("template_selection_policy", {})


def explain_template_selection(
    best_template: Dict[str, Any],
    all_template_scores: List[Dict[str, Any]],
    chain_type: str,
    policy_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    
    
    Args:
        best_template: 
        all_template_scores: 
        chain_type:  ("VH", "VL", "VHH")
        policy_path: （）
    
    Returns:
        selection_explanation 
    """
    policy = load_policy(policy_path)
    
    # （VH/VL/VHH）
    policy_key = chain_type.upper()
    if policy_key not in policy:
        # VH
        policy_key = "VH"
    
    policy_rules = policy[policy_key]
    priority = policy_rules.get("priority", [])
    tolerances = policy_rules.get("tolerances", {})
    
    key_reasons = []
    caution_notes = []
    
    # 
    fr_identity = best_template.get("fr_identity", {})
    cdr_length_match = best_template.get("cdr_length_match", {})
    hallmark_score = best_template.get("vhh_hallmark_score")
    fr_mutations = best_template.get("fr_mutations", 0)
    
    # 
    for criterion in priority:
        if criterion == "cdr_length_match":
            # CDR
            cdr1_match = cdr_length_match.get("CDR1", {}).get("match", False)
            cdr2_match = cdr_length_match.get("CDR2", {}).get("match", False)
            cdr3_match = cdr_length_match.get("CDR3", {}).get("match", False)
            
            cdr1_target = cdr_length_match.get("CDR1", {}).get("target_length", 0)
            cdr1_template = cdr_length_match.get("CDR1", {}).get("template_length", 0)
            cdr2_target = cdr_length_match.get("CDR2", {}).get("target_length", 0)
            cdr2_template = cdr_length_match.get("CDR2", {}).get("template_length", 0)
            cdr3_target = cdr_length_match.get("CDR3", {}).get("target_length", 0)
            cdr3_template = cdr_length_match.get("CDR3", {}).get("template_length", 0)
            
            if cdr1_match and cdr2_match:
                key_reasons.append("Exact match in CDR1 and CDR2 lengths")
            elif cdr1_match:
                key_reasons.append("Exact match in CDR1 length")
            elif cdr2_match:
                key_reasons.append("Exact match in CDR2 length")
            
            # CDR3
            cdr3_delta = abs(cdr3_target - cdr3_template)
            cdr3_tolerance = tolerances.get("cdr3_length_delta", 3)
            
            if cdr3_match:
                key_reasons.append("Exact match in CDR3 length")
            elif cdr3_delta <= cdr3_tolerance:
                if cdr3_template < cdr3_target:
                    key_reasons.append(f"Minor CDR3 length mismatch (Δ={cdr3_delta} aa), within acceptable range for {chain_type.lower()} chains")
                    caution_notes.append("CDR3 length shorter than query sequence. Consider experimental validation to assess impact on binding affinity.")
                else:
                    key_reasons.append(f"Minor CDR3 length mismatch (Δ={cdr3_delta} aa), within acceptable range for {chain_type.lower()} chains")
                    caution_notes.append("CDR3 length longer than query sequence. Consider experimental validation to assess impact on binding affinity.")
            else:
                caution_notes.append(f"CDR3 length mismatch (Δ={cdr3_delta} aa) exceeds tolerance ({cdr3_tolerance} aa). Experimental validation recommended to assess loop conformation and binding affinity.")
        
        elif criterion == "fr_identity":
            # FR identity
            if fr_identity:
                fr1_id = fr_identity.get("FR1", 0.0)
                fr2_id = fr_identity.get("FR2", 0.0)
                fr3_id = fr_identity.get("FR3", 0.0)
                fr4_id = fr_identity.get("FR4", 0.0)
                
                avg_identity = sum([fr1_id, fr2_id, fr3_id, fr4_id]) / len([f for f in [fr1_id, fr2_id, fr3_id, fr4_id] if f > 0])
                fr_identity_min = tolerances.get("fr_identity_min", 0.75)
                
                if avg_identity >= 0.95:
                    key_reasons.append(f"Very high framework identity (average {avg_identity:.1%})")
                elif avg_identity >= fr_identity_min:
                    key_reasons.append(f"High framework identity (average {avg_identity:.1%})")
                
                # FR
                if fr2_id >= 0.94 and fr3_id >= 0.94:
                    key_reasons.append("High framework identity (FR2/FR3 > 94%)")
                elif fr3_id >= 0.95:
                    key_reasons.append("Very high FR3 identity (> 95%)")
        
        elif criterion == "hallmark_score":
            # VHH hallmark
            if hallmark_score is not None:
                hallmark_min = tolerances.get("hallmark_min", 0.6)
                if hallmark_score >= 0.9:
                    key_reasons.append(f"Excellent VHH hallmark score ({hallmark_score:.2f})")
                elif hallmark_score >= hallmark_min:
                    key_reasons.append(f"Good VHH hallmark score ({hallmark_score:.2f})")
                else:
                    caution_notes.append(f"VHH hallmark score ({hallmark_score:.2f}) below recommended threshold ({hallmark_min}). Consider second-round optimization to enhance VHH characteristics.")
        
        elif criterion == "canonical_class":
            # Canonical class（）
            # ，canonical_class
            pass
        
        elif criterion == "cdr1_cdr2_match":
            # CDR1CDR2
            cdr1_match = cdr_length_match.get("CDR1", {}).get("match", False)
            cdr2_match = cdr_length_match.get("CDR2", {}).get("match", False)
            if cdr1_match and cdr2_match:
                key_reasons.append("Exact match in CDR1 and CDR2 lengths")
        
        elif criterion == "cdr3_length":
            # CDR3
            cdr3_target = cdr_length_match.get("CDR3", {}).get("target_length", 0)
            cdr3_template = cdr_length_match.get("CDR3", {}).get("template_length", 0)
            cdr3_delta = abs(cdr3_target - cdr3_template)
            cdr3_tolerance = tolerances.get("cdr3_length_delta", 3)
            
            if cdr3_delta == 0:
                key_reasons.append("Exact CDR3 length match")
            elif cdr3_delta <= cdr3_tolerance:
                key_reasons.append(f"CDR3 length within acceptable range (Δ={cdr3_delta} aa)")
    
    # FR
    if fr_mutations == 0:
        key_reasons.append("No framework mutations required")
    elif fr_mutations <= 3:
        key_reasons.append(f"Minimal framework mutations ({fr_mutations} positions)")
    elif fr_mutations <= 10:
        key_reasons.append(f"Moderate framework mutations ({fr_mutations} positions)")
    else:
        caution_notes.append(f"Significant number of framework mutations ({fr_mutations} positions) may affect stability")
    
    # 
    explanation = {
        "chain_type": chain_type,
        "policy_used": policy_key,
        "key_reasons": key_reasons,
        "caution_notes": caution_notes if caution_notes else []
    }
    
    return explanation


def explain_template_selection_zh(
    best_template: Dict[str, Any],
    all_template_scores: List[Dict[str, Any]],
    chain_type: str,
    policy_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    （）
    """
    policy = load_policy(policy_path)
    
    # 
    policy_key = chain_type.upper()
    if policy_key not in policy:
        policy_key = "VH"
    
    policy_rules = policy[policy_key]
    priority = policy_rules.get("priority", [])
    tolerances = policy_rules.get("tolerances", {})
    
    key_reasons = []
    caution_notes = []
    
    # 
    fr_identity = best_template.get("fr_identity", {})
    cdr_length_match = best_template.get("cdr_length_match", {})
    hallmark_score = best_template.get("vhh_hallmark_score")
    fr_mutations = best_template.get("fr_mutations", 0)
    
    # （）
    for criterion in priority:
        if criterion == "cdr_length_match":
            cdr1_match = cdr_length_match.get("CDR1", {}).get("match", False)
            cdr2_match = cdr_length_match.get("CDR2", {}).get("match", False)
            cdr3_match = cdr_length_match.get("CDR3", {}).get("match", False)
            
            cdr3_target = cdr_length_match.get("CDR3", {}).get("target_length", 0)
            cdr3_template = cdr_length_match.get("CDR3", {}).get("template_length", 0)
            cdr3_delta = abs(cdr3_target - cdr3_template)
            cdr3_tolerance = tolerances.get("cdr3_length_delta", 3)
            
            if cdr1_match and cdr2_match:
                key_reasons.append("CDR1CDR2")
            elif cdr1_match:
                key_reasons.append("CDR1")
            elif cdr2_match:
                key_reasons.append("CDR2")
            
            if cdr3_match:
                key_reasons.append("CDR3")
            elif cdr3_delta <= cdr3_tolerance:
                chain_name = "VH" if chain_type == "VH" else "VL" if chain_type == "VL" else "VHH"
                key_reasons.append(f"CDR3（Δ={cdr3_delta} aa），{chain_name}")
                if cdr3_template < cdr3_target:
                    caution_notes.append("CDR3。。")
                else:
                    caution_notes.append("CDR3。。")
            else:
                caution_notes.append(f"CDR3（Δ={cdr3_delta} aa）（{cdr3_tolerance} aa）。。")
        
        elif criterion == "fr_identity":
            if fr_identity:
                fr1_id = fr_identity.get("FR1", 0.0)
                fr2_id = fr_identity.get("FR2", 0.0)
                fr3_id = fr_identity.get("FR3", 0.0)
                fr4_id = fr_identity.get("FR4", 0.0)
                
                avg_identity = sum([fr1_id, fr2_id, fr3_id, fr4_id]) / len([f for f in [fr1_id, fr2_id, fr3_id, fr4_id] if f > 0])
                fr_identity_min = tolerances.get("fr_identity_min", 0.75)
                
                if avg_identity >= 0.95:
                    key_reasons.append(f"（{avg_identity:.1%}）")
                elif avg_identity >= fr_identity_min:
                    key_reasons.append(f"（{avg_identity:.1%}）")
                
                if fr2_id >= 0.94 and fr3_id >= 0.94:
                    key_reasons.append("（FR2/FR3 > 94%）")
                elif fr3_id >= 0.95:
                    key_reasons.append("FR3（> 95%）")
        
        elif criterion == "hallmark_score":
            if hallmark_score is not None:
                hallmark_min = tolerances.get("hallmark_min", 0.6)
                if hallmark_score >= 0.9:
                    key_reasons.append(f"VHH（{hallmark_score:.2f}）")
                elif hallmark_score >= hallmark_min:
                    key_reasons.append(f"VHH（{hallmark_score:.2f}）")
                else:
                    caution_notes.append(f"VHH（{hallmark_score:.2f}）（{hallmark_min}）。VHH。")
        
        elif criterion == "cdr1_cdr2_match":
            cdr1_match = cdr_length_match.get("CDR1", {}).get("match", False)
            cdr2_match = cdr_length_match.get("CDR2", {}).get("match", False)
            if cdr1_match and cdr2_match:
                key_reasons.append("CDR1CDR2")
        
        elif criterion == "cdr3_length":
            cdr3_target = cdr_length_match.get("CDR3", {}).get("target_length", 0)
            cdr3_template = cdr_length_match.get("CDR3", {}).get("template_length", 0)
            cdr3_delta = abs(cdr3_target - cdr3_template)
            cdr3_tolerance = tolerances.get("cdr3_length_delta", 3)
            
            if cdr3_delta == 0:
                key_reasons.append("CDR3")
            elif cdr3_delta <= cdr3_tolerance:
                key_reasons.append(f"CDR3（Δ={cdr3_delta} aa）")
    
    # FR（）
    if fr_mutations == 0:
        key_reasons.append("")
    elif fr_mutations <= 3:
        key_reasons.append(f"（{fr_mutations}）")
    elif fr_mutations <= 10:
        key_reasons.append(f"（{fr_mutations}）")
    else:
        caution_notes.append(f"（{fr_mutations}），。，。")
    
    explanation = {
        "chain_type": chain_type,
        "policy_used": policy_key,
        "key_reasons": key_reasons,
        "caution_notes": caution_notes if caution_notes else []
    }
    
    return explanation

