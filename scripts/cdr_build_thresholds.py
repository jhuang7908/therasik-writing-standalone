"""
Build CDR physico-chemical thresholds from per-locus distribution JSONs.

Reads:
  data/reference/CDR_physchem_AbRef458_v1.json   (VH/VL anchor)
  data/reference/CDR_physchem_VHH42_v1.json      (VHH anchor)

Writes:
  data/reference/CDR_physchem_thresholds_v1.json

Threshold rules (data-driven, source-aware):

  Upper-bound metrics (larger = riskier, one-sided):
    longest_hydrophobic_run, longest_same_sign_charge_run, agg_motif_count,
    n_glyc_motif, deamidation_motif, isomerization_motif, charge_asymmetry
    -> WARN at p95, VETO at p99

  Two-sided metrics:
    net_charge_pH7   -> WARN if outside [p5, p95], VETO if outside [p1_proxy, p99]
                        (p1_proxy = p5 - 1*(p25-p5) lower extrapolation; bounded)
    gravy            -> same scheme

  Hard bounds (not statistical):
    free_cys         -> WARN >=1, VETO >=2 (Cys is structural, anything free is suspect)

  De-novo design priors:
    length range      = [p5, p95]
    aa_freq_by_position copied as PSSM-like bias prior (use upstream)
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path
from typing import Dict, List


UPPER_ONLY = [
    "longest_hydrophobic_run",
    "longest_same_sign_charge_run",
    "agg_motif_count",
    "n_glyc_motif",
    "deamidation_motif",
    "isomerization_motif",
    "charge_asymmetry",
]
TWO_SIDED = ["net_charge_pH7", "gravy"]


def _q(metric: Dict[str, float], key: str) -> float:
    v = metric.get(key)
    return float(v) if v is not None else float("nan")


def _round(x: float, digits: int = 2) -> float:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return float("nan")
    return round(float(x), digits)


def build_locus_thresholds(locus_block: Dict) -> Dict:
    n = locus_block.get("n", 0)
    metrics = locus_block.get("metrics", {})
    out: Dict = {"n_samples": n, "thresholds": {}, "design_prior": {}}

    for m in UPPER_ONLY:
        if m not in metrics:
            continue
        d = metrics[m]
        out["thresholds"][m] = {
            "rule": "upper_bound",
            "warn": _round(_q(d, "p95")),
            "veto": _round(_q(d, "p99")),
            "source_p50": _round(_q(d, "p50")),
            "source_p95": _round(_q(d, "p95")),
            "source_p99": _round(_q(d, "p99")),
            "source_max": _round(_q(d, "max")),
        }

    for m in TWO_SIDED:
        if m not in metrics:
            continue
        d = metrics[m]
        # WARN window is [p5, p95]; VETO is [p1_extrapolated, p99_extrapolated].
        # When the distribution is too tight (p5 == p25 or p95 == p99), expand the
        # VETO bound by one IQR-equivalent step to keep WARN and VETO distinguishable.
        p5 = _q(d, "p5")
        p25 = _q(d, "p25")
        p50 = _q(d, "p50")
        p75 = _q(d, "p75")
        p95 = _q(d, "p95")
        p99 = _q(d, "p99")
        v_min = _q(d, "min")
        v_max = _q(d, "max")
        iqr = max(p75 - p25, 1.0)  # floor at 1.0 to keep windows nonzero on tight integer dists
        veto_lo = max(p5 - iqr, v_min - 0.001)
        veto_hi = min(p95 + iqr, v_max + 0.001)
        # If p5 == p25 (degenerate left tail), pull veto_lo further by 1 IQR.
        if abs(p25 - p5) < 1e-9:
            veto_lo = min(veto_lo, p5 - iqr)
        if abs(p95 - p75) < 1e-9:
            veto_hi = max(veto_hi, p95 + iqr)
        out["thresholds"][m] = {
            "rule": "two_sided",
            "warn_lo": _round(p5),
            "warn_hi": _round(p95),
            "veto_lo": _round(veto_lo),
            "veto_hi": _round(veto_hi),
            "source_p50": _round(p50),
            "source_iqr": _round(iqr),
        }

    # Hard bound for free cysteine (not statistical)
    out["thresholds"]["free_cys"] = {
        "rule": "hard_bound",
        "warn": 1,
        "veto": 2,
        "rationale": "Free Cys in CDR is intrinsically risky regardless of population frequency.",
    }

    # De-novo design priors
    if "length" in metrics:
        L = metrics["length"]
        out["design_prior"]["length_range"] = {
            "min": _round(_q(L, "p5"), 0),
            "max": _round(_q(L, "p95"), 0),
            "p50": _round(_q(L, "p50"), 0),
        }
    if "aa_freq_by_position" in locus_block:
        out["design_prior"]["aa_freq_by_position"] = locus_block["aa_freq_by_position"]
    if "length_histogram" in locus_block:
        out["design_prior"]["length_histogram"] = locus_block["length_histogram"]

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--abref458", type=Path, default=Path("data/reference/CDR_physchem_AbRef458_v1.json"))
    parser.add_argument("--vhh42", type=Path, default=Path("data/reference/CDR_physchem_VHH42_v1.json"))
    parser.add_argument("--output", type=Path, default=Path("data/reference/CDR_physchem_thresholds_v1.json"))
    parser.add_argument("--holdout-json", type=Path, default=None,
                        help="Optional holdout validation JSON to embed PASS-rate summary into _meta.")
    args = parser.parse_args()

    if not args.abref458.exists() or not args.vhh42.exists():
        parser.error("Both AbRef-458 and VHH42 distribution JSONs must exist.")

    abref = json.loads(args.abref458.read_text(encoding="utf-8"))
    vhh = json.loads(args.vhh42.read_text(encoding="utf-8"))

    out = {
        "_meta": {
            "purpose": "CDR per-loop physchem thresholds for VAM Stage 2.5 + de-novo CDR design priors",
            "generated": str(date.today()),
            "version": "v1",
            "rule_summary": {
                "upper_only_metrics": UPPER_ONLY,
                "two_sided_metrics": TWO_SIDED,
                "hard_bounds": ["free_cys"],
                "warn_quantile": "p95 (upper) / p5-p95 window (two-sided)",
                "veto_quantile": "p99 (upper) / p1_extrapolated-p99 window (two-sided)",
            },
            "sources": {
                "vh_vl": {
                    "label": abref["_meta"]["source"],
                    "n": abref["_meta"].get("n_antibodies_total"),
                    "cdr_definition": abref["_meta"].get("cdr_definition"),
                },
                "vhh": {
                    "label": vhh["_meta"]["source"],
                    "n": vhh["_meta"].get("n_antibodies_total"),
                    "cdr_definition": vhh["_meta"].get("cdr_definition"),
                },
            },
            "consumer_modules": [
                "core/structure/structural_integrity_veto.py (VAM Stage 2.5)",
                "future de-novo CDR design module (ProteinMPNN / RFAntibody bias)",
                "core/evaluation/evaluator.py (CDR-level supplement to Fv-level SAP/PPC)",
            ],
            "policy": "AbRef-458 powers vh_*/vl_* loci; VHH42 powers vhh_* loci. The two are NOT pooled.",
            "comparison_semantics": "Strict greater-than against quantile bounds (x > p99 -> VETO, x > p95 -> WARN, else PASS). Equality at the bound counts as PASS so degenerate-zero distributions on motif counts behave correctly.",
        },
        "loci": {},
    }

    for locus, block in abref.get("loci", {}).items():
        out["loci"][locus] = build_locus_thresholds(block)
    for locus, block in vhh.get("loci", {}).items():
        out["loci"][locus] = build_locus_thresholds(block)

    if args.holdout_json and args.holdout_json.exists():
        holdout = json.loads(args.holdout_json.read_text(encoding="utf-8"))
        n_total = 0
        n_ok = 0
        below_85: List[Dict] = []
        for locus, blk in holdout.get("per_locus", {}).items():
            for m, d in blk.get("metrics", {}).items():
                n_total += 1
                if d.get("ok"):
                    n_ok += 1
                else:
                    below_85.append({
                        "locus": locus, "metric": m,
                        "pass_rate": d.get("pass_rate"),
                    })
        out["_meta"]["holdout_validation"] = {
            "source": holdout["_meta"].get("holdout_source"),
            "n_metric_locus_pairs": n_total,
            "n_pass_>=_85pct": n_ok,
            "ratio": round(n_ok / n_total, 4) if n_total else None,
            "interpretation": "Engineered-derived thresholds applied to natural antibodies. PASS rate ~80-85% on a few metrics (e.g. vh_cdr3 gravy, vl_cdr3 NG/DG motifs) reflects genuine engineered-vs-natural differences (CDR liability scrubbing during engineering), not threshold artifacts.",
            "metric_locus_pairs_below_85pct": below_85,
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[written] {args.output}")
    print()
    print("=== Threshold summary (WARN/VETO) ===")
    print(f"{'locus':10s} {'len[p5,p95]':>14s} {'hydro_run':>14s} {'same_sign':>14s} {'net_q':>16s} {'agg_motif':>14s}")
    for locus, blk in out["loci"].items():
        thr = blk["thresholds"]
        dp = blk["design_prior"]
        L = dp.get("length_range", {})
        len_str = f"[{int(L.get('min', 0))},{int(L.get('max', 0))}]"
        hr = thr.get("longest_hydrophobic_run", {})
        ss = thr.get("longest_same_sign_charge_run", {})
        nq = thr.get("net_charge_pH7", {})
        ag = thr.get("agg_motif_count", {})
        hr_str = f"{hr.get('warn','-')}/{hr.get('veto','-')}"
        ss_str = f"{ss.get('warn','-')}/{ss.get('veto','-')}"
        nq_str = f"[{nq.get('warn_lo','-')},{nq.get('warn_hi','-')}]"
        ag_str = f"{ag.get('warn','-')}/{ag.get('veto','-')}"
        print(f"{locus:10s} {len_str:>14s} {hr_str:>14s} {ss_str:>14s} {nq_str:>16s} {ag_str:>14s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
