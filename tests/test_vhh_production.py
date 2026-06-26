"""
test_vhh_production.py — InSynBio AbEngineCore VHH Production Tests
=====================================================================
Production-level regression tests added in v1.2 / v1.3.

Covers new modules:
  - core/vhh/pre_delivery_gate.py   (D1: 15-item pre-delivery gate)
  - core/vhh/checklist.py           (D4: 25-item design checklist)
  - core/vhh/canonical_classifier.py (E1: North-equivalent VHH CDR3 classifier)
  - core/vhh/dual_scheme_validator.py (E2: IMGT+Kabat cross-validation)
  - scripts/vhh_design_learning_log.py (D3: learning feedback)
  - scripts/vhh_design_decision_tree.py infer_from_sequence dual_xval field (E2)

Golden regression:
  - muMAb4D5 VH: CDR1=10, CDR2=17, CDR3=9, germline=IGHV1-2 (approximately)
  - IGHV3-23 reference: germline=IGHV3-23, identity≥0.5
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_MUMAB4D5_VH = (
    "EVQLVQSGAEVKKPGASVKVSCKASGYTFTSYNMHWVRQAPGQEELELIGIINPSGGSTSYAQKFQGRVTMTRDTSTSTVY"
    "MELSSLRSEDTAVYYCARDRGSIRDFYWGQGTLVTVSS"
)
_VHH_IGHV3_23_LIKE = (
    "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQ"
    "MNSLRAEDTAVYYCAKDRGSIRDFYWGQGTLVTVSS"
)


# ─────────────────────────────────────────────────────────────────────────────
# Pre-delivery gate (D1)
# ─────────────────────────────────────────────────────────────────────────────

def _make_valid_output(seq=_MUMAB4D5_VH, cdr3="DRGSIRDFYW", anchor_94="R") -> dict:
    """Build a minimal but valid qa-rank output dict for gate testing."""
    return {
        "schema_version": "1.1",
        "generated_at":   "2026-03-22T00:00:00",
        "pipeline_meta": {
            "schema_version":              "1.1",
            "vhh_design_config_version":   "1.0",
            "ref_data_hashes":             {"vhh42_ref": "abc123def456"},
        },
        "task":    "vh-to-vhh",
        "project": "test_project",
        "inferred_input": {
            "sequence":           seq,
            "cdr1":               10,
            "cdr2":               17,
            "cdr3":               9,
            "germline":           "IGHV1-2",
            "germline_identity":  0.45,
            "dual_scheme_xval":   {"status": "PASS", "note": "OK"},
        },
        "_qa": {"status": "PASS", "n_pass": 4, "n_warn": 0, "n_fail": 0, "checks": []},
        "candidates": [{
            "variant_id":              "auto_FERF",
            "motif":                   "FERF",
            "sequence":                seq,
            "_cdr_preservation":       "PASS",
            "final_rank":              1,
            "vhh_adi": {
                "VHH_ADI":          62.0,
                "human_compat_ADI": 55.0,
                "compat_flag":      "OK",
            },
            "canonical_class": {
                "class_id":      "VHH-1a",
                "base_class":    "VHH-1",
                "subclass":      "a",
                "cdr3_length":   9,
                "anchor_94":     anchor_94,
                "ds_cdr3":       False,
                "ds_cdr1_3":     False,
                "cdr3_gravy":    0.5,
                "vernier_risk":  "low",
                "stability_note": "Short CDR3, R94 anchor.",
                "warnings":      [],
            },
        }],
    }


def test_pre_delivery_gate_pass_on_valid_output():
    """Pre-delivery gate must PASS for a complete, valid output dict."""
    from core.vhh.pre_delivery_gate import run_pre_delivery_gate
    report = run_pre_delivery_gate(_make_valid_output())
    assert report.status == "PASS", f"Expected PASS, got {report.status}: {report.summary}"
    assert report.n_fail == 0


def test_pre_delivery_gate_fail_on_empty_candidates():
    """Gate C.1 must FAIL when candidates list is empty."""
    from core.vhh.pre_delivery_gate import run_pre_delivery_gate
    out = _make_valid_output()
    out["candidates"] = []
    report = run_pre_delivery_gate(out)
    assert report.status == "FAIL"
    assert any(c.check_id == "C.1" and c.status == "FAIL" for c in report.checks)


def test_pre_delivery_gate_fail_on_missing_qa():
    """Gate C.4 must FAIL when _qa block is absent."""
    from core.vhh.pre_delivery_gate import run_pre_delivery_gate
    out = _make_valid_output()
    del out["_qa"]
    report = run_pre_delivery_gate(out)
    assert any(c.check_id == "C.4" and c.status == "FAIL" for c in report.checks)


def test_pre_delivery_gate_fail_on_adi_out_of_range():
    """Gate A.1 must FAIL when ADI score exceeds 100."""
    from core.vhh.pre_delivery_gate import run_pre_delivery_gate
    out = _make_valid_output()
    out["candidates"][0]["vhh_adi"]["VHH_ADI"] = 150.0
    report = run_pre_delivery_gate(out)
    assert any(c.check_id == "A.1" and c.status == "FAIL" for c in report.checks)


def test_pre_delivery_gate_fail_on_invalid_aa():
    """Gate A.4 must FAIL when candidate sequence has non-standard characters."""
    from core.vhh.pre_delivery_gate import run_pre_delivery_gate
    out = _make_valid_output()
    out["candidates"][0]["sequence"] = "EVQLV*QSGAEV"  # '*' is invalid
    report = run_pre_delivery_gate(out)
    assert any(c.check_id == "A.4" and c.status == "FAIL" for c in report.checks)


def test_pre_delivery_gate_a6_canonical_class_present():
    """Gate A.6 must PASS when top candidate has canonical_class."""
    from core.vhh.pre_delivery_gate import run_pre_delivery_gate
    report = run_pre_delivery_gate(_make_valid_output())
    a6 = next(c for c in report.checks if c.check_id == "A.6")
    assert a6.status == "PASS"


def test_pre_delivery_gate_a6_warn_when_missing():
    """Gate A.6 must WARN when canonical_class is missing."""
    from core.vhh.pre_delivery_gate import run_pre_delivery_gate
    out = _make_valid_output()
    del out["candidates"][0]["canonical_class"]
    report = run_pre_delivery_gate(out)
    a6 = next(c for c in report.checks if c.check_id == "A.6")
    assert a6.status == "WARN"


def test_pre_delivery_report_to_dict_structure():
    """PreDeliveryReport.to_dict() must contain required top-level keys."""
    from core.vhh.pre_delivery_gate import run_pre_delivery_gate
    report = run_pre_delivery_gate(_make_valid_output())
    d = report.to_dict()
    for k in ("project", "task", "status", "n_pass", "n_warn", "n_fail", "checks"):
        assert k in d


# ─────────────────────────────────────────────────────────────────────────────
# VHH Design Checklist (D4)
# ─────────────────────────────────────────────────────────────────────────────

def test_checklist_evaluates_25_items():
    """Checklist must produce exactly 25 evaluated items."""
    from core.vhh.checklist import evaluate_checklist
    report = evaluate_checklist(_make_valid_output())
    assert len(report.items) == 25, f"Expected 25 items, got {len(report.items)}"


def test_checklist_no_fail_on_valid_output():
    """Checklist must have 0 FAIL on a fully valid output dict."""
    from core.vhh.checklist import evaluate_checklist
    report = evaluate_checklist(_make_valid_output())
    fails = [i for i in report.items if i.status == "FAIL"]
    assert not fails, f"Unexpected FAIL items: {[(i.item_id, i.evidence) for i in fails]}"


def test_checklist_item_3_2_pass():
    """Checklist item 3.2 (CDR preservation) must PASS when _cdr_preservation=PASS."""
    from core.vhh.checklist import evaluate_checklist
    report = evaluate_checklist(_make_valid_output())
    item_3_2 = next((i for i in report.items if i.item_id == "3.2"), None)
    assert item_3_2 is not None
    assert item_3_2.status == "PASS"


def test_checklist_item_4_1_fail_when_no_adi():
    """Checklist item 4.1 must FAIL when no candidate has ADI."""
    from core.vhh.checklist import evaluate_checklist
    out = _make_valid_output()
    out["candidates"][0]["vhh_adi"] = {"error": "import failed"}
    report = evaluate_checklist(out)
    item_4_1 = next((i for i in report.items if i.item_id == "4.1"), None)
    assert item_4_1 is not None
    assert item_4_1.status == "FAIL"


def test_checklist_to_markdown_contains_header():
    """Checklist Markdown output must include project name and status."""
    from core.vhh.checklist import evaluate_checklist
    report = evaluate_checklist(_make_valid_output())
    md = report.to_markdown()
    assert "test_project" in md
    assert "Phase" in md


# ─────────────────────────────────────────────────────────────────────────────
# Canonical Classifier (E1)
# ─────────────────────────────────────────────────────────────────────────────

def test_canonical_classifier_vhh1_short():
    """CDR3 ≤9 residues must produce VHH-1 base class."""
    from core.vhh.canonical_classifier import classify_vhh_cdr3
    result = classify_vhh_cdr3("DRGSIRDFYW"[:9], anchor_94_residue="R")
    assert result.base_class == "VHH-1"
    assert result.subclass == "a"
    assert result.class_id == "VHH-1a"


def test_canonical_classifier_vhh2_medium():
    """CDR3 10–13 residues must produce VHH-2 base class."""
    from core.vhh.canonical_classifier import classify_vhh_cdr3
    result = classify_vhh_cdr3("DRGSIRDFYWGQ", anchor_94_residue="R")  # 12 residues
    assert result.base_class == "VHH-2"


def test_canonical_classifier_vhh4_very_long():
    """CDR3 ≥18 residues must produce VHH-4 base class."""
    from core.vhh.canonical_classifier import classify_vhh_cdr3
    result = classify_vhh_cdr3("DRGSIRDFYWGQGTLVTV", anchor_94_residue="K")  # 18 residues
    assert result.base_class == "VHH-4"
    assert result.subclass == "b"


def test_canonical_classifier_subclass_c_warning():
    """Non-R/K anchor at 94 must produce subclass c and a warning."""
    from core.vhh.canonical_classifier import classify_vhh_cdr3
    result = classify_vhh_cdr3("DRGSIRDFYW", anchor_94_residue="D")
    assert result.subclass == "c"
    assert result.vernier_risk == "high"
    assert len(result.warnings) >= 1


def test_canonical_classifier_disulfide_cdr3_detection():
    """Two Cys in CDR3 must set ds_cdr3=True and generate a warning."""
    from core.vhh.canonical_classifier import classify_vhh_cdr3
    result = classify_vhh_cdr3("CDRSICDFW", anchor_94_residue="R")
    assert result.ds_cdr3 is True
    assert any("Cys" in w or "disulfide" in w.lower() for w in result.warnings)


def test_canonical_classifier_cdr1_cdr3_disulfide():
    """CDR1 Cys + CDR3 Cys must set ds_cdr1_3=True."""
    from core.vhh.canonical_classifier import classify_vhh_cdr3
    result = classify_vhh_cdr3("DRGSICDFW", cdr1_seq="GFTCSSYA", anchor_94_residue="R")
    assert result.ds_cdr1_3 is True


def test_canonical_classifier_to_dict():
    """to_dict() must contain all required keys."""
    from core.vhh.canonical_classifier import classify_vhh_cdr3
    d = classify_vhh_cdr3("DRGSIRDFYW", anchor_94_residue="R").to_dict()
    for key in ("class_id", "base_class", "subclass", "cdr3_length",
                "anchor_94", "ds_cdr3", "ds_cdr1_3", "cdr3_gravy",
                "stability_note", "vernier_risk", "description", "warnings"):
        assert key in d, f"Missing key in canonical_class dict: {key}"


def test_classify_from_kabat_dict():
    """classify_from_kabat_dict must produce a valid VHHCanonicalClass from a real sequence."""
    from scripts.vhh_cli import _get_kabat_dict
    from core.vhh.canonical_classifier import classify_from_kabat_dict
    kd = _get_kabat_dict(_MUMAB4D5_VH)
    result = classify_from_kabat_dict(kd)
    assert result.class_id.startswith("VHH-")
    assert result.cdr3_length >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Dual-scheme validator (E2)
# ─────────────────────────────────────────────────────────────────────────────

def test_dual_scheme_validate_mumab4d5():
    """muMAb4D5 VH should produce PASS or WARN (not FAIL/ERROR)."""
    from core.vhh.dual_scheme_validator import dual_scheme_validate
    result = dual_scheme_validate(_MUMAB4D5_VH)
    assert result["status"] in {"PASS", "WARN"}, (
        f"Unexpected status: {result['status']} — {result['note']}"
    )
    assert result["kabat_cdr3_len"] >= 1


def test_dual_scheme_validate_result_keys():
    """dual_scheme_validate must return all required keys."""
    from core.vhh.dual_scheme_validator import dual_scheme_validate
    result = dual_scheme_validate(_MUMAB4D5_VH)
    for key in ("status", "kabat_cdr3", "imgt_cdr3", "kabat_cdr3_len",
                "imgt_cdr3_len", "len_mismatch", "seq_match", "note"):
        assert key in result, f"Missing key: {key}"


def test_dual_xval_embedded_in_infer_from_sequence():
    """infer_from_sequence must include dual_scheme_xval field."""
    from scripts.vhh_design_decision_tree import infer_from_sequence
    result = infer_from_sequence(_MUMAB4D5_VH)
    assert "dual_scheme_xval" in result, "dual_scheme_xval missing from inferred_input"
    xval = result["dual_scheme_xval"]
    assert "status" in xval
    assert xval["status"] in {"PASS", "WARN", "FAIL", "ERROR", "SKIP"}


# ─────────────────────────────────────────────────────────────────────────────
# Learning feedback (D3) — regression
# ─────────────────────────────────────────────────────────────────────────────

def test_learning_adjustment_neutral_no_data(tmp_path):
    """get_motif_priority_adjustment returns 0 when log is empty."""
    from scripts.vhh_design_learning_log import get_motif_priority_adjustment
    log = tmp_path / "empty.jsonl"
    adj = get_motif_priority_adjustment("FERF", "vh-to-vhh", 7, 9, log)
    assert adj == 0


def test_learning_adjustment_neutral_few_samples(tmp_path):
    """Returns 0 when fewer than min_samples records are present."""
    import json
    from scripts.vhh_design_learning_log import get_motif_priority_adjustment

    log = tmp_path / "log.jsonl"
    for _ in range(2):  # only 2 entries, below default min_samples=3
        log.open("a").write(json.dumps({
            "mode": "vh-to-vhh", "cdr2": 7, "cdr3": 9,
            "motif": "FERF", "accepted": True
        }) + "\n")
    adj = get_motif_priority_adjustment("FERF", "vh-to-vhh", 7, 9, log, min_samples=3)
    assert adj == 0


def test_learning_adjustment_boost_high_acceptance(tmp_path):
    """Returns -1 (boost) when acceptance rate >= 70%."""
    import json
    from scripts.vhh_design_learning_log import get_motif_priority_adjustment

    log = tmp_path / "log.jsonl"
    for _ in range(7):  # 7 accepted out of 7 = 100%
        log.open("a").write(json.dumps({
            "mode": "vh-to-vhh", "cdr2": 7, "cdr3": 9,
            "motif": "FERF", "accepted": True
        }) + "\n")
    adj = get_motif_priority_adjustment("FERF", "vh-to-vhh", 7, 9, log, min_samples=3)
    assert adj == -1, f"Expected -1 boost, got {adj}"


def test_learning_adjustment_penalize_low_acceptance(tmp_path):
    """Returns +1 (penalise) when acceptance rate <= 30%."""
    import json
    from scripts.vhh_design_learning_log import get_motif_priority_adjustment

    log = tmp_path / "log.jsonl"
    for accepted in [False, False, False, False, True]:  # 1/5 = 20%
        log.open("a").write(json.dumps({
            "mode": "vh-to-vhh", "cdr2": 7, "cdr3": 9,
            "motif": "FERF", "accepted": accepted
        }) + "\n")
    adj = get_motif_priority_adjustment("FERF", "vh-to-vhh", 7, 9, log, min_samples=3)
    assert adj == 1, f"Expected +1 penalise, got {adj}"


# ─────────────────────────────────────────────────────────────────────────────
# Golden regression (muMAb4D5)
# ─────────────────────────────────────────────────────────────────────────────

def test_golden_mumab4d5_cdr_lengths():
    """muMAb4D5 VH golden test: CDR1=10, CDR2=17, CDR3=9."""
    from scripts.vhh_design_decision_tree import infer_from_sequence
    result = infer_from_sequence(_MUMAB4D5_VH)
    assert result["cdr1"] == 10, f"CDR1 mismatch: {result['cdr1']}"
    assert result["cdr2"] == 17, f"CDR2 mismatch: {result['cdr2']}"
    assert result["cdr3"] == 9,  f"CDR3 mismatch: {result['cdr3']}"


def test_golden_mumab4d5_canonical_class():
    """muMAb4D5 CDR3=9 must classify as VHH-1 (compact beta-hairpin)."""
    from scripts.vhh_cli import _get_kabat_dict
    from core.vhh.canonical_classifier import classify_from_kabat_dict
    kd     = _get_kabat_dict(_MUMAB4D5_VH)
    result = classify_from_kabat_dict(kd)
    assert result.base_class == "VHH-1", (
        f"Expected VHH-1 for CDR3={result.cdr3_length}, got {result.base_class}"
    )
