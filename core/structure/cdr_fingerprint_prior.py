"""
cdr_fingerprint_prior.py
========================
VAM V1.6 CHECK 6 — CDR Fingerprint Design Prior

Routes mutation library construction through observed natural-antibody
amino-acid frequencies at each IMGT CDR position. This is purely a
SAMPLING-PROBABILITY prior — it does not modify any structural Veto.

Database routing
----------------
- VH/VL projects -> data/reference/CDR_physchem_thresholds_v1.json
                    (AbRef-458, n=458, has aa_freq_by_position priors)
- VHH    projects -> data/reference/CDR_physchem_VHH71_v1.json
                    (VHH-71, n=68, threshold-only as of 2026-05-01)
                    For aa_freq_by_position fall back to the VHH-42
                    cohort embedded inside CDR_physchem_thresholds_v1.json
                    until VHH-71 priors are regenerated.

Public API
----------
load_fingerprint(antibody_format)         -> dict
position_aa_distribution(fp, locus, k)    -> {AA: freq}
weight_mutation_candidates(fp, ...)       -> [(mutation, weight), ...]
filter_candidates_by_frequency(...)       -> list[mutation]
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

# Pinned data paths — registered in config/abenginecore_registry.json::tier_1_data
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent
_VHVL_FP = _REPO_ROOT / "data" / "reference" / "CDR_physchem_thresholds_v1.json"
_VHH_FP = _REPO_ROOT / "data" / "reference" / "CDR_physchem_VHH71_v1.json"

AntibodyFormat = Literal["vh_vl", "vhh"]
LocusName = str  # e.g. "vh_cdr3", "vhh_cdr3"


@dataclass(frozen=True)
class FingerprintHandle:
    antibody_format: AntibodyFormat
    threshold_source: str
    prior_source: str
    thresholds_doc: dict
    priors_doc: dict


def load_fingerprint(antibody_format: AntibodyFormat) -> FingerprintHandle:
    """Load the appropriate fingerprint database for the given antibody format.

    Returns a handle with two underlying docs because for VHH the threshold
    source (VHH-71) and the design-prior source (VHH-42 inside the v1 file)
    currently differ.
    """
    if antibody_format == "vh_vl":
        with open(_VHVL_FP, encoding="utf-8") as fh:
            doc = json.load(fh)
        return FingerprintHandle(
            antibody_format="vh_vl",
            threshold_source=str(_VHVL_FP.relative_to(_REPO_ROOT)),
            prior_source=str(_VHVL_FP.relative_to(_REPO_ROOT)),
            thresholds_doc=doc,
            priors_doc=doc,
        )

    if antibody_format == "vhh":
        with open(_VHH_FP, encoding="utf-8") as fh:
            vhh71_doc = json.load(fh)
        with open(_VHVL_FP, encoding="utf-8") as fh:
            vhvl_doc = json.load(fh)
        return FingerprintHandle(
            antibody_format="vhh",
            threshold_source=str(_VHH_FP.relative_to(_REPO_ROOT)),
            prior_source=str(_VHVL_FP.relative_to(_REPO_ROOT)) + "::vhh_*",
            thresholds_doc=vhh71_doc,
            priors_doc=vhvl_doc,
        )

    raise ValueError(f"Unsupported antibody_format: {antibody_format!r}")


def _normalise_locus(locus: LocusName) -> LocusName:
    locus = locus.lower().replace("-", "_")
    if locus in {"h_cdr1", "h_cdr2", "h_cdr3"}:
        return "vh_" + locus.split("_", 1)[1]
    if locus in {"l_cdr1", "l_cdr2", "l_cdr3"}:
        return "vl_" + locus.split("_", 1)[1]
    return locus


def position_aa_distribution(
    fp: FingerprintHandle,
    locus: LocusName,
    position_index: int,
) -> dict[str, float]:
    """Return the observed AA frequency distribution at the k-th position
    of the named CDR locus (0-indexed, IMGT-segmented).

    Empty dict if the position is out of the observed length range.
    """
    locus = _normalise_locus(locus)
    loci_block = fp.priors_doc.get("loci", {})
    locus_block = loci_block.get(locus)
    if not locus_block:
        return {}
    prior_block = locus_block.get("design_prior") or locus_block.get("aa_priors") or {}
    aa_freq = prior_block.get("aa_freq_by_position") or []
    if not (0 <= position_index < len(aa_freq)):
        return {}
    return dict(aa_freq[position_index])


def filter_candidates_by_frequency(
    fp: FingerprintHandle,
    locus: LocusName,
    position_index: int,
    candidate_aas: Iterable[str],
    min_freq: float = 0.005,
) -> list[str]:
    """Return only candidate AAs observed at >= ``min_freq`` at this position.

    If the position has no observations (empty distribution), return the input
    list unchanged so the caller can fall back to uniform sampling.
    """
    dist = position_aa_distribution(fp, locus, position_index)
    if not dist:
        return list(candidate_aas)
    return [aa for aa in candidate_aas if dist.get(aa, 0.0) >= min_freq]


def weight_mutation_candidates(
    fp: FingerprintHandle,
    locus: LocusName,
    position_index: int,
    candidate_aas: Iterable[str],
    min_freq: float = 0.005,
) -> list[tuple[str, float]]:
    """Return [(AA, weight), ...] using the observed natural distribution.

    Weights are renormalised over the surviving candidates so they sum to 1.
    AAs below ``min_freq`` are dropped before renormalisation.
    """
    dist = position_aa_distribution(fp, locus, position_index)
    surviving = [(aa, dist.get(aa, 0.0)) for aa in candidate_aas if dist.get(aa, 0.0) >= min_freq]
    total = sum(w for _, w in surviving)
    if total <= 0:
        return [(aa, 1.0 / max(len(list(candidate_aas)), 1)) for aa in candidate_aas]
    return [(aa, w / total) for aa, w in surviving]


def design_prior_audit(
    fp: FingerprintHandle,
    locus: LocusName,
    position_index: int,
    proposed_aa: str,
    min_freq: float = 0.005,
) -> dict:
    """Per-mutation audit record for inclusion in the V1.6 standard report.

    Returns a structured verdict (PASS / WARN / VETO) plus the supporting
    natural-frequency value so QA can reconstruct decisions later.
    """
    dist = position_aa_distribution(fp, locus, position_index)
    if not dist:
        return {
            "verdict": "PASS",
            "rule": "no_natural_observation_at_this_position",
            "freq": None,
            "min_freq": min_freq,
            "locus": locus,
            "position_index": position_index,
            "proposed_aa": proposed_aa,
            "source": fp.prior_source,
        }
    freq = dist.get(proposed_aa, 0.0)
    if freq >= min_freq:
        verdict = "PASS"
    elif freq > 0.0:
        verdict = "WARN"
    else:
        verdict = "VETO"
    return {
        "verdict": verdict,
        "rule": "fingerprint_design_prior_v1.6",
        "freq": freq,
        "min_freq": min_freq,
        "locus": locus,
        "position_index": position_index,
        "proposed_aa": proposed_aa,
        "source": fp.prior_source,
    }


__all__ = [
    "FingerprintHandle",
    "load_fingerprint",
    "position_aa_distribution",
    "filter_candidates_by_frequency",
    "weight_mutation_candidates",
    "design_prior_audit",
]
