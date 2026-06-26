"""
Visualize Phylogenetic Trees for FR2, FR3, and Combined regions.
Generates PNG dendrograms to visualize clustering of VHHs relative to Human/Alpaca anchors.
"""

import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import pdist, squareform
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Setup Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_METADATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"
OUT_DIR = PROJECT_ROOT / "paper" / "figures" / "Phylogeny"

if not OUT_DIR.exists():
    OUT_DIR.mkdir(parents=True)

# Reference Sequences
REF_SEQUENCES = {
    "Human_IGHV3-23": {
        "fr2": "MSWVRQAPGKGLEWVSA",
        "fr3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
        "type": "Ref_Human"
    },
    "Alpaca_IGHV3-3": {
        "fr2": "MGWFRQAPGKEREFVAA",
        "fr3": "YYADSVKGRFTISRDNAKNTVYLQMNSLKPEDTAVYYC",
        "type": "Ref_Alpaca"
    },
    "Mouse_IGHV1-72": {
        "fr2": "MNWVKQSHGKSLEWIGD",
        "fr3": "YNQKFKGKATLTVDKSSSTAYMELNSLTSEDSAVYYC",
        "type": "Ref_Mouse"
    }
}

def load_data():
    df_seq = pd.read_csv(IN_FR_SEQ)
    df_meta = pd.read_csv(IN_METADATA)
    
    # Handle column naming variations
    strat_col = "strategy_group_y" if "strategy_group_y" in df_meta.columns else "strategy_group"
    if strat_col not in df_meta.columns: strat_col = "strategy_group_x"
    if strat_col not in df_meta.columns: strat_col = "strategy_group"

    df_merged = df_seq.merge(df_meta[["antibody_id", strat_col]], on="antibody_id")
    df_merged = df_merged.rename(columns={strat_col: "Strategy"})
    return df_merged

def get_color(label_text):
    if "Ref_Human" in label_text: return "#1f77b4" # Blue
    if "Ref_Alpaca" in label_text: return "#9467bd" # Purple
    if "Ref_Mouse" in label_text: return "#7f7f7f" # Gray
    if "(BM)" in label_text: return "#d62728" # Red
    if "(SR)" in label_text: return "#ff7f0e" # Orange
    if "(Native)" in label_text: return "#2ca02c" # Green
    return "black"

def plot_tree(seqs, labels, title, filename):
    # Compute Distance
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

    # Plot
    plt.figure(figsize=(10, 8))
    ax = plt.gca()
    
    ddata = dendrogram(Z, labels=labels, orientation='left', ax=ax, leaf_font_size=10)
    
    # Color Labels
    ylocs = ax.get_yticks()
    for i, label in enumerate(ax.get_yticklabels()):
        text = label.get_text()
        color = get_color(text)
        label.set_color(color)
        if "Ref_" in text:
            label.set_fontweight('bold')

    plt.title(title, fontsize=14)
    plt.xlabel("Evolutionary Distance (Normalized Hamming)", fontsize=10)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"Generated: {filename}")

def main():
    df = load_data()
    
    # Prepare Data
    ids = df["antibody_id"].tolist()
    strats = df["Strategy"].tolist()
    fr2s = df["fr2_sequence"].tolist()
    fr3s = df["fr3_sequence"].tolist()
    
    # Format Labels
    vhh_labels = [f"{i} ({s})" for i, s in zip(ids, strats)]
    
    # Add References
    ref_labels = [f"{k} ({v['type']})" for k, v in REF_SEQUENCES.items()]
    ref_fr2s = [v["fr2"] for v in REF_SEQUENCES.values()]
    ref_fr3s = [v["fr3"] for v in REF_SEQUENCES.values()]
    
    final_labels = vhh_labels + ref_labels
    final_fr2 = fr2s + ref_fr2s
    final_fr3 = fr3s + ref_fr3s
    final_combined = [f2 + f3 for f2, f3 in zip(final_fr2, final_fr3)]
    
    # Plot 1: FR2
    plot_tree(final_fr2, final_labels, 
              "FR2 Region Phylogeny\n(Driven by Solubility/CDR3 Length)", 
              OUT_DIR / "FR2_Phylogeny_Tree.png")
              
    # Plot 2: FR3
    plot_tree(final_fr3, final_labels, 
              "FR3 Region Phylogeny\n(Conservative Structural Scaffold)", 
              OUT_DIR / "FR3_Phylogeny_Tree.png")
              
    # Plot 3: Combined
    plot_tree(final_combined, final_labels, 
              "Combined FR2+FR3 Phylogeny\n(Overall Humanization Landscape)", 
              OUT_DIR / "FR2_FR3_Combined_Phylogeny_Tree.png")

if __name__ == "__main__":
    main()
