"""
Define New VHH Classification System based on Phylogenetic Clustering.

1. Perform Hierarchical Clustering (k=3) on Combined FR2+FR3 sequences.
2. Calculate Global Camelid Identity (weighted average of regional identities).
3. Profile each cluster:
   - Human Identity vs Camelid Identity.
   - CDR3 Length.
   - Define new class names (e.g., Humanized-I, Humanized-II, Chimeric).

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/raw data/TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv

Outputs:
  - paper/raw data/Phylogeny/TheraSAbDab_19VHH_New_Classification.txt
  - paper/raw data/Phylogeny/TheraSAbDab_19VHH_New_Classification_Table.csv
"""

import pandas as pd
import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_METADATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"
OUT_REPORT = PROJECT_ROOT / "paper" / "raw data" / "Phylogeny" / "TheraSAbDab_19VHH_New_Classification.txt"
OUT_CSV = PROJECT_ROOT / "paper" / "raw data" / "Phylogeny" / "TheraSAbDab_19VHH_New_Classification_Table.csv"

def load_data():
    df_seq = pd.read_csv(IN_FR_SEQ)
    df_meta = pd.read_csv(IN_METADATA)
    
    # Merge relevant columns
    # We need regional vicugna pct to calculate global vicugna pct
    cols_to_keep = [
        "antibody_id", "global_human_identity_pct", 
        "fr1_vicugna_pct", "fr2_vicugna_pct", "fr3_vicugna_pct", "fr4_vicugna_pct",
        "h3_length", "strategy_group"
    ]
    
    # Handle column name variations if necessary
    # Assuming standard names from previous steps
    df_merged = df_seq.merge(df_meta, on="antibody_id")
    
    # Calculate Global Camelid Identity
    # Weights: FR1=25, FR2=17, FR3=38, FR4=11 (Total 91)
    w_fr1, w_fr2, w_fr3, w_fr4 = 25, 17, 38, 11
    total_len = 91
    
    df_merged["Global_Camelid_Identity"] = (
        df_merged["fr1_vicugna_pct"] * w_fr1 +
        df_merged["fr2_vicugna_pct"] * w_fr2 +
        df_merged["fr3_vicugna_pct"] * w_fr3 +
        df_merged["fr4_vicugna_pct"] * w_fr4
    ) / total_len
    
    return df_merged

def get_clusters(seqs, k=3):
    """Generate k clusters from sequences."""
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

def main():
    df = load_data()
    
    # Prepare Sequences for Clustering (FR2+FR3)
    fr2s = df["fr2_sequence"].tolist()
    fr3s = df["fr3_sequence"].tolist()
    combined_seqs = [f2+f3 for f2,f3 in zip(fr2s, fr3s)]
    
    # Perform Clustering (k=3)
    df["Cluster_ID"] = get_clusters(combined_seqs, k=3)
    
    # Analyze Clusters
    cluster_summary = []
    
    # Calculate stats per cluster
    stats = df.groupby("Cluster_ID").agg({
        "global_human_identity_pct": "mean",
        "Global_Camelid_Identity": "mean",
        "h3_length": "mean",
        "antibody_id": "count"
    }).rename(columns={"antibody_id": "Count"})
    
    # Sort clusters by Human Identity (High to Low)
    stats = stats.sort_values("global_human_identity_pct", ascending=False)
    
    # Assign new labels based on rank
    # Class I: Highest Human
    # Class II: Middle
    # Class III: Lowest Human (Highest Camelid)
    new_labels = {}
    for i, (idx, row) in enumerate(stats.iterrows()):
        new_labels[idx] = f"Class {i+1}"
        
    df["New_Class"] = df["Cluster_ID"].map(new_labels)
    
    # Generate Report
    lines = []
    lines.append("="*80)
    lines.append("NEW VHH CLASSIFICATION SYSTEM (Based on FR2+FR3 Phylogeny)")
    lines.append("="*80)
    lines.append("")
    
    for cls in sorted(new_labels.values()):
        sub = df[df["New_Class"] == cls]
        avg_h = sub["global_human_identity_pct"].mean()
        avg_c = sub["Global_Camelid_Identity"].mean()
        avg_len = sub["h3_length"].mean()
        
        lines.append(f"## {cls} (N={len(sub)})")
        lines.append(f"  - Human Identity:   {avg_h:.1f}%")
        lines.append(f"  - Camelid Identity: {avg_c:.1f}%")
        lines.append(f"  - Mean CDR3 Length: {avg_len:.1f} aa")
        lines.append(f"  - Members: {', '.join(sub['antibody_id'].tolist())}")
        lines.append("")
        
    lines.append("-" * 80)
    lines.append("COMPARISON WITH 'NATIVE' BENCHMARK")
    lines.append("Note: A theoretical 'Native' VHH would have ~100% Camelid Identity.")
    lines.append(f"Max Camelid Identity in Dataset: {df['Global_Camelid_Identity'].max():.1f}%")
    lines.append("")
    
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    df.to_csv(OUT_CSV, index=False)
    print(f"Classification complete: {OUT_REPORT}")

if __name__ == "__main__":
    main()
