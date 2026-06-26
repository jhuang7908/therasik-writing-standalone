#!/usr/bin/env python3
"""
Vernier Zone  ()

 458  Engineered ， Tier1-Tier3 Vernier ：
1. Packing  — ？
2. PCA  — Vernier ？
3.  — ？
4.  CDR / —  Vernier ？
5.  — 
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats as sp_stats
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mutual_info_score

METRICS_PATH = Path("data/humanization_assay/structure_metrics_summary.json")
OUT_DIR = Path("data/humanization_assay")

VH_POS = [2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94]
VL_POS = [2, 4, 36, 46, 49, 69, 71, 98]
ALL_POS = [f"VH_{p}" for p in VH_POS] + [f"VL_{p}" for p in VL_POS]

TIER_MAP = {
    "VH_71": "T1", "VH_94": "T1", "VL_71": "T1", "VL_49": "T1",
    "VH_27": "T2", "VH_28": "T2", "VH_29": "T2", "VH_30": "T2",
    "VH_93": "T2", "VL_36": "T2", "VL_46": "T2",
    "VH_2": "T3", "VH_48": "T3", "VH_49": "T3", "VH_67": "T3",
    "VH_69": "T3", "VH_73": "T3", "VH_78": "T3",
    "VL_2": "T3", "VL_4": "T3", "VL_69": "T3", "VL_98": "T3",
}


def load_packing_matrix():
    with open(METRICS_PATH, encoding="utf-8") as f:
        metrics = json.load(f)

    rows = []
    for m in metrics:
        if m.get("errors"):
            continue
        packing = m.get("vernier_packing", {})
        canonical = m.get("canonical", {})
        row = {
            "PDB": Path(m["pdb_path"]).stem,
            "H1": canonical.get("H1", "?"),
            "H2": canonical.get("H2", "?"),
            "L1": canonical.get("L1", "?"),
            "Angle": m.get("vh_vl_angle_deg"),
            "Interface_pairs": m.get("interface_n_pairs", 0),
            "Interface_mean": m.get("interface_mean_dist_A"),
        }
        for pos in ALL_POS:
            row[pos] = packing.get(pos, np.nan)
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


def analysis_1_correlation_matrix(df):
    """Pairwise Pearson correlation of packing density."""
    pack = df[ALL_POS].dropna(axis=0, how="any")
    corr = pack.corr(method="pearson")

    fig, ax = plt.subplots(figsize=(14, 12))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
                vmin=-1, vmax=1, center=0, ax=ax, square=True,
                linewidths=0.5, cbar_kws={"shrink": 0.7})
    ax.set_title("Vernier Zone Packing Density — Pearson Correlation", fontsize=14)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "vernier_packing_correlation.png", dpi=150)
    plt.close(fig)
    return corr


def analysis_2_hierarchical_clustering(corr):
    """Cluster Vernier positions by correlation similarity."""
    dist = 1 - corr.abs()
    link = linkage(dist.values[np.triu_indices_from(dist.values, k=1)], method="ward")

    fig, ax = plt.subplots(figsize=(14, 6))
    labels = [f"{p} ({TIER_MAP.get(p, '?')})" for p in corr.columns]
    dendrogram(link, labels=labels, ax=ax, leaf_rotation=45, leaf_font_size=10)
    ax.set_title("Vernier Zone Hierarchical Clustering (by Packing Correlation)", fontsize=14)
    ax.set_ylabel("Distance (1 - |r|)")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "vernier_clustering_dendrogram.png", dpi=150)
    plt.close(fig)

    clusters = fcluster(link, t=3, criterion="maxclust")
    cluster_map = {pos: int(c) for pos, c in zip(corr.columns, clusters)}
    return cluster_map


def analysis_3_pca(df):
    """PCA on packing matrix: discover latent structural axes."""
    pack = df[ALL_POS].dropna(axis=0, how="any")
    scaler = StandardScaler()
    X = scaler.fit_transform(pack)

    pca = PCA(n_components=5)
    scores = pca.fit_transform(X)
    loadings = pd.DataFrame(pca.components_.T, index=ALL_POS,
                            columns=[f"PC{i+1}" for i in range(5)])

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # Explained variance
    axes[0].bar(range(1, 6), pca.explained_variance_ratio_ * 100)
    axes[0].set_xlabel("Principal Component")
    axes[0].set_ylabel("Explained Variance (%)")
    axes[0].set_title("PCA Explained Variance")

    # Loadings PC1 vs PC2
    colors = ["red" if TIER_MAP.get(p) == "T1" else
              "orange" if TIER_MAP.get(p) == "T2" else "steelblue"
              for p in ALL_POS]
    axes[1].scatter(loadings["PC1"], loadings["PC2"], c=colors, s=80, zorder=5)
    for pos in ALL_POS:
        axes[1].annotate(pos, (loadings.loc[pos, "PC1"], loadings.loc[pos, "PC2"]),
                         fontsize=8, ha="left")
    axes[1].axhline(0, c="gray", ls="--", lw=0.5)
    axes[1].axvline(0, c="gray", ls="--", lw=0.5)
    axes[1].set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
    axes[1].set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
    axes[1].set_title("PCA Loadings: Vernier Zone Positions\n(Red=T1, Orange=T2, Blue=T3)")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "vernier_pca_loadings.png", dpi=150)
    plt.close(fig)

    return pca, loadings, scores, pack.index


def analysis_4_by_framework(df):
    """Vernier packing distribution stratified by framework subtype."""
    df["Subtype"] = df["H1"] + "|" + df["H2"] + "|" + df["L1"]
    top_subtypes = df["Subtype"].value_counts().head(5).index.tolist()
    key_pos = ["VH_71", "VH_94", "VL_71", "VL_49", "VH_93", "VL_36"]

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()
    for i, pos in enumerate(key_pos):
        ax = axes[i]
        data_list = []
        labels = []
        for st in top_subtypes:
            sub = df[df["Subtype"] == st][pos].dropna()
            if len(sub) > 5:
                data_list.append(sub.values)
                labels.append(f"{st}\n(n={len(sub)})")
        if data_list:
            ax.boxplot(data_list, labels=labels, vert=True)
        ax.set_title(f"{pos} ({TIER_MAP.get(pos, '?')})", fontsize=11)
        ax.set_ylabel("Packing (contacts)")
        ax.tick_params(axis="x", rotation=30, labelsize=8)
    plt.suptitle("Key Vernier Packing by Framework Subtype (Top 5)", fontsize=14, y=1.01)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "vernier_packing_by_framework.png", dpi=150)
    plt.close(fig)


def analysis_5_angle_scatter(df):
    """Scatter: VH/VL angle vs key Vernier packing."""
    key_pos = ["VH_71", "VH_94", "VL_71", "VL_49"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    for i, pos in enumerate(key_pos):
        ax = axes[i]
        sub = df[["Angle", pos]].dropna()
        ax.scatter(sub["Angle"], sub[pos], alpha=0.4, s=15, c="steelblue")
        if len(sub) > 10:
            z = np.polyfit(sub["Angle"], sub[pos], 1)
            xs = np.linspace(sub["Angle"].min(), sub["Angle"].max(), 50)
            ax.plot(xs, np.polyval(z, xs), "r-", lw=2)
            r, p = sp_stats.pearsonr(sub["Angle"], sub[pos])
            ax.set_title(f"{pos}: r={r:.3f}, p={p:.1e}", fontsize=11)
        else:
            ax.set_title(pos)
        ax.set_xlabel("VH/VL Angle (°)")
        ax.set_ylabel("Packing (contacts)")
    plt.suptitle("VH/VL Angle vs Vernier Packing", fontsize=14)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "vernier_angle_scatter.png", dpi=150)
    plt.close(fig)


def analysis_6_cross_position_regression(df):
    """Can one Vernier position predict another? (Inter-position dependency)"""
    pack = df[ALL_POS].dropna(axis=0, how="any")
    n = len(ALL_POS)
    r2_matrix = np.zeros((n, n))
    for i, pos_i in enumerate(ALL_POS):
        for j, pos_j in enumerate(ALL_POS):
            if i == j:
                r2_matrix[i, j] = 1.0
                continue
            X = pack[[pos_i]].values
            y = pack[pos_j].values
            rf = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42, n_jobs=1)
            rf.fit(X, y)
            r2_matrix[i, j] = rf.score(X, y)

    r2_df = pd.DataFrame(r2_matrix, index=ALL_POS, columns=ALL_POS)
    fig, ax = plt.subplots(figsize=(14, 12))
    sns.heatmap(r2_df, annot=True, fmt=".2f", cmap="YlOrRd", vmin=0, vmax=1,
                ax=ax, square=True, linewidths=0.5)
    ax.set_title("Cross-Position Predictability (RF R²)\nCan position X predict position Y?", fontsize=14)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "vernier_cross_position_r2.png", dpi=150)
    plt.close(fig)
    return r2_df


def write_report(corr, cluster_map, pca, loadings, r2_df, df):
    lines = [
        "# Vernier Zone ",
        "",
        " 458  Engineered ， Tier1-Tier3 Vernier Zone ",
        "、PCA 、、。",
        "",
        f"- : **{len(df)}**",
        f"- : **{len(ALL_POS)}** (VH {len(VH_POS)} + VL {len(VL_POS)})",
        "",
        "---",
        "",
        "## 1. Vernier ",
        "",
        "![Correlation Matrix](vernier_packing_correlation.png)",
        "",
    ]

    # Find strongest correlations
    pairs = []
    for i, p1 in enumerate(ALL_POS):
        for j, p2 in enumerate(ALL_POS):
            if j > i:
                pairs.append((p1, p2, corr.loc[p1, p2]))
    pairs.sort(key=lambda x: -abs(x[2]))

    lines.append("###  (Top 10)")
    lines.append("")
    lines.append("|  A |  B | Pearson r |  |")
    lines.append("|:---|:---|---:|:---|")
    for p1, p2, r in pairs[:10]:
        meaning = ""
        if "VH" in p1 and "VH" in p2:
            meaning = " → "
        elif "VL" in p1 and "VL" in p2:
            meaning = " → "
        else:
            meaning = " → VH/VL "
        lines.append(f"| {p1} ({TIER_MAP.get(p1,'')}) | {p2} ({TIER_MAP.get(p2,'')}) | {r:.3f} | {meaning} |")
    lines.append("")

    lines.append("###  (Top 5)")
    lines.append("")
    lines.append("|  A |  B | Pearson r |  |")
    lines.append("|:---|:---|---:|:---|")
    neg_pairs = [p for p in pairs if p[2] < 0]
    neg_pairs.sort(key=lambda x: x[2])
    for p1, p2, r in neg_pairs[:5]:
        lines.append(f"| {p1} ({TIER_MAP.get(p1,'')}) | {p2} ({TIER_MAP.get(p2,'')}) | {r:.3f} | ： |")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 2. ：Vernier ")
    lines.append("")
    lines.append("![Dendrogram](vernier_clustering_dendrogram.png)")
    lines.append("")
    lines.append("###  (3 )")
    lines.append("")
    for c_id in sorted(set(cluster_map.values())):
        members = [p for p, c in cluster_map.items() if c == c_id]
        tiers = [TIER_MAP.get(p, "?") for p in members]
        lines.append(f"- **Cluster {c_id}**: {', '.join(members)}")
        lines.append(f"  - Tier : {dict(pd.Series(tiers).value_counts())}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 3. PCA ：Vernier Zone ")
    lines.append("")
    lines.append("![PCA Loadings](vernier_pca_loadings.png)")
    lines.append("")
    ev = pca.explained_variance_ratio_
    lines.append(f"- **PC1** ({ev[0]*100:.1f}%): ，")
    lines.append(f"- **PC2** ({ev[1]*100:.1f}%): ， VH vs VL ")
    lines.append(f"- **PC1+PC2** : {(ev[0]+ev[1])*100:.1f}%")
    lines.append("")

    # Identify what PC1 and PC2 represent
    pc1_top = loadings["PC1"].abs().nlargest(5)
    pc2_top = loadings["PC2"].abs().nlargest(5)
    lines.append("### PC1 ")
    for pos, val in pc1_top.items():
        lines.append(f"  - {pos} ({TIER_MAP.get(pos,'')}): loading = {loadings.loc[pos,'PC1']:.3f}")
    lines.append("")
    lines.append("### PC2 ")
    for pos, val in pc2_top.items():
        lines.append(f"  - {pos} ({TIER_MAP.get(pos,'')}): loading = {loadings.loc[pos,'PC2']:.3f}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 4.  Vernier ")
    lines.append("")
    lines.append("![Framework Boxplots](vernier_packing_by_framework.png)")
    lines.append("")
    lines.append(" CDR ， Vernier ，")
    lines.append(" Vernier 。")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 5. VH/VL  Vernier ")
    lines.append("")
    lines.append("![Angle Scatter](vernier_angle_scatter.png)")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 6.  (Cross-Position RF R²)")
    lines.append("")
    lines.append("![Cross R²](vernier_cross_position_r2.png)")
    lines.append("")
    lines.append("###  (Top 10)")
    lines.append("")
    lines.append("|  |  | RF R² |  |")
    lines.append("|:---|:---|---:|:---|")
    xpairs = []
    for i, p1 in enumerate(ALL_POS):
        for j, p2 in enumerate(ALL_POS):
            if i != j:
                xpairs.append((p1, p2, r2_df.loc[p1, p2]))
    xpairs.sort(key=lambda x: -x[2])
    for p1, p2, r2 in xpairs[:10]:
        lines.append(f"| {p1} | {p2} | {r2:.3f} |  {p1}  {p2} |")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 7. ")
    lines.append("")
    lines.append("1. **Vernier Zone **：。，。")
    lines.append("2. ****：Vernier  2-3 （），。")
    lines.append("3. **VH/VL **： Vernier 。")
    lines.append("4. **L1 **： VL  Vernier （ VL 71）。")
    lines.append("5. ****：VH  VL  Vernier ， VH/VL 。")
    lines.append("")
    lines.append("* `ml_vernier_correlation_analysis.py` 。*")

    report_path = OUT_DIR / "vernier_correlation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report written to {report_path}")


def main():
    print("Loading data...", flush=True)
    df = load_packing_matrix()
    print(f"  {len(df)} antibodies, {len(ALL_POS)} Vernier positions", flush=True)

    print("1/6 Correlation matrix...", flush=True)
    corr = analysis_1_correlation_matrix(df)

    print("2/6 Hierarchical clustering...", flush=True)
    cluster_map = analysis_2_hierarchical_clustering(corr)

    print("3/6 PCA...", flush=True)
    pca, loadings, scores, idx = analysis_3_pca(df)

    print("4/6 Framework stratification...", flush=True)
    analysis_4_by_framework(df)

    print("5/6 Angle scatter...", flush=True)
    analysis_5_angle_scatter(df)

    print("6/6 Cross-position predictability...", flush=True)
    r2_df = analysis_6_cross_position_regression(df)

    print("Writing report...", flush=True)
    write_report(corr, cluster_map, pca, loadings, r2_df, df)

    print("Done.", flush=True)


if __name__ == "__main__":
    main()
