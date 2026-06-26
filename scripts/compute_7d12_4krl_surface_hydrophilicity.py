"""
Compute structure-based surface hydrophilicity for 7D12 (PDB 4KRL, chain B).

Goal:
- Compute per-residue SASA (Shrake–Rupley) and derive surface residues.
- Compute per-residue hydrophilicity (Kyte–Doolittle; hydrophilicity = -hydropathy).
- Identify surface hydrophilic patches.
- Map SR mutation IMGT positions onto structural surface metrics as evidence that SR targets surface residues.

Outputs:
- output/7D12/7d12_4krl_per_residue_surface_metrics.csv
- output/7D12/7d12_4krl_surface_hydrophilicity.md
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PDB_PATH = PROJECT_ROOT / "output" / "7D12" / "4KRL.pdb"
MUT_JSONL = PROJECT_ROOT / "output" / "7D12" / "7d12_4krl_variant_mutations.jsonl"
OUT_CSV = PROJECT_ROOT / "output" / "7D12" / "7d12_4krl_per_residue_surface_metrics.csv"
OUT_MD = PROJECT_ROOT / "output" / "7D12" / "7d12_4krl_surface_hydrophilicity.md"


# ANARCII IMGT numbering wrapper (already in repo)
import sys

sys.path.append(str(PROJECT_ROOT))
from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed  # noqa: E402


AA3_TO_AA1: Dict[str, str] = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}

# Kyte–Doolittle hydropathy (higher => more hydrophobic)
KD: Dict[str, float] = {
    "A": 1.8,
    "R": -4.5,
    "N": -3.5,
    "D": -3.5,
    "C": 2.5,
    "Q": -3.5,
    "E": -3.5,
    "G": -0.4,
    "H": -3.2,
    "I": 4.5,
    "L": 3.8,
    "K": -3.9,
    "M": 1.9,
    "F": 2.8,
    "P": -1.6,
    "S": -0.8,
    "T": -0.7,
    "W": -0.9,
    "Y": -1.3,
    "V": 4.2,
}

# Approximate max ASA (Å^2) for relative SASA (Tien et al. / commonly used values)
MAX_ASA: Dict[str, float] = {
    "A": 121.0,
    "R": 265.0,
    "N": 187.0,
    "D": 187.0,
    "C": 148.0,
    "Q": 214.0,
    "E": 214.0,
    "G": 97.0,
    "H": 216.0,
    "I": 195.0,
    "L": 191.0,
    "K": 230.0,
    "M": 203.0,
    "F": 228.0,
    "P": 154.0,
    "S": 143.0,
    "T": 163.0,
    "W": 264.0,
    "Y": 255.0,
    "V": 165.0,
}

# Simple vdW radii (Å) by element for SASA; probe will be added.
VDW: Dict[str, float] = {
    "H": 1.20,
    "C": 1.70,
    "N": 1.55,
    "O": 1.52,
    "S": 1.80,
    "P": 1.80,
    "SE": 1.90,
}


@dataclass(frozen=True)
class Atom:
    element: str
    coord: np.ndarray  # (3,)
    res_key: Tuple[int, str]  # (resseq, icode)
    resname: str
    atom_name: str


def _infer_element(atom_name: str, element_field: str) -> str:
    e = (element_field or "").strip().upper()
    if e:
        return e
    a = (atom_name or "").strip()
    if not a:
        return ""
    # Handle e.g. " CA " vs "CA" (alpha carbon): element should be C, not CA.
    # PDB convention: element is right-justified; if missing, infer from first char.
    first = a[0].upper()
    if first.isalpha():
        return first
    return ""


def parse_pdb_chain_atoms(pdb_path: Path, chain_id: str) -> Tuple[List[Atom], List[Tuple[int, str, str]]]:
    """
    Returns:
    - atoms for the chain (standard AA residues only)
    - residues list in order: (resseq, icode, aa1)
    """
    if not pdb_path.exists():
        raise FileNotFoundError(f"Missing PDB: {pdb_path}")

    atoms: List[Atom] = []
    residues_order: List[Tuple[int, str, str]] = []
    seen_res: set[Tuple[int, str]] = set()

    for line in pdb_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("ATOM"):
            continue
        ch = line[21:22]
        if ch != chain_id:
            continue

        resname = line[17:20].strip().upper()
        aa1 = AA3_TO_AA1.get(resname)
        if aa1 is None:
            continue  # skip non-standard residues for this analysis

        atom_name = line[12:16].strip()
        resseq = int(line[22:26])
        icode = line[26:27].strip() or ""
        x = float(line[30:38])
        y = float(line[38:46])
        z = float(line[46:54])
        element = _infer_element(atom_name, line[76:78] if len(line) >= 78 else "")

        res_key = (resseq, icode)
        if res_key not in seen_res:
            residues_order.append((resseq, icode, aa1))
            seen_res.add(res_key)

        atoms.append(
            Atom(
                element=element,
                coord=np.array([x, y, z], dtype=float),
                res_key=res_key,
                resname=resname,
                atom_name=atom_name,
            )
        )

    if not atoms:
        raise RuntimeError(f"No atoms parsed for chain {chain_id} in {pdb_path}")
    return atoms, residues_order


def fibonacci_sphere(n: int) -> np.ndarray:
    """
    Even-ish points on unit sphere using Fibonacci lattice.
    Returns (n,3).
    """
    i = np.arange(n, dtype=float)
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    theta = 2.0 * math.pi * i / phi
    z = 1.0 - (2.0 * i + 1.0) / n
    r = np.sqrt(np.clip(1.0 - z * z, 0.0, 1.0))
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return np.stack([x, y, z], axis=1)


def compute_sasa_shrake_rupley(
    coords: np.ndarray,
    radii: np.ndarray,
    probe_radius: float = 1.4,
    n_sphere_points: int = 200,
) -> np.ndarray:
    """
    Shrake–Rupley SASA per atom.
    - coords: (N,3)
    - radii: (N,) vdW radii (without probe)
    Returns atom_sasa: (N,) in Å^2
    """
    n_atoms = coords.shape[0]
    if n_atoms == 0:
        return np.array([], dtype=float)

    # Effective radii include probe.
    r_eff = radii + probe_radius
    max_r_eff = float(np.max(r_eff))
    sphere = fibonacci_sphere(n_sphere_points)  # (P,3)

    tree = cKDTree(coords)
    sasa = np.zeros(n_atoms, dtype=float)

    for i in range(n_atoms):
        center = coords[i]
        ri = float(r_eff[i])
        # Candidate neighbor atoms that could occlude points on this atom
        neigh = tree.query_ball_point(center, ri + max_r_eff)
        # Remove self
        neigh = [j for j in neigh if j != i]

        pts = center[None, :] + ri * sphere  # (P,3)
        if not neigh:
            acc = np.ones(n_sphere_points, dtype=bool)
        else:
            nb_coords = coords[np.array(neigh, dtype=int)]
            nb_r = r_eff[np.array(neigh, dtype=int)]
            # dist^2: (P, M)
            diff = pts[:, None, :] - nb_coords[None, :, :]
            dist2 = np.einsum("pmn,pmn->pm", diff, diff)
            occluded = (dist2 < (nb_r[None, :] ** 2)).any(axis=1)
            acc = ~occluded

        area = 4.0 * math.pi * (ri ** 2)
        sasa[i] = float(acc.sum()) / float(n_sphere_points) * area

    return sasa


def load_sr_mutations(jsonl_path: Path) -> List[Dict[str, object]]:
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Missing mutation JSONL: {jsonl_path}")
    muts: List[Dict[str, object]] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if obj.get("variant") == "sr":
            muts.append(obj)
    return muts


def main() -> None:
    # 1) Parse nanobody chain (B)
    chain_id = "B"
    atoms, residues = parse_pdb_chain_atoms(PDB_PATH, chain_id=chain_id)

    # Build chain sequence in residue order
    seq = "".join(aa1 for _, _, aa1 in residues)
    if len(seq) < 80:
        raise RuntimeError(f"Unexpectedly short chain sequence (len={len(seq)}) for chain {chain_id}")

    # 2) IMGT mapping via ANARCII
    numbered = imgt_number_anarcii_indexed(seq)
    seqidx_to_imgt: Dict[int, int] = {}
    for r in numbered["rows"]:
        pos = str(r["pos"])
        if pos.isdigit():
            seqidx_to_imgt[int(r["seq_idx"])] = int(pos)

    # 3) Atom-level SASA
    coords = np.stack([a.coord for a in atoms], axis=0)
    elements = [a.element.upper() for a in atoms]
    vdw_r = np.array([VDW.get(e, VDW.get("C")) for e in elements], dtype=float)
    atom_sasa = compute_sasa_shrake_rupley(coords, vdw_r, probe_radius=1.4, n_sphere_points=200)

    # 4) Residue-level aggregation
    # Map residue key -> seq_idx (by residue order)
    reskey_to_seqidx: Dict[Tuple[int, str], int] = {}
    for idx, (resseq, icode, _) in enumerate(residues):
        reskey_to_seqidx[(resseq, icode)] = idx

    # Sum SASA per residue
    res_sasa = np.zeros(len(residues), dtype=float)
    for a, sasa in zip(atoms, atom_sasa):
        si = reskey_to_seqidx.get(a.res_key)
        if si is None:
            continue
        res_sasa[si] += float(sasa)

    # 5) Build per-residue table
    rows = []
    for seq_idx, (resseq, icode, aa1) in enumerate(residues):
        imgt_pos = seqidx_to_imgt.get(seq_idx)
        kd = KD.get(aa1, float("nan"))
        hydrophil = -kd if not np.isnan(kd) else float("nan")
        max_asa = MAX_ASA.get(aa1, float("nan"))
        rel = (res_sasa[seq_idx] / max_asa) if (max_asa and not np.isnan(max_asa)) else float("nan")
        rows.append(
            {
                "chain": chain_id,
                "seq_idx": seq_idx,
                "imgt_pos": imgt_pos if imgt_pos is not None else np.nan,
                "resseq": resseq,
                "icode": icode,
                "aa": aa1,
                "sasa": float(res_sasa[seq_idx]),
                "rel_sasa": float(rel),
                "kd_hydropathy": float(kd),
                "hydrophilicity": float(hydrophil),
            }
        )

    df = pd.DataFrame(rows)
    df["is_surface"] = df["rel_sasa"] >= 0.25
    df["is_surface_hydrophilic"] = df["is_surface"] & (df["kd_hydropathy"] <= 0.0)

    # 6) Hydrophilic surface patches (contiguous seq_idx)
    patch_id = -1
    patch_ids: List[int] = []
    in_patch = False
    for i, ok in enumerate(df["is_surface_hydrophilic"].tolist()):
        if ok and not in_patch:
            patch_id += 1
            in_patch = True
        elif (not ok) and in_patch:
            in_patch = False
        patch_ids.append(patch_id if ok else -1)
    df["hydrophilic_patch_id"] = patch_ids

    patches = []
    for pid in sorted(set(patch_ids)):
        if pid < 0:
            continue
        sub = df[df["hydrophilic_patch_id"] == pid]
        if len(sub) < 3:
            continue
        patches.append(
            {
                "patch_id": pid,
                "seq_idx_start": int(sub["seq_idx"].min()),
                "seq_idx_end": int(sub["seq_idx"].max()),
                "imgt_start": int(sub["imgt_pos"].min()) if sub["imgt_pos"].notna().any() else np.nan,
                "imgt_end": int(sub["imgt_pos"].max()) if sub["imgt_pos"].notna().any() else np.nan,
                "length": int(len(sub)),
                "mean_rel_sasa": float(sub["rel_sasa"].mean()),
                "mean_hydrophilicity": float(sub["hydrophilicity"].mean()),
                "score_sum_relSASA_x_hydrophil": float((sub["rel_sasa"] * sub["hydrophilicity"]).sum()),
                "sequence": "".join(sub["aa"].tolist()),
            }
        )
    df_patches = pd.DataFrame(patches).sort_values(
        ["score_sum_relSASA_x_hydrophil", "length"], ascending=[False, False]
    )

    # 7) SR mutation mapping
    sr_muts = load_sr_mutations(MUT_JSONL)
    mut_rows = []
    for m in sr_muts:
        pos = int(m["imgt_pos"])
        hit = df[df["imgt_pos"] == pos]
        if hit.empty:
            mut_rows.append(
                {
                    "imgt_pos": pos,
                    "from": m.get("from"),
                    "to": m.get("to"),
                    "found_in_structure": False,
                    "rel_sasa": np.nan,
                    "is_surface": np.nan,
                    "kd_from": KD.get(str(m.get("from")), np.nan),
                    "kd_to": KD.get(str(m.get("to")), np.nan),
                    "delta_hydrophilicity": np.nan,
                }
            )
            continue
        r0 = hit.iloc[0]
        aa_from = str(m.get("from"))
        aa_to = str(m.get("to"))
        kd_from = KD.get(aa_from, np.nan)
        kd_to = KD.get(aa_to, np.nan)
        # hydrophilicity = -KD, so delta = (-kd_to) - (-kd_from) = kd_from - kd_to
        delta_hphil = (kd_from - kd_to) if (not np.isnan(kd_from) and not np.isnan(kd_to)) else np.nan

        mut_rows.append(
            {
                "imgt_pos": pos,
                "from": aa_from,
                "to": aa_to,
                "found_in_structure": True,
                "seq_idx": int(r0["seq_idx"]),
                "aa_structure": str(r0["aa"]),
                "rel_sasa": float(r0["rel_sasa"]),
                "is_surface": bool(r0["is_surface"]),
                "kd_from": float(kd_from),
                "kd_to": float(kd_to),
                "delta_hydrophilicity": float(delta_hphil),
                "patch_id": int(r0["hydrophilic_patch_id"]),
            }
        )
    df_sr = pd.DataFrame(mut_rows).sort_values("imgt_pos")

    # 8) Write outputs
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)

    # Summary stats for SR evidence
    sr_found = df_sr[df_sr["found_in_structure"] == True]  # noqa: E712
    sr_surface_n = int((sr_found["is_surface"] == True).sum())  # noqa: E712
    sr_total_n = int(len(sr_found))
    sr_surface_frac = (sr_surface_n / sr_total_n) if sr_total_n else float("nan")

    # Report
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("# 7D12 (4KRL) structure-based surface hydrophilicity report\n\n")
        f.write(f"- **Structure**: `{PDB_PATH}`\n")
        f.write(f"- **Analyzed chain**: `{chain_id}` (Nanobody/VHH 7D12)\n")
        f.write("- **Method**: Shrake–Rupley SASA (probe=1.4Å, 200 sphere points/atom), Kyte–Doolittle hydropathy.\n")
        f.write("- **Surface definition**: relSASA >= 0.25\n")
        f.write("- **Surface-hydrophilic**: surface AND KD <= 0.0\n\n")

        f.write("## 1) Global summary\n\n")
        f.write(f"- Residues (chain {chain_id}): **{len(df)}**\n")
        f.write(f"- Surface residues: **{int(df['is_surface'].sum())}** ({float(df['is_surface'].mean()):.1%})\n")
        f.write(
            f"- Surface-hydrophilic residues: **{int(df['is_surface_hydrophilic'].sum())}** "
            f"({float(df['is_surface_hydrophilic'].mean()):.1%})\n\n"
        )

        f.write("## 2) Top surface-hydrophilic patches\n\n")
        if df_patches.empty:
            f.write("No patches found with length>=3 under current thresholds.\n\n")
        else:
            f.write(df_patches.head(12).to_markdown(index=False, floatfmt=".3f") + "\n\n")

        f.write("## 3) SR mutations mapped to structure (evidence for SR)\n\n")
        f.write(f"- SR mutations found in structure: **{sr_total_n}/{len(df_sr)}**\n")
        f.write(f"- SR mutations on surface (relSASA>=0.25): **{sr_surface_n}/{sr_total_n}** ({sr_surface_frac:.1%})\n\n")
        f.write(df_sr.to_markdown(index=False, floatfmt=".3f") + "\n\n")

        f.write("### Interpretation (SR evidence)\n")
        f.write("- If SR is a true \"surface resurfacing\" design, SR mutation sites should be **surface-exposed** in the structure.\n")
        f.write("- The table above reports **relSASA** for each SR mutation IMGT position using the 4KRL structure.\n")
        f.write("- Use the `patch_id` to see whether mutations land inside identified **surface-hydrophilic patches**.\n\n")

        f.write("## 4) Files\n\n")
        f.write(f"- Per-residue metrics: `{OUT_CSV}`\n")
        f.write(f"- This report: `{OUT_MD}`\n")

    print(f"Wrote: {OUT_CSV}")
    print(f"Wrote: {OUT_MD}")


if __name__ == "__main__":
    main()

