"""
ADA Predictive Modeling — 136-Panel
Compares: ALL-135 vs Tier-A+B-129 (drop 6 Tier-C)
Models: Spearman univariate | Ridge regression | Random Forest
Features: germline identity, CMC, MHC-II, surface immunogenicity
"""
import pandas as pd
import numpy as np
from scipy.stats import spearmanr, pearsonr
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneOut, cross_val_score, KFold
from sklearn.metrics import r2_score
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('data/immunogenicity_panel_136_master.csv')

# ── Feature set ────────────────────────────────────────────────────────────────
FEATURES = {
    'VH_identity':       'vh_identity_842',
    'VL_identity':       'vl_identity_842',
    'pI':                'pI',
    'instability':       'instability_index',
    'net_charge':        'net_charge_pH7',
    'hydro_patch':       'hydro_patch_max9',
    'charge_patch':      'charge_patch_max7',
    'TCIA_score':        'immuno_tcia_score',
    'n_high_epitopes':   'immuno_n_high',
    'n_clusters':        'immuno_n_clusters',
    'frac_exposed_vh':   'surf_frac_exposed_vh',
    'n_surf_patches':    'surf_n_patches',
}
TARGET = 'ada_first_pct'

def prepare(df_in, label):
    sub = df_in.dropna(subset=[TARGET] + list(FEATURES.values()))
    X = sub[[v for v in FEATURES.values()]].values.astype(float)
    y = sub[TARGET].values.astype(float)
    print("\n{}: n={}, ADA range {:.1f}–{:.1f}%, mean {:.1f}%".format(
        label, len(sub), y.min(), y.max(), y.mean()))
    return sub, X, y

# ── Two datasets ───────────────────────────────────────────────────────────────
df_all   = df[df[TARGET].notna()].copy()
df_clean = df_all[df_all['evidence_tier'].isin(['A','B'])].copy()

print("="*65)
print("DATASET COMPARISON")
print("="*65)
print("ALL   (incl Tier C): {} rows".format(len(df_all)))
print("CLEAN (Tier A+B only): {} rows".format(len(df_clean)))
print("Dropped (Tier C): {}".format(len(df_all) - len(df_clean)))

# ── Helper: run full model suite ───────────────────────────────────────────────
def run_models(sub, X, y, label):
    feat_names = list(FEATURES.keys())
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    n = len(y)
    cv = KFold(n_splits=min(10, n), shuffle=True, random_state=42)

    print("\n" + "─"*60)
    print("  MODEL RESULTS — {}".format(label))
    print("─"*60)

    # 1. Univariate Spearman
    print("\n  [A] Univariate Spearman vs ADA%")
    print("  {:22} {:>8} {:>8} {:>6}".format("Feature", "rho", "p", "sig"))
    rho_dict = {}
    for fname, fcol in FEATURES.items():
        vals = sub[fcol].values.astype(float)
        mask = ~np.isnan(vals)
        rho, pval = spearmanr(vals[mask], y[mask])
        sig = '**' if pval < 0.05 else ('*' if pval < 0.1 else '')
        rho_dict[fname] = rho
        print("  {:22} {:+8.3f} {:8.4f} {}".format(fname, rho, pval, sig))

    # 2. Ridge regression (CV)
    ridge = Ridge(alpha=1.0)
    r2_ridge = cross_val_score(ridge, Xs, y, cv=cv, scoring='r2')
    ridge.fit(Xs, y)
    print("\n  [B] Ridge Regression (10-fold CV)")
    print("  R² mean={:.3f}  std={:.3f}".format(r2_ridge.mean(), r2_ridge.std()))
    coef_df = pd.DataFrame({'feature': feat_names, 'coef': ridge.coef_})
    coef_df = coef_df.reindex(coef_df['coef'].abs().sort_values(ascending=False).index)
    for _, row2 in coef_df.iterrows():
        print("  {:22} coef={:+.4f}".format(row2['feature'], row2['coef']))

    # 3. Random Forest (CV)
    rf = RandomForestRegressor(n_estimators=200, max_depth=4, min_samples_leaf=5,
                                random_state=42)
    r2_rf = cross_val_score(rf, X, y, cv=cv, scoring='r2')
    rf.fit(X, y)
    print("\n  [C] Random Forest (10-fold CV)")
    print("  R² mean={:.3f}  std={:.3f}".format(r2_rf.mean(), r2_rf.std()))
    imp_df = pd.DataFrame({'feature': feat_names, 'importance': rf.feature_importances_})
    imp_df = imp_df.sort_values('importance', ascending=False)
    for _, row2 in imp_df.iterrows():
        bar = '█' * int(row2['importance'] * 100)
        print("  {:22} {:.4f}  {}".format(row2['feature'], row2['importance'], bar))

    # 4. Gradient Boosting
    gb = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05,
                                    min_samples_leaf=5, random_state=42)
    r2_gb = cross_val_score(gb, X, y, cv=cv, scoring='r2')
    gb.fit(X, y)
    print("\n  [D] Gradient Boosting (10-fold CV)")
    print("  R² mean={:.3f}  std={:.3f}".format(r2_gb.mean(), r2_gb.std()))
    imp_gb = pd.DataFrame({'feature': feat_names, 'importance': gb.feature_importances_})
    imp_gb = imp_gb.sort_values('importance', ascending=False)
    for _, row2 in imp_gb.iterrows():
        bar = '█' * int(row2['importance'] * 100)
        print("  {:22} {:.4f}  {}".format(row2['feature'], row2['importance'], bar))

    return {
        'ridge_r2': r2_ridge.mean(),
        'rf_r2': r2_rf.mean(),
        'gb_r2': r2_gb.mean(),
        'top_feature': imp_df.iloc[0]['feature'],
        'rf_importances': dict(zip(feat_names, rf.feature_importances_)),
    }

sub_all,   X_all,   y_all   = prepare(df_all,   "ALL-135   (incl Tier C)")
sub_clean, X_clean, y_clean = prepare(df_clean, "CLEAN-129 (Tier A+B)")

res_all   = run_models(sub_all,   X_all,   y_all,   "ALL-135   incl Tier C")
res_clean = run_models(sub_clean, X_clean, y_clean, "CLEAN-129 Tier A+B")

# ── Head-to-head comparison ────────────────────────────────────────────────────
print("\n" + "="*65)
print("HEAD-TO-HEAD COMPARISON")
print("="*65)
print("  {:30} {:>12} {:>12}".format("Model", "ALL-135", "CLEAN-129"))
print("  {:30} {:>12} {:>12}".format("Ridge R²",
      "{:.3f}".format(res_all['ridge_r2']),
      "{:.3f}".format(res_clean['ridge_r2'])))
print("  {:30} {:>12} {:>12}".format("Random Forest R²",
      "{:.3f}".format(res_all['rf_r2']),
      "{:.3f}".format(res_clean['rf_r2'])))
print("  {:30} {:>12} {:>12}".format("Gradient Boosting R²",
      "{:.3f}".format(res_all['gb_r2']),
      "{:.3f}".format(res_clean['gb_r2'])))

print("\n  Feature importance shift (RF, top features):")
feat_names = list(FEATURES.keys())
all_imp   = res_all['rf_importances']
clean_imp = res_clean['rf_importances']
comp = [(f, all_imp[f], clean_imp[f]) for f in feat_names]
comp.sort(key=lambda x: -(x[1]+x[2]))
print("  {:22} {:>10} {:>10} {:>10}".format("Feature", "ALL-135", "CLEAN-129", "Delta"))
for f, a, c in comp:
    delta = c - a
    arrow = '↑' if delta > 0.01 else ('↓' if delta < -0.01 else '→')
    print("  {:22} {:10.4f} {:10.4f} {:+8.4f} {}".format(f, a, c, delta, arrow))

print("\n  Recommendation:")
delta_r2_rf = res_clean['rf_r2'] - res_all['rf_r2']
if delta_r2_rf > 0.01:
    print("  → CLEAN-129 is better by ΔR²={:.3f} (RF). Removing Tier C improves model.".format(delta_r2_rf))
elif delta_r2_rf < -0.01:
    print("  → ALL-135 is better by ΔR²={:.3f} (RF). Tier C not hurting.".format(-delta_r2_rf))
else:
    print("  → Minimal difference ΔR²={:.3f}. Tier C has negligible impact.".format(delta_r2_rf))
print("  → Use CLEAN-129 for any publication/reporting (evidence traceability).")
