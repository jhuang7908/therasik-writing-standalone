"""
Structure-guided protection for DeepFR-CTX-Pet (VH/VL + antigen complex).

Maps Boltz/AF3-class PDB contacts to Kabat positions and returns:
  - locked positions (never substitute)
  - CTX-eligible positions (surface FR, non-interface)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.humanization.kabat_utils import is_in_cdr

try:
    from Bio.PDB import PDBParser
    from Bio.PDB.Polypeptide import is_aa
    from Bio.PDB.SASA import ShrakeRupley
    from Bio.SeqUtils import seq1
except ImportError:
    PDBParser = None  # type: ignore

try:
    import anarci
except ImportError:
    anarci = None

_MAX_SASA_AA = {
    "A": 121.0, "R": 265.0, "N": 187.0, "D": 187.0, "C": 148.0,
    "E": 214.0, "Q": 214.0, "G": 97.0, "H": 216.0, "I": 195.0,
    "L": 191.0, "K": 230.0, "M": 203.0, "F": 228.0, "P": 154.0,
    "S": 143.0, "T": 163.0, "W": 264.0, "Y": 255.0, "V": 165.0,
}

KABAT_CDR_VH = {"H1": (26, 35), "H2": (50, 65), "H3": (95, 102)}
KABAT_CDR_VL = {"L1": (24, 34), "L2": (50, 56), "L3": (89, 97)}


def _chain_seq_residues(chain) -> Tuple[str, list]:
    seq, residues = [], []
    for r in chain.get_residues():
        if not is_aa(r, standard=True):
            continue
        try:
            aa = seq1(r.resname)
        except Exception:
            continue
        seq.append(aa)
        residues.append(r)
    return "".join(seq), residues


def _kabat_numbering(seq: str, chain_label: str) -> List[Tuple[Tuple[int, str], str]]:
    scheme_chain = "H" if chain_label == "VH" else "L"
    numbered, _, _ = anarci.anarci([(scheme_chain, seq)], scheme="kabat")
    if not numbered or not numbered[0] or not numbered[0][0]:
        raise RuntimeError(f"ANARCI failed for {chain_label}")
    return numbered[0][0][0]


def _cdr_ca_atoms(numbering: List, residues: list, chain_label: str) -> list:
    cdr_ranges = KABAT_CDR_VH if chain_label == "VH" else KABAT_CDR_VL
    atoms = []
    for idx, ((pos, ins), aa) in enumerate(numbering):
        if aa == "-" or idx >= len(residues):
            continue
        for lo, hi in cdr_ranges.values():
            if lo <= pos <= hi and "CA" in residues[idx]:
                atoms.append(residues[idx]["CA"])
                break
    return atoms


def _heavy_atoms(chain_ids: Set[str], model) -> list:
    atoms = []
    for cid in chain_ids:
        if cid not in model:
            continue
        for r in model[cid].get_residues():
            if r.id[0] != " ":
                continue
            for a in r.get_atoms():
                if a.element != "H":
                    atoms.append(a)
    return atoms


def _min_dist(atom, others: list) -> float:
    if not others or atom is None:
        return float("inf")
    best = float("inf")
    for o in others:
        d = float(atom - o)
        if d < best:
            best = d
    return best


def compute_structure_protection(
    pdb_path: Path,
    chain_id: str,
    chain_label: str,
    *,
    antigen_chain_ids: Tuple[str, ...] = ("A",),
    fv_partner_chain_id: Optional[str] = None,
    interface_cutoff_A: float = 4.5,
    cdr_proximity_A: float = 5.0,
    buried_rsa_threshold: float = 0.05,
    min_rsa_for_ctx: float = 0.12,
) -> Dict[str, Any]:
    """
    Per-chain structural protection report keyed by Kabat position.

    locked_kabat: FR positions that must not be mutated
    ctx_eligible_kabat: FR positions allowed for 9-mer voting (surface, non-interface)
    """
    out: Dict[str, Any] = {
        "pdb": str(pdb_path),
        "chain_id": chain_id,
        "chain_label": chain_label,
        "locked_kabat": set(),
        "ctx_eligible_kabat": set(),
        "reasons": {},
        "errors": [],
    }
    if PDBParser is None or anarci is None:
        out["errors"].append("BioPython or ANARCI unavailable")
        return out

    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("complex", str(pdb_path))
    model = structure[0]
    if chain_id not in model:
        out["errors"].append(f"Chain {chain_id!r} missing")
        return out

    ch = model[chain_id]
    seq, residues = _chain_seq_residues(ch)
    numbering = _kabat_numbering(seq, chain_label)
    cdr_ca = _cdr_ca_atoms(numbering, residues, chain_label)

    antigen_atoms = _heavy_atoms(set(antigen_chain_ids), model)
    partner_atoms = _heavy_atoms({fv_partner_chain_id}, model) if fv_partner_chain_id else []

    sr = ShrakeRupley(probe_radius=1.4, n_points=960)
    sr.compute(structure, level="R")

    locked: Set[int] = set()
    eligible: Set[int] = set()
    reasons: Dict[int, List[str]] = {}

    def _tag(pos: int, reason: str) -> None:
        locked.add(pos)
        reasons.setdefault(pos, []).append(reason)

    for idx, ((pos, ins), aa) in enumerate(numbering):
        if aa == "-" or idx >= len(residues) or is_in_cdr(pos, chain_label):
            continue
        ins_code = ins if ins not in (None, " ", "") else ""
        r = residues[idx]
        sasa = float(getattr(r, "sasa", 0.0))
        max_a = _MAX_SASA_AA.get(aa, 150.0)
        rsa = sasa / max_a if max_a else 0.0
        ca = r["CA"] if "CA" in r else None

        d_ag = _min_dist(ca, antigen_atoms)
        d_partner = _min_dist(ca, partner_atoms)
        d_cdr = _min_dist(ca, cdr_ca)

        if rsa < buried_rsa_threshold:
            _tag(pos, "buried")
        if d_ag < interface_cutoff_A:
            _tag(pos, "antigen_interface")
        if d_partner < interface_cutoff_A:
            _tag(pos, "fv_interface")
        if d_cdr < cdr_proximity_A:
            _tag(pos, "cdr_proximal")

        if pos not in locked and rsa >= min_rsa_for_ctx and d_cdr >= cdr_proximity_A:
            eligible.add(pos)

    # Eligible must not overlap locked
    eligible -= locked

    out["locked_kabat"] = locked
    out["ctx_eligible_kabat"] = eligible
    out["reasons"] = {str(k): v for k, v in sorted(reasons.items())}
    out["summary"] = {
        "n_fr_locked": len(locked),
        "n_fr_ctx_eligible": len(eligible),
        "antigen_chain_ids": list(antigen_chain_ids),
        "fv_partner_chain_id": fv_partner_chain_id,
    }
    return out


def load_protection_from_qc_json(qc_path: Path) -> Dict[str, Set[int]]:
    """Optional: parse precomputed interface lists from structure QC JSON."""
    data = json.loads(qc_path.read_text(encoding="utf-8"))
    # PDB resnum -> needs Kabat mapping externally; prefer live PDB analysis
    return {}
