"""
Quantitatively Compare Clustering Drivers: CDR3 Length vs CDR2 Fold.

Methodology:
1. Perform hierarchical clustering on FR sequences (FR2, FR3, Combined).
2. Cut the tree into k=2 natural clusters.
3. Calculate statistical association (Effect Size) for each driver:
   - CDR3 Length: Rank-Biserial Correlation (or T-test statistic)
   - CDR2 Fold: Cramer's V (or Chi-square statistic)
4. Compare effect sizes to determine the dominant driver.

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/raw data/TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv

Outputs:
  - paper/raw data/Phylogeny/TheraSAbDab_19VHH_clustering_comparison.txt
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
OUT_REPORT = PROJECT_ROOT / "paper" / "raw data" / "Phylogeny" / "TheraSAbDab_19VHH_clustering_comparison.txt"

def load_data():
    df_seq = pd.read_csv(IN_FR_SEQ)
    df_meta = pd.read_csv(IN_METADATA)
    
    # Handle column names
    h2_col = "h2_class_y" if "h2_class_y" in df_meta.columns else "h2_class"
    if h2_col not in df_meta.columns: h2_col = "h2_class_x"
    
    df_merged = df_seq.merge(df_meta[["antibody_id", h2_col, "h3_length"]], on="antibody_id")
    df_merged = df_merged.rename(columns={h2_col: "H2_Fold", "h3_length": "H3_Len"})
    return df_merged

def get_natural_clusters(seqs, k=2):
    """Return cluster labels for sequences."""
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
    labels = fcluster(Z, t=k, criterion='maxclust')
    return labels

def calculate_association(df, cluster_col):
    """
    Calculate association strength for both drivers against the cluster labels.
    Returns (p_value, effect_size_proxy)
    """
    # 1. CDR3 Length (Continuous vs Nominal) -> Kruskal-Wallis H statistic
    # Using H-statistic as proxy for effect size (larger = better separation)
    groups_h3 = [data["H3_Len"].values for _, data in df.groupby(cluster_col)]
    if len(groups_h3) < 2:
        h_stat_h3, p_h3 = 0, 1.0
    else:
        h_stat_h3, p_h3 = stats.kruskal(*groups_h3)
    
    # 2. CDR2 Fold (Nominal vs Nominal) -> Chi-Square statistic
    contingency = pd.crosstab(df[cluster_col], df["H2_Fold"])
    if contingency.size == 0:
        chi2_h2, p_h2 = 0, 1.0
    else:
        chi2_h2, p_h2, _, _ = stats.chi2_contingency(contingency)
        
    return {
        "CDR3_Len": {"p": p_h3, "score": h_stat_h3},
        "CDR2_Fold": {"p": p_h2, "score": chi2_h2}
    }

def analyze_region(df, seqs, region_name):
    # Perform Clustering (k=2 for binary separation test)
    df["Cluster"] = get_natural_clusters(seqs, k=2)
    
    # Calculate associations
    results = calculate_association(df, "Cluster")
    
    lines = []
    lines.append(f"Region: {region_name}")
    lines.append("-" * 40)
    
    # Report CDR3
    r1 = results["CDR3_Len"]
    sig1 = "**" if r1['p'] < 0.05 else ""
    lines.append(f"  CDR3 Length Association:")
    lines.append(f"    - P-value: {r1['p']:.5f} {sig1}")
    lines.append(f"    - Score (Kruskal H): {r1['score']:.2f}")
    
    # Report CDR2
    r2 = results["CDR2_Fold"]
    sig2 = "**" if r2['p'] < 0.05 else ""
    lines.append(f"  CDR2 Fold Association:")
    lines.append(f"    - P-value: {r2['p']:.5f} {sig2}")
    lines.append(f"    - Score (Chi-Square): {r2['score']:.2f}")
    
    # Verdict
    lines.append("  -> DOMINANT DRIVER: ")
    if r1['p'] < 0.05 and r2['p'] > 0.05:
        lines.append("     [CDR3 Length] (Strongly Significance)")
    elif r2['p'] < 0.05 and r1['p'] > 0.05:
        lines.append("     [CDR2 Fold] (Strongly Significance)")
    elif r1['p'] < 0.05 and r2['p'] < 0.05:
        # Compare relative strength (heuristic)
        lines.append("     [BOTH] (Both Significant)")
    else:
        lines.append("     [NONE] (Neither is Significant)")
        
    lines.append("")
    return lines

def main():
    df = load_data()
    
    fr2_seqs = df["fr2_sequence"].tolist()
    fr3_seqs = df["fr3_sequence"].tolist()
    combined_seqs = [f2+f3 for f2,f3 in zip(fr2_seqs, fr3_seqs)]
    
    report = []
    report.append("============================================================")
    report.append("COMPARISON OF CLUSTERING DRIVERS: CDR3 LENGTH vs CDR2 FOLD")
    report.append("============================================================")
    report.append("")
    
    report.extend(analyze_region(df.copy(), fr2_seqs, "FR2"))
    report.extend(analyze_region(df.copy(), fr3_seqs, "FR3"))
    report.extend(analyze_region(df.copy(), combined_seqs, "FR2+FR3 Combined"))
    
    OUT_REPORT.write_text("\n".join(report), encoding="utf-8")
    print(f"Comparison complete: {OUT_REPORT}")

if __name__ == "__main__":
    main()
