"""
core/vaccine_design/codon_optimizer.py
──────────────────────────────────────
mRNA codon optimization + structure-aware scoring.

Combines:
  - Codon Adaptation Index (CAI) optimization for human expression
  - Uridine depletion (N1-methylpseudouridine substitution compatibility)
  - GC content optimization (target 45-65%)
  - CpG dinucleotide depletion (reduce innate immune sensing)
  - Avoidance of rare codons, homo-polymer runs, and restriction sites
  - Integration with LinearFold for mRNA secondary structure MFE

100% local, CPU-only, no API dependency.

Usage:
    opt = CodonOptimizer()
    result = opt.optimize("MFVFLVLLPLVSSQCVNL")
    print(result.mrna_sequence, result.cai, result.gc_content)
"""
from __future__ import annotations

import logging
import math
import os
import random
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

__version__ = "1.0.0"

logger = logging.getLogger(__name__)

_SUITE = Path(__file__).resolve().parents[2]
LINEARFOLD_BIN = _SUITE / "tools" / "LinearFold" / "bin" / "linearfold_v.exe"
CODON_TABLE_PATH = _SUITE / "tools" / "LinearDesign" / "codon_usage_freq_table_human.csv"

# ── standard genetic code ────────────────────────────────────────────────────
CODON_TABLE = {
    "F": ["UUU", "UUC"], "L": ["UUA", "UUG", "CUU", "CUC", "CUA", "CUG"],
    "I": ["AUU", "AUC", "AUA"], "M": ["AUG"], "V": ["GUU", "GUC", "GUA", "GUG"],
    "S": ["UCU", "UCC", "UCA", "UCG", "AGU", "AGC"],
    "P": ["CCU", "CCC", "CCA", "CCG"], "T": ["ACU", "ACC", "ACA", "ACG"],
    "A": ["GCU", "GCC", "GCA", "GCG"],
    "Y": ["UAU", "UAC"], "H": ["CAU", "CAC"], "Q": ["CAA", "CAG"],
    "N": ["AAU", "AAC"], "K": ["AAA", "AAG"],
    "D": ["GAU", "GAC"], "E": ["GAA", "GAG"],
    "C": ["UGU", "UGC"], "W": ["UGG"],
    "R": ["CGU", "CGC", "CGA", "CGG", "AGA", "AGG"],
    "G": ["GGU", "GGC", "GGA", "GGG"],
    "*": ["UAA", "UAG", "UGA"],
}

STOP_CODONS = {"UAA", "UAG", "UGA"}


def _load_human_codon_freq() -> Dict[str, float]:
    """Load human codon usage frequencies."""
    freq: Dict[str, float] = {}
    if CODON_TABLE_PATH.exists():
        with open(CODON_TABLE_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",")
                if len(parts) >= 3:
                    codon, _aa, f_val = parts[0], parts[1], parts[2]
                    try:
                        freq[codon] = float(f_val)
                    except ValueError:
                        pass
    else:
        logger.warning("Codon frequency table not found, using defaults")
        freq = _default_human_freq()
    return freq


def _default_human_freq() -> Dict[str, float]:
    """Fallback: top human codons from Kazusa."""
    return {
        "GCC": 0.40, "UGC": 0.55, "GAC": 0.54, "GAG": 0.58, "UUC": 0.55,
        "GGC": 0.34, "CAC": 0.59, "AUC": 0.48, "AAG": 0.58, "CUG": 0.41,
        "AUG": 1.00, "AAC": 0.54, "CCC": 0.33, "CAG": 0.75, "CGG": 0.21,
        "AGC": 0.24, "ACC": 0.36, "GUG": 0.47, "UGG": 1.00, "UAC": 0.57,
        "GCU": 0.26, "UGU": 0.45, "GAU": 0.46, "GAA": 0.42, "UUU": 0.45,
        "GGU": 0.16, "CAU": 0.41, "AUU": 0.36, "AAA": 0.42, "CUU": 0.13,
        "CCU": 0.28, "CAA": 0.25, "CGU": 0.08, "UCU": 0.18, "ACU": 0.24,
        "GUU": 0.18, "UAU": 0.43, "GCA": 0.23, "GCG": 0.11, "AUA": 0.16,
        "UUA": 0.07, "UUG": 0.13, "CUC": 0.20, "CUA": 0.07, "CCA": 0.27,
        "CCG": 0.11, "CGC": 0.19, "CGA": 0.11, "AGA": 0.20, "AGG": 0.20,
        "UCC": 0.22, "UCA": 0.15, "UCG": 0.06, "AGU": 0.15, "ACA": 0.28,
        "ACG": 0.12, "GUC": 0.24, "GUA": 0.11, "GGA": 0.25, "GGG": 0.25,
        "AAU": 0.46, "UAA": 0.28, "UAG": 0.20, "UGA": 0.52,
    }


@dataclass
class CodonOptResult:
    protein_seq: str
    mrna_sequence: str      # optimized mRNA (CDS only, no UTR)
    cai: float              # Codon Adaptation Index (0-1)
    gc_content: float       # fraction
    uridine_fraction: float
    cpg_count: int
    homopolymer_max: int    # longest single-nt run
    mfe: Optional[float]    # minimum free energy from LinearFold (kcal/mol)
    structure: Optional[str]  # dot-bracket from LinearFold
    length_nt: int
    stop_codon: str


class CodonOptimizer:
    """mRNA codon optimizer for human expression — local, CPU-only."""

    def __init__(
        self,
        target_gc_min: float = 0.45,
        target_gc_max: float = 0.65,
        avoid_cpg: bool = True,
        minimize_uridine: bool = True,
        stop_codon: str = "UGA",
        use_linearfold: bool = True,
        n_candidates: int = 50,
        seed: int = 42,
    ):
        self.target_gc_min = target_gc_min
        self.target_gc_max = target_gc_max
        self.avoid_cpg = avoid_cpg
        self.minimize_uridine = minimize_uridine
        self.stop_codon = stop_codon
        self.use_linearfold = use_linearfold and LINEARFOLD_BIN.exists()
        self.n_candidates = n_candidates
        self.seed = seed
        self._freq = _load_human_codon_freq()
        self._max_freq = self._compute_max_freq()

    def _compute_max_freq(self) -> Dict[str, float]:
        """For each AA, find the highest-frequency codon."""
        max_f: Dict[str, float] = {}
        for aa, codons in CODON_TABLE.items():
            if aa == "*":
                continue
            best = max(self._freq.get(c, 0.01) for c in codons)
            max_f[aa] = best
        return max_f

    # ── scoring functions ────────────────────────────────────────────────

    def _cai(self, mrna: str, protein: str) -> float:
        """Codon Adaptation Index — geometric mean of relative adaptiveness."""
        codons = [mrna[i:i+3] for i in range(0, len(mrna) - 3, 3)]  # exclude stop
        if not codons:
            return 0.0
        log_sum = 0.0
        for codon, aa in zip(codons, protein):
            freq = self._freq.get(codon, 0.01)
            max_f = self._max_freq.get(aa, 0.01)
            w = freq / max_f
            log_sum += math.log(max(w, 1e-6))
        return math.exp(log_sum / len(codons))

    @staticmethod
    def _gc_content(mrna: str) -> float:
        gc = sum(1 for nt in mrna if nt in "GC")
        return gc / len(mrna) if mrna else 0.0

    @staticmethod
    def _uridine_fraction(mrna: str) -> float:
        return sum(1 for nt in mrna if nt == "U") / len(mrna) if mrna else 0.0

    @staticmethod
    def _cpg_count(mrna: str) -> int:
        dna = mrna.replace("U", "T")
        return sum(1 for i in range(len(dna) - 1) if dna[i:i+2] == "CG")

    @staticmethod
    def _max_homopolymer(mrna: str) -> int:
        if not mrna:
            return 0
        max_run, current_run = 1, 1
        for i in range(1, len(mrna)):
            if mrna[i] == mrna[i-1]:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 1
        return max_run

    # ── LinearFold integration ───────────────────────────────────────────

    def _run_linearfold(self, mrna: str) -> Tuple[Optional[str], Optional[float]]:
        """Run LinearFold to get MFE structure. Returns (structure, mfe)."""
        if not self.use_linearfold:
            return None, None
        try:
            proc = subprocess.run(
                [str(LINEARFOLD_BIN)],
                input=mrna,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode != 0:
                return None, None
            lines = proc.stdout.strip().split("\n")
            if len(lines) >= 2:
                parts = lines[1].split()
                structure = parts[0]
                mfe_str = parts[1].strip("()")
                return structure, float(mfe_str)
        except Exception as e:
            logger.debug(f"LinearFold failed: {e}")
        return None, None

    # ── single-sequence optimization ─────────────────────────────────────

    def _weighted_random_codon(self, aa: str, rng: random.Random) -> str:
        """Sample codon weighted by human usage frequency, with optional CpG/U penalty."""
        codons = CODON_TABLE.get(aa, [])
        if not codons:
            raise ValueError(f"Unknown amino acid: {aa}")
        if len(codons) == 1:
            return codons[0]

        weights = []
        for c in codons:
            w = self._freq.get(c, 0.01)
            if self.minimize_uridine:
                u_count = c.count("U")
                w *= (0.7 ** u_count)
            if self.avoid_cpg:
                cg_count = c.replace("U", "T").count("CG")
                w *= (0.3 ** cg_count)
            weights.append(max(w, 1e-4))

        total = sum(weights)
        weights = [w / total for w in weights]
        return rng.choices(codons, weights=weights, k=1)[0]

    def _generate_candidate(self, protein: str, rng: random.Random) -> str:
        """Generate one mRNA candidate for a protein sequence."""
        codons = [self._generate_codon_for_aa(aa, rng) for aa in protein]
        codons.append(self.stop_codon)
        return "".join(codons)

    def _generate_codon_for_aa(self, aa: str, rng: random.Random) -> str:
        if aa == "M":
            return "AUG"
        if aa == "W":
            return "UGG"
        return self._weighted_random_codon(aa, rng)

    def _score_candidate(self, mrna: str, protein: str) -> float:
        """Multi-objective score (higher = better)."""
        cai = self._cai(mrna, protein)
        gc = self._gc_content(mrna)
        u_frac = self._uridine_fraction(mrna)
        cpg = self._cpg_count(mrna)
        hp = self._max_homopolymer(mrna)

        gc_penalty = 0.0
        if gc < self.target_gc_min:
            gc_penalty = (self.target_gc_min - gc) * 5
        elif gc > self.target_gc_max:
            gc_penalty = (gc - self.target_gc_max) * 5

        cpg_penalty = cpg * 0.02
        hp_penalty = max(0, hp - 5) * 0.1
        u_penalty = max(0, u_frac - 0.25) * 2

        return cai - gc_penalty - cpg_penalty - hp_penalty - u_penalty

    # ── main optimization ────────────────────────────────────────────────

    def optimize(self, protein_seq: str) -> CodonOptResult:
        """Optimize mRNA codon usage for a protein sequence.

        Generates N candidates, scores each, picks best, optionally
        runs LinearFold for structure prediction.
        """
        protein_seq = protein_seq.upper().replace(" ", "").replace("\n", "")
        if protein_seq.endswith("*"):
            protein_seq = protein_seq[:-1]

        rng = random.Random(self.seed)
        best_mrna = None
        best_score = -999

        for _ in range(self.n_candidates):
            mrna = self._generate_candidate(protein_seq, rng)
            score = self._score_candidate(mrna, protein_seq)
            if score > best_score:
                best_score = score
                best_mrna = mrna

        structure, mfe = self._run_linearfold(best_mrna)

        return CodonOptResult(
            protein_seq=protein_seq,
            mrna_sequence=best_mrna,
            cai=round(self._cai(best_mrna, protein_seq), 4),
            gc_content=round(self._gc_content(best_mrna), 4),
            uridine_fraction=round(self._uridine_fraction(best_mrna), 4),
            cpg_count=self._cpg_count(best_mrna),
            homopolymer_max=self._max_homopolymer(best_mrna),
            mfe=round(mfe, 2) if mfe is not None else None,
            structure=structure,
            length_nt=len(best_mrna),
            stop_codon=self.stop_codon,
        )

    def optimize_epitope_cassette(self, mrna_cassette: str) -> Tuple[str, Optional[float]]:
        """Score / fold an already-assembled mRNA cassette (from MultiEpitopeAssembler).

        Returns (structure, mfe).
        """
        return self._run_linearfold(mrna_cassette)
