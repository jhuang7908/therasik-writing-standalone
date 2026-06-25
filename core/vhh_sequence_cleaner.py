"""
core/vhh_sequence_cleaner.py
────────────────────────────
Automatic VHH / VH sequence pre-processing: remove non-domain appendages
(His-tags, purification tags, signal peptides, Fc/Fab linkers) before
feeding sequences into humanization or CMC pipelines.

Strategy
--------
1. Run ANARCI (via existing imgt_number_anarcii_indexed adapter).
   ANARCI only numbers the actual VH/VHH Ig domain; anything before/after
   the numbered span in the original sequence is an appendage.
2. Classify N-terminal orphan residues as signal peptide / leader (common
   for expressed constructs with signal sequences).
3. Classify C-terminal orphan residues against a table of known purification
   tags (His-tag, FLAG, Strep-II, c-Myc, EPEA, etc.) and heavy-chain Fc
   linker sequences.

All operations are deterministic and tag-based — no ML inference required.

Returns
-------
{
    "original_sequence": str,
    "cleaned_sequence": str,
    "was_modified": bool,
    "removed": [
        {"tag": str, "position": "N-term"|"C-term", "sequence": str, "length": int}
    ],
    "domain_span": {"start": int, "end": int},  # 0-indexed, inclusive
    "warnings": [str],
    "error": str | None,
}
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# ── Known C-terminal purification tag patterns (regex, anchored at end) ─────
# Patterns listed longest-first so more specific matches win.
_CTAG_PATTERNS: List[Tuple[str, str]] = [
    # His-tags (3–12 consecutive H, allowing mixed case already .upper()ed)
    (r"H{6,12}$",                   "His-tag"),
    (r"H{4,5}$",                    "His-tag (short)"),
    (r"H{3}$",                      "His-tag (minimal)"),
    # Strep-tag II
    (r"WSHPQFEK$",                  "Strep-tag II"),
    (r"WRHPQFGG$",                  "Strep-tag"),
    # FLAG tag
    (r"DYKDDDDK$",                  "FLAG tag"),
    (r"DYKDHD[DG]D[YK]$",          "3×FLAG"),
    # c-Myc tag
    (r"EQKLISEEDL$",                "c-Myc tag"),
    # E-tag
    (r"GAPVPYPDPLEPR$",             "E-tag"),
    # EPEA tag
    (r"EPEA$",                      "EPEA tag"),
    # HA tag
    (r"YPYDVPDYA$",                 "HA tag"),
    # V5 tag
    (r"GKPIPNPLLGLDST$",            "V5 tag"),
    # T7 tag
    (r"MASMTGGQQMG$",               "T7 tag"),
    # Soft linker + His combos (GS-His, AAAA-His)
    (r"[GS]{2,6}H{6,}$",           "GS-linker + His-tag"),
    (r"A{2,4}H{6,}$",              "Ala-linker + His-tag"),
    # Hinge/Fc stub (GEC / CPPC hinge)
    (r"(DKTHTCPPC|ESKYGPP|EPKSCD)[A-Z]*$", "Fc hinge stub"),
]

# ── Known N-terminal signal peptide indicators ──────────────────────────────
# Signal peptides: typically 16–30 aa, begin with hydrophobic stretch,
# often start with M and end before the VHH framework.
# We use a heuristic: if ANARCI leaves N-terminal orphan ≤ 35 aa, classify
# as signal peptide / leader.
_MAX_SIGNAL_PEPTIDE_LEN = 35


def _strip_ctag(seq: str) -> Tuple[str, List[Dict]]:
    """Strip known C-terminal tags iteratively (longest match first)."""
    removed: List[Dict] = []
    while True:
        matched = False
        for pattern, tag_name in _CTAG_PATTERNS:
            m = re.search(pattern, seq)
            if m:
                tag_seq = m.group(0)
                seq = seq[: m.start()]
                removed.append({
                    "tag": tag_name,
                    "position": "C-term",
                    "sequence": tag_seq,
                    "length": len(tag_seq),
                })
                matched = True
                break  # restart outer loop after each removal
        if not matched:
            break
    return seq, removed


def clean_vhh_sequence(
    raw_seq: str,
    species: str = "alpaca",
    allow_partial: bool = True,
) -> Dict:
    """
    Clean a VHH/VH sequence by removing signal peptides, purification tags,
    and Fc/linker appendages.

    Parameters
    ----------
    raw_seq : str
        Raw input sequence (may contain His-tags, signal peptides, etc.)
    species : str
        ANARCI species hint ('alpaca', 'camel', 'human', 'mouse').
    allow_partial : bool
        Passed through to ANARCI adapter.

    Returns
    -------
    Dict (see module docstring for schema).
    """
    seq = raw_seq.strip().upper()
    removed: List[Dict] = []
    warnings: List[str] = []
    error: Optional[str] = None

    # ── Step 1: strip known C-terminal tags via regex ─────────────────────
    seq_after_ctag, ctag_removed = _strip_ctag(seq)
    removed.extend(ctag_removed)

    # ── Step 2: use ANARCI to find the actual Ig domain span ──────────────
    domain_start = 0
    domain_end   = len(seq_after_ctag) - 1
    working_seq  = seq_after_ctag

    try:
        from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed  # noqa: PLC0415
        result = imgt_number_anarcii_indexed(seq_after_ctag)
        rows = result.get("rows", [])
        # Filter to residues that were actually numbered (no gap)
        numbered = [r for r in rows if r.get("aa", "").strip() and r["aa"] != "-"]
        if numbered:
            domain_start = int(numbered[0].get("linear_idx", 0))
            domain_end   = int(numbered[-1].get("linear_idx", len(seq_after_ctag) - 1))

            # N-terminal orphan
            if domain_start > 0:
                n_orphan = seq_after_ctag[:domain_start]
                tag_name = (
                    "Signal peptide / leader"
                    if len(n_orphan) <= _MAX_SIGNAL_PEPTIDE_LEN
                    else "N-terminal extension"
                )
                removed.append({
                    "tag": tag_name,
                    "position": "N-term",
                    "sequence": n_orphan,
                    "length": len(n_orphan),
                })

            # C-terminal orphan (after regex stripping above)
            trailing = seq_after_ctag[domain_end + 1:]
            if trailing:
                removed.append({
                    "tag": "C-terminal extension",
                    "position": "C-term",
                    "sequence": trailing,
                    "length": len(trailing),
                })

            working_seq = seq_after_ctag[domain_start: domain_end + 1]
        else:
            warnings.append(
                "ANARCI returned no numbered residues — C-terminal tag stripping only was applied."
            )
    except Exception as _anarci_err:
        warnings.append(
            f"ANARCI unavailable ({_anarci_err}); only regex-based C-tag stripping applied."
        )
        working_seq = seq_after_ctag

    was_modified = working_seq != seq

    return {
        "original_sequence": seq,
        "cleaned_sequence": working_seq,
        "was_modified": was_modified,
        "removed": removed,
        "domain_span": {"start": domain_start, "end": domain_end},
        "warnings": warnings,
        "error": error,
    }
