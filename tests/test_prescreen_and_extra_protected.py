"""P0-2 + P1-4 acceptance tests.

P0-2 (enforce_prescreen contract):
  - When enforce_prescreen=True (CLI/engine default), humanize_vhh runs the
    standard §0.4 prescreen immediately after CDR extraction. On hard-gate
    rules (e.g. SAP > 0.771 or CDR3 length ≥ 25 aa) it short-circuits with route=
    "surface_reshaping_only" + a populated `prescreen` block, and returns
    no `best_match`.
  - When enforce_prescreen=False (API-layer contract), the same input
    bypasses the gate — the function proceeds to scaffold matching even on
    hard-gate sequences. This documents the API's responsibility to gate
    upstream.
  - The wrapper humanize_vhh_with_qa propagates this and skips QA when the
    short-circuit fires (status="PRESCREEN_SURFACE_RESHAPING_ONLY").

P1-4 (extra_protected union semantics):
  - extra_protected is now a UNION with the strategy/CDR3-aware dynamic set
    (was an OVERRIDE pre-V3.3). Result["_protected_provenance"] records
    both sources so reports/QA can audit the protection set.

Tests use real clinical / SAbDab VHHs from VHH42 supplement so behaviour
matches production data. ANARCI is required; tests skip gracefully if absent.
"""

from __future__ import annotations

from typing import Set

import pytest

# ANARCI is required for the function under test; skip gracefully if absent.
anarcii = pytest.importorskip("anarcii")  # noqa: F841

from core import vhh_humanization as vhhu  # noqa: E402
from core.vhh_humanization_with_qa import humanize_vhh_with_qa  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

# Hard-gate trigger: SAP proxy > 0.771 (VHH68 p90 red-zone rule).
# Synthetic stress case derived from SEQ_NORMAL with a hydrophobic CDR3 patch.
SEQ_HARD_GATE_SAP = (
    "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRD"
    "RNAKNTLYLQMNSLRAEDTAVYYCAALLLLLLLLLDYWGQGTLVTVSS"
)

# Standard clinical VHH with canonical-length CDR3 (~13 aa), expected to pass
# all §0.4 hard-gate rules. Source: VHH42 CMC metrics row 1 (131I-GMIB-Anti-
# HER2-VHH1).
SEQ_NORMAL = (
    "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTI"
    "SRDNAKNTLYLQMNSLRAEDTAVYYCAAYDIYGDGAMDYWGQGTLVTVSS"
)


# ── P0-2 tests ────────────────────────────────────────────────────────────────


def test_p0_2_hard_gate_short_circuits_with_route_marker():
    """enforce_prescreen=True + hard-gate donor → route='surface_reshaping_only'."""
    result = vhhu.humanize_vhh(
        seq=SEQ_HARD_GATE_SAP,
        panel="A",
        enforce_prescreen=True,
    )

    assert result.get("route") == "surface_reshaping_only", (
        f"Expected route='surface_reshaping_only' on hard-gate donor, "
        f"got route={result.get('route')!r}"
    )
    # Decision was made successfully — `success` flags pipeline correctness,
    # not "humanization happened". No best_match must be present.
    assert result.get("success") is True
    assert result.get("best_match") is None
    assert result.get("candidates") == []

    ps = result.get("prescreen") or {}
    assert ps.get("recommendation") == "surface_reshaping_only"
    assert isinstance(ps.get("triggered_rules"), list) and ps["triggered_rules"]
    assert "sap_red_zone_mandatory" in ps["triggered_rules"], (
        f"Expected SAP hard-gate trigger; triggered={ps.get('triggered_rules')!r}"
    )
    raw = ps.get("raw_metrics") or {}
    assert raw.get("SAP_proxy", 0) > 0.771, (
        f"Expected SAP > 0.771 to fire the hard gate; got {raw.get('SAP_proxy')}"
    )


def test_p0_2_enforce_false_bypasses_prescreen():
    """enforce_prescreen=False → no short-circuit, function attempts the
    full pipeline regardless of hard-gate metrics. Used by the API layer
    which has its own 5-route prescreen upstream."""
    result = vhhu.humanize_vhh(
        seq=SEQ_HARD_GATE_SAP,
        panel="A",
        enforce_prescreen=False,
    )

    # Hard gate must NOT have short-circuited the pipeline.
    assert result.get("route") != "surface_reshaping_only", (
        "enforce_prescreen=False must bypass the hard gate; "
        f"got route={result.get('route')!r}"
    )
    # The prescreen block should explicitly note the skip (not silently absent).
    ps = result.get("prescreen") or {}
    assert ps.get("recommendation") == "skipped_by_caller", (
        f"Expected prescreen.recommendation='skipped_by_caller' to advertise "
        f"the bypass; got {ps.get('recommendation')!r}"
    )


def test_p0_2_normal_sequence_passes_through_with_prescreen_recorded():
    """enforce_prescreen=True + canonical-length VHH → normal flow proceeds,
    and the prescreen verdict is still recorded for transparency."""
    result = vhhu.humanize_vhh(
        seq=SEQ_NORMAL,
        panel="A",
        enforce_prescreen=True,
    )

    assert result.get("success") is True, (
        f"Normal VHH should succeed; error={result.get('error')!r}"
    )
    assert result.get("route") in ("humanization", "humanization_plus_reshape",
                                    "humanization_plus_charge", "borderline"), (
        f"Normal VHH should not be routed to surface_reshaping_only; "
        f"got route={result.get('route')!r}"
    )
    # Prescreen must be recorded even on the success path.
    ps = result.get("prescreen") or {}
    assert ps.get("recommendation") in ("humanization", "humanization_plus_reshape",
                                         "humanization_plus_charge", "borderline"), (
        f"Prescreen recommendation absent on success path: {ps!r}"
    )
    assert "raw_metrics" in ps and ps["raw_metrics"].get("cdr3_len", 0) > 0


def test_p0_2_qa_wrapper_propagates_short_circuit():
    """humanize_vhh_with_qa must mirror humanize_vhh's short-circuit and
    skip QA when route='surface_reshaping_only' (no best_match to validate)."""
    result = humanize_vhh_with_qa(
        seq=SEQ_HARD_GATE_SAP,
        panel="A",
        enforce_prescreen=True,
        enable_safe_mode=False,
        strict_qa=False,
    )

    assert result.get("route") == "surface_reshaping_only"
    assert result.get("status") == "PRESCREEN_SURFACE_RESHAPING_ONLY"
    qa = result.get("qa") or {}
    assert qa.get("ok") is False
    # QA validators must NOT have run (no errors generated, just the skip note).
    assert isinstance(qa.get("warnings"), list) and any(
        "Prescreen routed to surface_reshaping_only" in w for w in qa["warnings"]
    ), f"Expected QA-skip warning; got warnings={qa.get('warnings')!r}"


# ── P1-4 tests ────────────────────────────────────────────────────────────────


def test_p1_4_extra_protected_unions_with_dynamic_set():
    """extra_protected={50} on a normal donor must:
       1. preserve the dynamic Tier 0/CDR3-aware positions (NOT override),
       2. add 50 to the union,
       3. record both sources in _protected_provenance.
    """
    extra: Set[int] = {50}
    result = vhhu.humanize_vhh(
        seq=SEQ_NORMAL,
        panel="A",  # S1: smallest dynamic set, easiest to inspect
        enforce_prescreen=True,
        extra_protected=extra,
    )
    assert result.get("success") is True

    prov = result.get("_protected_provenance")
    assert isinstance(prov, dict), (
        "Expected _protected_provenance dict on result; got "
        f"{type(prov).__name__}: {prov!r}"
    )

    from_dynamic = set(prov.get("from_dynamic") or [])
    from_extra = set(prov.get("from_extra") or [])
    union = set(prov.get("union") or [])

    # 1. Dynamic positions must include canonical Tier 0 (28, 29, 44, 45, 47, 94)
    #    minus position 37 which is CDR1 in standard V2.4. We assert the most
    #    invariant ones (Hallmarks 44/45/47) are still in the dynamic set.
    for p in (44, 45, 47, 94):
        assert p in from_dynamic, (
            f"Tier 0 IMGT {p} missing from from_dynamic={sorted(from_dynamic)}; "
            "extra_protected must NOT override the dynamic set."
        )

    # 2. extra_protected must appear in from_extra and in the union.
    assert from_extra == extra, (
        f"from_extra mismatch: expected {extra}, got {from_extra}"
    )
    assert 50 in union, f"50 missing from protected union: {sorted(union)}"

    # 3. union == from_dynamic ∪ from_extra (set algebra invariant).
    assert union == from_dynamic | from_extra, (
        "union must equal set-union of dynamic and extra; "
        f"got union={sorted(union)}, dyn∪extra={sorted(from_dynamic | from_extra)}"
    )

    # 4. Provenance metadata sanity.
    assert prov.get("strategy") == "S1"
    assert prov.get("extra_provided") is True
    assert isinstance(prov.get("dynamic_upgrades"), list)


def test_short_cdr3_7_10_enhances_fr3_protection_mode():
    """CDR3 7-10 should be allowed, with FR3 73/78 enhanced protection."""
    info = vhhu.get_cdr3_aware_protected_positions(cdr3_len=8, strategy="S1")
    protected = set(info.get("protected_positions") or set())
    assert {73, 78}.issubset(protected), (
        f"Expected FR3 73/78 enhanced protection for CDR3 7-10; got {sorted(protected)}"
    )
    assert 71 not in protected, (
        "FR3 71 should be reserved for very-short CDR3 (<=6) high-contact mode."
    )


def test_very_short_cdr3_le6_enhances_fr3_high_contact_mode():
    """CDR3<=6 should enable high FR3-contact mode (71/73/78)."""
    info = vhhu.get_cdr3_aware_protected_positions(cdr3_len=6, strategy="S1")
    protected = set(info.get("protected_positions") or set())
    assert {71, 73, 78}.issubset(protected), (
        f"Expected high FR3-contact protection 71/73/78 for CDR3<=6; got {sorted(protected)}"
    )


def test_p1_4_extra_protected_none_records_empty_extra_set():
    """When extra_protected is None, provenance must show from_extra=[] and
    extra_provided=False (not silently absent)."""
    result = vhhu.humanize_vhh(
        seq=SEQ_NORMAL,
        panel="A",
        enforce_prescreen=True,
        extra_protected=None,
    )
    assert result.get("success") is True

    prov = result.get("_protected_provenance") or {}
    assert prov.get("from_extra") == []
    assert prov.get("extra_provided") is False
    # Dynamic set must still be populated.
    assert set(prov.get("from_dynamic") or []) >= {44, 45, 47, 94}
    assert set(prov.get("union") or []) == set(prov.get("from_dynamic") or [])
