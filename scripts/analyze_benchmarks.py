import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Use v3 if it exists, otherwise v2
if (ROOT / "data/vhh_master_benchmarks_v3.csv").exists():
    df = pd.read_csv(ROOT / "data/vhh_master_benchmarks_v3.csv")
elif (ROOT / "data/vhh_master_benchmarks_v2.csv").exists():
    df = pd.read_csv(ROOT / "data/vhh_master_benchmarks_v2.csv")
else:
    df = pd.read_csv(ROOT / "data/vhh_master_benchmarks_v1.csv")

# Group by category and calculate mean/median
stats = df.groupby("category").agg({
    "abnativ_delta": ["mean", "median"],
    "nanobert_pll": ["mean", "median"],
    "hpr_index": ["mean", "median"],
    "pI": ["mean", "median"],
    "GRAVY": ["mean", "median"],
    "compactness_A": ["mean", "median", "count"]
}).round(4)

print("### Comparative Statistics by Category")
print(stats)

# Detailed analysis of Autonomous Human VH vs Engineered Human VH vs Natural VHH
print("\n### Key Metric Comparison: Naturalness & Compactness")
key_metrics = df.groupby("category").agg({
    "abnativ_delta": "median",
    "nanobert_pll": "median",
    "compactness_A": "median"
}).round(4)
print(key_metrics)

# Look at top and bottom 5 for AbNatiV Delta in Autonomous VH
print("\n### Top 5 Autonomous Human VH (Most VHH-like by AbNatiV Delta)")
auto_vh = df[df["category"] == "Autonomous_Human_VH"]
print(auto_vh.sort_values("abnativ_delta", ascending=False).head(5)[["id", "abnativ_delta", "nanobert_pll", "compactness_A"]])

print("\n### Bottom 5 Autonomous Human VH (Least VHH-like)")
print(auto_vh.sort_values("abnativ_delta", ascending=True).head(5)[["id", "abnativ_delta", "nanobert_pll", "compactness_A"]])

# Porustobart vs others
porustobart = df[df["id"] == "Porustobart"]
if not porustobart.empty:
    print("\n### Porustobart Benchmarks")
    print(porustobart[["id", "category", "abnativ_delta", "nanobert_pll", "compactness_A", "pI", "GRAVY"]])
