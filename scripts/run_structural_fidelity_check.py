#!/usr/bin/env python3
"""
run_structural_fidelity_check.py — InSynBio AbEngineCore
========================================================
Run the mandatory structural fidelity check after optimization.

Pipeline order (per spec):
  structure_validation → developability → cdr_scan → cmc_advisor → mutation_advisor
  → variant_generation → variant_re_evaluation → qc_gate → structural_fidelity_check
  → report_generation

This script runs the structural_fidelity_check step:
  - Compares mouse, initial humanized, and optimized PDBs
  - Saves structural_fidelity.json to project directory
  - Can be invoked before report_generation

Usage:
  python scripts/run_structural_fidelity_check.py \\
    --mouse path/to/mouse.pdb \\
    --initial path/to/humanized_initial.pdb \\
    --optimized path/to/optimized.pdb \\
    --out project_dir/structural_fidelity.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(SUITE))


def main() -> int:
    ap = argparse.ArgumentParser(description="Run structural fidelity check (three-way PDB comparison)")
    ap.add_argument("--mouse", required=True, help="Mouse antibody PDB path")
    ap.add_argument("--initial", required=True, help="Initial humanized PDB path")
    ap.add_argument("--optimized", required=True, help="Optimized variant PDB path")
    ap.add_argument("--out", required=True, help="Output structural_fidelity.json path")
    ap.add_argument("--vh", default="H", help="VH chain ID")
    ap.add_argument("--vl", default="L", help="VL chain ID")
    args = ap.parse_args()

    from core.structure.structural_fidelity import run_structural_fidelity_check

    result = run_structural_fidelity_check(
        mouse_pdb=args.mouse,
        humanized_initial_pdb=args.initial,
        optimized_pdb=args.optimized,
        output_path=args.out,
        chain_vh=args.vh,
        chain_vl=args.vl,
    )
    if "error" in result:
        print(f"[ERROR] {result['error']}")
        return 1
    print(f"[OK] structural_fidelity.json saved: {args.out}")
    print(f"  Fv RMSD (mouse vs opt): {result.get('fv_rmsd_mouse_vs_opt', '—')} Å")
    print(f"  Fv RMSD (initial vs opt): {result.get('fv_rmsd_initial_vs_opt', '—')} Å")
    print(f"  VH/VL orientation change: {result.get('vh_vl_orientation_change', '—')}°")
    print(f"  structural_warning: {result.get('structural_warning', False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
