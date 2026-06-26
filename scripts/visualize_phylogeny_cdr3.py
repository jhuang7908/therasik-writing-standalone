"""
Visualize Phylogenetic Trees with CDR3 Length Coloring.

Goal: Visualize how CDR3 length correlates with phylogenetic clustering.
Colors VHH labels based on CDR3 length:
- Red: Short CDR3 (<= 10)
- Green: Long CDR3 (> 10)
- References: Blue (Human), Purple (Alpaca), Gray (Mouse)
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

# Reference Sequences
REF_SEQUENCES = {
    "Human_IGHV3-23": {
        "fr2": "MSWVRQAPGKGLEWVSA",
        "fr3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
        "type": "Ref_Human"
    },
    "Human_IGHV3-13": {
        "fr2": "MHWVRQAPGKGLEWVAV",
        "fr3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
        "type": "Ref_Human"
    },
    "Alpaca_IGHV3-3": {
        "fr2": "MGWFRQAPGKEREFVAA",
        "fr3": "YYADSVKGRFTISRDNAKNTVYLQMNSLKPEDTAVYYC",
        "type": "Ref_Alpaca"
    },
    "Alpaca_IGHV3-1": {
        "fr2": "MGWVRQAPGKGLEWVAA",
        "fr3": "YYADSVKGRFTISRDNAKNTLYLQMNSLKPEDTAVYYC",
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
    
    # Merge H3 Length
    df_merged = df_seq.merge(df_meta[["antibody_id", "h3_length"]], on="antibody_id")
    df_merged = df_merged.rename(columns={"h3_length": "H3_Len"})
    return df_merged

def get_color(label_text, h3_len=None):
    if "Ref_Human" in label_text: return "#1f77b4" # Blue
    if "Ref_Alpaca" in label_text: return "#9467bd" # Purple
    if "Ref_Mouse" in label_text: return "#7f7f7f" # Gray
    
    # VHH coloring by CDR3 Length
    if h3_len is not None:
        if h3_len <= 10: return "#d62728" # Red (Short -> Human-like potential)
        return "#2ca02c" # Green (Long -> Camelid-like potential)
    
    return "black"

def plot_tree(seqs, labels, h3_lens, title, filename):
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
    plt.figure(figsize=(12, 10))
    ax = plt.gca()
    
    ddata = dendrogram(Z, labels=labels, orientation='left', ax=ax, leaf_font_size=10)
    
    # Color Labels
    ylocs = ax.get_yticks()
    for i, label in enumerate(ax.get_yticklabels()):
        text = label.get_text()
        
        # Extract H3 Len from text if VHH
        # Text format: "Name (L=XX)" or "Ref_..."
        h3_val = None
        if "(L=" in text:
            try:
                part = text.split("(L=")[1]
                h3_val = int(part.split(")")[0])
            except: pass
            
        color = get_color(text, h3_val)
        label.set_color(color)
        if "Ref_" in text:
            label.set_fontweight('bold')

    plt.title(title, fontsize=14)
    plt.xlabel("Evolutionary Distance (Normalized Hamming)", fontsize=10)
    
    # Custom Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='#1f77b4', lw=2, label='Human Ref (Goal)'),
        Line2D([0], [0], color='#9467bd', lw=2, label='Alpaca Ref (Origin)'),
        Line2D([0], [0], color='#d62728', lw=2, label='Short CDR3 (≤10)'),
        Line2D([0], [0], color='#2ca02c', lw=2, label='Long CDR3 (>10)'),
    ]
    ax.legend(handles=legend_elements, loc='upper left')
    
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"Generated: {filename}")

def main():
    df = load_data()
    
    # Prepare Data
    ids = df["antibody_id"].tolist()
    h3_lens = df["H3_Len"].tolist()
    fr2s = df["fr2_sequence"].tolist()
    fr3s = df["fr3_sequence"].tolist()
    
    # Format Labels with H3 Length info
    vhh_labels = [f"{i} (L={l})" for i, l in zip(ids, h3_lens)]
    
    # Add References
    ref_labels = [f"{k} ({v['type']})" for k, v in REF_SEQUENCES.items()]
    ref_fr2s = [v["fr2"] for v in REF_SEQUENCES.values()]
    ref_fr3s = [v["fr3"] for v in REF_SEQUENCES.values()]
    
    # For references, H3 len is undefined (None)
    final_labels = vhh_labels + ref_labels
    final_h3_lens = h3_lens + [None]*len(ref_labels)
    
    final_fr2 = fr2s + ref_fr2s
    final_fr3 = fr3s + ref_fr3s
    final_combined = [f2 + f3 for f2, f3 in zip(final_fr2, final_fr3)]
    
    # Plot 1: FR2
    plot_tree(final_fr2, final_labels, final_h3_lens,
              "FR2 Region Phylogeny (Colored by CDR3 Length)\nHypothesis: Short CDR3s cluster with Human, Long CDR3s with Alpaca", 
              OUT_DIR / "FR2_Phylogeny_by_CDR3Len.png")
              
    # Plot 2: FR3
    plot_tree(final_fr3, final_labels, final_h3_lens,
              "FR3 Region Phylogeny (Colored by CDR3 Length)\nHypothesis: No clear clustering by CDR3 Length", 
              OUT_DIR / "FR3_Phylogeny_by_CDR3Len.png")
              
    # Plot 3: Combined
    plot_tree(final_combined, final_labels, final_h3_lens,
              "FR2+FR3 Combined Phylogeny (Colored by CDR3 Length)\nOverall Humanization Landscape", 
              OUT_DIR / "FR2_FR3_Combined_Phylogeny_by_CDR3Len.png")

if __name__ == "__main__":
    main()
