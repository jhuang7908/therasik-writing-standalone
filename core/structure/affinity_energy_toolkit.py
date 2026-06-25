"""
Affinity Energy Toolkit
=======================
Unified Python API for six free/open-source binding-affinity and
mutation-energy tools:

  0. EvoEF2           — Physics-based ΔΔG_bind scan (fastest, MIT)
  1. PRODIGY          — IC-based ΔG / Kd prediction (fast, MIT)
  2. OpenMM MM/GBSA   — Physics-based ΔΔG (high accuracy, MIT)
  3. ESM-IF1          — Language-model inverse-folding ΔΔG (MIT)
  4. ThermoMPNN       — GNN ΔΔG + ΔTm (MIT)
  5. AntiFold         — Antibody CDR log-likelihood ΔΔG proxy (MIT)

Tool locations
--------------
  Source in tools/   : EvoEF2 (EvoEF2_src/), ProteinMPNN, ThermoMPNN, AntiFold, EpiScan
  pip packages       : prodigy-prot, fair-esm (ESM-IF1), openmm, ablang
  NOT in this toolkit: ProteinMPNN (sequence design, not ΔΔG)
                       EpiScan (epitope mapping / immunogenicity, not affinity)

All tools run in the `affmat` conda environment.
Python interpreter: d:/Users/NextVivo/miniconda3/envs/affmat/python.exe

Typical usage
-------------
from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit

tk = AffinityEnergyToolkit(
    complex_pdb   = "complex.pdb",
    ab_chains     = ["A", "B"],   # VH, VL (or just VHH: ["A"])
    ag_chains     = ["C"],
    evoef2_exe    = "tools/EvoEF2_src/EvoEF2.exe",
    thermompnn_dir= "tools/ThermoMPNN",
)

mutations = [{"chain":"A","resi":67,"wt":"Y","mut":"F"}]

result = tk.run_evoef2(mutations)           # Layer 1 fast scan
result = tk.run_prodigy(mutations)
result = tk.run_mmgbsa(mutations, minimization_steps=100)
result = tk.run_esm_if1(mutations)
result = tk.run_thermompnn(mutations)
result = tk.run_antifold(mutations)

all_results = tk.run_all(mutations)   # runs all five, merges output
"""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Public result schema:
#   {
#     "tool":    str,
#     "variant": str,          # e.g. "A67Y"
#     "dg":      float|None,   # absolute ΔG_bind  (kcal/mol)
#     "ddg":     float|None,   # ΔΔG relative to WT (kcal/mol, negative = better)
#     "kd_nM":   float|None,   # predicted Kd (nM), tool-dependent
#     "elapsed": float,        # wall-clock seconds
#     "error":   str|None,
#   }
# ---------------------------------------------------------------------------

THERMOMPNN_DEFAULT = Path(__file__).resolve().parents[2] / "tools" / "ThermoMPNN"
EVOEF2_DEFAULT     = Path(__file__).resolve().parents[2] / "tools" / "EvoEF2_src" / "EvoEF2.exe"
RT_KCAL            = 0.5922  # RT at 25°C in kcal/mol


# ── helpers ──────────────────────────────────────────────────────────────────

def _mut_label(mutations: list[dict]) -> str:
    """Return human-readable label like 'A67F+B102K'."""
    if not mutations:
        return "WT"
    return "+".join(f"{m['chain']}{m['resi']}{m['mut']}" for m in mutations)


def _evoef2_build(evoef2_exe: str, pdb_path: str, mutations: list[dict],
                  chain: str, work_dir: str) -> str | None:
    """Build mutant PDB with EvoEF2 BuildMutant. Returns path or None."""
    pdb_name = os.path.basename(pdb_path)
    shutil.copy2(pdb_path, os.path.join(work_dir, pdb_name))
    if not mutations:
        return os.path.join(work_dir, pdb_name)

    mut_str = ",".join(
        f"{m['wt']}{m['chain']}{m['resi']}{m['mut']}" for m in mutations
    ) + ";"
    with open(os.path.join(work_dir, "individual_list.txt"), "w") as f:
        f.write(mut_str + "\n")

    subprocess.run(
        [evoef2_exe, "--command=BuildMutant",
         f"--pdb={pdb_name}", "--mutant_file=individual_list.txt"],
        capture_output=True, text=True, cwd=work_dir, timeout=120,
    )
    stem   = Path(pdb_name).stem
    result = os.path.join(work_dir, f"{stem}_Model_0001.pdb")
    return result if os.path.exists(result) else None


def _kd_from_dg(dg_kcal: float, temp_c: float = 25.0) -> float:
    """Convert ΔG (kcal/mol) → Kd (M) using ΔG = RT ln(Kd)."""
    import math
    rt = 0.001987 * (temp_c + 273.15)  # kcal/mol
    return math.exp(dg_kcal / rt)


# ── main class ───────────────────────────────────────────────────────────────

class AffinityEnergyToolkit:
    """
    Unified interface for five binding-energy / ΔΔG tools.

    Parameters
    ----------
    complex_pdb : str
        Path to the wildtype antibody–antigen complex PDB.
    ab_chains : list[str]
        Chain IDs of the antibody (e.g. ["A"] for VHH, ["A","B"] for VH+VL).
    ag_chains : list[str]
        Chain IDs of the antigen (e.g. ["C"]).
    evoef2_exe : str
        Path to EvoEF2 executable (used by PRODIGY, MM/GBSA, ThermoMPNN for
        mutant building).
    thermompnn_dir : str
        Path to cloned ThermoMPNN repository root.
    temperature : float
        Temperature in °C for Kd conversion (default 25).
    """

    def __init__(
        self,
        complex_pdb:    str,
        ab_chains:      list[str],
        ag_chains:      list[str],
        evoef2_exe:     str  = str(EVOEF2_DEFAULT),
        thermompnn_dir: str  = str(THERMOMPNN_DEFAULT),
        temperature:    float = 25.0,
    ):
        self.complex_pdb    = str(Path(complex_pdb).resolve())
        self.ab_chains      = ab_chains
        self.ag_chains      = ag_chains
        self.evoef2_exe     = str(Path(evoef2_exe).resolve())
        self.thermompnn_dir = str(Path(thermompnn_dir).resolve())
        self.temperature    = temperature

    # ── 0. EvoEF2 ComputeBinding ────────────────────────────────────────────

    def run_evoef2(
        self,
        mutations: list[dict],
        wt_dg: float | None = None,
        split: str | None = None,
    ) -> dict[str, Any]:
        """
        EvoEF2 ComputeBinding: Physics-based ΔΔG_bind scan (fastest method).

        Mechanism
        ---------
        EvoEF2 (Evolutionary Energy Function 2) uses a semi-empirical
        physical energy function comprising:
          - Van der Waals interactions (12-6 LJ)
          - Hydrogen bonding (distance + angle terms)
          - Electrostatics (distance-dependent dielectric)
          - Solvation (Lazaridis–Karplus implicit solvation)
          - Backbone torsion energy (Ramachandran-derived)
          - Side-chain rotamer probability (backbone-dependent library)

        ComputeBinding workflow:
          1. Build mutant PDB (BuildMutant with rotamer optimization)
          2. Run EvoEF2 --command=ComputeBinding on complex
          3. ΔΔG_bind = ΔG_bind_mut - ΔG_bind_WT
             where ΔG_bind = E_complex - E_chain_A_part - E_chain_BC_part

        Accuracy
        --------
        Pearson r ≈ 0.50–0.60 vs experimental ΔΔG (SKEMPI2 AB–AG subset).
        MUE ≈ 1.1 kcal/mol. Best for fast relative ranking.
        Reference: Huang et al., Bioinformatics 2020.

        Speed
        -----
        < 5 s/mutant (CPU, no minimization needed — rotamer packing only).
        100 single-point mutations: < 10 min.

        Parameters
        ----------
        mutations : list[dict]
            Each dict: {"chain":"A","resi":67,"wt":"Y","mut":"F"}
        wt_dg : float, optional
            Pre-computed WT ΔG_bind from EvoEF2; if None, WT is run first.
        split : str, optional
            Chain split string, e.g. "A,BC" (antibody vs antigen).
            If None, auto-built from ab_chains and ag_chains.

        Returns
        -------
        dict: tool, variant, dg, ddg, kd_nM, elapsed, error
        """
        label = _mut_label(mutations)
        t0    = time.time()

        if split is None:
            ab_part = "".join(self.ab_chains)
            ag_part = "".join(self.ag_chains)
            split   = f"{ab_part},{ag_part}"

        def _parse_binding_energy(output: str) -> float | None:
            for line in output.splitlines():
                s = line.strip()
                if s.startswith("Binding energy") and "=" in s:
                    try:
                        return float(s.split("=")[-1].strip())
                    except ValueError:
                        pass
                # EvoEF2 sometimes says "Total = X.XXX"
                if s.startswith("Total") and "=" in s:
                    try:
                        return float(s.split("=")[-1].strip())
                    except ValueError:
                        pass
            return None

        try:
            with tempfile.TemporaryDirectory(prefix="evoef2_") as tmp:
                primary_chain = self.ab_chains[0]
                pdb = _evoef2_build(
                    self.evoef2_exe, self.complex_pdb, mutations, primary_chain, tmp
                )
                if pdb is None:
                    raise RuntimeError("EvoEF2 BuildMutant failed")

                pdb_name = os.path.basename(pdb)
                result = subprocess.run(
                    [self.evoef2_exe, "--command=ComputeBinding",
                     f"--pdb={pdb_name}", f"--split={split}"],
                    capture_output=True, text=True, cwd=tmp, timeout=120,
                )
                output = result.stdout + result.stderr
                dg = _parse_binding_energy(output)

            if dg is None:
                raise RuntimeError(f"Could not parse binding energy.\nOutput:\n{output[:500]}")

            ddg = round(dg - wt_dg, 3) if wt_dg is not None else None

            # ── HallucinationGuard: EVOEF2_ARTIFACT check ──────────────────
            # Flag |ΔΔG| > 5 kcal/mol as a possible structural artifact.
            # This does NOT abort — caller receives the result with a warning
            # recorded in the project audit log.
            if ddg is not None:
                try:
                    _guard_project_dir = Path(self.complex_pdb).resolve().parent
                    from core.integrity.hallucination_guard import HallucinationGuard
                    _guard = HallucinationGuard(
                        project_dir=_guard_project_dir,
                        pipeline="vam_standard",
                        step="run_evoef2",
                        verbose=False,
                    )
                    _guard.check_evoef2_artifact(ddg, label=label)
                    _guard.write_audit()
                except Exception:
                    pass  # guard failures must never block the toolkit

            return {
                "tool": "EvoEF2", "variant": label,
                "dg": round(dg, 3), "ddg": ddg, "kd_nM": None,
                "elapsed": round(time.time() - t0, 1), "error": None,
            }

        except Exception as e:
            return {"tool": "EvoEF2", "variant": label,
                    "dg": None, "ddg": None, "kd_nM": None,
                    "elapsed": round(time.time() - t0, 1), "error": str(e)}

    # ── 1. PRODIGY ──────────────────────────────────────────────────────────

    def run_prodigy(
        self,
        mutations: list[dict],
        wt_dg: float | None = None,
        distance_cutoff: float = 5.5,
        acc_threshold: float = 0.05,
    ) -> dict[str, Any]:
        """
        PRODIGY: Intermolecular Contact (IC)-based ΔG / Kd prediction.

        Mechanism
        ---------
        Counts residue-level intermolecular contacts (charged/polar/apolar)
        and solvent-accessible surface of non-interface residues (NIS).
        Applies a linear regression model trained on 144 protein–protein
        complexes (SKEMPI) to predict ΔG_bind and Kd.

        Accuracy
        --------
        Pearson r ≈ 0.74 on protein–protein test set (Vangone & Bonvin 2015).
        MUE ≈ 1.0 kcal/mol; best for relative ΔΔG ranking (not absolute Kd).

        Speed
        -----
        < 2 s/complex (pure Python contact counting, no minimization).

        Parameters
        ----------
        mutations : list[dict]
            Each dict: {"chain": "A", "resi": 67, "wt": "Y", "mut": "F"}
        wt_dg : float, optional
            Pre-computed WT ΔG to subtract; if None, WT is computed first.

        Returns
        -------
        dict with keys: tool, variant, dg, ddg, kd_nM, n_contacts, elapsed, error
        """
        from prodigy_prot.modules.prodigy import Prodigy
        from Bio.PDB import PDBParser

        label = _mut_label(mutations)
        t0    = time.time()

        try:
            with tempfile.TemporaryDirectory(prefix="prodigy_") as tmp:
                # Build mutant if needed
                primary_chain = self.ab_chains[0]
                pdb = _evoef2_build(
                    self.evoef2_exe, self.complex_pdb, mutations, primary_chain, tmp
                )
                if pdb is None:
                    raise RuntimeError("EvoEF2 BuildMutant failed")

                parser    = PDBParser(QUIET=True)
                structure = parser.get_structure("mol", pdb)
                model     = structure[0]

                # PRODIGY selection: antibody group vs antigen group
                selection = [",".join(self.ab_chains), ",".join(self.ag_chains)]
                p = Prodigy(model, selection=selection, temp=self.temperature)
                p.predict(distance_cutoff=distance_cutoff, acc_threshold=acc_threshold)
                d = p.as_dict()

            dg         = round(d["ba_val"], 3)
            kd_nM      = d["kd_val"] * 1e9
            n_contacts = d["ICs"]
            ddg        = round(dg - wt_dg, 3) if wt_dg is not None else None

            return {
                "tool": "PRODIGY", "variant": label,
                "dg": dg, "ddg": ddg, "kd_nM": round(kd_nM, 3),
                "n_contacts": n_contacts,
                "nis_apolar": round(d.get("nis_a", 0), 1),
                "nis_charged": round(d.get("nis_c", 0), 1),
                "elapsed": round(time.time() - t0, 1), "error": None,
            }

        except Exception as e:
            return {"tool": "PRODIGY", "variant": label,
                    "dg": None, "ddg": None, "kd_nM": None,
                    "elapsed": round(time.time() - t0, 1), "error": str(e)}

    # ── 2. OpenMM MM/GBSA ───────────────────────────────────────────────────

    def run_mmgbsa(
        self,
        mutations: list[dict],
        wt_dg: float | None = None,
        minimization_steps: int = 300,
        forcefield: str = "amber14/protein.ff14SB.xml",
        implicit_solvent: str = "implicit/obc2.xml",
        residue_range: dict | None = None,
    ) -> dict[str, Any]:
        """
        OpenMM MM/GBSA: Physics-based single-point binding energy.

        Mechanism
        ---------
        Builds mutant with EvoEF2 → adds H via PDBFixer → energy-minimizes
        the complex with AMBER ff14SB + OBC2 implicit solvent (Langevin MD,
        300 K) → computes:
            ΔG_bind = E_complex − E_antibody − E_antigen
        using the single-trajectory approximation (all sub-energies taken
        from the same minimized complex coordinates).

        Force field : AMBER ff14SB  (protein) + OBC2 GBSA (implicit water)
        Minimizer   : L-BFGS via OpenMM LocalEnergyMinimizer

        Accuracy
        --------
        Pearson r ≈ 0.55–0.65 vs experimental ΔΔG on SKEMPI2
        (single-trajectory, no explicit solvent, no entropy).
        Best for relative ranking of point mutants on the same scaffold.

        Speed
        -----
        ~1–3 min/mutant on CPU (300 minimization steps, ~200-residue complex).
        ~15–30 s on GPU (CUDA platform).

        Parameters
        ----------
        mutations : list[dict]
            Same format as run_prodigy.
        wt_dg : float, optional
            WT ΔG_bind (kcal/mol); if None, WT is computed first.
        minimization_steps : int
            Energy minimization iterations (default 300).
        residue_range : dict, optional
            {"chain": "C", "start": 1, "end": 200} to truncate large antigens.

        Returns
        -------
        dict with keys: tool, variant, dg, ddg, e_complex, e_ab, e_ag, elapsed, error
        """
        from openmm.app import ForceField, Simulation, PDBFile, Topology
        from openmm import LangevinMiddleIntegrator, Platform, unit, VerletIntegrator, Context
        from pdbfixer import PDBFixer
        import numpy as _np

        label = _mut_label(mutations)
        t0    = time.time()

        try:
            with tempfile.TemporaryDirectory(prefix="mmgbsa_") as tmp:
                primary_chain = self.ab_chains[0]
                full_pdb = _evoef2_build(
                    self.evoef2_exe, self.complex_pdb, mutations, primary_chain, tmp
                )
                if full_pdb is None:
                    raise RuntimeError("EvoEF2 BuildMutant failed")

                # Optional truncation of large antigen chains
                trunc = os.path.join(tmp, "trunc.pdb")
                with open(full_pdb) as fi, open(trunc, "w") as fo:
                    for line in fi:
                        if not line.startswith(("ATOM", "HETATM")):
                            continue
                        ch = line[21]
                        if ch in self.ab_chains:
                            fo.write(line)
                            continue
                        if ch in self.ag_chains:
                            if residue_range and residue_range.get("chain") == ch:
                                try:
                                    resi = int(line[22:26])
                                    if residue_range["start"] <= resi <= residue_range["end"]:
                                        fo.write(line)
                                except ValueError:
                                    pass
                            else:
                                fo.write(line)
                    fo.write("END\n")

                fixer = PDBFixer(filename=trunc)
                fixer.findMissingResidues()
                fixer.findMissingAtoms()
                fixer.addMissingAtoms()
                fixer.addMissingHydrogens(7.0)
                top = fixer.topology
                pos = fixer.positions
                top.createStandardBonds()
                top.createDisulfideBonds(pos)

                ff = ForceField(forcefield, implicit_solvent)
                sys_c = ff.createSystem(top,
                                        nonbondedCutoff=1.0 * unit.nanometers,
                                        constraints=None)
                integ = LangevinMiddleIntegrator(
                    self.temperature * unit.kelvin,
                    1.0 / unit.picosecond,
                    0.002 * unit.picoseconds,
                )

                env_plat = os.environ.get("OPENMM_DEFAULT_PLATFORM")
                plat_order = [env_plat] if env_plat else []
                plat_order += [
                    n for n in ("CUDA", "CPU", "Reference")
                    if n != env_plat
                ]

                last_err: Exception | None = None
                e_cplx = e_ab = e_ag = min_pos = None
                used_plat = None

                for plat_name in plat_order:
                    try:
                        platform = Platform.getPlatformByName(plat_name)
                        sim = Simulation(top, sys_c, integ, platform)
                        sim.context.setPositions(pos)
                        sim.minimizeEnergy(maxIterations=minimization_steps)
                        state = sim.context.getState(getEnergy=True, getPositions=True)
                        min_pos = state.getPositions(asNumpy=True)
                        e_cplx = state.getPotentialEnergy().value_in_unit(
                            unit.kilojoules_per_mole) / 4.184
                        used_plat = plat_name
                        break
                    except Exception as ex:
                        last_err = ex
                        continue

                if min_pos is None:
                    raise RuntimeError(
                        "OpenMM failed on all platforms (%s): %s"
                        % (plat_order, last_err)
                    )

                def _sub_e(keep_chains, platform):
                    new_top = Topology()
                    idx_map = []
                    for chain in top.chains():
                        if chain.id not in keep_chains:
                            continue
                        nc = new_top.addChain(chain.id)
                        for res in chain.residues():
                            nr = new_top.addResidue(res.name, nc, res.id, res.insertionCode)
                            for atom in res.atoms():
                                new_top.addAtom(atom.name, atom.element, nr, atom.id)
                                idx_map.append(atom.index)
                    new_top.createStandardBonds()
                    sub_pos = _np.take(min_pos, idx_map, axis=0) * unit.nanometers
                    new_top.createDisulfideBonds(sub_pos)
                    sys_s = ff.createSystem(new_top,
                                            nonbondedCutoff=1.0 * unit.nanometers,
                                            constraints=None)
                    ctx = Context(sys_s, VerletIntegrator(0.001 * unit.picoseconds), platform)
                    ctx.setPositions(sub_pos)
                    e = ctx.getState(getEnergy=True).getPotentialEnergy().value_in_unit(
                        unit.kilojoules_per_mole) / 4.184
                    del ctx
                    return e

                platform = Platform.getPlatformByName(used_plat)
                e_ab = _sub_e(self.ab_chains, platform)
                e_ag = _sub_e(self.ag_chains, platform)
                dg   = round(e_cplx - e_ab - e_ag, 2)
                ddg  = round(dg - wt_dg, 2) if wt_dg is not None else None

            return {
                "tool": "OpenMM_MMGBSA", "variant": label,
                "dg": dg, "ddg": ddg, "kd_nM": None,
                "e_complex": round(e_cplx, 2),
                "e_ab": round(e_ab, 2), "e_ag": round(e_ag, 2),
                "elapsed": round(time.time() - t0, 1), "error": None,
            }

        except Exception as e:
            return {"tool": "OpenMM_MMGBSA", "variant": label,
                    "dg": None, "ddg": None, "kd_nM": None,
                    "elapsed": round(time.time() - t0, 1), "error": str(e)}

    def run_mmgbsa_selfref(
        self,
        mutations: list[dict],
        minimization_steps: int = 300,
        forcefield: str = "amber14/protein.ff14SB.xml",
        implicit_solvent: str = "implicit/obc2.xml",
        residue_range: dict | None = None,
    ) -> dict[str, Any]:
        """MM/GBSA with per-site WT-self repack baseline (VAM V1.6.1 fix).

        ``run_mmgbsa`` computes WT against the *raw* input pose while every
        mutant is rebuilt via EvoEF2 BuildMutant (discrete side-chain repack).
        On a strained docking pose that asymmetry adds a spurious "repack
        relief" (observed ~5-8 kcal/mol on PAG-1 clone 001) to every mutant,
        flagging all of them as beneficial.

        This method removes the asymmetry: the WT baseline is the *same
        residue(s) self-mutated* (wt->wt), so WT and mutant pass through an
        identical BuildMutant + PDBFixer + OpenMM-minimize pipeline at the same
        site(s).  ``ddg_selfref = dg(mut) - dg(WT_self @ same site)``.

        Purely additive: does not alter ``run_mmgbsa`` defaults or any existing
        caller.  Returns the mutant dg/ddg plus the self-ref baseline and the
        corrected ΔΔG.
        """
        mut_res = self.run_mmgbsa(
            mutations,
            minimization_steps=minimization_steps,
            forcefield=forcefield,
            implicit_solvent=implicit_solvent,
            residue_range=residue_range,
        )
        self_muts = [dict(m, mut=m["wt"]) for m in mutations] if mutations else []
        wt_res = self.run_mmgbsa(
            self_muts,
            minimization_steps=minimization_steps,
            forcefield=forcefield,
            implicit_solvent=implicit_solvent,
            residue_range=residue_range,
        )
        ddg_selfref = None
        if mut_res.get("dg") is not None and wt_res.get("dg") is not None:
            ddg_selfref = round(mut_res["dg"] - wt_res["dg"], 2)
        return {
            "tool": "OpenMM_MMGBSA_selfref",
            "variant": mut_res.get("variant"),
            "dg": mut_res.get("dg"),
            "wt_self_dg": wt_res.get("dg"),
            "ddg_selfref": ddg_selfref,
            "ddg_raw_vs_input": mut_res.get("ddg"),
            "baseline_method": "per_site_wt_self_repack",
            "mut_error": mut_res.get("error"),
            "wt_self_error": wt_res.get("error"),
            "elapsed": round(
                (mut_res.get("elapsed") or 0) + (wt_res.get("elapsed") or 0), 1
            ),
            "error": mut_res.get("error") or wt_res.get("error"),
        }

    # ── 3. ESM-IF1 ──────────────────────────────────────────────────────────

    def run_esm_if1(
        self,
        mutations: list[dict],
        wt_logp: float | None = None,
    ) -> dict[str, Any]:
        """
        ESM-IF1 Inverse Folding ΔΔG proxy.

        Mechanism
        ---------
        ESM-IF1 (Hsu et al. 2022) is a GVP-GNN + Transformer trained to
        predict sequence log-likelihood given backbone coordinates.
        For ΔΔG estimation:
            ΔΔG_proxy = −RT × (log P(mut|backbone) − log P(wt|backbone))
        Negative value = mutant is more sequence-compatible with the
        structure → likely more stable / better binding.

        This is a *stability-oriented* proxy, not directly trained on
        binding ΔΔG.  Use together with PRODIGY/MM/GBSA for full picture.

        Accuracy
        --------
        Pearson r ≈ 0.45–0.55 vs experimental ΔΔG_stability (Ssym dataset).
        For binding ΔΔG: qualitative agreement, not quantitative.

        Speed
        -----
        Model loading: ~10 s (downloads ~142 MB on first run).
        Inference: < 2 s/structure (CPU), < 0.5 s (GPU).

        Model
        -----
        esm_if1_gvp4_t16_142M_UR50  (142M parameters, Apache 2.0 / MIT)

        Parameters
        ----------
        mutations : list[dict]
            Same format as run_prodigy.
        wt_logp : float, optional
            Pre-computed WT log-likelihood; if None, WT is run first.
        """
        label = _mut_label(mutations)
        t0    = time.time()

        try:
            import esm
            import esm.inverse_folding
            import torch

            model, alphabet = esm.pretrained.esm_if1_gvp4_t16_142M_UR50()
            model = model.eval()

            # Use ab_chains[0] for the antibody
            ab_chain = self.ab_chains[0]

            def _fix_bfactor_esm(src: str, dst: str) -> None:
                """Replace blank B-factor fields so biotite can parse the PDB."""
                with open(src) as fi, open(dst, "w") as fo:
                    for line in fi:
                        if line.startswith(("ATOM", "HETATM")):
                            bf = line[60:66]
                            if not bf.strip():
                                line = line[:60] + "  0.00" + line[66:]
                        fo.write(line)

            def _logp_chain(pdb_path, chain_id, work_dir=None):
                """Log-likelihood of the sequence given backbone coords."""
                # Fix blank B-factor fields that EvoEF2 sometimes produces
                if work_dir is not None:
                    fixed = os.path.join(work_dir, Path(pdb_path).stem + "_esm.pdb")
                    _fix_bfactor_esm(pdb_path, fixed)
                    pdb_path = fixed
                structure = esm.inverse_folding.util.load_structure(pdb_path, chain_id)
                coords, seq = esm.inverse_folding.util.extract_coords_from_structure(structure)
                ll, _ = esm.inverse_folding.util.score_sequence(
                    model, alphabet, coords, seq
                )
                return ll

            with tempfile.TemporaryDirectory(prefix="esmif1_") as tmp:
                # WT log-likelihood
                if wt_logp is None:
                    wt_logp = _logp_chain(self.complex_pdb, ab_chain, work_dir=tmp)

                # Build mutant PDB and score
                pdb = _evoef2_build(
                    self.evoef2_exe, self.complex_pdb, mutations, ab_chain, tmp
                )
                if pdb is None:
                    raise RuntimeError("EvoEF2 BuildMutant failed")
                mut_logp = _logp_chain(pdb, ab_chain, work_dir=tmp)

            ddg_proxy = round(-RT_KCAL * (mut_logp - wt_logp), 3)

            return {
                "tool": "ESM-IF1", "variant": label,
                "dg": None, "ddg": ddg_proxy, "kd_nM": None,
                "wt_logp": round(wt_logp, 4),
                "mut_logp": round(mut_logp, 4),
                "elapsed": round(time.time() - t0, 1), "error": None,
            }

        except Exception as e:
            return {"tool": "ESM-IF1", "variant": label,
                    "dg": None, "ddg": None, "kd_nM": None,
                    "elapsed": round(time.time() - t0, 1), "error": str(e)}

    # ── 4. ThermoMPNN ───────────────────────────────────────────────────────

    def run_thermompnn(
        self,
        mutations: list[dict],
        checkpoint: str | None = None,
    ) -> dict[str, Any]:
        """
        ThermoMPNN: GNN ΔΔG + ΔTm prediction.

        Mechanism
        ---------
        Transfer learning on ProteinMPNN encoder (trained on PDB) fine-tuned
        on Megascale (~350K point mutation stability measurements).
        Input: backbone coordinates (N, Cα, C, O per residue) + mutation spec.
        Output: ΔΔG (kcal/mol) per point mutation (forward pass through ddg_out head).

        For multi-mutants: sum of individual ΔΔG values (additive assumption).

        Accuracy
        --------
        Pearson r ≈ 0.55–0.60 vs experimental ΔΔG_stability (Ssym, ProTherm).
        Better calibrated than ESM-IF1 for stability; qualitative for binding.

        Speed
        -----
        Model load: ~3–5 s. Inference: ~2–8 s/mutation (CPU).
        Batch: all mutations on one PDB in a single forward pass.

        Checkpoint
        ----------
        Default: tools/ThermoMPNN/models/thermoMPNN_default.pt  (38 MB)
        or pass a .pt / .ckpt path explicitly.
        """
        label = _mut_label(mutations)
        t0    = time.time()

        try:
            tdir = self.thermompnn_dir
            # ensure ThermoMPNN + its analysis subdir are on path
            for d in [tdir, str(Path(tdir) / "analysis")]:
                if d not in sys.path:
                    sys.path.insert(0, d)

            import torch
            from omegaconf import OmegaConf
            from protein_mpnn_utils import alt_parse_PDB
            from datasets import Mutation as TM_Mutation
            from thermompnn_benchmarking import get_trained_model

            # ── locate checkpoint ────────────────────────────────────────
            if checkpoint is None:
                candidates = [
                    Path(tdir) / "models" / "thermoMPNN_default.pt",
                    Path(tdir) / "models" / "thermoMPNN_default.ckpt",
                ]
                for c in candidates:
                    if c.is_file():
                        checkpoint = str(c)
                        break
                if checkpoint is None:
                    raise FileNotFoundError(
                        "No ThermoMPNN checkpoint found in tools/ThermoMPNN/models/. "
                        "Pass checkpoint= explicitly."
                    )

            # ── build config ─────────────────────────────────────────────
            local_yaml = Path(tdir) / "local.yaml"
            cfg = OmegaConf.load(str(local_yaml))
            # override platform paths to local installation
            OmegaConf.update(cfg, "platform.thermompnn_dir", tdir, merge=True)
            model_cfg = OmegaConf.create({
                "training": {
                    "num_workers": 0,
                    "learn_rate": 0.001,
                    "epochs": 100,
                    "lr_schedule": True,
                },
                "model": {
                    "hidden_dims": [64, 32],
                    "subtract_mut": True,
                    "num_final_layers": 2,
                    "freeze_weights": True,
                    "load_pretrained": True,
                    "lightattn": True,
                    "lr_schedule": True,
                }
            })
            cfg = OmegaConf.merge(cfg, model_cfg)

            device = torch.device("cpu")
            tm_model = get_trained_model(
                model_name=checkpoint, config=cfg, override_custom=True
            )
            tm_model = tm_model.eval().to(device)

            # ── build mutation objects ────────────────────────────────────
            if not mutations:
                # WT: return 0 ΔΔG
                return {
                    "tool": "ThermoMPNN", "variant": "WT",
                    "dg": None, "ddg": 0.0, "kd_nM": None,
                    "n_mutations": 0,
                    "elapsed": round(time.time() - t0, 1), "error": None,
                }

            ab_chain = self.ab_chains[0]
            mut_pdb  = alt_parse_PDB(self.complex_pdb, ab_chain)

            ALPHABET = "ACDEFGHIKLMNPQRSTVWYX"
            tm_mutations = []
            for m in mutations:
                wt, resi, mt = m["wt"], m["resi"], m["mut"]
                assert wt in ALPHABET and mt in ALPHABET
                tm_mutations.append(
                    TM_Mutation(position=resi, wildtype=wt, mutation=mt,
                                ddG=None, pdb=mut_pdb[0]["name"])
                )

            with torch.no_grad():
                preds, _ = tm_model(mut_pdb, tm_mutations)

            ddg_total = sum(float(p["ddG"].cpu().item()) for p in preds if p is not None)
            ddg = round(ddg_total, 3)

            return {
                "tool": "ThermoMPNN", "variant": label,
                "dg": None, "ddg": ddg, "kd_nM": None,
                "n_mutations": len(mutations),
                "checkpoint": Path(checkpoint).name,
                "elapsed": round(time.time() - t0, 1), "error": None,
            }

        except Exception as e:
            return {"tool": "ThermoMPNN", "variant": label,
                    "dg": None, "ddg": None, "kd_nM": None,
                    "elapsed": round(time.time() - t0, 1), "error": str(e)}

    # ── 5. AntiFold ─────────────────────────────────────────────────────────

    def run_antifold(
        self,
        mutations: list[dict],
        wt_logp: float | None = None,
    ) -> dict[str, Any]:
        """
        AntiFold: Antibody-specific CDR inverse-folding ΔΔG proxy.

        Mechanism
        ---------
        AntiFold (Høie et al. 2024) is an antibody-specific inverse-folding
        model (141M parameters) trained on the OAS database + SAbDab structures.
        It predicts per-residue log-likelihoods conditioned on antibody backbone
        coordinates and framework context.

        ΔΔG proxy:
            ΔΔG = −RT × (log P_AntiFold(mut|backbone) − log P_AntiFold(wt|backbone))

        Unlike ESM-IF1, AntiFold is trained exclusively on antibody sequences,
        so CDR loop scoring is more accurate (especially CDR-H3).

        Accuracy
        --------
        Native sequence recovery on antibody CDRs: 60–70% (vs 50% for ProteinMPNN).
        ΔΔG proxy: qualitative, Pearson r ≈ 0.40–0.50 vs experimental ΔΔG.
        Best used as a *CDR compatibility filter* rather than energy predictor.

        Speed
        -----
        Model loading: ~5 s (weights cached after first download).
        Inference: < 1 s/structure (CPU), < 0.2 s (GPU).

        Parameters
        ----------
        mutations : list[dict]
            Same format as run_prodigy. Chain must be an antibody chain.
        wt_logp : float, optional
            WT log-likelihood from AntiFold; if None, computed first.
        """
        label = _mut_label(mutations)
        t0    = time.time()

        try:
            import pandas as pd
            import torch
            import torch.nn.functional as F
            from antifold.antiscripts import load_model, get_pdbs_logits, df_logits_to_logprobs

            af_model = load_model()
            af_model.eval()

            ab_chain_h = self.ab_chains[0]
            ab_chain_l = self.ab_chains[1] if len(self.ab_chains) > 1 else ""

            AMINO_LIST = list("ACDEFGHIKLMNPQRSTVWY")

            def _fix_bfactor(src: str, dst: str) -> None:
                """Replace blank B-factor fields with '  0.00' so biotite can parse."""
                with open(src) as fi, open(dst, "w") as fo:
                    for line in fi:
                        if line.startswith(("ATOM", "HETATM")):
                            bf = line[60:66]
                            if not bf.strip():
                                line = line[:60] + "  0.00" + line[66:]
                        fo.write(line)

            def _score(pdb_path: str, work_dir: str) -> float:
                """Mean per-residue log probability of the native sequence (VH chain)."""
                # Fix blank B-factor that EvoEF2 sometimes produces
                fixed = os.path.join(work_dir, Path(pdb_path).stem + "_af.pdb")
                _fix_bfactor(pdb_path, fixed)

                pdb_dir  = work_dir
                pdb_name = Path(fixed).stem
                pdbs_df = pd.DataFrame([{
                    "pdb":    pdb_name,
                    "Hchain": ab_chain_h,
                    "Lchain": ab_chain_l,
                }])
                df_logits_list = get_pdbs_logits(
                    af_model,
                    pdbs_csv_or_dataframe=pdbs_df,
                    pdb_dir=pdb_dir,
                    batch_size=1,
                    save_flag=False,
                )
                df = df_logits_list[0]
                # native residue column is 'pdb_res'
                native_col = "pdb_res" if "pdb_res" in df.columns else None
                t_logits  = torch.tensor(df[AMINO_LIST].values, dtype=torch.float32)
                log_probs = F.log_softmax(t_logits, dim=1)   # (L, 20)
                if native_col:
                    valid = [(i, AMINO_LIST.index(a))
                             for i, a in enumerate(df[native_col]) if a in AMINO_LIST]
                    if valid:
                        rows, cols = zip(*valid)
                        ll = log_probs[list(rows), list(cols)].mean().item()
                    else:
                        ll = log_probs.mean().item()
                else:
                    ll = log_probs.mean().item()
                return float(ll)

            with tempfile.TemporaryDirectory(prefix="antifold_") as tmp:
                if wt_logp is None:
                    wt_logp = _score(self.complex_pdb, tmp)

                if mutations:
                    pdb = _evoef2_build(
                        self.evoef2_exe, self.complex_pdb, mutations, ab_chain_h, tmp
                    )
                    if pdb is None:
                        raise RuntimeError("EvoEF2 BuildMutant failed")
                    mut_logp = _score(pdb, tmp)
                else:
                    mut_logp = wt_logp

            ddg_proxy = round(-RT_KCAL * (mut_logp - wt_logp), 3)

            return {
                "tool": "AntiFold", "variant": label,
                "dg": None, "ddg": ddg_proxy, "kd_nM": None,
                "wt_logp": round(wt_logp, 4),
                "mut_logp": round(mut_logp, 4),
                "elapsed": round(time.time() - t0, 1), "error": None,
            }

        except Exception as e:
            return {"tool": "AntiFold", "variant": label,
                    "dg": None, "ddg": None, "kd_nM": None,
                    "elapsed": round(time.time() - t0, 1), "error": str(e)}

    # ── 6. run_all ──────────────────────────────────────────────────────────

    def run_all(
        self,
        mutations_list: list[list[dict]],
        tools: list[str] | None = None,
        minimization_steps: int = 300,
        output_csv: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Run selected tools on all mutation candidates.

        Parameters
        ----------
        mutations_list : list of lists
            Each inner list is one variant: [{"chain":"A","resi":67,"wt":"Y","mut":"F"}]
            Include [] for WT.
        tools : list[str], optional
            Subset of: ["prodigy","mmgbsa","esm_if1","thermompnn","antifold"]
            Default: all five.
        minimization_steps : int
            MM/GBSA minimization iterations.
        output_csv : str, optional
            If given, write merged results to this CSV.

        Returns
        -------
        list[dict] — one row per (variant × tool), plus a merged summary row.
        """
        if tools is None:
            tools = ["evoef2", "prodigy", "mmgbsa", "esm_if1", "thermompnn", "antifold"]

        tools = [t.lower() for t in tools]
        rows  = []

        # Pre-compute WT baselines for relative ΔΔG
        wt_evoef2     = None
        wt_prodigy    = None
        wt_mmgbsa     = None
        wt_esm_logp   = None
        wt_antifold_lp= None

        print("\n" + "="*65)
        print(f"AffinityEnergyToolkit  |  {len(mutations_list)} variants  |  tools: {tools}")
        print("="*65)

        for idx, muts in enumerate(mutations_list):
            label = _mut_label(muts)
            is_wt = (muts == [])
            print(f"\n[{idx+1}/{len(mutations_list)}]  {label}")

            row = {"variant": label}

            if "evoef2" in tools:
                r = self.run_evoef2(muts, wt_dg=wt_evoef2)
                if is_wt and r["dg"] is not None:
                    wt_evoef2 = r["dg"]
                row.update({f"evoef2_{k}": v for k, v in r.items()
                             if k not in ("tool", "variant")})
                print(f"  EvoEF2   ΔG={r['dg']}  ΔΔG={r['ddg']}  ({r['elapsed']}s)")

            if "prodigy" in tools:
                r = self.run_prodigy(muts, wt_dg=wt_prodigy)
                if is_wt and r["dg"] is not None:
                    wt_prodigy = r["dg"]
                row.update({f"prodigy_{k}": v for k, v in r.items()
                             if k not in ("tool","variant")})
                print(f"  PRODIGY  ΔG={r['dg']}  ΔΔG={r['ddg']}  ({r['elapsed']}s)")

            if "mmgbsa" in tools:
                r = self.run_mmgbsa(muts, wt_dg=wt_mmgbsa,
                                    minimization_steps=minimization_steps)
                if is_wt and r["dg"] is not None:
                    wt_mmgbsa = r["dg"]
                row.update({f"mmgbsa_{k}": v for k, v in r.items()
                             if k not in ("tool","variant")})
                print(f"  MM/GBSA  ΔG={r['dg']}  ΔΔG={r['ddg']}  ({r['elapsed']}s)")

            if "esm_if1" in tools:
                r = self.run_esm_if1(muts, wt_logp=wt_esm_logp)
                if is_wt and r.get("wt_logp") is not None:
                    wt_esm_logp = r.get("mut_logp", r.get("wt_logp"))
                row.update({f"esm_{k}": v for k, v in r.items()
                             if k not in ("tool","variant")})
                print(f"  ESM-IF1  ΔΔG={r['ddg']}  ({r['elapsed']}s)")

            if "thermompnn" in tools:
                r = self.run_thermompnn(muts)
                row.update({f"thermo_{k}": v for k, v in r.items()
                             if k not in ("tool","variant")})
                print(f"  ThermoMPNN ΔΔG={r['ddg']}  ({r['elapsed']}s)")

            if "antifold" in tools:
                r = self.run_antifold(muts, wt_logp=wt_antifold_lp)
                if is_wt and r.get("wt_logp") is not None:
                    wt_antifold_lp = r.get("mut_logp", r.get("wt_logp"))
                row.update({f"af_{k}": v for k, v in r.items()
                             if k not in ("tool","variant")})
                print(f"  AntiFold  ΔΔG={r['ddg']}  ({r['elapsed']}s)")

            rows.append(row)

        if output_csv and rows:
            _write_csv(rows, output_csv)
            print(f"\nResults written to: {output_csv}")

        return rows


# ── CSV helper ───────────────────────────────────────────────────────────────

def _write_csv(rows: list[dict], path: str) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ── standalone quick-test ────────────────────────────────────────────────────

def _quick_prodigy_test(complex_pdb: str, ab_chains: list, ag_chains: list,
                         evoef2_exe: str) -> None:
    """Run PRODIGY on WT only and print result — fast sanity check."""
    tk = AffinityEnergyToolkit(
        complex_pdb=complex_pdb,
        ab_chains=ab_chains,
        ag_chains=ag_chains,
        evoef2_exe=evoef2_exe,
    )
    r = tk.run_prodigy([])
    print(f"PRODIGY WT: ΔG={r['dg']} kcal/mol  Kd={r['kd_nM']} nM  "
          f"ICs={r.get('n_contacts')}  ({r['elapsed']}s)")
