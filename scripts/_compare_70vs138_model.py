"""
_compare_70vs138_model.py
=========================
Quantitatively compare 70-antibody vs 138-antibody predictive correlation.

Strategy:
  1. Use sprint_matrix (n=70) as baseline with exact original feature encoding
  2. Map master CSV → same features for new 68 antibodies
  3. Merge → full 138-antibody feature matrix
  4. Run Spearman + LOO comparisons across 4 conditions:
       (A) p70-HU  vs  138-HU
       (B) p70-FH  vs  138-FH
  5. Print tables and summary

Run: python scripts/_compare_70vs138_model.py
"""
from __future__ import annotations
import csv, re, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import spearmanr
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
SPRINT = ROOT / "data/thera_sabdab/out/immuno70_sprint_matrix.csv"
MASTER = ROOT / "data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv"

# ── Immunosuppressant context encoding (from immunogenicity_sprint_model.py) ──
IMMUNO_SCORE = {
    "MTX in RA (>50% of patients)":      1.0,
    "MTX in RA common":                   0.9,
    "MTX in RA":                          0.8,
    "MTX combination common":             0.8,
    "chemo combination always":           0.9,
    "chemo combination often":            0.7,
    "chemo combination":                  0.6,
    "chemo combination sometimes":        0.4,
    "chemo setting":                      0.6,
    "transplant immunosuppressants":      0.9,
    "background SLE immunosuppressants":  0.5,
    "background IBD immunosuppressants":  0.4,
    "5-ASA/steroids/thiopurines in IBD":  0.4,
    "ICS background":                     0.2,
    "immunosuppressants in some aHUS":    0.4,
    "GM-CSF premedication":               0.0,
    "antibiotics":                        0.0,
    "none":                               0.0,
}
MTX_SCORE = {
    "high_proportion":      1.0,
    "moderate_proportion":  0.5,
    "none":                 0.0,
}
FC_SCORE = {
    "normal_IgG1":          1.0,
    "normal_IgG2":          0.7,
    "reduced_effector":     0.5,
    "stabilized_IgG4":      0.5,
    "enhanced_ADCC":        1.2,
    "no_effector":          0.0,
    "no_Fc_fragment":       0.0,
    "scFv_no_Fc":           0.0,
    "Fab_no_Fc":            0.0,
    "extended_half_life":   0.8,
    "modified_half_life":   0.7,
    "extended_recycling":   0.8,
    "modified":             0.6,
    "bispecific_effector":  0.8,
}

AA_AROMATIC = set('FYW')
AA_POLAR    = set('STNQ')

def cdrh3_arom(seq: str) -> float:
    s = seq.upper().strip()
    return sum(1 for c in s if c in AA_AROMATIC) / max(len(s), 1)

def cdrh3_polar(seq: str) -> float:
    s = seq.upper().strip()
    return sum(1 for c in s if c in AA_POLAR) / max(len(s), 1)

def parse_halflife(v) -> float:
    s = str(v).strip()
    nums = re.findall(r'[\d.]+', s)
    return float(nums[0]) if nums else float('nan')

def to_float(v) -> float:
    s = str(v).strip()
    if not s or s.lower() in ('nan','none',''):
        return float('nan')
    try:
        return float(s)
    except ValueError:
        return float('nan')

# ─────────────────────────────────────────────────────────────
# 1. Load sprint matrix (p70) — source of truth for 70 antibodies
# ─────────────────────────────────────────────────────────────
sp = pd.read_csv(SPRINT).drop_duplicates('antibody_name').copy()
sp['panel_source'] = 'confirmed_p70'
print(f"Sprint matrix: {len(sp)} rows")
print(f"  origin: {sp['origin'].value_counts().to_dict()}")

# ─────────────────────────────────────────────────────────────
# 2. Load master CSV — extract only new 68 antibodies
# ─────────────────────────────────────────────────────────────
master = pd.read_csv(MASTER).copy()
p70_names = set(sp['antibody_name'].str.lower())
new68 = master[~master['antibody_name'].str.lower().isin(p70_names)].copy()
print(f"Master: {len(master)} rows  |  New (non-p70): {len(new68)} rows")

# ─────────────────────────────────────────────────────────────
# 3. Build features for new 68 using same encoding as sprint model
# ─────────────────────────────────────────────────────────────
def build_features_new(r: pd.Series) -> dict:
    d = {}
    # ADA
    d['ada_rate_pct'] = to_float(r.get('ada_first_pct'))
    d['antibody_name'] = r['antibody_name']

    # Origin
    gen = str(r.get('genetics_normalized','')).strip().lower()
    d['origin'] = 'fully_human' if 'human' in gen and 'humanized' not in gen else 'humanized'
    d['panel_source'] = str(r.get('panel_source','')).strip()

    # Clinical confounders
    immuno_ctx = str(r.get('immunosuppressant_context','')).strip()
    mtx_raw    = str(r.get('mtx_comedication','')).strip()
    d['feat_immuno_suppression'] = IMMUNO_SCORE.get(immuno_ctx, 0.0)
    d['feat_mtx_suppression']   = MTX_SCORE.get(mtx_raw, 0.0)

    # If context is empty/missing → use a flag
    d['has_immuno_confounder'] = 1 if immuno_ctx and immuno_ctx.lower() not in ('nan','none','') else 0

    fc_eff = str(r.get('fc_effector_status','')).strip()
    d['feat_fc_tolerogenic'] = FC_SCORE.get(fc_eff, 0.7)

    d['feat_half_life'] = parse_halflife(r.get('half_life_days', ''))
    d['feat_assay_gen'] = to_float(r.get('assay_generation')) if to_float(r.get('assay_generation')) > 0 else 2.0

    # Immune-depleting
    d['feat_immune_depleting'] = to_float(r.get('immune_depleting')) if not math.isnan(to_float(r.get('immune_depleting',''))) else 0.0
    d['feat_checkpoint']       = to_float(r.get('checkpoint_inhibitor')) if not math.isnan(to_float(r.get('checkpoint_inhibitor',''))) else 0.0

    # Dosing (encode from dose_freq or route)
    # For the 68 new, use a conservative default if missing
    dose_freq = str(r.get('dose_freq', r.get('route_curated',''))).strip().lower()
    FREQ_SCORE = {
        'daily': 1.5, 'weekly': 1.2, 'biweekly': 1.0, 'q2w': 1.0,
        'monthly': 0.7, 'q3w': 0.75, 'q4w': 0.65, 'q8w': 0.5,
        'q12w': 0.3, 'q6m': 0.15, 'single': 0.1,
    }
    d['feat_dosing_freq'] = FREQ_SCORE.get(dose_freq, 0.6)

    # Sequence features
    cdrh3 = str(r.get('vh_cdr3','')).strip()
    d['feat_cdrh3_aromaticity'] = cdrh3_arom(cdrh3) if cdrh3 else float('nan')
    d['feat_cdrh3_polar']       = cdrh3_polar(cdrh3) if cdrh3 else float('nan')
    d['feat_cdrh3_len']         = len(cdrh3) if cdrh3 else float('nan')

    # VH germline identity
    d['feat_vh_identity']  = to_float(r.get('vh_germline_identity'))
    d['feat_vl_identity']  = to_float(r.get('vl_germline_identity'))

    # MHC-II epitope features
    d['feat_n_clusters']       = to_float(r.get('immuno_n_clusters'))
    d['feat_n_strong_binders'] = to_float(r.get('immuno_n_high'))
    n_high = to_float(r.get('immuno_n_high'))
    n_med  = to_float(r.get('immuno_n_medium'))
    d['feat_net_burden'] = (n_high + 0.5 * n_med) if not (math.isnan(n_high) or math.isnan(n_med)) else float('nan')

    # Surface features
    d['feat_surf_frac_vl'] = to_float(r.get('surf_frac_exposed_vl'))

    # CMC
    d['feat_cmc_pI']   = to_float(r.get('pI'))
    d['feat_cmc_gravy'] = to_float(r.get('GRAVY'))

    # V2 score (may be useful as composite)
    d['feat_v2_score'] = to_float(r.get('ada_v2_score'))

    return d

new68_feats = pd.DataFrame([build_features_new(r) for _, r in new68.iterrows()])
print(f"New-68 feature matrix: {new68_feats.shape}")

# ─────────────────────────────────────────────────────────────
# 4. Align sprint matrix columns to same feature names
# ─────────────────────────────────────────────────────────────
# Sprint has: feat_immuno_suppression, feat_cdrh3_aromaticity, feat_n_clusters, etc.
# We need to unify column names.

sp_aligned = pd.DataFrame()
sp_aligned['antibody_name']           = sp['antibody_name']
sp_aligned['ada_rate_pct']            = sp['ada_rate_pct']
sp_aligned['origin']                  = sp['origin']
sp_aligned['panel_source']            = sp['panel_source']
sp_aligned['has_immuno_confounder']   = 1  # p70 all have full confounder data

for feat in ['feat_immuno_suppression','feat_mtx_suppression','feat_fc_tolerogenic',
             'feat_half_life','feat_assay_gen','feat_immune_depleting','feat_dosing_freq',
             'feat_cdrh3_aromaticity','feat_cdrh3_polar','feat_cdrh3_len',
             'feat_vh_identity','feat_vl_identity',
             'feat_n_clusters','feat_n_strong_binders','feat_net_burden',
             'feat_surf_frac_vl','feat_cmc_pI','feat_cmc_gravy',
             'feat_checkpoint']:
    if feat in sp.columns:
        sp_aligned[feat] = sp[feat].values
    else:
        sp_aligned[feat] = float('nan')

# checkpoint from sprint matrix
if 'feat_checkpoint' not in sp.columns and 'checkpoint_inhibitor' in sp.columns:
    sp_aligned['feat_checkpoint'] = sp['checkpoint_inhibitor'].values

# v2 score not in sprint matrix
sp_aligned['feat_v2_score'] = float('nan')

# ─────────────────────────────────────────────────────────────
# 5. Merge into combined 138 matrix
# ─────────────────────────────────────────────────────────────
# Align new68_feats to same columns
for col in sp_aligned.columns:
    if col not in new68_feats.columns:
        new68_feats[col] = float('nan')

combined = pd.concat([sp_aligned, new68_feats[sp_aligned.columns]], ignore_index=True)
combined = combined[combined['ada_rate_pct'].notna()].copy()
print(f"\nCombined matrix: {len(combined)} rows with numeric ADA")
print(f"  HU: {(combined['origin']=='humanized').sum()}  FH: {(combined['origin']=='fully_human').sum()}")
print(f"  p70: {(combined['panel_source']=='confirmed_p70').sum()}  new: {(combined['panel_source']!='confirmed_p70').sum()}")

# ─────────────────────────────────────────────────────────────
# 6. Spearman correlation comparison
# ─────────────────────────────────────────────────────────────
def spear(x, y):
    pairs = [(xi,yi) for xi,yi in zip(x,y) if not (math.isnan(xi) or math.isnan(yi) or xi is None)]
    if len(pairs) < 5:
        return float('nan'), float('nan'), len(pairs)
    xs, ys = zip(*pairs)
    r, p = stats.spearmanr(xs, ys)
    return float(r), float(p), len(pairs)

def sig(p):
    if math.isnan(p): return ' '
    if p < 0.01: return '**'
    if p < 0.05: return '*'
    if p < 0.10: return '^'
    return ' '

subsets = {
    'HU_p70':  combined[(combined['origin']=='humanized')  & (combined['panel_source']=='confirmed_p70')],
    'HU_138':  combined[(combined['origin']=='humanized')],
    'FH_p70':  combined[(combined['origin']=='fully_human') & (combined['panel_source']=='confirmed_p70')],
    'FH_138':  combined[(combined['origin']=='fully_human')],
}
for k,v in subsets.items():
    print(f"  {k}: n={len(v)}")

FEATURES = [
    ('feat_immuno_suppression', 'Immunosuppressant context'),
    ('feat_mtx_suppression',    'MTX comedication'),
    ('feat_half_life',          'Half-life (days)'),
    ('feat_immune_depleting',   'Immune-depleting target'),
    ('feat_cdrh3_aromaticity',  'CDR-H3 aromaticity'),
    ('feat_n_clusters',         'MHC-II epitope clusters'),
    ('feat_net_burden',         'Net epitope burden'),
    ('feat_n_strong_binders',   'Strong MHC-II binders'),
    ('feat_surf_frac_vl',       'VL surface hydrophilic frac'),
    ('feat_vh_identity',        'VH germline identity'),
    ('feat_assay_gen',          'Assay generation'),
    ('feat_cmc_pI',             'pI (CMC)'),
    ('feat_v2_score',           'V2 composite score'),
]

print()
print("=" * 100)
print("SPEARMAN CORRELATIONS vs ADA RATE  (** p<0.01, * p<0.05, ^ p<0.10)")
print("=" * 100)
print(f"{'Feature':<30}  {'HU_p70(n=43)':>12}  {'HU_138(n=?)':>12}  {'Δr':>7}  |  {'FH_p70(n=27)':>12}  {'FH_138(n=?)':>12}  {'Δr':>7}")
print("-" * 100)

hu_p70 = subsets['HU_p70'];  hu_138 = subsets['HU_138']
fh_p70 = subsets['FH_p70'];  fh_138 = subsets['FH_138']

summary_rows = []
for fname, fdesc in FEATURES:
    def rs(ds):
        x = ds[fname].fillna(float('nan')).values.astype(float)
        y = ds['ada_rate_pct'].values.astype(float)
        return spear(x, y)

    r_hu_p70, p_hu_p70, n_hu_p70 = rs(hu_p70)
    r_hu_138, p_hu_138, n_hu_138 = rs(hu_138)
    r_fh_p70, p_fh_p70, n_fh_p70 = rs(fh_p70)
    r_fh_138, p_fh_138, n_fh_138 = rs(fh_138)

    def fmt(r, p, n):
        if math.isnan(r): return f"{'N/A':>9}"
        return f"{r:+.3f}{sig(p)}"

    d_hu = (r_hu_138 - r_hu_p70) if not (math.isnan(r_hu_138) or math.isnan(r_hu_p70)) else float('nan')
    d_fh = (r_fh_138 - r_fh_p70) if not (math.isnan(r_fh_138) or math.isnan(r_fh_p70)) else float('nan')

    print(f"  {fdesc:<28}  {fmt(r_hu_p70,p_hu_p70,n_hu_p70):>12}  {fmt(r_hu_138,p_hu_138,n_hu_138):>12}  {'+' if d_hu>=0 else ''}{d_hu:.3f}  |  {fmt(r_fh_p70,p_fh_p70,n_fh_p70):>12}  {fmt(r_fh_138,p_fh_138,n_fh_138):>12}  {'+' if d_fh>=0 else ''}{d_fh:.3f}")

    summary_rows.append({
        'feature': fdesc, 'fname': fname,
        'r_hu_p70': r_hu_p70, 'r_hu_138': r_hu_138, 'delta_hu': d_hu,
        'r_fh_p70': r_fh_p70, 'r_fh_138': r_fh_138, 'delta_fh': d_fh,
    })

print()
print(f"  HU n: p70={len(hu_p70)}, 138={len(hu_138)} (+{len(hu_138)-len(hu_p70)} new)")
print(f"  FH n: p70={len(fh_p70)}, 138={len(fh_138)} (+{len(fh_138)-len(fh_p70)} new)")

# ─────────────────────────────────────────────────────────────
# 7. LOO with RidgeCV (matches sprint_v3 approach)
# ─────────────────────────────────────────────────────────────
def loo_ridge_spearman(ds: pd.DataFrame, feat_cols: list[str]) -> tuple[float, float, int]:
    sub = ds[['ada_rate_pct'] + feat_cols].dropna()
    if len(sub) < 8:
        return float('nan'), float('nan'), len(sub)
    X = sub[feat_cols].values.astype(float)
    y = sub['ada_rate_pct'].values.astype(float)
    preds = np.zeros(len(y))
    for tr, te in LeaveOneOut().split(X):
        sc = StandardScaler()
        Xtr = sc.fit_transform(X[tr]); Xte = sc.transform(X[te])
        md = RidgeCV(alphas=[0.01,0.1,1,10,50,100,200]).fit(Xtr, y[tr])
        preds[te] = md.predict(Xte)
    r, p = spearmanr(y, preds)
    return float(r), float(p), len(sub)

print()
print("=" * 80)
print("LOO CROSS-VALIDATION (RidgeCV, same as sprint_v3)")
print("=" * 80)

LOO_MODELS = [
    ("HU-A (4f: immuno+arom+depl+hl)",
     hu_p70, hu_138,
     ['feat_immuno_suppression','feat_cdrh3_aromaticity','feat_immune_depleting','feat_half_life']),
    ("HU-seqclin (4f: immuno+n_clust+arom+hl)",
     hu_p70, hu_138,
     ['feat_immuno_suppression','feat_n_clusters','feat_cdrh3_aromaticity','feat_half_life']),
    ("HU-allclin (7f)",
     hu_p70, hu_138,
     ['feat_immuno_suppression','feat_mtx_suppression','feat_dosing_freq',
      'feat_fc_tolerogenic','feat_immune_depleting','feat_half_life','feat_assay_gen']),
    ("FH-A (3f: n_clust+net_bur+n_strong)",
     fh_p70, fh_138,
     ['feat_n_clusters','feat_net_burden','feat_n_strong_binders']),
    ("FH-seq (3f: n_clust+surf_vl+vh_id)",
     fh_p70, fh_138,
     ['feat_n_clusters','feat_surf_frac_vl','feat_vh_identity']),
    ("FH-mixed (4f: n_clust+net_bur+immuno+hl)",
     fh_p70, fh_138,
     ['feat_n_clusters','feat_net_burden','feat_immuno_suppression','feat_half_life']),
]

print(f"  {'Model':<40}  {'p70 LOO r':>10}  {'138 LOO r':>10}  {'n_p70':>6}  {'n_138':>6}  {'Δr':>7}")
print("  " + "-" * 90)

for label, ds_p70, ds_138, feats in LOO_MODELS:
    r_p70, p_p70, n_p70 = loo_ridge_spearman(ds_p70, feats)
    r_138, p_138, n_138 = loo_ridge_spearman(ds_138, feats)
    delta = (r_138 - r_p70) if not (math.isnan(r_138) or math.isnan(r_p70)) else float('nan')
    def fmtr(r, p):
        if math.isnan(r): return '   N/A  '
        return f"{r:+.3f}{sig(p)}"
    ds = f"{delta:+.3f}" if not math.isnan(delta) else '  N/A'
    print(f"  {label:<40}  {fmtr(r_p70,p_p70):>10}  {fmtr(r_138,p_138):>10}  {n_p70:>6}  {n_138:>6}  {ds:>7}")

# ─────────────────────────────────────────────────────────────
# 8. Effect of missing confounder data — direct test
# ─────────────────────────────────────────────────────────────
print()
print("=" * 80)
print("MISSING CONFOUNDER IMPACT ANALYSIS")
print("=" * 80)
print()
hu_138_full = hu_138.copy()
hu_138_full['immuno_is_zero'] = (hu_138_full['feat_immuno_suppression'] == 0).astype(int)

n_zero_p70  = (hu_p70['feat_immuno_suppression'] == 0).sum()
n_zero_138  = (hu_138_full['feat_immuno_suppression'] == 0).sum()
n_total_hu  = len(hu_138_full)
print(f"  HU antibodies with feat_immuno_suppression == 0.0:")
print(f"    In p70:  {n_zero_p70}/{len(hu_p70)} ({100*n_zero_p70//len(hu_p70)}%)")
print(f"    In 138:  {n_zero_138}/{n_total_hu} ({100*n_zero_138//n_total_hu}%)")
print(f"  → {n_zero_138-n_zero_p70} new HU antibodies added with no immunosuppressant data")

# Check what their true ADA rates look like
new_hu_zero = hu_138_full[
    (hu_138_full['panel_source'] != 'confirmed_p70') & 
    (hu_138_full['feat_immuno_suppression'] == 0)
]
print(f"\n  New HU antibodies (non-p70) with zero immunosuppressant score:")
print(f"    n={len(new_hu_zero)}, ADA mean={new_hu_zero['ada_rate_pct'].mean():.1f}%, "
      f"range={new_hu_zero['ada_rate_pct'].min():.1f}–{new_hu_zero['ada_rate_pct'].max():.1f}%")

# Among p70, correlation of immuno_sup with ADA
r_immuno_p70, p_immuno_p70 = spearmanr(
    hu_p70['feat_immuno_suppression'], hu_p70['ada_rate_pct']
)
r_immuno_138, p_immuno_138 = spearmanr(
    hu_138_full['feat_immuno_suppression'], hu_138_full['ada_rate_pct']
)
print(f"\n  feat_immuno_suppression vs ADA:")
print(f"    HU_p70 (n={len(hu_p70)}): r={r_immuno_p70:+.3f}{sig(p_immuno_p70)}  p={p_immuno_p70:.4f}")
print(f"    HU_138 (n={n_total_hu}): r={r_immuno_138:+.3f}{sig(p_immuno_138)}  p={p_immuno_138:.4f}")
print(f"    → Attenuation: Δr={r_immuno_138-r_immuno_p70:+.3f}")

# ─────────────────────────────────────────────────────────────
# 9. Summary table for report
# ─────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("SUMMARY: Key signal attenuation due to missing confounder data")
print("=" * 70)
clinical_feats = [r for r in summary_rows if r['fname'] in
    ('feat_immuno_suppression','feat_mtx_suppression','feat_half_life','feat_immune_depleting')]
seq_feats = [r for r in summary_rows if r['fname'] in
    ('feat_cdrh3_aromaticity','feat_n_clusters','feat_net_burden','feat_n_strong_binders','feat_surf_frac_vl')]
print("\nClinical confounder features (strongest attenuation expected in HU group):")
for r in clinical_feats:
    print(f"  {r['feature']:<35}  HU Δr={r['delta_hu']:+.3f}  FH Δr={r['delta_fh']:+.3f}")
print("\nSequence/structural features (should be more stable):")
for r in seq_feats:
    print(f"  {r['feature']:<35}  HU Δr={r['delta_hu']:+.3f}  FH Δr={r['delta_fh']:+.3f}")
print()
print("Done.")
