#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
compute_scfv_cmc.py
===================
Compute CMC developability metrics for all sequences in scfv_52_atlas
and produce a benchmark statistics JSON for comparison with VHH-GS-VHH
bispecific tandem nanobody constructs.

Output:
  data/scfv_52_atlas/cmc_computed.json  — per-entry results
  data/scfv_52_atlas/cmc_stats.json     — percentile distribution stats
"""
from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE_ROOT))

from Bio.SeqUtils.ProtParam import ProteinAnalysis


# ─── helpers ────────────────────────────────────────────────────────────────

def clean_seq(s: str) -> str:
    return re.sub(r"[^ACDEFGHIKLMNPQRSTVWY]", "", str(s).upper())


def count_net_charge(seq: str, pH: float = 7.0) -> float:
    return round(ProteinAnalysis(seq).charge_at_pH(pH), 2)


def count_agg_motifs(seq: str) -> int:
    """Count windows of ≥3 consecutive hydrophobic residues."""
    hydro = frozenset("AILMFWV")
    count = run = 0
    for aa in seq:
        if aa in hydro:
            run += 1
            if run >= 3:
                count += 1
        else:
            run = 0
    return count


def count_deamidation(seq: str) -> int:
    return len(re.findall(r"N[^P][ST]|NG|NS", seq))


def count_isomerization(seq: str) -> int:
    return len(re.findall(r"D[GT]", seq))


def count_oxidation(seq: str) -> int:
    return seq.count("M") + seq.count("W")


def count_glycosylation(seq: str) -> int:
    return len(re.findall(r"N[^P][ST]", seq))


def sap_proxy(seq: str) -> float:
    """Max fraction of AILMFWV in any 7-mer window."""
    hydro = frozenset("AILMFWV")
    if len(seq) < 7:
        return 0.0
    return round(
        max(sum(1 for a in seq[i : i + 7] if a in hydro) / 7.0 for i in range(len(seq) - 6)),
        3,
    )


def charge_patch_max7(seq: str) -> float:
    charged = frozenset("KRDE")
    if len(seq) < 7:
        return 0.0
    return round(
        max(sum(1 for a in seq[i : i + 7] if a in charged) / 7.0 for i in range(len(seq) - 6)),
        3,
    )


def compute_cmc(seq: str) -> dict:
    seq = clean_seq(seq)
    if len(seq) < 80:
        raise ValueError(f"Sequence too short ({len(seq)} aa)")
    pa = ProteinAnalysis(seq)
    return {
        "pI": round(pa.isoelectric_point(), 2),
        "GRAVY": round(pa.gravy(), 3),
        "instability_index": round(pa.instability_index(), 1),
        "net_charge_pH7": count_net_charge(seq),
        "SAP_score": sap_proxy(seq),
        "charge_patch_max7": charge_patch_max7(seq),
        "agg_motifs": count_agg_motifs(seq),
        "deamidation_sites": count_deamidation(seq),
        "isomerization_sites": count_isomerization(seq),
        "oxidation_sites": count_oxidation(seq),
        "glycosylation_sites": count_glycosylation(seq),
        "full_len": len(seq),
    }


# ─── percentile helpers ─────────────────────────────────────────────────────

def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (len(sorted_data) - 1) * p / 100.0
    lo = int(idx)
    hi = lo + 1
    if hi >= len(sorted_data):
        return sorted_data[-1]
    return sorted_data[lo] + (idx - lo) * (sorted_data[hi] - sorted_data[lo])


def build_stats(values: list[float]) -> dict:
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 3),
        "stdev": round(statistics.stdev(values), 3) if len(values) > 1 else 0.0,
        "min": round(min(values), 3),
        "p5": round(_percentile(values, 5), 3),
        "p25": round(_percentile(values, 25), 3),
        "p50": round(_percentile(values, 50), 3),
        "p75": round(_percentile(values, 75), 3),
        "p95": round(_percentile(values, 95), 3),
        "max": round(max(values), 3),
    }


# ─── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    atlas_path = SUITE_ROOT / "data" / "scfv_52_atlas" / "master_table.csv"
    out_cmc = SUITE_ROOT / "data" / "scfv_52_atlas" / "cmc_computed.json"
    out_stats = SUITE_ROOT / "data" / "scfv_52_atlas" / "cmc_stats.json"

    with open(atlas_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    valid_rows = [r for r in rows if r.get("full_sequence", "").strip()]
    print(f"scFv_52_atlas: {len(rows)} total, {len(valid_rows)} with sequence")

    results = []
    skipped = []
    for r in valid_rows:
        ab_id = r["antibody_id"]
        try:
            m = compute_cmc(r["full_sequence"])
            entry = {
                "antibody_id": ab_id,
                "scfv_format": r.get("scfv_format", ""),
                "orientation": r.get("orientation", ""),
                "targets": r.get("targets", ""),
                "phase": r.get("phase", ""),
                "linker_name": r.get("linker_name", ""),
                "linker_seq": r.get("linker_seq", ""),
                "linker_length": r.get("linker_length", ""),
                **m,
            }
            results.append(entry)
            print(
                f"  {ab_id[:32]:32s}  pI={m['pI']:.2f}  charge={m['net_charge_pH7']:+.1f}"
                f"  GRAVY={m['GRAVY']:.3f}  agg={m['agg_motifs']}  len={m['full_len']}"
            )
        except Exception as exc:
            skipped.append(ab_id)
            print(f"  SKIP {ab_id}: {exc}")

    print(f"\nComputed: {len(results)}  Skipped: {len(skipped)}")

    # ── per-metric stats ────────────────────────────────────────────────────
    METRICS = [
        "pI", "GRAVY", "instability_index", "net_charge_pH7",
        "SAP_score", "charge_patch_max7", "agg_motifs",
        "deamidation_sites", "isomerization_sites", "oxidation_sites",
        "glycosylation_sites", "full_len",
    ]
    stats = {}
    for m_key in METRICS:
        vals = [r[m_key] for r in results if m_key in r]
        if vals:
            stats[m_key] = build_stats(vals)

    # ── save ────────────────────────────────────────────────────────────────
    with open(out_cmc, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved CMC results -> {out_cmc}")

    stats_payload = {
        "_meta": {
            "source": "scfv_52_atlas",
            "n_entries": len(results),
            "description": "CMC distribution for 52 clinical/late-stage scFv sequences (VH-linker-VL format)",
        },
        "metrics": stats,
    }
    with open(out_stats, "w", encoding="utf-8") as f:
        json.dump(stats_payload, f, ensure_ascii=False, indent=2)
    print(f"Saved CMC stats  -> {out_stats}")

    # ── quick summary ────────────────────────────────────────────────────────
    print("\n=== scFv_52 CMC Distribution Summary ===")
    for m_key in ["pI", "net_charge_pH7", "GRAVY", "instability_index", "agg_motifs"]:
        s = stats.get(m_key, {})
        if s:
            print(f"  {m_key:25s}: p25={s['p25']:.2f}  p50={s['p50']:.2f}  p75={s['p75']:.2f}  "
                  f"mean={s['mean']:.2f}±{s['stdev']:.2f}")


if __name__ == "__main__":
    main()
