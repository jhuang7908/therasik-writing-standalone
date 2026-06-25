import pandas as pd
import os
import json

# Data from browser research
batch3_data = [
    {"name": "Briakinumab", "ada_pct": 1.2, "n_ada": 0.1, "assay": "ELISA", "indication": "Psoriasis", "dose": "200mg", "freq": "q12w", "route": "SC", "targets": "IL-12/23", "status": "HU"}, # Discontinued
    {"name": "Bermekimab", "ada_pct": 0.0, "n_ada": 0.0, "assay": "ELISA", "indication": "Hidradenitis Suppurativa", "dose": "400mg", "freq": "weekly", "route": "SC", "targets": "IL-1alpha", "status": "CA"},
    {"name": "Batoclimab", "ada_pct": 0.0, "n_ada": 0.0, "assay": "Bridging ELISA", "indication": "gMG", "dose": "340mg", "freq": "weekly", "route": "SC", "targets": "FcRn", "status": "CA"},
    {"name": "Satralizumab", "ada_pct": 71.0, "n_ada": 39.0, "assay": "ECLIA", "indication": "NMOSD", "dose": "120mg", "freq": "q4w", "route": "SC", "targets": "IL-6R", "status": "CA"},
    {"name": "Inebilizumab", "ada_pct": 5.6, "n_ada": 0.0, "assay": "ELISA", "indication": "NMOSD", "dose": "300mg", "freq": "q6m", "route": "IV", "targets": "CD19", "status": "CA"},
    {"name": "Margetuximab", "ada_pct": 2.0, "n_ada": 0.0, "assay": "ECLIA (MSD)", "indication": "Breast Cancer", "dose": "15mg/kg", "freq": "q3w", "route": "IV", "targets": "HER2", "status": "CA"},
    {"name": "Tafasitamab", "ada_pct": 0.0, "n_ada": 0.0, "assay": "ECLIA (MSD)", "indication": "DLBCL", "dose": "12mg/kg", "freq": "weekly", "route": "IV", "targets": "CD19", "status": "CA"},
    {"name": "Monalizumab", "ada_pct": 0.4, "n_ada": 0.0, "assay": "ELISA", "indication": "SCCHN/NSCLC", "dose": "10mg/kg", "freq": "q2w", "route": "IV", "targets": "NKG2A", "status": "CA"},
    {"name": "Tiragolumab", "ada_pct": 1.9, "n_ada": 0.0, "assay": "ECLIA (MSD)", "indication": "NSCLC", "dose": "600mg", "freq": "q3w", "route": "IV", "targets": "TIGIT", "status": "CA"},
    {"name": "Farletuzumab", "ada_pct": 0.0, "n_ada": 0.0, "assay": "ELISA", "indication": "Ovarian Cancer", "dose": "1.25mg/kg", "freq": "weekly", "route": "IV", "targets": "FR-alpha", "status": "LN"} # Failed phase 3 efficacy
]

base_dir = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data'
atlas_dirs = [d for d in os.listdir(base_dir) if d.endswith('_atlas') and os.path.isdir(os.path.join(base_dir, d))]

# Find sequences across all atlas files (but we won't analyze them structurally)
all_atlas_data = {}
for d in atlas_dirs:
    path = os.path.join(base_dir, d, 'master_table.csv')
    if os.path.exists(path):
        try:
            df_atlas = pd.read_csv(path)
            cols = df_atlas.columns.tolist()
            name_col = cols[0]
            for _, row in df_atlas.iterrows():
                name = str(row[name_col]).strip().lower()
                if name not in all_atlas_data:
                    all_atlas_data[name] = row.to_dict()
        except: pass

# Special case for clinical_kb
json_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\clinical_kb\Antibody_Atlas_1142_Aggregated.json'
if os.path.exists(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for entry in data:
            name = entry.get('name', '').strip().lower()
            if name not in all_atlas_data:
                all_atlas_data[name] = entry

# Combine with researched data
final_batch3 = []
for item in batch3_data:
    name_lower = item['name'].lower()
    atlas_entry = all_atlas_data.get(name_lower, {})
    
    entry = item.copy()
    entry['vh_seq'] = atlas_entry.get('vh_seq', atlas_entry.get('arm1_heavy', ''))
    entry['vl_seq'] = atlas_entry.get('vl_seq', atlas_entry.get('arm1_light', ''))
    entry['vh_germline'] = atlas_entry.get('vh_germline', '')
    entry['vl_germline'] = atlas_entry.get('vl_germline', '')
    
    # Structural fields (if they exist, but no new analysis)
    struct_cols = ['vh_fr1', 'vh_cdr1', 'vh_fr2', 'vh_cdr2', 'vh_fr3', 'vh_cdr3', 'vh_fr4', 
                   'vl_fr1', 'vl_cdr1', 'vl_fr2', 'vl_cdr2', 'vl_fr3', 'vl_cdr3', 'vl_fr4']
    for col in struct_cols:
        entry[col] = atlas_entry.get(col, '')
        
    final_batch3.append(entry)

df_batch3 = pd.DataFrame(final_batch3)
output_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_batch3_expanded.csv'
df_batch3.to_csv(output_path, index=False)
print(f"Saved {len(df_batch3)} entries to {output_path}")
