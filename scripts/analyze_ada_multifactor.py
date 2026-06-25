#!/usr/bin/env python3
"""
 ADA  — Layer 1-4
===================================
Layer 1:  Spearman  (7  × ADA%)
Layer 2:  (human / humanized / chimeric / murine / VHH)
Layer 3:  (Spearman Rank Residuals;  HPR + source_class)
Layer 4: RandomForest  + 

:
  -  HPR ,  HLA-II cluster →  low_hpr_hla_clusters_fr_surface
  - ADA : log10(ada_first_pct + 0.1) 
  -  source_class 
"""
from __future__ import annotations
import argparse
import json
import math
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

# ───  ────────────────────────────────────────────────────────────────
MASTER_CSV  = REPO / "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
CLUSTER_CSV = REPO / "data/immunogenicity_knowledge_base/reports/hpr_hla_cluster_analysis/per_record_low_hpr_hla_cluster_counts.csv"
OUT_DIR     = REPO / "data/immunogenicity_knowledge_base/reports/ada_multifactor_analysis"

# ───  ─────────────────────────────────────────────────────────────────
#  ()
IMMUNE_FEATURES = {
    "hpr_combined_score":             "HPR ()",
    "low_hpr_hla_clusters_fr_surface": "Low-HPR HLA-II  (FR/)",
}
BIOPHYSICAL_FEATURES = {
    "hydro_patch_max9":  " (SASA)",
    "surf_n_patches":    "",
    "instability_index": " (ProtParam)",
    "pI":                "",
    "GRAVY":             "GRAVY ()",
}
ALL_FEATURES = {**IMMUNE_FEATURES, **BIOPHYSICAL_FEATURES}

TARGET_RAW = "ada_first_pct"
TARGET_LOG = "ada_log10"


# ───  ─────────────────────────────────────────────────────────────────
def spearman(x: pd.Series, y: pd.Series) -> dict:
    valid = x.notna() & y.notna()
    x, y = x[valid], y[valid]
    n = len(x)
    if n < 8:
        return {"n": n, "rho": None, "p": None, "note": "n<8 skip"}
    if x.nunique() < 3 or y.nunique() < 3:
        return {"n": n, "rho": None, "p": None, "note": "too_few_unique"}
    rho, p = stats.spearmanr(x, y)
    stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    return {"n": n, "rho": round(float(rho), 4), "p": round(float(p), 6), "sig": stars}


def partial_spearman_rank_residual(
    feat: pd.Series, target: pd.Series, confounders: list[pd.Series]
) -> dict:
    """
    Partial Spearman correlation via rank-residual projection.
    Steps:
      1. Rank all variables.
      2. OLS regress feat_rank on confounders_ranks → residuals_feat.
      3. OLS regress target_rank on confounders_ranks → residuals_target.
      4. Pearson corr on residuals ≈ partial Spearman.
    """
    # Align valid rows across feat, target, and all confounders
    mask = feat.notna() & target.notna()
    for c in confounders:
        mask &= c.notna()
    if mask.sum() < 12:
        return {"n": int(mask.sum()), "partial_rho": None, "p": None, "note": "n<12 skip"}

    f = feat[mask].rank()
    t = target[mask].rank()
    conf_ranks = np.column_stack([c[mask].rank().values for c in confounders])

    def residuals(y_rank: np.ndarray) -> np.ndarray:
        X = np.column_stack([np.ones(len(conf_ranks)), conf_ranks])
        b = np.linalg.lstsq(X, y_rank, rcond=None)[0]
        return y_rank - X @ b

    resid_f = residuals(f.values)
    resid_t = residuals(t.values)
    r, p = stats.pearsonr(resid_f, resid_t)
    stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    return {
        "n": int(mask.sum()),
        "partial_rho": round(float(r), 4),
        "p": round(float(p), 6),
        "sig": stars,
    }


def stars_label(p: float | None) -> str:
    if p is None: return ""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


# ───  ────────────────────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    master = pd.read_csv(MASTER_CSV)
    cluster = pd.read_csv(CLUSTER_CSV)

    #  ADA 
    master = master[master[TARGET_RAW].notna()].copy()

    #  cluster  ()
    cluster_cols = [
        "antibody_name",
        "source_class",
        "low_hpr_hla_clusters_fr_surface",
        "high_hpr_hla_clusters_fr_surface",
        "low_hpr_hla_clusters_all_region",
        "n_low_hpr_15mer_windows",
        "n_high_hpr_15mer_windows",
        "tcia_score",
    ]
    cluster_sub = cluster[[c for c in cluster_cols if c in cluster.columns]].copy()
    df = master.merge(
        cluster_sub.rename(columns={"antibody_name": "name_cluster"}),
        left_on="antibody_name", right_on="name_cluster", how="left",
    )
    df = df.drop(columns=["name_cluster"], errors="ignore")

    # （ master  thera_genetics_class ）
    def _normalize_class(v: object) -> str:
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

    df["source_class"] = df["thera_genetics_class"].apply(_normalize_class)

    #  cluster  source_class ( NaN) — 
    if "source_class_y" in df.columns:
        df = df.drop(columns=["source_class_y"], errors="ignore")
    if "source_class_x" in df.columns:
        df = df.rename(columns={"source_class_x": "source_class"})

    # ADA 
    df[TARGET_LOG] = np.log10(df[TARGET_RAW] + 0.1)

    # source_class  ()
    le = LabelEncoder()
    df["source_class_code"] = le.fit_transform(df["source_class"].fillna("Unknown"))

    return df


# ─── Layer 1:  Spearman ─────────────────────────────────────────────────
def layer1_univariate(df: pd.DataFrame) -> list[dict]:
    print("\n" + "=" * 70)
    print("LAYER 1 —  Spearman  (vs ada_log10)")
    print("=" * 70)
    header = f"{'Factor':35s} | {'label':30s} | {'n':5s} | {'rho':7s} | {'p':10s} | sig"
    print(header)
    print("-" * len(header))

    rows = []
    for feat, label in ALL_FEATURES.items():
        if feat not in df.columns:
            print(f"  {feat:35s} NOT IN DATASET")
            continue
        res = spearman(df[feat], df[TARGET_LOG])
        rho_s = f"{res['rho']:.4f}" if res["rho"] is not None else "—"
        p_s   = f"{res['p']:.2e}"  if res["p"]   is not None else "—"
        print(f"  {feat:35s} | {label:30s} | {res['n']:5d} | {rho_s:7s} | {p_s:10s} | {res.get('sig','')}")
        rows.append({"factor": feat, "label": label, **res, "layer": "univariate"})

    # :  (hydro_patch 120，)
    if "hydro_patch_max9" in df.columns:
        has_patch = df["hydro_patch_max9"].notna()
        ada_w  = df[has_patch][TARGET_RAW].median()
        ada_wo = df[~has_patch][TARGET_RAW].median()
        print(f"\n  [Bias Check] hydro_patch_max9 coverage:")
        print(f"    Has 3D patch data (n={has_patch.sum()}): ADA median = {ada_w:.1f}%")
        print(f"    No  3D patch data (n={(~has_patch).sum()}): ADA median = {ada_wo:.1f}%  ← bias if significantly lower")
        # source_class composition in covered vs uncovered
        if "source_class" in df.columns:
            print("    Source class split (with vs without 3D patch):")
            for sc in ["Fully_human","Humanized","Chimeric","Murine","VHH"]:
                n_w  = (has_patch & (df["source_class"]==sc)).sum()
                n_wo = (~has_patch & (df["source_class"]==sc)).sum()
                print(f"      {sc:15s}: covered={n_w}, uncovered={n_wo}")

    return rows


# ─── Layer 2:  ────────────────────────────────────────────────────
def layer2_stratified(df: pd.DataFrame) -> list[dict]:
    print("\n" + "=" * 70)
    print("LAYER 2 —  Spearman  (Low-HPR cluster vs ADA)")
    print("=" * 70)

    groups = df["source_class"].value_counts()
    print(f"Source class distribution: {dict(groups)}")
    print()

    rows = []
    target_feat = "low_hpr_hla_clusters_fr_surface"
    if target_feat not in df.columns:
        print("  low_hpr_hla_clusters_fr_surface not available — skipping Layer 2")
        return rows

    for sc in sorted(df["source_class"].dropna().unique()):
        grp = df[df["source_class"] == sc].copy()
        res = spearman(grp[target_feat], grp[TARGET_LOG])
        rho_s = f"{res['rho']:.4f}" if res["rho"] is not None else "—"
        p_s   = f"{res['p']:.2e}"  if res["p"]   is not None else "—"
        print(f"  {sc:30s} | n={res['n']:5d} | rho={rho_s} | p={p_s} {res.get('sig','')}")
        rows.append({"source_class": sc, "factor": target_feat, **res, "layer": "stratified"})

    # Also do HPR in each group
    print()
    print("  [HPR vs ADA by source class]")
    for sc in sorted(df["source_class"].dropna().unique()):
        grp = df[df["source_class"] == sc].copy()
        res = spearman(grp["hpr_combined_score"], grp[TARGET_LOG])
        rho_s = f"{res['rho']:.4f}" if res["rho"] is not None else "—"
        p_s   = f"{res['p']:.2e}"  if res["p"]   is not None else "—"
        print(f"  HPR | {sc:30s} | n={res['n']:5d} | rho={rho_s} | p={p_s} {res.get('sig','')}")
        rows.append({"source_class": sc, "factor": "hpr_combined_score", **res, "layer": "stratified_hpr"})

    return rows


# ─── Layer 3:  ─────────────────────────────────────────────────────────
def layer3_partial(df: pd.DataFrame) -> list[dict]:
    print("\n" + "=" * 70)
    print("LAYER 3 —  ( HPR + source_class_code)")
    print("=" * 70)
    print("  : partial_rho  HPR ,  ADA ")
    print()

    confounders = [df["hpr_combined_score"], df["source_class_code"].astype(float)]
    conf_label = "HPR + source_class"

    rows = []
    header = f"{'Factor':35s} | {'n':5s} | {'partial_rho':11s} | {'p':10s} | sig"
    print(header)
    print("-" * len(header))

    for feat, label in ALL_FEATURES.items():
        if feat == "hpr_combined_score":
            continue  # HPR ，
        if feat not in df.columns:
            print(f"  {feat:35s} NOT IN DATASET")
            continue
        res = partial_spearman_rank_residual(df[feat], df[TARGET_LOG], confounders)
        rho_s = f"{res['partial_rho']:.4f}" if res["partial_rho"] is not None else "—"
        p_s   = f"{res['p']:.2e}"          if res["p"]           is not None else "—"
        print(f"  {feat:35s} | {res['n']:5d} | {rho_s:11s} | {p_s:10s} | {res.get('sig','')}")
        rows.append({"factor": feat, "label": label, "controlled_for": conf_label, **res, "layer": "partial"})

    return rows


# ─── Layer 4: RandomForest  +  ──────────────────────────
def layer4_rf_and_quadrant(df: pd.DataFrame) -> dict:
    print("\n" + "=" * 70)
    print("LAYER 4A — RandomForest ")
    print("=" * 70)

    #  7 
    feat_cols = [c for c in ALL_FEATURES.keys() if c in df.columns]
    sub = df[feat_cols + [TARGET_LOG]].dropna()
    print(f"  RF training set: {len(sub)} records (complete cases for all features)")

    rf_result = {}
    if len(sub) < 20:
        print("  Too few complete cases for RF — skipping")
    else:
        X = sub[feat_cols].values
        y = sub[TARGET_LOG].values
        rf = RandomForestRegressor(n_estimators=500, max_features="sqrt",
                                   min_samples_leaf=3, random_state=42)
        rf.fit(X, y)
        importances = rf.feature_importances_
        rf_result = {feat_cols[i]: round(float(importances[i]), 4)
                     for i in np.argsort(-importances)}
        print("\n  Feature Importances (descending):")
        for k, v in rf_result.items():
            bar = "█" * int(v * 100)
            print(f"    {k:35s}: {v:.4f}  {bar}")

    print("\n" + "=" * 70)
    print("LAYER 4B —  (Low-HPR Cluster × Hydro Patch vs ADA)")
    print("=" * 70)

    quadrant_result = {}
    if ("low_hpr_hla_clusters_fr_surface" in df.columns and
            "hydro_patch_max9" in df.columns):
        qdf = df[["low_hpr_hla_clusters_fr_surface", "hydro_patch_max9",
                  TARGET_LOG, TARGET_RAW]].dropna().copy()
        c_med = qdf["low_hpr_hla_clusters_fr_surface"].median()
        h_med = qdf["hydro_patch_max9"].median()

        qdf["quadrant"] = qdf.apply(
            lambda r: (
                "HiClust_HiHydro" if r["low_hpr_hla_clusters_fr_surface"] >= c_med and r["hydro_patch_max9"] >= h_med else
                "HiClust_LoHydro" if r["low_hpr_hla_clusters_fr_surface"] >= c_med else
                "LoClust_HiHydro" if r["hydro_patch_max9"] >= h_med else
                "LoClust_LoHydro"
            ), axis=1
        )

        print(f"\n  Median split: cluster_med={c_med:.1f}, hydro_patch_med={h_med:.1f}")
        print(f"  {'Quadrant':25s} | {'n':5s} | {'ADA median %':15s} | {'ADA mean %':12s}")
        print("  " + "-" * 65)
        order = ["HiClust_HiHydro", "HiClust_LoHydro", "LoClust_HiHydro", "LoClust_LoHydro"]
        for q in order:
            g = qdf[qdf["quadrant"] == q][TARGET_RAW]
            if len(g) == 0:
                continue
            print(f"  {q:25s} | {len(g):5d} | {g.median():15.2f} | {g.mean():12.2f}")
            quadrant_result[q] = {
                "n": len(g),
                "ada_median_pct": round(float(g.median()), 3),
                "ada_mean_pct": round(float(g.mean()), 3),
            }

        # Kruskal-Wallis test across quadrants
        groups_kw = [qdf[qdf["quadrant"] == q][TARGET_LOG].values for q in order if len(qdf[qdf["quadrant"] == q]) > 0]
        if len(groups_kw) >= 2:
            kw_stat, kw_p = stats.kruskal(*groups_kw)
            print(f"\n  Kruskal-Wallis across quadrants: H={kw_stat:.2f}, p={kw_p:.4e} {stars_label(kw_p)}")
            quadrant_result["kruskal_wallis"] = {"H": round(kw_stat, 4), "p": round(kw_p, 6)}

    return {"rf_importances": rf_result, "quadrant_analysis": quadrant_result}


# ───  ────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ADA ")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 
    df = load_data()
    print(f"\nLoaded {len(df)} records with numeric ADA (master + cluster merged)")

    # 
    l1 = layer1_univariate(df)
    l2 = layer2_stratified(df)
    l3 = layer3_partial(df)
    l4 = layer4_rf_and_quadrant(df)

    # ──  ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY —  ADA ")
    print("=" * 70)

    #  L1  L3 
    l1_map = {r["factor"]: r for r in l1}
    l3_map = {r["factor"]: r for r in l3}
    rf_map = l4.get("rf_importances", {})

    ranking_rows = []
    for feat, label in ALL_FEATURES.items():
        row = {"factor": feat, "label": label}
        if feat in l1_map:
            r = l1_map[feat]
            row["univ_rho"] = r.get("rho")
            row["univ_p"]   = r.get("p")
            row["univ_n"]   = r.get("n")
            row["univ_sig"] = r.get("sig", "")
        if feat in l3_map:
            r = l3_map[feat]
            row["partial_rho"] = r.get("partial_rho")
            row["partial_p"]   = r.get("p")
            row["partial_sig"] = r.get("sig", "")
        row["rf_importance"] = rf_map.get(feat)
        ranking_rows.append(row)

    #  RF importance （）,  |univ_rho|
    ranking_rows.sort(
        key=lambda r: (r.get("rf_importance") or 0), reverse=True
    )

    print(f"\n{'Rank':4s} | {'Factor':35s} | {'Univ ρ':7s} | {'Partial ρ':10s} | {'RF Imp':7s}")
    print("-" * 80)
    for i, row in enumerate(ranking_rows, 1):
        univ_r = f"{row.get('univ_rho', ''):.4f}" if row.get("univ_rho") is not None else "—"
        part_r = f"{row.get('partial_rho', ''):.4f}" if row.get("partial_rho") is not None else "—"
        rf_i   = f"{row.get('rf_importance'):.4f}" if row.get("rf_importance") is not None else "—"
        univ_s = row.get("univ_sig", "")
        part_s = row.get("partial_sig", "")
        print(f" {i:3d} | {row['factor']:35s} | {univ_r:7s}{univ_s:<3s} | {part_r:10s}{part_s:<3s} | {rf_i}")

    # ──  ────────────────────────────────────────────────────────────────
    summary = {
        "layer1_univariate":     l1,
        "layer2_stratified":     l2,
        "layer3_partial":        l3,
        "layer4_rf_quadrant":    l4,
        "ranking_table":         ranking_rows,
    }
    out_json = out / "ada_multifactor_summary.json"
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print(f"\n  Results saved → {out_json}")

    #  CSV
    pd.DataFrame(ranking_rows).to_csv(out / "ada_multifactor_ranking.csv", index=False)
    print(f"  Ranking table → {out / 'ada_multifactor_ranking.csv'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
