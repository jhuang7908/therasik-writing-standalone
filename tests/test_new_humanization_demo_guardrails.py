"""
Guardrail tests for New_Humanization_Demo.

These tests are *invariants* that prevent recurrence of the 2026-02 incident:
- Mixing Kabat numbering with IMGT CDR spans in CDR grafting (causes CDR corruption)
- Report status hardcoded to PASS while QC is FAIL (false green delivery)

They are intentionally lightweight: no modeling, no external tools, no pipelines.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
DEMO_DIR = PROJECT_ROOT / "projects" / "New_Humanization_Demo"


def _read_text(path: Path) -> str:
    assert path.exists, f"Missing file: {path}"
    return path.read_text(encoding="utf-8")


def test_run_real_phase3_5_uses_kabat_cdr_ranges_only:
    """
    Invariant: If Kabat numbering is used for assembly, CDR spans must be Kabat spans,
    and IMGT spans must NOT be used for grafting.
    """
    p = DEMO_DIR / "run_real_phase3_5.py"
    s = _read_text(p)

    assert "CDR_KABAT_VH" in s and "CDR_KABAT_VL" in s, "Kabat CDR spans missing."
    assert "CDR_IMGT_VH" not in s and "CDR_IMGT_VL" not in s, (
        "IMGT CDR spans found in run_real_phase3_5.py. "
        "This previously caused CDR corruption due to numbering mismatch."
    )


def test_run_real_phase3_5_has_cdr_preservation_hard_gate:
    """
    Invariant: CDR sequences must be 100% preserved after assembly,
    otherwise the pipeline must abort before modeling/QC/delivery.
    """
    p = DEMO_DIR / "run_real_phase3_5.py"
    s = _read_text(p)

    assert "_assert_cdr_preserved" in s, "Missing CDR-preservation guard function."
    assert "CDR grafting " in s or "CDR grafting" in s, "Guard message not found."
    assert "sys.exit(2)" in s, "Guard must abort with non-zero exit code."


def test_generate_proposal_status_is_not_hardcoded_and_uses_qc_final:
    """
    Invariant: Proposal status must derive from qc_final, not a hardcoded PASS string.
    """
    p = DEMO_DIR / "generate_proposal_new_demo.py"
    s = _read_text(p)

    assert "qc_final" in s, "generate_proposal_new_demo.py must reference qc_final."
    assert "verdict_to_bool" in s, "Missing verdict parsing (verdict_to_bool)."
    assert "🟢 PASS (Our_Hum)" not in s, "Hardcoded PASS marker found."
    assert "🔴 FAIL" in s or "FAIL" in s, "FAIL status rendering missing."


def test_run_phase5_is_deprecated_to_prevent_predicted_pass:
    """
    Invariant: The old heuristic QC script must be disabled to prevent false green outputs.
    """
    p = DEMO_DIR / "run_phase5.py"
    s = _read_text(p)
    assert "[DEPRECATED]" in s and "SystemExit" in s, "run_phase5.py must be deprecated."

