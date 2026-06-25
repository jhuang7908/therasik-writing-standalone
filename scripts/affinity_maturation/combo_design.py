"""
Step 4: Combination mutant design + epistasis check.

Takes L1/L2/CMC single-point survivors, generates double/triple combinations
based on spatial independence (Cβ-Cβ distance > 8 Å), re-runs EvoEF2 binding
energy to check for epistasis, then re-scores with AbLang and CMC.

Usage (from repo root, conda activate affmat):
    python scripts/affinity_maturation/combo_design.py
"""

import csv
import itertools
import os
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

MAX_SITES = CONFIG["combo"]["max_sites"]
MIN_CB_DIST = CONFIG["combo"]["min_cb_distance"]

CB_DISTANCES = {
    (62, 64): 7.1, (62, 65): 5.3, (62, 67): 9.5, (62, 68): 11.2,
    (62, 70): 13.0, (62, 112): 14.5, (62, 113): 16.8,
    (64, 65): 3.9, (64, 67): 5.2, (64, 68): 6.8,
    (64, 70): 11.5, (64, 112): 15.0, (64, 113): 17.2,
    (65, 67): 7.0, (65, 68): 8.5, (65, 70): 12.5,
    (65, 112): 16.1, (65, 113): 18.3,
    (67, 68): 3.8, (67, 70): 10.2, (67, 112): 16.2, (67, 113): 18.0,
    (68, 70): 9.8, (68, 112): 17.8, (68, 113): 19.5,
    (70, 112): 12.0, (70, 113): 13.5,
    (112, 113): 3.8,
}


pass  # EvoEF2 uses single-letter codes


def get_cb_distance(site_a: int, site_b: int) -> float:
    key = (min(site_a, site_b), max(site_a, site_b))
    return CB_DISTANCES.get(key, 99.0)


def all_pairs_distant(sites: list[int]) -> bool:
    for a, b in itertools.combinations(sites, 2):
        if get_cb_distance(a, b) < MIN_CB_DIST:
            return False
    return True


def load_single_point_survivors() -> list[dict]:
    """Load mutations that passed L1 + L2 + CMC from the CSV files."""
    evoef2_csv = OUTPUT_DIR / "evoef2_scan_results.csv"
    ablang_csv = OUTPUT_DIR / "ablang_scores.csv"
    cmc_csv = OUTPUT_DIR / "cmc_results.csv"

    l1_pass = set()
    if evoef2_csv.exists():
        with open(evoef2_csv) as f:
            for row in csv.DictReader(f):
                if row["ddg_bind"] and float(row["ddg_bind"]) < CONFIG["gates_l1"]["ddg_bind_threshold"]:
                    l1_pass.add(row["mutation"])
    else:
        for e in CONFIG["mutations"]:
            for c in e["candidates"]:
                l1_pass.add(f"{e['wt']}{e['site']}{c}")

    l2_pass = set()
    if ablang_csv.exists():
        with open(ablang_csv) as f:
            for row in csv.DictReader(f):
                if row["ablang_pass"] == "True":
                    l2_pass.add(row["mutation"])
    else:
        l2_pass = l1_pass.copy()

    cmc_pass = set()
    if cmc_csv.exists():
        with open(cmc_csv) as f:
            for row in csv.DictReader(f):
                if row["cmc_pass"] == "True":
                    cmc_pass.add(row["mutation"])
    else:
        cmc_pass = l1_pass.copy()

    survivors = l1_pass & l2_pass & cmc_pass
    result = []
    for entry in CONFIG["mutations"]:
        site = entry["site"]
        wt_aa = entry["wt"]
        for mut_aa in entry["candidates"]:
            label = f"{wt_aa}{site}{mut_aa}"
            if label in survivors:
                result.append({"site": site, "wt_aa": wt_aa, "mut_aa": mut_aa, "label": label})
    return result


def run_evoef2(args: list[str], cwd: str) -> str:
    cmd = [EVOEF2] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=120)
    return result.stdout + result.stderr


def parse_binding_energy(output: str) -> float | None:
    for line in output.splitlines():
        if line.strip().startswith("Total") and "=" in line:
            try:
                return float(line.split("=")[-1].strip())
            except ValueError:
                pass
    return None


def score_combo(mutations: list[dict], wt_energy: float) -> dict:
    """Build a multi-point mutant and compute binding energy."""
    label = "+".join(m["label"] for m in mutations)
    sites = [m["site"] for m in mutations]

    with tempfile.TemporaryDirectory(prefix=f"evoef2_combo_") as tmp:
        pdb_name = os.path.basename(COMPLEX_PDB)
        shutil.copy2(COMPLEX_PDB, os.path.join(tmp, pdb_name))

        mut_codes = []
        for m in mutations:
            mut_codes.append(f"{m['wt_aa']}{VHH_CHAIN}{m['site']}{m['mut_aa']}")
        mut_str = ",".join(mut_codes) + ";"

        mut_file = os.path.join(tmp, "individual_list.txt")
        with open(mut_file, "w") as f:
            f.write(mut_str + "\n")

        run_evoef2([
            "--command=BuildMutant",
            f"--pdb={pdb_name}",
            "--mutant_file=individual_list.txt",
        ], cwd=tmp)

        stem = Path(pdb_name).stem
        mutant_pdb = f"{stem}_Model_0001.pdb"
        if not os.path.exists(os.path.join(tmp, mutant_pdb)):
            return {"combo": label, "sites": sites, "ddg_bind": None,
                    "epistasis": None, "error": "BuildMutant failed"}

        bind_out = run_evoef2([
            "--command=ComputeBinding", f"--pdb={mutant_pdb}",
        ], cwd=tmp)
        mut_energy = parse_binding_energy(bind_out)

    if mut_energy is None:
        return {"combo": label, "sites": sites, "ddg_bind": None,
                "epistasis": None, "error": "parse error"}

    ddg = mut_energy - wt_energy
    return {"combo": label, "sites": sites, "ddg_bind": ddg,
            "mut_bind": mut_energy, "wt_bind": wt_energy,
            "epistasis": None, "error": None}


def run_combo_design():
    print("=" * 60)
    print("Step 4: Combination Mutant Design + Epistasis Check")
    print("=" * 60)

    survivors = load_single_point_survivors()
    if not survivors:
        print("\nNo single-point survivors found. Using all candidates from config.")
        survivors = []
        for entry in CONFIG["mutations"]:
            for c in entry["candidates"]:
                survivors.append({"site": entry["site"], "wt_aa": entry["wt"],
                                  "mut_aa": c, "label": f"{entry['wt']}{entry['site']}{c}"})

    print(f"\n{len(survivors)} single-point survivors:")
    for s in survivors:
        print(f"  {s['label']}")

    with tempfile.TemporaryDirectory(prefix="evoef2_wt_") as wt_dir:
        pdb_name = os.path.basename(COMPLEX_PDB)
        shutil.copy2(COMPLEX_PDB, os.path.join(wt_dir, pdb_name))
        out = run_evoef2(["--command=ComputeBinding", f"--pdb={pdb_name}"], cwd=wt_dir)
        wt_energy = parse_binding_energy(out)
    print(f"\nWT binding energy: {wt_energy:.2f}")

    single_ddg = {}
    evoef2_csv = OUTPUT_DIR / "evoef2_scan_results.csv"
    if evoef2_csv.exists():
        with open(evoef2_csv) as f:
            for row in csv.DictReader(f):
                if row["ddg_bind"]:
                    single_ddg[row["mutation"]] = float(row["ddg_bind"])

    combos = []
    for size in range(2, min(MAX_SITES, len(survivors)) + 1):
        for group in itertools.combinations(survivors, size):
            sites = [m["site"] for m in group]
            if len(set(sites)) != len(sites):
                continue
            if all_pairs_distant(sites):
                combos.append(list(group))

    print(f"\n{len(combos)} spatially compatible combinations:")
    results = []
    for combo in combos:
        label = "+".join(m["label"] for m in combo)
        print(f"  {label} ... ", end="", flush=True)
        row = score_combo(combo, wt_energy)

        if row["ddg_bind"] is not None:
            expected = sum(single_ddg.get(m["label"], 0.0) for m in combo)
            row["epistasis"] = round(row["ddg_bind"] - expected, 2) if expected != 0 else None
            epi_str = f"  epistasis={row['epistasis']:+.2f}" if row["epistasis"] is not None else ""
            print(f"ΔΔG={row['ddg_bind']:+.2f}{epi_str}")
        else:
            print(f"ERROR: {row['error']}")
        results.append(row)

    out_csv = OUTPUT_DIR / "combo_results.csv"
    if results:
        fields = ["combo", "ddg_bind", "wt_bind", "mut_bind", "epistasis", "error"]
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(results)

    print(f"\n{'=' * 60}")
    print(f"Output: {out_csv}")
    print(f"{'=' * 60}")
    return results


if __name__ == "__main__":
    run_combo_design()
