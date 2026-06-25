#!/usr/bin/env python3
"""
ADA Risk Analysis — Step 1 + Step 2
=====================================
Step 1: OLS two-factor model (source_class + HPR) → R², AIC, CV, residuals
Step 2: Clinical confounder analysis (route, disease area, assay sensitivity)
        + Partial Spearman of HPR vs ADA controlling all clinical fields

Cohort: Humanized + Fully Human only (n≈222)
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import LabelEncoder

REPO = Path(__file__).resolve().parents[1]
MASTER_CSV  = REPO / "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
CLUSTER_CSV = REPO / "data/immunogenicity_knowledge_base/reports/hpr_hla_cluster_analysis/per_record_low_hpr_hla_cluster_counts.csv"
OUT_DIR     = REPO / "data/immunogenicity_knowledge_base/reports/ada_step1_step2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_RAW = "ada_first_pct"
TARGET_LOG = "ada_log10"


# ─── Normalizers ──────────────────────────────────────────────────────────────

def normalize_class(v: object) -> str:
    if not isinstance(v, str): return "Other"
    v = v.strip().lower()
    if v in ("fully_human", "genetically_human", "fully human"): return "Fully_human"
    if "humanis" in v or "humaniz" in v: return "Humanized"
    return "Other"


def normalize_route(v: object) -> str:
    if not isinstance(v, str) or str(v).strip() in ("nan", ""): return "unknown"
    v = v.strip().lower()
    if "subcut" in v or v in ("sc", "s.c."): return "SC"
    if "intrav" in v or v in ("iv", "i.v."): return "IV"
    if "intramusc" in v: return "IM"
    if "intravitreal" in v: return "IVT"
    return "other"


def normalize_disease(v: object) -> str:
    if not isinstance(v, str) or str(v).strip() in ("nan", ""): return "unknown"
    v = v.strip().lower()
    if "oncol" in v or "cancer" in v or "tumor" in v: return "oncology"
    if "immun" in v or "autoim" in v or "inflamm" in v: return "immunology"
    if "infect" in v or "viral" in v or "bacter" in v: return "infectious"
    return "other"


def normalize_assay(v: object) -> str:
    """Collapse free-text assay platform into ECL/MSD (high-sensitivity) vs ELISA vs unknown."""
    if not isinstance(v, str) or str(v).strip() in ("nan", ""): return "unknown"
    v = v.lower()
    if "msd" in v or "ecl" in v or "electrochemi" in v: return "ECL_MSD"
    if "elisa" in v or "enzyme" in v: return "ELISA"
    if "not stated" in v or "not specified" in v or "not confirmed" in v: return "unknown"
    return "other"


# ─── Load + filter ─────────────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    master = pd.read_csv(MASTER_CSV, low_memory=False)
    cluster = pd.read_csv(CLUSTER_CSV)

    master = master[master[TARGET_RAW].notna()].copy()
    cluster_sub = cluster[[c for c in ["antibody_name","low_hpr_hla_clusters_fr_surface"]
                            if c in cluster.columns]].copy()
    df = master.merge(cluster_sub.rename(columns={"antibody_name": "name_c"}),
                      left_on="antibody_name", right_on="name_c", how="left"
                      ).drop(columns=["name_c"], errors="ignore")

    df["source_class"]  = df["thera_genetics_class"].apply(normalize_class)
    df["route_clean"]   = df["route_curated"].apply(normalize_route)
    df["disease_area"]  = df["ada_profile_disease"].apply(normalize_disease)
    df["assay_type"]    = df["assay_platform"].apply(normalize_assay)
    df[TARGET_LOG]      = np.log10(df[TARGET_RAW] + 0.1)

    # Keep HZ + FH only
    df = df[df["source_class"].isin({"Humanized","Fully_human"})].copy()
    print(f"Cohort: {len(df)} records (HZ={( df['source_class']=='Humanized').sum()}, "
          f"FH={(df['source_class']=='Fully_human').sum()})")
    return df


# ─── Helpers ──────────────────────────────────────────────────────────────────

def spearman(x: pd.Series, y: pd.Series) -> dict:
    m = x.notna() & y.notna()
    x, y = x[m], y[m]
    if len(x) < 8: return {"n": len(x), "rho": None, "p": None, "note": "n<8"}
    rho, p = stats.spearmanr(x, y)
    sig = "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else ""
    return {"n": len(x), "rho": round(float(rho),4), "p": round(float(p),6), "sig": sig}


def partial_spearman_resid(feat, target, confounders) -> dict:
    mask = feat.notna() & target.notna()
    for c in confounders: mask &= c.notna()
    n = mask.sum()
    if n < 10: return {"n": int(n), "partial_rho": None, "p": None, "note": "n<10"}
    f, t = feat[mask].rank(), target[mask].rank()
    C = np.column_stack([c[mask].rank().values for c in confounders])
    def resid(y):
        X = np.column_stack([np.ones(len(C)), C])
        b = np.linalg.lstsq(X, y, rcond=None)[0]
        return y - X @ b
    r, p = stats.pearsonr(resid(f.values), resid(t.values))
    sig = "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else ""
    return {"n": int(n), "partial_rho": round(float(r),4), "p": round(float(p),6), "sig": sig}


def ols_r2(X: np.ndarray, y: np.ndarray) -> dict:
    """Fit OLS, return R², adjusted R², F-stat, AIC."""
    n, k = X.shape
    model = LinearRegression().fit(X, y)
    y_pred = model.predict(X)
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - y.mean())**2)
    r2 = 1 - ss_res / ss_tot
    r2_adj = 1 - (1 - r2) * (n - 1) / (n - k - 1)
    # AIC via log-likelihood of OLS residuals
    sigma2 = ss_res / n
    log_lik = -n/2 * (np.log(2*np.pi*sigma2) + 1)
    aic = 2*(k+2) - 2*log_lik   # +2 for intercept + sigma
    return {"r2": round(r2,4), "r2_adj": round(r2_adj,4), "aic": round(aic,2),
            "coefs": dict(zip(range(k), [round(float(c),4) for c in model.coef_])),
            "intercept": round(float(model.intercept_),4)}


def cv_rmse(X: np.ndarray, y: np.ndarray, k: int = 5) -> float:
    kf = KFold(n_splits=k, shuffle=True, random_state=42)
    rmses = []
    for tr, te in kf.split(X):
        m = LinearRegression().fit(X[tr], y[tr])
        pred = m.predict(X[te])
        rmses.append(np.sqrt(mean_squared_error(y[te], pred)))
    return round(float(np.mean(rmses)), 4)


# ─── STEP 1 ───────────────────────────────────────────────────────────────────

def step1(df: pd.DataFrame) -> dict:
    print("\n" + "="*70)
    print("STEP 1 — OLS: ada_log10 ~ source_class + hpr_combined_score")
    print("="*70)

    # Only rows with HPR
    sub = df[df["hpr_combined_score"].notna()].copy()
    le = LabelEncoder()
    sub["class_code"] = le.fit_transform(sub["source_class"])  # Fully_human=0, Humanized=1

    # Model A: class only
    Xa = sub[["class_code"]].values
    ya = sub[TARGET_LOG].values
    mA = ols_r2(Xa, ya)
    cv_A = cv_rmse(Xa, ya)
    print(f"\nModel A (class only):      R²={mA['r2']:.4f}  R²adj={mA['r2_adj']:.4f}  AIC={mA['aic']:.1f}  CV-RMSE={cv_A}")

    # Model B: HPR only
    Xb = sub[["hpr_combined_score"]].values
    mB = ols_r2(Xb, ya)
    cv_B = cv_rmse(Xb, ya)
    print(f"Model B (HPR only):        R²={mB['r2']:.4f}  R²adj={mB['r2_adj']:.4f}  AIC={mB['aic']:.1f}  CV-RMSE={cv_B}")

    # Model C: class + HPR
    Xc = sub[["class_code","hpr_combined_score"]].values
    mC = ols_r2(Xc, ya)
    cv_C = cv_rmse(Xc, ya)
    print(f"Model C (class + HPR):     R²={mC['r2']:.4f}  R²adj={mC['r2_adj']:.4f}  AIC={mC['aic']:.1f}  CV-RMSE={cv_C}")

    # HPR marginal contribution = R²(C) - R²(A)
    delta_r2_hpr   = round(mC["r2"] - mA["r2"], 4)
    delta_r2_class = round(mC["r2"] - mB["r2"], 4)
    print(f"\n  Marginal R² of HPR   (beyond class):  ΔR²={delta_r2_hpr}")
    print(f"  Marginal R² of class (beyond HPR):    ΔR²={delta_r2_class}")
    print(f"\n  Class encodings: {dict(zip(le.classes_, le.transform(le.classes_)))}")

    # Residuals: top over- and under-predicted
    sub_c = sub.copy()
    from sklearn.linear_model import LinearRegression
    m_fit = LinearRegression().fit(Xc, ya)
    sub_c["pred_log"] = m_fit.predict(Xc)
    sub_c["resid"]    = sub_c[TARGET_LOG] - sub_c["pred_log"]
    # Back-transform
    sub_c["ada_actual"]    = np.power(10, sub_c[TARGET_LOG]) - 0.1
    sub_c["ada_predicted"] = np.power(10, sub_c["pred_log"]) - 0.1

    print("\n  Top 10 over-predicted (model says low, reality high):")
    over = sub_c.nlargest(10, "resid")[["antibody_name","ada_actual","ada_predicted","source_class","hpr_combined_score","resid"]]
    for _, r in over.iterrows():
        print(f"    {r['antibody_name']:<35s} actual={r['ada_actual']:.1f}%  pred={r['ada_predicted']:.1f}%  "
              f"cls={r['source_class']}  HPR={r['hpr_combined_score']:.3f}")

    print("\n  Top 10 under-predicted (model says high, reality low):")
    under = sub_c.nsmallest(10, "resid")[["antibody_name","ada_actual","ada_predicted","source_class","hpr_combined_score","resid"]]
    for _, r in under.iterrows():
        print(f"    {r['antibody_name']:<35s} actual={r['ada_actual']:.1f}%  pred={r['ada_predicted']:.1f}%  "
              f"cls={r['source_class']}  HPR={r['hpr_combined_score']:.3f}")

    return {
        "model_A_class_only":     {**mA, "cv_rmse": cv_A},
        "model_B_hpr_only":       {**mB, "cv_rmse": cv_B},
        "model_C_class_hpr":      {**mC, "cv_rmse": cv_C},
        "marginal_r2_hpr":        delta_r2_hpr,
        "marginal_r2_class":      delta_r2_class,
        "n": int(len(sub)),
    }


# ─── STEP 2 ───────────────────────────────────────────────────────────────────

def step2(df: pd.DataFrame) -> dict:
    print("\n" + "="*70)
    print("STEP 2 — Clinical Confounders")
    print("="*70)
    results = {}

    # --- 2A: ADA by confounder groups -----------------------------------------
    for field, label in [("route_clean","Route"), ("disease_area","Disease area"), ("assay_type","Assay type")]:
        print(f"\n  {label} × ADA% distribution:")
        grp = df.groupby(field)[TARGET_RAW].agg(
            n="count", median="median", mean="mean", p75=lambda x: x.quantile(.75)
        ).round(2).sort_values("median", ascending=False)
        print(grp.to_string())
        results[f"ada_by_{field}"] = grp.to_dict()

    # --- 2B: HPR by group (does HPR differ across clinical groups?) ------------
    print("\n  HPR by route (does systematic HPR bias exist across routes?):")
    for route, sub in df[df["route_clean"].isin(["IV","SC"])].groupby("route_clean"):
        hpr = sub["hpr_combined_score"].dropna()
        ada = sub[TARGET_RAW].dropna()
        print(f"    {route}: n_HPR={len(hpr)}, HPR median={hpr.median():.3f}, "
              f"n_ADA={len(ada)}, ADA median={ada.median():.1f}%")

    # --- 2C: Partial Spearman controlling clinical confounders ----------------
    print("\n  Partial Spearman — HPR vs ADA, controlling each confounder separately:")

    # encode categoricals
    le_route   = LabelEncoder()
    le_disease = LabelEncoder()
    le_assay   = LabelEncoder()

    df2 = df.copy()
    df2["route_code"]   = le_route.fit_transform(df2["route_clean"])
    df2["disease_code"] = le_disease.fit_transform(df2["disease_area"])
    df2["assay_code"]   = le_assay.fit_transform(df2["assay_type"])
    df2["class_code"]   = LabelEncoder().fit_transform(df2["source_class"])

    hpr = df2["hpr_combined_score"]
    ada = df2[TARGET_LOG]

    confounders = {
        "class only":                    [df2["class_code"]],
        "class + route":                 [df2["class_code"], df2["route_code"]],
        "class + disease":               [df2["class_code"], df2["disease_code"]],
        "class + assay":                 [df2["class_code"], df2["assay_code"]],
        "class + route + disease":       [df2["class_code"], df2["route_code"], df2["disease_code"]],
        "class + route + assay":         [df2["class_code"], df2["route_code"], df2["assay_code"]],
        "class + disease + assay":       [df2["class_code"], df2["disease_code"], df2["assay_code"]],
        "class + route + disease + assay":[df2["class_code"], df2["route_code"], df2["disease_code"], df2["assay_code"]],
    }

    partial_results = {}
    for name, ctrl in confounders.items():
        r = partial_spearman_resid(hpr, ada, ctrl)
        rho_s = f"{r['partial_rho']:+.4f}" if r["partial_rho"] is not None else "—"
        print(f"    Controlling {name:<45s}: partial_rho={rho_s}  p={r.get('p','—')}  {r.get('sig','')}")
        partial_results[name] = r
    results["partial_spearman_hpr"] = partial_results

    # --- 2D: ADA Kruskal-Wallis by assay type ---------------------------------
    print("\n  Kruskal-Wallis ADA% across assay types (ECL_MSD vs ELISA vs unknown):")
    groups_assay = [df[df["assay_type"]==t][TARGET_RAW].dropna().values
                    for t in ["ECL_MSD","ELISA","unknown"] if (df["assay_type"]==t).sum() >= 3]
    labels_assay = [t for t in ["ECL_MSD","ELISA","unknown"] if (df["assay_type"]==t).sum() >= 3]
    if len(groups_assay) >= 2:
        H, p_kw = stats.kruskal(*groups_assay)
        print(f"    H={H:.2f}  p={p_kw:.4f}  groups={labels_assay}")
        for lab, grp in zip(labels_assay, groups_assay):
            print(f"    {lab:<12s}: n={len(grp)}, median={np.median(grp):.1f}%, mean={np.mean(grp):.1f}%")
        results["kruskal_assay"] = {"H": float(H), "p": float(p_kw), "groups": labels_assay}

    # --- 2E: ADA Kruskal-Wallis by route (IV vs SC) ---------------------------
    print("\n  Mann-Whitney ADA%: IV vs SC:")
    iv_ada = df[df["route_clean"]=="IV"][TARGET_RAW].dropna()
    sc_ada = df[df["route_clean"]=="SC"][TARGET_RAW].dropna()
    if len(iv_ada) >= 5 and len(sc_ada) >= 5:
        U, p_mw = stats.mannwhitneyu(iv_ada, sc_ada, alternative="two-sided")
        print(f"    IV (n={len(iv_ada)}): median={iv_ada.median():.1f}%  "
              f"SC (n={len(sc_ada)}): median={sc_ada.median():.1f}%  p={p_mw:.4f}")
        results["mannwhitney_iv_vs_sc"] = {"U": float(U), "p": float(p_mw),
                                            "iv_median": float(iv_ada.median()),
                                            "sc_median": float(sc_ada.median()),
                                            "iv_n": len(iv_ada), "sc_n": len(sc_ada)}

    # --- 2F: Within disease area, does HPR still predict? ---------------------
    print("\n  HPR vs ADA correlation within disease area:")
    for area in ["oncology","immunology","other","unknown"]:
        sub = df[df["disease_area"]==area]
        if len(sub) < 8: continue
        r = spearman(sub["hpr_combined_score"], sub[TARGET_LOG])
        if r["rho"] is not None:
            print(f"    {area:<15s}: n={r['n']}, rho={r['rho']:+.4f}, p={r['p']:.4f} {r['sig']}")

    return results


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    df = load_data()
    all_results = {}

    all_results["step1"] = step1(df)
    all_results["step2"] = step2(df)

    # Print summary
    print("\n" + "="*70)
    print("COMBINED SUMMARY")
    print("="*70)
    s1 = all_results["step1"]
    print(f"  2-factor model (class + HPR): R²={s1['model_C_class_hpr']['r2']:.4f}  "
          f"CV-RMSE={s1['model_C_class_hpr']['cv_rmse']}")
    print(f"  HPR marginal R²: {s1['marginal_r2_hpr']} ({s1['marginal_r2_hpr']*100:.1f}% of ADA variance beyond class)")
    print(f"  Class marginal R²: {s1['marginal_r2_class']} beyond HPR")

    best_partial = all_results["step2"]["partial_spearman_hpr"].get("class + route + disease + assay", {})
    if best_partial.get("partial_rho") is not None:
        print(f"  HPR partial rho (all clinical confounders): {best_partial['partial_rho']:+.4f}  "
              f"p={best_partial['p']:.4f}  {best_partial.get('sig','')}")

    # Save JSON
    out_json = OUT_DIR / "ada_step1_step2_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nSaved: {out_json}")


if __name__ == "__main__":
    main()
