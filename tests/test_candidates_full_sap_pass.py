from __future__ import annotations

from core import vhh_humanization as vhhu


def _stub_run_anarcii_imgt(*args, **kwargs):
    seq = kwargs.get("seq") or args[0]
    regs = {
        "FR1": "A" * 10,
        "CDR1": "BBBB",
        "FR2": "C" * 10,
        "CDR2": "DDDD",
        "FR3": "E" * 10,
        "CDR3": "CCCCCCCCCCCCC",
        "FR4": "F" * 5,
    }
    rows = [{"pos": i + 1, "aa": aa, "ins_code": " "} for i, aa in enumerate(seq[:60])]
    return regs, rows, {"source": "stub"}


def test_each_candidate_gets_sap_and_optional_reshape_with_top_level_best_copy(monkeypatch):
    monkeypatch.setattr(vhhu, "load_alpaca_vhh_scaffolds", lambda: [{"scaffold_id": "scaf1", "consensus": {"framework_full": "A" * 50}}])
    monkeypatch.setattr(
        vhhu,
        "load_human_vhh_safe_templates",
        lambda: [
            {"template_id": "HIGH_SAFE_A", "developability": {"score": 0.8, "grade": "A"}, "immunogenicity": {"fr_immuno_risk": "low", "fr_hotspot_count": 0}},
            {"template_id": "LOW_SAFE_A", "developability": {"score": 0.7, "grade": "B"}, "immunogenicity": {"fr_immuno_risk": "low", "fr_hotspot_count": 0}},
        ],
    )
    monkeypatch.setattr(vhhu, "load_alignment_matrix", lambda: {"scaf1": {}})
    monkeypatch.setattr(vhhu, "find_best_matching_scaffold", lambda *_a, **_k: ({"scaffold_id": "scaf1"}, 0.95))
    monkeypatch.setattr(
        vhhu,
        "classify_all_cdrs",
        lambda *_a, **_k: {
            "cdr1": {"length": 4, "canonical_class": "ok"},
            "cdr2": {"length": 4, "canonical_class": "ok"},
            "cdr3": {"length": 13, "canonical_class": "ok"},
            "CDR1": {"canonical_class": "ok"},
        },
    )
    monkeypatch.setattr(vhhu, "build_pos_to_aa_map", lambda _rows: {44: "Q", 45: "A", 47: "G"})
    monkeypatch.setattr(vhhu, "get_key_position_residues", lambda _m: {})
    monkeypatch.setattr("core.segmentation.anarcii_adapter.run_anarcii_imgt", _stub_run_anarcii_imgt)
    monkeypatch.setattr(
        vhhu,
        "match_canonical_compatibility",
        lambda *_a, **_k: {"compatibility_score": 1.0, "key_position_score": 1.0, "warnings": []},
    )
    monkeypatch.setattr(vhhu, "_humanized_regions_for_qa", lambda *_a, **_k: {"FR1": "A", "CDR1": "BBBB", "FR2": "C", "CDR2": "DDDD", "FR3": "E", "CDR3": "CCCCCCCCCCCCC", "FR4": "F"})
    monkeypatch.setattr(vhhu, "_sync_sequence_analysis_with_final_best", lambda *_a, **_k: None)
    monkeypatch.setattr("core.germline_data_builder.build_germline_candidates", lambda **_k: {"candidates": []})

    def _stub_select(_scaf, panel, *_args, **_kwargs):
        return [
            {
                "template_id": "HIGH_SAFE_A",
                "source_scaffold": "scaf1",
                "safe_plan": panel,
                "plan_name": panel,
                "consensus": {"fr1": "A", "fr2": "C", "fr3": "E", "fr4": "F"},
                "length": 120,
                "alignment_scores": {"combined_score": 0.9, "scoring": {"combined_score": 0.9}},
                "cdr_compatibility": {"key_position_score": 1.0},
                "mutations": {},
                "developability": {"score": 0.8, "grade": "A"},
                "immunogenicity": {"fr_immuno_risk": "low", "fr_hotspot_count": 0},
            },
            {
                "template_id": "LOW_SAFE_A",
                "source_scaffold": "scaf1",
                "safe_plan": panel,
                "plan_name": panel,
                "consensus": {"fr1": "A", "fr2": "C", "fr3": "E", "fr4": "F"},
                "length": 120,
                "alignment_scores": {"combined_score": 0.7, "scoring": {"combined_score": 0.7}},
                "cdr_compatibility": {"key_position_score": 1.0},
                "mutations": {},
                "developability": {"score": 0.7, "grade": "B"},
                "immunogenicity": {"fr_immuno_risk": "low", "fr_hotspot_count": 0},
            },
        ], {"panel": panel}

    monkeypatch.setattr(vhhu, "select_human_templates", _stub_select)
    monkeypatch.setattr(vhhu, "graft_cdrs_to_template", lambda _cdrs, t: f"SEQ_{t['template_id']}")
    monkeypatch.setattr(
        vhhu,
        "apply_tier_back_mutations",
        lambda **kwargs: (kwargs.get("humanized_seq", kwargs.get("humanized_sequence", "")), []),
    )

    monkeypatch.setattr(
        vhhu,
        "_compute_hydro_patch_max9",
        lambda s: 0.85 if "HIGH" in s else 0.50,
    )
    monkeypatch.setattr(
        vhhu,
        "check_sap_against_strategy",
        lambda hydro, _strategy: {"action": "RESHAPE" if hydro > 0.7 else "PASS", "tier": "red" if hydro > 0.7 else "green"},
    )
    monkeypatch.setattr(
        vhhu,
        "surface_reshaping_trigger",
        lambda s, _h, _st: {"success": True, "reshaped_sequence": s + "_R", "final_tier": "yellow"},
    )

    seq = "QVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAGGGGGGGGGGGGWGQGTLVTVSS"
    out = vhhu.humanize_vhh(seq=seq, panel="A", enforce_prescreen=False, return_all_templates=True)

    assert out["success"] is True, out.get("error")
    assert len(out["candidates"]) == 2
    assert all("v22_sap_check" in c for c in out["candidates"])
    assert all("v22_reshaping" in c for c in out["candidates"])

    reshaped = [c for c in out["candidates"] if c["v22_sap_check"]["action"] == "RESHAPE"][0]
    assert reshaped["humanized_sequence"].endswith("_R")
    assert reshaped.get("humanized_sequence_pre_reshape") is not None

    # top-level fields are copies from best candidate (backward compatibility)
    assert out["v22_sap_check"] == out["candidates"][0]["v22_sap_check"]
