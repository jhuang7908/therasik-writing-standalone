"""
L3: OpenMM MM/GBSA high-precision binding energy validation.

For each final candidate (single + combo), builds the mutant PDB,
runs energy minimization + short MD with implicit solvent (OBC2),
then computes MM/GBSA binding free energy as:
    ΔG_bind = E_complex - E_VHH_alone - E_HER2_alone

Usage (from repo root, conda activate affmat):
    python scripts/affinity_maturation/openmm_mmgbsa.py
"""

import csv
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG = yaml.safe_load((SCRIPT_DIR / "config.yaml").read_text(encoding="utf-8"))

EVOEF2 = str((SCRIPT_DIR / CONFIG["paths"]["evoef2_exe"]).resolve())
COMPLEX_PDB = str((SCRIPT_DIR / CONFIG["paths"]["complex_pdb"]).resolve())
OUTPUT_DIR = Path((SCRIPT_DIR / CONFIG["paths"]["output_dir"]).resolve())
VHH_CHAIN = CONFIG["project"]["vhh_chain"]
AG_CHAIN = CONFIG["project"]["antigen_chain"]

OPENMM_CFG = CONFIG["openmm"]


pass  # EvoEF2 uses single-letter codes


def build_mutant_pdb(mutations: list[dict], work_dir: str) -> str | None:
    """Use EvoEF2 BuildMutant to create the mutant complex PDB."""
    pdb_name = os.path.basename(COMPLEX_PDB)
    shutil.copy2(COMPLEX_PDB, os.path.join(work_dir, pdb_name))

    if not mutations:
        return os.path.join(work_dir, pdb_name)

    mut_codes = []
    for m in mutations:
        mut_codes.append(f"{m['wt_aa']}{VHH_CHAIN}{m['site']}{m['mut_aa']}")
    mut_str = ",".join(mut_codes) + ";"

    mut_file = os.path.join(work_dir, "individual_list.txt")
    with open(mut_file, "w") as f:
        f.write(mut_str + "\n")

    cmd = [EVOEF2, "--command=BuildMutant", f"--pdb={pdb_name}",
           "--mutant_file=individual_list.txt"]
    subprocess.run(cmd, capture_output=True, text=True, cwd=work_dir, timeout=120)

    stem = Path(pdb_name).stem
    mutant_pdb = os.path.join(work_dir, f"{stem}_Model_0001.pdb")
    return mutant_pdb if os.path.exists(mutant_pdb) else None


def split_chains(pdb_path: str, work_dir: str) -> tuple[str, str, str]:
    """Split complex PDB into complex, VHH-only, and antigen-only files."""
    complex_lines = []
    vhh_lines = []
    ag_lines = []

    with open(pdb_path) as f:
        for line in f:
            if line.startswith(("ATOM", "HETATM")):
                chain = line[21]
                complex_lines.append(line)
                if chain == VHH_CHAIN:
                    vhh_lines.append(line)
                elif chain == AG_CHAIN:
                    ag_lines.append(line)

    complex_out = os.path.join(work_dir, "complex.pdb")
    vhh_out = os.path.join(work_dir, "vhh_only.pdb")
    ag_out = os.path.join(work_dir, "ag_only.pdb")

    for path, lines in [(complex_out, complex_lines), (vhh_out, vhh_lines), (ag_out, ag_lines)]:
        with open(path, "w") as f:
            f.writelines(lines)
            f.write("END\n")

    return complex_out, vhh_out, ag_out


def compute_mmgbsa_energy(pdb_path: str) -> float | None:
    """Minimize + short MD + ensemble-averaged potential energy.

    Unlike single-frame minimization, this runs a short MD equilibration
    then averages energy over N_SNAPSHOTS frames to reduce sensitivity
    to local rotamer packing artifacts.
    """
    try:
        from openmm.app import PDBFile, ForceField, Simulation
        from openmm import LangevinMiddleIntegrator, unit
    except ImportError:
        print("ERROR: OpenMM not available", file=sys.stderr)
        return None

    try:
        from pdbfixer import PDBFixer as Fixer
        fixer = Fixer(filename=pdb_path)
        fixer.findMissingResidues()
        fixer.findMissingAtoms()
        fixer.addMissingAtoms()
        fixer.addMissingHydrogens(7.0)
        fixed_path = pdb_path.replace(".pdb", "_fixed.pdb")
        with open(fixed_path, "w") as f:
            PDBFile.writeFile(fixer.topology, fixer.positions, f)
        pdb = PDBFile(fixed_path)
    except Exception:
        pdb = PDBFile(pdb_path)

    ff = ForceField(OPENMM_CFG["forcefield"], OPENMM_CFG["implicit_solvent"])

    try:
        system = ff.createSystem(pdb.topology, nonbondedCutoff=1.0 * unit.nanometers,
                                 constraints=None)
    except Exception as e:
        print(f"  ForceField error: {e}", file=sys.stderr)
        return None

    integrator = LangevinMiddleIntegrator(
        OPENMM_CFG["temperature_K"] * unit.kelvin,
        1.0 / unit.picosecond,
        0.002 * unit.picoseconds,
    )

    sim = Simulation(pdb.topology, system, integrator)
    sim.context.setPositions(pdb.positions)

    sim.minimizeEnergy(maxIterations=OPENMM_CFG["minimization_steps"])

    equil_steps = OPENMM_CFG.get("equilibration_steps", 25000)
    sim.step(equil_steps)

    n_snapshots = OPENMM_CFG.get("n_snapshots", 10)
    interval = OPENMM_CFG.get("snapshot_interval_steps", 5000)
    energies = []
    for _ in range(n_snapshots):
        sim.step(interval)
        state = sim.context.getState(getEnergy=True)
        e_kj = state.getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole)
        energies.append(e_kj / 4.184)

    return sum(energies) / len(energies)


def compute_binding_energy(mutations: list[dict], label: str) -> dict:
    """Full MM/GBSA pipeline for one variant."""
    print(f"  {label} ... ", end="", flush=True)

    with tempfile.TemporaryDirectory(prefix=f"mmgbsa_{label}_") as tmp:
        mutant_pdb = build_mutant_pdb(mutations, tmp)
        if mutant_pdb is None:
            print("BUILD FAILED")
            return {"variant": label, "mmgbsa_bind": None, "error": "BuildMutant failed"}

        complex_pdb, vhh_pdb, ag_pdb = split_chains(mutant_pdb, tmp)

        e_complex = compute_mmgbsa_energy(complex_pdb)
        e_vhh = compute_mmgbsa_energy(vhh_pdb)
        e_ag = compute_mmgbsa_energy(ag_pdb)

    if any(x is None for x in [e_complex, e_vhh, e_ag]):
        print("ENERGY FAILED")
        return {"variant": label, "mmgbsa_bind": None, "e_complex": e_complex,
                "e_vhh": e_vhh, "e_ag": e_ag, "error": "energy computation failed"}

    dg_bind = e_complex - e_vhh - e_ag
    print(f"ΔG_bind = {dg_bind:.1f} kcal/mol")

    return {
        "variant": label,
        "e_complex": round(e_complex, 1),
        "e_vhh": round(e_vhh, 1),
        "e_ag": round(e_ag, 1),
        "mmgbsa_bind": round(dg_bind, 1),
        "error": None,
    }


def get_candidate_list() -> list[tuple[str, list[dict]]]:
    """Build the list of candidates for L3 from prior results."""
    candidates = [("WT", [])]

    evoef2_csv = OUTPUT_DIR / "evoef2_scan_results.csv"
    combo_csv = OUTPUT_DIR / "combo_results.csv"

    if evoef2_csv.exists():
        with open(evoef2_csv) as f:
            for row in csv.DictReader(f):
                if row["ddg_bind"] and float(row["ddg_bind"]) < CONFIG["gates_l1"]["ddg_bind_threshold"]:
                    candidates.append((row["mutation"], [{
                        "site": int(row["site"]),
                        "wt_aa": row["wt_aa"],
                        "mut_aa": row["mut_aa"],
                    }]))
    else:
        for entry in CONFIG["mutations"]:
            for c in entry["candidates"]:
                label = f"{entry['wt']}{entry['site']}{c}"
                candidates.append((label, [{"site": entry["site"], "wt_aa": entry["wt"], "mut_aa": c}]))

    if combo_csv.exists():
        with open(combo_csv) as f:
            for row in csv.DictReader(f):
                if row.get("error"):
                    continue
                label = row["combo"]
                muts = []
                for part in label.split("+"):
                    wt_aa = part[0]
                    mut_aa = part[-1]
                    site = int(part[1:-1])
                    muts.append({"site": site, "wt_aa": wt_aa, "mut_aa": mut_aa})
                candidates.append((label, muts))

    return candidates


def run_openmm_mmgbsa():
    print("=" * 60)
    print("L3: OpenMM MM/GBSA Binding Energy Validation")
    print("=" * 60)

    candidates = get_candidate_list()
    print(f"\n{len(candidates)} candidates (including WT baseline):\n")

    results = []
    for label, mutations in candidates:
        row = compute_binding_energy(mutations, label)
        results.append(row)

    wt_bind = None
    for r in results:
        if r["variant"] == "WT" and r["mmgbsa_bind"] is not None:
            wt_bind = r["mmgbsa_bind"]
            break

    if wt_bind is not None:
        for r in results:
            if r["mmgbsa_bind"] is not None:
                r["mmgbsa_ddg"] = round(r["mmgbsa_bind"] - wt_bind, 1)
            else:
                r["mmgbsa_ddg"] = None

    out_csv = OUTPUT_DIR / "openmm_results.csv"
    if results:
        fields = ["variant", "e_complex", "e_vhh", "e_ag", "mmgbsa_bind", "mmgbsa_ddg", "error"]
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(results)

    print(f"\n{'=' * 60}")
    print(f"Output: {out_csv}")
    if wt_bind is not None:
        print(f"WT baseline: {wt_bind:.1f} kcal/mol")
    print(f"{'=' * 60}")
    return results


if __name__ == "__main__":
    run_openmm_mmgbsa()
