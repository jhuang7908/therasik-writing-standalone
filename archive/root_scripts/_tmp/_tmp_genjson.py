import pandas as pd
import json
import numpy as np

df = pd.read_csv(r'data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv')

# Compute derived field: net MHC-II clusters (excluding tolerated)
df['mhcii_net_clusters'] = (
    df['immuno_n_high'].fillna(0) + df['immuno_n_medium'].fillna(0)
).round(0).astype(int)

# Hydrophilic surface fraction (average VH+VL)
df['surf_hydrophilic_avg'] = (
    (df['surf_frac_exposed_vh'].fillna(np.nan) + df['surf_frac_exposed_vl'].fillna(np.nan)) / 2
).round(4)

# Select and rename fields for the web DB
FIELDS = {
    'antibody_name': 'name',
    'origin': 'origin',
    'thera_genetics_class': 'genetics',
    'targets': 'targets',
    'indication_text': 'indication',
    'disease_class_curated': 'disease_class',
    'ada_first_pct': 'ada_pct',
    'ada_value_display': 'ada_display',
    'evidence_tier': 'tier',
    'fc_isotype': 'fc_isotype',
    'fc_engineering': 'fc_engineering',
    'fc_effector_status': 'fc_effector',
    'route_curated': 'route',
    'dose_mg': 'dose_mg',
    'half_life_days': 'half_life',
    'assay_generation': 'assay_gen',
    'assay_platform': 'assay_platform',
    'mtx_comedication': 'mtx',
    'approval_year': 'approval_year',
    # Molecular: immunogenicity
    'immuno_tcia_score': 'tcia_score',
    'immuno_risk_level': 'tcia_risk',
    'immuno_n_clusters': 'mhcii_clusters_total',
    'mhcii_net_clusters': 'mhcii_net_clusters',
    'immuno_n_high': 'mhcii_n_high',
    'immuno_n_medium': 'mhcii_n_medium',
    'immuno_n_tolerated': 'mhcii_n_tolerated',
    # Molecular: surface
    'surf_hydrophilic_avg': 'hydrophilic_frac',
    'surf_frac_exposed_vh': 'hydrophilic_vh',
    'surf_frac_exposed_vl': 'hydrophilic_vl',
    'surf_n_patches': 'surf_patches',
    'surf_risk': 'surf_risk',
    # CMC
    'pI': 'pI',
    'GRAVY': 'gravy',
    'instability_index': 'instability',
    'net_charge_pH7': 'net_charge',
    'hydro_patch_max9': 'hydro_patch',
    # Germline
    'vh_germline_identity': 'vh_identity',
    'vl_germline_identity': 'vl_identity',
    'vh_germline': 'vh_germline',
    'vl_germline': 'vl_germline',
    # V2 score
    'ada_v2_score': 'v2_score',
    'ada_v2_risk': 'v2_risk',
    # Sequence
    'vh_cdr3': 'cdr_h3',
    # Evidence
    'ada_evidence_chain_excerpt': 'evidence_text',
    'citation_urls': 'citation_url',
    'ada_source_pmids': 'pmids',
    'format_type': 'format_type',
}

sub = df[list(FIELDS.keys())].copy()
sub.columns = list(FIELDS.values())

# Clean NaN -> null for JSON
records = []
for _, row in sub.iterrows():
    rec = {}
    for col in sub.columns:
        v = row[col]
        if pd.isna(v):
            rec[col] = None
        elif isinstance(v, float) and v == int(v):
            rec[col] = int(v)
        elif isinstance(v, (np.integer,)):
            rec[col] = int(v)
        elif isinstance(v, (np.floating,)):
            rec[col] = round(float(v), 4)
        else:
            rec[col] = v
    records.append(rec)

out = json.dumps(records, ensure_ascii=False, indent=None)
with open(r'docs/ada_db_data.json', 'w', encoding='utf-8') as f:
    f.write(out)

print(f'Written {len(records)} records, {len(out)//1024} KB')
print('Sample keys:', list(records[0].keys())[:10])
