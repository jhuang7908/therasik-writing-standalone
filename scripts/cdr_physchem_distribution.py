"""
CDR per-loop physico-chemical distribution sampler.

Computes 12 per-CDR metrics + per-position AA frequency matrices for any
antibody dataset with pre-segmented CDR columns. Designed to feed:

  1. VAM Stage 2.5 thresholds (`structural_integrity_veto.py`)
  2. CDR de-novo design priors (ProteinMPNN / RFAntibody bias)
  3. AbEvaluator CDR-level supplementary indicators

Reference samples (--source presets):
  * abref458 -> engineered VH/VL clinical Fv (n=458)
  * vhh42    -> clinical VHH single-domain (n=42)
  * natural384 -> natural human VH/VL (holdout only)

Output JSON layout:
{
  "_meta": {...},
  "loci": {
    "vh_cdr1": {
      "n": int,
      "metrics": { "<metric>": { "min/p5/p25/p50/p75/p90/p95/p99/max/mean/stdev/n": ... } },
      "aa_freq_by_position": [ {AA -> freq}, ... ],
      "length_histogram": { "<L>": count }
    },
    ...
  }
}
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics as st
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple


KD_HYDRO = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5,
    "E": -3.5, "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9,
    "M": 1.9, "F": 2.8, "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9,
    "Y": -1.3, "V": 4.2,
}
HYDROPHOBIC = set("ILVFAMW")
POSITIVE = set("KR")
NEGATIVE = set("DE")
AROMATIC = set("FWY")
AA20 = list("ACDEFGHIKLMNPQRSTVWY")

AGG_MOTIF_RE = re.compile(r"[FILVWY]{3,}")
NGLYC_RE = re.compile(r"N[^P][ST]")
DEAMID_RE = re.compile(r"N[GS]")
ISOMER_RE = re.compile(r"D[GS]")


PRESETS = {
    "abref458": {
        "csv": "data/engineered_459_atlas/master_table.csv",
        "id_col": "antibody_id",
        "loci": {
            "vh_cdr1": "vh_cdr1",
            "vh_cdr2": "vh_cdr2",
            "vh_cdr3": "vh_cdr3",
            "vl_cdr1": "vl_cdr1",
            "vl_cdr2": "vl_cdr2",
            "vl_cdr3": "vl_cdr3",
        },
        "label": "AbRef-458 (engineered_459_atlas master_table)",
        "cdr_definition": "IMGT (segmented in master_table.csv)",
    },
    "vhh42": {
        "csv": "data/vhh_clinical_39_union/vhh_39_cdr_fr_segments.csv",
        "id_col": "Name",
        "loci": {
            "vhh_cdr1": "CDR1",
            "vhh_cdr2": "CDR2",
            "vhh_cdr3": "CDR3",
        },
        "label": "VHH42 (vhh_39_cdr_fr_segments)",
        "cdr_definition": "IMGT (segmented upstream by ANARCII)",
    },
}


def _net_charge_pH7(seq: str) -> float:
    pos = sum(1 for a in seq if a in POSITIVE)
    neg = sum(1 for a in seq if a in NEGATIVE)
    his = sum(1 for a in seq if a == "H")
    return float(pos - neg + 0.1 * his)


def _longest_run(seq: str, members: set) -> int:
    best, cur = 0, 0
    for a in seq:
        if a in members:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def _longest_same_sign_charge_run(seq: str) -> int:
    return max(_longest_run(seq, POSITIVE), _longest_run(seq, NEGATIVE))


def _gravy(seq: str) -> float:
    if not seq:
        return 0.0
    return sum(KD_HYDRO.get(a, 0.0) for a in seq) / len(seq)


def compute_cdr_metrics(seq: str) -> Dict[str, float]:
    seq = (seq or "").strip().upper()
    if not seq:
        return {}
    pos = sum(1 for a in seq if a in POSITIVE)
    neg = sum(1 for a in seq if a in NEGATIVE)
    his = sum(1 for a in seq if a == "H")
    return {
        "length": float(len(seq)),
        "gravy": _gravy(seq),
        "longest_hydrophobic_run": float(_longest_run(seq, HYDROPHOBIC)),
        "aromatic_fraction": sum(1 for a in seq if a in AROMATIC) / len(seq),
        "net_charge_pH7": float(pos - neg + 0.1 * his),
        "longest_same_sign_charge_run": float(_longest_same_sign_charge_run(seq)),
        "charge_asymmetry": float(abs(pos - neg)),
        "agg_motif_count": float(len(AGG_MOTIF_RE.findall(seq))),
        "free_cys": float(seq.count("C")),
        "n_glyc_motif": float(len(NGLYC_RE.findall(seq))),
        "deamidation_motif": float(len(DEAMID_RE.findall(seq))),
        "isomerization_motif": float(len(ISOMER_RE.findall(seq))),
    }


def _percentile(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = (len(sorted_vals) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return float(sorted_vals[int(pos)])
    frac = pos - lo
    return float(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac)


def summarize_metric(values: List[float]) -> Dict[str, float]:
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not vals:
        return {"n": 0}
    s = sorted(vals)
    return {
        "n": len(s),
        "min": round(s[0], 4),
        "max": round(s[-1], 4),
        "mean": round(sum(s) / len(s), 4),
        "stdev": round(st.pstdev(s) if len(s) > 1 else 0.0, 4),
        "p5": round(_percentile(s, 0.05), 4),
        "p25": round(_percentile(s, 0.25), 4),
        "p50": round(_percentile(s, 0.50), 4),
        "p75": round(_percentile(s, 0.75), 4),
        "p90": round(_percentile(s, 0.90), 4),
        "p95": round(_percentile(s, 0.95), 4),
        "p99": round(_percentile(s, 0.99), 4),
    }


def compute_aa_freq_by_position(cdr_seqs: List[str]) -> List[Dict[str, float]]:
    """Per-position AA frequency (length = mode CDR length).

    For positions beyond mode length, only sequences that have that position
    contribute. Returns rows of {AA: probability} aligned to position index.
    """
    if not cdr_seqs:
        return []
    max_len = max(len(s) for s in cdr_seqs)
    result: List[Dict[str, float]] = []
    for i in range(max_len):
        counts: Dict[str, int] = {a: 0 for a in AA20}
        n = 0
        for s in cdr_seqs:
            if i < len(s):
                a = s[i]
                if a in counts:
                    counts[a] += 1
                    n += 1
        if n == 0:
            result.append({})
            continue
        result.append({a: round(counts[a] / n, 4) for a in AA20 if counts[a] > 0})
    return result


def length_histogram(cdr_seqs: List[str]) -> Dict[str, int]:
    h: Dict[int, int] = {}
    for s in cdr_seqs:
        h[len(s)] = h.get(len(s), 0) + 1
    return {str(k): v for k, v in sorted(h.items())}


def load_cdr_table(csv_path: Path, id_col: str, loci: Dict[str, str]) -> Dict[str, List[Tuple[str, str]]]:
    """Returns {locus_name -> [(antibody_id, cdr_seq), ...]}.

    Filters out empty/NaN rows. Robust to BOM / quoting via csv.DictReader.
    """
    rows: Dict[str, List[Tuple[str, str]]] = {k: [] for k in loci}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ab_id = (row.get(id_col) or "").strip()
            if not ab_id:
                continue
            for locus, col in loci.items():
                seq = (row.get(col) or "").strip().upper()
                if seq and seq != "NAN" and re.fullmatch(r"[A-Z]+", seq):
                    rows[locus].append((ab_id, seq))
    return rows


def compute_locus_block(cdr_pairs: List[Tuple[str, str]]) -> Dict:
    seqs = [s for _, s in cdr_pairs]
    n = len(seqs)
    if n == 0:
        return {"n": 0, "metrics": {}, "aa_freq_by_position": [], "length_histogram": {}}
    metric_names = list(compute_cdr_metrics("AAA").keys())
    bins: Dict[str, List[float]] = {m: [] for m in metric_names}
    for s in seqs:
        m = compute_cdr_metrics(s)
        for k, v in m.items():
            bins[k].append(v)
    return {
        "n": n,
        "metrics": {k: summarize_metric(v) for k, v in bins.items()},
        "aa_freq_by_position": compute_aa_freq_by_position(seqs),
        "length_histogram": length_histogram(seqs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=list(PRESETS.keys()), help="Preset dataset to load.")
    parser.add_argument("--csv", type=Path, help="Custom CSV path (override preset).")
    parser.add_argument("--id-col", default=None, help="Custom ID column.")
    parser.add_argument("--locus-map", default=None,
                        help='Custom locus->column JSON, e.g. \'{"vh_cdr1":"VHCDR1","vh_cdr3":"VHCDR3"}\'')
    parser.add_argument("--label", default=None, help="Human-readable label for _meta.source.")
    parser.add_argument("--cdr-definition", default=None, help="Numbering scheme used for CDRs.")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON path.")
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Repo root used to resolve preset CSV paths.")
    args = parser.parse_args()

    if args.source:
        cfg = PRESETS[args.source]
        csv_path = args.csv or (args.repo_root / cfg["csv"])
        id_col = args.id_col or cfg["id_col"]
        loci = cfg["loci"] if not args.locus_map else json.loads(args.locus_map)
        label = args.label or cfg["label"]
        cdr_def = args.cdr_definition or cfg["cdr_definition"]
    else:
        if not (args.csv and args.id_col and args.locus_map):
            parser.error("Without --source, --csv + --id-col + --locus-map are all required.")
        csv_path = args.csv
        id_col = args.id_col
        loci = json.loads(args.locus_map)
        label = args.label or csv_path.name
        cdr_def = args.cdr_definition or "unspecified"

    if not csv_path.exists():
        parser.error(f"CSV not found: {csv_path}")

    pairs = load_cdr_table(csv_path, id_col, loci)
    out = {
        "_meta": {
            "source": label,
            "csv_path": str(csv_path).replace("\\", "/"),
            "id_col": id_col,
            "loci_columns": loci,
            "cdr_definition": cdr_def,
            "generated": str(date.today()),
            "version": "v1",
            "n_antibodies_total": max((len(v) for v in pairs.values()), default=0),
        },
        "loci": {locus: compute_locus_block(p) for locus, p in pairs.items()},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[OK] {label}")
    for locus, block in out["loci"].items():
        n = block["n"]
        print(f"  {locus:10s} n={n:4d}", end="")
        if n:
            ln = block["metrics"]["length"]
            ch = block["metrics"]["net_charge_pH7"]
            hp = block["metrics"]["longest_hydrophobic_run"]
            print(f"  len={ln['p50']:.0f} (p95={ln['p95']:.0f}, p99={ln['p99']:.0f})"
                  f"  net_q={ch['p50']:+.1f} (p95={ch['p95']:+.1f})"
                  f"  hydro_run={hp['p50']:.0f} (p95={hp['p95']:.0f}, p99={hp['p99']:.0f})")
        else:
            print()
    print(f"[written] {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
