"""
immunogenicity_sprint_v3.py – Streamlined: fixed hyperparams, more models
"""
import pandas as pd, numpy as np
from pathlib import Path
from scipy.stats import spearmanr
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler
import warnings; warnings.filterwarnings("ignore")

ROOT = Path("d:/InSynBio-AI-Research/Antibody_Engineer_Suite")
OUT  = ROOT / "data/thera_sabdab/out"
m = pd.read_csv(OUT / "immuno70_sprint_matrix.csv").drop_duplicates("antibody_name").copy()
target = "ada_rate_pct"
print(f"N={len(m)}")

# --- Interaction features ---
m["ix_origin_freq"]    = m["feat_origin_code"] * m["feat_dosing_freq"]
m["ix_burden_nosupp"]  = m["feat_net_burden"] * (1 - m["feat_immuno_suppression"]*0.7)
m["ix_vz_origin"]      = m["feat_vz_foreignness"] * m["feat_origin_code"]
m["ix_depl_net"]       = m["feat_immune_depleting"] * (1 - m["feat_immuno_suppression"])
m["ix_binders_net"]    = m["feat_n_strong_binders"] * (1 - m["feat_immuno_suppression"])
m["ix_hl_inv"]         = 1.0 / m["feat_half_life"].fillna(m["feat_half_life"].median()).clip(lower=1)
m["ix_tnf_origin"]     = m["feat_anti_tnf"] * m["feat_origin_code"]
m["ix_fc_format"]      = m["feat_fc_tolerogenic"] * (2 - m["feat_format"])

# --- Hand-crafted composite ---
m["score_mol"] = (m["feat_origin_code"]*10 + m["feat_vz_foreignness"]*0.3 +
                  m["feat_n_strong_binders"]*0.05 + m["feat_net_burden"]*2.0 +
                  m["feat_n_clusters"]*0.5 + (100-m["feat_vh_identity"].fillna(85))*0.3)
m["score_clin"] = (m["feat_dosing_freq"]*3 + m["feat_immune_depleting"]*8 +
                   (1-m["feat_fc_tolerogenic"])*3 + (1-m["feat_immuno_suppression"])*2 +
                   m["feat_format"]*1.5)
m["score_comb"] = m["score_mol"]*0.4 + m["score_clin"]*0.6

for sc in ["score_mol","score_clin","score_comb"]:
    r,p = spearmanr(m[target], m[sc])
    star = "**" if p<0.01 else ("*" if p<0.05 else "")
    print(f"  {sc:25s}: r={r:+.3f}{star} p={p:.4f}")

# --- All features correlation (top 25) ---
all_feat = [c for c in m.columns if c.startswith("feat_") or c.startswith("ix_") or c.startswith("score_")]
rows=[]
for fc in all_feat:
    sub = m[[target,fc]].dropna()
    if len(sub)<10: continue
    r,p = spearmanr(sub[target],sub[fc])
    rows.append({"f":fc,"r":r,"p":p,"n":len(sub)})
cr = pd.DataFrame(rows).sort_values("r",key=abs,ascending=False)
print(f"\nTop 25 features:")
for _,row in cr.head(25).iterrows():
    star="**" if row["p"]<0.01 else ("*" if row["p"]<0.05 else ("^" if row["p"]<0.10 else " "))
    print(f"  {row['f']:35s}: r={row['r']:+.3f}{star} n={int(row['n'])}")

# --- LOO helper ---
def loo_ridge(X, y):
    preds = np.zeros(len(y))
    for tr, te in LeaveOneOut().split(X):
        sc = StandardScaler()
        Xtr = sc.fit_transform(X[tr]); Xte = sc.transform(X[te])
        md = RidgeCV(alphas=[0.01,0.1,1,10,50,100,200]).fit(Xtr, y[tr])
        preds[te] = md.predict(Xte)
    return preds

def loo_gbr(X, y, n_est=80, lr=0.05, md=2):
    preds = np.zeros(len(y))
    for tr, te in LeaveOneOut().split(X):
        gb = GradientBoostingRegressor(n_estimators=n_est, max_depth=md,
                learning_rate=lr, subsample=0.8, random_state=42, min_samples_leaf=3)
        gb.fit(X[tr], y[tr])
        preds[te] = gb.predict(X[te])
    return preds

# --- Model matrix ---
SETS = {
    "Ridge: mol(8)": [
        "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
        "feat_net_burden","feat_vh_identity","feat_cdrh3_aromaticity",
        "feat_cdrh3_len","feat_n_clusters"],
    "Ridge: clin(7)": [
        "feat_assay_gen","feat_fc_tolerogenic","feat_mtx_suppression",
        "feat_immuno_suppression","feat_dosing_freq","feat_clinical_context",
        "feat_immune_depleting"],
    "Ridge: all(15)": [
        "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
        "feat_net_burden","feat_vh_identity","feat_cdrh3_aromaticity",
        "feat_cdrh3_len","feat_n_clusters","feat_assay_gen","feat_fc_tolerogenic",
        "feat_mtx_suppression","feat_immuno_suppression","feat_dosing_freq",
        "feat_clinical_context","feat_immune_depleting"],
    "Ridge: interactions(8)": [
        "ix_origin_freq","ix_burden_nosupp","ix_depl_net","ix_vz_origin",
        "ix_fc_format","ix_hl_inv","ix_binders_net","ix_tnf_origin"],
    "Ridge: mol+ix(16)": [
        "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
        "feat_net_burden","feat_vh_identity","feat_cdrh3_len","feat_n_clusters",
        "feat_immune_depleting","ix_origin_freq","ix_burden_nosupp","ix_depl_net",
        "ix_vz_origin","ix_hl_inv","ix_binders_net","feat_half_life","feat_dosing_freq"],
    "GBR: all(15)": [
        "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
        "feat_net_burden","feat_vh_identity","feat_cdrh3_aromaticity",
        "feat_cdrh3_len","feat_n_clusters","feat_assay_gen","feat_fc_tolerogenic",
        "feat_mtx_suppression","feat_immuno_suppression","feat_dosing_freq",
        "feat_clinical_context","feat_immune_depleting"],
    "GBR: curated-8": [
        "feat_origin_code","feat_immune_depleting","feat_immuno_suppression",
        "feat_dosing_freq","feat_vz_foreignness","feat_fc_tolerogenic",
        "feat_half_life","feat_n_strong_binders"],
    "GBR: full-25": [
        "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
        "feat_net_burden","feat_vh_identity","feat_cdrh3_aromaticity",
        "feat_cdrh3_len","feat_n_clusters","feat_assay_gen","feat_fc_tolerogenic",
        "feat_mtx_suppression","feat_immuno_suppression","feat_dosing_freq",
        "feat_clinical_context","feat_immune_depleting","feat_half_life",
        "ix_origin_freq","ix_burden_nosupp","ix_depl_net","ix_vz_origin",
        "ix_fc_format","ix_hl_inv","ix_binders_net","feat_anti_tnf","feat_cdr_deamidation"],
    "GBR: mol+ix(16)": [
        "feat_origin_code","feat_vz_foreignness","feat_n_strong_binders",
        "feat_net_burden","feat_vh_identity","feat_cdrh3_len","feat_n_clusters",
        "feat_immune_depleting","ix_origin_freq","ix_burden_nosupp","ix_depl_net",
        "ix_vz_origin","ix_hl_inv","ix_binders_net","feat_half_life","feat_dosing_freq"],
}

print(f"\n{'='*80}")
print("LOO MODEL COMPARISON (full dataset n=70)")
print(f"{'='*80}")

best_r, best_name = -99, ""
for mname, fl in SETS.items():
    fl = [f for f in fl if f in m.columns]
    sub = m[[target]+fl].dropna()
    X, y = sub[fl].values, sub[target].values
    if "GBR" in mname:
        preds = loo_gbr(X, y)
    else:
        preds = loo_ridge(X, y)
    r_sp, p_sp = spearmanr(y, preds)
    star = "**" if p_sp<0.01 else ("*" if p_sp<0.05 else ("^" if p_sp<0.10 else " "))
    print(f"  {mname:35s} n={len(sub):2d} k={len(fl):2d}  r={r_sp:+.3f}{star}  p={p_sp:.4f}")
    if r_sp > best_r: best_r, best_name = r_sp, mname

# --- Exclude 3 extreme outliers ---
print(f"\n{'='*80}")
print("LOO MODEL COMPARISON (no 3 extreme outliers, n=67)")
print(f"{'='*80}")
EXCL = ["Donanemab","Alemtuzumab","Brolucizumab"]
mc = m[~m["antibody_name"].isin(EXCL)].copy()

for mname, fl in SETS.items():
    fl = [f for f in fl if f in mc.columns]
    sub = mc[[target]+fl].dropna()
    X, y = sub[fl].values, sub[target].values
    if "GBR" in mname:
        preds = loo_gbr(X, y)
    else:
        preds = loo_ridge(X, y)
    r_sp, p_sp = spearmanr(y, preds)
    star = "**" if p_sp<0.01 else ("*" if p_sp<0.05 else ("^" if p_sp<0.10 else " "))
    print(f"  {mname:35s} n={len(sub):2d} k={len(fl):2d}  r={r_sp:+.3f}{star}  p={p_sp:.4f}")
    if r_sp > best_r: best_r, best_name = r_sp, f"no-outlier: {mname}"

# --- Try log(ADA) target ---
print(f"\n{'='*80}")
print("LOO with log10(ADA) as target (full n=70)")
print(f"{'='*80}")
m["log_ada"] = np.log10(m[target].clip(lower=0.05))
for mname in ["GBR: all(15)","GBR: curated-8","GBR: full-25"]:
    fl = [f for f in SETS[mname] if f in m.columns]
    sub = m[["log_ada"]+fl].dropna()
    X, y = sub[fl].values, sub["log_ada"].values
    preds = loo_gbr(X, y)
    # Compare predicted LOG vs actual RAW (rank matters, not scale)
    r_sp, p_sp = spearmanr(sub[target].values if target in sub.columns 
                            else m.loc[sub.index, target].values, preds)
    star = "**" if p_sp<0.01 else ("*" if p_sp<0.05 else "")
    print(f"  {mname:35s} log target  r={r_sp:+.3f}{star}  p={p_sp:.4f}")

# --- GBR feature importance ---
print(f"\n{'='*80}")
print(f"GBR FEATURE IMPORTANCE (full-25)")
fl25 = [f for f in SETS["GBR: full-25"] if f in m.columns]
sub = m[[target]+fl25].dropna()
X, y = sub[fl25].values, sub[target].values
gb = GradientBoostingRegressor(n_estimators=80, max_depth=2, learning_rate=0.05,
                                subsample=0.8, random_state=42, min_samples_leaf=3).fit(X, y)
imp = sorted(zip(fl25, gb.feature_importances_), key=lambda x: x[1], reverse=True)
mx = max(x[1] for x in imp)
for f, i in imp[:15]:
    bar = "#" * int(i/mx*30)
    print(f"  {f:35s}: {i:.4f} [{bar}]")

print(f"\nBEST OVERALL: {best_name} r={best_r:+.3f}")
m.to_csv(OUT / "immuno70_sprint_matrix.csv", index=False)
print("Saved.")
