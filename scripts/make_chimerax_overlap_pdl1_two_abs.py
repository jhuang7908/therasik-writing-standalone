#!/usr/bin/env python3
"""
Make ChimeraX overlap script for two PD-L1 antibody complexes.

:
  python scripts/make_chimerax_overlap_pdl1_two_abs.py
    --ab1 "path/to/pdl1_ab1_a7c2a.result"
    --ab2 "path/to/PDL1_Ab2_dec04.result"
    -o overlap_PDL1_ab1_ab2.cxc  #  dongxiao 

: a. H(VH), b. L(VL), c. PD-L1
ColabFold : A=VH, B=VL, C=PD-L1
"""

from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path


def find_rank001_pdb(result_path: str) -> Path | None:
    """ ColabFold .result  rank_001 PDB（ relaxed）。"""
    p = Path(result_path)
    if not p.exists():
        return None
    # 
    relaxed = list(p.rglob("*relaxed*rank_001*.pdb"))
    unrelaxed = list(p.rglob("*unrelaxed*rank_001*.pdb"))
    if relaxed:
        return Path(relaxed[0])
    if unrelaxed:
        return Path(unrelaxed[0])
    # ： rank_001
    any_r1 = list(p.rglob("*rank_001*.pdb"))
    return Path(any_r1[0]) if any_r1 else None


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate ChimeraX overlap script for two PD-L1 Ab complexes.")
    ap.add_argument("--ab1", required=True, help="PDL1_Ab1 .result folder path.")
    ap.add_argument("--ab2", required=True, help="PDL1_Ab2 .result folder path.")
    ap.add_argument("-o", "--out", default="overlap_PDL1_ab1_ab2.cxc", help="Output ChimeraX script path.")
    ap.add_argument("--vh-chain", default="A", help="VH chain ID (default: A).")
    ap.add_argument("--vl-chain", default="B", help="VL chain ID (default: B).")
    ap.add_argument("--pdl1-chain", default="C", help="PD-L1 chain ID (default: C).")
    args = ap.parse_args()

    p1 = find_rank001_pdb(args.ab1)
    p2 = find_rank001_pdb(args.ab2)
    if not p1:
        raise FileNotFoundError(f"No rank_001 PDB found in: {args.ab1}")
    if not p2:
        raise FileNotFoundError(f"No rank_001 PDB found in: {args.ab2}")

    vh, vl, ag = args.vh_chain, args.vl_chain, args.pdl1_chain
    p1_posix = p1.resolve().as_posix()
    p2_posix = p2.resolve().as_posix()

    lines = [
        "set bgColor white",
        "graphics silhouettes true",
        f'open "{p1_posix}" name PDL1_Ab1',
        f'open "{p2_posix}" name PDL1_Ab2',
        f"matchmaker #2/{ag} to #1/{ag}",
        "hide #1 atoms",
        "hide #2 atoms",
        "show #1 cartoons",
        "show #2 cartoons",
        f"color #1/{vh} lightblue",
        f"color #1/{vl} lightcyan",
        f"color #2/{vh} salmon",
        f"color #2/{vl} lightsalmon",
        f"color #1/{ag} #2/{ag} lightgray",
        "view",
        "lighting soft",
    ]

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated: {out_path}")
    print(f"  Ab1: {p1}")
    print(f"  Ab2: {p2}")
    print("Run in ChimeraX: File → Open Script → select the .cxc file")


if __name__ == "__main__":
    main()
