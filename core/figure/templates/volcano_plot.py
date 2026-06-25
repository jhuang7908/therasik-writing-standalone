"""
Publication-grade volcano plot — InSynBio Figure Recipe.

For differential expression, proteomics, mutation significance, or any
log2FC vs -log10(p) analysis.

Usage (CLI):
    python scripts/insynbio_figure.py stats --recipe volcano --csv data.csv --out figures/volcano.svg
    python scripts/insynbio_figure.py stats --recipe volcano --csv data.csv \\
        --fc-col log2fc --pval-col padj --label-col gene \\
        --fc-thresh 1.0 --p-thresh 0.05 --top-labels 15

CSV schema:
    gene,log2fc,pval[,padj,mean_expr]
    Required: label_col (default: gene), fc_col (default: log2fc), pval_col (default: pval)
    Optional: padj — use adjusted p if present; mean_expr — point size ∝ expression
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
except ImportError:
    sys.exit("ERROR: matplotlib not installed.")

try:
    import pandas as pd
    import numpy as np
except ImportError:
    sys.exit("ERROR: pandas / numpy not installed.")


def _apply_rcparams(font_size: int = 8) -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
        "svg.fonttype": "none",
        "font.size": font_size,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
    })


def volcano_plot(
    df: "pd.DataFrame",
    *,
    fc_col: str = "log2fc",
    pval_col: str = "pval",
    label_col: str = "gene",
    size_col: str | None = None,
    fc_thresh: float = 1.0,
    p_thresh: float = 0.05,
    top_labels: int = 10,
    up_color: str = "#C0392B",
    down_color: str = "#2A6496",
    ns_color: str = "#CCCCCC",
    x_label: str = r"$\log_2$ fold change",
    y_label: str = r"$-\log_{10}$ p-value",
    title: str = "",
    double_column: bool = False,
    font_size: int = 8,
    dpi: int = 300,
    label_sig_only: bool = True,
) -> "plt.Figure":
    """
    Draw a publication-grade volcano plot.

    Points are colored:
      Up-regulated:   |FC| > fc_thresh AND p < p_thresh, positive FC → up_color
      Down-regulated: |FC| > fc_thresh AND p < p_thresh, negative FC → down_color
      NS:             everything else → ns_color

    Top `top_labels` significant points are labeled (by |FC| × -log10p score).
    """
    _apply_rcparams(font_size)

    df = df.copy()
    df["_y"] = -np.log10(df[pval_col].clip(lower=1e-300))
    df["_fc"] = df[fc_col]
    df["_sig"] = (df[pval_col] < p_thresh) & (df[fc_col].abs() > fc_thresh)
    df["_up"] = df["_sig"] & (df["_fc"] > 0)
    df["_down"] = df["_sig"] & (df["_fc"] < 0)
    df["_color"] = ns_color
    df.loc[df["_up"], "_color"] = up_color
    df.loc[df["_down"], "_color"] = down_color

    # Point size
    if size_col and size_col in df.columns:
        s_vals = df[size_col].fillna(df[size_col].median())
        s_norm = (s_vals - s_vals.min()) / (s_vals.max() - s_vals.min() + 1e-9)
        sizes = (s_norm * 40 + 8).values
    else:
        sizes = 12

    fig_w = 17.4 / 2.54 if double_column else 8.5 / 2.54
    fig, ax = plt.subplots(figsize=(fig_w, fig_w * 0.85))

    # Background NS points first, then significant on top
    ns_mask = ~df["_sig"]
    ax.scatter(df.loc[ns_mask, "_fc"], df.loc[ns_mask, "_y"],
               c=ns_color, s=sizes if isinstance(sizes, int) else sizes[ns_mask],
               alpha=0.4, linewidths=0, rasterized=True, zorder=1)
    for mask, color in [(df["_up"], up_color), (df["_down"], down_color)]:
        ax.scatter(df.loc[mask, "_fc"], df.loc[mask, "_y"],
                   c=color, s=sizes if isinstance(sizes, int) else sizes[mask],
                   alpha=0.8, linewidths=0.3, edgecolors="white", zorder=3)

    # Threshold lines
    p_line = -np.log10(p_thresh)
    ax.axhline(p_line, color="#888888", linewidth=0.7, linestyle="--", zorder=0)
    ax.axvline(fc_thresh, color="#888888", linewidth=0.7, linestyle="--", zorder=0)
    ax.axvline(-fc_thresh, color="#888888", linewidth=0.7, linestyle="--", zorder=0)

    # Labels for top significant hits
    if label_col in df.columns:
        sig_df = df[df["_sig"]].copy()
        sig_df["_score"] = sig_df["_fc"].abs() * sig_df["_y"]
        top = sig_df.nlargest(top_labels, "_score")
        for _, row in top.iterrows():
            ax.text(row["_fc"], row["_y"] + 0.15, str(row[label_col]),
                    fontsize=max(5, font_size - 2), ha="center", va="bottom",
                    color=row["_color"], fontweight="bold")

    ax.set_xlabel(x_label, fontsize=font_size)
    ax.set_ylabel(y_label, fontsize=font_size)
    if title:
        ax.set_title(title, fontsize=font_size + 1, pad=6)

    # Summary counts
    n_up = df["_up"].sum()
    n_down = df["_down"].sum()
    n_ns = (~df["_sig"]).sum()

    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=up_color,
               markersize=5, label=f"Up: {n_up}"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=down_color,
               markersize=5, label=f"Down: {n_down}"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=ns_color,
               markersize=5, alpha=0.6, label=f"NS: {n_ns}"),
    ]
    ax.legend(handles=legend_elements, fontsize=font_size - 1, loc="upper right",
              handletextpad=0.3, borderpad=0.4)

    # Threshold annotations
    ax.text(ax.get_xlim()[1], p_line + 0.1,
            f"p={p_thresh}", fontsize=max(5, font_size - 2),
            color="#888888", ha="right", va="bottom")

    plt.tight_layout(pad=0.3)
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(prog="volcano_plot",
                                     description="Publication-grade volcano plot")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--fc-col", default="log2fc")
    parser.add_argument("--pval-col", default="pval")
    parser.add_argument("--label-col", default="gene")
    parser.add_argument("--fc-thresh", type=float, default=1.0)
    parser.add_argument("--p-thresh", type=float, default=0.05)
    parser.add_argument("--top-labels", type=int, default=10)
    parser.add_argument("--title", default="")
    parser.add_argument("--double-column", action="store_true")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    print(f"[volcano_plot] Loaded {len(df)} rows")

    fig = volcano_plot(
        df,
        fc_col=args.fc_col, pval_col=args.pval_col, label_col=args.label_col,
        fc_thresh=args.fc_thresh, p_thresh=args.p_thresh, top_labels=args.top_labels,
        title=args.title, double_column=args.double_column, dpi=args.dpi,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fmt = out.suffix.lstrip(".")
    fig.savefig(out, dpi=args.dpi, format=fmt if fmt != "tiff" else "tiff",
                bbox_inches="tight")
    print(f"[volcano_plot] → {out}")
    svg = out.with_suffix(".svg")
    if svg != out:
        fig.savefig(svg, format="svg", bbox_inches="tight")
        print(f"[volcano_plot] → {svg}")
    plt.close(fig)


if __name__ == "__main__":
    main()
