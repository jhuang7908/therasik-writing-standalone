from __future__ import annotations

from collections import defaultdict

from core import vhh_humanization as vhhu


def _stub_run_anarcii_imgt(*args, **kwargs):
    seq = kwargs.get("seq") or args[0]
    cdr3 = "C" * 19  # long CDR3 for §3.3 dynamic-upgrade behavior
    regs = {
        "FR1": "A" * 10,
        "CDR1": "BBBB",
        "FR2": "C" * 10,
        "CDR2": "DDDD",
        "FR3": "E" * 10,
        "CDR3": cdr3,
        "FR4": "F" * 5,
    }
    rows = [{"pos": i + 1, "aa": aa, "ins_code": " "} for i, aa in enumerate(seq[:60])]
    return regs, rows, {"source": "stub"}


def test_panel_all_runs_progressive_strategies_independently(monkeypatch):
    monkeypatch.setattr(vhhu, "load_alpaca_vhh_scaffolds", lambda: [{"scaffold_id": "scaf1", "consensus": {"framework_full": "A" * 50}}])
    monkeypatch.setattr(vhhu, "load_human_vhh_safe_templates", lambda: [{"template_id": "dummy"}])
    monkeypatch.setattr(vhhu, "load_alignment_matrix", lambda: {"scaf1": {}})
    monkeypatch.setattr(vhhu, "find_best_matching_scaffold", lambda *_a, **_k: ({"scaffold_id": "scaf1"}, 0.95))
    monkeypatch.setattr(
        vhhu,
        "classify_all_cdrs",
        lambda *_a, **_k: {
            "cdr1": {"length": 4, "canonical_class": "ok"},
            "cdr2": {"length": 4, "canonical_class": "ok"},
            "cdr3": {"length": 19, "canonical_class": "ok"},
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
    monkeypatch.setattr(vhhu, "_humanized_regions_for_qa", lambda *_a, **_k: {"FR1": "A", "CDR1": "BBBB", "FR2": "C", "CDR2": "DDDD", "FR3": "E", "CDR3": "C" * 19, "FR4": "F"})
    monkeypatch.setattr(vhhu, "_sync_sequence_analysis_with_final_best", lambda *_a, **_k: None)
    monkeypatch.setattr("core.vhh.vhh42_reference_loader.annotate_input_vs_vhh42_population", lambda _s: {"available": False})

    def _stub_select(_scaf, panel, *_args, **_kwargs):
        cand = {
            "template_id": f"T_{panel}",
            "source_scaffold": "scaf1",
            "safe_plan": panel,
            "plan_name": panel,
            "consensus": {"fr1": "A", "fr2": "C", "fr3": "E", "fr4": "F"},
            "alignment_scores": {"combined_score": {"A": 0.7, "B": 0.8, "C": 0.9}[panel], "scoring": {"combined_score": {"A": 0.7, "B": 0.8, "C": 0.9}[panel]}},
            "cdr_compatibility": {"key_position_score": 1.0},
            "mutations": {},
        }
        return [cand], {"panel": panel}

    monkeypatch.setattr(vhhu, "select_human_templates", _stub_select)
    monkeypatch.setattr(vhhu, "graft_cdrs_to_template", lambda cdrs, _t: f"FR_{cdrs['CDR1']}_{cdrs['CDR2']}_{cdrs['CDR3']}")
    monkeypatch.setattr(vhhu, "_compute_hydro_patch_max9", lambda _s: 0.55)
    monkeypatch.setattr(vhhu, "check_sap_against_strategy", lambda *_a, **_k: {"action": "PASS", "tier": "green"})
    monkeypatch.setattr(vhhu, "surface_reshaping_trigger", lambda *_a, **_k: {"success": False})

    def _apply(**kwargs):
        protected_kabat = kwargs.get("protected_kabat", set())
        hum = kwargs.get("humanized_seq", kwargs.get("humanized_sequence", ""))
        muts = [{"kabat_position": p} for p in sorted(protected_kabat)]
        return hum, muts

    monkeypatch.setattr(vhhu, "apply_tier_back_mutations", _apply)
    monkeypatch.setattr("core.germline_data_builder.build_germline_candidates", lambda **_k: {"candidates": []})

    seq = "QVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYC" + ("C" * 19) + "WGQGTLVTVSS"
    out = vhhu.humanize_vhh(seq=seq, panel="all", enforce_prescreen=False, return_all_templates=True)

    assert out["success"] is True
    assert set(out["best_by_plan"].keys()) == {"A", "B", "C"}

    prov = out["_protected_provenance_by_panel"]
    # critical probe: long CDR3=19 => S1 upgrades 73/78, S2/S3 no dynamic upgrade entries.
    assert any("Pos 73" in x for x in prov["A"]["dynamic_upgrades"])
    assert any("Pos 78" in x for x in prov["A"]["dynamic_upgrades"])
    assert prov["B"]["dynamic_upgrades"] == []
    assert prov["C"]["dynamic_upgrades"] == []

    grouped = defaultdict(list)
    for c in out["candidates"]:
        grouped[c["panel"]].append(len(c["tier_back_mutations"]))
    assert grouped["A"][0] <= grouped["B"][0] <= grouped["C"][0]

    # CDR payload remains identical across strategies.
    seqs = [out["best_by_plan"][p]["humanized_sequence"] for p in ("A", "B", "C")]
    assert len(set(seqs)) == 1
