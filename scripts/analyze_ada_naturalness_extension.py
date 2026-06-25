#!/usr/bin/env python3
"""ADA naturalness extension analysis using AbLang2 and p-AbNatiV2.

Outputs per-record naturalness scores and correlation summaries without
modifying the master ADA CSV.
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
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.cmc.igg_hpr_ablang import compute_igg_cmc_hpr_ablang
from core.humanization.p_abnativ_layer import score_paired_humanness
from core.vh2vhh.abnativ_naturalness_layer import score_naturalness_delta

MASTER_CSV = REPO / "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
OUT_DIR = REPO / "data/immunogenicity_knowledge_base/reports/ada_naturalness_extension"

BAD_VALUES = {"", "nan", "none", "true", "false", "0", "115"}


def is_real_seq(value: object) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return len(text) > 10 and text.lower() not in BAD_VALUES


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


def chain_mode(name: str, vh: str, vl: str) -> str:
    if name.casefold() == "tebentafusp":
        return "fusion_fragment_noncanonical"
    if vh and vl:
        return "VHVL"
    if vh and not vl:
        return "single_domain_or_single_fragment"
    if vl and not vh:
        return "single_light_fragment"
    return "not_computed"


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

    def residuals(y: np.ndarray) -> np.ndarray:
        x = np.column_stack([np.ones(len(c)), c])
        beta = np.linalg.lstsq(x, y, rcond=None)[0]
        return y - x @ beta

    r, p = stats.pearsonr(residuals(f), residuals(t))
    return {"n": int(mask.sum()), "partial_rho": round(float(r), 4), "p": round(float(p), 6)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=MASTER_CSV)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip-ablang2", action="store_true")
    parser.add_argument("--skip-pabnativ", action="store_true")
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.csv)
    target = df[df["ada_first_pct"].notna() & df[["vh_seq", "vl_seq"]].notna().any(axis=1)].copy()
    if args.limit:
        target = target.head(args.limit).copy()

    rows: list[dict[str, Any]] = []
    print(f"Scoring {len(target)} numeric ADA records with sequence...")

    for n, (_, row) in enumerate(target.iterrows(), start=1):
        name = str(row.get("antibody_name", ""))
        vh = clean_sequence(row.get("vh_seq"), "H")
        vl = clean_sequence(row.get("vl_seq"), "L")
        mode = chain_mode(name, vh, vl)

        rec: dict[str, Any] = {
            "antibody_name": name,
            "ada_first_pct": row.get("ada_first_pct"),
            "ada_log10_pct_plus_0p1": math.log10(float(row.get("ada_first_pct")) + 0.1),
            "source_class": normalize_class(row.get("thera_genetics_class")),
            "chain_mode": mode,
            "hpr_combined_score": row.get("hpr_combined_score"),
            "vh_len_clean": len(vh),
            "vl_len_clean": len(vl),
            "ablang2_paired_pll": pd.NA,
            "ablang2_error": pd.NA,
            "pabnativ_vh_humanness": pd.NA,
            "pabnativ_vl_humanness": pd.NA,
            "pabnativ_paired_humanness": pd.NA,
            "pabnativ_pairing_likelihood": pd.NA,
            "pabnativ_error": pd.NA,
            "pabnativ_warning": pd.NA,
            "vh_abnativ_vh_score": pd.NA,
            "vh_abnativ_vhh_score": pd.NA,
            "vh_abnativ_delta_vhh_minus_vh": pd.NA,
            "vh_abnativ_tier": pd.NA,
            "vh_abnativ_error": pd.NA,
        }

        if mode == "VHVL":
            if not args.skip_ablang2:
                abl = compute_igg_cmc_hpr_ablang(vh, vl)
                rec["ablang2_paired_pll"] = abl.get("ablang_score")
                rec["ablang2_error"] = abl.get("ablang_error")
            else:
                rec["ablang2_error"] = "skipped_by_cli"

            if not args.skip_pabnativ:
                pab = score_paired_humanness(vh, vl, seq_id=name or f"seq_{n}")
                rec["pabnativ_vh_humanness"] = pab.vh_humanness
                rec["pabnativ_vl_humanness"] = pab.vl_humanness
                rec["pabnativ_paired_humanness"] = pab.paired_humanness
                rec["pabnativ_pairing_likelihood"] = pab.pairing_likelihood
                rec["pabnativ_error"] = pab.error
                rec["pabnativ_warning"] = pab.warning
        elif vh:
            # Single-domain or single-fragment records: AbLang2 paired and p-AbNatiV2
            # are not applicable, but the VH/VHH AbNatiV delta layer is informative.
            sd = score_naturalness_delta(vh, seq_id=name or f"seq_{n}", verbose=False)
            rec["vh_abnativ_vh_score"] = sd.vh2_score
            rec["vh_abnativ_vhh_score"] = sd.vhh2_score
            rec["vh_abnativ_delta_vhh_minus_vh"] = sd.delta
            rec["vh_abnativ_tier"] = sd.tier
            rec["vh_abnativ_error"] = sd.error
            rec["ablang2_error"] = "not_applicable_non_paired_vhvl"
            rec["pabnativ_error"] = "not_applicable_non_paired_vhvl"
        else:
            rec["ablang2_error"] = "missing_vh"
            rec["pabnativ_error"] = "missing_vh"

        rows.append(rec)
        if n % 10 == 0 or n == len(target):
            print(f"Scored {n}/{len(target)}")

    scored = pd.DataFrame(rows)
    scored_path = out_dir / "ada_ablang2_pabnativ_scores.csv"
    scored.to_csv(scored_path, index=False)

    scored["source_class_code"] = LabelEncoder().fit_transform(scored["source_class"].fillna("Unknown"))
    scored["hpr_combined_score"] = pd.to_numeric(scored["hpr_combined_score"], errors="coerce")

    feature_labels = {
        "ablang2_paired_pll": "AbLang2 paired PLL",
        "pabnativ_vh_humanness": "p-AbNatiV2 VH humanness",
        "pabnativ_vl_humanness": "p-AbNatiV2 VL humanness",
        "pabnativ_paired_humanness": "p-AbNatiV2 paired humanness",
        "pabnativ_pairing_likelihood": "p-AbNatiV2 pairing likelihood",
        "vh_abnativ_vh_score": "single-chain AbNatiV VH score",
        "vh_abnativ_vhh_score": "single-chain AbNatiV VHH score",
        "vh_abnativ_delta_vhh_minus_vh": "single-chain VHH-VH delta",
    }

    summary: dict[str, Any] = {
        "n_records": int(len(scored)),
        "coverage": {},
        "spearman_vs_ada_log10": {},
        "partial_vs_ada_log10_control_hpr_source": {},
        "spearman_vs_hpr": {},
    }

    target_y = scored["ada_log10_pct_plus_0p1"]
    confounders = [scored["hpr_combined_score"], scored["source_class_code"].astype(float)]
    for feat, label in feature_labels.items():
        scored[feat] = pd.to_numeric(scored[feat], errors="coerce")
        summary["coverage"][feat] = int(scored[feat].notna().sum())
        s = spearman(scored[feat], target_y)
        s["label"] = label
        summary["spearman_vs_ada_log10"][feat] = s
        p = partial_spearman(scored[feat], target_y, confounders)
        p["label"] = label
        summary["partial_vs_ada_log10_control_hpr_source"][feat] = p
        h = spearman(scored[feat], scored["hpr_combined_score"])
        h["label"] = label
        summary["spearman_vs_hpr"][feat] = h

    summary_path = out_dir / "ada_naturalness_correlation_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nCoverage:")
    for feat, n_cov in summary["coverage"].items():
        print(f"  {feat}: {n_cov}")

    print("\nSpearman vs ADA log10:")
    for feat, res in summary["spearman_vs_ada_log10"].items():
        if res["rho"] is None:
            continue
        print(f"  {feat:35s} n={res['n']:3d} rho={res['rho']:+.4f} p={res['p']:.2e}")

    print("\nPartial Spearman vs ADA log10 (control HPR + source_class):")
    for feat, res in summary["partial_vs_ada_log10_control_hpr_source"].items():
        if res["partial_rho"] is None:
            continue
        print(f"  {feat:35s} n={res['n']:3d} partial_rho={res['partial_rho']:+.4f} p={res['p']:.2e}")

    print(f"\nSaved scores: {scored_path}")
    print(f"Saved summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
