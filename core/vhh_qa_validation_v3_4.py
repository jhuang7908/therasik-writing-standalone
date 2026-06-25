"""
VHHQA v3.4

v3.4：
- 
- （FR2/grafting/CDR3 anchor）
- CDR3 anchor
"""

from typing import Dict, List, Any, Optional
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# v3.3（）
from core.vhh_qa_validation_v3_3 import (
    validate_vhh_humanization_result_v3_3,
    _create_warning,
    auto_build_mutations_from_regions
)

# v3.4
from core.vhh_qa_data_calibration import VHHDataCalibration
from core.vhh_qa_structural_risk_layered import (
    compute_layered_structural_risk,
    StructuralRiskComponents
)


def compute_final_score_v3_4(
    candidate: Dict[str, Any],
    calibration: Optional[VHHDataCalibration] = None
) -> float:
    """
    v3.4: final_score
    
    Args:
        candidate: 
        calibration: （，；）
    
    Returns:
        final score
    """
    scores = candidate.get("alignment_scores", {}) or candidate.get("scores", {})
    base = scores.get("combined_score", 0.0) or scores.get("combined", 0.0)
    
    # structural_risk（）
    structural_risk = scores.get("structural_risk", 0.0)
    
    # structural_risk，risk_components
    if structural_risk == 0.0:
        risk_components = scores.get("structural_risk_components", {})
        if risk_components:
            structural_risk = risk_components.get("total_risk", 0.0)
    
    # 
    if calibration:
        weights = calibration.get_calibrated_weights()
        structural_risk_weight = weights["structural_risk_weight"]
        hallmark_penalty_base = weights["hallmark_penalty"]
    else:
        # VHH：/，
        structural_risk_weight = 0.30
        hallmark_penalty_base = 0.15
    
    # Hallmark penalty
    actual_hallmark_penalty = 0.0
    flags = candidate.get("flags", {}) or {}
    template = candidate.get("template", {})
    if isinstance(template, dict):
        template_flags = template.get("flags", {}) or {}
        flags = {**flags, **template_flags}
    
    if not flags.get("has_vhh_hallmark", True):
        actual_hallmark_penalty = hallmark_penalty_base
    elif flags.get("reduced_hallmark", False):
        actual_hallmark_penalty = hallmark_penalty_base * 0.33
    
    final = base - structural_risk_weight * structural_risk - actual_hallmark_penalty
    
    # candidatescores
    if "scores" not in candidate:
        candidate["scores"] = {}
    candidate["scores"]["final"] = final
    candidate["scores"]["structural_risk"] = structural_risk
    candidate["scores"]["structural_risk_weight"] = structural_risk_weight
    candidate["scores"]["hallmark_penalty"] = actual_hallmark_penalty
    
    return final


def validate_vhh_humanization_result_v3_4(
    result: Dict[str, Any],
    strict: bool = True,
    calibration: Optional[VHHDataCalibration] = None
) -> Dict[str, Any]:
    """
    VHHQA v3.4
    
    v3.4：
    - 
    - （FR2/grafting/CDR3 anchor）
    - CDR3 anchor
    
    Args:
        result: 
        strict: （True，error）
        calibration: （）
    
    Returns:
        qa_v3_4（v3.3，structural_risk_components）
    """
    # v3.3（）
    qa_v3_3 = validate_vhh_humanization_result_v3_3(result, strict=False)
    
    errors = qa_v3_3.get("errors", [])
    warnings = qa_v3_3.get("warnings", [])
    
    # 
    seq_analysis = result.get("sequence_analysis", {})
    orig_regions = seq_analysis.get("original_regions", {}) or {}
    hum_regions = seq_analysis.get("humanized_regions", {}) or {}
    template_info = result.get("best_match", {}).get("template", {})
    
    # === v3.4: （） ===
    risk_components = compute_layered_structural_risk(
        orig_regions, hum_regions, template_info
    )
    
    # risk_componentsresult
    if "qa" not in result:
        result["qa"] = {}
    result["qa"]["structural_risk_components"] = risk_components.to_dict()
    
    # === v3.4: CDR3 anchor（： error）===
    if risk_components.cdr3_anchor_risk >= 0.95:
        # Note: this threshold (designed for VH/VL) is conservative for VHH.
        # VHH CDR3 loops are inherently more stable; flag as advisory, not hard error.
        warnings.append(_create_warning(
            "major",
            "structural",
            f"CDR3 anchor mismatch (IMGT FR3 positions 101–102; orig vs humanized vs VH3 template) — "
            f"risk score {risk_components.cdr3_anchor_risk:.2f} after VHH long-CDR3 dampening. "
            "Template residues at 101/102 often differ from camelid VHH; "
            "experimental validation (SPR/BLI, Tm) is recommended if score remains elevated."
        ))
    elif risk_components.cdr3_anchor_risk >= 0.7:
        warnings.append(_create_warning(
            "major",
            "structural",
            f"CDR3 anchor advisory (IMGT 101–102) — risk score {risk_components.cdr3_anchor_risk:.2f}. "
            "Confirm with structural modeling or cross-species VHH benchmarks."
        ))
    
        # === v3.4: structural_risk + final_score ===
    candidates = result.get("candidates", [])
    for cand in candidates:
        # （）
        # ：candidatesorig_regionshum_regions
        # ，orig_regionshum_regions
        cand_orig_regions = cand.get("orig_regions", orig_regions)
        cand_hum_regions = cand.get("hum_regions", hum_regions)
        
        # candidates，
        if not cand_orig_regions or not cand_hum_regions:
            cand_orig_regions = orig_regions
            cand_hum_regions = hum_regions
        
        # 
        cand_risk_components = compute_layered_structural_risk(
            cand_orig_regions, cand_hum_regions, cand.get("template", {})
        )
        
        # candidatescores
        if "scores" not in cand:
            cand["scores"] = {}
        cand["scores"]["structural_risk_components"] = cand_risk_components.to_dict()
        cand["scores"]["structural_risk"] = cand_risk_components.total_risk
        
        # final_score
        compute_final_score_v3_4(cand, calibration)
        
    # v3.4:  final_score  candidates，
    if candidates:
        candidates.sort(key=lambda c: c.get("scores", {}).get("final", 0.0), reverse=True)
    
    # === qa_v3_4（v3.3） ===
    qa_v3_4 = {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "checks": qa_v3_3.get("checks", {}),
        "summary_score": qa_v3_3.get("summary_score", {}),
        "structural_risk_components": risk_components.to_dict(),  # v3.4
        "meta": {
            "version": "3.4.0",
            "ruleset": "VHH_QA_V3.4_CALIBRATED",
            "calibration_used": calibration is not None
        }
    }
    
    # v3.3，
    for key in ["mutation_map", "conformation_risk_summary", "experimental_recommendations"]:
        if key in qa_v3_3:
            qa_v3_4[key] = qa_v3_3[key]
    
    return qa_v3_4


# TODO(v3.5):
# -  ranking stability  (analyze_ranking_stability, calibrate_score_consistency)
# -  validate_vhh_humanization_result_v3_4  ranking sanity 
# - heuristic
# - pairwise consistency
# - isotonic regression

















