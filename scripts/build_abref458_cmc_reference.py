#!/usr/bin/env python3
"""
Build frozen CMC + structural/TAP percentiles and ADI distribution for AbRef-458
(engineered_458 rows in 842_combined_assessment.csv).

VH/VL sequences are extracted from PDB (chains H, L) — same convention as
batch_compute_tap_metrics.

Outputs
-------
  data/reference/AbRef458_27m_stats_v1.json
  data/reference/AbRef458_27m_ADI_distribution_v1.json
  data/humanization_assay/abref458_27m_per_antibody.csv

Usage:
  conda run -n anarcii python scripts/build_abref458_cmc_reference.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))

from Bio.PDB import PDBParser  # noqa: E402
from Bio.PDB.Polypeptide import is_aa
from Bio.SeqUtils import seq1  # noqa: E402

from core.cmc.adi_score import (  # noqa: E402
    _METRIC_CATEGORY,
    compute_adi,
)
from core.cmc.cmc_metrics import CMCMetricEngine  # noqa: E402

_IN_CSV = SUITE / "data" / "humanization_assay" / "842_combined_assessment.csv"
_OUT_STATS = SUITE / "data" / "reference" / "AbRef458_27m_stats_v1.json"
_OUT_ADI = SUITE / "data" / "reference" / "AbRef458_27m_ADI_distribution_v1.json"
_OUT_PER_AB = SUITE / "data" / "humanization_assay" / "abref458_27m_per_antibody.csv"

_METRIC_ORDER: Tuple[str, ...] = tuple(_METRIC_CATEGORY.keys()) + (
    "total_cdr_length", "psh", "ppc", "pnc", "sfvcsp",
    "vh_vl_angle_deg", "interface_n_pairs", "interface_mean_dist_A",
    "interface_min_dist_A", "vernier_sasa_total",
)


def _scalar(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (list, tuple, set)):
        return float(len(val))
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return float(val)
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        try:
            v = float(s)
        except ValueError:
            return None
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    return None


def _percentile(sorted_vals: Sequence[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    d0 = sorted_vals[int(f)] * (c - k)
    d1 = sorted_vals[int(c)] * (k - f)
    return d0 + d1


def _stdev(xs: List[float], mean: float) -> float:
    if len(xs) < 2:
        return 0.0
    v = sum((x - mean) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(v)


def find_pdb(pdb_path_str: str) -> Optional[Path]:
    if not pdb_path_str:
        return None
    fname = Path(pdb_path_str.replace("\\", "/")).name
    direct = Path(pdb_path_str)
    if direct.is_file():
        return direct
    for p in (SUITE / "data" / "structures").rglob(fname):
        return p
    return None


def seq_from_chain(model, chain_id: str) -> str:
    if chain_id not in model:
        return ""
    out: List[str] = []
    for r in model[chain_id]:
        if is_aa(r, standard=False):
            out.append(seq1(r.get_resname(), custom_map={"MSE": "M"}))
    return "".join(out)


def main() -> int:
    if not _IN_CSV.exists():
        print(f"ERROR: missing {_IN_CSV}", file=sys.stderr)
        return 1

    with open(_IN_CSV, newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    parser = PDBParser(QUIET=True)
    cohort: List[Dict[str, str]] = []
    for row in all_rows:
        if (row.get("origin") or "").strip() != "engineered_458":
            continue
        cohort.append(row)

    if len(cohort) < 5:
        print(f"ERROR: engineered_458 cohort too small (n={len(cohort)})", file=sys.stderr)
        return 1

    per_m: List[Dict[str, Any]] = []
    for row in cohort:
        ab = row.get("antibody_id", "")
        pdb_file = find_pdb(row.get("pdb_path", "") or "")
        vh, vl = "", ""
        if pdb_file and pdb_file.exists():
            try:
                s = parser.get_structure("m", str(pdb_file))
                m = s[0]
                vh = seq_from_chain(m, "H")
                vl = seq_from_chain(m, "L")
            except Exception as e:  # noqa: BLE001
                print(f"[warn] {ab} PDB read: {e}", file=sys.stderr)
        if len(vh) < 50 or len(vl) < 40:
            print(f"[skip] {ab} missing VH/VL from PDB (H={len(vh)} L={len(vl)})", file=sys.stderr)
            continue

        raw = CMCMetricEngine.compute_metrics(vh, vl)
        if raw.get("_biopython_missing"):
            print("ERROR: BioPython required for CMCMetricEngine", file=sys.stderr)
            return 1
        flat: Dict[str, Any] = {"antibody_id": ab}
        for k in _METRIC_ORDER:
            flat[k] = _scalar(raw.get(k) if raw.get(k) is not None else row.get(k))
        per_m.append(flat)

    n_ok = len(per_m)
    if n_ok < 5:
        print(f"ERROR: not enough Antibodies with valid PDB sequences (n={n_ok})", file=sys.stderr)
        return 1

    metrics_out: Dict[str, Any] = {}
    for key in _METRIC_ORDER:
        col_vals: List[float] = []
        for p in per_m:
            v = p.get(key)
            if v is not None:
                col_vals.append(v)
        col_vals.sort()
        if len(col_vals) < 2:
            continue
        mean = sum(col_vals) / len(col_vals)
        metrics_out[key] = {
            "p5": round(_percentile(col_vals, 5.0), 4),
            "p25": round(_percentile(col_vals, 25.0), 4),
            "p50": round(_percentile(col_vals, 50.0), 4),
            "p75": round(_percentile(col_vals, 75.0), 4),
            "p95": round(_percentile(col_vals, 95.0), 4),
            "mean": round(mean, 4),
            "stdev": round(_stdev(col_vals, mean), 4),
            "n": len(col_vals),
        }

    adi_list: List[float] = []
    for p in per_m:
        mrow = {k: p[k] for k in _METRIC_ORDER if k in p and p.get(k) is not None}
        a = compute_adi(mrow, ref_metrics=metrics_out)  # type: ignore[arg-type]
        p["ADI_abref458_27m"] = a
        adi_list.append(a)

    adi_list.sort()
    n_adi = len(adi_list)
    m_adi = sum(adi_list) / n_adi
    adi_dist = {
        "_meta": {
            "source": "per-antibody ADI (compute_adi vs AbRef458 27m ref percentiles)",
            "n": n_adi,
        },
        "p5": round(_percentile(adi_list, 5.0), 2),
        "p25": round(_percentile(adi_list, 25.0), 2),
        "p50": round(_percentile(adi_list, 50.0), 2),
        "p75": round(_percentile(adi_list, 75.0), 2),
        "p95": round(_percentile(adi_list, 95.0), 2),
        "mean": round(m_adi, 2),
        "stdev": round(_stdev(adi_list, m_adi), 2),
    }

    gen_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    out_doc: Dict[str, Any] = {
        "_meta": {
            "name": "AbRef-458 engineered clinical cohort (27-metric baselines)",
            "source": "data/humanization_assay/842_combined_assessment.csv",
            "filter": "origin=engineered_458",
            "n_antibodies": n_ok,
            "n_source_rows_engineered_458": len(cohort),
            "generated_by": "scripts/build_abref458_cmc_reference.py",
            "generated_at": gen_at,
        },
        "n": n_ok,
        "metrics": metrics_out,
    }
    adi_dist["_meta"]["cohort_n"] = n_adi
    adi_dist["_meta"]["generated_at"] = gen_at

    _OUT_STATS.parent.mkdir(parents=True, exist_ok=True)
    with open(_OUT_STATS, "w", encoding="utf-8") as f:
        json.dump(out_doc, f, ensure_ascii=False, indent=2)
    with open(_OUT_ADI, "w", encoding="utf-8") as f:
        json.dump(adi_dist, f, indent=2, ensure_ascii=False)

    fns = ["antibody_id", "ADI_abref458_27m", *_METRIC_ORDER]
    with open(_OUT_PER_AB, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns, extrasaction="ignore")
        w.writeheader()
        for p in per_m:
            w.writerow({k: p.get(k, "") for k in fns})

    print(f"[ok] AbRef-458 27m: n={n_ok}/{len(cohort)}  -> {_OUT_STATS.relative_to(SUITE)}")
    print(f"[ok] ADI dist  {_OUT_ADI.relative_to(SUITE)}")
    print(f"[ok] per-Ab  {_OUT_PER_AB.relative_to(SUITE)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
