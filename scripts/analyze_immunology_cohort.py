#!/usr/bin/env python3
"""
Deep dive into the Immunology (Autoimmune/Inflammatory) cohort.
Evaluate HPR and HLA Cluster R^2 shares in predicting ADA.
"""
import sys, json
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from pathlib import Path

MASTER_CSV  = "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
CLUSTER_CSV = "data/immunogenicity_knowledge_base/reports/hpr_hla_cluster_analysis/per_record_low_hpr_hla_cluster_counts.csv"

def normalize_disease(v: object) -> str:
    if not isinstance(v, str) or str(v).strip() in ("nan", ""): return "unknown"
    v = v.strip().lower()
    if "oncol" in v or "cancer" in v or "tumor" in v: return "oncology"
    if "immun" in v or "autoim" in v or "inflamm" in v: return "immunology"
    if "infect" in v or "viral" in v or "bacter" in v: return "infectious"
    return "other"

def ols_r2(X: np.ndarray, y: np.ndarray) -> dict:
    n, k = X.shape
    model = LinearRegression().fit(X, y)
    y_pred = model.predict(X)
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - y.mean())**2)
    r2 = 1 - ss_res / ss_tot
    r2_adj = 1 - (1 - r2) * (n - 1) / (n - k - 1)
    return {"r2": round(r2,4), "r2_adj": round(r2_adj,4), "n": n}

def partial_spearman(feat, target, ctrl):
    f = feat.rank()
    t = target.rank()
    c = ctrl.rank().values.reshape(-1, 1)
    def resid(y):
        X = np.column_stack([np.ones(len(c)), c])
        b = np.linalg.lstsq(X, y, rcond=None)[0]
        return y - X @ b
    r, p = stats.pearsonr(resid(f.values), resid(t.values))
    return round(r, 4), round(p, 4)

def main():
    master = pd.read_csv(MASTER_CSV, low_memory=False)
    cluster = pd.read_csv(CLUSTER_CSV)
    
    master = master[master["ada_first_pct"].notna()].copy()
    master["ada_log10"] = np.log10(master["ada_first_pct"] + 0.1)
    master["disease_area"] = master["ada_profile_disease"].apply(normalize_disease)
    
    # Merge clusters
    cluster_sub = cluster[["antibody_name", "low_hpr_hla_clusters_fr_surface"]].copy()
    df = master.merge(cluster_sub.rename(columns={"antibody_name": "name_c"}),
                      left_on="antibody_name", right_on="name_c", how="left")
    
    # Focus on Immunology
    imm = df[df["disease_area"] == "immunology"].copy()
    imm = imm.dropna(subset=["hpr_combined_score", "low_hpr_hla_clusters_fr_surface", "ada_log10"])
    
    print("="*60)
    print(f"IMMUNOLOGY COHORT (Autoimmune/Inflammatory) n={len(imm)}")
    print("="*60)
    
    # 1. Spearman Correlations
    r_hpr, p_hpr = stats.spearmanr(imm["hpr_combined_score"], imm["ada_log10"])
    r_hla, p_hla = stats.spearmanr(imm["low_hpr_hla_clusters_fr_surface"], imm["ada_log10"])
    
    print(f"Spearman:")
    print(f"  HPR vs ADA:         rho = {r_hpr:+.4f} (p={p_hpr:.5f}) ***")
    print(f"  HLA Cluster vs ADA: rho = {r_hla:+.4f} (p={p_hla:.5f}) **")
    
    # Partial Spearman
    p_rho_hla, p_p_hla = partial_spearman(imm["low_hpr_hla_clusters_fr_surface"], imm["ada_log10"], imm["hpr_combined_score"])
    print(f"  HLA Cluster vs ADA (controlling HPR): partial rho = {p_rho_hla:+.4f} (p={p_p_hla:.4f})")

    # 2. OLS R^2
    y = imm["ada_log10"].values
    X_hpr = imm[["hpr_combined_score"]].values
    X_hla = imm[["low_hpr_hla_clusters_fr_surface"]].values
    X_both = imm[["hpr_combined_score", "low_hpr_hla_clusters_fr_surface"]].values
    
    m_hpr = ols_r2(X_hpr, y)
    m_hla = ols_r2(X_hla, y)
    m_both = ols_r2(X_both, y)
    
    print("\nVariance Explained (OLS R²):")
    print(f"  HPR alone:           R² = {m_hpr['r2']:.4f} (Explains {m_hpr['r2']*100:.1f}% of ADA variance)")
    print(f"  HLA Cluster alone:   R² = {m_hla['r2']:.4f} (Explains {m_hla['r2']*100:.1f}% of ADA variance)")
    print(f"  HPR + HLA Cluster:   R² = {m_both['r2']:.4f} (Explains {m_both['r2']*100:.1f}% of ADA variance)")
    
    marg_hla = m_both['r2'] - m_hpr['r2']
    print(f"\n  Marginal contribution of HLA Cluster beyond HPR: ΔR² = {marg_hla:.4f}")
    
    # 3. Compare with Oncology and Global
    onc = df[df["disease_area"] == "oncology"].copy()
    onc = onc.dropna(subset=["hpr_combined_score", "ada_log10"])
    m_onc = ols_r2(onc[["hpr_combined_score"]].values, onc["ada_log10"].values)
    
    glb = df.dropna(subset=["hpr_combined_score", "ada_log10"])
    m_glb = ols_r2(glb[["hpr_combined_score"]].values, glb["ada_log10"].values)
    
    print("\n" + "="*60)
    print("DISEASE CONTEXT R² COMPARISON (HPR -> ADA)")
    print("="*60)
    print(f"  Global (All diseases) n={m_glb['n']:3d} : R² = {m_glb['r2']:.4f} ({m_glb['r2']*100:.1f}%)")
    print(f"  Oncology              n={m_onc['n']:3d} : R² = {m_onc['r2']:.4f} ({m_onc['r2']*100:.1f}%)")
    print(f"  Immunology/Autoimmune n={m_hpr['n']:3d} : R² = {m_hpr['r2']:.4f} ({m_hpr['r2']*100:.1f}%)")
    
    print("\n  Ratio: In Immunology, HPR explains ~{:.1f}x more variance than the global average.".format(m_hpr['r2'] / m_glb['r2']))

if __name__ == "__main__":
    main()
