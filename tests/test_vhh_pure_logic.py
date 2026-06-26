"""
tests/test_vhh_pure_logic.py — InSynBio AbEngineCore VHH Platform
==================================================================
Unit tests for pure-logic functions with NO Anarcii dependency.

Coverage:
  - core.cmc.vhh_adi  : vhh_adi_interpretation, _compat_flag
  - scripts.vhh_design_decision_tree : cdr3_tier, build_candidates_for_vhh,
                                       build_candidates_for_vh,
                                       build_candidates_for_human_sdab
  - scripts.vhh_cli   : motif_to_replacements
  - core.humanization.kabat_utils : kabat_from_anarcii, sorted_keys,
                                    verify_cdr_preservation

Run:
    cd Antibody_Engineer_Suite
    python -m pytest tests/test_vhh_pure_logic.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_kabat_dict(pairs: list[tuple]) -> dict:
    """Build a KabatDict from (int, str, aa) triples."""
    return {(pos, ins): aa for pos, ins, aa in pairs}


# ─────────────────────────────────────────────────────────────────────────────
# 1. VHH-ADI interpretation thresholds
# ─────────────────────────────────────────────────────────────────────────────

class TestVhhAdiInterpretation:
    """vhh_adi.vhh_adi_interpretation: boundary values."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from core.cmc.vhh_adi import vhh_adi_interpretation
        self.fn = vhh_adi_interpretation

    def test_excellent_at_80(self):
        assert self.fn(80.0) == "Excellent"

    def test_excellent_above_80(self):
        assert self.fn(95.5) == "Excellent"

    def test_acceptable_at_60(self):
        assert self.fn(60.0) == "Acceptable"

    def test_acceptable_at_79(self):
        assert self.fn(79.9) == "Acceptable"

    def test_moderate_at_40(self):
        assert self.fn(40.0) == "Moderate risk"

    def test_moderate_at_59(self):
        assert self.fn(59.9) == "Moderate risk"

    def test_high_risk_below_40(self):
        assert self.fn(39.9) == "High risk"

    def test_high_risk_at_zero(self):
        assert self.fn(0.0) == "High risk"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Human compatibility flag
# ─────────────────────────────────────────────────────────────────────────────

class TestCompatFlag:
    """vhh_adi._compat_flag: task-aware thresholds.

    Signature: _compat_flag(primary_score, compat_adi, task)
    - primary_score: task-appropriate ADI (DBA or VHH42)
    - compat_adi:    AbRef-458 soft downgrade guard (< 25 downgrades OK → WARN)
    - task:          determines which primary reference and threshold table to use

    DBA-primary tasks (vh-to-vhh, human-sdab-optimization): ≥60 OK, ≥40 WARN, else FLAG
    camelid-vhh-humanization (VHH42-primary):               ≥60 OK, ≥40 WARN, else FLAG
    """

    @pytest.fixture(autouse=True)
    def _import(self):
        from core.cmc.vhh_adi import _compat_flag
        self.fn = _compat_flag

    # vh-to-vhh (DBA primary): ≥60 OK, ≥40 WARN, else FLAG
    def test_vh_to_vhh_ok(self):
        assert self.fn(60.0, 50.0, "vh-to-vhh") == "OK"

    def test_vh_to_vhh_warn(self):
        assert self.fn(45.0, 50.0, "vh-to-vhh") == "WARN"

    def test_vh_to_vhh_flag(self):
        assert self.fn(39.9, 50.0, "vh-to-vhh") == "FLAG"

    def test_vh_to_vhh_compat_downgrade(self):
        # compat_adi < 25 downgrades OK → WARN
        assert self.fn(65.0, 24.9, "vh-to-vhh") == "WARN"

    # camelid-vhh-humanization (VHH42 primary): ≥60 OK, ≥40 WARN, else FLAG
    def test_camelid_ok(self):
        assert self.fn(60.0, 50.0, "camelid-vhh-humanization") == "OK"

    def test_camelid_warn(self):
        assert self.fn(40.0, 50.0, "camelid-vhh-humanization") == "WARN"

    def test_camelid_flag(self):
        assert self.fn(39.9, 50.0, "camelid-vhh-humanization") == "FLAG"

    def test_sdab_ok(self):
        assert self.fn(65.0, 50.0, "human-sdab-optimization") == "OK"


# ─────────────────────────────────────────────────────────────────────────────
# 3. CDR3 tier classification
# ─────────────────────────────────────────────────────────────────────────────

class TestCdr3Tier:
    """decision_tree.cdr3_tier: boundary conditions per config defaults."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from scripts.vhh_design_decision_tree import cdr3_tier
        self.fn = cdr3_tier

    def test_short(self):
        assert self.fn(9) == "short"

    def test_medium_boundary(self):
        assert self.fn(10) == "medium"

    def test_medium(self):
        assert self.fn(13) == "medium"

    def test_long_boundary(self):
        assert self.fn(14) == "long"

    def test_long(self):
        assert self.fn(17) == "long"

    def test_very_long_boundary(self):
        assert self.fn(18) == "very_long"

    def test_very_long(self):
        assert self.fn(25) == "very_long"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Candidate builder for VHH humanization
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildCandidatesForVhh:
    """decision_tree.build_candidates_for_vhh: motif priority ordering."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from scripts.vhh_design_decision_tree import build_candidates_for_vhh
        self.fn = build_candidates_for_vhh

    def test_very_long_cdr3_first_priority(self):
        cands = self.fn(cdr2=7, cdr3=20, prefer_humanness=False)
        assert cands[0]["motif"] == "FERR"

    def test_very_long_cdr3_has_three_candidates(self):
        cands = self.fn(cdr2=7, cdr3=20, prefer_humanness=False)
        assert len(cands) >= 3

    def test_short_cdr3_first_is_vglw(self):
        cands = self.fn(cdr2=7, cdr3=8, prefer_humanness=False)
        assert cands[0]["motif"] == "VGLW"

    def test_medium_cdr3_first_is_verw(self):
        cands = self.fn(cdr2=7, cdr3=10, prefer_humanness=False)
        assert cands[0]["motif"] == "VERW"

    def test_long_cdr3_prefer_humanness_reorders(self):
        cands_prefer   = self.fn(cdr2=7, cdr3=15, prefer_humanness=True)
        cands_stability = self.fn(cdr2=7, cdr3=15, prefer_humanness=False)
        # prefer_humanness puts VERW first, stability-first puts FERF first
        assert cands_prefer[0]["motif"] == "VERW"
        assert cands_stability[0]["motif"] == "FERF"

    def test_long_cdr2_warning_on_vglw(self):
        cands = self.fn(cdr2=17, cdr3=8, prefer_humanness=False)
        vglw_cand = next((c for c in cands if c["motif"] == "VGLW"), None)
        assert vglw_cand is not None
        assert "warning" in vglw_cand

    def test_all_candidates_have_required_fields(self):
        cands = self.fn(cdr2=8, cdr3=12, prefer_humanness=False)
        for c in cands:
            assert "motif" in c
            assert "priority" in c
            assert "mutations" in c
            assert "why" in c


# ─────────────────────────────────────────────────────────────────────────────
# 5. Candidate builder for VH→VHH conversion
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildCandidatesForVh:
    """decision_tree.build_candidates_for_vh: long-CDR2 path."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from scripts.vhh_design_decision_tree import build_candidates_for_vh
        self.fn = build_candidates_for_vh

    def test_long_cdr2_short_cdr3_first_is_vgrw(self):
        cands = self.fn(cdr2=17, cdr3=8, prefer_humanness=False,
                        allow_secondary_interface=False)
        assert cands[0]["motif"] == "VGRW"

    def test_long_cdr2_long_cdr3_stability_first(self):
        cands = self.fn(cdr2=17, cdr3=15, prefer_humanness=False,
                        allow_secondary_interface=False)
        assert cands[0]["motif"] == "FERF"

    def test_long_cdr2_long_cdr3_humanness_first(self):
        cands = self.fn(cdr2=17, cdr3=15, prefer_humanness=True,
                        allow_secondary_interface=False)
        assert cands[0]["motif"] == "VERW"

    def test_short_cdr3_no_secondary(self):
        cands = self.fn(cdr2=8, cdr3=7, prefer_humanness=False,
                        allow_secondary_interface=False)
        assert any(c["motif"] == "VGRW" for c in cands)

    def test_secondary_interface_allowed_and_long_cdr3(self):
        cands = self.fn(cdr2=8, cdr3=12, prefer_humanness=False,
                        allow_secondary_interface=True)
        motifs = [c["motif"] for c in cands]
        assert "VGLW+secondary" in motifs


# ─────────────────────────────────────────────────────────────────────────────
# 6. motif_to_replacements (vhh_cli pure logic)
# ─────────────────────────────────────────────────────────────────────────────

class TestMotifToReplacements:
    """vhh_cli.motif_to_replacements: 4-letter motif → Kabat position dict."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from scripts.vhh_cli import motif_to_replacements
        self.fn = motif_to_replacements

    def test_vglw_mapping(self):
        r = self.fn("VGLW")
        assert r == {37: "V", 44: "G", 45: "L", 47: "W"}

    def test_ferf_mapping(self):
        r = self.fn("FERF")
        assert r == {37: "F", 44: "E", 45: "R", 47: "F"}

    def test_verw_mapping(self):
        r = self.fn("VERW")
        assert r == {37: "V", 44: "E", 45: "R", 47: "W"}

    def test_secondary_suffix_stripped(self):
        r = self.fn("VGLW+secondary")
        assert r == {37: "V", 44: "G", 45: "L", 47: "W"}

    def test_non_4letter_returns_empty(self):
        r = self.fn("VGL")
        assert r == {}

    def test_non_alpha_returns_empty(self):
        r = self.fn("VGL1")
        assert r == {}


# ─────────────────────────────────────────────────────────────────────────────
# 7. kabat_from_anarcii and sorted_keys
# ─────────────────────────────────────────────────────────────────────────────

class TestKabatFromAnarcii:
    """kabat_utils.kabat_from_anarcii: insertion-code preservation."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from core.humanization.kabat_utils import kabat_from_anarcii, sorted_keys
        self.from_fn = kabat_from_anarcii
        self.sort_fn = sorted_keys

    def _make_numbering(self, pairs: list[tuple[int, str, str]]) -> list[tuple]:
        """Build synthetic ANARCII-style numbering: list of ((pos, ins), aa)."""
        return [((pos, ins), aa) for pos, ins, aa in pairs]

    def test_base_positions_only(self):
        numbering = self._make_numbering([
            (1, " ", "E"), (2, " ", "V"), (3, " ", "Q"),
        ])
        kd = self.from_fn(numbering)
        assert (1, "") in kd
        assert (2, "") in kd
        assert (3, "") in kd
        assert kd[(1, "")] == "E"

    def test_insertion_codes_preserved(self):
        """52A must NOT overwrite 52 — the classic insertion-code bug."""
        numbering = self._make_numbering([
            (52, " ", "Y"),
            (52, "A", "P"),
            (52, "B", "G"),
        ])
        kd = self.from_fn(numbering)
        assert (52, "") in kd,  "base position 52 missing"
        assert (52, "A") in kd, "insertion 52A missing"
        assert (52, "B") in kd, "insertion 52B missing"
        assert kd[(52, "")] == "Y"
        assert kd[(52, "A")] == "P"
        assert kd[(52, "B")] == "G"

    def test_sorted_keys_insertion_order(self):
        """sorted_keys must return '' < 'A' < 'B' at same integer position."""
        numbering = self._make_numbering([
            (52, "B", "G"),
            (52, " ", "Y"),
            (52, "A", "P"),
        ])
        kd = self.from_fn(numbering)
        keys = self.sort_fn(kd)
        pos52_keys = [k for k in keys if k[0] == 52]
        assert pos52_keys == [(52, ""), (52, "A"), (52, "B")]

    def test_gap_residues_excluded(self):
        """Gaps ('-') should not appear in the returned KabatDict."""
        numbering = self._make_numbering([
            (10, " ", "-"),
            (11, " ", "V"),
        ])
        kd = self.from_fn(numbering)
        for aa in kd.values():
            assert aa != "-", "gap residue must not appear in KabatDict"


# ─────────────────────────────────────────────────────────────────────────────
# 8. verify_cdr_preservation
# ─────────────────────────────────────────────────────────────────────────────

class TestVerifyCdrPreservation:
    """kabat_utils.verify_cdr_preservation: CDR gate logic."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from core.humanization.kabat_utils import verify_cdr_preservation
        self.fn = verify_cdr_preservation

    def _stub_kd(self, cdrs: dict[str, str]) -> dict:
        """Build minimal KabatDict covering CDR1 (26-35), CDR2 (50-65), CDR3 (95-102)."""
        kd: dict = {}
        pos = 26
        for aa in cdrs.get("CDR1", "GYTFTSYN"):
            kd[(pos, "")] = aa
            pos += 1
        pos = 50
        for aa in cdrs.get("CDR2", "IINPSGGSTSYA"):
            kd[(pos, "")] = aa
            pos += 1
        pos = 95
        for aa in cdrs.get("CDR3", "ARDQGSIRG"):
            kd[(pos, "")] = aa
            pos += 1
        return kd

    def test_identical_cdrs_no_errors(self):
        kd = self._stub_kd({})
        errors = self.fn(kd, kd, "VH")
        assert errors == []

    def test_cdr1_mutation_detected(self):
        original = self._stub_kd({"CDR1": "GYTFTSYN"})
        mutated  = self._stub_kd({"CDR1": "GYTFTAYN"})  # S→A at pos 31
        errors = self.fn(mutated, original, "VH")
        assert len(errors) > 0, "CDR1 mutation must be flagged"

    def test_cdr3_mutation_detected(self):
        # Kabat CDR3 range is 95–102 (8 positions). Stub uses pos 95-102,
        # so use an 8-residue CDR3 and mutate the 4th residue (pos 98).
        original = self._stub_kd({"CDR3": "ARDQGSIA"})
        mutated  = self._stub_kd({"CDR3": "ARDKGSIA"})  # Q→K at pos 98
        errors = self.fn(mutated, original, "VH")
        assert len(errors) > 0, "CDR3 mutation must be flagged"

    def test_fr_mutation_not_flagged(self):
        """FR substitutions must NOT produce CDR errors."""
        original = self._stub_kd({})
        mutated  = dict(original)
        # Add a FR position (e.g. pos 44) outside CDR spans
        original[(44, "")] = "G"
        mutated[(44, "")]  = "E"
        errors = self.fn(mutated, original, "VH")
        assert errors == []


# ─────────────────────────────────────────────────────────────────────────────
# 9. VHH CDR1 canonical classification (North-adapted)
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifyVhhCdr1:
    """canonical_classifier.classify_vhh_cdr1: length tiers and anchor residue."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from core.vhh.canonical_classifier import classify_vhh_cdr1
        self.fn = classify_vhh_cdr1

    def test_short_loop_h1_1(self):
        r = self.fn("GYTFS")   # len=5 → H1-1
        assert r.base_class == "H1-1"
        assert r.cdr1_length == 5

    def test_standard_loop_h1_2(self):
        r = self.fn("GYTFTS")  # len=6 → H1-2
        assert r.base_class == "H1-2"

    def test_standard_loop_h1_2_len7(self):
        r = self.fn("GYTFTSY")  # len=7 → H1-2
        assert r.base_class == "H1-2"

    def test_extended_loop_h1_3(self):
        r = self.fn("GYTFTSYNM")  # len=9 → H1-3
        assert r.base_class == "H1-3"
        assert r.vernier_sensitivity == "moderate"

    def test_long_loop_h1_4(self):
        r = self.fn("GYTFTSYNMHW")  # len=11 → H1-4
        assert r.base_class == "H1-4"
        assert r.vernier_sensitivity == "high"

    def test_anchor_29_phe_subtype(self):
        # Kabat 29 = position index 3 from start (26, 27, 28, 29)
        r = self.fn("GYTFTS")   # seq[3] = 'F' → anchor .F
        assert r.anchor_subtype == "F"
        assert r.anchor_29 == "F"
        assert ".F" in r.class_id

    def test_anchor_29_tyr_subtype(self):
        r = self.fn("GYTYTSY")  # seq[3] = 'Y' → anchor .Y
        assert r.anchor_subtype == "Y"

    def test_anchor_29_atypical_warns(self):
        r = self.fn("GYTATSY")  # seq[3] = 'A' → anchor .x
        assert r.anchor_subtype == "x"
        assert len(r.warnings) > 0

    def test_explicit_anchor_override(self):
        r = self.fn("GYTFTS", anchor_29_residue="Y")
        assert r.anchor_29 == "Y"
        assert r.anchor_subtype == "Y"

    def test_class_id_format(self):
        r = self.fn("GYTFTSYNM")
        assert r.class_id == f"{r.base_class}.{r.anchor_subtype}"

    def test_to_dict_keys(self):
        r = self.fn("GYTFTS")
        d = r.to_dict()
        for k in ("class_id", "base_class", "anchor_29", "anchor_subtype",
                  "cdr1_length", "description", "vernier_sensitivity", "warnings"):
            assert k in d, f"Missing key: {k}"


# ─────────────────────────────────────────────────────────────────────────────
# 10. VHH CDR2 canonical classification (North-adapted)
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifyVhhCdr2:
    """canonical_classifier.classify_vhh_cdr2: length tiers and Kabat-47 anchor."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from core.vhh.canonical_classifier import classify_vhh_cdr2
        self.fn = classify_vhh_cdr2

    def test_short_cdr2_h2_1(self):
        r = self.fn("INPSG", anchor_47_residue="L")  # len=5 → H2-1
        assert r.base_class == "H2-1"
        assert r.cdr2_length == 5

    def test_standard_cdr2_h2_2(self):
        r = self.fn("INPSGGT", anchor_47_residue="E")  # len=7 → H2-2
        assert r.base_class == "H2-2"

    def test_long_cdr2_h2_3(self):
        r = self.fn("IINPSGGSTSYA", anchor_47_residue="G")  # len=12 → H2-3
        assert r.base_class == "H2-3"

    def test_very_long_cdr2_h2_4(self):
        r = self.fn("IINPSGGSTSYAQKFQ", anchor_47_residue="R")  # len=16 → H2-4
        assert r.base_class == "H2-4"

    def test_anchor_47_vhh_native_no_warning(self):
        for aa in ("G", "L", "R", "E", "F", "A"):
            r = self.fn("INPSGGT", anchor_47_residue=aa)
            assert r.anchor_subtype == "vhh"
            assert len(r.warnings) == 0, f"Unexpected warning for VHH-native {aa}"

    def test_anchor_47_trp_warns(self):
        r = self.fn("INPSGGT", anchor_47_residue="W")
        assert r.anchor_subtype == "W"
        assert len(r.warnings) > 0
        assert "Trp" in r.warnings[0] or "47" in r.warnings[0]

    def test_anchor_47_trp_engineering_path_mentions_mutation(self):
        r = self.fn("INPSGGT", anchor_47_residue="W")
        assert "47" in r.engineering_path or "mutation" in r.engineering_path.lower()

    def test_very_long_cdr2_engineering_path_vgrw(self):
        r = self.fn("IINPSGGSTSYAQKFQ", anchor_47_residue="R")
        assert "VGRW" in r.engineering_path or "VGEL" in r.engineering_path

    def test_atypical_47_warns(self):
        r = self.fn("INPSGGT", anchor_47_residue="Q")
        assert r.anchor_subtype == "x"
        assert len(r.warnings) > 0

    def test_class_id_format(self):
        r = self.fn("INPSGGT", anchor_47_residue="G")
        assert r.class_id == f"{r.base_class}.{r.anchor_subtype}"

    def test_to_dict_keys(self):
        r = self.fn("INPSGGT", anchor_47_residue="L")
        d = r.to_dict()
        for k in ("class_id", "base_class", "anchor_47", "anchor_subtype",
                  "cdr2_length", "description", "engineering_path", "warnings"):
            assert k in d, f"Missing key: {k}"


# ─────────────────────────────────────────────────────────────────────────────
# 11. VHHFullCanonicalResult backward compatibility
# ─────────────────────────────────────────────────────────────────────────────

class TestVHHFullCanonicalResult:
    """VHHFullCanonicalResult.to_dict() must be backward-compatible with VHHCanonicalClass."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from core.vhh.canonical_classifier import (
            classify_vhh_cdr1, classify_vhh_cdr2, classify_vhh_cdr3,
            VHHFullCanonicalResult,
        )
        self.cdr3 = classify_vhh_cdr3("ARDQGSIA", anchor_94_residue="R")
        self.cdr1 = classify_vhh_cdr1("GYTFTSYN")
        self.cdr2 = classify_vhh_cdr2("IINPSGGSTSYA", anchor_47_residue="G")
        self.full = VHHFullCanonicalResult(cdr3=self.cdr3, cdr1=self.cdr1, cdr2=self.cdr2)

    def test_class_id_property(self):
        assert self.full.class_id == self.cdr3.class_id

    def test_to_dict_backward_compat_cdr3_fields(self):
        d = self.full.to_dict()
        # All CDR3 fields must be present at top level (backward compat)
        for key in ("class_id", "base_class", "subclass", "cdr3_length",
                    "anchor_94", "ds_cdr3", "ds_cdr1_3", "cdr3_gravy",
                    "stability_note", "vernier_risk", "description", "warnings"):
            assert key in d, f"Backward-compat key missing: '{key}'"

    def test_to_dict_new_cdr1_section(self):
        d = self.full.to_dict()
        assert "cdr1_class" in d
        assert d["cdr1_class"]["class_id"] == self.cdr1.class_id

    def test_to_dict_new_cdr2_section(self):
        d = self.full.to_dict()
        assert "cdr2_class" in d
        assert d["cdr2_class"]["class_id"] == self.cdr2.class_id

    def test_system_tag_present(self):
        d = self.full.to_dict()
        assert "_system" in d
        assert "CDR1" in d["_system"] and "CDR2" in d["_system"]
