"""
IgG Fv structural CMC metrics.

Computes the structural 25-parameter CMC fields that are derivable from an
in-silico H/L Fv PDB. The output keys match regular_ab_developability.py:
psh, ppc, pnc, sfvcsp, interface_n_pairs, interface_mean_dist_A,
interface_min_dist_A, vernier_sasa_total.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HYDRO = {"ALA", "VAL", "ILE", "LEU", "MET", "PHE", "TRP", "PRO", "TYR"}
_POS = {"LYS", "ARG", "HIS"}
_NEG = {"ASP", "GLU"}
_AA1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}


def compute_igg_structural_metrics(
    pdb_path: str,
    vh_seq: str = "",
    vl_seq: str = "",
    vh_chain: str = "H",
    vl_chain: str = "L",
) -> Dict[str, Any]:
    """Return Fv structural CMC metrics from a VH/VL PDB."""
    try:
        import Bio.PDB as bpdb  # type: ignore
        from Bio.PDB.SASA import ShrakeRupley  # type: ignore
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"_struct_cmc_error": f"BioPython SASA unavailable: {exc}"}

    try:
        parser = bpdb.PDBParser(QUIET=True)
        structure = parser.get_structure("fv", str(Path(pdb_path)))
        sr = ShrakeRupley()
        sr.compute(structure, level="R")
        model = structure[0]
        h_res = _aa_residues(model, vh_chain, bpdb)
        l_res = _aa_residues(model, vl_chain, bpdb)
        if not h_res or not l_res:
            return {"_struct_cmc_error": "H/L chains not found or contain no amino-acid residues"}

        all_res = h_res + l_res
        sasa = {(_chain_id(r), _resnum(r)): float(getattr(r, "sasa", 0.0) or 0.0) for r in all_res}

        tap_metrics = _tap_metrics(str(pdb_path), vh_seq, vl_seq, vh_chain, vl_chain)
        psh = tap_metrics.get("psh")
        ppc = tap_metrics.get("ppc")
        pnc = tap_metrics.get("pnc")
        sfvcsp = tap_metrics.get("sfvcsp")
        if psh is None:
            # Fallback only; normal production path should use TAP_Analyzer.
            psh = sum(sasa[(_chain_id(r), _resnum(r))] for r in all_res if r.resname in _HYDRO) * 0.20
        if ppc is None:
            ppc = _max_charge_cluster(all_res, _POS)
        if pnc is None:
            pnc = _max_charge_cluster(all_res, _NEG)
        if sfvcsp is None:
            sfvcsp = _chain_charge(h_res) * _chain_charge(l_res)
        iface = _interface_geometry(h_res, l_res)
        vernier_sasa = _vernier_sasa_total(vh_seq, vl_seq, h_res, l_res)
        vh_vl_angle = _vh_vl_principal_axis_angle(h_res, l_res)

        return {
            "psh": round(psh, 3),
            "ppc": round(ppc, 3),
            "pnc": round(pnc, 3),
            "sfvcsp": round(sfvcsp, 3),
            "interface_n_pairs": iface["interface_n_pairs"],
            "interface_mean_dist_A": iface["interface_mean_dist_A"],
            "interface_min_dist_A": iface["interface_min_dist_A"],
            "vernier_sasa_total": round(vernier_sasa, 3) if vernier_sasa is not None else None,
            "vh_vl_angle_deg": round(vh_vl_angle, 1) if vh_vl_angle is not None else None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"_struct_cmc_error": f"{type(exc).__name__}: {exc}"}


def _vh_vl_principal_axis_angle(h_res: List[Any], l_res: List[Any]) -> Optional[float]:
    """VH/VL principal-axis angle (degrees) using SVD of CA coordinates.

    Mirrors core.humanization.engine._run_abodybuilder2 so saved PDBs can
    recover the same metric without re-running ABodyBuilder2.
    """
    try:
        import numpy as np  # type: ignore
    except Exception:
        return None
    try:
        h_ca = [_ca_coord(r) for r in h_res]
        l_ca = [_ca_coord(r) for r in l_res]
        h_arr = np.asarray([c for c in h_ca if c is not None], dtype=float)
        l_arr = np.asarray([c for c in l_ca if c is not None], dtype=float)
        if h_arr.shape[0] < 3 or l_arr.shape[0] < 3:
            return None
        _, _, vh_vec = np.linalg.svd(h_arr - h_arr.mean(axis=0))
        _, _, vl_vec = np.linalg.svd(l_arr - l_arr.mean(axis=0))
        ah, al = vh_vec[0], vl_vec[0]
        cos_a = float(np.dot(ah, al) / (np.linalg.norm(ah) * np.linalg.norm(al)))
        return float(np.degrees(np.arccos(max(-1.0, min(1.0, cos_a)))))
    except Exception:
        return None


def _aa_residues(model: Any, chain_id: str, bpdb: Any) -> List[Any]:
    if chain_id not in model:
        return []
    return [r for r in model[chain_id] if bpdb.is_aa(r, standard=True)]


def _chain_id(residue: Any) -> str:
    return str(residue.get_parent().id)


def _resnum(residue: Any) -> int:
    return int(residue.id[1])


def _ca_coord(residue: Any) -> Optional[Tuple[float, float, float]]:
    if "CA" not in residue:
        return None
    c = residue["CA"].coord
    return float(c[0]), float(c[1]), float(c[2])


def _dist(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _max_charge_cluster(residues: List[Any], charged_set: set, cutoff: float = 10.0) -> float:
    charged = [(r, _ca_coord(r)) for r in residues if r.resname in charged_set]
    charged = [(r, c) for r, c in charged if c is not None]
    if not charged:
        return 0.0
    best = 0
    for _, c0 in charged:
        n = sum(1 for _, c1 in charged if _dist(c0, c1) <= cutoff)
        best = max(best, n)
    return float(best)


def _chain_charge(residues: List[Any]) -> float:
    return float(sum(1 for r in residues if r.resname in _POS) - sum(1 for r in residues if r.resname in _NEG))


def _tap_metrics(pdb_path: str, vh_seq: str, vl_seq: str, vh_chain: str, vl_chain: str) -> Dict[str, Any]:
    try:
        from core.evaluation.tap import TAP_Analyzer
    except Exception:
        return {}
    cdrs = _cdrs_from_sequences(vh_seq, vl_seq)
    if not cdrs:
        return {}
    try:
        return TAP_Analyzer(pdb_path=pdb_path, vh_chain=vh_chain, vl_chain=vl_chain, cdr_seqs=cdrs).analyze()
    except Exception:
        return {}


def _cdrs_from_sequences(vh_seq: str, vl_seq: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        from core.numbering.imgt_anarcii import imgt_number_anarcii
        from core.vhh_humanization import split_regions
        for prefix, seq in (("H", vh_seq), ("L", vl_seq)):
            if not seq:
                continue
            regions = split_regions(imgt_number_anarcii(seq))
            for idx, cdr_name in enumerate(("CDR1", "CDR2", "CDR3"), start=1):
                val = str(regions.get(cdr_name) or "").replace("-", "")
                if val:
                    out[f"{prefix}{idx}"] = val
    except Exception:
        return {}
    return out


def _min_heavy_atom_distance(a: Any, b: Any) -> Optional[float]:
    best: Optional[float] = None
    for atom_a in a:
        if atom_a.element == "H":
            continue
        ca = atom_a.coord
        for atom_b in b:
            if atom_b.element == "H":
                continue
            cb = atom_b.coord
            d = math.sqrt(float(((ca - cb) ** 2).sum()))
            if best is None or d < best:
                best = d
    return best


def _interface_geometry(h_res: List[Any], l_res: List[Any], cutoff: float = 5.5) -> Dict[str, Any]:
    distances: List[float] = []
    pairs = set()
    for hr in h_res:
        for lr in l_res:
            pair_has_contact = False
            for atom_h in hr:
                if atom_h.element == "H":
                    continue
                ch = atom_h.coord
                for atom_l in lr:
                    if atom_l.element == "H":
                        continue
                    cl = atom_l.coord
                    d = math.sqrt(float(((ch - cl) ** 2).sum()))
                    if d <= cutoff:
                        pair_has_contact = True
                        distances.append(d)
            if pair_has_contact:
                pairs.add((_resnum(hr), _resnum(lr)))
    return {
        "interface_n_pairs": len(pairs),
        "interface_mean_dist_A": round(sum(distances) / len(distances), 4) if distances else None,
        "interface_min_dist_A": round(min(distances), 4) if distances else None,
    }


def _vernier_sasa_total(vh_seq: str, vl_seq: str, h_res: List[Any], l_res: List[Any]) -> Optional[float]:
    try:
        from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys
    except Exception:
        return None

    vernier_vh = {2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94}
    vernier_vl = {2, 4, 36, 46, 49, 69, 71, 98}
    total = 0.0
    observed = 0
    for seq, residues, vset in (
        (vh_seq, h_res, vernier_vh),
        (vl_seq, l_res, vernier_vl),
    ):
        if not seq:
            continue
        try:
            kd = get_kabat_numbering(seq)
            keys = sorted_keys(kd)
        except Exception:
            continue
        for seq_idx, key in enumerate(keys):
            pos, ins = key
            if ins or pos not in vset or seq_idx >= len(residues):
                continue
            total += float(getattr(residues[seq_idx], "sasa", 0.0) or 0.0)
            observed += 1
    return total if observed else None
