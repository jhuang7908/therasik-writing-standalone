"""
scripts/benchmark_ada_v2_dualtrack.py
═══════════════════════════════════════════════════════════════════════════════
ADA V2 Dual-Track Benchmark — End-to-End Demo
═══════════════════════════════════════════════════════════════════════════════

For each of the 138 curated clinical antibodies:
  1. Auto-detect track (FH = origin=="natural", HU = origin=="engineered")
  2. Run ADAScorer.score() with all available molecular features
  3. Assign stratified risk tier: LOW / MEDIUM / HIGH
  4. Compare to clinical ADA incidence (ada_first_pct)

Outputs:
  - Console benchmark report (Spearman, balanced accuracy, PPV/NPV)
  - fig_benchmark_confusion.png  — confusion matrix (binary HIGH vs others)
  - fig_benchmark_roc.png        — ROC curve (FH / HU / ALL)
  - fig_benchmark_score_dist.png — score distribution by track and ADA tier
  - benchmark_ada_v2_results.csv — per-antibody predictions

Usage:
  conda activate anarcii
  python scripts/benchmark_ada_v2_dualtrack.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from scipy import stats
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT   = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CSV_IN = ROOT / "data" / "immunogenicity_knowledge_base" / "master" / "ada_master_136_curated.csv"
OUT_DIR = ROOT / "data" / "immunogenicity_knowledge_base" / "reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Import scorer ──────────────────────────────────────────────────────────────
from core.immunogenicity.ada_risk_scorer import ADAScorer

# ── Plot style ─────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.size": 14, "font.weight": "bold",
    "axes.labelsize": 15, "axes.labelweight": "bold",
    "axes.titlesize": 16, "axes.titleweight": "bold",
    "xtick.labelsize": 13, "ytick.labelsize": 13,
    "legend.fontsize": 13,
    "figure.titlesize": 18, "figure.titleweight": "bold",
    "font.sans-serif": ["Noto Sans SC", "Inter", "Arial"],
    "axes.spines.top": False, "axes.spines.right": False,
})
FH_COLOR  = "#0d9488"   # teal
HU_COLOR  = "#6366f1"   # indigo
ALL_COLOR = "#374151"   # grey

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — Score all 138 antibodies
# ═══════════════════════════════════════════════════════════════════════════════

print("═" * 68)
print("  ADA V2 Dual-Track Benchmark  |  138 clinical antibodies")
print("═" * 68)

df = pd.read_csv(CSV_IN)
df["ada_first_pct"] = pd.to_numeric(df["ada_first_pct"], errors="coerce")
scorer = ADAScorer()

rows_out = []
for _, row in df.iterrows():
    try:
        res = scorer.score(
            mhc_result   = {"summary": {"n_high": int(row.get("immuno_n_high") or 0)},
                            "n_clusters": int(row.get("immuno_n_clusters") or 0)},
            surf_result  = {"frac_exposed_vh":   row.get("surf_frac_exposed_vh"),
                            "n_hydrophilic_patches": int(row.get("surf_n_patches") or 0)},
            germline_identity_vh = row.get("vh_germline_identity"),
            germline_identity_vl = row.get("vl_germline_identity"),
            interface_n_pairs    = row.get("interface_n_pairs"),
            instability_index    = row.get("instability_index"),
            hydro_patch_max9     = row.get("hydro_patch_max9"),
            origin               = str(row.get("origin", "engineered")),
            targets              = row.get("targets"),
            fc_isotype           = row.get("fc_isotype"),
            route                = row.get("route_curated"),
            assay_method         = row.get("assay_method"),
            trial_duration_weeks = row.get("trial_duration_weeks"),
        )
        rows_out.append({
            "antibody":   row.get("antibody_name", ""),
            "track":      res["track"],
            "ada_score":  res["clinical_ada_score"],
            "risk_tier":  res["clinical_ada_risk"],
            "ada_pct":    row.get("ada_first_pct"),
            "z_composite": res["components"]["z_composite"],
            # key components
            "G_germline":  res["components"]["G_germline_dist"],
            "F_exposure":  res["components"]["F_inverse_exp"],
            "I_interface": res["components"]["I_interface"],
            "E_epitopes":  res["components"]["E_epitopes"],
            "P_patches":   res["components"]["P_patches"],
            "VL_dev":      res["components"]["VL_deviation"],
            "cmc_pen":     res["components"]["cmc_penalty"],
        })
    except Exception as exc:
        rows_out.append({
            "antibody": row.get("antibody_name", ""),
            "track": "?", "ada_score": np.nan,
            "risk_tier": "UNKNOWN", "ada_pct": row.get("ada_first_pct"),
        })

bench = pd.DataFrame(rows_out)
bench.to_csv(OUT_DIR / "benchmark_ada_v2_results.csv", index=False)

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — Spearman correlations
# ═══════════════════════════════════════════════════════════════════════════════

print("\n── Spearman ρ (ada_v2_score vs clinical ADA%) ──────────────────────────")
print(f"  {'Group':<8} {'n':>4}  {'ρ':>8}  {'p':>8}  {'sig':>6}")
print("  " + "─" * 40)
for label, mask in [("ALL", slice(None)), ("FH", bench["track"]=="FH"), ("HU", bench["track"]=="HU")]:
    sub = bench.loc[mask].dropna(subset=["ada_score","ada_pct"]) if isinstance(mask, slice) \
          else bench[mask].dropna(subset=["ada_score","ada_pct"])
    if len(sub) < 5:
        continue
    rho, p = spearmanr(sub["ada_score"], sub["ada_pct"])
    sig = "✓" if p < 0.05 else ("~" if p < 0.10 else "")
    print(f"  {label:<8} {len(sub):>4}  {rho:>+8.4f}  {p:>8.4f}  {sig:>6}")

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — Binary classification (ADA > 10% = clinically immunogenic)
# ═══════════════════════════════════════════════════════════════════════════════

ADA_THRESHOLD = 10.0  # % clinical significance threshold
bench_bin = bench.dropna(subset=["ada_score", "ada_pct"]).copy()
bench_bin["clinical_pos"] = bench_bin["ada_pct"] > ADA_THRESHOLD
bench_bin["pred_pos"]     = bench_bin["risk_tier"] == "HIGH"

def classification_metrics(sub: pd.DataFrame, label: str):
    tp = int(( sub["clinical_pos"] &  sub["pred_pos"]).sum())
    tn = int((~sub["clinical_pos"] & ~sub["pred_pos"]).sum())
    fp = int((~sub["clinical_pos"] &  sub["pred_pos"]).sum())
    fn = int(( sub["clinical_pos"] & ~sub["pred_pos"]).sum())
    sens = tp / (tp + fn + 1e-9)
    spec = tn / (tn + fp + 1e-9)
    ppv  = tp / (tp + fp + 1e-9)
    npv  = tn / (tn + fn + 1e-9)
    bacc = (sens + spec) / 2
    prev = sub["clinical_pos"].mean()
    return {"label": label, "n": len(sub),
            "n_pos_clinical": int(sub["clinical_pos"].sum()),
            "prevalence": round(prev, 3),
            "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "sensitivity": round(sens, 3), "specificity": round(spec, 3),
            "PPV": round(ppv, 3), "NPV": round(npv, 3),
            "balanced_acc": round(bacc, 3)}

metrics_all = [
    classification_metrics(bench_bin, "ALL"),
    classification_metrics(bench_bin[bench_bin["track"]=="FH"], "FH"),
    classification_metrics(bench_bin[bench_bin["track"]=="HU"], "HU"),
]

print(f"\n── Binary classification (HIGH risk = predicted positive, ADA>10% = true positive) ──")
print(f"  {'Group':<5} {'n':>4}  {'Sens':>6}  {'Spec':>6}  {'PPV':>6}  {'NPV':>6}  {'BAcc':>6}")
print("  " + "─" * 50)
for m in metrics_all:
    print(f"  {m['label']:<5} {m['n']:>4}  "
          f"{m['sensitivity']:>6.3f}  {m['specificity']:>6.3f}  "
          f"{m['PPV']:>6.3f}  {m['NPV']:>6.3f}  {m['balanced_acc']:>6.3f}")

# ── Risk tier distribution ─────────────────────────────────────────────────────
print("\n── Risk tier distribution ───────────────────────────────────────────────")
print(f"  {'Tier':<8}", end="")
for m in metrics_all:
    print(f"  {m['label']:>8}", end="")
print()
for tier in ["HIGH", "MEDIUM", "LOW"]:
    print(f"  {tier:<8}", end="")
    for m in metrics_all:
        sub = bench_bin if m["label"] == "ALL" else bench_bin[bench_bin["track"]==m["label"]]
        n   = int((sub["risk_tier"]==tier).sum())
        pct = 100 * n / len(sub) if len(sub) else 0
        print(f"  {n:>4} ({pct:>4.1f}%)", end="")
    print()

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — ROC curves
# ═══════════════════════════════════════════════════════════════════════════════

def roc_data(sub):
    y_true  = sub["clinical_pos"].astype(int).values
    y_score = sub["ada_score"].values
    thrs = np.linspace(0, 1, 200)
    fprs, tprs = [], []
    for t in thrs:
        pred = (y_score >= t).astype(int)
        tp = int(((y_true==1) & (pred==1)).sum())
        tn = int(((y_true==0) & (pred==0)).sum())
        fp = int(((y_true==0) & (pred==1)).sum())
        fn = int(((y_true==1) & (pred==0)).sum())
        fprs.append(fp / (fp + tn + 1e-9))
        tprs.append(tp / (tp + fn + 1e-9))
    # AUC via trapezoidal rule (reverse so x increases)
    fprs_arr = np.array(fprs[::-1])
    tprs_arr = np.array(tprs[::-1])
    auc = float(np.trapz(tprs_arr, fprs_arr))
    return fprs, tprs, auc

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — Plots
# ═══════════════════════════════════════════════════════════════════════════════

# ── Fig A: Score distribution — horizontal 3-panel, MASSIVE fonts ──────────────
groups = [(" (ALL)  n=129", bench_bin, ALL_COLOR),
          (" (FH)  n=53", bench_bin[bench_bin["track"]=="FH"], FH_COLOR),
          (" (HU)  n=76", bench_bin[bench_bin["track"]=="HU"], HU_COLOR)]

fig, axes = plt.subplots(1, 3, figsize=(22, 7))
fig.suptitle(" 6a — ADA V2 ：HIGH / MEDIUM / LOW ",
             fontsize=26, fontweight="bold", y=1.05)

for ax, (label, sub, color) in zip(axes, groups):
    high = sub[sub["risk_tier"]=="HIGH"]["ada_score"]
    med  = sub[sub["risk_tier"]=="MEDIUM"]["ada_score"]
    low  = sub[sub["risk_tier"]=="LOW"]["ada_score"]

    ax.hist(low,  bins=16, color="#22c55e", alpha=0.85, label=f"LOW ({len(low)})")
    ax.hist(med,  bins=10, color="#f59e0b", alpha=0.90, label=f"MEDIUM ({len(med)})")
    ax.hist(high, bins=10, color="#ef4444", alpha=0.90, label=f"HIGH ({len(high)})")
    
    # Thicker threshold lines
    ax.axvline(0.67, color="#ef4444", ls="--", lw=2.5, alpha=0.9)
    ax.axvline(0.64, color="#f59e0b", ls="--", lw=2.5, alpha=0.9)

    if len(sub) > 3:
        v = sub[["ada_score","ada_pct"]].dropna()
        rho, p = spearmanr(v["ada_score"], v["ada_pct"])
        title = f"{label}\nρ = {rho:+.3f}   p = {p:.3f}"
    else:
        title = label
        
    ax.set_title(title, fontsize=20, fontweight="bold", pad=15)
    ax.set_xlabel("ADA V2 ", fontsize=18, fontweight="bold")
    ax.set_ylabel("", fontsize=18, fontweight="bold")
    ax.tick_params(labelsize=16, width=2, length=6)
    ax.legend(fontsize=15, loc="upper left", frameon=True, shadow=True)
    
    # Make spines thicker
    for spine in ax.spines.values():
        spine.set_linewidth(2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

plt.tight_layout(pad=3.0)
plt.savefig(OUT_DIR / "fig_benchmark_score_dist.png", dpi=200, bbox_inches="tight")
plt.close()
print("\n✓ fig_benchmark_score_dist.png saved (horizontal 3-panel, MASSIVE fonts)")

# ── Fig B: ROC curves ─────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 6))
ax.set_title("ROC — ADA V2 \n(ADA>10% )")
ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.4)

for label, color, mask in [
    ("ALL", ALL_COLOR, slice(None)),
    ("FH",  FH_COLOR,  bench_bin["track"]=="FH"),
    ("HU",  HU_COLOR,  bench_bin["track"]=="HU"),
]:
    sub = bench_bin.loc[mask] if isinstance(mask, slice) else bench_bin[mask]
    if sub["clinical_pos"].sum() < 2:
        continue
    fprs, tprs, auc = roc_data(sub)
    ax.plot(fprs, tprs, color=color, lw=2.2,
            label=f"{label}  AUC={auc:.3f}  n={len(sub)}")

ax.set_xlabel(" (1 − )")
ax.set_ylabel(" ()")
ax.legend(loc="lower right")
plt.tight_layout()
plt.savefig(OUT_DIR / "fig_benchmark_roc.png", dpi=160, bbox_inches="tight")
plt.close()
print("✓ fig_benchmark_roc.png saved")

# ── Fig C: Confusion matrices ─────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle(" — HIGH  vs  ADA>10%")

for ax, (label, mask) in zip(axes, [
    ("ALL", slice(None)),
    ("FH ", bench_bin["track"]=="FH"),
    ("HU ", bench_bin["track"]=="HU"),
]):
    sub = bench_bin.loc[mask] if isinstance(mask, slice) else bench_bin[mask]
    if len(sub) < 2:
        ax.set_visible(False)
        continue
    tp = int(( sub["clinical_pos"] &  sub["pred_pos"]).sum())
    tn = int((~sub["clinical_pos"] & ~sub["pred_pos"]).sum())
    fp = int((~sub["clinical_pos"] &  sub["pred_pos"]).sum())
    fn = int(( sub["clinical_pos"] & ~sub["pred_pos"]).sum())
    mat = np.array([[tp, fn], [fp, tn]])
    labels = [["TP", "FN"], ["FP", "TN"]]
    cmap = sns.color_palette("Blues", as_cmap=True)
    sns.heatmap(mat, annot=False, fmt="d", cmap=cmap, ax=ax,
                cbar=False, linewidths=2, linecolor="white")
    for i in range(2):
        for j in range(2):
            val = mat[i, j]
            pct = 100 * val / len(sub)
            color = "white" if val > mat.max() * 0.5 else "#1f2937"
            ax.text(j + 0.5, i + 0.4, f"{labels[i][j]}\n{val}", ha="center",
                    va="center", fontsize=15, fontweight="bold", color=color)
            ax.text(j + 0.5, i + 0.72, f"({pct:.0f}%)", ha="center",
                    va="center", fontsize=11, color=color)
    ax.set_xticklabels([" HIGH", " HIGH"], fontweight="bold")
    ax.set_yticklabels([" ADA>10%", " ADA≤10%"], rotation=0, fontweight="bold")
    m = classification_metrics(sub, label)
    ax.set_title(f"{label}\nSens={m['sensitivity']:.2f}  Spec={m['specificity']:.2f}  BAcc={m['balanced_acc']:.2f}")

plt.tight_layout()
plt.savefig(OUT_DIR / "fig_benchmark_confusion.png", dpi=160, bbox_inches="tight")
plt.close()
print("✓ fig_benchmark_confusion.png saved")

# ── Fig D: Score scatter FH vs HU ─────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
fig.suptitle("ADA V2  vs  ADA  — ")

for ax, (label, color, mask) in zip(axes, [
    ("FH ", FH_COLOR, bench_bin["track"]=="FH"),
    ("HU ", HU_COLOR, bench_bin["track"]=="HU"),
]):
    sub = bench_bin[mask].dropna(subset=["ada_score","ada_pct"])
    # Color by risk tier
    palette = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#22c55e"}
    for tier, tcolor in palette.items():
        ts = sub[sub["risk_tier"]==tier]
        ax.scatter(ts["ada_score"], ts["ada_pct"],
                   c=tcolor, label=f"{tier} ({len(ts)})",
                   s=60, alpha=0.8, edgecolors="white", linewidths=0.5)
    # Regression line
    if len(sub) > 5:
        m, b = np.polyfit(sub["ada_score"], sub["ada_pct"], 1)
        xs = np.linspace(sub["ada_score"].min(), sub["ada_score"].max(), 100)
        ax.plot(xs, m*xs + b, color=color, lw=2, ls="--", alpha=0.7)
        rho, p = spearmanr(sub["ada_score"], sub["ada_pct"])
        ax.set_title(f"{label}  ρ={rho:+.3f}  p={p:.3f}  n={len(sub)}")
    else:
        ax.set_title(f"{label}  n={len(sub)}")
    ax.axvline(0.67, color="#ef4444", ls=":", lw=1.2, alpha=0.5, label="HIGH threshold")
    ax.axhline(10,   color="#6b7280",  ls=":", lw=1.2, alpha=0.5, label="ADA>10% gate")
    ax.set_xlabel("ADA V2 ")
    ax.set_ylabel(" ADA  (%)")
    ax.legend(fontsize=10, loc="upper left")

plt.tight_layout()
plt.savefig(OUT_DIR / "fig_benchmark_scatter_fh_hu.png", dpi=160, bbox_inches="tight")
plt.close()
print("✓ fig_benchmark_scatter_fh_hu.png saved")

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — Summary table for website
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "═" * 68)
print("  BENCHMARK SUMMARY")
print("═" * 68)

all_m = metrics_all[0]
fh_m  = metrics_all[1]
hu_m  = metrics_all[2]

fh_sub  = bench_bin[bench_bin["track"]=="FH"].dropna(subset=["ada_score","ada_pct"])
hu_sub  = bench_bin[bench_bin["track"]=="HU"].dropna(subset=["ada_score","ada_pct"])
all_sub = bench_bin.dropna(subset=["ada_score","ada_pct"])

fh_rho, fh_p   = spearmanr(fh_sub["ada_score"], fh_sub["ada_pct"])
hu_rho, hu_p   = spearmanr(hu_sub["ada_score"], hu_sub["ada_pct"])
all_rho, all_p = spearmanr(all_sub["ada_score"], all_sub["ada_pct"])

_, _, fh_auc  = roc_data(bench_bin[bench_bin["track"]=="FH"])
_, _, hu_auc  = roc_data(bench_bin[bench_bin["track"]=="HU"])
_, _, all_auc = roc_data(bench_bin)

print(f"""
     │ n   │ ρ (Spearman)  │ p-value │ AUC-ROC │ BAcc  │ Sens  │ Spec
  ───────┼─────┼───────────────┼─────────┼─────────┼───────┼───────┼──────
  ALL    │ {all_m['n']:>3} │ {all_rho:>+13.4f} │ {all_p:>7.4f} │ {all_auc:>7.3f} │ {all_m['balanced_acc']:>5.3f} │ {all_m['sensitivity']:>5.3f} │ {all_m['specificity']:>5.3f}
  FH     │ {fh_m['n']:>3} │ {fh_rho:>+13.4f} │ {fh_p:>7.4f} │ {fh_auc:>7.3f} │ {fh_m['balanced_acc']:>5.3f} │ {fh_m['sensitivity']:>5.3f} │ {fh_m['specificity']:>5.3f}
  HU     │ {hu_m['n']:>3} │ {hu_rho:>+13.4f} │ {hu_p:>7.4f} │ {hu_auc:>7.3f} │ {hu_m['balanced_acc']:>5.3f} │ {hu_m['sensitivity']:>5.3f} │ {hu_m['specificity']:>5.3f}

  Risk tier counts (n):
    HIGH   = {int((bench['risk_tier']=='HIGH').sum()):>3}  ({100*(bench['risk_tier']=='HIGH').mean():.1f}%)
    MEDIUM = {int((bench['risk_tier']=='MEDIUM').sum()):>3}  ({100*(bench['risk_tier']=='MEDIUM').mean():.1f}%)
    LOW    = {int((bench['risk_tier']=='LOW').sum()):>3}  ({100*(bench['risk_tier']=='LOW').mean():.1f}%)

  Output files:
    {OUT_DIR / 'fig_benchmark_score_dist.png'}
    {OUT_DIR / 'fig_benchmark_roc.png'}
    {OUT_DIR / 'fig_benchmark_confusion.png'}
    {OUT_DIR / 'fig_benchmark_scatter_fh_hu.png'}
    {OUT_DIR / 'benchmark_ada_v2_results.csv'}
""")
print("═" * 68)
