import pandas as pd
import numpy as np

candidates_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_batch9_and_10_candidates.csv'
idc_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\idc_v1_mock.csv'
master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_202_curated.csv'
output_master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_245_curated.csv'

# Load candidates
candidates_df = pd.read_csv(candidates_path)

# Load IDC
idc_df = pd.read_csv(idc_path)
idc_df['Therapeutic_lower'] = idc_df['Therapeutic'].str.lower()

# Map ADA data
mapped_count = 0
for idx, row in candidates_df.iterrows():
    name = str(row['antibody_name']).lower()
    match = idc_df[idc_df['Therapeutic_lower'] == name]
    if not match.empty:
        ada_val = match.iloc[0]['IDC_ADA_Incidence']
        candidates_df.at[idx, 'ada_pct'] = ada_val
        candidates_df.at[idx, 'evidence_source'] = 'IDC_Database'
        candidates_df.at[idx, 'assay'] = 'IDC_Curated'
        mapped_count += 1

candidates_df.to_csv(candidates_path, index=False)
print(f"Mapped {mapped_count} out of {len(candidates_df)} candidates using IDC database.")

# Now merge those mapped candidates into master
master_df = pd.read_csv(master_path)
new_rows = []

for idx, row in candidates_df.iterrows():
    if pd.notna(row['ada_pct']) and str(row['ada_pct']).strip() != '':
        new_row = {
            'antibody_name': row['antibody_name'],
            'discovery_source': row['discovery_source'],
            'target': row['target'],
            'clinical_phase': row['clinical_phase'],
            'indication_text': row['indication'],
            'ada_first_pct': row['ada_pct'],
            'ada_value_display': str(row['ada_pct']) + "%",
            'evidence_source': row['evidence_source'],
            'assay_method': row['assay'],
            'verify_status': 'IDC_MAPPED',
            'ada_has_text_evidence': True
        }
        new_rows.append(new_row)

if new_rows:
    new_df = pd.DataFrame(new_rows)
    # Ensure columns match master
    for col in master_df.columns:
        if col not in new_df.columns:
            new_df[col] = np.nan
    new_df = new_df[master_df.columns]
    
    updated_master = pd.concat([master_df, new_df], ignore_index=True)
    # Keep up to 245
    if len(updated_master) > 245:
        updated_master = updated_master.head(245)
    
    updated_master.to_csv(output_master_path, index=False)
    print(f"Merged {len(new_rows)} into master. Final master size: {len(updated_master)} at {output_master_path}")
else:
    print("No valid mapped candidates to merge.")
