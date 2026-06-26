"""
scripts/rescore_ada.py
──────────────────────
Re-apply ADAScorer to an existing mhcii_immuno_70_summary.csv
without re-calling the IEDB API.

Usage
-----
    python scripts/rescore_ada.py [--summary PATH] [--out PATH]

The script reads the raw metrics (net_immunogenic_burden, n_clusters,
n_strong_binders, frac_exposed_vh, frac_exposed_vl) from the CSV and
re-computes clinical_ada_score + clinical_ada_risk with the current
ADAScorer parameters (default or calibrated).

It also re-runs calibration if ≥5 known-ADA antibodies are present.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

_SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SUITE))

from core.immunogenicity.ada_risk_scorer import ADAScorer


def rescore(summary_path: Path, out_path: Path) -> None:
    df = pd.read_csv(summary_path, comment="#")
    scorer = ADAScorer()
    print(scorer.params_summary())

    new_rows = []
    for _, row in df.iterrows():
        mhc = {
            "net_immunogenic_burden": row.get("net_immunogenic_burden", 0.0),
            "n_clusters":             row.get("n_clusters", 0),
            "n_strong_binders":       row.get("n_strong_binders", 0),
        }
        surf = {
            "frac_exposed_vh":  row.get("frac_exposed_vh"),
            "frac_exposed_vl":  row.get("frac_exposed_vl"),
            "n_hydrophilic_patches": row.get("n_hydrophilic_patches", 0),
            "surface_risk":     row.get("surface_risk", "—"),
        }
        ada = scorer.score(mhc, surf)
        r = row.to_dict()
        r["clinical_ada_score"] = ada["clinical_ada_score"]
        r["clinical_ada_risk"]  = ada["clinical_ada_risk"]
        comp = ada["components"]
        r["score_B_mhcii"]   = comp["B_mhcii_burden"]
        r["score_S_surface"]  = comp["S_surface_exp"]
        r["score_C_clusters"] = comp["C_clusters"]
        r["score_N_binders"]  = comp["N_binders"]
        new_rows.append(r)

    out_df = pd.DataFrame(new_rows)
    out_df.to_csv(out_path, index=False)
    print(f"\nRescored {len(out_df)} antibodies → {out_path}")

    # Distribution
    rc = out_df["clinical_ada_risk"].value_counts()
    for tier in ["HIGH", "MEDIUM", "LOW", "SKIPPED", "ERROR"]:
        if tier in rc:
            print(f"  {tier:8s}: {rc[tier]:3d}")

    valid = out_df[out_df["clinical_ada_score"].notna()][["antibody","clinical_ada_score"]]
    if len(valid) >= 5:
        result = scorer.calibrate(valid, save=True)
        if result:
            print(f"\nCalibration ({result.get('n_antibodies',0)} matched):")
            print(f"  Balanced accuracy: {result.get('balanced_accuracy')}")
            print(f"  Spearman r: {result.get('spearman_r')}")
            print(f"  Thresholds: HIGH≥{result.get('optimal_threshold_high')}, "
                  f"MEDIUM≥{result.get('optimal_threshold_medium')}")

            # Apply calibrated thresholds and save again
            scorer2 = ADAScorer()
            print("\nRescoring with calibrated thresholds...")
            cal_rows = []
            for _, row in out_df.iterrows():
                mhc = {"net_immunogenic_burden": row.get("net_immunogenic_burden",0.0),
                       "n_clusters": row.get("n_clusters",0),
                       "n_strong_binders": row.get("n_strong_binders",0)}
                surf = {"frac_exposed_vh": row.get("frac_exposed_vh"),
                        "frac_exposed_vl": row.get("frac_exposed_vl"),
                        "n_hydrophilic_patches": row.get("n_hydrophilic_patches",0),
                        "surface_risk": row.get("surface_risk","—")}
                ada2 = scorer2.score(mhc, surf)
                r2 = row.to_dict()
                r2["clinical_ada_score"] = ada2["clinical_ada_score"]
                r2["clinical_ada_risk"]  = ada2["clinical_ada_risk"]
                cal_rows.append(r2)
            cal_df = pd.DataFrame(cal_rows)
            cal_path = out_path.parent / out_path.name.replace(".csv", "_calibrated.csv")
            cal_df.to_csv(cal_path, index=False)
            print(f"Calibrated scores → {cal_path}")
            rc2 = cal_df["clinical_ada_risk"].value_counts()
            for tier in ["HIGH", "MEDIUM", "LOW"]:
                if tier in rc2:
                    print(f"  {tier:8s}: {rc2[tier]:3d}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", default=None, help="Path to summary CSV")
    parser.add_argument("--out", default=None, help="Output CSV path")
    args = parser.parse_args()

    default_dir = _SUITE / "data" / "thera_sabdab" / "out"
    summary = Path(args.summary) if args.summary else default_dir / "mhcii_immuno_70_summary.csv"
    out     = Path(args.out) if args.out else default_dir / "mhcii_immuno_70_summary_rescored.csv"

    if not summary.exists():
        print(f"Summary CSV not found: {summary}")
        sys.exit(1)

    rescore(summary, out)


if __name__ == "__main__":
    main()
