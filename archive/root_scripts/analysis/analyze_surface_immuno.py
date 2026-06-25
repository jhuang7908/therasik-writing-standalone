"""
Surface immunogenicity analysis for 136-panel.
Correlates SASA-based hydrophilic patch metrics with clinical ADA.
"""
import pandas as pd
import json
from scipy.stats import spearmanr

df = pd.read_csv('data/immunogenicity_panel_136_master.csv')
done = df[df['surf_mode'].notna()].copy()

print("=== SURFACE IMMUNOGENICITY RESULTS (n={}) ===\n".format(len(done)))

# Basic stats
print("[Surface Risk Distribution]")
print(done['surf_risk'].value_counts().to_string())

print("\n[Quantitative Stats]")
for col, label in [
    ('surf_n_patches',       'Hydrophilic patches (VH+VL)'),
    ('surf_frac_exposed_vh', 'Frac exposed residues VH'),
    ('surf_frac_exposed_vl', 'Frac exposed residues VL'),
    ('surf_mean_sasa_vh',    'Mean SASA VH (A^2)'),
    ('surf_mean_sasa_vl',    'Mean SASA VL (A^2)'),
]:
    s = done[col].dropna()
    print("  {:40} mean={:.2f} sd={:.2f} min={:.2f} max={:.2f}".format(
        label, s.mean(), s.std(), s.min(), s.max()))

# Correlation with ADA
print("\n[Spearman Correlation vs Clinical ADA]")
sub = done.dropna(subset=['ada_first_pct','surf_n_patches','surf_frac_exposed_vh',
                           'surf_frac_exposed_vl','surf_mean_sasa_vh','surf_mean_sasa_vl'])
print("Clean rows for correlation: {}".format(len(sub)))
for feat, label in [
    ('surf_n_patches',       'n_patches (VH+VL)'),
    ('surf_frac_exposed_vh', 'frac_exposed_vh'),
    ('surf_frac_exposed_vl', 'frac_exposed_vl'),
    ('surf_mean_sasa_vh',    'mean_sasa_vh'),
    ('surf_mean_sasa_vl',    'mean_sasa_vl'),
    # also vs MHC-II and germline for comparison
    ('vh_identity_842',      'VH germline identity'),
    ('immuno_tcia_score',    'TCIA score'),
    ('hydro_patch_max9',     'CMC hydro_patch_max9'),
]:
    if feat not in sub.columns:
        continue
    s2 = sub.dropna(subset=[feat])
    rho, pval = spearmanr(s2[feat], s2['ada_first_pct'])
    sig = '**' if pval < 0.05 else ('*' if pval < 0.1 else '')
    print("  {:30} rho={:+.3f}  p={:.4f}  n={} {}".format(label, rho, pval, len(s2), sig))

# By origin
print("\n[By Origin: natural vs engineered]")
for origin in ['natural', 'engineered']:
    grp = sub[sub['origin'] == origin]
    if len(grp) < 5:
        continue
    print("  {} (n={}):".format(origin, len(grp)))
    for feat, label in [('surf_n_patches','n_patches'),('surf_frac_exposed_vh','frac_exposed_vh')]:
        rho, pval = spearmanr(grp[feat], grp['ada_first_pct'])
        sig = '**' if pval < 0.05 else ('*' if pval < 0.1 else '')
        print("    {:25} rho={:+.3f} p={:.4f} {}".format(label, rho, pval, sig))

# Patch distribution
print("\n[n_patches Distribution]")
print(done['surf_n_patches'].value_counts().sort_index().to_string())

# Top 10 high-patch antibodies
print("\n[Top 10 highest n_patches antibodies]")
top = done.nlargest(10, 'surf_n_patches')[
    ['antibody_name','surf_n_patches','surf_frac_exposed_vh','surf_frac_exposed_vl','ada_first_pct','origin']
]
print(top.to_string(index=False))

# Patch sequence examples
print("\n[Sample VH patch sequences (n_patches >= 12, first 5)]")
big = done[done['surf_n_patches'] >= 12].head(5)
for _, r in big.iterrows():
    patches = json.loads(r['surf_patch_seqs_vh']) if pd.notna(r['surf_patch_seqs_vh']) else []
    print("  {} (ADA={:.1f}%) VH patches: {}".format(
        r['antibody_name'], r['ada_first_pct'] if pd.notna(r['ada_first_pct']) else 0,
        patches[:3]))
