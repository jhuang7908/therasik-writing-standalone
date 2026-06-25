import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '.')
from core.immunogenicity.ada_risk_scorer import ADAScorer

df = pd.read_csv('data/immunogenicity_panel_136_master.csv')
scorer = ADAScorer

scores = []
tiers = []
profile_disease = []
profile_route = []
profile_half_life = []
for _, row in df.iterrows:
    if pd.isna(row.get('vh_identity_842')) or pd.isna(row.get('immuno_n_high')):
        scores.append(np.nan)
        tiers.append('UNKNOWN')
        profile_disease.append(None)
        profile_route.append(None)
        profile_half_life.append(None)
        continue

    res = scorer.score(
        mhc_result={"summary": {"n_high": int(row.get('immuno_n_high', 0))},
                    "n_clusters": int(row.get('immuno_n_clusters', 0))},
        surf_result={"frac_exposed_vh": row.get('surf_frac_exposed_vh'),
                     "n_hydrophilic_patches": int(row.get('surf_n_patches', 0))},
        germline_identity_vh=row.get('vh_identity_842'),
        germline_identity_vl=row.get('vl_identity_842'),
        interface_n_pairs=row.get('interface_n_pairs'),
        instability_index=row.get('instability_index'),
        hydro_patch_max9=row.get('hydro_patch_max9'),
        origin=str(row.get('origin', 'engineered')),
        targets=row.get('targets'),
        fc_isotype=row.get('fc_isotype'),
        format_type=row.get('format_type'),
        modality=row.get('modality'),
    )
    scores.append(res['clinical_ada_score'])
    tiers.append(res['clinical_ada_risk'])
    profile_disease.append(res.get('profile', {}).get('disease_class'))
    profile_route.append(res.get('profile', {}).get('route'))
    profile_half_life.append(res.get('profile', {}).get('half_life_class'))

df['ada_v2_score'] = scores
df['ada_v2_risk'] = tiers
df['ada_profile_disease'] = profile_disease
df['ada_profile_route'] = profile_route
df['ada_profile_half_life'] = profile_half_life
df.to_csv('data/immunogenicity_panel_136_master.csv', index=False, encoding='utf-8')

# Generate Markdown Report
md_path = 'docs/ADA_V2_Prediction_Results.md'
with open(md_path, 'w', encoding='utf-8') as f:
    f.write('#  ADA  (V2 )\n\n')
    f.write('****: 136-Panel ( 131 )\n')
    f.write('****: ADA Scorer V2 ( + )\n\n')
    
    valid_df = df[df['ada_v2_risk'] != 'UNKNOWN'].copy
    valid_df = valid_df.sort_values('ada_v2_score', ascending=False)
    
    f.write('## 1. \n\n')
    f.write('|  |  |  ADA  |  ADA  |  ADA  |\n')
    f.write('| :--- | :--- | :--- | :--- | :--- |\n')
    for tier in ['HIGH', 'MEDIUM', 'LOW']:
        sub = valid_df[valid_df['ada_v2_risk'] == tier]
        if len(sub) > 0:
            f.write('| **{}** | {} | {:.1f}% | {:.1f}% | {:.1f}% - {:.1f}% |\n'.format(
                tier, len(sub), sub['ada_first_pct'].mean, sub['ada_first_pct'].median,
                sub['ada_first_pct'].min, sub['ada_first_pct'].max
            ))
            
    f.write('\n## 2.  (HIGH Risk) \n\n')
    f.write(' (Score ≥ 0.67)：\n\n')
    f.write('|  | V2  |  ADA% |  |  |\n')
    f.write('| :--- | :--- | :--- | :--- | :--- |\n')
    high_df = valid_df[valid_df['ada_v2_risk'] == 'HIGH']
    for _, r in high_df.iterrows:
        f.write('| {} | {:.3f} | {:.1f}% | {} | Tier {} |\n'.format(
            r['antibody_name'], r['ada_v2_score'], r['ada_first_pct'], r['origin'], r['evidence_tier']
        ))

    f.write('\n## 3.  (MEDIUM Risk) \n\n')
    f.write(' (0.64 ≤ Score < 0.67)：\n\n')
    f.write('|  | V2  |  ADA% |  |  |\n')
    f.write('| :--- | :--- | :--- | :--- | :--- |\n')
    med_df = valid_df[valid_df['ada_v2_risk'] == 'MEDIUM']
    for _, r in med_df.iterrows:
        f.write('| {} | {:.3f} | {:.1f}% | {} | Tier {} |\n'.format(
            r['antibody_name'], r['ada_v2_score'], r['ada_first_pct'], r['origin'], r['evidence_tier']
        ))

print("Prediction applied to 131 antibodies.")
print("HIGH risk count:", len(high_df))
print("MEDIUM risk count:", len(med_df))
print("LOW risk count:", len(valid_df) - len(high_df) - len(med_df))
print(f"Report saved to {md_path}")
