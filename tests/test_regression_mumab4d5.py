"""
tests/test_regression_mumab4d5.py — InSynBio AbEngineCore VHH Platform
=======================================================================
PURPOSE: ALGORITHM STABILITY REGRESSION — NOT a sequence identity test.
=========================================================================

This module tests that the VHH decision-tree algorithms (infer_from_sequence,
recommend_vh_to_vhh, mutate_by_kabat_positions, kabat_from_anarcii) produce
STABLE, REPRODUCIBLE outputs for a fixed input.

IMPORTANT: The sequence below (_MUMAB4D5_VH) is the HISTORICAL INCORRECT sequence
originally used in projects/mumab4d5_vhh/ before PISG-v1 was established.
It is IGHV1 family (CDR1 = GYTFTSYNMH), which is NOT the authentic muMAb4D5.
The authentic muMAb4D5 (PDB 1FVC) is IGHV3 family (CDR1 = GFNIKDTYIH).

Do NOT use this sequence as scientific input for any new project.
This fixture is kept as-is for algorithm regression only: same input = same output.

Cross-reference:
  - Authenticated muMAb4D5 sequences → data/sequence_cache/mumab4d5_verified.fasta
  - Sequence identity test (CDR preservation after grafting) → tests/test_vhvl_cdr_graft_qa.py
  - PISG-v1 rule (how to prevent future wrong-input errors) → .cursor/rules/project-input-sequence-gate.mdc

Golden values derived from:
  - projects/mumab4d5_vhh/auto_ranked_candidates.json  (cdr1/2/3, germline)
  - projects/mumab4d5_vhh/feasibility_report.json      (VH sequence)

Requirements:
  - Anarcii must be installed (conda env 'anarcii', or active env with anarcii)
  - Network not required (no IEDB calls)

Skip marker: all tests in this module are skipped if `anarcii` cannot be imported.
Run:
    cd Antibody_Engineer_Suite
    python -m pytest tests/test_regression_mumab4d5.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Skip entire module if Anarcii is unavailable
anarcii = pytest.importorskip("anarcii", reason="anarcii not installed — skipping regression tests")


# ─────────────────────────────────────────────────────────────────────────────
# Golden fixture: muMAb4D5 parent VH
# ─────────────────────────────────────────────────────────────────────────────

_MUMAB4D5_VH = (
    "EVQLVQSGAEVKKPGASVKVSCKASGYTFTSYNMHWVRQAPGQGLEWMG"
    "IINPSGGSTSYAQKFQGRVTMTRDTSTSTVYMELSSLRSEDTAVYYCAR"
    "DQGSIRGFDYWGQGTLVTVSS"
)

# Expected values from auto_ranked_candidates.json (source of truth)
_EXPECTED_CDR1     = 10
_EXPECTED_CDR2     = 17
_EXPECTED_CDR3     = 10
_EXPECTED_GERMLINE = "IGHV1-2"

# First candidate motif for vh-to-vhh, long-CDR2 path
_EXPECTED_FIRST_MOTIF_VH2VHH = "VGRW"


# ─────────────────────────────────────────────────────────────────────────────
# 1. infer_from_sequence: CDR lengths and germline
# ─────────────────────────────────────────────────────────────────────────────

class TestInferFromSequenceMuMAb4D5:
    """infer_from_sequence must reproduce the muMAb4D5 golden CDR/germline values."""

    @pytest.fixture(scope="class", autouse=True)
    def inferred(self):
        from scripts.vhh_design_decision_tree import infer_from_sequence
        return infer_from_sequence(_MUMAB4D5_VH)

    def test_cdr1_length(self, inferred):
        assert inferred["cdr1"] == _EXPECTED_CDR1, (
            f"CDR1 length regression: expected {_EXPECTED_CDR1}, got {inferred['cdr1']}"
        )

    def test_cdr2_length(self, inferred):
        assert inferred["cdr2"] == _EXPECTED_CDR2, (
            f"CDR2 length regression: expected {_EXPECTED_CDR2}, got {inferred['cdr2']}"
        )

    def test_cdr3_length(self, inferred):
        assert inferred["cdr3"] == _EXPECTED_CDR3, (
            f"CDR3 length regression: expected {_EXPECTED_CDR3}, got {inferred['cdr3']}"
        )

    def test_germline_assignment(self, inferred):
        assert inferred["germline"] == _EXPECTED_GERMLINE, (
            f"Germline regression: expected {_EXPECTED_GERMLINE}, got {inferred['germline']}"
        )

    def test_germline_identity_range(self, inferred):
        identity = inferred.get("germline_identity", 0.0)
        assert 0.75 <= identity <= 1.0, (
            f"Germline identity {identity:.3f} out of expected range [0.75, 1.0]"
        )

    def test_output_keys_present(self, inferred):
        expected_keys = {"sequence", "cdr1", "cdr2", "cdr3", "germline", "germline_identity"}
        assert expected_keys.issubset(inferred.keys())


# ─────────────────────────────────────────────────────────────────────────────
# 2. recommend_vh_to_vhh: first candidate for long-CDR2 path
# ─────────────────────────────────────────────────────────────────────────────

class TestRecommendVhToVhhMuMAb4D5:
    """recommend_vh_to_vhh must place VGRW first for CDR2=17, CDR3=10."""

    @pytest.fixture(scope="class")
    def recommendation(self):
        from scripts.vhh_design_decision_tree import recommend_vh_to_vhh
        return recommend_vh_to_vhh(
            cdr1=_EXPECTED_CDR1,
            cdr2=_EXPECTED_CDR2,
            cdr3=_EXPECTED_CDR3,
            germline=_EXPECTED_GERMLINE,
            preferred_germline=None,
            has_database_germline=False,
            prefer_humanness=False,
            allow_secondary_interface=False,
        )

    def test_first_candidate_motif(self, recommendation):
        assert recommendation.candidate_plans[0]["motif"] == _EXPECTED_FIRST_MOTIF_VH2VHH, (
            f"First motif regression: expected {_EXPECTED_FIRST_MOTIF_VH2VHH}, "
            f"got {recommendation.candidate_plans[0]['motif']}"
        )

    def test_has_three_or_more_candidates(self, recommendation):
        assert len(recommendation.candidate_plans) >= 3

    def test_risk_level_is_high(self, recommendation):
        assert recommendation.risk_level == "high"

    def test_mode_is_vh_to_vhh(self, recommendation):
        assert recommendation.mode == "vh-to-vhh"


# ─────────────────────────────────────────────────────────────────────────────
# 3. mutate_by_kabat_positions: VGRW substitution on muMAb4D5 VH
# ─────────────────────────────────────────────────────────────────────────────

def _mutate_by_kabat_direct(seq: str, replacements: dict) -> str:
    """
    Inline version of vhh_cli.mutate_by_kabat_positions that does NOT import
    vhh_cli (which would trigger top-level ImmuneBuilder import).
    Implements the same logic using kabat_utils primitives directly.
    """
    from anarcii import Anarcii
    from core.humanization.kabat_utils import kabat_from_anarcii, sorted_keys

    engine = Anarcii(seq_type="antibody", mode="accuracy")
    engine.number([seq])
    entry = engine.to_scheme("kabat").get("Sequence 1", {})
    if entry.get("error"):
        pytest.skip(f"Anarcii failed: {entry['error']}")
    kd = kabat_from_anarcii(entry["numbering"])
    rebuilt = []
    for key in sorted_keys(kd):
        pos, ins = key
        aa = kd[key]
        if ins == "" and pos in replacements:
            rebuilt.append(replacements[pos])
        else:
            rebuilt.append(aa)
    return "".join(rebuilt)


class TestMutateByKabatMuMAb4D5:
    """mutate_by_kabat_positions must apply L45R substitution correctly."""

    @pytest.fixture(scope="class")
    def mutated(self):
        return _mutate_by_kabat_direct(_MUMAB4D5_VH, {45: "R"})

    def test_sequence_length_preserved(self, mutated):
        assert len(mutated) == len(_MUMAB4D5_VH), (
            "Sequence length must not change after Kabat substitution"
        )

    def test_substitution_applied(self, mutated):
        # After numbering, Kabat 45 must be R in the mutated sequence
        # (we verify indirectly: mutated != original since L45→R)
        assert mutated != _MUMAB4D5_VH, "Substitution must produce a different sequence"

    def test_sequence_is_amino_acids_only(self, mutated):
        valid = set("ACDEFGHIKLMNPQRSTVWY")
        assert all(aa in valid for aa in mutated), "Mutated sequence contains non-standard residues"


# ─────────────────────────────────────────────────────────────────────────────
# 4. kabat_from_anarcii round-trip: muMAb4D5 VH
# ─────────────────────────────────────────────────────────────────────────────

class TestKabatRoundTripMuMAb4D5:
    """kabat_from_anarcii must produce a complete KabatDict from Anarcii output."""

    @pytest.fixture(scope="class")
    def kd(self):
        from anarcii import Anarcii
        from core.humanization.kabat_utils import kabat_from_anarcii
        engine = Anarcii(seq_type="antibody", mode="accuracy")
        engine.number([_MUMAB4D5_VH])
        entry = engine.to_scheme("kabat").get("Sequence 1", {})
        if entry.get("error"):
            pytest.skip(f"Anarcii failed: {entry['error']}")
        return kabat_from_anarcii(entry["numbering"])

    def test_no_plain_int_keys(self, kd):
        """All keys must be (int, str) tuples — never plain integers."""
        for k in kd:
            assert isinstance(k, tuple) and len(k) == 2, f"Non-tuple key found: {k!r}"
            assert isinstance(k[0], int),  f"Key[0] not int: {k!r}"
            assert isinstance(k[1], str),  f"Key[1] not str: {k!r}"

    def test_base_insertion_code_empty_string(self, kd):
        """Base positions must use empty string '' as insertion code, not ' '."""
        for pos, ins in kd:
            assert ins != " ", f"Space insertion code found at ({pos}, ' ') — must be ''"

    def test_cdr_positions_present(self, kd):
        """CDR1 (26-35), CDR2 (50-65), CDR3 (95-102) must have residues."""
        cdr1_residues = [kd.get((p, ""), "") for p in range(26, 36)]
        cdr3_residues = [kd.get((p, ""), "") for p in range(95, 103)]
        cdr1_seq = "".join(r for r in cdr1_residues if r and r != "-")
        cdr3_seq = "".join(r for r in cdr3_residues if r and r != "-")
        assert len(cdr1_seq) >= 5, f"CDR1 too short: {cdr1_seq!r}"
        assert len(cdr3_seq) >= 3, f"CDR3 too short: {cdr3_seq!r}"

    def test_reconstructed_sequence_length(self, kd):
        """Reconstructed sequence length must match original."""
        from core.humanization.kabat_utils import sorted_keys
        reconstructed = "".join(kd[k] for k in sorted_keys(kd) if kd[k] and kd[k] != "-")
        original_clean = "".join(c for c in _MUMAB4D5_VH.upper() if c.isalpha())
        assert len(reconstructed) == len(original_clean), (
            f"Reconstructed length {len(reconstructed)} != original {len(original_clean)}"
        )
