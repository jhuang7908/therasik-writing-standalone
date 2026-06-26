"""
stat_plots.py
=============
TheraSIK Statistical Figure Generation

Generates publication-quality statistical figures from JSON data specs.

Supported plot types:
  forest      — Forest plot (meta-analysis, OR/HR/RR with CIs)
  km          — Kaplan-Meier survival curves
  roc         — ROC / AUC curves (single or multiple classifiers)
  heatmap     — Correlation or expression heatmap
  bar         — Grouped bar chart with error bars
  box         — Box + strip plot (individual data points)
  scatter     — Scatter plot with optional regression line
  volcano     — Volcano plot (log2FC vs -log10p)

Output formats: PNG (300 DPI) / SVG / PDF
Style: journal-ready (white background, Helvetica, no chartjunk)

Usage (CLI):
  python scripts/stat_plots.py --type forest --data forest_data.json --out fig1.png
  python scripts/stat_plots.py --type km --data km_data.json --out fig2.svg

Programmatic:
  from stat_plots import generate_figure, make_forest, make_km, make_roc

Data spec formats are documented in each function's docstring.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# ── Try imports — matplotlib is required ─────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.lines import Line2D
    _MPL = True
except ImportError:
    _MPL = False

try:
    import numpy as np
    _NP = True
except ImportError:
    _NP = False

try:
    import seaborn as sns
    _SNS = True
except ImportError:
    _SNS = False


SKILL_DIR = Path(os.environ.get("THERASIK_DIR", Path(__file__).resolve().parents[1]))

# ── Default style constants ────────────────────────────────────────────────────
JOURNAL_FONT   = "DejaVu Sans"
JOURNAL_COLORS = ["#2166AC", "#D6604D", "#4DAC26", "#8E0152", "#F4A582",
                  "#762A83", "#1B7837", "#B2182B", "#4393C3", "#D1E5F0"]
GRAY_MED       = "#888888"
GRAY_LIGHT     = "#DDDDDD"
DPI            = 300

# ── Journal presets ───────────────────────────────────────────────────────────
# Each preset locks the visual style to match that journal's figure guidelines.
# Users can override individual keys via data["style"].

JOURNAL_PRESETS: dict[str, dict] = {
    "nature": {
        # Nature / Nature Medicine / Nature Communications
        "figsize_scale":  1.0,
        "font_size":      7,       # Nature requires ≥5 pt, typically 7 pt
        "title_size":     8,
        "label_size":     7,
        "tick_size":      6,
        "legend_size":    6,
        "linewidth":      0.75,
        "dpi":            300,
        "colors":         ["#1A5276", "#C0392B", "#117A65", "#6C3483",
                           "#784212", "#1F618D", "#148F77", "#7D6608"],
        "spine_color":    "#000000",
        "tick_color":     "#000000",
        "background":     "white",
        "grid":           False,
        "marker_size":    4,
        "capsize":        2,
        "notes":          "Nature: 7pt font, 300 DPI, CMYK-safe colors, no background grid",
    },
    "nejm": {
        # New England Journal of Medicine
        "figsize_scale":  1.0,
        "font_size":      8,
        "title_size":     9,
        "label_size":     8,
        "tick_size":      7,
        "legend_size":    7,
        "linewidth":      1.0,
        "dpi":            300,
        "colors":         ["#003087", "#CC0000", "#007A33", "#FF6600",
                           "#6B2D8B", "#005C5C", "#8B0000", "#2E4057"],
        "spine_color":    "#333333",
        "tick_color":     "#333333",
        "background":     "white",
        "grid":           False,
        "marker_size":    5,
        "capsize":        3,
        "notes":          "NEJM: 8pt font, professional navy/red palette",
    },
    "cell": {
        # Cell / Cell Reports / Cell Host & Microbe
        "figsize_scale":  1.0,
        "font_size":      8,
        "title_size":     9,
        "label_size":     8,
        "tick_size":      7,
        "legend_size":    7,
        "linewidth":      1.25,
        "dpi":            300,
        "colors":         ["#2166AC", "#D6604D", "#4DAC26", "#8E0152",
                           "#762A83", "#1B7837", "#B2182B", "#F46D43"],
        "spine_color":    "#444444",
        "tick_color":     "#444444",
        "background":     "white",
        "grid":           False,
        "marker_size":    5,
        "capsize":        3,
        "notes":          "Cell: 8pt, slightly heavier lines than Nature",
    },
    "plos": {
        # PLOS ONE / PLOS Medicine / PLOS Biology
        "figsize_scale":  1.1,
        "font_size":      10,
        "title_size":     11,
        "label_size":     10,
        "tick_size":      9,
        "legend_size":    9,
        "linewidth":      1.5,
        "dpi":            300,
        "colors":         ["#0072B2", "#E69F00", "#009E73", "#CC79A7",
                           "#56B4E9", "#D55E00", "#F0E442", "#000000"],
        "spine_color":    "#666666",
        "tick_color":     "#666666",
        "background":     "white",
        "grid":           True,
        "grid_alpha":     0.25,
        "marker_size":    6,
        "capsize":        4,
        "notes":          "PLOS: 10pt, colorblind-safe palette (Wong 2011), light grid OK",
    },
    "jci": {
        # Journal of Clinical Investigation
        "figsize_scale":  1.0,
        "font_size":      8,
        "title_size":     9,
        "label_size":     8,
        "tick_size":      7,
        "legend_size":    7,
        "linewidth":      1.0,
        "dpi":            300,
        "colors":         ["#1F4E79", "#C55A11", "#375623", "#7030A0",
                           "#833C00", "#203864", "#BF9000", "#843C0C"],
        "spine_color":    "#333333",
        "tick_color":     "#333333",
        "background":     "white",
        "grid":           False,
        "marker_size":    5,
        "capsize":        3,
        "notes":          "JCI: 8pt, muted professional palette",
    },
    "science": {
        # Science / Science Translational Medicine
        "figsize_scale":  0.9,
        "font_size":      7,
        "title_size":     8,
        "label_size":     7,
        "tick_size":      6,
        "legend_size":    6,
        "linewidth":      0.75,
        "dpi":            300,
        "colors":         ["#2166AC", "#B2182B", "#1A9850", "#7B2D8B",
                           "#D6604D", "#4393C3", "#F46D43", "#878787"],
        "spine_color":    "#000000",
        "tick_color":     "#000000",
        "background":     "white",
        "grid":           False,
        "marker_size":    4,
        "capsize":        2,
        "notes":          "Science: 7pt minimum, compact layout (single-column = 5.5 cm wide)",
    },
    "lancet": {
        # The Lancet family
        "figsize_scale":  1.0,
        "font_size":      8,
        "title_size":     9,
        "label_size":     8,
        "tick_size":      7,
        "legend_size":    7,
        "linewidth":      1.0,
        "dpi":            300,
        "colors":         ["#003057", "#B5121B", "#00843D", "#7B2C8B",
                           "#E87722", "#005EB8", "#7C3238", "#4E6A3B"],
        "spine_color":    "#222222",
        "tick_color":     "#222222",
        "background":     "white",
        "grid":           False,
        "marker_size":    5,
        "capsize":        3,
        "notes":          "Lancet: 8pt, dark navy/burgundy palette, no grid",
    },
    "default": {
        # TheraSIK default — clean, journal-agnostic
        "figsize_scale":  1.0,
        "font_size":      9,
        "title_size":     11,
        "label_size":     10,
        "tick_size":      9,
        "legend_size":    8,
        "linewidth":      1.5,
        "dpi":            300,
        "colors":         ["#2166AC", "#D6604D", "#4DAC26", "#8E0152", "#F4A582",
                           "#762A83", "#1B7837", "#B2182B", "#4393C3", "#D1E5F0"],
        "spine_color":    "#888888",
        "tick_color":     "#888888",
        "background":     "white",
        "grid":           False,
        "marker_size":    5,
        "capsize":        3,
        "notes":          "TheraSIK default: clean, works for most journals",
    },
}

# Aliases
JOURNAL_PRESETS["nature medicine"]     = JOURNAL_PRESETS["nature"]
JOURNAL_PRESETS["nature communications"] = JOURNAL_PRESETS["nature"]
JOURNAL_PRESETS["cell reports"]        = JOURNAL_PRESETS["cell"]
JOURNAL_PRESETS["plos one"]            = JOURNAL_PRESETS["plos"]
JOURNAL_PRESETS["science translational medicine"] = JOURNAL_PRESETS["science"]
JOURNAL_PRESETS["stm"]                 = JOURNAL_PRESETS["science"]
JOURNAL_PRESETS["the lancet"]          = JOURNAL_PRESETS["lancet"]
JOURNAL_PRESETS["lancet oncology"]     = JOURNAL_PRESETS["lancet"]


def resolve_style(data: dict) -> dict:
    """
    Resolve the effective style for a figure.

    Priority (highest → lowest):
      1. data["style"]  — explicit per-figure overrides (any key from preset)
      2. data["journal_preset"] — named journal preset (e.g. "nature", "nejm")
      3. JOURNAL_PRESETS["default"]

    Args:
        data: Figure data dict (may include "style" and/or "journal_preset" keys).

    Returns:
        Resolved style dict.
    """
    preset_name = (data.get("journal_preset") or "default").lower().strip()
    base = dict(JOURNAL_PRESETS.get(preset_name, JOURNAL_PRESETS["default"]))

    # Apply per-figure user overrides
    user_style = data.get("style", {})
    base.update(user_style)

    return base


def list_presets() -> dict:
    """Return available journal presets and their descriptions."""
    return {
        k: v.get("notes", "")
        for k, v in JOURNAL_PRESETS.items()
        if k not in ("nature medicine", "nature communications", "cell reports",
                     "plos one", "science translational medicine", "stm",
                     "the lancet", "lancet oncology")  # skip aliases
    }


def _check_deps():
    if not _MPL:
        raise ImportError("matplotlib not installed. Run: pip install matplotlib --break-system-packages")
    if not _NP:
        raise ImportError("numpy not installed. Run: pip install numpy --break-system-packages")


def _apply_journal_style(ax, style: dict | None = None):
    """Apply publication-quality aesthetics using resolved style dict."""
    s = style or JOURNAL_PRESETS["default"]
    spine_color = s.get("spine_color", "#888888")
    tick_color  = s.get("tick_color",  "#888888")
    tick_size   = s.get("tick_size",   9)
    bg          = s.get("background",  "white")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(spine_color)
    ax.spines["bottom"].set_color(spine_color)
    ax.tick_params(colors=tick_color, labelsize=tick_size)
    ax.set_facecolor(bg)
    ax.figure.patch.set_facecolor(bg)

    if s.get("grid", False):
        ax.grid(True, alpha=s.get("grid_alpha", 0.2), linewidth=0.5,
                color=spine_color, zorder=0)


def _save(fig, output: str | Path, dpi: int = DPI, style: dict | None = None):
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    effective_dpi = (style or {}).get("dpi", dpi)
    bg = (style or {}).get("background", "white")
    fig.savefig(str(out), dpi=effective_dpi, bbox_inches="tight",
                facecolor=bg, edgecolor="none")
    plt.close(fig)
    return str(out)


# ══════════════════════════════════════════════════════════════════════════════
# FOREST PLOT
# ══════════════════════════════════════════════════════════════════════════════

def make_forest(data: dict, output: str, **kwargs) -> str:
    """
    Generate a forest plot.

    Data spec:
    {
      "title":    "Risk of Recurrence — Pooled Analysis",
      "metric":   "OR",          // OR | HR | RR | MD | SMD
      "null_value": 1,           // 1 for ratio metrics, 0 for MD
      "x_label":  "Odds Ratio (95% CI)",
      "studies": [
        {"label": "Smith 2020",  "effect": 0.72, "ci_low": 0.45, "ci_high": 1.14, "weight": 18.3, "events_n": "12/84"},
        {"label": "Jones 2021",  "effect": 0.54, "ci_low": 0.31, "ci_high": 0.94, "weight": 22.1, "events_n": "8/72"},
        ...
      ],
      "subgroups": [                    // optional
        {"label": "Subgroup A", "after_study": "Jones 2021"}
      ],
      "pooled": {"effect": 0.63, "ci_low": 0.44, "ci_high": 0.91, "i2": 23.4, "p_het": 0.21},
      "log_scale": true              // true for ratio metrics
    }
    """
    _check_deps()
    s          = resolve_style(data)
    studies     = data.get("studies", [])
    pooled      = data.get("pooled", {})
    metric      = data.get("metric", "OR")
    null_val    = data.get("null_value", 1)
    log_scale   = data.get("log_scale", null_val == 1)
    x_label     = data.get("x_label", f"{metric} (95% CI)")
    title       = data.get("title", "Forest Plot")
    colors      = s.get("colors", JOURNAL_PRESETS["default"]["colors"])

    n_studies  = len(studies)
    n_rows     = n_studies + (2 if pooled else 0) + 2  # header + separator
    fig_height = max(4, n_rows * 0.45 + 1.5)

    fig, (ax_labels, ax_forest, ax_stats) = plt.subplots(
        1, 3, figsize=(12 * s.get("figsize_scale",1.0), fig_height),
        gridspec_kw={"width_ratios": [3, 4, 2.5]},
    )
    plt.subplots_adjust(wspace=0.05)

    y_positions = list(range(n_studies, 0, -1))

    # ── Left panel: study labels ──────────────────────────────────────────────
    ax_labels.set_xlim(0, 1)
    ax_labels.set_ylim(0, n_studies + 2)
    ax_labels.axis("off")
    ax_labels.text(0.05, n_studies + 1.5, "Study", fontsize=s.get("font_size",9), fontweight="bold", va="center")
    for i, (study, y) in enumerate(zip(studies, y_positions)):
        ax_labels.text(0.05, y, study["label"], fontsize=s.get("font_size",8.5), va="center")

    # ── Centre panel: forest ──────────────────────────────────────────────────
    all_effects = [s["effect"] for s in studies] + ([pooled["effect"]] if pooled else [])
    all_low     = [s["ci_low"] for s in studies] + ([pooled.get("ci_low", 0)] if pooled else [])
    all_high    = [s["ci_high"] for s in studies] + ([pooled.get("ci_high", 0)] if pooled else [])

    if log_scale:
        import math
        x_vals = [math.log(max(0.001, v)) for v in (all_effects + all_low + all_high)]
        x_min  = min(x_vals) * 1.2
        x_max  = max(x_vals) * 1.2
    else:
        x_all  = all_effects + all_low + all_high
        spread = max(x_all) - min(x_all) if x_all else 1
        x_min  = min(x_all) - spread * 0.15
        x_max  = max(x_all) + spread * 0.15

    ax_forest.set_xlim(x_min, x_max)
    ax_forest.set_ylim(0, n_studies + 2)

    # Null line
    null_x = math.log(null_val) if (log_scale and null_val > 0) else null_val
    ax_forest.axvline(null_x, color=GRAY_MED, linewidth=0.8, linestyle="--")

    # Study markers
    weights = [s.get("weight", 1.0) for s in studies]
    max_w   = max(weights) if weights else 1
    for study, y, w in zip(studies, y_positions, weights):
        eff  = study["effect"]
        low  = study["ci_low"]
        high = study["ci_high"]
        if log_scale:
            import math as _math
            ex, el, eh = _math.log(max(0.001, eff)), _math.log(max(0.001, low)), _math.log(max(0.001, high))
        else:
            ex, el, eh = eff, low, high

        size = 40 + 80 * (w / max_w)
        ax_forest.plot([el, eh], [y, y], color="#333333", linewidth=1.0, zorder=2)
        ax_forest.scatter(ex, y, s=size, color=colors[0], zorder=3, marker="s")

    # Pooled diamond
    if pooled:
        p_eff  = pooled["effect"]
        p_low  = pooled.get("ci_low",  p_eff)
        p_high = pooled.get("ci_high", p_eff)
        if log_scale:
            pe, pl, ph = math.log(max(0.001, p_eff)), math.log(max(0.001, p_low)), math.log(max(0.001, p_high))
        else:
            pe, pl, ph = p_eff, p_low, p_high

        py = 0.5
        diamond_h = 0.35
        diamond = plt.Polygon(
            [[pl, py], [pe, py + diamond_h], [ph, py], [pe, py - diamond_h]],
            closed=True, color="#D6604D", zorder=4
        )
        ax_forest.add_patch(diamond)
        ax_forest.axhline(1.3, color="#333333", linewidth=0.6, xmin=0, xmax=1)

    # X-axis ticks (log scale)
    if log_scale:
        tick_vals = [v for v in [0.1, 0.2, 0.33, 0.5, 0.67, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
                     if x_min <= math.log(v) <= x_max]
        ax_forest.set_xticks([math.log(v) for v in tick_vals])
        ax_forest.set_xticklabels([str(v) for v in tick_vals], fontsize=8)
    ax_forest.set_xlabel(x_label, fontsize=9)
    ax_forest.set_yticks([])
    ax_forest.spines["left"].set_visible(False)
    ax_forest.spines["top"].set_visible(False)
    ax_forest.spines["right"].set_visible(False)
    ax_forest.tick_params(axis="x", colors=GRAY_MED, labelsize=8)

    # ── Right panel: statistics ───────────────────────────────────────────────
    ax_stats.set_xlim(0, 1)
    ax_stats.set_ylim(0, n_studies + 2)
    ax_stats.axis("off")
    ax_stats.text(0.05, n_studies + 1.5, f"{metric} (95% CI)", fontsize=9, fontweight="bold", va="center")
    ax_stats.text(0.7, n_studies + 1.5, "Weight", fontsize=9, fontweight="bold", va="center")

    for study, y, w in zip(studies, y_positions, weights):
        eff_str = f"{study['effect']:.2f} ({study['ci_low']:.2f}–{study['ci_high']:.2f})"
        ax_stats.text(0.05, y, eff_str, fontsize=8, va="center")
        ax_stats.text(0.7,  y, f"{w:.1f}%", fontsize=8, va="center")

    if pooled:
        p_str = f"{pooled['effect']:.2f} ({pooled.get('ci_low',0):.2f}–{pooled.get('ci_high',0):.2f})"
        i2    = pooled.get("i2", "")
        p_het = pooled.get("p_het", "")
        ax_stats.text(0.05, 0.5, p_str, fontsize=8.5, fontweight="bold", va="center", color="#D6604D")
        if i2 != "":
            ax_stats.text(0.05, -0.4, f"I² = {i2:.1f}%,  P_het = {p_het:.2f}", fontsize=7.5, va="center", color=GRAY_MED)

    fig.suptitle(title, fontsize=s.get("title_size",11), fontweight="bold", y=1.01)
    return _save(fig, output, style=s)


# ══════════════════════════════════════════════════════════════════════════════
# KAPLAN-MEIER
# ══════════════════════════════════════════════════════════════════════════════

def make_km(data: dict, output: str, **kwargs) -> str:
    """
    Generate a Kaplan-Meier survival curve.

    Data spec:
    {
      "title":   "Overall Survival",
      "x_label": "Time (months)",
      "y_label": "Survival probability",
      "groups": [
        {
          "label": "Treatment A  (n=84)",
          "times":  [0, 3, 6, 9, 12, 18, 24, 36],
          "survival": [1.0, 0.92, 0.83, 0.75, 0.68, 0.55, 0.48, 0.41],
          "ci_low":   [1.0, 0.85, 0.74, 0.65, 0.57, 0.44, 0.37, 0.30],
          "ci_high":  [1.0, 0.97, 0.91, 0.85, 0.79, 0.67, 0.60, 0.52],
          "at_risk":  [84, 76, 62, 51, 43, 29, 19, 8],
          "censored_times": [4.2, 7.8, 11.3]   // optional
        },
        ...
      ],
      "p_value": 0.023,
      "hr": "0.64 (95% CI 0.41–0.99)",
      "median_os": [{"label":"A","median":28.4},{"label":"B","median":18.1}],
      "x_max": 48
    }
    """
    _check_deps()
    s       = resolve_style(data)
    groups  = data.get("groups", [])
    title   = data.get("title", "Kaplan-Meier Survival")
    x_label = data.get("x_label", "Time")
    y_label = data.get("y_label", "Survival probability")
    x_max   = data.get("x_max")
    p_value = data.get("p_value")
    hr_str  = data.get("hr", "")
    colors  = s.get("colors", JOURNAL_PRESETS["default"]["colors"])

    fig, ax = plt.subplots(figsize=(7 * s.get("figsize_scale",1.0), 5 * s.get("figsize_scale",1.0)))

    for i, grp in enumerate(groups):
        color  = colors[i % len(colors)]
        times  = grp["times"]
        surv   = grp["survival"]
        ci_low = grp.get("ci_low")
        ci_hi  = grp.get("ci_high")
        label  = grp.get("label", f"Group {i+1}")

        # Step plot
        ax.step(times, surv, where="post", color=color, linewidth=s.get("linewidth",2.0), label=label)

        # CI band
        if ci_low and ci_hi:
            ax.fill_between(times, ci_low, ci_hi, step="post",
                            alpha=0.12, color=color)

        # Censoring ticks
        for ct in grp.get("censored_times", []):
            ax.scatter(ct, _interp_survival(times, surv, ct),
                       marker="|", s=80, color=color, linewidths=1.5, zorder=5)

    # Annotations
    annot_lines = []
    if p_value is not None:
        annot_lines.append(f"p = {p_value:.3f}")
    if hr_str:
        annot_lines.append(f"HR: {hr_str}")
    for med in data.get("median_os", []):
        annot_lines.append(f"Median {med['label']}: {med['median']} mo")

    if annot_lines:
        ax.text(0.98, 0.97, "\n".join(annot_lines), transform=ax.transAxes,
                fontsize=8, va="top", ha="right",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=GRAY_LIGHT))

    # At-risk table
    if any(g.get("at_risk") for g in groups) and groups:
        ax.set_position([0.12, 0.22, 0.82, 0.70])
        tick_times = groups[0].get("times", [])[:8]
        for j, grp in enumerate(groups):
            at_risk = grp.get("at_risk", [])
            color   = JOURNAL_COLORS[j % len(JOURNAL_COLORS)]
            y_pos   = -0.06 - j * 0.055
            for k, (t, n) in enumerate(zip(tick_times, at_risk)):
                ax.text(t, y_pos, str(n), transform=ax.get_xaxis_transform(),
                        fontsize=7.5, ha="center", color=color)
            ax.text(-0.01, y_pos, grp.get("label","")[:20], transform=ax.get_xaxis_transform(),
                    fontsize=7.5, ha="right", color=color)
        ax.text(-0.01, -0.04, "No. at risk", transform=ax.get_xaxis_transform(),
                fontsize=7.5, ha="right", color=GRAY_MED)

    ax.set_xlim(left=0, right=x_max)
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlabel(x_label, fontsize=s.get("label_size",10))
    ax.set_ylabel(y_label, fontsize=s.get("label_size",10))
    ax.set_title(title, fontsize=s.get("title_size",11), fontweight="bold")
    ax.legend(fontsize=s.get("legend_size",8.5), frameon=False, loc="upper right")
    _apply_journal_style(ax, s)

    return _save(fig, output, style=s)


def _interp_survival(times, surv, t):
    """Step-interpolate survival at time t."""
    for i in range(len(times)-1, -1, -1):
        if times[i] <= t:
            return surv[i]
    return 1.0


# ══════════════════════════════════════════════════════════════════════════════
# ROC CURVE
# ══════════════════════════════════════════════════════════════════════════════

def make_roc(data: dict, output: str, **kwargs) -> str:
    """
    Generate ROC curve(s).

    Data spec:
    {
      "title": "ROC Curves",
      "curves": [
        {
          "label": "Model A",
          "fpr":   [0, 0.05, 0.10, 0.20, 0.40, 1.0],
          "tpr":   [0, 0.42, 0.65, 0.80, 0.90, 1.0],
          "auc":   0.87
        },
        ...
      ]
    }
    """
    _check_deps()
    s      = resolve_style(data)
    title  = data.get("title", "ROC Curve")
    curves = data.get("curves", [])
    colors = s.get("colors", JOURNAL_PRESETS["default"]["colors"])

    fig, ax = plt.subplots(figsize=(5.5 * s.get("figsize_scale",1.0), 5.5 * s.get("figsize_scale",1.0)))

    ax.plot([0, 1], [0, 1], "--", color=GRAY_LIGHT, linewidth=s.get("linewidth",1.0)*0.7, label="Random (AUC=0.50)")

    for i, curve in enumerate(curves):
        color = colors[i % len(colors)]
        fpr   = curve["fpr"]
        tpr   = curve["tpr"]
        auc   = curve.get("auc")
        label = curve.get("label", f"Model {i+1}")
        lbl   = f"{label}  (AUC={auc:.3f})" if auc is not None else label
        ax.plot(fpr, tpr, color=color, linewidth=s.get("linewidth",2.0), label=lbl)
        ax.fill_between(fpr, tpr, alpha=0.06, color=color)

    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(-0.01, 1.01)
    ax.set_xlabel("False Positive Rate (1 – Specificity)", fontsize=s.get("label_size",10))
    ax.set_ylabel("True Positive Rate (Sensitivity)", fontsize=s.get("label_size",10))
    ax.set_title(title, fontsize=s.get("title_size",11), fontweight="bold")
    ax.legend(fontsize=s.get("legend_size",8.5), frameon=False, loc="lower right")
    _apply_journal_style(ax, s)

    return _save(fig, output, style=s)


# ══════════════════════════════════════════════════════════════════════════════
# HEATMAP
# ══════════════════════════════════════════════════════════════════════════════

def make_heatmap(data: dict, output: str, **kwargs) -> str:
    """
    Generate a correlation or expression heatmap.

    Data spec:
    {
      "title":   "Correlation Heatmap",
      "matrix":  [[1.0, 0.72, -0.31], [0.72, 1.0, 0.05], [-0.31, 0.05, 1.0]],
      "row_labels": ["Gene A", "Gene B", "Gene C"],
      "col_labels": ["Gene A", "Gene B", "Gene C"],
      "colormap": "RdBu_r",     // optional, default RdBu_r
      "vmin": -1, "vmax": 1,    // optional
      "annot": true,            // show values in cells
      "cluster": false          // hierarchical clustering
    }
    """
    _check_deps()
    import numpy as np

    matrix     = np.array(data["matrix"])
    row_labels = data.get("row_labels", [str(i) for i in range(matrix.shape[0])])
    col_labels = data.get("col_labels", [str(i) for i in range(matrix.shape[1])])
    title      = data.get("title", "Heatmap")
    cmap       = data.get("colormap", "RdBu_r")
    vmin       = data.get("vmin")
    vmax       = data.get("vmax")
    annot      = data.get("annot", True)
    cluster    = data.get("cluster", False)

    n_rows, n_cols = matrix.shape
    fig_h = max(3, n_rows * 0.5 + 1.5)
    fig_w = max(4, n_cols * 0.6 + 2.0)

    if cluster and _SNS:
        # seaborn.clustermap uses xticklabels/yticklabels (not row_labels/col_labels)
        g = sns.clustermap(matrix, xticklabels=col_labels, yticklabels=row_labels,
                           cmap=cmap, vmin=vmin, vmax=vmax,
                           annot=annot, fmt=".2f", figsize=(fig_w, fig_h))
        fig = g.fig
    else:
        fig, ax = plt.subplots(figsize=(fig_w, fig_h))
        im = ax.imshow(matrix, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_xticks(range(n_cols))
        ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(n_rows))
        ax.set_yticklabels(row_labels, fontsize=8)
        fig.colorbar(im, ax=ax, fraction=0.03, pad=0.03)
        if annot:
            for r in range(n_rows):
                for c in range(n_cols):
                    val = matrix[r, c]
                    color = "white" if abs(val) > 0.6 else "black"
                    ax.text(c, r, f"{val:.2f}", ha="center", va="center",
                            fontsize=7, color=color)
        ax.set_title(title, fontsize=11, fontweight="bold")
        _apply_journal_style(ax, resolve_style(data))

    return _save(fig, output)


# ══════════════════════════════════════════════════════════════════════════════
# BAR CHART
# ══════════════════════════════════════════════════════════════════════════════

def make_bar(data: dict, output: str, **kwargs) -> str:
    """
    Grouped bar chart with error bars.

    Data spec:
    {
      "title":   "Response Rate by Subgroup",
      "x_label": "Subgroup",
      "y_label": "Response rate (%)",
      "groups": [
        {"label": "Treatment A", "values": [72, 58, 81], "errors": [8, 6, 10]},
        {"label": "Treatment B", "values": [45, 39, 52], "errors": [7, 5, 9]}
      ],
      "categories":  ["PD-L1 High", "PD-L1 Low", "Overall"],
      "significance": [{"pair": [0, 1], "category": 2, "text": "p=0.03"}]
    }
    """
    _check_deps()
    import numpy as np

    groups     = data.get("groups", [])
    categories = data.get("categories", [f"Cat {i}" for i in range(
        max((len(g["values"]) for g in groups), default=1))])
    title   = data.get("title", "Bar Chart")
    x_label = data.get("x_label", "")
    y_label = data.get("y_label", "")

    n_groups = len(groups)
    n_cats   = len(categories)
    x        = np.arange(n_cats)
    width    = 0.8 / max(n_groups, 1)

    s      = resolve_style(data)
    colors = s.get("colors", JOURNAL_PRESETS["default"]["colors"])
    fig, ax = plt.subplots(figsize=(max(5, n_cats * 1.2 + 2) * s.get("figsize_scale",1.0), 5 * s.get("figsize_scale",1.0)))

    for i, grp in enumerate(groups):
        color  = JOURNAL_COLORS[i % len(JOURNAL_COLORS)]
        vals   = grp["values"]
        errs   = grp.get("errors", [0] * len(vals))
        offset = (i - (n_groups - 1) / 2) * width
        ax.bar(x + offset, vals, width * 0.9, label=grp["label"],
               color=color, yerr=errs, capsize=s.get("capsize",4), error_kw={"linewidth": s.get("linewidth",1.0)*0.8},
               edgecolor="white", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_xlabel(x_label, fontsize=s.get("label_size",10))
    ax.set_ylabel(y_label, fontsize=s.get("label_size",10))
    ax.set_title(title, fontsize=s.get("title_size",11), fontweight="bold")
    ax.legend(fontsize=s.get("legend_size",8.5), frameon=False)
    _apply_journal_style(ax, s)

    return _save(fig, output, style=s)


# ══════════════════════════════════════════════════════════════════════════════
# BOX PLOT
# ══════════════════════════════════════════════════════════════════════════════

def make_box(data: dict, output: str, **kwargs) -> str:
    """
    Box + strip plot (individual data points visible).

    Data spec:
    {
      "title":  "Serum IL-6 by Response",
      "y_label": "IL-6 (pg/mL)",
      "groups": [
        {"label": "Responder",     "values": [12, 18, 9, 22, 14, 31, 11, 8]},
        {"label": "Non-responder", "values": [45, 67, 38, 88, 52, 71, 44, 93]}
      ],
      "log_scale": false,
      "significance": [{"pair": [0, 1], "text": "p=0.002", "y_offset": 100}]
    }
    """
    _check_deps()
    import numpy as np

    groups    = data.get("groups", [])
    title     = data.get("title", "Box Plot")
    y_label   = data.get("y_label", "Value")
    log_scale = data.get("log_scale", False)

    s      = resolve_style(data)
    colors_box = s.get("colors", JOURNAL_PRESETS["default"]["colors"])
    fig, ax = plt.subplots(figsize=(max(4, len(groups) * 1.4 + 1.5) * s.get("figsize_scale",1.0), 5 * s.get("figsize_scale",1.0)))

    positions   = list(range(1, len(groups) + 1))
    all_vals    = []
    box_data    = []
    for i, grp in enumerate(groups):
        color = colors_box[i % len(colors_box)]
        vals  = grp["values"]
        all_vals.extend(vals)
        box_data.append(vals)
        # Strip (jitter)
        jitter = np.random.uniform(-0.12, 0.12, size=len(vals))
        ax.scatter(np.full(len(vals), positions[i]) + jitter, vals,
                   color=color, alpha=0.55, s=25, zorder=3)

    bp = ax.boxplot(box_data, positions=positions, widths=0.45,
                    patch_artist=True, notch=False,
                    medianprops=dict(color="black", linewidth=1.5),
                    boxprops=dict(linewidth=1.0),
                    whiskerprops=dict(linewidth=0.8),
                    capprops=dict(linewidth=0.8),
                    flierprops=dict(marker="", markersize=0))
    for patch, i in zip(bp["boxes"], range(len(groups))):
        color = JOURNAL_COLORS[i % len(JOURNAL_COLORS)]
        patch.set_facecolor(color)
        patch.set_alpha(0.25)

    # Significance bars
    y_max = max(all_vals) if all_vals else 1
    for sig in data.get("significance", []):
        pair   = sig["pair"]
        text   = sig.get("text", "")
        y_off  = sig.get("y_offset", y_max * 0.1)
        y_bar  = y_max + y_off
        x1, x2 = positions[pair[0]], positions[pair[1]]
        ax.plot([x1, x1, x2, x2], [y_bar * 0.97, y_bar, y_bar, y_bar * 0.97],
                color="black", linewidth=0.8)
        ax.text((x1 + x2) / 2, y_bar * 1.005, text, ha="center", fontsize=8)

    ax.set_xticks(positions)
    ax.set_xticklabels([g["label"] for g in groups], fontsize=9)
    ax.set_ylabel(y_label, fontsize=s.get("label_size",10))
    ax.set_title(title, fontsize=s.get("title_size",11), fontweight="bold")
    if log_scale:
        ax.set_yscale("log")
    _apply_journal_style(ax, s)

    return _save(fig, output, style=s)


# ══════════════════════════════════════════════════════════════════════════════
# SCATTER PLOT
# ══════════════════════════════════════════════════════════════════════════════

def make_scatter(data: dict, output: str, **kwargs) -> str:
    """
    Scatter plot with optional regression line and R²/p annotation.

    Data spec:
    {
      "title":   "Correlation: Tumour Size vs Response",
      "x_label": "Tumour size (mm)",
      "y_label": "Change from baseline (%)",
      "series": [
        {
          "label":  "Cohort A",
          "x": [12, 18, 24, 9, 31, 42, 15, 28],
          "y": [-45, -32, -58, -21, -67, -80, -38, -55],
          "color":  "#2166AC"   // optional
        }
      ],
      "regression": true,
      "r2": 0.71,
      "p_value": 0.0003
    }
    """
    _check_deps()
    import numpy as np

    series    = data.get("series", [])
    title     = data.get("title",   "Scatter Plot")
    x_label   = data.get("x_label", "X")
    y_label   = data.get("y_label", "Y")
    regress   = data.get("regression", False)
    r2        = data.get("r2")
    p_value   = data.get("p_value")

    st     = resolve_style(data)
    colors_sc = st.get("colors", JOURNAL_PRESETS["default"]["colors"])
    fig, ax = plt.subplots(figsize=(5.5 * st.get("figsize_scale",1.0), 5 * st.get("figsize_scale",1.0)))

    for i, s in enumerate(series):
        color = s.get("color", colors_sc[i % len(colors_sc)])
        x_arr = np.array(s["x"])
        y_arr = np.array(s["y"])
        ax.scatter(x_arr, y_arr, color=color, alpha=0.75, s=50,
                   label=s.get("label"), zorder=3, edgecolors="white", linewidths=0.5)

        if regress and len(x_arr) > 2:
            m, b = np.polyfit(x_arr, y_arr, 1)
            x_fit = np.linspace(x_arr.min(), x_arr.max(), 100)
            ax.plot(x_fit, m * x_fit + b, color=color, linewidth=st.get("linewidth",1.5), alpha=0.7)

    annot = []
    if r2 is not None:
        annot.append(f"R² = {r2:.3f}")
    if p_value is not None:
        annot.append(f"p = {p_value:.4f}")
    if annot:
        ax.text(0.05, 0.95, "\n".join(annot), transform=ax.transAxes,
                fontsize=8.5, va="top",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=GRAY_LIGHT))

    if len(series) > 1:
        ax.legend(fontsize=8.5, frameon=False)
    ax.set_xlabel(x_label, fontsize=st.get("label_size",10))
    ax.set_ylabel(y_label, fontsize=st.get("label_size",10))
    ax.set_title(title, fontsize=st.get("title_size",11), fontweight="bold")
    _apply_journal_style(ax, st)

    return _save(fig, output, style=st)


# ══════════════════════════════════════════════════════════════════════════════
# VOLCANO PLOT
# ══════════════════════════════════════════════════════════════════════════════

def make_volcano(data: dict, output: str, **kwargs) -> str:
    """
    Volcano plot for differential expression or GWAS results.

    Data spec:
    {
      "title":  "Differential Expression: Treatment vs Control",
      "genes": [
        {"label": "IL6",  "log2fc": 3.2,  "neg_log10p": 6.4,  "highlight": true},
        {"label": "TNF",  "log2fc": 2.8,  "neg_log10p": 5.1},
        {"label": "MYC",  "log2fc": -2.1, "neg_log10p": 4.3},
        ...
      ],
      "fc_threshold":   1.5,   // log2FC cutoff lines (default ±1.5)
      "p_threshold":    1.301, // -log10(0.05) = 1.301
      "label_top":      10     // label top N by |log2fc| * p
    }
    """
    _check_deps()
    import numpy as np

    genes      = data.get("genes", [])
    title      = data.get("title", "Volcano Plot")
    fc_thresh  = data.get("fc_threshold",  1.5)
    p_thresh   = data.get("p_threshold",   1.301)
    label_top  = data.get("label_top",     10)

    fc_arr = np.array([g["log2fc"]      for g in genes])
    p_arr  = np.array([g["neg_log10p"]  for g in genes])

    # Colour coding
    colors = []
    for fc, p in zip(fc_arr, p_arr):
        if p >= p_thresh and fc >= fc_thresh:
            colors.append("#D6604D")   # up-regulated
        elif p >= p_thresh and fc <= -fc_thresh:
            colors.append("#2166AC")   # down-regulated
        else:
            colors.append(GRAY_LIGHT)  # not significant

    sv     = resolve_style(data)
    fig, ax = plt.subplots(figsize=(6 * sv.get("figsize_scale",1.0), 5.5 * sv.get("figsize_scale",1.0)))
    ax.scatter(fc_arr, p_arr, c=colors, alpha=0.6, s=18, edgecolors="none", zorder=2)

    # Axis limits with padding so edge labels and corner counts have headroom
    if len(fc_arr):
        fc_pad = (fc_arr.max() - fc_arr.min()) * 0.12 or 0.5
        p_top  = p_arr.max() if len(p_arr) else 1.0
        ax.set_xlim(fc_arr.min() - fc_pad, fc_arr.max() + fc_pad)
        ax.set_ylim(0, p_top * 1.18)   # reserve top ~15% for count labels

    # Threshold lines
    ax.axhline(p_thresh, color=GRAY_MED, linewidth=0.7, linestyle="--")
    ax.axvline( fc_thresh, color=GRAY_MED, linewidth=0.7, linestyle="--")
    ax.axvline(-fc_thresh, color=GRAY_MED, linewidth=0.7, linestyle="--")

    # Labels for top genes — collision-aware placement
    score   = np.abs(fc_arr) * p_arr
    top_idx = np.argsort(score)[::-1][:label_top]
    x_lo, x_hi = ax.get_xlim()
    y_lo, y_hi = ax.get_ylim()
    x_off = (x_hi - x_lo) * 0.012

    label_texts = []
    for idx in top_idx:
        g = genes[idx]
        if not g.get("label"):
            continue
        gx, gy = fc_arr[idx], p_arr[idx]
        # Point to the inside: right-side points label leftward, left-side rightward
        if gx >= 0:
            ha, dx = "right", -x_off
        else:
            ha, dx = "left", x_off
        # Keep labels out of the top band reserved for count text
        gy_clamped = min(gy, y_hi * 0.95)
        label_texts.append(
            ax.text(gx + dx, gy_clamped, g["label"], fontsize=6.5,
                    va="center", ha=ha, color="#333333", zorder=4)
        )

    # Optional: use adjustText for non-overlapping labels if installed
    try:
        from adjustText import adjust_text
        if label_texts:
            adjust_text(label_texts, ax=ax,
                        arrowprops=dict(arrowstyle="-", color=GRAY_LIGHT, lw=0.4))
    except Exception:
        pass  # graceful fallback to static collision-aware placement

    # Count labels (reserved top band; ha pulls them clear of plotted points)
    n_up   = sum(1 for fc, p in zip(fc_arr, p_arr) if p >= p_thresh and fc >= fc_thresh)
    n_down = sum(1 for fc, p in zip(fc_arr, p_arr) if p >= p_thresh and fc <= -fc_thresh)
    ax.text(0.99, 1.02, f"Up: {n_up}", transform=ax.transAxes,
            fontsize=8, ha="right", va="bottom", color="#D6604D", fontweight="bold")
    ax.text(0.01, 1.02, f"Down: {n_down}", transform=ax.transAxes,
            fontsize=8, ha="left", va="bottom", color="#2166AC", fontweight="bold")

    ax.set_xlabel("log₂ Fold Change", fontsize=sv.get("label_size",10))
    ax.set_ylabel("−log₁₀(adjusted p-value)", fontsize=sv.get("label_size",10))
    ax.set_title(title, fontsize=sv.get("title_size",11), fontweight="bold", pad=18)
    _apply_journal_style(ax, sv)

    return _save(fig, output, style=sv)


# ══════════════════════════════════════════════════════════════════════════════
# DISPATCHER
# ══════════════════════════════════════════════════════════════════════════════

PLOT_FUNCTIONS = {
    "forest":   make_forest,
    "km":       make_km,
    "roc":      make_roc,
    "heatmap":  make_heatmap,
    "bar":      make_bar,
    "box":      make_box,
    "scatter":  make_scatter,
    "volcano":  make_volcano,
}


def generate_figure(
    plot_type: str,
    data: dict,
    output: str,
    **kwargs,
) -> dict:
    """
    Generate a statistical figure.

    Args:
        plot_type: One of: forest, km, roc, heatmap, bar, box, scatter, volcano,
                   or "list_presets" to return available journal presets.
        data:      Data specification dict. Supports two optional top-level keys:
                     journal_preset: "nature" | "nejm" | "cell" | "plos" |
                                     "jci" | "science" | "lancet" | "default"
                     style: dict of overrides (any key from the preset).
                       e.g. {"font_size": 10, "linewidth": 2.0, "dpi": 600,
                              "colors": ["#FF0000", "#0000FF"]}
        output:    Output file path (.png / .svg / .pdf).

    Returns:
        dict with output_path, plot_type, applied_style, or error.
    """
    if plot_type.lower() == "list_presets":
        return {"presets": list_presets()}

    plot_type = plot_type.lower().strip()
    fn = PLOT_FUNCTIONS.get(plot_type)
    if fn is None:
        return {
            "error": f"Unknown plot type: {plot_type}",
            "available": list(PLOT_FUNCTIONS.keys()),
        }

    if not _MPL:
        return {"error": "matplotlib not installed. Run: pip install matplotlib --break-system-packages"}

    try:
        out_path = fn(data, output, **kwargs)
        applied  = resolve_style(data)
        return {"output_path": out_path, "plot_type": plot_type,
                "success": True, "applied_preset": data.get("journal_preset","default"),
                "dpi": applied.get("dpi", DPI)}
    except Exception as exc:
        import traceback
        return {"error": str(exc), "traceback": traceback.format_exc()}


def generate_figure_from_files(
    plot_type: str,
    data_path: str,
    output: str,
) -> dict:
    """Load data from a JSON file and generate a figure."""
    try:
        data = json.loads(Path(data_path).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": f"Could not read data file: {exc}"}
    return generate_figure(plot_type, data, output)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TheraSIK Statistical Figure Generator")
    parser.add_argument("--type",   required=True, choices=list(PLOT_FUNCTIONS.keys()),
                        help="Plot type")
    parser.add_argument("--data",   required=True, help="Path to JSON data file")
    parser.add_argument("--out",    required=True, help="Output file path (.png/.svg/.pdf)")
    parser.add_argument("--dpi",    type=int, default=300, help="Output DPI (default 300)")
    args = parser.parse_args()

    if not _MPL:
        print("ERROR: matplotlib not installed. Run:\n  pip install matplotlib --break-system-packages", file=sys.stderr)
        sys.exit(1)

    result = generate_figure_from_files(args.type, args.data, args.out)
    if "error" in result:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        if "traceback" in result:
            print(result["traceback"], file=sys.stderr)
        sys.exit(1)
    print(f"Figure saved: {result['output_path']}")


if __name__ == "__main__":
    main()
