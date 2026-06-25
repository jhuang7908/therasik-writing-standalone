#!/usr/bin/env python3
"""
ADA Clinical Relevance Analysis — Assay-Stratified Correlation Study
=====================================================================
Re-runs the 138-panel correlation analysis with proper stratification by
ADA detection method (assay_platform / assay_generation), since method
changes make cross-method comparison unreliable.

Within each assay stratum, computes Spearman rank correlations between
molecular/physicochemical parameters and clinical ADA incidence.

Compares results with previous (pooled) findings from
ADA_138_MetaAnalysis_Paper_EN.md to assess consistency.

Output: Markdown report → data/immunogenicity_knowledge_base/reports/
"""
import os, sys, json, warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

# Set plotting style — bold everywhere for presentation readability
plt.rcParams.update({
    'font.size': 15,
    'font.weight': 'bold',
    'axes.labelsize': 17,
    'axes.labelweight': 'bold',
    'axes.titlesize': 19,
    'axes.titleweight': 'bold',
    'xtick.labelsize': 14,
    'ytick.labelsize': 14,
    'legend.fontsize': 14,
    'figure.titlesize': 22,
    'figure.titleweight': 'bold',
    'font.sans-serif': ['Noto Sans SC', 'Inter', 'Arial'],
})

warnings.filterwarnings("ignore", category=RuntimeWarning)

ROOT = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite")
CSV_PATH = ROOT / "data" / "immunogenicity_knowledge_base" / "master" / "ada_master_136_curated.csv"
OUT_DIR  = ROOT / "data" / "immunogenicity_knowledge_base" / "reports"
IMG_DIR  = ROOT / "therasik-web-source" / "images" / "ada_study"
OUT_DIR.mkdir(parents=True, exist_ok=True)
IMG_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "ADA_Assay_Stratified_Clinical_Analysis_2026.md"
JSON_FILE = OUT_DIR / "ada_assay_stratified_correlations.json"

FEATURES = [
    ("vh_germline_identity",  "VH Germline Identity"),
    ("vl_germline_identity",  "VL Germline Identity"),
    ("pI",                    "Isoelectric Point (pI)"),
    ("GRAVY",                 "GRAVY Index"),
    ("instability_index",     "Instability Index"),
    ("net_charge_pH7",        "Net Charge (pH 7)"),
    ("hydro_patch_max9",      "Hydrophobic Patch Score"),
    ("charge_patch_max7",     "Charge Patch Score"),
    ("agg_motifs",            "Aggregation Motif Count"),
    ("deamidation_sites",     "Deamidation Sites"),
    ("isomerization_sites",   "Isomerization Sites"),
    ("immuno_tcia_score",     "TCIA Immunogenicity Score"),
    ("immuno_n_high",         "MHC-II High-Risk Epitopes"),
    ("immuno_n_clusters",     "T-cell Epitope Clusters"),
    ("surf_n_patches",        "Surface Hydrophobic Patches"),
    ("surf_frac_exposed_vh",  "VH Surface Exposure Fraction"),
    ("surf_frac_exposed_vl",  "VL Surface Exposure Fraction"),
    ("surf_hydrophilicity",   "Surface Hydrophilicity"),
    ("vh_vl_angle_deg",       "VH-VL Packing Angle"),
    ("interface_n_pairs",     "Interface Contact Pairs"),
    ("interface_mean_dist_A", "Interface Mean Distance"),
    ("ada_v2_score",          "ADA V2 Composite Score"),
    ("heavy_seq_len",         "Heavy Chain Length"),
    ("light_seq_len",         "Light Chain Length"),
]

PREVIOUS_FINDINGS = {
    "Full panel": {
        "surf_frac_exposed_vh": (-0.187, 0.033),
        "agg_motifs":           (+0.183, 0.037),
        "vh_germline_identity": (-0.178, 0.043),
    },
    "Humanized (HU)": {
        "surf_frac_exposed_vl": (+0.226, 0.049),
    },
    "Fully Human (FH)": {
        "surf_n_patches":       (+0.362, 0.007),
        "vl_germline_identity": (-0.323, 0.017),
        "ada_v2_score":         (+0.323, 0.017),
        "interface_n_pairs":    (+0.302, 0.027),
    },
}


def load_data():
    df = pd.read_csv(CSV_PATH)
    df["ada_first_pct"] = pd.to_numeric(df["ada_first_pct"], errors="coerce")
    for col, _ in FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def classify_assay(row):
    """Assign assay category from assay_platform + assay_generation."""
    platform = str(row.get("assay_platform", "")).strip().upper()
    gen = str(row.get("assay_generation", "")).strip().lower()

    if "bridg" in gen:
        return "Bridging"
    elif "tier" in gen:
        return "Tiered / Drug-tolerant"
    elif gen == "1.0" or (gen == "1.5"):
        return "ELISA (1st-gen)"
    elif gen == "2.0" or "ECL" in platform:
        return "ECL (2nd-gen)"
    elif "ELISA" in platform:
        return "ELISA (1st-gen)"
    else:
        return "Unknown/Other"


def compute_correlations(df_sub, label):
    """Compute Spearman correlations for all features vs ada_first_pct."""
    results = []
    ada = df_sub["ada_first_pct"].dropna()
    for col, name in FEATURES:
        if col not in df_sub.columns:
            continue
        valid = df_sub[[col, "ada_first_pct"]].dropna()
        n = len(valid)
        if n < 10:
            continue
        rho, p = stats.spearmanr(valid[col], valid["ada_first_pct"])
        results.append({
            "stratum": label,
            "feature": col,
            "feature_name": name,
            "rho": round(rho, 4),
            "p_value": round(p, 4),
            "n": n,
            "significant": p < 0.05,
        })
    return results


def assay_summary_table(df):
    """Generate summary statistics by assay category."""
    rows = []
    for cat in df["assay_category"].unique():
        sub = df[df["assay_category"] == cat]
        ada = sub["ada_first_pct"].dropna()
        rows.append({
            "Assay Category": cat,
            "n": len(sub),
            "n_ada": len(ada),
            "Mean ADA (%)": round(ada.mean(), 1) if len(ada) > 0 else "—",
            "Median ADA (%)": round(ada.median(), 1) if len(ada) > 0 else "—",
            "SD": round(ada.std(), 1) if len(ada) > 0 else "—",
            "Range": f"{ada.min():.1f}–{ada.max():.1f}" if len(ada) > 0 else "—",
        })
    return pd.DataFrame(rows).sort_values("n", ascending=False)


def origin_x_assay_summary(df):
    """Cross-tabulation: origin × assay."""
    rows = []
    for origin_label in ["HU", "FH"]:
        for cat in sorted(df["assay_category"].unique()):
            sub = df[(df["origin_class"] == origin_label) & (df["assay_category"] == cat)]
            ada = sub["ada_first_pct"].dropna()
            if len(ada) < 3:
                continue
            rows.append({
                "Origin": origin_label,
                "Assay": cat,
                "n": len(ada),
                "Mean ADA (%)": round(ada.mean(), 1),
                "Median ADA (%)": round(ada.median(), 1),
            })
    return pd.DataFrame(rows)


def kruskal_wallis_assay_test(df):
    """Test whether ADA differs significantly across assay categories."""
    groups = []
    labels = []
    for cat in df["assay_category"].unique():
        vals = df[df["assay_category"] == cat]["ada_first_pct"].dropna().values
        if len(vals) >= 5:
            groups.append(vals)
            labels.append(cat)
    if len(groups) < 2:
        return None, None, labels
    stat, p = stats.kruskal(*groups)
    return stat, p, labels


def compare_with_previous(current_results):
    """Compare current significant findings with previous analysis."""
    comparisons = []
    for prev_stratum, prev_feats in PREVIOUS_FINDINGS.items():
        for feat, (prev_rho, prev_p) in prev_feats.items():
            matched = [r for r in current_results
                       if r["feature"] == feat and r["stratum"] == prev_stratum]
            if matched:
                r = matched[0]
                direction_same = (np.sign(prev_rho) == np.sign(r["rho"]))
                comparisons.append({
                    "stratum": prev_stratum,
                    "feature": feat,
                    "prev_rho": prev_rho,
                    "prev_p": prev_p,
                    "new_rho": r["rho"],
                    "new_p": r["p_value"],
                    "new_n": r["n"],
                    "direction_consistent": direction_same,
                    "still_significant": r["p_value"] < 0.05,
                })
    return comparisons


def generate_plots(df):
    """Generate high-resolution plots for the study."""
    print("Generating plots...")

    # ── Fig 1: Three-panel ADA distribution (All / HU / FH) ──
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    df_hu = df[df["origin_class"] == "HU"]
    df_fh = df[df["origin_class"] == "FH"]

    ada_all = df['ada_first_pct'].dropna()
    ada_hu  = df_hu['ada_first_pct'].dropna()
    ada_fh  = df_fh['ada_first_pct'].dropna()

    panels = [
        (axes[0], ada_all, "#0d9488", f" (n={len(ada_all)})"),
        (axes[1], ada_hu,  "#1d4ed8", f" HU (n={len(ada_hu)})"),
        (axes[2], ada_fh,  "#0d9488", f" FH (n={len(ada_fh)})"),
    ]
    for ax, ada, color, title in panels:
        sns.histplot(ada, bins=18, kde=True, color=color, ax=ax)
        med = ada.median()
        ax.axvline(med, color='#ef4444', ls='--', lw=1.5, label=f'Median={med:.1f}%')
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('ADA  (%)', fontsize=14)
        ax.set_ylabel('', fontsize=14)
        ax.legend(fontsize=12)

    fig.suptitle(' 1: 138  ADA  —  /  / ', fontsize=20, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(IMG_DIR / "fig1_ada_distribution.png", dpi=150, bbox_inches='tight')
    plt.close()

    # ── Fig 2: Four-panel ADA boxplots ──
    fig, axes = plt.subplots(2, 2, figsize=(18, 14))

    # (a) By origin
    order_origin = [c for c in ["HU", "FH", "Other"] if c in df["origin_class"].values]
    sns.boxplot(x='origin_class', y='ada_first_pct', data=df, ax=axes[0,0],
                palette={"HU":"#93c5fd", "FH":"#6ee7b7", "Other":"#d1d5db"}, order=order_origin)
    sns.stripplot(x='origin_class', y='ada_first_pct', data=df, ax=axes[0,0],
                  color='#374151', alpha=0.35, size=4, order=order_origin)
    axes[0,0].set_title('(A) ', fontsize=16, fontweight='bold')
    axes[0,0].set_xlabel('')
    axes[0,0].set_ylabel('ADA (%)', fontsize=14)

    # (b) By assay category
    assay_order = sorted(df["assay_category"].unique())
    sns.boxplot(x='assay_category', y='ada_first_pct', data=df, ax=axes[0,1], palette='Set2', order=assay_order)
    sns.stripplot(x='assay_category', y='ada_first_pct', data=df, ax=axes[0,1],
                  color='#374151', alpha=0.35, size=4, order=assay_order)
    axes[0,1].set_title('(B) ', fontsize=16, fontweight='bold')
    axes[0,1].set_xlabel('')
    axes[0,1].set_ylabel('ADA (%)', fontsize=14)
    plt.setp(axes[0,1].get_xticklabels(), rotation=20, ha='right', fontsize=11)

    # (c) By route (simplified)
    route_map = {}
    for r in df["route_curated"].dropna().unique():
        r_up = str(r).upper()
        if "IV" in r_up and "SC" in r_up:
            route_map[r] = "IV+SC"
        elif "IVT" in r_up:
            route_map[r] = "IVT"
        elif "IV" in r_up:
            route_map[r] = "IV"
        elif "SC" in r_up:
            route_map[r] = "SC"
        elif "IM" in r_up:
            route_map[r] = "IM"
        else:
            route_map[r] = "Other"
    df["route_simple"] = df["route_curated"].map(route_map).fillna("Other")
    route_order = [r for r in ["IV", "SC", "IV+SC", "IM", "IVT", "Other"]
                   if r in df["route_simple"].values]
    sns.boxplot(x='route_simple', y='ada_first_pct', data=df, ax=axes[1,0], palette='Set3', order=route_order)
    sns.stripplot(x='route_simple', y='ada_first_pct', data=df, ax=axes[1,0],
                  color='#374151', alpha=0.35, size=4, order=route_order)
    axes[1,0].set_title('(C) ', fontsize=16, fontweight='bold')
    axes[1,0].set_xlabel('')
    axes[1,0].set_ylabel('ADA (%)', fontsize=14)

    # (d) By Fc isotype
    iso_order = [i for i in ["G1", "G2", "G4"] if i in df["fc_isotype"].dropna().unique()]
    df_fc = df[df["fc_isotype"].isin(iso_order)]
    sns.boxplot(x='fc_isotype', y='ada_first_pct', data=df_fc, ax=axes[1,1], palette='Pastel1', order=iso_order)
    sns.stripplot(x='fc_isotype', y='ada_first_pct', data=df_fc, ax=axes[1,1],
                  color='#374151', alpha=0.35, size=4, order=iso_order)
    axes[1,1].set_title('(D)  Fc ', fontsize=16, fontweight='bold')
    axes[1,1].set_xlabel('')
    axes[1,1].set_ylabel('ADA (%)', fontsize=14)

    fig.suptitle(' 2:  ADA ', fontsize=20, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(IMG_DIR / "fig2_ada_boxplots.png", dpi=150, bbox_inches='tight')
    plt.close()

    # ── Fig 3: Correlation Heatmap ──
    plot_feats = [f[0] for f in FEATURES if f[0] in df.columns]
    corr_matrix = df[plot_feats + ['ada_first_pct']].corr(method='spearman')
    plt.figure(figsize=(16, 14))
    sns.heatmap(corr_matrix, annot=False, cmap='RdBu_r', center=0, linewidths=0.3)
    plt.title(' 3: 31  ADA  Spearman ', fontsize=18, fontweight='bold')
    plt.tight_layout()
    plt.savefig(IMG_DIR / "fig3_correlation_heatmap.png", dpi=150, bbox_inches='tight')
    plt.close()

    # ── Fig 4: FH key scatter plots ──
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fh_scatters = [
        ('interface_n_pairs', 'VH-VL '),
        ('vl_germline_identity', 'VL '),
        ('surf_n_patches', ''),
        ('immuno_n_high', 'MHC-II '),
    ]
    for i, (col, name) in enumerate(fh_scatters):
        ax = axes[i//2, i%2]
        valid = df_fh[[col, 'ada_first_pct']].dropna()
        if len(valid) < 5:
            ax.text(0.5, 0.5, f'{name}\nN/A (n<5)', ha='center', va='center', transform=ax.transAxes, fontsize=14)
            continue
        sns.regplot(x=col, y='ada_first_pct', data=valid, ax=ax,
                    scatter_kws={'alpha':0.55, 'color':'#0d9488', 's':50}, line_kws={'color':'#ef4444', 'lw':2})
        rho, p = stats.spearmanr(valid[col], valid['ada_first_pct'])
        ax.set_title(f'{name}\n\u03c1={rho:+.3f}, p={p:.4f}', fontsize=15, fontweight='bold')
        ax.set_xlabel(name, fontsize=13)
        ax.set_ylabel('ADA (%)', fontsize=13)
    fig.suptitle(' 4:  (FH)  —  ADA ', fontsize=18, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(IMG_DIR / "fig4_scatter_key_features.png", dpi=150, bbox_inches='tight')
    plt.close()

    # ── Fig 5: HU key scatter plots ──
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    hu_scatters = [
        ('agg_motifs', ''),
        ('vh_germline_identity', 'VH '),
        ('instability_index', ''),
        ('immuno_tcia_score', 'TCIA '),
    ]
    for i, (col, name) in enumerate(hu_scatters):
        ax = axes[i//2, i%2]
        valid = df_hu[[col, 'ada_first_pct']].dropna()
        if len(valid) < 5:
            ax.text(0.5, 0.5, f'{name}\nN/A (n<5)', ha='center', va='center', transform=ax.transAxes, fontsize=14)
            continue
        sns.regplot(x=col, y='ada_first_pct', data=valid, ax=ax,
                    scatter_kws={'alpha':0.55, 'color':'#1d4ed8', 's':50}, line_kws={'color':'#ef4444', 'lw':2})
        rho, p = stats.spearmanr(valid[col], valid['ada_first_pct'])
        ax.set_title(f'{name}\n\u03c1={rho:+.3f}, p={p:.4f}', fontsize=15, fontweight='bold')
        ax.set_xlabel(name, fontsize=13)
        ax.set_ylabel('ADA (%)', fontsize=13)
    fig.suptitle(' 5:  (HU)  —  ADA ', fontsize=18, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(IMG_DIR / "fig5_hu_scatter.png", dpi=150, bbox_inches='tight')
    plt.close()

    # ── Fig 6: CMC vs ADA (full panel) ──
    fig, axes = plt.subplots(1, 4, figsize=(22, 6))
    cmc_feats = [
        ('agg_motifs', ''),
        ('deamidation_sites', ''),
        ('isomerization_sites', ''),
        ('charge_patch_max7', '')
    ]
    for i, (col, name) in enumerate(cmc_feats):
        ax = axes[i]
        valid = df[[col, 'ada_first_pct']].dropna()
        if len(valid) < 5:
            continue
        sns.regplot(x=col, y='ada_first_pct', data=valid, ax=ax,
                    scatter_kws={'alpha':0.5, 'color':'#0d9488', 's':40}, line_kws={'color':'#ef4444', 'lw':2})
        rho, p = stats.spearmanr(valid[col], valid['ada_first_pct'])
        ax.set_title(f'{name}\n\u03c1={rho:+.3f}, p={p:.4f}', fontsize=14, fontweight='bold')
        ax.set_xlabel(name, fontsize=13)
        ax.set_ylabel('ADA (%)', fontsize=13)
    fig.suptitle(' 6: CMC  ADA （）', fontsize=18, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.90])
    plt.savefig(IMG_DIR / "fig8_cmc_vs_ada.png", dpi=150, bbox_inches='tight')
    plt.close()

    # ── Fig 7: FH composite ADA V2 score vs ADA ──
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, sub, color, title in [
        (axes[0], df_fh, "#0d9488", " (FH)"),
        (axes[1], df_hu, "#1d4ed8", " (HU)"),
    ]:
        valid = sub[['ada_v2_score', 'ada_first_pct']].dropna()
        if len(valid) < 5:
            ax.text(0.5, 0.5, f'{title}: N/A', ha='center', va='center', transform=ax.transAxes)
            continue
        sns.regplot(x='ada_v2_score', y='ada_first_pct', data=valid, ax=ax,
                    scatter_kws={'alpha':0.55, 'color':color, 's':55}, line_kws={'color':'#ef4444', 'lw':2})
        rho, p = stats.spearmanr(valid['ada_v2_score'], valid['ada_first_pct'])
        ax.set_title(f'{title}\n\u03c1={rho:+.3f}, p={p:.4f}', fontsize=16, fontweight='bold')
        ax.set_xlabel('ADA V2 ', fontsize=14)
        ax.set_ylabel('ADA (%)', fontsize=14)
    fig.suptitle(' 7: ADA V2  ADA — FH vs HU', fontsize=18, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.90])
    plt.savefig(IMG_DIR / "fig7_ada_v2_composite.png", dpi=150, bbox_inches='tight')
    plt.close()


def main():
    print("Loading data...")
    df = load_data()
    print(f"  Loaded {len(df)} antibodies")

    # 1. Classify assay and origin
    df["assay_category"] = df.apply(classify_assay, axis=1)
    df["origin_class"] = "Other"
    df.loc[df["origin"] == "engineered", "origin_class"] = "HU"
    df.loc[df["origin"] == "natural", "origin_class"] = "FH"
    print(f"  Origin: HU={sum(df['origin_class']=='HU')}, FH={sum(df['origin_class']=='FH')}")

    # 2. Filter for High Sensitivity Assays for ADA V2
    df_high_sens = df[df["assay_category"].isin(["ECL (2nd-gen)", "Tiered / Drug-tolerant"])]
    print(f"  High sensitivity subset: n={len(df_high_sens)}")

    # 3. Generate plots with larger fonts
    generate_plots(df)

    all_results = []

    # ── 1. Full panel correlations (replication of previous) ──
    print("\n=== Full Panel (all assays pooled) ===")
    full_res = compute_correlations(df, "Full panel")
    all_results.extend(full_res)
    sig = [r for r in full_res if r["significant"]]
    print(f"  Significant: {len(sig)} / {len(full_res)}")

    # ── 1b. ADA V2 - High Sensitivity ONLY ──
    print("\n=== ADA V2 (High Sensitivity Assays ONLY) ===")
    v2_res = compute_correlations(df_high_sens, "ADA V2 (High-Sens)")
    all_results.extend(v2_res)
    sig_v2 = [r for r in v2_res if r["significant"]]
    print(f"  Significant: {len(sig_v2)} / {len(v2_res)}")

    # ── 1c. ADA V2 - High Sensitivity × FH ──
    df_hs_fh = df_high_sens[df_high_sens["origin_class"] == "FH"]
    print(f"\n=== ADA V2 (High-Sens × FH, n={len(df_hs_fh)}) ===")
    v2_fh_res = compute_correlations(df_hs_fh, "ADA V2 (High-Sens × FH)")
    all_results.extend(v2_fh_res)
    sig_v2_fh = [r for r in v2_fh_res if r["significant"]]
    print(f"  Significant: {len(sig_v2_fh)} / {len(v2_fh_res)}")

    # ── 1d. ADA V2 - High Sensitivity × HU ──
    df_hs_hu = df_high_sens[df_high_sens["origin_class"] == "HU"]
    print(f"\n=== ADA V2 (High-Sens × HU, n={len(df_hs_hu)}) ===")
    v2_hu_res = compute_correlations(df_hs_hu, "ADA V2 (High-Sens × HU)")
    all_results.extend(v2_hu_res)
    sig_v2_hu = [r for r in v2_hu_res if r["significant"]]
    print(f"  Significant: {len(sig_v2_hu)} / {len(v2_hu_res)}")

    # ── 2. By origin (HU / FH) — pooled across assays ──
    for origin_label in ["HU", "FH"]:
        sub = df[df["origin_class"] == origin_label]
        label = f"{'Humanized (HU)' if origin_label == 'HU' else 'Fully Human (FH)'}"
        print(f"\n=== {label} (n={len(sub)}) ===")
        res = compute_correlations(sub, label)
        all_results.extend(res)
        sig = [r for r in res if r["significant"]]
        print(f"  Significant: {len(sig)} / {len(res)}")

    # ── 3. By ASSAY category (key new analysis) ──
    for cat in sorted(df["assay_category"].unique()):
        sub = df[df["assay_category"] == cat]
        if len(sub["ada_first_pct"].dropna()) < 15:
            print(f"\n=== {cat} (n={len(sub)}) — SKIPPED (too few) ===")
            continue
        print(f"\n=== Assay: {cat} (n={len(sub)}) ===")
        res = compute_correlations(sub, f"Assay: {cat}")
        all_results.extend(res)
        sig = [r for r in res if r["significant"]]
        print(f"  Significant: {len(sig)} / {len(res)}")

    # ── 4. By ASSAY × ORIGIN (most rigorous) ──
    for cat in sorted(df["assay_category"].unique()):
        for origin_label in ["HU", "FH"]:
            sub = df[(df["assay_category"] == cat) & (df["origin_class"] == origin_label)]
            if len(sub["ada_first_pct"].dropna()) < 12:
                continue
            label = f"Assay: {cat} × {origin_label}"
            print(f"\n=== {label} (n={len(sub)}) ===")
            res = compute_correlations(sub, label)
            all_results.extend(res)
            sig = [r for r in res if r["significant"]]
            print(f"  Significant: {len(sig)} / {len(res)}")

    # ── 5. Kruskal-Wallis: ADA across assay categories ──
    kw_stat, kw_p, kw_labels = kruskal_wallis_assay_test(df)
    print(f"\nKruskal-Wallis ADA by assay: H={kw_stat}, p={kw_p}")

    # ── 6. Pairwise MW-U between assay categories ──
    pairwise_mw = []
    cats = sorted(df["assay_category"].unique())
    for i in range(len(cats)):
        for j in range(i+1, len(cats)):
            a = df[df["assay_category"] == cats[i]]["ada_first_pct"].dropna()
            b = df[df["assay_category"] == cats[j]]["ada_first_pct"].dropna()
            if len(a) >= 5 and len(b) >= 5:
                u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
                pairwise_mw.append({
                    "group_a": cats[i], "n_a": len(a),
                    "group_b": cats[j], "n_b": len(b),
                    "U": round(u, 1), "p": round(p, 4),
                })

    # ── 7. Compare with previous ──
    comparisons = compare_with_previous(all_results)

    # ── 8. Assay summary tables ──
    assay_summary = assay_summary_table(df)
    origin_assay = origin_x_assay_summary(df)

    # ── Save JSON ──
    json_out = {
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "n_antibodies": len(df),
        "assay_distribution": df["assay_category"].value_counts().to_dict(),
        "kruskal_wallis": {"H": kw_stat, "p": kw_p, "groups": kw_labels},
        "pairwise_mannwhitney": pairwise_mw,
        "all_correlations": all_results,
        "comparison_with_previous": comparisons,
    }
    JSON_FILE.write_text(json.dumps(json_out, indent=2, ensure_ascii=False, default=str))
    print(f"\nJSON saved: {JSON_FILE}")

    # ── Generate Report ──
    generate_report(df, all_results, comparisons, assay_summary,
                    origin_assay, kw_stat, kw_p, pairwise_mw)
    print(f"Report saved: {OUT_FILE}")


def generate_report(df, all_results, comparisons, assay_summary,
                    origin_assay, kw_stat, kw_p, pairwise_mw):
    lines = []
    w = lines.append

    w("# ADA ：")
    w("")
    w(f"****: {datetime.now().strftime('%Y-%m-%d')}")
    w(f"****: InSynBio ADA Master Database (`ada_master_136_curated.csv`, n={len(df)})")
    w("****:  ADA ，/ ADA ")
    w("****: Spearman  ×  ×  × ")
    w("")
    w("---")
    w("")

    # Section 0: ADA V2 High Sensitivity Results
    w("## 0. ADA V2： (ECL/Tiered) ")
    w("")
    w("， ADA V2 ****（ECL 2nd-gen  Tiered / Drug-tolerant），")
    w(" ELISA 。")
    w("")
    
    v2_results = [r for r in all_results if r["stratum"] == "ADA V2 (High-Sens)"]
    sig_v2 = sorted([r for r in v2_results if r["significant"]], key=lambda x: abs(x["rho"]), reverse=True)
    
    if sig_v2:
        w("####  (n=116)")
        w("")
        w("| Feature | ρ | p-value | n |  |")
        w("|---------|---|---------|---|------|")
        for r in sig_v2:
            direction = "↑ " if r["rho"] > 0 else "↓ "
            w(f"| {r['feature_name']} | {r['rho']:+.4f} | {r['p_value']:.4f} | {r['n']} | {direction} |")
        w("")
    
    v2_fh_results = [r for r in all_results if r["stratum"] == "ADA V2 (High-Sens × FH)"]
    sig_v2_fh = sorted([r for r in v2_fh_results if r["significant"]], key=lambda x: abs(x["rho"]), reverse=True)
    
    if sig_v2_fh:
        w("####  (n=48)")
        w("")
        w("| Feature | ρ | p-value | n |  |")
        w("|---------|---|---------|---|------|")
        for r in sig_v2_fh:
            direction = "↑ " if r["rho"] > 0 else "↓ "
            w(f"| {r['feature_name']} | {r['rho']:+.4f} | {r['p_value']:.4f} | {r['n']} | {direction} |")
        w("")
    
    w("****：，（ MHC-II 、）。")
    w("")

    # Section 1: Why assay stratification matters
    w("## 1. ：")
    w("")
    w("ADA  20 ，，")
    w(" ADA ****：")
    w("")
    w("|  |  |  |  |  |")
    w("|----------|--------|------------|------|--------|")
    w("| ELISA (1st-gen) |  |  | 2002–2010 | ， |")
    w("| ECL (2nd-gen) | - |  | 2010–2018 |  |")
    w("| Tiered / Drug-tolerant |  |  | 2015–present | /， |")
    w("")
    w("****：2015  Drug-tolerant ， ADA ")
    w(" ELISA ****，。")
    w("")

    # Section 2: Dataset by assay
    w("## 2. ")
    w("")
    w("|  |  |  ADA  | Mean ADA (%) | Median ADA (%) | SD | Range |")
    w("|----------|--------|------------|-------------|----------------|-----|-------|")
    for _, row in assay_summary.iterrows():
        w(f"| {row['Assay Category']} | {row['n']} | {row['n_ada']} | "
          f"{row['Mean ADA (%)']} | {row['Median ADA (%)']} | {row['SD']} | {row['Range']} |")
    w("")

    if kw_stat is not None:
        w(f"**Kruskal-Wallis **: H={kw_stat:.2f}, p={kw_p:.4f} "
          f"{'()' if kw_p < 0.05 else '()'}")
        w("")

    if pairwise_mw:
        w("** (Mann-Whitney U)**:")
        w("")
        w("|  A | n_A |  B | n_B | U | p |")
        w("|------|-----|------|-----|---|---|")
        for pw in pairwise_mw:
            sig_mark = " *" if pw["p"] < 0.05 else ""
            w(f"| {pw['group_a']} | {pw['n_a']} | {pw['group_b']} | {pw['n_b']} | "
              f"{pw['U']} | {pw['p']}{sig_mark} |")
        w("")

    # Section 3: Origin × Assay
    if len(origin_assay) > 0:
        w("## 3.  × ")
        w("")
        w("| Origin | Assay | n | Mean ADA (%) | Median ADA (%) |")
        w("|--------|-------|---|-------------|----------------|")
        for _, row in origin_assay.iterrows():
            w(f"| {row['Origin']} | {row['Assay']} | {row['n']} | "
              f"{row['Mean ADA (%)']} | {row['Median ADA (%)']} |")
        w("")

    # Section 4: Correlation results by stratum
    w("## 4.  Spearman ")
    w("")

    strata_order = ["Full panel", "Humanized (HU)", "Fully Human (FH)"]
    assay_strata = sorted(set(r["stratum"] for r in all_results if r["stratum"].startswith("Assay:")))
    strata_order.extend(assay_strata)

    for stratum in strata_order:
        s_results = [r for r in all_results if r["stratum"] == stratum]
        if not s_results:
            continue

        sig_results = sorted([r for r in s_results if r["significant"]],
                             key=lambda x: abs(x["rho"]), reverse=True)
        nonsig_top = sorted([r for r in s_results if not r["significant"]],
                            key=lambda x: abs(x["rho"]), reverse=True)[:5]

        w(f"### {stratum}")
        w("")
        if sig_results:
            w(f"** (p < 0.05): {len(sig_results)} **")
            w("")
            w("| Feature | ρ | p-value | n |  |")
            w("|---------|---|---------|---|------|")
            for r in sig_results:
                direction = "↑ " if r["rho"] > 0 else "↓ "
                w(f"| {r['feature_name']} | {r['rho']:+.4f} | {r['p_value']:.4f} | {r['n']} | {direction} |")
            w("")
        else:
            w("** (p < 0.05)**")
            w("")

        if nonsig_top:
            w(f"Top 5  (|ρ| ):")
            w("")
            w("| Feature | ρ | p-value | n |")
            w("|---------|---|---------|---|")
            for r in nonsig_top:
                w(f"| {r['feature_name']} | {r['rho']:+.4f} | {r['p_value']:.4f} | {r['n']} |")
            w("")

    # Section 5: Comparison with previous
    w("## 5. ")
    w("")
    w("：`ADA_138_MetaAnalysis_Paper_EN.md` (2026-04-04, Version 2.0)")
    w("")
    if comparisons:
        w("|  | Feature |  ρ |  p |  ρ |  p | n |  |  |")
        w("|---|---------|--------|--------|--------|--------|---|---------|--------|")
        for c in comparisons:
            feat_name = dict(FEATURES).get(c["feature"], c["feature"])
            dir_mark = "✅" if c["direction_consistent"] else "❌"
            sig_mark = "✅" if c["still_significant"] else "❌"
            w(f"| {c['stratum']} | {feat_name} | {c['prev_rho']:+.3f} | {c['prev_p']:.3f} | "
              f"{c['new_rho']:+.4f} | {c['new_p']:.4f} | {c['new_n']} | {dir_mark} | {sig_mark} |")
        w("")

        n_consistent = sum(1 for c in comparisons if c["direction_consistent"])
        n_still_sig = sum(1 for c in comparisons if c["still_significant"])
        w(f"****: {n_consistent}/{len(comparisons)} ，"
          f"{n_still_sig}/{len(comparisons)} 。")
    w("")

    # Section 6: Key conclusions
    w("## 6. ")
    w("")
    w("### 6.1  ADA ")
    w("")
    w(" ADA 。，")
    w("，。")
    w("")
    w("### 6.2 ")
    w("")
    w("， ADA ？")
    w(" 5 。，。")
    w("")
    w("### 6.3 ")
    w("")
    w("1. ** ADA **，")
    w("2. **ECL (2nd-gen)** 、，")
    w("3. ****-ADA （、VL ）")
    w("4. **** ADA ，")
    w("5. ****（、）")
    w("")
    w("---")
    w("")
    w(f"*: `scripts/ada_clinical_assay_stratified_analysis.py`*")
    w(f"*: `ada_master_136_curated.csv` (n={len(df)})*")
    w(f"*: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    OUT_FILE.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
