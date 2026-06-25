"""
Engineered VH Similarity Score — V1.6 Evidence Layer (Step 1, non-LOCKED)
=========================================================================

Computes a [0, 1] similarity score between a candidate VHH (post VH→VHH
conversion) and the **Atlas-24** prior — the 24 Engineered_Human_VH entries
in `data/vhh_design_atlas_v3.json` whose statistics were frozen on
2026-04-30 by `scripts/analyze_engineered_vh24_site_map.py`.

This module is **purely additive**. It does not change V1.5 algorithm
thresholds, BLOCKER/WARN logic, or the existing payload schema. Its output
is intended to be appended as `engineered_vh_similarity` to the V1.6 report
payload (LOCKED-file integration is a separate, explicitly approved step).

Frozen priors live as module-level constants. They are not loaded from JSON
at runtime to avoid hidden drift; bumping the prior requires bumping
`ATLAS24_PRIOR_VERSION` and updating EVOLUTION_LOG.

Dependencies:
- `core.humanization.kabat_utils.kabat_from_anarcii` — canonical Kabat dict
  (KabatKey = (int_pos, ins_code)). Mandatory per Owner-locked rule.
- `anarcii` (env: `anarcii`) — antibody numbering.

Author: AbEngineCore Agent (V1.6 prep)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Frozen Atlas-24 prior (provenance: ENGINEERED_VH24_SITE_MAP.json, 2026-04-30)
# ─────────────────────────────────────────────────────────────────────────────
ATLAS24_PRIOR_VERSION = "atlas24_v1.0_2026-04-30"
ATLAS24_N = 24

# CDR-H3 metric percentiles (from ENGINEERED_VH24_SITE_MAP.json §1)
ATLAS24_CDR3_LEN     = {"min": 3,    "p25": 9.5,    "median": 10.5,  "p75": 15.0,  "max": 19}
ATLAS24_CDR3_CHARGE  = {"min": -2,   "p25": -2.0,   "median": -1.0,  "p75":  1.0,  "max":  3}
ATLAS24_CDR3_GRAVY   = {"min": -2.03,"p25": -1.097, "median": -1.033,"p75": -0.565,"max":  0.05}
ATLAS24_ALLCDR_GRAVY = {"min": -1.297,"p25": -0.829,"median": -0.6,  "p75": -0.492,"max":  0.028}

# Hallmark motifs observed in Atlas-24 (count). Anything not in this set is
# considered an "off-Atlas" hallmark and gets a partial score only if its
# 4-letter pattern still resembles the observed motif vocabulary by 3-of-4.
ATLAS24_HALLMARK_MOTIFS: Dict[str, int] = {
    "VGRW": 5, "VGEL": 4, "VALW": 2, "FERF": 2, "VGPW": 2,
    "VERW": 1, "FERW": 1, "FERI": 1, "VGLR": 1, "VTPW": 1,
    "VGEW": 1, "VGPV": 1, "VAQW": 1, "FGRL": 1,
}

# Stealth departure (35/50/89/94) count distribution in Atlas-24.
# Source: ENGINEERED_VH24_SITE_MAP.md §5.
ATLAS24_STEALTH_DEPARTURE_RATE: Dict[int, float] = {
    0: 0.0,
    1: 0.167,
    2: 0.083,
    3: 0.708,
    4: 0.042,
}

# Liability base rates (used as background priors for penalty calibration).
ATLAS24_LIABILITY_RATES = {
    "any_cdr_nglyc":     0.042,
    "any_cdr_deamid":    0.125,
    "cdr3_anchor_risk":  0.083,
}

# IGHV3-23 reference at the 8 focus Kabat positions (VH→VHH stealth/hallmark
# decision sites). Same as analyzed in scripts/analyze_engineered_vh24_site_map.py.
IGHV3_23_REF: Dict[int, str] = {
    35: "S", 37: "V", 44: "G", 45: "L",
    47: "W", 50: "A", 89: "V", 94: "K",
}

# Component weights — sum should be 1.0. Liability is a multiplicative penalty,
# applied on top of the weighted average.
WEIGHTS = {
    "hallmark_motif":   0.25,
    "stealth_pattern":  0.20,
    "cdr3_charge":      0.20,
    "cdr_hydrophilicity": 0.20,
    "cdr3_envelope":    0.15,  # length within Atlas-24 envelope
}

# Liability penalty (multiplicative): one flag → ×0.85, two → ×0.70, three → ×0.55.
LIABILITY_PENALTIES = {0: 1.0, 1: 0.85, 2: 0.70, 3: 0.55}

# ─────────────────────────────────────────────────────────────────────────────
# Local helpers (kept here to keep the module self-contained; logic mirrors
# `scripts/analyze_engineered_vh24_site_map.py`)
# ─────────────────────────────────────────────────────────────────────────────
KD_SCALE = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5,
    "E": -3.5, "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9,
    "M": 1.9, "F": 2.8, "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9,
    "Y": -1.3, "V": 4.2,
}


def _gravy(seq: str) -> float:
    if not seq:
        return 0.0
    return round(sum(KD_SCALE.get(aa, 0.0) for aa in seq) / len(seq), 3)


def _net_charge(seq: str) -> int:
    return sum(1 for aa in seq if aa in "KRH") - sum(1 for aa in seq if aa in "DE")


def _has_nglyc(seq: str) -> bool:
    for i in range(len(seq) - 2):
        if seq[i] == "N" and seq[i + 1] != "P" and seq[i + 2] in "ST":
            return True
    return False


def _has_deamid(seq: str) -> bool:
    return "NG" in seq or "NS" in seq


def _kabat_extract(seq: str) -> Tuple[Dict[int, str], str, str, str]:
    """Run ANARCI in Kabat scheme; return (focus_residues, cdr1, cdr2, cdr3).

    Uses `core.humanization.kabat_utils.kabat_from_anarcii` to honor the
    locked KabatKey contract. Returns base-position residues only at the 8
    focus positions (insertion codes in CDR loops are kept inside the CDR
    string but not used for the hallmark/stealth lookup).
    """
    from anarcii import Anarcii  # local import — env-only dependency
    from core.humanization.kabat_utils import kabat_from_anarcii, sorted_keys

    a = Anarcii(seq_type="antibody", mode="accuracy", verbose=False)
    a.number([seq])
    entry = a.to_scheme("kabat").get("Sequence 1", {})
    if entry.get("error") or entry.get("chain_type") != "H":
        raise ValueError(entry.get("error") or "ANARCI did not identify a heavy chain")

    kd = kabat_from_anarcii(entry["numbering"])

    focus: Dict[int, str] = {}
    cdr1, cdr2, cdr3 = [], [], []
    for (pos, ins) in sorted_keys(kd):
        aa = kd[(pos, ins)]
        if pos in IGHV3_23_REF and ins == "":
            focus[pos] = aa
        if 31 <= pos <= 35:
            cdr1.append(aa)
        elif 50 <= pos <= 65:
            cdr2.append(aa)
        elif 95 <= pos <= 102:
            cdr3.append(aa)
    return focus, "".join(cdr1), "".join(cdr2), "".join(cdr3)


# ─────────────────────────────────────────────────────────────────────────────
# Component scoring
# ─────────────────────────────────────────────────────────────────────────────

def _score_in_band(value: float, p25: float, p75: float, lo: float, hi: float) -> float:
    """1.0 if in P25–P75; 0.5 if in (lo, hi) but outside P25–P75; 0.0 outside."""
    if p25 <= value <= p75:
        return 1.0
    if lo <= value <= hi:
        return 0.5
    return 0.0


def _hallmark_score(motif: str) -> Tuple[float, str]:
    if motif in ATLAS24_HALLMARK_MOTIFS:
        n = ATLAS24_HALLMARK_MOTIFS[motif]
        # Common (>=2 cases) → full credit; rare (1 case) → 0.85
        return (1.0 if n >= 2 else 0.85, "atlas24_observed")
    # Loose match: 3 of 4 letters identical to any Atlas motif
    for ref in ATLAS24_HALLMARK_MOTIFS:
        if sum(1 for a, b in zip(motif, ref) if a == b) >= 3:
            return (0.5, "atlas24_3of4_match")
    return (0.0, "off_atlas")


def _stealth_score(focus: Dict[int, str]) -> Tuple[float, int, List[int]]:
    departures = [pos for pos in (35, 50, 89, 94) if focus.get(pos) and focus[pos] != IGHV3_23_REF[pos]]
    n = len(departures)
    rate = ATLAS24_STEALTH_DEPARTURE_RATE.get(n, 0.0)
    # Normalize by peak rate (≈0.708 at n=3) — full credit for 3, partial for others.
    peak = max(ATLAS24_STEALTH_DEPARTURE_RATE.values())
    score = round(rate / peak, 3) if peak > 0 else 0.0
    return score, n, departures


def _charge_score(cdr3: str) -> Tuple[float, int]:
    nc = _net_charge(cdr3)
    score = _score_in_band(nc, ATLAS24_CDR3_CHARGE["p25"], ATLAS24_CDR3_CHARGE["p75"],
                           ATLAS24_CDR3_CHARGE["min"], ATLAS24_CDR3_CHARGE["max"])
    return score, nc


def _hydrophilicity_score(cdr1: str, cdr2: str, cdr3: str) -> Tuple[float, float, float]:
    cdr3_g = _gravy(cdr3)
    all_g = _gravy(cdr1 + cdr2 + cdr3)
    s_cdr3 = _score_in_band(cdr3_g, ATLAS24_CDR3_GRAVY["p25"], ATLAS24_CDR3_GRAVY["p75"],
                            ATLAS24_CDR3_GRAVY["min"], ATLAS24_CDR3_GRAVY["max"])
    s_all = _score_in_band(all_g, ATLAS24_ALLCDR_GRAVY["p25"], ATLAS24_ALLCDR_GRAVY["p75"],
                           ATLAS24_ALLCDR_GRAVY["min"], ATLAS24_ALLCDR_GRAVY["max"])
    return round((s_cdr3 + s_all) / 2.0, 3), cdr3_g, all_g


def _envelope_score(cdr3: str) -> float:
    return _score_in_band(len(cdr3),
                          ATLAS24_CDR3_LEN["p25"], ATLAS24_CDR3_LEN["p75"],
                          ATLAS24_CDR3_LEN["min"], ATLAS24_CDR3_LEN["max"])


def _liability_flags(cdr1: str, cdr2: str, cdr3: str) -> List[str]:
    flags = []
    all_cdr = cdr1 + cdr2 + cdr3
    if _has_nglyc(all_cdr):
        flags.append("any_cdr_nglyc")
    if _has_deamid(all_cdr):
        flags.append("any_cdr_deamid")
    if cdr3 and cdr3[0] in "PD":
        flags.append("cdr3_anchor_risk")
    return flags


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EngineeredVhSimilarityResult:
    score: float                     # final [0, 1]
    score_band: str                  # "high" / "medium" / "low"
    prior_version: str = ATLAS24_PRIOR_VERSION
    components: Dict[str, float] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)
    flags: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 3),
            "score_band": self.score_band,
            "prior_version": self.prior_version,
            "components": {k: round(v, 3) for k, v in self.components.items()},
            "evidence": self.evidence,
            "flags": self.flags,
            "notes": self.notes,
        }


def _band(score: float) -> str:
    if score >= 0.70:
        return "high"
    if score >= 0.40:
        return "medium"
    return "low"


def score_engineered_vh_similarity(
    sequence: str,
    *,
    extra_notes: Optional[List[str]] = None,
) -> EngineeredVhSimilarityResult:
    """Compute Engineered VH Similarity (Atlas-24 prior) for a candidate VHH.

    Parameters
    ----------
    sequence : str
        Full VH/VHH amino acid sequence (already converted candidate or
        original VH; Kabat numbering is computed internally).
    extra_notes : Optional[List[str]]
        Free-text annotations to forward into the result.

    Returns
    -------
    EngineeredVhSimilarityResult
        Score, components, evidence, and flags. On ANARCI failure the score
        is 0.0 with a note; the V1.5 pipeline must continue to operate
        normally regardless of this layer.
    """
    seq = "".join(ch for ch in (sequence or "").upper() if ch.isalpha())
    notes = list(extra_notes or [])

    if len(seq) < 60:
        return EngineeredVhSimilarityResult(
            score=0.0, score_band="low",
            notes=notes + [f"sequence_len={len(seq)} too short — not scored"],
        )

    # ANARCI naturally trims linkers / Fc / extra constructs to the heavy
    # variable region. We accept inputs up to ~600 aa (full constructs) and
    # rely on ANARCI to surface only V-region residues.
    if len(seq) > 600:
        return EngineeredVhSimilarityResult(
            score=0.0, score_band="low",
            notes=notes + [f"sequence_len={len(seq)} above 600 aa — not scored"],
        )

    try:
        focus, cdr1, cdr2, cdr3 = _kabat_extract(seq)
    except Exception as exc:
        return EngineeredVhSimilarityResult(
            score=0.0, score_band="low",
            notes=notes + [f"anarci_failed: {exc}"],
        )

    motif = "".join(focus.get(p, "?") for p in (37, 44, 45, 47))
    s_motif, motif_label = _hallmark_score(motif)
    s_stealth, n_dep, deps = _stealth_score(focus)
    s_charge, cdr3_charge = _charge_score(cdr3)
    s_hydro, cdr3_g, all_g = _hydrophilicity_score(cdr1, cdr2, cdr3)
    s_env = _envelope_score(cdr3)

    components = {
        "hallmark_motif":   s_motif,
        "stealth_pattern":  s_stealth,
        "cdr3_charge":      s_charge,
        "cdr_hydrophilicity": s_hydro,
        "cdr3_envelope":    s_env,
    }
    weighted = sum(components[k] * WEIGHTS[k] for k in components)

    flags = _liability_flags(cdr1, cdr2, cdr3)
    penalty = LIABILITY_PENALTIES.get(min(len(flags), 3), 0.55)
    final = round(weighted * penalty, 3)

    evidence = {
        "hallmark_motif":     motif,
        "hallmark_label":     motif_label,
        "stealth_departures": {"count": n_dep, "positions": deps},
        "cdr1_seq":           cdr1,
        "cdr2_seq":           cdr2,
        "cdr3_seq":           cdr3,
        "cdr3_len":           len(cdr3),
        "cdr3_net_charge":    cdr3_charge,
        "cdr3_gravy":         cdr3_g,
        "all_cdr_gravy":      all_g,
        "liability_penalty":  penalty,
        "atlas24_n":          ATLAS24_N,
    }

    if final >= 0.70:
        notes.append("Candidate sits inside the Atlas-24 success envelope.")
    elif final < 0.40:
        notes.append("Candidate is far from the Atlas-24 success envelope; review report risk matrix.")

    return EngineeredVhSimilarityResult(
        score=final,
        score_band=_band(final),
        components=components,
        evidence=evidence,
        flags=flags,
        notes=notes,
    )
