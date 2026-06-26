#!/usr/bin/env python3
"""Run structure metrics on one PDB with per-step timing to find bottleneck."""
import json
import sys
import time
from pathlib import Path

# Add project root so we can import
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Bio.PDB import PDBParser
from Bio.PDB.Polypeptide import is_aa
import numpy as np

from scripts.structure_metrics_humanization import (
    analyze_structure,
    metrics_to_dict,
)

def main():
    pdb = Path("data/structures/engineered/Abazistobart.pdb")
    lookup_path = Path("data/humanization_assay/vernier_index_lookup.json")
    if not pdb.is_file():
        print(f"Not found: {pdb}")
        return
    with open(lookup_path, encoding="utf-8") as f:
        vernier_lookup = json.load(f)
    print(f"PDB: {pdb}, lookup entries: {len(vernier_lookup)}")

    t0 = time.perf_counter()
    m = analyze_structure(
        pdb,
        chain_vh="H",
        chain_vl="L",
        vernier_lookup=vernier_lookup,
        skip_sasa=True,
    )
    elapsed = time.perf_counter() - t0
    print(f"analyze_structure total: {elapsed:.2f}s")
    print(f"Errors: {m.errors}")
    if not m.errors:
        d = metrics_to_dict(m)
        print(f"Angle: {d.get('vh_vl_angle_deg')}, packing keys: {len(d.get('vernier_packing', {}))}")
    return

if __name__ == "__main__":
    main()
