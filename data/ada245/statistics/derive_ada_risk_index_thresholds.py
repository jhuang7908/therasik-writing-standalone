#!/usr/bin/env python3
"""
Derive **candidate** index thresholds separating high vs low clinical ADA risk.

Label (default): high_risk = ada_first_pct >= --ada-threshold (default 10%).

Metrics (from ada_master CSV when present):
  - immuno_tcia_score
  - hpr_proxy_pct = (vh_identity_imgt + vl_identity_imgt) / 2 * 100  (IMGT display; NOT promb 9-mer HPR Index)

For each metric, the script infers whether **higher** or **lower** values associate with high ADA,
builds an internal risk score (higher = more likely high_risk), and reports ROC AUC + Youden J cutoff.

Output: JSON / optional markdown. **Exploratory** — freeze into config only after owner approval.

If the CSV has fewer than 245 rows, n is reported explicitly (current snapshot may be incomplete).
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

ADA245_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ADA245_ROOT / "database" / "ada_master_245_curated.csv"
NAT384 = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "natural_380_atlas"
    / "natural384_cmc_per_antibody.csv"
)


@dataclass
class MetricCut:
    metric: str
    n_valid: int
    n_high_risk: int
    n_low_risk: int
    orientation: str
    auc: float | None
    youden_threshold_raw: float | None
    sensitivity: float | None
    specificity: float | None
    median_high_risk: float | None
    median_low_risk: float | None
    rule_text: str
    note: str


def one_metric(
    name: str,
    raw: pd.Series,
    y: pd.Series,
) -> MetricCut:
    m = pd.to_numeric(raw, errors="coerce")
    ok = m.notna() & y.notna()
    m = m[ok].astype(float).values
    yy = y[ok].astype(int).values
    n_valid = len(yy)
    n_pos = int(yy.sum())
    n_neg = n_valid - n_pos

    med_pos = float(np.median(m[yy == 1])) if n_pos else None
    med_neg = float(np.median(m[yy == 0])) if n_neg else None

    if n_valid < 20 or n_pos < 5 or n_neg < 5:
        return MetricCut(
            metric=name,
            n_valid=n_valid,
            n_high_risk=n_pos,
            n_low_risk=n_neg,
            orientation="unknown",
            auc=None,
            youden_threshold_raw=None,
            sensitivity=None,
            specificity=None,
            median_high_risk=med_pos,
            median_low_risk=med_neg,
            rule_text="insufficient n for stable ROC (recommend n>=20, high>=5, low>=5)",
            note="",
        )

    higher_risk_if_high = med_pos >= med_neg
    s = m if higher_risk_if_high else -m
    orient = "higher_is_risk" if higher_risk_if_high else "lower_is_risk"

    try:
        auc = float(roc_auc_score(yy, s))
    except ValueError:
        auc = None

    fpr, tpr, thr = roc_curve(yy, s)
    j = tpr - fpr
    ix = int(np.argmax(j))
    t_internal = float(thr[ix]) if len(thr) else float("nan")
    if not higher_risk_if_high:
        raw_cut = -t_internal
    else:
        raw_cut = t_internal

    # Confusion at internal threshold: s >= t_internal -> predict high_risk
    pred = s >= t_internal
    tp = int(np.sum(pred & (yy == 1)))
    fp = int(np.sum(pred & (yy == 0)))
    fn = n_pos - tp
    tn = n_neg - fp
    sens = tp / (tp + fn) if (tp + fn) else None
    spec = tn / (tn + fp) if (tn + fp) else None

    if higher_risk_if_high:
        rule = f"high ADA risk if {name} >= {raw_cut:.6g}"
    else:
        rule = f"high ADA risk if {name} <= {raw_cut:.6g}"

    note = ""
    if auc is not None:
        if auc < 0.55:
            note = "AUC near random — do not use this metric alone for gating."
        elif auc > 0.85:
            note = "High AUC on small cohort — validate externally before freezing thresholds."

    return MetricCut(
        metric=name,
        n_valid=n_valid,
        n_high_risk=n_pos,
        n_low_risk=n_neg,
        orientation=orient,
        auc=auc,
        youden_threshold_raw=raw_cut,
        sensitivity=float(sens) if sens is not None else None,
        specificity=float(spec) if spec is not None else None,
        median_high_risk=med_pos,
        median_low_risk=med_neg,
        rule_text=rule,
        note=note,
    )


def load_frame(csv_path: Path, join_nat384: bool) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["ada"] = pd.to_numeric(df["ada_first_pct"], errors="coerce")
    df["hpr_proxy_pct"] = (
        pd.to_numeric(df["vh_identity_imgt"], errors="coerce")
        + pd.to_numeric(df["vl_identity_imgt"], errors="coerce")
    ) / 2.0 * 100.0
    if join_nat384 and NAT384.is_file():
        nat = pd.read_csv(NAT384)
        nat["key"] = nat["antibody_id"].astype(str).str.strip()
        df["key"] = df["antibody_name"].astype(str).str.strip()
        df = df.merge(nat[["key", "discovery_platform"]], on="key", how="left")
    return df


def run_block(df: pd.DataFrame, ada_th: float, label: str) -> dict[str, Any]:
    y = (df["ada"] >= ada_th).astype(float)
    return {
        "label_definition": f"high_risk = ada_first_pct >= {ada_th}",
        "stratum": label,
        "rows_total_in_frame": int(len(df)),
        "rows_with_ada": int(df["ada"].notna().sum()),
        "metrics": [
            asdict(one_metric("immuno_tcia_score", df["immuno_tcia_score"], y)),
            asdict(one_metric("hpr_proxy_pct_IMGT_mean", df["hpr_proxy_pct"], y)),
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--ada-threshold", type=float, default=10.0)
    ap.add_argument("--join-natural384", action="store_true")
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--out-md", type=Path, default=None)
    args = ap.parse_args()

    df = load_frame(args.csv, args.join_natural384)
    ada_th = args.ada_threshold

    report: dict[str, Any] = {
        "source_csv": str(args.csv.resolve()),
        "n_rows_file": len(df),
        "ada_threshold_pct": ada_th,
        "disclaimer": "Candidate thresholds from retrospective cohort; not SSOT until owner-approved config freeze.",
    }

    base = df[df["ada"].notna()].copy()
    report["global"] = run_block(base, ada_th, "global (all rows with ADA%)")

    def eff_class(row: pd.Series) -> Any:
        t = row.get("thera_genetics_class")
        g = row.get("genetics_normalized")
        if pd.isna(t) or str(t).strip() == "" or str(t) == "nan":
            return g
        return t

    base["gclass"] = base.apply(eff_class, axis=1)
    strata: dict[str, Any] = {}
    for gc, g in base.groupby("gclass"):
        if gc is None or (isinstance(gc, float) and math.isnan(gc)):
            continue
        yy = (g["ada"] >= ada_th).astype(int)
        if len(g) < 25 or int(yy.sum()) < 8 or int(len(yy) - yy.sum()) < 8:
            continue
        strata[str(gc)] = run_block(g, ada_th, f"thera_genetics_class={gc}")

    report["by_genetics_class"] = strata

    if args.join_natural384 and "discovery_platform" in base.columns:
        plat_map: dict[str, Any] = {}
        for plat in ("phage_display", "human_b_cell_derived"):
            sub = base[base["discovery_platform"] == plat]
            yy = (sub["ada"] >= ada_th).astype(int)
            if len(sub) < 20 or int(yy.sum()) < 5 or int(len(yy) - yy.sum()) < 5:
                plat_map[plat] = {
                    "skipped": True,
                    "reason": "insufficient n for ROC",
                    "n": int(len(sub)),
                    "n_high_risk": int(yy.sum()),
                }
            else:
                plat_map[plat] = run_block(sub, ada_th, f"discovery_platform={plat}")
        report["by_discovery_platform"] = plat_map

    js = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(js, encoding="utf-8")
        print("Wrote", args.out_json)
    else:
        print(js)

    if args.out_md:
        lines = [
            "# ADA risk index thresholds (candidate)",
            "",
            f"- Source: `{report['source_csv']}`",
            f"- Rows in file: **{report['n_rows_file']}**",
            f"- High ADA definition: **first incidence ≥ {ada_th}%**",
            "",
            "## Global",
            "",
        ]
        for m in report["global"]["metrics"]:
            lines.append(f"### `{m['metric']}`")
            lines.append(f"- n valid: {m['n_valid']} (high-risk {m['n_high_risk']}, low-risk {m['n_low_risk']})")
            lines.append(f"- Orientation: **{m['orientation']}**")
            if m.get("auc") is not None:
                lines.append(f"- ROC AUC: **{m['auc']:.3f}**")
            if m.get("youden_threshold_raw") is not None:
                lines.append(f"- Youden cutoff (raw): **{m['youden_threshold_raw']:.6g}**")
                lines.append(
                    f"- Sensitivity / specificity @ cutoff: **{m['sensitivity']:.3f}** / **{m['specificity']:.3f}**"
                )
            lines.append(
                f"- Medians — high-risk: **{m['median_high_risk']}**, low-risk: **{m['median_low_risk']}**"
            )
            lines.append(f"- Rule: {m['rule_text']}")
            if m.get("note"):
                lines.append(f"- Note: {m['note']}")
            lines.append("")

        lines.append("---")
        lines.append("_Candidate values — not production SSOT until owner-approved registry update._")
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text("\n".join(lines), encoding="utf-8")
        print("Wrote", args.out_md)


if __name__ == "__main__":
    main()
