
import pandas as pd
import numpy as np
import os

# Paths
master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv'
batch6_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_batch6_expanded.csv'
ph3_candidates_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_ph3_disc_candidates.csv'
output_path = master_path # Overwrite master

# Load data
master_df = pd.read_csv(master_path)
batch6_df = pd.read_csv(batch6_path)
ph3_df = pd.read_csv(ph3_candidates_path)

# Extract selected candidates from ph3_df for metadata
selected_names = batch6_df['antibody_name'].tolist()
metadata_df = ph3_df[ph3_df['antibody_name'].isin(selected_names)].copy()

# Create a mapping for batch6 data
batch6_map = batch6_df.set_index('antibody_name').to_dict('index')

# Initialize new rows for master
new_rows = []

for name in selected_names:
    if name.lower() in master_df['antibody_name'].str.lower().values:
        print(f"Skipping {name}, already in master.")
        continue
    
    # Get metadata from ph3_df
    try:
        meta = metadata_df[metadata_df['antibody_name'] == name].iloc[0].to_dict()
    except IndexError:
        print(f"Error: Metadata for {name} not found in ph3_df. Using defaults.")
        meta = {'antibody_name': name}
    
    # Get research data from batch6_df
    research = batch6_map[name]
    
    # Merge and align
    row = meta.copy()
    
    # Overwrite/Fill specific fields
    row['ada_first_pct'] = research['ada_pct']
    row['ada_value_display'] = str(research['ada_pct']) + "%"
    row['assay_method'] = research['assay']
    row['indication_text'] = research['indication']
    row['route_curated'] = research['route']
    row['half_life_days'] = research['half_life']
    row['evidence_source'] = research['evidence_source']
    row['verify_status'] = 'LITERATURE_VERIFIED'
    row['ada_source_type_curated'] = 'discontinued_literature'
    row['ada_has_text_evidence'] = True
    
    # Ensure VH/VL are correct
    row['vh_seq'] = research['vh_seq']
    row['vl_seq'] = research['vl_seq']
    
    # Append to new rows
    new_rows.append(row)

if new_rows:
    new_df = pd.DataFrame(new_rows)
    # Ensure columns match master
    for col in master_df.columns:
        if col not in new_df.columns:
            new_df[col] = np.nan
    
    # Reorder columns to match master
    new_df = new_df[master_df.columns]
    
    # Concat
    updated_master = pd.concat([master_df, new_df], ignore_index=True)
    
    # Save
    updated_master.to_csv(output_path, index=False)
    print(f"Successfully added {len(new_rows)} antibodies to master. Total count: {len(updated_master)}")
else:
    print("No new antibodies added.")
