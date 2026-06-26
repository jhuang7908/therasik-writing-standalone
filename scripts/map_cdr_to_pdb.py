"""Map CDR regions to PDB residue numbers for ProteinMPNN masking."""
import sys
import json
from Bio.PDB import PDBParser
from Bio.Data.IUPACData import protein_letters_3to1

def three_to_one(name):
    return protein_letters_3to1.get(name.lower().capitalize(), 'X')

pdb_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\projects\mumab4d5_VGRW_SR_R2\affinity_maturation\complex_repaired.pdb'
parser = PDBParser(QUIET=True)
struct = parser.get_structure('complex', pdb_path)

wt_seq = 'QVQLVQSGAEVVKPGSSVKLSCKASGFNIKDTYIHWVKQRPEQGREWIGRIYPTNGYTRYDPKFQDRATITADTSTSTAYLEVSRLRSEDTAVYYCSRWGGDGFYAMDYWGQGASVTVSS'

cdr_defs = {
    'CDR1': {'seq': 'GFNIKDTYIH', 'length': 10},
    'CDR2': {'seq': 'WIGRIYPTNGYTRYDPK', 'length': 17},
    'CDR3': {'seq': 'SRWGGDGFYAMDY', 'length': 13},
}

for cdr_name, cdr_info in cdr_defs.items():
    idx = wt_seq.find(cdr_info['seq'])
    if idx >= 0:
        cdr_info['seq_start'] = idx
        cdr_info['seq_end'] = idx + cdr_info['length'] - 1
        sys.stderr.write(f"{cdr_name}: '{cdr_info['seq']}' at linear positions {idx}-{idx+cdr_info['length']-1}\n")
    else:
        sys.stderr.write(f"WARNING: {cdr_name} sequence '{cdr_info['seq']}' not found in WT!\n")

chain_a = struct[0]['A']
residues = [r for r in chain_a if r.id[0] == ' ']
pdb_seq = ''.join(three_to_one(r.get_resname()) for r in residues)
assert pdb_seq == wt_seq, f"PDB seq mismatch!\nPDB: {pdb_seq}\nWT:  {wt_seq}"

pdb_resnums = [r.id[1] for r in residues]

sys.stderr.write(f"\nPDB residue number range: {pdb_resnums[0]}-{pdb_resnums[-1]}\n")
sys.stderr.write(f"Number of residues: {len(pdb_resnums)}\n\n")

mask_config = {
    'pdb_file': pdb_path,
    'vhh_chain': 'A',
    'antigen_chain': 'B',
    'wt_sequence': wt_seq,
    'wt_oasis_coverage': 0.545,
    'cdr_regions': {},
    'design_mask': {
        'redesign_cdrs': ['CDR1', 'CDR2'],
        'fix_cdrs': ['CDR3'],
        'fix_framework': True,
        'designable_pdb_residues': [],
        'fixed_pdb_residues': [],
    }
}

for cdr_name, cdr_info in cdr_defs.items():
    start = cdr_info['seq_start']
    end = cdr_info['seq_end']
    pdb_start = pdb_resnums[start]
    pdb_end = pdb_resnums[end]
    pdb_positions = pdb_resnums[start:end+1]
    
    mask_config['cdr_regions'][cdr_name] = {
        'sequence': cdr_info['seq'],
        'linear_start': start,
        'linear_end': end,
        'pdb_resnum_start': pdb_start,
        'pdb_resnum_end': pdb_end,
        'pdb_resnums': pdb_positions,
        'length': cdr_info['length'],
    }
    
    sys.stderr.write(f"{cdr_name}: PDB# {pdb_start}-{pdb_end} ({len(pdb_positions)} residues)\n")
    for i, (pos, aa) in enumerate(zip(pdb_positions, cdr_info['seq'])):
        sys.stderr.write(f"  PDB# {pos:>4} = {aa}\n")
    
    if cdr_name in ['CDR1', 'CDR2']:
        mask_config['design_mask']['designable_pdb_residues'].extend(pdb_positions)
    else:
        mask_config['design_mask']['fixed_pdb_residues'].extend(pdb_positions)

fr_positions = [pdb_resnums[i] for i in range(len(wt_seq))
                if i not in range(cdr_defs['CDR1']['seq_start'], cdr_defs['CDR1']['seq_end']+1)
                and i not in range(cdr_defs['CDR2']['seq_start'], cdr_defs['CDR2']['seq_end']+1)
                and i not in range(cdr_defs['CDR3']['seq_start'], cdr_defs['CDR3']['seq_end']+1)]
mask_config['design_mask']['fixed_pdb_residues'].extend(fr_positions)

sys.stderr.write(f"\n=== Design Mask Summary ===\n")
sys.stderr.write(f"Designable (CDR1+CDR2): {len(mask_config['design_mask']['designable_pdb_residues'])} positions\n")
sys.stderr.write(f"Fixed (CDR3+FR): {len(mask_config['design_mask']['fixed_pdb_residues'])} positions\n")
sys.stderr.write(f"Total: {len(mask_config['design_mask']['designable_pdb_residues']) + len(mask_config['design_mask']['fixed_pdb_residues'])} / {len(wt_seq)} residues\n")

out_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\projects\denovo_HER2_VGRW_SR_R2\config\mask_strategy.json'
with open(out_path, 'w') as f:
    json.dump(mask_config, f, indent=2)
sys.stderr.write(f"\nMask config saved to: {out_path}\n")
