import pandas as pd
import numpy as np
import os

master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv'
batch2_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_batch2_expanded.csv'
output_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_batch2_master_aligned.csv'

# Read master to get columns
df_master = pd.read_csv(master_path)
master_cols = df_master.columns.tolist()

# Read batch 2
df_b2 = pd.read_csv(batch2_path)

# Create a new DataFrame with master columns
df_new = pd.DataFrame(columns=master_cols)

# Mapping dictionary (Batch2 column -> Master column)
mapping = {
    'name': 'antibody_name',
    'ada_pct': 'ada_first_pct',
    'assay': 'assay_platform',
    'indication': 'indication_text',
    'freq': 'dose_freq',
    'route': 'route_curated',
    'targets': 'targets',
    'vh_seq': 'vh_seq',
    'vl_seq': 'vl_seq',
    'vh_germline': 'vh_germline',
    'vl_germline': 'vl_germline',
    'vh_fr1': 'vh_fr1', 'vh_cdr1': 'vh_cdr1', 'vh_fr2': 'vh_fr2', 'vh_cdr2': 'vh_cdr2', 'vh_fr3': 'vh_fr3', 'vh_cdr3': 'vh_cdr3', 'vh_fr4': 'vh_fr4',
    'vl_fr1': 'vl_fr1', 'vl_cdr1': 'vl_cdr1', 'vl_fr2': 'vl_fr2', 'vl_cdr2': 'vl_cdr2', 'vl_fr3': 'vl_fr3', 'vl_cdr3': 'vl_cdr3', 'vl_fr4': 'vl_fr4',
    'status': 'ada_v2_track'
}

for i, row in df_b2.iterrows():
    new_row = {col: '' for col in master_cols}
    
    # Fill based on mapping
    for b2_col, m_col in mapping.items():
        if b2_col in row:
            new_row[m_col] = row[b2_col]
    
    # Fill additional fields
    new_row['ada_value_display'] = f"{row['ada_pct']}%" if pd.notnull(row['ada_pct']) else ''
    new_row['evidence_tier'] = 'Tier 1' # Primary clinical data
    new_row['origin'] = 'clinical'
    
    # Dose MG handling (if string contains mg)
    dose_str = str(row['dose'])
    if 'mg/kg' in dose_str:
        new_row['dose_mg'] = dose_str.replace('mg/kg', '').strip() # We'll store the numeric part
    elif 'mg' in dose_str:
        new_row['dose_mg'] = dose_str.replace('mg', '').strip()
    else:
        new_row['dose_mg'] = dose_str
        
    df_new = pd.concat([df_new, pd.DataFrame([new_row])], ignore_index=True)

# Save aligned file
df_new.to_csv(output_path, index=False)
print(f"Saved {len(df_new)} aligned entries to {output_path}")
