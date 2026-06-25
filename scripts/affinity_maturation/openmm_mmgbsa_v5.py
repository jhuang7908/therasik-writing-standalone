"""
L3 v5: Single-Point MM/GBSA  —  working version.

Key fixes vs earlier attempts:
  - Use PDBFixer (not Modeller.addHydrogens) for H addition → handles truncated chains
  - Use amber14/protein.ff14SB.xml (not amber14-all.xml) → createSystem in 4s not 10min
  - Single-trajectory: minimize complex, compute E_vhh and E_ag from same coordinates
  - HER2 truncated to residues 520-620 (~100 aa, domain IV binding site)

Expected runtime: ~6–12 min/candidate (CPU) × N.

（ WT + G49A/S + F112L + ）:

    conda activate affmat
    python scripts/affinity_maturation/openmm_mmgbsa_v5.py --doubles-only

: affinity_maturation_v2/openmm_v5_doubles_results.csv
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

HER2_START, HER2_END = 520, 620


def _singles_from_config():
    out = []
    for mut_block in CONFIG.get("mutations_l3", []):
        site = mut_block["site"]
        wt_aa = mut_block["wt"]
        for mut_aa in mut_block["candidates"]:
            label = f"{wt_aa}{site}{mut_aa}"
            out.append((label, [{"site": site, "wt_aa": wt_aa, "mut_aa": mut_aa}]))
    return out


def doubles_run_candidates():
    """WT +  G49A/S、F112L + config （）。"""
    out = [("WT", [])]
    out.append(("G49A", [{"site": 49, "wt_aa": "G", "mut_aa": "A"}]))
    out.append(("G49S", [{"site": 49, "wt_aa": "G", "mut_aa": "S"}]))
    out.append(("F112L", [{"site": 112, "wt_aa": "F", "mut_aa": "L"}]))
    for d in CONFIG.get("mutations_l3_doubles", []):
        muts = [
            {"site": m["site"], "wt_aa": m["wt"], "mut_aa": m["mut_aa"]}
            for m in d["mutations"]
        ]
        out.append((d["name"], muts))
    return out


CANDIDATES = [("WT", [])] + _singles_from_config()


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


def truncate_and_fix(full_pdb, work_dir):
    """Truncate HER2, run PDBFixer, return (topology, positions, n_heavy, n_total).

    Returns fixer.topology and fixer.positions directly to avoid PDB round-trip
    which loses bond information needed for FF template matching.
    """
    from pdbfixer import PDBFixer

    trunc = os.path.join(work_dir, "trunc.pdb")
    n_heavy = 0
    with open(full_pdb) as fi, open(trunc, "w") as fo:
        for line in fi:
            if not line.startswith(("ATOM", "HETATM")):
                continue
            chain = line[21]
            try:
                resi = int(line[22:26].strip())
            except ValueError:
                continue
            if chain == VHH_CHAIN or (chain == AG_CHAIN and HER2_START <= resi <= HER2_END):
                fo.write(line)
                n_heavy += 1
        fo.write("END\n")

    fixer = PDBFixer(filename=trunc)
    fixer.findMissingResidues()
    fixer.findMissingAtoms()
    fixer.addMissingAtoms()
    fixer.addMissingHydrogens(7.0)

    top = fixer.topology
    pos = fixer.positions
    # PDBFixer topology has atoms but no standard bonds; PDBFile does this on load.
    top.createStandardBonds()
    top.createDisulfideBonds(pos)

    return top, pos, n_heavy, top.getNumAtoms()


def sub_energy(ff, full_top, min_pos, keep_chain, platform):
    """Single-point energy for one chain using minimized complex positions."""
    from openmm.app import Topology
    from openmm import VerletIntegrator, Context, unit
    import numpy as np

    new_top = Topology()
    idx_map = []
    for chain in full_top.chains():
        if chain.id != keep_chain:
            continue
        nc = new_top.addChain(chain.id)
        for res in chain.residues():
            nr = new_top.addResidue(res.name, nc, res.id, res.insertionCode)
            for atom in res.atoms():
                new_top.addAtom(atom.name, atom.element, nr, atom.id)
                idx_map.append(atom.index)

    new_top.createStandardBonds()
    sub_arr = np.take(min_pos, idx_map, axis=0)
    sub_pos = sub_arr * unit.nanometers
    
    # ff14SB requires disulfide bonds to be explicitly created
    # However, createDisulfideBonds() can fail if positions are slightly off
    # We ignore disulfides for single point energy of sub-chains since we just want the non-bonded + internal
    # new_top.createDisulfideBonds(sub_pos)
    
    sys_s = ff.createSystem(new_top, nonbondedCutoff=1.0 * unit.nanometers, constraints=None)
    ctx = Context(sys_s, VerletIntegrator(0.001 * unit.picoseconds), platform)
    ctx.setPositions(sub_pos)
    e = ctx.getState(getEnergy=True).getPotentialEnergy().value_in_unit(
        unit.kilojoules_per_mole) / 4.184
    del ctx
    return e


def compute_mmgbsa(topology, positions, label):
    """Compute MM/GBSA using topology+positions directly from PDBFixer (no PDB round-trip)."""
    from openmm.app import ForceField, Simulation
    from openmm import LangevinMiddleIntegrator, Platform, unit

    ff = ForceField("amber14/protein.ff14SB.xml", "implicit/obc2.xml")

    # Force CPU Platform
    platform = Platform.getPlatformByName("CPU")
    prop = {}

    sys_c = ff.createSystem(topology, nonbondedCutoff=1.0 * unit.nanometers, constraints=None)
    integ = LangevinMiddleIntegrator(300 * unit.kelvin, 1.0 / unit.picosecond, 0.002 * unit.picoseconds)
    sim = Simulation(topology, sys_c, integ, platform, prop)
    sim.context.setPositions(positions)
    sim.minimizeEnergy(maxIterations=MIN_STEPS)

    state = sim.context.getState(getEnergy=True, getPositions=True)
    min_pos = state.getPositions(asNumpy=True)
    e_complex = state.getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole) / 4.184

    e_vhh = sub_energy(ff, topology, min_pos, VHH_CHAIN, platform)
    e_ag  = sub_energy(ff, topology, min_pos, AG_CHAIN,  platform)

    dg = e_complex - e_vhh - e_ag
    return {"variant": label, "e_complex": round(e_complex, 2),
            "e_vhh": round(e_vhh, 2), "e_ag": round(e_ag, 2),
            "mmgbsa_bind": round(dg, 2), "error": None}


def run(candidates=None, out_csv_name="openmm_v5_results.csv"):
    print("=" * 65)
    print("L3 v5: MM/GBSA  (PDBFixer + protein.ff14SB)")
    print(f"HER2 {HER2_START}-{HER2_END}  |  minimize {MIN_STEPS} steps")
    print("=" * 65)

    to_run = candidates if candidates is not None else CANDIDATES
    results = []
    for label, mutations in to_run:
        print(f"\n[{label}]", flush=True)
        t0 = time.time()
        with tempfile.TemporaryDirectory(prefix=f"mmgbsa5_{label}_") as tmp:
            full_pdb = build_mutant_pdb(mutations, tmp)
            if full_pdb is None:
                print("  BUILD FAILED")
                results.append({"variant": label, "mmgbsa_bind": None, "error": "build"})
                continue
            print("  truncating + PDBFixer...", flush=True)
            try:
                top, pos, n_heavy, n_total = truncate_and_fix(full_pdb, tmp)
            except Exception as e:
                print(f"  PDBFixer ERROR: {e}")
                results.append({"variant": label, "mmgbsa_bind": None, "error": str(e)})
                continue
            t1 = time.time()
            print(f"  {n_heavy} heavy → {n_total} total atoms  ({t1-t0:.0f}s prep)  minimizing...", flush=True)
            try:
                row = compute_mmgbsa(top, pos, label)
            except Exception as e:
                print(f"  MM/GBSA ERROR: {e}")
                results.append({"variant": label, "mmgbsa_bind": None, "error": str(e)})
                continue

        elapsed = time.time() - t0
        print(f"  ΔG = {row['mmgbsa_bind']:.2f} kcal/mol  ({elapsed:.0f}s total)")
        results.append(row)

    wt = next((r["mmgbsa_bind"] for r in results if r["variant"] == "WT" and r["mmgbsa_bind"]), None)
    for r in results:
        r["mmgbsa_ddg"] = round(r["mmgbsa_bind"] - wt, 2) if r["mmgbsa_bind"] and wt else None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = OUTPUT_DIR / out_csv_name
    fields = ["variant", "e_complex", "e_vhh", "e_ag", "mmgbsa_bind", "mmgbsa_ddg", "error"]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(results)

    print("\n" + "=" * 65)
    print(f"{'Variant':<25} {'ΔG':>10} {'ΔΔG':>10}")
    print("-" * 50)
    for r in sorted(results, key=lambda x: x.get("mmgbsa_ddg") or 999):
        if r.get("mmgbsa_bind") is not None:
            print(f"  {r['variant']:<23} {r['mmgbsa_bind']:>10.2f} {r['mmgbsa_ddg']:>+10.2f}")
    print(f"\nOutput: {out_csv}")
    print("=" * 65)

    # ：（ WT  ΔΔG）
    if out_csv_name == "openmm_v5_doubles_results.csv" and wt is not None:
        ddg = {r["variant"]: r["mmgbsa_ddg"] for r in results if r.get("mmgbsa_ddg") is not None}
        g49a, g49s, f112l = ddg.get("G49A"), ddg.get("G49S"), ddg.get("F112L")
        d1 = ddg.get("G49A+F112L")
        d2 = ddg.get("G49S+F112L")
        print("\n── （ΔΔG  WT； kcal/mol）──")
        if g49a is not None and f112l is not None and d1 is not None:
            pred = g49a + f112l
            print(f"  G49A+F112L:  ΔΔG={d1:+.2f}  |   ΔΔG(G49A)+ΔΔG(F112L)={pred:+.2f}  |  ={d1-pred:+.2f}")
        if g49s is not None and f112l is not None and d2 is not None:
            pred = g49s + f112l
            print(f"  G49S+F112L:  ΔΔG={d2:+.2f}  |   ΔΔG(G49S)+ΔΔG(F112L)={pred:+.2f}  |  ={d2-pred:+.2f}")

    return results


if __name__ == "__main__":
    if "--doubles-only" in sys.argv:
        run(candidates=doubles_run_candidates(), out_csv_name="openmm_v5_doubles_results.csv")
    else:
        run()
