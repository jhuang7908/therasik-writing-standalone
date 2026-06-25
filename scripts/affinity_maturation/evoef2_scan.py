"""
L1: EvoEF2 single-point ΔΔG scan for structure-driven affinity maturation.

Runs BuildMutant + ComputeBinding for each candidate mutation on the
VHH-HER2 complex. Outputs a CSV of binding energy changes.

Usage (from repo root, conda activate affmat):
    python scripts/affinity_maturation/evoef2_scan.py
"""

import csv
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG = yaml.safe_load((SCRIPT_DIR / "config.yaml").read_text(encoding="utf-8"))

EVOEF2 = str((SCRIPT_DIR / CONFIG["paths"]["evoef2_exe"]).resolve())
COMPLEX_PDB = str((SCRIPT_DIR / CONFIG["paths"]["complex_pdb"]).resolve())
OUTPUT_DIR = Path((SCRIPT_DIR / CONFIG["paths"]["output_dir"]).resolve())
VHH_CHAIN = CONFIG["project"]["vhh_chain"]

MUTATIONS = CONFIG["mutations"]
DDG_BIND_THRESHOLD = CONFIG["gates_l1"]["ddg_bind_threshold"]


pass  # EvoEF2 uses single-letter codes: {wt}{chain}{resi}{mut}


def run_evoef2(args: list[str], cwd: str) -> str:
    cmd = [EVOEF2] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=120)
    return result.stdout + result.stderr


def parse_binding_energy(output: str) -> float | None:
    for line in output.splitlines():
        if line.strip().startswith("Total") and "=" in line:
            parts = line.split("=")
            try:
                return float(parts[-1].strip())
            except ValueError:
                pass
    return None


def compute_wt_binding(work_dir: str) -> float:
    pdb_name = os.path.basename(COMPLEX_PDB)
    shutil.copy2(COMPLEX_PDB, os.path.join(work_dir, pdb_name))
    out = run_evoef2(["--command=ComputeBinding", f"--pdb={pdb_name}"], cwd=work_dir)
    energy = parse_binding_energy(out)
    if energy is None:
        raise RuntimeError(f"Failed to parse WT binding energy:\n{out}")
    return energy


def build_and_score_mutant(site: int, wt_aa: str, mut_aa: str, work_dir: str) -> dict:
    """Build a single-point mutant and compute its binding energy."""
    pdb_name = os.path.basename(COMPLEX_PDB)
    shutil.copy2(COMPLEX_PDB, os.path.join(work_dir, pdb_name))

    mutant_code = f"{wt_aa}{VHH_CHAIN}{site}{mut_aa}"
    mut_file = os.path.join(work_dir, "individual_list.txt")
    with open(mut_file, "w") as f:
        f.write(f"{mutant_code};\n")

    build_out = run_evoef2([
        "--command=BuildMutant",
        f"--pdb={pdb_name}",
        "--mutant_file=individual_list.txt",
    ], cwd=work_dir)

    stem = Path(pdb_name).stem
    mutant_pdb = f"{stem}_Model_0001.pdb"
    mutant_path = os.path.join(work_dir, mutant_pdb)
    if not os.path.exists(mutant_path):
        return {
            "site": site, "wt_aa": wt_aa, "mut_aa": mut_aa,
            "mutation": f"{wt_aa}{site}{mut_aa}",
            "ddg_bind": None, "wt_bind": None, "mut_bind": None,
            "error": f"BuildMutant failed: {build_out[-200:]}",
        }

    bind_out = run_evoef2([
        "--command=ComputeBinding", f"--pdb={mutant_pdb}",
    ], cwd=work_dir)
    mut_energy = parse_binding_energy(bind_out)

    return {
        "site": site, "wt_aa": wt_aa, "mut_aa": mut_aa,
        "mutation": f"{wt_aa}{site}{mut_aa}",
        "mut_bind": mut_energy,
        "error": None if mut_energy is not None else "parse error",
    }


def run_scan():
    print("=" * 60)
    print("L1: EvoEF2 Single-Point ΔΔG Scan")
    print("=" * 60)

    with tempfile.TemporaryDirectory(prefix="evoef2_wt_") as wt_dir:
        wt_energy = compute_wt_binding(wt_dir)
    print(f"\nWT binding energy: {wt_energy:.2f} kcal/mol\n")

    results = []
    for entry in MUTATIONS:
        site = entry["site"]
        wt_aa = entry["wt"]
        for mut_aa in entry["candidates"]:
            print(f"  Scanning {wt_aa}{site}{mut_aa} ... ", end="", flush=True)
            with tempfile.TemporaryDirectory(prefix=f"evoef2_{wt_aa}{site}{mut_aa}_") as tmp:
                row = build_and_score_mutant(site, wt_aa, mut_aa, tmp)
            row["wt_bind"] = wt_energy
            if row["mut_bind"] is not None:
                row["ddg_bind"] = row["mut_bind"] - wt_energy
                status = "PASS" if row["ddg_bind"] < DDG_BIND_THRESHOLD else "fail"
                print(f"ΔΔG = {row['ddg_bind']:+.2f}  [{status}]")
            else:
                row["ddg_bind"] = None
                print(f"ERROR: {row['error']}")
            results.append(row)

    out_csv = OUTPUT_DIR / "evoef2_scan_results.csv"
    fields = ["mutation", "site", "wt_aa", "mut_aa", "wt_bind", "mut_bind", "ddg_bind", "error"]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    passed = [r for r in results if r["ddg_bind"] is not None and r["ddg_bind"] < DDG_BIND_THRESHOLD]
    print(f"\n{'=' * 60}")
    print(f"Results: {len(passed)}/{len(results)} mutations passed (ΔΔG < {DDG_BIND_THRESHOLD})")
    print(f"Output:  {out_csv}")
    print(f"{'=' * 60}")
    return results


if __name__ == "__main__":
    run_scan()
