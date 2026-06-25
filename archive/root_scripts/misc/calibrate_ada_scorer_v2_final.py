"""
ADA Scorer V2 — Final calibration with expanded grid + nonlinear terms.
Uses CLEAN-129 (Tier A+B) as calibration panel.
Optimizes for: max Spearman(score, ADA%), then tier separation.
"""
import pandas as pd
import numpy as np
import math
import json
from scipy.stats import spearmanr, mannwhitneyu
from sklearn.metrics import balanced_accuracy_score
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('data/immunogenicity_panel_136_master.csv')
panel = df[df['evidence_tier'].isin(['A','B']) & df['ada_first_pct'].notna()].copy()
panel = panel.dropna(subset=['vh_identity_842','vl_identity_842',
                              'surf_frac_exposed_vh','surf_frac_exposed_vl',
                              'interface_n_pairs','immuno_tcia_score',
                              'immuno_n_high','immuno_n_clusters',
                              'instability_index','hydro_patch_max9',
                              'surf_n_patches'])
n = len(panel)
y = panel['ada_first_pct'].values.astype(float)
y_log = np.log1p(y)
print("Panel: n={}  ADA range: {:.1f}–{:.1f}%\n".format(n, y.min(), y.max()))

def sigmoid(x):
    x = max(-20, min(20, x))
    return 1.0 / (1.0 + math.exp(-x))

# Pre-extract arrays for speed
arr = {
    'vh_id':       panel['vh_identity_842'].values.astype(float),
    'vl_id':       panel['vl_identity_842'].values.astype(float),
    'frac_vh':     panel['surf_frac_exposed_vh'].values.astype(float),
    'frac_vl':     panel['surf_frac_exposed_vl'].values.astype(float),
    'n_pairs':     panel['interface_n_pairs'].values.astype(float),
    'n_high':      panel['immuno_n_high'].values.astype(float),
    'n_clust':     panel['immuno_n_clusters'].values.astype(float),
    'n_patches':   panel['surf_n_patches'].values.astype(float),
    'instab':      panel['instability_index'].values.astype(float),
    'hydro':       panel['hydro_patch_max9'].values.astype(float),
    'origin':      panel['origin'].values,
}

def score_batch(p):
    G = np.clip(1.0 - arr['vh_id'], 0, 1)                  # germline distance
    F = np.clip(1.0 - arr['frac_vh'], 0, 1)                 # inverse exposure VH
    I = np.clip(arr['n_pairs'] / p['i_scale'], 0, 1)        # interface density
    E = np.clip(arr['n_high'] / p['e_scale'], 0, 1)         # high-risk epitopes
    C = np.clip(arr['n_clust'] / 5.0, 0, 1)                 # cluster density
    P = np.clip(arr['n_patches'] / p['p_scale'], 0, 1)      # surface patch count

    z = (p['w_G']*G + p['w_F']*F + p['w_I']*I +
         p['w_E']*E + p['w_C']*C + p['w_P']*P)

    # VL modulator (subgroup-specific sign)
    vl_delta = np.where(
        arr['origin'] == 'natural',
        p['vl_nat'] * (arr['vl_id'] - 0.95),
        p['vl_eng'] * (arr['vl_id'] - 0.90),
    )
    z += vl_delta

    # Synergy: germline distance * surface exposure
    z += p['syn_GF'] * G * F

    # Synergy: germline distance * interface
    z += p['syn_GI'] * G * I

    # CMC veto
    z += np.where(arr['instab'] > p['instab_gate'], p['instab_pen'], 0.0)
    z += np.where(arr['hydro'] > p['hydro_gate'], p['hydro_pen'], 0.0)

    scores = np.array([sigmoid(p['slope'] * (zi - p['mid'])) for zi in z])
    return scores

# ════════════════════════════════════════════════════════════════════════════════
# Expanded grid
# ════════════════════════════════════════════════════════════════════════════════
configs = []
for w_G in [0.25, 0.30, 0.35, 0.40]:
    for w_F in [0.15, 0.20, 0.25, 0.30]:
        for w_I in [0.05, 0.10, 0.15]:
            for w_E in [0.05, 0.10, 0.15]:
                for w_P in [0.00, 0.05, 0.10]:
                    w_C = round(1.0 - w_G - w_F - w_I - w_E - w_P, 2)
                    if w_C < 0.0 or w_C > 0.20:
                        continue
                    for slope in [3.0, 4.0, 5.0, 6.0]:
                        for mid in [0.25, 0.30, 0.35, 0.40, 0.45]:
                            for syn_GF in [0.0, 0.05, 0.10]:
                                for syn_GI in [0.0, 0.05]:
                                    configs.append({
                                        'w_G': w_G, 'w_F': w_F, 'w_I': w_I,
                                        'w_E': w_E, 'w_C': w_C, 'w_P': w_P,
                                        'slope': slope, 'mid': mid,
                                        'syn_GF': syn_GF, 'syn_GI': syn_GI,
                                        'vl_nat': -0.15, 'vl_eng': +0.05,
                                        'i_scale': 60, 'e_scale': 40, 'p_scale': 14,
                                        'instab_gate': 45, 'instab_pen': 0.08,
                                        'hydro_gate': 0.75, 'hydro_pen': 0.05,
                                    })

print("Expanded grid: {} configurations".format(len(configs)))

best_rho = -1.0
best_cfg = None
for cfg in configs:
    scores = score_batch(cfg)
    rho, _ = spearmanr(scores, y)
    if rho > best_rho:
        best_rho = rho
        best_cfg = cfg

print("Best Spearman rho: {:+.4f}".format(best_rho))

# Refine around best with finer VL params
print("\nRefining VL modulator...")
refined_best = best_rho
refined_cfg = dict(best_cfg)
for vl_n in [-0.30, -0.20, -0.15, -0.10, -0.05]:
    for vl_e in [-0.05, 0.0, +0.05, +0.10, +0.15]:
        cfg2 = dict(best_cfg)
        cfg2['vl_nat'] = vl_n
        cfg2['vl_eng'] = vl_e
        scores2 = score_batch(cfg2)
        rho2, _ = spearmanr(scores2, y)
        if rho2 > refined_best:
            refined_best = rho2
            refined_cfg = dict(cfg2)

print("After VL refinement: rho {:+.4f} -> {:+.4f}".format(best_rho, refined_best))

# Refine CMC gates
print("Refining CMC veto...")
for ig in [40, 42, 45, 48, 50]:
    for ip in [0.04, 0.06, 0.08, 0.10, 0.12]:
        for hg in [0.60, 0.65, 0.70, 0.75, 0.80]:
            for hp in [0.03, 0.05, 0.07]:
                cfg3 = dict(refined_cfg)
                cfg3['instab_gate'] = ig
                cfg3['instab_pen'] = ip
                cfg3['hydro_gate'] = hg
                cfg3['hydro_pen'] = hp
                scores3 = score_batch(cfg3)
                rho3, _ = spearmanr(scores3, y)
                if rho3 > refined_best:
                    refined_best = rho3
                    refined_cfg = dict(cfg3)

print("After CMC refinement: rho {:+.4f}".format(refined_best))
best_cfg = refined_cfg

# ════════════════════════════════════════════════════════════════════════════════
# Final evaluation
# ════════════════════════════════════════════════════════════════════════════════
scores_final = score_batch(best_cfg)
rho_f, p_f = spearmanr(scores_final, y)
rho_log_f, _ = spearmanr(scores_final, y_log)

print("\n" + "="*65)
print("FINAL V2 PARAMETERS (calibrated on CLEAN-{})".format(n))
print("="*65)
for k in ['w_G','w_F','w_I','w_E','w_C','w_P','slope','mid',
          'syn_GF','syn_GI','vl_nat','vl_eng',
          'i_scale','e_scale','p_scale',
          'instab_gate','instab_pen','hydro_gate','hydro_pen']:
    print("  {:20} = {}".format(k, best_cfg[k]))

print("\nSpearman vs ADA%: rho={:+.4f} p={:.4f}".format(rho_f, p_f))
print("Spearman vs log(1+ADA): rho={:+.4f}".format(rho_log_f))

# Threshold calibration
ADA_CUTOFF = 10.0
y_binary = (y > ADA_CUTOFF).astype(int)
best_bal = -1
best_th = 0.5
best_tm = 0.3
for th in np.arange(0.30, 0.90, 0.01):
    for tm in np.arange(0.15, th - 0.03, 0.01):
        pred = np.where(scores_final >= th, 2, np.where(scores_final >= tm, 1, 0))
        pred_bin = (pred >= 1).astype(int)
        ba = balanced_accuracy_score(y_binary, pred_bin)
        if ba > best_bal:
            best_bal = ba
            best_th = round(th, 3)
            best_tm = round(tm, 3)

best_cfg['threshold_high'] = best_th
best_cfg['threshold_medium'] = best_tm

print("\nThreshold HIGH >= {}, MEDIUM >= {}".format(best_th, best_tm))
print("Balanced accuracy (ADA>{}%): {:.3f}".format(ADA_CUTOFF, best_bal))

# Tier analysis
tiers = np.where(scores_final >= best_th, 'HIGH',
         np.where(scores_final >= best_tm, 'MEDIUM', 'LOW'))
panel_out = panel.copy()
panel_out['v2_score'] = scores_final
panel_out['v2_tier'] = tiers

print("\nTier Distribution & ADA Profile:")
for t in ['LOW','MEDIUM','HIGH']:
    sub = panel_out[panel_out['v2_tier']==t]
    if len(sub) == 0:
        continue
    print("  {:6} n={:3} ({:4.0f}%)  ADA: mean={:5.1f}% median={:4.1f}%  range={:.0f}–{:.0f}%".format(
        t, len(sub), len(sub)/n*100, sub['ada_first_pct'].mean(), sub['ada_first_pct'].median(),
        sub['ada_first_pct'].min(), sub['ada_first_pct'].max()))

# Statistical tier separation
for t1, t2 in [('LOW','MEDIUM'),('MEDIUM','HIGH'),('LOW','HIGH')]:
    g1 = panel_out[panel_out['v2_tier']==t1]['ada_first_pct'].values
    g2 = panel_out[panel_out['v2_tier']==t2]['ada_first_pct'].values
    if len(g1) > 2 and len(g2) > 2:
        u, p = mannwhitneyu(g1, g2, alternative='less')
        print("  {} vs {}: Mann-Whitney p={:.4f} {}".format(t1, t2, p, '**' if p<0.05 else ''))

# V1 comparison
def score_v1_batch():
    B = np.full(n, min(math.log1p(0.5/0.5), 1.0))
    S = (arr['frac_vh'] + arr['frac_vl']) / 2
    C = np.clip(arr['n_clust'] / 5.0, 0, 1)
    N = np.clip(arr['n_high'] / 20.0, 0, 1)
    z = 0.50*B + 0.15*S + 0.25*C + 0.10*N + 0.10*B*S
    return np.array([sigmoid(5.0*(zi - 0.45)) for zi in z])

scores_v1 = score_v1_batch()
rho_v1, _ = spearmanr(scores_v1, y)

print("\n=== V1 vs V2 HEAD-TO-HEAD ===")
print("  V1 Spearman: {:+.4f}".format(rho_v1))
print("  V2 Spearman: {:+.4f}".format(rho_f))
print("  Improvement: {:+.4f} ({:.0f}x)".format(rho_f - rho_v1,
      rho_f/rho_v1 if rho_v1 > 0.001 else float('inf')))

# High-ADA antibody ranking check
print("\nTop-10 ADA antibodies: V2 score ranking")
top10 = panel_out.nlargest(10, 'ada_first_pct')[
    ['antibody_name','ada_first_pct','v2_score','v2_tier','origin']]
for _, r in top10.iterrows():
    print("  {:25} ADA={:5.1f}% score={:.3f} tier={:6} {}".format(
        r['antibody_name'], r['ada_first_pct'], r['v2_score'], r['v2_tier'], r['origin']))

# Save
save_obj = {
    'version': '2.0',
    'calibration_date': '2026-04-03',
    'calibration_panel': 'CLEAN-129 Tier A+B (n={})'.format(n),
    'spearman_rho_ada': round(rho_f, 4),
    'spearman_rho_log_ada': round(rho_log_f, 4),
    'balanced_accuracy_10pct': round(best_bal, 4),
    'components': {
        'G_germline_distance': {'weight': best_cfg['w_G'], 'formula': '1 - VH_germline_identity'},
        'F_inverse_exposure':  {'weight': best_cfg['w_F'], 'formula': '1 - frac_exposed_vh'},
        'I_interface_density': {'weight': best_cfg['w_I'], 'formula': 'min(n_pairs/scale, 1)', 'scale': best_cfg['i_scale']},
        'E_high_epitopes':     {'weight': best_cfg['w_E'], 'formula': 'min(n_high/scale, 1)', 'scale': best_cfg['e_scale']},
        'C_cluster_density':   {'weight': best_cfg['w_C'], 'formula': 'min(n_clusters/5, 1)'},
        'P_surface_patches':   {'weight': best_cfg['w_P'], 'formula': 'min(n_patches/scale, 1)', 'scale': best_cfg['p_scale']},
    },
    'synergy_terms': {
        'GxF': best_cfg['syn_GF'],
        'GxI': best_cfg['syn_GI'],
    },
    'vl_modulator': {
        'natural': best_cfg['vl_nat'],
        'engineered': best_cfg['vl_eng'],
        'reference_point_natural': 0.95,
        'reference_point_engineered': 0.90,
    },
    'cmc_veto_gates': {
        'instability_index': {'gate': best_cfg['instab_gate'], 'penalty': best_cfg['instab_pen']},
        'hydro_patch_max9':  {'gate': best_cfg['hydro_gate'], 'penalty': best_cfg['hydro_pen']},
    },
    'sigmoid': {'slope': best_cfg['slope'], 'midpoint': best_cfg['mid']},
    'thresholds': {'high': best_th, 'medium': best_tm},
}

out = Path('config/immunogenicity_risk_v2.json')
out.write_text(json.dumps(save_obj, indent=2, ensure_ascii=False))
print("\nSaved: {}".format(out))

cal = Path('data/reference/ada_calibration/calibrated_params.json')
cal.write_text(json.dumps({
    'threshold_high': best_th,
    'threshold_medium': best_tm,
    'version': '2.0',
}, indent=2))
print("Saved: {}".format(cal))
