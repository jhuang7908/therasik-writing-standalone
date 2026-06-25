#!/usr/bin/env python3
"""
Summarize immuno / similarity metrics for ADA245 by ADA incidence slice.

Default: compare ADA first incidence >= 10% vs < 10%.
Optional: stratify by --column (e.g. thera_genetics_class) with --min-n per cell.

Outputs JSON (+ optional markdown) for methodology documentation — not a frozen product SSOT.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ADA245_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ADA245_ROOT / "database" / "ada_master_245_curated.csv"


def _desc(s: pd.Series) -> dict[str, Any]:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return {"n": 0}
    return {
        "n": int(s.shape[0]),
        "min": float(s.min()),
        "p25": float(s.quantile(0.25)),
        "median": float(s.median()),
        "p75": float(s.quantile(0.75)),
        "max": float(s.max()),
        "mean": float(s.mean()),
        "std": float(s.std(ddof=1)) if s.shape[0] > 1 else 0.0,
    }


def run(
    csv_path: Path,
    ada_ge: float,
    stratify: str | None,
    min_n: int,
    metrics: list[str],
) -> dict[str, Any]:
    df = pd.read_csv(csv_path)
    df["ada"] = pd.to_numeric(df["ada_first_pct"], errors="coerce")
    df = df[df["ada"].notna()].copy()
    high = df["ada"] >= ada_ge

    out: dict[str, Any] = {
        "csv": str(csv_path),
        "rows_total": len(df),
        "ada_ge_pct": ada_ge,
        "counts": {"ada_high": int(high.sum()), "ada_low": int((~high).sum())},
        "metrics_global": {},
        "by_stratum": None,
    }

    for m in metrics:
        if m not in df.columns:
            out["metrics_global"][m] = {
                "error": "column_missing",
                "ada_high": {},
                "ada_low": {},
            }
            continue
        out["metrics_global"][m] = {
            "ada_high": _desc(df.loc[high, m]),
            "ada_low": _desc(df.loc[~high, m]),
        }

    if stratify and stratify in df.columns:
        cells: dict[str, Any] = {}
        for key, g in df.groupby(stratify, dropna=False):
            if len(g) < min_n:
                continue
            hi = g["ada"] >= ada_ge
            cell: dict[str, Any] = {"n": len(g), "ada_high": int(hi.sum()), "metrics": {}}
            for m in metrics:
                if m not in g.columns:
                    cell["metrics"][m] = {"error": "column_missing"}
                    continue
                cell["metrics"][m] = {
                    "ada_high": _desc(g.loc[hi, m]),
                    "ada_low": _desc(g.loc[~hi, m]),
                }
            cells[str(key)] = cell
        out["by_stratum"] = cells
    elif stratify:
        out["by_stratum_error"] = f"column_not_found:{stratify}"

    return out


def to_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# ADA10 risk-threshold exploration (data-only)",
        "",
        f"- Source: `{summary['csv']}`",
        f"- Rows with non-null ADA: **{summary['rows_total']}**",
        f"- High ADA slice: `ada_first_pct >= {summary['ada_ge_pct']}` → **{summary['counts']['ada_high']}**; low: **{summary['counts']['ada_low']}**",
        "",
        "## Global distributions",
        "",
    ]
    for m, block in summary.get("metrics_global", {}).items():
        lines.append(f"### `{m}`")
        if "error" in block:
            lines.append(f"- {block.get('error', 'error')}")
            lines.append("")
            continue
        for label in ("ada_high", "ada_low"):
            d = block.get(label, {})
            if d.get("n", 0) == 0:
                lines.append(f"- **{label}**: n=0")
                continue
            lines.append(
                f"- **{label}**: n={d['n']}, median={d['median']:.4f}, "
                f"p25–p75=[{d['p25']:.4f}, {d['p75']:.4f}], "
                f"range=[{d['min']:.4f}, {d['max']:.4f}]"
            )
        lines.append("")

    if summary.get("by_stratum"):
        lines.append("## By stratum")
        lines.append("")
        for k, cell in summary["by_stratum"].items():
            lines.append(f"### {k} (n={cell['n']}, ADA-high={cell['ada_high']})")
            for m, mb in cell.get("metrics", {}).items():
                if "error" in mb:
                    lines.append(f"- `{m}`: {mb['error']}")
                    continue
                ha = mb["ada_high"]
                la = mb["ada_low"]
                if ha.get("n", 0) and la.get("n", 0):
                    lines.append(
                        f"- `{m}`: high median={ha['median']:.4f} (n={ha['n']}) vs "
                        f"low median={la['median']:.4f} (n={la['n']})"
                    )
                else:
                    lines.append(f"- `{m}`: insufficient split (high n={ha.get('n',0)}, low n={la.get('n',0)})")
            lines.append("")

    lines.append("---")
    lines.append("_Screening cutoffs for production require owner approval and frozen config._")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--ada-ge", type=float, default=10.0, help="ADA%% threshold for 'high' slice")
    ap.add_argument("--stratify", type=str, default=None, help="e.g. thera_genetics_class")
    ap.add_argument("--min-n", type=int, default=8, help="Minimum rows per stratum")
    ap.add_argument(
        "--metrics",
        type=str,
        default="immuno_tcia_score,vh_identity_imgt,vl_identity_imgt",
        help="Comma-separated column names",
    )
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--out-md", type=Path, default=None)
    args = ap.parse_args()

    metrics = [x.strip() for x in args.metrics.split(",") if x.strip()]
    summary = run(args.csv, args.ada_ge, args.stratify, args.min_n, metrics)

    js = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(js, encoding="utf-8")
        print("Wrote", args.out_json)
    else:
        print(js)

    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(to_markdown(summary), encoding="utf-8")
        print("Wrote", args.out_md)


if __name__ == "__main__":
    main()
