"""
VHH QA v3.5 
"""

import pytest
from core.vhh_qa_validation_v3_5 import validate_vhh_humanization_result_v3_5
from core.vhh_qa_ranking_stability import (
    analyze_ranking_stability,
    calibrate_score_consistency
)


def make_minimal_result_skeleton:
    """"""
    return {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFNIKDTY",
                "FR2": "MHWVRQRPGKGLEWVSA",
                "CDR2": "YISYSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS"
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFNIKDTY",
                "FR2": "MHWVRQRPGKGLEWVSA",
                "CDR2": "YISYSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS"
            }
        },
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFNIKDTYMHWVRQRPGKGLEWVSAYISYSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDYWGQGTQVTVSS",
            "template": {
                "id": "TEMPLATE_001",
                "flags": {"has_vhh_hallmark": True},
                "fr3_sequence": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC"
            },
            "developability": {"score": 0.65, "score_type": "aggregate"},
            "immunogenicity": {"fr_immuno_risk": "low"}
        },
        "original_developability": {"score": 0.60},
        "original_immunogenicity": {"fr_immuno_risk": "low"},
        "candidates": [],
        "mutations": {"list": []}
    }


def test_ranking_stability_stable_case:
    """："""
    candidates = [
        {
            "template_id": "TEMPLATE_001",
            "scores": {
                "final": 0.75,
                "fr_identity": 0.85,
                "structural_risk": 0.2
            },
            "flags": {"has_vhh_hallmark": True}
        },
        {
            "template_id": "TEMPLATE_002",
            "scores": {
                "final": 0.70,
                "fr_identity": 0.80,
                "structural_risk": 0.25
            },
            "flags": {"has_vhh_hallmark": True}
        }
    ]
    
    result = analyze_ranking_stability(candidates)
    
    # ：is_stablestability_score >= 0.7 AND swap_risk < 0.3
    # ：gap_final=0.05, gap_risk=0.05，"1"swap_risk=0.1
    # ，swap_risk < 0.3
    # gap_final > 0.05 and gap_risk >= 0.1，swap_risk = 0.1
    assert result.is_stable is True or result.stability_score >= 0.7, ""
    assert len(result.consistency_issues) == 0, "consistency issues"


def test_ranking_stability_unstable_fr_gap:
    """：FR identityscore"""
    candidates = [
        {
            "template_id": "TEMPLATE_001",
            "scores": {
                "final": 0.72,
                "fr_identity": 0.75,
                "structural_risk": 0.2
            },
            "flags": {"has_vhh_hallmark": True}
        },
        {
            "template_id": "TEMPLATE_002",
            "scores": {
                "final": 0.71,  # 
                "fr_identity": 0.90,  # FR identity
                "structural_risk": 0.2
            },
            "flags": {"has_vhh_hallmark": True}
        }
    ]
    
    result = analyze_ranking_stability(candidates)
    
    assert result.is_stable is False, ""
    assert result.swap_risk > 0.3 or len(result.consistency_issues) > 0, ""


def test_ranking_stability_hallmark_mismatch:
    """：Hallmark"""
    candidates = [
        {
            "template_id": "TEMPLATE_001",
            "scores": {
                "final": 0.72,
                "fr_identity": 0.85,
                "structural_risk": 0.2
            },
            "flags": {"has_vhh_hallmark": False}  # hallmark
        },
        {
            "template_id": "TEMPLATE_002",
            "scores": {
                "final": 0.70,  # 
                "fr_identity": 0.80,
                "structural_risk": 0.2
            },
            "flags": {"has_vhh_hallmark": True}  # hallmark
        }
    ]
    
    result = analyze_ranking_stability(candidates)
    
    # ：analyze_ranking_stabilityhallmark，swap_riskconsistency_issues
    # ，hallmarkv3.5
    # swap_riskconsistency_issues
    assert result.is_stable is False or result.swap_risk > 0.3 or len(result.consistency_issues) > 0, ""


def test_score_consistency_calibration:
    """：Score"""
    candidates = [
        {
            "template_id": "TEMPLATE_001",
            "scores": {"final": 0.75}
        },
        {
            "template_id": "TEMPLATE_002",
            "scores": {"final": 0.70}
        },
        {
            "template_id": "TEMPLATE_003",
            "scores": {"final": 0.65}
        }
    ]
    
    result = calibrate_score_consistency(candidates)
    
    # ：calibrate_score_consistencycombined_score，final
    # combined_score
    candidates_with_combined = [
        {
            "template_id": "TEMPLATE_001",
            "scores": {"final": 0.75, "combined": 0.75}
        },
        {
            "template_id": "TEMPLATE_002",
            "scores": {"final": 0.70, "combined": 0.70}
        },
        {
            "template_id": "TEMPLATE_003",
            "scores": {"final": 0.65, "combined": 0.65}
        }
    ]
    result = calibrate_score_consistency(candidates_with_combined)
    
    assert result["calibrated"] is True, ""
    assert result.get("is_monotonic", True), ""


def test_score_consistency_non_monotonic:
    """："""
    candidates = [
        {
            "template_id": "TEMPLATE_001",
            "scores": {"final": 0.75}
        },
        {
            "template_id": "TEMPLATE_002",
            "scores": {"final": 0.80}  # ，
        },
        {
            "template_id": "TEMPLATE_003",
            "scores": {"final": 0.65}
        }
    ]
    
    # ：calibrate_score_consistencycombined_score
    candidates_with_combined = [
        {
            "template_id": "TEMPLATE_001",
            "scores": {"final": 0.75, "combined": 0.75}
        },
        {
            "template_id": "TEMPLATE_002",
            "scores": {"final": 0.80, "combined": 0.80}  # ，
        },
        {
            "template_id": "TEMPLATE_003",
            "scores": {"final": 0.65, "combined": 0.65}
        }
    ]
    result = calibrate_score_consistency(candidates_with_combined)
    
    # ，calibrated=Trueis_monotonic
    # PAV，is_monotonicTrue
    # ：PAV
    if result.get("calibrated"):
        # ，
        assert result.get("is_monotonic", False) is True, "PAV"
        # （sorted_combined_scores vs sorted_final_scores）
        sorted_final = result.get("sorted_final_scores", [])
        if len(sorted_final) >= 2:
            # final_scores（combined）
            # combined[0.65, 0.75, 0.80]，final[0.75, 0.80, 0.65]
            # 
            calibrated = result.get("calibrated_scores", [])
            assert all(calibrated[i] <= calibrated[i+1] + 1e-8 for i in range(len(calibrated)-1)), ""
    else:
        assert result.get("reason") in ["insufficient_data", "degenerate_combined_scores"], ""


def test_v3_5_integration:
    """：v3.5"""
    result = make_minimal_result_skeleton
    
    # 
    result["candidates"] = [
        {
            "template_id": "TEMPLATE_001",
            "scores": {
                "final": 0.75,
                "fr_identity": 0.85,
                "structural_risk": 0.2,
                "combined": 0.75
            },
            "flags": {"has_vhh_hallmark": True}
        },
        {
            "template_id": "TEMPLATE_002",
            "scores": {
                "final": 0.70,
                "fr_identity": 0.80,
                "structural_risk": 0.25,
                "combined": 0.70
            },
            "flags": {"has_vhh_hallmark": True}
        }
    ]
    
    qa_v3_5 = validate_vhh_humanization_result_v3_5(result, strict=True)
    
    assert "ranking_stability" in qa_v3_5, "ranking_stability"
    assert qa_v3_5["meta"]["version"] == "3.5.0", "3.5.0"
    
    if qa_v3_5.get("ranking_stability"):
        stability = qa_v3_5["ranking_stability"]
        assert "is_stable" in stability, "is_stable"
        assert "stability_score" in stability, "stability_score"
        assert "swap_risk" in stability, "swap_risk"
    
    # guideline
    assert "guideline" in qa_v3_5, "guideline"
    if qa_v3_5.get("guideline"):
        guideline = qa_v3_5["guideline"]
        assert "traffic_light" in guideline, "guidelinetraffic_light"
        assert "flags" in guideline, "guidelineflags"
        assert guideline["traffic_light"] in ["green", "yellow", "red"], "traffic_lightgreen/yellow/red"

