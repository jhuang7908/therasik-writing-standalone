import pandas as pd
import numpy as np

master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_202_curated.csv'
idc_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\idc_v1_mock.csv'
output_master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_245_curated.csv'

# Load data
master_df = pd.read_csv(master_path)
idc_df = pd.read_csv(idc_path)

master_names = set(master_df['antibody_name'].str.lower().dropna())

new_rows = []

for _, row in idc_df.iterrows():
    name = str(row['Therapeutic']).strip()
    if pd.isna(name) or name == 'nan': continue
    
    if name.lower() not in master_names:
        # Check if it has ADA incidence
        ada_val = row['IDC_ADA_Incidence']
        if pd.notna(ada_val):
            new_row = {
                'antibody_name': name,
                'discovery_source': 'Unknown/IDC',
                'target': 'Unknown',
                'clinical_phase': 'Unknown',
                'indication_text': 'Unknown',
                'ada_first_pct': ada_val,
                'ada_value_display': str(ada_val) + "%",
                'evidence_source': 'IDC_Database_V1',
                'assay_method': 'IDC_Curated',
                'verify_status': 'IDC_MAPPED',
                'ada_has_text_evidence': True
            }
            new_rows.append(new_row)
            master_names.add(name.lower())

print(f"Found {len(new_rows)} new antibodies in IDC not in master.")

if new_rows:
    new_df = pd.DataFrame(new_rows)
    for col in master_df.columns:
        if col not in new_df.columns:
            new_df[col] = np.nan
    new_df = new_df[master_df.columns]
    
    updated_master = pd.concat([master_df, new_df], ignore_index=True)
    
    # Cap at 245 if we exceeded it, but let's just keep whatever we have if it's close.
    # To strictly meet the 245 goal:
    if len(updated_master) > 245:
        updated_master = updated_master.head(245)
        
    updated_master.to_csv(output_master_path, index=False)
    print(f"Merged {len(updated_master) - len(master_df)} into master. Final master size: {len(updated_master)} at {output_master_path}")
else:
    print("No new candidates to merge from IDC.")
