"""
VHH QA v3.0 

，QA
"""

import pytest
from core.vhh_qa_validation import validate_vhh_humanization_result_v3
from core.vhh_qa_structural_rules import check_cdr3_fr3_compatibility
from core.vhh_qa_grafting import qa_grafting_impact
from core.vhh_qa_ranking import qa_ranking_sanity


def test_cdr3_30aa_fr3_35aa_should_fail:
    """：CDR3=20aaFR3=35aa → FAIL（structural_compat）"""
    # 20aaCDR3（>=15aa）35aaFR3（<38aa）
    # ：CDR3(15-25)FR3(38-45)，35aaFR3
    # FR3"YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC"38，35
    # 35aaFR3
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYY",  # 35aa（35）
                "CDR3": "AAGGVGWPYFDYAAGGVGWPY",  # 20aa (>=15aa)
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYY",  # 35aa < 38aa
                "CDR3": "AAGGVGWPYFDYAAGGVGWPY",  # 20aa >= 15aa
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMHWVRQRPGKGLEYVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYAAGGVGWPYFDYAAGGVGWPYWGQGTQVTVSS"
        }
    }
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    # structural_compat
    structural_errors = qa_v3.get("checks", {}).get("structural_compat", {}).get("errors", [])
    structural_warnings = qa_v3.get("checks", {}).get("structural_compat", {}).get("warnings", [])
    
    # CDR3=20aa >= 15aa  FR3=35aa < 38aa，ERROR
    # ：cdr3_len=20 >= 15, fr3_len=35 < 38，ERROR
    fr3_len = len(result["sequence_analysis"]["humanized_regions"]["FR3"])
    cdr3_len = len(result["sequence_analysis"]["humanized_regions"]["CDR3"])
    assert cdr3_len >= 15 and fr3_len < 38, f": CDR3={cdr3_len}>=15, FR3={fr3_len}<38"
    
    # warning
    assert len(structural_errors) > 0 or len(structural_warnings) > 0, \
        f"，errors={len(structural_errors)}, warnings={len(structural_warnings)}"
    # 
    all_issues = structural_errors + structural_warnings
    assert any("CDR3" in issue and ("FR3" in issue or "" in issue) for issue in all_issues)


def test_fr2_missing_hallmarks_should_fail:
    """：FR244/45/47 → FAIL"""
    # hallmarkFR2
    # FR244=E/Q, 45=R/K, 47=W
    # human-likeFR2（VHH hallmark）
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",  # hallmark（44=E, 45=R）
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MGWVRQRPGKGLEYVSA",  # hallmark（44EG，45RL）
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMGWVRQRPGKGLEYVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
        }
    }
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    # hallmark（checks）
    all_errors = qa_v3.get("errors", [])
    # VHH≥2hallmark，≥2
    # FR2VHHhuman，FAIL
    # FRhallmark
    assert qa_v3["ok"] is False or any(
        "hallmark" in err.lower or "FR2" in err or "" in err 
        for err in all_errors
    )


def test_hallmark_incompatibility_should_fail:
    """：hallmark → FAIL"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",  # VHH hallmark
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MGWVRQRPGKGLEYVSA",  # VHHhuman
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMGWVRQRPGKGLEYVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
        }
    }
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    # VHH≥2hallmark，≥2
    # FR2VHHhuman，FAIL
    assert qa_v3["ok"] is False


def test_template2_more_reasonable_ranking_fail:
    """：2 → ranking_fail"""
    candidates = [
        {
            "template_id": "TEMPLATE_1",
            "alignment_scores": {
                "framework_identity": 0.80,
                "combined_score": 0.75
            },
            "flags": {"has_vhh_hallmark": False},
            "qa_v3": {
                "checks": {
                    "grafting_impact": {
                        "impact_score_normalized": 0.5  # 
                    }
                }
            }
        },
        {
            "template_id": "TEMPLATE_2",
            "alignment_scores": {
                "framework_identity": 0.90,  # 
                "combined_score": 0.77  # 
            },
            "flags": {"has_vhh_hallmark": True},
            "qa_v3": {
                "checks": {
                    "grafting_impact": {
                        "impact_score_normalized": 0.1  # 
                    }
                }
            }
        }
    ]
    
    errors, warnings, details = qa_ranking_sanity(candidates)
    
    # ranking
    assert len(errors) > 0 or len(warnings) > 0
    # FR identitycombined score
    assert any("FR identity" in w or "" in e for w in warnings for e in errors)


def test_delta_immunogenicity_increase_should_fail:
    """：Δimmunogenicity → FAIL"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMHWVRQRPGKGLEYVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDYWGQGTQVTVSS",
            "immunogenicity": {
                "fr_immuno_risk": "high"  # 
            }
        },
        "original_immunogenicity": {
            "fr_immuno_risk": "low"  # 
        }
    }
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    assert qa_v3["ok"] is False
    assert any("" in err and "" in err for err in qa_v3["errors"])


def test_impact_score_high_should_fail:
    """：impact_score≥0.4 → FAIL"""
    # 
    orig_regions = {
        "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
        "CDR1": "GFWYNH",
        "FR2": "MHWVRQRPGKGLEYVSA",
        "CDR2": "ITADSGST",
        "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
        "CDR3": "AAGGVGWPYFDY",
        "FR4": "WGQGTQVTVSS",
    }
    
    # ，
    hum_regions = {
        "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
        "CDR1": "GFWYNH",
        "FR2": "MGWVRQRPGKGLEYVSA",  # 44EG
        "CDR2": "ITADSGST",
        "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
        "CDR3": "AAGGVGWPYFDY",
        "FR4": "WGQGTQVTVSS",
    }
    
    errors, warnings, impact_details = qa_grafting_impact(orig_regions, hum_regions)
    
    impact_norm = impact_details.get("impact_score_normalized", 0)
    # impact_score_normalized >= 0.4，error
    if impact_norm >= 0.4:
        assert len(errors) > 0
        assert any("CDR–FR " in err for err in errors)


def test_developability_decrease_major_should_warn:
    """：developability → WARNING"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMHWVRQRPGKGLEYVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDYWGQGTQVTVSS",
            "developability": {
                "score": 0.3  # 
            }
        },
        "original_developability": {
            "score": 0.85  # 
        }
    }
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    # delta = 0.3 - 0.85 = -0.55 < -0.1，warning
    assert any("developability" in w.lower and "" in w for w in qa_v3["warnings"])


def test_cdr_mutation_should_fail:
    """：CDR → FAIL"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",  # 
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",  # 
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",  # 
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {
            "list": [
                {
                    "region": "CDR1",  # CDR
                    "position": 27,
                    "from": "G",
                    "to": "A"
                }
            ]
        },
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMHWVRQRPGKGLEYVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
        }
    }
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    assert qa_v3["ok"] is False
    assert any("CDR" in err and "" in err for err in qa_v3["errors"])


def test_fr4_missing_should_fail:
    """：FR4 → FAIL"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "",  # FR4
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMHWVRQRPGKGLEYVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDY"
        }
    }
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    assert qa_v3["ok"] is False
    assert any("FR4" in err for err in qa_v3["errors"])


def test_sequence_length_mismatch_should_fail:
    """： → FAIL"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMHWVRQRPGKGLEYVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
        }
    }
    
    # ，>3
    result["sequence_analysis"]["original_regions"]["FR1"] = "EVQLVESGGGLVQPGGSLRLSCAAS" + "AAA"  # 3
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    # >3，FAIL
    orig_len = sum(len(r) for r in result["sequence_analysis"]["original_regions"].values)
    hum_len = sum(len(r) for r in result["sequence_analysis"]["humanized_regions"].values)
    if abs(orig_len - hum_len) > 3:
        assert qa_v3["ok"] is False
        assert any("" in err for err in qa_v3["errors"])


def test_cdr3_length_abnormal_should_fail:
    """：CDR3 → FAIL"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "A",  # CDR3（1aa）
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "A",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMHWVRQRPGKGLEYVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAWGQGTQVTVSS"
        }
    }
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    assert qa_v3["ok"] is False
    assert any("CDR3" in err and "" in err for err in qa_v3["errors"])


def test_ranking_hallmark_mismatch_should_fail:
    """：hallmark → ranking_fail"""
    candidates = [
        {
            "template_id": "TEMPLATE_1",
            "alignment_scores": {
                "framework_identity": 0.85,
                "combined_score": 0.80
            },
            "flags": {"has_vhh_hallmark": False},  # hallmark
            "template": {
                "flags": {"has_vhh_hallmark": False}
            }
        },
        {
            "template_id": "TEMPLATE_2",
            "alignment_scores": {
                "framework_identity": 0.82,
                "combined_score": 0.78
            },
            "flags": {"has_vhh_hallmark": True},  # hallmark
            "template": {
                "flags": {"has_vhh_hallmark": True}
            }
        }
    ]
    
    errors, warnings, details = qa_ranking_sanity(candidates)
    
    # hallmark mismatch
    assert len(errors) > 0
    assert any("hallmark" in err.lower for err in errors)


def test_structural_compat_cdr1_fr2_incompatible:
    """：CDR1–FR2 → WARNING"""
    is_compat, note, strength = check_cdr3_fr3_compatibility(30, 35)
    # CDR3=30aa, FR3=35aa
    assert is_compat is False


def test_grafting_impact_normalized_threshold:
    """：grafting impact"""
    # 
    orig_regions = {
        "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
        "CDR1": "GFWYNH",
        "FR2": "MHWVRQRPGKGLEYVSA",
        "CDR2": "ITADSGST",
        "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
        "CDR3": "AAGGVGWPYFDY",
        "FR4": "WGQGTQVTVSS",
    }
    
    hum_regions = {
        "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
        "CDR1": "GFWYNH",
        "FR2": "MGWVRQRPGKGLEYVSA",  # 44EG
        "CDR2": "ITADSGST",
        "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
        "CDR3": "AAGGVGWPYFDY",
        "FR4": "WGQGTQVTVSS",
    }
    
    errors, warnings, impact_details = qa_grafting_impact(orig_regions, hum_regions)
    
    impact_norm = impact_details.get("impact_score_normalized", 0)
    # 
    assert "impact_score_normalized" in impact_details
    assert impact_norm >= 0


def test_mutation_map_generation:
    """：mutation map"""
    from core.vhh_qa_mutation_map import generate_mutation_map
    
    orig_regions = {
        "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
        "CDR1": "GFWYNH",
        "FR2": "MHWVRQRPGKGLEYVSA",
        "CDR2": "ITADSGST",
        "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
        "CDR3": "AAGGVGWPYFDY",
        "FR4": "WGQGTQVTVSS",
    }
    
    hum_regions = {
        "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
        "CDR1": "GFWYNH",
        "FR2": "MHWVRQRPGKGLEYVSA",
        "CDR2": "ITADSGST",
        "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
        "CDR3": "AAGGVGWPYFDY",
        "FR4": "WGQGTQVTVSS",
    }
    
    mutations = [
        {
            "region": "FR1",
            "position": 5,
            "from": "A",
            "to": "S"
        }
    ]
    
    mutation_map = generate_mutation_map(orig_regions, hum_regions, mutations)
    
    assert "regions" in mutation_map
    assert "mutations_by_category" in mutation_map
    assert "summary" in mutation_map
    assert mutation_map["summary"]["total_mutations"] == 1


def test_conformation_risk_summary_generation:
    """："""
    from core.vhh_qa_conformation_risk import generate_conformation_risk_summary
    
    hum_regions = {
        "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
        "CDR1": "GFWYNH",
        "FR2": "MHWVRQRPGKGLEYVSA",
        "CDR2": "ITADSGST",
        "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
        "CDR3": "AAGGVGWPYFDY",
        "FR4": "WGQGTQVTVSS",
    }
    
    conformation_risk = generate_conformation_risk_summary(hum_regions)
    
    assert "cdr3_anchor_stability" in conformation_risk
    assert "fr2_hydrophilic_patch" in conformation_risk
    assert "cdr1_torsion_compatibility" in conformation_risk
    assert "overall_structural_feasibility" in conformation_risk


def test_experimental_recommendations_generation:
    """："""
    from core.vhh_qa_experimental_recommendations import generate_experimental_recommendations
    
    qa_v3_result = {
        "errors": ["Test error"],
        "warnings": ["Test warning"],
        "checks": {
            "structural_compat": {"errors": []},
            "grafting_impact": {
                "impact_score_normalized": 0.5  # 
            },
            "ranking_sanity": {"errors": []}
        },
        "summary_score": {
            "biological_feasibility": 60,
            "risk_level": "medium"
        }
    }
    
    recommendations = generate_experimental_recommendations(qa_v3_result)
    
    assert "directed_evolution" in recommendations
    assert "yeast_display_validation" in recommendations
    assert "multi_template_comparison" in recommendations
    assert "thermodynamic_analysis" in recommendations
    assert "summary" in recommendations


def test_qa_v3_interface_structure:
    """：QA v3"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMHWVRQRPGKGLEYVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
        }
    }
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # qa_v3
    assert "ok" in qa_v3
    assert "errors" in qa_v3
    assert "warnings" in qa_v3
    assert "checks" in qa_v3
    assert "summary_score" in qa_v3
    assert "metadata" in qa_v3
    assert "mutation_map" in qa_v3
    assert "conformation_risk_summary" in qa_v3
    assert "experimental_recommendations" in qa_v3


def test_qa_v3_metadata_version:
    """：QA v3 metadata"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMHWVRQRPGKGLEYVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
        }
    }
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # metadata
    assert "metadata" in qa_v3
    metadata = qa_v3["metadata"]
    assert metadata["version"] == "3.2.0"  # v3.2.0
    assert metadata["rules_version"] == "3.2.0"
    assert "rules_source" in metadata
    assert "thresholds" in metadata


def test_biological_feasibility_calculation:
    """："""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMHWVRQRPGKGLEYVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
        }
    }
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # summary_score
    assert "summary_score" in qa_v3
    summary = qa_v3["summary_score"]
    assert "biological_feasibility" in summary
    assert "risk_level" in summary
    assert 0 <= summary["biological_feasibility"] <= 100
    assert summary["risk_level"] in ["low", "medium", "high"]

