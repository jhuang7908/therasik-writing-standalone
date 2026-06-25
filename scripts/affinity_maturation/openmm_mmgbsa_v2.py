"""
L3 v2: Single-Trajectory Ensemble MM/GBSA

Key fix over v1: runs MD on the COMPLEX only, then strips chains from each
snapshot to compute E_complex, E_VHH, E_HER2 from the SAME conformation.
This cancels out shared conformational noise and gives physically meaningful ΔΔG.

Workflow per candidate:
  1. Build mutant PDB (EvoEF2 BuildMutant)
  2. PDBFixer: add missing atoms + H
  3. OpenMM: minimize (500 steps) + equilibrate (50 ps)
  4. Collect N snapshots every 10 ps
  5. Per snapshot: strip to complex / VHH / HER2 sub-system (NO re-minimize)
     compute potential energy via single-point calculation
  6. ΔG_bind_i = E_complex_i - E_VHH_i - E_HER2_i
  7. Report mean ± std over N snapshots

Usage (from repo root):
    $env:KMP_DUPLICATE_LIB_OK="TRUE"
    conda run -n affmat python scripts/affinity_maturation/openmm_mmgbsa_v2.py
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

N_SNAPSHOTS = OPENMM_CFG.get("n_snapshots", 10)
EQUIL_STEPS = OPENMM_CFG.get("equilibration_steps", 25000)   # 50 ps
SNAP_INTERVAL = OPENMM_CFG.get("snapshot_interval_steps", 5000)  # 10 ps

CANDIDATES = [
    ("WT",           []),
    ("Y67F",         [{"site": 67,  "wt_aa": "Y", "mut_aa": "F"}]),
    ("N62S",         [{"site": 62,  "wt_aa": "N", "mut_aa": "S"}]),
    ("K70R",         [{"site": 70,  "wt_aa": "K", "mut_aa": "R"}]),
    ("F112Y",        [{"site": 112, "wt_aa": "F", "mut_aa": "Y"}]),
    ("Y67F+K70R",    [{"site": 67,  "wt_aa": "Y", "mut_aa": "F"},
                      {"site": 70,  "wt_aa": "K", "mut_aa": "R"}]),
    ("Y67F+N62S+F112Y", [{"site": 67,  "wt_aa": "Y", "mut_aa": "F"},
                          {"site": 62,  "wt_aa": "N", "mut_aa": "S"},
                          {"site": 112, "wt_aa": "F", "mut_aa": "Y"}]),
    ("Y67F+F112Y",   [{"site": 67,  "wt_aa": "Y", "mut_aa": "F"},
                      {"site": 112, "wt_aa": "F", "mut_aa": "Y"}]),
]


def build_mutant_pdb(mutations: list[dict], work_dir: str) -> str | None:
    pdb_name = os.path.basename(COMPLEX_PDB)
    shutil.copy2(COMPLEX_PDB, os.path.join(work_dir, pdb_name))

    if not mutations:
        return os.path.join(work_dir, pdb_name)

    mut_str = ",".join(f"{m['wt_aa']}{VHH_CHAIN}{m['site']}{m['mut_aa']}" for m in mutations) + ";"
    mut_file = os.path.join(work_dir, "individual_list.txt")
    with open(mut_file, "w") as f:
        f.write(mut_str + "\n")

    cmd = [EVOEF2, "--command=BuildMutant", f"--pdb={pdb_name}",
           "--mutant_file=individual_list.txt"]
    subprocess.run(cmd, capture_output=True, text=True, cwd=work_dir, timeout=120)

    stem = Path(pdb_name).stem
    mutant_pdb = os.path.join(work_dir, f"{stem}_Model_0001.pdb")
    return mutant_pdb if os.path.exists(mutant_pdb) else None


def fix_pdb(pdb_path: str) -> str:
    """Add missing hydrogens only (EvoEF2 RepairStructure already handles heavy atoms).
    If skip_pdbfixer is set in config, return pdb_path as-is and let OpenMM handle H.
    """
    if OPENMM_CFG.get("skip_pdbfixer", False):
        return pdb_path

    try:
        from pdbfixer import PDBFixer
        from openmm.app import PDBFile
    except ImportError:
        return pdb_path

    fixer = PDBFixer(filename=pdb_path)
    fixer.findMissingResidues()
    fixer.findMissingAtoms()
    fixer.addMissingAtoms()
    fixer.addMissingHydrogens(7.0)
    fixed = pdb_path.replace(".pdb", "_fixed.pdb")
    with open(fixed, "w") as f:
        PDBFile.writeFile(fixer.topology, fixer.positions, f)
    return fixed


def build_subsystem_topology(full_topology, keep_chain_ids: list[str]):
    """Build sub-system Topology for selected chains. Returns (topology, atom_idx_map)."""
    from openmm.app import Topology, Element

    new_top = Topology()
    atom_map = []  # maps new atom index → old atom index

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


def compute_single_traj_mmgbsa(pdb_path: str, label: str) -> dict:
    """Single-trajectory ensemble MM/GBSA — optimized: build sub-systems ONCE.

    1. Build complex, VHH-only, HER2-only topologies and Contexts once.
    2. Run MD on complex only.
    3. Per snapshot: get complex positions, set positions in VHH/HER2 contexts,
       compute all three energies — no system rebuild per snapshot.
    """
    try:
        from openmm.app import PDBFile, ForceField, Simulation
        from openmm import LangevinMiddleIntegrator, VerletIntegrator, Context, Platform, unit
    except ImportError:
        return {"variant": label, "mmgbsa_bind": None, "mmgbsa_std": None, "error": "no openmm"}

    ff = ForceField(OPENMM_CFG["forcefield"], OPENMM_CFG["implicit_solvent"])

    try:
        pdb = PDBFile(pdb_path)
    except Exception as e:
        return {"variant": label, "mmgbsa_bind": None, "mmgbsa_std": None, "error": str(e)}

    # Add missing hydrogens via Modeller (fast, no PDBFixer overhead)
    try:
        from openmm.app import Modeller
        modeller = Modeller(pdb.topology, pdb.positions)
        modeller.addHydrogens(ff, pH=7.0)
        top = modeller.topology
        pos = modeller.positions
    except Exception:
        top = pdb.topology
        pos = pdb.positions

    try:
        platform = Platform.getPlatformByName("CPU")
    except Exception:
        platform = Platform.getPlatformByName("Reference")

    # ----- Build complex system + simulation -----
    try:
        sys_complex = ff.createSystem(top, nonbondedCutoff=1.0 * unit.nanometers,
                                      constraints=None)
    except Exception as e:
        return {"variant": label, "mmgbsa_bind": None, "mmgbsa_std": None, "error": f"FF_complex: {e}"}

    integ_complex = LangevinMiddleIntegrator(
        OPENMM_CFG["temperature_K"] * unit.kelvin, 1.0 / unit.picosecond, 0.002 * unit.picoseconds)
    sim = Simulation(top, sys_complex, integ_complex, platform)
    sim.context.setPositions(pos)
    sim.minimizeEnergy(maxIterations=OPENMM_CFG["minimization_steps"])
    sim.step(EQUIL_STEPS)

    # ----- Build VHH sub-system Context (once) -----
    vhh_top, vhh_atom_idx = build_subsystem_topology(top, [VHH_CHAIN])
    try:
        sys_vhh = ff.createSystem(vhh_top, nonbondedCutoff=1.0 * unit.nanometers, constraints=None)
        integ_vhh = VerletIntegrator(0.001 * unit.picoseconds)
        ctx_vhh = Context(sys_vhh, integ_vhh, platform)
    except Exception as e:
        return {"variant": label, "mmgbsa_bind": None, "mmgbsa_std": None, "error": f"FF_vhh: {e}"}

    # ----- Build HER2 sub-system Context (once) -----
    ag_top, ag_atom_idx = build_subsystem_topology(top, [AG_CHAIN])
    try:
        sys_ag = ff.createSystem(ag_top, nonbondedCutoff=1.0 * unit.nanometers, constraints=None)
        integ_ag = VerletIntegrator(0.001 * unit.picoseconds)
        ctx_ag = Context(sys_ag, integ_ag, platform)
    except Exception as e:
        return {"variant": label, "mmgbsa_bind": None, "mmgbsa_std": None, "error": f"FF_ag: {e}"}

    # ----- Collect snapshots -----
    dg_list = []
    for _ in range(N_SNAPSHOTS):
        sim.step(SNAP_INTERVAL)
        state = sim.context.getState(getEnergy=True, getPositions=True)
        all_pos = state.getPositions(asNumpy=True)

        e_complex_kj = state.getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole)
        e_complex = e_complex_kj / 4.184

        try:
            ctx_vhh.setPositions([all_pos[i] for i in vhh_atom_idx])
            e_vhh_kj = ctx_vhh.getState(getEnergy=True).getPotentialEnergy().value_in_unit(
                unit.kilojoules_per_mole)
            e_vhh = e_vhh_kj / 4.184

            ctx_ag.setPositions([all_pos[i] for i in ag_atom_idx])
            e_ag_kj = ctx_ag.getState(getEnergy=True).getPotentialEnergy().value_in_unit(
                unit.kilojoules_per_mole)
            e_ag = e_ag_kj / 4.184

            dg_list.append(e_complex - e_vhh - e_ag)
        except Exception:
            continue

    del ctx_vhh, ctx_ag

    if not dg_list:
        return {"variant": label, "mmgbsa_bind": None, "mmgbsa_std": None, "error": "no snapshots"}

    mean_dg = sum(dg_list) / len(dg_list)
    std = (sum((x - mean_dg) ** 2 for x in dg_list) / max(len(dg_list) - 1, 1)) ** 0.5

    return {
        "variant": label,
        "mmgbsa_bind": round(mean_dg, 2),
        "mmgbsa_std": round(std, 2),
        "n_snapshots": len(dg_list),
        "dg_snapshots": [round(x, 2) for x in dg_list],
        "error": None,
    }


def run():
    print("=" * 65)
    print("L3 v2: Single-Trajectory Ensemble MM/GBSA")
    print(f"Candidates: {len(CANDIDATES)} | Snapshots: {N_SNAPSHOTS} each")
    print("=" * 65)

    results = []
    for label, mutations in CANDIDATES:
        print(f"\n[{label}]", flush=True)
        with tempfile.TemporaryDirectory(prefix=f"mmgbsa2_{label}_") as tmp:
            raw_pdb = build_mutant_pdb(mutations, tmp)
            if raw_pdb is None:
                print("  BUILD FAILED")
                results.append({"variant": label, "mmgbsa_bind": None,
                                 "mmgbsa_std": None, "n_snapshots": 0, "error": "build failed"})
                continue

            fixed_pdb = fix_pdb(raw_pdb)
            print(f"  PDB ready, running MD ({N_SNAPSHOTS} snapshots × {SNAP_INTERVAL*0.002:.0f} ps)...",
                  flush=True)
            row = compute_single_traj_mmgbsa(fixed_pdb, label)

        if row["mmgbsa_bind"] is not None:
            print(f"  ΔG_bind = {row['mmgbsa_bind']:.2f} ± {row['mmgbsa_std']:.2f} kcal/mol")
        else:
            print(f"  ERROR: {row['error']}")
        results.append(row)

    wt_bind = next((r["mmgbsa_bind"] for r in results if r["variant"] == "WT"
                    and r["mmgbsa_bind"] is not None), None)

    for r in results:
        if r["mmgbsa_bind"] is not None and wt_bind is not None:
            r["mmgbsa_ddg"] = round(r["mmgbsa_bind"] - wt_bind, 2)
        else:
            r["mmgbsa_ddg"] = None

    out_csv = OUTPUT_DIR / "openmm_v2_results.csv"
    fields = ["variant", "mmgbsa_bind", "mmgbsa_std", "mmgbsa_ddg", "n_snapshots", "error"]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    print("\n" + "=" * 65)
    print("RESULTS SUMMARY (sorted by ΔΔG):")
    print(f"{'Variant':<25} {'ΔG_bind':>10} {'±':>5} {'ΔΔG':>10}")
    print("-" * 55)
    for r in sorted(results, key=lambda x: (x.get("mmgbsa_ddg") or 999)):
        if r["mmgbsa_bind"] is not None:
            ddg = r.get("mmgbsa_ddg", "—")
            ddg_str = f"{ddg:>+10.2f}" if isinstance(ddg, float) else "        —"
            print(f"  {r['variant']:<23} {r['mmgbsa_bind']:>10.2f} {r['mmgbsa_std']:>5.2f} {ddg_str}")
    print("=" * 65)
    print(f"\nOutput: {out_csv}")
    return results


if __name__ == "__main__":
    run()
