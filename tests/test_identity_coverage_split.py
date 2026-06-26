from types import SimpleNamespace

from core import vhh_humanization as vhhu


def test_dynamic_alignment_adds_split_fields_and_keeps_framework_identity_semantics():
    # Build maps with partial overlap to make coverage < 1.
    input_map = {1: "Q", 2: "V", 3: "Q", 39: "A", 40: "B", 66: "C", 118: "D"}
    templ_map = {1: "Q", 2: "X", 39: "A", 66: "Y", 104: "Z", 118: "D"}

    out = vhhu._compute_dynamic_alignment(input_map, templ_map)

    # New P2-11 fields.
    assert "fr_identity_on_shared_positions" in out
    assert "fr_coverage" in out

    # framework_identity must keep old semantics:
    # numerator = matches on shared FR positions
    # denominator = FR union-count logic (old implementation contract)
    fr_positions = list(range(1, 27)) + list(range(39, 56)) + list(range(66, 105)) + list(range(118, 130))
    legacy_match = 0
    legacy_total = 0
    for p in fr_positions:
        in_i = p in input_map
        in_t = p in templ_map
        if in_i and in_t:
            legacy_total += 1
            if input_map[p] == templ_map[p]:
                legacy_match += 1
        elif in_i or in_t:
            legacy_total += 1
    legacy_framework_identity = legacy_match / legacy_total if legacy_total else 0.0
    assert abs(out["framework_identity"] - legacy_framework_identity) < 1e-12
    assert 0.0 <= out["fr_identity_on_shared_positions"] <= 1.0
    assert 0.0 <= out["fr_coverage"] <= 1.0


def test_select_order_unchanged_when_low_coverage_only_logs(monkeypatch):
    class _Params:
        fallback_penalty_template = 1.0
        fallback_penalty_numbering = 1.0
        hard_min_cdr_score = 0.3
        soft_min_cdr_score = 0.6

        @staticmethod
        def get_scoring_weights():
            return {"framework_identity": 0.6, "cdr_compatibility": 0.15, "developability": 0.25}

    monkeypatch.setattr(vhhu, "get_config", lambda: SimpleNamespace(parameters=_Params()))
    monkeypatch.setattr(vhhu, "load_fr3_packing_rule", lambda: {})
    monkeypatch.setattr(vhhu, "load_clinical_germline_anchors", lambda: {})
    monkeypatch.setattr(vhhu, "extract_template_key_positions", lambda _t: {})

    alignment_index = {
        "scaf1": {
            "HIGH_SAFE_A": {
                "framework_identity": 0.92,
                "fr_identity_on_shared_positions": 0.95,
                "fr_coverage": 0.55,  # low coverage => warning only
            },
            "LOW_SAFE_A": {
                "framework_identity": 0.85,
                "fr_identity_on_shared_positions": 0.85,
                "fr_coverage": 0.95,
            },
        }
    }
    templates = [
        {
            "template_id": "HIGH_SAFE_A",
            "safe_plan": "A",
            "plan_name": "A",
            "source_scaffold": "scaf1",
            "consensus": {"framework_full": "QVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLE"},
            "developability": {"score": 0.7, "grade": "B"},
            "immunogenicity": {"fr_immuno_risk": "low"},
        },
        {
            "template_id": "LOW_SAFE_A",
            "safe_plan": "A",
            "plan_name": "A",
            "source_scaffold": "scaf1",
            "consensus": {"framework_full": "QVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLE"},
            "developability": {"score": 0.7, "grade": "B"},
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

    # Behavior remains ranking-driven; coverage does not filter in PR-2.
    assert [x["template_id"] for x in out] == ["HIGH_SAFE_A", "LOW_SAFE_A"]
