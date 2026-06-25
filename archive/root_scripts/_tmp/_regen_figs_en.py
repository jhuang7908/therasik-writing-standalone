"""
Regenerate immunogenicity figures with English labels.
Output: insynbio-web-source/images/ada_study/fig*.png
"""
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from scipy import stats
import os

# ── paths ──────────────────────────────────────────────────────────────────
CSV = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv"
OUT = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/images/ada_study"
os.makedirs(OUT, exist_ok=True)

# ── load ────────────────────────────────────────────────────────────────────
df = pd.read_csv(CSV)
df = df[df["ada_first_pct"].notna()].copy()
fh = df[df["ada_v2_track"] == "FH"].copy()
hu = df[df["ada_v2_track"] == "HU"].copy()

# ── palette ─────────────────────────────────────────────────────────────────
C_ALL  = "#64748b"
C_FH   = "#0d9488"
C_HU   = "#7c3aed"
STYLE  = {"edgecolor": "white", "linewidth": 0.6}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.35,
    "figure.dpi": 150,
})


# ═══════════════════════════════════════════════════════════════════════════
# Fig 1 – ADA incidence distribution (All / FH / HU)
# ═══════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=False)
bins = np.arange(0, 92, 5)

for ax, subset, label, color in [
    (axes[0], df,  f"All Antibodies (n={len(df)})",   C_ALL),
    (axes[1], fh,  f"Fully Human — FH (n={len(fh)})", C_FH),
    (axes[2], hu,  f"Humanized — HU (n={len(hu)})",   C_HU),
]:
    ax.hist(subset["ada_first_pct"].dropna(), bins=bins, color=color, **STYLE)
    med = subset["ada_first_pct"].median()
    ax.axvline(med, color="#ef4444", lw=1.5, linestyle="--", label=f"Median {med:.1f}%")
    ax.set_title(label, fontweight="bold", pad=8)
    ax.set_xlabel("ADA Incidence (%)")
    ax.set_ylabel("Number of Antibodies")
    ax.legend(fontsize=9)

fig.suptitle("Figure 1 — ADA Incidence Distribution: All / FH / HU", fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(f"{OUT}/fig1_ada_distribution.png", bbox_inches="tight")
plt.close(fig)
print("✓ fig1")


# ═══════════════════════════════════════════════════════════════════════════
# Fig 2 – Boxplots by assay generation
# ═══════════════════════════════════════════════════════════════════════════
# Simplify assay labels
assay_map = {
    "tiered": "Tiered",
    "tiered (drug-tolerant)": "Tiered(DT)",
    "tiered (drug-tolerant assay)": "Tiered(DT)",
    "tiered (screening/confirmatory/titer)": "Tiered",
    "2.0": "ELISA Gen2",
    "1.0": "ELISA Gen1",
    "1.5": "ELISA Gen1.5",
    "bridging": "Bridging ECL",
}
df["assay_label"] = df["assay_generation"].map(assay_map).fillna("Other")

order = ["ELISA Gen1", "ELISA Gen1.5", "ELISA Gen2", "Bridging ECL", "Tiered", "Tiered(DT)"]
groups = [df[df["assay_label"] == g]["ada_first_pct"].dropna().values for g in order]
labels_n = [f"{g}\n(n={len(v)})" for g, v in zip(order, groups)]

fig, ax = plt.subplots(figsize=(13, 5))
bp = ax.boxplot(groups, labels=labels_n, patch_artist=True, notch=False,
                medianprops={"color": "#111827", "linewidth": 2},
                flierprops={"marker": "o", "markersize": 4, "alpha": 0.5})
colors = ["#94a3b8", "#94a3b8", "#64748b", "#f59e0b", "#0d9488", "#5eead4"]
for patch, c in zip(bp["boxes"], colors):
    patch.set_facecolor(c)
    patch.set_alpha(0.75)

ax.set_ylabel("ADA Incidence (%)")
ax.set_xlabel("Assay Generation")
ax.set_title("Figure 2 — ADA Distribution by Assay Generation\n(higher-sensitivity assays detect more ADA)",
             fontweight="bold")
fig.tight_layout()
fig.savefig(f"{OUT}/fig2_ada_boxplots.png", bbox_inches="tight")
plt.close(fig)
print("✓ fig2")


# ═══════════════════════════════════════════════════════════════════════════
# Fig 3 – Spearman correlation heatmap (31 features vs ADA)
# ═══════════════════════════════════════════════════════════════════════════
feat_map = {
    "interface_n_pairs":     "VH-VL Interface Contacts",
    "surf_n_patches":        "Hydrophobic Patch Count",
    "vh_germline_identity":  "VH Germline Identity",
    "vl_germline_identity":  "VL Germline Identity",
    "vh_identity_842":       "VH Identity (842-db)",
    "vl_identity_842":       "VL Identity (842-db)",
    "vh_identity_imgt":      "VH IMGT Identity",
    "vl_identity_imgt":      "VL IMGT Identity",
    "immuno_n_high":         "MHC-II High Binders",
    "immuno_n_medium":       "MHC-II Medium Binders",
    "immuno_tcia_score":     "TCIA Score",
    "pI":                    "Isoelectric Point (pI)",
    "GRAVY":                 "GRAVY Index",
    "instability_index":     "Instability Index",
    "net_charge_pH7":        "Net Charge pH 7",
    "hydro_patch_max9":      "Max Hydrophobic Patch",
    "charge_patch_max7":     "Max Charge Patch",
    "agg_motifs":            "Aggregation Motifs",
    "deamidation_sites":     "Deamidation Sites",
    "isomerization_sites":   "Isomerization Sites",
    "half_life_days":        "Half-Life (days)",
    "dose_mg":               "Dose (mg)",
    "vh_vl_angle_deg":       "VH-VL Packing Angle",
    "interface_mean_dist_A": "Interface Mean Distance (Å)",
    "surf_mean_sasa_vh":     "VH Mean SASA",
    "surf_mean_sasa_vl":     "VL Mean SASA",
    "surf_frac_exposed_vh":  "VH Exposed Fraction",
    "surf_frac_exposed_vl":  "VL Exposed Fraction",
    "surf_hydrophilicity":   "Surface Hydrophilicity",
    "immuno_n_clusters":     "MHC-II Epitope Clusters",
    "ada_v2_score":          "ADA V2 Composite Score",
}

target = "ada_first_pct"
rho_rows = []
for col, label in feat_map.items():
    if col not in df.columns:
        continue
    sub = df[[col, target]].dropna()
    if len(sub) < 20:
        continue
    r, p = stats.spearmanr(sub[col], sub[target])
    rho_rows.append({"label": label, "rho": r, "p": p, "n": len(sub)})

rho_df = pd.DataFrame(rho_rows).sort_values("rho")

fig, ax = plt.subplots(figsize=(10, 0.38 * len(rho_df) + 1.5))
colors_bar = [C_FH if r >= 0 else C_HU for r in rho_df["rho"]]
bars = ax.barh(rho_df["label"], rho_df["rho"], color=colors_bar, alpha=0.8, height=0.7)

for bar, row in zip(bars, rho_df.itertuples()):
    sig = "**" if row.p < 0.01 else ("*" if row.p < 0.05 else "")
    x_off = 0.005 if row.rho >= 0 else -0.005
    ha = "left" if row.rho >= 0 else "right"
    ax.text(row.rho + x_off, bar.get_y() + bar.get_height()/2,
            f"ρ={row.rho:+.3f}{sig}", va="center", ha=ha, fontsize=7.5)

ax.axvline(0, color="#111827", lw=0.8)
ax.set_xlabel("Spearman ρ vs ADA Incidence")
ax.set_title("Figure 3 — 31-Feature Spearman Correlation vs ADA Incidence\n(* p<0.05; ** p<0.01)",
             fontweight="bold")
fig.tight_layout()
fig.savefig(f"{OUT}/fig3_correlation_heatmap.png", bbox_inches="tight")
plt.close(fig)
print("✓ fig3")


# ═══════════════════════════════════════════════════════════════════════════
# Fig 4 – FH key features scatter vs ADA
# ═══════════════════════════════════════════════════════════════════════════
fh_plot = fh[["ada_first_pct","interface_n_pairs","surf_n_patches",
              "vl_germline_identity","immuno_n_high"]].dropna()

fig, axes = plt.subplots(1, 4, figsize=(16, 4.5))
specs = [
    ("interface_n_pairs",    "VH-VL Interface Contacts",     C_FH),
    ("surf_n_patches",       "Hydrophobic Patch Count",       "#f59e0b"),
    ("vl_germline_identity", "VL Germline Identity (%)",      "#7c3aed"),
    ("immuno_n_high",        "MHC-II High Binders",           "#ef4444"),
]
for ax, (col, xlabel, c) in zip(axes, specs):
    r, p = stats.spearmanr(fh_plot[col], fh_plot["ada_first_pct"])
    ax.scatter(fh_plot[col], fh_plot["ada_first_pct"], color=c, alpha=0.65,
               edgecolors="white", linewidths=0.5, s=55)
    m, b = np.polyfit(fh_plot[col], fh_plot["ada_first_pct"], 1)
    xs = np.linspace(fh_plot[col].min(), fh_plot[col].max(), 100)
    ax.plot(xs, m*xs+b, color="#111827", lw=1.4, linestyle="--")
    sig = "**" if p < 0.01 else ("*" if p < 0.05 else "n.s.")
    ax.set_title(f"ρ = {r:+.3f} ({sig})", fontweight="bold", fontsize=10)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("ADA Incidence (%)")

fig.suptitle(f"Figure 4 — FH Antibodies: Key Feature Correlations (n={len(fh_plot)})",
             fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(f"{OUT}/fig4_scatter_key_features.png", bbox_inches="tight")
plt.close(fig)
print("✓ fig4")


# ═══════════════════════════════════════════════════════════════════════════
# Fig 5 – HU key features scatter vs ADA
# ═══════════════════════════════════════════════════════════════════════════
hu_plot = hu[["ada_first_pct","agg_motifs","vh_germline_identity",
              "instability_index","immuno_n_high"]].dropna()

fig, axes = plt.subplots(1, 4, figsize=(16, 4.5))
hu_specs = [
    ("agg_motifs",           "Aggregation Motifs",         "#f59e0b"),
    ("vh_germline_identity", "VH Germline Identity (%)",   C_HU),
    ("instability_index",    "Instability Index",          "#ef4444"),
    ("immuno_n_high",        "MHC-II High Binders",        "#0d9488"),
]
for ax, (col, xlabel, c) in zip(axes, hu_specs):
    r, p = stats.spearmanr(hu_plot[col], hu_plot["ada_first_pct"])
    ax.scatter(hu_plot[col], hu_plot["ada_first_pct"], color=c, alpha=0.65,
               edgecolors="white", linewidths=0.5, s=55)
    m, b = np.polyfit(hu_plot[col], hu_plot["ada_first_pct"], 1)
    xs = np.linspace(hu_plot[col].min(), hu_plot[col].max(), 100)
    ax.plot(xs, m*xs+b, color="#111827", lw=1.4, linestyle="--")
    sig = "**" if p < 0.01 else ("*" if p < 0.05 else "n.s.")
    ax.set_title(f"ρ = {r:+.3f} ({sig})", fontweight="bold", fontsize=10)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("ADA Incidence (%)")

fig.suptitle(f"Figure 5 — HU Antibodies: Key Feature Correlations (n={len(hu_plot)})",
             fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(f"{OUT}/fig5_hu_scatter.png", bbox_inches="tight")
plt.close(fig)
print("✓ fig5")


# ═══════════════════════════════════════════════════════════════════════════
# Fig 7 – ADA V2 Composite Score vs ADA: FH vs HU
# ═══════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

for ax, subset, label, color in [
    (axes[0], fh, "Fully Human (FH)", C_FH),
    (axes[1], hu, "Humanized (HU)",  C_HU),
]:
    sub = subset[["ada_v2_score","ada_first_pct"]].dropna()
    r, p = stats.spearmanr(sub["ada_v2_score"], sub["ada_first_pct"])
    ax.scatter(sub["ada_v2_score"], sub["ada_first_pct"], color=color, alpha=0.7,
               edgecolors="white", linewidths=0.5, s=60)
    m, b = np.polyfit(sub["ada_v2_score"], sub["ada_first_pct"], 1)
    xs = np.linspace(sub["ada_v2_score"].min(), sub["ada_v2_score"].max(), 100)
    ax.plot(xs, m*xs+b, color="#111827", lw=1.6, linestyle="--")
    sig = "**" if p < 0.01 else ("*" if p < 0.05 else "n.s.")
    ax.set_title(f"{label}\nρ = {r:+.3f}, p = {p:.3f} ({sig}, n={len(sub)})",
                 fontweight="bold")
    ax.set_xlabel("ADA V2 Composite Score")
    ax.set_ylabel("Clinical ADA Incidence (%)")

fig.suptitle("Figure 7 — ADA V2 Composite Score vs Clinical ADA: FH vs HU",
             fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(f"{OUT}/fig7_ada_v2_composite.png", bbox_inches="tight")
plt.close(fig)
print("✓ fig7")


# ═══════════════════════════════════════════════════════════════════════════
# Fig 8 – CMC features vs ADA
# ═══════════════════════════════════════════════════════════════════════════
cmc_specs = [
    ("agg_motifs",       "Aggregation Motifs",      "#f59e0b"),
    ("deamidation_sites","Deamidation Sites",        "#ef4444"),
    ("pI",               "Isoelectric Point (pI)",  "#0d9488"),
    ("instability_index","Instability Index",        "#7c3aed"),
]

fig, axes = plt.subplots(1, 4, figsize=(16, 4.5))
for ax, (col, xlabel, c) in zip(axes, cmc_specs):
    sub = df[[col,"ada_first_pct"]].dropna()
    r, p = stats.spearmanr(sub[col], sub["ada_first_pct"])
    ax.scatter(sub[col], sub["ada_first_pct"], color=c, alpha=0.6,
               edgecolors="white", linewidths=0.5, s=50)
    m, b = np.polyfit(sub[col], sub["ada_first_pct"], 1)
    xs = np.linspace(sub[col].min(), sub[col].max(), 100)
    ax.plot(xs, m*xs+b, color="#111827", lw=1.4, linestyle="--")
    sig = "**" if p < 0.01 else ("*" if p < 0.05 else "n.s.")
    ax.set_title(f"ρ = {r:+.3f} ({sig})", fontweight="bold", fontsize=10)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("ADA Incidence (%)")

fig.suptitle(f"Figure 8 — CMC Developability Features vs ADA Incidence (n={len(df)})",
             fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(f"{OUT}/fig8_cmc_vs_ada.png", bbox_inches="tight")
plt.close(fig)
print("✓ fig8")

print("\nAll figures saved to:", OUT)
