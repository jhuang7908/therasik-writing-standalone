"""
Prepare Publication Source Data.

Goal:
1. Generate a consolidated CSV containing all sequences, metadata, and classifications used for the figures.
2. Generate Newick Tree files with detailed labels (ID + CDR3 Len + H2 Fold) for external visualization (e.g., iTOL).

Outputs:
  - paper/raw data/Publication_Source_Data.csv
  - paper/raw data/Phylogeny/Tree_FR2_Detailed.newick
  - paper/raw data/Phylogeny/Tree_FR3_Detailed.newick
  - paper/raw data/Phylogeny/Tree_Combined_Detailed.newick
"""

import pandas as pd
import numpy as np
from scipy.cluster.hierarchy import linkage, to_tree
from scipy.spatial.distance import pdist
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_METADATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"
IN_CLASS = PROJECT_ROOT / "paper" / "raw data" / "Phylogeny" / "TheraSAbDab_19VHH_New_Classification_Table.csv"

OUT_CSV = PROJECT_ROOT / "paper" / "raw data" / "Publication_Source_Data.csv"
OUT_TREE_DIR = PROJECT_ROOT / "paper" / "raw data" / "Phylogeny"

# Reference Sequences
REF_SEQUENCES = {
    "Human_IGHV3-23": {
        "fr2": "MSWVRQAPGKGLEWVSA",
        "fr3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
        "type": "Reference"
    },
    "Alpaca_IGHV3-3": {
        "fr2": "MGWFRQAPGKEREFVAA",
        "fr3": "YYADSVKGRFTISRDNAKNTVYLQMNSLKPEDTAVYYC",
        "type": "Reference"
    },
    "Mouse_IGHV1-72": {
        "fr2": "MNWVKQSHGKSLEWIGD",
        "fr3": "YNQKFKGKATLTVDKSSSTAYMELNSLTSEDSAVYYC",
        "type": "Reference"
    }
}

def get_newick(node, newick, parentdist, leaf_names):
    if node.is_leaf():
        return "%s:%.2f" % (leaf_names[node.id], parentdist - node.dist)
    else:
        if len(newick) > 0:
            newick = f"),{newick}"
        else:
            newick = ")"
        newick = get_newick(node.get_left(), newick, node.dist, leaf_names)
        newick = get_newick(node.get_right(), f"({newick}", node.dist, leaf_names)
        return f"{newick}:%.2f" % (parentdist - node.dist)

def build_newick_string(seqs, labels):
    """Build Newick string using scipy linkage."""
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
    
    tree = to_tree(Z, rd=False)
    
    # Custom Newick generator for scipy tree
    def to_newick(node):
        if node.is_leaf():
            return labels[node.id]
        else:
            return f"({to_newick(node.left)}:0.1,{to_newick(node.right)}:0.1)" 
            # Note: Scipy to_tree doesn't easily give branch lengths in simple traversal without recursion tracking
            # For simplicity in this script, we use a simpler approach or just use the structure.
            # Actually, let's use a robust way or just the Z matrix.
            
    # Better: Construct Newick from Z matrix directly
    n = len(labels)
    nodes = {i: labels[i] for i in range(n)}
    for i, row in enumerate(Z):
        c1, c2, dist, count = row
        new_idx = n + i
        # Branch length approximation (dist/2)
        nodes[new_idx] = f"({nodes[int(c1)]}:{dist/2:.4f},{nodes[int(c2)]}:{dist/2:.4f})"
        
    return nodes[n + len(Z) - 1] + ";"

def main():
    # 1. Load and Merge Data
    df_seq = pd.read_csv(IN_FR_SEQ)
    df_meta = pd.read_csv(IN_METADATA)
    df_class = pd.read_csv(IN_CLASS)
    
    # Handle column names
    h2_col = "h2_class_y" if "h2_class_y" in df_meta.columns else "h2_class"
    if h2_col not in df_meta.columns: h2_col = "h2_class_x"
    
    df_meta = df_meta[["antibody_id", h2_col, "h3_length", "strategy_group"]]
    df_meta = df_meta.rename(columns={h2_col: "H2_Fold", "h3_length": "H3_Len", "strategy_group": "Strategy"})
    
    df_class = df_class[["antibody_id", "New_Class", "Global_Camelid_Identity"]]
    
    df = df_seq.merge(df_meta, on="antibody_id").merge(df_class, on="antibody_id")
    
    # 2. Add References to DataFrame for CSV
    rows = []
    for _, row in df.iterrows():
        rows.append(row.to_dict())
        
    for name, seqs in REF_SEQUENCES.items():
        rows.append({
            "antibody_id": name,
            "fr2_sequence": seqs["fr2"],
            "fr3_sequence": seqs["fr3"],
            "H3_Len": 0, # Placeholder
            "H2_Fold": "Ref",
            "Strategy": "Reference",
            "New_Class": "Reference",
            "Global_Camelid_Identity": 0 if "Human" in name else (100 if "Alpaca" in name else 0)
        })
        
    df_final = pd.DataFrame(rows)
    
    # Save CSV
    df_final.to_csv(OUT_CSV, index=False)
    print(f"Saved Source Data: {OUT_CSV}")
    
    # 3. Generate Newick Trees with Detailed Labels
    # Label Format: "ID_L=XX_H2=XX" (Underscores for Newick compatibility)
    labels = []
    fr2_seqs = []
    fr3_seqs = []
    combined_seqs = []
    
    for _, row in df_final.iterrows():
        clean_id = row['antibody_id'].replace(" ", "_")
        if row['Strategy'] == "Reference":
            label = clean_id
        else:
            label = f"{clean_id}_L={int(row['H3_Len'])}_H2={row['H2_Fold']}_{row['New_Class'].replace(' ', '')}"
            
        labels.append(label)
        fr2_seqs.append(row['fr2_sequence'])
        fr3_seqs.append(row['fr3_sequence'])
        combined_seqs.append(row['fr2_sequence'] + row['fr3_sequence'])
        
    # Build and Save Trees
    tree_fr2 = build_newick_string(fr2_seqs, labels)
    (OUT_TREE_DIR / "Tree_FR2_Detailed.newick").write_text(tree_fr2, encoding="utf-8")
    
    tree_fr3 = build_newick_string(fr3_seqs, labels)
    (OUT_TREE_DIR / "Tree_FR3_Detailed.newick").write_text(tree_fr3, encoding="utf-8")
    
    tree_comb = build_newick_string(combined_seqs, labels)
    (OUT_TREE_DIR / "Tree_Combined_Detailed.newick").write_text(tree_comb, encoding="utf-8")
    
    print(f"Saved Newick Trees to: {OUT_TREE_DIR}")

if __name__ == "__main__":
    main()
