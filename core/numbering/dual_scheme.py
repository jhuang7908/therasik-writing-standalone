"""
dual_scheme.py — InSynBio AbEngineCore
======================================

Dual-scheme numbering (IMGT + Kabat) computed independently, then aligned by
sequence index for QA cross-check and stable downstream mapping (e.g., Vernier).

Why this exists
---------------
IMGT↔Kabat does NOT have a universal global offset. Insertions (30A, 52A, 82B…)
must be preserved. The only robust approach is:
  1) number the SAME sequence in IMGT scheme (ANARCI)
  2) number the SAME sequence in Kabat scheme (ANARCI)
  3) align the two outputs by original sequence index (0-based)

This module returns both schemes in a normalized, index-aligned form.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple


PosIns = Tuple[int, str]  # (position_int, insertion_code_str); insertion may be "" / "A" / "B" ...


@dataclass(frozen=True)
class NumberedResidue:
    seq_index: int          # 0-based index into original sequence
    pos: int                # scheme position integer
    ins: str                # insertion code, "" for none
    aa: str                 # amino acid


@dataclass(frozen=True)
class DualSchemeNumbering:
    scheme_imgt: str
    scheme_kabat: str
    chain_type: str
    sequence: str
    imgt: List[NumberedResidue]
    kabat: List[NumberedResidue]

    @property
    def length(self) -> int:
        return len(self.sequence)


def _normalize_ins(ins: Optional[str]) -> str:
    if not ins:
        return ""
    s = str(ins)
    return "" if s.strip() == "" else s.strip()


def _number_with_anarci(sequence_id: str, sequence: str, scheme: str):
    """
    Run ANARCI (anarcii) for a single sequence and return raw numbering list.

    Returns a dict entry with keys: numbering, chain_type.
    numbering is expected to be: [((pos, ins), aa, ...), ...] OR [((pos, ins), aa), ...]
    """
    from anarcii import Anarcii  # imported lazily

    engine = Anarcii()
    # In this repo's environment, Anarcii is `anarcii.pipeline.Anarcii`:
    # - .number() does NOT accept scheme=...
    # - .to_scheme(scheme) converts the LAST output in-engine.
    engine.number([(sequence_id, sequence)])
    res = engine.to_scheme(scheme)
    entry = (res.get(sequence_id) or {}) if isinstance(res, dict) else {}
    if not entry or not entry.get("numbering"):
        raise ValueError(f"ANARCI numbering failed (scheme={scheme}) for {sequence_id}")
    return entry


def _to_indexed(numbering_raw: list, sequence: str) -> List[NumberedResidue]:
    """
    Convert ANARCI numbering list to index-aligned residues.
    Skips '-' gaps; advances seq_index only on non-gap residues.
    """
    out: List[NumberedResidue] = []
    seq_i = 0

    for item in numbering_raw:
        # item could be ((pos, ins), aa, meta) or ((pos, ins), aa)
        pos_ins = item[0]
        aa = item[1]
        if aa == "-" or aa is None:
            continue
        if seq_i >= len(sequence):
            raise ValueError(
                "ANARCI produced more non-gap residues than sequence length "
                f"(seq_i={seq_i}, len={len(sequence)})"
            )
        pos = int(pos_ins[0])
        ins = _normalize_ins(pos_ins[1] if len(pos_ins) > 1 else "")
        out.append(NumberedResidue(seq_index=seq_i, pos=pos, ins=ins, aa=aa))
        seq_i += 1

    if seq_i != len(sequence):
        raise ValueError(
            "ANARCI non-gap residue count mismatch "
            f"(got={seq_i}, expected={len(sequence)})"
        )

    return out


def compute_dual_scheme_numbering(sequence: str, chain_label: str = "VH") -> DualSchemeNumbering:
    """
    Compute IMGT + Kabat numbering independently and align by sequence index.
    """
    sequence = sequence.strip().upper()
    if not sequence:
        raise ValueError("Empty sequence")

    e_imgt = _number_with_anarci(f"{chain_label}_imgt", sequence, scheme="imgt")
    e_kab  = _number_with_anarci(f"{chain_label}_kabat", sequence, scheme="kabat")

    imgt_raw = e_imgt["numbering"]
    kab_raw  = e_kab["numbering"]

    imgt = _to_indexed(imgt_raw, sequence)
    kab  = _to_indexed(kab_raw, sequence)

    # Sanity: AA must match at every sequence index
    for i in range(len(sequence)):
        if imgt[i].seq_index != i or kab[i].seq_index != i:
            raise ValueError("Internal indexing error in dual-scheme conversion")
        if imgt[i].aa != sequence[i] or kab[i].aa != sequence[i]:
            raise ValueError("Numbering AA mismatch vs sequence")
        if imgt[i].aa != kab[i].aa:
            raise ValueError("IMGT vs Kabat AA mismatch at same seq_index (should never happen)")

    chain_type = (e_imgt.get("chain_type") or e_kab.get("chain_type") or "—")
    return DualSchemeNumbering(
        scheme_imgt="imgt",
        scheme_kabat="kabat",
        chain_type=str(chain_type),
        sequence=sequence,
        imgt=imgt,
        kabat=kab,
    )


def count_kabat_insertions(d: DualSchemeNumbering) -> int:
    """Count Kabat insertion residues (ins != '')."""
    return sum(1 for r in d.kabat if r.ins != "")

