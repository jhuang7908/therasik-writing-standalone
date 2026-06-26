"""P0-1 acceptance tests: surface_reshaping_trigger must be insertion-code safe.

These tests guard against the regression described in V3.3-fix-1:

  Pre-fix code in ``surface_reshaping_trigger`` mapped linear residue index to
  Kabat/IMGT position via ``pos_1 = linear_index + 1``. For VHH with long
  CDR3 (≥ 17 aa, IMGT inserts 111A/111B/112A/...), every FR3 residue
  downstream of CDR3 had its linear index inflated by the number of
  insertions, so Tier 1 positions (e.g. IMGT 71/73/78) were no longer
  recognised as protected and could be silently edited by reshaping.

The post-fix function uses an ANARCI-driven ``linear_index → IMGT(base, ins_code)``
map. These tests assert that for two real long-CDR3 VHHs (one with 111A/111B
class insertions and one with 112A/112B/112C class insertions):

  1. CDR1 (IMGT 27–38), CDR2 (IMGT 56–65), CDR3 (IMGT 105–117 incl. insertions)
     are character-identical between donor and reshaped sequences.
  2. Tier 0 IMGT positions {28, 29, 44, 45, 47, 94} are character-identical.
  3. Tier 1 IMGT positions {34, 36, 40, 42, 49, 71, 73, 78} are
     character-identical.
  4. The reshaped sequence still numbers via ANARCI without errors.

To guarantee the reshape loop actually attempts mutations (otherwise the
invariants are vacuously true on a no-op), the SAP gate is monkey-patched to
return ``action="RESHAPE"`` for several iterations.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import pytest

# ANARCI is required for the function under test; skip gracefully if absent.
anarcii = pytest.importorskip("anarcii")  # noqa: F841

from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed  # noqa: E402
from core import vhh_humanization as vhhu  # noqa: E402


# ── Test fixtures ─────────────────────────────────────────────────────────────

# Two real clinical/SAbDab VHHs from data/vhh_clinical_39_union/vhh42_sabdab_supplement.json
# Both have long CDR3s that force IMGT insertion codes:
#   - SEQ_A: CDR3 ≈ 18 aa, expected insertions in the 111A/111B family
#   - SEQ_B: CDR3 ≈ 22 aa, expected insertions in the 112A/112B/112C family
SEQ_A = (
    "QVQLVESGGGLVQPGGSLRLSCAASGGSEYSYSTFSLGWFRQAPGQGLEAVAAIASMGGLTYYADSVKGRFTI"
    "SRDNSKNTLYLQMNSLRAEDTAVYYCAAVRGYFMRLPSSHNFRYWGQGTLVTVS"
)
SEQ_B = (
    "EVQLVESGGGLVQPGGSLRLSCEASGYTLANYAIGWFRQAPGKEREGVSCISSGGSTVYSESVKDRFTISRD"
    "NAKKIVYLQMNSLQPEDTAVYYCAADPFGERLCIDPNTFAGYLETWGQGTQVTVSSL"
)

# Tier protection constants (must match surface_reshaping_trigger's IMGT semantics).
TIER0_IMGT = {28, 29, 44, 45, 47, 94}
TIER1_IMGT = {34, 36, 40, 42, 49, 71, 73, 78}
PROTECTED_IMGT = TIER0_IMGT | TIER1_IMGT
CDR_IMGT_RANGES = [(27, 38), (56, 65), (105, 117)]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _imgt_residue_map(seq: str) -> Dict[Tuple[int, str], str]:
    """Return {(imgt_pos, ins_code): residue} for every numbered residue in seq.

    Insertion codes are normalised: ' ' for base positions, alphabetic for
    insertions. Residues outside the ANARCI-numbered region are not included.
    """
    payload = imgt_number_anarcii_indexed(seq)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    out: Dict[Tuple[int, str], str] = {}
    for r in rows:
        pos = r.get("pos")
        ins = r.get("ins_code", " ")
        aa = r.get("aa")
        if not isinstance(pos, int) or not isinstance(aa, str) or aa == "-":
            continue
        ins_norm = (str(ins) if ins is not None else " ")
        if ins_norm == "":
            ins_norm = " "
        out[(int(pos), ins_norm)] = aa
    return out


def _has_cdr3_insertions_in_family(
    rmap: Dict[Tuple[int, str], str],
    base_pos_family: List[int],
) -> bool:
    """Return True iff ``rmap`` contains at least one insertion-code residue at
    any of ``base_pos_family`` (e.g. [111] or [112])."""
    for (pos, ins), _aa in rmap.items():
        if pos in base_pos_family and ins.strip():
            return True
    return False


def _force_reshape_action(monkeypatch, max_calls: int = 6) -> Dict[str, int]:
    """Monkey-patch ``check_sap_against_strategy`` so the first ``max_calls``
    invocations report ``action="RESHAPE"`` (driving the loop to actually
    edit residues), then fall through to the real implementation so the
    function can terminate naturally.

    Returns a counter dict so callers can introspect how many forced calls
    were consumed.
    """
    counter = {"forced": 0, "passthrough": 0}
    real_fn = vhhu.check_sap_against_strategy

    def _wrapped(hydro_patch: float, strategy: str):
        if counter["forced"] < max_calls:
            counter["forced"] += 1
            return {
                "hydro_patch": hydro_patch,
                "strategy": strategy,
                "tier": "over_red",
                "pass": False,
                "action": "RESHAPE",
                "message": "[forced for test]",
                "thresholds": {"p50": 0.556, "p75": 0.639, "p90": 0.750},
                "standard_ref": "test override",
                "data_ref": "test override",
            }
        counter["passthrough"] += 1
        return real_fn(hydro_patch, strategy)

    monkeypatch.setattr(vhhu, "check_sap_against_strategy", _wrapped)
    return counter


def _assert_protection_invariants(donor: str, reshaped: str) -> None:
    """Core invariant assertions used by both test cases."""
    donor_map = _imgt_residue_map(donor)
    resh_map = _imgt_residue_map(reshaped)

    # 1. Reshaped sequence must still be ANARCI-numberable.
    assert resh_map, "Reshaped sequence failed to number via ANARCI."

    # 2. CDR1/CDR2/CDR3 (including insertion-code residues) must be identical.
    cdr_violations: List[str] = []
    for (pos, ins), donor_aa in donor_map.items():
        if not any(lo <= pos <= hi for lo, hi in CDR_IMGT_RANGES):
            continue
        resh_aa = resh_map.get((pos, ins))
        if resh_aa != donor_aa:
            cdr_violations.append(
                f"CDR drift @ IMGT {pos}{ins.strip()}: donor={donor_aa!r} reshaped={resh_aa!r}"
            )
    assert not cdr_violations, "CDR residues must remain identical:\n  " + "\n  ".join(cdr_violations)

    # 3. Tier 0 ∪ Tier 1 base positions must remain identical.
    tier_violations: List[str] = []
    for pos in sorted(PROTECTED_IMGT):
        donor_aa = donor_map.get((pos, " "))
        resh_aa = resh_map.get((pos, " "))
        if donor_aa is None and resh_aa is None:
            continue  # neither present; donor lacks this position (rare)
        if donor_aa != resh_aa:
            tier = "Tier0" if pos in TIER0_IMGT else "Tier1"
            tier_violations.append(
                f"{tier} drift @ IMGT {pos}: donor={donor_aa!r} reshaped={resh_aa!r}"
            )
    assert not tier_violations, "Tier 0/1 residues must remain identical:\n  " + "\n  ".join(tier_violations)


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_seq_a_has_cdr3_insertions_around_111():
    """Sanity precondition: SEQ_A's CDR3 must induce an insertion at base 111
    (otherwise this fixture isn't probing the insertion-code bug at all)."""
    rmap = _imgt_residue_map(SEQ_A)
    assert _has_cdr3_insertions_in_family(rmap, [111]), (
        "Test fixture invariant violated: SEQ_A was expected to produce "
        "an IMGT 111A/B-class insertion under ANARCI but did not. The "
        "bug-probe value of this test depends on real CDR3 insertion codes."
    )


def test_seq_b_has_cdr3_insertions_around_112():
    """Sanity precondition: SEQ_B's CDR3 must induce an insertion at base 112."""
    rmap = _imgt_residue_map(SEQ_B)
    assert _has_cdr3_insertions_in_family(rmap, [112]), (
        "Test fixture invariant violated: SEQ_B was expected to produce "
        "an IMGT 112A/B/C-class insertion under ANARCI but did not."
    )


def test_reshape_preserves_cdr_and_tier_for_seq_a(monkeypatch):
    """SEQ_A: long CDR3 (~18 aa) with 111A/111B insertions.

    With the pre-fix code, FR3 residues downstream of CDR3 had their linear
    indices shifted by the insertion count, so Tier 1 IMGT 71/73/78 could be
    edited by reshaping. The post-fix code must protect them by base position
    regardless of CDR3 length.
    """
    counter = _force_reshape_action(monkeypatch, max_calls=6)

    result = vhhu.surface_reshaping_trigger(SEQ_A, hydro_patch=0.99, strategy="S2")

    assert result["coord_provenance"] == "imgt_anarcii_v1", (
        f"Expected ANARCI-driven coords, got {result.get('coord_provenance')!r}; "
        f"note: {result.get('note')!r}"
    )
    # The forced RESHAPE drove the loop, so reshape MUST have attempted edits
    # if any FR position was eligible. If mutations is empty it can only be
    # because every eligible FR residue was already non-hydrophobic — record
    # that as an explicit assertion failure so the bug-probe value isn't lost.
    assert counter["forced"] > 0, "Forced-reshape monkeypatch was never invoked."
    assert result["mutations"], (
        "Expected the forced-reshape loop to perform at least one FR substitution "
        "on SEQ_A; got an empty mutation list. The protection invariants below "
        "would still hold, but the bug-probe value of this test would be lost."
    )

    _assert_protection_invariants(SEQ_A, result["reshaped_sequence"])


def test_reshape_preserves_cdr_and_tier_for_seq_b(monkeypatch):
    """SEQ_B: extra-long CDR3 (~22 aa) with 112A/112B/112C insertions.

    Stronger probe than SEQ_A because the FR3 linear shift is larger
    (every FR3 residue's linear index is offset by ~5 positions vs the
    canonical 13-aa CDR3 baseline).
    """
    counter = _force_reshape_action(monkeypatch, max_calls=6)

    result = vhhu.surface_reshaping_trigger(SEQ_B, hydro_patch=0.99, strategy="S2")

    assert result["coord_provenance"] == "imgt_anarcii_v1"
    assert counter["forced"] > 0, "Forced-reshape monkeypatch was never invoked."
    assert result["mutations"], (
        "Expected the forced-reshape loop to perform at least one FR substitution "
        "on SEQ_B; got an empty mutation list."
    )

    _assert_protection_invariants(SEQ_B, result["reshaped_sequence"])


def test_reshape_skips_cleanly_when_anarci_mapping_unavailable(monkeypatch):
    """If ANARCI mapping cannot be established, the function must refuse to
    edit — not silently fall back to the buggy linear-index proxy."""

    def _fail_map(_seq: str):
        return {}, {}, "simulated mapping failure"

    monkeypatch.setattr(vhhu, "_build_linear_to_imgt_map", _fail_map)

    result = vhhu.surface_reshaping_trigger(SEQ_A, hydro_patch=0.99, strategy="S2")

    assert result["success"] is False
    assert result["mutations"] == []
    # Reshaped sequence equals donor (modulo whitespace cleaning).
    assert result["reshaped_sequence"].replace(" ", "") == SEQ_A.replace(" ", "")
    assert result["coord_provenance"].startswith("skipped:")
