import pandas as pd
import json
import re

def parse_ada(val):
    if pd.isna(val): return None
    val = str(val)
    match = re.search(r'(\d+(\.\d+)?)%', val)
    if match: return float(match.group(1))
    match_range = re.search(r'(\d+)-(\d+)%', val)
    if match_range: return (float(match_range.group(1)) + float(match_range.group(2))) / 2
    if 'no treatment-emergent' in val.lower or '0%' in val: return 0.0
    return None

# Load P70
p70 = pd.read_csv(r'data/thera_sabdab/out/confirmed70_human_humanized_germline_ada.csv')
p70_names = set(p70['antibody_name'].str.lower)

# Load atlases
natural_df    = pd.read_csv(r'data/natural_380_atlas/master_table.csv')
engineered_df = pd.read_csv(r'data/engineered_459_atlas/master_table.csv')
full_atlas = pd.concat([natural_df, engineered_df]).drop_duplicates(subset=['antibody_id'])

with open(r'data/ADA_reliable_package/clinical_db/clinical_ada_db_index.json', 'r', encoding='utf-8') as f:
    ada_index = json.load(f)['index']
ada_map = {item['antibody_name'].lower: item for item in ada_index}

# All atlas columns that have actual data (skip 0-coverage columns)
# vernier_sasa_total = 0/384 -> skip; structure_errors/sequence_errors = 0/384 -> skip
ATLAS_ENRICH = [
    # sequences
    'vh_seq', 'vl_seq',
    # CDR/FR breakdown
    'vh_fr1','vh_cdr1','vh_fr2','vh_cdr2','vh_fr3','vh_cdr3','vh_fr4',
    'vl_fr1','vl_cdr1','vl_fr2','vl_cdr2','vl_fr3','vl_cdr3','vl_fr4',
    # germline identity (atlas column name)
    'vh_germline_identity', 'vl_germline_identity',
    # structure extended
    'pdb_path', 'interface_mean_dist_A', 'interface_min_dist_A',
    # CDR canonical classes
    'canonical_H1','canonical_H2','canonical_H3',
    'canonical_L1','canonical_L2','canonical_L3',
    # CMC numeric
    'pI','GRAVY','instability_index','net_charge_pH7',
    'hydro_patch_max9','charge_patch_max7','cmc_flags',
    # CMC chemical liability detail
    'agg_motifs','deamidation_sites','isomerization_sites',
    # Structure
    'vh_vl_angle_deg','interface_n_pairs',
    # MHC-II immunogenicity
    'immuno_tcia_score','immuno_risk_level',
    'immuno_n_high','immuno_n_medium','immuno_n_tolerated','immuno_n_clusters',
    # Treatment/Clinical
    'targets','fc_isotype','phase_bucket','format_type','modality','origin',
    'genetics_normalized',
]
ATLAS_ENRICH = [c for c in ATLAS_ENRICH if c in full_atlas.columns]

# Build lookup
atlas_lookup = {arow['antibody_id'].lower: arow for _, arow in full_atlas.iterrows}

# Identify 66 NEW
new_66_rows = []
overlap_names = []
for _, row in full_atlas.iterrows:
    name = str(row['antibody_id']).lower
    if name in ada_map:
        ada_num = parse_ada(ada_map[name]['ada_value_display'])
        if ada_num is not None:
            if name in p70_names:
                overlap_names.append(row['antibody_id'])
            else:
                new_66_rows.append(row)

print("P70={} | Overlap={} | New66={}".format(len(p70), len(overlap_names), len(new_66_rows)))

# Build 66 rows
rows_out = []
for row in new_66_rows:
    idx = ada_map[row['antibody_id'].lower]
    ada_num = parse_ada(idx['ada_value_display'])
    r = {
        'antibody_name':        row['antibody_id'],
        'thera_genetics_class': row['genetics_normalized'],
        'ada_value_display':    idx['ada_value_display'],
        'ada_first_pct':        ada_num,
        'vh_germline':          row['vh_germline'],
        'vl_germline':          row['vl_germline'],
        'vh_family':            str(row['vh_germline']).split('*')[0] if pd.notna(row['vh_germline']) else '',
        'vl_family':            str(row['vl_germline']).split('*')[0] if pd.notna(row['vl_germline']) else '',
        'vh_identity_842':      row['vh_germline_identity'],
        'vl_identity_842':      row['vl_germline_identity'],
        'vh_germline_imgt':     row['vh_germline'],
        'vl_germline_imgt':     row['vl_germline'],
        'vh_identity_imgt':     row['vh_germline_identity'],
        'vl_identity_imgt':     row['vl_germline_identity'],
        'evidence_tier':        idx['evidence_tier'],
        'evidence_source':      idx['source_type'],
        'citation_urls':        '; '.join(idx.get('citation_urls', [])),
        'panel_source':         'atlas_new_66',
    }
    for col in ATLAS_ENRICH:
        if col in row.index:
            r[col] = row[col]
    rows_out.append(r)

df_66 = pd.DataFrame(rows_out)

# Enrich P70
p70_out = p70.copy
p70_out['panel_source'] = 'confirmed_p70'
for col in ATLAS_ENRICH + ['evidence_tier','evidence_source','citation_urls']:
    if col not in p70_out.columns:
        p70_out[col] = None

for i, p70_row in p70_out.iterrows:
    pname = p70_row['antibody_name'].lower
    if pname in atlas_lookup:
        arow = atlas_lookup[pname]
        for col in ATLAS_ENRICH:
            if col in arow.index:
                p70_out.at[i, col] = arow[col]
    if pname in ada_map:
        ai = ada_map[pname]
        p70_out.at[i, 'evidence_tier']   = ai['evidence_tier']
        p70_out.at[i, 'evidence_source']  = ai['source_type']
        p70_out.at[i, 'citation_urls']    = '; '.join(ai.get('citation_urls', []))

# Merge
merged = pd.concat([p70_out, df_66], ignore_index=True, sort=False)
merged.to_csv('data/immunogenicity_panel_136_master.csv', index=False, encoding='utf-8')

n = len(merged)
print("\n=== 136-PANEL COMPLETE FIELD AUDIT (n={}) ===\n".format(n))

groups = {
    ' Sequences': ['vh_seq','vl_seq'],
    'CDR/FR ': ['vh_cdr1','vh_cdr2','vh_cdr3','vl_cdr1','vl_cdr2','vl_cdr3',
                    'vh_fr1','vh_fr2','vh_fr3','vl_fr1','vl_fr2','vl_fr3'],
    'CDR  Canonical': ['canonical_H1','canonical_H2','canonical_H3',
                             'canonical_L1','canonical_L2','canonical_L3'],
    'Germline': ['vh_germline','vl_germline','vh_identity_842','vl_identity_842',
                 'vh_germline_identity','vl_germline_identity'],
    ' Structure': ['pdb_path','vh_vl_angle_deg','interface_n_pairs',
                       'interface_mean_dist_A','interface_min_dist_A'],
    'SASA': ['vernier_sasa_total'],
    'CMC ': ['pI','GRAVY','instability_index','net_charge_pH7',
                 'hydro_patch_max9','charge_patch_max7'],
    'CMC ': ['agg_motifs','deamidation_sites','isomerization_sites','cmc_flags'],
    'MHC-II  (drb1_35)': ['immuno_tcia_score','immuno_risk_level',
                                    'immuno_n_high','immuno_n_medium',
                                    'immuno_n_tolerated','immuno_n_clusters'],
    ' ADA': ['ada_first_pct','ada_value_display','evidence_tier'],
    '//': ['targets','fc_isotype','phase_bucket','format_type','modality','origin'],
}

for grp, cols in groups.items:
    print('[{}]'.format(grp))
    for col in cols:
        if col in merged.columns:
            nn = merged[col].notna.sum
            status = 'FULL' if nn == n else ('PARTIAL' if nn > 0 else 'EMPTY')
            bar = '#' * int(nn/n*20)
            print('  {:35} {:3}/{} [{:20}] {}'.format(col, nn, n, bar, status))
        else:
            print('  {:35} NOT IN MASTER'.format(col))
    print

print("Note: vernier_sasa_total = 0/384 in atlas (SASA not computed for atlas batch)")
print("Note: Detailed per-cluster epitope data available only via fresh MHCII_Analyzer run")
print("Saved: data/immunogenicity_panel_136_master.csv")
