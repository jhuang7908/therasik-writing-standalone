#!/usr/bin/env python3
"""ADA correlation test for locally available AbLang sequence naturalness.

This uses the registered AbLang 0.3.1 API in the affmat environment:
    ablang.pretrained("heavy" / "light")(seqs, mode="likelihood")

The score matches existing local code practice: mean likelihood tensor value per
chain, then length-weighted VH/VL mean for paired Fv records.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import LabelEncoder

REPO = Path(__file__).resolve().parents[1]
MASTER_CSV = REPO / "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
OUT_DIR = REPO / "data/immunogenicity_knowledge_base/reports/ada_naturalness_extension"
BAD_VALUES = {"", "nan", "none", "true", "false", "0", "115"}


def is_real_seq(value: object) -> bool:
    return isinstance(value, str) and len(value.strip()) > 10 and value.strip().lower() not in BAD_VALUES


def clean_sequence(seq: object, chain: str) -> str:
    if not is_real_seq(seq):
        return ""
    text = re.sub(r"[^A-Za-z]", "", str(seq)).upper()
    if chain == "H":
        for motif in ("ASTKGPSVF", "TVSSASTK", "RTVAAPSVF"):
            idx = text.find(motif)
            if idx > 90:
                return text[:idx]
    else:
        for motif in ("RTVAAPSVF", "TVAAPSVF", "FGQGTKVEIKRTV"):
            idx = text.find(motif)
            if idx > 85:
                return text[:idx]
    return text


def normalize_class(value: object) -> str:
    if not isinstance(value, str):
        return "Unknown"
    text = value.strip().lower()
    if text in {"fully_human", "genetically_human", "fully human"}:
        return "Fully_human"
    if "humanis" in text or "humaniz" in text:
        return "Humanized"
    if "chimeric" in text:
        return "Chimeric"
    if text == "murine":
        return "Murine"
    if text == "vhh" or "nanobody" in text:
        return "VHH"
    if "bispecific" in text:
        return "Bispecific"
    return "Other"


def spearman(x: pd.Series, y: pd.Series) -> dict[str, Any]:
    mask = x.notna() & y.notna()
    x = x[mask]
    y = y[mask]
    if len(x) < 8 or x.nunique() < 3 or y.nunique() < 3:
        return {"n": int(len(x)), "rho": None, "p": None}
    rho, p = stats.spearmanr(x, y)
    return {"n": int(len(x)), "rho": round(float(rho), 4), "p": round(float(p), 6)}


def partial_spearman(feat: pd.Series, target: pd.Series, confounders: list[pd.Series]) -> dict[str, Any]:
    mask = feat.notna() & target.notna()
    for conf in confounders:
        mask &= conf.notna()
    if int(mask.sum()) < 12:
        return {"n": int(mask.sum()), "partial_rho": None, "p": None}

    f = feat[mask].rank().to_numpy()
    t = target[mask].rank().to_numpy()
    c = np.column_stack([conf[mask].rank().to_numpy() for conf in confounders])

    def resid(y: np.ndarray) -> np.ndarray:
        x = np.column_stack([np.ones(len(c)), c])
        beta = np.linalg.lstsq(x, y, rcond=None)[0]
        return y - x @ beta

    r, p = stats.pearsonr(resid(f), resid(t))
    return {"n": int(mask.sum()), "partial_rho": round(float(r), 4), "p": round(float(p), 6)}


def score_batch(model: Any, seqs: list[str], batch_size: int) -> list[float | None]:
    scores: list[float | None] = []
    for start in range(0, len(seqs), batch_size):
        batch = seqs[start : start + batch_size]
        arr = model(batch, mode="likelihood")
        for item in arr:
            scores.append(round(float(np.asarray(item).mean()), 4))
    return scores


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=MASTER_CSV)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    import ablang  # type: ignore

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.csv)
    target = df[df["ada_first_pct"].notna() & df[["vh_seq", "vl_seq"]].notna().any(axis=1)].copy()
    target["source_class"] = target["thera_genetics_class"].apply(normalize_class)
    target["ada_log10_pct_plus_0p1"] = np.log10(target["ada_first_pct"].astype(float) + 0.1)
    target["vh_clean"] = target["vh_seq"].apply(lambda x: clean_sequence(x, "H"))
    target["vl_clean"] = target["vl_seq"].apply(lambda x: clean_sequence(x, "L"))

    print(f"Scoring AbLang legacy naturalness for {len(target)} records...")
    heavy_model = ablang.pretrained("heavy")
    light_model = ablang.pretrained("light")

    vh_nonempty = target["vh_clean"].astype(bool)
    vl_nonempty = target["vl_clean"].astype(bool)
    vh_scores = pd.Series(np.nan, index=target.index, dtype="float64")
    vl_scores = pd.Series(np.nan, index=target.index, dtype="float64")

    if vh_nonempty.any():
        vh_values = target.loc[vh_nonempty, "vh_clean"].tolist()
        vh_scores.loc[vh_nonempty] = score_batch(heavy_model, vh_values, args.batch_size)
        print(f"  scored VH: {vh_nonempty.sum()}")
    if vl_nonempty.any():
        vl_values = target.loc[vl_nonempty, "vl_clean"].tolist()
        vl_scores.loc[vl_nonempty] = score_batch(light_model, vl_values, args.batch_size)
        print(f"  scored VL: {vl_nonempty.sum()}")

    target["ablang_legacy_vh_score"] = vh_scores
    target["ablang_legacy_vl_score"] = vl_scores
    target["ablang_legacy_pair_mean"] = target[["ablang_legacy_vh_score", "ablang_legacy_vl_score"]].mean(axis=1)

    out_cols = [
        "antibody_name",
        "ada_first_pct",
        "ada_log10_pct_plus_0p1",
        "source_class",
        "thera_genetics_class",
        "hpr_combined_score",
        "vh_clean",
        "vl_clean",
        "ablang_legacy_vh_score",
        "ablang_legacy_vl_score",
        "ablang_legacy_pair_mean",
    ]
    out_csv = out_dir / "ada_ablang_legacy_scores.csv"
    target[out_cols].to_csv(out_csv, index=False)

    target["source_class_code"] = LabelEncoder().fit_transform(target["source_class"].fillna("Unknown"))
    target["hpr_combined_score"] = pd.to_numeric(target["hpr_combined_score"], errors="coerce")

    features = {
        "ablang_legacy_vh_score": "AbLang legacy VH likelihood mean",
        "ablang_legacy_vl_score": "AbLang legacy VL likelihood mean",
        "ablang_legacy_pair_mean": "AbLang legacy paired mean",
    }
    summary: dict[str, Any] = {
        "n_records": int(len(target)),
        "method": "ablang 0.3.1 likelihood tensor mean; higher is locally treated as more natural",
        "coverage": {},
        "spearman_vs_ada_log10": {},
        "spearman_vs_hpr": {},
        "partial_vs_ada_log10_control_hpr_source": {},
        "source_stratified_pair_mean_vs_ada": {},
    }
    y = target["ada_log10_pct_plus_0p1"]
    conf = [target["hpr_combined_score"], target["source_class_code"].astype(float)]

    for feat, label in features.items():
        summary["coverage"][feat] = int(target[feat].notna().sum())
        s = spearman(target[feat], y)
        s["label"] = label
        summary["spearman_vs_ada_log10"][feat] = s
        h = spearman(target[feat], target["hpr_combined_score"])
        h["label"] = label
        summary["spearman_vs_hpr"][feat] = h
        p = partial_spearman(target[feat], y, conf)
        p["label"] = label
        summary["partial_vs_ada_log10_control_hpr_source"][feat] = p

    for source_class, group in target.groupby("source_class"):
        res = spearman(group["ablang_legacy_pair_mean"], group["ada_log10_pct_plus_0p1"])
        summary["source_stratified_pair_mean_vs_ada"][source_class] = res

    out_json = out_dir / "ada_ablang_legacy_correlation_summary.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nSpearman vs ADA log10:")
    for feat, res in summary["spearman_vs_ada_log10"].items():
        print(f"  {feat:30s} n={res['n']:3d} rho={res['rho']:+.4f} p={res['p']:.2e}")
    print("\nPartial Spearman vs ADA log10 (control HPR + source_class):")
    for feat, res in summary["partial_vs_ada_log10_control_hpr_source"].items():
        print(f"  {feat:30s} n={res['n']:3d} partial_rho={res['partial_rho']:+.4f} p={res['p']:.2e}")
    print("\nSpearman vs HPR:")
    for feat, res in summary["spearman_vs_hpr"].items():
        print(f"  {feat:30s} n={res['n']:3d} rho={res['rho']:+.4f} p={res['p']:.2e}")
    print(f"\nSaved scores: {out_csv}")
    print(f"Saved summary: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
