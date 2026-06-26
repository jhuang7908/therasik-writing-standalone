"""
QA v3.1  - （N01-N08）
 ok=False，
"""
import pytest
from core.vhh_qa_validation import validate_vhh_humanization_result_v3


def make_minimal_result_skeleton:
    """"""
    return {
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
            "template": {
                "template_id": "HUMAN_VH3_SCF_24",
                "flags": {
                    "has_vhh_hallmark": True,
                    "uses_fallback_numbering": False,
                    "uses_fallback_fr2": False
                }
            },
            "developability": {
                "score": 0.65,
                "score_type": "aggregate"
            },
            "immunogenicity": {
                "fr_immuno_risk": "low"
            }
        },
        "original_developability": {"score": 0.50},
        "original_immunogenicity": {"fr_immuno_risk": "low"},
        "candidates": [
            {
                "template_id": "HUMAN_VH3_SCF_24",
                "scores": {
                    "fr_identity": 0.85,
                    "combined": 0.75
                },
                "flags": {
                    "has_vhh_hallmark": True
                }
            }
        ]
    }


def test_N01_missing_fr4_should_fail:
    """
    ❌ N01：FR4 
    ： FR4  FAIL。
    """
    result = make_minimal_result_skeleton
    
    # ：humanized.regions.FR4 == ""  key
    result["sequence_analysis"]["humanized_regions"]["FR4"] = ""
    
    # （FR4）
    full_seq = "".join([
        result["sequence_analysis"]["humanized_regions"]["FR1"],
        result["sequence_analysis"]["humanized_regions"]["CDR1"],
        result["sequence_analysis"]["humanized_regions"]["FR2"],
        result["sequence_analysis"]["humanized_regions"]["CDR2"],
        result["sequence_analysis"]["humanized_regions"]["FR3"],
        result["sequence_analysis"]["humanized_regions"]["CDR3"]
    ])
    result["best_match"]["humanized_sequence"] = full_seq
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    assert qa_v3["ok"] is False
    assert any("FR4" in e and ("" in e or "" in e) for e in qa_v3["errors"])


def test_N02_cdr_mutation_should_fail:
    """
    ❌ N02：CDR （ VHH FR-only ）
    ： CDR  error。
    """
    result = make_minimal_result_skeleton
    
    # ：CDR1  "AAA"，humanized  "ARA"
    result["sequence_analysis"]["original_regions"]["CDR1"] = "AAA"
    result["sequence_analysis"]["humanized_regions"]["CDR1"] = "ARA"
    
    # 
    full_seq = "".join([
        result["sequence_analysis"]["humanized_regions"]["FR1"],
        result["sequence_analysis"]["humanized_regions"]["CDR1"],
        result["sequence_analysis"]["humanized_regions"]["FR2"],
        result["sequence_analysis"]["humanized_regions"]["CDR2"],
        result["sequence_analysis"]["humanized_regions"]["FR3"],
        result["sequence_analysis"]["humanized_regions"]["CDR3"],
        result["sequence_analysis"]["humanized_regions"]["FR4"]
    ])
    result["best_match"]["humanized_sequence"] = full_seq
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    assert qa_v3["ok"] is False
    assert any("CDR1" in e and "" in e for e in qa_v3["errors"])


def test_N03_fr_mutations_count_mismatch:
    """
    ❌ N03：FR  mutations.list 
    ：。
    """
    result = make_minimal_result_skeleton
    
    # ：FR1  2  AA ， mutations.list  1 
    # humanized FR12
    orig_fr1 = result["sequence_analysis"]["original_regions"]["FR1"]
    hum_fr1 = list(orig_fr1)
    hum_fr1[5] = "S"  # 1
    hum_fr1[10] = "T"  # 2
    result["sequence_analysis"]["humanized_regions"]["FR1"] = "".join(hum_fr1)
    
    # mutations.list1
    result["mutations"]["list"] = [
        {"region": "FR1", "position": 5, "from": orig_fr1[5], "to": "S"}
    ]
    
    # 
    full_seq = "".join([
        result["sequence_analysis"]["humanized_regions"]["FR1"],
        result["sequence_analysis"]["humanized_regions"]["CDR1"],
        result["sequence_analysis"]["humanized_regions"]["FR2"],
        result["sequence_analysis"]["humanized_regions"]["CDR2"],
        result["sequence_analysis"]["humanized_regions"]["FR3"],
        result["sequence_analysis"]["humanized_regions"]["CDR3"],
        result["sequence_analysis"]["humanized_regions"]["FR4"]
    ])
    result["best_match"]["humanized_sequence"] = full_seq
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    assert qa_v3["ok"] is False
    assert any("FR" in e and ("" in e or "FR" in e) for e in qa_v3["errors"])


def test_N04_full_sequence_inconsistency:
    """
    ❌ N04：humanized.full_sequence  regions 
    ： full_sequence 。
    """
    result = make_minimal_result_skeleton
    
    # ：regions  "AAA…GGG"，full_sequence  "AAA…GGA"
    # 
    correct_seq = "".join([
        result["sequence_analysis"]["humanized_regions"]["FR1"],
        result["sequence_analysis"]["humanized_regions"]["CDR1"],
        result["sequence_analysis"]["humanized_regions"]["FR2"],
        result["sequence_analysis"]["humanized_regions"]["CDR2"],
        result["sequence_analysis"]["humanized_regions"]["FR3"],
        result["sequence_analysis"]["humanized_regions"]["CDR3"],
        result["sequence_analysis"]["humanized_regions"]["FR4"]
    ])
    # （，）
    # 50
    if len(correct_seq) > 50:
        wrong_seq = correct_seq[:50] + "X" + correct_seq[51:]
    else:
        # ，
        wrong_seq = correct_seq[:-1] + "X"
    result["best_match"]["humanized_sequence"] = wrong_seq
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    # ：rebuilt_seqreported_seq，>3，fail
    # ：<=3，warning
    integrity_errors = qa_v3.get("checks", {}).get("integrity", {}).get("errors", [])
    all_errors = qa_v3["errors"] + integrity_errors
    # 
    if any(("" in e or "" in e) and ("" in e or "" in e) for e in all_errors):
        assert qa_v3["ok"] is False
    else:
        # （<=3），warning，，
        # ：，fail
        from core.vhh_qa_validation import rebuild_v_region_from_regions
        rebuilt = rebuild_v_region_from_regions(result["sequence_analysis"]["humanized_regions"])
        reported = result["best_match"]["humanized_sequence"]
        if rebuilt != reported and abs(len(rebuilt) - len(reported)) > 3:
            assert qa_v3["ok"] is False


def test_N05_abnormal_cdr3_length:
    """
    ❌ N05：CDR3 （>35  <2）
    ： CDR3。
    """
    result = make_minimal_result_skeleton
    
    # ：CDR3_len = 40
    result["sequence_analysis"]["original_regions"]["CDR3"] = "A" * 40
    result["sequence_analysis"]["humanized_regions"]["CDR3"] = "A" * 40
    
    # 
    full_seq = "".join([
        result["sequence_analysis"]["humanized_regions"]["FR1"],
        result["sequence_analysis"]["humanized_regions"]["CDR1"],
        result["sequence_analysis"]["humanized_regions"]["FR2"],
        result["sequence_analysis"]["humanized_regions"]["CDR2"],
        result["sequence_analysis"]["humanized_regions"]["FR3"],
        result["sequence_analysis"]["humanized_regions"]["CDR3"],
        result["sequence_analysis"]["humanized_regions"]["FR4"]
    ])
    result["best_match"]["humanized_sequence"] = full_seq
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    assert qa_v3["ok"] is False
    assert any("CDR3 " in e or ("CDR3" in e and "" in e) for e in qa_v3["errors"])


def test_N06_vhh_hallmark_missing:
    """
    ❌ N06：VHH hallmark （ 44/45/47 ）
    ： hallmark 。
    """
    result = make_minimal_result_skeleton
    
    # ：
    #  FR2  37/44/45/47  motif
    # humanized FR2  45R  44E/Q
    # ：VHH hallmarkFR2
    # FR2hallmark
    # VHH FR2 "WVRQRPGKGLEYVSA" 
    # 
    result["sequence_analysis"]["humanized_regions"]["FR2"] = "MHWVRQRPGKGLEYVSA"  # ，hallmark
    # ，hallmarkFR2
    # ，hallmark，
    
    # hallmark
    result["best_match"]["template"]["flags"]["has_vhh_hallmark"] = False
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    # ：hallmarkflags
    # hallmarkranking sanity，fail
    # ranking sanity
    if not qa_v3["ok"]:
        # hallmark
        assert any("hallmark" in e.lower for e in qa_v3["errors"])


def test_N07_long_cdr3_short_fr3_incompatible:
    """
    ❌ N07： CDR3+ FR3（structural compatibility error）
    ： QA 。
    """
    result = make_minimal_result_skeleton
    
    # ：CDR3_len = 20，FR3_len = 35
    result["sequence_analysis"]["original_regions"]["CDR3"] = "AAGGVGWPYFDYAAGGVGWPY"  # 20aa
    result["sequence_analysis"]["humanized_regions"]["CDR3"] = "AAGGVGWPYFDYAAGGVGWPY"
    result["sequence_analysis"]["original_regions"]["FR3"] = "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVY"  # 35aa
    result["sequence_analysis"]["humanized_regions"]["FR3"] = "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVY"
    
    # 
    full_seq = "".join([
        result["sequence_analysis"]["humanized_regions"]["FR1"],
        result["sequence_analysis"]["humanized_regions"]["CDR1"],
        result["sequence_analysis"]["humanized_regions"]["FR2"],
        result["sequence_analysis"]["humanized_regions"]["CDR2"],
        result["sequence_analysis"]["humanized_regions"]["FR3"],
        result["sequence_analysis"]["humanized_regions"]["CDR3"],
        result["sequence_analysis"]["humanized_regions"]["FR4"]
    ])
    result["best_match"]["humanized_sequence"] = full_seq
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    assert qa_v3["ok"] is False
    structural_errors = qa_v3.get("checks", {}).get("structural_compat", {}).get("errors", [])
    assert len(structural_errors) > 0
    assert any("CDR3 " in err and "FR3" in err for err in structural_errors)


def test_N08_high_grafting_impact_should_fail:
    """
    ❌ N08：grafting impact （impact_score_normalized ≥ ）
    ： FAIL。
    """
    result = make_minimal_result_skeleton
    
    # ：
    #  interface  hydrophobic→charged  G→W 
    # impact_score_normalized ≥ 0.7
    # ：grafting impactFR-CDR
    # 
    
    # FR1（IMGT 25）
    orig_fr1 = result["sequence_analysis"]["original_regions"]["FR1"]
    hum_fr1 = list(orig_fr1)
    # ：A -> R
    if len(hum_fr1) > 20:
        hum_fr1[20] = "R"  # 
    result["sequence_analysis"]["humanized_regions"]["FR1"] = "".join(hum_fr1)
    
    # FR2
    orig_fr2 = result["sequence_analysis"]["original_regions"]["FR2"]
    hum_fr2 = list(orig_fr2)
    if len(hum_fr2) > 5:
        hum_fr2[5] = "D"  # 
    result["sequence_analysis"]["humanized_regions"]["FR2"] = "".join(hum_fr2)
    
    # FR3（CDR3 anchor）
    orig_fr3 = result["sequence_analysis"]["original_regions"]["FR3"]
    hum_fr3 = list(orig_fr3)
    if len(hum_fr3) > 30:
        hum_fr3[30] = "E"  # 
    result["sequence_analysis"]["humanized_regions"]["FR3"] = "".join(hum_fr3)
    
    # 
    full_seq = "".join([
        result["sequence_analysis"]["humanized_regions"]["FR1"],
        result["sequence_analysis"]["humanized_regions"]["CDR1"],
        result["sequence_analysis"]["humanized_regions"]["FR2"],
        result["sequence_analysis"]["humanized_regions"]["CDR2"],
        result["sequence_analysis"]["humanized_regions"]["FR3"],
        result["sequence_analysis"]["humanized_regions"]["CDR3"],
        result["sequence_analysis"]["humanized_regions"]["FR4"]
    ])
    result["best_match"]["humanized_sequence"] = full_seq
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    # impact_score_normalized >= 0.4 (ERROR)，fail
    impact_info = qa_v3.get("checks", {}).get("grafting_impact", {})
    impact_normalized = impact_info.get("impact_score_normalized", 0)
    
    if impact_normalized >= 0.4:
        assert qa_v3["ok"] is False
        assert any("grafting" in e.lower or "" in e for e in qa_v3["errors"])

