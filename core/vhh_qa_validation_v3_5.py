"""
VHH QA v3.5 -  v3.4  Ranking Stability & Score Consistency
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from core.vhh_qa_data_calibration import VHHDataCalibration
from core.vhh_qa_validation_v3_4 import (
    validate_vhh_humanization_result_v3_4,
    _create_warning,  #  v3.4 （v3.4  v3.3 ）
)
from core.vhh_qa_ranking_stability import (
    analyze_ranking_stability,
    calibrate_score_consistency,
)
from core.vhh_qa_guidelines_vhh import build_vhh_developability_guidelines


def validate_vhh_humanization_result_v3_5(
    result: Dict[str, Any],
    strict: bool = True,
    calibration: Optional[VHHDataCalibration] = None,
) -> Dict[str, Any]:
    """
    VHH  QA  v3.5

    ：
    1.  v3.4 /
    2.  candidates  ranking stability / score consistency 
    3.  v3.4 QA  v3.5 ， qa_v3_5 
    """
    # 1.  v3.4 QA
    qa_v3_4 = validate_vhh_humanization_result_v3_4(
        result=result,
        strict=strict,
        calibration=calibration,
    )

    #  v3.5 
    qa_v3_5 = deepcopy(qa_v3_4)
    qa_v3_5.setdefault("meta", {})
    qa_v3_5["meta"]["version"] = "3.5.0"
    qa_v3_5["meta"]["ruleset"] = "VHH_QA_V3.5_RANKING"

    errors: List[str] = list(qa_v3_5.get("errors", []))
    warnings: List[Dict[str, str]] = list(qa_v3_5.get("warnings", []))

    # 2.  candidates 
    candidates = result.get("candidates") or []

    # 
    stability_result = analyze_ranking_stability(candidates, calibration=calibration)
    stability_dict = stability_result.to_dict()

    # 
    consistency_dict = calibrate_score_consistency(candidates)

    #  v3.5 
    # 1： checks （）
    checks = qa_v3_5.setdefault("checks", {})
    checks.setdefault("ranking_sanity_v3_5", {})
    checks["ranking_sanity_v3_5"]["stability_analysis"] = stability_dict
    checks["ranking_sanity_v3_5"]["score_consistency"] = consistency_dict
    
    # 2：（，）
    qa_v3_5["ranking_stability"] = stability_dict

    # 3. /

    # 3.1  major warning（ error）
    if not stability_result.is_stable:
        level = "major"
        qual = "moderately low" if stability_result.swap_risk < 0.7 else "low"
        msg = (
            f"Candidate ranking stability is {qual} (swap_risk={stability_result.swap_risk:.2f}, "
            f"stability_score={stability_result.stability_score:.2f}). "
            "Manually review template choice or prioritize consensus across top candidates."
        )
        warnings.append(_create_warning(level, "ranking", msg))

    # 3.2 pairwise consistency  warning
    for issue in stability_result.consistency_issues:
        warnings.append(
            _create_warning(
                "major",
                "ranking",
                issue,
            )
        )

    # 3.3 
    if consistency_dict.get("calibrated") and not consistency_dict.get("is_monotonic", True):
        warnings.append(
            _create_warning(
                "minor",
                "ranking",
                "After score calibration, combined vs final scores remain non-monotonic — "
                "review scoring weights if ranking decisions look inconsistent.",
            )
        )

    #  errors / warnings
    qa_v3_5["errors"] = errors
    qa_v3_5["warnings"] = warnings

    # 4.  VHH developability guideline + traffic light
    #  v3.4 QA  structural_risk_components
    structural_risk_components = (
        qa_v3_4.get("structural_risk_components")
        or qa_v3_5.get("structural_risk_components")
        or {}
    )

    #  best candidate / template  flags
    best_candidate = (result.get("candidates") or [None])[0]
    combined_flags: Dict[str, Any] = {}

    if best_candidate:
        combined_flags.update(best_candidate.get("flags") or {})
        tpl = best_candidate.get("template") or {}
        if isinstance(tpl, dict):
            tpl_flags = tpl.get("flags") or {}
            combined_flags.update(tpl_flags)

    guideline = build_vhh_developability_guidelines(
        structural_risk_components=structural_risk_components,
        flags=combined_flags,
    )

    qa_v3_5["guideline"] = guideline

    # 5.  qa_v3_5["ok"]
    # ： v3.4 OK   → OK
    qa_v3_5["ok"] = bool(qa_v3_4.get("ok", True) and len(errors) == 0)

    return qa_v3_5
