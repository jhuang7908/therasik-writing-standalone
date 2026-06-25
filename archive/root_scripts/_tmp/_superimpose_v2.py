"""
Sequence-guided superimposition of VHH onto 1N8Z VH (chain B).
Uses pairwise alignment to find matching CA positions instead of
relying on residue number identity.
"""
from Bio.PDB import PDBParser, PDBIO, Superimposer, Structure, Model
from Bio import pairwise2
import warnings
warnings.filterwarnings("ignore")

VHH_PDB  = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\projects\mumab4d5_VGRW_SR_R2\vhh_pipeline_runs\5bfa8e9c-02ba-400e-80c8-590dab28366e\structures\auto_VGRW.pdb"
CPLX_PDB = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\_1N8Z.pdb"
OUT_PDB  = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\projects\mumab4d5_VGRW_SR_R2\VHH_HER2_docked_v2.pdb"

AA3 = {'ALA':'A','ARG':'R','ASN':'N','ASP':'D','CYS':'C','GLN':'Q','GLU':'E',
       'GLY':'G','HIS':'H','ILE':'I','LEU':'L','LYS':'K','MET':'M','PHE':'F',
       'PRO':'P','SER':'S','THR':'T','TRP':'W','TYR':'Y','VAL':'V'}

parser = PDBParser(QUIET=True)
vhh_struct  = parser.get_structure("VHH",  VHH_PDB)
cplx_struct = parser.get_structure("1N8Z", CPLX_PDB)

vh_chain   = cplx_struct[0]["B"]   # trastuzumab VH
her2_chain = cplx_struct[0]["C"]   # HER2 ECD
vhh_chain  = list(vhh_struct[0].get_chains)[0]

# Get ATOM (protein) residues only (exclude HETATM)
def protein_residues(chain):
    return [r for r in chain.get_residues if r.get_id[0] == ' ' and r.get_resname in AA3]

vh_res   = protein_residues(vh_chain)
vhh_res  = protein_residues(vhh_chain)
her2_res = protein_residues(her2_chain)

vh_seq   = ''.join(AA3[r.get_resname] for r in vh_res)
vhh_seq  = ''.join(AA3[r.get_resname] for r in vhh_res)

print(f"1N8Z VH  (chain B): {len(vh_res)} residues")
print(f"VHH VGRW_SR_R2:     {len(vhh_res)} residues")
print(f"HER2 ECD (chain C): {len(her2_res)} residues")
print(f"\n1N8Z VH  seq: {vh_seq[:30]}...")
print(f"VHH seq:      {vhh_seq[:30]}...")

# Sequence alignment — use only first 120 aa of VH (Fv region)
vh_fv  = vh_seq[:120]
vh_res_fv = vh_res[:120]

alns = pairwise2.align.globalms(vh_fv, vhh_seq, 2, -1, -3, -0.5)
aln = alns[0]
print(f"\nGlobal alignment score: {aln.score:.1f}")
print(f"Aligned:\n  VH : {aln.seqA}")
print(f"  VHH: {aln.seqB}")

# Build index pairs of matched (non-gap) positions
vh_pairs  = []
vhh_pairs = []
vh_i = vhh_i = 0
for a, b in zip(aln.seqA, aln.seqB):
    if a != '-' and b != '-':
        vh_pairs.append(vh_res_fv[vh_i])
        vhh_pairs.append(vhh_res[vhh_i])
    if a != '-': vh_i += 1
    if b != '-': vhh_i += 1

print(f"\nMatched aligned positions: {len(vh_pairs)}")

# Extract CA atoms
def ca(res_list):
    return [r["CA"] for r in res_list if "CA" in r]

vh_ca  = ca(vh_pairs)
vhh_ca = ca(vhh_pairs)
n = min(len(vh_ca), len(vhh_ca))
vh_ca  = vh_ca[:n]
vhh_ca = vhh_ca[:n]

print(f"CA atoms for superimposition: {n}")

# Superimpose
sup = Superimposer
sup.set_atoms(vh_ca, vhh_ca)
sup.apply(vhh_struct.get_atoms)
print(f"Superimposition RMSD: {sup.rms:.3f} Å")

# Check CDR3 position after alignment
print("\nVHH CDR3 residues (pos 95-102 in VHH):")
for r in vhh_res:
    rid = r.get_id[1]
    if 95 <= rid <= 107:
        print(f"  VHH pos {rid}: {AA3.get(r.get_resname,'X')}")

# Write: VHH (A) + HER2 (B)
out_struct = Structure.Structure("VHH_HER2")
out_model  = Model.Model(0)
out_struct.add(out_model)

vhh_chain.detach_parent
vhh_chain.id = "A"
her2_chain.detach_parent
her2_chain.id = "B"
out_model.add(vhh_chain)
out_model.add(her2_chain)

io = PDBIO
io.set_structure(out_struct)
io.save(OUT_PDB)

print(f"\n✓ Saved: {OUT_PDB}")
print(f"  Chain A = VHH VGRW_SR_R2  ({len(vhh_res)} aa)")
print(f"  Chain B = HER2 ECD        ({len(her2_res)} aa)")
print(f"  RMSD to trastuzumab VH Fv: {sup.rms:.3f} Å")
print(f"\nPyMOL/ChimeraX でく:")
print(f"  open {OUT_PDB}")
print(f"  select her2, chain B and resi 557-605")
print(f"  select vhh_cdr3, chain A and resi 95-107")
