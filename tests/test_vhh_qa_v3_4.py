"""
VHH QA v3.4 
"""

import pytest
from core.vhh_qa_validation_v3_4 import (
    validate_vhh_humanization_result_v3_4,
    compute_final_score_v3_4
)
from core.vhh_qa_data_calibration import VHHDataCalibration
from core.vhh_qa_structural_risk_layered import (
    compute_layered_structural_risk,
    StructuralRiskComponents
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


def test_cdr3_anchor_risk_high_should_fail:
    """：CDR3 anchor >= 0.7 fail"""
    result = make_minimal_result_skeleton
    
    # FR3101/102，
    fr3_list = list(result["sequence_analysis"]["humanized_regions"]["FR3"])
    # FR3IMGT 66，101-66=35, 102-66=36
    if len(fr3_list) > 36:
        fr3_list[35] = "X"  # 101
        fr3_list[36] = "Y"  # 102
    result["sequence_analysis"]["humanized_regions"]["FR3"] = "".join(fr3_list)
    
    qa_v3_4 = validate_vhh_humanization_result_v3_4(result, strict=True)
    
    assert qa_v3_4["ok"] is False, "CDR3 anchor>=0.7fail"
    assert len(qa_v3_4["errors"]) > 0, "error"
    assert any("CDR3 anchor" in e for e in qa_v3_4["errors"]), "CDR3 anchorerror"


def test_hallmark_penalty_applied:
    """：hallmarkhallmark_penalty"""
    candidate = {
        "scores": {
            "combined": 0.70,
            "structural_risk": 0.3
        },
        "flags": {"has_vhh_hallmark": False},
        "template": {"flags": {}}
    }
    
    final_score = compute_final_score_v3_4(candidate, calibration=None)
    
    # hallmark_penalty (0.15)
    expected_final = 0.70 - 0.20 * 0.3 - 0.15
    assert abs(final_score - expected_final) < 0.01, f"Final scorehallmark penalty: {final_score} vs {expected_final}"


def test_calibration_weights_applied:
    """：calibration，structural_risk_weight"""
    candidate = {
        "scores": {
            "combined": 0.70,
            "structural_risk": 0.3
        },
        "flags": {"has_vhh_hallmark": True},
        "template": {"flags": {}}
    }
    
    # 
    final_score_default = compute_final_score_v3_4(candidate, calibration=None)
    
    # （，，）
    calibration = VHHDataCalibration(calibration_db_path=None)
    final_score_calibrated = compute_final_score_v3_4(candidate, calibration=calibration)
    
    # ，
    assert abs(final_score_default - final_score_calibrated) < 0.01, ""


def test_layered_structural_risk_components:
    """："""
    orig_regions = {
        "FR2": "MHWVRQRPGKGLEWVSA",
        "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC"
    }
    hum_regions = {
        "FR2": "MHWVRQRPGKGLEWVSA",
        "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC"
    }
    
    risk_components = compute_layered_structural_risk(orig_regions, hum_regions)
    
    assert isinstance(risk_components, StructuralRiskComponents)
    assert 0 <= risk_components.fr2_hydrophilic_patch_risk <= 1
    assert 0 <= risk_components.grafting_interface_risk <= 1
    assert 0 <= risk_components.cdr3_anchor_risk <= 1
    assert 0 <= risk_components.total_risk <= 1
    assert "total_risk" in risk_components.to_dict


def test_structural_risk_components_in_result:
    """：structural_risk_components"""
    result = make_minimal_result_skeleton
    
    qa_v3_4 = validate_vhh_humanization_result_v3_4(result, strict=True)
    
    assert "structural_risk_components" in qa_v3_4, "structural_risk_components"
    components = qa_v3_4["structural_risk_components"]
    assert "fr2_hydrophilic_patch_risk" in components
    assert "grafting_interface_risk" in components
    assert "cdr3_anchor_risk" in components
    assert "total_risk" in components

















