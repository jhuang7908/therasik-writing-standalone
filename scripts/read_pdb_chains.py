import sys
from Bio.PDB import PDBParser
from Bio.Data.IUPACData import protein_letters_3to1

def three_to_one(name):
    return protein_letters_3to1.get(name.lower().capitalize(), 'X')

parser = PDBParser(QUIET=True)
pdb_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\projects\mumab4d5_VGRW_SR_R2\affinity_maturation\complex_repaired.pdb'
struct = parser.get_structure('complex', pdb_path)

for model in struct:
    for chain in model:
        residues = [r for r in chain if r.id[0] == ' ']
        if not residues:
            continue
        try:
            seq = ''.join(three_to_one(r.get_resname()) for r in residues)
        except:
            seq = 'PARSE_ERROR'
        first_id = residues[0].id[1]
        last_id = residues[-1].id[1]
        sys.stderr.write(f"Chain {chain.id}: {len(residues)} residues, PDB# {first_id}-{last_id}\n")
        sys.stderr.write(f"  Seq[:30]: {seq[:30]}...\n")
        sys.stderr.write(f"  Seq[-30:]: ...{seq[-30:]}\n")
        sys.stderr.write(f"  Full seq ({len(seq)} aa): {seq}\n\n")
