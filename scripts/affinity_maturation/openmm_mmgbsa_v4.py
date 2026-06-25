"""
L3 v4: Single-point MM/GBSA (minimization only, no MD).

Rationale: Full MD is too slow for the HER2 ECD on CPU. Instead:
  1. Minimize complex (300 steps) → get minimized geometry
  2. Compute E_complex at minimized positions
  3. From SAME positions, compute E_VHH and E_HER2 without re-minimizing
     → consistent geometry, noise cancels when computing ΔΔG

For ΔΔG ranking between closely-related mutants this is adequate.
The key fix vs v1: all three energies come from the SAME conformation.

Truncated HER2: residues 520-620 (domain IV interface, 100 aa)
Total system: ~1900 heavy atoms → ~15-20 min for all 8 candidates
"""

import csv, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import yaml

SCRIPT_DIR  = Path(__file__).resolve().parent
CONFIG      = yaml.safe_load((SCRIPT_DIR / "config.yaml").read_text())
EVOEF2      = str((SCRIPT_DIR / CONFIG["paths"]["evoef2_exe"]).resolve())
COMPLEX_PDB = str((SCRIPT_DIR / CONFIG["paths"]["complex_pdb"]).resolve())
OUTPUT_DIR  = Path((SCRIPT_DIR / CONFIG["paths"]["output_dir"]).resolve())
VHH_CHAIN   = CONFIG["project"]["vhh_chain"]
AG_CHAIN    = CONFIG["project"]["antigen_chain"]
OPENMM_CFG  = CONFIG["openmm"]
MIN_STEPS   = OPENMM_CFG.get("minimization_steps", 300)

HER2_RESI_START = 520
HER2_RESI_END   = 620

CANDIDATES = [
    ("WT",              []),
    ("F112Y",           [{"site": 112, "wt_aa": "F", "mut_aa": "Y"}]),
    ("K70R",            [{"site": 70,  "wt_aa": "K", "mut_aa": "R"}]),
    ("Y67F",            [{"site": 67,  "wt_aa": "Y", "mut_aa": "F"}]),
    ("N62S",            [{"site": 62,  "wt_aa": "N", "mut_aa": "S"}]),
    ("Y67F+K70R",       [{"site": 67,  "wt_aa": "Y", "mut_aa": "F"},
                          {"site": 70,  "wt_aa": "K", "mut_aa": "R"}]),
    ("Y67F+F112Y",      [{"site": 67,  "wt_aa": "Y", "mut_aa": "F"},
                          {"site": 112, "wt_aa": "F", "mut_aa": "Y"}]),
    ("Y67F+N62S+F112Y", [{"site": 67,  "wt_aa": "Y", "mut_aa": "F"},
                          {"site": 62,  "wt_aa": "N", "mut_aa": "S"},
                          {"site": 112, "wt_aa": "F", "mut_aa": "Y"}]),
]


def build_mutant_pdb(mutations, work_dir):
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
    m = os.path.join(work_dir, f"{stem}_Model_0001.pdb")
    return m if os.path.exists(m) else None


def truncate_her2(pdb_path, out_path):
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
            if chain == VHH_CHAIN or (chain == AG_CHAIN and HER2_RESI_START <= resi <= HER2_RESI_END):
                fo.write(line)
                kept += 1
        fo.write("END\n")
    return kept


def compute_mmgbsa_minimonly(pdb_path, label):
    """Minimize complex once; compute E_complex, E_VHH, E_HER2 from same geometry."""
    try:
        from openmm.app import PDBFile, ForceField, Simulation, Modeller
        from openmm import LangevinMiddleIntegrator, VerletIntegrator, Context, Platform, unit
    except ImportError:
        return {"variant": label, "mmgbsa_bind": None, "error": "no openmm"}

    ff = ForceField(OPENMM_CFG["forcefield"], OPENMM_CFG["implicit_solvent"])

    try:
        pdb = PDBFile(pdb_path)
        mod = Modeller(pdb.topology, pdb.positions)
        mod.addHydrogens(ff, pH=7.0)
        top, pos = mod.topology, mod.positions
    except Exception as e:
        return {"variant": label, "mmgbsa_bind": None, "error": f"prep: {e}"}

    try:
        platform = Platform.getPlatformByName("CPU")
    except Exception:
        platform = Platform.getPlatformByName("Reference")

    # ---- minimize complex ----
    try:
        sys_c = ff.createSystem(top, nonbondedCutoff=1.0 * unit.nanometers, constraints=None)
    except Exception as e:
        return {"variant": label, "mmgbsa_bind": None, "error": f"FF: {e}"}

    integ = LangevinMiddleIntegrator(300 * unit.kelvin, 1.0 / unit.picosecond, 0.002 * unit.picoseconds)
    sim = Simulation(top, sys_c, integ, platform)
    sim.context.setPositions(pos)
    sim.minimizeEnergy(maxIterations=MIN_STEPS)
    state = sim.context.getState(getEnergy=True, getPositions=True)
    min_pos = state.getPositions(asNumpy=True)
    e_complex = state.getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole) / 4.184

    # ---- build VHH sub-topology from minimized positions ----
    def sub_energy(keep_chain):
        from openmm.app import Topology
        new_top = Topology()
        atom_idx = []
        for chain in top.chains():
            if chain.id != keep_chain:
                continue
            nc = new_top.addChain(chain.id)
            for res in chain.residues():
                nr = new_top.addResidue(res.name, nc)
                for atom in res.atoms():
                    new_top.addAtom(atom.name, atom.element, nr)
                    atom_idx.append(atom.index)
        sub_pos = [min_pos[i] for i in atom_idx]
        sys_s = ff.createSystem(new_top, nonbondedCutoff=1.0 * unit.nanometers, constraints=None)
        ctx = Context(sys_s, VerletIntegrator(0.001 * unit.picoseconds), platform)
        ctx.setPositions(sub_pos)
        e = ctx.getState(getEnergy=True).getPotentialEnergy().value_in_unit(
            unit.kilojoules_per_mole) / 4.184
        del ctx
        return e

    try:
        e_vhh = sub_energy(VHH_CHAIN)
        e_ag  = sub_energy(AG_CHAIN)
    except Exception as e:
        return {"variant": label, "mmgbsa_bind": None, "error": f"sub: {e}"}

    dg = e_complex - e_vhh - e_ag
    return {
        "variant": label,
        "e_complex": round(e_complex, 2),
        "e_vhh":     round(e_vhh, 2),
        "e_ag":      round(e_ag, 2),
        "mmgbsa_bind": round(dg, 2),
        "mmgbsa_std":  None,
        "error": None,
    }


def run():
    print("=" * 65)
    print("L3 v4: Single-Point MM/GBSA (minimize-only, single-trajectory)")
    print(f"HER2 truncated {HER2_RESI_START}-{HER2_RESI_END}  |  {MIN_STEPS} minimization steps")
    print("=" * 65)

    results = []
    for label, mutations in CANDIDATES:
        print(f"\n[{label}]", flush=True)
        t0 = time.time()
        with tempfile.TemporaryDirectory(prefix=f"mmgbsa4_{label}_") as tmp:
            full_pdb = build_mutant_pdb(mutations, tmp)
            if full_pdb is None:
                print("  BUILD FAILED"); results.append({"variant": label, "mmgbsa_bind": None, "error": "build"}); continue
            trunc = os.path.join(tmp, "trunc.pdb")
            n = truncate_her2(full_pdb, trunc)
            print(f"  {n} heavy atoms  (addH + minimize {MIN_STEPS} steps)...", flush=True)
            row = compute_mmgbsa_minimonly(trunc, label)
        elapsed = time.time() - t0
        if row["mmgbsa_bind"] is not None:
            print(f"  ΔG = {row['mmgbsa_bind']:.2f} kcal/mol  ({elapsed:.0f}s)")
        else:
            print(f"  ERROR: {row['error']}  ({elapsed:.0f}s)")
        results.append(row)

    wt = next((r["mmgbsa_bind"] for r in results if r["variant"] == "WT" and r["mmgbsa_bind"] is not None), None)
    for r in results:
        r["mmgbsa_ddg"] = round(r["mmgbsa_bind"] - wt, 2) if r["mmgbsa_bind"] is not None and wt else None

    out_csv = OUTPUT_DIR / "openmm_v4_results.csv"
    fields = ["variant", "e_complex", "e_vhh", "e_ag", "mmgbsa_bind", "mmgbsa_ddg", "error"]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(results)

    print("\n" + "=" * 65)
    print(f"{'Variant':<25} {'ΔG':>10} {'ΔΔG':>10}")
    print("-" * 50)
    for r in sorted(results, key=lambda x: x.get("mmgbsa_ddg") or 999):
        if r["mmgbsa_bind"] is not None:
            print(f"  {r['variant']:<23} {r['mmgbsa_bind']:>10.2f} {r['mmgbsa_ddg']:>+10.2f}")
    print(f"\nOutput: {out_csv}")
    print("=" * 65)
    return results


if __name__ == "__main__":
    run()
