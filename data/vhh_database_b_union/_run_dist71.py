"""Run cdr_physchem_distribution for VHH71."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.chdir(r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite')

import scripts.cdr_physchem_distribution as dist
from pathlib import Path
import json

csv_path = Path('data/vhh_database_b_union/vhh71_merged_cdr_segments.csv')
loci = {'vhh_cdr1': 'CDR1', 'vhh_cdr2': 'CDR2', 'vhh_cdr3': 'CDR3'}
id_col = 'safe_id'
label = 'VHH71 (VHH42 + VHH29)'
cdr_def = 'IMGT'
output = Path('data/reference/CDR_physchem_VHH71_v1.json')

cdr_table = dist.load_cdr_table(csv_path, id_col, loci)
print('Loaded CDR table:', {k: len(v) for k, v in cdr_table.items()}, flush=True)

loci_blocks = {locus: dist.compute_locus_block(cdr_pairs) for locus, cdr_pairs in cdr_table.items()}
print('Computed blocks:', {k: v['n'] for k, v in loci_blocks.items()}, flush=True)

from datetime import date
output_json = {
    '_meta': {
        'source': label,
        'cdr_definition': cdr_def,
        'n_sequences': len(list(cdr_table.values())[0]) if cdr_table else 0,
        'generated': str(date.today()),
        'loci': list(loci.keys()),
    },
    'loci': loci_blocks,
}

output.parent.mkdir(parents=True, exist_ok=True)
with open(output, 'w') as f:
    json.dump(output_json, f, indent=2)
print(f'Saved to {output}', flush=True)
