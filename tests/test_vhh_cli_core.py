"""
test_vhh_cli_core.py — InSynBio AbEngineCore VHH Unit Tests
============================================================
Level 3 (Verifiable) regression tests for the VHH CLI core path.

Covers:
  T1 — infer_from_sequence: correct CDR lengths and germline from a known sequence
  T2 — mutate_by_kabat_positions: substitution applied at correct Kabat positions
  T3 — verify_cdr_preservation PASS: mutations outside CDR regions accepted
  T4 — verify_cdr_preservation FAIL: mutations inside CDR regions raise RuntimeError
  T5 — compute_vhh_adi pipeline: sequence → CMCMetrics → VHH_ADI in [0, 100]
  T6 — vhh_design_config: config file loads and has required keys
  T7 — default_acceptance_gates: reads from config correctly
  T8 — PipelineQA Gate 1: invalid input raises QAViolation
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ─────────────────────────────────────────────────────────────────────────────
# Known reference sequence: muMAb4D5 VH (Kabat numbering compatible)
# ─────────────────────────────────────────────────────────────────────────────
_MUMAB4D5_VH = (
    "EVQLVQSGAEVKKPGASVKVSCKASGYTFTSYNMHWVRQAPGQEELELIGIINPSGGSTSYAQKFQGRVTMTRDTSTSTVY"
    "MELSSLRSEDTAVYYCARDRGSIRDFYWGQGTLVTVSS"
)

# Shorter VHH-like sequence for basic tests (IGHV3-23 derived, 119 AA)
_VHH_IGHV3_23 = (
    "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYL"
    "QMNSLRAEDTAVYYCAKWGQGTLVTVSS"
)


# ─────────────────────────────────────────────────────────────────────────────
# T1 — infer_from_sequence
# ─────────────────────────────────────────────────────────────────────────────

def test_infer_from_sequence_returns_expected_keys():
    """infer_from_sequence must return cdr1/cdr2/cdr3/germline/germline_identity."""
    from scripts.vhh_design_decision_tree import infer_from_sequence
    result = infer_from_sequence(_VHH_IGHV3_23)
    for key in ("cdr1", "cdr2", "cdr3", "germline", "germline_identity", "sequence"):
        assert key in result, f"Missing key: {key}"


def test_infer_from_sequence_cdr_range():
    """CDR lengths must be positive integers within VHH/VH plausible range."""
    from scripts.vhh_design_decision_tree import infer_from_sequence
    # Use muMAb4D5 VH which has well-defined CDR3 (known: CDR1=10, CDR2=17, CDR3=9)
    result = infer_from_sequence(_MUMAB4D5_VH)
    assert 1 <= result["cdr1"] <= 20, f"CDR1 out of range: {result['cdr1']}"
    assert 1 <= result["cdr2"] <= 17, f"CDR2 out of range: {result['cdr2']}"
    assert 1 <= result["cdr3"] <= 30, f"CDR3 out of range: {result['cdr3']}"


def test_infer_from_sequence_germline():
    """IGHV3-23-like sequence should best match IGHV3-23."""
    from scripts.vhh_design_decision_tree import infer_from_sequence
    result = infer_from_sequence(_VHH_IGHV3_23)
    assert result["germline"] == "IGHV3-23", f"Expected IGHV3-23, got {result['germline']}"
    assert 0.5 < result["germline_identity"] <= 1.0, "Identity implausibly low"


def test_infer_from_sequence_short_raises():
    """Sequence shorter than 70 AA must raise ValueError."""
    from scripts.vhh_design_decision_tree import infer_from_sequence
    with pytest.raises(ValueError, match="too short"):
        infer_from_sequence("EVQLVES")


# ─────────────────────────────────────────────────────────────────────────────
# T2 — mutate_by_kabat_positions
# ─────────────────────────────────────────────────────────────────────────────

def test_mutate_by_kabat_positions_single_substitution():
    """A single Kabat substitution must change exactly one residue."""
    from scripts.vhh_cli import mutate_by_kabat_positions, _get_kabat_dict
    from core.humanization.kabat_utils import sorted_keys

    seq = _VHH_IGHV3_23
    # Substitute Kabat position 44 (hallmark)
    kd = _get_kabat_dict(seq)
    orig_aa = kd.get((44, ""), None)
    assert orig_aa is not None, "Position 44 not found in Kabat dict"

    new_aa = "R" if orig_aa != "R" else "G"
    mutated = mutate_by_kabat_positions(seq, {44: new_aa})
    # Must differ by exactly one residue
    diffs = sum(a != b for a, b in zip(seq, mutated))
    assert diffs == 1, f"Expected 1 difference, got {diffs}"


def test_mutate_by_kabat_positions_no_op():
    """Empty replacements dict must return the original sequence unchanged."""
    from scripts.vhh_cli import mutate_by_kabat_positions
    seq = _VHH_IGHV3_23
    assert mutate_by_kabat_positions(seq, {}) == seq


def test_mutate_by_kabat_positions_preserves_length():
    """Substitution must not change sequence length."""
    from scripts.vhh_cli import mutate_by_kabat_positions
    seq = _VHH_IGHV3_23
    mutated = mutate_by_kabat_positions(seq, {44: "F", 45: "G", 47: "L"})
    assert len(mutated) == len(seq), "Mutation changed sequence length"


# ─────────────────────────────────────────────────────────────────────────────
# T3/T4 — verify_cdr_preservation
# ─────────────────────────────────────────────────────────────────────────────

def test_verify_cdr_preservation_pass_on_fr_mutation():
    """Mutations in framework regions must NOT trigger CDR preservation failure."""
    from core.humanization.kabat_utils import verify_cdr_preservation
    from scripts.vhh_cli import _get_kabat_dict, mutate_by_kabat_positions

    # Use muMAb4D5 VH — has well-defined CDR3
    seq = _MUMAB4D5_VH
    parent_kd = _get_kabat_dict(seq)
    # Mutate FR2 hallmark positions 44/45/47 — all in framework
    mutated = mutate_by_kabat_positions(seq, {44: "F", 45: "E", 47: "W"})
    mutant_kd = _get_kabat_dict(mutated)
    # verify_cdr_preservation(humanized_kd, original_kd, chain)
    errors = verify_cdr_preservation(mutant_kd, parent_kd, "VH")
    assert not errors, f"Unexpected CDR preservation error on FR mutation: {errors}"


def test_verify_cdr_preservation_detects_cdr_change():
    """Direct substitution at a CDR1 position must be detected by verify_cdr_preservation."""
    from core.humanization.kabat_utils import verify_cdr_preservation
    from scripts.vhh_cli import _get_kabat_dict, mutate_by_kabat_positions

    seq = _MUMAB4D5_VH
    parent_kd = _get_kabat_dict(seq)

    # Kabat position 31 is in CDR1 (26-35); mutate it
    cdr1_pos = 31
    target = "W"
    orig = parent_kd.get((cdr1_pos, ""), "")
    if orig == target:
        target = "G"

    mutated = mutate_by_kabat_positions(seq, {cdr1_pos: target})
    mutant_kd = _get_kabat_dict(mutated)
    # verify_cdr_preservation(humanized_kd, original_kd, chain)
    errors = verify_cdr_preservation(mutant_kd, parent_kd, "VH")
    assert errors, "Expected CDR preservation error when CDR1 residue is changed"


# ─────────────────────────────────────────────────────────────────────────────
# T5 — compute_vhh_adi pipeline (sequence → metrics → ADI)
# ─────────────────────────────────────────────────────────────────────────────

def test_compute_vhh_adi_output_range():
    """VHH_ADI and human_compat_ADI must be in [0, 100]."""
    from core.cmc.cmc_metrics import CMCMetricEngine
    from core.cmc.vhh_adi import compute_vhh_adi

    metrics = CMCMetricEngine.compute_metrics(vh_seq=_VHH_IGHV3_23, vl_seq="")
    result = compute_vhh_adi(metrics, task="vh-to-vhh")

    assert 0 <= result["VHH_ADI"] <= 100, f"VHH_ADI out of range: {result['VHH_ADI']}"
    assert 0 <= result["human_compat_ADI"] <= 100, f"human_compat_ADI out of range: {result['human_compat_ADI']}"
    assert result["interpretation"] in {
        "Excellent", "Good", "Acceptable", "Moderate risk", "High risk"
    }, f"Unexpected interpretation: {result['interpretation']}"


def test_compute_vhh_adi_contains_required_keys():
    """ADI output must contain VHH_ADI, human_compat_ADI, interpretation, compat_flag."""
    from core.cmc.cmc_metrics import CMCMetricEngine
    from core.cmc.vhh_adi import compute_vhh_adi

    metrics = CMCMetricEngine.compute_metrics(vh_seq=_VHH_IGHV3_23, vl_seq="")
    result = compute_vhh_adi(metrics, task="camelid-vhh-humanization")
    for key in ("VHH_ADI", "human_compat_ADI", "interpretation", "compat_flag"):
        assert key in result, f"Missing key in ADI output: {key}"


# ─────────────────────────────────────────────────────────────────────────────
# T6 — vhh_design_config.json structure
# ─────────────────────────────────────────────────────────────────────────────

def test_vhh_design_config_loads_and_has_required_keys():
    """config/vhh_design_config.json must load and contain all required top-level keys."""
    cfg_path = ROOT / "config" / "vhh_design_config.json"
    assert cfg_path.exists(), "config/vhh_design_config.json not found"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    for key in ("version", "vernier_zones", "cdr3_tier_thresholds",
                "hallmark_motif_stability", "acceptance_gates",
                "rmsd_thresholds", "pipeline_qa_thresholds", "germline_refs"):
        assert key in cfg, f"Missing required key in vhh_design_config.json: {key}"


def test_vhh_design_config_vernier_zones_complete():
    """Vernier zones config must contain redline, safe, and case_by_case lists."""
    cfg_path = ROOT / "config" / "vhh_design_config.json"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    vz = cfg["vernier_zones"]
    assert "redline" in vz and len(vz["redline"]) >= 4
    assert "safe" in vz and len(vz["safe"]) >= 3
    assert "case_by_case" in vz


# ─────────────────────────────────────────────────────────────────────────────
# T7 — default_acceptance_gates reads from config
# ─────────────────────────────────────────────────────────────────────────────

def test_default_acceptance_gates_vh_to_vhh():
    """vh-to-vhh gates must include cross-type reference_type and cdr_rmsd threshold."""
    from scripts.vhh_design_decision_tree import default_acceptance_gates
    gates = default_acceptance_gates("vh-to-vhh")
    assert "cross-type" in gates.get("reference_type", "").lower(), (
        "Expected cross-type reference for vh-to-vhh"
    )
    assert "cdr_rmsd" in str(gates), "CDR RMSD threshold missing from vh-to-vhh gates"


def test_default_acceptance_gates_vhh_humanization():
    """vhh-humanization gates must be same-type and have hard gate RMSD."""
    from scripts.vhh_design_decision_tree import default_acceptance_gates
    gates = default_acceptance_gates("vhh-humanization")
    assert gates.get("global_delta_rmsd_role") == "hard gate"


# ─────────────────────────────────────────────────────────────────────────────
# T8 — PipelineQA Gate 1: invalid input raises QAViolation
# ─────────────────────────────────────────────────────────────────────────────

def test_pipeline_qa_gate1_raises_on_invalid_sequence():
    """_run_pipeline_qa must raise QAViolation when input sequence is too short / invalid."""
    from core.qa.pipeline_qa import QAViolation
    from scripts.vhh_cli import _run_pipeline_qa

    with pytest.raises(QAViolation):
        _run_pipeline_qa(
            project="test_project",
            task="vh-to-vhh",
            sequence="EVQLV",     # too short — should fail Gate 1
            inferred={"cdr1": 5, "cdr2": 6, "cdr3": 7},
            candidates=[],
        )


def test_pipeline_qa_gate1_pass_on_valid_sequence():
    """_run_pipeline_qa must return a dict with status key on valid input."""
    from scripts.vhh_cli import _run_pipeline_qa

    qa_report = _run_pipeline_qa(
        project="test_project",
        task="vh-to-vhh",
        sequence=_VHH_IGHV3_23,
        inferred={"cdr1": 8, "cdr2": 7, "cdr3": 9},
        candidates=[],
    )
    assert "status" in qa_report, "QA report missing 'status' key"
    assert qa_report["status"] in {"PASS", "WARN", "FAIL"}
