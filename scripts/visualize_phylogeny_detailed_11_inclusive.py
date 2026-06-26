"""
Update Phylogenetic Trees with Detailed Labels.
Colors: Red (Short CDR3 <= 11), Green (Long CDR3 > 11).
Threshold changed to INCLUDE 11 in Short group.
"""

import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import pdist
import pandas as pd
import numpy as np
from pathlib import Path

# Setup Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_METADATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"
OUT_DIR = PROJECT_ROOT / "paper" / "figures" / "Phylogeny"

if not OUT_DIR.exists():
    OUT_DIR.mkdir(parents=True)

# Reference Sequences (Standard)
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
    
    # Handle column names
    h2_col = "h2_class_y" if "h2_class_y" in df_meta.columns else "h2_class"
    if h2_col not in df_meta.columns: h2_col = "h2_class_x"
    
    df_merged = df_seq.merge(df_meta[["antibody_id", h2_col, "h3_length"]], on="antibody_id")
    df_merged = df_merged.rename(columns={h2_col: "H2_Fold", "h3_length": "H3_Len"})
    return df_merged

def get_color(label_text, h3_len=None):
    if "Ref_Human" in label_text: return "#1f77b4" # Blue
    if "Ref_Alpaca" in label_text: return "#9467bd" # Purple
    if "Ref_Mouse" in label_text: return "#7f7f7f" # Gray
    
    if h3_len is not None:
        if h3_len <= 11: return "#d62728" # Red (Short <= 11)
        return "#2ca02c" # Green (Long > 11)
    
    return "black"

def plot_tree(seqs, labels, h3_lens, title, filename):
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

    plt.figure(figsize=(14, 12))
    ax = plt.gca()
    
    dendrogram(Z, labels=labels, orientation='left', ax=ax, leaf_font_size=9)
    
    for label in ax.get_yticklabels():
        text = label.get_text()
        
        # Extract H3 Len
        h3_val = None
        if "L=" in text:
            try:
                # Format: "Name (L=XX, H2-X)"
                part = text.split("L=")[1]
                h3_val = int(part.split(",")[0])
            except: pass
            
        color = get_color(text, h3_val)
        label.set_color(color)
        if "Ref_" in text:
            label.set_fontweight('bold')

    plt.title(title, fontsize=14)
    plt.xlabel("Evolutionary Distance (Normalized Hamming)", fontsize=10)
    
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='#1f77b4', lw=2, label='Human Ref'),
        Line2D([0], [0], color='#9467bd', lw=2, label='Alpaca Ref'),
        Line2D([0], [0], color='#d62728', lw=2, label='Short CDR3 (<=11)'),
        Line2D([0], [0], color='#2ca02c', lw=2, label='Long CDR3 (>11)'),
    ]
    ax.legend(handles=legend_elements, loc='upper left')
    
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"Generated: {filename}")

def main():
    df = load_data()
    
    ids = df["antibody_id"].tolist()
    h3_lens = df["H3_Len"].tolist()
    h2_folds = df["H2_Fold"].tolist()
    fr2s = df["fr2_sequence"].tolist()
    fr3s = df["fr3_sequence"].tolist()
    
    # Detailed Labels
    vhh_labels = [f"{i} (L={l}, {h})" for i, l, h in zip(ids, h3_lens, h2_folds)]
    
    ref_labels = [f"{k} ({v['type']})" for k, v in REF_SEQUENCES.items()]
    ref_fr2s = [v["fr2"] for v in REF_SEQUENCES.values()]
    ref_fr3s = [v["fr3"] for v in REF_SEQUENCES.values()]
    
    final_labels = vhh_labels + ref_labels
    final_h3_lens = h3_lens + [None]*len(ref_labels)
    
    final_fr2 = fr2s + ref_fr2s
    final_fr3 = fr3s + ref_fr3s
    final_combined = [f2 + f3 for f2, f3 in zip(final_fr2, final_fr3)]
    
    # Generate Trees
    plot_tree(final_fr2, final_labels, final_h3_lens,
              "FR2 Phylogeny (Colored by CDR3 Length <= 11)\nLabels include H2 Fold info", 
              OUT_DIR / "FR2_Phylogeny_Detailed_Threshold11_Inclusive.png")
              
    plot_tree(final_combined, final_labels, final_h3_lens,
              "FR2+FR3 Combined Phylogeny (Colored by CDR3 Length <= 11)\nLabels include H2 Fold info", 
              OUT_DIR / "FR2_FR3_Combined_Phylogeny_Detailed_Threshold11_Inclusive.png")

if __name__ == "__main__":
    main()
