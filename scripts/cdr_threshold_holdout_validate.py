"""
Validate CDR thresholds against an independent holdout dataset.

Applies thresholds in `data/reference/CDR_physchem_thresholds_v1.json` to the
384 natural (or any) holdout sequence table and reports PASS/WARN/VETO rates
per locus per metric. Acceptance criterion: PASS rate >= 85% per metric.

Note: segmentation may differ slightly between datasets (IMGT vs Kabat CDR1
length); we transparently report rates and never silently re-segment.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent))
from cdr_physchem_distribution import compute_cdr_metrics  # noqa: E402


def evaluate(seq: str, thresholds: Dict) -> Dict[str, str]:
    m = compute_cdr_metrics(seq)
    if not m:
        return {}
    verdict: Dict[str, str] = {}
    for metric, rule_block in thresholds.items():
        if metric not in m:
            continue
        rule = rule_block.get("rule")
        v = m[metric]
        if rule == "upper_bound":
            warn = float(rule_block.get("warn", 0))
            veto = float(rule_block.get("veto", 0))
            # Strict greater-than: "x in rare top 1%" means x > p99, not x >= p99.
            if v > veto:
                verdict[metric] = "VETO"
            elif v > warn:
                verdict[metric] = "WARN"
            else:
                verdict[metric] = "PASS"
        elif rule == "two_sided":
            wlo = float(rule_block.get("warn_lo", -1e9))
            whi = float(rule_block.get("warn_hi", 1e9))
            vlo = float(rule_block.get("veto_lo", -1e9))
            vhi = float(rule_block.get("veto_hi", 1e9))
            if v < vlo or v > vhi:
                verdict[metric] = "VETO"
            elif v < wlo or v > whi:
                verdict[metric] = "WARN"
            else:
                verdict[metric] = "PASS"
        elif rule == "hard_bound":
            warn = float(rule_block.get("warn", 1))
            veto = float(rule_block.get("veto", 2))
            if v >= veto:
                verdict[metric] = "VETO"
            elif v >= warn:
                verdict[metric] = "WARN"
            else:
                verdict[metric] = "PASS"
    return verdict


def load_table(csv_path: Path, id_col: str, locus_col_map: Dict[str, str]) -> Dict[str, List[Tuple[str, str]]]:
    rows: Dict[str, List[Tuple[str, str]]] = {k: [] for k in locus_col_map}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ab = (row.get(id_col) or "").strip()
            if not ab:
                continue
            for locus, col in locus_col_map.items():
                seq = (row.get(col) or "").strip().upper()
                if seq and re.fullmatch(r"[A-Z]+", seq):
                    rows[locus].append((ab, seq))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--thresholds", type=Path,
                        default=Path("data/reference/CDR_physchem_thresholds_v1.json"))
    parser.add_argument("--holdout-csv", type=Path,
                        default=Path("data/humanization_assay/384_natural_segmentation.csv"))
    parser.add_argument("--id-col", default="ab_id")
    parser.add_argument("--locus-map", default=json.dumps({
        "vh_cdr1": "vh_cdr1", "vh_cdr2": "vh_cdr2", "vh_cdr3": "vh_cdr3",
        "vl_cdr1": "vl_cdr1", "vl_cdr2": "vl_cdr2", "vl_cdr3": "vl_cdr3",
    }))
    parser.add_argument("--output", type=Path,
                        default=Path("data/reference/CDR_physchem_holdout_384natural_v1.json"))
    parser.add_argument("--accept-rate", type=float, default=0.85,
                        help="Minimum PASS rate per metric (default 0.85)")
    args = parser.parse_args()

    thresholds = json.loads(args.thresholds.read_text(encoding="utf-8"))
    locus_map = json.loads(args.locus_map)
    table = load_table(args.holdout_csv, args.id_col, locus_map)

    report: Dict = {
        "_meta": {
            "thresholds_source": str(args.thresholds).replace("\\", "/"),
            "holdout_source": str(args.holdout_csv).replace("\\", "/"),
            "accept_rate": args.accept_rate,
            "policy": "Apply AbRef-458/VHH42 derived thresholds to independent holdout. Report rates only; never silently re-segment.",
        },
        "per_locus": {},
        "global_pass_rate_check": {},
    }

    overall_pass: List[Tuple[str, str, float]] = []
    for locus, pairs in table.items():
        if locus not in thresholds.get("loci", {}):
            print(f"[skip] {locus}: not present in thresholds JSON")
            continue
        thr = thresholds["loci"][locus]["thresholds"]
        per_metric: Dict[str, Counter] = {m: Counter() for m in thr.keys()}
        per_metric_n = 0
        for ab, seq in pairs:
            verdict = evaluate(seq, thr)
            if not verdict:
                continue
            per_metric_n += 1
            for m, v in verdict.items():
                per_metric[m][v] += 1
        locus_block: Dict = {"n": per_metric_n, "metrics": {}}
        for m, ctr in per_metric.items():
            n = sum(ctr.values())
            if n == 0:
                continue
            pass_n = ctr.get("PASS", 0)
            warn_n = ctr.get("WARN", 0)
            veto_n = ctr.get("VETO", 0)
            pass_rate = pass_n / n
            locus_block["metrics"][m] = {
                "n": n,
                "PASS": pass_n,
                "WARN": warn_n,
                "VETO": veto_n,
                "pass_rate": round(pass_rate, 4),
                "warn_rate": round(warn_n / n, 4),
                "veto_rate": round(veto_n / n, 4),
                "ok": pass_rate >= args.accept_rate,
            }
            overall_pass.append((locus, m, pass_rate))
        report["per_locus"][locus] = locus_block

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[written] {args.output}")
    print()
    print("=== Holdout PASS rates (target >= {0:.0%}) ===".format(args.accept_rate))
    n_total = len(overall_pass)
    n_ok = sum(1 for _, _, r in overall_pass if r >= args.accept_rate)
    weak = [(loc, met, r) for loc, met, r in overall_pass if r < args.accept_rate]
    for locus in report["per_locus"]:
        block = report["per_locus"][locus]
        print(f"\n[{locus}] n={block['n']}")
        for m, d in block["metrics"].items():
            mark = "OK " if d["ok"] else "LOW"
            print(f"  {mark} {m:35s} pass={d['pass_rate']:.3f} (warn={d['warn_rate']:.3f}, veto={d['veto_rate']:.3f})")
    print()
    print(f"Overall: {n_ok}/{n_total} metric-locus pairs meet >= {args.accept_rate:.0%} PASS rate.")
    if weak:
        print("Below target:")
        for loc, met, r in weak:
            print(f"  - {loc}.{met} = {r:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
