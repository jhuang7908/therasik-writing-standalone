#!/usr/bin/env python3
"""
Compute VH/VL angle (principal-axis SVD) + miniCMC for all rat Campath variants.
Reads existing PDBs; no re-prediction needed.

  conda activate anarcii
  python scripts/angle_minicmc_rat_campath.py
"""
from __future__ import annotations

import json
import sys
import math
from pathlib import Path

import numpy as np

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))

PROJ = SUITE / "projects" / "rat_campath_console_humanization"
PDB_DIR = PROJ / "pdbs"

VARIANTS = [
    "Rat_parent",
    "DEEP-FR",
    "9AA-CTX",
    "DeepFR-CTX",
    "DeepFR-CTX-CMC",
    "CDR_graft_Vernier_BM",
    "Surface_reshape",
]


def compute_angle_from_pdb(pdb_path: Path) -> float | None:
    """VH/VL orientation angle via SVD principal axis (same method as engine.py)."""
    try:
        import Bio.PDB as bpdb
        parser = bpdb.PDBParser(QUIET=True)
        structure = parser.get_structure("ab", str(pdb_path))
        model = structure[0]
        chains = {c.id: c for c in model.get_chains()}

        def _axis(chain):
            cas = np.array([list(r["CA"].get_vector())
                            for r in chain if r.has_id("CA")])
            if len(cas) < 3:
                return None
            _, _, vmat = np.linalg.svd(cas - cas.mean(axis=0))
            return vmat[0]

        hc, lc = chains.get("H"), chains.get("L")
        if hc and lc:
            ah, al = _axis(hc), _axis(lc)
            if ah is not None and al is not None:
                cos_a = np.dot(ah, al) / (np.linalg.norm(ah) * np.linalg.norm(al))
                return round(float(np.degrees(np.arccos(np.clip(cos_a, -1, 1)))), 1)
    except Exception:
        pass
    return None


def compute_rmsd_from_pdb(ref_path: Path, tgt_path: Path) -> float | None:
    try:
        from Bio.PDB import PDBParser, Superimposer
        parser = PDBParser(QUIET=True)
        ref = parser.get_structure("ref", str(ref_path))
        tgt = parser.get_structure("tgt", str(tgt_path))
        ref_ca = [a for a in ref.get_atoms() if a.get_name() == "CA"]
        tgt_ca = [a for a in tgt.get_atoms() if a.get_name() == "CA"]
        n = min(len(ref_ca), len(tgt_ca))
        sup = Superimposer()
        sup.set_atoms(ref_ca[:n], tgt_ca[:n])
        return round(sup.rms, 3)
    except Exception:
        return None


def main() -> None:
    data = json.loads((PROJ / "humanized_sequences.json").read_text(encoding="utf-8"))
    metrics = json.loads((PROJ / "comprehensive_metrics.json").read_text(encoding="utf-8"))
    metrics_by_name = {r["variant"]: r for r in metrics}

    ref_pdb = PDB_DIR / "Rat_parent.pdb"
    ref_angle = compute_angle_from_pdb(ref_pdb)

    rows = []
    for name in VARIANTS:
        pdb = PDB_DIR / f"{name}.pdb"
        angle = compute_angle_from_pdb(pdb) if pdb.is_file() else None
        angle_delta = (round(angle - ref_angle, 1)
                       if angle is not None and ref_angle is not None else None)
        rmsd = (0.0 if name == "Rat_parent" else
                compute_rmsd_from_pdb(ref_pdb, pdb) if pdb.is_file() else None)

        m = metrics_by_name.get(name, {})
        rows.append({
            "variant": name,
            "angle_deg": angle,
            "angle_delta_vs_rat": angle_delta,
            "rmsd_ca_A": rmsd,
            "pI": m.get("pI"),
            "Instab": m.get("instability_index"),
            "ADI": m.get("ADI"),
            "agg_motifs": m.get("agg_motifs"),
            "charge_patch7": m.get("charge_patch_max7"),
            "Fv_asym": m.get("Fv_charge_asymmetry"),
            "n_deamid": m.get("n_deamidation"),
            "n_isomer": m.get("n_isomerization"),
        })

    # Save JSON
    out_json = PROJ / "angle_minicmc.json"
    out_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # Markdown table
    lines = [
        "# Rat Campath — VH/VL Angle + miniCMC",
        "",
        "**Angle:** VH/VL principal-axis angle (SVD); ref = Rat_parent.  "
        "Δ = humanized − rat (positive = opener, negative = closer).",
        "",
        "**miniCMC:** pI, Instability Index, ADI (higher = better), "
        "aggregation hotspots, charge patch (Fv window 7), Fv charge asymmetry, "
        "deamidation sites, isomerisation sites.",
        "",
        "| Variant | Angle (°) | ΔAngle | RMSD (Å) | pI | Instab | ADI | Agg | ChgPatch7 | FvAsym | Deamid | Isomer |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        def f(v): return str(v) if v is not None else "—"
        lines.append(
            f"| {r['variant']} | {f(r['angle_deg'])} | {f(r['angle_delta_vs_rat'])} |"
            f" {f(r['rmsd_ca_A'])} | {f(r['pI'])} | {f(r['Instab'])} | {f(r['ADI'])} |"
            f" {f(r['agg_motifs'])} | {f(r['charge_patch7'])} | {f(r['Fv_asym'])} |"
            f" {f(r['n_deamid'])} | {f(r['n_isomer'])} |"
        )

    out_md = PROJ / "ANGLE_MINICMC.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()
