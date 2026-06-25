#!/usr/bin/env python3
"""
 - Full200  cluster_1_model_2.pdb
 Fast （N62, Y67, K70, F112）
"""
from Bio.PDB import PDBParser, NeighborSearch, SASA
import numpy as np
import sys

PDB = sys.argv[1] if len(sys.argv) > 1 else \
    "/mnt/d/InSynBio-AI-Research/Antibody_Engineer_Suite/projects/mumab4d5_VGRW_SR_R2/cluster_1_model_2.pdb"

parser = PDBParser(QUIET=True)
struct = parser.get_structure("complex", PDB)
model = struct[0]

chains = [c.id for c in model]
print(f"Chains in PDB: {chains}")

# （VHH=A, HER2=B）
all_atoms = list(model.get_atoms())
vhh_residues  = list(model["A"].get_residues())
her2_residues = list(model["B"].get_residues())
print(f"VHH residues: {len(vhh_residues)}, HER2 residues: {len(her2_residues)}")

her2_atoms = [a for r in her2_residues for a in r.get_atoms()]
vhh_atoms  = [a for r in vhh_residues  for a in r.get_atoms()]

# ── 5 Å  ────────────────────────────────────────────────
ns_her2 = NeighborSearch(her2_atoms)
ns_vhh  = NeighborSearch(vhh_atoms)

CUTOFF = 5.0

contact_vhh = {}   # VHH residue -> list of HER2 residues
for atom in vhh_atoms:
    neighbors = ns_her2.search(atom.coord, CUTOFF, "R")
    if neighbors:
        res = atom.get_parent()
        resi = res.get_id()[1]
        resn = res.get_resname()
        if resi not in contact_vhh:
            contact_vhh[resi] = {"resn": resn, "her2": set()}
        for nb in neighbors:
            contact_vhh[resi]["her2"].add(nb.get_id()[1])

# ── SASA （PyMOL-like ShrakeRupley）────────────────────────
sr = SASA.ShrakeRupley()
sr.compute(model, level="R")

print("\n" + "="*65)
print(f"{'VHH Res':>10}  {'nHER2':>6}  {'SASA(Å²)':>10}  {'HER2 contacts'}")
print("="*65)

KNOWN_WHITELIST = {62: "N62S/D", 67: "Y67F", 70: "K70R", 112: "F112Y"}

for resi in sorted(contact_vhh):
    d = contact_vhh[resi]
    resn = d["resn"]
    n_her2 = len(d["her2"])
    her2_list = ",".join(str(x) for x in sorted(d["her2"])[:6])
    try:
        sasa = model["A"][(" ", resi, " ")].sasa
    except Exception:
        sasa = -1.0
    flag = " ← WHITELIST" if resi in KNOWN_WHITELIST else ""
    flag += " *** NEW ***" if resi not in KNOWN_WHITELIST and n_her2 >= 2 else ""
    print(f"{resn:>4}{resi:<6}  {n_her2:>6}  {sasa:>10.1f}  {her2_list}{flag}")

print("="*65)
print(f"\nTotal VHH interface residues (≥1 contact @ 5Å): {len(contact_vhh)}")
print(f"Known whitelist found: {[k for k in KNOWN_WHITELIST if k in contact_vhh]}")
print(f"Residues with ≥3 HER2 contacts: {[r for r,d in contact_vhh.items() if len(d['her2'])>=3]}")
