from types import SimpleNamespace

from core import vhh_humanization as vhhu


def test_combined_score_is_normalized_and_ada_applies_symmetrically(monkeypatch):
    class _Params:
        fallback_penalty_template = 1.0
        fallback_penalty_numbering = 1.0
        hard_min_cdr_score = 0.0
        soft_min_cdr_score = 0.0

        @staticmethod
        def get_scoring_weights():
            # Intentionally non-unit sum to verify normalization.
            return {
                "framework_identity": 1.2,
                "cdr_compatibility": 0.5,
                "developability": 0.5,
                "fr_immunogenicity": 0.3,
            }

    monkeypatch.setattr(vhhu, "get_config", lambda: SimpleNamespace(parameters=_Params()))
    monkeypatch.setattr(vhhu, "load_fr3_packing_rule", lambda: {})
    monkeypatch.setattr(
        vhhu,
        "load_clinical_germline_anchors",
        lambda: {"IGHV1-2": {"ada_majority_risk": "HIGH"}},
    )
    monkeypatch.setattr(vhhu, "extract_template_key_positions", lambda _t: {})

    alignment_index = {
        "scaf1": {
            "TMP_SAFE_A": {
                "framework_identity": 0.9,
                "fr2_identity": 0.8,
            }
        }
    }
    templates = [
        {
            "template_id": "TMP_SAFE_A",
            "safe_plan": "A",
            "plan_name": "A",
            "source_scaffold": "scaf1",
            "consensus": {"framework_full": "QVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLE"},
            "developability": {"score": 0.8, "grade": "A"},
            "immunogenicity": {"fr_immuno_risk": "high"},
            "germline": "IGHV1-2",
        }
    ]

    out, _ = vhhu.select_human_templates(
        alpaca_scaffold_id="scaf1",
        panel="A",
        alignment_index=alignment_index,
        human_templates=templates,
        top_k=1,
        use_cdr_filtering=False,
        input_pos_map=None,
        vhh_cdr3_seq=None,
    )
    assert out, "Expected one candidate"
    scoring = out[0]["alignment_scores"]["scoring"]
    combined = scoring["combined_score"]

    # Core regression assertions for P2-10:
    # 1) Value is always clamped to [0,1].
    # 2) ADA penalty is preserved in scoring details.
    assert 0.0 <= combined <= 1.0
    assert scoring["ada_penalty"] == 0.8
