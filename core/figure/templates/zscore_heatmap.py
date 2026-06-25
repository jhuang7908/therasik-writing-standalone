"""
Publication-grade Z-score heatmap — InSynBio Figure Recipe.

For gene expression, antibody binding profiles, protein panels, immune signatures.
Applies row-wise Z-score normalization before rendering.

Usage (CLI):
    python scripts/insynbio_figure.py stats --recipe heatmap --csv data.csv --out figures/heatmap.svg
    python scripts/insynbio_figure.py stats --recipe heatmap --csv data.csv \\
        --row-group-col group --cluster-rows --cluster-cols --top-n 50

CSV schema:
    Rows = features (genes/proteins/antibodies).
    First column = feature name. Remaining columns = samples/conditions (numeric).
    Optional: last meta-column for row groups (specify via --row-group-col).

    feature,Sample_A,Sample_B,Sample_C[,group]
    CD19,5.2,1.1,4.8[,B_cell]
    ...
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
    import matplotlib.gridspec as gridspec
    import matplotlib.patches as mpatches
    from matplotlib.colors import TwoSlopeNorm
except ImportError:
    sys.exit("ERROR: matplotlib not installed.")

try:
    import pandas as pd
    import numpy as np
    from scipy.cluster.hierarchy import linkage, dendrogram, leaves_list
    from scipy.spatial.distance import pdist
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from matplotlib.colors import LinearSegmentedColormap
except ImportError:
    pass


def _apply_rcparams(font_size: int = 7) -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
        "svg.fonttype": "none",
        "font.size": font_size,
        "axes.linewidth": 0.5,
        "legend.frameon": False,
    })


# InSynBio diverging colormap (blue–white–red, nature-friendly)
_CMAP = LinearSegmentedColormap.from_list(
    "insynbio_div",
    ["#2A6496", "#FFFFFF", "#C0392B"],  # blue → white → red
    N=256,
)


def _zscore_normalize(mat: "np.ndarray") -> "np.ndarray":
    """Row-wise Z-score normalization with clip to [-3, 3]."""
    mu = mat.mean(axis=1, keepdims=True)
    sd = mat.std(axis=1, keepdims=True)
    sd[sd == 0] = 1.0
    z = (mat - mu) / sd
    return np.clip(z, -3, 3)


def _cluster_order(mat: "np.ndarray") -> list[int]:
    """Return hierarchical clustering leaf order."""
    if not HAS_SCIPY:
        return list(range(mat.shape[0]))
    if mat.shape[0] < 2:
        return [0]
    dist = pdist(mat, metric="euclidean")
    link = linkage(dist, method="ward")
    return list(leaves_list(link))


def zscore_heatmap(
    df: "pd.DataFrame",
    *,
    row_group_col: str | None = None,
    cluster_rows: bool = True,
    cluster_cols: bool = False,
    top_n: int | None = None,
    colormap=None,
    zscore_clip: float = 3.0,
    show_col_labels: bool = True,
    show_row_labels: bool = True,
    col_label_rotation: int = 45,
    group_palette: list[str] | None = None,
    title: str = "",
    double_column: bool = True,
    font_size: int = 7,
    dpi: int = 300,
) -> "plt.Figure":
    """
    Draw a Z-score normalized heatmap with optional group annotations.

    Parameters
    ----------
    df            : DataFrame — rows=features, first col=name, remaining=numeric samples
    row_group_col : column name for row group labels (shown as color bar on left)
    cluster_rows  : apply hierarchical clustering to rows
    cluster_cols  : apply hierarchical clustering to columns
    top_n         : if set, select top N rows by variance before clustering
    """
    _apply_rcparams(font_size)
    cmap = colormap or _CMAP

    # Identify data vs group columns
    if row_group_col and row_group_col in df.columns:
        groups = df[row_group_col].values
        data_cols = [c for c in df.columns if c not in [df.columns[0], row_group_col]]
    else:
        groups = None
        data_cols = list(df.columns[1:])

    feature_names = df.iloc[:, 0].values
    mat = df[data_cols].values.astype(float)

    # Select top N by variance
    if top_n and top_n < mat.shape[0]:
        var = mat.var(axis=1)
        idx = np.argsort(var)[::-1][:top_n]
        mat = mat[idx]
        feature_names = feature_names[idx]
        if groups is not None:
            groups = groups[idx]

    # Z-score
    mat_z = _zscore_normalize(mat)

    # Clustering
    row_order = _cluster_order(mat_z) if cluster_rows and HAS_SCIPY else list(range(mat_z.shape[0]))
    col_order = _cluster_order(mat_z.T) if cluster_cols and HAS_SCIPY else list(range(mat_z.shape[1]))

    mat_z = mat_z[np.ix_(row_order, col_order)]
    feature_names = feature_names[row_order]
    sample_names = [data_cols[i] for i in col_order]
    if groups is not None:
        groups = groups[row_order]

    n_rows, n_cols = mat_z.shape
    has_groups = groups is not None and groups.ndim > 0

    # Layout
    fig_w = 17.4 / 2.54 if double_column else 8.5 / 2.54
    row_height_cm = max(0.25, min(0.55, 12 / n_rows))
    fig_h = (n_rows * row_height_cm + 2.5) / 2.54

    # Gridspec: [group bar | heatmap | colorbar]
    width_ratios = [0.3, 1] if has_groups else [1]
    ncols_grid = 2 if has_groups else 1
    fig = plt.figure(figsize=(fig_w, fig_h))
    gs = gridspec.GridSpec(1, ncols_grid + 1,
                           width_ratios=width_ratios + [0.05],
                           wspace=0.03, figure=fig)

    hm_ax = fig.add_subplot(gs[0, ncols_grid - 1])
    cb_ax = fig.add_subplot(gs[0, ncols_grid])
    if has_groups:
        grp_ax = fig.add_subplot(gs[0, 0])
    else:
        grp_ax = None

    # Heatmap
    norm = TwoSlopeNorm(vmin=-zscore_clip, vcenter=0, vmax=zscore_clip)
    im = hm_ax.imshow(mat_z, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")

    # Tick labels
    hm_ax.set_xticks(range(n_cols))
    if show_col_labels:
        hm_ax.set_xticklabels(sample_names, rotation=col_label_rotation,
                               ha="right", fontsize=font_size - 1)
    else:
        hm_ax.set_xticklabels([])

    hm_ax.set_yticks(range(n_rows))
    if show_row_labels and n_rows <= 60:
        hm_ax.set_yticklabels(feature_names, fontsize=font_size - 1)
    else:
        hm_ax.set_yticklabels([])

    hm_ax.tick_params(axis="both", length=0)

    # Group color bar
    if has_groups and grp_ax is not None:
        unique_groups = list(dict.fromkeys(groups))  # preserve order
        default_palette = [
            "#2A6496", "#C0392B", "#27AE60", "#E67E22",
            "#8E44AD", "#16A085", "#D35400", "#2C3E50",
        ]
        pal = group_palette or default_palette
        group_color_map = {g: pal[i % len(pal)] for i, g in enumerate(unique_groups)}
        colors_arr = [group_color_map[g] for g in groups]

        for r, c in enumerate(colors_arr):
            grp_ax.barh(r, 1, color=c, height=1.0, left=0)
        grp_ax.set_xlim(0, 1)
        grp_ax.set_ylim(-0.5, n_rows - 0.5)
        grp_ax.invert_yaxis()
        grp_ax.axis("off")

        # Group legend
        legend_patches = [mpatches.Patch(color=group_color_map[g], label=g)
                          for g in unique_groups]
        fig.legend(handles=legend_patches, fontsize=font_size - 1,
                   loc="lower left", bbox_to_anchor=(0.0, 0.0),
                   borderpad=0.3, handlelength=1.0)

    # Colorbar
    cbar = fig.colorbar(im, cax=cb_ax)
    cbar.set_label("Z-score", fontsize=font_size - 1)
    cbar.ax.tick_params(labelsize=font_size - 2, length=2)
    cbar.set_ticks([-zscore_clip, 0, zscore_clip])
    cbar.set_ticklabels([f"≤{-zscore_clip:.0f}", "0", f"≥{zscore_clip:.0f}"])

    if title:
        fig.suptitle(title, fontsize=font_size + 1, y=1.01)

    plt.tight_layout(pad=0.2)
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(prog="zscore_heatmap",
                                     description="Z-score heatmap (rows=features, cols=samples)")
    parser.add_argument("--csv", required=True,
                        help="CSV: col0=feature name, remaining cols=numeric samples")
    parser.add_argument("--out", required=True)
    parser.add_argument("--row-group-col", default=None,
                        help="Column name for row group labels")
    parser.add_argument("--cluster-rows", action="store_true", default=True)
    parser.add_argument("--no-cluster-rows", dest="cluster_rows", action="store_false")
    parser.add_argument("--cluster-cols", action="store_true", default=False)
    parser.add_argument("--top-n", type=int, default=None,
                        help="Keep top N rows by variance")
    parser.add_argument("--title", default="")
    parser.add_argument("--double-column", action="store_true")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    print(f"[zscore_heatmap] Loaded {df.shape[0]} features × {df.shape[1]-1} samples")

    fig = zscore_heatmap(
        df,
        row_group_col=args.row_group_col,
        cluster_rows=args.cluster_rows,
        cluster_cols=args.cluster_cols,
        top_n=args.top_n,
        title=args.title,
        double_column=args.double_column,
        dpi=args.dpi,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fmt = out.suffix.lstrip(".")
    fig.savefig(out, dpi=args.dpi, bbox_inches="tight")
    print(f"[zscore_heatmap] → {out}")
    svg = out.with_suffix(".svg")
    if svg != out:
        fig.savefig(svg, format="svg", bbox_inches="tight")
        print(f"[zscore_heatmap] → {svg}")
    plt.close(fig)


if __name__ == "__main__":
    main()
