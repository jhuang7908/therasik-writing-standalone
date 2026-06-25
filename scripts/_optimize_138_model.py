"""
_optimize_138_model.py
======================
Systematic model optimization for the 138-antibody panel.

Strategy:
 1. Expand feature space (55+ features including interactions)
 2. Stratified (HU / FH) + whole-panel modeling
 3. RidgeCV, GBR, exhaustive k-feature LOO search (k=2..6)
 4. log(ADA) transform
 5. Report best models and compare to 70-panel baseline

Run: python scripts/_optimize_138_model.py
"""
from __future__ import annotations
import csv, re, math, sys, itertools
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parents[1]
SPRINT = ROOT / "data/thera_sabdab/out/immuno70_sprint_matrix.csv"
MASTER = ROOT / "data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv"

# ═══════════════════════════════════════════════════════════════
# Feature encoding functions
# ═══════════════════════════════════════════════════════════════
IMMUNO_SCORE = {
    "MTX in RA (>50% of patients)": 1.0, "MTX in RA common": 0.9,
    "MTX in RA": 0.8, "MTX combination common": 0.8,
    "chemo combination always": 0.9, "chemo combination often": 0.7,
    "chemo combination": 0.6, "chemo combination sometimes": 0.4,
    "chemo setting": 0.6, "transplant immunosuppressants": 0.9,
    "background SLE immunosuppressants": 0.5, "background IBD immunosuppressants": 0.4,
    "5-ASA/steroids/thiopurines in IBD": 0.4, "ICS background": 0.2,
    "immunosuppressants in some aHUS": 0.4, "GM-CSF premedication": 0.0,
    "antibiotics": 0.0, "none": 0.0,
}
MTX_SCORE = {"high_proportion": 1.0, "moderate_proportion": 0.5, "none": 0.0}
FC_SCORE = {
    "normal_IgG1": 1.0, "normal_IgG2": 0.7, "reduced_effector": 0.5,
    "stabilized_IgG4": 0.5, "enhanced_ADCC": 1.2, "no_effector": 0.0,
    "no_Fc_fragment": 0.0, "scFv_no_Fc": 0.0, "Fab_no_Fc": 0.0,
    "extended_half_life": 0.8, "modified_half_life": 0.7,
    "extended_recycling": 0.8, "modified": 0.6, "bispecific_effector": 0.8,
}
FREQ_SCORE = {
    'daily': 1.5, 'weekly': 1.2, 'biweekly': 1.0, 'q2w': 1.0,
    'monthly': 0.7, 'q3w': 0.75, 'q4w': 0.65, 'q4-8w': 0.55,
    'q8w (after loading)': 0.5, 'q8w': 0.5, 'q8-12w': 0.4,
    'q12w': 0.3, 'q3m': 0.3, 'monthly or q3m': 0.5,
    'weekly to q4w': 0.9, 'q3w then q6w': 0.6, 'q6m': 0.15,
    '5-day course yearly': 0.2, 'single dose': 0.1, 'single': 0.1,
    'cycle-based': 0.7, 'd1/8 q21d': 0.8, 'd1/8/15 q28d': 0.85,
    'q2-3w': 0.9, 'q2-4w': 0.9,
}
ROUTE_SCORE = {'SC': 1.0, 'IV infusion': 0.3, 'IV': 0.3, 'IM': 0.7,
               'intravitreal': 0.1, 'topical': 0.1}

AA_AROMATIC = set('FYW')
AA_HYDROPHOBIC = set('VILMACFYW')
AA_POLAR = set('STNQ')
AA_POS = set('KRH')
AA_NEG = set('DE')

def aa_frac(seq, aa_set):
    s = seq.upper().strip()
    return sum(1 for c in s if c in aa_set) / max(len(s), 1)

def to_float(v) -> float:
    s = str(v).strip()
    if not s or s.lower() in ('nan', 'none', ''):
        return float('nan')
    try:
        return float(s)
    except ValueError:
        return float('nan')

def parse_halflife(v) -> float:
    s = str(v).strip()
    nums = re.findall(r'[\d.]+', s)
    return float(nums[0]) if nums else float('nan')

def parse_dose_mg(v) -> float:
    s = str(v).strip().lower()
    nums = re.findall(r'[\d.]+', s)
    if not nums:
        return float('nan')
    val = float(nums[0])
    if 'mg/kg' in s:
        val *= 70
    return val


# ═══════════════════════════════════════════════════════════════
# Build combined feature matrix: p70 from sprint + new68 from master
# ═══════════════════════════════════════════════════════════════
sp = pd.read_csv(SPRINT).drop_duplicates('antibody_name').copy()
master = pd.read_csv(MASTER).copy()
p70_names = set(sp['antibody_name'].str.lower())
new68 = master[~master['antibody_name'].str.lower().isin(p70_names)].copy()

sys.stdout.reconfigure(line_buffering=True)
print(f"Loading: p70={len(sp)}, new68={len(new68)}, master={len(master)}")

def build_from_sprint(sp: pd.DataFrame) -> pd.DataFrame:
    """Extract + derive expanded features from the sprint matrix."""
    df = pd.DataFrame()
    df['antibody_name'] = sp['antibody_name']
    df['ada'] = sp['ada_rate_pct']
    df['origin'] = sp['origin']
    df['source'] = 'p70'

    # Direct features
    direct = [
        'feat_immuno_suppression','feat_mtx_suppression','feat_fc_tolerogenic',
        'feat_half_life','feat_assay_gen','feat_immune_depleting','feat_dosing_freq',
        'feat_checkpoint','feat_cdrh3_aromaticity','feat_cdrh3_polar','feat_cdrh3_len',
        'feat_cdrh3_charge','feat_cdrh3_risk',
        'feat_vh_identity','feat_vl_identity','feat_vh_family_score',
        'feat_n_clusters','feat_n_strong_binders','feat_net_burden',
        'feat_effective_burden','feat_surf_frac_vl','feat_surf_n_patches',
        'feat_cmc_pI','feat_cmc_gravy','feat_cmc_agg','feat_cmc_instability',
        'feat_cmc_net_charge','feat_cmc_hydro_patch',
        'feat_cdr_deamidation','feat_cdr_isomerization','feat_cdr_oxidation',
        'feat_cdr_hydrophobicity','feat_total_cdr_length',
        'feat_agg_risk','feat_route_sc','feat_format',
        'feat_target_bio','feat_anti_tnf','feat_approval_era',
        'feat_vz_foreignness','feat_origin_code',
        'feat_fc_x_format','feat_fc_glycan',
    ]
    for f in direct:
        df[f] = sp[f].values if f in sp.columns else float('nan')

    return df


def build_from_master(new: pd.DataFrame) -> pd.DataFrame:
    """Build same feature set from the master CSV for new antibodies."""
    rows = []
    for _, r in new.iterrows():
        d = {}
        d['antibody_name'] = r['antibody_name']
        d['ada'] = to_float(r.get('ada_first_pct'))

        gen = str(r.get('genetics_normalized', '')).strip().lower()
        # Only genetically_human is fully human; British "humanised" must not match "human" alone
        d['origin'] = 'fully_human' if gen == 'genetically_human' else 'humanized'
        d['source'] = 'new68'

        # Clinical confounders
        immuno_ctx = str(r.get('immunosuppressant_context', '')).strip()
        mtx_raw = str(r.get('mtx_comedication', '')).strip()
        d['feat_immuno_suppression'] = IMMUNO_SCORE.get(immuno_ctx, 0.0)
        d['feat_mtx_suppression'] = MTX_SCORE.get(mtx_raw, 0.0)

        fc_eff = str(r.get('fc_effector_status', '')).strip()
        d['feat_fc_tolerogenic'] = FC_SCORE.get(fc_eff, 0.7)

        d['feat_half_life'] = parse_halflife(r.get('half_life_days', ''))
        ag = to_float(r.get('assay_generation'))
        d['feat_assay_gen'] = ag if not math.isnan(ag) else 2.0

        immune_depl = to_float(r.get('immune_depleting'))
        d['feat_immune_depleting'] = immune_depl if not math.isnan(immune_depl) else 0.0

        checkpoint = to_float(r.get('checkpoint_inhibitor'))
        d['feat_checkpoint'] = checkpoint if not math.isnan(checkpoint) else 0.0

        dose_freq = str(r.get('dose_freq', '')).strip().lower()
        d['feat_dosing_freq'] = FREQ_SCORE.get(dose_freq, 0.6)

        route = str(r.get('route_curated', '')).strip()
        d['feat_route_sc'] = 1.0 if route.upper() == 'SC' else 0.0

        # Sequence features
        cdrh3 = str(r.get('vh_cdr3', '')).strip()
        if cdrh3 and cdrh3.lower() not in ('nan', 'none', ''):
            d['feat_cdrh3_aromaticity'] = aa_frac(cdrh3, AA_AROMATIC)
            d['feat_cdrh3_polar'] = aa_frac(cdrh3, AA_POLAR)
            d['feat_cdrh3_len'] = float(len(cdrh3))
            d['feat_cdr_hydrophobicity'] = aa_frac(cdrh3, AA_HYDROPHOBIC)
            pos = sum(1 for c in cdrh3.upper() if c in AA_POS)
            neg = sum(1 for c in cdrh3.upper() if c in AA_NEG)
            d['feat_cdrh3_charge'] = float(pos - neg)
        else:
            for f in ['feat_cdrh3_aromaticity','feat_cdrh3_polar','feat_cdrh3_len',
                       'feat_cdr_hydrophobicity','feat_cdrh3_charge']:
                d[f] = float('nan')

        # Germline
        d['feat_vh_identity'] = to_float(r.get('vh_germline_identity'))
        d['feat_vl_identity'] = to_float(r.get('vl_germline_identity'))

        # VH family scoring
        vh_fam = str(r.get('vh_family', '')).strip()
        fam_scores = {'IGHV1': 0.3, 'IGHV3': 0.0, 'IGHV4': 0.2, 'IGHV5': 0.5}
        d['feat_vh_family_score'] = fam_scores.get(vh_fam.split('-')[0] if vh_fam else '', 0.1)

        # MHC-II
        d['feat_n_clusters'] = to_float(r.get('immuno_n_clusters'))
        n_high = to_float(r.get('immuno_n_high'))
        n_med = to_float(r.get('immuno_n_medium'))
        d['feat_n_strong_binders'] = n_high
        d['feat_net_burden'] = (n_high + 0.5 * n_med) if not (math.isnan(n_high) or math.isnan(n_med)) else float('nan')

        # Surface
        d['feat_surf_frac_vl'] = to_float(r.get('surf_frac_exposed_vl'))
        d['feat_surf_n_patches'] = float('nan')  # not available for new

        # CMC
        d['feat_cmc_pI'] = to_float(r.get('pI'))
        d['feat_cmc_gravy'] = to_float(r.get('GRAVY'))
        for f in ['feat_cmc_agg','feat_cmc_instability','feat_cmc_net_charge','feat_cmc_hydro_patch']:
            d[f] = float('nan')  # not computed for new

        # Liabilities
        d['feat_cdr_deamidation'] = float('nan')
        d['feat_cdr_isomerization'] = float('nan')
        d['feat_cdr_oxidation'] = float('nan')

        # Origin code
        d['feat_origin_code'] = 0.0 if d['origin'] == 'fully_human' else 1.0

        # Misc
        d['feat_total_cdr_length'] = float('nan')
        d['feat_agg_risk'] = float('nan')
        d['feat_format'] = 1.0  # default IgG
        d['feat_target_bio'] = float('nan')
        d['feat_anti_tnf'] = 0.0
        d['feat_approval_era'] = float('nan')
        d['feat_vz_foreignness'] = float('nan')  # needs ABARCII
        d['feat_fc_x_format'] = d['feat_fc_tolerogenic'] * (2 - d['feat_format'])
        d['feat_fc_glycan'] = float('nan')
        d['feat_cdrh3_risk'] = float('nan')
        d['feat_effective_burden'] = float('nan')

        # Dose magnitude
        d['dose_mg'] = parse_dose_mg(r.get('dose_mg', ''))

        rows.append(d)
    return pd.DataFrame(rows)


p70_df = build_from_sprint(sp)
new68_df = build_from_master(new68)

# Align columns
all_cols = sorted(set(p70_df.columns) | set(new68_df.columns))
for c in all_cols:
    if c not in p70_df.columns:
        p70_df[c] = float('nan')
    if c not in new68_df.columns:
        new68_df[c] = float('nan')

combined = pd.concat([p70_df, new68_df], ignore_index=True)
combined = combined[combined['ada'].notna()].reset_index(drop=True)

# ═══════════════════════════════════════════════════════════════
# Derive interaction features on the combined set
# ═══════════════════════════════════════════════════════════════
c = combined
c['ix_burden_nosupp']   = c['feat_net_burden'] * (1 - c['feat_immuno_suppression'] * 0.7)
c['ix_clust_nosupp']    = c['feat_n_clusters'] * (1 - c['feat_immuno_suppression'] * 0.7)
c['ix_depl_nosupp']     = c['feat_immune_depleting'] * (1 - c['feat_immuno_suppression'])
c['ix_arom_origin']     = c['feat_cdrh3_aromaticity'] * c['feat_origin_code']
c['ix_hl_inv']          = 1.0 / c['feat_half_life'].clip(lower=1)
c['ix_clust_hl']        = c['feat_n_clusters'] * c['ix_hl_inv']
c['ix_burden_hl']       = c['feat_net_burden'] * c['ix_hl_inv']
c['ix_route_burden']    = c['feat_route_sc'] * c['feat_net_burden']
c['ix_route_clust']     = c['feat_route_sc'] * c['feat_n_clusters']
c['ix_assay_burden']    = c['feat_assay_gen'] * c['feat_net_burden']
c['ix_assay_clust']     = c['feat_assay_gen'] * c['feat_n_clusters']
c['ix_pI_burden']       = c['feat_cmc_pI'] * c['feat_net_burden']
c['ix_vh_id_inv']       = (1 - c['feat_vh_identity'].clip(lower=0.5))
c['ix_vh_foreign_burd'] = c['ix_vh_id_inv'] * c['feat_net_burden']
c['ix_sup_hl']          = c['feat_immuno_suppression'] * c['feat_half_life']
c['ix_strong_nosupp']   = c['feat_n_strong_binders'] * (1 - c['feat_immuno_suppression'] * 0.7)

# Log ADA
c['log_ada'] = np.log10(c['ada'].clip(lower=0.05))

print(f"Combined: {len(c)} rows  (HU={sum(c['origin']=='humanized')}, FH={sum(c['origin']=='fully_human')})")
print(f"  p70: {sum(c['source']=='p70')}   new68: {sum(c['source']=='new68')}")

# ═══════════════════════════════════════════════════════════════
# Subsets
# ═══════════════════════════════════════════════════════════════
hu_p70 = c[(c['origin'] == 'humanized') & (c['source'] == 'p70')]
hu_all = c[c['origin'] == 'humanized']
fh_p70 = c[(c['origin'] == 'fully_human') & (c['source'] == 'p70')]
fh_all = c[c['origin'] == 'fully_human']
print(f"  HU_p70={len(hu_p70)}, HU_all={len(hu_all)}, FH_p70={len(fh_p70)}, FH_all={len(fh_all)}")

# ═══════════════════════════════════════════════════════════════
# LOO engines
# ═══════════════════════════════════════════════════════════════
def loo_ridge(ds: pd.DataFrame, feat_cols: list[str], target='ada'):
    sub = ds[[target] + feat_cols].dropna()
    if len(sub) < 8:
        return float('nan'), float('nan'), len(sub)
    X = sub[feat_cols].values.astype(float)
    y = sub[target].values.astype(float)
    preds = np.zeros(len(y))
    for tr, te in LeaveOneOut().split(X):
        sc = StandardScaler()
        Xtr = sc.fit_transform(X[tr]); Xte = sc.transform(X[te])
        md = RidgeCV(alphas=[0.01,0.1,1,10,50,100,200]).fit(Xtr, y[tr])
        preds[te] = md.predict(Xte)
    r, p = spearmanr(sub['ada'].values if target != 'ada' else y, preds)
    return float(r), float(p), len(sub)


def loo_gbr(ds: pd.DataFrame, feat_cols: list[str], target='ada',
            n_est=100, lr=0.04, md=2, msl=4):
    need_cols = list(dict.fromkeys([target, 'ada'] + feat_cols))
    sub = ds[need_cols].dropna(subset=[target]+feat_cols)
    if len(sub) < 10:
        return float('nan'), float('nan'), len(sub)
    X = sub[feat_cols].values.astype(float)
    y = sub[target].values.astype(float).ravel()
    y_raw = sub['ada'].values.astype(float).ravel() if target != 'ada' else y
    preds = np.zeros(len(y))
    for tr, te in LeaveOneOut().split(X):
        gb = GradientBoostingRegressor(
            n_estimators=n_est, max_depth=md, learning_rate=lr,
            subsample=0.8, random_state=42, min_samples_leaf=msl)
        gb.fit(X[tr], y[tr])
        preds[te] = gb.predict(X[te])
    r, p = spearmanr(y_raw, preds)
    return float(r), float(p), len(sub)


def sig(p):
    if math.isnan(p): return ' '
    if p < 0.01: return '**'
    if p < 0.05: return '*'
    if p < 0.10: return '^'
    return ' '


# ═══════════════════════════════════════════════════════════════
# Feature pools per group
# ═══════════════════════════════════════════════════════════════
# HU group: clinical confounders matter most
HU_POOL = [
    'feat_immuno_suppression','feat_half_life','feat_cdrh3_aromaticity',
    'feat_immune_depleting','feat_dosing_freq','feat_assay_gen',
    'feat_fc_tolerogenic','feat_n_clusters','feat_n_strong_binders',
    'feat_net_burden','feat_cdrh3_len','feat_cdrh3_polar',
    'feat_vh_identity','feat_cmc_pI','feat_route_sc',
    'feat_cdr_hydrophobicity','feat_cdrh3_charge',
    'ix_burden_nosupp','ix_depl_nosupp','ix_hl_inv','ix_sup_hl',
    'ix_clust_nosupp','ix_route_burden',
]

# FH group: sequence/structure matters more (no VZ foreignness for new)
FH_POOL = [
    'feat_n_clusters','feat_net_burden','feat_n_strong_binders',
    'feat_vh_identity','feat_cdrh3_aromaticity','feat_cdrh3_len',
    'feat_cdrh3_polar','feat_cdr_hydrophobicity','feat_cdrh3_charge',
    'feat_cmc_pI','feat_cmc_gravy','feat_half_life',
    'feat_immuno_suppression','feat_route_sc','feat_assay_gen',
    'feat_dosing_freq','feat_fc_tolerogenic',
    'ix_burden_nosupp','ix_clust_nosupp','ix_hl_inv',
    'ix_clust_hl','ix_burden_hl','ix_route_clust','ix_route_burden',
    'ix_assay_burden','ix_assay_clust','ix_vh_foreign_burd',
    'ix_strong_nosupp',
]

# WHOLE panel
ALL_POOL = list(set(HU_POOL + FH_POOL + ['feat_origin_code','ix_arom_origin']))


# ═══════════════════════════════════════════════════════════════
# Phase 1: Univariate Spearman scan (quick)
# ═══════════════════════════════════════════════════════════════
def corr_scan(ds, pool, label):
    rows = []
    y = ds['ada'].values
    for f in pool:
        if f not in ds.columns:
            continue
        x = ds[f].values.astype(float)
        mask = ~(np.isnan(x) | np.isnan(y))
        if mask.sum() < 5:
            continue
        r, p = spearmanr(x[mask], y[mask])
        rows.append({'f': f, 'r': r, 'p': p, 'n': int(mask.sum())})
    df = pd.DataFrame(rows).sort_values('r', key=abs, ascending=False)
    print(f"\n{'='*70}")
    print(f"UNIVARIATE SPEARMAN: {label}")
    print(f"{'='*70}")
    for _, row in df.head(20).iterrows():
        s = '**' if row['p'] < 0.01 else ('*' if row['p'] < 0.05 else ('^' if row['p'] < 0.10 else ' '))
        print(f"  {row['f']:35s} r={row['r']:+.3f}{s}  p={row['p']:.4f}  n={int(row['n'])}")
    return df

corr_hu = corr_scan(hu_all, HU_POOL, f'HU_all (n={len(hu_all)})')
corr_fh = corr_scan(fh_all, FH_POOL, f'FH_all (n={len(fh_all)})')
corr_all = corr_scan(c, ALL_POOL, f'ALL (n={len(c)})')


# ═══════════════════════════════════════════════════════════════
# Phase 2: Exhaustive LOO search for k=3..5 features (top-15 pool)
# ═══════════════════════════════════════════════════════════════
def exhaustive_loo_search(ds, pool_df, k_range=(3, 5), max_pool=15,
                           label='', method='ridge', target='ada'):
    top_feats = pool_df.head(max_pool)['f'].tolist()
    # Filter features that are actually available
    avail = [f for f in top_feats if f in ds.columns and ds[f].notna().sum() > len(ds) * 0.5]
    print(f"\n{'='*70}")
    print(f"EXHAUSTIVE LOO SEARCH: {label}  |  method={method}  target={target}")
    print(f"  Pool: {len(avail)} features from top-{max_pool} univariate")
    print(f"{'='*70}")

    results = []
    for k in range(k_range[0], k_range[1] + 1):
        combos = list(itertools.combinations(avail, k))
        nc = len(combos)
        print(f"  k={k}: {nc} combinations to evaluate ...", flush=True)
        for i, combo in enumerate(combos):
            fl = list(combo)
            if method == 'ridge':
                r, p, n = loo_ridge(ds, fl, target=target)
            else:
                r, p, n = loo_gbr(ds, fl, target=target)
            if not math.isnan(r):
                results.append({'k': k, 'feats': fl, 'r': r, 'p': p, 'n': n})
            if (i+1) % 50 == 0:
                print(f"    ... {i+1}/{nc}", flush=True)

    if not results:
        print("  No valid results!")
        return []

    results.sort(key=lambda x: -x['r'])
    print(f"\n  TOP 10 MODELS:")
    print(f"  {'k':>2}  {'LOO r':>8}  {'p':>8}  {'n':>4}  Features")
    print(f"  {'-'*70}")
    for i, res in enumerate(results[:10]):
        s = sig(res['p'])
        feats_str = ' + '.join(f.replace('feat_','').replace('ix_','X_') for f in res['feats'])
        print(f"  {res['k']:>2}  {res['r']:+.3f}{s}  {res['p']:.4f}  {res['n']:>4}  {feats_str}")

    return results


# Run exhaustive search
print("\n" + "#" * 80)
print("# PHASE 2: EXHAUSTIVE MODEL SEARCH")
print("#" * 80)

# HU group
hu_ridge = exhaustive_loo_search(hu_all, corr_hu, k_range=(3,5), max_pool=12,
                                  label=f'HU_all (n={len(hu_all)})', method='ridge')
hu_gbr   = exhaustive_loo_search(hu_all, corr_hu, k_range=(3,4), max_pool=8,
                                  label=f'HU_all GBR', method='gbr')

# FH group
fh_ridge = exhaustive_loo_search(fh_all, corr_fh, k_range=(3,5), max_pool=12,
                                  label=f'FH_all (n={len(fh_all)})', method='ridge')
fh_gbr   = exhaustive_loo_search(fh_all, corr_fh, k_range=(3,4), max_pool=8,
                                  label=f'FH_all GBR', method='gbr')

# Whole panel
all_ridge = exhaustive_loo_search(c, corr_all, k_range=(3,6), max_pool=15,
                                   label=f'ALL (n={len(c)})', method='ridge')
all_gbr   = exhaustive_loo_search(c, corr_all, k_range=(3,4), max_pool=8,
                                   label=f'ALL GBR', method='gbr')


# ═══════════════════════════════════════════════════════════════
# Phase 3: log(ADA) target
# ═══════════════════════════════════════════════════════════════
print("\n" + "#" * 80)
print("# PHASE 3: LOG-TRANSFORM TARGET")
print("#" * 80)

fh_ridge_log = exhaustive_loo_search(fh_all, corr_fh, k_range=(3,5), max_pool=12,
                                      label='FH_all log(ADA)', method='ridge', target='log_ada')
hu_ridge_log = exhaustive_loo_search(hu_all, corr_hu, k_range=(3,5), max_pool=12,
                                      label='HU_all log(ADA)', method='ridge', target='log_ada')
all_ridge_log = exhaustive_loo_search(c, corr_all, k_range=(3,5), max_pool=12,
                                       label='ALL log(ADA)', method='ridge', target='log_ada')


# ═══════════════════════════════════════════════════════════════
# Phase 4: Best model summary + comparison to 70-panel
# ═══════════════════════════════════════════════════════════════
print("\n" + "#" * 80)
print("# PHASE 4: BEST MODELS SUMMARY & COMPARISON")
print("#" * 80)

def get_best(results):
    if not results:
        return None
    return max(results, key=lambda x: x['r'])

sections = [
    ('HU Ridge', hu_ridge), ('HU GBR', hu_gbr),
    ('HU Ridge log', hu_ridge_log),
    ('FH Ridge', fh_ridge), ('FH GBR', fh_gbr),
    ('FH Ridge log', fh_ridge_log),
    ('ALL Ridge', all_ridge), ('ALL GBR', all_gbr),
    ('ALL Ridge log', all_ridge_log),
]

print(f"\n{'Model Group':<20}  {'LOO r':>8}  {'p':>8}  {'k':>3}  {'n':>4}  Features")
print("-" * 90)
for label, results in sections:
    best = get_best(results)
    if best is None:
        print(f"  {label:<20}  {'N/A':>8}")
        continue
    feats_str = ' + '.join(f.replace('feat_','').replace('ix_','X_') for f in best['feats'])
    s = sig(best['p'])
    print(f"  {label:<20}  {best['r']:+.3f}{s}  {best['p']:.4f}  {best['k']:>3}  {best['n']:>4}  {feats_str}")

# Baselines from 70-panel report
print(f"\n  --- 70-panel baselines (from published report) ---")
print(f"  {'HU-A p70 reference':<20}  +0.391**  0.0100    4    43  immuno_sup + cdrh3_arom + immune_depl + half_life")
print(f"  {'FH-A p70 reference':<20}  +0.518**  0.0060    3    27  n_clusters + net_burden + n_strong_binders")

# Also run the exact p70 baselines on current data for direct comparison
print(f"\n  --- Same baseline models evaluated on 138 ---")
for label, ds, feats in [
    ('HU-A on 138', hu_all, ['feat_immuno_suppression','feat_cdrh3_aromaticity','feat_immune_depleting','feat_half_life']),
    ('FH-A on 138', fh_all, ['feat_n_clusters','feat_net_burden','feat_n_strong_binders']),
]:
    r, p, n = loo_ridge(ds, feats)
    s = sig(p)
    feats_str = ' + '.join(f.replace('feat_','') for f in feats)
    print(f"  {label:<20}  {r:+.3f}{s}  {p:.4f}  {len(feats):>3}  {n:>4}  {feats_str}")

print("\nDone.")
