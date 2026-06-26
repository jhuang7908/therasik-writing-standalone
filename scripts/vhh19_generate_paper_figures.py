"""
Generate publication-ready figures (Fig1–Fig5) for the 19 clinical-stage VHH dataset.

Input (raw table, versioned in-repo):
  - paper/tables/Table1_slice3_19_clinical_vhh_master.csv

Outputs (written under paper/):
  - paper/figures/VHH19_Fig*.png (+ .svg)
  - paper/figures_data/VHH19_Fig*.csv  (exact data used to plot)
  - paper/stats/VHH19_*.tsv            (statistical test outputs)

This script is intentionally self-contained and deterministic.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from scipy import stats as sp_stats
except Exception as e:  # pragma: no cover
    sp_stats = None
    _SCIPY_IMPORT_ERROR = e


PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_TABLE1 = PROJECT_ROOT / "paper" / "tables" / "Table1_slice3_19_clinical_vhh_master.csv"

OUT_PAPER = PROJECT_ROOT / "paper"
OUT_FIGS = OUT_PAPER / "figures"
OUT_FIG_DATA = OUT_PAPER / "figures_data"
OUT_STATS = OUT_PAPER / "stats"


STRATEGY_ORDER = ["BM", "SR", "Native"]
FOLD_ORDER = ["H2-9-1", "H2-10-1", "unknown"]


def _ensure_dirs() -> None:
    for d in (OUT_PAPER, OUT_FIGS, OUT_FIG_DATA, OUT_STATS):
        d.mkdir(parents=True, exist_ok=True)


def _save_png_svg(fig: plt.Figure, out_base: Path) -> None:
    fig.savefig(out_base.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(out_base.with_suffix(".svg"), bbox_inches="tight")


def _norm_strategy_group(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("BM"):
        return "BM"
    if s.startswith("SR"):
        return "SR"
    if s.startswith("Native"):
        return "Native"
    # already normalized in table1, but keep safe
    if s in {"BM", "SR", "Native"}:
        return s
    return "Unknown"


def _clinical_stage_bin(status: str) -> str:
    s = (status or "").strip()
    if s.startswith("Approved"):
        return "Approved"
    if s.startswith("Phase 3"):
        return "Phase 3"
    if s.startswith("Phase 2"):
        return "Phase 2"
    if s.startswith("Phase 1/2"):
        return "Phase 1/2"
    if s.startswith("Phase 1"):
        return "Phase 1"
    if s.startswith("Preclinical"):
        return "Preclinical/Early"
    if "Discontinued" in s:
        return "Discontinued"
    if "Stalled" in s:
        return "Stalled"
    return "Other"


def _fusion_module_from_target(target: str) -> str:
    t = (target or "")
    if re.search(r"\bHSA\b", t, flags=re.IGNORECASE) or re.search(r"\bALB\b", t, flags=re.IGNORECASE):
        return "HSA"
    if re.search(r"\bFc\b", t, flags=re.IGNORECASE):
        return "Fc"
    return "None"


def _jitter_scatter(ax: plt.Axes, xs: float, ys: np.ndarray, seed: int = 42, scale: float = 0.06) -> None:
    rng = np.random.default_rng(seed)
    xj = rng.normal(loc=xs, scale=scale, size=len(ys))
    ax.scatter(xj, ys, s=22, alpha=0.75, zorder=3)


def _boxplot_with_points(
    df: pd.DataFrame,
    group_col: str,
    value_col: str,
    order: list[str],
    title: str,
    ylabel: str,
    out_base: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.9))
    data = []
    for g in order:
        vals = df.loc[df[group_col] == g, value_col].dropna().astype(float).values
        data.append(vals)
    ax.boxplot(data, tick_labels=order, showfliers=True)
    for i, g in enumerate(order, start=1):
        vals = df.loc[df[group_col] == g, value_col].dropna().astype(float).values
        if len(vals):
            _jitter_scatter(ax, i, vals)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)
    _save_png_svg(fig, out_base)
    plt.close(fig)


def _heatmap(
    data: np.ndarray,
    row_labels: list[str],
    col_labels: list[str],
    title: str,
    out_base: Path,
    cmap: str = "viridis",
) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    im = ax.imshow(data, aspect="auto", interpolation="nearest", cmap=cmap)
    ax.set_yticks(range(len(row_labels)), labels=row_labels)
    ax.set_xticks(range(len(col_labels)), labels=col_labels, rotation=35, ha="right")
    ax.set_title(title)
    cbar = fig.colorbar(im, ax=ax, shrink=0.9)
    cbar.ax.set_ylabel("Scaled value (z-score)", rotation=90)
    ax.grid(False)
    _save_png_svg(fig, out_base)
    plt.close(fig)


def _zscore(x: pd.Series) -> pd.Series:
    x = x.astype(float)
    mu = float(x.mean())
    sd = float(x.std(ddof=0))
    if sd == 0.0 or math.isnan(sd):
        return x * 0.0
    return (x - mu) / sd


def _holm_adjust(pvals: list[float]) -> list[float]:
    """Holm-Bonferroni adjustment."""
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m, dtype=float)
    for k, idx in enumerate(order):
        adj[idx] = min(1.0, (m - k) * pvals[idx])
    # enforce monotonicity
    for i in range(1, m):
        prev = order[i - 1]
        cur = order[i]
        adj[cur] = max(adj[cur], adj[prev])
    return adj.tolist()


def _fisher_or_ci(a: int, b: int, c: int, d: int) -> tuple[float, float, float]:
    """
    Odds ratio and Wald 95% CI on log(OR).
    Applies Haldane–Anscombe correction (+0.5) if any cell is 0.
    """
    aa, bb, cc, dd = float(a), float(b), float(c), float(d)
    if min(aa, bb, cc, dd) == 0.0:
        aa += 0.5
        bb += 0.5
        cc += 0.5
        dd += 0.5
    or_hat = (aa * dd) / (bb * cc)
    se = math.sqrt(1.0 / aa + 1.0 / bb + 1.0 / cc + 1.0 / dd)
    lo = math.exp(math.log(or_hat) - 1.96 * se)
    hi = math.exp(math.log(or_hat) + 1.96 * se)
    return float(or_hat), float(lo), float(hi)


def _require_scipy() -> None:
    if sp_stats is None:
        raise RuntimeError(f"scipy is required for statistics, but could not import it: {_SCIPY_IMPORT_ERROR}")


def _write_tsv(rows: list[dict], out_path: Path) -> None:
    pd.DataFrame(rows).to_csv(out_path, sep="\t", index=False)


def _pairwise_mannwhitney(
    df: pd.DataFrame, group_col: str, value_col: str, groups: list[str]
) -> pd.DataFrame:
    _require_scipy()
    pairs = []
    pvals = []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            g1, g2 = groups[i], groups[j]
            x1 = df.loc[df[group_col] == g1, value_col].dropna().astype(float).values
            x2 = df.loc[df[group_col] == g2, value_col].dropna().astype(float).values
            if len(x1) == 0 or len(x2) == 0:
                p = float("nan")
                u = float("nan")
            else:
                u, p = sp_stats.mannwhitneyu(x1, x2, alternative="two-sided")
            pairs.append((g1, g2, u, p))
            pvals.append(1.0 if math.isnan(p) else float(p))
    adj = _holm_adjust(pvals)
    out = []
    for (g1, g2, u, p), p_adj in zip(pairs, adj, strict=True):
        out.append(
            {
                "test": "Mann-Whitney U (two-sided)",
                "value_col": value_col,
                "group1": g1,
                "group2": g2,
                "U": u,
                "p": p,
                "p_holm": p_adj,
            }
        )
    return pd.DataFrame(out)


def main() -> None:
    _ensure_dirs()

    if not IN_TABLE1.exists():
        raise RuntimeError(f"Missing input: {IN_TABLE1}")

    df = pd.read_csv(IN_TABLE1)
    df["strategy_group"] = df["strategy_group"].astype(str).map(_norm_strategy_group)
    df["clinical_stage"] = df["clinical_status"].astype(str).map(_clinical_stage_bin)
    df["fusion_module"] = df["target"].astype(str).map(_fusion_module_from_target)

    # Persist an auditable "analysis-ready" copy (raw + derived columns)
    analysis_ready = OUT_PAPER / "tables" / "Table1_slice3_19_clinical_vhh_master_analysis_ready.csv"
    df.to_csv(analysis_ready, index=False)

    # -------------------------
    # Fig1: dataset landscape
    # -------------------------
    fig1a = df[["antibody_id", "strategy_group", "clinical_stage", "fusion_module"]].copy()
    fig1a.to_csv(OUT_FIG_DATA / "VHH19_Fig1_dataset_landscape.csv", index=False)

    # Fig1A: strategy counts
    counts = df["strategy_group"].value_counts().reindex(STRATEGY_ORDER)
    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    ax.bar(counts.index, counts.values, color=["#4C78A8", "#F58518", "#54A24B"])
    ax.set_title("Clinical VHH humanization strategies (N=19)")
    ax.set_ylabel("Count")
    for i, v in enumerate(counts.values):
        ax.text(i, v + 0.15, str(int(v)), ha="center", va="bottom", fontsize=10)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)
    _save_png_svg(fig, OUT_FIGS / "VHH19_Fig1A_strategy_counts")
    plt.close(fig)

    # Fig1B: clinical stage by strategy (stacked)
    stage_order = ["Approved", "Phase 3", "Phase 2", "Phase 1/2", "Phase 1", "Preclinical/Early", "Stalled", "Discontinued", "Other"]
    pivot = (
        df.pivot_table(index="clinical_stage", columns="strategy_group", values="antibody_id", aggfunc="count", fill_value=0)
        .reindex(stage_order)
        .reindex(columns=STRATEGY_ORDER, fill_value=0)
    )
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bottom = np.zeros(len(pivot), dtype=float)
    colors = {"BM": "#4C78A8", "SR": "#F58518", "Native": "#54A24B"}
    for g in STRATEGY_ORDER:
        vals = pivot[g].values.astype(float)
        ax.bar(pivot.index, vals, bottom=bottom, label=g, color=colors[g])
        bottom += vals
    ax.set_title("Clinical stage distribution by strategy")
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=35)
    ax.legend(frameon=False, ncol=3, loc="upper right")
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)
    _save_png_svg(fig, OUT_FIGS / "VHH19_Fig1B_stage_by_strategy")
    plt.close(fig)

    # -------------------------
    # Fig2: canonical fold × strategy association + OR/CI
    # -------------------------
    fig2_df = df[["antibody_id", "strategy_group", "h2_class"]].copy()
    fig2_df["h2_class"] = fig2_df["h2_class"].fillna("unknown").astype(str)
    fig2_df.to_csv(OUT_FIG_DATA / "VHH19_Fig2_fold_strategy_table.csv", index=False)

    cont = (
        fig2_df.pivot_table(index="h2_class", columns="strategy_group", values="antibody_id", aggfunc="count", fill_value=0)
        .reindex(index=FOLD_ORDER)
        .reindex(columns=STRATEGY_ORDER, fill_value=0)
    )

    # Fig2A: heatmap of counts (annotated)
    fig, ax = plt.subplots(figsize=(6.3, 3.8))
    im = ax.imshow(cont.values, cmap="Blues")
    ax.set_xticks(range(len(cont.columns)), labels=cont.columns)
    ax.set_yticks(range(len(cont.index)), labels=cont.index)
    ax.set_title("H2 canonical fold vs humanization strategy (counts)")
    for i in range(cont.shape[0]):
        for j in range(cont.shape[1]):
            ax.text(j, i, str(int(cont.values[i, j])), ha="center", va="center", color="black", fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.85, label="Count")
    _save_png_svg(fig, OUT_FIGS / "VHH19_Fig2A_fold_strategy_counts")
    plt.close(fig)

    # Fig2B: Fisher exact + OR (H2-9-1 vs H2-10-1; BM vs non-BM), excluding unknown
    _require_scipy()
    sub = fig2_df[fig2_df["h2_class"].isin(["H2-9-1", "H2-10-1"])].copy()
    sub["is_bm"] = sub["strategy_group"].eq("BM")
    # 2x2:
    #            BM   notBM
    # H2-9-1      a     b
    # H2-10-1     c     d
    a = int(((sub["h2_class"] == "H2-9-1") & (sub["is_bm"])).sum())
    b = int(((sub["h2_class"] == "H2-9-1") & (~sub["is_bm"])).sum())
    c = int(((sub["h2_class"] == "H2-10-1") & (sub["is_bm"])).sum())
    d = int(((sub["h2_class"] == "H2-10-1") & (~sub["is_bm"])).sum())
    or_hat, or_lo, or_hi = _fisher_or_ci(a, b, c, d)
    fisher_or, fisher_p = sp_stats.fisher_exact([[a, b], [c, d]])

    _write_tsv(
        [
            {
                "comparison": "H2-9-1 vs H2-10-1 (exclude unknown)",
                "outcome": "BM vs non-BM",
                "a_H2_9_1_BM": a,
                "b_H2_9_1_nonBM": b,
                "c_H2_10_1_BM": c,
                "d_H2_10_1_nonBM": d,
                "fisher_exact_or": float(fisher_or),
                "fisher_exact_p": float(fisher_p),
                "wald_or": or_hat,
                "wald_or_ci95_low": or_lo,
                "wald_or_ci95_high": or_hi,
            }
        ],
        OUT_STATS / "VHH19_fold_strategy_fisher.tsv",
    )

    # Forest-style single-point plot (OR with CI)
    fig, ax = plt.subplots(figsize=(6.0, 2.2))
    ax.errorbar(
        x=[or_hat],
        y=[0],
        xerr=[[or_hat - or_lo], [or_hi - or_hat]],
        fmt="o",
        color="#4C78A8",
        capsize=4,
    )
    ax.axvline(1.0, linestyle="--", color="gray", alpha=0.7)
    ax.set_xscale("log")
    ax.set_yticks([0], labels=["BM enrichment in H2-9-1"])
    ax.set_xlabel("Odds ratio (log scale), 95% CI")
    ax.set_title(f"Fold–strategy association (Fisher p={fisher_p:.3g})")
    ax.grid(True, axis="x", linestyle="--", alpha=0.35)
    _save_png_svg(fig, OUT_FIGS / "VHH19_Fig2B_fold_strategy_or")
    plt.close(fig)

    # -------------------------
    # Fig3: strategy trade-offs (humanness & immunogenicity proxy)
    # -------------------------
    fig3a = df[["antibody_id", "strategy_group", "human_identity"]].copy()
    fig3a.to_csv(OUT_FIG_DATA / "VHH19_Fig3A_human_identity_by_strategy.csv", index=False)
    _boxplot_with_points(
        fig3a,
        group_col="strategy_group",
        value_col="human_identity",
        order=STRATEGY_ORDER,
        title="Global human identity by strategy (N=19)",
        ylabel="Human identity",
        out_base=OUT_FIGS / "VHH19_Fig3A_human_identity_by_strategy",
    )

    fig3b = df[["antibody_id", "strategy_group", "B_total_1pct"]].copy()
    fig3b.to_csv(OUT_FIG_DATA / "VHH19_Fig3B_B_total_1pct_by_strategy.csv", index=False)
    _boxplot_with_points(
        fig3b,
        group_col="strategy_group",
        value_col="B_total_1pct",
        order=STRATEGY_ORDER,
        title="MHC-II binding burden (rank≤1) by strategy",
        ylabel="B_total_1pct (count)",
        out_base=OUT_FIGS / "VHH19_Fig3B_B_total_1pct_by_strategy",
    )

    # Fig3C: scatter (human_identity vs B_total_1pct)
    fig3c = df[["antibody_id", "strategy_group", "human_identity", "B_total_1pct"]].copy()
    fig3c.to_csv(OUT_FIG_DATA / "VHH19_Fig3C_scatter_human_identity_vs_B_total_1pct.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    colors = {"BM": "#4C78A8", "SR": "#F58518", "Native": "#54A24B"}
    for g in STRATEGY_ORDER:
        subg = fig3c[fig3c["strategy_group"] == g]
        ax.scatter(
            subg["human_identity"].astype(float),
            subg["B_total_1pct"].astype(float),
            s=46,
            alpha=0.85,
            label=g,
            color=colors[g],
        )
    # correlation (overall)
    rho, p_rho = sp_stats.spearmanr(fig3c["human_identity"].astype(float), fig3c["B_total_1pct"].astype(float))
    ax.set_title(f"Humanness vs immunogenicity proxy (Spearman ρ={rho:.2f}, p={p_rho:.3g})")
    ax.set_xlabel("Human identity")
    ax.set_ylabel("B_total_1pct (count)")
    ax.grid(True, linestyle="--", alpha=0.25)
    ax.legend(frameon=False, loc="best")
    _save_png_svg(fig, OUT_FIGS / "VHH19_Fig3C_human_identity_vs_B_total_1pct")
    plt.close(fig)

    _write_tsv(
        [{"metric_x": "human_identity", "metric_y": "B_total_1pct", "spearman_rho": float(rho), "spearman_p": float(p_rho)}],
        OUT_STATS / "VHH19_spearman_human_identity_vs_B_total_1pct.tsv",
    )

    # Stats: strategy group comparisons (Kruskal + pairwise MWU Holm)
    rows = []
    for metric in ["human_identity", "B_total_1pct", "score", "hp_max9", "cp_max7"]:
        vals = [df.loc[df["strategy_group"] == g, metric].dropna().astype(float).values for g in STRATEGY_ORDER]
        if sp_stats is not None and all(len(v) > 0 for v in vals):
            h, p_kw = sp_stats.kruskal(*vals)
        else:
            h, p_kw = float("nan"), float("nan")
        rows.append({"test": "Kruskal-Wallis", "metric": metric, "H": float(h), "p": float(p_kw)})
        pair = _pairwise_mannwhitney(df, "strategy_group", metric, STRATEGY_ORDER)
        pair.to_csv(OUT_STATS / f"VHH19_pairwise_mannwhitney_{metric}.tsv", sep="\t", index=False)
    _write_tsv(rows, OUT_STATS / "VHH19_strategy_group_kruskal.tsv")

    # -------------------------
    # Fig4: feature heatmap (scaled) across molecules
    # -------------------------
    feat_cols = ["human_identity", "B_total_1pct", "score", "hp_max9", "cp_max7", "ngly_count", "extra_cys_flag"]
    fig4 = df[["antibody_id", "strategy_group", "h2_class", "clinical_stage", "fusion_module"] + feat_cols].copy()
    fig4.to_csv(OUT_FIG_DATA / "VHH19_Fig4_feature_heatmap_data.csv", index=False)

    # order rows by strategy then antibody_id (stable)
    fig4 = fig4.sort_values(["strategy_group", "antibody_id"]).reset_index(drop=True)
    row_labels = [f"{r.antibody_id} ({r.strategy_group})" for r in fig4.itertuples(index=False)]
    z = np.column_stack([_zscore(fig4[c]).to_numpy() for c in feat_cols])
    _heatmap(
        z,
        row_labels=row_labels,
        col_labels=feat_cols,
        title="Clinical VHH feature profile (z-scored across N=19)",
        out_base=OUT_FIGS / "VHH19_Fig4_feature_heatmap",
        cmap="RdYlBu_r",
    )

    # -------------------------
    # Fig4B: CDR length distributions by strategy (new - CDR1/2/3)
    # -------------------------
    # Load CDR boundaries
    cdr_path = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_ANARCII_CDR_boundaries.csv"
    if cdr_path.exists():
        cdr = pd.read_csv(cdr_path)
        cdr_merged = cdr.merge(df[["antibody_id", "strategy_group"]], on="antibody_id", how="left")
        cdr_merged.to_csv(OUT_FIG_DATA / "VHH19_Fig4B_cdr_lengths_by_strategy.csv", index=False)

        # Fig4B: boxplot of CDR3 length by strategy
        _boxplot_with_points(
            cdr_merged,
            group_col="strategy_group",
            value_col="cdr3_length",
            order=STRATEGY_ORDER,
            title="CDR3 length by strategy (N=19)",
            ylabel="CDR3 length (aa)",
            out_base=OUT_FIGS / "VHH19_Fig4B_cdr3_length_by_strategy",
        )

        # Fig4C: stacked bar of CDR signature (CDR1-CDR2-CDR3 length pattern)
        cdr_merged["cdr_signature"] = (
            cdr_merged["cdr1_length"].astype(str)
            + "-"
            + cdr_merged["cdr2_length"].astype(str)
            + "-"
            + cdr_merged["cdr3_length"].astype(str)
        )
        sig_counts = cdr_merged.groupby(["cdr_signature", "strategy_group"]).size().unstack(fill_value=0)
        sig_counts.to_csv(OUT_FIG_DATA / "VHH19_Fig4C_cdr_signature_counts.csv")

        fig, ax = plt.subplots(figsize=(8.2, 4.5))
        bottom = np.zeros(len(sig_counts), dtype=float)
        colors = {"BM": "#4C78A8", "SR": "#F58518", "Native": "#54A24B"}
        for g in STRATEGY_ORDER:
            if g not in sig_counts.columns:
                continue
            vals = sig_counts[g].values.astype(float)
            ax.barh(sig_counts.index, vals, left=bottom, label=g, color=colors[g])
            bottom += vals
        ax.set_xlabel("Count")
        ax.set_title("CDR signature (CDR1-CDR2-CDR3 lengths) by strategy")
        ax.legend(frameon=False, loc="best")
        ax.grid(True, axis="x", linestyle="--", alpha=0.35)
        _save_png_svg(fig, OUT_FIGS / "VHH19_Fig4C_cdr_signature_by_strategy")
        plt.close(fig)

    # -------------------------
    # Fig5: decision framework as Mermaid (paper-friendly)
    # -------------------------
    fig5_md = OUT_FIGS / "VHH19_Fig5_decision_framework_mermaid.md"
    fig5_md.write_text(
        "\n".join(
            [
                "## VHH19 Fig5. Fold-informed humanization decision framework (Mermaid)",
                "",
                "```mermaid",
                "flowchart TD",
                "  A[Input: VHH sequence] --> B[IMGT numbering + CDR definition]",
                "  B --> C[Annotate H2 canonical fold (e.g., H2-9-1 / H2-10-1)]",
                "  C --> D{H2 fold?}",
                "  D -->|H2-9-1 (framework-dependent)| E[Prefer BM (grafting + back-mutations)]",
                "  D -->|H2-10-1 (more robust)| F[Prefer SR or Native]",
                "  D -->|unknown/ambiguous| G[Start with SR; escalate to BM if risks rise]",
                "  E --> H[In silico checks: MHC-II scan + developability/CMC proxies]",
                "  F --> H",
                "  G --> H",
                "  H --> I{Fusion module (HSA/Fc)?}",
                "  I -->|Yes| J[Interpret humanness thresholds in context; evaluate ADA risk plan]",
                "  I -->|No| K[Stricter immunogenicity control; consider SR/BM tuning]",
                "  J --> L[Output: recommended strategy + verification checklist]",
                "  K --> L",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print("Wrote VHH19 paper figures to:", OUT_FIGS)
    print("Wrote VHH19 plot data to:", OUT_FIG_DATA)
    print("Wrote VHH19 stats to:", OUT_STATS)


if __name__ == "__main__":
    main()

