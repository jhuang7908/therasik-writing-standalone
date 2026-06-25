"""
Decision Rationale Builder
： risk_level  confidence_level 
"""

from typing import Dict, Any, Optional


def build_decision_rationales(result: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    （risk_rationale  confidence_rationale）
    
    ：
    - 、、
    - 
    - 
    
    Args:
        result: benchmark_antibody ，：
            - best_template: 
            - selection_explanation: 
            - decision_summary: （ risk_level, confidence_level, notes）
    
    Returns:
        rationales ， risk  confidence 
    """
    best_template = result.get("best_template", {})
    selection_explanation = result.get("selection_explanation", {})
    decision_summary = result.get("decision_summary", {})
    
    risk_level = decision_summary.get("risk_level", "Medium")
    confidence_level = decision_summary.get("confidence_level", "Medium")
    notes = decision_summary.get("notes", [])
    policy_used = selection_explanation.get("policy_used", "VH")
    
    # 
    fr_identity = best_template.get("fr_identity", {})
    fr_values = [v for v in fr_identity.values() if isinstance(v, (int, float))]
    avg_fr_identity = sum(fr_values) / len(fr_values) if fr_values else 0.0
    fr_mutations = best_template.get("fr_mutations", 0)
    
    cdr_length_match = best_template.get("cdr_length_match", {})
    cdr3_target = cdr_length_match.get("CDR3", {}).get("target_length", 0)
    cdr3_template = cdr_length_match.get("CDR3", {}).get("template_length", 0)
    cdr3_delta = abs(cdr3_target - cdr3_template)
    
    #  Caution notes
    has_caution = any("[Caution]" in note for note in notes)
    
    #  Risk Rationale
    risk_rationale_en = _build_risk_rationale_en(
        risk_level, has_caution, avg_fr_identity, fr_mutations, cdr3_delta
    )
    risk_rationale_zh = _build_risk_rationale_zh(
        risk_level, has_caution, avg_fr_identity, fr_mutations, cdr3_delta
    )
    
    #  Confidence Rationale
    confidence_rationale_en = _build_confidence_rationale_en(
        confidence_level, policy_used, avg_fr_identity, fr_mutations
    )
    confidence_rationale_zh = _build_confidence_rationale_zh(
        confidence_level, policy_used, avg_fr_identity, fr_mutations
    )
    
    rationales = {
        "risk": {
            "en": risk_rationale_en,
            "zh": risk_rationale_zh
        },
        "confidence": {
            "en": confidence_rationale_en,
            "zh": confidence_rationale_zh
        }
    }
    
    # canonical（）
    # ：canonical，，scaffold
    canonical_risk_level = result.get("canonical_risk_level")
    if canonical_risk_level:
        canonical_rationale_en, canonical_rationale_zh = _build_canonical_rationale(canonical_risk_level)
        rationales["canonical"] = {
            "canonical_risk_level": canonical_risk_level,
            "canonical_rationale_en": canonical_rationale_en,
            "canonical_rationale_zh": canonical_rationale_zh,
        }
    
    return rationales


def _build_risk_rationale_en(
    risk_level: str,
    has_caution: bool,
    avg_fr_identity: float,
    fr_mutations: int,
    cdr3_delta: int
) -> str:
    """"""
    parts = []
    
    #  risk_level 
    if risk_level == "Low":
        if avg_fr_identity >= 0.90:
            parts.append("framework compatibility is high")
        elif avg_fr_identity >= 0.80:
            parts.append("framework compatibility is good")
        
        if not has_caution:
            parts.append("no policy-level caution flags were triggered")
        else:
            parts.append("only minor caution items were noted")
        
        if fr_mutations <= 5:
            parts.append("minimal framework mutations required")
    
    elif risk_level == "Medium":
        if has_caution:
            parts.append("policy-level caution flags were triggered")
        
        if avg_fr_identity < 0.80:
            parts.append("framework compatibility is moderate")
        elif avg_fr_identity >= 0.80:
            parts.append("framework compatibility is good but some concerns exist")
        
        if fr_mutations > 10:
            parts.append("moderate number of framework mutations required")
        elif cdr3_delta > 5:
            parts.append("significant CDR3 length differences")
        
        # ""
        parts.append("the template remains viable with appropriate experimental validation and potential second-round optimization")
    
    else:  # High
        parts.append("multiple risk factors are present")
        if fr_mutations > 15:
            parts.append("high number of framework mutations required")
        if avg_fr_identity < 0.75:
            parts.append("low framework compatibility")
        if cdr3_delta > 10:
            parts.append("major CDR3 length differences")
        
        # ""（High Risk ）
        parts.append("the template may still be viable with extensive experimental validation and comprehensive second-round optimization, though higher risk should be carefully considered")
    
    if parts:
        # ""，
        main_parts = [p for p in parts if "remains viable" not in p.lower()]
        viability_parts = [p for p in parts if "remains viable" in p.lower()]
        
        if main_parts and viability_parts:
            rationale = f"Risk rated {risk_level} because {', '.join(main_parts)}. However, {', '.join(viability_parts)}."
        elif main_parts:
            rationale = f"Risk rated {risk_level} because {', '.join(main_parts)}."
        else:
            rationale = f"Risk rated {risk_level} based on overall template compatibility assessment."
    else:
        rationale = f"Risk rated {risk_level} based on overall template compatibility assessment."
    
    return rationale


def _build_risk_rationale_zh(
    risk_level: str,
    has_caution: bool,
    avg_fr_identity: float,
    fr_mutations: int,
    cdr3_delta: int
) -> str:
    """"""
    parts = []
    
    if risk_level == "Low":
        if avg_fr_identity >= 0.90:
            parts.append("")
        elif avg_fr_identity >= 0.80:
            parts.append("")
        
        if not has_caution:
            parts.append("")
        else:
            parts.append("")
        
        if fr_mutations <= 5:
            parts.append("")
    
    elif risk_level == "Medium":
        if has_caution:
            parts.append("")
        
        if avg_fr_identity < 0.80:
            parts.append("")
        elif avg_fr_identity >= 0.80:
            parts.append("")
        
        if fr_mutations > 10:
            parts.append("")
        elif cdr3_delta > 5:
            parts.append("CDR3")
        
        # ""
        parts.append("，")
    
    else:  # High
        parts.append("")
        if fr_mutations > 15:
            parts.append("")
        if avg_fr_identity < 0.75:
            parts.append("")
        if cdr3_delta > 10:
            parts.append("CDR3")
        
        # ""（High Risk ）
        parts.append("，，")
    
    # 
    risk_level_zh_map = {
        "Low": "",
        "Medium": "",
        "High": ""
    }
    risk_level_zh = risk_level_zh_map.get(risk_level, risk_level)
    
    if parts:
        # ""，
        main_parts = [p for p in parts if "" not in p]
        viability_parts = [p for p in parts if "" in p]
        
        if main_parts and viability_parts:
            rationale = f"{risk_level_zh}：{', '.join(main_parts)}。，{', '.join(viability_parts)}。"
        elif main_parts:
            rationale = f"{risk_level_zh}：{', '.join(main_parts)}。"
        else:
            rationale = f"{risk_level_zh}：。"
    else:
        rationale = f"{risk_level_zh}：。"
    
    return rationale


def _build_confidence_rationale_en(
    confidence_level: str,
    policy_used: str,
    avg_fr_identity: float,
    fr_mutations: int
) -> str:
    """"""
    # 
    policy_name_map = {
        "VH": "VH",
        "VL": "VL",
        "VHH": "VHH"
    }
    policy_display = policy_name_map.get(policy_used, "VH")
    
    # 
    if confidence_level == "High":
        if avg_fr_identity >= 0.90:
            match_performance = "strong framework compatibility"
        else:
            match_performance = "strong overall match"
    elif confidence_level in ["Medium-High", "Medium"]:
        match_performance = "moderate overall match"
    else:  # Low
        match_performance = "limited overall match"
    
    rationale = (
        f"Confidence rated {confidence_level} because {match_performance} "
        f"exceeds the {confidence_level.lower()}-confidence thresholds "
        f"under {policy_display}-specific policy."
    )
    
    return rationale


def _build_confidence_rationale_zh(
    confidence_level: str,
    policy_used: str,
    avg_fr_identity: float,
    fr_mutations: int
) -> str:
    """"""
    # 
    policy_name_map = {
        "VH": "VH",
        "VL": "VL",
        "VHH": "VHH"
    }
    policy_display = policy_name_map.get(policy_used, "VH")
    
    # 
    if confidence_level == "High":
        if avg_fr_identity >= 0.90:
            match_performance = ""
        else:
            match_performance = ""
    elif confidence_level in ["Medium-High", "Medium"]:
        match_performance = ""
    else:  # Low
        match_performance = ""
    
    # 
    confidence_desc_map = {
        "High": "",
        "Medium-High": "",
        "Medium": "",
        "Low": ""
    }
    confidence_desc = confidence_desc_map.get(confidence_level, "")
    
    # 
    confidence_level_zh_map = {
        "High": "",
        "Medium-High": "",
        "Medium": "",
        "Low": ""
    }
    confidence_level_zh = confidence_level_zh_map.get(confidence_level, confidence_level)
    
    rationale = (
        f"{confidence_level_zh}：{policy_display}，"
        f"{match_performance}{confidence_desc}。"
    )
    
    return rationale


def _build_canonical_rationale(risk_level: str) -> tuple[str, str]:
    """
    canonical（）
    
    ：，（、Kabat）
    
    Canonical analysis is an explanatory layer for structural compatibility.
    It does not alter scaffold selection or humanization rules in the Classic Panel.
    
    Args:
        risk_level: "low" | "medium" | "high"
    
    Returns:
        (rationale_en, rationale_zh)
    """
    risk_level_lower = risk_level.lower()
    
    if risk_level_lower == "low":
        rationale_en = "CDR1 and CDR2 canonical features are compatible with the selected scaffold, indicating low structural compatibility risk."
        rationale_zh = "CDR1  CDR2 ，。"
    elif risk_level_lower == "medium":
        rationale_en = "A mismatch in CDR1 or CDR2 canonical features was observed, which may introduce moderate structural compatibility risk."
        rationale_zh = " CDR1  CDR2 ，。"
    elif risk_level_lower == "high":
        rationale_en = "Both CDR1 and CDR2 canonical features differ from the selected scaffold, indicating a higher risk of structural incompatibility."
        rationale_zh = "CDR1  CDR2 ，。"
    else:
        rationale_en = "Canonical compatibility analysis completed."
        rationale_zh = "。"
    
    return rationale_en, rationale_zh

