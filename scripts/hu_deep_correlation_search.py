import pandas as pd
from scipy import stats
from pathlib import Path
import numpy as np

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

# Get all numeric columns
num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
num_cols = [f for f in num_cols if f != "ada_first_pct" and f != "approval_year"]

results = []
print(f"Searching for HU High-Sens correlations (n={len(df_hs_hu)})...")
for col in num_cols:
    valid = df_hs_hu[[col, "ada_first_pct"]].dropna()
    if len(valid) >= 20:
        rho, p = stats.spearmanr(valid[col], valid["ada_first_pct"])
        results.append((col, rho, p, len(valid)))

results.sort(key=lambda x: abs(x[1]), reverse=True)

print(f"Top Correlations for HU High-Sens (n={len(df_hs_hu)})")
print(f"{'Feature':40} | {'rho':>7} | {'p-value':>7} | {'n':>3}")
print("-" * 70)
for res in results[:25]:
    print(f"{res[0]:40} | {res[1]:+7.4f} | {res[2]:7.4f} | {res[3]:3}")
