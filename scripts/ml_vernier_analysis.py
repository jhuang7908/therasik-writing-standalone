import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Load Data
METRICS_PATH = Path("data/humanization_assay/structure_metrics_summary.json")
LOOKUP_PATH = Path("data/humanization_assay/vernier_index_lookup.json")

def load_data():
    with open(METRICS_PATH, encoding="utf-8") as f:
        metrics = json.load(f)
    
    # Flatten metrics into Vernier-centric rows
    # Target: "Is this Vernier residue Human or Mouse?" (Proxy: Is it conserved in engineered set?)
    # Actually, for this dataset (Engineered Humanized), the Vernier residues ARE the result of humanization decisions.
    # So we want to predict: "What amino acid type (or property) is at this position?" 
    # OR better: "Is this position occupied by a residue that matches the Germline (Human) or Donor (Mouse)?"
    # Since we don't have the donor/germline sequences here, we can look at "Residue Identity" directly
    # and see which structural features predict it.
    
    # But a more direct "Rule Discovery" approach is:
    # Input: Structural Features (SASA, Packing, Dist to CDR, Angle, Canonical Class)
    # Output: The specific Residue Choice (or "Is it a critical Vernier residue?")
    
    # Let's pivot: We want to find PATTERNS.
    # "For H2-10-1 antibodies, VH_71 is always Arg when Distance < 4.0A"
    
    rows = []
    for m in metrics:
        if m.get("errors"): continue
        
        # Global features
        pdb = m["pdb_path"]
        h1 = m["canonical"].get("H1", "Unknown")
        h2 = m["canonical"].get("H2", "Unknown")
        l1 = m["canonical"].get("L1", "Unknown")
        angle = m.get("vh_vl_angle_deg")
        
        # Per-Vernier features
        # We focus on key Vernier positions: VH 27-30, 48, 49, 71, 93, 94; VL 36, 46, 49, 71
        # We need the actual amino acid at these positions to see the "decision".
        # The metrics JSON doesn't store the AA sequence directly in a structured way, 
        # but we can infer it or we might need to re-parse.
        # Wait, step 2 didn't save the AA identity in `vernier_packing` keys, just "VH_71".
        # We need to fetch the AA identity from the structure or lookup.
        # Actually, `vernier_index_lookup.json` has indices, not AAs.
        # We might need to quickly re-read PDBs or use `structure_metrics_humanization.py` to dump AAs.
        
        # Let's assume we want to predict structural properties first, 
        # OR we assume the "Engineered" set represents "Successful Humanization".
        # We want to know: "Which structural features distinguish different Framework/Canonical contexts?"
        
        # Let's build a dataset of "Vernier Environments":
        # Row = (PDB, Position, Canonical_Context, Packing, SASA, Dist_CDR, Angle)
        
        packing = m.get("vernier_packing", {})
        sasa = m.get("vernier_sasa_per_residue", {})
        # Distances are summarized, not per-residue-to-CDR. 
        # `vernier_cdr_distances` is "Vernier_to_H1", meaning min dist of ANY vernier to H1.
        # We need per-residue distance to CDRs to be precise.
        # The current JSON has `vernier_cdr_distances` as global.
        # Ah, looking at `structure_metrics_humanization.py`:
        # It computes `min_dist_set_to_set`. It does NOT output per-residue distance.
        
        # LIMITATION: We lack per-residue distance to CDR in the current JSON.
        # We have per-residue Packing and SASA.
        
        for pos_key, pack_val in packing.items():
            # pos_key like "VH_71"
            chain, num = pos_key.split("_")
            
            row = {
                "PDB": pdb,
                "Position": pos_key,
                "Chain": chain,
                "Kabat": int(num),
                "H1_Class": h1,
                "H2_Class": h2,
                "L1_Class": l1,
                "VH_VL_Angle": angle,
                "Packing": pack_val,
                "SASA": sasa.get(pos_key, np.nan),
                # "Dist_to_CDR": ??? (Missing)
            }
            rows.append(row)
            
    return pd.DataFrame(rows)

def train_model(df, target_pos="VH_71"):
    sub = df[df["Position"] == target_pos].copy()
    sub = sub.dropna(subset=["Packing", "VH_VL_Angle"])
    
    if len(sub) < 10: # Skip if too few samples
        return None, None
    
    le_h1 = LabelEncoder()
    le_h2 = LabelEncoder()
    le_l1 = LabelEncoder()
    
    # Handle unknown categories in future if needed, but here we just fit/transform
    sub["H1_Code"] = le_h1.fit_transform(sub["H1_Class"].astype(str))
    sub["H2_Code"] = le_h2.fit_transform(sub["H2_Class"].astype(str))
    sub["L1_Code"] = le_l1.fit_transform(sub["L1_Class"].astype(str))
    
    X = sub[["H1_Code", "H2_Code", "L1_Code", "VH_VL_Angle"]]
    y = sub["Packing"]
    
    # RandomForest Regressor
    from sklearn.ensemble import RandomForestRegressor
    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=1)
    rf.fit(X, y)
    
    importances = pd.Series(rf.feature_importances_, index=X.columns)
    return rf, importances

if __name__ == "__main__":
    df = load_data()
    print(f"Loaded {len(df)} residue records.")
    
    # All Vernier positions from structure_metrics_humanization.py / vernier_zone_weights.md
    # VH: 2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94
    # VL: 2, 4, 36, 46, 49, 69, 71, 98
    
    vh_positions = [2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94]
    vl_positions = [2, 4, 36, 46, 49, 69, 71, 98]
    
    all_res = [f"VH_{p}" for p in vh_positions] + [f"VL_{p}" for p in vl_positions]
    
    results = []
    for pos in all_res:
        _, imps = train_model(df, pos)
        if imps is not None:
            res_dict = imps.to_dict()
            res_dict["Position"] = pos
            results.append(res_dict)
            
    res_df = pd.DataFrame(results).set_index("Position")
    
    # Plot heatmap
    plt.figure(figsize=(10, 12))
    sns.heatmap(res_df, annot=True, cmap="viridis", fmt=".2f")
    plt.title("Feature Importance for Vernier Packing Density")
    plt.tight_layout()
    plt.savefig("data/humanization_assay/vernier_feature_importance.png")
    print("Saved heatmap to data/humanization_assay/vernier_feature_importance.png")
    
    # Print summary of top drivers
    print("\n--- Top Drivers Summary ---")
    for idx, row in res_df.iterrows():
        top_feat = row.idxmax()
        top_val = row.max()
        print(f"{idx}: Dominated by {top_feat} ({top_val:.2f})")
    
    # Save CSV
    res_df.to_csv("data/humanization_assay/vernier_feature_importance.csv")
