#!/usr/bin/env python3
"""
Kabat-static + structure-guided surface position selection for petization.

Uses BioPython Shrake–Rupley SASA on the supplied Fv PDB (preferred: VH+VL in one file),
ANARCI Kabat numbering for residue↔Kabat mapping, and distance-to-CDR filters.

Does not modify scripts/structure_metrics_humanization.py (locked); this module is standalone.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

from core.humanization.kabat_utils import is_in_cdr  # noqa: E402

try:
    import anarci
except ImportError:
    anarci = None

try:
    from Bio.PDB import PDBParser
    from Bio.PDB.Polypeptide import is_aa
    from Bio.PDB.SASA import ShrakeRupley
except ImportError:
    PDBParser = None  # type: ignore
    is_aa = None  # type: ignore
    ShrakeRupley = None  # type: ignore

# Max SASA per residue (Å²) — Tien et al.-style reference (approximate)
_MAX_SASA_AA = {
    "A": 121.0, "R": 265.0, "N": 187.0, "D": 187.0, "C": 148.0,
    "E": 214.0, "Q": 214.0, "G": 97.0, "H": 216.0, "I": 195.0,
    "L": 191.0, "K": 230.0, "M": 203.0, "F": 228.0, "P": 154.0,
    "S": 143.0, "T": 163.0, "W": 264.0, "Y": 255.0, "V": 165.0,
}

KABAT_CDR_VH = {"H1": (26, 35), "H2": (50, 65), "H3": (95, 102)}
KABAT_CDR_VL = {"L1": (24, 34), "L2": (50, 56), "L3": (89, 97)}


def _chain_sequence_and_residues(chain) -> Tuple[str, List]:
    from Bio.SeqUtils import seq1

    seq_list: List[str] = []
    res_list: List = []
    for r in chain.get_residues():
        if not is_aa(r, standard=True):
            continue
        try:
            aa = seq1(r.resname)
        except Exception:
            continue
        seq_list.append(aa)
        res_list.append(r)
    return "".join(seq_list), res_list


def _cdr_ca_coords(numbering_list: List, residue_list: List, cdr_ranges: Dict[str, Tuple[int, int]]) -> List:
    """Collect CA atoms for all CDR residues."""
    from Bio.PDB import Atom

    coords: List = []
    for idx, ((pos, ins), aa) in enumerate(numbering_list):
        if aa == "-" or idx >= len(residue_list):
            continue
        for _name, (lo, hi) in cdr_ranges.items():
            if lo <= pos <= hi:
                r = residue_list[idx]
                if "CA" in r:
                    coords.append(r["CA"])
                break
    return coords


def _min_dist_ca_to_set(ca_atom, others: List) -> float:
    import numpy as np

    if not others or ca_atom is None:
        return float("inf")
    p = np.array(ca_atom.coord, dtype=float)
    best = float("inf")
    for o in others:
        q = np.array(o.coord, dtype=float)
        d = float(np.linalg.norm(p - q))
        if d < best:
            best = d
    return best


def _other_chain_ca_atoms(model, skip_chain_id: str):
    from Bio.PDB import Atom

    atoms = []
    for ch in model:
        if ch.id == skip_chain_id:
            continue
        for r in ch.get_residues():
            if r.id[0] != " ":
                continue
            if "CA" in r:
                atoms.append(r["CA"])
    return atoms


def analyze_chain_surface_guided(
    pdb_path: Path,
    chain_id: str,
    chain_label: str,
    rsa_min_exposed: float = 0.12,
    min_dist_cdr_ca: float = 5.0,
    max_rsa_buried_prune: float = 0.05,
    skip_interface_struct_extras: bool = True,
    interface_cutoff_A: float = 4.5,
) -> Dict[str, Any]:
    """
    Per-residue SASA/RSA and CDR distance for one Fv chain.

    Returns:
      keys_allowed_struct: set of (kabat_pos, ins_code) for FR residues that pass structural filters
      keys_buried_static: set of (pos, ins) with RSA below prune threshold (optional drop from static)
      errors: list[str]
      meta: diagnostics
    """
    out: Dict[str, Any] = {
        "keys_allowed_struct": set(),
        "keys_buried_static": set(),
        "errors": [],
        "meta": {},
    }
    if PDBParser is None or ShrakeRupley is None:
        out["errors"].append("BioPython PDB/SASA not available")
        return out
    if anarci is None:
        out["errors"].append("ANARCI not available")
        return out

    cdr_ranges = KABAT_CDR_VH if chain_label == "VH" else KABAT_CDR_VL
    anarci_chain = "H" if chain_label == "VH" else "L"

    parser = PDBParser(QUIET=True)
    try:
        structure = parser.get_structure("fv", str(pdb_path))
    except Exception as e:
        out["errors"].append(f"PDB parse: {e}")
        return out

    model = structure[0]
    if chain_id not in model:
        out["errors"].append(f"Chain {chain_id!r} not in PDB")
        return out

    ch = model[chain_id]
    seq, residues = _chain_sequence_and_residues(ch)
    if not seq:
        out["errors"].append("Empty chain sequence")
        return out

    try:
        numbered, _, _ = anarci.anarci([(anarci_chain, seq)], scheme="kabat")
    except Exception as e:
        out["errors"].append(f"ANARCI: {e}")
        return out

    if not numbered or not numbered[0] or not numbered[0][0]:
        out["errors"].append("ANARCI returned no numbering")
        return out

    num_list = numbered[0][0][0]
    cdr_ca = _cdr_ca_coords(num_list, residues, cdr_ranges)
    other_ca = _other_chain_ca_atoms(model, chain_id)

    try:
        sr = ShrakeRupley(probe_radius=1.4, n_points=960)
        sr.compute(model, level="R")
    except Exception as e:
        out["errors"].append(f"SASA: {e}")
        return out

    struct_keys: Set[Tuple[int, str]] = set()
    buried_keys: Set[Tuple[int, str]] = set()
    per_pos: List[Dict[str, Any]] = []

    for idx, ((pos, ins), aa) in enumerate(num_list):
        if aa == "-" or idx >= len(residues):
            continue
        ins_code = ins if ins not in (None, " ", "") else ""
        key = (pos, ins_code)
        if is_in_cdr(pos, chain_label):
            continue
        r = residues[idx]
        sasa = float(getattr(r, "sasa", 0.0))
        max_a = _MAX_SASA_AA.get(aa, 150.0)
        rsa = (sasa / max_a) if max_a > 0 else 0.0
        ca = r["CA"] if "CA" in r else None
        d_cdr = _min_dist_ca_to_set(ca, cdr_ca) if cdr_ca else float("inf")
        d_int = _min_dist_ca_to_set(ca, other_ca) if (skip_interface_struct_extras and other_ca) else float("inf")

        per_pos.append({
            "kabat_pos": pos,
            "kabat_ins": ins_code,
            "aa": aa,
            "sasa": round(sasa, 2),
            "rsa": round(rsa, 4),
            "min_dist_cdr_ca": round(d_cdr, 2) if d_cdr < float("inf") else None,
            "min_dist_other_chain_ca": round(d_int, 2) if d_int < float("inf") else None,
        })

        if rsa < max_rsa_buried_prune:
            buried_keys.add(key)

        exposed = rsa >= rsa_min_exposed and d_cdr >= min_dist_cdr_ca
        if skip_interface_struct_extras and d_int < interface_cutoff_A:
            exposed = False
        if exposed:
            struct_keys.add(key)

    out["keys_allowed_struct"] = struct_keys
    out["keys_buried_static"] = buried_keys
    out["meta"] = {
        "chain_id": chain_id,
        "chain_label": chain_label,
        "n_fr_positions_scanned": len(per_pos),
        "rsa_min_exposed": rsa_min_exposed,
        "min_dist_cdr_ca": min_dist_cdr_ca,
        "per_residue": per_pos[:200],  # cap JSON size
        "per_residue_truncated": len(per_pos) > 200,
    }
    return out


def build_reshape_keys_for_petization(
    pdb_path: Path,
    donor_seq: str,
    chain: str,
    pdb_chain_id: str,
    static_positions: Set[int],
    mode: str,
    drop_static_if_buried: bool,
    rsa_min_exposed: float = 0.12,
    min_dist_cdr_ca: float = 5.0,
) -> Tuple[Optional[Set[Tuple[int, str]]], Dict[str, Any]]:
    """
    Returns ``(reshape_keys, report)``. ``reshape_keys`` is None when the caller
    should use legacy Kabat-only tables (no PDB structural merge).
    """
    from core.humanization.kabat_utils import get_kabat_numbering

    donor_kd = get_kabat_numbering(donor_seq) or {}
    report: Dict[str, Any] = {"pdb": str(pdb_path), "chain": chain, "pdb_chain_id": pdb_chain_id}

    if mode == "kabat_only" and not drop_static_if_buried:
        report["note"] = "structure_guidance_disabled_for_positions_use_legacy_tables"
        return None, report

    an = analyze_chain_surface_guided(
        pdb_path,
        chain_id=pdb_chain_id,
        chain_label=chain,
        rsa_min_exposed=rsa_min_exposed,
        min_dist_cdr_ca=min_dist_cdr_ca,
    )
    report["structure_analysis"] = {
        k: (list(v) if isinstance(v, set) else v)
        for k, v in an.items()
        if k != "keys_allowed_struct"
    }
    if an.get("errors"):
        report["errors"] = an["errors"]
        report["fallback"] = "legacy_kabat_tables"
        return None, report

    eff_mode = mode if mode != "kabat_only" else "kabat_only"
    keys, merge_info = merge_surface_keys(
        static_positions,
        donor_kd,
        chain,
        an["keys_allowed_struct"],
        an["keys_buried_static"],
        eff_mode,
        drop_static_if_buried,
    )
    report["merge"] = merge_info
    return keys, report


def merge_surface_keys(
    static_positions: Set[int],
    donor_kd: Dict,
    chain: str,
    struct_allowed: Set[Tuple[int, str]],
    struct_buried: Set[Tuple[int, str]],
    mode: str,
    drop_static_if_buried: bool,
) -> Tuple[Set[Tuple[int, str]], Dict[str, Any]]:
    """
    Build final set of Kabat keys to reshape toward scaffold.

    Modes:
      kabat_only — positions where base Kabat pos in static_positions (legacy)
      union — static ∪ struct_allowed (FR keys only)
      intersect — static ∩ struct_allowed (requires structure)
    """
    info: Dict[str, Any] = {"mode": mode, "n_static_keys": 0, "n_union": 0, "dropped_buried": 0}

    static_keys: Set[Tuple[int, str]] = set()
    for key in donor_kd:
        pos, ins = key
        ins_code = ins if ins not in (None, " ") else ""
        if pos not in static_positions or is_in_cdr(pos, chain):
            continue
        static_keys.add((pos, ins_code))

    info["n_static_keys"] = len(static_keys)

    if mode == "kabat_only":
        final = static_keys.copy()
        if drop_static_if_buried:
            before = len(final)
            final -= struct_buried
            info["dropped_buried"] = before - len(final)
        info["n_union"] = len(final)
        return final, info

    if mode == "union":
        final = static_keys | struct_allowed
        if drop_static_if_buried:
            before = len(final)
            final -= struct_buried
            info["dropped_buried"] = before - len(final)
        info["n_union"] = len(final)
        return final, info

    if mode == "intersect":
        final = static_keys & struct_allowed
        info["n_union"] = len(final)
        return final, info

    raise ValueError(f"Unknown surface mode: {mode}")
