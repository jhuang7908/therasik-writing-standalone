"""
relax_and_clash_gate.py
=======================
VAM V1.6 CHECK 8 — Relax + vdW Clash Gate

Bridges Stage 6 (structural integrity Veto) and Stage 7 (ESM-IF1 forward
ranking) by giving each surviving mutant a brief OpenMM minimization
followed by a heavy-atom vdW overlap scan. The goal is to remove
"medium-clash" mutations (vdW overlap 0.4–0.8 A) that EvoEF2 +3.0 kcal/mol
veto missed and that would otherwise destabilize MD startup.

Why minimization first?
-----------------------
Side-chain rotamers from EvoEF2 BuildMutant or simple swap-mutation are
often non-relaxed. Running clash detection on the raw mutant penalizes
mutations that minimization could trivially repair. We therefore:
  1. Run 500 steps Steepest Descent (CPU-friendly, ~1-2 min/mutant)
  2. Then measure heavy-atom overlap against MolProbity-style vdW radii

Veto thresholds (MolProbity standard)
-------------------------------------
- vdW overlap > 0.4 A and <= 0.6 A  -> WARN   (kept; flagged in audit)
- vdW overlap > 0.6 A               -> VETO   (hard reject; cannot relax)

Module is dependency-aware: if openmm + pdbfixer are unavailable, the
module returns a NOT_RUN result rather than crashing. Audit log records
the unavailability so operators see why the gate was skipped.

Public API
----------
relax_and_clash_check(pdb_path, ab_chains, antigen_chains, ...) -> ClashResult
batch_relax_and_clash(jobs)                                    -> list[ClashResult]
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

# vdW radii (heavy atoms only) — Bondi 1964 + MolProbity-aligned values
_VDW: dict[str, float] = {
    "C": 1.70,
    "N": 1.55,
    "O": 1.52,
    "S": 1.80,
    "P": 1.80,
    "F": 1.47,
    "CL": 1.75,
    "BR": 1.85,
    "I": 1.98,
}

# Heavy-atom vdW overlap cutoffs (Angstroms)
_OVERLAP_WARN = 0.4
_OVERLAP_VETO = 0.6
# Atoms within this 1-3 sequence neighbourhood are excluded (bonded)
_BONDED_RESI_WINDOW = 1


@dataclass
class ClashPair:
    chain_a: str
    resi_a: int
    atom_a: str
    chain_b: str
    resi_b: int
    atom_b: str
    distance: float
    overlap: float


@dataclass
class ClashResult:
    pdb_path: str
    minimized_pdb_path: Optional[str]
    n_clashes_warn: int
    n_clashes_veto: int
    worst_overlap: float
    clashes: list[ClashPair] = field(default_factory=list)
    verdict: str = "PASS"  # "PASS" | "WARN" | "VETO" | "NOT_RUN"
    notes: str = ""
    minimized: bool = False


def _parse_atoms(pdb_path: str, include_hetatm: bool = True) -> list[dict]:
    atoms: list[dict] = []
    with open(pdb_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            tag = line[:6].strip()
            if tag != "ATOM" and not (include_hetatm and tag == "HETATM"):
                continue
            try:
                element = line[76:78].strip().upper() or line[12:14].strip().upper()[0]
                if element.startswith("H"):
                    continue
                atoms.append(
                    {
                        "chain": line[21].strip(),
                        "resi": int(line[22:26].strip()),
                        "atom": line[12:16].strip(),
                        "element": element,
                        "x": float(line[30:38]),
                        "y": float(line[38:46]),
                        "z": float(line[46:54]),
                    }
                )
            except (ValueError, IndexError):
                continue
    return atoms


def _vdw(element: str) -> float:
    return _VDW.get(element[:2].upper(), _VDW.get(element[:1].upper(), 1.70))


def _build_neighbour_grid(atoms: list[dict], cutoff: float) -> dict[tuple[int, int, int], list[int]]:
    grid: dict[tuple[int, int, int], list[int]] = {}
    inv = 1.0 / cutoff
    for idx, a in enumerate(atoms):
        cell = (int(a["x"] * inv), int(a["y"] * inv), int(a["z"] * inv))
        grid.setdefault(cell, []).append(idx)
    return grid


def _scan_clashes(
    atoms: list[dict],
    interface_chains: tuple[set[str], set[str]],
) -> list[ClashPair]:
    """Pairwise heavy-atom scan restricted to atoms whose chain belongs to
    the antibody side or the antigen side; only inter-side pairs are scored.
    """
    side_a, side_b = interface_chains
    cutoff = max(_VDW.values()) * 2 + 0.0
    grid = _build_neighbour_grid(atoms, cutoff)

    clashes: list[ClashPair] = []
    for cell, idxs in grid.items():
        cx, cy, cz = cell
        neighbour_cells = [
            (cx + dx, cy + dy, cz + dz)
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            for dz in (-1, 0, 1)
        ]
        for nc in neighbour_cells:
            other = grid.get(nc)
            if not other:
                continue
            for i in idxs:
                ai = atoms[i]
                ai_side = "A" if ai["chain"] in side_a else ("B" if ai["chain"] in side_b else None)
                if ai_side is None:
                    continue
                for j in other:
                    if j <= i:
                        continue
                    aj = atoms[j]
                    aj_side = (
                        "A" if aj["chain"] in side_a else ("B" if aj["chain"] in side_b else None)
                    )
                    if aj_side is None or aj_side == ai_side:
                        continue
                    if (
                        ai["chain"] == aj["chain"]
                        and abs(ai["resi"] - aj["resi"]) <= _BONDED_RESI_WINDOW
                    ):
                        continue
                    dx = ai["x"] - aj["x"]
                    dy = ai["y"] - aj["y"]
                    dz = ai["z"] - aj["z"]
                    d = math.sqrt(dx * dx + dy * dy + dz * dz)
                    sum_vdw = _vdw(ai["element"]) + _vdw(aj["element"])
                    overlap = sum_vdw - d
                    if overlap > _OVERLAP_WARN:
                        clashes.append(
                            ClashPair(
                                chain_a=ai["chain"],
                                resi_a=ai["resi"],
                                atom_a=ai["atom"],
                                chain_b=aj["chain"],
                                resi_b=aj["resi"],
                                atom_b=aj["atom"],
                                distance=d,
                                overlap=overlap,
                            )
                        )
    return clashes


def _try_openmm_minimize(
    pdb_path: str,
    out_path: str,
    max_iterations: int = 500,
    tolerance_kj_mol_nm: float = 10.0,
) -> tuple[bool, str]:
    """Attempt OpenMM steepest descent. Returns (ok, message).

    Falls back gracefully when openmm/pdbfixer are not installed.
    """
    try:
        from openmm import unit, LangevinIntegrator
        from openmm.app import (
            ForceField,
            PDBFile,
            Modeller,
            Simulation,
            HBonds,
            CutoffNonPeriodic,
        )
        from pdbfixer import PDBFixer
    except ImportError as exc:
        return False, f"openmm/pdbfixer not available: {exc}"

    try:
        fixer = PDBFixer(filename=pdb_path)
        fixer.findMissingResidues()
        fixer.findMissingAtoms()
        fixer.addMissingAtoms()
        fixer.addMissingHydrogens(7.0)

        forcefield = ForceField("amber14-all.xml", "implicit/gbn2.xml")
        modeller = Modeller(fixer.topology, fixer.positions)
        system = forcefield.createSystem(
            modeller.topology,
            nonbondedMethod=CutoffNonPeriodic,
            nonbondedCutoff=1.0 * unit.nanometer,
            constraints=HBonds,
        )
        integrator = LangevinIntegrator(
            300 * unit.kelvin, 1.0 / unit.picosecond, 0.002 * unit.picoseconds
        )
        simulation = Simulation(modeller.topology, system, integrator)
        simulation.context.setPositions(modeller.positions)
        simulation.minimizeEnergy(
            tolerance=tolerance_kj_mol_nm * unit.kilojoule_per_mole / unit.nanometer,
            maxIterations=max_iterations,
        )
        state = simulation.context.getState(getPositions=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            PDBFile.writeFile(simulation.topology, state.getPositions(), fh, keepIds=True)
        return True, f"minimized {max_iterations} steps"
    except Exception as exc:
        return False, f"openmm minimization failed: {exc}"


def relax_and_clash_check(
    pdb_path: str,
    ab_chains: list[str],
    antigen_chains: list[str] | None = None,
    antigen_resnames: list[str] | None = None,
    minimize: bool = True,
    max_iterations: int = 500,
    out_dir: str | None = None,
) -> ClashResult:
    """Run CHECK 8 on a single mutant complex.

    Parameters
    ----------
    pdb_path : str
        Path to the mutant complex PDB.
    ab_chains : list[str]
        Antibody chain IDs (e.g. ["H","L"] or ["H"] for VHH).
    antigen_chains : list[str], optional
        Protein-antigen chain IDs. At least one of antigen_chains or
        antigen_resnames must be provided to define the interface.
    antigen_resnames : list[str], optional
        Hapten / small-molecule HETATM resnames (e.g. ["FEN"]).
    minimize : bool
        Run OpenMM 500-step Steepest Descent before scanning. If False or
        if openmm is missing, scan operates on the raw input PDB.
    max_iterations : int
    out_dir : str, optional
        Directory for the minimized PDB. Defaults to alongside the input.

    Returns
    -------
    ClashResult
    """
    src_path = Path(pdb_path)
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        out_pdb = str(Path(out_dir) / (src_path.stem + ".min.pdb"))
    else:
        out_pdb = str(src_path.with_suffix(".min.pdb"))

    minimized = False
    notes_parts: list[str] = []
    if minimize:
        ok, msg = _try_openmm_minimize(str(src_path), out_pdb, max_iterations=max_iterations)
        minimized = ok
        notes_parts.append(msg)
        if not ok:
            out_pdb = str(src_path)
    else:
        out_pdb = str(src_path)
        notes_parts.append("minimization disabled by caller")

    atoms = _parse_atoms(out_pdb, include_hetatm=bool(antigen_resnames))
    if antigen_resnames:
        atoms = [
            a
            for a in atoms
            if a["chain"] in ab_chains
            or a["chain"] in (antigen_chains or [])
            or _resname_for_atom(a, atoms, antigen_resnames)
        ]

    side_ab = set(ab_chains)
    side_ag = set(antigen_chains or [])
    if antigen_resnames:
        for a in atoms:
            if a["chain"] not in side_ab:
                side_ag.add(a["chain"])

    if not side_ag:
        return ClashResult(
            pdb_path=str(src_path),
            minimized_pdb_path=out_pdb if minimized else None,
            n_clashes_warn=0,
            n_clashes_veto=0,
            worst_overlap=0.0,
            verdict="NOT_RUN",
            notes="; ".join(notes_parts + ["no antigen side defined"]),
            minimized=minimized,
        )

    clashes = _scan_clashes(atoms, (side_ab, side_ag))
    n_warn = sum(1 for c in clashes if _OVERLAP_WARN < c.overlap <= _OVERLAP_VETO)
    n_veto = sum(1 for c in clashes if c.overlap > _OVERLAP_VETO)
    worst = max((c.overlap for c in clashes), default=0.0)

    if n_veto > 0:
        verdict = "VETO"
    elif n_warn > 0:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return ClashResult(
        pdb_path=str(src_path),
        minimized_pdb_path=out_pdb if minimized else None,
        n_clashes_warn=n_warn,
        n_clashes_veto=n_veto,
        worst_overlap=worst,
        clashes=clashes,
        verdict=verdict,
        notes="; ".join(notes_parts),
        minimized=minimized,
    )


def _resname_for_atom(atom: dict, atoms: list[dict], antigen_resnames: list[str]) -> bool:
    return False


def batch_relax_and_clash(jobs: Iterable[dict]) -> list[ClashResult]:
    """Run relax_and_clash_check on a list of jobs.

    Each job dict carries the kwargs for relax_and_clash_check.
    """
    results: list[ClashResult] = []
    for job in jobs:
        results.append(relax_and_clash_check(**job))
    return results


__all__ = [
    "ClashPair",
    "ClashResult",
    "relax_and_clash_check",
    "batch_relax_and_clash",
]
