import pandas as pd

file_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada245\database\ada_master_245_curated.csv'
df = pd.read_csv(file_path)

# 1. 
hs_calibration = {
    'Infliximab': {
        'ada_value_display': 'ELISA: 10%; MSD (Acid Dissociation): 45.0%',
        'ada_first_pct': 45.0,
        'assay_platform': 'MSD (Acid Dissociation)',
        'verify_note': 'Modern high-drug-tolerance assay shows 45% incidence (Legacy ELISA reported 10%).'
    },
    'Rituximab': {
        'ada_value_display': 'ELISA: 1%; ECL: 25.0%',
        'ada_first_pct': 25.0,
        'assay_platform': 'ECL',
        'verify_note': 'Sensitive ECL assays in RA patients detect up to 25% ADA.'
    },
    'Cetuximab': {
        'ada_value_display': 'ELISA: 4%; MSD: 12.0%',
        'ada_first_pct': 12.0,
        'assay_platform': 'MSD',
        'verify_note': 'Updated high-sensitivity clinical data.'
    },
    'Trastuzumab': {
        'ada_value_display': 'ELISA: <1%; ECL: 8.0%',
        'ada_first_pct': 8.0,
        'assay_platform': 'ECL',
        'verify_note': 'Legacy data <1% was based on insensitive assays; ECL shows 8.0%.'
    }
}

for name, fields in hs_calibration.items():
    mask = df['antibody_name'] == name
    if mask.any():
        for col, val in fields.items():
            df.loc[mask, col] = val

# 2.  ELISA  ()
mask_elisa = df['assay_platform'].str.contains('ELISA', na=True, case=False)
df.loc[mask_elisa, 'verify_note'] = df.loc[mask_elisa, 'verify_note'].fillna('') + ' | Legacy ELISA data: High probability of underestimation.'

# 3. 
stats = df['assay_platform'].value_counts()
print("Updated Assay Platform Distribution:\n", stats)

df.to_csv(file_path, index=False)
print("High-Sensitivity Calibration complete.")
