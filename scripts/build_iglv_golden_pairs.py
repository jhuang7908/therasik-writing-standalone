#!/usr/bin/env python3
"""
Build IGLV (lambda light chain) VH/VL pairing priors for rabbit / humanized-λ workflows.

Sources (in-repo):
  - data/humanization_assay/842_antibody_germline_assignment.csv  (κ-only in current snapshot)
  - data/thera_sabdab/features/framework_route_examples_slice_1.csv  (explicit IGLV matches)
  - data/thera_sabdab/out/thera_germline_mapping.csv  (marginal VL usage counts for IGLV genes)

Run: python scripts/build_iglv_golden_pairs.py
Outputs:
  - data/humanization_assay/vh_iglv_golden_pairs_v1.json
  - data/humanization_assay/vh_iglv_pairing_report.md
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "data/humanization_assay/vh_iglv_golden_pairs_v1.json"
OUT_MD = ROOT / "data/humanization_assay/vh_iglv_pairing_report.md"


def _load_route_examples() -> pd.DataFrame:
    p = ROOT / "data/thera_sabdab/features/framework_route_examples_slice_1.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def _load_842() -> pd.DataFrame:
    p = ROOT / "data/humanization_assay/842_antibody_germline_assignment.csv"
    return pd.read_csv(p)


def _load_thera_marginal() -> pd.DataFrame:
    p = ROOT / "data/thera_sabdab/out/thera_germline_mapping.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def main() -> int:
    df842 = _load_842()
    iglv_842 = df842[df842["vl_germline"].astype(str).str.startswith("IGLV")]
    n_842_iglv = len(iglv_842)

    route = _load_route_examples()
    pairs_explicit: list[dict] = []
    pair_counter: Counter[tuple[str, str]] = Counter()
    if not route.empty and "vl_germline_match" in route.columns:
        ig = route[route["vl_germline_match"].astype(str).str.startswith("IGLV")]
        for _, row in ig.iterrows():
            vh = str(row.get("vh_germline_match", ""))
            vl = str(row.get("vl_germline_match", ""))
            ab = str(row.get("antibody_id", ""))
            pair_counter[(vh, vl)] += 1
            pairs_explicit.append(
                {
                    "antibody_id": ab,
                    "vh_germline": vh,
                    "vl_germline": vl,
                    "source": "thera_sabdab/framework_route_examples_slice_1.csv",
                }
            )

    marginal_rows: list[dict] = []
    tm = _load_thera_marginal()
    if not tm.empty and set(tm.columns) >= {"chain", "germline", "count"}:
        sub = tm[(tm["chain"] == "VL") & (tm["germline"].astype(str).str.startswith("IGLV"))]
        for _, row in sub.iterrows():
            marginal_rows.append(
                {
                    "vl_germline": str(row["germline"]),
                    "count": int(row["count"]),
                    "note": "Marginal VL usage in Thera-SAbDab-derived mapping (not VH–VL joint frequency)",
                }
            )

    built_at = pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "version": "1.0",
        "built_at": built_at,
        "purpose": "IGLV λ-chain priors for Phase 2 framework selection when κ-based Golden Pairs are insufficient",
        "limitations": [
            "842 engineered+natural assignment CSV is κ-only (IGKV) in the current repository snapshot — no joint VH–IGLV frequencies from that file.",
            "Explicit VH–IGLV pairs below are sparse; use together with Vernier score + CDR gate + clinical precedent search.",
            "Marginal IGLV counts are not VH–VL co-occurrence frequencies.",
        ],
        "sources": {
            "842_antibody_germline_assignment": {
                "path": "data/humanization_assay/842_antibody_germline_assignment.csv",
                "rows_total": int(len(df842)),
                "rows_vl_iglv": n_842_iglv,
            },
            "framework_route_examples": {
                "path": "data/thera_sabdab/features/framework_route_examples_slice_1.csv",
                "explicit_iglv_rows": len(pairs_explicit),
            },
            "thera_germline_mapping_marginal_vl": {
                "path": "data/thera_sabdab/out/thera_germline_mapping.csv",
                "iglv_genes_listed": len(marginal_rows),
            },
        },
        "joint_vh_iglv_pairs_ranked": [
            {"vh_germline": vh, "vl_germline": vl, "count": c, "source": "framework_route_examples_slice_1"}
            for (vh, vl), c in pair_counter.most_common()
        ],
        "explicit_examples": pairs_explicit,
        "marginal_iglv_vl_usage": marginal_rows,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        "# VH / IGLV（λ ）",
        "",
        f"**:** `{payload['version']}`  ·  **built_at:** `{built_at}`",
        "",
        "## 1. ",
        "",
        "- `842_antibody_germline_assignment.csv`  ** IGKV**（`rows_vl_iglv={n_842_iglv}`）， λ 。",
        "-  `thera_sabdab`  ** IGLV**  VH–VL ， Thera  **IGLV **（）。",
        "",
        "## 2.  VH–IGLV （ framework_route_examples）",
        "",
        "| Rank | VH | VL (λ) | Count |",
        "|------|-----|--------|-------|",
    ]
    for i, row in enumerate(payload["joint_vh_iglv_pairs_ranked"], start=1):
        md_lines.append(
            f"| {i} | `{row['vh_germline']}` | `{row['vl_germline']}` | {row['count']} |"
        )
    if not payload["joint_vh_iglv_pairs_ranked"]:
        md_lines.append("| — | — | — | 0 |")

    md_lines += [
        "",
        "## 3. IGLV （Thera germline mapping， VH–VL ）",
        "",
        "| Rank | VL (λ) | Count |",
        "|------|--------|-------|",
    ]
    for i, row in enumerate(sorted(marginal_rows, key=lambda x: -x["count"]), start=1):
        md_lines.append(f"| {i} | `{row['vl_germline']}` | {row['count']} |")

    md_lines += [
        "",
        "## 4. ",
        "",
        "-  Phase 2： **CDR gate + Vernier + IGLV **； ****（）。",
        "-  `842`  Thera  **λ **， `vh_iglv_golden_pairs_v1.json`。",
        "",
        f" JSON：`{OUT_JSON.relative_to(ROOT)}`",
        "",
    ]
    OUT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"[OK] Wrote {OUT_JSON}")
    print(f"[OK] Wrote {OUT_MD}")
    print(f"     842 IGLV rows: {n_842_iglv}; explicit pairs: {len(pair_counter)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
