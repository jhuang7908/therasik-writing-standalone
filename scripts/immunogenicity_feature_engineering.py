"""
immunogenicity_feature_engineering.py
======================================
Comprehensive feature engineering for ADA correlation analysis.
Goal: Build a feature-rich matrix and push Spearman r toward 0.7.

New dimensions added vs baseline matrix:
  1. Molecular – CDR-H3 composition (aromatic %, charge, length)
  2. Molecular – Fv biophysics (net charge, pI, GRAVY from CMC)
  3. Biological context – immune-depleting target
  4. Biological context – format (scFv/VHH vs full IgG)
  5. Clinical context composite  (route × indication × immunosuppression)
  6. ADA assay correction  (IV/high-dose → drug interference → depress detected ADA)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr, pearsonr
from sklearn.linear_model import RidgeCV, Ridge
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score
import warnings
warnings.filterwarnings("ignore")

ROOT = Path("d:/InSynBio-AI-Research/Antibody_Engineer_Suite")
OUT  = ROOT / "data/thera_sabdab/out"
REF  = ROOT / "data/reference"

# ---- Load base matrix (deduplicated) ----
mat  = pd.read_csv(OUT / "immuno70_full_matrix.csv")
mat  = mat.drop_duplicates("antibody_name").copy()
print(f"Loaded {len(mat)} antibodies")

# ---- Load SAbDab metadata ----
xlsx = ROOT / "data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx"
sab  = pd.read_excel(xlsx)
sub70 = (sab[sab["Therapeutic"].isin(mat["antibody_name"].tolist())]
         [["Therapeutic","CH1 Isotype","Format","Development Tech"]]
         .drop_duplicates("Therapeutic").copy())
sub70.columns = ["antibody_name","isotype","format_sab","dev_tech"]
m = mat.merge(sub70, on="antibody_name", how="left")

# ---- Standardise route/oncology columns (deduplicate _x/_y suffixes) ----
for col in ["route", "oncology_indication"]:
    if f"{col}_x" in m.columns:
        m[col] = m[f"{col}_x"].fillna(m.get(f"{col}_y", np.nan))

# ============================================================
# FEATURE GROUP 1 – CDR-H3 sequence composition
# ============================================================
AROMATIC  = set("YWF")
POS_CHARGE = set("KRH")
NEG_CHARGE = set("DE")

def cdrh3_aromaticity(seq):
    """Fraction of Tyr/Trp/Phe in CDR-H3 → drives MHC-II anchor pins"""
    seq = str(seq) if pd.notna(seq) else ""
    if len(seq) == 0: return np.nan
    return sum(1 for aa in seq if aa in AROMATIC) / len(seq)

def cdrh3_net_charge(seq):
    """Net charge of CDR-H3 at pH 7.4 (positive = potential immunogenicity)"""
    seq = str(seq) if pd.notna(seq) else ""
    return sum(1 for aa in seq if aa in POS_CHARGE) - sum(1 for aa in seq if aa in NEG_CHARGE)

def fv_charge(row):
    """Approximate Fv net charge from VH+VL CDR sequences concatenated"""
    cdrs = "".join([str(row.get(c,"")) for c in
                    ["vh_cdr1","vh_cdr2","vh_cdr3","vl_cdr1","vl_cdr2","vl_cdr3"]
                    if pd.notna(row.get(c))])
    return sum(1 for aa in cdrs if aa in POS_CHARGE) - sum(1 for aa in cdrs if aa in NEG_CHARGE)

m["feat_cdrh3_aromaticity"] = m["vh_cdr3"].apply(cdrh3_aromaticity)
m["feat_cdrh3_charge"]      = m["vh_cdr3"].apply(cdrh3_net_charge)
m["feat_fv_cdr_charge"]     = m.apply(fv_charge, axis=1)
m["feat_cdrh3_len"]         = m["vh_cdr3"].apply(lambda s: len(str(s)) if pd.notna(s) else np.nan)

# ============================================================
# FEATURE GROUP 2 – Format (non-IgG formats are more immunogenic)
# ============================================================
FORMAT_SCORE = {
    "scFv":                                          3.0,
    "Bispecific Single Domains (VH-VH'-VH)":         2.5,   # VHH-based
    "Bispecific scFv":                               2.0,
    "Fab":                                           1.5,
    "Whole mAb ADC":                                 1.3,
    "Bispecific mAb":                                1.2,
    "Whole mAb":                                     1.0,
}
m["feat_format"] = m["format_sab"].map(FORMAT_SCORE).fillna(1.2)

# ============================================================
# FEATURE GROUP 3 – IgG Isotype immunostimulatory potential
# IgG4: no ADCC, reduced complement, less DC activation → lower ADA context
# ============================================================
def isotype_immuno(iso):
    if pd.isna(iso): return 0.5
    iso = str(iso).upper()
    if "G4" in iso: return 0.0
    if "G2" in iso: return 0.3
    if "G1" in iso: return 1.0
    return 0.5

m["feat_isotype_immuno"] = m["isotype"].apply(isotype_immuno)

# ============================================================
# FEATURE GROUP 4 – Clinical immunogenicity context
# = SC route × (1-oncology) × (1 - immunosuppression effect)
# ============================================================
route_val    = m["route"].map({"SC":1.0,"IM":0.8,"IV":0.0,"IVT":1.2}).fillna(0.4)
oncol_val    = m.get("oncology_indication", pd.Series(0, index=m.index)).fillna(0).astype(float)
immuno_val   = m.get("concomitant_immuno_likely", pd.Series(0, index=m.index)).fillna(0).astype(float)
checkpoint   = m.get("checkpoint_inhibitor", pd.Series(0, index=m.index)).fillna(0).astype(float)
depleting    = m.get("immune_depleting", pd.Series(0, index=m.index)).fillna(0).astype(float)

m["feat_clinical_context"] = route_val * (1 - oncol_val*0.7) * (1 - immuno_val*0.5)

# Checkpoint block: anti-checkpoint drugs that block PD-1/PD-L1 are often in 
# immunosuppressed oncology patients BUT checkpoint activation prevents ADA (PD-1)
# Anti-PD-L1 on dendritic cells (Atezolizumab) → DC hyperactivation → MORE ADA
# Anti-PD-1 on T cells → T cell activation but also faster exhaustion
# Net: checkpoint inhibitors slightly increase ADA risk vs non-checkpoint oncology
m["feat_checkpoint"] = checkpoint

# Immune depleting: anti-CD52/CD20/CD38 → lymphocyte depletion then reconstitution
# → paradoxically HIGH ADA during reconstitution phase
m["feat_immune_depleting"] = depleting

# ============================================================
# FEATURE GROUP 5 – ADA assay drug-interference correction
# High-dose IV drugs have drug tolerance window → underestimates true ADA
# SC drugs at lower dose → easier to detect ADA in drug-free window
# Proxy: IV high-dose (≥10 mg/kg or flat 300+mg) → apply "suppress factor"
# We use route_code as proxy (IV=0, SC=1)
# ============================================================
# Already captured in route_val and clinical_context

# ============================================================
# FEATURE GROUP 6 – Molecular immunogenicity (from MHC-II analysis)
# ============================================================
# These are already in the matrix; just rename for clarity
m["feat_n_strong_binders"]     = m["n_strong_binders"]
m["feat_net_burden"]           = m["net_immunogenic_burden"]
m["feat_vz_foreignness"]       = m["vz_n_foreign_total"]
m["feat_vh_identity"]          = m["vh_identity_pct"]
m["feat_vl_identity"]          = m.get("vl_identity_pct", pd.Series(np.nan, index=m.index))
m["feat_origin_code"]          = m["origin_code"]
m["feat_n_clusters"]           = m["n_clusters"]

# ============================================================
# FEATURE GROUP 7 – CMC biophysical features
# ============================================================
m["feat_cmc_pI"]               = m["cmc_pI"]
m["feat_cmc_gravy"]            = m["cmc_GRAVY"]
m["feat_cmc_agg"]              = m["cmc_agg_motifs"]
m["feat_cmc_instability"]      = m["cmc_instability"]
m["feat_cmc_net_charge"]       = m["cmc_net_charge_7_4"]
m["feat_cmc_hydro_patch"]      = m["cmc_hydro_patch_max9"]

# ============================================================
# FEATURE GROUP 8 – Surface hydrophilicity (structural, for PDB subset)
# ============================================================
for c in ["surf_frac_exposed_vl", "surf_n_patches_primary"]:
    if c in m.columns:
        pass
    elif f"{c}_y" in m.columns:
        m[c] = m[f"{c}_y"]
    elif f"{c}_x" in m.columns:
        m[c] = m[f"{c}_x"]

m["feat_surf_frac_vl"]         = m.get("surf_frac_exposed_vl", pd.Series(np.nan, index=m.index))
m["feat_surf_n_patches"]       = m.get("surf_n_patches_primary", pd.Series(np.nan, index=m.index))

# ============================================================
# CORRELATION TABLE
# ============================================================
ALL_FEAT_COLS = [c for c in m.columns if c.startswith("feat_")]
target = "ada_rate_pct"

print("\n" + "="*70)
print("COMPREHENSIVE FEATURE CORRELATION TABLE")
print("="*70)
rows = []
for fc in ALL_FEAT_COLS:
    sub = m[[target, fc]].dropna()
    if len(sub) < 8: continue
    r, p = spearmanr(sub[target], sub[fc])
    rows.append({"feature": fc, "r": r, "p": p, "n": len(sub)})

corr_df = pd.DataFrame(rows).sort_values("r", key=abs, ascending=False)
for _, row in corr_df.iterrows():
    star = "**" if row["p"] < 0.01 else ("*" if row["p"] < 0.05 else ("^" if row["p"] < 0.10 else ""))
    bar_len = int(abs(row["r"]) * 30)
    bar_dir = "+" if row["r"] > 0 else "-"
    bar = bar_dir * bar_len
    print(f"  {row['feature']:35s}: r={row['r']:+.3f}{star:2s} [{bar:<30s}] n={int(row['n'])}")

print()

# ============================================================
# MULTI-VARIATE LOO RIDGE REGRESSION
# ============================================================
print("="*70)
print("MULTI-VARIATE LOO RIDGE REGRESSION")
print("="*70)

FEAT_SETS = {
    "Molecular only": [
        "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
        "feat_net_burden","feat_vh_identity","feat_cdrh3_len",
        "feat_cdrh3_aromaticity","feat_cdrh3_charge","feat_n_clusters",
    ],
    "Clinical context only": [
        "feat_clinical_context","feat_format","feat_immune_depleting","feat_checkpoint",
        "feat_isotype_immuno",
    ],
    "Full combined": [
        "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
        "feat_net_burden","feat_clinical_context","feat_format",
        "feat_immune_depleting","feat_cdrh3_aromaticity","feat_cdrh3_charge",
        "feat_cmc_pI","feat_cmc_gravy","feat_cmc_agg","feat_isotype_immuno",
        "feat_vh_identity","feat_cdrh3_len",
    ],
    "Top-5 by |r|": [row["feature"] for _, row in corr_df.head(5).iterrows()],
}

for set_name, feats in FEAT_SETS.items():
    feats = [f for f in feats if f in m.columns]
    sub   = m[[target] + feats].dropna()
    if len(sub) < 15:
        print(f"\n  {set_name}: too few samples ({len(sub)}), skip")
        continue
    X = sub[feats].values
    y = sub[target].values

    # LOO predictions
    loo    = LeaveOneOut()
    preds  = np.zeros(len(y))
    pipe   = Pipeline([("scl", StandardScaler()), ("ridge", RidgeCV(alphas=[0.01,0.1,1,10,50,100]))])
    for tr, te in loo.split(X):
        pipe.fit(X[tr], y[tr])
        preds[te] = pipe.predict(X[te])

    r_sp, p_sp = spearmanr(y, preds)
    r_pe, _    = pearsonr(y, preds)
    star = "**" if p_sp < 0.01 else ("*" if p_sp < 0.05 else ("^" if p_sp < 0.10 else ""))
    print(f"\n  [{set_name}] n={len(sub)} features={len(feats)}")
    print(f"    Spearman r={r_sp:+.3f}{star} p={p_sp:.4f}  Pearson r={r_pe:+.3f}")

# ============================================================
# SAVE EXTENDED MATRIX
# ============================================================
out_path = OUT / "immuno70_extended_features.csv"
m.to_csv(out_path, index=False)
print(f"\nExtended feature matrix saved → {out_path}")
print(f"  {len(m)} rows × {len(m.columns)} columns")
print(f"  Feature columns: {len(ALL_FEAT_COLS)}")
