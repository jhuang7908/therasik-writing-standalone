#!/usr/bin/env python3
"""
Batch-compute **true HPR Index** + **TCIA** for ADA245 antibodies tagged Phage Display (n=7).

Reads VH/VL and **clinical ADA fields** (``ada_first_pct``, ``ada_value_display``, citations)
from ``data/ada245/database/ada_master_245_curated.csv``.
Writes:
  - ``data/ada245/statistics/phage_display_ada7_hpr_tcia_batch.tsv``
  - ``data/ada245/statistics/phage_display_ada7_hpr_tcia_batch.json``

Does not modify the master CSV (owner can merge columns after review).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
ADA_CSV = REPO / "data" / "ada245" / "database" / "ada_master_245_curated.csv"
OUT_DIR = REPO / "data" / "ada245" / "statistics"
PLATFORM_LABEL = "Phage Display"


def _ada_fields(src: dict) -> dict:
    """Subset of ADA245 master columns for reporting."""
    out = {
        "ada_first_pct": src.get("ada_first_pct", "").strip() or None,
        "ada_value_display": (src.get("ada_value_display") or "").strip() or None,
        "evidence_tier": (src.get("evidence_tier") or "").strip() or None,
        "evidence_source": (src.get("evidence_source") or "").strip() or None,
        "ada_source_url_primary": (src.get("ada_source_url_primary") or "").strip() or None,
        "citation_urls": (src.get("citation_urls") or "").strip() or None,
        "ada_source_pmids": (src.get("ada_source_pmids") or "").strip() or None,
    }
    if out["ada_first_pct"] is not None:
        try:
            out["ada_first_pct"] = float(out["ada_first_pct"])
        except ValueError:
            pass
    return out


def _load_rows() -> list[dict]:
    rows: list[dict] = []
    with ADA_CSV.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("discovery_platform", "").strip() == PLATFORM_LABEL:
                rows.append(r)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--iedb",
        action="store_true",
        help="Use IEDB path in MHCII_Analyzer if configured (default: False, matches IgG CMC pipeline).",
    )
    args = ap.parse_args()

    from core.humanization.hpr_index import compute_hpr_index
    from core.immunogenicity.mhcii_analyzer import MHCII_Analyzer

    rows = _load_rows()
    if len(rows) != 7:
        raise SystemExit(f"Expected 7 '{PLATFORM_LABEL}' rows, got {len(rows)}")

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results: list[dict] = []

    for r in rows:
        name = r["antibody_name"].strip()
        vh = (r.get("vh_seq") or "").strip().upper()
        vl = (r.get("vl_seq") or "").strip().upper()
        legacy_tcia = r.get("immuno_tcia_score", "").strip()

        hpr = compute_hpr_index(vh, vl)
        comb = (hpr.get("combined") or {}).get("score")
        vhs = (hpr.get("vh") or {}).get("score")
        vls = (hpr.get("vl") or {}).get("score")

        tcia_score = None
        tcia_risk = None
        tcia_err = None
        try:
            mh = MHCII_Analyzer(vh_seq=vh, vl_seq=vl, use_iedb=bool(args.iedb))
            mres = mh.run(is_vhh=False)
            tcia_score = round(float(mres.tcia_score), 4)
            tcia_risk = str(mres.risk_level)
        except Exception as exc:  # noqa: BLE001
            tcia_err = f"{type(exc).__name__}: {exc}"

        row_out = {
            "antibody_name": name,
            **_ada_fields(r),
            "hpr_combined": comb,
            "hpr_vh": vhs,
            "hpr_vl": vls,
            "hpr_status": (hpr.get("combined") or {}).get("status"),
            "tcia_score": tcia_score,
            "tcia_risk_level": tcia_risk,
            "tcia_error": tcia_err,
            "ada245_csv_immuno_tcia_score": legacy_tcia or None,
            "tcia_delta_vs_csv": (
                round(tcia_score - float(legacy_tcia), 6)
                if tcia_score is not None and legacy_tcia not in ("", "nan")
                else None
            ),
        }
        results.append(row_out)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tsv_path = OUT_DIR / "phage_display_ada7_hpr_tcia_batch.tsv"
    json_path = OUT_DIR / "phage_display_ada7_hpr_tcia_batch.json"

    fieldnames = [
        "antibody_name",
        "ada_first_pct",
        "ada_value_display",
        "evidence_tier",
        "evidence_source",
        "ada_source_url_primary",
        "ada_source_pmids",
        "hpr_combined",
        "hpr_vh",
        "hpr_vl",
        "tcia_score",
        "tcia_risk_level",
        "ada245_csv_immuno_tcia_score",
        "tcia_delta_vs_csv",
        "tcia_error",
        "citation_urls",
    ]
    with tsv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in results:
            w.writerow({k: row.get(k) for k in fieldnames})

    payload = {
        "generated_at_utc": generated_at,
        "source_csv": str(ADA_CSV.relative_to(REPO)),
        "platform_filter": PLATFORM_LABEL,
        "n_rows": len(results),
        "tcia_use_iedb": bool(args.iedb),
        "rows": results,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Wrote {tsv_path.relative_to(REPO)}")
    print(f"Wrote {json_path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
