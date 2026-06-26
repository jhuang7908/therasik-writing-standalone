"""
VHH QA
"""

import pytest
from core.vhh_qa_validation import (
    rebuild_v_region_from_regions,
    validate_vhh_humanization_result,
    V_REGION_ORDER
)


def test_rebuild_v_region_includes_fr4:
    """FR4"""
    regions = {
        "FR1": "AAAA",
        "CDR1": "BBBB",
        "FR2": "CCCC",
        "CDR2": "DDDD",
        "FR3": "EEEE",
        "CDR3": "FFFF",
        "FR4": "GGGG",
    }
    seq = rebuild_v_region_from_regions(regions)
    assert seq == "AAAABBBBCCCCDDDDEEEEFFFFGGGG"
    assert len(seq) == 28
    assert seq.endswith("GGGG")  # FR4


def test_rebuild_v_region_missing_fr4:
    """FR4"""
    regions = {
        "FR1": "AAAA",
        "CDR1": "BBBB",
        "FR2": "CCCC",
        "CDR2": "DDDD",
        "FR3": "EEEE",
        "CDR3": "FFFF",
        # FR4
    }
    seq = rebuild_v_region_from_regions(regions)
    # FR4
    assert seq == "AAAABBBBCCCCDDDDEEEEFFFF"


def test_rebuild_v_region_empty_regions:
    """"""
    regions = {
        "FR1": "",
        "CDR1": "",
        "FR2": "",
        "CDR2": "",
        "FR3": "",
        "CDR3": "",
        "FR4": "",
    }
    seq = rebuild_v_region_from_regions(regions)
    assert seq == ""


def test_rebuild_v_region_none_values:
    """None"""
    regions = {
        "FR1": "AAAA",
        "CDR1": None,
        "FR2": "CCCC",
        "CDR2": "DDDD",
        "FR3": "EEEE",
        "CDR3": "FFFF",
        "FR4": "GGGG",
    }
    seq = rebuild_v_region_from_regions(regions)
    # None
    assert seq == "AAAACCCCDDDDEEEEFFFFGGGG"


def test_validate_vhh_humanization_result_fr4_missing:
    """QAFR4"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "AAAA",
                "CDR1": "BBBB",
                "FR2": "CCCC",
                "CDR2": "DDDD",
                "FR3": "EEEE",
                "CDR3": "FFFF",
                "FR4": "GGGG",
            },
            "humanized_regions": {
                "FR1": "AAAA",
                "CDR1": "BBBB",
                "FR2": "CCCC",
                "CDR2": "DDDD",
                "FR3": "EEEE",
                "CDR3": "FFFF",
                "FR4": "",  # FR4
            }
        },
        "mutations": {
            "list": []
        },
        "best_match": {
            "humanized_sequence": "AAAABBBBCCCCDDDDEEEEFFFF"
        }
    }
    
    qa_result = validate_vhh_humanization_result(result, strict=True)
    assert not qa_result["ok"]
    assert any("FR4" in err for err in qa_result["errors"])


def test_validate_vhh_humanization_result_cdr_mutation:
    """QACDR"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "AAAA",
                "CDR1": "BBBB",
                "FR2": "CCCC",
                "CDR2": "DDDD",
                "FR3": "EEEE",
                "CDR3": "FFFF",
                "FR4": "GGGG",
            },
            "humanized_regions": {
                "FR1": "AAAA",
                "CDR1": "BBBB",
                "FR2": "CCCC",
                "CDR2": "DDDD",
                "FR3": "EEEE",
                "CDR3": "FFFF",
                "FR4": "GGGG",
            }
        },
        "mutations": {
            "list": [
                {
                    "position": 30,
                    "from": "B",
                    "to": "X",
                    "region": "CDR1"  # CDR
                }
            ]
        },
        "best_match": {
            "humanized_sequence": "AAAABXBBCCCCDDDDEEEEFFFFGGGG"
        }
    }
    
    qa_result = validate_vhh_humanization_result(result, strict=True)
    assert not qa_result["ok"]
    assert any("CDR" in err and "" in err for err in qa_result["errors"])


def test_validate_vhh_humanization_result_success:
    """QA"""
    # ，VHH hallmark
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",  # 26aa
                "CDR1": "GFWYNH",  # 6aa
                "FR2": "MHWVRQRPGKGLEYVSA",  # 17aa, VHH hallmark: Q(44), R(45), W(47)
                "CDR2": "ITADSGST",  # 8aa
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",  # 39aa
                "CDR3": "AAGGVGWPYFDY",  # 12aa
                "FR4": "WGQGTQVTVSS",  # 11aa
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",  # 
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",  # VHH hallmark
                "CDR2": "ITADSGST",
                "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {
            "list": []  # ，
        },
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMHWVRQRPGKGLEYVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDYWGQGTQVTVSS",
            "scoring": {
                "framework_identity": 0.95
            },
            "cdr_compatibility": {
                "compatibility_score": 0.9
            }
        }
    }
    
    qa_result = validate_vhh_humanization_result(result, strict=True)
    assert qa_result["ok"]
    assert len(qa_result["errors"]) == 0


def test_validate_vhh_humanization_result_fallback_warning:
    """fallback - warning"""
    # VHH hallmarkFR2
    # FR2: IMGT 39-55, hallmark: 44=E/Q, 45=R/K, 47=W
    # "MGWFRQAPGKEREGVAV" -> hallmark: "MGWFRQAPGKEREGVAV" -> "MGWFRQAPGKEREGVAV"
    # ：5E/Q (IMGT 44), 6R/K (IMGT 45), 8W (IMGT 47)
    # "MGWFRQAPGKEREGVAV" ：5=Q(✓), 6=A(✗R/K), 8=P(✗W)
    # : "MGWFRQAPGKEREGVAV" -> "MGWFRQAPGKEREGVAV" (Q, AR, PW)
    # ，hallmark
    # : "MHWVRQRPGKGLEYVSA" - 5=Q, 6=R, 8=W (VHH)
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",  # VHH hallmark: Q(44), R(45), W(47)
                "CDR2": "ITADSGST",
                "FR3": "TYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MHWVRQRPGKGLEYVSA",  # VHH hallmark
                "CDR2": "ITADSGST",
                "FR3": "TYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHMHWVRQRPGKGLEYVSAITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS",
            "template": {
                "flags": {
                    "uses_fallback_numbering": True,
                    "uses_fallback_fr2": False,
                }
            }
        },
        "quality_flags": {}
    }
    
    qa = validate_vhh_humanization_result(result, strict=True)
    assert qa["ok"] is True  # fallbackwarning，
    assert any("fallback" in w.lower for w in qa["warnings"])


def test_validate_vhh_humanization_result_fr_mutations_mismatch:
    """FR - error"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MGWFRQAPGKEREGVAV",
                "CDR2": "ITADSGST",
                "FR3": "TYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "AVQLVESGGGLVQPGGSLRLSCAAS",  # 0: E->A (1)
                "CDR1": "GFWYNH",
                "FR2": "MGWFRQAPGKEREGVAV",
                "CDR2": "ITADSGST",
                "FR3": "TYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {
            "list": [
                {"region": "FR1", "position": 1, "from": "E", "to": "A"},
                {"region": "FR1", "position": 3, "from": "Q", "to": "X"},  # 
            ]
        },
        "best_match": {
            "humanized_sequence": "AVQLVESGGGLVQPGGSLRLSCAASGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
        }
    }
    
    qa = validate_vhh_humanization_result(result, strict=True)
    assert qa["ok"] is False
    # FR
    assert any(
        "FR " in e or 
        "" in e or 
        "" in e or
        "" in e
        for e in qa["errors"]
    )


def test_validate_vhh_humanization_result_sequence_inconsistency:
    """full_sequencerebuilt - error"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MGWFRQAPGKEREGVAV",
                "CDR2": "ITADSGST",
                "FR3": "TYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MGWFRQAPGKEREGVAV",
                "CDR2": "ITADSGST",
                "FR3": "TYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "XXXXXXXXXXXX"  # 
        }
    }
    
    qa = validate_vhh_humanization_result(result, strict=True)
    #  > 3，
    assert qa["ok"] is False
    assert any("" in e or "" in e for e in qa["errors"])


def test_validate_vhh_humanization_result_cdr_difference_error:
    """CDR - error"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MGWFRQAPGKEREGVAV",
                "CDR2": "ITADSGST",
                "FR3": "TYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYQH",  # 4: N->Q (CDR，FR-only)
                "FR2": "MGWFRQAPGKEREGVAV",
                "CDR2": "ITADSGST",
                "FR3": "TYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYQHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
        }
    }
    
    qa = validate_vhh_humanization_result(result, strict=True)
    assert qa["ok"] is False
    assert any("CDR1 " in e for e in qa["errors"])


def test_validate_vhh_humanization_result_cdr_length_mismatch:
    """CDR - error"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNH",
                "FR2": "MGWFRQAPGKEREGVAV",
                "CDR2": "ITADSGST",
                "FR3": "TYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
            "humanized_regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GFWYNHX",  # （6 vs 7）
                "FR2": "MGWFRQAPGKEREGVAV",
                "CDR2": "ITADSGST",
                "FR3": "TYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFWYNHXMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
        }
    }
    
    qa = validate_vhh_humanization_result(result, strict=True)
    assert qa["ok"] is False
    assert any("CDR1 " in e and "" in e for e in qa["errors"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

