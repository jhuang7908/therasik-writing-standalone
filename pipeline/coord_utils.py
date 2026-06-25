"""
coord_utils.py — Canonical coordinate-system helpers for the VHH/VH design pipeline
=====================================================================================

TWO COORDINATE SYSTEMS EXIST IN EVERY PROJECT.  NEVER MIX THEM.

┌─────────────────────────────────────────────────────────────────────────────┐
│  LINEAR (sequence) coordinates                                              │
│  ─────────────────────────────                                              │
│  Source  : mask["cdr_regions"][CDR]["linear_start/end"]                     │
│  Range   : 0-indexed positions in the raw ungapped protein sequence         │
│  Use for : seq[i], mutation counting, CDR identity, ablang scoring          │
│  NEVER   : PDB operations, MPNN mask generation                             │
│                                                                             │
│  PDB / MPNN-sequential coordinates                                          │
│  ─────────────────────────────────                                          │
│  Source  : mask["design_mask"]["designable_pdb_residues"]                   │
│            mask["cdr_regions"][CDR]["pdb_resnums"]                          │
│  Range   : Chothia/IMGT PDB residue numbers (include numbering gaps)        │
│  Use for : ProteinMPNN mask, EvoEF2/PRODIGY mutations, HADDOCK restraints  │
│  NEVER   : Indexing into a Python string / numpy array                      │
│                                                                             │
│  WHY THEY DIFFER: Chothia VHH PDBs contain conventional numbering gaps     │
│  (e.g. positions 10, 31–34, 60–61, 73 for the muMAb4D5 VHH).              │
│  The raw protein has N residues; the PDB has N + G residue *slots* where   │
│  G is the number of gaps.  CDR3 is typically offset by +8 for this VHH.   │
└─────────────────────────────────────────────────────────────────────────────┘

All public functions in this module are named to make the coordinate system
unambiguous:  *_linear_*  →  raw sequence  |  *_pdb_*  →  PDB residue number
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


# ── Public API: coordinate accessors ──────────────────────────────────────────

def cdr_linear_ranges(
    mask: dict,
    cdrs: list[str] | None = None,
) -> dict[str, tuple[int, int]]:
    """Return {cdr_key: (linear_start, linear_end)} for the given CDRs.

    *linear_start* and *linear_end* are **0-indexed** positions in the raw
    protein sequence string — safe for ``seq[ls : le + 1]`` and ``range(ls, le+1)``.

    Args:
        mask : Parsed mask_strategy.json dict.
        cdrs : CDR keys to include; defaults to all keys in cdr_regions.
    """
    regions = mask.get("cdr_regions", {})
    keys = cdrs if cdrs is not None else list(regions.keys())
    result: dict[str, tuple[int, int]] = {}
    for k in keys:
        c = regions.get(k, {})
        ls, le = c.get("linear_start"), c.get("linear_end")
        if ls is None or le is None:
            raise ValueError(
                f"CDR '{k}' is missing linear_start or linear_end in mask_strategy.json"
            )
        result[k] = (int(ls), int(le))
    return result


def cdr_pdb_resnums(
    mask: dict,
    cdrs: list[str] | None = None,
) -> dict[str, list[int]]:
    """Return {cdr_key: [pdb_resnum, ...]} for the given CDRs.

    PDB residue numbers are suitable for structural operations (EvoEF2, HADDOCK,
    PRODIGY restraints) and for cross-referencing with BioPython PDB parsers.
    They are **not** valid Python string indices.
    """
    regions = mask.get("cdr_regions", {})
    keys = cdrs if cdrs is not None else list(regions.keys())
    result: dict[str, list[int]] = {}
    for k in keys:
        c = regions.get(k, {})
        resnums = c.get("pdb_resnums", [])
        if not resnums:
            raise ValueError(
                f"CDR '{k}' is missing pdb_resnums in mask_strategy.json"
            )
        result[k] = [int(r) for r in resnums]
    return result


def mpnn_designable_pdb_positions(mask: dict) -> list[int]:
    """Return sorted PDB residue numbers that ProteinMPNN should design.

    These come from ``design_mask.designable_pdb_residues`` minus
    ``design_mask.fixed_root_pdb_residues``.  They equal the MPNN
    *sequential* positions because Chothia PDB residue numbers and MPNN
    sequential indices both skip the same gap slots.

    This is the **only** correct source for the ``--position_list`` argument
    of ``make_fixed_positions_dict.py --specify_non_fixed``.
    """
    dm = mask.get("design_mask", {})
    designable = set(dm.get("designable_pdb_residues", []))
    fixed_root = set(dm.get("fixed_root_pdb_residues", []))
    if not designable:
        raise ValueError(
            "design_mask.designable_pdb_residues is empty in mask_strategy.json"
        )
    return sorted(designable - fixed_root)


def redesign_linear_eligible(mask: dict) -> list[int]:
    """0-indexed linear positions eligible for redesign (body + semiopen, no roots).

    Use this for sequence-level analysis: CDR identity, mutation counting,
    ablang scoring windows.  Do NOT pass these to MPNN.
    """
    redesign = mask["design_mask"].get("redesign_cdrs", [])
    regions = mask["cdr_regions"]
    root_cfg = mask.get("root_constraints", {})
    pos: list[int] = []
    for k in redesign:
        c = regions.get(k, {})
        ls, le = c.get("linear_start"), c.get("linear_end")
        if ls is None or le is None:
            continue
        fixed = set(root_cfg.get(k, {}).get("fixed_0indexed", []))
        for i in range(int(ls), int(le) + 1):
            if i not in fixed:
                pos.append(i)
    return sorted(pos)


# ── Validation ─────────────────────────────────────────────────────────────────

def validate_mask_coords(mask: dict, *, abort: bool = True) -> list[str]:
    """Cross-check linear and PDB coordinates for internal consistency.

    Checks:
    1. CDR length matches between linear span and pdb_resnums count.
    2. CDR sequence can be sliced from wt_sequence using linear coords.
    3. designable_pdb_residues contains no positions from fixed_root_pdb_residues.
    4. linear_start offsets are non-negative and linear_end > linear_start.

    Args:
        mask  : Parsed mask_strategy.json.
        abort : If True, call sys.exit(1) on any error (default for pipeline use).

    Returns:
        List of error strings (empty = all OK).
    """
    errors: list[str] = []
    wt = mask.get("wt_sequence", "")
    regions = mask.get("cdr_regions", {})
    dm = mask.get("design_mask", {})
    designable = set(dm.get("designable_pdb_residues", []))
    fixed_root = set(dm.get("fixed_root_pdb_residues", []))

    for cdr_key, c in regions.items():
        ls = c.get("linear_start")
        le = c.get("linear_end")
        seq = c.get("sequence", "")
        resnums = c.get("pdb_resnums", [])

        if ls is None or le is None:
            errors.append(f"{cdr_key}: missing linear_start or linear_end")
            continue
        ls, le = int(ls), int(le)

        # Check 4: range sanity
        if ls < 0 or le < ls:
            errors.append(f"{cdr_key}: invalid linear range [{ls}, {le}]")

        # Check 2: sequence slice matches stored sequence
        if wt and seq:
            sliced = wt[ls: le + 1]
            if sliced != seq:
                errors.append(
                    f"{cdr_key}: wt_sequence[{ls}:{le+1}]='{sliced}' "
                    f"does not match stored sequence='{seq}' — "
                    f"linear_start/end are wrong"
                )

        # Check 1: length agreement
        linear_len = le - ls + 1
        if resnums and len(resnums) != linear_len:
            errors.append(
                f"{cdr_key}: linear span = {linear_len} residues but "
                f"pdb_resnums has {len(resnums)} entries — "
                f"one of them is wrong"
            )

    # Check 3: no overlap between designable and root-fixed
    overlap = designable & fixed_root
    if overlap:
        errors.append(
            f"designable_pdb_residues and fixed_root_pdb_residues overlap: {sorted(overlap)}"
        )

    if errors:
        header = "[COORD VALIDATE ❌] mask_strategy.json has coordinate inconsistencies:"
        print(header)
        for e in errors:
            print(f"  • {e}")
        if abort:
            sys.exit(1)
    else:
        print("[COORD VALIDATE ✓] mask_strategy.json coordinates are internally consistent.")

    return errors


# ── Mutation helpers (sequence-level, linear coords) ──────────────────────────

def count_linear_mutations(
    seq: str,
    wt_seq: str,
    linear_start: int,
    linear_end: int,
) -> int:
    """Count mutations in seq vs wt_seq in the 0-indexed linear range [start, end]."""
    return sum(
        1 for i in range(linear_start, linear_end + 1)
        if i < len(seq) and i < len(wt_seq) and seq[i] != wt_seq[i]
    )


def per_cdr_linear_mutations(
    seq: str,
    wt_seq: str,
    mask: dict,
    cdrs: list[str] | None = None,
) -> dict[str, int]:
    """Return {cdr_key: n_mutations} using linear coordinates."""
    ranges = cdr_linear_ranges(mask, cdrs)
    return {
        k: count_linear_mutations(seq, wt_seq, ls, le)
        for k, (ls, le) in ranges.items()
    }


def cdr_linear_identity(
    seq: str,
    wt_seq: str,
    mask: dict,
    cdrs: list[str] | None = None,
) -> float:
    """Combined CDR identity over all listed CDRs (linear coordinate)."""
    ranges = cdr_linear_ranges(mask, cdrs)
    total = sum(le - ls + 1 for ls, le in ranges.values())
    if total == 0:
        return 1.0
    matches = sum(
        1 for ls, le in ranges.values()
        for i in range(ls, le + 1)
        if i < len(seq) and i < len(wt_seq) and seq[i] == wt_seq[i]
    )
    return matches / total


def get_combined_cdr_string(
    seq: str,
    mask: dict,
    cdrs: list[str] | None = None,
) -> str:
    """Concatenate CDR slices from seq using linear coordinates."""
    ranges = cdr_linear_ranges(mask, cdrs)
    return "".join(seq[ls: le + 1] for ls, le in ranges.values())


# ── CLI: validate a mask file from the command line ───────────────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        description="Validate mask_strategy.json coordinate consistency"
    )
    ap.add_argument("mask_json", help="Path to mask_strategy.json")
    args = ap.parse_args()
    mask_data = json.loads(Path(args.mask_json).read_text(encoding="utf-8"))
    errs = validate_mask_coords(mask_data, abort=False)
    sys.exit(1 if errs else 0)
