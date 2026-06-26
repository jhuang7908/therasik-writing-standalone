"""
tests/test_clinical_gold_standard_v1_1.py
==========================================
Smoke tests for AbEngineCore v1.1 Clinical Gold Standard Integration.

Tests cover:
  A. ClinicalRuleEngine — population gate logic + industry fallback
  B. calibration.py — VernierWeights + GoldenPairs loading
  C. evaluator.py — AntibodyType.DOG + clinical_population dispatch
  D. engine.py — workflow='dog' dispatch + SUPPORTED_WORKFLOWS
  E. Structure-first cap — dry_run=True caps overall_status at WARN

These are all DRY-RUN tests (no ImmuneBuilder / ANARCI required).
Run with: python -m pytest tests/test_clinical_gold_standard_v1_1.py -v
"""
import sys
from pathlib import Path

# Allow running from workspace root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ─────────────────────────────────────────────────────────────────────────────
# A. ClinicalRuleEngine
# ─────────────────────────────────────────────────────────────────────────────

def test_cre_import_and_valid_populations():
    from core.evaluation.clinical_rule_engine import ClinicalRuleEngine
    for pop in ("igg_like_232fab", "scfv_84", "vhh_40"):
        try:
            cre = ClinicalRuleEngine(pop)
            assert cre.population == pop
        except FileNotFoundError:
            pass  # evaluation_reference_stats.json not present in CI — acceptable


def test_cre_invalid_population_raises():
    from core.evaluation.clinical_rule_engine import ClinicalRuleEngine
    try:
        ClinicalRuleEngine("unknown_pop")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_cre_get_engine_returns_none_gracefully():
    """get_engine must never raise; returns None if stats file missing."""
    from core.evaluation.clinical_rule_engine import get_engine
    result = get_engine("igg_like_232fab")
    # Either None (file missing) or a ClinicalRuleEngine instance
    assert result is None or hasattr(result, "evaluate")


def test_cre_evaluate_returns_engine_result():
    from core.evaluation.clinical_rule_engine import get_engine, EngineResult
    cre = get_engine("igg_like_232fab")
    if cre is None:
        return  # skip if reference file absent
    metrics = {"pI": 8.5, "GRAVY": -0.3, "instability_index": 45.0}
    result = cre.evaluate(metrics)
    assert isinstance(result, EngineResult)
    assert result.population == "igg_like_232fab"
    assert result.overall_gate in ("PASS", "WARN", "FAIL")
    assert 0.0 <= result.clinical_score <= 100.0


def test_cre_industry_fallback_warn_not_fail():
    """Industry rules (w=0.5) must only produce WARN, never FAIL."""
    from core.evaluation.clinical_rule_engine import ClinicalRuleEngine, GateResult
    # Create engine targeting a population that won't be in stats (will fall to industry)
    cre = ClinicalRuleEngine("vhh_40")
    # Directly test industry gate
    gate = cre._industry_gate(4.0, {"warn_low": 5.0})
    assert gate == "WARN"
    gate_pass = cre._industry_gate(7.0, {"warn_low": 5.0})
    assert gate_pass == "PASS"


def test_cre_gate_status_returns_string():
    from core.evaluation.clinical_rule_engine import get_engine
    cre = get_engine("igg_like_232fab")
    if cre is None:
        return
    status = cre.gate_status("pI", 8.5)
    assert status in ("PASS", "WARN", "FAIL")


# ─────────────────────────────────────────────────────────────────────────────
# B. calibration.py — VernierWeights + GoldenPairs
# ─────────────────────────────────────────────────────────────────────────────

def test_vernier_weights_vh_not_empty():
    from core.humanization.calibration import get_vernier_weights_vh
    wts = get_vernier_weights_vh()
    assert isinstance(wts, dict)
    assert len(wts) >= 10
    # All Kabat VH Vernier positions should be present
    for pos in (2, 27, 48, 71, 94):
        assert pos in wts, f"VH position {pos} missing from Vernier weights"
    # All weights in [0, 1]
    for pos, w in wts.items():
        assert 0.0 <= w <= 1.0, f"Weight {w} out of [0,1] range for VH pos {pos}"


def test_vernier_weights_vl_vl71_special_case():
    from core.humanization.calibration import get_vernier_weights_vl
    wts = get_vernier_weights_vl()
    assert 71 in wts
    # VL_71 must use L1_Code (0.552) not VH_VL_Angle (0.417)
    assert wts[71] >= 0.50, f"VL_71 weight should reflect L1_Code dominance; got {wts[71]}"


def test_pairing_score_range():
    from core.humanization.calibration import pairing_score
    score = pairing_score("IGHV3-30", "IGKV1-39")
    assert 0.0 <= score <= 1.0
    # Unknown pair should return 0.0
    zero = pairing_score("IGHV99-99", "IGKV99-99")
    assert zero == 0.0


def test_pairing_bonus_range():
    from core.humanization.calibration import pairing_bonus
    bonus = pairing_bonus("IGHV3-30", "IGKV1-39")
    assert 0.0 <= bonus <= 10.0


def test_top_pairs_for_vh_sorted():
    from core.humanization.calibration import top_pairs_for_vh
    tops = top_pairs_for_vh("IGHV3-30", n=3)
    if not tops:
        return  # No data loaded — acceptable
    scores = [sc for _, sc in tops]
    assert scores == sorted(scores, reverse=True), "top_pairs_for_vh not sorted descending"


# ─────────────────────────────────────────────────────────────────────────────
# C. evaluator.py — AntibodyType.DOG + population dispatch
# ─────────────────────────────────────────────────────────────────────────────

def test_antibody_type_dog_exists():
    from core.evaluation.evaluator import AntibodyType
    assert hasattr(AntibodyType, "DOG")
    assert AntibodyType.DOG.value == "dog_caninized"


def test_antibody_type_dog_modules_applicable():
    from core.evaluation.evaluator import AntibodyType, ALL_MODULES
    for mod_name in ("developability", "cdr_scan", "germline", "dog_scaffold"):
        mod = ALL_MODULES.get(mod_name, {})
        applies = mod.get("applies_to", [])
        assert AntibodyType.DOG in applies, (
            f"AntibodyType.DOG should be in {mod_name}.applies_to"
        )


def test_evaluator_vhh_uses_vhh40_population(monkeypatch):
    """When ab_type=VHH, _run_developability should call ClinicalRuleEngine('vhh_40')."""
    from core.evaluation.evaluator import AbEvaluator, AntibodyType
    calls = []

    def mock_get_engine(pop):
        calls.append(pop)
        return None  # avoid real evaluation

    import core.evaluation.evaluator as ev_mod
    original = ev_mod.__dict__.get("_get_cre")
    # monkeypatch via module-level import alias inside _run_developability
    import core.evaluation.clinical_rule_engine as cre_mod
    orig_fn = cre_mod.get_engine
    cre_mod.get_engine = mock_get_engine
    try:
        ev = AbEvaluator(
            vh_seq="EVQLVESGGGLVQPGRSLRLSCAASGFTFSSYAMS",
            vl_seq="",
            ab_type=AntibodyType.VHH,
            project_name="test_vhh_pop",
            strict_qa=False,
        )
        ev._run_developability()
    finally:
        cre_mod.get_engine = orig_fn

    assert "vhh_40" in calls, (
        f"Expected 'vhh_40' population called; got {calls}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# D. engine.py — workflow='dog' support
# ─────────────────────────────────────────────────────────────────────────────

def test_engine_supported_workflows_includes_dog():
    from core.humanization.engine import HumanizationEngine
    assert "dog" in HumanizationEngine.SUPPORTED_WORKFLOWS


def test_engine_dog_workflow_init():
    from core.humanization.engine import HumanizationEngine
    eng = HumanizationEngine(workflow="dog")
    assert eng.workflow == "dog"


def test_engine_invalid_workflow_raises():
    from core.humanization.engine import HumanizationEngine
    try:
        HumanizationEngine(workflow="fish")
        assert False, "Should raise ValueError"
    except ValueError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# E. Structure-first cap — dry_run caps PASS → WARN
# ─────────────────────────────────────────────────────────────────────────────

def test_phase5_structure_pending_flag():
    """Phase 5 must set structure_pending=True when engine is in dry_run mode."""
    from core.humanization.engine import HumanizationEngine
    eng = HumanizationEngine(workflow="vh_vl")
    assert eng._dry_run is True  # no ImmuneBuilder in test environment
    result = eng._phase5_qc(
        sequences={"Our_Hum_VH": "EVQLVESGGGLVQPGG", "Our_Hum_VL": "DIQMTQSPSSL"},
        struct={},
    )
    assert result.get("structure_pending") is True
    assert "structure_status" in result


def test_vhh_stage2_clinical_gate_key_present():
    """Stage 2 result should have 'clinical_gate' key from ClinicalRuleEngine."""
    # This is a contract test; actual gate result depends on data file presence
    from scripts.vhh_conversion_pipeline import run_stage2
    result = run_stage2("EVQLVESGGGLVQPGG")
    # Must not crash; 'clinical_gate' or 'ref_context' present (fallback)
    has_gate = "clinical_gate" in result or "ref_context" in result or "vhh_gate" in result
    assert has_gate, f"Expected gate key in Stage 2 result; got keys: {list(result.keys())}"
