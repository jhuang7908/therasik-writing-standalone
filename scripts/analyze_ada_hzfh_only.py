#!/usr/bin/env python3
"""
ADA Multi-factor analysis restricted to Humanized + Fully Human antibodies only.
Excludes: Murine, Chimeric, VHH, Synthetic/TCR, Bispecific.
Goal: clean within-therapeutic-class correlations without cross-class HPR confound.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

MASTER_CSV  = REPO / "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
CLUSTER_CSV = REPO / "data/immunogenicity_knowledge_base/reports/hpr_hla_cluster_analysis/per_record_low_hpr_hla_cluster_counts.csv"
OUT_DIR     = REPO / "data/immunogenicity_knowledge_base/reports/ada_hzfh_analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_RAW = "ada_first_pct"
TARGET_LOG = "ada_log10"

INCLUDE_CLASSES = {"Humanized", "Fully_human"}

ALL_FEATURES = {
    "hpr_combined_score":              "HPR ()",
    "low_hpr_hla_clusters_fr_surface": "Low-HPR HLA-II clusters",
    "hydro_patch_max9":                " max (SASA)",
    "surf_n_patches":                  "",
    "instability_index":               "",
    "pI":                              "",
    "GRAVY":                           "GRAVY",
}


def spearman(x: pd.Series, y: pd.Series) -> dict:
    valid = x.notna() & y.notna()
    x, y = x[valid], y[valid]
    n = len(x)
    if n < 8:
        return {"n": n, "rho": None, "p": None, "note": "n<8"}
    if x.nunique() < 3 or y.nunique() < 3:
        return {"n": n, "rho": None, "p": None, "note": "few_unique"}
    rho, p = stats.spearmanr(x, y)
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    return {"n": n, "rho": round(float(rho), 4), "p": round(float(p), 6), "sig": sig}


def partial_spearman(feat: pd.Series, target: pd.Series, confounders: list[pd.Series]) -> dict:
    mask = feat.notna() & target.notna()
    for c in confounders:
        mask &= c.notna()
    n = mask.sum()
    if n < 10:
        return {"n": int(n), "partial_rho": None, "p": None, "note": "n<10"}
    f = feat[mask].rank()
    t = target[mask].rank()
    conf_ranks = np.column_stack([c[mask].rank().values for c in confounders])
    def resid(y_rank):
        X = np.column_stack([np.ones(len(conf_ranks)), conf_ranks])
        b = np.linalg.lstsq(X, y_rank, rcond=None)[0]
        return y_rank - X @ b
    r, p = stats.pearsonr(resid(f.values), resid(t.values))
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    return {"n": int(n), "partial_rho": round(float(r), 4), "p": round(float(p), 6), "sig": sig}


def normalize_class(v: object) -> str:
    if not isinstance(v, str):
        return "Unknown"
    v = v.strip().lower()
    if v in ("fully_human", "genetically_human", "fully human"):
        return "Fully_human"
    if "humanis" in v or "humaniz" in v:
        return "Humanized"
    if "chimeric" in v:
        return "Chimeric"
    if v == "murine":
        return "Murine"
    if v == "vhh" or "nanobody" in v:
        return "VHH"
    if "bispecific" in v:
        return "Bispecific"
    return "Other"


def load_data() -> pd.DataFrame:
    master = pd.read_csv(MASTER_CSV, low_memory=False)
    cluster = pd.read_csv(CLUSTER_CSV)

    master = master[master[TARGET_RAW].notna()].copy()

    cluster_sub = cluster[
        [c for c in ["antibody_name","source_class","low_hpr_hla_clusters_fr_surface",
                     "high_hpr_hla_clusters_fr_surface","n_low_hpr_15mer_windows",
                     "n_high_hpr_15mer_windows","tcia_score"] if c in cluster.columns]
    ].copy()

    df = master.merge(
        cluster_sub.rename(columns={"antibody_name": "name_cluster"}),
        left_on="antibody_name", right_on="name_cluster", how="left",
    ).drop(columns=["name_cluster"], errors="ignore")

    if "source_class_y" in df.columns:
        df = df.drop(columns=["source_class_y"], errors="ignore")
    if "source_class_x" in df.columns:
        df = df.rename(columns={"source_class_x": "source_class"})

    df["source_class"] = df["thera_genetics_class"].apply(normalize_class)

    # ─── Filter to HZ + FH only ───
    before = len(df)
    df = df[df["source_class"].isin(INCLUDE_CLASSES)].copy()
    print(f"Filtered {before} → {len(df)} records (Humanized + Fully Human only)")
    print(f"Source class dist: {df['source_class'].value_counts().to_dict()}")

    df[TARGET_LOG] = np.log10(df[TARGET_RAW] + 0.1)

    le = LabelEncoder()
    df["source_class_code"] = le.fit_transform(df["source_class"])

    return df


def main():
    df = load_data()
    results = {}

    # ─── Layer 1: Univariate ──────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("LAYER 1 — Univariate Spearman (HZ + FH only)")
    print("=" * 70)
    univ = {}
    for feat, label in ALL_FEATURES.items():
        if feat not in df.columns:
            continue
        r = spearman(df[feat], df[TARGET_LOG])
        univ[feat] = r
        rho_s = f"{r['rho']:+.4f}" if r["rho"] is not None else "—"
        sig   = r.get("sig", "")
        print(f"  {label:<40s} | n={r['n']:3d} | rho={rho_s} | p={r.get('p','—'):<12} | {sig}")
    results["layer1_univariate"] = univ

    # ─── Layer 2: Stratified HPR by class ────────────────────────────────────
    print("\n" + "=" * 70)
    print("LAYER 2 — HPR × ADA stratified by class (HZ vs FH)")
    print("=" * 70)
    strat = {}
    for cls in ["Humanized", "Fully_human"]:
        sub = df[df["source_class"] == cls]
        r = spearman(sub["hpr_combined_score"], sub[TARGET_LOG])
        strat[cls] = r
        rho_s = f"{r['rho']:+.4f}" if r["rho"] is not None else "—"
        print(f"  {cls:<20s} | n={r['n']:3d} | HPR rho={rho_s} | p={r.get('p','—'):<12} | {r.get('sig','')}")
    results["layer2_stratified_hpr"] = strat

    # Also test each factor stratified
    print("\n  [All factors by class]")
    for feat, label in ALL_FEATURES.items():
        if feat not in df.columns:
            continue
        for cls in ["Humanized", "Fully_human"]:
            sub = df[df["source_class"] == cls]
            r = spearman(sub[feat], sub[TARGET_LOG])
            if r["rho"] is not None:
                print(f"  {cls:<14s} | {label:<35s} | n={r['n']:3d} | rho={r['rho']:+.4f} | {r.get('sig','')}")

    # ─── Layer 3: Partial (control source_class only, since HPR is now a feature) ──
    print("\n" + "=" * 70)
    print("LAYER 3 — Partial Spearman (controlling source_class_code)")
    print("=" * 70)
    partial = {}
    ctrl = [df["source_class_code"]]
    for feat, label in ALL_FEATURES.items():
        if feat not in df.columns:
            continue
        r = partial_spearman(df[feat], df[TARGET_LOG], ctrl)
        partial[feat] = r
        rho_s = f"{r['partial_rho']:+.4f}" if r["partial_rho"] is not None else "—"
        print(f"  {label:<40s} | n={r['n']:3d} | partial_rho={rho_s} | p={r.get('p','—'):<12} | {r.get('sig','')}")
    results["layer3_partial"] = partial

    # ─── Layer 4: RF importance ───────────────────────────────────────────────
    feat_cols = [f for f in ALL_FEATURES if f in df.columns]
    complete = df[feat_cols + [TARGET_LOG]].dropna()
    print(f"\n  RF training set: {len(complete)} complete cases")
    if len(complete) >= 20:
        X = complete[feat_cols].values
        y = complete[TARGET_LOG].values
        rf = RandomForestRegressor(n_estimators=500, random_state=42)
        rf.fit(X, y)
        importances = dict(zip(feat_cols, [round(float(v), 4) for v in rf.feature_importances_]))
        print("\nLayer 4 — RF Feature Importances:")
        for k, v in sorted(importances.items(), key=lambda x: -x[1]):
            bar = "█" * int(v * 100)
            print(f"  {k:<40s}: {v:.4f}  {bar}")
        results["layer4_rf_importance"] = importances

    # ─── ADA statistics by class ──────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("ADA% STATISTICS BY CLASS")
    print("=" * 70)
    ada_stats = {}
    for cls in ["Humanized", "Fully_human", "ALL"]:
        sub = df if cls == "ALL" else df[df["source_class"] == cls]
        ada = sub[TARGET_RAW].dropna()
        stats_d = {
            "n": len(ada),
            "median": round(float(ada.median()), 2),
            "mean": round(float(ada.mean()), 2),
            "p25": round(float(ada.quantile(0.25)), 2),
            "p75": round(float(ada.quantile(0.75)), 2),
            "max": round(float(ada.max()), 2),
        }
        ada_stats[cls] = stats_d
        print(f"  {cls:<14s} n={stats_d['n']:3d} | median={stats_d['median']:5.1f}% | "
              f"mean={stats_d['mean']:5.1f}% | IQR=[{stats_d['p25']},{stats_d['p75']}]% | max={stats_d['max']}%")
    results["ada_stats"] = ada_stats

    # ─── Mann-Whitney HZ vs FH ────────────────────────────────────────────────
    hz_ada = df[df["source_class"] == "Humanized"][TARGET_RAW].dropna()
    fh_ada = df[df["source_class"] == "Fully_human"][TARGET_RAW].dropna()
    u, p_mw = stats.mannwhitneyu(hz_ada, fh_ada, alternative="two-sided")
    print(f"\n  Mann-Whitney Humanized vs Fully Human ADA: U={u:.0f}, p={p_mw:.4f} "
          f"{'*' if p_mw < 0.05 else ''}")
    results["mann_whitney_hz_vs_fh"] = {"U": float(u), "p": round(float(p_mw), 6)}

    # ─── HPR statistics by class ──────────────────────────────────────────────
    print("\n  HPR combined score by class:")
    for cls in ["Humanized", "Fully_human"]:
        sub = df[df["source_class"] == cls]["hpr_combined_score"].dropna()
        print(f"  {cls:<14s} n={len(sub):3d} | median={sub.median():.3f} | mean={sub.mean():.3f} | "
              f"range=[{sub.min():.3f}, {sub.max():.3f}]")

    # Save
    out_json = OUT_DIR / "ada_hzfh_analysis.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved: {out_json}")


if __name__ == "__main__":
    main()
