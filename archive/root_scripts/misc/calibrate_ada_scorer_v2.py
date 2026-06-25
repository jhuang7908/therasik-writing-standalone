"""
ADA Scorer V2 Parameter Calibration
Based on CLEAN-129 (Tier A+B) evidence.

Changes from V1:
  1. Add germline identity gate (VH_identity is #1 RF feature)
  2. Replace mean(frac_exposed_vh, frac_exposed_vl) with frac_exposed_vh alone
     (VL exposure is noise; VH exposure is the only significant signal)
  3. Add interface_pairs as new structural component
  4. TCIA_score → weight=0 (rho=0.000 vs ADA)
  5. Add subgroup-aware VL_identity modulator
  6. CMC veto gates (instability, hydro_patch)
  7. Recalibrate thresholds on 129-sample panel
"""
import pandas as pd
import numpy as np
import math
import json
from scipy.stats import spearmanr
from sklearn.metrics import balanced_accuracy_score
from pathlib import Path

df = pd.read_csv('data/immunogenicity_panel_136_master.csv')
panel = df[df['evidence_tier'].isin(['A','B']) & df['ada_first_pct'].notna()].copy()
panel = panel.dropna(subset=['vh_identity_842','surf_frac_exposed_vh',
                              'interface_n_pairs','immuno_tcia_score',
                              'immuno_n_high','immuno_n_clusters',
                              'instability_index','hydro_patch_max9'])
n = len(panel)
y = panel['ada_first_pct'].values.astype(float)
y_log = np.log1p(y)
print("Calibration panel: n={}  ADA range: {:.1f}–{:.1f}%\n".format(n, y.min(), y.max()))

# ════════════════════════════════════════════════════════════════════════════════
# V2 Scoring Function
# ════════════════════════════════════════════════════════════════════════════════
#
# Components (all normalised [0,1]):
#   G = 1 - VH_germline_identity         # germline distance (higher = more foreign = more risk)
#   F = 1 - frac_exposed_vh              # inverse exposure (higher = more buried = more risk)
#   I = min(interface_pairs, 60) / 60    # VH-VL interface contact density
#   E = min(n_high_epitopes, 40) / 40    # MHC-II high-risk epitope count
#   C = min(n_clusters, 5) / 5           # spatial hotspot clusters
#
# VL modulator (subgroup-dependent):
#   if origin == 'natural':   VL_mod = -0.05 * (VL_identity - 0.95)   # more human VL → lower risk
#   if origin == 'engineered': VL_mod = +0.02 * (VL_identity - 0.90)  # reversed signal
#
# CMC veto:
#   instability_index > 45 → +0.10 penalty
#   hydro_patch_max9 > 0.75 → +0.05 penalty
#
# Composite:
#   z = w_G*G + w_F*F + w_I*I + w_E*E + w_C*C + VL_mod + CMC_penalty
#   score = sigmoid(slope * (z - midpoint))

def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))

def score_v2(row, params):
    p = params
    vh_id = float(row['vh_identity_842'])
    frac_vh = float(row['surf_frac_exposed_vh'])
    n_pairs = float(row['interface_n_pairs'])
    n_high = float(row['immuno_n_high'])
    n_clust = float(row['immuno_n_clusters'])
    vl_id = float(row['vl_identity_842']) if pd.notna(row.get('vl_identity_842')) else 0.95
    origin = str(row.get('origin', 'engineered')).lower()
    instab = float(row['instability_index'])
    hydro = float(row['hydro_patch_max9'])

    G = max(0, min(1 - vh_id, 1.0))
    F = max(0, min(1 - frac_vh, 1.0))
    I = min(n_pairs / p['interface_scale'], 1.0)
    E = min(n_high / p['epitope_scale'], 1.0)
    C = min(n_clust / 5.0, 1.0)

    z = (p['w_G'] * G + p['w_F'] * F + p['w_I'] * I +
         p['w_E'] * E + p['w_C'] * C)

    if origin == 'natural':
        vl_mod = p['vl_natural_w'] * (vl_id - 0.95)
    else:
        vl_mod = p['vl_engineered_w'] * (vl_id - 0.90)
    z += vl_mod

    cmc_pen = 0.0
    if instab > p['instab_veto']:
        cmc_pen += p['instab_penalty']
    if hydro > p['hydro_veto']:
        cmc_pen += p['hydro_penalty']
    z += cmc_pen

    score = sigmoid(p['slope'] * (z - p['midpoint']))
    return score, {'G': G, 'F': F, 'I': I, 'E': E, 'C': C,
                   'vl_mod': vl_mod, 'cmc_pen': cmc_pen, 'z': z}

# ════════════════════════════════════════════════════════════════════════════════
# Grid search for optimal weight combination
# ════════════════════════════════════════════════════════════════════════════════

best_rho = -1.0
best_params = None

# Anchor ranges from evidence:
#   VH_identity (RF=18%, rho=-0.141 ~ -0.155)
#   frac_exposed_vh (RF=20%, rho=-0.214)
#   interface_pairs (rho=+0.178)
#   n_high_epitopes (RF=6%)
#   n_clusters (marginal)

base = {
    'interface_scale': 60,
    'epitope_scale': 40,
    'vl_natural_w': -0.15,
    'vl_engineered_w': +0.05,
    'instab_veto': 45,
    'instab_penalty': 0.08,
    'hydro_veto': 0.75,
    'hydro_penalty': 0.05,
}

configs = []
for w_G in [0.25, 0.30, 0.35]:
    for w_F in [0.20, 0.25, 0.30]:
        for w_I in [0.10, 0.15, 0.20]:
            for w_E in [0.05, 0.10, 0.15]:
                w_C = 1.0 - w_G - w_F - w_I - w_E
                if w_C < 0.02 or w_C > 0.25:
                    continue
                for slope in [4.0, 5.0, 6.0]:
                    for mid in [0.30, 0.35, 0.40, 0.45]:
                        configs.append({
                            **base,
                            'w_G': w_G, 'w_F': w_F, 'w_I': w_I,
                            'w_E': w_E, 'w_C': w_C,
                            'slope': slope, 'midpoint': mid,
                        })

print("Grid search: {} configurations".format(len(configs)))

results_all = []
for i, cfg in enumerate(configs):
    scores = np.array([score_v2(row, cfg)[0] for _, row in panel.iterrows()])
    rho, p_val = spearmanr(scores, y)
    rho_log, _ = spearmanr(scores, y_log)
    results_all.append({'cfg_idx': i, 'rho': rho, 'rho_log': rho_log, 'p': p_val, **cfg})
    if rho > best_rho:
        best_rho = rho
        best_params = cfg

res_df = pd.DataFrame(results_all)
res_df = res_df.sort_values('rho', ascending=False)

print("\nTop 5 configurations (by Spearman rho vs ADA%):")
for _, r in res_df.head(5).iterrows():
    print("  rho={:+.4f} rho_log={:+.4f} p={:.4f} | G={:.2f} F={:.2f} I={:.2f} E={:.2f} C={:.2f} slope={:.0f} mid={:.2f}".format(
        r['rho'], r['rho_log'], r['p'],
        r['w_G'], r['w_F'], r['w_I'], r['w_E'], r['w_C'], r['slope'], r['midpoint']))

# ════════════════════════════════════════════════════════════════════════════════
# Apply best params, calibrate thresholds
# ════════════════════════════════════════════════════════════════════════════════
print("\n=== BEST PARAMETERS ===")
for k, v in sorted(best_params.items()):
    print("  {:25} = {}".format(k, v))

scores_best = np.array([score_v2(row, best_params)[0] for _, row in panel.iterrows()])

# Threshold calibration: maximize balanced accuracy for binary ADA >10%
ADA_CUTOFF = 10.0
y_binary = (y > ADA_CUTOFF).astype(int)
print("\nBinary split: ADA>{:.0f}% = {} positive, {} negative".format(
    ADA_CUTOFF, y_binary.sum(), (1-y_binary).sum()))

best_bal = -1
best_th = 0.5
best_tm = 0.3
for th in np.arange(0.3, 0.85, 0.02):
    for tm in np.arange(0.15, th - 0.05, 0.02):
        pred = (scores_best >= tm).astype(int)
        ba = balanced_accuracy_score(y_binary, pred)
        if ba > best_bal:
            best_bal = ba
            best_th = round(th, 3)
            best_tm = round(tm, 3)

best_params['threshold_high'] = best_th
best_params['threshold_medium'] = best_tm

print("Optimal thresholds: HIGH >= {}, MEDIUM >= {}".format(best_th, best_tm))
print("Balanced accuracy (ADA>10% binary): {:.3f}".format(best_bal))

# Full correlation
rho_final, p_final = spearmanr(scores_best, y)
rho_log_f, p_log_f = spearmanr(scores_best, y_log)
print("\nFinal Spearman: rho={:+.4f} p={:.4f}".format(rho_final, p_final))
print("Final Spearman (log): rho={:+.4f} p={:.4f}".format(rho_log_f, p_log_f))

# Risk tier distribution
tiers = []
for s in scores_best:
    if s >= best_th:
        tiers.append('HIGH')
    elif s >= best_tm:
        tiers.append('MEDIUM')
    else:
        tiers.append('LOW')
panel_out = panel.copy()
panel_out['v2_score'] = scores_best
panel_out['v2_tier'] = tiers

print("\nRisk tier distribution:")
tier_counts = pd.Series(tiers).value_counts()
for t in ['LOW','MEDIUM','HIGH']:
    if t in tier_counts:
        sub = panel_out[panel_out['v2_tier']==t]
        print("  {} {:3} ({:.0f}%)  mean_ADA={:.1f}%  median_ADA={:.1f}%".format(
            t, len(sub), len(sub)/n*100, sub['ada_first_pct'].mean(), sub['ada_first_pct'].median()))

# Separation quality
print("\nTier separation quality:")
for t1, t2 in [('LOW','MEDIUM'),('MEDIUM','HIGH')]:
    g1 = panel_out[panel_out['v2_tier']==t1]['ada_first_pct'].values
    g2 = panel_out[panel_out['v2_tier']==t2]['ada_first_pct'].values
    if len(g1) > 2 and len(g2) > 2:
        from scipy.stats import mannwhitneyu
        u, p = mannwhitneyu(g1, g2, alternative='less')
        print("  {} vs {}: U={:.0f} p={:.4f} {}".format(t1, t2, u, p, '** sig' if p<0.05 else ''))

# ════════════════════════════════════════════════════════════════════════════════
# Compare V1 vs V2 on same panel
# ════════════════════════════════════════════════════════════════════════════════
print("\n=== V1 vs V2 COMPARISON ===")
# Run V1 scoring
def score_v1(row):
    net_burden = 0.5
    frac_vh = float(row.get('surf_frac_exposed_vh', 0.6))
    frac_vl = float(row.get('surf_frac_exposed_vl', 0.6))
    n_clusters = float(row.get('immuno_n_clusters', 3))
    n_strong = float(row.get('immuno_n_high', 15))
    B = math.log1p(net_burden / 0.5)
    B = min(B, 1.0)
    fracs = [f for f in [frac_vh, frac_vl] if not np.isnan(f)]
    S = np.mean(fracs) if fracs else 0.5
    C = min(n_clusters/5.0, 1.0)
    N = min(n_strong/20.0, 1.0)
    z = 0.50*B + 0.15*S + 0.25*C + 0.10*N + 0.10*B*S
    return sigmoid(5.0 * (z - 0.45))

scores_v1 = np.array([score_v1(row) for _, row in panel.iterrows()])
rho_v1, p_v1 = spearmanr(scores_v1, y)
rho_v2, p_v2 = spearmanr(scores_best, y)
print("  V1 Spearman: rho={:+.4f} p={:.4f}".format(rho_v1, p_v1))
print("  V2 Spearman: rho={:+.4f} p={:.4f}".format(rho_v2, p_v2))
print("  Improvement: ΔSpearman = {:+.4f}".format(rho_v2 - rho_v1))

# Save parameters
out_path = Path('config/immunogenicity_risk_v2.json')
out_path.parent.mkdir(parents=True, exist_ok=True)
save_params = {
    'version': '2.0',
    'calibration_date': '2026-04-03',
    'calibration_panel': 'CLEAN-129 (Tier A+B, n={})'.format(n),
    'evidence_source': 'data/immunogenicity_panel_136_master.csv',
    **{k: round(v, 4) if isinstance(v, float) else v for k, v in best_params.items()},
}
out_path.write_text(json.dumps(save_params, indent=2, ensure_ascii=False))
print("\nSaved: {}".format(out_path))

# Also save calibrated_params.json for ADAScorer
cal_path = Path('data/reference/ada_calibration')
cal_path.mkdir(parents=True, exist_ok=True)
cal_file = cal_path / 'calibrated_params.json'
cal_data = {
    'threshold_high': best_th,
    'threshold_medium': best_tm,
    'calibration_source': 'calibrate_ada_scorer_v2.py',
    'calibration_panel_size': n,
    'spearman_rho': round(rho_final, 4),
}
cal_file.write_text(json.dumps(cal_data, indent=2))
print("Saved: {}".format(cal_file))

print("\n=== DONE ===")
