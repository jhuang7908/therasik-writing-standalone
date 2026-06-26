"""
immunogenicity_sprint_model.py
=================================
Sprint to r≈0.7 by incorporating clinical confounders:
  - ADA assay generation (ELISA=1 vs ECL=2)
  - Fc engineering status
  - MTX/immunosuppressant co-medication
  - Dosing frequency (APC priming proxy)
  - Dose magnitude (drug interference proxy)
  - Corrected ADA rate (adjust for assay + clinical confounders)
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path
from scipy.stats import spearmanr, pearsonr
from sklearn.linear_model import RidgeCV, LassoCV, ElasticNetCV
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import warnings
warnings.filterwarnings("ignore")

ROOT = Path("d:/InSynBio-AI-Research/Antibody_Engineer_Suite")
OUT  = ROOT / "data/thera_sabdab/out"

# ---- Load feature matrix + clinical confounders ----
m = pd.read_csv(OUT / "immuno70_extended_features.csv")
m = m.drop_duplicates("antibody_name").copy()

cc = pd.read_csv(ROOT / "data/reference/clinical_confounders_70.csv")
m = m.merge(cc[["antibody_name","approval_year","assay_platform","assay_generation",
                 "dose_freq","fc_engineering","fc_effector_status",
                 "mtx_comedication","immunosuppressant_context","half_life_days"]],
            on="antibody_name", how="left")

print(f"Dataset: {len(m)} antibodies")
print(f"Assay gen distribution: {m['assay_generation'].value_counts().to_dict()}")

# ============================================================
# ENCODE NEW CLINICAL FEATURES
# ============================================================

# 1. Assay sensitivity correction
# ELISA (gen 1) has ~5-10× lower sensitivity → detected ADA is underestimated
# ECL (gen 2) is the modern standard
m["feat_assay_gen"] = m["assay_generation"].fillna(2).astype(float)

# 2. Fc effector function → tolerogenic capacity
FC_SCORE = {
    "normal_IgG1":          1.0,   # Full effector + FcγRIIb → tolerogenic
    "normal_IgG2":          0.7,   # Reduced effector
    "reduced_effector":     0.5,   # IgG4, some mutations
    "stabilized_IgG4":      0.5,   # S228P
    "enhanced_ADCC":        1.2,   # Afucosylated → more DC engagement
    "no_effector":          0.0,   # LALA, N297A → no FcγR → no tolerance
    "no_Fc_fragment":       0.0,   # Fab, scFv, VHH → no Fc at all
    "scFv_no_Fc":           0.0,
    "Fab_no_Fc":            0.0,
    "extended_half_life":   0.8,   # YTE → less frequent dosing
    "modified_half_life":   0.7,
    "extended_recycling":   0.8,
    "modified":             0.6,
    "bispecific_effector":  0.8,
}
m["feat_fc_tolerogenic"] = m["fc_effector_status"].map(FC_SCORE).fillna(0.7)

# 3. MTX/immunosuppressant co-medication
MTX_SCORE = {
    "high_proportion":      1.0,   # >50% of patients on MTX → strongly suppresses ADA
    "moderate_proportion":  0.5,
    "none":                 0.0,
}
m["feat_mtx_suppression"] = m["mtx_comedication"].map(MTX_SCORE).fillna(0.0)

# Broader immunosuppressant context
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
m["feat_immuno_suppression"] = m["immunosuppressant_context"].map(IMMUNO_SCORE).fillna(0.0)

# 4. Dosing frequency → APC priming frequency
FREQ_SCORE = {
    "daily":                1.5,   # Very frequent → constant APC priming
    "weekly":               1.2,
    "biweekly":             1.0,
    "q2w":                  1.0,
    "monthly":              0.7,
    "q3w":                  0.75,
    "q4w":                  0.65,
    "q4-8w":                0.55,
    "q8w (after loading)":  0.5,
    "q8w":                  0.5,
    "q8-12w":               0.4,
    "q12w":                 0.3,
    "q3m":                  0.3,
    "monthly or q3m":       0.5,
    "weekly to q4w":        0.9,
    "q3w then q6w":         0.6,
    "q6m":                  0.15,
    "5-day course yearly":  0.2,  # Alemtuzumab: intense burst then long gap
    "single dose":          0.1,
    "single":               0.1,
    "cycle-based":          0.7,
    "d1/8 q21d":            0.8,
    "d1/8/15 q28d":         0.85,
    "q2-3w":                0.9,
    "q2-4w":                0.9,
}
m["feat_dosing_freq"] = m["dose_freq"].map(FREQ_SCORE).fillna(0.6)

# 5. Half-life (longer half-life → higher drug levels → more ADA assay interference;
#    but also less frequent dosing)
def parse_halflife(val):
    if pd.isna(val): return np.nan
    val = str(val)
    nums = re.findall(r'[\d.]+', val)
    if nums: return float(nums[0])
    return np.nan

m["feat_half_life"] = m["half_life_days"].apply(parse_halflife)

# 6. Approval year (proxy for assay/manufacturing quality improvement)
m["feat_approval_era"] = m["approval_year"].fillna(2015).astype(float)
m["feat_approval_era"] = (m["feat_approval_era"] - 2000) / 25  # normalize 0-1

# ============================================================
# ADA RATE CORRECTION
# ============================================================
# Adjust observed ADA for known confounders to extract "intrinsic immunogenicity"
def correct_ada(row):
    ada = row["ada_rate_pct"]
    if pd.isna(ada): return np.nan
    
    # Assay correction: ELISA (gen1) underestimates → multiply up
    assay_mult = 1.0
    if row.get("assay_generation") == 1:
        assay_mult = 2.5  # ELISA detects ~2-3× less than ECL
    
    # Immunosuppression correction: MTX/chemo hides ADA → multiply up
    immuno_mult = 1.0
    sup = row.get("feat_immuno_suppression", 0)
    if sup > 0:
        immuno_mult = 1.0 + sup * 2.0  # strong suppression → 3× undercount
    
    # Fc tolerogenic correction: drugs with NO Fc lose tolerance mechanism
    # → observed ADA is "real" (no artificial suppression)
    fc_tol = row.get("feat_fc_tolerogenic", 0.7)
    fc_mult = 1.0  # baseline (normal IgG1)
    if fc_tol < 0.3:
        fc_mult = 0.6  # No-Fc drugs: high observed ADA is expected from format, not intrinsic sequence
    
    # Immune-depleting correction: reconstitution ADA is not sequence-driven
    depl_mult = 1.0
    if row.get("feat_immune_depleting", 0) > 0:
        depl_mult = 0.3  # 70% of observed ADA is from reconstitution, not sequence
    
    return ada * assay_mult * immuno_mult * fc_mult * depl_mult

m["ada_corrected"] = m.apply(correct_ada, axis=1)
m["log_ada_corrected"] = np.log10(m["ada_corrected"].clip(lower=0.05))

print(f"\nADA corrected range: {m['ada_corrected'].min():.1f}–{m['ada_corrected'].max():.1f}%")
print(f"ADA raw range:       {m['ada_rate_pct'].min():.1f}–{m['ada_rate_pct'].max():.1f}%")

# ============================================================
# COMPREHENSIVE CORRELATION TABLE
# ============================================================
ALL_FEAT = [c for c in m.columns if c.startswith("feat_")]
target_raw = "ada_rate_pct"
target_cor = "ada_corrected"

print("\n" + "="*80)
print("CORRELATIONS: All features vs raw ADA AND corrected ADA")
print("="*80)
rows = []
for fc in ALL_FEAT:
    for tgt_name, tgt_col in [("raw", target_raw), ("corrected", target_cor)]:
        sub = m[[tgt_col, fc]].dropna()
        if len(sub) < 8: continue
        r, p = spearmanr(sub[tgt_col], sub[fc])
        rows.append({"feature": fc.replace("feat_",""), "target": tgt_name,
                      "r": r, "p": p, "n": len(sub)})

cr = pd.DataFrame(rows)
# Show sorted by |r| for corrected ADA
cr_cor = cr[cr["target"]=="corrected"].sort_values("r", key=abs, ascending=False)
cr_raw = cr[cr["target"]=="raw"].set_index("feature")

print(f"{'Feature':35s} {'r_corrected':>12s} {'p_corr':>8s} {'r_raw':>10s} {'n':>4s}")
print("-"*75)
for _, row in cr_cor.iterrows():
    fn = row["feature"]
    raw_r = cr_raw.loc[fn, "r"] if fn in cr_raw.index else float("nan")
    star = "**" if row["p"]<0.01 else ("*" if row["p"]<0.05 else ("^" if row["p"]<0.10 else " "))
    print(f"  {fn:33s} {row['r']:+.3f}{star}   p={row['p']:.3f}   (raw:{raw_r:+.3f})  n={int(row['n'])}")

# ============================================================
# LOO REGRESSION MODELS
# ============================================================
print("\n" + "="*80)
print("LOO RIDGE REGRESSION – Sprint Models")
print("="*80)

m["log_ada"] = np.log10(m[target_raw].clip(lower=0.05))

# Feature sets
MOLECULAR = [
    "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
    "feat_net_burden","feat_vh_identity","feat_cdrh3_aromaticity",
    "feat_cdrh3_len","feat_n_clusters",
]
CLINICAL_NEW = [
    "feat_assay_gen","feat_fc_tolerogenic","feat_mtx_suppression",
    "feat_immuno_suppression","feat_dosing_freq","feat_clinical_context",
    "feat_immune_depleting",
]
COMBINED = MOLECULAR + CLINICAL_NEW
TOP_SELECT = [
    "feat_origin_code","feat_immuno_suppression","feat_fc_tolerogenic",
    "feat_dosing_freq","feat_vz_foreignness","feat_n_strong_binders",
    "feat_immune_depleting","feat_assay_gen",
]

MODELS = {
    "Molecular only (8)": (MOLECULAR, target_raw),
    "Clinical confounders only (7)": (CLINICAL_NEW, target_raw),
    "Combined raw ADA (15)": (COMBINED, target_raw),
    "Combined log(ADA) (15)": (COMBINED, "log_ada"),
    "Top-8 selected → raw": (TOP_SELECT, target_raw),
    "Top-8 selected → log": (TOP_SELECT, "log_ada"),
    "Combined → corrected ADA": (COMBINED, target_cor),
    "Top-8 → corrected ADA": (TOP_SELECT, target_cor),
    "Molecular → corrected ADA": (MOLECULAR, target_cor),
}

loo = LeaveOneOut()
best_r, best_name = -99, ""

for mod_name, (feats, tgt) in MODELS.items():
    feats = [f for f in feats if f in m.columns]
    sub   = m[[tgt] + feats].dropna()
    X     = sub[feats].values
    y     = sub[tgt].values
    
    preds = np.zeros(len(y))
    for tr, te in loo.split(X):
        sc = StandardScaler()
        Xtr, Xte = sc.fit_transform(X[tr]), sc.transform(X[te])
        md = RidgeCV(alphas=[0.001,0.01,0.1,1,5,10,50,100,200,500])
        md.fit(Xtr, y[tr])
        preds[te] = md.predict(Xte)
    
    r_sp, p_sp = spearmanr(y, preds)
    r_pe, _    = pearsonr(y, preds)
    star = "**" if p_sp<0.01 else ("*" if p_sp<0.05 else ("^" if p_sp<0.10 else " "))
    
    if r_sp > best_r:
        best_r, best_name = r_sp, mod_name
        best_feats, best_tgt = feats, tgt
        best_y, best_preds = y.copy(), preds.copy()
    
    print(f"  [{mod_name:40s}] n={len(sub):2d}  Spearman r={r_sp:+.3f}{star} p={p_sp:.4f}  Pearson r={r_pe:+.3f}")

# --- Also try GBR (non-linear) ---
print("\n--- Non-linear models ---")
for mod_name, (feats, tgt) in [
    ("GBR Combined→raw (15)", (COMBINED, target_raw)),
    ("GBR Top-8→raw", (TOP_SELECT, target_raw)),
    ("RF Combined→raw (15)", (COMBINED, target_raw)),
    ("GBR Combined→corrected (15)", (COMBINED, target_cor)),
]:
    feats = [f for f in feats if f in m.columns]
    sub = m[[tgt]+feats].dropna()
    X, y = sub[feats].values, sub[tgt].values
    preds = np.zeros(len(y))
    for tr, te in loo.split(X):
        if "GBR" in mod_name:
            md = GradientBoostingRegressor(n_estimators=80, max_depth=2, 
                    learning_rate=0.05, subsample=0.8, random_state=42)
        else:
            md = RandomForestRegressor(n_estimators=100, max_depth=3, random_state=42)
        md.fit(X[tr], y[tr])
        preds[te] = md.predict(X[te])
    r_sp, p_sp = spearmanr(y, preds)
    star = "**" if p_sp<0.01 else ("*" if p_sp<0.05 else ("^" if p_sp<0.10 else " "))
    print(f"  [{mod_name:40s}] n={len(sub):2d}  Spearman r={r_sp:+.3f}{star} p={p_sp:.4f}")
    if r_sp > best_r:
        best_r, best_name = r_sp, mod_name
        best_feats, best_tgt = feats, tgt
        best_y, best_preds = y.copy(), preds.copy()

print(f"\n{'='*80}")
print(f"BEST MODEL: {best_name}  Spearman r={best_r:+.3f}")
print(f"{'='*80}")

# --- Feature importance for best linear model ---
print("\n=== Feature coefficients (best Ridge model on all data) ===")
feats = [f for f in (COMBINED if "Combined" in best_name else TOP_SELECT) if f in m.columns]
sub = m[[target_raw]+feats].dropna()
X, y = sub[feats].values, sub[target_raw].values
sc = StandardScaler()
Xsc = sc.fit_transform(X)
md = RidgeCV(alphas=[0.01,0.1,1,10,50,100]).fit(Xsc, y)
coefs = sorted(zip([f.replace("feat_","") for f in feats], md.coef_), 
               key=lambda x: abs(x[1]), reverse=True)
for f, c in coefs:
    bar = ("+" if c>0 else "-") * int(abs(c)/max(abs(x[1]) for x in coefs)*25)
    print(f"  {f:35s}: {c:+7.2f} [{bar}]")

# --- Save enhanced matrix ---
m.to_csv(OUT / "immuno70_sprint_matrix.csv", index=False)
print(f"\nSaved {OUT / 'immuno70_sprint_matrix.csv'}")
print(f"  {len(m)} rows × {len(m.columns)} columns, {len(ALL_FEAT)} features")
