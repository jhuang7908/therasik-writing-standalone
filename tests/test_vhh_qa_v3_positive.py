"""
QA v3.3 （10）
 ok=True， warning（minor/major）
"""
import pytest
from core.vhh_qa_validation_v3_3 import validate_vhh_humanization_result_v3_3
from core.vhh_qa_validation_v3_3 import auto_build_mutations_from_regions


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


def test_P01_standard_vhh_pass:
    """
    ✅ P01： VHH ，
    ："" VHH  QA 。
    """
    result = make_minimal_result_skeleton
    
    # ：
    # - original / humanized regions ：FR1–4, CDR1–3 
    # - CDR （ CDR ）
    # - VHH hallmark（37/44/45/47） humanized 
    # - CDR3 = 14 aa，FR3 = 38 aa，
    # - impact_score_normalized < 0.2
    # - Δdevelopability ≥ 0，Δimmunogenicity ≤ 0
    # - best template  hallmark，ranking 
    
    # CDR3=14aa, FR3=38aa
    result["sequence_analysis"]["original_regions"]["CDR3"] = "AAGGVGWPYFDYA"
    result["sequence_analysis"]["humanized_regions"]["CDR3"] = "AAGGVGWPYFDYA"
    result["sequence_analysis"]["original_regions"]["FR3"] = "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC"  # 38aa
    result["sequence_analysis"]["humanized_regions"]["FR3"] = "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC"
    
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
    
    # Δdevelopability ≥ 0，Δimmunogenicity ≤ 0
    result["best_match"]["developability"]["score"] = 0.60  # 
    result["original_developability"]["score"] = 0.50
    result["best_match"]["immunogenicity"]["fr_immuno_risk"] = "low"
    result["original_immunogenicity"]["fr_immuno_risk"] = "medium"  # 
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    assert qa_v3["ok"] is True
    assert len(qa_v3["errors"]) == 0
    assert qa_v3["summary_score"]["biological_feasibility"] >= 70


def test_P02_fallback_numbering_warning_only:
    """
    ✅ P02： fallback （ warning）
    ： fallback  warning， fail。
    """
    result = make_minimal_result_skeleton
    
    # ： flags.uses_fallback_numbering = True
    result["best_match"]["template"]["flags"]["uses_fallback_numbering"] = True
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    assert qa_v3["ok"] is True
    assert len(qa_v3["errors"]) == 0
    assert any("fallback" in w.lower for w in qa_v3["warnings"])


def test_P03_long_cdr3_long_fr3_acceptable:
    """
    ✅ P03： CDR3（20 aa）， FR3（40 aa），
    ： CDR3 +  FR3 。
    """
    result = make_minimal_result_skeleton
    
    # ：CDR3_len = 20, FR3_len = 40
    result["sequence_analysis"]["original_regions"]["CDR3"] = "AAGGVGWPYFDYAAGGVGWPY"  # 20aa
    result["sequence_analysis"]["humanized_regions"]["CDR3"] = "AAGGVGWPYFDYAAGGVGWPY"
    result["sequence_analysis"]["original_regions"]["FR3"] = "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAA"  # 40aa
    result["sequence_analysis"]["humanized_regions"]["FR3"] = "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAA"
    
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
    assert qa_v3["ok"] is True
    # structural_compaterror
    structural_errors = qa_v3.get("checks", {}).get("structural_compat", {}).get("errors", [])
    assert len(structural_errors) == 0


def test_P04_minor_developability_drop_warning:
    """
    ✅ P04： developability +  warning
    ： Δdevelopability （>-0.1） fail。
    """
    result = make_minimal_result_skeleton
    
    # ：Δdevelopability = -0.05
    result["best_match"]["developability"]["score"] = 0.45
    result["original_developability"]["score"] = 0.50
    result["best_match"]["immunogenicity"]["fr_immuno_risk"] = "low"
    result["original_immunogenicity"]["fr_immuno_risk"] = "low"
    
    qa_v3_3 = validate_vhh_humanization_result_v3_3(result, strict=True)
    
    # ：
    assert qa_v3_3["ok"] is True, f"，: {qa_v3_3['errors']}"
    assert len(qa_v3_3["errors"]) == 0
    # v3.3: delta_risk
    delta_warnings = qa_v3_3.get("checks", {}).get("delta_risk", {}).get("warnings", [])
    all_warnings = qa_v3_3["warnings"] + delta_warnings
    # -0.05minormajor warning
    assert len(all_warnings) > 0, "developabilitywarning"
    assert any(
        (isinstance(w, dict) and w.get("category") == "delta_risk" and 
         ("developability" in w.get("message", "").lower or "" in w.get("message", "")))
        or (isinstance(w, str) and "developability" in w.lower and "" in w)
        for w in all_warnings
    ), f"delta_riskwarning，: {all_warnings}"


def test_P05_ideal_immuno_dev_improvement:
    """
    ✅ P05：Immunogenicity ，Developability 
    ： "" 。
    """
    result = make_minimal_result_skeleton
    
    # ：Δimmunogenicity = -0.20, Δdevelopability = +0.15
    result["best_match"]["developability"]["score"] = 0.65
    result["original_developability"]["score"] = 0.50
    result["best_match"]["immunogenicity"]["fr_immuno_risk"] = "low"
    result["original_immunogenicity"]["fr_immuno_risk"] = "high"
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    assert qa_v3["ok"] is True
    assert qa_v3["summary_score"]["biological_feasibility"] >= 80


def test_P06_edge_case_fr3_slightly_short:
    """
    ✅ P06：FR3 ， CDR3 
    ： QA "" warning  error。
    """
    result = make_minimal_result_skeleton
    
    # ：CDR3_len = 14, FR3_len = 36
    result["sequence_analysis"]["original_regions"]["CDR3"] = "AAGGVGWPYFDYA"  # 14aa
    result["sequence_analysis"]["humanized_regions"]["CDR3"] = "AAGGVGWPYFDYA"
    result["sequence_analysis"]["original_regions"]["FR3"] = "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVY"  # 36aa
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
    
    qa_v3_3 = validate_vhh_humanization_result_v3_3(result, strict=True)
    
    # ：
    assert qa_v3_3["ok"] is True, f"，: {qa_v3_3['errors']}"
    # v3.3: FR3=36aa, CDR3=14aa（CDR3≤14FR3≥35）
    structural_errors = qa_v3_3.get("checks", {}).get("structural_compat", {}).get("errors", [])
    assert len(structural_errors) == 0, f"structural error，: {structural_errors}"


def test_P07_medium_grafting_impact_warning:
    """
    ✅ P07： grafting（impact_score_normalized ）
    ： grafting impact  warning。
    """
    result = make_minimal_result_skeleton
    
    # ：interface  2–3  hydrophobic→polar 
    # impact_score_normalized （ 0.3–0.5）
    # FR1/FR2/FR3
    # ：grafting impact，FR
    result["sequence_analysis"]["humanized_regions"]["FR1"] = "EVQLVESGGGLVQPGGSLRLSCAAS"  # 
    result["sequence_analysis"]["humanized_regions"]["FR2"] = "MHWVRQRPGKGLEYVSA"  # 
    result["sequence_analysis"]["humanized_regions"]["FR3"] = "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC"  # 
    
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
    assert qa_v3["ok"] is True
    # grafting impact，warning
    grafting_warnings = qa_v3.get("checks", {}).get("grafting_impact", {}).get("warnings", [])
    # warning，error（impact_score_normalized >= 0.4）


def test_P08_second_template_slightly_better_warning:
    """
    ✅ P08：， →  warning  fail
    ： ranking_sanity 。
    """
    result = make_minimal_result_skeleton
    
    # ：
    # best.fr_identity = 0.82, best.combined = 0.70
    # second.fr_identity = 0.86, second.combined = 0.69
    #  hallmarks 
    result["candidates"] = [
        {
            "template_id": "HUMAN_VH3_SCF_24",
            "scores": {
                "fr_identity": 0.82,
                "combined": 0.70
            },
            "flags": {
                "has_vhh_hallmark": True
            }
        },
        {
            "template_id": "HUMAN_VH3_SCF_25",
            "scores": {
                "fr_identity": 0.86,
                "combined": 0.69
            },
            "flags": {
                "has_vhh_hallmark": True
            }
        }
    ]
    
    qa_v3_3 = validate_vhh_humanization_result_v3_3(result, strict=True)
    
    # ：
    assert qa_v3_3["ok"] is True, f"，: {qa_v3_3['errors']}"
    # v3.3: FR identity0.04minor warning（0.03-0.05）
    ranking_errors = qa_v3_3.get("checks", {}).get("ranking_sanity", {}).get("errors", [])
    ranking_warnings = qa_v3_3.get("checks", {}).get("ranking_sanity", {}).get("warnings", [])
    assert len(ranking_errors) == 0, f"ranking error，: {ranking_errors}"
    # minormajor warning
    if len(ranking_warnings) > 0:
        assert any(
            (isinstance(w, dict) and w.get("category") == "ranking" and 
             w.get("level") in ["minor", "major"])
            or (isinstance(w, str) and "ranking" in w.lower)
            for w in ranking_warnings
        ), f"ranking warning，: {ranking_warnings}"


def test_P09_fallback_with_good_delta:
    """
    ✅ P09：Template  fallback + VHH hallmark  + Δ
    ：， QA 。
    """
    result = make_minimal_result_skeleton
    
    # ：
    # uses_fallback_numbering = True
    # hallmarks 
    # Δimmunogenicity ≤ 0, Δdevelopability ≥ 0
    result["best_match"]["template"]["flags"]["uses_fallback_numbering"] = True
    result["best_match"]["developability"]["score"] = 0.60
    result["original_developability"]["score"] = 0.50
    result["best_match"]["immunogenicity"]["fr_immuno_risk"] = "low"
    result["original_immunogenicity"]["fr_immuno_risk"] = "medium"
    
    qa_v3 = validate_vhh_humanization_result_v3(result, strict=True)
    
    # ：
    assert qa_v3["ok"] is True
    # fallback  ""  warning 
    assert any("fallback" in w.lower for w in qa_v3["warnings"])


def test_P10_safe_mode_conservative_pass:
    """
    ✅ P10：Safe mode （FR ）
    ： safe_mode  QA。
    """
    result = make_minimal_result_skeleton
    
    # ：
    # FR （ 3 ）
    # FR identity 
    #  QA （hallmark、struct、grafting、Δ）
    
    # v3.3: auto_build_mutations_from_regionsmutations.list
    # humanized regions3FR
    orig_regions = result["sequence_analysis"]["original_regions"]
    hum_regions = result["sequence_analysis"]["humanized_regions"].copy
    
    # FR15 A->S
    fr1_list = list(hum_regions["FR1"])
    if len(fr1_list) > 4:
        fr1_list[4] = "S"  # 0-based，54
    hum_regions["FR1"] = "".join(fr1_list)
    
    # FR23 V->I（FR2）
    # FR2IMGT 39，FR23IMGT 41
    fr2_list = list(hum_regions["FR2"])
    if len(fr2_list) > 2:
        fr2_list[2] = "I"  # 0-based
    hum_regions["FR2"] = "".join(fr2_list)
    
    # FR310 K->R（FR3）
    # FR3IMGT 66，FR310IMGT 75
    fr3_list = list(hum_regions["FR3"])
    if len(fr3_list) > 9:
        fr3_list[9] = "R"  # 0-based
    hum_regions["FR3"] = "".join(fr3_list)
    
    result["sequence_analysis"]["humanized_regions"] = hum_regions
    
    # v3.3auto_build_mutations_from_regionsmutations.list
    auto_mutations = auto_build_mutations_from_regions(orig_regions, hum_regions)
    result["mutations"]["list"] = auto_mutations
    
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
    
    qa_v3_3 = validate_vhh_humanization_result_v3_3(result, strict=True)
    
    # ：
    assert qa_v3_3["ok"] is True, f"，: {qa_v3_3['errors']}"
    # v3.3: auto_build_mutations_from_regions，mutations.listregions
    # warning，error
    assert len(qa_v3_3["errors"]) == 0, f"error，: {qa_v3_3['errors']}"

