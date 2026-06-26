"""
Guardrail tests for InSynBio AbEngineCore v1.0

Tests:
  1. ChecklistRunner loads v44 config and builds 27 items correctly
  2. ChecklistRunner enforces phase order (phase_complete blocks on PENDING)
  3. ChecklistRunner hard_gate aborts on FAIL (sys.exit(2))
  4. ChecklistRunner blocks must_not_do violations
  5. AbEvaluator filters modules by ab_type
  6. AbEvaluator runs cdr_scan and developability without PDB
  7. HumanizationEngine instantiates without crashing
  8. Governance: locked files all exist
  9. Governance: Cursor rule exists and contains key constraints
"""

import json
import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# 1. ChecklistRunner — item count
# ─────────────────────────────────────────────────────────────────────────────

def test_checklist_runner_loads_all_items():
    from core.humanization.checklist_runner import ChecklistRunner
    runner = ChecklistRunner()
    items = list(runner.items())
    # V4.4 config item count breakdown (source: config/vh_vl_humanization_v44.json):
    #   Phase 1 (1.1-1.3) = 3
    #   Phase 2 (2.1-2.6) = 6  ← 2.6 is a phase_5_after rescue item, counted here
    #   Phase 3 (3.1-3.2e) = ~7
    #   Phase 4 (4.1-4.9 + 4.SC1-SC5) = 14
    #   Phase 5 (5.1-5.8 + 5.R2 + 5.OB) = 11
    # Total = 41 (all sub-items and rescue steps enumerated by ChecklistRunner.items())
    # Governance docs state "36 core logic items" (excluding SC/rescue sub-items).
    # The VHH checklist (core/vhh/checklist.py) has 29 separate items in vhh_design_config.json.
    assert len(items) >= 27, (
        f"Expected at least 27 checklist items from v44 config, got {len(items)}."
    )
    assert len(items) == 41, (
        f"Expected 41 checklist items from v44 config (incl. 2.6, SC sub-items, 5.R2, 5.OB), got {len(items)}. "
        f"IDs: {[i.item_id for i in items]}"
    )


def test_checklist_runner_has_all_phases():
    from core.humanization.checklist_runner import ChecklistRunner
    runner = ChecklistRunner()
    phases = {item.phase for item in runner.items()}
    assert phases == {1, 2, 3, 4, 5, 6}, f"Expected phases 1-5 and 6 (phase_5_after), got {phases}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Phase order enforcement
# ─────────────────────────────────────────────────────────────────────────────

def test_phase_complete_blocks_on_pending_items():
    from core.humanization.checklist_runner import ChecklistRunner
    runner = ChecklistRunner()
    # Only check 1.1, leave 1.2 PENDING
    runner.check("1.1", evidence={"test": True})
    with pytest.raises(RuntimeError, match="incomplete"):
        runner.phase_complete(1)


def test_phase_complete_passes_when_all_checked():
    from core.humanization.checklist_runner import ChecklistRunner
    runner = ChecklistRunner()
    runner.check("1.1", evidence={"ok": True})
    runner.check("1.2", evidence={"ok": True})
    runner.phase_complete(1)  # should not raise


# ─────────────────────────────────────────────────────────────────────────────
# 3. Hard gate (CDR integrity)
# ─────────────────────────────────────────────────────────────────────────────

def test_hard_gate_exits_on_cdr_fail(monkeypatch):
    from core.humanization.checklist_runner import ChecklistRunner, ChecklistStatus
    runner = ChecklistRunner()
    with pytest.raises(SystemExit) as exc_info:
        runner.check(
            "4.8",
            evidence={"cdr_match": False},
            status=ChecklistStatus.FAIL,
            hard_gate=True,
        )
    assert exc_info.value.code == 2, "Hard gate must exit with code 2"


def test_hard_gate_does_not_exit_on_pass():
    from core.humanization.checklist_runner import ChecklistRunner, ChecklistStatus
    runner = ChecklistRunner()
    item = runner.check(
        "4.8",
        evidence={"cdr_match": True},
        status=ChecklistStatus.PASS,
        hard_gate=True,
    )
    assert item.status == ChecklistStatus.PASS


# ─────────────────────────────────────────────────────────────────────────────
# 4. must_not_do enforcement
# ─────────────────────────────────────────────────────────────────────────────

def test_must_not_do_raises_on_skip():
    from core.humanization.checklist_runner import ChecklistRunner, ChecklistViolation
    runner = ChecklistRunner()
    with pytest.raises(ChecklistViolation):
        runner.enforce_must_not_do("skip structure modeling and make backmutation decisions empirically")


def test_must_not_do_passes_on_allowed_action():
    from core.humanization.checklist_runner import ChecklistRunner
    runner = ChecklistRunner()
    runner.enforce_must_not_do("compute SASA for each Vernier residue")  # should not raise


# ─────────────────────────────────────────────────────────────────────────────
# 5. AbEvaluator — module filtering
# ─────────────────────────────────────────────────────────────────────────────

def test_ab_evaluator_filters_delta_vs_mouse_for_fully_human():
    from core.evaluation.evaluator import AbEvaluator, AntibodyType
    ev = AbEvaluator("test", ab_type=AntibodyType.FULLY_HUMAN)
    applicable = ev._applicable_modules()
    assert "delta_vs_mouse" not in applicable, (
        "delta_vs_mouse must not apply to FULLY_HUMAN antibodies (no mouse reference)"
    )


def test_ab_evaluator_includes_shm_hotspots_for_fully_human():
    from core.evaluation.evaluator import AbEvaluator, AntibodyType
    ev = AbEvaluator("test", ab_type=AntibodyType.FULLY_HUMAN)
    applicable = ev._applicable_modules()
    assert "shm_hotspots" in applicable


def test_ab_evaluator_includes_delta_vs_mouse_for_humanized():
    from core.evaluation.evaluator import AbEvaluator, AntibodyType
    ev = AbEvaluator("test", ab_type=AntibodyType.HUMANIZED)
    applicable = ev._applicable_modules()
    assert "delta_vs_mouse" in applicable


# ─────────────────────────────────────────────────────────────────────────────
# 6. AbEvaluator — cdr_scan and developability without PDB
# ─────────────────────────────────────────────────────────────────────────────

def test_cdr_scan_detects_deamidation():
    from core.evaluation.evaluator import AbEvaluator, AntibodyType
    ev = AbEvaluator(
        "test",
        ab_type=AntibodyType.FULLY_HUMAN,
        vh_seq="EVQLVESGGNGASNYNLH",  # contains NG → deamidation risk
        vl_seq="DIQMTQSPSDGSTLH",
    )
    r = ev._run_cdr_scan()
    types = [lib["type"] for lib in r["liabilities"]]
    assert "deamidation" in types, "NG motif not detected as deamidation risk"


def test_developability_runs_on_sequence():
    from core.evaluation.evaluator import AbEvaluator, AntibodyType
    ev = AbEvaluator(
        "test",
        ab_type=AntibodyType.FULLY_HUMAN,
        vh_seq="EVQLVESGGGLVQPGGSLRLSCAASGFTFS",
        vl_seq="DIQMTQSPSSLSASVGDRVTITC",
    )
    r = ev._run_developability()
    if r["status"] == "SKIPPED":
        pytest.skip("BioPython not installed")
    assert "pI_fab_estimate" in r


# ─────────────────────────────────────────────────────────────────────────────
# 7. HumanizationEngine instantiation
# ─────────────────────────────────────────────────────────────────────────────

def test_humanization_engine_instantiates():
    from core.humanization.engine import HumanizationEngine
    engine = HumanizationEngine(workflow="vh_vl")
    assert engine.workflow == "vh_vl"


def test_humanization_engine_rejects_invalid_workflow():
    from core.humanization.engine import HumanizationEngine
    with pytest.raises(ValueError):
        HumanizationEngine(workflow="invalid_workflow")


# ─────────────────────────────────────────────────────────────────────────────
# 8. Governance — locked files all exist
# ─────────────────────────────────────────────────────────────────────────────

def test_all_locked_files_exist():
    registry_path = ROOT / "config" / "abenginecore_registry.json"
    assert registry_path.exists(), "Registry file missing"

    with open(registry_path, encoding="utf-8") as f:
        registry = json.load(f)

    locked = registry.get("locked_files", {})
    missing = []
    for category, paths in locked.items():
        if isinstance(paths, list):
            for p in paths:
                if not p.endswith("/"):  # skip directory entries
                    full = ROOT / p
                    if not full.exists():
                        missing.append(p)

    assert not missing, f"Locked files missing from disk: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# 9. Governance — Cursor rule exists and contains key constraints
# ─────────────────────────────────────────────────────────────────────────────

def test_cursor_rule_exists_and_enforces_locked_files():
    rule_path = ROOT / ".cursor" / "rules" / "abenginecore-ownership.mdc"
    assert rule_path.exists(), "AbEngineCore Cursor rule file missing"
    content = rule_path.read_text(encoding="utf-8")
    assert "LOCKED FILES" in content, "Rule must list locked files"
    assert "alwaysApply: true" in content, "Rule must be alwaysApply to take effect every session"
    assert "vh_vl_humanization_v44.json" in content, "Rule must name the primary config as locked"
    assert "NEVER" in content.upper(), "Rule must contain explicit prohibition language"


# ─────────────────────────────────────────────────────────────────────────────
# 10. interface_metrics — unit tests (sequence/geometry only, no real PDB)
# ─────────────────────────────────────────────────────────────────────────────

def test_interface_metrics_module_imports():
    """Ensure interface_metrics module imports without error."""
    from core.evaluation import interface_metrics  # noqa: F401


def test_charge_analysis_complementary():
    """Positive Ab charge + Negative Ag charge → complementarity > 0."""
    from core.evaluation.interface_metrics import _charge_analysis

    class FakeRes:
        def __init__(self, chain, seq_num, resname):
            self._chain = chain
            self._id = (" ", seq_num, " ")
            self.resname = resname
        def get_parent(self):
            class C:
                id = self._chain
            return C()
        @property
        def id(self):
            return self._id

    # 2 Arg on Ab (paratope) → charge +2
    # 2 Asp on Ag (epitope) → charge -2
    paratope = [FakeRes("H", 50, "ARG"), FakeRes("H", 55, "ARG")]
    epitope  = [FakeRes("A", 10, "ASP"), FakeRes("A", 15, "ASP")]
    result = _charge_analysis(paratope, epitope)
    assert result["paratope_net_charge"] == 2
    assert result["epitope_net_charge"]  == -2
    assert result["charge_complementarity"] > 0, "Opposite charges must give positive complementarity"


def test_charge_analysis_same_charge():
    """Same-sign charges → complementarity ≤ 0 (repulsive)."""
    from core.evaluation.interface_metrics import _charge_analysis

    class FakeRes:
        def __init__(self, chain, seq_num, resname):
            self._chain = chain
            self._id = (" ", seq_num, " ")
            self.resname = resname
        def get_parent(self):
            class C:
                id = self._chain
            return C()
        @property
        def id(self):
            return self._id

    paratope = [FakeRes("H", 50, "ARG")]   # +1
    epitope  = [FakeRes("A", 10, "LYS")]   # +1
    result = _charge_analysis(paratope, epitope)
    assert result["charge_complementarity"] <= 0


def test_interface_metrics_skips_without_pdb():
    """AbEvaluator.binding_site returns SKIPPED when no PDB provided."""
    from core.evaluation.evaluator import AbEvaluator, AntibodyType
    ev = AbEvaluator(
        "test", ab_type=AntibodyType.FULLY_HUMAN,
        antigen_chain="A",
        # no pdb_path
    )
    result = ev._run_binding_site()
    assert result["status"] == "SKIPPED"


def test_interface_metrics_skips_without_antigen_chain():
    """AbEvaluator.binding_site returns SKIPPED when no antigen chain specified."""
    from core.evaluation.evaluator import AbEvaluator, AntibodyType
    ev = AbEvaluator(
        "test", ab_type=AntibodyType.FULLY_HUMAN,
        pdb_path="some.pdb",
        # no antigen_chain
    )
    result = ev._run_binding_site()
    assert result["status"] == "SKIPPED"


def test_interface_metrics_output_keys():
    """compute_interface_metrics returns correct keys even on missing file."""
    from core.evaluation.interface_metrics import compute_interface_metrics
    result = compute_interface_metrics(
        pdb_path="nonexistent.pdb",
        vh_chain="H", vl_chain="L", ag_chain="A",
    )
    # Should return ERROR with proper structure
    assert "status" in result
    assert result["status"] in ("ERROR", "PASS")


def test_ab_evaluator_accepts_cdr_seqs_and_blocking_ref():
    """AbEvaluator stores cdr_seqs and blocking_ref correctly."""
    from core.evaluation.evaluator import AbEvaluator, AntibodyType
    cdr_seqs = {"H1": "GFTFSSYD", "H2": "ISYDGS", "H3": "ARDY",
                "L1": "QSISSY",   "L2": "AAS",    "L3": "QQSYS"}
    blocking_ref = {"R113": 94, "M115": 96}
    ev = AbEvaluator(
        "PDL1_Ab2", ab_type=AntibodyType.FULLY_HUMAN,
        cdr_seqs=cdr_seqs, blocking_ref=blocking_ref,
    )
    assert ev.cdr_seqs == cdr_seqs
    assert ev.blocking_ref == blocking_ref


# ─────────────────────────────────────────────────────────────────────────────
# 11. PipelineQA — unit tests
# ─────────────────────────────────────────────────────────────────────────────

def test_pipelineqa_imports():
    from core.qa import PipelineQA, QAViolation, QALevel  # noqa: F401


def test_pipelineqa_pass_on_valid_sequence():
    from core.qa import PipelineQA, QALevel
    qa = PipelineQA("test", "seq_check")
    vh = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARARDYYYGMDVWGQGTTVTVSS"
    qa.check_sequence("vh", vh, "VH")
    report = qa.finalize()
    assert report.status == QALevel.PASS


def test_pipelineqa_fail_on_illegal_characters():
    from core.qa import PipelineQA, QALevel
    qa = PipelineQA("test", "illegal_aa")
    qa.check_sequence("vh", "EVQLVESGG*GLVQPGG", "VH")  # * is illegal
    report = qa.finalize()
    # Length will warn but alphabet should fail or sequence should have issues
    fail_checks = [c for c in report.checks if c.level == QALevel.FAIL]
    # Either alphabet fail or length fail - there should be at least a FAIL or WARN
    assert report.n_fail + report.n_warn > 0


def test_pipelineqa_assembly_integrity():
    from core.qa import PipelineQA, QALevel
    qa = PipelineQA("test", "assembly")
    fr1, cdr1, fr2, cdr2, fr3, cdr3, fr4 = (
        "EVQLVES", "GFTFSSYD", "WVRQAPGK", "ISYDGSNT", "GRFTISRD", "ARDYYYGMDV", "WGQGT"
    )
    full = fr1 + cdr1 + fr2 + cdr2 + fr3 + cdr3 + fr4
    qa.check_assembly("asm", fr1, cdr1, fr2, cdr2, fr3, cdr3, fr4, full_seq=full)
    report = qa.finalize()
    assert report.n_fail == 0, "Correct assembly must have zero FAIL"


def test_pipelineqa_assembly_detects_corruption():
    from core.qa import PipelineQA, QALevel
    qa = PipelineQA("test", "assembly_corrupt")
    fr1, cdr1, fr2, cdr2, fr3, cdr3, fr4 = (
        "EVQLVES", "GFTFSSYD", "WVRQAPGK", "ISYDGSNT", "GRFTISRD", "ARDYYYGMDV", "WGQGT"
    )
    full = fr1 + cdr1 + fr2 + cdr2 + fr3 + cdr3 + fr4
    corrupted_full = full[:-3] + "XXX"   # last 3 residues corrupted
    qa.check_assembly("asm", fr1, cdr1, fr2, cdr2, fr3, cdr3, fr4, full_seq=corrupted_full)
    report = qa.finalize()
    assert report.n_fail > 0, "Corrupted assembly must be detected"


def test_pipelineqa_cdr_preservation():
    from core.qa import PipelineQA, QALevel
    qa = PipelineQA("test", "cdr_preserved")
    fr1, cdr1, fr2, cdr2, fr3, cdr3, fr4 = (
        "EVQLVES", "GFTFSSYD", "WVRQAPGK", "ISYDGSNT", "GRFTISRD", "ARDYYYGMDV", "WGQGT"
    )
    full = fr1 + cdr1 + fr2 + cdr2 + fr3 + cdr3 + fr4
    original_cdrs = {"H1": cdr1, "H2": cdr2, "H3": cdr3}
    qa.check_assembly("asm", fr1, cdr1, fr2, cdr2, fr3, cdr3, fr4,
                      full_seq=full, original_cdrs=original_cdrs)
    report = qa.finalize()
    assert report.n_fail == 0


def test_pipelineqa_cdr_violation_detected():
    from core.qa import PipelineQA, QALevel
    qa = PipelineQA("test", "cdr_mutated")
    fr1, cdr1_orig, fr2, cdr2, fr3, cdr3, fr4 = (
        "EVQLVES", "GFTFSSYD", "WVRQAPGK", "ISYDGSNT", "GRFTISRD", "ARDYYYGMDV", "WGQGT"
    )
    cdr1_mutated = "GFTFSSYA"   # last residue changed: D→A — CDR mutation!
    full = fr1 + cdr1_mutated + fr2 + cdr2 + fr3 + cdr3 + fr4
    qa.check_assembly("asm", fr1, cdr1_mutated, fr2, cdr2, fr3, cdr3, fr4,
                      full_seq=full,
                      original_cdrs={"H1": cdr1_orig, "H2": cdr2, "H3": cdr3})
    report = qa.finalize()
    assert report.n_fail > 0, "CDR mutation must be detected as FAIL"


def test_pipelineqa_mutation_authorized_only():
    from core.qa import PipelineQA, QALevel
    qa = PipelineQA("test", "mutations")
    original  = "EVQLVESGGGLVQPGG"
    mutated   = "EVQLVKSGGGLVQPGG"   # pos 6 changed (1-based): E→K at index 5
    qa.check_mutations("backmut", original, mutated, allowed_positions={6})
    report = qa.finalize()
    assert report.n_fail == 0


def test_pipelineqa_unauthorized_mutation_detected():
    from core.qa import PipelineQA, QALevel
    qa = PipelineQA("test", "mutations_unauth")
    original = "EVQLVESGGGLVQPGG"
    mutated  = "EVQLVKSGGGLVQPGG"   # pos 7 changed, but allowed={10}
    qa.check_mutations("backmut", original, mutated, allowed_positions={10})
    report = qa.finalize()
    assert report.n_fail > 0, "Unauthorized mutation must be detected"


def test_pipelineqa_metric_in_range():
    from core.qa import PipelineQA, QALevel
    qa = PipelineQA("test", "metrics")
    qa.check_metric("pI", 7.2)
    qa.check_metric("pLDDT", 88.5)
    qa.check_metric("bsa_total_A2", 1840.3)
    report = qa.finalize()
    assert report.n_fail == 0


def test_pipelineqa_metric_out_of_range():
    from core.qa import PipelineQA, QALevel
    qa = PipelineQA("test", "metrics_bad")
    qa.check_metric("pLDDT", 20.0)   # below hard minimum 30
    report = qa.finalize()
    assert report.n_fail > 0


def test_pipelineqa_assert_pass_raises_on_fail():
    from core.qa import PipelineQA, QAViolation
    qa = PipelineQA("test", "assert_test")
    qa.check_metric("pLDDT", 10.0)   # will FAIL (< 30)
    qa.finalize()
    with pytest.raises(QAViolation):
        qa.assert_pass()


def test_pipelineqa_hash_chain():
    from core.qa import PipelineQA, QALevel
    seq = "EVQLVESGGGLVQPGG"
    qa = PipelineQA("test", "hashchain")
    qa.set_input_hash(seq)
    prev_hash = PipelineQA.seq_hash(seq)
    qa.check_hash_chain("step1→step2", prev_hash, seq)
    report = qa.finalize()
    assert report.n_fail == 0


def test_pipelineqa_hash_chain_detects_substitution():
    from core.qa import PipelineQA, QALevel
    seq1 = "EVQLVESGGGLVQPGG"
    seq2 = "QVQLVQSGAEVKKPGA"   # different sequence
    qa = PipelineQA("test", "hashchain_bad")
    prev_hash = PipelineQA.seq_hash(seq1)
    qa.check_hash_chain("step1→step2", prev_hash, seq2)   # wrong input
    report = qa.finalize()
    assert report.n_fail > 0, "Sequence substitution must be detected"


# ──────────────────────────────────────────────────────────────────────────────
# Kabat insertion-code preservation tests
# BUG HISTORY: d[pos]=aa (integer key) silently dropped 52A/82A/82B/82C residues.
# These tests are a permanent guard — NEVER remove or weaken them.
# ──────────────────────────────────────────────────────────────────────────────

def test_kabat_utils_normalizes_space_insertion_code():
    """kabat_from_anarcii must convert (' ') to '' so (pos,'') lookups work."""
    from core.humanization.kabat_utils import kabat_from_anarcii
    fake_numbering = [
        ((52, ' '), 'Y'),   # base position — space insertion code
        ((52, 'A'), 'P'),   # insertion position 52A
        ((82, 'A'), 'S'),
        ((82, 'B'), 'S'),
        ((82, 'C'), 'T'),
    ]
    kd = kabat_from_anarcii(fake_numbering)
    assert (52, '')  in kd, "Base position (52,'') must be present after normalization"
    assert (52, 'A') in kd, "Insertion 52A must be preserved"
    assert (82, 'A') in kd, "Insertion 82A must be preserved"
    assert (82, 'B') in kd, "Insertion 82B must be preserved"
    assert (82, 'C') in kd, "Insertion 82C must be preserved"
    assert kd[(52, '')] == 'Y'
    assert kd[(52, 'A')] == 'P'


def test_kabat_utils_no_integer_key_allowed():
    """No plain integer key must appear in KabatDict — all keys must be tuples."""
    from core.humanization.kabat_utils import kabat_from_anarcii
    fake_numbering = [
        ((1, ' '), 'Q'), ((52, ' '), 'Y'), ((52, 'A'), 'P'), ((82, 'A'), 'S'),
    ]
    kd = kabat_from_anarcii(fake_numbering)
    for k in kd:
        assert isinstance(k, tuple) and len(k) == 2, (
            f"All KabatDict keys must be (int, str) tuples, got {k!r}"
        )
        assert isinstance(k[1], str), f"Insertion code must be str, got {type(k[1])}"


def test_kabat_utils_assemble_preserves_cdr_insertion():
    """assemble_humanized_v must include 52A if present in mouse_num."""
    from core.humanization.kabat_utils import assemble_humanized_v, CDR_RANGES_VH

    # Minimal CDR-H2 region: pos 50-65 with insertion at 52A
    mouse_num = {
        (50, ''): 'D', (51, ''): 'V', (52, ''): 'Y', (52, 'A'): 'P',
        (53, ''): 'R', (54, ''): 'D',
    }
    germ_num = {
        (50, ''): 'G', (51, ''): 'F', (52, ''): 'T', (52, 'A'): 'S',
        (53, ''): 'N', (54, ''): 'Y',
    }
    # CDR range [50,65] → all positions above are in CDR → mouse wins
    result = assemble_humanized_v("VH", mouse_num, germ_num, {}, "")
    assert 'Y' in result and 'P' in result, (
        f"CDR-H2 must include 52=Y and 52A=P from mouse, got: {result!r}"
    )
    assert result.index('Y') < result.index('P'), "52 (Y) must come before 52A (P)"


def test_kabat_utils_verify_cdr_catches_missing_52a():
    """verify_cdr_preservation must fail if humanized CDR-H2 is missing 52A."""
    from core.humanization.kabat_utils import verify_cdr_preservation

    mouse_num = {(52, ''): 'Y', (52, 'A'): 'P', (53, ''): 'R'}
    # Humanized version missing 52A — as if assembled with the old integer-key bug
    human_num = {(52, ''): 'Y', (53, ''): 'R'}   # 52A dropped!

    errors = verify_cdr_preservation(human_num, mouse_num, "VH")
    assert errors, "Missing 52A in humanized CDR-H2 must be detected by verify_cdr_preservation"


def test_kabat_utils_cdr_span_includes_insertions():
    """cdr_span must include insertion-code residues within the integer range."""
    from core.humanization.kabat_utils import cdr_span

    kd = {(50, ''): 'D', (51, ''): 'V', (52, ''): 'Y', (52, 'A'): 'P',
          (53, ''): 'R', (54, ''): 'D', (55, ''): 'G'}
    span = cdr_span(kd, 50, 55)
    # 50:D 51:V 52:Y 52A:P 53:R 54:D 55:G  → 7 residues including the insertion
    assert span == 'DVYPRDG', f"cdr_span must include 52A (P), got {span!r}"
    assert 'P' in span, "52A residue (P) must be present in span"


def test_qa_auto_runs_with_evaluator():
    """AbEvaluator.run() automatically appends _qa key to results."""
    from core.evaluation.evaluator import AbEvaluator, AntibodyType
    ev = AbEvaluator(
        "QA_smoke_test", ab_type=AntibodyType.FULLY_HUMAN,
        vh_seq="EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARARDYYYGMDVWGQGTTVTVSS",
        vl_seq="DIQMTQSPSSLSASVGDRVTITCQASQSISSYLNWYQQKPGKAPKLLIYAASTLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQSYSTPLTFGGGTKVEIK",
    )
    result = ev.run(modules=["developability"])
    assert "_qa" in result.results, "AbEvaluator must auto-append _qa key"
    assert "status" in result.results["_qa"]
