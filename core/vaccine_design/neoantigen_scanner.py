"""
core/vaccine_design/neoantigen_scanner.py
─────────────────────────────────────────
MHC-I epitope prediction using MHCflurry 2.0 (local, CPU-only).

Capabilities:
  - Sliding-window peptide generation from protein sequence (8-11 mer)
  - MHC-I binding affinity + antigen processing + presentation score
  - Multi-allele panel scanning
  - Neoantigen ranking (mutant vs wild-type differential binding)
  - No external API dependency — runs 100% offline

Usage:
    scanner = NeoantigenScanner(alleles=["HLA-A*02:01", "HLA-A*24:02"])
    hits = scanner.scan_protein("MFVFLVLLPLVSSQCVNL...")
    neo  = scanner.compare_neoantigen(wt_seq="WILD", mut_seq="MUTD")
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

import pandas as pd

__version__ = "1.0.0"

logger = logging.getLogger(__name__)

DEFAULT_ALLELES = [
    "HLA-A*02:01", "HLA-A*01:01", "HLA-A*03:01",
    "HLA-A*24:02", "HLA-A*11:01",
    "HLA-B*07:02", "HLA-B*08:01",
]

PEPTIDE_LENGTHS = [8, 9, 10, 11]


def _get_predictor():
    """Lazy-load MHCflurry predictor (heavy on first call)."""
    from mhcflurry import Class1PresentationPredictor
    return Class1PresentationPredictor.load()


@dataclass
class EpitopeHit:
    peptide: str
    allele: str
    start: int
    affinity_nM: float
    processing_score: float
    presentation_score: float
    presentation_percentile: float
    rank_label: str  # SB / WB / NB


@dataclass
class NeoantigenResult:
    wt_peptide: str
    mut_peptide: str
    allele: str
    wt_affinity: float
    mut_affinity: float
    dai: float  # differential agretopicity index
    mut_presentation: float
    verdict: str


class NeoantigenScanner:
    """MHC-I epitope scanner — local, CPU-only, no API."""

    def __init__(
        self,
        alleles: Optional[List[str]] = None,
        lengths: Optional[List[int]] = None,
        sb_threshold: float = 0.5,   # presentation_percentile < 0.5% = SB
        wb_threshold: float = 2.0,
    ):
        self.alleles = alleles or DEFAULT_ALLELES
        self.lengths = lengths or PEPTIDE_LENGTHS
        self.sb_threshold = sb_threshold
        self.wb_threshold = wb_threshold
        self._predictor = None

    @property
    def predictor(self):
        if self._predictor is None:
            logger.info("Loading MHCflurry models (first call may take ~10s)...")
            self._predictor = _get_predictor()
        return self._predictor

    # ── sliding-window scan ──────────────────────────────────────────────

    def scan_protein(
        self,
        protein_seq: str,
        top_n: int = 50,
        only_sb: bool = False,
    ) -> pd.DataFrame:
        """Scan a full protein for MHC-I epitopes across all alleles/lengths.

        Returns DataFrame sorted by presentation_score descending.
        """
        protein_seq = protein_seq.upper().replace(" ", "").replace("\n", "")
        peptides, starts, lens = [], [], []
        for plen in self.lengths:
            for i in range(len(protein_seq) - plen + 1):
                pep = protein_seq[i:i + plen]
                if "X" in pep or "*" in pep:
                    continue
                peptides.append(pep)
                starts.append(i + 1)
                lens.append(plen)

        if not peptides:
            return pd.DataFrame()

        results = []
        for allele in self.alleles:
            df = self.predictor.predict(
                peptides=peptides,
                alleles=[allele],
                verbose=0,
            )
            df["start"] = starts
            df["allele"] = allele
            results.append(df)

        combined = pd.concat(results, ignore_index=True)
        combined["rank_label"] = combined["presentation_percentile"].apply(
            lambda x: "SB" if x < self.sb_threshold
            else ("WB" if x < self.wb_threshold else "NB")
        )

        if only_sb:
            combined = combined[combined["rank_label"] == "SB"]

        combined = combined.sort_values("presentation_score", ascending=False)
        if top_n:
            combined = combined.head(top_n)

        return combined.reset_index(drop=True)

    # ── single peptide prediction ────────────────────────────────────────

    def predict_peptides(
        self,
        peptides: List[str],
        allele: str = "HLA-A*02:01",
    ) -> pd.DataFrame:
        """Predict binding for a list of peptides against one allele."""
        df = self.predictor.predict(
            peptides=peptides,
            alleles=[allele],
            verbose=0,
        )
        df["rank_label"] = df["presentation_percentile"].apply(
            lambda x: "SB" if x < self.sb_threshold
            else ("WB" if x < self.wb_threshold else "NB")
        )
        return df

    # ── neoantigen differential analysis ─────────────────────────────────

    def compare_neoantigen(
        self,
        wt_seq: str,
        mut_seq: str,
        allele: str = "HLA-A*02:01",
    ) -> NeoantigenResult:
        """Compare mutant vs wild-type peptide for neoantigen potential.

        DAI (Differential Agretopicity Index) = log2(wt_affinity / mut_affinity).
        DAI > 0 means mutant binds better; DAI > 1 is promising.
        """
        import math

        wt_df = self.predictor.predict(
            peptides=[wt_seq], alleles=[allele], verbose=0,
        ).reset_index(drop=True)
        mut_df = self.predictor.predict(
            peptides=[mut_seq], alleles=[allele], verbose=0,
        ).reset_index(drop=True)

        wt_aff = float(wt_df["affinity"].iloc[0])
        mut_aff = float(mut_df["affinity"].iloc[0])
        dai = math.log2(max(wt_aff, 0.1) / max(mut_aff, 0.1))
        mut_pres = float(mut_df["presentation_score"].iloc[0])

        if dai > 1 and mut_aff < 500:
            verdict = "STRONG_NEOANTIGEN"
        elif dai > 0 and mut_aff < 500:
            verdict = "MODERATE_NEOANTIGEN"
        elif mut_aff < 500:
            verdict = "WEAK_NEOANTIGEN"
        else:
            verdict = "NON_BINDER"

        return NeoantigenResult(
            wt_peptide=wt_seq,
            mut_peptide=mut_seq,
            allele=allele,
            wt_affinity=wt_aff,
            mut_affinity=mut_aff,
            dai=round(dai, 3),
            mut_presentation=round(mut_pres, 4),
            verdict=verdict,
        )

    # ── batch protein scan for neoantigens ───────────────────────────────

    def scan_mutations(
        self,
        wt_protein: str,
        mut_protein: str,
        allele: str = "HLA-A*02:01",
    ) -> List[NeoantigenResult]:
        """Find neoantigen-generating mutations by comparing WT vs mutant protein.

        Identifies positions where sequences differ, extracts surrounding
        peptide windows, and evaluates differential binding.
        """
        assert len(wt_protein) == len(mut_protein), "Sequences must be same length"

        mut_positions = [
            i for i in range(len(wt_protein))
            if wt_protein[i] != mut_protein[i]
        ]

        results = []
        for pos in mut_positions:
            for plen in self.lengths:
                start = max(0, pos - plen + 1)
                end = min(len(wt_protein), pos + plen)
                for s in range(start, min(pos + 1, end - plen + 1)):
                    wt_pep = wt_protein[s:s + plen]
                    mut_pep = mut_protein[s:s + plen]
                    if wt_pep == mut_pep or "X" in mut_pep or "*" in mut_pep:
                        continue
                    result = self.compare_neoantigen(wt_pep, mut_pep, allele)
                    if result.verdict != "NON_BINDER":
                        results.append(result)

        seen = set()
        unique = []
        for r in results:
            key = (r.mut_peptide, r.allele)
            if key not in seen:
                seen.add(key)
                unique.append(r)

        return sorted(unique, key=lambda r: r.dai, reverse=True)
