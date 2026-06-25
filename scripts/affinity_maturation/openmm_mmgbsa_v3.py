"""
L3 v3: Single-Trajectory Ensemble MM/GBSA on truncated interface system.

Observation: Full HER2 ECD (650 aa, ~13k atoms with H) makes CPU MD prohibitively
slow (~10 min just for system setup). Solution: retain only HER2 interface region
(residues 520-620, ~100 aa, the domain IV binding site) for computation.

This reduces the system from ~13,000 to ~4,000 atoms, making each candidate
feasible in ~3-5 minutes on CPU.

Physical justification: long-range contributions from distal HER2 residues cancel
out when computing ΔΔG = ΔG_mut - ΔG_WT (same truncation applied consistently).

Usage:
    $env:KMP_DUPLICATE_LIB_OK="TRUE"
    conda run -n affmat python scripts/affinity_maturation/openmm_mmgbsa_v3.py
"""

import csv
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG = yaml.safe_load((SCRIPT_DIR / "config.yaml").read_text(encoding="utf-8"))

EVOEF2      = str((SCRIPT_DIR / CONFIG["paths"]["evoef2_exe"]).resolve())
COMPLEX_PDB = str((SCRIPT_DIR / CONFIG["paths"]["complex_pdb"]).resolve())
OUTPUT_DIR  = Path((SCRIPT_DIR / CONFIG["paths"]["output_dir"]).resolve())
VHH_CHAIN   = CONFIG["project"]["vhh_chain"]
AG_CHAIN    = CONFIG["project"]["antigen_chain"]
OPENMM_CFG  = CONFIG["openmm"]

N_SNAPSHOTS  = OPENMM_CFG.get("n_snapshots", 6)
EQUIL_STEPS  = OPENMM_CFG.get("equilibration_steps", 2000)
SNAP_INTERVAL= OPENMM_CFG.get("snapshot_interval_steps", 1000)
MIN_STEPS    = OPENMM_CFG.get("minimization_steps", 300)

# HER2 interface region (domain IV, contains 90%+ of VHH contacts)
HER2_RESI_START = 520
HER2_RESI_END   = 620

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


def truncate_her2(pdb_path: str, out_path: str,
                  her2_start: int = HER2_RESI_START,
                  her2_end: int = HER2_RESI_END) -> int:
    """Write a new PDB keeping all VHH residues + HER2 [her2_start..her2_end]."""
    kept = 0
    with open(pdb_path) as fi, open(out_path, "w") as fo:
        for line in fi:
            if not line.startswith(("ATOM", "HETATM")):
                continue
            chain = line[21]
            try:
                resi = int(line[22:26].strip())
            except ValueError:
                continue
            if chain == VHH_CHAIN:
                fo.write(line)
                kept += 1
            elif chain == AG_CHAIN and her2_start <= resi <= her2_end:
                fo.write(line)
                kept += 1
        fo.write("END\n")
    return kept


def build_subsystem_topology(full_topology, keep_chain_ids: list[str]):
    from openmm.app import Topology
    new_top = Topology()
    atom_map = []
    for chain in full_topology.chains():
        if chain.id not in keep_chain_ids:
            continue
        new_chain = new_top.addChain(chain.id)
        for res in chain.residues():
            new_res = new_top.addResidue(res.name, new_chain)
            for atom in res.atoms():
                new_top.addAtom(atom.name, atom.element, new_res)
                atom_map.append(atom.index)
    return new_top, atom_map


def compute_mmgbsa(pdb_path: str, label: str) -> dict:
    """Single-trajectory ensemble MM/GBSA on the truncated complex."""
    try:
        from openmm.app import PDBFile, ForceField, Simulation, Modeller
        from openmm import LangevinMiddleIntegrator, VerletIntegrator, Context, Platform, unit
    except ImportError:
        return {"variant": label, "mmgbsa_bind": None, "error": "no openmm"}

    ff = ForceField(OPENMM_CFG["forcefield"], OPENMM_CFG["implicit_solvent"])

    try:
        pdb = PDBFile(pdb_path)
    except Exception as e:
        return {"variant": label, "mmgbsa_bind": None, "error": str(e)}

    try:
        modeller = Modeller(pdb.topology, pdb.positions)
        modeller.addHydrogens(ff, pH=7.0)
        top = modeller.topology
        pos = modeller.positions
        n_atoms = top.getNumAtoms()
    except Exception as e:
        return {"variant": label, "mmgbsa_bind": None, "error": f"addH: {e}"}

    try:
        platform = Platform.getPlatformByName("CPU")
    except Exception:
        platform = Platform.getPlatformByName("Reference")

    try:
        sys_c = ff.createSystem(top, nonbondedCutoff=1.0 * unit.nanometers, constraints=None)
    except Exception as e:
        return {"variant": label, "mmgbsa_bind": None, "error": f"FF: {e}"}

    integ = LangevinMiddleIntegrator(
        OPENMM_CFG["temperature_K"] * unit.kelvin, 1.0 / unit.picosecond, 0.002 * unit.picoseconds)
    sim = Simulation(top, sys_c, integ, platform)
    sim.context.setPositions(pos)
    sim.minimizeEnergy(maxIterations=MIN_STEPS)
    sim.step(EQUIL_STEPS)

    vhh_top, vhh_idx = build_subsystem_topology(top, [VHH_CHAIN])
    ag_top, ag_idx   = build_subsystem_topology(top, [AG_CHAIN])

    try:
        sys_v = ff.createSystem(vhh_top, nonbondedCutoff=1.0 * unit.nanometers, constraints=None)
        ctx_v = Context(sys_v, VerletIntegrator(0.001 * unit.picoseconds), platform)
        sys_a = ff.createSystem(ag_top, nonbondedCutoff=1.0 * unit.nanometers, constraints=None)
        ctx_a = Context(sys_a, VerletIntegrator(0.001 * unit.picoseconds), platform)
    except Exception as e:
        return {"variant": label, "mmgbsa_bind": None, "error": f"subFF: {e}"}

    dg_list = []
    for _ in range(N_SNAPSHOTS):
        sim.step(SNAP_INTERVAL)
        state = sim.context.getState(getEnergy=True, getPositions=True)
        all_pos = state.getPositions(asNumpy=True)
        e_c = state.getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole) / 4.184

        try:
            ctx_v.setPositions([all_pos[i] for i in vhh_idx])
            e_v = ctx_v.getState(getEnergy=True).getPotentialEnergy().value_in_unit(
                unit.kilojoules_per_mole) / 4.184
            ctx_a.setPositions([all_pos[i] for i in ag_idx])
            e_a = ctx_a.getState(getEnergy=True).getPotentialEnergy().value_in_unit(
                unit.kilojoules_per_mole) / 4.184
            dg_list.append(e_c - e_v - e_a)
        except Exception:
            continue

    del ctx_v, ctx_a

    if not dg_list:
        return {"variant": label, "mmgbsa_bind": None, "error": "no snapshots"}

    mean = sum(dg_list) / len(dg_list)
    std  = (sum((x - mean) ** 2 for x in dg_list) / max(len(dg_list) - 1, 1)) ** 0.5

    return {
        "variant": label,
        "mmgbsa_bind": round(mean, 2),
        "mmgbsa_std":  round(std, 2),
        "n_snapshots": len(dg_list),
        "n_atoms": n_atoms,
        "error": None,
    }


def run():
    print("=" * 65)
    print("L3 v3: Single-Trajectory Ensemble MM/GBSA (truncated HER2)")
    print(f"HER2 region: {HER2_RESI_START}-{HER2_RESI_END} | "
          f"Snapshots: {N_SNAPSHOTS} × {SNAP_INTERVAL*0.002:.0f} ps")
    print("=" * 65)

    results = []
    for label, mutations in CANDIDATES:
        print(f"\n[{label}]", flush=True)
        t0 = time.time()

        with tempfile.TemporaryDirectory(prefix=f"mmgbsa3_{label}_") as tmp:
            full_pdb = build_mutant_pdb(mutations, tmp)
            if full_pdb is None:
                print("  BUILD FAILED")
                results.append({"variant": label, "mmgbsa_bind": None,
                                 "mmgbsa_std": None, "n_snapshots": 0, "error": "build"})
                continue

            trunc_pdb = os.path.join(tmp, "trunc.pdb")
            n_kept = truncate_her2(full_pdb, trunc_pdb)
            print(f"  Truncated: {n_kept} heavy atoms  →  running MD...", flush=True)

            row = compute_mmgbsa(trunc_pdb, label)

        elapsed = time.time() - t0
        if row["mmgbsa_bind"] is not None:
            print(f"  ΔG = {row['mmgbsa_bind']:.2f} ± {row['mmgbsa_std']:.2f} kcal/mol  "
                  f"({row['n_atoms']} atoms incl H, {elapsed:.0f}s)")
        else:
            print(f"  ERROR: {row['error']}  ({elapsed:.0f}s)")
        results.append(row)

    wt_bind = next((r["mmgbsa_bind"] for r in results
                    if r["variant"] == "WT" and r["mmgbsa_bind"] is not None), None)
    for r in results:
        if r["mmgbsa_bind"] is not None and wt_bind is not None:
            r["mmgbsa_ddg"] = round(r["mmgbsa_bind"] - wt_bind, 2)
        else:
            r["mmgbsa_ddg"] = None

    out_csv = OUTPUT_DIR / "openmm_v3_results.csv"
    fields = ["variant", "mmgbsa_bind", "mmgbsa_std", "mmgbsa_ddg", "n_snapshots", "n_atoms", "error"]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    print("\n" + "=" * 65)
    print(f"{'Variant':<25} {'ΔG':>8} {'±':>6} {'ΔΔG':>8}")
    print("-" * 55)
    for r in sorted(results, key=lambda x: x.get("mmgbsa_ddg") or 999):
        if r["mmgbsa_bind"] is not None:
            ddg = r.get("mmgbsa_ddg", 0)
            print(f"  {r['variant']:<23} {r['mmgbsa_bind']:>8.2f} {r['mmgbsa_std']:>6.2f} {ddg:>+8.2f}")
    print(f"\nOutput: {out_csv}")
    print("=" * 65)
    return results


if __name__ == "__main__":
    run()
