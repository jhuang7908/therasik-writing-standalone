"""
sequence_delivery.codon_optimizer — Canonical CHO/human codon optimization.

Single source of truth for the codon table used across all delivery packages.
Supersedes:
  - scripts/codon_optimizer.py
  - core/vaccine_design/codon_optimizer.py  (vaccine-specific; kept separate)
  - core/car_design/codon_optimizer.py       (CAR-T-specific; kept separate)

Version: 1.0.0  (matches sequence_delivery package version)

Notes:
  - Uses highest-frequency CHO/human codons based on Kazusa Codon Usage Table
    (Homo sapiens, RefSeq mRNA).
  - S:  AGC preferred over TCN  (avoids CpG motif, more stable in CHO)
  - R:  CGC preferred           (high expression in CHO)
  - L:  CTG preferred           (Kozak-compatible start context)
  - Stop: TGA (amber suppression-resistant in most mammalian systems)
"""

from __future__ import annotations

# ── Canonical CHO codon table (one codon per amino acid) ──────────────────
CHO_CODON_TABLE: dict[str, str] = {
    "A": "GCC",  # Ala  — GCC is highest freq in human/CHO
    "C": "TGC",  # Cys
    "D": "GAC",  # Asp
    "E": "GAG",  # Glu
    "F": "TTC",  # Phe
    "G": "GGC",  # Gly
    "H": "CAC",  # His
    "I": "ATC",  # Ile
    "K": "AAG",  # Lys
    "L": "CTG",  # Leu  — avoids TTA/TTG (low CHO)
    "M": "ATG",  # Met  (only codon)
    "N": "AAC",  # Asn
    "P": "CCC",  # Pro
    "Q": "CAG",  # Gln
    "R": "CGC",  # Arg  — CGC/CGG preferred; avoid AGA/AGG (rare in CHO)
    "S": "AGC",  # Ser  — AGC avoids CpG; TCC also acceptable
    "T": "ACC",  # Thr
    "V": "GTG",  # Val
    "W": "TGG",  # Trp  (only codon)
    "Y": "TAC",  # Tyr
    "*": "TGA",  # Stop — TGA preferred over TAA/TAG
}

# Amino acids with known alternative choices (for reference / future expansion)
_ALT_CODONS: dict[str, list[str]] = {
    "R": ["CGC", "CGG", "AGA"],
    "S": ["AGC", "TCC", "AGT"],
    "L": ["CTG", "CTC", "TTG"],
    "G": ["GGC", "GGG"],
}

CODON_TABLE_VERSION = "CHO-1.0"  # bump when table is updated


def optimize(aa_seq: str, *, add_stop: bool = True) -> str:
    """Convert an amino acid sequence to CHO-optimized DNA.

    Args:
        aa_seq:    Amino acid string (single-letter codes, case-insensitive).
                   May or may not contain a trailing '*'.
        add_stop:  If True (default), append TGA stop codon at the end
                   unless aa_seq already ends with '*'.

    Returns:
        DNA string (uppercase, no spaces, no newlines).

    Raises:
        ValueError: if aa_seq contains an unknown amino acid code.
    """
    seq = aa_seq.upper().rstrip("*")
    codons: list[str] = []
    for i, aa in enumerate(seq):
        codon = CHO_CODON_TABLE.get(aa)
        if codon is None:
            raise ValueError(
                f"Unknown amino acid '{aa}' at position {i + 1} in sequence. "
                f"Use standard single-letter codes."
            )
        codons.append(codon)
    if add_stop:
        codons.append(CHO_CODON_TABLE["*"])
    return "".join(codons)


def gc_content(dna: str) -> float:
    """Return GC fraction (0.0 – 1.0) of a DNA string."""
    dna = dna.upper()
    if not dna:
        return 0.0
    return (dna.count("G") + dna.count("C")) / len(dna)


def back_translate_check(aa_seq: str, dna: str) -> list[str]:
    """Verify that *dna* correctly encodes *aa_seq*.

    Returns:
        List of discrepancy strings (empty → all OK).
    """
    aa = aa_seq.upper().rstrip("*")
    dna_clean = dna.upper().rstrip("TGA")  # strip trailing stop if present
    issues: list[str] = []

    # Basic length check
    if len(dna_clean) % 3 != 0:
        issues.append(f"DNA length {len(dna_clean)} is not a multiple of 3")
        return issues

    codons = [dna_clean[i:i+3] for i in range(0, len(dna_clean), 3)]
    if len(codons) != len(aa):
        issues.append(
            f"Codon count {len(codons)} ≠ AA length {len(aa)}"
        )
        return issues

    # Codon → AA lookup (standard genetic code for verification)
    _CODON_TO_AA = _build_codon_to_aa()
    for idx, (codon, expected_aa) in enumerate(zip(codons, aa)):
        decoded = _CODON_TO_AA.get(codon, "?")
        if decoded != expected_aa:
            issues.append(
                f"Position {idx + 1}: codon {codon} → {decoded}, expected {expected_aa}"
            )
    return issues


def _build_codon_to_aa() -> dict[str, str]:
    """Standard genetic code codon→AA lookup (no ambiguity codes)."""
    table = {
        "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
        "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
        "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
        "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
        "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
        "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
        "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
        "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
        "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
        "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
        "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
        "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
        "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
        "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
        "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
        "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
    }
    return table
