"""
Publication-grade forest plot — InSynBio Figure Recipe.

Follows nature-figure rcParams SSOT and figure-contract.
Supports: odds ratios, hazard ratios, mean differences, benchmark comparisons.

Usage (CLI via insynbio_figure.py):
    python scripts/insynbio_figure.py stats --recipe forest --csv data.csv --out figures/forest.svg
    python scripts/insynbio_figure.py stats --recipe forest --csv data.csv --pooled "Pooled effect" --out figures/forest.svg

Usage (API):
    from core.figure.templates.forest_plot import forest_plot
    fig = forest_plot(df, effect_col="effect", ci_low="ci_low", ci_high="ci_high")

CSV schema:
    label,effect,ci_low,ci_high[,group,n,p_value,weight]
    Required: label, effect, ci_low, ci_high
    Optional:
      group   — adds group separator bars (str)
      n       — sample size shown after label
      p_value — shown in rightmost column
      weight  — square size ∝ weight (meta-analysis mode)
      is_pooled — True/1 for the pooled estimate row (diamond symbol)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.lines as mlines
except ImportError:
    sys.exit("ERROR: matplotlib not installed.")

try:
    import pandas as pd
except ImportError:
    sys.exit("ERROR: pandas not installed. Run: pip install pandas")

import numpy as np

# ── rcParams SSOT (nature-figure Stable) ─────────────────────────────────────

def _apply_rcparams(font_size: int = 8) -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
        "svg.fonttype": "none",
        "font.size": font_size,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.spines.left": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
        "xtick.major.width": 0.8,
        "xtick.minor.width": 0.5,
    })


# ── Core renderer ─────────────────────────────────────────────────────────────

def forest_plot(
    df: "pd.DataFrame",
    *,
    effect_col: str = "effect",
    ci_low_col: str = "ci_low",
    ci_high_col: str = "ci_high",
    label_col: str = "label",
    group_col: str | None = "group",
    n_col: str | None = "n",
    p_col: str | None = "p_value",
    weight_col: str | None = "weight",
    pooled_col: str | None = "is_pooled",
    null_line: float = 0.0,
    null_label: str = "No effect",
    x_label: str = "Effect size (95% CI)",
    title: str = "",
    color_palette: dict | None = None,
    double_column: bool = False,
    font_size: int = 8,
    dpi: int = 300,
) -> "plt.Figure":
    """
    Draw a publication-grade forest plot.

    Parameters
    ----------
    df            : DataFrame with required columns (label, effect, ci_low, ci_high)
    null_line     : x-position of null effect line (0 for mean diff, 1 for OR/HR)
    double_column : 17.4 cm width for 2-column journals; else 8.5 cm
    """
    _apply_rcparams(font_size)

    palette = color_palette or {
        "study": "#2A6496",
        "pooled": "#C0392B",
        "null": "#888888",
        "ci": "#2A6496",
        "group_header": "#4D4D4D",
        "significant": "#C0392B",
        "ns": "#767676",
    }

    n_rows = len(df)
    has_groups = group_col and group_col in df.columns and df[group_col].notna().any()
    has_n = n_col and n_col in df.columns
    has_p = p_col and p_col in df.columns
    has_weight = weight_col and weight_col in df.columns
    has_pooled = pooled_col and pooled_col in df.columns

    # Figure size
    fig_w = 17.4 / 2.54 if double_column else 8.5 / 2.54
    fig_h = max(4.0 / 2.54, (n_rows * 0.45 + 1.5) / 2.54)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.spines["bottom"].set_visible(True)
    ax.spines["left"].set_visible(False)
    ax.yaxis.set_visible(False)

    y_positions = list(range(n_rows, 0, -1))

    group_breaks: set[int] = set()
    if has_groups:
        groups = df[group_col].values
        for i in range(1, n_rows):
            if groups[i] != groups[i - 1]:
                group_breaks.add(i)

    for i, (_, row) in enumerate(df.iterrows()):
        y = y_positions[i]
        eff = row[effect_col]
        lo = row[ci_low_col]
        hi = row[ci_high_col]
        is_pooled_row = bool(row[pooled_col]) if has_pooled and pooled_col in row.index else False

        # Square or diamond size ∝ weight
        sq_size = 60
        if has_weight and not pd.isna(row.get(weight_col, float("nan"))):
            w = float(row[weight_col])
            sq_size = max(20, min(200, w * 200))

        if is_pooled_row:
            # Diamond for pooled estimate
            diamond_w = (hi - lo) / 2
            diamond = mpatches.FancyArrow(
                eff, y, 0, 0,
                width=0, head_width=0, head_length=0,
            )
            diamond_pts = np.array([
                [lo, y], [eff, y + 0.35], [hi, y], [eff, y - 0.35]
            ])
            diamond_patch = mpatches.Polygon(diamond_pts, closed=True,
                                              fc=palette["pooled"], ec=palette["pooled"])
            ax.add_patch(diamond_patch)
        else:
            # CI line
            ax.plot([lo, hi], [y, y], color=palette["ci"], linewidth=1.0, zorder=2)
            # Center square
            ax.scatter([eff], [y], s=sq_size, marker="s",
                       color=palette["study"], zorder=3)

        # Label on left
        label_text = str(row[label_col])
        if has_n and not pd.isna(row.get(n_col, float("nan"))):
            label_text += f" (n={int(row[n_col])})"
        ax.text(ax.get_xlim()[0] if ax.get_xlim()[0] != 0 else -0.1, y,
                label_text, ha="right", va="center", fontsize=font_size - 1,
                color=palette["group_header"] if is_pooled_row else "black",
                transform=ax.get_yaxis_transform())

        # p-value on right
        if has_p and not pd.isna(row.get(p_col, float("nan"))):
            pv = float(row[p_col])
            pv_str = _format_pvalue(pv)
            ax.text(1.02, y, pv_str, ha="left", va="center",
                    fontsize=font_size - 1,
                    color=palette["significant"] if pv < 0.05 else palette["ns"],
                    transform=ax.get_yaxis_transform())

        # Group separator
        if i in group_breaks:
            ax.axhline(y + 0.7, color="#CCCCCC", linewidth=0.5, linestyle="--")

    # Null effect vertical line
    x_min = df[ci_low_col].min()
    x_max = df[ci_high_col].max()
    x_pad = (x_max - x_min) * 0.1
    ax.set_xlim(x_min - x_pad, x_max + x_pad)
    ax.set_ylim(0.3, n_rows + 0.7)

    ax.axvline(null_line, color=palette["null"], linewidth=0.8,
               linestyle="--", zorder=0, label=null_label)

    ax.set_xlabel(x_label, fontsize=font_size)
    if title:
        ax.set_title(title, fontsize=font_size + 1, pad=6)

    plt.tight_layout(pad=0.3)
    return fig


def _format_pvalue(p: float) -> str:
    if p < 0.001:
        return "p<0.001"
    if p < 0.01:
        return f"p={p:.3f}"
    return f"p={p:.2f}"


# ── CLI entry ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(prog="forest_plot",
                                     description="Publication-grade forest plot")
    parser.add_argument("--csv", required=True, help="Input CSV (label,effect,ci_low,ci_high,...)")
    parser.add_argument("--out", required=True, help="Output path (.svg / .pdf / .tiff / .png)")
    parser.add_argument("--null", type=float, default=0.0,
                        help="Null line x position (0=mean diff, 1=OR/HR)")
    parser.add_argument("--null-label", default="No effect")
    parser.add_argument("--x-label", default="Effect size (95% CI)")
    parser.add_argument("--title", default="")
    parser.add_argument("--double-column", action="store_true")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    print(f"[forest_plot] Loaded {len(df)} rows from {args.csv}")

    fig = forest_plot(
        df,
        null_line=args.null,
        null_label=args.null_label,
        x_label=args.x_label,
        title=args.title,
        double_column=args.double_column,
        dpi=args.dpi,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fmt = out.suffix.lstrip(".")
    if fmt == "tiff":
        fig.savefig(out, dpi=args.dpi, format="tiff", bbox_inches="tight")
    else:
        fig.savefig(out, dpi=args.dpi, bbox_inches="tight")
    print(f"[forest_plot] → {out}")

    # Always export SVG alongside
    svg_path = out.with_suffix(".svg")
    if svg_path != out:
        fig.savefig(svg_path, format="svg", bbox_inches="tight")
        print(f"[forest_plot] → {svg_path}")

    plt.close(fig)


if __name__ == "__main__":
    main()
