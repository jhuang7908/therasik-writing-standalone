#!/usr/bin/env python3
"""
Structure-based metrics for antibody humanization template selection.

From a VH/VL PDB structure, computes:
  1. North/canonical  — CDR canonical class (H1/H2/H3, L1/L2/L3) from sequence/length.
  2. VH/VL  — Inter-domain angle (principal axis angle between VH and VL).
  3. Vernier Zone Packing — Contact number (heavy atoms within 4.5 Å) at key Vernier positions.
  4. Vernier Zone ↔ CDR  — Min heavy-atom distance from Vernier residues to each CDR loop.
  5. VH/VL  — Interface residue pairs (5.5 Å), mean and min distance.
  6. Vernier Zone  — SASA (Å²) of Vernier residues (burial = low SASA).

Requires: BioPython, numpy. ANARCI/ANARCII for Kabat numbering (via project anarci shim).
Usage:
  python scripts/structure_metrics_humanization.py --pdb path/to/fab.pdb [--vh H --vl L] [--out metrics.json]
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from Bio.PDB import PDBParser, NeighborSearch
from Bio.PDB.Polypeptide import is_aa, Polypeptide
from Bio.SeqUtils import seq1

try:
    from Bio.PDB.SASA import ShrakeRupley
except ImportError:
    ShrakeRupley = None

warnings_filter = getattr(__import__("warnings"), "filterwarnings", lambda *a, **k: None)
warnings_filter("ignore", category=UserWarning, module="Bio.PDB")
try:
    from Bio.PDB.PDBExceptions import PDBConstructionWarning
    warnings_filter("ignore", category=PDBConstructionWarning)
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import anarci
except ImportError:
    anarci = None

# Kabat numbering: Vernier positions (from vernier_zone_weights.md)
VERNIER_KABAT_VH = [2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94]
VERNIER_KABAT_VL = [2, 4, 36, 46, 49, 69, 71, 98]

# Tier labels for reporting / QA (22 positions total)
_VH_TIER = {71: "T1"}
_VH_TIER.update({p: "T2" for p in [2, 27, 28, 29, 30, 69, 93, 94]})
_VH_TIER.update({p: "T3" for p in [48, 49, 67, 73, 78]})
_VL_TIER = {71: "T1"}
_VL_TIER.update({p: "T2" for p in [36, 46]})
_VL_TIER.update({p: "T3" for p in [2, 4, 49, 69, 98]})

# Kabat CDR ranges (inclusive) — standard definitions
KABAT_CDR_VH = {"H1": (26, 35), "H2": (50, 65), "H3": (95, 102)}
KABAT_CDR_VL = {"L1": (24, 34), "L2": (50, 56), "L3": (89, 97)}

AA3_TO_1 = {
    "ALA": "A", "CYS": "C", "ASP": "D", "GLU": "E", "PHE": "F",
    "GLY": "G", "HIS": "H", "ILE": "I", "LYS": "K", "LEU": "L",
    "MET": "M", "ASN": "N", "PRO": "P", "GLN": "Q", "ARG": "R",
    "SER": "S", "THR": "T", "VAL": "V", "TRP": "W", "TYR": "Y",
}


@dataclass
class StructureMetrics:
    pdb_path: str
    chain_vh: str
    chain_vl: str
    # 1. Canonical (North-style, length + key position)
    canonical: Dict[str, str] = field(default_factory=dict)
    # 1b. North canonical from structure (phi/psi): Standard vs Outlier, per CDR
    canonical_north: Dict[str, str] = field(default_factory=dict)
    canonical_north_score: Dict[str, float] = field(default_factory=dict)
    # 2. VH/VL angle (degrees)
    vh_vl_angle_deg: Optional[float] = None
    # 3. Vernier packing (contact number per position)
    vernier_packing: Dict[str, float] = field(default_factory=dict)
    # 4. Vernier ↔ CDR min distances (Å)
    vernier_cdr_distances: Dict[str, float] = field(default_factory=dict)
    # 5. VH/VL interface
    interface_n_pairs: int = 0
    interface_mean_dist_A: Optional[float] = None
    interface_min_dist_A: Optional[float] = None
    # 6. Vernier burial (SASA Å²)
    vernier_sasa_total: Optional[float] = None
    vernier_sasa_per_residue: Dict[str, float] = field(default_factory=dict)
    # 22 Vernier positions dual numbering table (IMGT + Kabat) aligned by sequence_index
    vernier_dual_numbering: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def _get_residues_at_kabat_positions(
    numbering_list: List,
    residue_list: List,
    kabat_positions: List[int],
) -> Dict[int, Any]:
    """Map Kabat position -> residue object. numbering_list from same chain as residue_list."""
    pos_to_idx: Dict[int, int] = {}
    for idx, ((pos, ins), aa) in enumerate(numbering_list):
        if ins in (" ", "") and aa != "-" and pos in kabat_positions:
            pos_to_idx[pos] = idx
    return {pos: residue_list[idx] for pos, idx in pos_to_idx.items() if idx < len(residue_list)}


def _get_cdr_residue_indices(
    numbering_list: List,
    cdr_ranges: Dict[str, Tuple[int, int]],
) -> Dict[str, List[int]]:
    """Return {cdr_name: [seq_indices]} for residues in each CDR (Kabat)."""
    result: Dict[str, List[int]] = {k: [] for k in cdr_ranges}
    for idx, ((pos, ins), aa) in enumerate(numbering_list):
        if aa == "-":
            continue
        for cdr_name, (lo, hi) in cdr_ranges.items():
            if lo <= pos <= hi:
                result[cdr_name].append(idx)
                break
    return result


def _canonical_class_h1(cdr_seq: str, _fr1_tail: str = "") -> str:
    n = len(cdr_seq)
    if n == 13:
        return "H1-13-1"
    if n == 10:
        return "H1-10-1"
    if n == 11:
        return "H1-11-1"
    if n == 12:
        return "H1-12-1"
    return f"H1-{n}-?"


def _canonical_class_h2(cdr_seq: str, vh_71_aa: str) -> str:
    n = len(cdr_seq)
    if n == 10:
        return "H2-10-1" if vh_71_aa in ("A", "V") else "H2-10-2"
    if n == 9:
        return "H2-9-1"
    if n == 12:
        return "H2-12-1"
    return f"H2-{n}-?"


def _canonical_class_h3(cdr_seq: str) -> str:
    return f"H3-{len(cdr_seq)}"


def _canonical_class_l1(cdr_seq: str) -> str:
    n = len(cdr_seq)
    if n == 11:
        return "L1-11-1"
    if n == 12:
        return "L1-12-1"
    if n == 13:
        return "L1-13-1"
    if n == 10:
        return "L1-10-1"
    return f"L1-{n}-?"


def _canonical_class_l2(cdr_seq: str) -> str:
    n = len(cdr_seq)
    if n == 7:
        return "L2-7-1"
    if n == 8:
        return "L2-8-1"
    return f"L2-{n}-?"


def _canonical_class_l3(cdr_seq: str) -> str:
    return f"L3-{len(cdr_seq)}"


def _phi_psi_for_chain(chain: Any) -> Tuple[List[Tuple[Optional[float], Optional[float]]], Dict[Tuple, int]]:
    """(phi, psi) in radians per residue in chain (Polypeptide order), and res_id -> index."""
    poly = Polypeptide(chain)
    phi_psi_list = poly.get_phi_psi_list()
    poly_residues = [r for r in chain.get_residues() if r.id[0] == " " and is_aa(r)]
    res_id_to_idx = {r.get_id(): i for i, r in enumerate(poly_residues)}
    return phi_psi_list, res_id_to_idx


def _north_type(cdr_name: str, angles_deg: List[Tuple[float, float]]) -> Tuple[str, float]:
    """
    North structural type from phi/psi: Standard (canonical-like) vs Outlier.
    H1/H2/L1/L2: beta/alpha allowed regions; H3/L3: broader allowed, different threshold.
    """
    if not angles_deg:
        return "N/A", 0.0
    # Allowed regions (degrees): beta (-120,-60)x(-30,30), (-120,-60)x(90,150), (-90,-30)x(-30,30)
    def allowed_non_h3(phi: float, psi: float) -> bool:
        if not (-180 <= phi <= 180 and -180 <= psi <= 180):
            return False
        if (-120 <= phi <= -60 and -30 <= psi <= 30):
            return True
        if (-120 <= phi <= -60 and 90 <= psi <= 150):
            return True
        if (-90 <= phi <= -30 and -30 <= psi <= 30):
            return True
        return False
    # H3/L3: exclude disallowed (positive phi + very negative psi, or very negative phi + high psi)
    def allowed_h3(phi: float, psi: float) -> bool:
        if not (-180 <= phi <= 180 and -180 <= psi <= 180):
            return False
        if (phi > 0 and psi < -90):
            return False
        if (phi < -90 and psi > 90):
            return False
        return True
    is_h3_or_l3 = cdr_name in ("H3", "L3")
    valid = sum(
        1 for phi, psi in angles_deg
        if (allowed_h3(phi, psi) if is_h3_or_l3 else allowed_non_h3(phi, psi))
    )
    score = valid / len(angles_deg)
    threshold = 0.7 if is_h3_or_l3 else 0.8
    label = "Standard" if score >= threshold else "Outlier"
    return label, round(float(score), 2)


def _extract_cdr_sequences(numbering_list: List, cdr_ranges: Dict[str, Tuple[int, int]]) -> Dict[str, str]:
    seqs = {}
    for cdr_name, (lo, hi) in cdr_ranges.items():
        aas = []
        for (pos, ins), aa in numbering_list:
            if ins in (" ", "") and lo <= pos <= hi and aa != "-":
                aas.append(aa)
        seqs[cdr_name] = "".join(aas)
    return seqs


def _principal_axis_angle_deg(coords: np.ndarray) -> np.ndarray:
    """First principal axis (direction of max variance). coords shape (N, 3)."""
    if coords.shape[0] < 3:
        return np.array([1.0, 0.0, 0.0])
    center = coords.mean(axis=0)
    centered = coords - center
    _, _, vh = np.linalg.svd(centered)
    return vh[0]


def _angle_between_vectors_deg(v1: np.ndarray, v2: np.ndarray) -> float:
    v1 = np.asarray(v1, dtype=float)
    v2 = np.asarray(v2, dtype=float)
    v1 = v1 / (np.linalg.norm(v1) + 1e-12)
    v2 = v2 / (np.linalg.norm(v2) + 1e-12)
    dot = np.clip(np.dot(v1, v2), -1.0, 1.0)
    return float(np.degrees(np.arccos(np.abs(dot))))


def _contact_number(residue, all_atoms: List, radius: float = 4.5) -> float:
    backbone = {"N", "CA", "C", "O"}
    target_atoms = [a for a in residue.get_atoms() if getattr(a, "element", None) != "H"]
    side_chain = [a for a in target_atoms if a.name not in backbone]
    if not side_chain:
        side_chain = [a for a in target_atoms if a.name == "CA"]
    if not side_chain:
        return float("nan")
    ns = NeighborSearch(all_atoms)
    contacts: Set = set()
    for atom in side_chain:
        for n in ns.search(atom.get_coord(), radius, level="A"):
            if n.get_parent() != residue:
                contacts.add(n)
    return float(len(contacts))


def _min_heavy_atom_distance(res_a, res_b) -> float:
    def heavy_coords(res):
        return np.array([a.coord for a in res.get_atoms() if getattr(a, "element", None) != "H"])
    ca = heavy_coords(res_a)
    cb = heavy_coords(res_b)
    if ca.size == 0 or cb.size == 0:
        return float("nan")
    diff = ca[:, None, :] - cb[None, :, :]
    return float(np.sqrt((diff * diff).sum(axis=-1)).min())


def _interface_pairs_and_distances(chain_a, chain_b, cutoff: float = 5.5) -> Tuple[Set[Tuple], List[float]]:
    def heavy_atoms(chain):
        return [a for a in chain.get_atoms() if getattr(a, "element", None) != "H"]

    atoms_a = heavy_atoms(chain_a)
    atoms_b = heavy_atoms(chain_b)
    # Build a fast O(1) lookup set for chain_b atoms to avoid O(n) `in atoms_a` scan
    set_b = set(id(a) for a in atoms_b)
    ns = NeighborSearch(atoms_a + atoms_b)
    pairs: Set[Tuple] = set()
    distances: List[float] = []
    for a in atoms_a:
        ra = a.get_parent()
        if ra.id[0] != " ":
            continue
        for b in ns.search(a.coord, cutoff, level="A"):
            if id(b) not in set_b:
                continue
            rb = b.get_parent()
            if rb.id[0] != " ":
                continue
            pairs.add((ra.id, rb.id))
            distances.append(float(np.linalg.norm(a.coord - b.coord)))
    return pairs, distances


def analyze_structure(
    pdb_path: Path,
    chain_vh: str = "H",
    chain_vl: str = "L",
    vernier_lookup: Optional[Dict[str, Any]] = None,
    skip_sasa: bool = False,
    debug_timing: bool = False,
) -> StructureMetrics:
    _t0 = time.perf_counter()
    def _tstep(label: str) -> None:
        if debug_timing:
            print(f"    [t] {label}: {time.perf_counter()-_t0:.3f}s", flush=True)
    out = StructureMetrics(
        pdb_path=str(pdb_path),
        chain_vh=chain_vh,
        chain_vl=chain_vl,
    )
    parser = PDBParser(QUIET=True)
    try:
        structure = parser.get_structure("ab", str(pdb_path))
    except Exception as e:
        out.errors.append(f"PDB parse: {e}")
        return out

    _tstep("PDB parse")
    model = structure[0]
    if chain_vh not in model or chain_vl not in model:
        out.errors.append(f"Chains {chain_vh}/{chain_vl} not found")
        return out

    ch_h = model[chain_vh]
    ch_l = model[chain_vl]

    def chain_seq_res(chain):
        seq_list = []
        res_list = []
        for r in chain.get_residues():
            if not is_aa(r, standard=True):
                continue
            try:
                seq_list.append(AA3_TO_1.get(r.resname, "X"))
                res_list.append(r)
            except Exception:
                continue
        return "".join(seq_list), res_list

    vh_seq, vh_residues = chain_seq_res(ch_h)
    vl_seq, vl_residues = chain_seq_res(ch_l)
    if not vh_seq or not vl_seq:
        out.errors.append("Empty chain sequence")
        return out

    # Dual-scheme numbering (IMGT + Kabat) for Vernier 22 positions — independent compute + index alignment.
    # This does NOT depend on PDB residue numbering and is used to prevent Kabat insertion-loss / drift
    # from corrupting Vernier interpretation across modules and reports.
    try:
        from core.numbering.dual_scheme import compute_dual_scheme_numbering  # noqa: PLC0415

        dual_vh = compute_dual_scheme_numbering(vh_seq, chain_label="VH")
        dual_vl = compute_dual_scheme_numbering(vl_seq, chain_label="VL")

        def _rows(dual, kabat_positions: List[int], tier_map: Dict[int, str], chain: str) -> Tuple[List[Dict[str, Any]], List[int]]:
            # Build lookup: (pos, ins) -> residue record; we only require the base position (ins="") for Vernier points.
            kab_base = {(r.pos, r.ins): r for r in dual.kabat}
            rows: List[Dict[str, Any]] = []
            missing: List[int] = []
            for kpos in kabat_positions:
                r_k = kab_base.get((kpos, ""))
                if r_k is None:
                    missing.append(kpos)
                    continue
                r_i = dual.imgt[r_k.seq_index]
                rows.append({
                    "chain": chain,
                    "tier": tier_map.get(kpos, "?"),
                    "seq_index": r_k.seq_index,
                    "aa": r_k.aa,
                    "kabat_pos": r_k.pos,
                    "kabat_ins": r_k.ins or "",
                    "imgt_pos": r_i.pos,
                    "imgt_ins": r_i.ins or "",
                })
            return rows, missing

        rows_vh, miss_vh = _rows(dual_vh, VERNIER_KABAT_VH, _VH_TIER, "VH")
        rows_vl, miss_vl = _rows(dual_vl, VERNIER_KABAT_VL, _VL_TIER, "VL")
        out.vernier_dual_numbering = rows_vh + rows_vl

        if miss_vh or miss_vl:
            out.errors.append(
                "Vernier dual-numbering missing Kabat base positions: "
                f"VH_missing={miss_vh or []}, VL_missing={miss_vl or []}"
            )
        elif len(out.vernier_dual_numbering) != (len(VERNIER_KABAT_VH) + len(VERNIER_KABAT_VL)):
            out.errors.append(
                "Vernier dual-numbering row count mismatch: "
                f"got={len(out.vernier_dual_numbering)}, expected={len(VERNIER_KABAT_VH)+len(VERNIER_KABAT_VL)}"
            )
    except Exception as e:
        out.errors.append(f"Dual-scheme numbering failed: {e}")

    _tstep("chain seq+res")
    use_lookup = vernier_lookup is not None and pdb_path.stem in vernier_lookup
    vernier_h: Dict[int, Any] = {}
    vernier_l: Dict[int, Any] = {}
    cdr_res_h: Dict[str, List] = {}
    cdr_res_l: Dict[str, List] = {}

    cdr_idx_h: Dict[str, List[int]] = {}
    cdr_idx_l: Dict[str, List[int]] = {}
    if use_lookup:
        #  ANARCI ：Vernier/CDR  IMGT/Kabat ， ANARCI
        ent = vernier_lookup[pdb_path.stem]
        out.canonical = dict(ent.get("canonical") or {})
        vernier_h = {int(pos): vh_residues[idx] for pos, idx in (ent.get("VH") or {}).items() if idx < len(vh_residues)}
        vernier_l = {int(pos): vl_residues[idx] for pos, idx in (ent.get("VL") or {}).items() if idx < len(vl_residues)}
        cdr_idx_h = {name: list(inds) for name, inds in (ent.get("VH_cdr_indices") or {}).items()}
        cdr_idx_l = {name: list(inds) for name, inds in (ent.get("VL_cdr_indices") or {}).items()}
        cdr_res_h = {name: [vh_residues[i] for i in inds if i < len(vh_residues)] for name, inds in cdr_idx_h.items()}
        cdr_res_l = {name: [vl_residues[i] for i in inds if i < len(vl_residues)] for name, inds in cdr_idx_l.items()}
    else:
        if anarci is None:
            out.errors.append("anarci not available and no vernier_lookup")
            return out
        try:
            numbered, _, _ = anarci.anarci([("H", vh_seq), ("L", vl_seq)], scheme="kabat")
        except Exception as e:
            out.errors.append(f"ANARCI: {e}")
            return out
        if not numbered or not numbered[0]:
            out.errors.append("ANARCI returned no numbering")
            return out
        num_h = numbered[0][0][0] if numbered[0][0] and len(numbered[0][0]) > 0 else []
        num_l = numbered[0][1][0] if len(numbered[0]) > 1 and numbered[0][1] and len(numbered[0][1]) > 0 else []
        if not num_h or not num_l:
            out.errors.append("ANARCI numbering empty for H or L")
            return out
        cdr_seqs_h = _extract_cdr_sequences(num_h, KABAT_CDR_VH)
        cdr_seqs_l = _extract_cdr_sequences(num_l, KABAT_CDR_VL)
        vh_71_aa = "X"
        for (pos, ins), aa in num_h:
            if pos == 71 and (ins in (" ", "") or not ins):
                vh_71_aa = aa if aa != "-" else "X"
                break
        out.canonical["H1"] = _canonical_class_h1(cdr_seqs_h.get("H1", ""))
        out.canonical["H2"] = _canonical_class_h2(cdr_seqs_h.get("H2", ""), vh_71_aa)
        out.canonical["H3"] = _canonical_class_h3(cdr_seqs_h.get("H3", ""))
        out.canonical["L1"] = _canonical_class_l1(cdr_seqs_l.get("L1", ""))
        out.canonical["L2"] = _canonical_class_l2(cdr_seqs_l.get("L2", ""))
        out.canonical["L3"] = _canonical_class_l3(cdr_seqs_l.get("L3", ""))
        vernier_h = _get_residues_at_kabat_positions(num_h, vh_residues, VERNIER_KABAT_VH)
        vernier_l = _get_residues_at_kabat_positions(num_l, vl_residues, VERNIER_KABAT_VL)
        cdr_idx_h = _get_cdr_residue_indices(num_h, KABAT_CDR_VH)
        cdr_idx_l = _get_cdr_residue_indices(num_l, KABAT_CDR_VL)
        cdr_res_h = {name: [vh_residues[i] for i in idxs if i < len(vh_residues)] for name, idxs in cdr_idx_h.items()}
        cdr_res_l = {name: [vl_residues[i] for i in idxs if i < len(vl_residues)] for name, idxs in cdr_idx_l.items()}

    _tstep("vernier/cdr lookup")
    vernier_residues_h = list(vernier_h.values())
    vernier_residues_l = list(vernier_l.values())

    # 1b. North canonical from structure (phi/psi via Polypeptide.get_phi_psi_list)
    phi_psi_h_list, res_id_to_idx_h = _phi_psi_for_chain(ch_h)
    phi_psi_l_list, res_id_to_idx_l = _phi_psi_for_chain(ch_l)
    for cdr_name in ("H1", "H2", "H3"):
        angles_rad = []
        for r in cdr_res_h.get(cdr_name, []):
            idx = res_id_to_idx_h.get(r.get_id())
            if idx is not None and idx < len(phi_psi_h_list):
                p = phi_psi_h_list[idx]
                if p[0] is not None and p[1] is not None:
                    angles_rad.append(p)
        angles_deg = [(math.degrees(p[0]), math.degrees(p[1])) for p in angles_rad]
        out.canonical_north[cdr_name], out.canonical_north_score[cdr_name] = _north_type(cdr_name, angles_deg)
    for cdr_name in ("L1", "L2", "L3"):
        angles_rad = []
        for r in cdr_res_l.get(cdr_name, []):
            idx = res_id_to_idx_l.get(r.get_id())
            if idx is not None and idx < len(phi_psi_l_list):
                p = phi_psi_l_list[idx]
                if p[0] is not None and p[1] is not None:
                    angles_rad.append(p)
        angles_deg = [(math.degrees(p[0]), math.degrees(p[1])) for p in angles_rad]
        out.canonical_north[cdr_name], out.canonical_north_score[cdr_name] = _north_type(cdr_name, angles_deg)

    # 2. VH/VL angle (principal axis of CA)
    def ca_coords(chain):
        return np.array([r["CA"].coord for r in chain.get_residues() if r.id[0] == " " and "CA" in r])

    ca_h = ca_coords(ch_h)
    ca_l = ca_coords(ch_l)
    if ca_h.shape[0] >= 3 and ca_l.shape[0] >= 3:
        axis_h = _principal_axis_angle_deg(ca_h)
        axis_l = _principal_axis_angle_deg(ca_l)
        out.vh_vl_angle_deg = _angle_between_vectors_deg(axis_h, axis_l)

    _tstep("VH/VL angle")
    # 3. Vernier packing (contact number) — Fv-only atoms to avoid slow full-structure scan
    all_atoms = [a for ch in (ch_h, ch_l) for a in ch.get_atoms() if getattr(a, "element", None) != "H"]
    if not use_lookup:
        vernier_h = _get_residues_at_kabat_positions(num_h, vh_residues, VERNIER_KABAT_VH)
        vernier_l = _get_residues_at_kabat_positions(num_l, vl_residues, VERNIER_KABAT_VL)
    for pos, res in vernier_h.items():
        out.vernier_packing[f"VH_{pos}"] = _contact_number(res, all_atoms)
    for pos, res in vernier_l.items():
        out.vernier_packing[f"VL_{pos}"] = _contact_number(res, all_atoms)

    _tstep("Vernier packing")
    # 4. Vernier ↔ CDR distances
    if not use_lookup:
        cdr_idx_h = _get_cdr_residue_indices(num_h, KABAT_CDR_VH)
        cdr_idx_l = _get_cdr_residue_indices(num_l, KABAT_CDR_VL)
    vernier_residues_h = list(vernier_h.values())
    vernier_residues_l = list(vernier_l.values())

    def min_dist_set_to_set(set_a: List, set_b: List) -> float:
        if not set_a or not set_b:
            return float("nan")
        def _heavy(resList):
            coords = []
            for r in resList:
                for a in r.get_atoms():
                    if getattr(a, "element", None) != "H":
                        coords.append(a.coord)
            return np.array(coords) if coords else np.empty((0, 3))
        ca = _heavy(set_a)
        cb = _heavy(set_b)
        if ca.size == 0 or cb.size == 0:
            return float("nan")
        diff = ca[:, None, :] - cb[None, :, :]
        return float(np.sqrt((diff * diff).sum(axis=-1)).min())

    if not use_lookup:
        cdr_res_h = {name: [vh_residues[i] for i in idxs if i < len(vh_residues)] for name, idxs in cdr_idx_h.items()}
        cdr_res_l = {name: [vl_residues[i] for i in idxs if i < len(vl_residues)] for name, idxs in cdr_idx_l.items()}
    for cdr_name, cdr_res in cdr_res_h.items():
        out.vernier_cdr_distances[f"Vernier_to_{cdr_name}"] = min_dist_set_to_set(vernier_residues_h + vernier_residues_l, cdr_res)
    for cdr_name, cdr_res in cdr_res_l.items():
        if f"Vernier_to_{cdr_name}" not in out.vernier_cdr_distances:
            out.vernier_cdr_distances[f"Vernier_to_{cdr_name}"] = min_dist_set_to_set(vernier_residues_h + vernier_residues_l, cdr_res)
    all_cdr_res = []
    for r in cdr_res_h.values():
        all_cdr_res.extend(r)
    for r in cdr_res_l.values():
        all_cdr_res.extend(r)
    if all_cdr_res:
        out.vernier_cdr_distances["Vernier_to_any_CDR"] = min_dist_set_to_set(vernier_residues_h + vernier_residues_l, all_cdr_res)

    _tstep("Vernier-CDR distances")
    # 5. VH/VL interface
    pairs, dists = _interface_pairs_and_distances(ch_h, ch_l, cutoff=5.5)
    out.interface_n_pairs = len(pairs)
    if dists:
        out.interface_mean_dist_A = float(np.mean(dists))
        out.interface_min_dist_A = float(np.min(dists))

    _tstep("VH/VL interface")
    # 6. Vernier burial (SASA)
    if not skip_sasa and ShrakeRupley is not None:
        try:
            sr = ShrakeRupley(probe_radius=1.4, n_points=960)
            sr.compute(model, level="R")
            total_sasa = 0.0
            for pos, res in vernier_h.items():
                sasa = float(getattr(res, "sasa", 0.0))
                out.vernier_sasa_per_residue[f"VH_{pos}"] = sasa
                total_sasa += sasa
            for pos, res in vernier_l.items():
                sasa = float(getattr(res, "sasa", 0.0))
                out.vernier_sasa_per_residue[f"VL_{pos}"] = sasa
                total_sasa += sasa
            out.vernier_sasa_total = total_sasa
        except Exception as e:
            out.errors.append(f"SASA: {e}")

    return out


def _process_one_pdb(
    payload: Tuple[int, Path, str, str, Optional[Dict[str, Any]], bool],
) -> Tuple[int, Dict[str, Any]]:
    """Top-level for multiprocessing: (index, pdb_path, chain_vh, chain_vl, vernier_lookup, skip_sasa)."""
    i, p, chain_vh, chain_vl, vernier_lookup, skip_sasa = payload
    m = analyze_structure(
        p, chain_vh=chain_vh, chain_vl=chain_vl, vernier_lookup=vernier_lookup, skip_sasa=skip_sasa
    )
    return i, metrics_to_dict(m)


def metrics_to_dict(m: StructureMetrics) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "pdb_path": m.pdb_path,
        "chain_vh": m.chain_vh,
        "chain_vl": m.chain_vl,
        "canonical": m.canonical,
        "canonical_north": m.canonical_north,
        "canonical_north_score": m.canonical_north_score,
        "vh_vl_angle_deg": m.vh_vl_angle_deg,
        "vernier_packing": m.vernier_packing,
        "vernier_cdr_distances": m.vernier_cdr_distances,
        "interface_n_pairs": m.interface_n_pairs,
        "interface_mean_dist_A": m.interface_mean_dist_A,
        "interface_min_dist_A": m.interface_min_dist_A,
        "vernier_sasa_total": m.vernier_sasa_total,
        "vernier_sasa_per_residue": m.vernier_sasa_per_residue,
        "vernier_dual_numbering": m.vernier_dual_numbering,
        "errors": m.errors,
    }
    return d


def main():
    ap = argparse.ArgumentParser(description="Structure-based humanization metrics from VH/VL PDB")
    ap.add_argument("--pdb", default=None, help="Path to single PDB file (Fv or Fab)")
    ap.add_argument("--vh", default="H", help="Chain ID for VH")
    ap.add_argument("--vl", default="L", help="Chain ID for VL")
    ap.add_argument("--out", default=None, help="Output JSON path (default: stdout)")
    ap.add_argument("--dir", default=None, help="If set, process all PDBs in directory and write summary JSON")
    ap.add_argument("--vernier-lookup", default=None, help="JSON from build_vernier_index_lookup.py: reuse ANARCI/IMGT indices, skip ANARCI on PDB")
    ap.add_argument("--skip-sasa", action="store_true", help="Skip SASA (Vernier burial) to speed up batch; metrics JSON will have null SASA fields")
    ap.add_argument("--workers", type=int, default=None, help="Parallel workers for --dir (default: CPU count - 1, min 1)")
    ap.add_argument("--debug-timing", action="store_true", help="Print per-step timing for a single PDB (use with --pdb)")
    args = ap.parse_args()

    vernier_lookup: Optional[Dict[str, Any]] = None
    if args.vernier_lookup:
        path = Path(args.vernier_lookup)
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                vernier_lookup = json.load(f)
            print(f"Loaded vernier lookup: {len(vernier_lookup)} entries", flush=True)
        else:
            print(f"Warning: vernier-lookup file not found: {path}", file=sys.stderr)

    if args.dir:
        pdb_path = Path(args.dir)
        pdbs = sorted(pdb_path.glob("*.pdb"))
        if not pdbs:
            print("No PDB files in directory", file=sys.stderr)
            sys.exit(1)
        n_workers = args.workers
        if n_workers is None:
            n_workers = max(1, (multiprocessing.cpu_count() or 2) - 1)
        n_workers = max(1, n_workers)

        tasks = [
            (i, p, args.vh, args.vl, vernier_lookup, args.skip_sasa)
            for i, p in enumerate(pdbs)
        ]
        results = [None] * len(pdbs)
        if n_workers <= 1:
            for i, p in enumerate(pdbs):
                if (i + 1) % 10 == 0 or i == 0:
                    print(f"Processing {i + 1}/{len(pdbs)}: {p.name}", flush=True)
                _, results[i] = _process_one_pdb(tasks[i])
        else:
            print(f"Using {n_workers} workers", flush=True)
            with multiprocessing.Pool(n_workers) as pool:
                for i, d in pool.imap_unordered(_process_one_pdb, tasks, chunksize=1):
                    results[i] = d
                    done = sum(1 for r in results if r is not None)
                    if done % 50 == 0 or done == 1:
                        print(f"Completed {done}/{len(pdbs)}", flush=True)
        out_path = Path(args.out) if args.out else pdb_path / "structure_metrics_summary.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Wrote {len(results)} metrics to {out_path}")
        return

    pdb_path = Path(args.pdb) if args.pdb else None
    if not pdb_path or not pdb_path.is_file():
        print("Single PDB mode requires --pdb path/to/file.pdb", file=sys.stderr)
        sys.exit(1)

    m = analyze_structure(pdb_path, chain_vh=args.vh, chain_vl=args.vl, vernier_lookup=vernier_lookup,
                          skip_sasa=args.skip_sasa, debug_timing=args.debug_timing)
    d = metrics_to_dict(m)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        print(f"Wrote {out_path}")
    else:
        print(json.dumps(d, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
