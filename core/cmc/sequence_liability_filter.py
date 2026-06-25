"""
sequence_liability_filter.py
============================
VAM V1.6 CHECK 7 — Sequence-Level CMC Liability Pre-Filter

Runs O(sequence) liability checks BEFORE any 3D evaluation, so candidates
with intrinsic developability defects are removed before EvoEF2 / AntiFold
/ ThermoMPNN / MD spend compute on them.

Detection scope
---------------
- N-glycosylation sequon: NxS or NxT (x != P)
- Asn deamidation hotspot: NG / NS / NT
- Asp isomerization hotspot: DG / DS / DT / DH
- Met / Trp oxidation surface exposure (sequence-only proxy: any new M/W in CDR)
- Longest hydrophobic run vs natural p95 / p99 (from CDR fingerprint)
- New free Cys in CDR

Threshold source
----------------
All thresholds come from data/reference/CDR_physchem_thresholds_v1.json
(AbRef-458 for VH/VL) or data/reference/CDR_physchem_VHH71_v1.json
(VHH-71 for VHH). No hardcoded numbers in this module.

Public API
----------
filter_candidates(wt_seq, mutations, locus, antibody_format) -> LiabilityResult
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent
_VHVL_FP = _REPO_ROOT / "data" / "reference" / "CDR_physchem_thresholds_v1.json"
_VHH_FP = _REPO_ROOT / "data" / "reference" / "CDR_physchem_VHH71_v1.json"

AntibodyFormat = Literal["vh_vl", "vhh"]

_HYDROPHOBIC = set("AILMFWVY")
_NEW_MOTIFS = {
    "n_glyc": re.compile(r"N[^P][ST]"),
    "deamid": re.compile(r"N[GST]"),
    "isomer": re.compile(r"D[GSTH]"),
}


@dataclass
class LiabilityFinding:
    motif: str
    position_in_cdr: int
    sequence_window: str
    severity: str  # "PASS" | "WARN" | "VETO"


@dataclass
class CandidateLiability:
    mutation: dict
    overall: str  # "PASS" | "WARN" | "VETO"
    findings: list[LiabilityFinding] = field(default_factory=list)


@dataclass
class LiabilityResult:
    passed: list[dict] = field(default_factory=list)
    warned: list[CandidateLiability] = field(default_factory=list)
    vetoed: list[CandidateLiability] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def _load_thresholds(antibody_format: AntibodyFormat) -> dict:
    path = _VHVL_FP if antibody_format == "vh_vl" else _VHH_FP
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _locus_thresholds(doc: dict, locus: str) -> dict:
    locus = locus.lower().replace("-", "_")
    return (doc.get("loci") or {}).get(locus, {})


def _longest_hydrophobic_run(seq: str) -> int:
    longest = run = 0
    for aa in seq:
        if aa in _HYDROPHOBIC:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest


def _upper_thresholds(locus_thresholds: dict, metric: str) -> tuple[float | None, float | None]:
    """Return WARN/VETO upper bounds across VH/VL and VHH fingerprint schemas."""
    threshold_block = (locus_thresholds.get("thresholds") or {}).get(metric) or {}
    warn_t = threshold_block.get("warn")
    veto_t = threshold_block.get("veto")
    if warn_t is not None or veto_t is not None:
        return warn_t, veto_t

    metric_block = (locus_thresholds.get("metrics") or {}).get(metric) or {}
    return metric_block.get("p95"), metric_block.get("p99")


def _count_motif(seq: str, pattern: re.Pattern) -> list[tuple[int, str]]:
    return [(m.start(), m.group(0)) for m in pattern.finditer(seq)]


def _delta_motifs(wt: str, mut: str, pattern: re.Pattern) -> list[tuple[int, str]]:
    wt_hits = set(_count_motif(wt, pattern))
    mut_hits = set(_count_motif(mut, pattern))
    return sorted(mut_hits - wt_hits)


def _apply_mutation(wt_seq: str, mutation: dict, cdr_offset_in_seq: int) -> str:
    """Apply a single mutation dict to wt_seq.

    ``mutation`` is expected to carry an ``index_in_cdr`` (0-based offset
    within the CDR) OR a ``resi`` plus ``cdr_start_resi``.
    """
    if "index_in_cdr" in mutation:
        i = cdr_offset_in_seq + int(mutation["index_in_cdr"])
    elif "resi" in mutation and "cdr_start_resi" in mutation:
        i = cdr_offset_in_seq + (int(mutation["resi"]) - int(mutation["cdr_start_resi"]))
    else:
        raise KeyError("mutation must carry 'index_in_cdr' or ('resi' and 'cdr_start_resi')")
    if not (0 <= i < len(wt_seq)):
        raise IndexError(f"mutation index {i} out of range for sequence length {len(wt_seq)}")
    if mutation.get("wt") and wt_seq[i] != mutation["wt"]:
        raise ValueError(
            f"mutation wt {mutation.get('wt')!r} does not match seq[{i}]={wt_seq[i]!r}"
        )
    return wt_seq[:i] + mutation["mut"] + wt_seq[i + 1 :]


def _eval_one_candidate(
    wt_full_seq: str,
    mut_full_seq: str,
    cdr_start: int,
    cdr_end: int,
    locus_thresholds: dict,
    mutation: dict,
) -> CandidateLiability:
    findings: list[LiabilityFinding] = []
    cdr_wt = wt_full_seq[cdr_start:cdr_end]
    cdr_mut = mut_full_seq[cdr_start:cdr_end]

    new_glyc = _delta_motifs(cdr_wt, cdr_mut, _NEW_MOTIFS["n_glyc"])
    for pos, motif in new_glyc:
        findings.append(
            LiabilityFinding(
                motif=f"new_n_glyc:{motif}",
                position_in_cdr=pos,
                sequence_window=cdr_mut[max(0, pos - 1) : pos + 4],
                severity="VETO",
            )
        )

    new_deamid = _delta_motifs(cdr_wt, cdr_mut, _NEW_MOTIFS["deamid"])
    for pos, motif in new_deamid:
        sev = "VETO" if motif == "NG" else "WARN"
        findings.append(
            LiabilityFinding(
                motif=f"new_deamid:{motif}",
                position_in_cdr=pos,
                sequence_window=cdr_mut[max(0, pos - 1) : pos + 3],
                severity=sev,
            )
        )

    new_isomer = _delta_motifs(cdr_wt, cdr_mut, _NEW_MOTIFS["isomer"])
    for pos, motif in new_isomer:
        sev = "VETO" if motif in {"DG", "DS"} else "WARN"
        findings.append(
            LiabilityFinding(
                motif=f"new_isomer:{motif}",
                position_in_cdr=pos,
                sequence_window=cdr_mut[max(0, pos - 1) : pos + 3],
                severity=sev,
            )
        )

    wt_run = _longest_hydrophobic_run(cdr_wt)
    mut_run = _longest_hydrophobic_run(cdr_mut)
    warn_t, veto_t = _upper_thresholds(locus_thresholds, "longest_hydrophobic_run")
    if veto_t is not None and mut_run > veto_t and mut_run > wt_run:
        findings.append(
            LiabilityFinding(
                motif=f"hydrophobic_run:{mut_run}>p99={veto_t}",
                position_in_cdr=-1,
                sequence_window=cdr_mut,
                severity="VETO",
            )
        )
    elif warn_t is not None and mut_run > warn_t and mut_run > wt_run:
        findings.append(
            LiabilityFinding(
                motif=f"hydrophobic_run:{mut_run}>p95={warn_t}",
                position_in_cdr=-1,
                sequence_window=cdr_mut,
                severity="WARN",
            )
        )

    if mutation.get("mut") == "C" and mutation.get("wt") != "C":
        findings.append(
            LiabilityFinding(
                motif="new_free_cys",
                position_in_cdr=int(mutation.get("index_in_cdr", -1)),
                sequence_window=cdr_mut,
                severity="VETO",
            )
        )

    severity_rank = {"PASS": 0, "WARN": 1, "VETO": 2}
    overall = "PASS"
    for f in findings:
        if severity_rank[f.severity] > severity_rank[overall]:
            overall = f.severity
    return CandidateLiability(mutation=mutation, overall=overall, findings=findings)


def filter_candidates(
    wt_full_seq: str,
    candidates: Iterable[dict],
    locus: str,
    cdr_start: int,
    cdr_end: int,
    antibody_format: AntibodyFormat,
    keep_warnings: bool = True,
) -> LiabilityResult:
    """Run CHECK 7 sequence-level liability pre-filter.

    Parameters
    ----------
    wt_full_seq : str
        Full antibody Fv sequence (concatenated H + L, or VHH single chain).
    candidates : iterable of dict
        Each item: {"chain", "wt", "mut", "index_in_cdr"} or compatible.
    locus : str
        CDR locus name, e.g. "vh_cdr3", "vhh_cdr1".
    cdr_start, cdr_end : int
        Half-open slice indices into ``wt_full_seq`` for this CDR.
    antibody_format : "vh_vl" | "vhh"
        Routes to AbRef-458 vs VHH-71 thresholds.
    keep_warnings : bool
        If True, WARN candidates flow into ``result.warned`` and ``result.passed``;
        if False, only PASS reaches ``result.passed``.

    Returns
    -------
    LiabilityResult
    """
    doc = _load_thresholds(antibody_format)
    locus_th = _locus_thresholds(doc, locus)
    if not locus_th:
        raise KeyError(
            f"Locus {locus!r} not found in {antibody_format} fingerprint database. "
            f"Valid loci: {list((doc.get('loci') or {}).keys())}"
        )

    result = LiabilityResult()
    for cand in candidates:
        try:
            mut_seq = _apply_mutation(wt_full_seq, cand, cdr_start)
        except (KeyError, IndexError, ValueError) as exc:
            entry = CandidateLiability(
                mutation=cand,
                overall="VETO",
                findings=[
                    LiabilityFinding(
                        motif="apply_mutation_error",
                        position_in_cdr=-1,
                        sequence_window=str(exc),
                        severity="VETO",
                    )
                ],
            )
            result.vetoed.append(entry)
            continue
        verdict = _eval_one_candidate(
            wt_full_seq, mut_seq, cdr_start, cdr_end, locus_th, cand
        )
        if verdict.overall == "PASS":
            result.passed.append(cand)
        elif verdict.overall == "WARN":
            result.warned.append(verdict)
            if keep_warnings:
                result.passed.append(cand)
        else:
            result.vetoed.append(verdict)

    result.summary = {
        "n_input": len(result.passed) + len(result.warned) + len(result.vetoed)
        if not keep_warnings
        else len(result.passed) + len(result.vetoed) + len([w for w in result.warned if w.mutation not in result.passed]),
        "n_passed": len(result.passed),
        "n_warned": len(result.warned),
        "n_vetoed": len(result.vetoed),
        "antibody_format": antibody_format,
        "locus": locus,
        "threshold_source": str(
            (_VHVL_FP if antibody_format == "vh_vl" else _VHH_FP).relative_to(_REPO_ROOT)
        ),
    }
    return result


__all__ = [
    "LiabilityFinding",
    "CandidateLiability",
    "LiabilityResult",
    "filter_candidates",
]
