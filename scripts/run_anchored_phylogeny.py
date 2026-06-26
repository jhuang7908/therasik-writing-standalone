"""
Phylogenetic Tree Construction with Reference Anchors (Human/Alpaca/Mouse).

Goal: Build rooted phylogenetic trees for FR2, FR3, and FR2+FR3 regions to unbiasedly
classify VHHs and evaluate which region provides the best discrimination of structural features.

Reference Sequences (IMGT):
  - Human (Goal): IGHV3-23*01, IGHV3-13*01
  - Alpaca (Origin): IGHV3-3*01 (VHH), IGHV3-1*01 (VH-like)
  - Mouse (Outgroup): IGHV1-72*01

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/raw data/TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv (metadata)

Outputs:
  - paper/raw data/Phylogeny/TheraSAbDab_19VHH_FR2_anchored.newick
  - paper/raw data/Phylogeny/TheraSAbDab_19VHH_FR3_anchored.newick
  - paper/raw data/Phylogeny/TheraSAbDab_19VHH_FR2_FR3_anchored.newick
  - paper/raw data/Phylogeny/TheraSAbDab_19VHH_phylogeny_discrimination_analysis.txt
"""

from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent

IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_METADATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"

OUT_DIR = PROJECT_ROOT / "paper" / "raw data" / "Phylogeny"
OUT_TREE_FR2 = OUT_DIR / "TheraSAbDab_19VHH_FR2_anchored.newick"
OUT_TREE_FR3 = OUT_DIR / "TheraSAbDab_19VHH_FR3_anchored.newick"
OUT_TREE_COMBINED = OUT_DIR / "TheraSAbDab_19VHH_FR2_FR3_anchored.newick"
OUT_REPORT = OUT_DIR / "TheraSAbDab_19VHH_phylogeny_discrimination_analysis.txt"

# Ensure output directory exists
if not OUT_DIR.exists():
    os.makedirs(OUT_DIR)

# --- Reference Sequences (Standard IMGT FRs) ---
REF_SEQUENCES = {
    "Human_IGHV3-23": {
        "fr2": "MSWVRQAPGKGLEWVSA",  # 17aa
        "fr3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC", # 38aa - Fixed start
        "type": "Reference_Human"
    },
    "Human_IGHV3-13": {
        "fr2": "MHWVRQAPGKGLEWVAV",
        "fr3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC", # 38aa
        "type": "Reference_Human"
    },
    "Alpaca_IGHV3-3": { # Typical VHH
        "fr2": "MGWFRQAPGKEREFVAA", # VHH hallmark enriched
        "fr3": "YYADSVKGRFTISRDNAKNTVYLQMNSLKPEDTAVYYC", # 38aa
        "type": "Reference_Alpaca"
    },
    "Alpaca_IGHV3-1": { # VH-like
        "fr2": "MGWVRQAPGKGLEWVAA", # More human-like
        "fr3": "YYADSVKGRFTISRDNAKNTLYLQMNSLKPEDTAVYYC", # 38aa
        "type": "Reference_Alpaca"
    },
    "Mouse_IGHV1-72": { # Outgroup
        "fr2": "MNWVKQSHGKSLEWIGD", 
        "fr3": "YNQKFKGKATLTVDKSSSTAYMELNSLTSEDSAVYYC", # 37aa
        "type": "Reference_Mouse_Outgroup"
    }
}

def compute_distance_matrix(sequences: list[str]) -> pd.DataFrame:
    """Compute pairwise p-distance (normalized Hamming)."""
    ids = list(range(len(sequences)))
    
    def hamming_normalized(u, v):
        seq_u = sequences[int(u[0])]
        seq_v = sequences[int(v[0])]
        min_len = min(len(seq_u), len(seq_v))
        if min_len == 0: return 1.0
        # Simple hamming on overlapping part
        diffs = sum(1 for i in range(min_len) if seq_u[i] != seq_v[i])
        # Add penalty for length difference
        diffs += abs(len(seq_u) - len(seq_v)) 
        return diffs / max(len(seq_u), len(seq_v))

    X = np.array(ids).reshape(-1, 1)
    dists = pdist(X, metric=hamming_normalized)
    return squareform(dists)

def build_newick_tree(dist_matrix: np.ndarray, labels: list[str]) -> str:
    """Build UPGMA tree and return Newick string."""
    Z = linkage(dist_matrix, method='average')
    n = len(labels)
    nodes = {i: labels[i] for i in range(n)}
    
    for i, row in enumerate(Z):
        c1, c2, dist, count = row
        new_idx = n + i
        branch_len = dist / 2.0
        c1_label = nodes.get(int(c1), f"Node_{int(c1)}")
        c2_label = nodes.get(int(c2), f"Node_{int(c2)}")
        nodes[new_idx] = f"({c1_label}:{branch_len:.4f},{c2_label}:{branch_len:.4f})"
        
    return nodes[n + len(Z) - 1] + ";"

def main() -> None:
    # 1. Load Data
    print(f"Loading sequences from {IN_FR_SEQ}...")
    df_seq = pd.read_csv(IN_FR_SEQ)
    df_meta = pd.read_csv(IN_METADATA)
    
    # Clean metadata columns
    strat_col = "strategy_group_y" if "strategy_group_y" in df_meta.columns else "strategy_group"
    h2_col = "h2_class_y" if "h2_class_y" in df_meta.columns else "h2_class"
    
    if strat_col not in df_meta.columns: strat_col = "strategy_group_x"
    if h2_col not in df_meta.columns: h2_col = "h2_class_x"
        
    df_merged = df_seq.merge(df_meta[["antibody_id", strat_col, h2_col, "h3_length"]], on="antibody_id")
    df_merged = df_merged.rename(columns={strat_col: "Strategy", h2_col: "H2_Fold", "h3_length": "H3_Len"})
    
    # 2. Prepare Sequences
    all_labels = df_merged["antibody_id"].tolist()
    all_fr2 = df_merged["fr2_sequence"].tolist()
    all_fr3 = df_merged["fr3_sequence"].tolist()
    
    # Add references
    ref_labels = list(REF_SEQUENCES.keys())
    
    final_labels = all_labels + ref_labels
    final_fr2 = all_fr2 + [REF_SEQUENCES[k]["fr2"] for k in ref_labels]
    final_fr3 = all_fr3 + [REF_SEQUENCES[k]["fr3"] for k in ref_labels]
    final_combined = [f2 + f3 for f2, f3 in zip(final_fr2, final_fr3)]
    
    # 3. Build Trees and Analyze
    tree_configs = [
        ("FR2", final_fr2, OUT_TREE_FR2),
        ("FR3", final_fr3, OUT_TREE_FR3),
        ("FR2+FR3", final_combined, OUT_TREE_COMBINED)
    ]
    
    report_lines = []
    report_lines.append("="*80)
    report_lines.append("Phylogenetic Discrimination Analysis: FR2 vs FR3 vs Combined")
    report_lines.append("="*80)
    report_lines.append("")
    report_lines.append("References used:")
    for k, v in REF_SEQUENCES.items():
        report_lines.append(f"  - {k} ({v['type']})")
    report_lines.append("")
    
    for region_name, seqs, out_file in tree_configs:
        print(f"Processing {region_name}...")
        dist_mat = compute_distance_matrix(seqs)
        dist_df = pd.DataFrame(dist_mat, index=final_labels, columns=final_labels)
        
        # Build Tree
        newick = build_newick_tree(dist_mat, final_labels)
        out_file.write_text(newick, encoding="utf-8")
        
        # Calculate Human vs Alpaca Proximity Score
        human_refs = [l for l in ref_labels if "Human" in l]
        alpaca_refs = [l for l in ref_labels if "Alpaca" in l]
        
        vhh_scores = []
        for vhh_id in all_labels:
            d_human = dist_df.loc[vhh_id, human_refs].mean()
            d_alpaca = dist_df.loc[vhh_id, alpaca_refs].mean()
            # Positive = Closer to Human
            score = d_alpaca - d_human 
            
            meta = df_merged[df_merged["antibody_id"] == vhh_id].iloc[0]
            vhh_scores.append({
                "antibody_id": vhh_id,
                "score": score,
                "strategy": meta["Strategy"],
                "h2_fold": meta["H2_Fold"],
                "h3_len": meta["H3_Len"]
            })
            
        scores_df = pd.DataFrame(vhh_scores)
        
        report_lines.append(f"## Region: {region_name}")
        report_lines.append(f"Tree File: {out_file.name}")
        report_lines.append(f"Mean Human-Shift Score: {scores_df['score'].mean():.4f}")
        
        # Test 1: Strategy
        bm_scores = scores_df[scores_df["strategy"] == "BM"]["score"]
        sr_scores = scores_df[scores_df["strategy"] == "SR"]["score"]
        nat_scores = scores_df[scores_df["strategy"] == "Native"]["score"]
        
        try:
            stat, p_strat = stats.kruskal(bm_scores, sr_scores, nat_scores)
        except ValueError: p_strat = 1.0
        
        report_lines.append(f"1. Strategy Discrimination (P-value): {p_strat:.4f}")
        report_lines.append(f"   - BM Mean: {bm_scores.mean():.3f}")
        report_lines.append(f"   - SR Mean: {sr_scores.mean():.3f}")
        report_lines.append(f"   - Native Mean: {nat_scores.mean():.3f}")
        
        # Test 2: CDR2 Fold
        h2_9 = scores_df[scores_df["h2_fold"] == "H2-9-1"]["score"]
        h2_10 = scores_df[scores_df["h2_fold"] == "H2-10-1"]["score"]
        try:
            stat, p_fold = stats.mannwhitneyu(h2_9, h2_10)
        except ValueError: p_fold = 1.0
        report_lines.append(f"2. CDR2 Fold Discrimination (P-value): {p_fold:.4f}")
        report_lines.append(f"   - H2-9-1 Mean: {h2_9.mean():.3f}")
        report_lines.append(f"   - H2-10-1 Mean: {h2_10.mean():.3f}")

        # Test 3: CDR3 Length Correlation
        corr, p_len = stats.spearmanr(scores_df["h3_len"], scores_df["score"])
        report_lines.append(f"3. CDR3 Length Correlation: rho={corr:.3f}, p={p_len:.4f}")
        
        if p_fold < 0.05 and p_strat > 0.05:
            report_lines.append("-> VERDICT: Structure-Driven (CDR2 Fold)")
        elif p_strat < 0.05:
            report_lines.append("-> VERDICT: Strategy-Driven")
        else:
            report_lines.append("-> VERDICT: No strong discrimination")
            
        report_lines.append("-" * 60)
        report_lines.append("")
        
    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Analysis complete. Report written to: {OUT_REPORT}")

if __name__ == "__main__":
    main()
