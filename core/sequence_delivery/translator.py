"""
sequence_delivery.translator — AA ↔ DNA translation utilities.

Functions:
    translate(dna)           DNA → AA (standard genetic code)
    back_translate(aa, ...)  AA → DNA using codon_optimizer (CHO table)
    strip_signal_peptide(full_aa, sp_aa)  remove SP prefix; assert match
    extract_sp(full_aa, sp_aa)            return (sp, mature) tuple
"""

from __future__ import annotations
from . import codon_optimizer as _co
from .codon_optimizer import _build_codon_to_aa


def translate(dna: str, *, stop_symbol: str = "*") -> str:
    """Translate a DNA sequence to amino acids (standard genetic code).

    Args:
        dna:         DNA string (ACGT, uppercase or lowercase).
        stop_symbol: character used for stop codons (default '*').
    Returns:
        AA string including stop symbol if present.
    Raises:
        ValueError: if dna length is not a multiple of 3.
    """
    dna = dna.upper()
    if len(dna) % 3 != 0:
        raise ValueError(
            f"DNA length {len(dna)} is not a multiple of 3; cannot translate cleanly."
        )
    table = _build_codon_to_aa()
    aas: list[str] = []
    for i in range(0, len(dna), 3):
        codon = dna[i:i+3]
        aa = table.get(codon, "X")
        if aa == "*":
            aas.append(stop_symbol)
        else:
            aas.append(aa)
    return "".join(aas)


def back_translate(aa_seq: str, *, add_stop: bool = True) -> str:
    """Translate AA → CHO-optimized DNA using the canonical codon table.

    Thin wrapper around codon_optimizer.optimize().
    """
    return _co.optimize(aa_seq, add_stop=add_stop)


def strip_signal_peptide(full_aa: str, sp_aa: str) -> str:
    """Remove signal peptide prefix and return mature protein AA.

    Raises:
        ValueError: if full_aa does not start with sp_aa.
    """
    if not full_aa.upper().startswith(sp_aa.upper()):
        raise ValueError(
            f"Sequence does not start with the expected SP.\n"
            f"  Expected SP: {sp_aa}\n"
            f"  Sequence start: {full_aa[:len(sp_aa)+5]}"
        )
    return full_aa[len(sp_aa):]


def extract_sp(full_aa: str, sp_aa: str) -> tuple[str, str]:
    """Return (signal_peptide, mature_protein) from a full-length AA.

    Raises:
        ValueError: if SP prefix is not found.
    """
    mature = strip_signal_peptide(full_aa, sp_aa)
    return sp_aa, mature


def find_signal_peptide_end(aa_seq: str, max_sp_len: int = 30) -> int:
    """Heuristic: find likely SP cleavage site within the first *max_sp_len* residues.

    Uses the AXA / SXA motif common to IgH/IgK signal peptides.
    Returns 0-based index of first mature residue (or 0 if not detected).
    """
    import re
    # Common SP cleavage: ends with A-X-A pattern (signal peptidase I rule)
    window = aa_seq[:max_sp_len]
    for m in re.finditer(r"[ACGST][A-Z][A]", window):
        return m.end()
    return 0
