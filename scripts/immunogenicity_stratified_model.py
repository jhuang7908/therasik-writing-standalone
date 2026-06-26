"""
immunogenicity_stratified_model.py
====================================
Stratified modeling: separate models for humanized vs fully human antibodies.
Hypothesis: within-group molecular features have stronger signal once
clinical background variance is reduced.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr, pearsonr, mannwhitneyu
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")

ROOT = Path("d:/InSynBio-AI-Research/Antibody_Engineer_Suite")
OUT  = ROOT / "data/thera_sabdab/out"

m = pd.read_csv(OUT / "immuno70_sprint_matrix.csv")
m = m.drop_duplicates("antibody_name").copy()
target = "ada_rate_pct"

hu = m[m["origin"] == "humanized"].copy()
fu = m[m["origin"] == "fully_human"].copy()

print("=" * 78)
print(f"HUMANIZED: n={len(hu)}  ADA mean={hu[target].mean():.1f}%  "
      f"median={hu[target].median():.1f}%  range={hu[target].min():.1f}–{hu[target].max():.1f}%")
print(f"FULLY HUMAN: n={len(fu)}  ADA mean={fu[target].mean():.1f}%  "
      f"median={fu[target].median():.1f}%  range={fu[target].min():.1f}–{fu[target].max():.1f}%")
U, p_mw = mannwhitneyu(hu[target], fu[target], alternative="greater")
print(f"Mann-Whitney U: humanized > fully_human  p={p_mw:.4f}")

# ============================================================
# Define feature sets specific to each group
# ============================================================

# For HUMANIZED: molecular foreignness features matter most
# (they have murine CDRs, back-mutations, variable Vernier zone identity)
HUMANIZED_MOL = [
    "feat_vz_foreignness",      # Vernier zone foreign residues
    "feat_vh_identity",         # framework germline identity
    "feat_vl_identity",         # VL framework identity
    "feat_n_strong_binders",    # MHC-II epitope count
    "feat_net_burden",          # tolerance-adjusted burden
    "feat_n_clusters",          # epitope hot spots
    "feat_cdrh3_len",           # CDR-H3 loop length
    "feat_cdrh3_aromaticity",   # CDR-H3 aromatic content
    "feat_cdr_deamidation",     # CDR deamidation motifs
    "feat_total_cdr_length",    # total CDR length
    "feat_vh_family_score",     # VH germline family
]

HUMANIZED_CLIN = [
    "feat_fc_tolerogenic",      # Fc engineering (no Fc = high risk)
    "feat_immuno_suppression",  # MTX/chemo co-medication
    "feat_dosing_freq",         # injection frequency
    "feat_immune_depleting",    # CD52/CD20 depletion targets
    "feat_format",              # scFv/VHH/Fab vs whole IgG
    "feat_half_life",           # drug half-life
    "feat_clinical_context",    # route × indication composite
]

HUMANIZED_INTER = [
    "feat_effective_burden",    # burden × (1-immuno_suppression)
    "feat_vz_x_origin",        # Vernier × origin (always =vz for humanized)
    "feat_fc_x_format",        # Fc × format interaction
    "feat_hl_inv",             # 1/half-life
]

# For FULLY HUMAN: molecular features are weak (all have human frameworks)
# Clinical context dominates
FULLHUMAN_MOL = [
    "feat_n_strong_binders",
    "feat_net_burden",
    "feat_n_clusters",
    "feat_cdrh3_len",
    "feat_cdrh3_aromaticity",
    "feat_cdr_deamidation",
    "feat_total_cdr_length",
    "feat_vh_identity",         # still varies even in fully human
    "feat_cmc_agg",
    "feat_cmc_pI",
]

FULLHUMAN_CLIN = [
    "feat_immuno_suppression",
    "feat_dosing_freq",
    "feat_clinical_context",
    "feat_half_life",
    "feat_isotype_immuno",
    "feat_immune_depleting",
]


def run_corr_table(df, feats, label):
    """Compute Spearman correlations for a feature set within a subgroup."""
    print(f"\n--- {label} (n={len(df)}) ---")
    rows = []
    for fc in feats:
        if fc not in df.columns:
            continue
        sub = df[[target, fc]].dropna()
        if len(sub) < 5:
            continue
        r, p = spearmanr(sub[target], sub[fc])
        rows.append({"feature": fc.replace("feat_", ""), "r": r, "p": p, "n": len(sub)})
    if not rows:
        print("  (No valid features to correlate)")
        return pd.DataFrame(columns=["feature", "r", "p", "n"])
    cr = pd.DataFrame(rows).sort_values("r", key=abs, ascending=False)
    for _, row in cr.iterrows():
        if np.isnan(row["r"]):
            print(f"  {row['feature']:30s}: r=NaN (constant feature)")
            continue
        star = "**" if row["p"] < 0.01 else ("*" if row["p"] < 0.05 else
               ("^" if row["p"] < 0.10 else " "))
        bar_len = int(abs(row["r"]) * 25)
        bar = ("+" if row["r"] > 0 else "-") * bar_len
        print(f"  {row['feature']:30s}: r={row['r']:+.3f}{star} [{bar:<25s}] n={int(row['n'])}")
    return cr


def run_loo_models(df, feat_configs, label):
    """Run LOO Ridge + GBR for multiple feature sets."""
    print(f"\n{'='*78}")
    print(f"LOO MODELS: {label} (n={len(df)})")
    print(f"{'='*78}")
    loo = LeaveOneOut()
    results = []

    for mod_name, feats in feat_configs.items():
        feats = [f for f in feats if f in df.columns]
        sub = df[[target] + feats].dropna()
        if len(sub) < 10:
            print(f"  [{mod_name}]: skip (n={len(sub)} < 10)")
            continue
        X, y = sub[feats].values, sub[target].values

        # Ridge
        preds_r = np.zeros(len(y))
        for tr, te in loo.split(X):
            sc = StandardScaler()
            Xtr, Xte = sc.fit_transform(X[tr]), sc.transform(X[te])
            md = RidgeCV(alphas=[0.001, 0.01, 0.1, 1, 5, 10, 50, 100, 200])
            md.fit(Xtr, y[tr])
            preds_r[te] = md.predict(Xte)
        r_ridge, p_ridge = spearmanr(y, preds_r)

        # GBR with mini grid search
        best_sp_gbr = -99
        preds_g = np.zeros(len(y))
        for n_est in [50, 80]:
            for lr in [0.03, 0.06]:
                for md in [2, 3]:
                    p2 = np.zeros(len(y))
                    for tr, te in loo.split(X):
                        gb = GradientBoostingRegressor(
                            n_estimators=n_est, max_depth=md, learning_rate=lr,
                            subsample=0.8, random_state=42, min_samples_leaf=2)
                        gb.fit(X[tr], y[tr])
                        p2[te] = gb.predict(X[te])
                    rr, _ = spearmanr(y, p2)
                    if rr > best_sp_gbr:
                        best_sp_gbr = rr
                        preds_g = p2.copy()
        r_gbr, p_gbr = spearmanr(y, preds_g)

        star_r = "**" if p_ridge < 0.01 else ("*" if p_ridge < 0.05 else
                 ("^" if p_ridge < 0.10 else " "))
        star_g = "**" if p_gbr < 0.01 else ("*" if p_gbr < 0.05 else
                 ("^" if p_gbr < 0.10 else " "))
        print(f"  [{mod_name:40s}] n={len(sub):2d} k={len(feats):2d}"
              f"  Ridge r={r_ridge:+.3f}{star_r}  GBR r={r_gbr:+.3f}{star_g}")
        results.append({
            "model": mod_name, "n": len(sub), "k": len(feats),
            "ridge_r": r_ridge, "ridge_p": p_ridge,
            "gbr_r": r_gbr, "gbr_p": p_gbr,
            "y": y, "preds_ridge": preds_r, "preds_gbr": preds_g,
            "sub": sub,
        })
    return results


# ============================================================
# HUMANIZED GROUP ANALYSIS
# ============================================================
print("\n" + "=" * 78)
print("HUMANIZED GROUP ()")
print("=" * 78)
print(f"\nTop/Bottom 5:")
for _, r in hu.nlargest(5, target)[["antibody_name", target, "route",
    "disease_class", "target"]].iterrows():
    print(f"  HIGH: {r['antibody_name']:18s} ADA={r[target]:5.1f}%  "
          f"{r['route']:3s}  {r['disease_class']:15s}  {str(r['target'])[:25]}")
for _, r in hu.nsmallest(5, target)[["antibody_name", target, "route",
    "disease_class", "target"]].iterrows():
    print(f"  LOW:  {r['antibody_name']:18s} ADA={r[target]:5.1f}%  "
          f"{r['route']:3s}  {r['disease_class']:15s}  {str(r['target'])[:25]}")

cr_hu_mol = run_corr_table(hu, HUMANIZED_MOL, "HUMANIZED – Molecular features")
cr_hu_clin = run_corr_table(hu, HUMANIZED_CLIN, "HUMANIZED – Clinical features")
cr_hu_inter = run_corr_table(hu, HUMANIZED_INTER, "HUMANIZED – Interaction features")

hu_models = run_loo_models(hu, {
    "Mol only": HUMANIZED_MOL,
    "Clin only": HUMANIZED_CLIN,
    "Mol + Clin": HUMANIZED_MOL + HUMANIZED_CLIN,
    "Mol + Clin + Inter": HUMANIZED_MOL + HUMANIZED_CLIN + HUMANIZED_INTER,
}, "HUMANIZED")

all_hu_feats = HUMANIZED_MOL + HUMANIZED_CLIN + HUMANIZED_INTER
cr_hu_all = run_corr_table(hu, all_hu_feats, "HUMANIZED – All features ranked")
top6_hu = ["feat_" + row["feature"] for _, row in cr_hu_all.head(6).iterrows()]
print(f"\nTop-6 features for humanized: {[f.replace('feat_','') for f in top6_hu]}")
hu_top6_results = run_loo_models(hu, {"Top-6 humanized": top6_hu}, "HUMANIZED Top-6")

# ============================================================
# FULLY HUMAN GROUP ANALYSIS
# ============================================================
print("\n" + "=" * 78)
print("FULLY HUMAN GROUP ()")
print("=" * 78)
print(f"\nTop/Bottom 5:")
for _, r in fu.nlargest(5, target)[["antibody_name", target, "route",
    "disease_class", "target"]].iterrows():
    print(f"  HIGH: {r['antibody_name']:18s} ADA={r[target]:5.1f}%  "
          f"{r['route']:3s}  {r['disease_class']:15s}  {str(r['target'])[:25]}")
for _, r in fu.nsmallest(5, target)[["antibody_name", target, "route",
    "disease_class", "target"]].iterrows():
    print(f"  LOW:  {r['antibody_name']:18s} ADA={r[target]:5.1f}%  "
          f"{r['route']:3s}  {r['disease_class']:15s}  {str(r['target'])[:25]}")

cr_fu_mol = run_corr_table(fu, FULLHUMAN_MOL, "FULLY HUMAN – Molecular features")
cr_fu_clin = run_corr_table(fu, FULLHUMAN_CLIN, "FULLY HUMAN – Clinical features")

fu_models = run_loo_models(fu, {
    "Mol only": FULLHUMAN_MOL,
    "Clin only": FULLHUMAN_CLIN,
    "Mol + Clin": FULLHUMAN_MOL + FULLHUMAN_CLIN,
}, "FULLY HUMAN")

all_fu_feats = FULLHUMAN_MOL + FULLHUMAN_CLIN
cr_fu_all = run_corr_table(fu, all_fu_feats, "FULLY HUMAN – All features ranked")
top6_fu = ["feat_" + row["feature"] for _, row in cr_fu_all.head(6).iterrows()]
print(f"\nTop-6 features for fully human: {[f.replace('feat_','') for f in top6_fu]}")
fu_top6_results = run_loo_models(fu, {"Top-6 fully human": top6_fu}, "FULLY HUMAN Top-6")

# ============================================================
# HUMANIZED subgroup: exclude 3 mechanism-driven outliers
# ============================================================
print("\n" + "=" * 78)
print("HUMANIZED (excluding Donanemab/Alemtuzumab/Brolucizumab)")
print("=" * 78)
hu_clean = hu[~hu["antibody_name"].isin(
    ["Donanemab", "Alemtuzumab", "Brolucizumab"])].copy()
print(f"n={len(hu_clean)}, ADA range: {hu_clean[target].min():.1f}–"
      f"{hu_clean[target].max():.1f}%  mean={hu_clean[target].mean():.1f}%")

cr_huc = run_corr_table(hu_clean, all_hu_feats,
                         "HUMANIZED clean – All features ranked")
top6_huc = ["feat_" + row["feature"] for _, row in cr_huc.head(6).iterrows()]
print(f"\nTop-6 clean: {[f.replace('feat_','') for f in top6_huc]}")

huc_models = run_loo_models(hu_clean, {
    "Mol only (clean)": HUMANIZED_MOL,
    "Clin only (clean)": HUMANIZED_CLIN,
    "Mol+Clin (clean)": HUMANIZED_MOL + HUMANIZED_CLIN,
    "Top-6 (clean)": top6_huc,
}, "HUMANIZED clean")

# ============================================================
# MINIMAL MODELS (3-4 features per group, anti-overfitting)
# ============================================================
from scipy.optimize import differential_evolution

print("\n" + "=" * 78)
print("MINIMAL MODELS — 3-4 features per group (anti-overfitting)")
print("=" * 78)


def prep_matrix(df, feat_list):
    cols = []
    for f in feat_list:
        v = df[f].values.copy().astype(float)
        med = np.nanmedian(v) if np.any(~np.isnan(v)) else 0.0
        v = np.where(np.isnan(v), med, v)
        cols.append(v)
    return df[target].values, np.column_stack(cols)


def neg_spearman_l2(weights, y_arr, X_mat, lam):
    s = X_mat @ np.array(weights)
    r, _ = spearmanr(y_arr, s)
    penalty = lam * np.sum(np.array(weights) ** 2)
    return (-r if not np.isnan(r) else 0.0) + penalty


def loo_opt(y, X, bounds, lam=0.0):
    n = len(y)
    preds = np.zeros(n)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        res = differential_evolution(neg_spearman_l2, bounds,
                                     args=(y[mask], X[mask], lam),
                                     seed=42, maxiter=200, tol=1e-5)
        preds[i] = X[i] @ res.x
    r, p = spearmanr(y, preds)
    return r, p


def run_minimal(label, df, feats, bounds, lam_values):
    y, X = prep_matrix(df, feats)
    feat_names = [f.replace("feat_", "") for f in feats]
    print(f"\n--- {label} (n={len(df)}, k={len(feats)}: {feat_names}) ---")

    for lam in lam_values:
        res = differential_evolution(neg_spearman_l2, bounds,
                                     args=(y, X, lam),
                                     seed=42, maxiter=300, tol=1e-6)
        score = X @ res.x
        r_fit, p_fit = spearmanr(y, score)
        r_loo, p_loo = loo_opt(y, X, bounds, lam)
        s_fit = "**" if p_fit < 0.01 else ("*" if p_fit < 0.05 else "")
        s_loo = "**" if p_loo < 0.01 else ("*" if p_loo < 0.05 else
                ("^" if p_loo < 0.10 else " "))
        print(f"  λ={lam:.3f}  fit r={r_fit:+.3f}{s_fit}  LOO r={r_loo:+.3f}{s_loo}")
        if lam == lam_values[0]:
            print(f"    Weights: ", end="")
            for fn, w in zip(feat_names, res.x):
                if abs(w) > 0.001:
                    print(f"{fn}={w:+.2f}  ", end="")
            print()
    return y, X


# ── HUMANIZED MINIMAL: top 4 by |r| ─────────────────────────────────────
HU_MIN = [
    "feat_immuno_suppression",   # r=-0.408
    "feat_cdrh3_aromaticity",    # r=-0.324
    "feat_immune_depleting",     # r=+0.249
    "feat_half_life",            # r=-0.348
]
HU_MIN_B = [(-15, 0), (-60, 0), (0, 25), (-5, 0)]

y_hu, X_hu = run_minimal("HUMANIZED minimal-4", hu, HU_MIN, HU_MIN_B,
                          [0.0, 0.001, 0.005, 0.01, 0.05])

# ── HUMANIZED MINIMAL-3: drop immune_depleting ───────────────────────────
HU_M3 = ["feat_immuno_suppression", "feat_cdrh3_aromaticity", "feat_half_life"]
HU_M3_B = [(-15, 0), (-60, 0), (-5, 0)]
run_minimal("HUMANIZED minimal-3", hu, HU_M3, HU_M3_B,
            [0.0, 0.001, 0.005, 0.01])

# ── HUMANIZED: top 6 ────────────────────────────────────────────────────
HU_6 = [
    "feat_immuno_suppression", "feat_cdrh3_aromaticity",
    "feat_immune_depleting", "feat_half_life",
    "feat_vh_family_score", "feat_cdrh3_len",
]
HU_6_B = [(-15, 0), (-60, 0), (0, 25), (-5, 0), (-15, 0), (-5, 0)]
run_minimal("HUMANIZED top-6", hu, HU_6, HU_6_B,
            [0.0, 0.005, 0.01, 0.05])

# ── FULLY HUMAN MINIMAL: top 3 by |r| ───────────────────────────────────
FU_MIN = [
    "feat_n_clusters",           # r=+0.444
    "feat_net_burden",           # r=+0.371
    "feat_n_strong_binders",     # r=+0.355
]
FU_MIN_B = [(0, 8), (0, 5), (0, 0.5)]

y_fu, X_fu = run_minimal("FULLY HUMAN minimal-3", fu, FU_MIN, FU_MIN_B,
                          [0.0, 0.001, 0.005, 0.01, 0.05])

# ── FULLY HUMAN: top 3 mol + top 2 clin ─────────────────────────────────
FU_5 = [
    "feat_n_clusters", "feat_net_burden", "feat_n_strong_binders",
    "feat_dosing_freq", "feat_vh_identity",
]
FU_5_B = [(0, 8), (0, 5), (0, 0.5), (0, 12), (-3, 0)]
run_minimal("FULLY HUMAN top-5", fu, FU_5, FU_5_B,
            [0.0, 0.005, 0.01, 0.05])

# ── FULLY HUMAN: top 4 mol only ─────────────────────────────────────────
FU_4 = [
    "feat_n_clusters", "feat_net_burden",
    "feat_n_strong_binders", "feat_vh_identity",
]
FU_4_B = [(0, 8), (0, 5), (0, 0.5), (-3, 0)]
run_minimal("FULLY HUMAN mol-4", fu, FU_4, FU_4_B,
            [0.0, 0.001, 0.005, 0.01])

# ============================================================
# BEST STRATIFIED COMBINATION
# ============================================================
print("\n" + "=" * 78)
print("BEST STRATIFIED COMBINATION")
print("=" * 78)

best_lam_hu, best_lam_fu = 0.005, 0.001
res_hu = differential_evolution(neg_spearman_l2, HU_MIN_B,
                                args=(y_hu, X_hu, best_lam_hu),
                                seed=42, maxiter=300, tol=1e-6)
hu["score_hu"] = X_hu @ res_hu.x

y_fu2, X_fu2 = prep_matrix(fu, FU_MIN)
res_fu = differential_evolution(neg_spearman_l2, FU_MIN_B,
                                args=(y_fu2, X_fu2, best_lam_fu),
                                seed=42, maxiter=300, tol=1e-6)
fu["score_fu"] = X_fu2 @ res_fu.x

hu_norm = (hu["score_hu"] - hu["score_hu"].mean()) / hu["score_hu"].std()
fu_norm = (fu["score_fu"] - fu["score_fu"].mean()) / fu["score_fu"].std()
all_preds = []
for i, (_, row) in enumerate(hu.iterrows()):
    all_preds.append({"antibody_name": row["antibody_name"],
                      "actual": row[target], "predicted": hu_norm.iloc[i],
                      "group": "humanized"})
for i, (_, row) in enumerate(fu.iterrows()):
    all_preds.append({"antibody_name": row["antibody_name"],
                      "actual": row[target], "predicted": fu_norm.iloc[i],
                      "group": "fully_human"})
ap = pd.DataFrame(all_preds)
r_strat, p_strat = spearmanr(ap["actual"], ap["predicted"])
star = "**" if p_strat < 0.01 else ("*" if p_strat < 0.05 else "")
print(f"  STRATIFIED combined (fitted):     r={r_strat:+.3f}{star}  p={p_strat:.6f}  n={len(ap)}")

if "score_combined" in m.columns:
    r_global, p_global = spearmanr(m[target], m["score_combined"])
    print(f"  Global baseline (all 70):         r={r_global:+.3f}   p={p_global:.4f}")

print("\nDone.")
