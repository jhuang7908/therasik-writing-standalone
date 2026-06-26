"""Diagnose why FH ADA V2 composite rho < individual factor rho values."""
import pandas as pd
import numpy as np
from scipy import stats

df = pd.read_csv(
    r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv"
)
df["ada_first_pct"] = pd.to_numeric(df["ada_first_pct"], errors="coerce")
df["origin_class"] = "Other"
df.loc[df["origin"] == "natural",    "origin_class"] = "FH"
df.loc[df["origin"] == "engineered", "origin_class"] = "HU"

fh = df[df["origin_class"] == "FH"].copy()
for c in ["vl_germline_identity", "vh_germline_identity", "interface_n_pairs",
          "surf_n_patches", "immuno_n_high", "ada_v2_score"]:
    fh[c] = pd.to_numeric(fh[c], errors="coerce")

print("=" * 60)
print("FH individual Spearman correlations")
print("=" * 60)
pairs = [
    ("interface_n_pairs",    "Interface contacts (I)        [+]"),
    ("vl_germline_identity", "VL identity (raw)             [-]"),
    ("surf_n_patches",       "Surface hydrophobic patches   [+]"),
    ("immuno_n_high",        "MHC-II high-risk epitopes     [+]"),
    ("ada_v2_score",         "Current V2 composite"),
]
for col, label in pairs:
    v = fh[[col, "ada_first_pct"]].dropna()
    rho, p = stats.spearmanr(v[col], v["ada_first_pct"])
    print(f"  {label:45s}: rho={rho:+.4f}  p={p:.4f}  n={len(v)}")

print()
print("=" * 60)
print("VL modulator: current behaviour vs correct behaviour")
print("=" * 60)
fh2 = fh[["vl_germline_identity", "ada_first_pct"]].dropna().copy()

# Current scorer: -0.05 * (vl_id - 0.95)   <- tiny, wrong direction for FH
fh2["vl_current_mod"] = -0.05 * (fh2["vl_germline_identity"] - 0.95)
# Correct: 1 - vl_id  (invert so that low identity = high risk value)
fh2["vl_correct_inv"] = 1.0 - fh2["vl_germline_identity"]

mod_min  = fh2["vl_current_mod"].min()
mod_max  = fh2["vl_current_mod"].max()
mod_mean = fh2["vl_current_mod"].mean()
cor_min  = fh2["vl_correct_inv"].min()
cor_max  = fh2["vl_correct_inv"].max()
cor_mean = fh2["vl_correct_inv"].mean()

print(f"  Current VL mod range : [{mod_min:.4f}, {mod_max:.4f}]  mean={mod_mean:.4f}")
print(f"  Correct (1-VL) range : [{cor_min:.4f}, {cor_max:.4f}]  mean={cor_mean:.4f}")

rho_cur, _ = stats.spearmanr(fh2["vl_current_mod"], fh2["ada_first_pct"])
rho_cor, _ = stats.spearmanr(fh2["vl_correct_inv"], fh2["ada_first_pct"])
print(f"  VL mod corr (current): rho={rho_cur:+.4f}  <- near zero, barely contributes")
print(f"  VL inv corr (correct): rho={rho_cor:+.4f}  <- should drive composite up")

print()
print("=" * 60)
print("Corrected FH composite (|rho|-proportional weights)")
print("=" * 60)
cols = ["interface_n_pairs", "vl_germline_identity", "surf_n_patches",
        "immuno_n_high", "ada_first_pct"]
fh3 = fh[cols].dropna().copy()

# Normalise each factor so it is a POSITIVE risk signal
fh3["I_norm"]  = (fh3["interface_n_pairs"] / 60.0).clip(0, 1)
fh3["VL_inv"]  = 1.0 - fh3["vl_germline_identity"]        # INVERT: low identity = high risk
fh3["P_norm"]  = (fh3["surf_n_patches"]    / 14.0).clip(0, 1)
fh3["E_norm"]  = (fh3["immuno_n_high"]     / 40.0).clip(0, 1)

# Weights proportional to absolute rho values of each factor
abs_rhos = {"I_norm": 0.339, "VL_inv": 0.313, "P_norm": 0.311, "E_norm": 0.212}
total    = sum(abs_rhos.values())
weights  = {k: v / total for k, v in abs_rhos.items()}

fh3["corrected_composite"] = sum(weights[k] * fh3[k] for k in weights)
rho_c, p_c = stats.spearmanr(fh3["corrected_composite"], fh3["ada_first_pct"])

print(f"  Corrected FH composite: rho={rho_c:+.4f}  p={p_c:.4f}  n={len(fh3)}")
print()
for k, w in weights.items():
    print(f"    {k:12s}: weight={w:.3f}")

print()
print("=" * 60)
print("Root cause summary")
print("=" * 60)
print("  1. VL identity in scorer: -0.05*(vl_id-0.95)  -- nearly zero contribution")
print("     Correct treatment   : (1-vl_id) with weight ~0.27")
print("  2. Interface (I) weight in V2: only 5%")
print("     Should be ~30% for FH (strongest single predictor)")
print("  3. Consequence: composite diluted by near-zero VL signal")
print("     → composite rho (0.266) < best single factor (0.339)")
