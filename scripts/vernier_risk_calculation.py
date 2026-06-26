import pandas as pd
from scipy import stats
from pathlib import Path
import numpy as np

ROOT = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite")
CSV_PATH = ROOT / "data" / "immunogenicity_knowledge_base" / "master" / "ada_master_136_curated.csv"

# Vernier Zone positions (Chothia numbering approximate mapped to common regions)
# VH: 2, 27-30, 47-49, 67-71, 73, 78, 93-94
# VL: 2, 4, 35-36, 46-49, 64, 66, 68, 71, 98
# Note: In our dataset, we have vh_fr1, vh_cdr1, etc. but not per-residue flags.
# However, we can look at "interface_n_pairs" and "vh_vl_angle_deg" as proxies for Vernier stability.
# And "vh_germline_identity" / "vl_germline_identity" as proxies for Back-mutations.

def classify_assay(row):
    platform = str(row.get("assay_platform", "")).strip().upper()
    gen = str(row.get("assay_generation", "")).strip().lower()
    if "bridg" in gen: return "Bridging"
    elif "tier" in gen: return "Tiered / Drug-tolerant"
    elif gen == "1.0" or (gen == "1.5"): return "ELISA (1st-gen)"
    elif gen == "2.0" or "ECL" in platform: return "ECL (2nd-gen)"
    elif "ELISA" in platform: return "ELISA (1st-gen)"
    else: return "Unknown/Other"

df = pd.read_csv(CSV_PATH)
df["ada_first_pct"] = pd.to_numeric(df["ada_first_pct"], errors="coerce")
df["assay_category"] = df.apply(classify_assay, axis=1)
df["origin_class"] = "Other"
df.loc[df["origin"] == "engineered", "origin_class"] = "HU"
df.loc[df["origin"] == "natural", "origin_class"] = "FH"

# High Sensitivity Subset
df_hs = df[df["assay_category"].isin(["ECL (2nd-gen)", "Tiered / Drug-tolerant"])]
df_hu = df_hs[df_hs["origin_class"] == "HU"]
df_fh = df_hs[df_hs["origin_class"] == "FH"]

# Features related to Vernier/Interface/Epitopes
feats = [
    ("immuno_tcia_score", "TCIA Score (Overall)"),
    ("immuno_n_high", "MHC-II High-Risk (Epitopes)"),
    ("immuno_n_clusters", "T-cell Clusters"),
    ("interface_n_pairs", "Interface Stability (Vernier Proxy)"),
    ("vh_vl_angle_deg", "VH-VL Packing (Vernier Proxy)"),
    ("vh_germline_identity", "VH Identity (Back-mut Proxy)"),
    ("vl_germline_identity", "VL Identity (Back-mut Proxy)"),
    ("agg_motifs", "Aggregation Motifs (CMC Risk)"),
    ("surf_n_patches", "Surface Patches (CMC Risk)"),
    ("instability_index", "Instability Index")
]

def run_analysis(sub_df, label):
    print(f"\n--- Analysis for {label} (n={len(sub_df)}) ---")
    results = []
    for col, name in feats:
        valid = sub_df[[col, "ada_first_pct"]].dropna()
        if len(valid) >= 15:
            rho, p = stats.spearmanr(valid[col], valid["ada_first_pct"])
            results.append((name, rho, p, len(valid)))
    
    # Sort by rho absolute value
    results.sort(key=lambda x: abs(x[1]), reverse=True)
    print(f"{'Feature':35} | {'rho':>7} | {'p-value':>7} | {'n':>3}")
    print("-" * 65)
    for res in results:
        sig = "*" if res[2] < 0.05 else ""
        print(f"{res[0]:35} | {res[1]:+7.4f} | {res[2]:7.4f}{sig} | {res[3]:3}")

run_analysis(df_hu, "Humanized (HU) High-Sens")
run_analysis(df_fh, "Fully Human (FH) High-Sens")
