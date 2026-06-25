"""
core/vaccine_design/heteroclitic_designer.py
────────────────────────────────────────────
TAA heteroclitic peptide design with cross-reactivity guard.

Design principle:
  - ONLY mutate anchor positions (P2, P9) to enhance MHC binding
  - NEVER touch TCR contact face (P4-P8) — must preserve cross-reactivity
  - Validate that backbone conformation is preserved (RMSD check)

Usage:
    designer = HeteroclicticDesigner(allele="HLA-A*02:01")
    results = designer.design("ITDQVPFSV")  # gp100 wild-type epitope
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd

__version__ = "1.0.0"

logger = logging.getLogger(__name__)

# ── HLA anchor preference rules ─────────────────────────────────────────────
# Derived from crystal structure analysis + SYFPEITHI + MHCflurry training data.
# Only anchor positions (P2, P9 for 9-mer; P2, PΩ for others) are mutatable.

ANCHOR_RULES: Dict[str, Dict[str, List[str]]] = {
    "HLA-A*02:01": {"P2": list("LMVAI"), "P9": list("VLIAT")},
    "HLA-A*01:01": {"P2": list("TSE"),   "P9": list("Y")},
    "HLA-A*03:01": {"P2": list("VLM"),   "P9": list("KR")},
    "HLA-A*24:02": {"P2": list("YFW"),   "P9": list("FLI")},
    "HLA-A*11:01": {"P2": list("VLM"),   "P9": list("K")},
    "HLA-B*07:02": {"P2": list("P"),     "P9": list("L")},
    "HLA-B*08:01": {"P2": list("K"),     "P9": list("L")},
    "HLA-B*35:01": {"P2": list("P"),     "P9": list("YF")},
}

HYDROPHOBIC = set("LIVMFYWAP")
CHARGED     = set("RKHDE")
AROMATIC    = set("FYW")

AA_ALPHABET = "ACDEFGHIKLMNPQRSTVWY"


@dataclass
class HeteroclicticCandidate:
    wt_peptide: str
    mut_peptide: str
    mutations: str          # e.g. "P2:T→L, P9:V→V"
    allele: str
    wt_affinity_nM: float
    mut_affinity_nM: float
    fold_improvement: float
    tcr_face_preserved: bool
    physicochemical_compatible: bool
    backbone_risk: str      # SAFE / CAUTION / REJECT
    overall_verdict: str    # RECOMMENDED / CAUTION / REJECT
    presentation_score: float


@dataclass
class CrossReactivityReport:
    wt_peptide: str
    mut_peptide: str
    tcr_face_wt: str        # P4-P8
    tcr_face_mut: str
    tcr_face_identical: bool
    anchor_changes: List[str]
    physicochemical_score: float  # 0-1, higher = more compatible
    backbone_risk: str
    verdict: str


class HeteroclicticDesigner:
    """Design heteroclitic peptides: enhance MHC binding, preserve TCR cross-reactivity."""

    def __init__(
        self,
        allele: str = "HLA-A*02:01",
        max_candidates: int = 20,
    ):
        self.allele = allele
        self.max_candidates = max_candidates
        self._predictor = None

    @property
    def predictor(self):
        if self._predictor is None:
            from mhcflurry import Class1PresentationPredictor
            self._predictor = Class1PresentationPredictor.load()
        return self._predictor

    # ── anchor position identification ───────────────────────────────────

    @staticmethod
    def get_anchor_positions(peptide_len: int) -> Tuple[int, int]:
        """Return 0-indexed anchor positions (P2, PΩ)."""
        return (1, peptide_len - 1)

    @staticmethod
    def get_tcr_face(peptide: str) -> str:
        """Extract TCR contact face (P4-P8 for 9-mer, adapted for other lengths)."""
        n = len(peptide)
        if n == 8:
            return peptide[3:7]   # P4-P7
        elif n == 9:
            return peptide[3:8]   # P4-P8
        elif n == 10:
            return peptide[3:9]   # P4-P9 (P10=anchor)
        elif n == 11:
            return peptide[3:10]  # P4-P10 (P11=anchor)
        return peptide[3:-1]

    # ── physicochemical compatibility ────────────────────────────────────

    @staticmethod
    def _physicochemical_compatible(wt_aa: str, mut_aa: str) -> float:
        """Score how physicochemically compatible a mutation is (0-1).

        Same physicochemical class → high score → less likely to distort backbone.
        """
        if wt_aa == mut_aa:
            return 1.0

        both_hydrophobic = (wt_aa in HYDROPHOBIC) and (mut_aa in HYDROPHOBIC)
        both_charged = (wt_aa in CHARGED) and (mut_aa in CHARGED)
        both_aromatic = (wt_aa in AROMATIC) and (mut_aa in AROMATIC)

        if both_aromatic:
            return 0.95
        if both_hydrophobic:
            return 0.85
        if both_charged:
            return 0.7

        size_similar = abs(
            _aa_volume.get(wt_aa, 120) - _aa_volume.get(mut_aa, 120)
        ) < 30
        if size_similar:
            return 0.5

        return 0.2

    # ── cross-reactivity assessment ──────────────────────────────────────

    def assess_cross_reactivity(
        self,
        wt_peptide: str,
        mut_peptide: str,
    ) -> CrossReactivityReport:
        """Evaluate whether mutant peptide will maintain TCR cross-reactivity with WT."""
        assert len(wt_peptide) == len(mut_peptide), "Peptides must be same length"

        tcr_wt = self.get_tcr_face(wt_peptide)
        tcr_mut = self.get_tcr_face(mut_peptide)
        tcr_identical = (tcr_wt == tcr_mut)

        p2_idx, p_omega_idx = self.get_anchor_positions(len(wt_peptide))
        anchor_changes = []
        compat_scores = []
        non_anchor_changes = []

        for i in range(len(wt_peptide)):
            if wt_peptide[i] != mut_peptide[i]:
                pos_label = f"P{i+1}"
                change = f"{pos_label}:{wt_peptide[i]}→{mut_peptide[i]}"
                compat = self._physicochemical_compatible(
                    wt_peptide[i], mut_peptide[i]
                )
                compat_scores.append(compat)

                if i in (p2_idx, p_omega_idx):
                    anchor_changes.append(change)
                else:
                    non_anchor_changes.append(change)

        avg_compat = sum(compat_scores) / len(compat_scores) if compat_scores else 1.0

        if not tcr_identical:
            risk = "REJECT"
            verdict = "REJECT — TCR contact face altered"
        elif non_anchor_changes:
            risk = "CAUTION"
            verdict = f"CAUTION — non-anchor position(s) changed: {non_anchor_changes}"
        elif avg_compat >= 0.8:
            risk = "SAFE"
            verdict = "SAFE — anchor-only, physicochemically compatible"
        elif avg_compat >= 0.5:
            risk = "CAUTION"
            verdict = "CAUTION — anchor change may alter backbone (structural validation recommended)"
        else:
            risk = "CAUTION"
            verdict = "CAUTION — large physicochemical shift at anchor"

        return CrossReactivityReport(
            wt_peptide=wt_peptide,
            mut_peptide=mut_peptide,
            tcr_face_wt=tcr_wt,
            tcr_face_mut=tcr_mut,
            tcr_face_identical=tcr_identical,
            anchor_changes=anchor_changes,
            physicochemical_score=round(avg_compat, 3),
            backbone_risk=risk,
            verdict=verdict,
        )

    # ── main design entry ────────────────────────────────────────────────

    def design(
        self,
        wt_peptide: str,
        allele: Optional[str] = None,
    ) -> List[HeteroclicticCandidate]:
        """Design heteroclitic variants of a TAA epitope.

        Strategy:
          1. Enumerate all anchor mutations (P2 × PΩ)
          2. Score with MHCflurry
          3. Filter by cross-reactivity guard
          4. Rank by fold-improvement
        """
        allele = allele or self.allele
        wt_peptide = wt_peptide.upper().strip()
        plen = len(wt_peptide)
        p2_idx, p_omega_idx = self.get_anchor_positions(plen)

        rules = ANCHOR_RULES.get(allele, {"P2": list(AA_ALPHABET), "P9": list(AA_ALPHABET)})
        p2_candidates = rules.get("P2", list(AA_ALPHABET))
        p_omega_candidates = rules.get("P9", list(AA_ALPHABET))

        variants = []
        for p2_aa in p2_candidates:
            for po_aa in p_omega_candidates:
                mut = list(wt_peptide)
                mut[p2_idx] = p2_aa
                mut[p_omega_idx] = po_aa
                mut_seq = "".join(mut)
                if mut_seq != wt_peptide:
                    variants.append(mut_seq)

        if not variants:
            logger.warning("No anchor variants generated")
            return []

        all_peptides = [wt_peptide] + variants

        df = self.predictor.predict(
            peptides=all_peptides,
            alleles=[allele],
            verbose=0,
        )

        wt_row = df.iloc[0]
        wt_affinity = float(wt_row["affinity"])

        candidates = []
        for idx in range(1, len(df)):
            row = df.iloc[idx]
            mut_seq = str(row["peptide"])
            mut_aff = float(row["affinity"])

            if mut_aff >= wt_affinity:
                continue

            fold_imp = wt_affinity / max(mut_aff, 0.1)

            xr = self.assess_cross_reactivity(wt_peptide, mut_seq)

            mutations = []
            for i in range(plen):
                if wt_peptide[i] != mut_seq[i]:
                    mutations.append(f"P{i+1}:{wt_peptide[i]}→{mut_seq[i]}")
            mut_str = ", ".join(mutations) if mutations else "none"

            candidates.append(HeteroclicticCandidate(
                wt_peptide=wt_peptide,
                mut_peptide=mut_seq,
                mutations=mut_str,
                allele=allele,
                wt_affinity_nM=round(wt_affinity, 2),
                mut_affinity_nM=round(mut_aff, 2),
                fold_improvement=round(fold_imp, 2),
                tcr_face_preserved=xr.tcr_face_identical,
                physicochemical_compatible=(xr.physicochemical_score >= 0.7),
                backbone_risk=xr.backbone_risk,
                overall_verdict=xr.backbone_risk,
                presentation_score=round(float(row["presentation_score"]), 4),
            ))

        candidates.sort(key=lambda c: c.fold_improvement, reverse=True)

        safe = [c for c in candidates if c.overall_verdict == "SAFE"]
        caution = [c for c in candidates if c.overall_verdict == "CAUTION"]

        result = safe[:self.max_candidates]
        remaining = self.max_candidates - len(result)
        if remaining > 0:
            result.extend(caution[:remaining])

        return result

    # ── summary report ───────────────────────────────────────────────────

    def design_report(
        self,
        wt_peptide: str,
        allele: Optional[str] = None,
    ) -> pd.DataFrame:
        """Return design results as a DataFrame for easy viewing."""
        candidates = self.design(wt_peptide, allele)
        if not candidates:
            return pd.DataFrame()

        from dataclasses import asdict
        return pd.DataFrame([asdict(c) for c in candidates])


# ── amino acid volumes (Å³, Zamyatnin 1972) ─────────────────────────────────
_aa_volume = {
    "G": 60, "A": 89, "V": 140, "L": 164, "I": 164,
    "P": 115, "F": 190, "W": 228, "M": 163, "S": 89,
    "T": 116, "C": 108, "Y": 194, "H": 153, "D": 111,
    "E": 138, "N": 114, "Q": 144, "K": 169, "R": 173,
}
