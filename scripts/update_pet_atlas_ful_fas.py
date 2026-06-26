import csv
import json

MASTER_CSV = 'data/pet_antibody_atlas/master_table.csv'

# New entries to add
new_entries = [
    {
        'antibody_id': 'Fulranumab_InSynBio_Dog',
        'pet_type': 'canine',
        'format': 'Caninised Whole mAb',
        'genetics': 'Caninised',
        'target': 'NGFB',
        'phase': 'Preclinical',
        'companies': 'InSynBio',
        'conditions_active': 'Pain',
        'vh_seq': 'EVQLVESGGDLVKPVGSLRLSCVASGFTLRSYSMNWVRQAPGKGLQWVSYISRSSHTIFYADSVKGRFTISRDNAKNTLYLQLQSLRAEETALYYCARVYSSGWHVSDYFDYWGQGILVTVSS',
        'vl_seq': 'EIVLTQSPASLSLSQEEKVTITCRASQGISSALAWYQQKPGQAPKLLIYDASSLESGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQFNSYPLTFGGGTKVEIK',
        'vh_dog_germline': 'IGHV3-35*01',
        'vl_dog_germline': 'IGKV3-18*02',
        'pdb_path': 'projects/Ful_Fas_Engineering/Ful_dog_opt_v2_model.pdb',
        'notes': 'InSynBio engineered, 91.9% VH identity to patent, optimized pI and CMC.',
        'fc_species': 'canine',
        'fc_isotype_pet': 'dog_IgGB',
    },
    {
        'antibody_id': 'Fulranumab_Patent_Dog',
        'pet_type': 'canine',
        'format': 'Caninised Whole mAb',
        'genetics': 'Caninised',
        'target': 'NGFB',
        'phase': 'Patent',
        'companies': 'Merck Animal Health',
        'conditions_active': 'Pain',
        'vh_seq': 'EVQLVESGGDLVKPGGSLRLSCVASGFTFSSYSMNWIRQAPGKGLQWVSYISRSSHTIFYADSVKGRFTISRDNAKNTLYLQMNSLRDEDTAVYYCARVYSSGWHVSDYFDYWGQGTLVTVSS',
        'vl_seq': 'EIVMTQSPASLSLSQEEKVTITCRASQGISSALAWYQQKPGQAPKLLIYDASSLESGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQFNSYPLTFGQGTKVEIK',
        'notes': 'CN118401549A. Claimed 32-49pM EC50.',
        'fc_species': 'canine',
        'fc_isotype_pet': 'dog_IgGB',
    },
    {
        'antibody_id': 'Fasinumab_InSynBio_Dog',
        'pet_type': 'canine',
        'format': 'Caninised Whole mAb',
        'genetics': 'Caninised',
        'target': 'NGFB',
        'phase': 'Preclinical',
        'companies': 'InSynBio',
        'conditions_active': 'Pain',
        'vh_seq': 'QVQLVQSGGNLVKPVGSLRLSCVVSGFTLTELSIHWVRQAPGKGLQWMGGFDPEDGETIYAQKFQGRVTMSENTAKNTAYLQLQSLRAQETALYYCSTIGVVTNFDNWGQGTLVTVSS',
        'vl_seq': 'QIVMTQSPASLSLSQQQKVTITCRASQAIRNDLGWYQQKPGQAPKRLIYAAFNLQSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQYNRYPWTFGQGTKVEIK',
        'vh_dog_germline': 'IGHV3-35*01',
        'vl_dog_germline': 'IGKV3-18*02',
        'pdb_path': 'projects/Ful_Fas_Engineering/Fas_dog_opt_v2_model.pdb',
        'notes': 'InSynBio FR Anchored. Strategy to rescue affinity loss reported in patent.',
        'fc_species': 'canine',
        'fc_isotype_pet': 'dog_IgGB',
    },
    {
        'antibody_id': 'Fasinumab_Patent_Dog',
        'pet_type': 'canine',
        'format': 'Caninised Whole mAb',
        'genetics': 'Caninised',
        'target': 'NGFB',
        'phase': 'Patent',
        'companies': 'Merck Animal Health',
        'conditions_active': 'Pain',
        'vh_seq': 'EVQLVQSGAEVKKPGASVKVSCKTSGYTFIELSIHWVRQAPGAGLDWMGGFDPEDGETIYAQKFQGRVTLTADTSTSTAYMELSSLRAGDIAVYYCARIGVVTNFDNWGQGTLVTVSS',
        'vl_seq': 'EIVMTQSPASLSLSQEEKVTITCRASQAIRNDLGWYQQKPGQAPKRLIYAAFNLQSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQYNRYPWTFGQGTKVEIK',
        'notes': 'CN118401549A. Patent admits EC50 unmeasurable. Failed caninization due to FR mismatch.',
        'fc_species': 'canine',
        'fc_isotype_pet': 'dog_IgGB',
    }
]

with open(MASTER_CSV, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

existing = {r['antibody_id'] for r in rows}

for ne in new_entries:
    if ne['antibody_id'] not in existing:
        row = {f: ne.get(f, '') for f in fieldnames}
        rows.append(row)

with open(MASTER_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Added {len(new_entries)} entries to {MASTER_CSV}")
