"""
immunogenicity_minimal_refit.py
Minimal models (3-5 features per group) with L2 regularization + LOO validation.
Uses the new 13-factor features including cdr_oxidation, cdr_hydrophobicity, etc.
"""
import pandas as pd, numpy as np
from scipy.stats import spearmanr
from scipy.optimize import differential_evolution

ROOT = "d:/InSynBio-AI-Research/Antibody_Engineer_Suite"
m = pd.read_csv(f"{ROOT}/data/thera_sabdab/out/immuno70_sprint_matrix.csv")
m = m.drop_duplicates("antibody_name").copy()
target = "ada_rate_pct"

hu = m[m["origin"] == "humanized"].copy()
fu = m[m["origin"] == "fully_human"].copy()
print(f"Humanized: n={len(hu)}  Fully human: n={len(fu)}")


def prep(df, feats):
    cols = []
    for f in feats:
        v = df[f].values.copy().astype(float)
        med = np.nanmedian(v) if np.any(~np.isnan(v)) else 0.0
        v = np.where(np.isnan(v), med, v)
        cols.append(v)
    return df[target].values, np.column_stack(cols)


def obj(w, y, X, lam):
    s = X @ np.array(w)
    r, _ = spearmanr(y, s)
    return (-r if not np.isnan(r) else 0.0) + lam * np.sum(np.array(w)**2)


def fit_and_loo(label, df, feats, bounds, lam_list):
    y, X = prep(df, feats)
    names = [f.replace("feat_", "") for f in feats]
    print(f"\n{'='*78}")
    print(f"{label} (n={len(df)}, k={len(feats)})")
    print(f"  Features: {names}")
    print(f"{'='*78}")

    best_loo_r, best_lam, best_w = -99, 0, None

    for lam in lam_list:
        res = differential_evolution(obj, bounds, args=(y, X, lam),
                                     seed=42, maxiter=300, tol=1e-6)
        r_fit, _ = spearmanr(y, X @ res.x)

        n = len(y)
        preds = np.zeros(n)
        for i in range(n):
            mask = np.ones(n, dtype=bool)
            mask[i] = False
            ri = differential_evolution(obj, bounds, args=(y[mask], X[mask], lam),
                                        seed=42, maxiter=200, tol=1e-5)
            preds[i] = X[i] @ ri.x
        r_loo, p_loo = spearmanr(y, preds)

        sf = "**" if r_fit > 0 and spearmanr(y, X @ res.x)[1] < 0.01 else (
             "*" if spearmanr(y, X @ res.x)[1] < 0.05 else "")
        sl = "**" if p_loo < 0.01 else ("*" if p_loo < 0.05 else (
             "^" if p_loo < 0.10 else " "))
        print(f"  lam={lam:.4f}  fit={r_fit:+.3f}{sf}  LOO={r_loo:+.3f}{sl}  p_loo={p_loo:.4f}")

        if r_loo > best_loo_r:
            best_loo_r, best_lam, best_w = r_loo, lam, res.x.copy()

    print(f"\n  BEST LOO: r={best_loo_r:+.3f}  (lam={best_lam})")
    print(f"  Weights:")
    for fn, w in zip(names, best_w):
        print(f"    {fn:30s}: {w:+.4f}")
    return y, X, best_w, best_loo_r


# ============================================================
# HUMANIZED MODELS
# ============================================================

# HU-A: Top 4 (previous best LOO=0.391)
fit_and_loo("HU-A: immuno_sup + cdrh3_arom + immune_depl + half_life",
    hu,
    ["feat_immuno_suppression", "feat_cdrh3_aromaticity",
     "feat_immune_depleting", "feat_half_life"],
    [(-15, 0), (-60, 0), (0, 25), (-5, 0)],
    [0.0, 0.001, 0.005])

# HU-B: Replace immune_depleting with fc_glycan
fit_and_loo("HU-B: immuno_sup + cdrh3_arom + fc_glycan + half_life",
    hu,
    ["feat_immuno_suppression", "feat_cdrh3_aromaticity",
     "feat_fc_glycan", "feat_half_life"],
    [(-15, 0), (-60, 0), (-15, 0), (-5, 0)],
    [0.0, 0.001, 0.005])

# HU-C: Add sc_x_origin (route x origin interaction)
fit_and_loo("HU-C: immuno_sup + cdrh3_arom + immune_depl + half_life + sc_x_origin",
    hu,
    ["feat_immuno_suppression", "feat_cdrh3_aromaticity",
     "feat_immune_depleting", "feat_half_life", "feat_sc_x_origin"],
    [(-15, 0), (-60, 0), (0, 25), (-5, 0), (-5, 15)],
    [0.0, 0.001, 0.005])

# ============================================================
# FULLY HUMAN MODELS  (previous best LOO=0.153 with 3 features)
# ============================================================

# FH-A: Original top 3
fit_and_loo("FH-A: n_clusters + net_burden + n_strong_binders",
    fu,
    ["feat_n_clusters", "feat_net_burden", "feat_n_strong_binders"],
    [(0, 8), (0, 5), (0, 0.5)],
    [0.0, 0.001, 0.005])

# FH-B: Replace n_strong_binders with cdr_oxidation (r=-0.396)
fit_and_loo("FH-B: n_clusters + net_burden + cdr_oxidation",
    fu,
    ["feat_n_clusters", "feat_net_burden", "feat_cdr_oxidation"],
    [(0, 8), (0, 5), (-5, 0)],
    [0.0, 0.001, 0.005])

# FH-C: Add vz_foreignness (r=+0.375 in FH)
fit_and_loo("FH-C: n_clusters + net_burden + cdr_oxidation + vz_foreignness",
    fu,
    ["feat_n_clusters", "feat_net_burden", "feat_cdr_oxidation", "feat_vz_foreignness"],
    [(0, 8), (0, 5), (-5, 0), (0, 3)],
    [0.0, 0.001, 0.005])

# FH-D: Add surf_frac_vl (r=-0.409 in FH, but only n=65)
fu_struct = fu[fu["feat_surf_frac_vl"].notna()].copy()
if len(fu_struct) >= 15:
    fit_and_loo("FH-D: n_clusters + cdr_oxidation + surf_frac_vl (struct only)",
        fu_struct,
        ["feat_n_clusters", "feat_cdr_oxidation", "feat_surf_frac_vl"],
        [(0, 8), (-5, 0), (-20, 0)],
        [0.0, 0.001, 0.005])

# FH-E: Top 5 new mix
fit_and_loo("FH-E: n_clusters + cdr_oxidation + vz_foreignness + cdr_hydrophobicity + dosing_freq",
    fu,
    ["feat_n_clusters", "feat_cdr_oxidation", "feat_vz_foreignness",
     "feat_cdr_hydrophobicity", "feat_dosing_freq"],
    [(0, 8), (-5, 0), (0, 3), (0, 30), (0, 12)],
    [0.0, 0.001, 0.005])

# FH-F: Purely molecular 4 features
fit_and_loo("FH-F: n_clusters + cdr_oxidation + cdr_hydrophobicity + vh_identity",
    fu,
    ["feat_n_clusters", "feat_cdr_oxidation", "feat_cdr_hydrophobicity", "feat_vh_identity"],
    [(0, 8), (-5, 0), (0, 30), (-3, 0)],
    [0.0, 0.001, 0.005])

print("\n" + "=" * 78)
print("Done.")
