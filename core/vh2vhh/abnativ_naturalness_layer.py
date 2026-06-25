"""
AbNatiV Naturalness Layer — V1.7 Δ Layer for VH→VHH Pipeline
=============================================================

**Purpose:** Determine whether a VH sequence has "single-domain secretion potential"
by computing the delta between AbNatiV VHH2 score (naturalness as nanobody) and
AbNatiV VH2 score (naturalness as conventional paired VH).

    Δ = AbNatiV_VHH2 − AbNatiV_VH2

    Δ > +THRESH_POS  → VHH_biased    → single_domain_potential = LIKELY
    THRESH_NEG ≤ Δ ≤ THRESH_POS → neutral    → single_domain_potential = POSSIBLE
    Δ < THRESH_NEG   → VH_biased     → single_domain_potential = UNLIKELY

**Rationale (OBSERVATION 2026-05-08):**
The V1.6 `engineered_vh_similarity.py` layer measures similarity to Atlas-24
(engineered human VH), which is highly correlated with regular IgG VH frameworks.
Extended validation on 64 sequences (Cohen's d = −0.52, wrong direction) showed
that V1.6 cannot distinguish "secretable single-domain VH" from "paired-VH IgG VH".
The AbNatiV Δ layer directly addresses this gap.

**Pilot calibration data (2026-05-08, n=6 representative sequences):**
  Clinical VHH (Caplacizumab):       VH2=0.638  VHH2=0.865  Δ=+0.227  VHH_biased
  DB-B humanized camelid VHH:        VH2=0.594  VHH2=0.765  Δ=+0.171  VHH_biased
  Atlas-24 engineered autonomous VH: VH2=0.849  VHH2=0.869  Δ=+0.020  neutral
  Adalimumab (fully human IgG VH):   VH2=0.845  VHH2=0.795  Δ=−0.050  borderline
  Denosumab  (fully human IgG VH):   VH2=0.937  VHH2=0.803  Δ=−0.133  VH_biased
  Abagovomab (naive murine IgG VH):  VH2=0.559  VHH2=0.367  Δ=−0.192  VH_biased

**Relationship to V1.6:** Purely additive / orthogonal. V1.6 scores engineering
depth vs Atlas-24 prior. V1.7 scores single-domain naturalness. Both are needed
for complete VH→VHH evaluation.

**Conda env:** `anarcii` (AbNatiV installed; VH2 + VHH2 models pre-downloaded).

**Owner approval:** 2026-05-08 ("。VH").
**Standard reference:** docs/VH_TO_VHH_CONVERSION_STANDARD_V1.8.md §V1.7 (pending update).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Frozen 5-tier thresholds (V1.8.0 — 2026-05-09, AbNatiV2)
#
# Anchored on the VHH Clinical-26 & Atlas-24 (AbNatiV2 scoring):
#   Clinical VHH (n=26)           median Δ = +0.020  → EXCELLENT anchor
#   Atlas-24 engineered VH (n=24) median Δ = -0.074  → PASS lower-bound anchor
#
# Bump LAYER_VERSION and update these when re-calibrated on a larger dataset
# or when wet-lab secretion data become available.
# ─────────────────────────────────────────────────────────────────────────────
LAYER_VERSION = "V1.8.4-2026-05-14"

# Δ = VHH2 − VH2 tier thresholds (5-tier, AbNatiV2)
THRESH_EXCELLENT: float = +0.020   # Clinical VHH median
THRESH_GOOD: float      = -0.020   # Intermediate LIKELY lower bound
THRESH_PASS: float      = -0.050   # Potentially secretable (Adalimumab-like)
THRESH_FAIL: float      = -0.074   # Atlas-24 median (Engineered VH floor) — HARD GATE

# Absolute VHH2 floor — below this even a positive Δ is not reliable
VHH2_FLOOR: float = 0.50

# Absolute VH2 floor — below this the VH2 score is unreliable (murine framework)
VH2_FLOOR: float = 0.40

# Algorithm-target reference values (for VH→VHH pipeline benchmarking)
ALGORITHM_TARGET_MEDIAN_PASS: float = -0.074   # candidates' median Δ should reach Atlas-24
ALGORITHM_TARGET_MEDIAN_STRETCH: float = +0.020  # stretch goal: clinical VHH


@dataclass
class AbNatiVNaturalnessResult:
    """Output of score_naturalness_delta().

    Fields
    ------
    vh2_score : float
        AbNatiV VH2 score — how "natural" the sequence is as a conventional
        paired VH domain (0–1, higher = more natural as regular IgG VH).
    vhh2_score : float
        AbNatiV VHH2 score — how "natural" the sequence is as a VHH/nanobody
        single-domain (0–1, higher = more natural as VHH).
    delta : float
        vhh2_score − vh2_score. Positive → VHH-like; negative → VH-like.
    tier : str
        5-tier rating: 'EXCELLENT' / 'GOOD' / 'PASS' / 'WARN' / 'FAIL' / 'ERROR'.
    verdict : str
        'VHH_biased' / 'neutral' / 'VH_biased' (legacy 3-tier flag, kept for
        backward compatibility).
    single_domain_potential : str
        'LIKELY' / 'POSSIBLE' / 'UNLIKELY' (legacy 3-tier flag).
    layer_version : str
        Frozen threshold version tag for audit traceability.
    notes : list[str]
        Any quality warnings (e.g., VH2 below floor, short sequence).
    error : str | None
        Set if scoring failed; other fields will be None / default.
    """

    vh2_score: Optional[float]
    vhh2_score: Optional[float]
    delta: Optional[float]
    tier: str
    verdict: str
    single_domain_potential: str
    layer_version: str = LAYER_VERSION
    notes: list = field(default_factory=list)
    error: Optional[str] = None


# ── Heavy imports (cached at module level) ───────────────────────────────────
_ABNATIV_SCORING = None

def _get_abnativ_scoring():
    global _ABNATIV_SCORING
    if _ABNATIV_SCORING is None:
        from abnativ.model.scoring_functions import abnativ_scoring
        _ABNATIV_SCORING = abnativ_scoring
    return _ABNATIV_SCORING


def score_naturalness_delta(
    sequence: str,
    *,
    seq_id: str = "query",
    verbose: bool = False,
) -> AbNatiVNaturalnessResult:
    """Compute AbNatiV VH2 + VHH2 dual scores and return Δ-based verdict.

    Parameters
    ----------
    sequence : str
        Amino-acid string for the VH or VHH domain. Non-ACDEFGHIKLMNPQRSTVWY
        characters are stripped before scoring.
    seq_id : str
        Label for logging; does not affect scoring.
    verbose : bool
        If True, prints AbNatiV progress messages.

    Returns
    -------
    AbNatiVNaturalnessResult
        Structured result with scores, delta, verdict, and quality notes.
    """
    # ── 1. Clean sequence ─────────────────────────────────────────────────────
    valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
    seq_clean = "".join(aa for aa in sequence.upper() if aa in valid_aa)

    notes: list[str] = []

    if len(seq_clean) < 90:
        return AbNatiVNaturalnessResult(
            vh2_score=None, vhh2_score=None, delta=None,
            tier="ERROR", verdict="ERROR", single_domain_potential="ERROR",
            notes=[f"Sequence too short: {len(seq_clean)} aa (min 90)"],
            error="sequence_too_short",
        )

    try:
        from Bio.Seq import Seq
        from Bio.SeqRecord import SeqRecord
        abnativ_scoring = _get_abnativ_scoring()
    except ImportError as e:
        return AbNatiVNaturalnessResult(
            vh2_score=None, vhh2_score=None, delta=None,
            tier="ERROR", verdict="ERROR", single_domain_potential="ERROR",
            notes=[], error=f"ImportError: {e}",
        )

    rec = [SeqRecord(Seq(seq_clean), id=seq_id)]

    try:
        df_vh2, _ = abnativ_scoring(
            model_type="VH",
            seq_records=rec,
            batch_size=1,
            mean_score_only=True,
            do_align=True,
            is_VHH=False,
            verbose=verbose,
            run_parall_al=False,
        )
        vh2 = round(float(df_vh2.iloc[0]["AbNatiV VH Score"]), 4)
    except Exception as e:
        return AbNatiVNaturalnessResult(
            vh2_score=None, vhh2_score=None, delta=None,
            tier="ERROR", verdict="ERROR", single_domain_potential="ERROR",
            notes=[], error=f"VH2 scoring failed: {e}",
        )

    try:
        df_vhh2, _ = abnativ_scoring(
            model_type="VHH",
            seq_records=rec,
            batch_size=1,
            mean_score_only=True,
            do_align=True,
            is_VHH=True,
            verbose=verbose,
            run_parall_al=False,
        )
        vhh2 = round(float(df_vhh2.iloc[0]["AbNatiV VHH Score"]), 4)
    except Exception as e:
        return AbNatiVNaturalnessResult(
            vh2_score=vh2, vhh2_score=None, delta=None,
            tier="ERROR", verdict="ERROR", single_domain_potential="ERROR",
            notes=[], error=f"VHH2 scoring failed: {e}",
        )

    delta = round(vhh2 - vh2, 4)

    if vh2 < VH2_FLOOR:
        notes.append(f"VH2 score {vh2:.3f} below floor {VH2_FLOOR} — murine or non-standard framework.")
    if vhh2 < VHH2_FLOOR:
        notes.append(f"VHH2 score {vhh2:.3f} below floor {VHH2_FLOOR} — may not fold as VHH.")

    # ── 5-tier rating (V1.8.4, anchored on Atlas-24 hard gate) ──────────────
    if delta >= THRESH_EXCELLENT:
        tier = "EXCELLENT"
        verdict = "VHH_biased"
        potential = "LIKELY"
    elif delta >= THRESH_GOOD:
        tier = "GOOD"
        verdict = "VHH_biased"
        potential = "LIKELY"
    elif delta >= THRESH_PASS:
        tier = "PASS"
        verdict = "neutral"
        potential = "POSSIBLE"
    elif delta >= THRESH_FAIL:
        tier = "WARN"
        verdict = "neutral"
        potential = "POSSIBLE"
    else:
        tier = "FAIL"
        verdict = "VH_biased"
        potential = "UNLIKELY"

    # Override if both VH2 and VHH2 are very low (degraded scoring)
    if vh2 < VH2_FLOOR and vhh2 < VHH2_FLOOR:
        notes.append("Both VH2 and VHH2 below floor — structural integrity uncertain.")
        tier = "WARN" if tier in ("EXCELLENT", "GOOD", "PASS") else tier
        potential = "UNLIKELY"

    return AbNatiVNaturalnessResult(
        vh2_score=vh2,
        vhh2_score=vhh2,
        delta=delta,
        tier=tier,
        verdict=verdict,
        single_domain_potential=potential,
        layer_version=LAYER_VERSION,
        notes=notes,
    )
