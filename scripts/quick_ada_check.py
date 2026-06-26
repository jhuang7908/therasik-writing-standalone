import pandas as pd
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
    elif "ELISA" in platform: return "ELISA (1st-gen)"
    else: return "Unknown/Other"

df = pd.read_csv(CSV_PATH)
df["ada_first_pct"] = pd.to_numeric(df["ada_first_pct"], errors="coerce")
df["assay_category"] = df.apply(classify_assay, axis=1)
df["origin_class"] = "Other"
df.loc[df["origin"] == "engineered", "origin_class"] = "HU"
df.loc[df["origin"] == "natural", "origin_class"] = "FH"

df_hs = df[df["assay_category"].isin(["ECL (2nd-gen)", "Tiered / Drug-tolerant"])]
df_hs_hu = df_hs[df_hs["origin_class"] == "HU"]
df_hs_fh = df_hs[df_hs["origin_class"] == "FH"]

feats = ["immuno_tcia_score", "immuno_n_high", "immuno_n_clusters", "vh_germline_identity", "vl_germline_identity", "surf_frac_exposed_vh", "surf_frac_exposed_vl", "interface_n_pairs"]

print(f"High-Sens HU (n={len(df_hs_hu)})")
for f in feats:
    valid = df_hs_hu[[f, "ada_first_pct"]].dropna()
    if len(valid) >= 10:
        rho, p = stats.spearmanr(valid[f], valid["ada_first_pct"])
        print(f"{f:25}: rho={rho:+.4f}, p={p:.4f}")

print(f"\nHigh-Sens FH (n={len(df_hs_fh)})")
for f in feats:
    valid = df_hs_fh[[f, "ada_first_pct"]].dropna()
    if len(valid) >= 10:
        rho, p = stats.spearmanr(valid[f], valid["ada_first_pct"])
        print(f"{f:25}: rho={rho:+.4f}, p={p:.4f}")
