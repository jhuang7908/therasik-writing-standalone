"""
PRODIGY binding affinity prediction for all mutant candidates.

PRODIGY uses interfacial contact (IC) counting + buried surface statistics
to predict ΔG_bind and Kd. MIT license, free for commercial use.

Reference: Vangone & Bonvin, eLife 2015; Xue et al., Bioinformatics 2016.
Benchmark: Pearson r ~0.74 on protein-protein affinity dataset.

Workflow:
  1. Build each mutant PDB with EvoEF2 BuildMutant
  2. Run PRODIGY on the mutant complex (chains A+B)
  3. Compute ΔΔG = ΔG_mut - ΔG_WT
  4. Output ranked table

Usage (from repo root):
    $env:KMP_DUPLICATE_LIB_OK="TRUE"
    conda run -n affmat python scripts/affinity_maturation/prodigy_score.py
"""

import csv
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml
from Bio.PDB import PDBParser

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG = yaml.safe_load((SCRIPT_DIR / "config.yaml").read_text(encoding="utf-8"))

EVOEF2 = str((SCRIPT_DIR / CONFIG["paths"]["evoef2_exe"]).resolve())
COMPLEX_PDB = str((SCRIPT_DIR / CONFIG["paths"]["complex_pdb"]).resolve())
OUTPUT_DIR = Path((SCRIPT_DIR / CONFIG["paths"]["output_dir"]).resolve())
VHH_CHAIN = CONFIG["project"]["vhh_chain"]

CANDIDATES = [
    ("WT",              []),
    ("Y67F",            [{"site": 67,  "wt_aa": "Y", "mut_aa": "F"}]),
    ("N62S",            [{"site": 62,  "wt_aa": "N", "mut_aa": "S"}]),
    ("K70R",            [{"site": 70,  "wt_aa": "K", "mut_aa": "R"}]),
    ("F112Y",           [{"site": 112, "wt_aa": "F", "mut_aa": "Y"}]),
    ("Y67F+K70R",       [{"site": 67,  "wt_aa": "Y", "mut_aa": "F"},
                          {"site": 70,  "wt_aa": "K", "mut_aa": "R"}]),
    ("Y67F+N62S+F112Y", [{"site": 67,  "wt_aa": "Y", "mut_aa": "F"},
                          {"site": 62,  "wt_aa": "N", "mut_aa": "S"},
                          {"site": 112, "wt_aa": "F", "mut_aa": "Y"}]),
    ("Y67F+F112Y",      [{"site": 67,  "wt_aa": "Y", "mut_aa": "F"},
                          {"site": 112, "wt_aa": "F", "mut_aa": "Y"}]),
    ("N62S+K70R",       [{"site": 62,  "wt_aa": "N", "mut_aa": "S"},
                          {"site": 70,  "wt_aa": "K", "mut_aa": "R"}]),
    ("N62S+F112Y+K70R", [{"site": 62,  "wt_aa": "N", "mut_aa": "S"},
                          {"site": 112, "wt_aa": "F", "mut_aa": "Y"},
                          {"site": 70,  "wt_aa": "K", "mut_aa": "R"}]),
]


def build_mutant_pdb(mutations: list[dict], work_dir: str) -> str | None:
    pdb_name = os.path.basename(COMPLEX_PDB)
    shutil.copy2(COMPLEX_PDB, os.path.join(work_dir, pdb_name))
    if not mutations:
        return os.path.join(work_dir, pdb_name)

    mut_str = ",".join(f"{m['wt_aa']}{VHH_CHAIN}{m['site']}{m['mut_aa']}" for m in mutations) + ";"
    with open(os.path.join(work_dir, "individual_list.txt"), "w") as f:
        f.write(mut_str + "\n")

    subprocess.run([EVOEF2, "--command=BuildMutant", f"--pdb={pdb_name}",
                    "--mutant_file=individual_list.txt"],
                   capture_output=True, text=True, cwd=work_dir, timeout=120)

    stem = Path(pdb_name).stem
    mutant = os.path.join(work_dir, f"{stem}_Model_0001.pdb")
    return mutant if os.path.exists(mutant) else None


def run_prodigy(pdb_path: str) -> dict | None:
    from prodigy_prot.modules.prodigy import Prodigy

    parser = PDBParser(QUIET=True)
    try:
        structure = parser.get_structure("mol", pdb_path)
        model = structure[0]
    except Exception as e:
        return None

    p = Prodigy(model, selection=[VHH_CHAIN, CONFIG["project"]["antigen_chain"]], temp=25.0)
    p.predict(distance_cutoff=5.5, acc_threshold=0.05)
    d = p.as_dict()
    return {
        "dg": round(d["ba_val"], 3),
        "kd": d["kd_val"],
        "n_contacts": d["ICs"],
        "nis_a": round(d["nis_a"], 1),
        "nis_c": round(d["nis_c"], 1),
    }


def run():
    print("=" * 65)
    print("PRODIGY Binding Affinity Scan (MIT license, commercial OK)")
    print("=" * 65)

    results = []
    wt_dg = None

    for label, mutations in CANDIDATES:
        print(f"  {label:<25s} ... ", end="", flush=True)
        with tempfile.TemporaryDirectory(prefix=f"prodigy_{label}_") as tmp:
            pdb = build_mutant_pdb(mutations, tmp)
            if pdb is None:
                print("BUILD FAILED")
                results.append({"variant": label, "dg": None, "kd": None,
                                 "ddg": None, "n_contacts": None})
                continue
            pred = run_prodigy(pdb)

        if pred is None:
            print("PRODIGY ERROR")
            results.append({"variant": label, "dg": None, "kd": None,
                             "ddg": None, "n_contacts": None})
            continue

        if label == "WT":
            wt_dg = pred["dg"]

        ddg = round(pred["dg"] - wt_dg, 3) if wt_dg is not None else None
        kd_nm = pred["kd"] * 1e9
        print(f"ΔG={pred['dg']:+.2f}  ΔΔG={ddg:+.3f}  Kd={kd_nm:.2f} nM  "
              f"ICs={pred['n_contacts']}")
        results.append({
            "variant": label,
            "dg": pred["dg"],
            "kd_nM": round(kd_nm, 3),
            "ddg": ddg,
            "n_contacts": pred["n_contacts"],
            "nis_a": pred["nis_a"],
            "nis_c": pred["nis_c"],
        })

    out_csv = OUTPUT_DIR / "prodigy_results.csv"
    if results:
        fields = ["variant", "dg", "ddg", "kd_nM", "n_contacts", "nis_a", "nis_c"]
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(results)

    print(f"\n{'=' * 65}")
    print("RANKED BY ΔΔG:")
    for r in sorted(results, key=lambda x: (x.get("ddg") or 999)):
        if r["dg"] is not None:
            print(f"  {r['variant']:<25s}  ΔΔG={r['ddg']:+.3f}  Kd={r['kd_nM']:.2f} nM")
    print(f"\nOutput: {out_csv}")
    print(f"{'=' * 65}")
    return results


if __name__ == "__main__":
    run()
