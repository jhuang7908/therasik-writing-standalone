#!/usr/bin/env python3
"""
Build frozen CMC percentile + ADI reference from natural (fully human) IgG Fv cohort.

Input : data/natural_380_atlas/master_table.csv
        Rows: origin == "natural" AND genetics_normalized == "genetically_human"

Platform labels (discovery modality within fully-human drugs):
        data/reference/fully_human_357_platform_labels.json
        Keys = antibody_id; values = phage_display | transgenic_animal | human_b_cell_derived
        Antibodies absent from this file are tagged "unlabeled" for stratification summaries.

Metrics: Same keys as core/cmc/adi_score._METRIC_CATEGORY (+ structural columns), via CMCMetricEngine.

Outputs
-------
  data/reference/Natural384_IgG_stats_v1.json          — full cohort (mixed platforms)
  data/reference/Natural384_IgG_ADI_distribution.json
  data/reference/Natural384_subset_<platform>_stats_v1.json
  data/reference/Natural384_subset_<platform>_ADI_distribution_v1.json
        platforms: phage_display, transgenic_animal, human_b_cell_derived, unlabeled
  data/reference/Natural384_platform_stratification_summary_v1.json — cohort counts
  data/natural_380_atlas/natural384_cmc_per_antibody.csv  — optional audit (+ discovery_platform)

Usage:
  conda run -n anarcii python scripts/build_natural384_cmc_reference.py
  conda run -n anarcii python scripts/build_natural384_cmc_reference.py --no-per-antibody-csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))

from core.cmc.adi_score import (  # noqa: E402
    _METRIC_CATEGORY,
    compute_adi,
)
from core.cmc.cmc_metrics import CMCMetricEngine  # noqa: E402

_METRIC_ORDER: Tuple[str, ...] = tuple(_METRIC_CATEGORY.keys()) + (
    "total_cdr_length", "psh", "ppc", "pnc", "sfvcsp",
    "vh_vl_angle_deg", "interface_n_pairs", "interface_mean_dist_A",
    "interface_min_dist_A", "vernier_sasa_total",
)
_OUT_STATS = SUITE / "data" / "reference" / "Natural384_IgG_stats_v1.json"
_OUT_ADI = SUITE / "data" / "reference" / "Natural384_IgG_ADI_distribution.json"
_OUT_CSV = SUITE / "data" / "natural_380_atlas" / "natural384_cmc_per_antibody.csv"
_IN_CSV = SUITE / "data" / "natural_380_atlas" / "master_table.csv"
_PLATFORM_LABELS = SUITE / "data" / "reference" / "fully_human_357_platform_labels.json"
_OUT_STRAT_SUMMARY = SUITE / "data" / "reference" / "Natural384_platform_stratification_summary_v1.json"

SUBSET_KEYS = ("phage_display", "transgenic_animal", "human_b_cell_derived", "unlabeled")


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


def _load_platform_labels(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items()}
    except Exception:
        return {}


def _discovery_platform(aid: str, labels: Dict[str, str]) -> str:
    p = labels.get(aid)
    if p in {"phage_display", "transgenic_animal", "human_b_cell_derived"}:
        return p
    return "unlabeled"


def _aggregate_metrics(per_m: List[Dict[str, Any]]) -> Dict[str, Any]:
    metrics_out: Dict[str, Any] = {}
    for key in _METRIC_ORDER:
        col_vals: List[float] = []
        for row in per_m:
            v = row.get(key)
            if v is not None:
                col_vals.append(float(v))
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
    return metrics_out


def _adi_distribution_for_ref(per_m: List[Dict[str, Any]], metrics_out: Dict[str, Any]) -> Tuple[List[float], Dict[str, Any]]:
    adi_list: List[float] = []
    for p in per_m:
        mrow = {k: p[k] for k in _METRIC_ORDER if k in p and p.get(k) is not None}
        if not mrow:
            continue
        adi_list.append(float(compute_adi(mrow, ref_metrics=metrics_out)))  # type: ignore[arg-type]
    adi_list.sort()
    n_adi = len(adi_list)
    if n_adi < 2:
        return adi_list, {}
    m_adi = sum(adi_list) / n_adi
    dist = {
        "_meta": {
            "source": "per-antibody ADI (compute_adi vs cohort metric percentiles)",
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
    return adi_list, dist


def _write_subset(
    per_m: List[Dict[str, Any]],
    *,
    slug: str,
    meta_title: str,
    meta_filter: str,
    generated_at: str,
    input_rel: str,
    min_n: int = 5,
) -> bool:
    n_sub = len(per_m)
    if n_sub < min_n:
        print(f"[skip] subset {slug}: n={n_sub} < min_n={min_n}", file=sys.stderr)
        return False
    metrics_out = _aggregate_metrics(per_m)
    if not metrics_out:
        print(f"[skip] subset {slug}: no metric columns", file=sys.stderr)
        return False
    _, adi_dist = _adi_distribution_for_ref(per_m, metrics_out)
    if not adi_dist:
        print(f"[skip] subset {slug}: ADI distribution empty", file=sys.stderr)
        return False

    out_stats = SUITE / "data" / "reference" / f"Natural384_subset_{slug}_stats_v1.json"
    out_adi = SUITE / "data" / "reference" / f"Natural384_subset_{slug}_ADI_distribution_v1.json"
    doc: Dict[str, Any] = {
        "_meta": {
            "name": meta_title,
            "source": input_rel,
            "filter": meta_filter,
            "n_antibodies": n_sub,
            "generated_by": "scripts/build_natural384_cmc_reference.py",
            "generated_at": generated_at,
            "parent_cohort": "Natural-384 (origin=natural & genetically_human)",
        },
        "n": n_sub,
        "metrics": metrics_out,
    }
    adi_dist["_meta"]["cohort_n"] = adi_dist["_meta"]["n"]
    adi_dist["_meta"]["subset"] = slug
    adi_dist["_meta"]["generated_at"] = generated_at

    out_stats.parent.mkdir(parents=True, exist_ok=True)
    out_stats.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    out_adi.write_text(json.dumps(adi_dist, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] subset {slug} n={n_sub}  {out_stats.relative_to(SUITE)}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=_IN_CSV)
    ap.add_argument("--no-per-antibody-csv", action="store_true")
    args = ap.parse_args()

    if not args.input.exists():
        print(f"ERROR: missing {args.input}", file=sys.stderr)
        return 1

    labels = _load_platform_labels(_PLATFORM_LABELS)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    input_rel = str(
        args.input.resolve().relative_to(SUITE.resolve())
        if str(args.input.resolve()).startswith(str(SUITE.resolve()))
        else args.input
    )

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        rdr = csv.DictReader(f)
        all_rows = list(rdr)

    cohort: List[Dict[str, str]] = []
    for row in all_rows:
        if (row.get("origin") or "").strip() != "natural":
            continue
        if (row.get("genetics_normalized") or "").strip() != "genetically_human":
            continue
        vh = (row.get("vh_seq") or "").strip()
        vl = (row.get("vl_seq") or "").strip()
        if not vh or not vl:
            continue
        cohort.append({**row, "vh_seq": vh, "vl_seq": vl})
    n_cohort = len(cohort)
    if n_cohort < 5:
        print(f"ERROR: cohort too small (n={n_cohort})", file=sys.stderr)
        return 1

    per_m: List[Dict[str, Any]] = []
    for row in cohort:
        raw = CMCMetricEngine.compute_metrics(
            row["vh_seq"],
            row["vl_seq"],
        )
        if raw.get("_biopython_missing"):
            print("ERROR: BioPython required", file=sys.stderr)
            return 1
        aid = row.get("antibody_id", "") or ""
        plat = _discovery_platform(str(aid), labels)
        flat: Dict[str, Any] = {"antibody_id": aid, "discovery_platform": plat}
        for k in _METRIC_ORDER:
            flat[k] = _scalar(raw.get(k) if raw.get(k) is not None else row.get(k))
        per_m.append(flat)

    metrics_out = _aggregate_metrics(per_m)
    adi_list, adi_dist = _adi_distribution_for_ref(per_m, metrics_out)
    n_adi = len(adi_list)
    if n_adi < 2:
        print("ERROR: could not compute ADI list", file=sys.stderr)
        return 1

    for p in per_m:
        mrow = {k: p[k] for k in _METRIC_ORDER if k in p and p.get(k) is not None}
        p["ADI_natural384"] = float(compute_adi(mrow, ref_metrics=metrics_out))  # type: ignore[arg-type]

    out_doc: Dict[str, Any] = {
        "_meta": {
            "name": "Natural-384 (IgG Fv) fully human clinical cohort CMC baselines",
            "source": input_rel,
            "filter": "origin=natural & genetics_normalized=genetically_human",
            "n_antibodies": n_cohort,
            "platform_label_file": str(_PLATFORM_LABELS.relative_to(SUITE)),
            "stratified_outputs": [
                f"Natural384_subset_{s}_stats_v1.json" for s in SUBSET_KEYS
            ],
            "generated_by": "scripts/build_natural384_cmc_reference.py",
            "generated_at": generated_at,
        },
        "n": n_cohort,
        "metrics": metrics_out,
    }
    adi_dist["_meta"]["cohort_n"] = n_adi
    adi_dist["_meta"]["generated_at"] = generated_at

    _OUT_STATS.parent.mkdir(parents=True, exist_ok=True)
    _OUT_STATS.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    _OUT_ADI.write_text(json.dumps(adi_dist, indent=2, ensure_ascii=False), encoding="utf-8")

    # Stratification summary + subset JSONs
    from collections import Counter

    ctr = Counter(str(p.get("discovery_platform") or "unlabeled") for p in per_m)
    summary = {
        "_meta": {
            "generated_at": generated_at,
            "label_source": str(_PLATFORM_LABELS.relative_to(SUITE)),
            "note": (
                "transgenic_animal is a coarse label in fully_human_357_platform_labels.json "
                "(not exclusively human-Ig-transgenic mouse)."
            ),
        },
        "cohort_total": n_cohort,
        "counts_by_discovery_platform": {k: ctr.get(k, 0) for k in SUBSET_KEYS},
    }
    _OUT_STRAT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] summary {_OUT_STRAT_SUMMARY.relative_to(SUITE)}")

    subset_meta = {
        "phage_display": (
            "Natural-384 subset — phage display (fully human)",
            "origin=natural & genetically_human & discovery_platform=phage_display",
        ),
        "transgenic_animal": (
            "Natural-384 subset — transgenic animal (fully human)",
            "origin=natural & genetically_human & discovery_platform=transgenic_animal",
        ),
        "human_b_cell_derived": (
            "Natural-384 subset — human B-cell derived (fully human)",
            "origin=natural & genetically_human & discovery_platform=human_b_cell_derived",
        ),
        "unlabeled": (
            "Natural-384 subset — no entry in platform label file",
            "origin=natural & genetically_human & antibody_id not in fully_human_357_platform_labels.json",
        ),
    }
    for slug in SUBSET_KEYS:
        sub_rows = [p for p in per_m if p.get("discovery_platform") == slug]
        title, filt = subset_meta[slug]
        _write_subset(
            sub_rows,
            slug=slug,
            meta_title=title,
            meta_filter=filt,
            generated_at=generated_at,
            input_rel=input_rel,
            min_n=5,
        )

    print(f"[ok] n={n_cohort}  wrote {_OUT_STATS.relative_to(SUITE)}")
    print(f"[ok] ADI dist  {_OUT_ADI.relative_to(SUITE)}")
    if not args.no_per_antibody_csv:
        fns = ["antibody_id", "discovery_platform", "ADI_natural384", *_METRIC_ORDER]
        with open(_OUT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fns, extrasaction="ignore")
            w.writeheader()
            for p in per_m:
                w.writerow({k: p.get(k, "") for k in fns})
        print(f"[ok] per-Ab  {_OUT_CSV.relative_to(SUITE)}")

    sample_adi = compute_adi(
        {k: per_m[0][k] for k in _METRIC_ORDER if per_m[0].get(k) is not None},
        ref_stats_path=_OUT_STATS,
    )
    if abs(sample_adi - (per_m[0].get("ADI_natural384") or 0.0)) > 0.02:
        print("WARN: ADI file load vs in-memory ref mismatch", sample_adi, per_m[0].get("ADI_natural384"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
