#!/usr/bin/env python3
"""
Compute FR3 vernier contact metrics + buriedness (SASA) + overlay (RMSD) for VHH models.

Inputs:
  - data/vhh_clinical_39_union/immunebuilder_models/*/meta.json
  - data/vhh_clinical_39_union/immunebuilder_models/*/rank0_unrefined_contig.pdb

Outputs (written under data/vhh_clinical_39_union/):
  - vhh_fr3_vernier_metrics.json
  - vhh_fr3_vernier_position_summary.csv
  - vhh_fr3_vernier_vhh_summary.csv

Notes:
  - Region boundaries use IMGT (heavy chain):
      CDR1 27-38, CDR2 56-65, FR3 66-104, CDR3 105-117, FR4 118-128
  - PDB is contiguous residue numbering (1..N). We map residue index -> IMGT position using ANARCI (IMGT).
  - "Vernier" here means FR3 residues having any atom within cutoff Å of any CDR atom.
  - Buriedness uses per-residue SASA from freesasa (absolute and relASA). buried = 1 - relASA.
  - Overlay (RMSD) computed by aligning framework backbone atoms (FR1-3) to a reference model (first model),
    then reporting RMSD on FR3 backbone.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
from Bio.PDB import PDBParser, Superimposer  # type: ignore

try:
    import freesasa  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit("freesasa is required in this environment") from e


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "data" / "vhh_clinical_39_union" / "immunebuilder_models"
OUT_DIR = PROJECT_ROOT / "data" / "vhh_clinical_39_union"

OUT_JSON = OUT_DIR / "vhh_fr3_vernier_metrics.json"
OUT_POS_CSV = OUT_DIR / "vhh_fr3_vernier_position_summary.csv"
OUT_VHH_CSV = OUT_DIR / "vhh_fr3_vernier_vhh_summary.csv"

# ANARCI shim (delegates to anarcii)
sys.path.insert(0, str(PROJECT_ROOT / "reports" / "anarci_compat"))
import anarci as anarci_module  # type: ignore


IMGT = {
    "FR1": (1, 26),
    "CDR1": (27, 38),
    "FR2": (39, 55),
    "CDR2": (56, 65),
    "FR3": (66, 104),
    "CDR3": (105, 117),
    "FR4": (118, 128),
}


def is_aa_residue(res) -> bool:
    hetfield, resseq, icode = res.id
    return hetfield == " " and isinstance(resseq, int)


def get_imgt_numbering(seq: str):
    numbered, _, _ = anarci_module.anarci([("q", seq)], scheme="imgt", output=False)
    # shim returns [[numbering_list]] for first sequence
    return numbered[0][0][0]


def build_idx_to_imgtpos(numbering_list) -> Dict[int, int]:
    """
    numbering_list: [((pos, ins), aa), ...] including '-' gaps.
    Returns: map from contiguous residue index (1..N residues) to IMGT position (int).
    """
    m: Dict[int, int] = {}
    idx = 0
    for (pos, _ins), aa in numbering_list:
        if aa == "-":
            continue
        idx += 1
        m[idx] = int(pos)
    return m


def region_mask(idx_to_pos: Dict[int, int], lo: int, hi: int) -> List[int]:
    return [idx for idx, pos in idx_to_pos.items() if lo <= pos <= hi]


def atoms_for_residue(res) -> List:
    # Include all heavy atoms + H if present; simplest: all atoms
    return list(res.get_atoms())


def is_hydrogen_atom(atom) -> bool:
    try:
        el = (atom.element or "").upper()
        if el == "H":
            return True
    except Exception:
        pass
    name = (getattr(atom, "get_name", lambda: "")() or "").upper()
    return name.startswith("H")


def heavy_atom_coords_by_residue(idx_to_res: Dict[int, object]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build arrays for neighbor search.
    Returns:
      coords: (N,3) float32
      res_idx: (N,) int32  residue index (contig)
    """
    coords: List[np.ndarray] = []
    res_idx: List[int] = []
    for idx, res in idx_to_res.items():
        for a in res.get_atoms():
            if is_hydrogen_atom(a):
                continue
            coords.append(a.get_coord().astype(np.float32))
            res_idx.append(int(idx))
    if not coords:
        return np.zeros((0, 3), dtype=np.float32), np.zeros((0,), dtype=np.int32)
    return np.stack(coords, axis=0), np.array(res_idx, dtype=np.int32)


def packing_counts_for_residue(
    *,
    target_idx: int,
    coords: np.ndarray,
    res_idx: np.ndarray,
    is_cdr_residue: Dict[int, bool],
    radius_A: float,
) -> Dict[str, int]:
    """
    Neighbor/crowding metric:
      - counts of neighbor atoms within radius
      - counts of unique neighbor residues within radius
    Split by whether neighbor residue is CDR vs framework.
    """
    r2 = float(radius_A * radius_A)
    target_mask = res_idx == target_idx
    if not np.any(target_mask):
        return {
            "pack_atom_total": 0,
            "pack_atom_cdr": 0,
            "pack_atom_fr": 0,
            "pack_res_total": 0,
            "pack_res_cdr": 0,
            "pack_res_fr": 0,
        }
    target_coords = coords[target_mask]  # (M,3)
    # Boolean mask over all atoms: within radius of any target atom
    within = np.zeros((coords.shape[0],), dtype=bool)
    for tc in target_coords:
        d2 = np.sum((coords - tc) ** 2, axis=1)
        within |= (d2 <= r2)
    # exclude self atoms
    within &= ~target_mask

    neigh_atom_total = int(np.count_nonzero(within))
    neigh_res = np.unique(res_idx[within]).astype(int)
    neigh_res_total = int(neigh_res.size)

    # Split CDR vs FR at residue level
    neigh_res_cdr = sum(1 for i in neigh_res if is_cdr_residue.get(int(i), False))
    neigh_res_fr = neigh_res_total - neigh_res_cdr

    # Split CDR vs FR at atom level (approx by residue label of atom)
    neigh_atom_cdr = 0
    if neigh_atom_total:
        neigh_atom_cdr = int(
            np.count_nonzero(
                [is_cdr_residue.get(int(i), False) for i in res_idx[within].tolist()]
            )
        )
    neigh_atom_fr = neigh_atom_total - neigh_atom_cdr

    return {
        "pack_atom_total": neigh_atom_total,
        "pack_atom_cdr": int(neigh_atom_cdr),
        "pack_atom_fr": int(neigh_atom_fr),
        "pack_res_total": neigh_res_total,
        "pack_res_cdr": int(neigh_res_cdr),
        "pack_res_fr": int(neigh_res_fr),
    }

def min_distance_between_residues(res_a, res_b) -> float:
    # brute force: small proteins, ok
    a_atoms = atoms_for_residue(res_a)
    b_atoms = atoms_for_residue(res_b)
    if not a_atoms or not b_atoms:
        return float("inf")
    min_d2 = float("inf")
    for aa in a_atoms:
        pa = aa.get_coord()
        for bb in b_atoms:
            pb = bb.get_coord()
            d2 = float(np.sum((pa - pb) ** 2))
            if d2 < min_d2:
                min_d2 = d2
    return float(math.sqrt(min_d2))


def backbone_atoms(res) -> List:
    out = []
    for name in ("N", "CA", "C"):
        if name in res:
            out.append(res[name])
    return out


def compute_sasa_by_residue(pdb_path: Path) -> Dict[Tuple[str, int], Dict[str, float]]:
    """
    Returns per-residue SASA for chain+resseq in the PDB.
    Uses freesasa's built-in residue areas and relative areas if available.
    """
    # freesasa works from filename
    structure = freesasa.Structure(str(pdb_path))
    result = freesasa.calc(structure)
    areas = result.residueAreas()

    out: Dict[Tuple[str, int], Dict[str, float]] = {}
    # areas[chain][resnum] has .total and .relativeTotal
    for chain_id, chain_map in areas.items():
        for resnum, a in chain_map.items():
            try:
                out[(str(chain_id), int(resnum))] = {
                    "sasa": float(a.total),
                    "rel_sasa": float(getattr(a, "relativeTotal", float("nan"))),
                }
            except Exception:
                continue
    return out


@dataclass
class VhhModel:
    name: str
    pdb_path: Path
    seq: str
    idx_to_pos: Dict[int, int]  # residue index in contig PDB -> IMGT pos


def load_models() -> List[VhhModel]:
    models: List[VhhModel] = []
    for d in sorted(MODELS_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / "meta.json"
        pdb_path = d / "rank0_unrefined_contig.pdb"
        if not meta_path.exists() or not pdb_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        seq = (meta.get("sequence") or "").strip().upper()
        name = str(meta.get("name") or d.name)
        if not seq:
            continue
        num = get_imgt_numbering(seq)
        idx_to_pos = build_idx_to_imgtpos(num)
        models.append(VhhModel(name=name, pdb_path=pdb_path, seq=seq, idx_to_pos=idx_to_pos))
    if not models:
        raise SystemExit(f"No models found under: {MODELS_DIR}")
    return models


def parse_chain_residues(pdb_path: Path, chain_id: str = "H") -> List:
    parser = PDBParser(QUIET=True)
    struct = parser.get_structure("vhh", str(pdb_path))
    # Assume first model
    model = next(struct.get_models())
    chain = model[chain_id] if chain_id in model else next(model.get_chains())
    residues = [r for r in chain.get_residues() if is_aa_residue(r)]
    return residues


def main(cutoff_A: float = 4.0, packing_radius_A: float = 6.0) -> None:
    models = load_models()
    print(f"Loaded {len(models)} VHH models")

    # reference for overlay
    ref = models[0]
    ref_residues = parse_chain_residues(ref.pdb_path, chain_id="H")
    ref_idx_to_res = {i + 1: r for i, r in enumerate(ref_residues)}

    # Precompute reference framework atoms for alignment (FR1-3 backbone)
    ref_framework_idxs = region_mask(ref.idx_to_pos, IMGT["FR1"][0], IMGT["FR3"][1])
    ref_framework_atoms = []
    for idx in ref_framework_idxs:
        res = ref_idx_to_res.get(idx)
        if res is None:
            continue
        ref_framework_atoms.extend(backbone_atoms(res))

    # Accumulators for position-level summary on FR3
    pos_contact_counts = defaultdict(int)  # IMGT pos -> number of VHH where pos has any CDR contact
    pos_buried_sum = defaultdict(float)  # IMGT pos -> sum(buriedness)
    pos_buried_n = defaultdict(int)
    pos_min_dist_sum = defaultdict(float)
    pos_min_dist_n = defaultdict(int)
    pos_pack_res_total_sum = defaultdict(float)
    pos_pack_res_cdr_sum = defaultdict(float)
    pos_pack_res_fr_sum = defaultdict(float)
    pos_pack_atom_total_sum = defaultdict(float)
    pos_pack_atom_cdr_sum = defaultdict(float)
    pos_pack_atom_fr_sum = defaultdict(float)
    pos_pack_n = defaultdict(int)

    vhh_rows = []
    all_details = []

    for m in models:
        residues = parse_chain_residues(m.pdb_path, chain_id="H")
        idx_to_res = {i + 1: r for i, r in enumerate(residues)}

        # SASA
        sasa_map = compute_sasa_by_residue(m.pdb_path)
        # map contig residue index -> SASA using chain/resseq; contig resseq starts at 1
        # we assume chain id is 'H' in contig pdb; if not, try first chain later
        chain_id_guess = "H"
        if (chain_id_guess, 1) not in sasa_map:
            # try to detect first chain id
            # take first key in sasa_map
            if sasa_map:
                chain_id_guess = next(iter(sasa_map.keys()))[0]

        # CDR residue indices (for distance)
        cdr_idxs = (
            region_mask(m.idx_to_pos, *IMGT["CDR1"])
            + region_mask(m.idx_to_pos, *IMGT["CDR2"])
            + region_mask(m.idx_to_pos, *IMGT["CDR3"])
        )
        cdr_res = [idx_to_res[i] for i in cdr_idxs if i in idx_to_res]

        fr3_idxs = region_mask(m.idx_to_pos, *IMGT["FR3"])
        framework_idxs = region_mask(m.idx_to_pos, IMGT["FR1"][0], IMGT["FR4"][1])

        # Packing neighbor search arrays (heavy atoms only)
        coords, atom_res_idx = heavy_atom_coords_by_residue(idx_to_res)
        cdr_idx_set = set(cdr_idxs)
        is_cdr_residue = {idx: (idx in cdr_idx_set) for idx in framework_idxs}

        # overlay: align framework backbone to reference, then compute FR3 RMSD
        sup = Superimposer()
        mob_framework_atoms = []
        for idx in region_mask(m.idx_to_pos, IMGT["FR1"][0], IMGT["FR3"][1]):
            res = idx_to_res.get(idx)
            if res is None:
                continue
            mob_framework_atoms.extend(backbone_atoms(res))

        # Need equal lengths for Superimposer; take min prefix
        n_atoms = min(len(ref_framework_atoms), len(mob_framework_atoms))
        if n_atoms >= 3:
            sup.set_atoms(ref_framework_atoms[:n_atoms], mob_framework_atoms[:n_atoms])
            # apply to all atoms for consistent distances (optional)
            sup.apply([a for a in next(PDBParser(QUIET=True).get_structure("x", str(m.pdb_path)).get_models()).get_atoms()])

        # compute FR3 backbone RMSD using corresponding indices after alignment (use original residues coords already moved? sup.apply used new struct)
        # Simpler: compute RMSD on framework atoms using sup.rms and then separately compute FR3 rms by re-superimposing on FR3 atoms:
        # We'll compute FR3-only RMSD by another superimpose call.
        ref_fr3_atoms = []
        mob_fr3_atoms = []
        for idx in fr3_idxs:
            rr = ref_idx_to_res.get(idx)
            mr = idx_to_res.get(idx)
            if rr is None or mr is None:
                continue
            ref_fr3_atoms.extend(backbone_atoms(rr))
            mob_fr3_atoms.extend(backbone_atoms(mr))
        fr3_rmsd = None
        n2 = min(len(ref_fr3_atoms), len(mob_fr3_atoms))
        if n2 >= 3:
            sup2 = Superimposer()
            sup2.set_atoms(ref_fr3_atoms[:n2], mob_fr3_atoms[:n2])
            fr3_rmsd = float(sup2.rms)

        # Per-FR3 residue metrics
        fr3_contact_positions = 0
        fr3_buried_vals = []
        fr3_min_dists = []
        fr3_pack_res_total = []
        fr3_pack_res_cdr = []
        fr3_pack_res_fr = []
        fr3_pack_atom_total = []
        fr3_pack_atom_cdr = []
        fr3_pack_atom_fr = []
        details = []

        for idx in fr3_idxs:
            res = idx_to_res.get(idx)
            if res is None:
                continue
            imgt_pos = m.idx_to_pos.get(idx)
            if imgt_pos is None:
                continue

            # min distance to any CDR residue
            min_d = float("inf")
            for cr in cdr_res:
                d = min_distance_between_residues(res, cr)
                if d < min_d:
                    min_d = d

            is_contact = min_d <= cutoff_A
            if is_contact:
                fr3_contact_positions += 1
                pos_contact_counts[imgt_pos] += 1

            # buriedness from SASA (per residue resseq)
            # contig resseq is idx; icode blank
            sasa_rec = sasa_map.get((chain_id_guess, idx))
            rel_sasa = float("nan") if not sasa_rec else float(sasa_rec.get("rel_sasa", float("nan")))
            sasa_abs = float("nan") if not sasa_rec else float(sasa_rec.get("sasa", float("nan")))
            buried = None
            if not math.isnan(rel_sasa):
                buried = float(max(0.0, min(1.0, 1.0 - rel_sasa)))
                pos_buried_sum[imgt_pos] += buried
                pos_buried_n[imgt_pos] += 1
                fr3_buried_vals.append(buried)

            pos_min_dist_sum[imgt_pos] += min_d
            pos_min_dist_n[imgt_pos] += 1
            fr3_min_dists.append(min_d)

            # packing / crowding
            pack = packing_counts_for_residue(
                target_idx=idx,
                coords=coords,
                res_idx=atom_res_idx,
                is_cdr_residue=is_cdr_residue,
                radius_A=packing_radius_A,
            )
            fr3_pack_res_total.append(pack["pack_res_total"])
            fr3_pack_res_cdr.append(pack["pack_res_cdr"])
            fr3_pack_res_fr.append(pack["pack_res_fr"])
            fr3_pack_atom_total.append(pack["pack_atom_total"])
            fr3_pack_atom_cdr.append(pack["pack_atom_cdr"])
            fr3_pack_atom_fr.append(pack["pack_atom_fr"])

            pos_pack_res_total_sum[imgt_pos] += pack["pack_res_total"]
            pos_pack_res_cdr_sum[imgt_pos] += pack["pack_res_cdr"]
            pos_pack_res_fr_sum[imgt_pos] += pack["pack_res_fr"]
            pos_pack_atom_total_sum[imgt_pos] += pack["pack_atom_total"]
            pos_pack_atom_cdr_sum[imgt_pos] += pack["pack_atom_cdr"]
            pos_pack_atom_fr_sum[imgt_pos] += pack["pack_atom_fr"]
            pos_pack_n[imgt_pos] += 1

            details.append(
                {
                    "idx": idx,
                    "imgt_pos": imgt_pos,
                    "aa": res.get_resname(),
                    "min_dist_to_cdr": float(min_d),
                    "contact": bool(is_contact),
                    "sasa": sasa_abs,
                    "rel_sasa": rel_sasa,
                    "buried": buried,
                    "packing_radius_A": packing_radius_A,
                    **pack,
                }
            )

        vhh_rows.append(
            {
                "name": m.name,
                "fr3_contact_positions": fr3_contact_positions,
                "fr3_contact_fraction": fr3_contact_positions / max(1, len(fr3_idxs)),
                "fr3_buried_mean": (sum(fr3_buried_vals) / len(fr3_buried_vals)) if fr3_buried_vals else None,
                "fr3_min_dist_mean": (sum(fr3_min_dists) / len(fr3_min_dists)) if fr3_min_dists else None,
                "fr3_pack_res_total_mean": (sum(fr3_pack_res_total) / len(fr3_pack_res_total)) if fr3_pack_res_total else None,
                "fr3_pack_res_cdr_mean": (sum(fr3_pack_res_cdr) / len(fr3_pack_res_cdr)) if fr3_pack_res_cdr else None,
                "fr3_pack_res_fr_mean": (sum(fr3_pack_res_fr) / len(fr3_pack_res_fr)) if fr3_pack_res_fr else None,
                "fr3_pack_atom_total_mean": (sum(fr3_pack_atom_total) / len(fr3_pack_atom_total)) if fr3_pack_atom_total else None,
                "fr3_pack_atom_cdr_mean": (sum(fr3_pack_atom_cdr) / len(fr3_pack_atom_cdr)) if fr3_pack_atom_cdr else None,
                "fr3_pack_atom_fr_mean": (sum(fr3_pack_atom_fr) / len(fr3_pack_atom_fr)) if fr3_pack_atom_fr else None,
                "fr3_rmsd_to_ref": fr3_rmsd,
                "pdb": str(m.pdb_path),
            }
        )
        all_details.append({"name": m.name, "cutoff_A": cutoff_A, "packing_radius_A": packing_radius_A, "fr3_details": details})

    # Position summary (FR3)
    fr3_positions = list(range(IMGT["FR3"][0], IMGT["FR3"][1] + 1))
    pos_rows = []
    for p in fr3_positions:
        pos_rows.append(
            {
                "imgt_pos": p,
                "contact_freq": pos_contact_counts[p] / len(models),
                "contact_n": pos_contact_counts[p],
                "buried_mean": (pos_buried_sum[p] / pos_buried_n[p]) if pos_buried_n[p] else None,
                "min_dist_mean": (pos_min_dist_sum[p] / pos_min_dist_n[p]) if pos_min_dist_n[p] else None,
                "pack_res_total_mean": (pos_pack_res_total_sum[p] / pos_pack_n[p]) if pos_pack_n[p] else None,
                "pack_res_cdr_mean": (pos_pack_res_cdr_sum[p] / pos_pack_n[p]) if pos_pack_n[p] else None,
                "pack_res_fr_mean": (pos_pack_res_fr_sum[p] / pos_pack_n[p]) if pos_pack_n[p] else None,
                "pack_atom_total_mean": (pos_pack_atom_total_sum[p] / pos_pack_n[p]) if pos_pack_n[p] else None,
                "pack_atom_cdr_mean": (pos_pack_atom_cdr_sum[p] / pos_pack_n[p]) if pos_pack_n[p] else None,
                "pack_atom_fr_mean": (pos_pack_atom_fr_sum[p] / pos_pack_n[p]) if pos_pack_n[p] else None,
            }
        )

    OUT_JSON.write_text(
        json.dumps(
            {
                "n_models": len(models),
                "cutoff_A": cutoff_A,
                "packing_radius_A": packing_radius_A,
                "imgt_regions": {k: list(v) for k, v in IMGT.items()},
                "vhh_summary": vhh_rows,
                "fr3_position_summary": pos_rows,
                "details": all_details,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # CSVs
    with OUT_VHH_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "name",
                "fr3_contact_positions",
                "fr3_contact_fraction",
                "fr3_buried_mean",
                "fr3_min_dist_mean",
                "fr3_pack_res_total_mean",
                "fr3_pack_res_cdr_mean",
                "fr3_pack_res_fr_mean",
                "fr3_pack_atom_total_mean",
                "fr3_pack_atom_cdr_mean",
                "fr3_pack_atom_fr_mean",
                "fr3_rmsd_to_ref",
                "pdb",
            ],
        )
        w.writeheader()
        for r in vhh_rows:
            w.writerow(r)

    # Position CSV with packing columns
    with OUT_POS_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "imgt_pos",
                "contact_freq",
                "contact_n",
                "buried_mean",
                "min_dist_mean",
                "pack_res_total_mean",
                "pack_res_cdr_mean",
                "pack_res_fr_mean",
                "pack_atom_total_mean",
                "pack_atom_cdr_mean",
                "pack_atom_fr_mean",
            ],
        )
        w.writeheader()
        for r in pos_rows:
            w.writerow(r)

    print(f"Wrote: {OUT_JSON}")
    print(f"Wrote: {OUT_VHH_CSV}")
    print(f"Wrote: {OUT_POS_CSV}")


if __name__ == "__main__":
    main()

