#!/usr/bin/env python3
"""
Per-origin descriptive statistics for the **25-parameter developability set** + **+2 humanness**
(HPR Index, AbLang2) vocabulary used in `core/cmc/regular_ab_developability.py`.

Data sources:
  - `data/ada245/database/ada_master_245_curated.csv` — stratification via `discovery_platform`
  - `data/natural_380_atlas/natural384_cmc_per_antibody.csv` — full **25 numeric keys** where antibody names match

Important:
  - Not every ADA245 antibody appears in Natural384 → merged metrics use columns prefixed `nat384_`.
  - **AbLang2** is **not** stored in these CSVs; output documents `ablang2_status: pending_batch`.
  - **VHH** rows often lack VL sequence columns suitable for paired metrics; `hpr_proxy` uses heavy-chain-only IMGT
    identity when VL columns are empty.

Outputs JSON (+ optional markdown) under `data/ada245/statistics/`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from core.cmc.regular_ab_developability import PARAMETER_SET_25

REPO = Path(__file__).resolve().parents[3]
ADA_CSV = REPO / "data" / "ada245" / "database" / "ada_master_245_curated.csv"
NAT384 = REPO / "data" / "natural_380_atlas" / "natural384_cmc_per_antibody.csv"

# Canonical cohort labels in ada_master (exact strings)
PLATFORM_GROUPS: dict[str, str] = {
    "gene_engineered_humanization": "Humanized (CDR Grafting)",
    "transgenic_mouse": "Transgenic Mice",
    "phage_display": "Phage Display",
    "vhh": "VHH",
}


def _desc(s: pd.Series) -> dict[str, Any]:
    x = pd.to_numeric(s, errors="coerce").dropna()
    n = int(x.shape[0])
    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "mean": float(x.mean()),
        "std": float(x.std(ddof=1)) if n > 1 else 0.0,
        "p25": float(x.quantile(0.25)),
        "p50": float(x.median()),
        "p75": float(x.quantile(0.75)),
        "min": float(x.min()),
        "max": float(x.max()),
    }


def _hpr_proxy_row(r: pd.Series) -> float | None:
    vh = pd.to_numeric(r.get("vh_identity_imgt"), errors="coerce")
    vl = pd.to_numeric(r.get("vl_identity_imgt"), errors="coerce")
    if pd.notna(vh) and pd.notna(vl):
        return float((vh + vl) / 2.0)
    if pd.notna(vh) and pd.isna(vl):
        return float(vh)
    return None


def build_merged() -> pd.DataFrame:
    ada = pd.read_csv(ADA_CSV)
    keys = [p["key"] for p in PARAMETER_SET_25]
    nat = pd.read_csv(NAT384)
    keep = ["antibody_id"] + [k for k in keys if k in nat.columns]
    nat = nat[keep].copy()
    ren = {k: f"nat384_{k}" for k in keys if k in nat.columns}
    nat = nat.rename(columns=ren)
    nat["key"] = nat["antibody_id"].astype(str).str.strip().str.lower()
    nat = nat.drop(columns=["antibody_id"])
    ada["key"] = ada["antibody_name"].astype(str).str.strip().str.lower()
    m = ada.merge(nat, on="key", how="left", indicator=True)
    m["hpr_proxy_imgt"] = m.apply(_hpr_proxy_row, axis=1)
    return m


def run_summary(df: pd.DataFrame) -> dict[str, Any]:
    keys = [p["key"] for p in PARAMETER_SET_25]
    ada_keys = [k for k in keys if k in df.columns]
    out: dict[str, Any] = {
        "sources": {"ada245": str(ADA_CSV), "natural384": str(NAT384)},
        "n_rows_ada245": int(len(df)),
        "vocabulary": "25 developability keys from PARAMETER_SET_25; +2 = HPR Index + AbLang2 (per product CMC)",
        "coverage_note": {
            "ada245_direct_keys": ada_keys,
            "ada245_direct_count": len(ada_keys),
            "missing_in_ada245_csv": [k for k in keys if k not in df.columns],
            "natural384": "Full 25 keys for antibodies that exist in Natural384 (name match to antibody_id).",
        },
        "plus2_note": {
            "hpr_index": "Interim: hpr_proxy_imgt = (vh_identity_imgt+vl_identity_imgt)/2, or VH-only if no VL (VHH). True promb HPR Index requires `compute_hpr_index` batch.",
            "ablang2": "not_in_csv — requires ablang2-paired batch on VH/VL (VHH: N/A paired).",
        },
        "platforms": {},
    }

    for slug, dpl in PLATFORM_GROUPS.items():
        g = df[df["discovery_platform"] == dpl].copy()
        n_tot = int(len(g))
        nat_mask = g["_merge"] == "both"
        n_nat = int(nat_mask.sum())
        block: dict[str, Any] = {
            "discovery_platform_label": dpl,
            "n_total": n_tot,
            "n_matched_natural384": n_nat,
            "parameters_25_from_ada245_rows": {k: _desc(g[k]) for k in ada_keys},
            "parameters_25_from_natural384_matched_only": {},
            "hpr_proxy_imgt": _desc(g["hpr_proxy_imgt"]) if "hpr_proxy_imgt" in g.columns else {"n": 0},
            "ablang2": {"status": "pending_batch", "n_computed": 0},
        }
        for k in keys:
            col = f"nat384_{k}"
            if col not in g.columns:
                block["parameters_25_from_natural384_matched_only"][k] = {"error": "column_missing"}
                continue
            block["parameters_25_from_natural384_matched_only"][k] = _desc(g.loc[nat_mask, col])
        out["platforms"][slug] = block
    return out


def to_markdown(summary: dict[str, Any]) -> str:
    cov = summary.get("coverage_note", {})
    ada_n = len(cov.get("ada245_direct_keys", []))
    lines = [
        "# Platform 25+2 statistics (ADA245 cohort)",
        "",
        f"- ADA table: `{summary['sources']['ada245']}`",
        f"- Natural-384 (25 numeric developability fields): `{summary['sources']['natural384']}`",
        "- **25** = `PARAMETER_SET_25` keys; **+2** = HPR Index + AbLang2 in CMC vocabulary.",
        f"- **ADA245 row coverage:** **{ada_n}/25** developability keys exist as columns in the ADA CSV (sequence/Fv metrics). Remaining keys require Natural384 merge or batch structure metrics.",
        "- **IMGT HPR proxy** = `(vh_identity_imgt + vl_identity_imgt)/2` when VL exists; otherwise VH-only. **AbLang2**: not in CSV (pending batch).",
        "",
    ]
    for slug, block in summary["platforms"].items():
        lines.append(f"## {slug} — {block.get('discovery_platform_label', '')}")
        lines.append("")
        lines.append(
            f"- n (platform): **{block['n_total']}** | matched to Natural384: **{block['n_matched_natural384']}**"
        )
        hp = block.get("hpr_proxy_imgt", {})
        if hp.get("n", 0):
            lines.append(
                f"- **HPR proxy (IMGT mean)**: n={hp['n']}, mean={hp['mean']:.4f}, "
                f"median={hp['p50']:.4f}, p25–p75=[{hp['p25']:.4f}, {hp['p75']:.4f}]"
            )
        lines.append("- **AbLang2**: pending batch (not in source CSV).")
        lines.append("")
        lines.append("### 25-parameter subset — direct from ADA245 rows (same platform)")
        lines.append("")
        lines.append("| Parameter | n | mean | p50 | p25 | p75 |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for k, d in block.get("parameters_25_from_ada245_rows", {}).items():
            if d.get("n", 0) == 0:
                continue
            lines.append(
                f"| {k} | {d['n']} | {d['mean']:.4f} | {d['p50']:.4f} | {d['p25']:.4f} | {d['p75']:.4f} |"
            )
        lines.append("")
        lines.append("### 25-parameter full keys — Natural384 name match (subset of platform)")
        lines.append("")
        lines.append("| Parameter | n | mean | p50 | p25 | p75 |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for k, d in block.get("parameters_25_from_natural384_matched_only", {}).items():
            if d.get("n", 0) == 0:
                continue
            lines.append(
                f"| {k} | {d['n']} | {d['mean']:.4f} | {d['p50']:.4f} | {d['p25']:.4f} | {d['p75']:.4f} |"
            )
        lines.append("")
    lines.append("---")
    lines.append("_Descriptive stats only; not production reference ranges._")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=REPO / "data" / "ada245" / "statistics" / "platform_25plus2_stats.json")
    ap.add_argument("--out-md", type=Path, default=REPO / "data" / "ada245" / "statistics" / "PLATFORM_25PLUS2_STATS.md")
    args = ap.parse_args()

    merged = build_merged()
    summary = run_summary(merged)
    js = json.dumps(summary, indent=2, ensure_ascii=False)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(js, encoding="utf-8")
    print("Wrote", args.out_json)
    md = to_markdown(summary)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(md, encoding="utf-8")
    print("Wrote", args.out_md)


if __name__ == "__main__":
    main()
