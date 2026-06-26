#!/usr/bin/env python
"""
FGF23 VAM Pre-Stage: OpenMM energy minimization on Boltz Model-0 PDB.

Reads:  projects/fgf 23/boltz/FGF23/.../FGF23_model_0.pdb
Writes: projects/fgf 23/vam_boltz_scan/FGF23/FGF23_relaxed.pdb
        projects/fgf 23/vam_boltz_scan/FGF23/FGF23_relax_report.json

GPU auto-detected; falls back to CPU if no CUDA available.

Usage (conda env affmat):
  conda run -n affmat python scripts/run_fgf23_relax.py
  conda run -n affmat python scripts/run_fgf23_relax.py --steps 1000 --dry-run

Server (GPU):
  OPENMM_DEFAULT_PLATFORM=CUDA conda run -n affmat python scripts/run_fgf23_relax.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROJECT_DIR  = ROOT / "projects/fgf 23"
BOLTZ_PDB    = PROJECT_DIR / "boltz/FGF23/boltz_results_FGF23/predictions/FGF23/FGF23_model_0.pdb"
VAM_DIR      = PROJECT_DIR / "vam_boltz_scan/FGF23"
RELAXED_PDB  = VAM_DIR / "FGF23_relaxed.pdb"
REPORT_JSON  = VAM_DIR / "FGF23_relax_report.json"

DEFAULT_STEPS = 2000


def _detect_platform() -> str:
    """Return OpenMM platform name: CUDA > OpenCL > CPU."""
    try:
        import openmm
        platforms = [openmm.Platform.getPlatform(i).getName()
                     for i in range(openmm.Platform.getNumPlatforms())]
        print(f"[relax] Available platforms: {platforms}", flush=True)
        for name in ("CUDA", "OpenCL"):
            if name in platforms:
                return name
        return "CPU"
    except Exception as e:
        print(f"[relax] Platform detection error: {e}", flush=True)
        return "CPU"


def _run_openmm(
    input_pdb: Path,
    output_pdb: Path,
    *,
    steps: int,
    platform: str,
) -> dict:
    """Run OpenMM FF14SB + implicit solvent minimization + short NVT."""
    import openmm
    import openmm.app as app
    import openmm.unit as unit
    from pdbfixer import PDBFixer

    t0 = time.time()

    # 1. PDBFixer — add missing atoms, remove HETATM, cap terminals
    print(f"[relax] PDBFixer: {input_pdb.name}", flush=True)
    fixer = PDBFixer(str(input_pdb))
    fixer.findMissingResidues()
    fixer.findNonstandardResidues()
    fixer.replaceNonstandardResidues()
    fixer.removeHeterogens(keepWater=False)
    fixer.findMissingAtoms()
    fixer.addMissingAtoms()
    fixer.addMissingHydrogens(7.4)

    # 2. Force field
    ff = app.ForceField("amber14-all.xml", "implicit/gbn2.xml")
    modeller = app.Modeller(fixer.topology, fixer.positions)
    # OpenMM 8+: implicit solvent configured via XML (implicit/gbn2.xml);
    # do not pass implicitSolvent kwarg to createSystem.
    system = ff.createSystem(
        modeller.topology,
        nonbondedMethod=app.NoCutoff,
        constraints=app.HBonds,
    )

    # 3. Platform
    platform_obj = openmm.Platform.getPlatformByName(platform)
    integrator   = openmm.LangevinMiddleIntegrator(300 * unit.kelvin, 1 / unit.picosecond, 0.002 * unit.picoseconds)

    sim = app.Simulation(modeller.topology, system, integrator, platform_obj)
    sim.context.setPositions(modeller.positions)

    # 4. Energy minimization
    print(f"[relax] Energy minimization ...", flush=True)
    sim.minimizeEnergy()

    # 5. Short NVT equilibration
    print(f"[relax] NVT equilibration: {steps} steps", flush=True)
    sim.step(steps)

    # 6. Write PDB (OpenMM renames chains to A/B/C; rename back to H/L/A)
    output_pdb.parent.mkdir(parents=True, exist_ok=True)
    positions = sim.context.getState(getPositions=True).getPositions()
    tmp_pdb = output_pdb.with_suffix(".tmp.pdb")
    with tmp_pdb.open("w") as fh:
        app.PDBFile.writeFile(sim.topology, positions, fh)

    # Chain rename map: OpenMM A→H (VH), B→L (VL), C→A (antigen)
    chain_map = {"A": "H", "B": "L", "C": "A"}
    lines = tmp_pdb.read_text(encoding="utf-8").splitlines(keepends=True)
    fixed = []
    for line in lines:
        if line.startswith(("ATOM", "HETATM", "TER", "ANISOU")) and len(line) > 21:
            old_chain = line[21]
            new_chain = chain_map.get(old_chain, old_chain)
            line = line[:21] + new_chain + line[22:]
        fixed.append(line)
    # Strip hydrogen atoms (EvoEF2 requires heavy-atom-only PDB)
    heavy_only = [
        line for line in fixed
        if not (line.startswith(("ATOM", "HETATM")) and
                len(line) > 13 and line[12:16].strip().startswith("H"))
    ]
    output_pdb.write_text("".join(heavy_only), encoding="utf-8")
    tmp_pdb.unlink()
    n_removed = len(fixed) - len(heavy_only)
    print(f"[relax] Chain renaming A→H, B→L, C→A applied; {n_removed} H-atom lines stripped.", flush=True)

    elapsed = round(time.time() - t0, 1)
    print(f"[relax] Done. Platform={platform}  steps={steps}  elapsed={elapsed}s", flush=True)
    return {"platform": platform, "steps": steps, "elapsed_s": elapsed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--steps",    type=int,  default=DEFAULT_STEPS,
                        help=f"NVT steps after minimization (default: {DEFAULT_STEPS}).")
    parser.add_argument("--platform", default=None,
                        help="OpenMM platform override (CUDA/OpenCL/CPU).")
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--in-pdb",   type=Path, default=BOLTZ_PDB,
                        help="Input Boltz PDB.")
    parser.add_argument("--out-pdb",  type=Path, default=RELAXED_PDB,
                        help="Output relaxed PDB.")
    args = parser.parse_args(argv)

    in_pdb  = args.in_pdb.resolve()
    out_pdb = args.out_pdb.resolve()

    if not in_pdb.is_file():
        print(f"ERROR: Input PDB not found: {in_pdb}", file=sys.stderr)
        return 1

    platform = args.platform or _detect_platform()
    print(f"[relax] Input  : {in_pdb}")
    print(f"[relax] Output : {out_pdb}")
    print(f"[relax] Steps  : {args.steps}")
    print(f"[relax] Platform: {platform}")

    if args.dry_run:
        print("[relax] Dry-run mode: no computation performed.")
        return 0

    result = _run_openmm(in_pdb, out_pdb, steps=args.steps, platform=platform)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "clone": "FGF23",
        "in_pdb":  str(in_pdb.relative_to(ROOT)).replace("\\", "/"),
        "out_pdb": str(out_pdb.relative_to(ROOT)).replace("\\", "/"),
        **result,
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[relax] Report: {REPORT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
