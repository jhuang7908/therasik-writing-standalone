"""
Statistical annotation utility — InSynBio Figure Recipe.

Adds p-value brackets, CI whiskers, and n-labels to existing matplotlib axes.
Works with bar plots, violin plots, box plots, strip plots.

Usage (API — attach to existing figure):
    from core.figure.templates.stats_annotator import add_stat_brackets, add_n_labels, add_ci_bars

    # After creating a bar/box/violin plot:
    add_stat_brackets(ax, comparisons=[(0, 1, 0.001), (0, 2, 0.042)], y_start=0.95)
    add_n_labels(ax, ns=[45, 32, 28], y=-0.08)
    add_ci_bars(ax, x_pos=[0, 1, 2], means=[0.72, 0.65, 0.81], ci_low=[0.65, 0.58, 0.74], ci_high=[0.79, 0.72, 0.88])

Usage (standalone demo):
    python core/figure/templates/stats_annotator.py --demo --out figures/stats_demo.svg
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
except ImportError:
    sys.exit("ERROR: matplotlib not installed.")

try:
    import numpy as np
except ImportError:
    sys.exit("ERROR: numpy not installed.")


# ── p-value formatting ────────────────────────────────────────────────────────

def format_pvalue(p: float, style: str = "stars") -> str:
    """
    Format a p-value for annotation.
    style: 'stars' → ns/*/†/**/***/n.s. | 'numeric' → p=0.042 | 'combined' → both
    """
    if style == "stars":
        if p >= 0.05:
            return "n.s."
        if p >= 0.01:
            return "*"
        if p >= 0.001:
            return "**"
        return "***"
    if style == "numeric":
        if p < 0.001:
            return "p<0.001"
        if p < 0.01:
            return f"p={p:.3f}"
        return f"p={p:.2f}"
    # combined
    stars = format_pvalue(p, "stars")
    numeric = format_pvalue(p, "numeric")
    return f"{stars}\n{numeric}" if stars != "n.s." else "n.s."


# ── Statistical brackets ──────────────────────────────────────────────────────

def add_stat_brackets(
    ax: "plt.Axes",
    comparisons: list[tuple[int | float, int | float, float]],
    *,
    y_start: float | None = None,
    step_frac: float = 0.08,
    line_color: str = "#333333",
    line_width: float = 0.8,
    font_size: int = 7,
    pval_style: str = "stars",
    tip_length: float = 0.03,
    x_positions: list[float] | None = None,
) -> None:
    """
    Draw statistical comparison brackets on an existing axis.

    Parameters
    ----------
    ax          : matplotlib Axes (bar/box/violin)
    comparisons : list of (x1_idx, x2_idx, p_value)
                  x1/x2 are bar indices (int) or actual x positions (float)
    y_start     : fractional y position to start first bracket (default: 0.92 of ylim)
    step_frac   : fractional y step between successive brackets
    x_positions : actual x positions if bars are not at integer positions
    """
    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min

    if y_start is None:
        y_start = y_max - y_range * 0.05
    else:
        y_start = y_min + y_start * y_range

    for level, (x1_idx, x2_idx, pval) in enumerate(comparisons):
        label = format_pvalue(pval, pval_style)
        if label in ("n.s.",) and pval >= 0.05:
            continue  # skip non-significant unless user wants them

        # Map idx to x position
        x1 = x_positions[int(x1_idx)] if x_positions else float(x1_idx)
        x2 = x_positions[int(x2_idx)] if x_positions else float(x2_idx)
        if x1 > x2:
            x1, x2 = x2, x1

        y_bracket = y_start + level * step_frac * y_range
        tip = tip_length * y_range

        # Bracket lines
        ax.plot([x1, x1, x2, x2],
                [y_bracket - tip, y_bracket, y_bracket, y_bracket - tip],
                color=line_color, linewidth=line_width, clip_on=False)

        # Annotation text
        x_mid = (x1 + x2) / 2
        ax.text(x_mid, y_bracket + 0.005 * y_range, label,
                ha="center", va="bottom", fontsize=font_size,
                color=line_color)

    # Expand y-axis to fit brackets
    n_brackets = len(comparisons)
    new_top = y_start + (n_brackets + 0.5) * step_frac * y_range
    if new_top > y_max:
        ax.set_ylim(y_min, new_top)


# ── N labels ─────────────────────────────────────────────────────────────────

def add_n_labels(
    ax: "plt.Axes",
    ns: Sequence[int],
    *,
    y: float = -0.07,
    font_size: int = 7,
    color: str = "#555555",
    prefix: str = "n=",
    x_positions: list[float] | None = None,
) -> None:
    """
    Add sample size labels below each bar/group.

    Parameters
    ----------
    ax          : matplotlib Axes
    ns          : sample sizes in bar order
    y           : y position in axes fraction (negative = below x-axis)
    x_positions : actual x positions if not at integers 0, 1, 2, ...
    """
    y_min, y_max = ax.get_ylim()
    y_abs = y_min + y * (y_max - y_min)

    for i, n in enumerate(ns):
        x = x_positions[i] if x_positions else i
        ax.text(x, y_abs, f"{prefix}{n}",
                ha="center", va="top", fontsize=font_size,
                color=color, clip_on=False)


# ── CI error bars (for bar plots without seaborn) ────────────────────────────

def add_ci_bars(
    ax: "plt.Axes",
    x_pos: Sequence[float],
    means: Sequence[float],
    ci_low: Sequence[float],
    ci_high: Sequence[float],
    *,
    color: str = "#333333",
    cap_width: float = 0.1,
    line_width: float = 1.0,
    zorder: int = 4,
) -> None:
    """
    Overlay CI error bars on existing bar plot.

    Parameters
    ----------
    ci_low, ci_high : absolute lower/upper bounds (NOT half-widths)
    """
    for x, mu, lo, hi in zip(x_pos, means, ci_low, ci_high):
        ax.plot([x, x], [lo, hi], color=color, linewidth=line_width, zorder=zorder)
        ax.plot([x - cap_width / 2, x + cap_width / 2], [lo, lo],
                color=color, linewidth=line_width, zorder=zorder)
        ax.plot([x - cap_width / 2, x + cap_width / 2], [hi, hi],
                color=color, linewidth=line_width, zorder=zorder)


# ── mean ± SD/CI band for line plots ─────────────────────────────────────────

def add_confidence_band(
    ax: "plt.Axes",
    x: Sequence[float],
    mean: Sequence[float],
    ci_low: Sequence[float],
    ci_high: Sequence[float],
    *,
    color: str = "#2A6496",
    band_alpha: float = 0.15,
    line_width: float = 1.5,
    label: str = "",
) -> None:
    """
    Draw a mean line + shaded CI band (for time series / dose-response curves).
    """
    x_arr = np.array(x)
    ax.plot(x_arr, mean, color=color, linewidth=line_width, label=label, zorder=3)
    ax.fill_between(x_arr, ci_low, ci_high, color=color, alpha=band_alpha, zorder=2)


# ── Demo ──────────────────────────────────────────────────────────────────────

def _demo(out_path: str) -> None:
    """Render a demo figure showing all annotation features."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "svg.fonttype": "none",
        "font.size": 8,
        "axes.spines.right": False,
        "axes.spines.top": False,
    })

    fig, axes = plt.subplots(1, 2, figsize=(17.4 / 2.54, 6 / 2.54))

    # Panel a — grouped bar with brackets + n labels
    ax = axes[0]
    groups = ["Control", "Treatment A", "Treatment B"]
    values = [0.42, 0.71, 0.65]
    lo = [0.35, 0.63, 0.58]
    hi = [0.49, 0.79, 0.72]
    ns = [45, 32, 28]
    colors = ["#AAAAAA", "#2A6496", "#C0392B"]

    bars = ax.bar(range(3), values, color=colors, width=0.55, alpha=0.85)
    add_ci_bars(ax, [0, 1, 2], values, lo, hi)
    add_n_labels(ax, ns, y=-0.12)
    add_stat_brackets(ax, comparisons=[(0, 1, 0.0003), (0, 2, 0.031)],
                      y_start=0.88, step_frac=0.10)
    ax.set_xticks(range(3))
    ax.set_xticklabels(groups, rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("Response score", fontsize=8)
    ax.set_ylim(0, 1.0)
    ax.text(-0.12, 1.06, "a", transform=ax.transAxes,
            fontsize=9, fontweight="bold", va="top")

    # Panel b — line + CI band
    ax2 = axes[1]
    x = np.linspace(0, 10, 50)
    mu = 0.5 * np.sin(x) + 0.5
    ci_lo = mu - 0.1
    ci_hi = mu + 0.1
    add_confidence_band(ax2, x, mu, ci_lo, ci_hi, color="#2A6496", label="Group A")
    mu2 = 0.3 * np.cos(x) + 0.4
    add_confidence_band(ax2, x, mu2, mu2 - 0.08, mu2 + 0.08,
                        color="#C0392B", label="Group B")
    ax2.set_xlabel("Time (days)", fontsize=8)
    ax2.set_ylabel("Mean ± 95% CI", fontsize=8)
    ax2.legend(fontsize=7, loc="upper right")
    ax2.text(-0.12, 1.06, "b", transform=ax2.transAxes,
             fontsize=9, fontweight="bold", va="top")

    plt.tight_layout(pad=0.4)
    from pathlib import Path
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    print(f"[stats_annotator] Demo → {out}")
    svg = out.with_suffix(".svg")
    fig.savefig(svg, format="svg", bbox_inches="tight")
    print(f"[stats_annotator] Demo → {svg}")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(prog="stats_annotator",
                                     description="Statistical annotation demo + utility")
    parser.add_argument("--demo", action="store_true",
                        help="Render a demo figure showing all annotation features")
    parser.add_argument("--out", default="figures/stats_annotator_demo.svg")
    args = parser.parse_args()

    if args.demo:
        _demo(args.out)
    else:
        print("stats_annotator is a library module. Use --demo to see a rendered example.")
        print("Import in your figure script:")
        print("  from core.figure.templates.stats_annotator import add_stat_brackets, add_n_labels, add_ci_bars")


if __name__ == "__main__":
    main()
