"""
1. Copy already-English figures from reports/figures/ → ada_study/
2. Regenerate the 4 benchmark figures (immuno/) in English.
"""
import warnings; warnings.filterwarnings("ignore")
import shutil, os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from sklearn.metrics import confusion_matrix, roc_curve, auc
from scipy import stats

# ── paths ─────────────────────────────────────────────────────────────────
SRC_FIGS = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/immunogenicity_knowledge_base/reports/figures"
ADA_OUT  = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/images/ada_study"
IMM_OUT  = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/images/immuno"
THERASIK_IMM_OUT = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/images/immuno"
BM_CSV   = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/immunogenicity_knowledge_base/reports/benchmark_ada_v2_results.csv"
MASTER   = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv"

os.makedirs(ADA_OUT, exist_ok=True)
os.makedirs(IMM_OUT, exist_ok=True)
os.makedirs(THERASIK_IMM_OUT, exist_ok=True)

# ── STEP 1: copy original English figures ────────────────────────────────
copy_map = {
    "fig1_ada_distribution.png":  "fig1_ada_distribution.png",
    "fig2_ada_boxplots.png":      "fig2_ada_boxplots.png",
    "fig3_correlation_heatmap.png": "fig3_correlation_heatmap.png",
    "fig4_scatter_key_features.png": "fig4_scatter_key_features.png",
    "fig8_cmc_vs_ada.png":        "fig8_cmc_vs_ada.png",
}
for src_name, dst_name in copy_map.items():
    src = f"{SRC_FIGS}/{src_name}"
    dst = f"{ADA_OUT}/{dst_name}"
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"✓ copied {src_name}")
    else:
        print(f"✗ not found: {src_name}")

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.35,
    "figure.dpi": 150,
})

C_FH = "#0d9488"
C_HU = "#7c3aed"

# ── load data ─────────────────────────────────────────────────────────────
bm = pd.read_csv(BM_CSV)
master = pd.read_csv(MASTER)
bm = bm.dropna(subset=["ada_pct", "ada_score"])
bm_fh = bm[bm["track"] == "FH"].copy()
bm_hu = bm[bm["track"] == "HU"].copy()

# Binary high/low ADA (threshold 10%)
THRESH = 10
THRESH_SCORE = 0.646
bm["ada_high"] = (bm["ada_pct"] >= THRESH).astype(int)
bm_fh["ada_high"] = (bm_fh["ada_pct"] >= THRESH).astype(int)
bm_hu["ada_high"] = (bm_hu["ada_pct"] >= THRESH).astype(int)

# ── Fig: Score Distribution ───────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

for ax, subset, label, color in [
    (axes[0], bm_fh, f"Fully Human (FH, n={len(bm_fh)})", C_FH),
    (axes[1], bm_hu, f"Humanized (HU, n={len(bm_hu)})",   C_HU),
]:
    low  = subset[subset["ada_high"] == 0]["ada_score"]
    high = subset[subset["ada_high"] == 1]["ada_score"]
    bins = np.linspace(subset["ada_score"].min() - 0.01,
                       subset["ada_score"].max() + 0.01, 20)
    ax.hist(low,  bins=bins, color="#94a3b8", alpha=0.75, label=f"Low ADA (<{THRESH}%)",  edgecolor="white")
    ax.hist(high, bins=bins, color=color,     alpha=0.75, label=f"High ADA (≥{THRESH}%)", edgecolor="white")
    ax.axvline(THRESH_SCORE, color="#111827", lw=1.3, linestyle="--",
               label=f"Threshold {THRESH_SCORE:.3f}")
    ax.set_xlabel("ADA V2 Score")
    ax.set_ylabel("Count")
    ax.set_title(label, fontweight="bold")
    ax.legend(fontsize=9)

fig.suptitle("ADA V2 Score Distribution by Risk Group (FH vs HU)", fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(f"{IMM_OUT}/fig_benchmark_score_dist.png", bbox_inches="tight")
shutil.copy2(f"{IMM_OUT}/fig_benchmark_score_dist.png", f"{THERASIK_IMM_OUT}/fig_benchmark_score_dist.png")
plt.close(fig)
print("✓ fig_benchmark_score_dist")

# ── Fig: Confusion Matrices ───────────────────────────────────────────────
def confusion_for(subset, thresh_score=THRESH_SCORE):
    pred = (subset["ada_score"] >= thresh_score).astype(int)
    true = subset["ada_high"]
    cm = confusion_matrix(true, pred)
    return cm

fig, axes = plt.subplots(1, 2, figsize=(10, 4))

thresh_score = THRESH_SCORE
for ax, subset, label, color in [
    (axes[0], bm_fh, f"FH (threshold ≥{thresh_score:.3f})", C_FH),
    (axes[1], bm_hu, f"HU (threshold ≥{thresh_score:.3f})", C_HU),
]:
    cm = confusion_for(subset, thresh_score)
    # Balanced accuracy = (sensitivity + specificity) / 2
    tn, fp, fn, tp = cm[0,0], cm[0,1], cm[1,0], cm[1,1]
    sens = tp / (tp + fn) if (tp + fn) > 0 else 0
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0
    bal_acc = (sens + spec) / 2

    im = ax.imshow(cm, cmap="Blues", vmin=0)
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(["Low ADA (pred)", "High ADA (pred)"])
    ax.set_yticklabels(["Low ADA (true)", "High ADA (true)"])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    fontsize=16, fontweight="bold",
                    color="white" if cm[i,j] > cm.max()*0.5 else "black")
    ax.set_title(f"{label}\nBalanced Acc: {bal_acc:.1%}  |  Sensitivity: {sens:.1%}", fontweight="bold", fontsize=9)

fig.suptitle("Confusion Matrices: ADA V2 Binary Classification", fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(f"{IMM_OUT}/fig_benchmark_confusion.png", bbox_inches="tight")
shutil.copy2(f"{IMM_OUT}/fig_benchmark_confusion.png", f"{THERASIK_IMM_OUT}/fig_benchmark_confusion.png")
plt.close(fig)
print("✓ fig_benchmark_confusion")

# ── Fig: ROC Curves ───────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6, 5.5))
ax.plot([0,1],[0,1],"k--",lw=0.8,label="Random")

for subset, label, color in [
    (bm_fh, "FH",  C_FH),
    (bm_hu, "HU",  C_HU),
    (bm,    "All", "#64748b"),
]:
    sub = subset.dropna(subset=["ada_high","ada_score"])
    if len(sub) < 10: continue
    fpr, tpr, _ = roc_curve(sub["ada_high"], sub["ada_score"])
    roc_auc = auc(fpr, tpr)
    ax.plot(fpr, tpr, color=color, lw=2, label=f"{label} (AUC = {roc_auc:.3f})")

ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate")
ax.set_title("ROC Curves — ADA V2 Composite Score", fontweight="bold")
ax.legend(loc="lower right", fontsize=10)
fig.tight_layout()
fig.savefig(f"{IMM_OUT}/fig_benchmark_roc.png", bbox_inches="tight")
shutil.copy2(f"{IMM_OUT}/fig_benchmark_roc.png", f"{THERASIK_IMM_OUT}/fig_benchmark_roc.png")
plt.close(fig)
print("✓ fig_benchmark_roc")

# ── Fig: Score vs ADA Scatter FH + HU ────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

for ax, subset, label, color in [
    (axes[0], bm_fh, f"Fully Human (FH, n={len(bm_fh)})", C_FH),
    (axes[1], bm_hu, f"Humanized (HU, n={len(bm_hu)})",   C_HU),
]:
    r, p = stats.spearmanr(subset["ada_score"], subset["ada_pct"])
    sc = ax.scatter(subset["ada_score"], subset["ada_pct"],
                    c=subset["ada_pct"], cmap="RdYlGn_r",
                    vmin=0, vmax=50, alpha=0.75,
                    edgecolors="white", linewidths=0.5, s=65)
    m, b = np.polyfit(subset["ada_score"], subset["ada_pct"], 1)
    xs = np.linspace(subset["ada_score"].min(), subset["ada_score"].max(), 100)
    ax.plot(xs, m*xs+b, color="#111827", lw=1.6, linestyle="--")
    sig = "**" if p < 0.01 else ("*" if p < 0.05 else "n.s.")
    ax.set_title(f"{label}\nρ = {r:+.3f}, p = {p:.3f} ({sig})", fontweight="bold")
    ax.set_xlabel("ADA V2 Score")
    ax.set_ylabel("Clinical ADA Incidence (%)")
    plt.colorbar(sc, ax=ax, label="ADA %")

fig.suptitle("ADA V2 Score vs Clinical ADA Incidence: FH vs HU", fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(f"{IMM_OUT}/fig_benchmark_scatter_fh_hu.png", bbox_inches="tight")
shutil.copy2(f"{IMM_OUT}/fig_benchmark_scatter_fh_hu.png", f"{THERASIK_IMM_OUT}/fig_benchmark_scatter_fh_hu.png")
plt.close(fig)
print("✓ fig_benchmark_scatter_fh_hu")

print("\nDone.")
