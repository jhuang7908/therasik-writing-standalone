#!/usr/bin/env python3
"""
Build an analysis-ready library linking germline assignments to first-reported ADA % for the confirmed-70 panel.

Inputs:
  data/thera_sabdab/out/confirmed70_human_humanized_germline_ada.csv
  (includes naive-blood V-gene population usage priors from analyze_70)

Outputs (directory created automatically):
  data/thera_sabdab/out/germline_ada_panel/
    confirmed70_germline_ada_analytic.csv   — 70 rows + numeric coercion + optional ADA imputation
    germline_ada_feature_correlations.csv   — Spearman rho vs ada_first_pct (pairwise complete)
    germline_ada_by_vh_family.csv           — median/mean ADA and n per IGHV family (n>=3 only in summary text)
    germline_ada_by_vl_family.csv           — same for light-chain family
    germline_ada_correlation_summary.txt    — human-readable caveats + key numbers

Use:
  Exploratory assessment of germline–ADA association only. ADA varies by indication, assay, and regimen;
  n=70 is underpowered for causal claims; use stratification (e.g. thera_genetics_class) in follow-ups.

Run:
  python scripts/build_germline_ada_correlation_library.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy import stats
except ImportError as e:
    raise SystemExit("Requires scipy: pip install scipy") from e

SUITE = Path(__file__).resolve().parents[1]
SRC = SUITE / "data/thera_sabdab/out/confirmed70_human_humanized_germline_ada.csv"
OUT_DIR = SUITE / "data/thera_sabdab/out/germline_ada_panel"

# Qualitative “no ADA detected” → 0% for sensitivity column only
_NO_ADA_PAT = re.compile(
    r"no\s+treatment-?emergent\s+anti-?drug\s+antibod",
    re.I,
)


def _to_float(s: object) -> float | None:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    if isinstance(s, (int, float)) and not isinstance(s, bool):
        return float(s)
    t = str(s).strip()
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def main() -> int:
    if not SRC.is_file():
        print(f"Missing source: {SRC}", file=sys.stderr)
        return 1

    df = pd.read_csv(SRC)
    n0 = len(df)
    if n0 != 70:
        print(f"Warning: expected 70 rows, got {n0}", file=sys.stderr)

    out = df.copy()
    out["ada_first_pct"] = pd.to_numeric(out["ada_first_pct"], errors="coerce")

    # Sensitivity: impute 0 where text says no TEA-ADA and numeric missing
    out["ada_imputed_for_sensitivity"] = out["ada_first_pct"].copy()
    mask_qual = out["ada_first_pct"].isna() & out["ada_value_display"].astype(str).apply(
        lambda x: bool(_NO_ADA_PAT.search(x))
    )
    out.loc[mask_qual, "ada_imputed_for_sensitivity"] = 0.0
    out["ada_numeric_imputed_flag"] = mask_qual.astype(int)

    id_cols = [
        "vh_identity_842",
        "vl_identity_842",
        "vh_identity_ogrdb",
        "vl_identity_ogrdb",
        "vh_identity_imgt",
        "vl_identity_imgt",
        "vh2_identity_ogrdb",
        "vl2_identity_ogrdb",
        "vh3_identity_ogrdb",
        "vh3_identity_imgt",
        "vh_pop_naive_usage_frac",
        "vh_pop_rarity_neglog10",
        "vl_pop_naive_usage_frac_global",
        "vl_pop_rarity_global_neglog10",
        "vh2_pop_naive_usage_frac",
        "vh2_pop_rarity_neglog10",
        "vl2_pop_naive_usage_frac_global",
        "vl2_pop_rarity_global_neglog10",
        "vh3_pop_naive_usage_frac",
        "vh3_pop_rarity_neglog10",
    ]
    for c in id_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    analytic_path = OUT_DIR / "confirmed70_germline_ada_analytic.csv"
    out.to_csv(analytic_path, index=False)

    y = out["ada_first_pct"]
    y_sens = out["ada_imputed_for_sensitivity"]

    numeric_features = [
        "vh_identity_ogrdb",
        "vl_identity_ogrdb",
        "vh_identity_imgt",
        "vl_identity_imgt",
        "heavy_seq_len",
        "light_seq_len",
        "vh3_seq_len",
        "vh_pop_naive_usage_frac",
        "vh_pop_rarity_neglog10",
        "vl_pop_naive_usage_frac_global",
        "vl_pop_rarity_global_neglog10",
        "vh2_pop_naive_usage_frac",
        "vh2_pop_rarity_neglog10",
        "vl2_pop_naive_usage_frac_global",
        "vl2_pop_rarity_global_neglog10",
        "vh3_pop_naive_usage_frac",
        "vh3_pop_rarity_neglog10",
    ]
    corr_rows = []
    for label, yy in (("ada_first_pct", y), ("ada_imputed_sensitivity", y_sens)):
        for feat in numeric_features:
            if feat not in out.columns:
                continue
            x = pd.to_numeric(out[feat], errors="coerce")
            m = yy.notna() & x.notna()
            if m.sum() < 5:
                continue
            xv = x[m]
            if xv.nunique() < 4:
                continue
            rho, p = stats.spearmanr(xv, yy[m])
            corr_rows.append(
                {
                    "outcome": label,
                    "feature": feat,
                    "n": int(m.sum()),
                    "spearman_rho": round(float(rho), 4),
                    "spearman_p": float(p) if p == p else None,
                }
            )

    pd.DataFrame(corr_rows).to_csv(OUT_DIR / "germline_ada_feature_correlations.csv", index=False)

    def family_table(fam_col: str, name: str) -> pd.DataFrame:
        sub = out[out["ada_first_pct"].notna() & out[fam_col].astype(str).str.strip().ne("")]
        g = sub.groupby(fam_col)["ada_first_pct"].agg(["count", "median", "mean", "std"]).reset_index()
        g = g.rename(columns={fam_col: "family", "count": "n"})
        g = g.sort_values("median")
        g.to_csv(OUT_DIR / name, index=False)
        return g

    g_vh = family_table("vh_family", "germline_ada_by_vh_family.csv")
    g_vl = family_table("vl_family", "germline_ada_by_vl_family.csv")

    # Kruskal–Wallis across VH families with n>=2 (global test; weak power)
    sub = out[out["ada_first_pct"].notna() & out["vh_family"].astype(str).str.strip().ne("")]
    vc = sub["vh_family"].value_counts()
    keep = vc[vc >= 2].index
    groups = [sub.loc[sub["vh_family"] == f, "ada_first_pct"].values for f in keep]
    groups = [g for g in groups if len(g) >= 2]
    kw_vh = stats.kruskal(*groups) if len(groups) >= 3 else None

    sub_l = out[out["ada_first_pct"].notna() & out["vl_family"].astype(str).str.strip().ne("")]
    vc_l = sub_l["vl_family"].value_counts()
    keep_l = vc_l[vc_l >= 2].index
    groups_l = [sub_l.loc[sub_l["vl_family"] == f, "ada_first_pct"].values for f in keep_l]
    groups_l = [g for g in groups_l if len(g) >= 2]
    kw_vl = stats.kruskal(*groups_l) if len(groups_l) >= 3 else None

    lines = [
        "Germline vs ADA (confirmed-70) — exploratory summary",
        "=" * 60,
        f"Source: {SRC.relative_to(SUITE)}",
        f"Rows: {len(out)}; ada_first_pct non-missing: {int(y.notna().sum())}",
        f"ADA imputed 0% (no TEA-ADA text only): {int(mask_qual.sum())} row(s)",
        "",
        "CAUTION: ADA is indication- and assay-dependent; n=70 is small.",
        "Correlations are hypothesis-generating, not causal.",
        "",
        "--- Spearman vs ada_first_pct (selected numeric features) ---",
    ]
    for _, r in pd.DataFrame(corr_rows).query("outcome == 'ada_first_pct'").iterrows():
        lines.append(f"  {r['feature']:22s}  n={int(r['n']):2d}  rho={r['spearman_rho']:+.3f}  p={r['spearman_p']}")

    lines += ["", "--- Kruskal–Wallis (ADA across families, ada_first_pct) ---"]
    if kw_vh is not None:
        lines.append(f"  VH family: H={kw_vh.statistic:.3f}, p={kw_vh.pvalue:.4g} ({len(groups)} families with n>=2)")
    else:
        lines.append("  VH family: insufficient multi-group structure for Kruskal–Wallis")
    if kw_vl is not None:
        lines.append(f"  VL family: H={kw_vl.statistic:.3f}, p={kw_vl.pvalue:.4g} ({len(groups_l)} families with n>=2)")
    else:
        lines.append("  VL family: insufficient multi-group structure for Kruskal–Wallis")

    lines += [
        "",
        f"VH families in panel: {g_vh['n'].sum():.0f} assigned rows; distinct families: {len(g_vh)}",
        f"VL families in panel: {g_vl['n'].sum():.0f} assigned rows; distinct families: {len(g_vl)}",
        "",
        "Outputs:",
        f"  {analytic_path.relative_to(SUITE)}",
        f"  {(OUT_DIR / 'germline_ada_feature_correlations.csv').relative_to(SUITE)}",
        f"  {(OUT_DIR / 'germline_ada_by_vh_family.csv').relative_to(SUITE)}",
        f"  {(OUT_DIR / 'germline_ada_by_vl_family.csv').relative_to(SUITE)}",
    ]

    summary_path = OUT_DIR / "germline_ada_correlation_summary.txt"
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
