import pandas as pd

file_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada245\database\ada_master_245_curated.csv'
df = pd.read_csv(file_path)

# High-Sensitivity Humanized Updates
humanized_updates = {
    'Risankizumab': {
        'ada_value_display': '24.0% (High-Sensitivity)',
        'ada_first_pct': 24.0,
        'ada_source_type_curated': 'High-Sensitivity',
        'ada_evidence_chain_excerpt': 'High-sensitivity ECL assay detected 24% ADA incidence in long-term clinical trials.'
    },
    'Tildrakizumab': {
        'ada_value_display': '6.5% (ECL)',
        'ada_first_pct': 6.5,
        'ada_source_type_curated': 'High-Sensitivity',
        'ada_evidence_chain_excerpt': 'Approximately 6.5% to 12% ADA incidence confirmed via validated ECL assays.'
    },
    'Benralizumab': {
        'ada_value_display': '13.0%',
        'ada_first_pct': 13.0,
        'ada_source_type_curated': 'High-Sensitivity',
        'ada_evidence_chain_excerpt': '13% ADA incidence reported in late-phase trials using modern sensitive assays.'
    },
    'Mepolizumab': {
        'ada_value_display': '6.0%',
        'ada_first_pct': 6.0,
        'ada_source_type_curated': 'High-Sensitivity',
        'ada_evidence_chain_excerpt': 'Consistent 6% ADA rate observed across multiple clinical indications.'
    },
    'Natalizumab': {
        'ada_value_display': '9.0%',
        'ada_first_pct': 9.0,
        'ada_source_type_curated': 'High-Sensitivity',
        'ada_evidence_chain_excerpt': 'Persistent ADA detected in 6% and transient in 3%, total 9% using sensitive bridging ELISA/ECL.'
    }
}

for name, fields in humanized_updates.items():
    mask = df['antibody_name'] == name
    if mask.any():
        print(f"Updating Humanized antibody: {name}")
        for col, val in fields.items():
            df.loc[mask, col] = val
    else:
        print(f"Warning: {name} not found in database.")

df.to_csv(file_path, index=False)
print("Batch 9 (Humanized Calibration) complete.")
