"""
rank_phase1_for_p2.py — Rank T1-passed candidates for Phase 2 (minimal bar: not identical to WT)
================================================================================================
- Eligible: T1 AbLang pass AND full sequence != WT (any difference counts).
- Writes per-sequence metrics + multiple rank columns + min–max composite for downstream picks.

Outputs (under <project_dir>/phase1_generation/):
  p2_ranked_full.jsonl   — all eligible rows with ranks
  p2_ranked_full.csv     — same (optional readability)
  p2_input_topk.fasta    — top --top_k by composite_score (default 50)

Usage:
  conda run -n affmat python pipeline/rank_phase1_for_p2.py --project_dir projects/denovo_HER2_VGRW_SR_R2_v2
  conda run -n affmat python pipeline/rank_phase1_for_p2.py --project_dir <path> --top_k 100 --no_csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

_PIPELINE = Path(__file__).resolve().parent
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))

import cluster_and_filter_v2 as cf  # noqa: E402

try:
    from pipeline.coord_utils import cdr_linear_ranges, validate_mask_coords
except ModuleNotFoundError:
    import importlib.util, pathlib as _pl
    _spec = importlib.util.spec_from_file_location(
        "coord_utils", _pl.Path(__file__).parent / "coord_utils.py")
    _mod = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mod)
    cdr_linear_ranges    = _mod.cdr_linear_ranges
    validate_mask_coords = _mod.validate_mask_coords

try:
    from pipeline.run_mpnn_v2 import is_conservative
except ModuleNotFoundError:
    _spec2 = importlib.util.spec_from_file_location(
        "run_mpnn_v2", _pl.Path(__file__).parent / "run_mpnn_v2.py")
    _mod2 = importlib.util.module_from_spec(_spec2); _spec2.loader.exec_module(_mod2)
    is_conservative = _mod2.is_conservative


def _minmax_norm(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _dense_rank_desc(scores: list[float]) -> list[int]:
    """1 = best (highest score). Ties share same rank."""
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    rank_by_i = [0] * len(scores)
    r = 0
    prev = None
    for j, i in enumerate(order):
        if prev is None or scores[i] != prev:
            r = j + 1
            prev = scores[i]
        rank_by_i[i] = r
    return rank_by_i


def _dense_rank_asc(values: list[float]) -> list[int]:
    """1 = best (lowest value)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    rank_by_i = [0] * len(values)
    r = 0
    prev = None
    for j, i in enumerate(order):
        if prev is None or values[i] != prev:
            r = j + 1
            prev = values[i]
        rank_by_i[i] = r
    return rank_by_i


def run_rank(project_dir: Path, top_k: int, write_csv: bool) -> None:
    project_dir = project_dir.resolve()
    p1 = project_dir / "phase1_generation"
    mask_path = project_dir / "config" / "mask_strategy.json"
    mask = json.loads(mask_path.read_text(encoding="utf-8"))
    validate_mask_coords(mask, abort=True)   # coordinate consistency gate
    wt_seq   = mask["wt_sequence"].upper()
    redesign = mask["design_mask"]["redesign_cdrs"]
    cdr_regions = mask["cdr_regions"]
    # cdr_linear_ranges returns {cdr_key: (ls, le)} — linear 0-indexed, correct for seq ops
    cdr_ranges = list(cdr_linear_ranges(mask, redesign).values())

    fasta_path = p1 / "mpnn_raw_sequences.fasta"
    seq_map = cf.load_fasta(fasta_path)
    t0_by_id = {r["seq_id"]: r for r in cf.load_jsonl(p1 / "t0_oasis_blast.jsonl")}
    t1_rows = [r for r in cf.load_jsonl(p1 / "t1_ablang_scores.jsonl") if r.get("pass")]

    semiopen_0indexed = []
    for cdr_key, cfg in mask.get("root_constraints", {}).items():
        if cdr_key in redesign:
            semiopen_0indexed.extend(cfg.get("semiopen_0indexed", []))

    rows: list[dict] = []
    n_t1 = len(t1_rows)
    n_wt_identical = 0
    n_missing_fasta = 0

    for rec in t1_rows:
        sid = rec["seq_id"]
        seq = seq_map.get(sid)
        if not seq:
            n_missing_fasta += 1
            continue
        su = seq.upper()
        if su == wt_seq:
            n_wt_identical += 1
            continue

        n_semi_fails = 0
        for pos in semiopen_0indexed:
            if pos < len(su) and pos < len(wt_seq):
                if su[pos] != wt_seq[pos] and not is_conservative(wt_seq[pos], su[pos]):
                    n_semi_fails += 1

        per_cdr = cf.cdr_mutations_per_cdr(su, wt_seq, cdr_regions, redesign)
        tot_muts = sum(per_cdr.values())
        idn = cf.cdr_identity(su, wt_seq, cdr_ranges)
        cdr_str = cf.get_combined_cdr_string(su, cdr_ranges)
        t0 = t0_by_id.get(sid, {})
        oasis = float(t0.get("oasis_coverage", 0.0))
        abl = float(rec.get("ablang_mean_logp", rec.get("score", 0.0)))
        full_muts = sum(1 for a, b in zip(su, wt_seq) if a != b) if len(su) == len(wt_seq) else None

        rows.append(
            {
                "seq_id": sid,
                "sequence": su,
                "combined_cdr": cdr_str,
                "ablang_mean_logp": round(abl, 6),
                "oasis_coverage": round(oasis, 6),
                "cdr_identity_vs_wt": round(idn, 6),
                "total_cdr_mutations": tot_muts,
                "per_cdr_mutations": per_cdr,
                "full_chain_mutation_count": full_muts,
                "semiopen_fails": n_semi_fails,
            }
        )

    if not rows:
        print("[ERROR] No eligible sequences (T1 pass, in FASTA, != WT).")
        raise SystemExit(1)

    n = len(rows)
    abls = [r["ablang_mean_logp"] for r in rows]
    oass = [r["oasis_coverage"] for r in rows]
    idns = [r["cdr_identity_vs_wt"] for r in rows]
    muts = [float(r["total_cdr_mutations"]) for r in rows]

    z_abl = _minmax_norm(abls)
    z_oas = _minmax_norm(oass)
    z_div = _minmax_norm([1.0 - x for x in idns])
    z_mut = _minmax_norm(muts)
    for i, r in enumerate(rows):
        base_comp = (z_abl[i] + z_oas[i] + z_div[i]) / 3.0
        base_c4 = (z_abl[i] + z_oas[i] + z_div[i] + z_mut[i]) / 4.0
        
        # Penalize for non-conservative mutations at semiopen positions
        penalty = 0.15 * r.get("semiopen_fails", 0)
        
        r["composite_score"] = round(base_comp - penalty, 6)
        r["composite_with_muts"] = round(base_c4 - penalty, 6)

    comps = [r["composite_score"] for r in rows]
    comps4 = [r["composite_with_muts"] for r in rows]
    order_comp = sorted(range(n), key=lambda i: comps[i], reverse=True)
    order_c4 = sorted(range(n), key=lambda i: comps4[i], reverse=True)

    rank_comp = [0] * n
    rank_c4 = [0] * n
    for rank, i in enumerate(order_comp, start=1):
        rank_comp[i] = rank
    for rank, i in enumerate(order_c4, start=1):
        rank_c4[i] = rank

    r_abl = _dense_rank_desc(abls)
    r_oas = _dense_rank_desc(oass)
    r_mut = _dense_rank_desc(muts)
    r_idn = _dense_rank_asc(idns)

    for i, r in enumerate(rows):
        r["rank_by_ablang"] = r_abl[i]
        r["rank_by_oasis"] = r_oas[i]
        r["rank_by_cdr_mutations"] = r_mut[i]
        r["rank_by_cdr_identity_asc"] = r_idn[i]
        r["rank_composite"] = rank_comp[i]
        r["rank_composite_plus_muts"] = rank_c4[i]

    rows.sort(key=lambda x: x["rank_composite"])

    out_jsonl = p1 / "p2_ranked_full.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    if write_csv:
        out_csv = p1 / "p2_ranked_full.csv"
        flat_keys = [
            "seq_id",
            "ablang_mean_logp",
            "oasis_coverage",
            "cdr_identity_vs_wt",
            "total_cdr_mutations",
            "full_chain_mutation_count",
            "composite_score",
            "composite_with_muts",
            "rank_composite",
            "rank_composite_plus_muts",
            "rank_by_ablang",
            "rank_by_oasis",
            "rank_by_cdr_mutations",
            "rank_by_cdr_identity_asc",
            "combined_cdr",
        ]
        with open(out_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=flat_keys, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in flat_keys})

    top_k = min(top_k, n)
    out_fa = p1 / "p2_input_topk.fasta"
    with open(out_fa, "w", encoding="utf-8") as f:
        for r in rows[:top_k]:
            f.write(
                f">{r['seq_id']} | rank={r['rank_composite']} | "
                f"comp={r['composite_score']} | abl={r['ablang_mean_logp']} | "
                f"oas={r['oasis_coverage']} | cdr_id={r['cdr_identity_vs_wt']} | "
                f"cdr_muts={r['total_cdr_mutations']}\n{r['sequence']}\n"
            )

    manifest_path = project_dir / "project_manifest.json"
    if manifest_path.exists():
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        m.setdefault("stats", {}).update(
            {
                "p2_rank_t1_passed": n_t1,
                "p2_rank_eligible_not_wt": n,
                "p2_rank_excluded_wt_identical": n_wt_identical,
                "p2_rank_missing_fasta": n_missing_fasta,
                "p2_input_topk": top_k,
            }
        )
        m.setdefault("phase_status", {})["phase1_p2_ranking"] = "DONE"
        manifest_path.write_text(json.dumps(m, indent=2), encoding="utf-8")

    print("=" * 60)
    print(f"  rank_phase1_for_p2 — {project_dir.name}")
    print("=" * 60)
    print(f"  T1 passed (records):     {n_t1}")
    print(f"  Excluded (= WT):         {n_wt_identical}")
    print(f"  Missing FASTA:           {n_missing_fasta}")
    print(f"  Eligible for ranking:    {n}")
    print(f"  Written: {out_jsonl.name}")
    if write_csv:
        print(f"  Written: p2_ranked_full.csv")
    print(f"  Written: {out_fa.name}  (top {top_k} by composite)")
    print("=" * 60)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_dir", type=Path, required=True)
    ap.add_argument("--top_k", type=int, default=50, help="FASTA size for Phase 2 input")
    ap.add_argument("--no_csv", action="store_true")
    args = ap.parse_args()
    run_rank(args.project_dir, args.top_k, write_csv=not args.no_csv)


if __name__ == "__main__":
    main()
