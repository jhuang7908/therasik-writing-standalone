"""
Glycan-Dependent Epitope Risk Checker — V1.7 Additive Layer
=============================================================
Detects signals suggesting a VH→VHH conversion candidate may lose antigen
binding due to glycan-contact disruption caused by VL-decoupling.

Two detection pathways:
  A. Knowledge-Base match  — drug name / sequence identity in GLYCAN_CONTACT_AB_KB
  B. CDR-H3 motif scan     — NxS/T deamidation hotspots in the CDR3 tip region
                              (Kabat 98–106), interpreted as putative glycan-contact residues

V1.7 additive: does NOT modify V1.5 decision tree.  Penalty factor is
multiplied into success_probability AFTER V1.5/V1.6 calculations.

Scientific basis (verified):
  - Liu et al. 2021, Nat. Commun. 12:3569
    "Structural basis of anti-PD-1 antibody SHR-1210 binding to PD-1"
    CDR-H3 NSN residues (Kabat ~100–102) form direct H-bonds with
    GlcNAc at PD-1 N58 glycan.
  - Li et al. 2021, Cell Res. 31:749–753
    Confirms N-glycan at PD-1 N58 is required for Camrelizumab binding;
    PNGaseF deglycosylation abolishes Camrelizumab but not Nivolumab binding.

Module version: v1.7_glycan_checker_2026-04-30
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Frozen knowledge base (verified, version-locked 2026-04-30)
# ─────────────────────────────────────────────────────────────────────────────
GLYCAN_CHECKER_VERSION = "v1.7.1_glycan_checker_2026-04-30"

# Each entry: drug_name (canonical) → mechanism, confidence, penalty, sources
GLYCAN_CONTACT_AB_KB: Dict[str, Dict] = {
    "camrelizumab": {
        "alias": ["SHR-1210", "airuika", "AiRuiKa"],
        "cdr3_signature": "NSNGMDV", # Used for sequence-based fallback matching
        "mechanism": (
            "CDR-H3 NSN motif (Kabat ~100-102) forms direct H-bonds with "
            "GlcNAc at PD-1 N58 N-linked glycan. VL decoupling in VHH "
            "causes CDR-H3 tip reorientation, disrupting glycan contact."
        ),
        "target_glycan": "PD-1 N58",
        "confidence": "verified",
        "penalty_factor": 0.45, # Direct HIGH RISK penalty for known contact
        "severity": "HIGH",
        "sources": [
            "Liu et al. 2021 Nat. Commun. 12:3569",
            "Li et al. 2021 Cell Res. 31:749",
        ],
        "rescue_note": (
            "Experimental: test binding on deglycosylated PD-1 (PNGase F) vs. "
            "native PD-1. If VHH retains binding on deglycosylated PD-1, "
            "VHH has adapted to non-glycan contact mode. "
            "Consider N101Q substitution to protect against deamidation while "
            "preserving H-bond geometry (Gln side chain mimics Asn)."
        ),
    },
}

# NxS/T motif regex — putative N-linked glycan contact (deamidation + H-bond donor)
_GLYCAN_MOTIF_RE = re.compile(r"N[STAGCVILMPFYW][ST]")
# Broader H-bond motif in CDR3 tip
_NGX_MOTIF_RE = re.compile(r"N[GS]")


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class GlycanDependencyResult:
    """
    Output of glycan_dependency_checker.score_glycan_dependency_risk().

    penalty_factor: multiply into success_probability (1.0 = no penalty).
    risk_level:     "NONE" / "LOW" / "MODERATE" / "HIGH"
    """
    penalty_factor: float = 1.0
    risk_level: str = "NONE"
    known_glycan_contact: bool = False
    kb_entry: Optional[Dict] = None
    glycan_motifs_in_cdr3: List[str] = field(default_factory=list)
    cdr3_tip_nxst_count: int = 0
    vl_decoupling_risk: str = "unknown"
    risk_attribution_rows: List[Dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    checker_version: str = GLYCAN_CHECKER_VERSION

    def to_dict(self) -> Dict:
        return {
            "penalty_factor": self.penalty_factor,
            "risk_level": self.risk_level,
            "known_glycan_contact": self.known_glycan_contact,
            "glycan_motifs_in_cdr3": self.glycan_motifs_in_cdr3,
            "cdr3_tip_nxst_count": self.cdr3_tip_nxst_count,
            "vl_decoupling_risk": self.vl_decoupling_risk,
            "risk_attribution_rows": self.risk_attribution_rows,
            "notes": self.notes,
            "checker_version": self.checker_version,
            "kb_source": (self.kb_entry or {}).get("sources", []),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────
def _extract_cdr3_kabat(seq: str) -> Optional[str]:
    """
    Use ANARCI to extract CDR-H3 (Kabat positions 95–102 + insertions).
    Returns CDR3 string or None on failure.
    """
    try:
        from anarcii import Anarcii
        a = Anarcii(seq_type="antibody", mode="accuracy", verbose=False)
        a.number([seq])
        entry = a.to_scheme("kabat").get("Sequence 1", {})
        if entry.get("error") or entry.get("chain_type") != "H":
            return None
        # CDR-H3: Kabat 95–102 (+ insertion codes up to 102Z)
        cdr3_residues = []
        for (pos, icode), aa in entry.get("numbering", []):
            if 95 <= pos <= 102 and aa != "-":
                cdr3_residues.append(aa)
        return "".join(cdr3_residues) if cdr3_residues else None
    except Exception:
        return None


def _extract_cdr3_tip(cdr3: str) -> str:
    """
    Return the 'tip' of CDR3 — middle third (positions 4 onward for length ≥ 8,
    or entire string for shorter CDRs).  Glycan contacts typically occur at
    the loop apex, away from framework anchor residues.
    """
    if not cdr3 or len(cdr3) < 6:
        return cdr3 or ""
    # Trim first 3 and last 2 anchor-adjacent residues
    tip = cdr3[3:-2]
    return tip if tip else cdr3


def _kb_lookup(drug_name: Optional[str], cdr3: Optional[str]) -> Optional[Dict]:
    """Case-insensitive lookup in GLYCAN_CONTACT_AB_KB by name or CDR3 signature."""
    if drug_name:
        key = drug_name.strip().lower()
        if key in GLYCAN_CONTACT_AB_KB:
            return GLYCAN_CONTACT_AB_KB[key]
        # Try aliases
        for entry in GLYCAN_CONTACT_AB_KB.values():
            aliases = [a.lower() for a in entry.get("alias", [])]
            if key in aliases:
                return entry
    
    # Fallback: Sequence signature match
    if cdr3:
        for entry in GLYCAN_CONTACT_AB_KB.values():
            sig = entry.get("cdr3_signature")
            if sig and sig in cdr3:
                return entry

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────────────────────────────────────
def score_glycan_dependency_risk(
    converted_seq: str,
    drug_name: Optional[str] = None,
    cdr3_explicit: Optional[str] = None,
) -> GlycanDependencyResult:
    """
    Assess glycan-dependent epitope contact risk for a VH→VHH candidate.

    Parameters
    ----------
    converted_seq : str
        Full converted VHH sequence (used for ANARCI CDR3 extraction).
    drug_name : str, optional
        Original drug / project name for knowledge-base lookup
        (e.g. "Camrelizumab", "SHR-1210").
    cdr3_explicit : str, optional
        If CDR-H3 sequence is already known (skips ANARCI).

    Returns
    -------
    GlycanDependencyResult
        penalty_factor  ∈ (0, 1] — multiply into success_probability.
        risk_level      "NONE" / "LOW" / "MODERATE" / "HIGH"
    """
    result = GlycanDependencyResult()

    # ── Step 1: Extract CDR3 ─────────────────────────────────────────────────
    cdr3 = cdr3_explicit
    if not cdr3 and converted_seq:
        cdr3 = _extract_cdr3_kabat(converted_seq)

    # ── Step 2: Knowledge-base lookup ────────────────────────────────────────
    kb = _kb_lookup(drug_name, cdr3)
    if kb:
        result.known_glycan_contact = True
        result.kb_entry = kb
        kb_penalty = float(kb.get("penalty_factor", 0.45))
        result.penalty_factor *= kb_penalty
        result.notes.append(
            f"[KB-match] {drug_name or 'Sequence Match'}: {kb['mechanism']} "
            f"(confidence={kb['confidence']}, source={kb['sources'][0]})"
        )
        if kb.get("rescue_note"):
            result.notes.append(f"[Rescue] {kb['rescue_note']}")
        result.risk_attribution_rows.append({
            "risk_dimension": "Glycan-Dependent Epitope Contact",
            "current_value": f"Known glycan-contact antibody ({kb.get('target_glycan','')})",
            "safety_threshold": "Non-glycan-dependent binding mechanism",
            "attribution_source": kb["sources"][0],
            "severity": kb.get("severity", "HIGH"),
        })

    # ── Step 3: CDR-H3 motif scan ────────────────────────────────────────────
    if cdr3:
        tip = _extract_cdr3_tip(cdr3)
        # Scan tip for NxS/T glycan-contact motifs
        nxst_matches = _GLYCAN_MOTIF_RE.findall(tip)
        ngx_matches = _NGX_MOTIF_RE.findall(tip)
        all_motifs = list(set(nxst_matches + ngx_matches))
        result.glycan_motifs_in_cdr3 = all_motifs
        result.cdr3_tip_nxst_count = len(nxst_matches)

        if nxst_matches and not result.known_glycan_contact:
            # Unknown antibody but CDR3 tip has NxS/T — potential glycan contact
            # Downgraded penalty for unknown antibodies (0.90 instead of 0.75)
            motif_penalty = 0.90
            result.penalty_factor *= motif_penalty
            result.notes.append(
                f"CDR-H3 tip contains NxS/T motif(s) {nxst_matches} "
                f"(Kabat tip region) — potential N-glycosylation/deamidation site; "
                f"may act as putative glycan-contact residues."
            )
            result.risk_attribution_rows.append({
                "risk_dimension": "CDR-H3 Glycan-Contact Motif",
                "current_value": f"NxS/T motifs in CDR3 tip: {nxst_matches}",
                "safety_threshold": "No NxS/T in CDR3 tip (or glycan-independent mechanism confirmed)",
                "attribution_source": "CDR-H3 sequence motif scan (V1.7.1)",
                "severity": "INFO", # Downgraded from WARN
            })
        elif nxst_matches and result.known_glycan_contact:
            # KB match already applied full penalty
            result.notes.append(
                f"CDR-H3 tip NxS/T motifs {nxst_matches} confirmed consistent "
                f"with KB glycan-contact mechanism."
            )

        # VL-decoupling structural risk
        cdr3_len = len(cdr3)
        if cdr3_len >= 10 and (nxst_matches or ngx_matches):
            result.vl_decoupling_risk = "HIGH"
            result.notes.append(
                f"CDR-H3 length {cdr3_len} aa ≥ 10 + glycan-contact motif: "
                f"VL-decoupling (VHH conversion) likely causes 15–30° tip "
                f"reorientation → loss of glycan H-bond geometry."
            )
        elif cdr3_len >= 10:
            result.vl_decoupling_risk = "MODERATE"
        else:
            result.vl_decoupling_risk = "LOW"

    # ── Step 3: Determine risk level ─────────────────────────────────────────
    pf = result.penalty_factor
    if pf >= 0.95:
        result.risk_level = "NONE"
    elif pf >= 0.75:
        result.risk_level = "LOW"
    elif pf >= 0.50:
        result.risk_level = "MODERATE"
    else:
        result.risk_level = "HIGH"

    return result
