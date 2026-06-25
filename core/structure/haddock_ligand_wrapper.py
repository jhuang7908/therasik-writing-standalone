#!/usr/bin/env python3
"""HADDOCK3 + Prodigy-LIG Bridge for Antibody-Ligand VAM.

Two modes:
  1. run_prodigy_lig()  — direct Prodigy-LIG scoring via WSL (no HADDOCK3 needed).
     Use when a docked pose PDB is already available.

  2. run_refinement()   — full HADDOCK3 EM refinement then Prodigy-LIG scoring.
     Requires CNS topology/param files for any non-standard small molecule.
     For canonical amino-acid only complexes or when ligand param files are
     supplied via ligand_top_fname / ligand_param_fname.

Notes:
  - Prodigy-LIG CLI (WSL): prodigy_lig -c <protein_chains> <ligand_chain>:<resname> -i <pdb>
  - receptor_chain accepts comma-separated values (e.g. "H,L")
  - ligand_chain must be a single chain containing the ligand HETATM residue
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

class HaddockLigandWrapper:
    """Wrapper to run HADDOCK3 refinement and Prodigy-LIG scoring via WSL."""

    def __init__(self, workspace_root: str | Path):
        self.root = Path(workspace_root).resolve()
        # Detect WSL drive mapping (usually /mnt/d/...)
        drive = str(self.root.drive).lower().replace(":", "")
        self.wsl_root = Path(f"/mnt/{drive}") / self.root.as_posix().split(":", 1)[1].lstrip("/")

    def to_wsl_path(self, win_path: str | Path) -> str:
        """Convert a Windows absolute path to its WSL equivalent."""
        p = Path(win_path).resolve()
        try:
            rel = p.relative_to(self.root)
            return (self.wsl_root / rel).as_posix()
        except ValueError:
            # Not under root, try generic mapping
            drive = str(p.drive).lower().replace(":", "")
            return (Path(f"/mnt/{drive}") / p.as_posix().split(":", 1)[1].lstrip("/")).as_posix()

    def run_prodigy_lig(
        self,
        complex_pdb: str | Path,
        receptor_chains: str = "H,L",
        ligand_chain: str = "Z",
        ligand_resname: str = "FEN",
        distance_cutoff: float = 10.5,
    ) -> dict[str, Any]:
        """Run standalone Prodigy-LIG on a docked complex (no HADDOCK3 required).

        Args:
            complex_pdb: Path to the protein-ligand complex PDB.
            receptor_chains: Comma-separated chain IDs of the receptor protein.
            ligand_chain: Single chain ID containing the ligand HETATM residue.
            ligand_resname: Three-letter residue name of the ligand.
            distance_cutoff: Contact distance cutoff in Angstroms (default 10.5).

        Returns:
            dict with keys: status, dG_kcal_mol, pKd, raw_output, error.
        """
        wsl_pdb = self.to_wsl_path(complex_pdb)
        # prodigy_lig -c <protein_chains> <ligand_chain>:<resname> -i <pdb>
        cmd = (
            f"source ~/.bashrc && "
            f"prodigy_lig -c {receptor_chains} {ligand_chain}:{ligand_resname} "
            f"-d {distance_cutoff} -i {wsl_pdb}"
        )
        proc = subprocess.run(
            ["wsl", "bash", "-c", cmd],
            capture_output=True, text=True,
        )
        raw = proc.stdout.strip() + proc.stderr.strip()
        if proc.returncode != 0:
            return {"status": "FAIL", "error": raw[-800:], "raw_output": raw}

        # Parse output — prodigy_lig emits TSV:
        #   Job name\tDGprediction (low refinement) (Kcal/mol)[\tpKd]
        #   <name>\t<value>[\t<value>]
        result: dict[str, Any] = {
            "status": "SUCCESS",
            "raw_output": raw,
            "dG_kcal_mol": None,
            "pKd": None,
        }
        lines = [l for l in raw.splitlines() if l.strip()]
        if len(lines) >= 2:
            header = lines[0].lower()
            data_line = lines[1]
            cols = data_line.split("\t")
            h_cols = lines[0].split("\t")
            for i, h in enumerate(h_cols):
                h_l = h.lower()
                if i < len(cols):
                    try:
                        val = float(cols[i])
                    except (ValueError, IndexError):
                        continue
                    if "dg" in h_l or "binding affinity" in h_l or "kcal" in h_l:
                        result["dG_kcal_mol"] = val
                    elif "pkd" in h_l or "pki" in h_l:
                        result["pKd"] = val
        # Fallback: scan all lines for first float value
        if result["dG_kcal_mol"] is None:
            for line in raw.splitlines():
                parts = line.split()
                for p in parts:
                    try:
                        val = float(p)
                        result["dG_kcal_mol"] = val
                        break
                    except ValueError:
                        pass
                if result["dG_kcal_mol"] is not None:
                    break
        return result

    def run_refinement(
        self,
        complex_pdb: str | Path,
        output_dir: str | Path,
        ligand_resname: str = "FEN",
        receptor_chain: str = "H",
        ligand_chain: str = "Z",
        n_models: int = 20,
    ) -> dict[str, Any]:
        """Run HADDOCK3 refinement + built-in Prodigy-LIG scoring on a complex PDB.
        
        Args:
            complex_pdb: Path to complex PDB (antibody + ligand).
            output_dir: Directory to write config, run, and results.
            ligand_resname: Residue name of the small molecule (e.g. "FEN").
            receptor_chain: Chain ID of the antibody to use as receptor (single chain).
            ligand_chain: Chain ID of the ligand molecule.
            n_models: Number of refined models to generate.
        """
        out_path = Path(output_dir).resolve()
        out_path.mkdir(parents=True, exist_ok=True)
        
        cfg_path = out_path / "haddock3_refine.cfg"
        wsl_pdb = self.to_wsl_path(complex_pdb)
        wsl_out = self.to_wsl_path(out_path)

        # Generate HADDOCK3 config — CORRECT FORMAT:
        # - molecules is a TOP-LEVEL global param (not inside [topoaa])
        # - Use built-in [prodigyligand] module instead of external CLI
        # - receptor_chain = antibody heavy chain (primary binding partner)
        # - ligand_chain = small molecule chain (e.g. Z for fentanyl)
        cfg_content = f"""
# HADDOCK3 refinement config generated by AbEngineCore
# molecules must be at top level — not inside [topoaa]
run_dir = "{wsl_out}/run"
molecules = ["{wsl_pdb}"]
mode = "local"
ncores = 4

[topoaa]
autohis = true
autotoppar = true

[emref]
tolerance = 20
sampling_factor = {n_models}

[seletop]
select = 1

[prodigyligand]
receptor_chain = "{receptor_chain}"
ligand_chain = "{ligand_chain}"
ligand_resname = "{ligand_resname}"
temperature = 25.0
electrostatics = true
to_pkd = true
"""
        cfg_path.write_text(cfg_content.strip(), encoding="utf-8")
        wsl_cfg = self.to_wsl_path(cfg_path)

        print(f"[HADDOCK3] Starting refinement + Prodigy-LIG for {complex_pdb}...")
        t0 = time.time()

        # Execute via WSL
        proc = subprocess.run(
            ["wsl", "bash", "-c", f"source ~/.bashrc && haddock3 {wsl_cfg}"],
            capture_output=True, text=True, cwd=str(self.root)
        )
        elapsed = time.time() - t0

        if proc.returncode != 0 and "Finished" not in (proc.stderr + proc.stdout):
            return {
                "status": "HADDOCK_FAIL",
                "error": (proc.stderr or proc.stdout)[-1200:],
                "elapsed": round(elapsed, 1),
            }

        # Parse Prodigy-LIG scores from run directory
        # HADDOCK3 writes prodigyligand scores to CSV files
        run_wsl = f"{wsl_out}/run"
        score_proc = subprocess.run(
            ["wsl", "bash", "-c",
             f"find {run_wsl} -name 'prodigyligand*.csv' 2>/dev/null | "
             "xargs -I{{}} cat {{}} 2>/dev/null | head -40"],
            capture_output=True, text=True
        )

        return {
            "status": "SUCCESS",
            "elapsed": round(elapsed, 1),
            "prodigyligand_csv": score_proc.stdout.strip() or None,
            "haddock_log_tail": proc.stdout[-600:] or proc.stderr[-600:],
            "run_dir_wsl": run_wsl,
        }

if __name__ == "__main__":
    # Quick test
    wrapper = HaddockLigandWrapper(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite")
    print(f"WSL Root: {wrapper.wsl_root}")
    test_p = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\test.pdb"
    print(f"Test Path: {wrapper.to_wsl_path(test_p)}")
