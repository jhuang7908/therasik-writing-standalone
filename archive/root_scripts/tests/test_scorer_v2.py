"""Quick smoke test for ADA Scorer V2."""
import sys
sys.path.insert(0, '.')
from core.immunogenicity.ada_risk_scorer import ADAScorer

scorer = ADAScorer()
print(scorer.params_summary())

# Test: high-risk case (low identity, buried, many epitopes)
res_high = scorer.score(
    mhc_result={"summary": {"n_high": 35}, "n_clusters": 4},
    surf_result={"frac_exposed_vh": 0.61, "n_hydrophilic_patches": 12},
    germline_identity_vh=0.85,
    germline_identity_vl=0.88,
    interface_n_pairs=55,
    instability_index=48,
    hydro_patch_max9=0.72,
    origin="engineered",
)
print("\nHigh-risk test:")
print("  score={:.3f} tier={}".format(res_high['clinical_ada_score'], res_high['clinical_ada_risk']))
for k, v in res_high['components'].items():
    print("    {:20} = {:.4f}".format(k, v))

# Test: low-risk case (high identity, exposed, few epitopes)
res_low = scorer.score(
    mhc_result={"summary": {"n_high": 5}, "n_clusters": 1},
    surf_result={"frac_exposed_vh": 0.68, "n_hydrophilic_patches": 7},
    germline_identity_vh=0.96,
    germline_identity_vl=0.97,
    interface_n_pairs=30,
    origin="natural",
)
print("\nLow-risk test:")
print("  score={:.3f} tier={}".format(res_low['clinical_ada_score'], res_low['clinical_ada_risk']))

# Test: no structural data (fallback)
res_seq = scorer.score(
    mhc_result={"summary": {"n_high": 20}, "n_clusters": 3},
    surf_result={"n_hydrophilic_patches": 10},
    germline_identity_vh=0.92,
)
print("\nSeq-only test:")
print("  score={:.3f} tier={}".format(res_seq['clinical_ada_score'], res_seq['clinical_ada_risk']))

# Validate on CLEAN-124 panel
import pandas as pd
import numpy as np
from scipy.stats import spearmanr

df = pd.read_csv('data/immunogenicity_panel_136_master.csv')
panel = df[df['evidence_tier'].isin(['A','B']) & df['ada_first_pct'].notna()].copy()
panel = panel.dropna(subset=['vh_identity_842','surf_frac_exposed_vh','immuno_n_high'])

scores = []
for _, row in panel.iterrows():
    r = scorer.score(
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
    )
    scores.append(r['clinical_ada_score'])

s = np.array(scores)
y = panel['ada_first_pct'].values
rho, pval = spearmanr(s, y)
print("\nCLEAN-124 validation: Spearman rho={:+.4f} p={:.4f} (n={})".format(rho, pval, len(s)))
