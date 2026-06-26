"""
immunogenicity_sprint_v2.py
=================================
Sprint v2: deeper feature interactions + model tuning + outlier analysis
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr, pearsonr
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
print(f"N={len(m)}")

# ============================================================
# INTERACTION FEATURES
# ============================================================

# 1. Origin × clinical context
m["feat_origin_x_context"] = m["feat_origin_code"] * m["feat_clinical_context"]

# 2. Origin × dosing frequency (humanized + frequent SC = high risk)
m["feat_origin_x_freq"] = m["feat_origin_code"] * m["feat_dosing_freq"]

# 3. Molecular burden × (1 - immunosuppression) → "effective immunogenic load"
m["feat_effective_burden"] = m["feat_net_burden"] * (1 - m["feat_immuno_suppression"] * 0.7)

# 4. Fc tolerogenic × format
m["feat_fc_x_format"] = m["feat_fc_tolerogenic"] * (2 - m["feat_format"])  

# 5. Vernier foreignness × origin (only relevant for humanized)
m["feat_vz_x_origin"] = m["feat_vz_foreignness"] * m["feat_origin_code"]

# 6. Immune depleting × (1 - immuno_suppression)
m["feat_depl_net"] = m["feat_immune_depleting"] * (1 - m["feat_immuno_suppression"])

# 7. CDR-H3 len × origin (only matters for humanized)
m["feat_cdrh3_x_origin"] = m["feat_cdrh3_len"] * m["feat_origin_code"]

# 8. Strong binders × (1 - immuno_suppression)
m["feat_binders_net"] = m["feat_n_strong_binders"] * (1 - m["feat_immuno_suppression"])

# 9. Half-life inverse (shorter = more immunogenic for fragments)
hl = m["feat_half_life"].fillna(m["feat_half_life"].median())
m["feat_hl_inv"] = 1.0 / (hl.clip(lower=1))

# 10. Anti-TNF × origin (anti-TNF humanized vs fully human)
m["feat_tnf_x_origin"] = m["feat_anti_tnf"] * m["feat_origin_code"]

# ============================================================
# CURATED COMPOSITE SCORES
# ============================================================

# Intrinsic molecular risk score (hand-crafted from domain knowledge)
m["score_molecular"] = (
    m["feat_origin_code"] * 10 +
    m["feat_vz_foreignness"] * 0.3 +
    m["feat_n_strong_binders"] * 0.05 +
    m["feat_net_burden"] * 2.0 +
    m["feat_n_clusters"] * 0.5 +
    (100 - m["feat_vh_identity"].fillna(85)) * 0.3
)

# Clinical risk modifier
m["score_clinical_risk"] = (
    m["feat_dosing_freq"] * 3 +
    m["feat_immune_depleting"] * 8 +
    (1 - m["feat_fc_tolerogenic"]) * 3 +
    (1 - m["feat_immuno_suppression"]) * 2 +
    m["feat_format"] * 1.5
)

# Combined predicted ADA score
m["score_combined"] = m["score_molecular"] * 0.4 + m["score_clinical_risk"] * 0.6

# Check correlation of hand-crafted scores
target = "ada_rate_pct"
for sc in ["score_molecular","score_clinical_risk","score_combined"]:
    r, p = spearmanr(m[target], m[sc])
    star = "**" if p<0.01 else ("*" if p<0.05 else "")
    print(f"  {sc:30s}: r={r:+.3f}{star} p={p:.4f}")

# ============================================================
# FULL CORRELATION TABLE (ALL features including interactions)
# ============================================================
ALL_FEAT = sorted([c for c in m.columns if c.startswith("feat_")])
print(f"\n{'='*80}")
print(f"ALL {len(ALL_FEAT)} FEATURES – Top 20 by |r|")
print(f"{'='*80}")
rows = []
for fc in ALL_FEAT:
    sub = m[[target, fc]].dropna()
    if len(sub) < 10: continue
    r, p = spearmanr(sub[target], sub[fc])
    rows.append({"feature": fc.replace("feat_",""), "r": r, "p": p, "n": len(sub)})
cr = pd.DataFrame(rows).sort_values("r", key=abs, ascending=False)
for _, row in cr.head(20).iterrows():
    star = "**" if row["p"]<0.01 else ("*" if row["p"]<0.05 else ("^" if row["p"]<0.10 else " "))
    print(f"  {row['feature']:35s}: r={row['r']:+.3f}{star}  p={row['p']:.4f}  n={int(row['n'])}")

# ============================================================
# MODEL SUITE
# ============================================================
print(f"\n{'='*80}")
print("LOO MODEL SUITE")
print(f"{'='*80}")

FEAT_SETS = {
    "Ridge: interactions (10)": [
        "feat_origin_x_freq","feat_effective_burden","feat_depl_net",
        "feat_vz_x_origin","feat_fc_x_format","feat_hl_inv",
        "feat_binders_net","feat_tnf_x_origin","feat_cdrh3_x_origin",
        "feat_origin_x_context",
    ],
    "Ridge: top-12 raw": [r["feature"] for _,r in cr.head(12).iterrows()],
    "GBR: full combined (25)": [
        "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
        "feat_net_burden","feat_vh_identity","feat_cdrh3_aromaticity",
        "feat_cdrh3_len","feat_n_clusters","feat_assay_gen","feat_fc_tolerogenic",
        "feat_mtx_suppression","feat_immuno_suppression","feat_dosing_freq",
        "feat_clinical_context","feat_immune_depleting","feat_half_life",
        "feat_origin_x_freq","feat_effective_burden","feat_depl_net",
        "feat_vz_x_origin","feat_fc_x_format","feat_hl_inv",
        "feat_binders_net","feat_anti_tnf","feat_cdr_deamidation",
    ],
    "GBR: top-12": [r["feature"] for _,r in cr.head(12).iterrows()],
    "GBR: curated-8": [
        "feat_origin_code","feat_immune_depleting","feat_immuno_suppression",
        "feat_dosing_freq","feat_vz_foreignness","feat_fc_tolerogenic",
        "feat_half_life","feat_n_strong_binders",
    ],
    "GBR: interactions+mol (15)": [
        "feat_origin_x_freq","feat_effective_burden","feat_depl_net",
        "feat_vz_x_origin","feat_fc_x_format","feat_hl_inv",
        "feat_binders_net","feat_tnf_x_origin",
        "feat_origin_code","feat_vh_identity","feat_n_clusters",
        "feat_cdrh3_len","feat_immune_depleting","feat_half_life",
        "feat_dosing_freq",
    ],
}

loo = LeaveOneOut()
results = []

for mod_name, feat_list in FEAT_SETS.items():
    feats = ["feat_" + f if not f.startswith("feat_") else f for f in feat_list]
    feats = [f for f in feats if f in m.columns]
    sub   = m[[target] + feats].dropna()
    X, y  = sub[feats].values, sub[target].values
    
    preds = np.zeros(len(y))
    
    if "GBR" in mod_name:
        for n_est in [60]:
            for lr in [0.05]:
                for md in [2]:
                    p2 = np.zeros(len(y))
                    for tr, te in loo.split(X):
                        gb = GradientBoostingRegressor(
                            n_estimators=n_est, max_depth=md,
                            learning_rate=lr, subsample=0.8, random_state=42,
                            min_samples_leaf=3)
                        gb.fit(X[tr], y[tr])
                        p2[te] = gb.predict(X[te])
                    r2, _ = spearmanr(y, p2)
                    if r2 > spearmanr(y, preds)[0]:
                        preds = p2.copy()
    else:
        for tr, te in loo.split(X):
            sc = StandardScaler()
            Xtr, Xte = sc.fit_transform(X[tr]), sc.transform(X[te])
            md = RidgeCV(alphas=[0.001,0.01,0.1,1,5,10,50,100,200,500])
            md.fit(Xtr, y[tr])
            preds[te] = md.predict(Xte)
    
    r_sp, p_sp = spearmanr(y, preds)
    star = "**" if p_sp<0.01 else ("*" if p_sp<0.05 else ("^" if p_sp<0.10 else " "))
    results.append((mod_name, r_sp, p_sp, len(sub), len(feats)))
    print(f"  [{mod_name:45s}] n={len(sub):2d} k={len(feats):2d}  r={r_sp:+.3f}{star}  p={p_sp:.4f}")

# ============================================================
# OUTLIER ANALYSIS: what if we exclude extreme mechanism-driven outliers?
# ============================================================
print(f"\n{'='*80}")
print("SENSITIVITY: Excluding extreme outliers")
print(f"{'='*80}")

# Donanemab (90%) - unique amyloid mechanism
# Alemtuzumab (85%) - immune reconstitution
# Brolucizumab (52%) - intravitreal scFv
EXCLUDE = ["Donanemab","Alemtuzumab","Brolucizumab"]
m_clean = m[~m["antibody_name"].isin(EXCLUDE)].copy()
print(f"After excluding {EXCLUDE}: n={len(m_clean)}, ADA range: {m_clean[target].min():.1f}–{m_clean[target].max():.1f}%")

for mod_name, feat_list in [
    ("GBR curated-8 (no outliers)", [
        "feat_origin_code","feat_immune_depleting","feat_immuno_suppression",
        "feat_dosing_freq","feat_vz_foreignness","feat_fc_tolerogenic",
        "feat_half_life","feat_n_strong_binders",
    ]),
    ("GBR interactions+mol (no outliers)", [
        "feat_origin_x_freq","feat_effective_burden","feat_depl_net",
        "feat_vz_x_origin","feat_fc_x_format","feat_hl_inv",
        "feat_binders_net","feat_tnf_x_origin",
        "feat_origin_code","feat_vh_identity","feat_n_clusters",
        "feat_cdrh3_len","feat_immune_depleting","feat_half_life",
        "feat_dosing_freq",
    ]),
    ("GBR full 25 (no outliers)", [
        "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
        "feat_net_burden","feat_vh_identity","feat_cdrh3_aromaticity",
        "feat_cdrh3_len","feat_n_clusters","feat_assay_gen","feat_fc_tolerogenic",
        "feat_mtx_suppression","feat_immuno_suppression","feat_dosing_freq",
        "feat_clinical_context","feat_immune_depleting","feat_half_life",
        "feat_origin_x_freq","feat_effective_burden","feat_depl_net",
        "feat_vz_x_origin","feat_fc_x_format","feat_hl_inv",
        "feat_binders_net","feat_anti_tnf","feat_cdr_deamidation",
    ]),
]:
    feats = [f for f in feat_list if f in m_clean.columns]
    sub = m_clean[[target]+feats].dropna()
    X, y = sub[feats].values, sub[target].values
    preds = np.zeros(len(y))
    best_sp = -99
    for n_est in [60]:
        for lr in [0.05]:
            for md in [2]:
                p2 = np.zeros(len(y))
                for tr, te in LeaveOneOut().split(X):
                    gb = GradientBoostingRegressor(
                        n_estimators=n_est, max_depth=md,
                        learning_rate=lr, subsample=0.8, random_state=42,
                        min_samples_leaf=3)
                    gb.fit(X[tr], y[tr])
                    p2[te] = gb.predict(X[te])
                r2, _ = spearmanr(y, p2)
                if r2 > best_sp:
                    best_sp = r2
                    preds = p2.copy()
    r_sp, p_sp = spearmanr(y, preds)
    star = "**" if p_sp<0.01 else ("*" if p_sp<0.05 else "")
    print(f"  [{mod_name:45s}] n={len(sub):2d}  r={r_sp:+.3f}{star}  p={p_sp:.4f}")

# ============================================================
# FEATURE IMPORTANCE (GBR)
# ============================================================
print(f"\n{'='*80}")
print("GBR FEATURE IMPORTANCE (best model)")
print(f"{'='*80}")
feats = [f for f in [
    "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
    "feat_net_burden","feat_vh_identity","feat_cdrh3_aromaticity",
    "feat_cdrh3_len","feat_n_clusters","feat_assay_gen","feat_fc_tolerogenic",
    "feat_mtx_suppression","feat_immuno_suppression","feat_dosing_freq",
    "feat_clinical_context","feat_immune_depleting","feat_half_life",
    "feat_origin_x_freq","feat_effective_burden","feat_depl_net",
    "feat_vz_x_origin","feat_fc_x_format","feat_hl_inv",
    "feat_binders_net","feat_anti_tnf","feat_cdr_deamidation",
] if f in m.columns]
sub = m[[target]+feats].dropna()
X, y = sub[feats].values, sub[target].values
gb = GradientBoostingRegressor(n_estimators=80, max_depth=2, learning_rate=0.05,
                                subsample=0.8, random_state=42, min_samples_leaf=3)
gb.fit(X, y)
imp = sorted(zip([f.replace("feat_","") for f in feats], gb.feature_importances_),
             key=lambda x: x[1], reverse=True)
for f, i in imp[:15]:
    bar = "#" * int(i / max(x[1] for x in imp) * 30)
    print(f"  {f:35s}: {i:.4f} [{bar}]")

m.to_csv(OUT / "immuno70_sprint_matrix.csv", index=False)
print(f"\nDone. Matrix: {len(m)} × {len(m.columns)}")
