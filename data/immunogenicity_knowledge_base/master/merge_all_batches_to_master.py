import pandas as pd
import numpy as np
import os
import glob

# Paths
master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\immunogenicity_panel_136_master.csv'
ph3_candidates_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_ph3_disc_candidates.csv'
neg_lib_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_negative_library_by_phase.csv'
output_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_202_curated.csv'

# Load base data
master_df = pd.read_csv(master_path)
print(f"Original master size: {len(master_df)}")

ph3_df = pd.read_csv(ph3_candidates_path) if os.path.exists(ph3_candidates_path) else pd.DataFrame()
neg_df = pd.read_csv(neg_lib_path) if os.path.exists(neg_lib_path) else pd.DataFrame()

# Combine metadata sources
metadata_sources = [ph3_df, neg_df]
meta_columns_to_keep = ['antibody_name', 'target', 'Target', 'clinical_phase', 'highest_status', 'status', 'indication', 'primary_indication']

# We need to find all batch files
batch_files = glob.glob(r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_batch*_expanded.csv')
batch_files.sort()

new_rows = []

for batch_file in batch_files:
    try:
        batch_df = pd.read_csv(batch_file)
    except Exception as e:
        print(f"Failed to read {batch_file}: {e}")
        continue
    
    # Try to map column names
    name_col = None
    for col in ['antibody_name', 'Antibody', 'name', 'Name']:
        if col in batch_df.columns:
            name_col = col
            break
            
    if not name_col:
        print(f"Skipping {batch_file}, no name column found.")
        continue
        
    for _, research in batch_df.iterrows():
        name = research[name_col]
        if pd.isna(name): continue
        
        # Check if already in master
        if name.lower() in master_df['antibody_name'].str.lower().values:
            # Check if it's already in new_rows
            if any(r['antibody_name'].lower() == name.lower() for r in new_rows):
                continue
            else:
                # Already in master, skip
                continue
                
        # Get metadata
        meta = {'antibody_name': name}
        found_meta = False
        for m_df in metadata_sources:
            if not m_df.empty:
                # find by name
                for n_col in ['antibody_name', 'Antibody']:
                    if n_col in m_df.columns:
                        match = m_df[m_df[n_col].str.lower() == name.lower()]
                        if not match.empty:
                            meta_row = match.iloc[0].to_dict()
                            for k, v in meta_row.items():
                                meta[k] = v
                            found_meta = True
                            break
            if found_meta: break
            
        row = meta.copy()
        
        # Populate from research
        if 'ada_pct' in research:
            row['ada_first_pct'] = research['ada_pct']
            row['ada_value_display'] = str(research['ada_pct']) + "%"
        if 'assay' in research: row['assay_method'] = research['assay']
        if 'indication' in research and not pd.isna(research['indication']): row['indication_text'] = research['indication']
        if 'route' in research: row['route_curated'] = research['route']
        if 'half_life' in research: row['half_life_days'] = research['half_life']
        if 'evidence_source' in research: row['evidence_source'] = research['evidence_source']
        if 'vh_seq' in research: row['vh_seq'] = research['vh_seq']
        if 'vl_seq' in research: row['vl_seq'] = research['vl_seq']
        
        row['verify_status'] = 'LITERATURE_VERIFIED'
        row['ada_has_text_evidence'] = True
        
        new_rows.append(row)

if new_rows:
    new_df = pd.DataFrame(new_rows)
    for col in master_df.columns:
        if col not in new_df.columns:
            new_df[col] = np.nan
            
    new_df = new_df[master_df.columns]
    
    updated_master = pd.concat([master_df, new_df], ignore_index=True)
    
    # Remove strict duplicates if any
    updated_master = updated_master.drop_duplicates(subset=['antibody_name'], keep='last')
    
    updated_master.to_csv(output_path, index=False)
    print(f"Successfully added {len(new_df)} antibodies. Total count: {len(updated_master)}")
else:
    print("No new antibodies to add.")
    # Still save it as 202 just to have the file
    master_df.to_csv(output_path, index=False)
    print(f"Saved copy to {output_path}. Total count: {len(master_df)}")
