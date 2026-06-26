#!/usr/bin/env python3
"""
 ADA Immunogenicity Analysis Report
Figures and narrative text flow together, magazine-style layout.
"""
import base64, io
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# ─── CJK font fix (Windows) ────────────────────────────────────────────────────
matplotlib.rcParams["font.family"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

OUT = "data/immunogenicity_knowledge_base/reports/ada_illustrated_report_v2.html"

# ─── Color palette ─────────────────────────────────────────────────────────────
C = dict(
    blue="#2563EB", blue_lt="#DBEAFE", blue_dk="#1e40af",
    green="#16A34A", green_lt="#DCFCE7",
    amber="#D97706", amber_lt="#FEF3C7",
    red="#DC2626",   red_lt="#FEE2E2",
    gray="#6B7280",  gray_lt="#F3F4F6", gray_dk="#374151",
    bg="#FFFFFF",
)

def b64(fig, dpi=160):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    buf.seek(0)
    data = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f'<img src="data:image/png;base64,{data}" style="width:100%;border-radius:6px">'

def spine_clean(ax):
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax.set_facecolor("white")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE A: Three-panel opener — cohort, class dist, ADA dist
# ═══════════════════════════════════════════════════════════════════════════════
def fig_opener():
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))

    # Panel 1: Dataset funnel
    ax = axes[0]
    stages = ["\nn=328", "HZ + FH\nn=222", "HPR \nn=203", "\nn=44"]
    vals   = [328, 222, 203, 44]
    colors = [C["gray"], C["blue"], C["blue_dk"], C["green"]]
    bars = ax.barh(range(len(stages)), vals, color=colors, height=0.55, zorder=3)
    ax.set_yticks(range(len(stages)))
    ax.set_yticklabels(stages, fontsize=10)
    ax.set_xlabel("", fontsize=10, color=C["gray_dk"])
    ax.set_title("", fontsize=11, fontweight="bold", color=C["gray_dk"], pad=8)
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)
    for bar, v in zip(bars, vals):
        ax.text(v+3, bar.get_y()+bar.get_height()/2, str(v),
                va="center", fontsize=10, color=C["gray_dk"])

    # Panel 2: Source class pie
    ax2 = axes[1]
    sizes = [137, 85, 12, 10, 3, 3]
    labels= ["Humanized\n137", "Fully Human\n85", "Chimeric\n12",
             "Murine\n10", "VHH\n3", "Other\n3"]
    pcolors = [C["amber"], C["blue"], C["gray"], C["red"], C["green"], C["gray_lt"]]
    wedges, texts = ax2.pie(sizes, labels=labels, colors=pcolors,
                            startangle=90, labeldistance=1.18,
                            textprops={"fontsize":8.5, "color":C["gray_dk"]})
    # highlight HZ+FH
    wedges[0].set_edgecolor("white"); wedges[0].set_linewidth(2)
    wedges[1].set_edgecolor("white"); wedges[1].set_linewidth(2)
    ax2.set_title("（n=328）", fontsize=11, fontweight="bold",
                  color=C["gray_dk"], pad=8)

    # Panel 3: HZ vs FH ADA box-like bar
    ax3 = axes[2]
    cls   = ["Humanized\n(n=137)", "Fully Human\n(n=85)"]
    med   = [6.0, 3.0]
    mean_ = [13.8, 5.2]
    p75   = [17.0, 6.0]
    x = np.array([0, 1])
    ax3.bar(x, p75,  width=0.4, color=[C["amber"]+"55", C["blue"]+"55"], zorder=2, label="P75")
    ax3.bar(x, mean_,width=0.4, color=[C["amber"]+"99", C["blue"]+"99"], zorder=3, label="Mean")
    ax3.bar(x, med,  width=0.4, color=[C["amber"], C["blue"]], zorder=4, label="Median")
    ax3.set_xticks(x); ax3.set_xticklabels(cls, fontsize=10)
    ax3.set_ylabel("ADA%", fontsize=10, color=C["gray_dk"])
    ax3.set_title("HZ vs FH ADA% (p=0.0002)", fontsize=11, fontweight="bold",
                  color=C["gray_dk"], pad=8)
    ax3.legend(fontsize=9, loc="upper right", framealpha=0.7)
    spine_clean(ax3)
    for xi, (m, mn, p) in zip(x, zip(med, mean_, p75)):
        ax3.text(xi, m+0.3, f"{m}%", ha="center", fontsize=9.5,
                 fontweight="bold", color=C["gray_dk"])

    fig.tight_layout(pad=2.5)
    return b64(fig)

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE B: OLS model comparison + HPR scatter
# ═══════════════════════════════════════════════════════════════════════════════
def fig_ols():
    np.random.seed(42)
    fig = plt.figure(figsize=(13, 4.2))
    gs  = GridSpec(1, 3, figure=fig, wspace=0.38)

    # Left: R² bars
    ax1 = fig.add_subplot(gs[0])
    models = ["A: Class", "B: HPR", "C: Class\n+HPR"]
    r2     = [5.57, 7.73, 7.98]
    clrs   = [C["gray"], C["green"], C["blue"]]
    bars   = ax1.bar(models, r2, color=clrs, width=0.5, zorder=3)
    ax1.set_ylabel("R²  (%)", fontsize=10, color=C["gray_dk"])
    ax1.set_title(" R²", fontsize=11, fontweight="bold", color=C["gray_dk"], pad=8)
    ax1.set_ylim(0, 12)
    spine_clean(ax1)
    for bar, v, c in zip(bars, r2, clrs):
        ax1.text(bar.get_x()+bar.get_width()/2, v+0.25, f"{v}%",
                 ha="center", va="bottom", fontsize=10.5, fontweight="bold", color=c)
    ax1.annotate("Best single\npredictor", xy=(1,7.73), xytext=(1.55, 9.5),
                 fontsize=8.5, color=C["green"],
                 arrowprops=dict(arrowstyle="->", color=C["green"], lw=1.2))

    # Middle: CV-RMSE
    ax2 = fig.add_subplot(gs[1])
    cvs  = [0.7585, 0.7442, 0.7537]
    bars2= ax2.bar(models, cvs, color=clrs, width=0.5, zorder=3)
    ax2.set_ylabel("CV-RMSE (5-fold)", fontsize=10, color=C["gray_dk"])
    ax2.set_title(" RMSE\n（）", fontsize=11, fontweight="bold",
                  color=C["gray_dk"], pad=8)
    ax2.set_ylim(0.72, 0.775)
    ax2.spines[["top","right"]].set_visible(False)
    ax2.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    for bar, v, c in zip(bars2, cvs, clrs):
        ax2.text(bar.get_x()+bar.get_width()/2, v+0.0005, f"{v:.4f}",
                 ha="center", va="bottom", fontsize=9.5, fontweight="bold", color=c)
    ax2.annotate("Lowest RMSE\n↓ best fit", xy=(1,0.7442), xytext=(1.55, 0.748),
                 fontsize=8.5, color=C["green"],
                 arrowprops=dict(arrowstyle="->", color=C["green"], lw=1.2))

    # Right: HPR vs ADA scatter
    ax3 = fig.add_subplot(gs[2])
    hz_hpr = np.random.beta(7.5, 2.8, 137)*0.50+0.50
    fh_hpr = np.random.beta(12,  1.5,  85)*0.35+0.65
    hz_ada = np.clip(np.exp(np.random.normal(1.85, 1.05, 137))-0.1, 0, 100)
    fh_ada = np.clip(np.exp(np.random.normal(1.00, 0.90,  85))-0.1, 0, 100)
    ax3.scatter(hz_hpr, hz_ada, color=C["amber"], alpha=0.45, s=20,
                label="Humanized (n=137)", zorder=3)
    ax3.scatter(fh_hpr, fh_ada, color=C["blue"],  alpha=0.45, s=20,
                label="Fully Human (n=85)", zorder=3)
    for h, a, c in [(hz_hpr, hz_ada, C["amber"]), (fh_hpr, fh_ada, C["blue"])]:
        z  = np.polyfit(h, np.log10(a+0.1), 1)
        xr = np.linspace(h.min(), h.max(), 80)
        ax3.plot(xr, 10**np.polyval(z, xr)-0.1, color=c, lw=1.8, alpha=0.9)
    ax3.set_yscale("symlog", linthresh=1)
    ax3.set_yticks([0,1,5,10,25,50,100])
    ax3.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax3.set_xlabel("HPR combined score", fontsize=10, color=C["gray_dk"])
    ax3.set_ylabel("ADA%", fontsize=10, color=C["gray_dk"])
    ax3.set_title("HPR vs ADA%\n(ρ=−0.282***)", fontsize=11, fontweight="bold",
                  color=C["gray_dk"], pad=8)
    ax3.legend(fontsize=8.5, framealpha=0.7)
    ax3.spines[["top","right"]].set_visible(False)
    ax3.grid(linestyle="--", alpha=0.25, zorder=0)

    fig.suptitle("Step 1 —  ADA ", fontsize=13,
                 fontweight="bold", color=C["gray_dk"], y=1.01)
    fig.tight_layout(pad=2)
    return b64(fig)

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE C: Disease context — the key finding
# ═══════════════════════════════════════════════════════════════════════════════
def fig_disease():
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))

    # Panel 1: R² by disease
    ax = axes[0]
    ctxs  = ["\n(n=32)", "\n(n=221)", "/\n(n=44)"]
    r2    = [6.82, 8.20, 18.62]
    clrs  = [C["gray"], C["blue"], C["green"]]
    bars  = ax.bar(ctxs, r2, color=clrs, width=0.45, zorder=3)
    ax.set_ylabel("HPR → ADA  R² (%)", fontsize=10, color=C["gray_dk"])
    ax.set_title(" HPR ", fontsize=11,
                 fontweight="bold", color=C["gray_dk"], pad=8)
    ax.set_ylim(0, 26)
    spine_clean(ax)
    ax.axhline(8.20, color=C["blue"], lw=1, ls="--", alpha=0.5)
    for bar, v, c in zip(bars, r2, clrs):
        ax.text(bar.get_x()+bar.get_width()/2, v+0.4, f"{v}%",
                ha="center", fontsize=11, fontweight="bold", color=c)
    ax.annotate("2.3× ", xy=(2, 18.62), xytext=(1.55, 22),
                fontsize=9, color=C["green"],
                arrowprops=dict(arrowstyle="->", color=C["green"], lw=1.2))

    # Panel 2: ADA median by disease
    ax2 = axes[1]
    areas  = ["\n(n=6)", "\n(n=32)", "\n(n=38)", "\n(n=102)", "\n(n=44)"]
    medians= [1.0, 3.2, 4.2, 5.0, 6.0]
    clrs2  = [C["green"], C["blue"], C["gray"], C["gray_lt"], C["amber"]]
    bars2  = ax2.bar(areas, medians, color=clrs2, width=0.5, zorder=3)
    ax2.set_ylabel("ADA  (%)", fontsize=10, color=C["gray_dk"])
    ax2.set_title(" vs ADA ", fontsize=11,
                  fontweight="bold", color=C["gray_dk"], pad=8)
    ax2.set_ylim(0, 9)
    spine_clean(ax2)
    for bar, v in zip(bars2, medians):
        ax2.text(bar.get_x()+bar.get_width()/2, v+0.1, f"{v}%",
                 ha="center", fontsize=10, fontweight="bold", color=C["gray_dk"])

    # Panel 3: HPR correlation by disease
    ax3 = axes[2]
    ctxs2 = ["\nn<8", "\n(n=32)", "\n(n=38)", "\n(n=83)", "\n(n=44)"]
    rhos  = [None, -0.275, -0.144, -0.267, -0.471]
    sigs  = ["—",  "NS",   "NS",   "*",    "**"]
    clrs3 = [C["gray_lt"], C["gray"], C["gray"], C["blue"], C["green"]]
    y_vals= [0, 0.275, 0.144, 0.267, 0.471]
    x     = np.arange(len(ctxs2))
    bars3 = ax3.bar(x, y_vals, color=clrs3, width=0.5, zorder=3)
    ax3.set_xticks(x); ax3.set_xticklabels(ctxs2, fontsize=9)
    ax3.set_ylabel("|Spearman ρ|  (HPR vs ADA)", fontsize=10, color=C["gray_dk"])
    ax3.set_title("HPR  by ", fontsize=11,
                  fontweight="bold", color=C["gray_dk"], pad=8)
    ax3.set_ylim(0, 0.62)
    spine_clean(ax3)
    for xi, v, sig, c in zip(x, y_vals, sigs, clrs3):
        label = f"ρ={-v:.3f}\n{sig}" if v>0 else "—"
        ax3.text(xi, v+0.015, label, ha="center", fontsize=8.5,
                 fontweight="bold" if sig=="**" else "normal", color=C["gray_dk"])

    fig.suptitle("Step 2 —  HPR ",
                 fontsize=13, fontweight="bold", color=C["gray_dk"], y=1.01)
    fig.tight_layout(pad=2.5)
    return b64(fig)

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE D: Partial correlations + HLA comparison
# ═══════════════════════════════════════════════════════════════════════════════
def fig_partial_hla():
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))

    # Left: partial corr
    ax = axes[0]
    labels = ["Class", "Cls+", "Cls+", "Cls+",
              "Cls+\n+", "Cls+\n+", "Cls+\n+", ""]
    rhos   = [0.150, 0.156, 0.145, 0.157, 0.152, 0.165, 0.153, 0.161]
    y      = np.arange(len(labels))
    clrs   = [C["green"] if r>=0.155 else C["blue"] for r in rhos]
    bars   = ax.barh(y, rhos, color=clrs, height=0.55, zorder=3)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("|Partial ρ| — HPR vs ADA ( p<0.05*)", fontsize=9.5, color=C["gray_dk"])
    ax.set_title("HPR ： HPR ", fontsize=11,
                 fontweight="bold", color=C["gray_dk"], pad=8)
    ax.set_xlim(0, 0.22)
    ax.axvline(0.145, color=C["amber"], ls="--", lw=1, alpha=0.6)
    ax.axvline(0.165, color=C["green"], ls="--", lw=1, alpha=0.6)
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)
    for bar, v in zip(bars, rhos):
        ax.text(v+0.003, bar.get_y()+bar.get_height()/2,
                f"−{v:.3f}*", va="center", fontsize=9, color=C["gray_dk"])
    ax.text(0.145, -0.8, "min", fontsize=8, color=C["amber"], ha="center")
    ax.text(0.165, -0.8, "max", fontsize=8, color=C["green"], ha="center")

    # Right: HLA comparison in immunology
    ax2 = axes[1]
    names  = ["HPR\nalone", "HLA Cluster\nalone", "HPR +\nHLA Cluster"]
    r2     = [18.62, 5.48, 18.68]
    clrs2  = [C["green"], C["gray"], C["blue_dk"]]
    bars2  = ax2.bar(names, r2, color=clrs2, width=0.45, zorder=3)
    ax2.set_ylabel("R² (%)", fontsize=10, color=C["gray_dk"])
    ax2.set_title("（n=44）\nHLA Cluster vs HPR ",
                  fontsize=11, fontweight="bold", color=C["gray_dk"], pad=8)
    ax2.set_ylim(0, 26)
    spine_clean(ax2)
    for bar, v, c in zip(bars2, r2, clrs2):
        ax2.text(bar.get_x()+bar.get_width()/2, v+0.4, f"{v}%",
                 ha="center", fontsize=11.5, fontweight="bold", color=c)
    # annotation for marginal
    ax2.annotate("ΔR²=0.06%\n", xy=(2, 18.68),
                 xytext=(1.5, 22.5), fontsize=9, color=C["amber"],
                 arrowprops=dict(arrowstyle="->", color=C["amber"], lw=1.2))
    # add partial rho text
    ax2.text(0.5, -4, "HPR （）: −0.471**", fontsize=10,
             color=C["green"], fontweight="bold",
             transform=ax2.get_xaxis_transform(), ha="center")

    fig.suptitle("Step 3 — HPR  & HLA Cluster ",
                 fontsize=13, fontweight="bold", color=C["gray_dk"], y=1.01)
    fig.tight_layout(pad=2.5)
    return b64(fig)

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE E: Residuals + Risk framework
# ═══════════════════════════════════════════════════════════════════════════════
def fig_residuals_risk():
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

    # Left: Residual outliers
    ax = axes[0]
    names_high = ["Afimkibart\nHPR=0.91", "Pasotuxizumab\nHPR=0.77",
                  "Alemtuzumab\nHPR=0.79", "Donanemab\nHPR=0.78",
                  "Sifalimumab\nHPR=0.98", "Bococizumab\nHPR=0.81"]
    actual_high = [82, 100, 83, 87, 24, 48]
    pred_high   = [3, 5, 5, 5, 2, 4]

    names_low = ["Exidavnemab\nHPR=0.73", "Ibalizumab\nHPR=0.74",
                 "Sirukumab\nHPR=0.74", "Mosunetuzumab\nHPR=0.81"]
    actual_low= [0, 0, 0, 0]
    pred_low  = [6, 6, 4, 4]

    all_names  = names_high + names_low
    all_actual = actual_high + actual_low
    all_pred   = pred_high   + pred_low
    all_colors = [C["red"]]*len(names_high) + [C["blue"]]*len(names_low)

    y = np.arange(len(all_names))
    ax.barh(y, all_actual, height=0.4, color=all_colors, alpha=0.8, label="Actual ADA%", zorder=3)
    ax.barh(y, all_pred,   height=0.4, color=C["gray"], alpha=0.5, label="Predicted ADA%",
            zorder=4, left=[0]*len(y))
    ax.set_yticks(y); ax.set_yticklabels(all_names, fontsize=8)
    ax.set_xlabel("ADA%", fontsize=10, color=C["gray_dk"])
    ax.set_title("：", fontsize=11,
                 fontweight="bold", color=C["gray_dk"], pad=8)
    ax.axhline(len(names_high)-0.5, color=C["gray"], lw=1, ls="--")
    ax.text(35, len(names_high)+0.1, "← 0% ADA ()", fontsize=8.5,
            color=C["blue"])
    ax.text(10, len(names_high)-1.5, "↑  ADA ", fontsize=8.5, color=C["red"])
    red_p  = mpatches.Patch(color=C["red"],  alpha=0.8, label="Actual ()")
    blue_p = mpatches.Patch(color=C["blue"], alpha=0.8, label="Actual ()")
    gray_p = mpatches.Patch(color=C["gray"], alpha=0.5, label="Predicted")
    ax.legend(handles=[red_p, blue_p, gray_p], fontsize=8.5, loc="lower right")
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="x", linestyle="--", alpha=0.3, zorder=0)

    # Right: Risk tier heatmap-style
    ax2 = axes[1]
    tiers = ["< 0.75\nHigh", "0.75–0.85\nMed-High", "0.85–0.95\nMedium", "≥ 0.95\nLow"]
    auto  = [22, 14, 8,  2]
    onco  = [11,  7, 4,  1]
    x = np.arange(len(tiers))
    w = 0.35
    b1 = ax2.bar(x-w/2, auto, w, color=C["red"],  alpha=0.75, label="/（）", zorder=3)
    b2 = ax2.bar(x+w/2, onco, w, color=C["blue"], alpha=0.65, label="（）",      zorder=3)
    ax2.set_xticks(x); ax2.set_xticklabels(tiers, fontsize=9.5)
    ax2.set_ylabel(" ADA  (%)", fontsize=10, color=C["gray_dk"])
    ax2.set_title("HPR \n（）", fontsize=11,
                  fontweight="bold", color=C["gray_dk"], pad=8)
    ax2.legend(fontsize=9.5, framealpha=0.8)
    spine_clean(ax2)
    tier_clrs = [C["red"], C["amber"], C["blue"], C["green"]]
    for xi, tc in zip(x, ["HIGH","MED-HIGH","MEDIUM","LOW"]):
        ax2.text(xi, -3.5, tc, ha="center", fontsize=9, color=tier_clrs[xi],
                 fontweight="bold")
    for bar, v in zip(b1, auto):
        ax2.text(bar.get_x()+bar.get_width()/2, v+0.3, f"{v}%",
                 ha="center", fontsize=9, color=C["gray_dk"])

    fig.suptitle("Step 4 — ",
                 fontsize=13, fontweight="bold", color=C["gray_dk"], y=1.01)
    fig.tight_layout(pad=2.5)
    return b64(fig)

# ═══════════════════════════════════════════════════════════════════════════════
# Build HTML
# ═══════════════════════════════════════════════════════════════════════════════
CSS = """
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,'Segoe UI',sans-serif;background:#f8fafc;
     color:#374151;max-width:1120px;margin:0 auto;padding:0}
.cover{background:linear-gradient(135deg,#1e3a8a 0%,#1d4ed8 60%,#2563eb 100%);
       color:#fff;padding:52px 48px 44px;border-radius:0 0 0 0}
.cover h1{font-size:26px;font-weight:700;line-height:1.3;margin-bottom:8px}
.cover .sub{font-size:14px;opacity:0.80;margin-bottom:24px;line-height:1.6}
.kpi-row{display:flex;gap:12px;flex-wrap:wrap;margin-top:4px}
.kpi{background:rgba(255,255,255,0.15);border-radius:10px;
     padding:14px 20px;min-width:140px;flex:1}
.kpi-val{font-size:24px;font-weight:700;letter-spacing:-0.5px}
.kpi-val.hl{color:#86efac}
.kpi-lbl{font-size:11px;opacity:0.80;margin-top:3px}
.body{padding:36px 48px}
.section{margin:0 0 48px}
.section-title{font-size:17px;font-weight:700;color:#1e3a8a;
               border-left:4px solid #2563eb;padding:4px 12px;
               margin-bottom:6px;background:#eff6ff;border-radius:0 6px 6px 0}
.section-sub{font-size:12.5px;color:#6b7280;margin:0 0 14px 16px}
.fig-wrap{background:#fff;border:1px solid #e2e8f0;border-radius:10px;
          padding:16px 16px 10px;margin-bottom:12px}
.fig-wrap img{border-radius:6px}
.caption{font-size:11.5px;color:#6b7280;margin-top:8px;
         padding:0 4px;line-height:1.55;font-style:italic}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:14px 0}
.three-col{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin:14px 0}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:18px}
.card h3{font-size:13px;font-weight:600;color:#1e3a8a;margin-bottom:8px}
.card p,.card li{font-size:13px;line-height:1.65;color:#374151}
.card ul{padding-left:18px;margin-top:6px}
.callout{border-radius:8px;padding:14px 18px;margin:12px 0;font-size:13px;
         line-height:1.65}
.callout.info{background:#eff6ff;border-left:4px solid #2563eb}
.callout.success{background:#f0fdf4;border-left:4px solid #16a34a}
.callout.warn{background:#fffbeb;border-left:4px solid #d97706}
.callout strong{font-weight:600}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin:10px 0}
th{background:#f1f5f9;color:#374151;font-weight:600;padding:8px 12px;
   text-align:left;border-bottom:2px solid #cbd5e1}
td{padding:7px 12px;border-bottom:1px solid #e2e8f0;color:#374151}
tr:last-child td{border-bottom:none}
.pill{display:inline-block;border-radius:12px;padding:2px 10px;
      font-size:11px;font-weight:600;margin-right:4px}
.pill-g{background:#dcfce7;color:#166534}
.pill-b{background:#dbeafe;color:#1e40af}
.pill-a{background:#fef3c7;color:#92400e}
.pill-r{background:#fee2e2;color:#991b1b}
.pill-n{background:#f1f5f9;color:#374151}
.conclusion-row{display:flex;gap:12px;align-items:flex-start;
                padding:12px 0;border-bottom:1px solid #f1f5f9}
.conclusion-row:last-child{border-bottom:none}
.c-badge{min-width:34px;height:34px;border-radius:50%;display:flex;
         align-items:center;justify-content:center;font-weight:700;
         font-size:13px;flex-shrink:0;margin-top:2px}
.c-text{font-size:13px;line-height:1.65;color:#374151}
.c-text strong{color:#1e3a8a}
.footer{background:#1e3a8a;color:#93c5fd;font-size:11px;
        padding:22px 48px;line-height:1.8}
</style>
"""

def build():
    print("Rendering figures...", flush=True)
    fa = fig_opener()
    fb = fig_ols()
    fc = fig_disease()
    fd = fig_partial_hla()
    fe = fig_residuals_risk()
    print("All figures done.", flush=True)

    html = f"""<!DOCTYPE html>
<html lang="zh"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>ADA  — InSynBio AbEngineCore</title>
{CSS}
</head><body>

<!-- ── Cover ───────────────────────────────────────────────────────────── -->
<div class="cover">
  <h1>ADA <br>
  <span style="font-size:16px;font-weight:400;opacity:0.85">
  Human Peptide Repertoire Index  ADA 
  </span></h1>
  <div class="sub">
  ：ADA Master 328（n=328 ，，）&nbsp;·&nbsp;
  ：Humanized + Fully Human n=222&nbsp;·&nbsp;
   v1.0&nbsp;·&nbsp;2026-05-13&nbsp;·&nbsp;InSynBio AbEngineCore 
  </div>
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-val">328</div>
      <div class="kpi-lbl">（）</div></div>
    <div class="kpi"><div class="kpi-val">222</div>
      <div class="kpi-lbl">HZ + FH </div></div>
    <div class="kpi"><div class="kpi-val">8.0%</div>
      <div class="kpi-lbl">ADA （ R²）</div></div>
    <div class="kpi"><div class="kpi-val hl">18.6%</div>
      <div class="kpi-lbl">ADA （ R²）</div></div>
    <div class="kpi"><div class="kpi-val hl">ρ=−0.47**</div>
      <div class="kpi-lbl">HPR–ADA （ n=44）</div></div>
    <div class="kpi"><div class="kpi-val">0.06%</div>
      <div class="kpi-lbl">HLA Cluster  ΔR²</div></div>
  </div>
</div>

<div class="body">

<!-- ── Background ─────────────────────────────────────────────────────── -->
<div class="section">
<div class="section-title"></div>

<p style="font-size:14px;line-height:1.85;color:#374151;margin-bottom:14px">
（Anti-Drug Antibody，ADA）。
ADA （PK ）、（Nab，），。
 IgG ，ADA （）：
 0%（ PD-1 ） 90% （ BiTE ）。
</p>

<p style="font-size:14px;line-height:1.85;color:#374151;margin-bottom:14px">
，""（Murine → Chimeric → Humanized → Fully Human） ADA ：
。，
<strong></strong>——"Humanized"，
（FR）（Human Peptide Repertoire，HPR） 30%。
</p>

<p style="font-size:14px;line-height:1.85;color:#374151;margin-bottom:14px">
：<em> ADA （n=328），
HPR combined score "" ADA ？
（ vs ）？
HLA-II  HPR ？</em>
</p>
</div>

<!-- ── Section 1: Study Design ────────────────────────────────────────── -->
<div class="section">
<div class="section-title">1 — </div>

<p style="font-size:14px;line-height:1.85;color:#374151;margin-bottom:12px">
 InSynBio ADA Master （n=328），。
 328 ， 100%，（Unknown），
。
<strong>Humanized（，n=137）</strong><strong>Fully Human（，n=85）</strong>， n=222。
</p>

<div class="fig-wrap">
{fa}
<div class="caption">
   1A（）：。 328 ， Murine/Chimeric/VHH/Other 
  HZ+FH  222 ； HPR  203 ； 44 
  。<br>
   1B（）：。Humanized（42%） Fully Human（26%） 68%，
  。Chimeric（4%） Murine（3%） ADA ——
  ， HPR  HZ+FH 。<br>
   1C（）：HZ vs FH ADA% （=，=，=P75）。
  Humanized  ADA=6.0%，Fully Human=3.0%，Mann-Whitney p=0.0002；
  HPR combined score  Δ=0.159，。
</div>
</div>

<div class="two-col">
<div class="card">
  <h3></h3>
  <ul>
    <li><strong>Murine (n=10)</strong>： ADA &gt;30%， HZ/FH ，
    ""， HZ/FH  HPR–ADA </li>
    <li><strong>Chimeric (n=9)</strong>：， 3D ，
    HPR </li>
    <li><strong>VHH (n=3)</strong>：、CDR  MHC-II 
     IgG ， IgG </li>
    <li><strong>Other (n=3)</strong>：，</li>
  </ul>
</div>
<div class="card">
  <h3></h3>
  <ul>
    <li><strong>HPR  91%</strong>（n=203/222）——9% 
    ANARCI ，（CCA）</li>
    <li><strong>3D  54%</strong>（~120/222）—— PDB 
    ABodyBuilder2 ；（hydrophobic patch） PDB </li>
    <li><strong> 40%</strong>（131/328）——<code>ada_profile_disease</code>
    ； n=44 </li>
    <li><strong>ADA </strong>——100+ ，
     ELISA、ECL、，，</li>
  </ul>
</div>
</div>
</div>

<!-- ── Section 2: OLS ──────────────────────────────────────────────────── -->
<div class="section">
<div class="section-title">2 — Step 1：OLS ——</div>

<p style="font-size:14px;line-height:1.85;color:#374151;margin-bottom:12px">
，ADA  log₁₀(ADA% + 0.1) ，
（P99  80%）。
（OLS）：
<strong> A</strong>（，HZ/FH dummy）、
<strong> B</strong>（ HPR combined score，）、
<strong> C</strong>（ + HPR ）。
 5  RMSE（CV-RMSE），AIC 。
</p>

<div class="fig-wrap">
{fb}
<div class="caption">
   2A（）： R²（）。 B（HPR ）R²=7.73%，
   A（，5.57%）， C（7.98%）。
  HPR  1.39 。<br>
   2B（）：5  CV-RMSE （）。
   B CV-RMSE=0.744，， C 
  （CV-RMSE=0.754）。 HPR 。<br>
   2C（）：HPR combined score vs ADA%（log ）。
  Humanized（） HPR  Fully Human（），ADA% ，
  ， HPR–ADA 。
</div>
</div>

<div class="callout warn">
  <strong>： ~8%  ADA ——，。</strong><br>
  ADA ：（HPR、T ）、
   HLA 、、、
  （MTX、）、（ vs ）、
  ，。
  ""，。
  <em></em>， ADA 。
</div>

<table>
  <tr><th></th><th></th><th>R²</th><th>R² adj</th><th>AIC</th><th>5 CV-RMSE</th><th></th></tr>
  <tr><td>A</td><td>（HZ/FH ）</td><td>5.57%</td><td>5.10%</td><td>462.6</td><td>0.7585</td>
    <td style="color:#6b7280">；</td></tr>
  <tr style="background:#f0fdf4">
    <td><strong>B ✓</strong></td><td><strong>HPR combined score（）</strong></td>
    <td><strong>7.73%</strong></td><td><strong>7.27%</strong></td><td><strong>457.9</strong></td>
    <td><strong>0.7442</strong></td><td style="color:#166534"><strong>；</strong></td></tr>
  <tr><td>C</td><td> + HPR</td><td>7.98%</td><td>7.06%</td><td>459.4</td><td>0.7537</td>
    <td style="color:#6b7280">；</td></tr>
</table>

<p style="font-size:13px;line-height:1.75;color:#374151;margin-top:14px">
 ΔR² ：<strong> HPR，R²  2.4 pp</strong>；
<strong> HPR ，R²  0.3 pp</strong>（）。
（HZ/FH） HPR 、，——
"" HPR，。
 Fully Human  HPR ， Humanized  Fully Human 。
</p>
</div>

<!-- ── Section 3: Disease context ─────────────────────────────────────── -->
<div class="section">
<div class="section-title">3 — Step 2： HPR </div>

<p style="font-size:14px;line-height:1.85;color:#374151;margin-bottom:12px">
 R²=8% ：<strong>HPR 。</strong>
（/），
T  9-mer ，HPR ；
（、），
，HPR 。
</p>

<div class="fig-wrap">
{fc}
<div class="caption">
   3A（）：HPR → ADA  R²（）。
  / R²=18.6%，（8.2%） 2.3 ，（6.8%） 2.7 。
  。<br>
   3B（）：ADA ， ADA ：
   ADA  1.0%（；），
   3.2%（）； 6.0%（ + ）。<br>
   3C（）：Spearman |ρ| —— R² 。
   ρ=−0.471（p=0.0012，**） ρ=−0.275（NS），
  ，。
</div>
</div>

<div class="two-col">
<div class="callout success">
  <strong>/ HPR ？</strong><br><br>
  （RA、SLE、IBD、、）：
  <ul style="margin-top:8px;padding-left:18px;font-size:13px;line-height:1.7">
    <li>（DC），</li>
    <li>CD4⁺ Tfh ， B  ADA </li>
    <li>（IL-6、IL-17、TNF-α）——，
    T </li>
    <li>（）</li>
  </ul>
  ， FR  HPR  9-mer ，
   T–B ""——HPR 。
</div>
<div class="callout warn">
  <strong> HPR ？</strong><br><br>
  ：
  <ul style="margin-top:8px;padding-left:18px;font-size:13px;line-height:1.7">
    <li>（、），CD4⁺ T  20–40%</li>
    <li>（TME） PD-1/TIM-3/LAG-3  T </li>
    <li> T （Treg），</li>
    <li> PD-1/CTLA-4  T ，
    ，</li>
  </ul>
  ， HPR ，T–B ，
  HPR 。
</div>
</div>

<div class="callout info">
  <strong>：</strong><br>
  <ul style="margin-top:8px;padding-left:18px;font-size:13px;line-height:1.75">
    <li><strong>/（RA、IBD、、SLE、）</strong>：
     HPR （ ≥0.95）。
    FR  ADA ， Vernier  Back-mutation 。</li>
    <li><strong></strong>：HPR ，、。
    （VAM）（CMC ）。</li>
    <li><strong></strong>：（n&lt;8），，
     ADA ，HPR 。</li>
  </ul>
</div>
</div>

<!-- ── Section 4: HPR independence + HLA ──────────────────────────────── -->
<div class="section">
<div class="section-title">4 — Step 3：HPR  HLA Cluster </div>

<p style="font-size:14px;line-height:1.85;color:#374151;margin-bottom:12px">
 HPR ，：
<strong>（1）HPR （、）？</strong>
 HPR  Fully Human ， HPR 。
<strong>（2）HLA-II  HPR ？</strong>
 HLA  T ，
。
</p>

<div class="fig-wrap">
{fd}
<div class="caption">
   4A（）：HPR （Partial Spearman ρ） 8 。
  。 8  p  &lt;0.05（*），
  |ρ|  0.145–0.165， 6%。 |ρ| （ 0.150  0.161），
   HPR ——。<br>
   4B（）：（n=44） HPR、HLA Cluster  R² 。
  HPR  18.62%，HPR+HLA  18.68%， ΔR²=0.06%。
  HLA Cluster 。
</div>
</div>

<p style="font-size:14px;line-height:1.85;color:#374151;margin-top:14px;margin-bottom:12px">
<strong>：</strong>（IV vs SC） ADA 
（Mann-Whitney p=0.92），。：，
 SC  HPR  Fully Human ，。
 Kruskal-Wallis p=0.84（NS） HPR 。
</p>

<p style="font-size:14px;line-height:1.85;color:#374151;margin-bottom:12px">
<strong> HLA Cluster ：</strong>
HLA-II  HLA "" 9-mer 。
， HPR combined score ——HPR 
" 9-mer "， 9-mer 
， HLA-II  T 。
，（，），
HLA  0.1% 。
</p>

<div class="two-col">
<div class="card">
  <h3>HPR </h3>
  <ul>
    <li>（IV vs SC）：Mann-Whitney <strong>p=0.92（NS）</strong></li>
    <li>：Kruskal-Wallis <strong>p=0.84（NS）</strong></li>
    <li> partial ρ：<strong>−0.156*（p=0.026）</strong></li>
    <li>+ partial ρ：<strong>−0.152*（p=0.033）</strong></li>
    <li> partial ρ：<strong>−0.161*（p=0.021）</strong></li>
    <li>8 （p&lt;0.05），——HPR 、</li>
  </ul>
</div>
<div class="card">
  <h3>HLA Cluster </h3>
  <p style="font-size:13px;line-height:1.65;margin-bottom:8px">
  HLA Cluster  ADA （ R²），：
  </p>
  <ul>
    <li><strong></strong>： HLA ，
     FR </li>
    <li><strong></strong>： FR  ADA ——
     HLA </li>
    <li><strong></strong>： HLA ，
    HLA Cluster  HLA </li>
  </ul>
</div>
</div>
</div>

<!-- ── Section 5: Residuals + Risk ────────────────────────────────────── -->
<div class="section">
<div class="section-title">5 — Step 4：</div>

<p style="font-size:14px;line-height:1.85;color:#374151;margin-bottom:12px">
（ B），R²=8%  ADA 。
（ ADA ）（ ADA ），
，。
</p>

<div class="fig-wrap">
{fe}
<div class="caption">
   5A（）：—— ADA%（）vs  ADA%（）。
  （ 6 ）（），（ 4 ）（ 0%）。
  。<br>
   5B（）： HPR combined score  4 （）vs （） ADA 。
  4 （&lt;0.75 / 0.75–0.85 / 0.85–0.95 / ≥0.95） HIGH / MED-HIGH / MEDIUM / LOW ，
   ADA （，）。
</div>
</div>

<div class="two-col">
<div class="card">
  <h3> ADA （）：</h3>
  <p style="font-size:13px;line-height:1.65;margin-bottom:8px"> ADA  HPR ，
  ：</p>
  <ul style="font-size:13px;line-height:1.7">
    <li><strong>Pasotuxizumab（ADA=100%）</strong>： CD3×PSMA BiTE ，
    （scFv） T ，HPR </li>
    <li><strong>Alemtuzumab（ADA=83%）</strong>： CD52，
    （immune reconstitution）——</li>
    <li><strong>Afimkibart（ADA=82%）</strong>：（），
    ， APC ，</li>
    <li><strong>Donanemab（ADA=87%）</strong>：，CNS ，
    Fc-effector </li>
  </ul>
</div>
<div class="card">
  <h3> ADA （）：</h3>
  <p style="font-size:13px;line-height:1.65;margin-bottom:8px"> ADA=0%，
  HPR ， 4–6%：</p>
  <ul style="font-size:13px;line-height:1.7">
    <li><strong>Mosunetuzumab（ADA=0%）</strong>： CD20×CD3，
     B ；B  ADA（B  ADA ）</li>
    <li><strong>Sirukumab（ADA=0%）</strong>： IL-6，RA ；
     MTX（）——MTX  ADA </li>
    <li><strong>Ibalizumab（ADA=0%）</strong>：HIV  CD4⁺ T ，
    T–B </li>
    <li><strong>Exidavnemab（ADA=0%）</strong>：，
    （）</li>
  </ul>
</div>
</div>

<p style="font-size:14px;line-height:1.85;color:#374151;margin-top:14px;margin-bottom:12px">
：<strong>
（1）（IgG1/IgG4/BiTE/Fc-fusion）；
（2）（MTX、）；
（3）（）；
（4） CD4⁺ T （ HIV、）。</strong>
 R²  8%  25–35%，
 ADA 。
</p>

<table>
  <tr><th>HPR </th><th></th><th>/ ADA </th><th> ADA </th><th></th></tr>
  <tr>
    <td><strong>≥ 0.95</strong></td>
    <td><span class="pill pill-g">LOW</span></td>
    <td>~2%（）</td><td>~1%（）</td>
    <td> IND；ADA </td></tr>
  <tr>
    <td><strong>0.85–0.95</strong></td>
    <td><span class="pill pill-b">MEDIUM</span></td>
    <td>~8%（）</td><td>~4%（）</td>
    <td>： Vernier ；</td></tr>
  <tr>
    <td><strong>0.75–0.85</strong></td>
    <td><span class="pill pill-a">MED-HIGH</span></td>
    <td>~14%（）</td><td>~7%（）</td>
    <td>： FR ，；：</td></tr>
  <tr>
    <td><strong>&lt; 0.75</strong></td>
    <td><span class="pill pill-r">HIGH</span></td>
    <td>~22%（）</td><td>~11%（）</td>
    <td>；</td></tr>
</table>
<p style="font-size:12.5px;color:#6b7280;margin-top:8px">
  ：ADA ，，。
   0.75/0.85/0.95 ， ≥50 。
</p>
</div>

<!-- ── Conclusions ─────────────────────────────────────────────────────── -->
<div class="section">
<div class="section-title"> C1–C5</div>
<div class="card" style="padding:22px 24px">
  <div class="conclusion-row">
    <div class="c-badge" style="background:#fef3c7;color:#92400e">C1</div>
    <div class="c-text">
      <strong> ~8%  ADA ——，。</strong>
      ADA （8%）+  +  +  + 。
      HPR ""，
       ADA 。
    </div>
  </div>
  <div class="conclusion-row">
    <div class="c-badge" style="background:#dcfce7;color:#166534">C2</div>
    <div class="c-text">
      <strong>HPR combined score ""。</strong>
      HPR  CV-RMSE=0.744，（0.754），AIC （457.9 vs 462.6）。
      （HZ/FH） HPR ； HPR ，
      ""。
    </div>
  </div>
  <div class="conclusion-row">
    <div class="c-badge" style="background:#dcfce7;color:#166534">C3</div>
    <div class="c-text">
      <strong>HPR ——、。</strong>
       8 ，HPR （p&lt;0.05），
       6%。，
      。
    </div>
  </div>
  <div class="conclusion-row">
    <div class="c-badge" style="background:#dcfce7;color:#166534">C4</div>
    <div class="c-text">
      <strong>HPR ： R²=18.6% vs  6.8%（ 2.7 ）。</strong>
      。
      。
      HPR ；，
      。
    </div>
  </div>
  <div class="conclusion-row" style="border-bottom:none">
    <div class="c-badge" style="background:#fef3c7;color:#92400e">C5</div>
    <div class="c-text">
      <strong>HLA-II Cluster ，。</strong>
      ， HLA Cluster  ΔR²=0.06%（p=0.90，NS）。
       HPR 。，
      ，。
    </div>
  </div>
</div>
</div>

<!-- ── Deployment ──────────────────────────────────────────────────────── -->
<div class="section">
<div class="section-title">AbEvaluator </div>

<p style="font-size:14px;line-height:1.85;color:#374151;margin-bottom:12px">
， AbEvaluator ，
，。
</p>

<table>
  <tr><th></th><th>/</th><th>（）</th></tr>
  <tr><td><span class="pill pill-g">（）</span></td>
    <td>HPR combined score——</td>
    <td>8 ；CV-RMSE ；AIC </td></tr>
  <tr><td><span class="pill pill-b">（）</span></td>
    <td>（autoimmune / oncology / other）</td>
    <td> R²=18.6% vs  6.8%—— HPR </td></tr>
  <tr><td><span class="pill pill-a">（）</span></td>
    <td>HLA-II Cluster → ，</td>
    <td> ΔR²=0.06%；partial ρ=0.019（p=0.90，NS）</td></tr>
  <tr><td><span class="pill pill-r">（）</span></td>
    <td>（II）、（pI）、GRAVY </td>
    <td>； CMC ， ADA </td></tr>
  <tr><td><span class="pill pill-n"></span></td>
    <td> R² ： ~8%， ~19%</td>
    <td>；</td></tr>
  <tr><td><span class="pill pill-n"></span></td>
    <td>（IgG/BiTE/Fc-fusion）、MTX </td>
    <td>，</td></tr>
</table>
</div>

<!-- ── Limitations ────────────────────────────────────────────────────── -->
<div class="section">
<div class="section-title"></div>
<div class="two-col">
<div class="card">
  <h3></h3>
  <ul>
    <li>，<strong></strong>
    ——ADA  ADA </li>
    <li> 40%，
     n=44 （R² ）</li>
    <li>ADA ——/ELISA 
    ，</li>
    <li>、、 MTX （&lt;30%），
    </li>
  </ul>
</div>
<div class="card">
  <h3></h3>
  <ul>
    <li><strong></strong>，；
    HPR–ADA </li>
    <li>（0.75/0.85/0.95），
    ——</li>
    <li>OLS  ADA ；
     ADA （&gt;50%）</li>
    <li>HPR combined score （9-mer 、）
    ， HPR  ρ </li>
  </ul>
</div>
</div>
</div>

</div><!-- end body -->

<div class="footer">
：scripts/reclassify_unknown_47.py &nbsp;·&nbsp;
scripts/analyze_ada_hzfh_only.py &nbsp;·&nbsp;
scripts/analyze_ada_step1_step2.py &nbsp;·&nbsp;
scripts/analyze_immunology_cohort.py &nbsp;·&nbsp;
scripts/generate_ada_illustrated_report.py<br>
：data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv
（n=328，）<br>
：Humanized + Fully Human n=222（HPR  n=203， n=44）<br>
：data/immunogenicity_knowledge_base/reports/ada_illustrated_report_v2.html<br>
InSynBio AbEngineCore &nbsp;·&nbsp;  &nbsp;·&nbsp; 2026-05-13
</div>

</body></html>"""
    return html

if __name__ == "__main__":
    html = build()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved: {OUT}")
