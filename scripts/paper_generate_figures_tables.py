"""
Generate paper-ready figures and tables for:
  - 19 clinical VHHs (Slice-3) humanization analysis
  - 7D12 (4KRL) humanization evaluation summary

Outputs are written to:
  - paper/tables/
  - paper/figures/
  - paper/figures_data/

Design:
  - Deterministic, uses existing computed reports as inputs.
  - Produces both CSV (machine-readable) and PNG/SVG (publication-ready).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

IN_META = PROJECT_ROOT / "reports" / "slice3_vhh_comprehensive_functional_library.csv"
IN_IMM = PROJECT_ROOT / "reports" / "slice3_vhh_immunogenicity_features.csv"
IN_DEV = PROJECT_ROOT / "reports" / "slice3_vhh_developability_features_native_sr_bm.csv"

IN_7D12 = PROJECT_ROOT / "output" / "7D12" / "7d12_4krl_eval_table.csv"
IN_7D12_SURF = PROJECT_ROOT / "output" / "7D12" / "7d12_4krl_per_residue_surface_metrics.csv"

OUT_DIR = PROJECT_ROOT / "paper"
OUT_TABLES = OUT_DIR / "tables"
OUT_FIGS = OUT_DIR / "figures"
OUT_FIG_DATA = OUT_DIR / "figures_data"


def norm_strategy(strategy: str) -> str:
    s = (strategy or "").strip()
    if s.startswith("SR"):
        return "SR"
    if s.startswith("BM"):
        return "BM"
    if s.startswith("Native"):
        return "Native"
    return "Unknown"


def save_png_svg(fig: plt.Figure, basepath: Path) -> None:
    fig.savefig(basepath.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(basepath.with_suffix(".svg"), bbox_inches="tight")


def boxplot_by_group(
    df: pd.DataFrame,
    x: str,
    y: str,
    order: list[str],
    title: str,
    ylabel: str,
    out_base: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    data = [df.loc[df[x] == g, y].dropna().astype(float).values for g in order]
    ax.boxplot(data, tick_labels=order, showfliers=True)

    # overlay jittered points
    rng = np.random.default_rng(42)
    for i, g in enumerate(order, start=1):
        vals = df.loc[df[x] == g, y].dropna().astype(float).values
        if len(vals) == 0:
            continue
        xs = rng.normal(loc=i, scale=0.05, size=len(vals))
        ax.scatter(xs, vals, s=20, alpha=0.7)

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)
    save_png_svg(fig, out_base)
    plt.close(fig)


def main() -> None:
    for d in (OUT_DIR, OUT_TABLES, OUT_FIGS, OUT_FIG_DATA):
        d.mkdir(parents=True, exist_ok=True)

    missing = [p for p in (IN_META, IN_IMM, IN_DEV, IN_7D12, IN_7D12_SURF) if not p.exists()]
    if missing:
        raise RuntimeError("Missing required inputs:\n" + "\n".join(f"- {p}" for p in missing))

    # -------------------------
    # Table 1: 19 clinical VHHs master table
    # -------------------------
    meta = pd.read_csv(IN_META).rename(
        columns={
            "Drug Name": "antibody_id",
            "Humanization Strategy": "strategy",
            "Clinical Status": "clinical_status",
            "Target": "target",
            "Global Human Identity": "human_identity",
            "H2 Class": "h2_class",
            "FR2/3 Delta (Hu-Alp)": "fr23_delta_hu_alp",
        }
    )
    meta["strategy_group"] = meta["strategy"].astype(str).map(norm_strategy)

    imm = pd.read_csv(IN_IMM)
    dev = pd.read_csv(IN_DEV)
    imm_n = imm[imm["variant"] == "native"].copy()
    dev_n = dev[dev["variant"] == "native"].copy()

    # Standardize IDs
    imm_n = imm_n.rename(columns={"antibody_id": "antibody_id"})
    dev_n = dev_n.rename(columns={"antibody_id": "antibody_id"})

    table1 = (
        meta.merge(
            imm_n[["antibody_id", "B_total_1pct", "B_total_2pct", "B_breadth_1pct", "min_rank"]],
            on="antibody_id",
            how="left",
        )
        .merge(
            dev_n[["antibody_id", "score", "risk_tier", "hp_max9", "cp_max7", "ngly_count", "extra_cys_flag"]],
            on="antibody_id",
            how="left",
        )
        .sort_values(["strategy_group", "antibody_id"])
    )
    table1_out_cols = [
        "antibody_id",
        "strategy",
        "strategy_group",
        "clinical_status",
        "target",
        "human_identity",
        "h2_class",
        "fr23_delta_hu_alp",
        "B_total_1pct",
        "B_total_2pct",
        "B_breadth_1pct",
        "min_rank",
        "score",
        "risk_tier",
        "hp_max9",
        "cp_max7",
        "ngly_count",
        "extra_cys_flag",
    ]
    table1_csv = OUT_TABLES / "Table1_slice3_19_clinical_vhh_master.csv"
    table1_md = OUT_TABLES / "Table1_slice3_19_clinical_vhh_master.md"
    table1[table1_out_cols].to_csv(table1_csv, index=False)
    table1[table1_out_cols].to_markdown(table1_md, index=False)

    # -------------------------
    # Table 2: 7D12 native/SR/BM evaluation table
    # -------------------------
    df7 = pd.read_csv(IN_7D12)
    table2_cols = [
        "variant",
        "B_total_1pct",
        "B_total_2pct",
        "B_breadth_1pct",
        "B_breadth_2pct",
        "min_rank",
        "dev_score",
        "dev_risk_tier",
        "hydro_patch_max9",
        "charge_patch_max7",
        "ngly_count",
        "extra_cys_flag",
        "ox_w_count",
        "total_len",
    ]
    table2_csv = OUT_TABLES / "Table2_7D12_native_sr_bm_summary.csv"
    table2_md = OUT_TABLES / "Table2_7D12_native_sr_bm_summary.md"
    df7[table2_cols].to_csv(table2_csv, index=False)
    df7[table2_cols].to_markdown(table2_md, index=False)

    # -------------------------
    # Figure data + plots
    # -------------------------
    # Fig2: FR2/3 Delta (Hu-Alp) by clinical strategy group
    fig2_df = table1[["antibody_id", "strategy_group", "fr23_delta_hu_alp"]].copy()
    fig2_df.to_csv(OUT_FIG_DATA / "Fig2_fr23_delta_by_strategy.csv", index=False)
    boxplot_by_group(
        fig2_df,
        x="strategy_group",
        y="fr23_delta_hu_alp",
        order=["SR", "BM", "Native"],
        title="FR2/FR3 identity contrast (Human−Alpaca) by strategy",
        ylabel="Δ identity (Hu − Alp) over FR2+FR3",
        out_base=OUT_FIGS / "Fig2_fr23_delta_by_strategy",
    )

    # Fig3: Immunogenicity proxy (B_total_1pct) by strategy group
    fig3_df = table1[["antibody_id", "strategy_group", "B_total_1pct"]].copy()
    fig3_df.to_csv(OUT_FIG_DATA / "Fig3_B_total_1pct_by_strategy.csv", index=False)
    boxplot_by_group(
        fig3_df,
        x="strategy_group",
        y="B_total_1pct",
        order=["SR", "BM", "Native"],
        title="MHC-II binding burden (rank≤1) by strategy",
        ylabel="B_total_1pct (count of 15-mers with rank ≤ 1.0)",
        out_base=OUT_FIGS / "Fig3_B_total_1pct_by_strategy",
    )

    # Fig4: Developability score and hydrophobic patch by strategy group
    fig4a_df = table1[["antibody_id", "strategy_group", "score"]].copy()
    fig4a_df.to_csv(OUT_FIG_DATA / "Fig4A_dev_score_by_strategy.csv", index=False)
    boxplot_by_group(
        fig4a_df,
        x="strategy_group",
        y="score",
        order=["SR", "BM", "Native"],
        title="Developability composite score by strategy",
        ylabel="Developability score (higher = better)",
        out_base=OUT_FIGS / "Fig4A_dev_score_by_strategy",
    )

    fig4b_df = table1[["antibody_id", "strategy_group", "hp_max9"]].copy()
    fig4b_df.to_csv(OUT_FIG_DATA / "Fig4B_hp_max9_by_strategy.csv", index=False)
    boxplot_by_group(
        fig4b_df,
        x="strategy_group",
        y="hp_max9",
        order=["SR", "BM", "Native"],
        title="Hydrophobic patch (hp_max9) by strategy",
        ylabel="hp_max9 (max 9-mer hydrophobic fraction; lower = better)",
        out_base=OUT_FIGS / "Fig4B_hp_max9_by_strategy",
    )

    # Fig5: 7D12 surface map (relSASA vs hydrophilicity; highlight SR mutations)
    surf = pd.read_csv(IN_7D12_SURF)
    surf = surf[surf["imgt_pos"].notna()].copy()
    surf["imgt_pos"] = surf["imgt_pos"].astype(int)
    # hydrophilicity column already exists in this file; if not, fallback
    if "hydrophilicity" not in surf.columns and "kd_hydropathy" in surf.columns:
        surf["hydrophilicity"] = -surf["kd_hydropathy"]

    sr_muts = {12: "S>L", 40: "G>S", 42: "F>V", 83: "A>S", 96: "P>A", 101: "I>V"}
    surf["is_sr_site"] = surf["imgt_pos"].isin(sr_muts.keys())
    surf["sr_label"] = surf["imgt_pos"].map(sr_muts).fillna("")

    surf_out = OUT_FIG_DATA / "Fig5_7D12_surface_scatter_data.csv"
    surf.to_csv(surf_out, index=False)

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    base = surf[~surf["is_sr_site"]]
    ax.scatter(
        base["rel_sasa"].astype(float),
        base["hydrophilicity"].astype(float),
        s=18,
        alpha=0.6,
        label="other residues",
    )
    hi = surf[surf["is_sr_site"]]
    ax.scatter(
        hi["rel_sasa"].astype(float),
        hi["hydrophilicity"].astype(float),
        s=50,
        alpha=0.95,
        label="SR mutation sites",
    )
    for _, r in hi.iterrows():
        ax.annotate(
            f"{int(r['imgt_pos'])}",
            (float(r["rel_sasa"]), float(r["hydrophilicity"])),
            textcoords="offset points",
            xytext=(5, 3),
            fontsize=8,
        )
    ax.axvline(0.25, linestyle="--", color="gray", alpha=0.6)
    ax.axhline(0.0, linestyle="--", color="gray", alpha=0.6)
    ax.set_xlabel("relSASA")
    ax.set_ylabel("Hydrophilicity (−Kyte–Doolittle)")
    ax.set_title("7D12 surface exposure vs hydrophilicity (SR sites highlighted)")
    ax.legend(frameon=False, loc="best")
    ax.grid(True, linestyle="--", alpha=0.25)
    save_png_svg(fig, OUT_FIGS / "Fig5_7D12_surface_hydrophilicity_scatter")
    plt.close(fig)

    # Fig1: pipeline schematic as Mermaid (easy to paste into paper/slide)
    fig1_md = OUT_FIGS / "Fig1_pipeline_mermaid.md"
    fig1_md.write_text(
        "\n".join(
            [
                "## Fig1. Pipeline schematic (Mermaid)",
                "",
                "```mermaid",
                "flowchart TD",
                "  A[Input sequences: 19 clinical VHH + 7D12] --> B[ANARCI IMGT numbering + FR/CDR segmentation]",
                "  B --> C[SSOT position sets: anchors/vernier/hallmark/ND-dependent/surface-strict]",
                "  C --> D[Observed strategy inference: SR vs BM vs Native (human vs alpaca template matching)]",
                "  C --> E[Variant generation: Native / SR / BM (IMGT constrained)]",
                "  E --> F[IEDB MHC-II 15-mer scan (rank≤1,≤2) + audit/cache]",
                "  E --> G[CMC/developability proxy: liabilities + hp_max9/cp_max7 + dev_score]",
                "  A --> H[Structure: PDB or AlphaFold2]",
                "  H --> I[Surface hydrophilicity: relSASA + KD; patch analysis]",
                "  F --> J[Paper tables/figures]",
                "  G --> J",
                "  I --> J",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # Index
    index = OUT_DIR / "FIGURES_TABLES_INDEX.md"
    index.write_text(
        "\n".join(
            [
                "# Paper Figures & Tables (auto-generated)",
                "",
                "## Tables",
                f"- Table 1: `{table1_csv}` and `{table1_md}`",
                f"- Table 2: `{table2_csv}` and `{table2_md}`",
                "",
                "## Figures (PNG + SVG) and data",
                "- Fig1: Mermaid schematic",
                f"  - `{OUT_FIGS / 'Fig1_pipeline_mermaid.md'}`",
                "- Fig2: FR2/FR3 Δ(Hu−Alp) by strategy",
                f"  - `{OUT_FIGS / 'Fig2_fr23_delta_by_strategy.png'}` / `.svg`",
                f"  - data: `{OUT_FIG_DATA / 'Fig2_fr23_delta_by_strategy.csv'}`",
                "- Fig3: B_total_1pct by strategy",
                f"  - `{OUT_FIGS / 'Fig3_B_total_1pct_by_strategy.png'}` / `.svg`",
                f"  - data: `{OUT_FIG_DATA / 'Fig3_B_total_1pct_by_strategy.csv'}`",
                "- Fig4A: developability score by strategy",
                f"  - `{OUT_FIGS / 'Fig4A_dev_score_by_strategy.png'}` / `.svg`",
                f"  - data: `{OUT_FIG_DATA / 'Fig4A_dev_score_by_strategy.csv'}`",
                "- Fig4B: hp_max9 by strategy",
                f"  - `{OUT_FIGS / 'Fig4B_hp_max9_by_strategy.png'}` / `.svg`",
                f"  - data: `{OUT_FIG_DATA / 'Fig4B_hp_max9_by_strategy.csv'}`",
                "- Fig5: 7D12 relSASA vs hydrophilicity (SR sites highlighted)",
                f"  - `{OUT_FIGS / 'Fig5_7D12_surface_hydrophilicity_scatter.png'}` / `.svg`",
                f"  - data: `{OUT_FIG_DATA / 'Fig5_7D12_surface_scatter_data.csv'}`",
                "",
                "## Re-run",
                "```bash",
                "python scripts/paper_generate_figures_tables.py",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print("Wrote paper outputs under:", OUT_DIR)


if __name__ == "__main__":
    main()

