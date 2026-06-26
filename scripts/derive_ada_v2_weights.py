import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

ROOT = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite")
CSV_PATH = ROOT / "data" / "immunogenicity_knowledge_base" / "master" / "ada_master_136_curated.csv"

def classify_assay(row):
    platform = str(row.get("assay_platform", "")).strip().upper()
    gen = str(row.get("assay_generation", "")).strip().lower()
    if "bridg" in gen: return "Bridging"
    elif "tier" in gen: return "Tiered / Drug-tolerant"
    elif gen == "1.0" or (gen == "1.5"): return "ELISA (1st-gen)"
    elif gen == "2.0" or "ECL" in platform: return "ECL (2nd-gen)"
    else: return "Unknown/Other"

df = pd.read_csv(CSV_PATH)
df["ada_first_pct"] = pd.to_numeric(df["ada_first_pct"], errors="coerce")
df["assay_category"] = df.apply(classify_assay, axis=1)
df["origin_class"] = "Other"
df.loc[df["origin"] == "engineered", "origin_class"] = "HU"
df.loc[df["origin"] == "natural", "origin_class"] = "FH"

# Focus on High-Sensitivity Subset (n=122)
df_hs = df[df["assay_category"].isin(["ECL (2nd-gen)", "Tiered / Drug-tolerant"])]
df_hu = df_hs[df_hs["origin_class"] == "HU"]
df_fh = df_hs[df_hs["origin_class"] == "FH"]

def derive_scoring_system(sub_df, label):
    print(f"\n=== Deriving Scoring System for {label} (n={len(sub_df)}) ===")
    
    # Candidate features for the scoring system
    candidates = [
        ("immuno_n_high", "MHC-II Epitopes (Degradation Risk)"),
        ("interface_n_pairs", "Interface Stability (Vernier Support)"),
        ("vl_germline_identity", "Germline Identity (Human-ness)"),
        ("agg_motifs", "Aggregation Propensity (CMC Risk)"),
        ("surf_n_patches", "Surface Hydrophobicity"),
        ("instability_index", "Structural Instability")
    ]
    
    results = []
    for col, name in candidates:
        valid = sub_df[[col, "ada_first_pct"]].dropna()
        if len(valid) >= 15:
            rho, p = stats.spearmanr(valid[col], valid["ada_first_pct"])
            # Weight is based on rho^2 (explained variance) normalized
            results.append({"feature": col, "name": name, "rho": rho, "p": p})
    
    # Calculate weights based on abs(rho)
    total_abs_rho = sum(abs(r["rho"]) for r in results if r["p"] < 0.2) # Use trend-level features
    
    print(f"{'Feature Name':35} | {'rho':>7} | {'p-value':>7} | {'Weight (%)':>10}")
    print("-" * 75)
    for r in results:
        weight = (abs(r["rho"]) / total_abs_rho * 100) if r["p"] < 0.2 else 0
        sig = "*" if r["p"] < 0.05 else ("+" if r["p"] < 0.15 else "")
        print(f"{r['name']:35} | {r['rho']:+7.4f} | {r['p']:7.4f}{sig} | {weight:9.1f}%")

derive_scoring_system(df_fh, "Fully Human (FH) - High-Sens")
derive_scoring_system(df_hu, "Humanized (HU) - High-Sens")
