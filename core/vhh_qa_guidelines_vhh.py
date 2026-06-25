"""
VHH QA - Developability guideline & traffic light for VHH (v3.5+)

：
-  (FR2 / grafting / CDR3 anchor)
- hallmark 
-  structural_risk

：
- guideline_flags:  / 
- traffic_light: "green" / "yellow" / "red"
"""

from __future__ import annotations

from typing import Any, Dict, List


def _classify_risk_level(value: float, low: float, high: float) -> str:
    """
    ：
    - value <= low  -> "low"
    - low < value < high -> "medium"
    - value >= high -> "high"
    """
    if value <= low:
        return "low"
    if value >= high:
        return "high"
    return "medium"


def build_vhh_developability_guidelines(
    structural_risk_components: Dict[str, float],
    flags: Dict[str, Any],
) -> Dict[str, Any]:
    """
     VHH ， guideline flag + traffic light。

    Args:
        structural_risk_components: 
            {
                "fr2_hydrophilic_patch_risk": float,
                "grafting_interface_risk": float,
                "cdr3_anchor_risk": float,
                "total_risk": float,
            }
        flags:  candidate / template ，：
            {
                "has_vhh_hallmark": bool,
                "reduced_hallmark": bool,
                ...
            }

    Returns:
        {
            "traffic_light": "green" | "yellow" | "red",
            "flags": [
                {
                    "id": "FR2_RISK",
                    "level": "low" | "medium" | "high",
                    "message": "..."
                },
                ...
            ]
        }
    """
    fr2_risk = float(structural_risk_components.get("fr2_hydrophilic_patch_risk", 0.0))
    graft_risk = float(structural_risk_components.get("grafting_interface_risk", 0.0))
    anchor_risk = float(structural_risk_components.get("cdr3_anchor_risk", 0.0))
    total_risk = float(structural_risk_components.get("total_risk", 0.0))

    has_hallmark = bool(flags.get("has_vhh_hallmark", True))
    reduced_hallmark = bool(flags.get("reduced_hallmark", False))

    guideline_flags: List[Dict[str, Any]] = []

    # 1. FR2 
    fr2_level = _classify_risk_level(fr2_risk, low=0.2, high=0.6)
    if fr2_level == "low":
        msg = "FR2 hydrophilic patch ，VHH 。"
    elif fr2_level == "medium":
        msg = "FR2 hydrophilic patch ，。"
    else:
        msg = "FR2 hydrophilic patch ，VHH ，。"
    guideline_flags.append({
        "id": "FR2_RISK",
        "level": fr2_level,
        "message": msg,
        "value": fr2_risk,
    })

    # 2. CDR3 anchor （）
    anchor_level = _classify_risk_level(anchor_risk, low=0.2, high=0.7)
    if anchor_level == "low":
        msg = "CDR3 anchor ，101/102 。"
    elif anchor_level == "medium":
        msg = "CDR3 anchor ，，。"
    else:
        msg = (
            "CDR3 anchor ，，"
            " VHH 。"
        )
    guideline_flags.append({
        "id": "CDR3_ANCHOR_RISK",
        "level": anchor_level,
        "message": msg,
        "value": anchor_risk,
    })

    # 3. Grafting interface 
    graft_level = _classify_risk_level(graft_risk, low=0.2, high=0.6)
    if graft_level == "low":
        msg = "Grafting interface ，FR–CDR 。"
    elif graft_level == "medium":
        msg = "Grafting interface ，。"
    else:
        msg = "Grafting interface ，。"
    guideline_flags.append({
        "id": "GRAFTING_RISK",
        "level": graft_level,
        "message": msg,
        "value": graft_risk,
    })

    # 4. 
    total_level = _classify_risk_level(total_risk, low=0.2, high=0.6)
    if total_level == "low":
        msg = "， VHH 。"
    elif total_level == "medium":
        msg = "，，。"
    else:
        msg = "，。"
    guideline_flags.append({
        "id": "TOTAL_STRUCTURAL_RISK",
        "level": total_level,
        "message": msg,
        "value": total_risk,
    })

    # 5. hallmark 
    if not has_hallmark:
        guideline_flags.append({
            "id": "VHH_HALLMARK",
            "level": "high",
            "message": (
                "VHH hallmark （FR2 ），"
                " VHH  scaffold。"
            ),
            "value": 1.0,
        })
    elif reduced_hallmark:
        guideline_flags.append({
            "id": "VHH_HALLMARK",
            "level": "medium",
            "message": "VHH hallmark ，。",
            "value": 0.5,
        })
    else:
        guideline_flags.append({
            "id": "VHH_HALLMARK",
            "level": "low",
            "message": "VHH hallmark ， FR2 。",
            "value": 0.0,
        })

    # ===  traffic_light ===
    # （）：
    # - ：anchor_level == "high"  total_level == "high"
    # - ： "medium"  "high"
    # - ： low， hallmark  low
    has_high = any(f["level"] == "high" for f in guideline_flags)
    has_medium = any(f["level"] == "medium" for f in guideline_flags)

    if has_high:
        traffic_light = "red"
    elif has_medium:
        traffic_light = "yellow"
    else:
        traffic_light = "green"

    return {
        "traffic_light": traffic_light,
        "flags": guideline_flags,
    }

















