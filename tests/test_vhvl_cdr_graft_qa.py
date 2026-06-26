"""
tests/test_vhvl_cdr_graft_qa.py — Kabat CDR substring gate after scaffold graft
================================================================================
Regression for 2026-03-26 bug: IMGT CDR1_union [26,38] could truncate Kabat CDR1-H
when cutting mouse CDRs. Pipeline must use Kabat ``cdr_span`` + substring check.

Requires: anarcii
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytest.importorskip("anarcii", reason="anarcii not installed")


def _load_mumab4d5_from_cache() -> tuple[str, str]:
    fasta = ROOT / "data" / "sequence_cache" / "mumab4d5_verified.fasta"
    if not fasta.is_file():
        pytest.skip(f"missing {fasta}")
    from scripts.run_mumAb4D5_standard_humanization import load_mumab4d5_verified_vh_vl
    return load_mumab4d5_verified_vh_vl()


class TestVerifyCdrSubstringsMouseInAssembledV:
    def test_mouse_vh_full_sequence_passes_against_own_v_region(self) -> None:
        from core.humanization.kabat_utils import verify_cdr_substrings_mouse_in_assembled_v

        vh, _ = _load_mumab4d5_from_cache()
        fr4 = "WGQGTLVTVSS"
        assert vh.endswith(fr4), "verified VH must end with canonical FR4"
        v_region = vh[: -len(fr4)]
        errs = verify_cdr_substrings_mouse_in_assembled_v(vh, v_region, "VH")
        assert errs == [], errs

    def test_mouse_vl_full_sequence_passes_against_own_v_region(self) -> None:
        from core.humanization.kabat_utils import verify_cdr_substrings_mouse_in_assembled_v

        _, vl = _load_mumab4d5_from_cache()
        fr4 = "FGQGTKVEIK"
        assert vl.endswith(fr4), "verified VL (107 aa) must end with kappa FR4 from cache"
        v_region = vl[: -len(fr4)]
        errs = verify_cdr_substrings_mouse_in_assembled_v(vl, v_region, "VL")
        assert errs == [], errs

    def test_truncated_v_region_fails(self) -> None:
        from core.humanization.kabat_utils import verify_cdr_substrings_mouse_in_assembled_v

        vh, _ = _load_mumab4d5_from_cache()
        fr4 = "WGQGTLVTVSS"
        v_region = vh[: -len(fr4)]
        bad = v_region[:-3]
        errs = verify_cdr_substrings_mouse_in_assembled_v(vh, bad, "VH")
        assert errs, "expected CDR substring failure when V region truncated"


def test_vh_cdr1_substring_is_gfnikdtyih_not_gytftsynmh() -> None:
    """Documented golden: muMAb4D5 CDR1-H is IGHV3-like GFNIKDTYIH, not IGHV1 GYTFTSYNMH."""
    from core.humanization.kabat_utils import cdr_span, get_kabat_numbering

    vh, _ = _load_mumab4d5_from_cache()
    kd = get_kabat_numbering(vh)
    c1 = cdr_span(kd, 26, 35)
    assert c1 == "GFNIKDTYIH", f"unexpected CDR1-H from cache: {c1!r}"
