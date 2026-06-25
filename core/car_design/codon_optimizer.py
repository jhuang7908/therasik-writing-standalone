"""
Human codon optimizer for CAR construct DNA sequences.

Converts amino acid sequences to codon-optimized DNA using human RSCU
(Relative Synonymous Codon Usage) values from Kazusa DB.
"""
from __future__ import annotations

import math
import random
import re

# Human high-frequency codon table (Homo sapiens, Kazusa Codon Usage DB)
# For each amino acid: list of (codon, relative_frequency) sorted by frequency
_HUMAN_CODONS: dict[str, list[tuple[str, float]]] = {
    "A": [("GCC", 0.40), ("GCT", 0.26), ("GCA", 0.23), ("GCG", 0.11)],
    "R": [("CGG", 0.21), ("AGA", 0.20), ("AGG", 0.20), ("CGC", 0.19), ("CGT", 0.08), ("CGA", 0.11)],
    "N": [("AAC", 0.54), ("AAT", 0.46)],
    "D": [("GAC", 0.54), ("GAT", 0.46)],
    "C": [("TGC", 0.55), ("TGT", 0.45)],
    "Q": [("CAG", 0.73), ("CAA", 0.27)],
    "E": [("GAG", 0.58), ("GAA", 0.42)],
    "G": [("GGC", 0.34), ("GGG", 0.25), ("GGA", 0.25), ("GGT", 0.16)],
    "H": [("CAC", 0.58), ("CAT", 0.42)],
    "I": [("ATC", 0.48), ("ATT", 0.36), ("ATA", 0.16)],
    "L": [("CTG", 0.41), ("CTC", 0.20), ("CTT", 0.13), ("TTG", 0.13), ("TTA", 0.07), ("CTA", 0.07)],
    "K": [("AAG", 0.58), ("AAA", 0.42)],
    "M": [("ATG", 1.00)],
    "F": [("TTC", 0.55), ("TTT", 0.45)],
    "P": [("CCC", 0.33), ("CCT", 0.28), ("CCA", 0.27), ("CCG", 0.11)],
    "S": [("AGC", 0.24), ("TCC", 0.22), ("TCT", 0.15), ("AGT", 0.15), ("TCA", 0.12), ("TCG", 0.06)],
    "T": [("ACC", 0.36), ("ACA", 0.28), ("ACT", 0.24), ("ACG", 0.12)],
    "W": [("TGG", 1.00)],
    "Y": [("TAC", 0.57), ("TAT", 0.43)],
    "V": [("GTG", 0.47), ("GTC", 0.24), ("GTT", 0.18), ("GTA", 0.12)],
    "*": [("TGA", 0.47), ("TAA", 0.28), ("TAG", 0.25)],
}

_RESTRICTION_SITES = {
    "BsaI": "GGTCTC",
    "BsmBI": "CGTCTC",
    "NotI": "GCGGCCGC",
    "EcoRI": "GAATTC",
    "BamHI": "GGATCC",
}

_COMPLEMENT = str.maketrans("ATCG", "TAGC")


def _revcomp(seq: str) -> str:
    return seq.translate(_COMPLEMENT)[::-1]


def _weighted_choice(codons: list[tuple[str, float]], rng: random.Random) -> str:
    total = sum(w for _, w in codons)
    r = rng.random() * total
    cumulative = 0.0
    for codon, weight in codons:
        cumulative += weight
        if r <= cumulative:
            return codon
    return codons[0][0]


def _gc_content(seq: str) -> float:
    if not seq:
        return 0.0
    gc = sum(1 for c in seq if c in "GC")
    return gc / len(seq)


def _has_restriction_site(seq: str, sites: dict[str, str] | None = None) -> list[str]:
    if sites is None:
        sites = _RESTRICTION_SITES
    found = []
    for name, site in sites.items():
        if site in seq or _revcomp(site) in seq:
            found.append(name)
    return found


def _has_homopolymer(seq: str, max_run: int = 6) -> bool:
    for base in "ATCG":
        if base * (max_run + 1) in seq:
            return True
    return False


def _cai_score(dna: str) -> float:
    """Compute Codon Adaptation Index relative to human high-frequency codons."""
    max_freq = {}
    for aa, codons in _HUMAN_CODONS.items():
        top = max(w for _, w in codons)
        for codon, w in codons:
            max_freq[codon] = w / top

    log_sum = 0.0
    count = 0
    for i in range(0, len(dna) - 2, 3):
        codon = dna[i:i + 3]
        if codon in max_freq:
            log_sum += math.log(max_freq[codon]) if max_freq[codon] > 0 else -10
            count += 1
    if count == 0:
        return 0.0
    return math.exp(log_sum / count)


class CodonOptimizer:
    """Optimize amino acid sequences into human codon-optimized DNA.

    Args:
        deplete_cpg: Reduce CpG dinucleotides (useful for mRNA-LNP constructs).
        avoid_sites: Restriction enzyme sites to avoid. Defaults to BsaI, BsmBI, NotI.
        max_homopolymer: Maximum homopolymer run length allowed. Default 6.
        gc_target: Target GC content range (min, max). Default (0.40, 0.60).
        seed: Random seed for reproducibility.
    """

    def __init__(
        self,
        deplete_cpg: bool = False,
        avoid_sites: dict[str, str] | None = None,
        max_homopolymer: int = 6,
        gc_target: tuple[float, float] = (0.40, 0.60),
        seed: int = 42,
    ):
        self._deplete_cpg = deplete_cpg
        self._sites = avoid_sites if avoid_sites is not None else dict(_RESTRICTION_SITES)
        self._max_homo = max_homopolymer
        self._gc_target = gc_target
        self._rng = random.Random(seed)
        self._codons = self._build_codon_table()

    def _build_codon_table(self) -> dict[str, list[tuple[str, float]]]:
        table = {}
        for aa, codons in _HUMAN_CODONS.items():
            if self._deplete_cpg:
                adjusted = []
                for codon, w in codons:
                    if "CG" in codon:
                        w *= 0.3
                    adjusted.append((codon, w))
                table[aa] = adjusted
            else:
                table[aa] = list(codons)
        return table

    def optimize(self, aa_sequence: str) -> dict:
        """Optimize an amino acid sequence to human codon-optimized DNA.

        Returns dict with keys: dna, cai, gc_content, length_bp, warnings.
        """
        aa_sequence = aa_sequence.upper().replace(" ", "").replace("\n", "")
        warnings: list[str] = []
        codons: list[str] = []

        for aa in aa_sequence:
            if aa not in self._codons:
                warnings.append(f"Unknown amino acid '{aa}' — skipped")
                continue
            codons.append(_weighted_choice(self._codons[aa], self._rng))

        dna = "".join(codons)

        for attempt in range(50):
            problems = _has_restriction_site(dna, self._sites)
            if not problems and not _has_homopolymer(dna, self._max_homo):
                break
            dna = self._fix_problems(aa_sequence, dna, problems)

        gc = _gc_content(dna)
        if gc < self._gc_target[0]:
            warnings.append(f"GC content {gc:.1%} below target {self._gc_target[0]:.0%}")
        elif gc > self._gc_target[1]:
            warnings.append(f"GC content {gc:.1%} above target {self._gc_target[1]:.0%}")

        remaining_sites = _has_restriction_site(dna, self._sites)
        if remaining_sites:
            warnings.append(f"Could not eliminate restriction sites: {remaining_sites}")

        cai = _cai_score(dna)

        return {
            "dna": dna,
            "cai": round(cai, 4),
            "gc_content": round(gc, 4),
            "length_bp": len(dna),
            "length_aa": len(aa_sequence),
            "deplete_cpg": self._deplete_cpg,
            "warnings": warnings,
        }

    def _fix_problems(self, aa_seq: str, dna: str, site_names: list[str]) -> str:
        codons = [dna[i:i + 3] for i in range(0, len(dna), 3)]

        for site_name in site_names:
            site_seq = self._sites.get(site_name, "")
            for pat in (site_seq, _revcomp(site_seq)):
                idx = dna.find(pat)
                while idx >= 0:
                    codon_idx = idx // 3
                    if codon_idx < len(aa_seq):
                        aa = aa_seq[codon_idx]
                        new_codon = self._pick_alternative(aa, codons[codon_idx])
                        codons[codon_idx] = new_codon
                    dna = "".join(codons)
                    idx = dna.find(pat, idx + 1)

        for base in "ATCG":
            pattern = base * (self._max_homo + 1)
            idx = dna.find(pattern)
            while idx >= 0:
                codon_idx = idx // 3
                if codon_idx < len(aa_seq):
                    aa = aa_seq[codon_idx]
                    codons[codon_idx] = self._pick_alternative(aa, codons[codon_idx])
                dna = "".join(codons)
                idx = dna.find(pattern, idx + 1)

        return "".join(codons)

    def _pick_alternative(self, aa: str, current: str) -> str:
        options = [c for c, _ in self._codons.get(aa, []) if c != current]
        if not options:
            return current
        return self._rng.choice(options)


def optimize_sequence(aa_sequence: str, deplete_cpg: bool = False, seed: int = 42) -> dict:
    """Convenience function: optimize AA → human codon-optimized DNA."""
    return CodonOptimizer(deplete_cpg=deplete_cpg, seed=seed).optimize(aa_sequence)
