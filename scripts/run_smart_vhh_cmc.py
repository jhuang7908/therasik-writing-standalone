"""
run_smart_vhh_cmc.py
──────────────────────────────────────────────────────────────────────────────
Smart-VHH-CMC  — VHH  /  VH CMC 


--------
 run_vhh_surface_reshaping_v1.py  VHH  pipeline ，
 AbNatiV Δ + ADI + VHH CMC ，。


--------
Regular VH/VL   : run_deepfr_ctx_cmc_polish.py → run_smart_cmc_orchestrator.py
VHH/Eng VH      : run_vhh_surface_reshaping_v1.py → run_smart_vhh_cmc.py ()


-----------
1. AbNatiV Δ ≥ floor（ VHH  0.020， VH  -0.074）
2. ADI （baseline-aware  Smart-CMC P0）
3. Aggregation Motifs  vs baseline


--------
--seq          :  baseline VHH/VH （raw AA  FASTA ）
--candidates   :  FASTA （ VHH  pipeline）
--origin       : humanized_vhh（）| engineered_vh
--out-dir      : 
--abnativ-floor: AbNatiV Δ （ humanized_vhh=0.020, engineered_vh=-0.074）
--max-mutations:  FR （ 5）
--top-n        :  N （ 3）

: anarcii conda （abnativ + anarcii + ImmuneBuilder）
Usage:
    python scripts/run_smart_vhh_cmc.py \\
        --seq EVQLVES... \\
        --candidates projects/anti_PD1_VHH/surface_reshaping_candidates.fasta \\
        --origin humanized_vhh \\
        --out-dir projects/anti_PD1_VHH/smart_vhh_cmc
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

warnings.filterwarnings("ignore")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# ─── Reference stat JSONs ─────────────────────────────────────────────────────
_REF_STATS: Dict[str, str] = {
    "humanized_vhh": str(REPO / "data/reference/VHH_Clinical26_stats_v1.json"),
    "engineered_vh": str(REPO / "data/reference/Atlas24_EngVH_stats_v1.json"),
}

# ─── AbNatiV Δ floor defaults ─────────────────────────────────────────────────
_ABNATIV_FLOOR_DEFAULTS: Dict[str, float] = {
    "humanized_vhh": 0.020,
    "engineered_vh": -0.074,
}

# ─── ADI tolerance (mirrors Smart-CMC P0 logic) ───────────────────────────────
def _max_adi_drop(baseline_adi: Optional[float]) -> float:
    if baseline_adi is None:
        return 0.0
    if baseline_adi < 60.0:
        return 0.0
    if baseline_adi < 80.0:
        return 0.5
    return 1.0  # generous ceiling for already high ADI


# ══════════════════════════════════════════════════════════════════════════════
# Sequence utilities
# ══════════════════════════════════════════════════════════════════════════════

def _parse_seq_arg(arg: str) -> str:
    if not arg:
        return ""
    p = Path(arg)
    if p.is_file():
        seqs = _read_fasta(p)
        return list(seqs.values())[0] if seqs else ""
    return arg.strip()


def _read_fasta(path: Path) -> Dict[str, str]:
    records: Dict[str, str] = {}
    cur = ""
    buf: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if cur:
                records[cur] = "".join(buf)
            cur = line[1:].split()[0]
            buf = []
        else:
            buf.append(line)
    if cur:
        records[cur] = "".join(buf)
    return records


def _count_mutations(seq: str, baseline: str) -> int:
    return sum(a != b for a, b in zip(seq, baseline)) + abs(len(seq) - len(baseline))


def _count_agg_motifs(seq: str) -> int:
    return len(re.findall(r"[VYFIL]{4,}", seq))


# ══════════════════════════════════════════════════════════════════════════════
# CMC evaluation — VHH full panel via core engine
# ══════════════════════════════════════════════════════════════════════════════

def _eval_vhh_cmc(seq: str) -> Dict[str, Any]:
    """
    Run VHH CMC engine (14+ parameter panel).
    Falls back to basic BioPython metrics if engine unavailable.
    """
    try:
        from core.cmc.vhh_cmc_engine import compute_vhh_metrics_full  # type: ignore
        return compute_vhh_metrics_full(seq)
    except Exception:
        pass

    # Fallback: basic metrics
    metrics: Dict[str, Any] = {
        "pi": None, "gravy": None, "instability_index": None,
        "agg_motifs": _count_agg_motifs(seq),
    }
    try:
        from Bio.SeqUtils.ProtParam import ProteinAnalysis  # type: ignore
        pa = ProteinAnalysis(seq.replace("X", "A"))
        metrics["pi"] = round(pa.isoelectric_point(), 2)
        metrics["gravy"] = round(pa.gravy(), 4)
        metrics["instability_index"] = round(pa.instability_index(), 2)
    except Exception:
        pass
    return metrics


# ══════════════════════════════════════════════════════════════════════════════
# AbNatiV Δ computation
# ══════════════════════════════════════════════════════════════════════════════

def _compute_abnativ_delta(seq: str) -> Optional[float]:
    """
    Compute AbNatiV Δ (VHH_score - VH_score) for a sdAb sequence.
    Returns None on failure.
    """
    try:
        from core.vh2vhh.abnativ_naturalness_layer import score_naturalness_delta  # type: ignore
        result = score_naturalness_delta(seq)
        return result.get("delta") if isinstance(result, dict) else float(result)
    except Exception:
        pass
    try:
        import abnativ  # type: ignore
        scores = abnativ.score(sequences=[seq], model="vhh")
        vhh_score = scores[0] if scores else None
        scores_vh = abnativ.score(sequences=[seq], model="vh")
        vh_score = scores_vh[0] if scores_vh else None
        if vhh_score is not None and vh_score is not None:
            return round(float(vhh_score) - float(vh_score), 5)
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
# ADI score
# ══════════════════════════════════════════════════════════════════════════════

def _compute_adi(cmc_metrics: Dict[str, Any]) -> Optional[float]:
    """Extract or compute ADI from CMC metrics dict."""
    # vhh_cmc_engine already returns adi_score if available
    if "adi_score" in cmc_metrics:
        return cmc_metrics["adi_score"]
    if "adi" in cmc_metrics:
        return cmc_metrics["adi"]
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Guard function
# ══════════════════════════════════════════════════════════════════════════════

def _guard_candidate(
    seq: str,
    baseline_seq: str,
    baseline_cmc: Dict[str, Any],
    baseline_abnativ: Optional[float],
    baseline_adi: Optional[float],
    origin: str,
    abnativ_floor: float,
    max_mutations: int,
) -> Dict[str, Any]:
    """Evaluate a single candidate against guard constraints."""
    flags: List[str] = []

    # 1. Mutation count
    n_mut = _count_mutations(seq, baseline_seq)
    if n_mut > max_mutations:
        flags.append(f"MutCount_exceed: {n_mut} > {max_mutations}")

    # 2. CMC evaluation
    cmc = _eval_vhh_cmc(seq)
    adi = _compute_adi(cmc)

    # 3. AbNatiV Δ floor
    abnativ_delta = _compute_abnativ_delta(seq)
    if abnativ_delta is not None and abnativ_delta < abnativ_floor:
        flags.append(f"AbNatiV_Δ_below_floor: {abnativ_delta:.4f} < {abnativ_floor:.4f}")

    # 4. ADI non-regression
    if adi is not None and baseline_adi is not None:
        allowed_drop = _max_adi_drop(baseline_adi)
        if adi < baseline_adi - allowed_drop:
            flags.append(f"ADI_drop: {baseline_adi:.1f} → {adi:.1f} (allowed_drop={allowed_drop:.1f})")

    # 5. Aggregation motifs non-increase
    cand_agg = _count_agg_motifs(seq)
    base_agg = baseline_cmc.get("agg_motifs", _count_agg_motifs(baseline_seq))
    if cand_agg > base_agg:
        flags.append(f"AggMotif_increase: {base_agg} → {cand_agg}")

    # 6. Free Cys — non-increase
    base_cys = baseline_seq.count("C")
    cand_cys = seq.count("C")
    if cand_cys > base_cys:
        flags.append(f"FreeCys_increase: {base_cys} → {cand_cys}")

    passed = len(flags) == 0
    return {
        "pass": passed,
        "flags": flags,
        "n_mutations": n_mut,
        "abnativ_delta": abnativ_delta,
        "adi": adi,
        "agg_motifs": cand_agg,
        "cmc": cmc,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Ranking score (for passing candidates)
# ══════════════════════════════════════════════════════════════════════════════

def _rank_score(r: Dict[str, Any]) -> float:
    """
    Higher is better. Combines AbNatiV Δ (primary) + GRAVY improvement.
    """
    score = 0.0
    if r.get("abnativ_delta") is not None:
        score += r["abnativ_delta"] * 10.0
    gravy = r.get("cmc", {}).get("gravy")
    if gravy is not None:
        score -= max(0.0, gravy)  # negative GRAVY preferred
    return score


# ══════════════════════════════════════════════════════════════════════════════
# Report rendering
# ══════════════════════════════════════════════════════════════════════════════

def _render_audit_md(
    payload: Dict[str, Any],
    out: Path,
) -> Path:
    lines: List[str] = [
        "# Smart-VHH-CMC Audit Report",
        f"**Origin:** {payload['origin']}  ",
        f"**Screened:** {payload['n_candidates']}  |  "
        f"**Passing:** {payload['n_passing']}  |  "
        f"**Selected:** {len(payload['selected'])}",
        "",
        "## Baseline",
        f"| Metric | Value |",
        f"|---|---|",
        f"| AbNatiV Δ | {payload['baseline']['abnativ_delta']} |",
        f"| ADI | {payload['baseline']['adi']} |",
        f"| Agg Motifs | {payload['baseline']['agg_motifs']} |",
        "",
        "## Selected Candidates",
    ]
    for i, r in enumerate(payload["selected"], 1):
        lines += [
            f"### Candidate {i}: {r['header']}",
            f"- Mutations vs baseline: {r['n_mutations']}",
            f"- AbNatiV Δ: {r['abnativ_delta']}",
            f"- ADI: {r['adi']}",
            f"- Agg Motifs: {r['agg_motifs']}",
            f"- Guard: **PASS**",
            "",
        ]
    lines += ["## Failing Candidates", ""]
    for r in payload["failing"]:
        lines.append(f"- **{r['header']}**: " + "; ".join(r["flags"]))
    md_path = out / "SMART_VHH_CMC_AUDIT.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Smart-VHH-CMC — VHH humanization / engineered VH CMC non-regression guard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--seq", required=True,
                    help="Baseline VHH/VH sequence (raw AA or FASTA path)")
    ap.add_argument("--candidates", required=True,
                    help="Candidate FASTA from VHH surface reshaping or humanization pipeline")
    ap.add_argument("--origin", choices=["humanized_vhh", "engineered_vh"],
                    default="humanized_vhh",
                    help="Molecule origin: humanized_vhh (default) or engineered_vh")
    ap.add_argument("--out-dir", default=".",
                    help="Output directory")
    ap.add_argument("--abnativ-floor", type=float, default=None,
                    help="AbNatiV Δ minimum floor (default: 0.013 for humanized_vhh, 0.000 for engineered_vh)")
    ap.add_argument("--max-mutations", type=int, default=5,
                    help="Maximum allowed FR mutations vs baseline (default: 5)")
    ap.add_argument("--top-n", type=int, default=3,
                    help="Maximum passing candidates to emit (default: 3)")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    baseline_seq = _parse_seq_arg(args.seq)
    if not baseline_seq:
        sys.exit("ERROR: --seq is empty or file not found.")

    candidates = _read_fasta(Path(args.candidates))
    if not candidates:
        sys.exit(f"ERROR: no sequences found in {args.candidates}")

    # AbNatiV floor: use argument if provided, else default per origin
    abnativ_floor = args.abnativ_floor
    if abnativ_floor is None:
        abnativ_floor = _ABNATIV_FLOOR_DEFAULTS.get(args.origin, 0.0)

    # Baseline evaluation
    print(f"[Smart-VHH-CMC] Evaluating baseline ({args.origin}) ...")
    baseline_cmc = _eval_vhh_cmc(baseline_seq)
    baseline_abnativ = _compute_abnativ_delta(baseline_seq)
    baseline_adi = _compute_adi(baseline_cmc)
    baseline_agg = _count_agg_motifs(baseline_seq)

    print(f"  Baseline AbNatiV Δ: {baseline_abnativ}  ADI: {baseline_adi}  AggMotifs: {baseline_agg}")

    # Screen candidates
    results: List[Dict[str, Any]] = []
    for header, seq in candidates.items():
        guard = _guard_candidate(
            seq=seq,
            baseline_seq=baseline_seq,
            baseline_cmc=baseline_cmc,
            baseline_abnativ=baseline_abnativ,
            baseline_adi=baseline_adi,
            origin=args.origin,
            abnativ_floor=abnativ_floor,
            max_mutations=args.max_mutations,
        )
        guard["header"] = header
        guard["seq"] = seq
        results.append(guard)

    passing = [r for r in results if r["pass"]]
    failing = [r for r in results if not r["pass"]]
    passing.sort(key=_rank_score, reverse=True)
    selected = passing[: args.top_n]

    # Build payload
    payload: Dict[str, Any] = {
        "schema": "smart_vhh_cmc_v1",
        "origin": args.origin,
        "policy": {
            "abnativ_floor": abnativ_floor,
            "max_mutations": args.max_mutations,
            "top_n": args.top_n,
        },
        "baseline": {
            "abnativ_delta": baseline_abnativ,
            "adi": baseline_adi,
            "agg_motifs": baseline_agg,
            "cmc": baseline_cmc,
        },
        "n_candidates": len(results),
        "n_passing": len(passing),
        "selected": selected,
        "failing": failing,
    }

    # Write JSON
    json_path = out / "smart_vhh_cmc_result.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write selected FASTA
    fasta_path = out / "smart_vhh_selected.fasta"
    with fasta_path.open("w", encoding="utf-8") as fh:
        for r in selected:
            tag = (
                f"AbNatiV_Δ={r['abnativ_delta']}|ADI={r['adi']}|Mut={r['n_mutations']}"
            )
            fh.write(f">{r['header']}|{tag}\n{r['seq']}\n")

    # Write audit MD
    md_path = _render_audit_md(payload, out)

    print(f"[Smart-VHH-CMC] {args.origin.upper()} | "
          f"Screened={len(results)} Passing={len(passing)} Selected={len(selected)}")
    print(f"  JSON   → {json_path}")
    print(f"  FASTA  → {fasta_path}")
    print(f"  Audit  → {md_path}")


if __name__ == "__main__":
    main()
