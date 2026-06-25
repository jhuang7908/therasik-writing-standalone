"""
VHH QA v3.5 - Ranking stability & score consistency

：
- （best vs second ）
-  pairwise consistency（FR identity  final_score ）
-  combined_score / final_score （ isotonic regression）

：
- numpy
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class RankingStabilityResult:
    """"""

    is_stable: bool
    stability_score: float  # 0~1, 
    swap_risk: float        # 0~1, best/second 
    consistency_issues: List[str]
    tier: str = "A"  # A/B/C/D
    recommended_output_mode: str = "single_lead"
    tier_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_stable": self.is_stable,
            "stability_score": float(self.stability_score),
            "swap_risk": float(self.swap_risk),
            "consistency_issues": list(self.consistency_issues),
            "tier": self.tier,
            "recommended_output_mode": self.recommended_output_mode,
            "tier_reason": self.tier_reason,
        }


def analyze_ranking_stability(
    candidates: List[Dict[str, Any]],
    calibration: Optional[Any] = None,  # ，
) -> RankingStabilityResult:
    """
    （v3.5 ）

    ：
    1.  top2：best / second  final_score   structural_risk 
    2.  ""  swap_risk
    3.  pairwise consistency（FR identity vs final_score ）

    ：
        RankingStabilityResult
    """
    if not candidates or len(candidates) < 2:
        return RankingStabilityResult(
            is_stable=True,
            stability_score=1.0,
            swap_risk=0.0,
            consistency_issues=[],
            tier="A",
            recommended_output_mode="single_lead",
            tier_reason="Only one candidate available; ranking swap risk is not applicable.",
        )

    best = candidates[0]
    second = candidates[1]

    swap_risk = _compute_swap_risk(best, second)
    consistency_issues = _check_pairwise_consistency(candidates)

    # ：1 - swap_risk
    stability_score = 1.0 - swap_risk

    #  consistency issue （0.1 / issue）
    stability_score -= 0.1 * len(consistency_issues)
    stability_score = max(0.0, min(1.0, stability_score))

    # ""
    is_stable = (stability_score >= 0.7) and (swap_risk < 0.3)
    tier, output_mode, tier_reason = _map_stability_tier(
        swap_risk=swap_risk,
        stability_score=stability_score,
        n_consistency_issues=len(consistency_issues),
    )

    return RankingStabilityResult(
        is_stable=is_stable,
        stability_score=stability_score,
        swap_risk=swap_risk,
        consistency_issues=consistency_issues,
        tier=tier,
        recommended_output_mode=output_mode,
        tier_reason=tier_reason,
    )


def _map_stability_tier(
    swap_risk: float,
    stability_score: float,
    n_consistency_issues: int,
) -> Tuple[str, str, str]:
    """
    Map ranking stability into product-facing recommendation tiers.

    A: single lead is reliable
    B: lead + consensus recommendation
    C: dual lead + consensus (near tie)
    D: unstable ranking, require manual review before claiming lead
    """
    if swap_risk >= 0.8 or (swap_risk >= 0.6 and n_consistency_issues >= 2):
        return (
            "D",
            "manual_review_required",
            (
                f"Very high swap risk ({swap_risk:.2f}) with ranking inconsistencies "
                f"({n_consistency_issues}); avoid claiming a single lead before manual/experimental review."
            ),
        )
    if swap_risk >= 0.6 or stability_score < 0.4:
        return (
            "C",
            "dual_lead_plus_consensus",
            (
                f"Near-tied ranking (swap_risk={swap_risk:.2f}, stability_score={stability_score:.2f}); "
                "present Top-1 and Top-2 as dual leads and prioritize shared mutations."
            ),
        )
    if swap_risk >= 0.4 or stability_score < 0.7:
        return (
            "B",
            "lead_plus_consensus",
            (
                f"Moderate ranking uncertainty (swap_risk={swap_risk:.2f}); keep Top-1 as lead "
                "but provide consensus mutations as robust fallback."
            ),
        )
    return (
        "A",
        "single_lead",
        (
            f"Stable ranking (swap_risk={swap_risk:.2f}, stability_score={stability_score:.2f}); "
            "single lead recommendation is acceptable."
        ),
    )


def _get_scores_view(cand: Dict[str, Any]) -> Dict[str, float]:
    """ candidate  score """
    scores = cand.get("scores") or cand.get("alignment_scores") or {}
    return {
        "final": float(scores.get("final", 0.0) or 0.0),
        "combined": float(
            scores.get("combined_score", scores.get("combined", 0.0)) or 0.0
        ),
        "fr_identity": float(
            scores.get("fr_identity", scores.get("framework_identity", 0.0)) or 0.0
        ),
        "structural_risk": float(scores.get("structural_risk", 0.0) or 0.0),
    }


def _compute_swap_risk(best: Dict[str, Any], second: Dict[str, Any]) -> float:
    """
     best / second （0~1）

    ：
    -  second  structural_risk  best， final_score  →  → swap_risk 
    -  final_score / risk  →  → swap_risk 
    -  second  best（risk ） → swap_risk （）
    """
    s_best = _get_scores_view(best)
    s_second = _get_scores_view(second)

    gap_final = s_best["final"] - s_second["final"]         # >0  best 
    gap_risk = s_second["structural_risk"] - s_best["structural_risk"]  # >0  second 

    # （，）
    abs_gap_final = abs(gap_final)
    abs_gap_risk = abs(gap_risk)

    #  1： – best 
    if gap_final > 0.05 and gap_risk >= 0.1:
        return 0.1

    #  2：， → 
    if abs_gap_final < 0.03 and abs_gap_risk < 0.05:
        return 0.5

    #  3：second  best， → 
    if gap_risk < -0.1 and gap_final < 0.02:
        return 0.8

    # ：
    return 0.3


def _check_pairwise_consistency(candidates: List[Dict[str, Any]]) -> List[str]:
    """
     pairwise consistency：

     (i, j) ，：
    - A.FR identity  B
    -  A.final_score  B

    ，。
    """
    issues: List[str] = []

    n = len(candidates)
    for i in range(n):
        a = candidates[i]
        sa = _get_scores_view(a)
        for j in range(i + 1, n):
            b = candidates[j]
            sb = _get_scores_view(b)

            # A  B  FR  & final 
            fr_diff = sa["fr_identity"] - sb["fr_identity"]
            final_diff = sa["final"] - sb["final"]

            # ：A.FR ， final 
            if fr_diff > 0.05 and final_diff < -0.02:
                a_id = a.get("template_id") or a.get("id") or f"#{i+1}"
                b_id = b.get("template_id") or b.get("id") or f"#{j+1}"
                issues.append(
                    (
                        f"Template {a_id} has higher FR identity ({sa['fr_identity']:.2f}) than {b_id} "
                        f"({sb['fr_identity']:.2f}), but a lower final_score "
                        f"({sa['final']:.3f} vs {sb['final']:.3f}) — possible ranking inconsistency; "
                        "manually review."
                    )
                )

    return issues


def calibrate_score_consistency(
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
     isotonic regression  final_score 。

    ：
    -  combined_score ， final_score 
    -  QA  debug， pipeline
    """
    if len(candidates) < 3:
        return {"calibrated": False, "reason": "insufficient_data"}

    combined_scores: List[float] = []
    final_scores: List[float] = []

    for cand in candidates:
        s = _get_scores_view(cand)
        combined_scores.append(s["combined"])
        final_scores.append(s["final"])

    x = np.array(combined_scores, dtype=float)
    y = np.array(final_scores, dtype=float)

    #  combined_score ， isotonic，
    if np.allclose(x, x[0]):
        return {"calibrated": False, "reason": "degenerate_combined_scores"}

    #  combined_score 
    order = np.argsort(x)
    x_sorted = x[order]
    y_sorted = y[order]

    #  PAV （pool-adjacent-violators）
    y_iso = _pav_isotonic_regression(y_sorted)

    # ：combined ，y_iso （""，）
    is_monotonic = bool(np.all(y_iso[:-1] <= y_iso[1:] + 1e-8))

    return {
        "calibrated": True,
        "is_monotonic": is_monotonic,
        "sorted_combined_scores": x_sorted.tolist(),
        "sorted_final_scores": y_sorted.tolist(),
        "calibrated_scores": y_iso.tolist(),
    }


def _pav_isotonic_regression(y: np.ndarray) -> np.ndarray:
    """
    Pool-Adjacent-Violators (PAV) （）。

    ：
        y:  y （ x ）

    ：
        y_iso: 
    """
    n = len(y)
    y_iso = y.astype(float).copy()
    weights = np.ones(n, dtype=float)

    i = 0
    while i < n - 1:
        if y_iso[i] > y_iso[i + 1] + 1e-12:
            #  violation，pool 
            total_weight = weights[i] + weights[i + 1]
            avg = (weights[i] * y_iso[i] + weights[i + 1] * y_iso[i + 1]) / total_weight
            y_iso[i] = avg
            y_iso[i + 1] = avg
            weights[i] = total_weight
            weights[i + 1] = total_weight

            # ， violation
            j = i
            while j > 0 and y_iso[j - 1] > y_iso[j] + 1e-12:
                total_weight = weights[j - 1] + weights[j]
                avg = (weights[j - 1] * y_iso[j - 1] + weights[j] * y_iso[j]) / total_weight
                y_iso[j - 1] = avg
                y_iso[j] = avg
                weights[j - 1] = total_weight
                weights[j] = total_weight
                j -= 1
        i += 1

    return y_iso
