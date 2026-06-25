"""
VHH，QAsafe_mode
"""

from typing import Dict, Any, Optional
from core.vhh_humanization import humanize_vhh
from core.vhh_qa_validation import validate_vhh_humanization_result, validate_vhh_humanization_result_v3
from core.vhh_qa_validation_v3_3 import validate_vhh_humanization_result_v3_3
from core.vhh_qa_validation_v3_4 import validate_vhh_humanization_result_v3_4
from core.vhh_qa_validation_v3_5 import validate_vhh_humanization_result_v3_5
from core.vhh_qa_data_calibration import VHHDataCalibration
from core.audit import get_audit_logger
import logging

logger = logging.getLogger(__name__)

_VHH_QA_MERGE_KEYS = (
    "cdr_canonical",
    "cdrs",
    "key_positions",
    "hallmarks",
    "risk_flags",
    "best_match",
    "candidates",
    "sequence_analysis",
    "mutations",
    "segmentation_provenance",
)


def _merge_vhh_pipeline_into_qa_payload(qa_payload: Dict[str, Any], pipeline: Dict[str, Any]) -> None:
    """Ensure QA validators see the same VHH fields as the raw pipeline (esp. cdr_canonical)."""
    for key in _VHH_QA_MERGE_KEYS:
        if key not in pipeline:
            continue
        cur = qa_payload.get(key)
        if key == "cdr_canonical" and cur:
            continue
        if cur in (None, {}, []) and pipeline.get(key) not in (None, {}, []):
            qa_payload[key] = pipeline[key]
            continue
        if key in ("sequence_analysis", "mutations") and (not cur or not (cur.get("original_regions") or cur.get("list"))):
            qa_payload[key] = pipeline[key]


def humanize_vhh_with_qa(
    seq: str,
    panel: str = "A",
    top_k: int = 3,
    species: str = "alpaca",
    return_all_templates: bool = False,
    scoring_profile: Optional[str] = None,
    enable_safe_mode: bool = True,
    strict_qa: bool = True,
    qa_version: str = "v3.5",  # ：QA（"v3.4"  "v3.5"）
    extra_protected: Optional[set] = None,  # V2.2: CDR3Tier
    enforce_prescreen: bool = True,         # P0-2: prescreen hard-gate (default True)
) -> Dict[str, Any]:
    """
    VHH，QAsafe_mode
    
    Args:
        seq: VHH
        panel: （'A', 'B', 'C', 'all'）
        top_k: k
        species: 
        return_all_templates: 
        scoring_profile: Scoring profile
        enable_safe_mode: safe_mode
        strict_qa: QA（True，QA）
        qa_version: QA（"v3.4"  "v3.5"， "v3.5"）
    
    Returns:
        ，status：
        - "OK": QA，
        - "OK_SAFE_MODE": safe_mode
        - "FAILED_QA": QA
        - "FAILED": 
    """
    # ：
    # V2.2:  extra_protected  Tier 
    # P0-2:  enforce_prescreen；hard-gate  humanize_vhh 
    #       route='surface_reshaping_only'， QA。
    result = humanize_vhh(
        seq=seq,
        panel=panel,
        top_k=top_k,
        species=species,
        return_all_templates=return_all_templates,
        scoring_profile=scoring_profile,
        extra_protected=extra_protected,
        enforce_prescreen=enforce_prescreen,
    )

    # P0-2: prescreen short-circuit — no graft attempted, no QA to run.
    if result.get("route") == "surface_reshaping_only":
        result.setdefault("status", "PRESCREEN_SURFACE_RESHAPING_ONLY")
        result.setdefault("qa", {})
        result["qa"].setdefault("ok", False)
        result["qa"].setdefault("active_version", qa_version)
        result["qa"].setdefault("errors", [])
        result["qa"].setdefault(
            "warnings",
            ["Prescreen routed to surface_reshaping_only; QA skipped by design."],
        )
        return result

    # ，
    if not result.get("success"):
        result["status"] = "FAILED"
        return result
    
    # QA
    from core.json_data_preparer import prepare_json_data
    try:
        json_data = prepare_json_data(result, "QA_CHECK")
    except Exception as e:
        logger.warning(f"QA: {e}，")
        json_data = {
            "sequence_analysis": {
                "original_regions": {},
                "humanized_regions": {},
            },
            "mutations": {"list": []},
            "best_match": result.get("best_match", {})
        }
    _merge_vhh_pipeline_into_qa_payload(json_data, result)
    
    # QA - 
    qa_v2_result = validate_vhh_humanization_result(json_data, strict=False)  # v2.0
    qa_v3_result = validate_vhh_humanization_result_v3(json_data, strict=strict_qa)  # v3.2
    qa_v3_3_result = validate_vhh_humanization_result_v3_3(json_data, strict=strict_qa)  # v3.3
    qa_v3_4_result = validate_vhh_humanization_result_v3_4(json_data, strict=strict_qa, calibration=None)  # v3.4
    qa_v3_5_result = validate_vhh_humanization_result_v3_5(json_data, strict=strict_qa, calibration=None)  # v3.5
    
    # ：
    result.setdefault("qa", {})
    result["qa"]["v2"] = qa_v2_result
    result["qa"]["v3"] = qa_v3_result
    result["qa"]["v3_3"] = qa_v3_3_result
    result["qa"]["v3_4"] = qa_v3_4_result
    result["qa"]["v3_5"] = qa_v3_5_result
    
    #  risk 
    try:
        from core.vhh_affinity_optimization import run_affinity_optimization_v1
        affinity_block = run_affinity_optimization_v1(result)
        result["affinity"] = affinity_block
    except Exception as e:
        logger.warning(f": {e}")
        result["affinity"] = {
            "hotspots": [],
            "candidates": [],
            "variants": {},
            "narrative": f": {str(e)}",
        }
    
    # qa_versionOK
    if qa_version == "v3.5":
        active_qa_result = qa_v3_5_result
        result["qa"]["active_version"] = "v3.5"
    elif qa_version == "v3.4":
        active_qa_result = qa_v3_4_result
        result["qa"]["active_version"] = "v3.4"
    else:
        # v3.5
        active_qa_result = qa_v3_5_result
        result["qa"]["active_version"] = "v3.5"
        logger.warning(f"qa_version={qa_version}，v3.5")
    
    # ：result["qa"]active_version
    result["qa"]["ok"] = active_qa_result.get("ok", False)
    result["qa"]["errors"] = active_qa_result.get("errors", [])
    # warnings
    warnings_list = []
    for w in active_qa_result.get("warnings", []):
        if isinstance(w, dict):
            warnings_list.append(w.get("message", str(w)))
        else:
            warnings_list.append(str(w))
    result["qa"]["warnings"] = warnings_list
    
    # QA（active_version）
    if active_qa_result["ok"]:
        result["status"] = "OK"
        active_warnings = active_qa_result.get("warnings", [])
        if active_warnings:
            major_warnings = [w for w in active_warnings if isinstance(w, dict) and w.get("level") == "major"]
            if major_warnings:
                logger.warning(f"QA ({result['qa']['active_version']}): {[w.get('message') for w in major_warnings]}")
        return result

    # strict_qa=False ：QA，
    if not strict_qa:
        qa_errors = active_qa_result.get("errors", [])
        logger.warning(f"QA（，）: {qa_errors}")
        result["status"] = "OK_WITH_QA_WARNINGS"
        result["qa"]["ok"] = False  # QA，
        return result

    # QA（strict_qa=True）
    logger.warning(f"QA ({result['qa']['active_version']}): {active_qa_result['errors']}")
    
    # safe_mode，
    if enable_safe_mode:
        logger.info("safe_mode...")
        safe_result = _try_safe_mode(
            seq=seq,
            panel=panel,
            top_k=top_k,
            species=species,
            return_all_templates=return_all_templates,
        )
        
        if safe_result.get("success"):
            # safe_mode
            try:
                safe_json_data = prepare_json_data(safe_result, "QA_CHECK")
            except Exception as e:
                logger.warning(f"safe_mode QA: {e}，")
                safe_json_data = {
                    "sequence_analysis": {
                        "original_regions": {},
                        "humanized_regions": {},
                    },
                    "mutations": {"list": []},
                    "best_match": safe_result.get("best_match", {})
                }
            _merge_vhh_pipeline_into_qa_payload(safe_json_data, safe_result)
            
            # Safe mode QA（qa_version）
            safe_qa_v2 = validate_vhh_humanization_result(safe_json_data, strict=False)
            safe_qa_v3 = validate_vhh_humanization_result_v3(safe_json_data, strict=strict_qa)
            safe_qa_v3_3 = validate_vhh_humanization_result_v3_3(safe_json_data, strict=strict_qa)
            safe_qa_v3_4 = validate_vhh_humanization_result_v3_4(safe_json_data, strict=strict_qa, calibration=None)
            safe_qa_v3_5 = validate_vhh_humanization_result_v3_5(safe_json_data, strict=strict_qa, calibration=None)
            
            safe_result.setdefault("qa", {})
            safe_result["qa"]["v2"] = safe_qa_v2
            safe_result["qa"]["v3"] = safe_qa_v3
            safe_result["qa"]["v3_3"] = safe_qa_v3_3
            safe_result["qa"]["v3_4"] = safe_qa_v3_4
            safe_result["qa"]["v3_5"] = safe_qa_v3_5
            
            # qa_version
            if qa_version == "v3.5":
                safe_active_qa = safe_qa_v3_5
                safe_result["qa"]["active_version"] = "v3.5"
            elif qa_version == "v3.4":
                safe_active_qa = safe_qa_v3_4
                safe_result["qa"]["active_version"] = "v3.4"
            else:
                safe_active_qa = safe_qa_v3_5
                safe_result["qa"]["active_version"] = "v3.5"
            
            if safe_active_qa["ok"]:
                safe_result["qa"]["ok"] = safe_active_qa["ok"]
                safe_result["qa"]["errors"] = safe_active_qa["errors"]
                # warnings
                warnings_list = []
                for w in safe_active_qa.get("warnings", []):
                    if isinstance(w, dict):
                        warnings_list.append(w.get("message", str(w)))
                    else:
                        warnings_list.append(str(w))
                safe_result["qa"]["warnings"] = warnings_list
                logger.info(f"safe_mode (QA: {safe_result['qa']['active_version']})")
                safe_result["status"] = "OK_SAFE_MODE"
                safe_result["fallback_reason"] = f"Standard mode failed QA ({result['qa']['active_version']}), used safe_mode"
                safe_result["original_qa_errors"] = active_qa_result["errors"]
                return safe_result
            else:
                logger.warning(f"safe_modeQA ({safe_result['qa']['active_version']}): {safe_active_qa['errors']}")
    
    # 
    result["status"] = f"FAILED_QA_{result['qa']['active_version'].upper().replace('.', '_')}"
    result["error"] = f"QA ({result['qa']['active_version']}): {', '.join(active_qa_result['errors'])}"
    return result


def _try_safe_mode(
    seq: str,
    panel: str = "A",
    top_k: int = 3,
    species: str = "alpaca",
    return_all_templates: bool = False,
) -> Dict[str, Any]:
    """
    Safe：
    
    - A（）
    - CMC/
    - 
    """
    # A（）
    safe_panel = "A"

    # scoring profile（）
    # default
    # P0-2: safe_mode is reached only after the outer call already passed
    # prescreen (otherwise the wrapper short-circuits via PRESCREEN_*).
    # Skip prescreen here to avoid re-running an already-decided gate.
    safe_result = humanize_vhh(
        seq=seq,
        panel=safe_panel,  # A
        top_k=min(top_k, 5),  # 
        species=species,
        return_all_templates=return_all_templates,
        scoring_profile="default",  # 
        enforce_prescreen=False,
    )
    
    # safe_mode
    if safe_result.get("success"):
        safe_result["safe_mode"] = True
        safe_result["safe_mode_panel"] = safe_panel
    
    return safe_result

