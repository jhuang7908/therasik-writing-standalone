import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
import re

ROOT = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite")
CSV_PATH = ROOT / "data" / "immunogenicity_knowledge_base" / "master" / "ada_master_136_curated.csv"

# Define Vernier Zone positions (Chothia numbering)
# VH: 2, 27-30, 47-49, 67-71, 73, 78, 93-94
# VL: 2, 4, 35-36, 46-49, 64, 66, 68, 71, 98

# Since we don't have residue-level germline mismatch data for every position yet,
# we will use the sequence segments (vh_fr1, vh_fr2, etc.) to calculate
# "Segment-specific Germline Identity" as a proxy for Vernier/Junction risk.

def calculate_segment_metrics(row):
    # This is a simplified proxy: 
    # Vernier Zone is heavily concentrated in FR2 and FR3.
    # Junctions are at the edges of FR and CDR.
    
    # We use the existing identity fields if available, or placeholder for now
    # In a real deep-dive, we would align vh_seq to its germline and count mismatches in Vernier positions.
    return pd.Series({
        "vh_fr2_id": row.get("vh_identity_imgt", 0.9), # Proxy
        "vh_fr3_id": row.get("vh_identity_imgt", 0.9), # Proxy
    })

def main():
    print("Loading ADA Master Data...")
    df = pd.read_csv(CSV_PATH)
    df["ada_first_pct"] = pd.to_numeric(df["ada_first_pct"], errors="coerce")
    
    # Filter for Humanized (HU) and High-Sensitivity Assays
    # (This is where the 'Design-Induced Risk' is most relevant)
    df_hu = df[(df["origin"] == "engineered") & 
               (df["assay_platform"].str.contains("ECL|Tiered|Drug-tolerant", na=False, case=False))]
    
    print(f"Analyzing HU High-Sens Subset (n={len(df_hu)})")

    # 1. Calculate Correlation for 'Interface Stability' (Vernier Proxy)
    valid_int = df_hu[["interface_n_pairs", "ada_first_pct"]].dropna()
    rho_int, p_int = stats.spearmanr(valid_int["interface_n_pairs"], valid_int["ada_first_pct"])
    
    # 2. Calculate Correlation for 'Packing Angle' (Vernier Proxy)
    valid_ang = df_hu[["vh_vl_angle_deg", "ada_first_pct"]].dropna()
    rho_ang, p_ang = stats.spearmanr(valid_ang["vh_vl_angle_deg"], valid_ang["ada_first_pct"])

    # 3. Calculate Correlation for 'Aggregation Motifs' (Vernier Failure Proxy)
    valid_agg = df_hu[["agg_motifs", "ada_first_pct"]].dropna()
    rho_agg, p_agg = stats.spearmanr(valid_agg["agg_motifs"], valid_agg["ada_first_pct"])

    print("\n=== Vernier Zone Distribution Characteristics & ADA Correlation (HU Only) ===")
    print(f"{'Characteristic (Proxy)':40} | {'rho':>7} | {'p-value':>7}")
    print("-" * 75)
    print(f"{'Interface Contact Density (Vernier Support)':40} | {rho_int:+7.4f} | {p_int:7.4f}")
    print(f"{'VH-VL Packing Angle (Vernier Geometry)':40} | {rho_ang:+7.4f} | {p_ang:7.4f}")
    print(f"{'Aggregation Propensity (Vernier Instability)':40} | {rho_agg:+7.4f} | {p_agg:7.4f}")

    print("\n：")
    if p_agg < 0.15:
        print(f"1.  (rho={rho_agg:.3f})  HU ， Vernier 。")
    if abs(rho_ang) > 0.1:
        print(f"2.  (rho={rho_ang:.3f})  Vernier 。")

if __name__ == "__main__":
    main()
