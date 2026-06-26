#!/usr/bin/env python3
"""
General-purpose DeepFR-CTX-CMC–style FR-only mini-CMC polish (project-level).

Canonical product name: **DeepFR-CTX-CMC** (SSOT). The legacy label *DeepFR-CTX-CM*
is deprecated — do not use in new filenames or client copy.

Modes
-----
1) ``sources`` — Same philosophy as ``scripts/deepfr_ctx_cm_rat_campath.py``:
   diff base VH/VL against one or more same-length donor sequences at Kabat FR
   positions; substitutions must pass safety filters (no new N-glyc, no C/P/G play).

2) ``sweep`` — When no donor panel exists: enumerate conservative biochem substitutes
   at FR positions only (small fixed alphabet). Useful for charge / instability tuning
   (e.g. Fv_charge_asymmetry) before full IgG CMC.

Outputs: deepfr_ctx_cmc_scan.json, DEEPFR_CTX_CMC_SCAN.md, polish_result.json

Role
----
This CLI is a candidate generator for FR-only polish proposals.
Final release decision must be made by an outer policy layer (e.g. Smart-CMC),
not by this script alone.

Examples
--------
  # Humira Fv + conservative sweep (no external JSON)
  python scripts/run_deepfr_ctx_cmc_polish.py --mode sweep \\
    --base-vh EVQLV... --base-vl DIQMT... \\
    --out-dir projects/humira_cmc_analysis/deepfr_ctx_cmc_polish

  # Multi-source panel (aligned lengths)
  python scripts/run_deepfr_ctx_cmc_polish.py --mode sources \\
    --base-vh ... --base-vl ... --sources-json donors.json \\
    --out-dir projects/my_proj/deepfr_polish
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.cmc.adi_score import compute_adi
from core.cmc.cmc_metrics import CMCMetricEngine
from core.cmc.regular_ab_developability import load_effective_primary_reference, _normalize_origin
from core.humanization.hpr_index import compute_hpr_index
from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys

NGLYC_RE = re.compile(r"N[^P][ST]")

# Small biochem neighborhood for sweep mode (not a frozen standard; engineering convenience).
_CONSERVATIVE_SUBS: Dict[str, List[str]] = {
    "A": ["S", "T", "V"],
    "D": ["E", "N"],
    "E": ["D", "Q"],
    "F": ["Y", "L"],
    "G": ["A", "S"],
    "H": ["Q", "N", "Y"],
    "I": ["L", "V"],
    "K": ["R", "Q"],
    "L": ["I", "V", "M"],
    "M": ["L", "I"],
    "N": ["D", "S", "Q"],
    "Q": ["E", "N"],
    "R": ["K", "Q"],
    "S": ["T", "N"],
    "T": ["S", "A"],
    "V": ["I", "A"],
    "W": ["Y", "F"],
    "Y": ["F", "H"],
}


def _is_sdab_origin(origin: str) -> bool:
    o = str(origin or "").lower()
    return "vhh" in o or "engineered_vh" in o or "atlas24" in o


def _normalize_smart_origin(origin: str) -> str:
    o = (origin or "").strip().lower().replace("-", "_").replace(" ", "_")
    if o in {"humanized_vhh", "clinical_vhh", "vhh_humanized"}:
        return "humanized_vhh"
    if o in {"engineered_vh", "atlas24", "atlas24_engvh", "eng_vh"}:
        return "engineered_vh"
    if o in {"dog", "canine", "dog_clinical"}:
        return "dog_clinical"
    if o in {"cat", "feline", "cat_clinical"}:
        return "cat_clinical"
    return _normalize_origin(origin)


def _chain_fr_indices(seq: str, chain: str) -> List[int]:
    if not seq:
        return []
    kd = get_kabat_numbering(seq)
    keys = sorted_keys(kd)
    fr_indices: List[int] = []
    for i, key in enumerate(keys):
        pos = key[0]
        if chain == "VH":
            in_cdr = (26 <= pos <= 35) or (50 <= pos <= 65) or (95 <= pos <= 102)
        else:
            in_cdr = (24 <= pos <= 34) or (50 <= pos <= 56) or (89 <= pos <= 97)
        if not in_cdr:
            fr_indices.append(i)
    return fr_indices


def _metrics(vh: str, vl: str, ref_metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not vl:
        # Single-chain VHH mode
        from core.cmc.vhh_cmc_engine import compute_vhh_metrics_full, compute_flags, compute_adi_vhh
        m = compute_vhh_metrics_full(vh)
        flags = compute_flags(m)
        rm = {
            "pI": m.get("pI"),
            "GRAVY": m.get("GRAVY"),
            "instability_index": m.get("instability_index"),
            "net_charge_pH7": m.get("net_charge_pH7"),
            "hydro_patch_max9": m.get("hydro_patch_max9"),
            "charge_patch_max7": m.get("charge_patch_max7"),
            "SAP_score": m.get("SAP_score"),
            "Fv_charge_asymmetry": 0.0, # N/A for VHH
            "agg_motifs": m.get("agg_motifs"),
            "hydro_cluster_count": m.get("hydro_cluster_count"),
            "n_deamidation": m.get("deamidation_sites", 0),
            "n_isomerization": m.get("isomerization_sites", 0),
            "n_glyc": m.get("glycosylation_sites", 0),
            "n_oxidation": m.get("oxidation_sites", 0),
            "n_free_cys": m.get("free_cys", 0),
            "ADI": compute_adi_vhh(flags),
        }
        return rm

    m = CMCMetricEngine.compute_metrics(vh, vl)
    rm = {
        "pI": m.get("pI"),
        "GRAVY": m.get("GRAVY"),
        "instability_index": m.get("instability_index"),
        "net_charge_pH7": m.get("net_charge_pH7"),
        "hydro_patch_max9": m.get("hydro_patch_max9"),
        "charge_patch_max7": m.get("charge_patch_max7"),
        "SAP_score": m.get("SAP_score"),
        "Fv_charge_asymmetry": m.get("Fv_charge_asymmetry"),
        "agg_motifs": m.get("agg_motifs"),
        "hydro_cluster_count": m.get("hydro_cluster_count"),
        "n_deamidation": len(m.get("deamidation_sites") or []),
        "n_isomerization": len(m.get("isomerization_sites") or []),
        "n_glyc": len(m.get("glycosylation_sites") or []),
        "n_oxidation": len(m.get("oxidation_sites") or []),
        "n_free_cys": len(m.get("free_cys") or []),
    }
    try:
        rm["ADI"] = round(float(compute_adi(rm, ref_metrics=ref_metrics)), 2)
    except Exception:
        rm["ADI"] = None
    return rm


def _apply(base_vh: str, base_vl: str, muts: Iterable[Tuple[str, int, str, str]]) -> Tuple[str, str]:
    vh = list(base_vh)
    vl = list(base_vl)
    for chain, idx, old, new in muts:
        arr = vh if chain == "VH" else vl
        if arr[idx] != old:
            raise ValueError(f"{chain}{idx}: expected {old}, observed {arr[idx]}")
        arr[idx] = new
    return "".join(vh), "".join(vl)


def _safe_candidate(base_seq: str, idx: int, old: str, new: str) -> bool:
    if old == new:
        return False
    if old in {"C", "P", "G"} or new in {"C", "P", "G"}:
        return False
    mutated = base_seq[:idx] + new + base_seq[idx + 1:]
    return set(m.start() for m in NGLYC_RE.finditer(mutated)) <= set(
        m.start() for m in NGLYC_RE.finditer(base_seq)
    )


def _build_candidates_sources(
    base_vh: str,
    base_vl: str,
    variants: Dict[str, Dict[str, str]],
) -> List[Tuple[str, int, str, str, str]]:
    fr_vh = set(_chain_fr_indices(base_vh, "VH"))
    fr_vl = set(_chain_fr_indices(base_vl, "VL"))

    candidates: List[Tuple[str, int, str, str, str]] = []
    seen = set()
    for source_name, pair in variants.items():
        src_vh = (pair.get("vh") or "").strip().upper()
        src_vl = (pair.get("vl") or "").strip().upper()
        for chain, base_seq, src_seq, fr_idxs in [
            ("VH", base_vh, src_vh, fr_vh),
            ("VL", base_vl, src_vl, fr_vl),
        ]:
            if len(base_seq) != len(src_seq):
                continue
            for idx, (old, new) in enumerate(zip(base_seq, src_seq)):
                key = (chain, idx, old, new)
                if idx in fr_idxs and key not in seen and _safe_candidate(base_seq, idx, old, new):
                    candidates.append((chain, idx, old, new, source_name))
                    seen.add(key)
    return candidates


def _build_candidates_sweep(base_vh: str, base_vl: str) -> List[Tuple[str, int, str, str, str]]:
    """Enumerate conservative substitutions at FR positions (virtual source: conservative_sweep)."""
    fr_vh = set(_chain_fr_indices(base_vh, "VH"))
    fr_vl = set(_chain_fr_indices(base_vl, "VL"))
    out: List[Tuple[str, int, str, str, str]] = []
    seen = set()
    for chain, seq, fr_idxs in [
        ("VH", base_vh, fr_vh),
        ("VL", base_vl, fr_vl),
    ]:
        for idx in fr_idxs:
            old = seq[idx]
            for new in _CONSERVATIVE_SUBS.get(old, []):
                key = (chain, idx, old, new)
                if key in seen:
                    continue
                if not _safe_candidate(seq, idx, old, new):
                    continue
                seen.add(key)
                out.append((chain, idx, old, new, "conservative_sweep"))
    return out


def _score_single(
    base_m: Dict[str, Any],
    m: Dict[str, Any],
    *,
    fv_weight: float,
    ref_metrics: Optional[Dict[str, Any]] = None,
) -> Tuple[float, float, float]:
    instab_delta = float(base_m["instability_index"]) - float(m["instability_index"])
    adi_delta = float(m.get("ADI") or 0) - float(base_m.get("ADI") or 0)
    fv_delta = float(base_m.get("Fv_charge_asymmetry") or 0) - float(m.get("Fv_charge_asymmetry") or 0)

    # Origin-aware danger zone boost: if a metric is in the danger zone (>p95) for this origin,
    # and the mutation improves it, give a 2.0x weight boost to that delta.
    boost = 1.0
    if ref_metrics:
        # Check Fv charge asymmetry specifically as it is often a hard-gate failure
        asym_ref = ref_metrics.get("Fv_charge_asymmetry", {})
        p95 = asym_ref.get("p95")
        if p95 is not None and float(base_m.get("Fv_charge_asymmetry") or 0) > p95 and fv_delta > 0:
            boost = 2.0

    score = instab_delta + 0.25 * adi_delta + (fv_weight * boost) * max(0.0, fv_delta)
    return score, instab_delta, fv_delta


def _run_combo_search(
    base_vh: str,
    base_vl: str,
    base_m: Dict[str, Any],
    base_hpr: float,
    top: Sequence[Dict[str, Any]],
    max_combo: int,
    max_pick: int,
    ref_metrics: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    combo_rows: List[Dict[str, Any]] = []
    mutations_pool = [x["mutation"] for x in top[:max_pick]]
    for r in range(1, min(max_combo, len(mutations_pool)) + 1):
        for combo in itertools.combinations(mutations_pool, r):
            positions = {(c[0], c[1]) for c in combo}
            if len(positions) != len(combo):
                continue
            vh, vl = _apply(base_vh, base_vl, [(c[0], c[1], c[2], c[3]) for c in combo])
            m = _metrics(vh, vl, ref_metrics=ref_metrics)
            if (m.get("n_glyc") or 0) > (base_m.get("n_glyc") or 0):
                continue
            
            if not vl:
                # VHH mode
                from core.cmc.igg_hpr_ablang import compute_vhh_cmc_hpr_ablang
                hpr_index = compute_vhh_cmc_hpr_ablang(vh).get("hpr_index") or {}
                hpr = (hpr_index.get("combined") or {}).get("score") or 0.0
            else:
                hpr = compute_hpr_index(vh, vl)["combined"]["score"]
            if vl and float(hpr) < 0.80:
                continue
            instab_delta = float(base_m["instability_index"]) - float(m["instability_index"])
            
            # Allow combinations that improve Fv_charge_asymmetry even if instability delta is zero
            fv_delta = float(base_m.get("Fv_charge_asymmetry") or 0) - float(m.get("Fv_charge_asymmetry") or 0)
            
            if instab_delta <= 0 and fv_delta <= 0.001:
                continue

            # Scoring with origin-aware HPR and ADI
            score = (
                instab_delta
                + 0.4 * (float(m.get("ADI") or 0) - float(base_m.get("ADI") or 0))
                + 5.0 * (float(hpr) - float(base_hpr))
                + 2.0 * max(0.0, fv_delta) # Explicit combo boost for asymmetry
                - 0.25 * len(combo)
            )
            combo_rows.append({
                "combo": combo,
                "vh": vh,
                "vl": vl,
                "metrics": m,
                "hpr_combined": round(float(hpr), 4),
                "instab_delta": round(instab_delta, 3),
                "fv_charge_asym_delta": round(fv_delta, 4),
                "score": round(score, 3),
            })
    if not combo_rows:
        raise RuntimeError(
            "No valid combination improved instability index while preserving HPR≥0.80. "
            "Try --mode sweep with --fv-weight higher, add more sources, or relax filters in code."
        )
    combo_rows.sort(key=lambda x: (-x["score"], -x["instab_delta"], -x["hpr_combined"]))
    return combo_rows, combo_rows[0]


def main() -> None:
    ap = argparse.ArgumentParser(description="DeepFR-CTX-CMC FR-only polish (general CLI)")
    ap.add_argument("--mode", choices=("sources", "sweep"), required=True)
    ap.add_argument("--base-vh", type=str, help="Base VH sequence")
    ap.add_argument("--base-vl", type=str, help="Base VL sequence")
    ap.add_argument(
        "--snapshot-json",
        type=Path,
        help="Optional: read vh_sequence / vl_sequence from IgG CMC snapshot JSON",
    )
    ap.add_argument(
        "--sources-json",
        type=Path,
        help='JSON: {"VariantA": {"vh":"...","vl":"..."}, ...} (aligned lengths)',
    )
    ap.add_argument(
        "--origin",
        type=str,
        default="humanized",
        help="Antibody origin for reference ranges (e.g. natural384_phage_display, transgenic_animal, engineered)",
    )
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--top-singles", type=int, default=14, help="Cap singles feeding combo search")
    ap.add_argument("--max-combo", type=int, default=3)
    ap.add_argument(
        "--fv-weight",
        type=float,
        default=0.08,
        help="Extra score weight for reducing Fv_charge_asymmetry (sweep ranking)",
    )
    ap.add_argument(
        "--allow-fv-only-improvement",
        action="store_true",
        help="Include singles that reduce Fv_charge_asymmetry even if instability unchanged",
    )
    args = ap.parse_args()

    if args.snapshot_json:
        snap = json.loads(args.snapshot_json.read_text(encoding="utf-8"))
        base_vh = (snap.get("vh_sequence") or "").strip().upper()
        base_vl = (snap.get("vl_sequence") or "").strip().upper()
    else:
        base_vh = (args.base_vh or "").strip().upper()
        base_vl = (args.base_vl or "").strip().upper()

    norm_origin = _normalize_smart_origin(args.origin)
    is_sdab = _is_sdab_origin(norm_origin)

    if len(base_vh) < 80 or (not is_sdab and len(base_vl) < 70):
        raise SystemExit("Provide --base-vh/--base-vl, or base VH only for sdAb origins.")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "sources":
        if not args.sources_json:
            raise SystemExit("--mode sources requires --sources-json")
        variants = json.loads(args.sources_json.read_text(encoding="utf-8"))
        if not isinstance(variants, dict):
            raise SystemExit("sources-json must be an object mapping label -> {vh, vl}")
        candidates = _build_candidates_sources(base_vh, base_vl, variants)
    else:
        candidates = _build_candidates_sweep(base_vh, base_vl)

    # Load origin-aware reference metrics
    if is_sdab:
        from core.cmc.vhh_cmc_engine import get_sdab_origin_ref, load_vhh_ref
        ref_path = get_sdab_origin_ref(norm_origin)
        ref_data = {"_meta": {"name": ref_path.name}, "metrics": load_vhh_ref(ref_path)}
    else:
        ref_data = load_effective_primary_reference(norm_origin)
    ref_metrics = ref_data.get("metrics", {}) if isinstance(ref_data, dict) else {}

    base_m = _metrics(base_vh, base_vl, ref_metrics=ref_metrics)
    if not base_vl:
        from core.cmc.igg_hpr_ablang import compute_vhh_cmc_hpr_ablang
        hpr_index = compute_vhh_cmc_hpr_ablang(base_vh).get("hpr_index") or {}
        base_hpr = float((hpr_index.get("combined") or {}).get("score") or 0.0)
    else:
        base_hpr = float(compute_hpr_index(base_vh, base_vl)["combined"]["score"])

    scored_singles: List[Dict[str, Any]] = []
    for cand in candidates:
        chain, idx, old, new, src = cand
        vh, vl = _apply(base_vh, base_vl, [(chain, idx, old, new)])
        m = _metrics(vh, vl, ref_metrics=ref_metrics)
        score, instab_delta, fv_delta = _score_single(base_m, m, fv_weight=args.fv_weight, ref_metrics=ref_metrics)
        keep = instab_delta > 0
        if args.allow_fv_only_improvement and fv_delta > 0.01:
            keep = True
        if not keep:
            continue
        scored_singles.append({
            "mutation": cand,
            "metrics": m,
            "instab_delta": round(instab_delta, 3),
            "fv_charge_asym_delta": round(fv_delta, 4),
            "score": round(score, 3),
        })

    scored_singles.sort(key=lambda x: (-x["score"], -x["instab_delta"]))
    top = scored_singles[: args.top_singles]

    if not top:
        raise RuntimeError(
            "No improving single mutations under current filters. "
            "Try --mode sweep --allow-fv-only-improvement, increase --fv-weight, "
            "or supply richer --sources-json."
        )

    combo_rows, best = _run_combo_search(
        base_vh,
        base_vl,
        base_m,
        base_hpr,
        top,
        max_combo=args.max_combo,
        max_pick=args.top_singles,
        ref_metrics=ref_metrics,
    )

    payload: Dict[str, Any] = {
        "algorithm": "DeepFR-CTX-CMC",
        "component_role": "candidate_generator_only",
        "final_decision_owner": "smart_cmc_orchestrator_or_owner_workflow",
        "scope": "general FR-only mini-CMC polish (CLI)",
        "mode": args.mode,
        "origin": norm_origin,
        "note_deprecated_alias": "DeepFR-CTX-CM is deprecated; use DeepFR-CTX-CMC naming in deliverables.",
        "base_metrics": {**base_m, "HPR_combined": round(float(base_hpr), 4)},
        "candidate_count": len(candidates),
        "top_single_mutations": scored_singles[:40],
        "selected_combo": {
            "mutations": [
                {
                    "chain": c[0],
                    "linear_index_0based": c[1],
                    "from": c[2],
                    "to": c[3],
                    "source_variant": c[4],
                }
                for c in best["combo"]
            ],
            "metrics": best["metrics"],
            "HPR_combined": best["hpr_combined"],
            "instab_delta": best["instab_delta"],
            "score": best["score"],
        },
        "all_combo_candidates_top": combo_rows[:15],
    }

    result_out = {
        "algorithm": "DeepFR-CTX-CMC",
        "vh": best["vh"],
        "vl": best["vl"],
        "polish_meta": payload["selected_combo"],
    }

    (args.out_dir / "deepfr_ctx_cmc_scan.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    (args.out_dir / "polish_result.json").write_text(
        json.dumps(result_out, indent=2), encoding="utf-8"
    )

    sm = payload["selected_combo"]["metrics"]
    lines = [
        "# DeepFR-CTX-CMC polish scan",
        "",
        f"Mode: **{args.mode}**",
        f"Origin: **{norm_origin}**",
        "",
        "## Optimization Rules (Origin-Aware)",
        f"- **Reference Cohort**: {norm_origin} (n={ref_data.get('n_count', 'unknown')})",
        "- **Primary Objective**: Reduce Instability Index < 40.0",
        "- **Secondary Objective**: Reduce Fv charge asymmetry (danger zone > p95)",
        "- **Guardrails**: Preserve HPR Index ≥ 0.80; No new N-glyc; No C/P/G backbone changes",
        "- **Substitution Logic**: Conservative biochemical neighborhood (DeepFR sweep)",
        "",
        f"Base Instab: {base_m['instability_index']} | Base ADI: {base_m['ADI']} | Base HPR: {round(float(base_hpr), 4)}",
        f"Base Fv charge asymmetry: {base_m.get('Fv_charge_asymmetry')}",
        "",
        "## Selected DeepFR-CTX-CMC candidate",
        "",
        "| Mutation | Source |",
        "|---|---|",
    ]
    for c in payload["selected_combo"]["mutations"]:
        lines.append(
            f"| {c['chain']}[{c['linear_index_0based']}] {c['from']}->{c['to']} | {c['source_variant']} |"
        )
    lines += [
        "",
        "## mini-CMC (selected)",
        "",
        "| Metric | Base | Polished |",
        "|---|---:|---:|",
        f"| Instability index | {base_m['instability_index']} | {sm['instability_index']} |",
        f"| ADI | {base_m['ADI']} | {sm['ADI']} |",
        f"| HPR combined | {round(float(base_hpr), 4)} | {payload['selected_combo']['HPR_combined']} |",
        f"| Fv charge asymmetry | {base_m.get('Fv_charge_asymmetry')} | {sm.get('Fv_charge_asymmetry')} |",
        f"| pI | {base_m['pI']} | {sm['pI']} |",
        "",
        "**Next step:** evaluate candidates in Smart-CMC or equivalent guarded policy layer.",
        "This script generates candidates only and does not produce final release decisions.",
    ]
    (args.out_dir / "DEEPFR_CTX_CMC_SCAN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nWrote {args.out_dir / 'deepfr_ctx_cmc_scan.json'}")
    print(f"Wrote {args.out_dir / 'polish_result.json'}")
    print(f"Wrote {args.out_dir / 'DEEPFR_CTX_CMC_SCAN.md'}")


if __name__ == "__main__":
    main()
