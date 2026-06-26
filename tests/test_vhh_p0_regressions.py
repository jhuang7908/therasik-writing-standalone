from __future__ import annotations

from types import SimpleNamespace

from core import vhh_humanization as vhhu


def _rows_from_pos_map(pos_map: dict[int, str]):
    return [{"pos": p, "aa": aa, "ins_code": " "} for p, aa in sorted(pos_map.items())]


def test_find_best_matching_scaffold_uses_imgt_position_identity(monkeypatch):
    # Guardrail: old buggy implementation depended on split_regions + linear
    # concatenation. New implementation must not call split_regions.
    monkeypatch.setattr(
        vhhu,
        "split_regions",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("split_regions must not be used")),
    )

    input_map = {1: "Q", 2: "V", 39: "A", 66: "L", 118: "W"}
    good_map = {1: "Q", 2: "V", 39: "A", 66: "L", 118: "W"}
    bad_map = {1: "Q", 2: "X", 39: "X", 66: "X", 118: "W"}

    def _stub_number(seq: str):
        if seq == "INPUT_SEQ":
            return _rows_from_pos_map(input_map)
        if seq == "GOOD_FW":
            return _rows_from_pos_map(good_map)
        if seq == "BAD_FW":
            return _rows_from_pos_map(bad_map)
        raise RuntimeError(f"Unexpected sequence: {seq}")

    monkeypatch.setattr(vhhu, "imgt_number_anarcii", _stub_number)

    scaffolds = [
        {"scaffold_id": "bad", "consensus": {"framework_full": "BAD_FW"}},
        {"scaffold_id": "good", "consensus": {"framework_full": "GOOD_FW"}},
    ]
    best, identity = vhhu.find_best_matching_scaffold("INPUT_SEQ", scaffolds)

    assert best is not None
    assert best["scaffold_id"] == "good"
    assert identity > 0.9


def test_surface_reshape_i_to_t_and_m_to_q_leave_hydrophobic_set(monkeypatch):
    # Deterministic mapping: linear index i -> IMGT i+1, all valid FR positions.
    def _map(seq: str):
        return {i: i + 1 for i in range(len(seq))}, {i: " " for i in range(len(seq))}, None

    monkeypatch.setattr(vhhu, "_build_linear_to_imgt_map", _map)
    monkeypatch.setattr(vhhu, "_compute_hydro_patch_max9", lambda _s: 1.0)

    calls = {"n": 0}

    def _check(_h, _s):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"action": "RESHAPE", "tier": "over_red"}
        return {"action": "PASS", "tier": "green"}

    monkeypatch.setattr(vhhu, "check_sap_against_strategy", _check)

    out_i = vhhu.surface_reshaping_trigger("IIIIIIIIIII", hydro_patch=1.0, strategy="S2")
    assert out_i["mutations"][0]["from_aa"] == "I"
    assert out_i["mutations"][0]["to_aa"] == "T"
    assert out_i["mutations"][0]["to_aa"] not in set("FILMVWY")

    calls["n"] = 0
    out_m = vhhu.surface_reshaping_trigger("MMMMMMMMMMM", hydro_patch=1.0, strategy="S2")
    assert out_m["mutations"][0]["from_aa"] == "M"
    assert out_m["mutations"][0]["to_aa"] == "Q"
    assert out_m["mutations"][0]["to_aa"] not in set("FILMVWY")


def test_select_sort_key_respects_fr_priority_before_grade(monkeypatch):
    class _Params:
        fallback_penalty_template = 1.0
        fallback_penalty_numbering = 1.0
        hard_min_cdr_score = 0.0
        soft_min_cdr_score = 0.0

        @staticmethod
        def get_scoring_weights():
            return {"framework_identity": 0.6, "cdr_compatibility": 0.15, "developability": 0.25}

    monkeypatch.setattr(vhhu, "get_config", lambda: SimpleNamespace(parameters=_Params()))
    monkeypatch.setattr(vhhu, "load_fr3_packing_rule", lambda: {})
    monkeypatch.setattr(vhhu, "load_clinical_germline_anchors", lambda: {})
    monkeypatch.setattr(vhhu, "extract_template_key_positions", lambda _t: {})

    alignment_index = {
        "scaf1": {
            "HIGH_FR_SAFE_A": {"framework_identity": 0.92, "fr2_identity": 0.9},
            "LOW_FR_SAFE_A": {"framework_identity": 0.80, "fr2_identity": 0.9},
        }
    }
    templates = [
        {
            "template_id": "HIGH_FR_SAFE_A",
            "safe_plan": "A",
            "plan_name": "A",
            "source_scaffold": "scaf1",
            "consensus": {"framework_full": "QVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLE"},
            "developability": {"score": 0.65, "grade": "B"},
            "immunogenicity": {"fr_immuno_risk": "low"},
        },
        {
            "template_id": "LOW_FR_SAFE_A",
            "safe_plan": "A",
            "plan_name": "A",
            "source_scaffold": "scaf1",
            "consensus": {"framework_full": "QVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLE"},
            "developability": {"score": 0.95, "grade": "A"},  # better grade, lower FR
            "immunogenicity": {"fr_immuno_risk": "low"},
        },
    ]

    out, _ = vhhu.select_human_templates(
        alpaca_scaffold_id="scaf1",
        panel="A",
        alignment_index=alignment_index,
        human_templates=templates,
        top_k=2,
        use_cdr_filtering=False,
    )

    assert [x["template_id"] for x in out] == ["HIGH_FR_SAFE_A", "LOW_FR_SAFE_A"]
