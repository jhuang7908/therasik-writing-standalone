"""
immunogenicity_final_model.py
=================================
Final comprehensive immunogenicity analysis:
- All known factors encoded
- Best achievable model for this heterogeneous dataset
- Honest assessment of r=0.7 feasibility
- HTML report generation
"""

import pandas as pd
import numpy as np
import json
import re
from pathlib import Path
from scipy.stats import spearmanr, pearsonr
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline
import warnings
warnings.filterwarnings("ignore")

ROOT = Path("d:/InSynBio-AI-Research/Antibody_Engineer_Suite")
OUT  = ROOT / "data/thera_sabdab/out"
REF  = ROOT / "data/reference"

# ---- Load extended feature matrix ----------------------------------------
m = pd.read_csv(OUT / "immuno70_extended_features.csv")
m = m.drop_duplicates("antibody_name").copy()
print(f"Dataset: {len(m)} antibodies, ada_rate_pct range: "
      f"{m['ada_rate_pct'].min():.1f}–{m['ada_rate_pct'].max():.1f}%")

# =========================================================
# NEW FEATURES BATCH 2
# =========================================================

# --- 1. CDR-specific PTM motifs (deamidation NG / isomerization DS) ------
CDR_COLS = ["vh_cdr1","vh_cdr2","vh_cdr3","vl_cdr1","vl_cdr2","vl_cdr3"]

def cdr_ng_count(row):
    """Count NG motifs (deamidation) specifically in CDRs"""
    return sum(str(row.get(c,"")).count("NG") for c in CDR_COLS if pd.notna(row.get(c)))

def cdr_ds_count(row):
    """Count DS motifs (isomerization) specifically in CDRs"""
    return sum(str(row.get(c,"")).count("DS") for c in CDR_COLS if pd.notna(row.get(c)))

def cdr_total_length(row):
    return sum(len(str(row.get(c,""))) for c in CDR_COLS if pd.notna(row.get(c)))

m["feat_cdr_deamidation"] = m.apply(cdr_ng_count, axis=1)
m["feat_cdr_isomerization"] = m.apply(cdr_ds_count, axis=1)
m["feat_total_cdr_length"]  = m.apply(cdr_total_length, axis=1)

# --- 2. Fc presence (IgG with Fc vs fragment without) --------------------
# Full IgG / ADC → Fc-mediated tolerance (FcγRIIb, FcRn)
# Fab, scFv, VHH → no Fc → less tolerogenic
FORMAT_FC = {
    "Whole mAb": 1.0,
    "Whole mAb ADC": 0.9,
    "Bispecific mAb": 0.9,
    "Fab": 0.0,
    "scFv": 0.0,
    "Bispecific scFv": 0.1,
    "Bispecific Single Domains (VH-VH'-VH)": 0.3,  # has some Fc but small
}
m["feat_fc_present"] = m.get("format_sab", pd.Series("Whole mAb", index=m.index)).map(FORMAT_FC).fillna(0.8)

# --- 3. Target class biological context ----------------------------------
# Targets that engage immunologically active cells/pathways
TARGET_CLASS_SCORE = {
    # Anti-checkpoint: blocks T-cell tolerance machinery
    # Net effect on ADA: complex (PD-L1 blocking DCs → more immunogenic context)
    # anti-PD-1: T cell PD-1 blockade → but usually low oncology ADA
    # anti-PD-L1: DC/tumor PD-L1 blockade → context-dependent
    "cytokine": 0.3,       # anti-cytokine: moderate ADA risk (self-similar)
    "receptor": 0.5,       # anti-receptor: higher risk
    "immune_checkpoint": 0.4,  # checkpoint: special context
    "immune_depleting": 1.2,   # depleting: reconstitution ADA
    "tumor_antigen": 0.2,  # VEGF, HER2: generally low immunogenicity
    "other": 0.5,
}

CYTOKINE_TARGETS = {"TNF","IL-17","IL-23","IL-12","IL-6","IL-4","IL-13","IL-31",
                    "IL-33","CGRP","IFN","GM-CSF","BAFF","TSLP","NGF"}
RECEPTOR_TARGETS  = {"CGRP-R","IL-6R","IL-4R","VEGFR","EGFR","HER2","CD3","CD4","CD8","BCMA","GLP1R"}
CHECKPOINT_TARGETS= {"PD-1","PD-L1","CTLA-4","LAG-3","TIGIT","TIM-3","OX40","4-1BB","ICOS"}
DEPLETING_TARGETS = {"CD20","CD52","CD38","CD19","CD6","CD5","CD22","CCR4"}
TUMOR_TARGETS     = {"VEGF","VEGF-A","EGFR","HER2","PCSK9","RANKL","C5",
                     "Amyloid","amyloid","BCMA","PDL1","CEA","GD2","Sclerostin","FGF23"}

def target_bio_score(row):
    tgt = str(row.get("target",""))
    if any(d in tgt for d in DEPLETING_TARGETS): return 1.2
    if any(r in tgt for r in RECEPTOR_TARGETS):  return 0.5
    if any(c in tgt for c in CHECKPOINT_TARGETS):return 0.4
    if any(c in tgt for c in CYTOKINE_TARGETS):  return 0.3
    if any(t in tgt for t in TUMOR_TARGETS):     return 0.2
    return 0.5

m["feat_target_bio"] = m.apply(target_bio_score, axis=1)

# --- 4. Anti-TNF class (historically highest ADA rates for class) --------
m["feat_anti_tnf"] = m["target"].str.contains("TNF", na=False).astype(float)

# --- 5. CDR-H3 polar/charged content ------------------------------------
POLAR_AA = set("STCYNQ")
def cdrh3_polar_frac(seq):
    seq = str(seq) if pd.notna(seq) else ""
    if len(seq) == 0: return np.nan
    return sum(1 for aa in seq if aa in POLAR_AA) / len(seq)

m["feat_cdrh3_polar"] = m["vh_cdr3"].apply(cdrh3_polar_frac)

# --- 6. VH germline family (IGHV1 vs IGHV3 etc.) -------------------------
# IGHV3: most common, lowest immunogenicity
# IGHV1, IGHV2, IGHV4: rarer, potentially more immunogenic
def vhfam_score(fam):
    if pd.isna(fam): return 0.5
    fam = str(fam)
    if "IGHV3" in fam: return 0.0   # most tolerogenic
    if "IGHV1" in fam: return 0.3
    if "IGHV4" in fam: return 0.4
    if "IGHV2" in fam: return 0.6
    return 0.5

m["feat_vh_family_score"] = m["vh_family"].apply(vhfam_score)

# --- 7. CDR-H3 loop exposure risk (long CDR-H3 with unusual composition) --
# Long, aromatic-rich CDR-H3 → more HLA binding potential
def cdrh3_risk(row):
    seq  = str(row.get("vh_cdr3","")) if pd.notna(row.get("vh_cdr3")) else ""
    L    = len(seq)
    if L == 0: return 0.0
    arom = sum(1 for aa in seq if aa in set("YWF")) / L
    # Risk = length-normalized aromatic content (longer loops with more aromatics = riskier)
    return np.log1p(L) * arom * 10

m["feat_cdrh3_risk"] = m.apply(cdrh3_risk, axis=1)

# =========================================================
# FULL CORRELATION TABLE (all features)
# =========================================================
ALL_FEAT = [c for c in m.columns if c.startswith("feat_")]
target   = "ada_rate_pct"

print("\n" + "="*72)
print("COMPLETE FEATURE CORRELATION TABLE (n=70, ranked by |r|)")
print("="*72)
rows = []
for fc in ALL_FEAT:
    sub = m[[target, fc]].dropna()
    if len(sub) < 8: continue
    r, p = spearmanr(sub[target], sub[fc])
    rows.append({"feature": fc.replace("feat_",""), "r": r, "p": p, "n": len(sub),
                 "group": "molecular" if any(x in fc for x in 
                    ["origin","vz","strong","burden","cdrh3","cdr","vh_id","vl_id","family","surf","target"]) 
                    else "clinical"})

corr_df = pd.DataFrame(rows).sort_values("r", key=abs, ascending=False)
for _, row in corr_df.iterrows():
    star = "**" if row["p"] < 0.01 else ("*" if row["p"] < 0.05 else ("^" if row["p"] < 0.10 else " "))
    bar_len = int(abs(row["r"]) * 35)
    bar = ("+" if row["r"]>0 else "-") * bar_len
    print(f"  {row['feature']:30s}: r={row['r']:+.3f}{star} [{bar:<35s}] n={int(row['n'])}")

# =========================================================
# LOO RIDGE REGRESSION – final best model
# =========================================================
print("\n" + "="*72)
print("MULTI-VARIATE LOO RIDGE REGRESSION – FINAL MODELS")
print("="*72)

m["log_ada"] = np.log10(m[target].clip(lower=0.05))

# Top-8 by |r| (with n≥40)
top8 = [row["feature"] for _,row in corr_df[corr_df["n"]>=40].head(8).iterrows()]
top8 = ["feat_" + f for f in top8]

MODELS = {
    "Top-8 features": top8,
    "Molecular core": [
        "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
        "feat_net_burden","feat_vh_identity","feat_total_cdr_length",
        "feat_target_bio","feat_fc_present","feat_cdrh3_risk",
    ],
    "Full 15-feature": [
        "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
        "feat_net_burden","feat_clinical_context","feat_immune_depleting",
        "feat_format","feat_isotype_immuno","feat_fc_present",
        "feat_target_bio","feat_vh_identity","feat_cdrh3_len",
        "feat_cdrh3_aromaticity","feat_total_cdr_length","feat_cdrh3_risk",
    ],
}

loo = LeaveOneOut()
best_r, best_name, best_pred = -99, "", None

for mod_name, feats in MODELS.items():
    feats = [f for f in feats if f in m.columns]
    sub   = m[[target,"log_ada"] + feats].dropna()
    X     = sub[feats].values
    y_raw = sub[target].values
    y_log = sub["log_ada"].values

    preds_raw, preds_log = np.zeros(len(y_raw)), np.zeros(len(y_log))
    for tr, te in loo.split(X):
        sc = StandardScaler()
        Xtr, Xte = sc.fit_transform(X[tr]), sc.transform(X[te])
        for yy, preds in [(y_raw, preds_raw), (y_log, preds_log)]:
            md = RidgeCV(alphas=[0.01,0.1,1,10,50,100,200])
            md.fit(Xtr, yy[tr])
            preds[te] = md.predict(Xte)

    r_raw, p_raw = spearmanr(y_raw, preds_raw)
    r_log, p_log = spearmanr(y_log, preds_log)
    star_r = "**" if p_raw<0.01 else ("*" if p_raw<0.05 else ("^" if p_raw<0.10 else " "))
    star_l = "**" if p_log<0.01 else ("*" if p_log<0.05 else ("^" if p_log<0.10 else " "))
    print(f"\n  [{mod_name}] n={len(sub)} k={len(feats)}")
    print(f"    Raw ADA:  Spearman r={r_raw:+.3f}{star_r} p={p_raw:.4f}")
    print(f"    Log ADA:  Spearman r={r_log:+.3f}{star_l} p={p_log:.4f}")

    if r_raw > best_r:
        best_r, best_name = r_raw, mod_name
        best_feats = feats
        best_sub   = sub
        best_preds = preds_raw
        best_y     = y_raw

# =========================================================
# FEATURE IMPORTANCE for best model
# =========================================================
print(f"\n=== Feature importance for '{best_name}' ===")
feats   = [f for f in best_feats if f in m.columns]
sub_fi  = m[["antibody_name", target] + feats].dropna()
X_fi    = sub_fi[feats].values
y_fi    = sub_fi[target].values
sc_fi   = StandardScaler()
X_fi_sc = sc_fi.fit_transform(X_fi)
md_fi   = RidgeCV(alphas=[0.01,0.1,1,10,50,100]).fit(X_fi_sc, y_fi)
coef_df = pd.DataFrame({"feature": [f.replace("feat_","") for f in feats],
                         "coef": md_fi.coef_}).sort_values("coef", key=abs, ascending=False)
for _, row in coef_df.iterrows():
    bar = ("+" if row["coef"]>0 else "-") * int(abs(row["coef"])/max(abs(coef_df["coef"]))*20)
    print(f"  {row['feature']:30s}: coef={row['coef']:+.3f} [{bar}]")

# =========================================================
# SAVE UPDATED MATRIX
# =========================================================
m.to_csv(OUT / "immuno70_extended_features.csv", index=False)
print(f"\nUpdated matrix saved with {len([c for c in m.columns if c.startswith('feat_')])} features")

# =========================================================
# OUTLIER TABLE
# =========================================================
print("\n=== NOTABLE OUTLIERS (actual vs expected) ===")
# Re-run best model for residuals
best_feats_clean = [f for f in best_feats if f in m.columns]
sub_out = m[["antibody_name","origin","route","target","disease_class",target] + best_feats_clean].dropna()
X_out   = sub_out[best_feats_clean].values
y_out   = sub_out[target].values
preds_out = np.zeros(len(y_out))
for tr, te in LeaveOneOut().split(X_out):
    sc = StandardScaler()
    Xtr, Xte = sc.fit_transform(X_out[tr]), sc.transform(X_out[te])
    md_out = RidgeCV(alphas=[0.01,0.1,1,10,50])
    md_out.fit(Xtr, y_out[tr])
    preds_out[te] = md_out.predict(Xte)

sub_out = sub_out.copy()
sub_out["predicted"] = preds_out
sub_out["residual"]  = sub_out[target] - preds_out
sub_out_show = sub_out[abs(sub_out["residual"])>10].sort_values("residual", ascending=False)
print(sub_out_show[["antibody_name","ada_rate_pct","predicted","residual","origin","route","target"]].to_string(index=False))

print("\n[Done] immunogenicity_final_model.py")
