"""Basic sequence-level developability screen for humanization reports.

This is intentionally smaller than the standalone 25-parameter IgG CMC workflow.
It supports donor-vs-humanized comparisons for essential sequence liabilities:
pI, hydrophobicity, instability, charge proxy, PTM motifs, oxidation-sensitive
residues, cysteine count, and simple sequence patches.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


def _motif_positions(seq: str, pattern: str) -> List[str]:
    out: List[str] = []
    for match in re.finditer(pattern, seq):
        out.append(f"{match.group(0)}@{match.start() + 1}")
    return out


def _net_charge_proxy(seq: str) -> int:
    seq = seq.upper()
    return sum(seq.count(aa) for aa in "KRH") - sum(seq.count(aa) for aa in "DE")


def basic_developability_screen(vh: str, vl: str) -> Dict[str, Any]:
    """Return a lightweight variable-region developability screen."""
    from Bio.SeqUtils.ProtParam import ProteinAnalysis  # type: ignore

    vh = (vh or "").strip().upper()
    vl = (vl or "").strip().upper()
    seq = vh + vl
    if not seq:
        return {"status": "ERROR", "error": "missing VH/VL sequence"}

    clean = seq.replace("X", "")
    pa = ProteinAnalysis(clean)

    glyco = _motif_positions(seq, r"N[^P][ST]")
    deamidation = _motif_positions(seq, r"N[GSTH]")
    isomerization = _motif_positions(seq, r"D[GST]")
    oxidation = _motif_positions(seq, r"[MW]")
    cysteine_count = seq.count("C")
    hydrophobic_stretch = _motif_positions(seq, r"[AILMFWV]{6,}")

    flags: List[str] = []
    p_i = round(float(pa.isoelectric_point()), 2)
    gravy = round(float(pa.gravy()), 3)
    instability = round(float(pa.instability_index()), 2)
    if not (5.5 <= p_i <= 9.5):
        flags.append(f"pI_review:{p_i}")
    if gravy > 0.2:
        flags.append(f"hydrophobicity_review:{gravy}")
    if instability > 45.0:
        flags.append(f"instability_review:{instability}")
    if glyco:
        flags.append(f"n_glycosylation_motif:{len(glyco)}")
    if deamidation:
        flags.append(f"deamidation_motif:{len(deamidation)}")
    if isomerization:
        flags.append(f"isomerization_motif:{len(isomerization)}")
    if cysteine_count % 2:
        flags.append(f"odd_cys_count:{cysteine_count}")
    if hydrophobic_stretch:
        flags.append(f"hydrophobic_stretch:{len(hydrophobic_stretch)}")

    status = "PASS" if not flags else "REVIEW"
    return {
        "status": status,
        "length": len(seq),
        "pI": p_i,
        "net_charge_proxy": _net_charge_proxy(seq),
        "gravy": gravy,
        "instability_index": instability,
        "aromaticity": round(float(pa.aromaticity()), 3),
        "n_glycosylation_motifs": glyco,
        "deamidation_motifs": deamidation,
        "isomerization_motifs": isomerization,
        "oxidation_sensitive_motifs": oxidation,
        "cysteine_count": cysteine_count,
        "free_cys_review": bool(cysteine_count % 2),
        "hydrophobic_stretches": hydrophobic_stretch,
        "flags": flags,
    }


def compare_basic_developability(
    donor_vh: str,
    donor_vl: str,
    humanized_vh: str,
    humanized_vl: str,
) -> Dict[str, Any]:
    donor = basic_developability_screen(donor_vh, donor_vl)
    humanized = basic_developability_screen(humanized_vh, humanized_vl)

    def _delta(key: str, digits: int = 3) -> float | None:
        a = donor.get(key)
        b = humanized.get(key)
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            return None
        return round(float(b) - float(a), digits)

    return {
        "screen_name": "Basic Developability Screen",
        "scope": "sequence-level variable-region screen; full IgG CMC remains a separate assessment",
        "donor": donor,
        "humanized": humanized,
        "delta": {
            "pI": _delta("pI", 2),
            "gravy": _delta("gravy", 3),
            "instability_index": _delta("instability_index", 2),
            "net_charge_proxy": _delta("net_charge_proxy", 0),
        },
    }
