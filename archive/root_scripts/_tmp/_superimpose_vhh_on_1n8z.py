"""
Superimpose VHH VGRW_SR_R2 onto 1N8Z chain H (trastuzumab VH)
using CDR CA atoms → produce VHH + HER2 ECD complex PDB.

No AF2 needed — deterministic binding pose from crystal template.
"""
from Bio.PDB import PDBParser, PDBIO, Select, Superimposer
import numpy as np

VHH_PDB  = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\projects\mumab4d5_VGRW_SR_R2\vhh_pipeline_runs\5bfa8e9c-02ba-400e-80c8-590dab28366e\structures\auto_VGRW.pdb"
CPLX_PDB = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\_1N8Z.pdb"
OUT_PDB  = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\projects\mumab4d5_VGRW_SR_R2\VHH_HER2_docked.pdb"

parser = PDBParser(QUIET=True)
vhh_struct = parser.get_structure("VHH", VHH_PDB)
cplx_struct = parser.get_structure("1N8Z", CPLX_PDB)

# 1N8Z chains: B=VH (trastuzumab heavy), A=VL (light), C=HER2 ECD
vh_chain   = cplx_struct[0]["B"]
her2_chain = cplx_struct[0]["C"]

# VHH is chain H or single chain
vhh_chains = list(vhh_struct[0].get_chains)
vhh_chain = vhh_chains[0]
print(f"VHH chain id: {vhh_chain.id}  residues: {len(list(vhh_chain.get_residues))}")
print(f"1N8Z VH residues: {len(list(vh_chain.get_residues))}")
print(f"1N8Z HER2 residues: {len(list(her2_chain.get_residues))}")

# CDR residue ranges in Kabat (sequential numbering in PDB)
# muMAb4D5 VH CDRs (Kabat): CDR1 31-35, CDR2 50-65, CDR3 95-102
# Use a broader window including FR anchors for robustness
CDR_RANGES = list(range(26, 36)) + list(range(50, 66)) + list(range(95, 103))

def get_ca_atoms(chain, res_range):
    atoms = []
    res_ids = []
    for res in chain.get_residues:
        seq_id = res.get_id[1]
        if seq_id in res_range and "CA" in res:
            atoms.append(res["CA"])
            res_ids.append(seq_id)
    return atoms, res_ids

vh_atoms, vh_ids   = get_ca_atoms(vh_chain, CDR_RANGES)
vhh_atoms, vhh_ids = get_ca_atoms(vhh_chain, CDR_RANGES)

print(f"\nCDR CA atoms found — VH(1N8Z): {len(vh_atoms)}, VHH: {len(vhh_atoms)}")

# Match on common residue positions
common = sorted(set(vh_ids) & set(vhh_ids))
print(f"Common CDR positions for alignment: {len(common)}")

vh_ca  = [a for a, i in zip(vh_atoms, vh_ids)  if i in common]
vhh_ca = [a for a, i in zip(vhh_atoms, vhh_ids) if i in common]

if len(common) < 10:
    print("WARNING: fewer than 10 anchor atoms — falling back to all CA atoms")
    vh_all  = [r["CA"] for r in vh_chain.get_residues  if "CA" in r]
    vhh_all = [r["CA"] for r in vhh_chain.get_residues if "CA" in r]
    n = min(len(vh_all), len(vhh_all))
    vh_ca  = vh_all[:n]
    vhh_ca = vhh_all[:n]
    print(f"  Fallback: aligning first {n} CA atoms")

# Superimpose
sup = Superimposer
sup.set_atoms(vh_ca, vhh_ca)  # fixed=VH, moving=VHH
sup.apply(vhh_struct.get_atoms)
print(f"\nSuperimposition RMSD: {sup.rms:.3f} Å")

# Write output: VHH (chain A) + HER2 (chain B)
class ComplexSelect(Select):
    def accept_chain(self, chain):
        return True

# Rename chains for clarity
for ch in vhh_struct[0].get_chains:
    ch.id = "A"
her2_chain.id = "B"

io = PDBIO

# Merge into one structure
from Bio.PDB import Structure, Model

out_struct = Structure.Structure("complex")
out_model  = Model.Model(0)
out_struct.add(out_model)

for ch in vhh_struct[0].get_chains:
    out_model.add(ch)
out_model.add(her2_chain)

io.set_structure(out_struct)
io.save(OUT_PDB)
print(f"\nSaved docked complex → {OUT_PDB}")
print("\n===  ===")
print("Chain A = VHH VGRW_SR_R2 (superimposed onto 1N8Z VH position)")
print("Chain B = HER2 ECD (from 1N8Z, unchanged)")
print(f"RMSD to trastuzumab VH CDRs: {sup.rms:.3f} Å")
print("\n PyMOL / ChimeraX  VHH  HER2 ")
print(": VHH CDR3 (SRWGGDGFY)  HER2 Domain IV ")
