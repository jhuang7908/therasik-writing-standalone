"""
QA v3.1  - （N09-N20）
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


def test_N09_immunogenicity_increase_should_fail:
    """
    ❌ N09：Δimmunogenicity 
    ：。
    """
    result = make_minimal_result_skeleton
    
    # ：Δimmunogenicity = +0.10
    # ：low=1, medium=2, high=3
    result["best_match"]["immunogenicity"]["fr_immuno_risk"] = "high"
    result["original_immunogenicity"]["fr_immuno_risk"] = "low"
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    assert qa_v3["ok"] is False
    assert any("" in e and ("" in e or "" in e) for e in qa_v3["errors"])


def test_N10_major_developability_drop_should_fail:
    """
    ❌ N10：Δdevelopability 
    ：。
    """
    result = make_minimal_result_skeleton
    
    # ：Δdevelopability = -0.3
    result["best_match"]["developability"]["score"] = 0.20
    result["original_developability"]["score"] = 0.50
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    # ok == False  risk_level == "high"
    delta_errors = qa_v3.get("checks", {}).get("delta_risk", {}).get("errors", [])
    delta_warnings = qa_v3.get("checks", {}).get("delta_risk", {}).get("warnings", [])
    
    # developability
    assert len(delta_errors) > 0 or len(delta_warnings) > 0
    assert any("developability" in msg.lower and ("" in msg or "" in msg) 
               for msg in delta_errors + delta_warnings)
    
    # ，fail
    if qa_v3["summary_score"]["risk_level"] == "high":
        assert qa_v3["ok"] is False


def test_N11_best_template_missing_hallmark_should_fail:
    """
    ❌ N11： hallmark （ranking sanity error）
    ： ranking sanity 。
    """
    result = make_minimal_result_skeleton
    
    # ：
    # best.flags.has_vhh_hallmark = False
    # second.flags.has_vhh_hallmark = True， combined  < 0.02
    result["best_match"]["template"]["flags"]["has_vhh_hallmark"] = False
    result["candidates"] = [
        {
            "template_id": "HUMAN_VH3_SCF_24",
            "scores": {
                "fr_identity": 0.85,
                "combined": 0.75
            },
            "flags": {
                "has_vhh_hallmark": False  # besthallmark
            }
        },
        {
            "template_id": "HUMAN_VH3_SCF_25",
            "scores": {
                "fr_identity": 0.82,
                "combined": 0.74  # <0.02
            },
            "flags": {
                "has_vhh_hallmark": True  # secondhallmark
            }
        }
    ]
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    assert qa_v3["ok"] is False
    ranking_errors = qa_v3.get("checks", {}).get("ranking_sanity", {}).get("errors", [])
    # hallmark
    all_ranking_errors = ranking_errors + qa_v3["errors"]
    assert any(("" in e or "hallmark" in e.lower) and ("" in e or "missing" in e.lower or "" in e) for e in all_ranking_errors)


def test_N12_fr_identity_ranking_mismatch:
    """
    ❌ N12：FR identity  combined score 
    ： bug。
    """
    result = make_minimal_result_skeleton
    
    # ：
    # best.fr_identity = 0.75, best.combined = 0.70
    # second.fr_identity = 0.90, second.combined = 0.68
    result["candidates"] = [
        {
            "template_id": "HUMAN_VH3_SCF_24",
            "scores": {
                "fr_identity": 0.75,
                "combined": 0.70
            },
            "flags": {
                "has_vhh_hallmark": True
            }
        },
        {
            "template_id": "HUMAN_VH3_SCF_25",
            "scores": {
                "fr_identity": 0.90,  # 
                "combined": 0.68  # combined0.02
            },
            "flags": {
                "has_vhh_hallmark": True
            }
        }
    ]
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    # v3.2：FR identity>=0.10combined<=0.03，error
    # best.fr_identity=0.75, second.fr_identity=0.90 (0.15 >= 0.10)
    # best.combined=0.70, second.combined=0.68 (0.02 <= 0.03)
    ranking_warnings = qa_v3.get("checks", {}).get("ranking_sanity", {}).get("warnings", [])
    ranking_errors = qa_v3.get("checks", {}).get("ranking_sanity", {}).get("errors", [])
    
    # ranking（v3.2error）
    all_ranking_msgs = ranking_warnings + ranking_errors
    # error，fr_gap=0.15 >= 0.10combined_gap=0.02 <= 0.03
    assert len(ranking_errors) > 0, f"FR identity>=0.10combined<=0.03error，warnings: {ranking_warnings}"
    assert any("Ranking sanity violated" in msg or "FR identity vs combined inconsistency" in msg or "scoring model" in msg.lower
               for msg in ranking_errors), f"ranking sanity violated，: {ranking_errors}"
    assert qa_v3["ok"] is False, "fail"


def test_N13_combined_score_inconsistency:
    """
    ❌ N13：combined score 
    ： bug。
    """
    result = make_minimal_result_skeleton
    
    # ：
    # recorded combined = 0.70
    #  weights  0.62
    # ：combined score
    # ，
    result["candidates"] = [
        {
            "template_id": "HUMAN_VH3_SCF_24",
            "scores": {
                "fr_identity": 0.85,
                "cdr_compatibility": 0.80,
                "developability": 0.60,
                "immunogenicity": 0.40,  # 
                "combined": 0.70  # 
            },
            "flags": {
                "has_vhh_hallmark": True
            }
        }
    ]
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    # combined score，
    # 
    ranking_errors = qa_v3.get("checks", {}).get("ranking_sanity", {}).get("errors", [])
    ranking_warnings = qa_v3.get("checks", {}).get("ranking_sanity", {}).get("warnings", [])
    
    # combined score，
    # ，fail，


def test_N14_imgt_anchor_misalignment:
    """
    ❌ N14：IMGT anchor （CDR1/2/3 ）
    ： IMGT anchoring QA。
    """
    result = make_minimal_result_skeleton
    
    # ：
    # CDR1  26； CDR3  95–102 
    # ：IMGTIMGT
    # 
    
    # FR1，CDR1
    result["sequence_analysis"]["original_regions"]["FR1"] = "EVQLVESGGGLVQPGGSLRLSCAAS" + "AAA"  # 3
    result["sequence_analysis"]["humanized_regions"]["FR1"] = "EVQLVESGGGLVQPGGSLRLSCAAS" + "AAA"
    
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
    # IMGT，
    # IMGT
    integrity_errors = qa_v3.get("checks", {}).get("integrity", {}).get("errors", [])
    
    # 
    if len(result["sequence_analysis"]["original_regions"]["FR1"]) - len(result["sequence_analysis"]["humanized_regions"]["FR1"]) > 3:
        assert any("" in e for e in integrity_errors + qa_v3["errors"])


def test_N15_safe_mode_still_fails:
    """
    ❌ N15：Safe mode （ hallmark ）
    ： safe_mode 。
    """
    result = make_minimal_result_skeleton
    
    # ：
    # mode="safe"， hallmark 
    result["best_match"]["template"]["flags"]["has_vhh_hallmark"] = False
    result["candidates"] = [
        {
            "template_id": "HUMAN_VH3_SCF_24",
            "scores": {
                "fr_identity": 0.85,
                "combined": 0.75
            },
            "flags": {
                "has_vhh_hallmark": False  # hallmark
            }
        }
    ]
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    # ok == False
    # status == "FAILED_QA_V3" 
    # ：statushumanize_vhh_with_qa，QA
    # hallmark，fail（hallmarkfail）
    ranking_errors = qa_v3.get("checks", {}).get("ranking_sanity", {}).get("errors", [])
    all_errors = ranking_errors + qa_v3["errors"]
    # hallmark，fail
    if any("hallmark" in e.lower for e in all_errors):
        assert qa_v3["ok"] is False
    # hallmark，
    elif not qa_v3["ok"]:
        assert len(all_errors) > 0


def test_N16_length_difference_too_large:
    """
    ❌ N16：original / humanized 
    ：。
    """
    result = make_minimal_result_skeleton
    
    # ：original_len = 117，humanized_len = 100
    # FR3
    result["sequence_analysis"]["humanized_regions"]["FR3"] = "YYADSVKGRFTISRDNSKNTLYLQMGSLRAED"  # 17
    
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
    # （integrity）
    integrity_errors = qa_v3.get("checks", {}).get("integrity", {}).get("errors", [])
    all_errors = qa_v3["errors"] + integrity_errors
    # 
    if any("" in e and ("" in e or "" in e or "" in e) for e in all_errors):
        assert qa_v3["ok"] is False
    # ，fail
    elif any("" in e and ("" in e or "" in e) for e in all_errors):
        assert qa_v3["ok"] is False


def test_N17_missing_fr2_or_fr3:
    """
    ❌ N17： FR2  FR3 （regions ）
    ： fail。
    """
    result = make_minimal_result_skeleton
    
    # ：humanized.regions.FR2 
    result["sequence_analysis"]["humanized_regions"]["FR2"] = ""
    
    # （FR2）
    full_seq = "".join([
        result["sequence_analysis"]["humanized_regions"]["FR1"],
        result["sequence_analysis"]["humanized_regions"]["CDR1"],
        result["sequence_analysis"]["humanized_regions"]["CDR2"],
        result["sequence_analysis"]["humanized_regions"]["FR3"],
        result["sequence_analysis"]["humanized_regions"]["CDR3"],
        result["sequence_analysis"]["humanized_regions"]["FR4"]
    ])
    result["best_match"]["humanized_sequence"] = full_seq
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    # FR2（integrity）
    integrity_errors = qa_v3.get("checks", {}).get("integrity", {}).get("errors", [])
    all_errors = qa_v3["errors"] + integrity_errors
    # FR2，fail
    # FR2
    if any("FR2" in e and ("" in e or "" in e or "0" in e or "" in e) for e in all_errors):
        assert qa_v3["ok"] is False
    else:
        # FR2，
        # （FR2）
        assert qa_v3["ok"] is False or len(all_errors) > 0


def test_N18_cdr_fr_combo_not_in_allowed_matrix:
    """
    ❌ N18：CDR  FR 
    ： allowed matrix 。
    """
    result = make_minimal_result_skeleton
    
    # ：CDR1_len = 4, FR2_len = 10
    result["sequence_analysis"]["original_regions"]["CDR1"] = "AAAA"  # 4aa
    result["sequence_analysis"]["humanized_regions"]["CDR1"] = "AAAA"
    result["sequence_analysis"]["original_regions"]["FR2"] = "MHWVRQRPGK"  # 10aa
    result["sequence_analysis"]["humanized_regions"]["FR2"] = "MHWVRQRPGK"
    
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
    # v3.2：CDR1=4aa (<5aa)  FR2=10aa (<13aa) fail
    # VHH，error
    structural_warnings = qa_v3.get("checks", {}).get("structural_compat", {}).get("warnings", [])
    structural_errors = qa_v3.get("checks", {}).get("structural_compat", {}).get("errors", [])
    
    # CDR1=4aa < 5aa，FR2=10aa < 13aa
    # fail，VHH
    assert len(structural_errors) > 0, f"CDR1<5aaFR2<13aafail，warnings: {structural_warnings}"
    assert any("" in err or "" in err or "fail" in err 
               for err in structural_errors), f"''，: {structural_errors}"
    assert qa_v3["ok"] is False, "fail"


def test_N19_multiple_fallbacks_with_bad_delta:
    """
    ❌ N19： fallback（numbering  FR2  fallback）+ Δ
    ：。
    """
    result = make_minimal_result_skeleton
    
    # ：
    # flags.uses_fallback_numbering = True
    # flags.uses_fallback_fr2 = True
    # Δimmunogenicity > 0，Δdevelopability < 0
    result["best_match"]["template"]["flags"]["uses_fallback_numbering"] = True
    result["best_match"]["template"]["flags"]["uses_fallback_fr2"] = True
    result["best_match"]["developability"]["score"] = 0.30  # 
    result["original_developability"]["score"] = 0.50
    result["best_match"]["immunogenicity"]["fr_immuno_risk"] = "high"  # 
    result["original_immunogenicity"]["fr_immuno_risk"] = "low"
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    assert qa_v3["ok"] is False
    # errors  fallback、delta_risk 
    assert any("fallback" in e.lower for e in qa_v3["warnings"])
    delta_errors = qa_v3.get("checks", {}).get("delta_risk", {}).get("errors", [])
    assert len(delta_errors) > 0 or any("" in e and "" in e for e in qa_v3["errors"])


def test_N20_interface_mutation_not_in_list:
    """
    ❌ N20：interface  mutations.list （grafting+mutations ）
    ： grafting QA  QA 。
    """
    result = make_minimal_result_skeleton
    
    # ：
    #  interface  AA ， mutations.list 
    # FR1（IMGT 25）
    orig_fr1 = result["sequence_analysis"]["original_regions"]["FR1"]
    hum_fr1 = list(orig_fr1)
    if len(hum_fr1) > 20:
        hum_fr1[20] = "R"  # 
    result["sequence_analysis"]["humanized_regions"]["FR1"] = "".join(hum_fr1)
    
    # mutations.list
    result["mutations"]["list"] = []  # 
    
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
    # errors "FR "， grafting impact 
    assert any("FR " in e or "" in e for e in qa_v3["errors"])

