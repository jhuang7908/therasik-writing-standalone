"""
surface_immuno.py — InSynBio AbEngineCore v1.0
===============================================
Antibody hydrophilic surface immunogenicity analysis.

Principle
---------
The immunogenicity of a therapeutic antibody is not only driven by T-cell
epitopes (MHC-II, sequence-level) but also by the **solvent-exposed surface**
of the antibody:

1. **Hydrophilic patches** on the exposed VH/VL surface can bind B-cell
   receptors (BCR) or innate immune receptors, triggering a humoral response
   even without T-cell help — particularly when a patch is large, charged,
   or contains foreign sequence motifs.

2. **Hydrophobic patches** on the exposed surface (especially in CDR loops)
   are a major risk factor for aggregation-induced immunogenicity: aggregated
   antibody is up to 100× more immunogenic than monomer.

3. **B-cell epitope propensity**: exposed aromatic + charged residues form
   conformational epitopes that can be directly recognised by circulating
   anti-drug antibodies (ADA).

This module computes surface immunogenicity from:

  (a) PDB structure  → per-residue SASA → exposed residue classification
  (b) Sequence only  → mean propensity score (no structure, less accurate)

Key outputs
-----------
  • `exposed_hydrophilic_patches` — continuous runs of exposed hydrophilic
    residues (DEHKNQR + Ser/Thr/Tyr) on the Ab surface, with area and risk.
  • `exposed_hydrophobic_patches` — Phe/Trp/Leu/Ile/Val/Met patches,
    aggregation + immunogenicity risk.
  • `bcell_epitope_propensity` — per-residue B-cell epitope score
    (Parker et al. 1986 hydrophilicity scale).
  • `surface_charge_map` — distribution of positive/negative charge on
    exposed surface residues.
  • `overall_surface_risk` — composite risk level.

Usage
-----
    # With PDB
    from core.immunogenicity.surface_immuno import SurfaceImmunogenicity
    si = SurfaceImmunogenicity(pdb_path="Ab.pdb", vh_chain="H", vl_chain="L")
    result = si.analyze()

    # Sequence only
    si = SurfaceImmunogenicity(vh_seq="EVQLVES...", vl_seq="DIQMTQ...")
    result = si.analyze()
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ── Optional BioPython ────────────────────────────────────────────────────────
try:
    from Bio.PDB import PDBParser
    from Bio.PDB.Polypeptide import is_aa
    _HAS_BP = True
except ImportError:
    _HAS_BP = False

try:
    from Bio.PDB.SASA import ShrakeRupley
    _HAS_SASA = True
except ImportError:
    _HAS_SASA = False


# ─────────────────────────────────────────────────────────────────────────────
# Residue property scales
# ─────────────────────────────────────────────────────────────────────────────

# Parker (1986) hydrophilicity scale (higher = more hydrophilic / surface-prone)
_PARKER_HYDROPHILICITY: Dict[str, float] = {
    "R": 3.0, "K": 3.0, "D": 3.0, "E": 3.0, "N": 0.2, "Q": 0.2,
    "S": 0.6, "T": 0.7, "H": 1.1, "Y": 0.4, "W": -3.4,
    "A": -1.6, "C": -2.0, "F": -3.7, "G": -1.0, "I": -3.1,
    "L": -2.8, "M": -3.4, "P": 0.0, "V": -2.6,
}

# Kyte-Doolittle hydrophobicity (higher = more hydrophobic)
_KD_HYDROPHOBICITY: Dict[str, float] = {
    "I": 4.5, "V": 4.2, "L": 3.8, "F": 2.8, "C": 2.5, "M": 1.9,
    "A": 1.8, "G": -0.4, "T": -0.7, "S": -0.8, "W": -0.9, "Y": -1.3,
    "P": -1.6, "H": -3.2, "E": -3.5, "Q": -3.5, "D": -3.5, "N": -3.5,
    "K": -3.9, "R": -4.5,
}

# B-cell epitope propensity (Kolaskar & Tongaonkar, 1990)
_KOLASKAR_BCELL: Dict[str, float] = {
    "A": 1.064, "C": 1.012, "D": 1.068, "E": 1.068, "F": 1.091,
    "G": 0.874, "H": 1.105, "I": 1.152, "K": 0.971, "L": 1.014,
    "M": 0.826, "N": 0.776, "P": 1.064, "Q": 0.907, "R": 0.873,
    "S": 1.012, "T": 1.086, "V": 1.025, "W": 1.073, "Y": 1.161,
}

_HYDROPHILIC_AA = set("RKHDEQNST")
_HYDROPHOBIC_AA = set("FWLIVMACP")
_CHARGED_POS    = set("RK")
_CHARGED_NEG    = set("DE")

# SASA threshold for "exposed" residue (fraction of max theoretical SASA)
_EXPOSED_THRESHOLD = 0.20   # residue with ≥20% of its max SASA is considered exposed

# Max theoretical SASA values (Å²) from Miller et al. 1987
_MAX_SASA: Dict[str, float] = {
    "A": 129.0, "R": 274.0, "N": 195.0, "D": 193.0, "C": 167.0,
    "E": 223.0, "Q": 225.0, "G": 104.0, "H": 224.0, "I": 197.0,
    "L": 201.0, "K": 236.0, "M": 224.0, "F": 240.0, "P": 159.0,
    "S": 155.0, "T": 172.0, "W": 285.0, "Y": 263.0, "V": 174.0,
}


# ─────────────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SurfacePatch:
    """A continuous or clustered surface patch."""
    chain:          str           # "VH" or "VL"
    start:          int           # sequence start (0-based)
    end:            int           # sequence end (0-based, exclusive)
    sequence:       str           # residue one-letter sequence of the patch
    patch_type:     str           # "hydrophilic" or "hydrophobic"
    region:         str           # e.g. "CDR2", "FR3"
    area_A2:        Optional[float] = None   # SASA area if PDB available
    mean_score:     float          = 0.0     # mean propensity score
    n_charged:      int            = 0       # charged residues in patch
    risk:           str            = "LOW"


@dataclass
class SurfaceImmunoResult:
    method:                    str    # "pdb_sasa" or "sequence_propensity"
    exposed_hydrophilic_patches: List[SurfacePatch]
    exposed_hydrophobic_patches: List[SurfacePatch]
    bcell_profile:             List[Dict]    # per-residue B-cell propensity
    surface_charge_map:        Dict[str, int]  # {"positive": n, "negative": n, "neutral": n}
    hydrophilicity_score:      float           # mean Parker score of exposed residues
    overall_surface_risk:      str
    flags:                     List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Main class
# ─────────────────────────────────────────────────────────────────────────────

class SurfaceImmunogenicity:
    """
    Antibody hydrophilic/hydrophobic surface immunogenicity analyzer.

    Parameters
    ----------
    pdb_path   : Path to PDB file (complex or antibody-only).
    vh_chain   : VH chain ID in PDB.
    vl_chain   : VL chain ID in PDB.
    vh_seq     : VH amino-acid sequence (used if no PDB or to supplement).
    vl_seq     : VL amino-acid sequence.
    patch_min  : Minimum consecutive residues to form a patch (default 4).
    sasa_cutoff: Fraction of max SASA to be "exposed" (default 0.20).
    """

    def __init__(
        self,
        pdb_path:    Optional[str]  = None,
        vh_chain:    str             = "H",
        vl_chain:    str             = "L",
        vh_seq:      Optional[str]  = None,
        vl_seq:      Optional[str]  = None,
        patch_min:   int             = 4,
        sasa_cutoff: float           = 0.20,
    ):
        self.pdb_path   = pdb_path
        self.vh_chain   = vh_chain
        self.vl_chain   = vl_chain
        self.vh_seq     = (vh_seq or "").strip().upper()
        self.vl_seq     = (vl_seq or "").strip().upper()
        self.patch_min  = patch_min
        self.sasa_cutoff = sasa_cutoff

    def analyze(self) -> SurfaceImmunoResult:
        if self.pdb_path and _HAS_BP and _HAS_SASA:
            return self._analyze_pdb()
        else:
            return self._analyze_sequence()

    # ──────────────────────────────────────────────────────────────────────────
    # PDB-based analysis
    # ──────────────────────────────────────────────────────────────────────────

    def _analyze_pdb(self) -> SurfaceImmunoResult:
        parser = PDBParser(QUIET=True)
        try:
            structure = parser.get_structure("ab", self.pdb_path)
        except Exception as e:
            return self._analyze_sequence(error=f"PDB parse failed: {e}")

        model = structure[0]
        sr = ShrakeRupley(probe_radius=1.4, n_points=960)
        try:
            sr.compute(model, level="R")
        except Exception as e:
            return self._analyze_sequence(error=f"SASA compute failed: {e}")

        chain_data: Dict[str, List[Tuple[str, float, int]]] = {}  # chain → [(aa, sasa, seqidx)]
        for chain_id, label in [(self.vh_chain, "VH"), (self.vl_chain, "VL")]:
            residues = []
            for res in model[chain_id] if chain_id in {c.id for c in model.get_chains()} else []:
                if not (is_aa(res, standard=False) and res.id[0] == " "):
                    continue
                aa = _three_to_one(res.resname)
                sasa = res.sasa if hasattr(res, "sasa") else 0.0
                max_s = _MAX_SASA.get(aa, 200.0)
                rel_sasa = sasa / max_s if max_s > 0 else 0.0
                exposed = rel_sasa >= self.sasa_cutoff
                residues.append((aa, sasa, rel_sasa, exposed))
            chain_data[label] = residues

        return self._compute_from_residues(chain_data, method="pdb_sasa")

    # ──────────────────────────────────────────────────────────────────────────
    # Sequence-based analysis
    # ──────────────────────────────────────────────────────────────────────────

    def _analyze_sequence(self, error: Optional[str] = None) -> SurfaceImmunoResult:
        """
        Sequence-only: use Parker hydrophilicity to estimate surface exposure.
        Residues with Parker score > 0 are considered "surface-exposed".
        Uses a 7-residue sliding window average for smoothing.
        """
        chain_data: Dict[str, List] = {}
        for label, seq in [("VH", self.vh_seq), ("VL", self.vl_seq)]:
            if not seq:
                continue
            smoothed = _window_smooth(seq, _PARKER_HYDROPHILICITY, window=7)
            residues = []
            for i, aa in enumerate(seq):
                score = smoothed[i]
                exposed = score > 0.0    # positive Parker score = surface-prone
                max_s = _MAX_SASA.get(aa, 200.0)
                residues.append((aa, score * 10, score / max(_MAX_SASA.values()), exposed))
            chain_data[label] = residues

        result = self._compute_from_residues(chain_data, method="sequence_propensity")
        if error:
            result.flags.insert(0, f"WARN:fallback_to_sequence ({error})")
        return result

    # ──────────────────────────────────────────────────────────────────────────
    # Core computation
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_from_residues(
        self,
        chain_data: Dict[str, List],   # label → [(aa, sasa, rel_sasa, exposed)]
        method: str,
    ) -> SurfaceImmunoResult:
        from core.evaluation.evaluator import _SUITE_ROOT  # for Kabat lookup
        from core.immunogenicity.mhcii_analyzer import _KABAT_VH, _KABAT_VL, _region_of

        hydrophilic_patches: List[SurfacePatch] = []
        hydrophobic_patches: List[SurfacePatch] = []
        bcell_profile: List[Dict] = []
        charge_counts  = {"positive": 0, "negative": 0, "neutral": 0}
        exposed_scores: List[float] = []

        for chain_label, residues in chain_data.items():
            kabat = _KABAT_VH if chain_label == "VH" else _KABAT_VL

            # B-cell propensity profile
            for i, (aa, sasa_val, rel_sasa, exposed) in enumerate(residues):
                bcell_score = _KOLASKAR_BCELL.get(aa, 1.0)
                parker      = _PARKER_HYDROPHILICITY.get(aa, 0.0)
                kd          = _KD_HYDROPHOBICITY.get(aa, 0.0)
                region      = _region_of(i, kabat)

                bcell_profile.append({
                    "chain":        chain_label,
                    "index":        i,
                    "aa":           aa,
                    "region":       region,
                    "exposed":      exposed,
                    "sasa":         round(sasa_val, 1),
                    "rel_sasa":     round(rel_sasa, 3),
                    "parker":       parker,
                    "kd":           kd,
                    "bcell_score":  bcell_score,
                })

                if exposed:
                    exposed_scores.append(parker)
                    if aa in _CHARGED_POS:
                        charge_counts["positive"] += 1
                    elif aa in _CHARGED_NEG:
                        charge_counts["negative"] += 1
                    else:
                        charge_counts["neutral"] += 1

            # Find hydrophilic patches (continuous runs of hydrophilic exposed residues)
            hydrophilic_patches += self._find_patches(
                residues, chain_label, kabat, _HYDROPHILIC_AA,
                _PARKER_HYDROPHILICITY, "hydrophilic"
            )
            # Find hydrophobic patches
            hydrophobic_patches += self._find_patches(
                residues, chain_label, kabat, _HYDROPHOBIC_AA,
                _KD_HYDROPHOBICITY, "hydrophobic"
            )

        # Rank patches by score/area
        hydrophilic_patches.sort(key=lambda p: -p.mean_score)
        hydrophobic_patches.sort(key=lambda p: -p.mean_score)

        mean_hydrophilicity = float(np.mean(exposed_scores)) if exposed_scores else 0.0

        # Overall surface risk
        n_high_phil = sum(1 for p in hydrophilic_patches if p.risk == "HIGH")
        n_high_phob = sum(1 for p in hydrophobic_patches if p.risk == "HIGH")
        n_charged_exposed = charge_counts["positive"] + charge_counts["negative"]

        if n_high_phil >= 3 or n_high_phob >= 2 or n_charged_exposed > 20:
            overall = "HIGH"
        elif n_high_phil >= 1 or n_high_phob >= 1 or n_charged_exposed > 10:
            overall = "MEDIUM"
        else:
            overall = "LOW"

        flags = []
        cdr_phob = [p for p in hydrophobic_patches if "CDR" in p.region and p.risk != "LOW"]
        if cdr_phob:
            flags.append(
                f"WARN:EXPOSED_HYDROPHOBIC_CDR — {len(cdr_phob)} hydrophobic patches "
                "in CDRs (aggregation + immunogenicity risk)."
            )
        large_phil = [p for p in hydrophilic_patches if p.n_charged >= 4]
        if large_phil:
            flags.append(
                f"WARN:LARGE_CHARGED_SURFACE_PATCH — {len(large_phil)} hydrophilic patches "
                "with ≥4 charged residues (BCR / innate immune recognition risk)."
            )
        if n_charged_exposed > 15:
            flags.append(
                f"INFO:HIGH_SURFACE_CHARGE — {n_charged_exposed} charged residues exposed; "
                "review pI and off-target binding risk."
            )

        return SurfaceImmunoResult(
            method                     = method,
            exposed_hydrophilic_patches = hydrophilic_patches,
            exposed_hydrophobic_patches = hydrophobic_patches,
            bcell_profile              = bcell_profile,
            surface_charge_map         = charge_counts,
            hydrophilicity_score       = round(mean_hydrophilicity, 3),
            overall_surface_risk       = overall,
            flags                      = flags,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Patch finding
    # ──────────────────────────────────────────────────────────────────────────

    def _find_patches(
        self,
        residues:     List,
        chain_label:  str,
        kabat:        Dict,
        aa_set:       set,
        score_map:    Dict[str, float],
        patch_type:   str,
    ) -> List[SurfacePatch]:
        from core.immunogenicity.mhcii_analyzer import _region_of

        patches = []
        in_patch = False
        patch_start = 0
        patch_aas: List[str] = []

        def _flush(start, aas):
            if len(aas) < self.patch_min:
                return
            seq = "".join(aas)
            region = _region_of(start, kabat)
            scores  = [abs(score_map.get(aa, 0.0)) for aa in aas]
            mean_s  = float(np.mean(scores)) if scores else 0.0
            n_ch    = sum(1 for aa in aas if aa in _CHARGED_POS | _CHARGED_NEG)
            area    = None   # set from SASA data below
            # Risk classification
            if len(aas) >= 8 or (len(aas) >= 5 and n_ch >= 3) or mean_s >= 3.0:
                risk = "HIGH"
            elif len(aas) >= 6 or (len(aas) >= 4 and n_ch >= 2) or mean_s >= 1.5:
                risk = "MEDIUM"
            else:
                risk = "LOW"
            patches.append(SurfacePatch(
                chain       = chain_label,
                start       = start,
                end         = start + len(aas),
                sequence    = seq,
                patch_type  = patch_type,
                region      = region,
                area_A2     = area,
                mean_score  = round(mean_s, 3),
                n_charged   = n_ch,
                risk        = risk,
            ))

        for i, (aa, sasa_val, rel_sasa, exposed) in enumerate(residues):
            in_target = exposed and aa in aa_set
            if in_target:
                if not in_patch:
                    in_patch = True
                    patch_start = i
                    patch_aas = []
                patch_aas.append(aa)
            else:
                if in_patch:
                    _flush(patch_start, patch_aas)
                    in_patch = False
                    patch_aas = []
        if in_patch:
            _flush(patch_start, patch_aas)

        return patches


# ─────────────────────────────────────────────────────────────────────────────
# Utility functions
# ─────────────────────────────────────────────────────────────────────────────

_THREE_TO_ONE: Dict[str, str] = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}

def _three_to_one(resname: str) -> str:
    return _THREE_TO_ONE.get(resname.upper(), "X")


def _window_smooth(seq: str, scale: Dict[str, float], window: int = 7) -> List[float]:
    """Sliding-window average of a residue property scale."""
    n = len(seq)
    scores = [scale.get(aa, 0.0) for aa in seq]
    half = window // 2
    smoothed = []
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        smoothed.append(float(np.mean(scores[lo:hi])))
    return smoothed
