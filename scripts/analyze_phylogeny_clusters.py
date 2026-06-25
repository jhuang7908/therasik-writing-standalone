"""
Analyze Phylogenetic Clusters to correct classification and test structural correlations.

1. Perform Hierarchical Clustering on FR2 and FR2+FR3 sequences.
2. Cut trees to define "Natural Clusters" (k=2 or k=3).
3. Test hypothesis:
   - FR2 Clusters are driven by CDR3 Length.
   - FR2+FR3 Clusters are driven by CDR2 Fold (or Strategy).

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/raw data/TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv

Outputs:
  - paper/raw data/Phylogeny/TheraSAbDab_19VHH_cluster_analysis.txt
"""

import pandas as pd
import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist
from scipy import stats
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_METADATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"
OUT_REPORT = PROJECT_ROOT / "paper" / "raw data" / "Phylogeny" / "TheraSAbDab_19VHH_cluster_analysis.txt"

def load_data():
    df_seq = pd.read_csv(IN_FR_SEQ)
    df_meta = pd.read_csv(IN_METADATA)
    
    strat_col = "strategy_group_y" if "strategy_group_y" in df_meta.columns else "strategy_group"
    if strat_col not in df_meta.columns: strat_col = "strategy_group_x"
    
    h2_col = "h2_class_y" if "h2_class_y" in df_meta.columns else "h2_class"
    if h2_col not in df_meta.columns: h2_col = "h2_class_x"

    df_merged = df_seq.merge(df_meta[["antibody_id", strat_col, h2_col, "h3_length"]], on="antibody_id")
    df_merged = df_merged.rename(columns={strat_col: "Strategy", h2_col: "H2_Fold", "h3_length": "H3_Len"})
    return df_merged

def get_clusters(seqs, n_clusters=2):
    """Generate clusters from sequences using Hamming distance and Average Linkage."""
    def hamming_normalized(u, v):
        seq_u = seqs[int(u[0])]
        seq_v = seqs[int(v[0])]
        min_len = min(len(seq_u), len(seq_v))
        if min_len == 0: return 1.0
        diffs = sum(1 for i in range(min_len) if seq_u[i] != seq_v[i])
        diffs += abs(len(seq_u) - len(seq_v)) 
        return diffs / max(len(seq_u), len(seq_v))

    X = np.array(range(len(seqs))).reshape(-1, 1)
    dists = pdist(X, metric=hamming_normalized)
    Z = linkage(dists, method='average')
    
    # fcluster returns cluster labels 1..k
    labels = fcluster(Z, t=n_clusters, criterion='maxclust')
    return labels

def analyze_clusters(df, cluster_col, region_name):
    lines = []
    lines.append(f"## {region_name} Natural Clusters Analysis")
    lines.append("-" * 60)
    
    # 1. Cluster Composition
    lines.append("Cluster Profiles:")
    lines.append(f"{'Cluster':<8} | {'N':<3} | {'Mean H3_Len':<12} | {'% H2-10-1':<10} | {'Dominant Strategy'}")
    
    unique_clusters = sorted(df[cluster_col].unique())
    
    cluster_stats = []
    
    for c in unique_clusters:
        sub = df[df[cluster_col] == c]
        n = len(sub)
        mean_h3 = sub["H3_Len"].mean()
        pct_h2_10 = (sub["H2_Fold"] == "H2-10-1").mean() * 100
        dom_strat = sub["Strategy"].mode()[0] if not sub["Strategy"].mode().empty else "N/A"
        
        lines.append(f"{c:<8} | {n:<3} | {mean_h3:<12.1f} | {pct_h2_10:<10.1f}% | {dom_strat}")
        
        cluster_stats.append({
            "cluster": c,
            "h3_len": sub["H3_Len"].values,
            "h2_binary": (sub["H2_Fold"] == "H2-10-1").astype(int).values,
            "strategies": sub["Strategy"].values
        })
        
    lines.append("")
    
    # 2. Test Hypothesis: CDR3 Length (ANOVA/Kruskal)
    h3_groups = [s["h3_len"] for s in cluster_stats]
    if len(h3_groups) > 1:
        stat, p_h3 = stats.kruskal(*h3_groups)
        lines.append(f"Hypothesis 1: Do clusters differ by CDR3 Length?")
        lines.append(f"  -> P-value: {p_h3:.5f} {'(SIGNIFICANT)' if p_h3 < 0.05 else ''}")
    
    # 3. Test Hypothesis: CDR2 Fold (Chi-Square/Fisher)
    # Construct contingency table: Cluster vs Fold
    if len(unique_clusters) == 2:
        # 2x2 table if binary clusters
        c1_h2_10 = sum(cluster_stats[0]["h2_binary"])
        c1_total = len(cluster_stats[0]["h2_binary"])
        c2_h2_10 = sum(cluster_stats[1]["h2_binary"])
        c2_total = len(cluster_stats[1]["h2_binary"])
        
        table = [[c1_h2_10, c1_total - c1_h2_10],
                 [c2_h2_10, c2_total - c2_h2_10]]
        
        odds, p_fold = stats.fisher_exact(table)
        lines.append(f"Hypothesis 2: Do clusters differ by CDR2 Fold?")
        lines.append(f"  -> P-value: {p_fold:.5f} {'(SIGNIFICANT)' if p_fold < 0.05 else ''}")
    else:
        # Chi-square for k>2
        # Build full contingency table
        contingency = pd.crosstab(df[cluster_col], df["H2_Fold"])
        chi2, p_fold, dof, ex = stats.chi2_contingency(contingency)
        lines.append(f"Hypothesis 2: Do clusters differ by CDR2 Fold?")
        lines.append(f"  -> P-value: {p_fold:.5f} {'(SIGNIFICANT)' if p_fold < 0.05 else ''}")
        
    lines.append("")
    lines.append("Interpretation:")
    if p_h3 < 0.05 and p_fold > 0.05:
        lines.append(f"  -> {region_name} clustering is driven by **CDR3 Length**.")
    elif p_fold < 0.05 and p_h3 > 0.05:
        lines.append(f"  -> {region_name} clustering is driven by **CDR2 Fold**.")
    elif p_fold < 0.05 and p_h3 < 0.05:
        lines.append(f"  -> {region_name} clustering is driven by **BOTH**.")
    else:
        lines.append(f"  -> {region_name} clustering is NOT driven by these structural features.")
        
    lines.append("="*60)
    lines.append("")
    return lines

def main():
    df = load_data()
    ids = df["antibody_id"].tolist()
    
    # 1. FR2 Analysis
    fr2_seqs = df["fr2_sequence"].tolist()
    df["FR2_Cluster"] = get_clusters(fr2_seqs, n_clusters=2) # Try 2 main clusters
    
    # 2. FR2+FR3 Analysis
    fr3_seqs = df["fr3_sequence"].tolist()
    combined_seqs = [f2 + f3 for f2, f3 in zip(fr2_seqs, fr3_seqs)]
    df["Combined_Cluster"] = get_clusters(combined_seqs, n_clusters=3) # Try 3 clusters (Human, Mixed, Alpaca)
    
    report = []
    report.append("="*60)
    report.append("Re-Classification Analysis: Natural Phylogenetic Clusters")
    report.append("="*60)
    report.append("")
    
    report.extend(analyze_clusters(df, "FR2_Cluster", "FR2 Region"))
    report.extend(analyze_clusters(df, "Combined_Cluster", "FR2+FR3 Combined"))
    
    OUT_REPORT.write_text("\n".join(report), encoding="utf-8")
    print(f"Analysis complete: {OUT_REPORT}")

if __name__ == "__main__":
    main()
