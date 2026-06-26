"""
Structure + RMSD for rat console four-way humanization variants.

Reads: projects/rat_campath_console_humanization/humanized_sequences.json
Writes: pdbs/*.pdb, SEQUENCE_AND_RMSD.md, sequence_rmsd.json

  conda activate anarcii
  python scripts/comprehensive_eval_rat_campath.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from Bio.PDB import PDBParser, Superimposer

PROJ = SUITE / "projects" / "rat_campath_console_humanization"
PDB_DIR = PROJ / "pdbs"


def main() -> None:
    data = json.loads((PROJ / "humanized_sequences.json").read_text(encoding="utf-8"))

    variants = {
        "Rat_parent": (
            data["rat_parent"]["vh"],
            data["rat_parent"]["vl"],
        ),
        "DEEP-FR": (
            data["DEEP_FR"]["vh"],
            data["DEEP_FR"]["vl"],
        ),
        "9AA-CTX": (
            data["9AA_CTX"]["vh"],
            data["9AA_CTX"]["vl"],
        ),
        "DeepFR-CTX": (
            data["DeepFR_CTX"]["vh"],
            data["DeepFR_CTX"]["vl"],
        ),
        "DeepFR-CTX-CMC": (
            data["DeepFR_CTX_CMC"]["vh"],
            data["DeepFR_CTX_CMC"]["vl"],
        ),
        "CDR_graft_Vernier_BM": (
            data["CDR_graft_Vernier_BM"]["vh"],
            data["CDR_graft_Vernier_BM"]["vl"],
        ),
        "Surface_reshape": (
            data["Surface_reshape"]["vh"],
            data["Surface_reshape"]["vl"],
        ),
    }

    from ImmuneBuilder import ABodyBuilder2

    PDB_DIR.mkdir(parents=True, exist_ok=True)
    predictor = ABodyBuilder2()
    pdb_paths: dict[str, Path] = {}

    print("Step 1: ABodyBuilder2 Fv prediction…")
    for name, (vh, vl) in variants.items():
        path = PDB_DIR / f"{name}.pdb"
        if not path.is_file():
            print(f"  predicting {name}…")
            ab = predictor.predict({"H": vh, "L": vl})
            ab.save(str(path))
        pdb_paths[name] = path

    ref_name = "Rat_parent"
    rmsd_results: dict[str, float | None] = {}
    parser = PDBParser(QUIET=True)
    if ref_name in pdb_paths:
        ref_struct = parser.get_structure(ref_name, str(pdb_paths[ref_name]))
        ref_atoms = [a for a in ref_struct.get_atoms() if a.get_name() == "CA"]
        for name, path in pdb_paths.items():
            if name == ref_name:
                rmsd_results[name] = 0.0
                continue
            tgt = parser.get_structure(name, str(path))
            tgt_atoms = [a for a in tgt.get_atoms() if a.get_name() == "CA"]
            n = min(len(ref_atoms), len(tgt_atoms))
            sup = Superimposer()
            sup.set_atoms(ref_atoms[:n], tgt_atoms[:n])
            rmsd_results[name] = round(sup.rms, 3)
    else:
        print("Missing Rat_parent PDB")

    out_metrics = []
    for name, (vh, vl) in variants.items():
        out_metrics.append(
            {
                "variant": name,
                "vh_len": len(vh),
                "vl_len": len(vl),
                "fv_len": len(vh) + len(vl),
                "pdb": str(pdb_paths.get(name, "")),
                "rmsd_ca_vs_rat_parent": rmsd_results.get(name),
            }
        )

    (PROJ / "sequence_rmsd.json").write_text(
        json.dumps(out_metrics, indent=2), encoding="utf-8"
    )

    # Markdown: RMSD table + FASTA blocks
    lines = [
        "# Rat Campath console demo — sequences & structural RMSD",
        "",
        "Reference for RMSD: **Rat_parent** (same VH/VL as `api/static/demo.html` rat demo).",
        "",
        "Model: **ImmuneBuilder ABodyBuilder2** Fv; RMSD: Cα superposition (min length matched).",
        "",
        "| Variant | VH aa | VL aa | RMSD vs Rat_parent (Å) | PDB |",
        "|---|---:|---:|---:|---|",
    ]
    for row in out_metrics:
        rms = row["rmsd_ca_vs_rat_parent"]
        rms_s = f"{rms}" if rms is not None else "—"
        pdb_rel = f"`pdbs/{Path(row['pdb']).name}`" if row.get("pdb") else "—"
        lines.append(
            f"| {row['variant']} | {row['vh_len']} | {row['vl_len']} | {rms_s} | {pdb_rel} |"
        )

    lines += ["", "## Sequences (VH then VL)", ""]
    for name, (vh, vl) in variants.items():
        lines.append(f"### {name}")
        lines.append("")
        lines.append(f">VH ({len(vh)} aa)")
        lines.append("")
        lines.append(f"`{vh}`")
        lines.append("")
        lines.append(f">VL ({len(vl)} aa)")
        lines.append("")
        lines.append(f"`{vl}`")
        lines.append("")

    dest = PROJ / "SEQUENCE_AND_RMSD.md"
    dest.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {dest}")
    print(json.dumps(out_metrics, indent=2))


if __name__ == "__main__":
    main()
