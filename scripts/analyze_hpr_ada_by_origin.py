#!/usr/bin/env python3
"""Analyze HPR Index versus ADA incidence by antibody source class."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def _norm_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def classify_source(row: pd.Series) -> str:
    text = " ".join(
        _norm_text(row.get(col))
        for col in [
            "thera_genetics_class",
            "genetics_normalized",
            "origin",
            "modality",
            "format_type",
            "hpr_chain_mode",
        ]
    )
    name = _norm_text(row.get("antibody_name"))
    if "tebentafusp" in name or "immtac" in text or "tcr-scfv" in text:
        return "TCR-scFv / fusion"
    if "vhh" in text or "nanobody" in text or "single_domain" in text:
        return "VHH / single-domain"
    if "murine" in text:
        return "Murine"
    if "chimeric" in text:
        return "Chimeric"
    if "humanised" in text or "humanized" in text:
        return "Humanized"
    if "fully_human" in text or "genetically_human" in text or text.split().count("human") > 0:
        return "Fully human"
    return "Unspecified / other"


def corr_pair(x: pd.Series, y: pd.Series) -> dict[str, float | int | None]:
    valid = x.notna() & y.notna()
    x = x[valid].astype(float)
    y = y[valid].astype(float)
    n = int(len(x))
    out: dict[str, float | int | None] = {"n": n}
    if n < 3 or x.nunique() < 2 or y.nunique() < 2:
        out.update(
            {
                "spearman_rho": None,
                "spearman_p": None,
                "pearson_r": None,
                "pearson_p": None,
                "pearson_log10_ada_r": None,
                "pearson_log10_ada_p": None,
            }
        )
        return out

    spearman = stats.spearmanr(x, y)
    pearson = stats.pearsonr(x, y)
    log_ada = np.log10(y + 0.1)
    pearson_log = stats.pearsonr(x, log_ada)

    out.update(
        {
            "spearman_rho": round(float(spearman.statistic), 4),
            "spearman_p": round(float(spearman.pvalue), 6),
            "pearson_r": round(float(pearson.statistic), 4),
            "pearson_p": round(float(pearson.pvalue), 6),
            "pearson_log10_ada_r": round(float(pearson_log.statistic), 4),
            "pearson_log10_ada_p": round(float(pearson_log.pvalue), 6),
        }
    )
    return out


def summarize(group: pd.DataFrame, label: str) -> dict[str, object]:
    corr = corr_pair(group["hpr_combined_score"], group["ada_first_pct"])
    result: dict[str, object] = {
        "source_class": label,
        "n": corr["n"],
        "ada_median_pct": round(float(group["ada_first_pct"].median()), 4),
        "ada_mean_pct": round(float(group["ada_first_pct"].mean()), 4),
        "ada_q25_pct": round(float(group["ada_first_pct"].quantile(0.25)), 4),
        "ada_q75_pct": round(float(group["ada_first_pct"].quantile(0.75)), 4),
        "hpr_median": round(float(group["hpr_combined_score"].median()), 4),
        "hpr_mean": round(float(group["hpr_combined_score"].mean()), 4),
        "hpr_q25": round(float(group["hpr_combined_score"].quantile(0.25)), 4),
        "hpr_q75": round(float(group["hpr_combined_score"].quantile(0.75)), 4),
    }
    result.update({k: v for k, v in corr.items() if k != "n"})
    result["interpretation_flag"] = (
        "underpowered_n_lt_10" if int(corr["n"] or 0) < 10 else "interpretable_with_caution"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        default="data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv",
    )
    parser.add_argument(
        "--out-dir",
        default="data/immunogenicity_knowledge_base/reports/hpr_ada_origin_analysis",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    csv_path = (repo / args.csv).resolve()
    out_dir = (repo / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    numeric = df[["vh_seq", "vl_seq"]].notna().any(axis=1) & df["ada_first_pct"].notna()
    a = df[numeric & df["hpr_combined_score"].notna()].copy()
    a["source_class"] = a.apply(classify_source, axis=1)
    a["ada_log10_pct_plus_0p1"] = np.log10(a["ada_first_pct"].astype(float) + 0.1)

    summaries = [summarize(a, "All numeric ADA records")]
    for label, group in a.groupby("source_class"):
        summaries.append(summarize(group, label))
    summary_df = pd.DataFrame(summaries).sort_values(["source_class"])
    all_row = summary_df[summary_df["source_class"] == "All numeric ADA records"]
    rest = summary_df[summary_df["source_class"] != "All numeric ADA records"].sort_values(
        ["n", "source_class"], ascending=[False, True]
    )
    summary_df = pd.concat([all_row, rest], ignore_index=True)

    tertiles = a.copy()
    tertiles["hpr_tertile"] = pd.qcut(
        tertiles["hpr_combined_score"], q=3, labels=["low_hpr", "mid_hpr", "high_hpr"], duplicates="drop"
    )
    tertile_df = (
        tertiles.groupby(["source_class", "hpr_tertile"], observed=True)
        .agg(
            n=("antibody_name", "count"),
            ada_median_pct=("ada_first_pct", "median"),
            ada_mean_pct=("ada_first_pct", "mean"),
            hpr_median=("hpr_combined_score", "median"),
        )
        .reset_index()
    )

    records_cols = [
        "antibody_name",
        "source_class",
        "ada_first_pct",
        "hpr_combined_score",
        "hpr_vh_score",
        "hpr_vl_score",
        "hpr_chain_mode",
        "thera_genetics_class",
        "genetics_normalized",
        "origin",
        "modality",
        "target_unified",
        "indication_unified",
        "ada_source_type_curated",
    ]
    records = a[[c for c in records_cols if c in a.columns]].copy()

    summary_path = out_dir / "hpr_ada_correlation_by_source.csv"
    tertile_path = out_dir / "hpr_ada_by_hpr_tertile_and_source.csv"
    records_path = out_dir / "hpr_ada_records_with_source_class.csv"
    json_path = out_dir / "hpr_ada_correlation_by_source.json"

    summary_df.to_csv(summary_path, index=False)
    tertile_df.to_csv(tertile_path, index=False)
    records.to_csv(records_path, index=False)
    json_path.write_text(json.dumps(summary_df.to_dict(orient="records"), indent=2), encoding="utf-8")

    print(f"Analyzed records: {len(a)}")
    print(summary_df.to_string(index=False))
    print(f"Saved: {summary_path}")
    print(f"Saved: {tertile_path}")
    print(f"Saved: {records_path}")
    print(f"Saved: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
