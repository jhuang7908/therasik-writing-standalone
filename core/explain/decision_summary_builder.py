"""
Decision Summary Builder
：
"""

from typing import Dict, Any, Optional

# 
try:
    from core.explain.decision_rationale_builder import build_decision_rationales
    HAS_RATIONALE_BUILDER = True
except ImportError:
    HAS_RATIONALE_BUILDER = False
    print("⚠️  ")


def build_decision_summary(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    
    
    Args:
        result: benchmark_antibody ，：
            - best_template: 
            - selection_explanation: 
            - selection_explanation_zh: 
    
    Returns:
        decision_summary ， None
    """
    best_template = result.get("best_template")
    if not best_template:
        return None
    
    selection_explanation = result.get("selection_explanation", {})
    selection_explanation_zh = result.get("selection_explanation_zh", {})
    
    template_id = best_template.get("template_id", "Unknown")
    balanced_score = best_template.get("balanced_score", 0.0)
    fr_identity = best_template.get("fr_identity", {})
    cdr_length_match = best_template.get("cdr_length_match", {})
    fr_mutations = best_template.get("fr_mutations", 0)
    hallmark_score = best_template.get("vhh_hallmark_score")
    
    # FR identity
    fr_values = [v for v in fr_identity.values() if isinstance(v, (int, float))]
    avg_fr_identity = sum(fr_values) / len(fr_values) if fr_values else 0.0
    
    # CDR
    cdr1_match = cdr_length_match.get("CDR1", {}).get("match", False)
    cdr2_match = cdr_length_match.get("CDR2", {}).get("match", False)
    cdr3_match = cdr_length_match.get("CDR3", {}).get("match", False)
    cdr3_target = cdr_length_match.get("CDR3", {}).get("target_length", 0)
    cdr3_template = cdr_length_match.get("CDR3", {}).get("template_length", 0)
    cdr3_delta = abs(cdr3_target - cdr3_template)
    
    #  confidence_level
    confidence_level = "Medium"
    if balanced_score >= 0.85 and avg_fr_identity >= 0.90:
        confidence_level = "High"
    elif balanced_score >= 0.75 and avg_fr_identity >= 0.80:
        confidence_level = "Medium-High"
    elif balanced_score < 0.60 or avg_fr_identity < 0.70:
        confidence_level = "Low"
    
    #  risk_level
    risk_level = "Low"
    risk_factors = []
    
    if fr_mutations > 15:
        risk_level = "High"
        risk_factors.append("High number of framework mutations")
    elif fr_mutations > 10:
        risk_level = "Medium"
        risk_factors.append("Moderate framework mutations")
    
    if not cdr3_match and cdr3_delta > 5:
        if risk_level == "Low":
            risk_level = "Medium"
        risk_factors.append("Significant CDR3 length mismatch")
    
    if avg_fr_identity < 0.75:
        if risk_level == "Low":
            risk_level = "Medium"
        risk_factors.append("Low framework identity")
    
    if hallmark_score is not None and hallmark_score < 0.5:
        if risk_level == "Low":
            risk_level = "Medium"
        risk_factors.append("Low VHH hallmark score")
    
    #  one_line_reason（）
    key_reasons = selection_explanation.get("key_reasons", [])
    chain_type = selection_explanation.get("chain_type", "VH")
    
    one_line_reason_en = _build_one_line_reason_en(
        chain_type, balanced_score, avg_fr_identity,
        cdr1_match, cdr2_match, cdr3_match, cdr3_delta,
        hallmark_score, key_reasons
    )
    
    #  one_line_reason（）
    key_reasons_zh = selection_explanation_zh.get("key_reasons", [])
    one_line_reason_zh = _build_one_line_reason_zh(
        chain_type, balanced_score, avg_fr_identity,
        cdr1_match, cdr2_match, cdr3_match, cdr3_delta,
        hallmark_score, key_reasons_zh
    )
    
    #  notes（）
    # ：
    # -  3  bullet
    # -  key_reasons  1-2 （ Strength）
    # -  caution_notes  0-1 （ Caution）
    # - ：[Strength]  [Caution]
    notes = []
    
    #  key_reasons  1-2  Strength
    key_reasons = selection_explanation.get("key_reasons", [])
    if key_reasons:
        #  1-2 
        strength_count = min(2, len(key_reasons))
        for reason in key_reasons[:strength_count]:
            notes.append(f"[Strength] {reason}")
    
    #  caution_notes  0-1  Caution
    caution_notes = selection_explanation.get("caution_notes", [])
    if caution_notes:
        # （）
        notes.append(f"[Caution] {caution_notes[0]}")
    
    #  3 
    notes = notes[:3]
    
    decision_summary = {
        "template_id": template_id,
        "confidence_level": confidence_level,
        "one_line_reason": {
            "en": one_line_reason_en,
            "zh": one_line_reason_zh
        },
        "risk_level": risk_level,
        "notes": notes if notes else []
    }
    
    # （risk_rationale  confidence_rationale）
    if HAS_RATIONALE_BUILDER:
        try:
            #  decision_summary  result ， build_decision_rationales 
            result_with_summary = result.copy()
            result_with_summary["decision_summary"] = decision_summary
            rationales = build_decision_rationales(result_with_summary)
            decision_summary["rationales"] = rationales
        except Exception as e:
            print(f"⚠️  : {e}")
    
    return decision_summary


def _build_one_line_reason_en(
    chain_type: str,
    balanced_score: float,
    avg_fr_identity: float,
    cdr1_match: bool,
    cdr2_match: bool,
    cdr3_match: bool,
    cdr3_delta: int,
    hallmark_score: Optional[float],
    key_reasons: list
) -> str:
    """"""
    parts = []
    
    if chain_type == "VHH" and hallmark_score is not None and hallmark_score >= 0.8:
        parts.append("excellent VHH hallmark compatibility")
    elif avg_fr_identity >= 0.90:
        parts.append("high framework compatibility")
    elif avg_fr_identity >= 0.80:
        parts.append("good framework compatibility")
    
    if cdr1_match and cdr2_match:
        parts.append("conserved CDR architecture")
    elif cdr1_match or cdr2_match:
        parts.append("partially conserved CDR architecture")
    
    if cdr3_match:
        parts.append("exact CDR3 length match")
    elif cdr3_delta <= 3:
        parts.append("acceptable CDR3 length variation")
    
    if chain_type == "VHH":
        policy_note = "under VHH-specific policy"
    elif chain_type == "VL":
        policy_note = "under VL-specific policy"
    else:
        policy_note = "under VH-specific policy"
    
    if parts:
        reason = f"Selected based on {', '.join(parts)} {policy_note}."
    else:
        reason = f"Selected based on balanced scoring ({balanced_score:.2f}) {policy_note}."
    
    return reason


def _build_one_line_reason_zh(
    chain_type: str,
    balanced_score: float,
    avg_fr_identity: float,
    cdr1_match: bool,
    cdr2_match: bool,
    cdr3_match: bool,
    cdr3_delta: int,
    hallmark_score: Optional[float],
    key_reasons_zh: list
) -> str:
    """"""
    parts = []
    
    if chain_type == "VHH" and hallmark_score is not None and hallmark_score >= 0.8:
        parts.append("VHH")
    elif avg_fr_identity >= 0.90:
        parts.append("")
    elif avg_fr_identity >= 0.80:
        parts.append("")
    
    if cdr1_match and cdr2_match:
        parts.append("CDR")
    elif cdr1_match or cdr2_match:
        parts.append("CDR")
    
    if cdr3_match:
        parts.append("CDR3")
    elif cdr3_delta <= 3:
        parts.append("CDR3")
    
    if chain_type == "VHH":
        policy_note = "VHH"
    elif chain_type == "VL":
        policy_note = "VL"
    else:
        policy_note = "VH"
    
    if parts:
        reason = f"{policy_note}，{', '.join(parts)}。"
    else:
        reason = f"{policy_note}，（{balanced_score:.2f}）。"
    
    return reason
