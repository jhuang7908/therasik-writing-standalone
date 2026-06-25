import pandas as pd
from scipy import stats
from pathlib import Path

df = pd.read_csv("projects/CD3_VH2VHH_Batch_20260515/vl_interface_audit/y91_sasa_vs_cdr3_length.csv")

print(f"n total = {len(df)}\n")

# All cohort
r_p, p_p = stats.pearsonr(df["cdr3_len"], df["sasa_pos91"])
r_s, p_s = stats.spearmanr(df["cdr3_len"], df["sasa_pos91"])
print(f"All cohort (n={len(df)}):")
print(f"  Pearson  r = {r_p:+.3f}, p = {p_p:.4f}")
print(f"  Spearman r = {r_s:+.3f}, p = {p_s:.4f}")

# Clinical only
sub = df[df["is_VHH_clinical"]]
r_p, p_p = stats.pearsonr(sub["cdr3_len"], sub["sasa_pos91"])
r_s, p_s = stats.spearmanr(sub["cdr3_len"], sub["sasa_pos91"])
print(f"\nClinical_VHH only (n={len(sub)}):")
print(f"  Pearson  r = {r_p:+.3f}, p = {p_p:.4f}")
print(f"  Spearman r = {r_s:+.3f}, p = {p_s:.4f}")

print("\n--- Bin comparison (Mann-Whitney U) ---")
short = df[df["cdr3_len"] <= 12]["sasa_pos91"].values
long = df[df["cdr3_len"] >= 18]["sasa_pos91"].values
u, p = stats.mannwhitneyu(short, long, alternative="greater")
print(f"Short CDR3 (<=12, n={len(short)}) vs Long CDR3 (>=18, n={len(long)}):")
print(f"  mean SASA: {short.mean():.2f} vs {long.mean():.2f}  (diff = {short.mean()-long.mean():+.2f})")
print(f"  median:    {pd.Series(short).median():.2f} vs {pd.Series(long).median():.2f}")
print(f"  Mann-Whitney U = {u:.0f}, p (short > long) = {p:.4f}")

print("\n--- Fraction passing 40 A^2 gate ---")
for lo, hi in [(0,12),(13,17),(18,30)]:
    sub = df[(df["cdr3_len"]>=lo) & (df["cdr3_len"]<=hi)]
    frac = (sub["sasa_pos91"] > 40).mean()
    print(f"  CDR3 {lo}-{hi}: n={len(sub):<3}  fraction SASA>40 = {frac:.0%}")

# 30 thresh
print("\n--- Fraction passing 30 A^2 gate ---")
for lo, hi in [(0,12),(13,17),(18,30)]:
    sub = df[(df["cdr3_len"]>=lo) & (df["cdr3_len"]<=hi)]
    frac = (sub["sasa_pos91"] > 30).mean()
    print(f"  CDR3 {lo}-{hi}: n={len(sub):<3}  fraction SASA>30 = {frac:.0%}")
