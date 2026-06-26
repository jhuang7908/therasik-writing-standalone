#!/usr/bin/env python3
"""
Smart-CMC orchestrator (phase-1 standalone CLI).

Purpose
-------
Unify origin-aware CMC drift detection and FR-only repair selection while
keeping humanization and CMC responsibilities separated.

This script is a policy/orchestration layer and does not change locked
standards, thresholds, or reference databases.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import html as html_module
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.cmc.cmc_metrics import CMCMetricEngine
from core.cmc.regular_ab_developability import (  # noqa: E402
    HARD_FAIL_PARAMETERS,
    build_regular_ab_developability,
    load_effective_primary_reference,
    _normalize_origin,
)
from core.cmc.vhh_cmc_engine import (
    evaluate_single_vhh,
    compute_vhh_metrics_full,
)
from core.vh2vhh.abnativ_naturalness_layer import score_naturalness_delta
from core.humanization.hpr_index import compute_hpr_index  # noqa: E402
from core.cmc.igg_hpr_ablang import compute_igg_cmc_hpr_ablang
from core.cmc.igg_structural_metrics import compute_igg_structural_metrics
from core.immunogenicity.mhcii_analyzer import MHCII_Analyzer
from core.humanization.kabat_utils import kabat_from_anarcii, cdr_span

SMART_CMC_PROTOCOL_VERSION = "5.2.0"
SMART_CMC_ANALYSIS_VERSION = "5.2.0"
SMART_CMC_REPORT_FORMAT_VERSION = "4.2.6"
DEFAULT_INSTABILITY_SAFE_CEILING = 38.0


def _analysis_track_from_origin(origin: str) -> str:
    o = str(origin or "").lower()
    if "phage" in o:
        return "smart-cmc-phagedisplay"
    if "transgenic" in o:
        return "smart-cmc-transgenic"
    if "single_b_cell" in o or "b_cell" in o:
        return "smart-cmc-single-b-cell"
    if "engineered_vh" in o or "atlas24" in o:
        return "smart-cmc-engineered-vh"
    if "humanized_vhh" in o or "clinical_vhh" in o:
        return "smart-cmc-humanized-vhh"
    if "engineer" in o:
        return "smart-cmc-engineered"
    if "dog" in o or "canine" in o:
        return "smart-cmc-dog-clinical"
    if "cat" in o or "feline" in o:
        return "smart-cmc-cat-clinical"
    return "smart-cmc-regular-vhvl"


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


def _effective_max_adi_drop(base_adi: float, configured_drop: float) -> float:
    if base_adi < 60.0:
        return 0.0
    if base_adi < 80.0:
        return min(configured_drop, 0.5)
    return configured_drop


def _effective_abnativ_floor(origin: str, configured_floor: Optional[float]) -> Optional[float]:
    if configured_floor is not None:
        return configured_floor
    o = str(origin or "").lower()
    if "humanized_vhh" in o or "clinical_vhh" in o:
        return 0.013
    if "engineered_vh" in o or "atlas24" in o:
        return 0.0
    return None


def _evaluate_sdab_block(seq: str, origin: str) -> Dict[str, Any]:
    # 1) Basic CMC metrics
    eval_res = evaluate_single_vhh(name="candidate", seq=seq, origin=origin)
    
    # 2) AbNatiV delta
    ab_res = score_naturalness_delta(seq)
    
    # 3) HPR
    from core.cmc.igg_hpr_ablang import compute_vhh_cmc_hpr_ablang
    hpr_res = compute_vhh_cmc_hpr_ablang(seq)
    hpr_index = hpr_res.get("hpr_index") or {}
    hpr_combined = hpr_index.get("combined") or {}
    
    return {
        "vh_sequence": seq,
        "vl_sequence": "",
        "raw_metrics": eval_res["metrics"],
        "sdab_developability": eval_res,
        "abnativ_delta": round(float(ab_res.delta), 4) if ab_res.delta is not None else None,
        "abnativ_tier": ab_res.tier,
        "hpr_combined": round(_safe_float(hpr_combined.get("score"), 0.0), 4),
        "overall_status": eval_res["overall_status"],
        "adi_score": eval_res["adi_score"],
    }


def _status_rank(status: Optional[str]) -> int:
    table = {"PASS": 0, "WARN": 1, "FAIL": 2, "NOT_RUN": 3}
    return table.get((status or "NOT_RUN").upper(), 3)


def _risk_rank(risk: Optional[str]) -> int:
    table = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "NOT_RUN": 3}
    return table.get((risk or "NOT_RUN").upper(), 3)


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _compute_raw_metrics(vh: str, vl: str) -> Dict[str, Any]:
    m = CMCMetricEngine.compute_metrics(vh, vl)
    return {
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
        "glycosylation_sites": m.get("glycosylation_sites") or [],
        "deamidation_sites": m.get("deamidation_sites") or [],
        "isomerization_sites": m.get("isomerization_sites") or [],
        "oxidation_sites": m.get("oxidation_sites") or [],
        "free_cys": m.get("free_cys") or [],
        "psh": m.get("psh"),
        "ppc": m.get("ppc"),
        "pnc": m.get("pnc"),
        "sfvcsp": m.get("sfvcsp"),
        "vh_vl_angle_deg": m.get("vh_vl_angle_deg"),
        "interface_n_pairs": m.get("interface_n_pairs"),
        "interface_mean_dist_A": m.get("interface_mean_dist_A"),
        "interface_min_dist_A": m.get("interface_min_dist_A"),
        "vernier_sasa_total": m.get("vernier_sasa_total"),
    }


def _evaluate_regular_block(vh: str, vl: str, origin: str, fv_pdb_path: Optional[Path] = None) -> Dict[str, Any]:
    raw = _compute_raw_metrics(vh, vl)
    if fv_pdb_path and fv_pdb_path.exists():
        # Re-compute metrics with PDB
        m = compute_igg_structural_metrics(str(fv_pdb_path), vh_seq=vh, vl_seq=vl)
        for k, v in m.items():
            if v is not None:
                raw[k] = v
    
    # 1) IMGT segmentation & Germline
    imgt_seg = {}
    germline = {}
    try:
        from anarcii import ANARCII
        a = ANARCII()
        num_h = a.to_scheme("imgt", vh)
        num_l = a.to_scheme("imgt", vl)
        
        def _extract_imgt(num_res):
            if not num_res or "Sequence 1" not in num_res:
                return {}
            try:
                from core.vhh_humanization import split_regions as split_regions_imgt
                return split_regions_imgt(num_res["Sequence 1"]["numbering"])
            except:
                return {}

        def _extract_germline(num_res):
            if not num_res or "Sequence 1" not in num_res:
                return {}
            return {
                "top_match": num_res["Sequence 1"].get("v_gene"),
                "top_match_id": num_res["Sequence 1"].get("v_gene"),
            }

        imgt_seg = {
            "VH": _extract_imgt(num_h),
            "VL": _extract_imgt(num_l)
        }
        germline = {
            "VH": _extract_germline(num_h),
            "VL": _extract_germline(num_l)
        }
    except:
        pass

    # 2) TCIA
    tcia_score = None
    tcia_risk = None
    try:
        tcia_res = MHCII_Analyzer.analyze_sequence(vh + vl)
        tcia_score = tcia_res.get("score")
        tcia_risk = tcia_res.get("risk_level")
    except:
        pass

    # 3) HPR & AbLang2
    hpr_abl = compute_igg_cmc_hpr_ablang(vh, vl)
    
    # 4) p-AbNatiV2 Pairing Guard
    try:
        from core.humanization.p_abnativ_layer import score_paired_humanness
        p_abnativ = score_paired_humanness(vh, vl)
    except:
        p_abnativ = None
    
    block = build_regular_ab_developability(
        vh_seq=vh,
        vl_seq=vl,
        origin=origin,
        raw_metrics=raw,
        cdr_liabilities=[],
        germline=germline,
        mutation_suggestions=[],
        fv_pdb_path=fv_pdb_path,
    )
    
    return {
        "vh_sequence": vh,
        "vl_sequence": vl,
        "raw_metrics": raw,
        "regular_ab_developability": block,
        "fv_pdb_path": str(fv_pdb_path) if fv_pdb_path else None,
        "hpr_index": hpr_abl.get("hpr_index"),
        "hpr_combined": round(_safe_float(hpr_abl.get("hpr_index", {}).get("combined", {}).get("score"), 0.0), 4),
        "tcia_score": tcia_score,
        "tcia_risk_level": tcia_risk,
        "ablang_score": hpr_abl.get("ablang_score"),
        "imgt_segmentation": imgt_seg,
        "overall_status": block.get("overall_gate_status"),
        "developability_index": block.get("developability_index"),
        "clinical_score": block.get("clinical_score"),
        "overall_flags": block.get("overall_flags") or [],
        "pI_fab": raw.get("pI"),
        "GRAVY": raw.get("GRAVY"),
        "instability_index": raw.get("instability_index"),
        "p_abnativ2": {
            "vh_humanness": p_abnativ.vh_humanness if p_abnativ else None,
            "vl_humanness": p_abnativ.vl_humanness if p_abnativ else None,
            "paired_humanness": p_abnativ.paired_humanness if p_abnativ else None,
            "pairing_likelihood": p_abnativ.pairing_likelihood if p_abnativ else None,
        } if p_abnativ else None,
    }


def _extract_drift_parameters(block: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in block.get("parameters") or []:
        key = str(p.get("key") or "")
        gate = str(p.get("gate_status") or "NOT_RUN")
        risk = str(p.get("risk") or "NOT_RUN")
        if gate not in {"FAIL", "WARN"} and risk not in {"HIGH", "MODERATE"}:
            continue
        priority = 0
        if key in HARD_FAIL_PARAMETERS:
            priority += 3
        if gate == "FAIL":
            priority += 2
        elif gate == "WARN":
            priority += 1
        if risk == "HIGH":
            priority += 2
        elif risk == "MODERATE":
            priority += 1
        out.append(
            {
                "key": key,
                "label": p.get("label"),
                "value": p.get("value"),
                "risk": risk,
                "gate_status": gate,
                "range_position": p.get("range_position"),
                "priority": priority,
                "hard_fail_parameter": key in HARD_FAIL_PARAMETERS,
            }
        )
    out.sort(key=lambda x: (-x["priority"], x["key"]))
    return out


@dataclass
class GuardResult:
    passed: bool
    reasons: List[str]
    evidence: Dict[str, Any]
    score: float


def _apply_balanced_guard(
    baseline: Dict[str, Any],
    candidate: Dict[str, Any],
    *,
    origin: str,
    mutation_count: int,
    allow_soft_regressions: int,
    max_instability_regression: float,
    instability_safe_ceiling: float,
    max_hpr_drop: float,
    max_adi_drop: float,
    max_mutations: int,
    abnativ_floor: Optional[float],
) -> GuardResult:
    reasons: List[str] = []
    evidence: Dict[str, Any] = {}
    soft_regressions = 0
    
    o = origin.lower()
    is_sdab = _is_sdab_origin(o)
    evidence["mutation_count"] = mutation_count
    evidence["max_mutations"] = max_mutations
    if mutation_count > max_mutations:
        reasons.append("mutation_count_exceeds_limit")
    
    if is_sdab:
        base_block = baseline["sdab_developability"]
        cand_block = candidate["sdab_developability"]
        base_adi = _safe_float(baseline.get("adi_score"))
        cand_adi = _safe_float(candidate.get("adi_score"))
        base_abnativ = _safe_float(baseline.get("abnativ_delta"), -1.0)
        cand_abnativ = _safe_float(candidate.get("abnativ_delta"), -1.0)
        
        evidence["adi_base"] = base_adi
        evidence["adi_candidate"] = cand_adi
        evidence["abnativ_base"] = base_abnativ
        evidence["abnativ_candidate"] = cand_abnativ
        evidence["abnativ_floor"] = abnativ_floor
        if abnativ_floor is not None and cand_abnativ < abnativ_floor:
            reasons.append("abnativ_below_origin_floor")
        allowed_adi_drop = _effective_max_adi_drop(base_adi, max_adi_drop)
        evidence["max_adi_drop_effective"] = allowed_adi_drop
        if cand_adi < base_adi - allowed_adi_drop:
            reasons.append("adi_drop_beyond_dynamic_limit")
        
        # Track B: Humanized VHH
        if "humanized_vhh" in o:
            if cand_adi < base_adi:
                reasons.append("adi_dropped_for_humanized_vhh")
            if cand_abnativ < base_abnativ:
                reasons.append("abnativ_dropped_for_humanized_vhh")
        
        # Track C: Engineered VH
        if "engineered_vh" in o or "atlas24" in o:
            cand_agg = _safe_float(candidate["raw_metrics"].get("agg_motifs"), 0.0)
            if cand_agg > 0:
                reasons.append("agg_motifs_not_zero_for_engineered_vh")
            if cand_abnativ < 0:
                reasons.append("abnativ_delta_negative_for_engineered_vh")
                
        # Composite score for sdAb
        score = (
            2.0 * (cand_abnativ - base_abnativ)
            + 1.0 * (cand_adi - base_adi)
            + 0.5 * (
                _safe_float(baseline["raw_metrics"].get("instability_index"))
                - _safe_float(candidate["raw_metrics"].get("instability_index"))
            )
        )
    else:
        # Track A: Regular VH/VL
        base_block = baseline["regular_ab_developability"]
        cand_block = candidate["regular_ab_developability"]
        
        base_fail = len(base_block.get("hard_gate_failures") or [])
        cand_fail = len(cand_block.get("hard_gate_failures") or [])
        evidence["hard_gate_failures_base"] = base_fail
        evidence["hard_gate_failures_candidate"] = cand_fail
        if cand_fail > base_fail:
            reasons.append("hard_gate_failures_increased")

        base_gate = str(base_block.get("overall_gate_status") or "NOT_RUN")
        cand_gate = str(cand_block.get("overall_gate_status") or "NOT_RUN")
        evidence["overall_gate_base"] = base_gate
        evidence["overall_gate_candidate"] = cand_gate
        if _status_rank(cand_gate) > _status_rank(base_gate):
            reasons.append("overall_gate_worsened")

        base_instab = _safe_float(baseline["raw_metrics"].get("instability_index"))
        cand_instab = _safe_float(candidate["raw_metrics"].get("instability_index"))
        evidence["instability_index_base"] = base_instab
        evidence["instability_index_candidate"] = cand_instab
        evidence["instability_delta"] = round(base_instab - cand_instab, 3)
        evidence["instability_safe_ceiling"] = instability_safe_ceiling
        if cand_instab > instability_safe_ceiling and cand_instab > base_instab + max_instability_regression:
            reasons.append("instability_regressed_beyond_limit")

        base_hpr = _safe_float(baseline.get("hpr_combined"))
        cand_hpr = _safe_float(candidate.get("hpr_combined"))
        evidence["hpr_base"] = base_hpr
        evidence["hpr_candidate"] = cand_hpr
        evidence["hpr_delta"] = round(cand_hpr - base_hpr, 4)
        
        # Sub-Track A1/A3/A5: Force HPR not to decrease
        if any(x in o for x in ["fully_human", "phage", "single_b_cell"]):
            if cand_hpr < base_hpr:
                reasons.append("hpr_dropped_for_human_derived_track")
        elif cand_hpr < base_hpr - max_hpr_drop:
            reasons.append("hpr_drop_beyond_limit")

        # Track A: p-AbNatiV2 Pairing Likelihood Non-Regression
        base_pairing = _safe_float(baseline.get("p_abnativ2", {}).get("pairing_likelihood"), -1.0)
        cand_pairing = _safe_float(candidate.get("p_abnativ2", {}).get("pairing_likelihood"), -1.0)
        evidence["pairing_likelihood_base"] = base_pairing
        evidence["pairing_likelihood_candidate"] = cand_pairing
        evidence["pairing_likelihood_delta"] = round(cand_pairing - base_pairing, 4) if base_pairing != -1.0 else 0.0
        
        # Max acceptable drop in pairing likelihood (e.g. 0.05)
        MAX_PAIRING_DROP = 0.05
        if base_pairing > 0 and cand_pairing < base_pairing - MAX_PAIRING_DROP:
            reasons.append("pairing_likelihood_drop_beyond_limit")

        base_adi = _safe_float(base_block.get("developability_index"))
        cand_adi = _safe_float(cand_block.get("developability_index"))
        evidence["adi_base"] = base_adi
        evidence["adi_candidate"] = cand_adi
        evidence["adi_delta"] = round(cand_adi - base_adi, 3)
        allowed_adi_drop = _effective_max_adi_drop(base_adi, max_adi_drop)
        evidence["max_adi_drop_effective"] = allowed_adi_drop
        
        # Sub-Track A2: Transgenic - Force ADI not to decrease
        if "transgenic" in o:
            if cand_adi < base_adi:
                reasons.append("adi_dropped_for_transgenic_track")
        elif cand_adi < base_adi - allowed_adi_drop:
            reasons.append("adi_drop_beyond_limit")
        elif cand_adi < base_adi:
            soft_regressions += 1

        base_asym = _safe_float(baseline["raw_metrics"].get("Fv_charge_asymmetry"))
        cand_asym = _safe_float(candidate["raw_metrics"].get("Fv_charge_asymmetry"))
        evidence["fv_charge_asymmetry_base"] = base_asym
        evidence["fv_charge_asymmetry_candidate"] = cand_asym
        evidence["fv_charge_asymmetry_delta"] = round(base_asym - cand_asym, 3)
        if cand_asym > base_asym:
            soft_regressions += 1

        evidence["soft_regressions"] = soft_regressions
        evidence["soft_regressions_allowed"] = allow_soft_regressions
        if soft_regressions > allow_soft_regressions:
            reasons.append("too_many_soft_regressions")

        # Track A4: Murine Humanized - Force ADI increase
        if "murine_humanized" in o or "humanized" == o:
            if cand_adi <= base_adi and cand_fail >= base_fail:
                # Allow if it fixes a hard fail even if ADI doesn't increase
                if not (cand_fail < base_fail):
                    reasons.append("adi_not_increased_for_humanized_murine")

        # Composite score for Track A
        score = (
            1.8 * (base_fail - cand_fail)
            + 1.2 * (_status_rank(base_gate) - _status_rank(cand_gate))
            + 1.0 * (base_instab - cand_instab)
            + 0.6 * (cand_adi - base_adi)
            + 0.9 * (base_asym - cand_asym)
            + 2.0 * (cand_hpr - base_hpr)
        )
        
    evidence["balanced_score"] = round(score, 3)
    if score <= 0 and not is_sdab: # For sdAb, we allow score <= 0 if it fixes something? No, let's keep it strict.
        reasons.append("composite_score_not_improved")
    if is_sdab and score < 0:
        reasons.append("composite_score_regressed")

    return GuardResult(
        passed=(len(reasons) == 0),
        reasons=reasons,
        evidence=evidence,
        score=round(score, 3),
    )


def _opt_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _build_generator_best_polish_comparison(
    baseline_eval: Dict[str, Any],
    polish_result: Dict[str, Any],
    guard_rows: List[Dict[str, Any]],
    selected: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compare DeepFR polish_result.json mini-CMC vs full baseline_eval.
    Always emitted so reports can show charge-asymmetry movement even when
    balanced_guard rejects adoption (primary-score non-regression).
    """
    pm = polish_result.get("polish_meta")
    if not isinstance(pm, dict):
        return {"available": False, "reason": "polish_meta_missing_in_polish_result.json"}

    metrics = pm.get("metrics") or {}
    base_rm = baseline_eval.get("raw_metrics") or {}
    rab = baseline_eval.get("regular_ab_developability") or {}

    base_asym = _opt_float(base_rm.get("Fv_charge_asymmetry"))
    base_adi = _opt_float(rab.get("developability_index"))
    base_hpr = _opt_float(baseline_eval.get("hpr_combined"))
    base_instab = _opt_float(base_rm.get("instability_index"))
    base_pair = _opt_float((baseline_eval.get("p_abnativ2") or {}).get("pairing_likelihood"))

    polish_asym = _opt_float(metrics.get("Fv_charge_asymmetry"))
    polish_adi = _opt_float(metrics.get("ADI"))
    polish_hpr = _opt_float(pm.get("HPR_combined"))
    polish_instab = _opt_float(metrics.get("instability_index"))

    def _delta(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        return round(b - a, 4)

    deltas = {
        "Fv_charge_asymmetry_polish_minus_baseline": _delta(base_asym, polish_asym),
        "ADI_polish_minus_baseline": _delta(base_adi, polish_adi),
        "HPR_polish_minus_baseline": _delta(base_hpr, polish_hpr),
        "instability_index_polish_minus_baseline": _delta(base_instab, polish_instab),
    }

    asym_improved = (
        base_asym is not None
        and polish_asym is not None
        and polish_asym < base_asym - 1e-9
    )
    adi_ok = (
        base_adi is not None
        and polish_adi is not None
        and polish_adi >= base_adi - 1e-9
    )
    hpr_ok = (
        base_hpr is not None
        and polish_hpr is not None
        and polish_hpr >= base_hpr - 1e-9
    )

    combo_row = next((r for r in guard_rows if str(r.get("id")) == "selected_combo"), None)
    combo_reasons = list(combo_row.get("reasons") or []) if isinstance(combo_row, dict) else []
    combo_passed = bool(combo_row.get("passed")) if combo_row else None

    is_fallback = str(selected.get("id")) == "baseline_fallback" or str(selected.get("source")) == "fallback"

    notes: List[str] = []
    if asym_improved and not adi_ok:
        notes.append(
            "Generator-best polish lowers Fv charge asymmetry but mini-CMC ADI is below baseline; "
            "primary-score policy (no ADI regression) prevents adopting this sequence as the delivery candidate."
        )
    if asym_improved and adi_ok and hpr_ok and is_fallback:
        notes.append(
            "Generator-best polish improves asymmetry without ADI/HPR regression vs baseline mini-metrics; "
            "if Smart-CMC still selected fallback, inspect full guard_results_top for composite_score / gate / instability constraints."
        )
    if is_fallback and combo_reasons:
        notes.append(
            "Balanced-guard reasons on evaluated candidate `selected_combo`: "
            + ", ".join(combo_reasons)
            + "."
        )

    return {
        "available": True,
        "role": "informational_comparison_generator_mini_cmc_vs_full_baseline",
        "baseline_primary_indices": {
            "Fv_charge_asymmetry": base_asym,
            "ADI_developability_index": base_adi,
            "HPR_combined": base_hpr,
            "instability_index": base_instab,
            "pairing_likelihood": base_pair,
        },
        "generator_best_polish_mini_cmc": {
            "Fv_charge_asymmetry": polish_asym,
            "ADI": polish_adi,
            "HPR_combined": polish_hpr,
            "instability_index": polish_instab,
            "mutation_count": len(pm.get("mutations") or []),
        },
        "deltas": deltas,
        "generator_best_polish_primary_non_regression": {
            "ADI_not_below_baseline": adi_ok,
            "HPR_not_below_baseline": hpr_ok,
            "Fv_charge_asymmetry_improved": asym_improved,
            "pairing_likelihood_not_in_generator_mini_cmc": True,
        },
        "selected_sequence_is_baseline_fallback": is_fallback,
        "generator_best_candidate_guard_passed": combo_passed,
        "generator_best_candidate_guard_reasons": combo_reasons,
        "interpretation_notes": notes,
    }


def _collect_candidates_from_scan(
    base_vh: str,
    base_vl: str,
    scan_payload: Dict[str, Any],
    polish_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    selected_vh = str(polish_result.get("vh") or "").strip().upper()
    selected_vl = str(polish_result.get("vl") or "").strip().upper()
    
    def _normalize_muts(ms):
        if not ms: return []
        res = []
        for m in ms:
            if isinstance(m, dict):
                res.append({
                    "chain": m.get("chain", "?"),
                    "pos": m.get("linear_index_0based", "?"),
                    "wt": m.get("from", "?"),
                    "mut": m.get("to", "?")
                })
            elif isinstance(m, (list, tuple)) and len(m) >= 4:
                res.append({
                    "chain": m[0],
                    "pos": m[1],
                    "wt": m[2],
                    "mut": m[3]
                })
        return res

    if selected_vh and (selected_vl or not base_vl):
        out.append(
            {
                "id": "selected_combo",
                "source": "deepfr_ctx_cmc_scan.selected_combo",
                "vh": selected_vh,
                "vl": selected_vl,
                "score_hint": _safe_float(scan_payload.get("selected_combo", {}).get("score")),
                "mutation_count": len(scan_payload.get("selected_combo", {}).get("mutations") or []),
                "mutations": _normalize_muts(scan_payload.get("selected_combo", {}).get("mutations")),
            }
        )
    for i, row in enumerate(scan_payload.get("all_combo_candidates_top") or []):
        vh = str(row.get("vh") or "").strip().upper()
        vl = str(row.get("vl") or "").strip().upper()
        if not vh or (base_vl and not vl):
            continue
        if vh == base_vh and vl == base_vl:
            continue
        out.append(
            {
                "id": f"combo_{i + 1}",
                "source": "deepfr_ctx_cmc_scan.all_combo_candidates_top",
                "vh": vh,
                "vl": vl,
                "score_hint": _safe_float(row.get("score")),
                "mutation_count": len(row.get("combo") or []),
                "mutations": _normalize_muts(row.get("combo")),
            }
        )
    # Deduplicate by sequence pair
    dedup: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for c in out:
        key = (c["vh"], c["vl"])
        if key not in dedup or c["score_hint"] > dedup[key]["score_hint"]:
            dedup[key] = c
    return sorted(dedup.values(), key=lambda x: (-x["score_hint"], x["id"]))


def _render_md_report(
    out_path: Path,
    result: Dict[str, Any],
) -> None:
    baseline = result["baseline_snapshot"]
    selected = result.get("selected_candidate") or {}
    versioning = result.get("versioning") or {}
    
    is_sdab = "vhh" in result.get("origin", "").lower() or "engineered_vh" in result.get("origin", "").lower()
    
    lines: List[str] = [
        "# Smart-CMC Audit Report",
        "",
        "## Version Metadata",
        "",
        f"- **Protocol Version**: {versioning.get('protocol_version')}",
        f"- **Analysis Version**: {versioning.get('analysis_version')}",
        f"- **Report Format Version**: {versioning.get('report_format_version')}",
        f"- **Analysis Track**: {versioning.get('analysis_track')}",
        "",
        f"- **Origin**: {result.get('origin')}",
        f"- **Policy**: {result.get('policy', {}).get('name')}",
        f"- **Generator role**: {result.get('generator', {}).get('role')}",
        "",
        "## Baseline",
        "",
        f"- Instability index: {baseline.get('raw_metrics', {}).get('instability_index')}",
    ]
    
    if is_sdab:
        lines += [
            f"- ADI: {baseline.get('adi_score')}",
            f"- HPR combined: {baseline.get('hpr_combined')}",
        ]
    else:
        lines += [
            f"- ADI: {baseline.get('regular_ab_developability', {}).get('developability_index')}",
            f"- HPR combined: {baseline.get('hpr_combined')}",
        ]
    lines += md_lines_naturalness_and_p_abnativ(baseline)
        
    lines += [
        "",
        "## Drift Parameters (Top 10)",
        "",
    ]
    drift = result.get("drift_parameters") or []
    if not drift:
        lines.append("- None")
    else:
        for d in drift[:10]:
            lines.append(
                f"- `{d.get('key')}`: risk={d.get('risk')}, priority={d.get('priority')}"
            )
    lines += [
        "",
        "## Selected Candidate",
        "",
    ]
    if not selected:
        lines.append("- No candidate passed balanced guards.")
    else:
        guard = selected.get("guard_result", {})
        cand_eval = selected.get("evaluation", {})
        lines += [
            f"- Candidate ID: `{selected.get('id')}`",
            f"- Mutation count: {selected.get('mutation_count')}",
            f"- Balanced score: {guard.get('score')}",
            f"- Instability index: {cand_eval.get('raw_metrics', {}).get('instability_index')}",
        ]
        if is_sdab:
            lines += [
                f"- ADI: {cand_eval.get('adi_score')}",
                f"- HPR combined: {cand_eval.get('hpr_combined')}",
            ]
        else:
            lines += [
                f"- ADI: {cand_eval.get('regular_ab_developability', {}).get('developability_index')}",
                f"- HPR combined: {cand_eval.get('hpr_combined')}",
            ]
        lines += md_lines_naturalness_and_p_abnativ(cand_eval)

    cmpb = result.get("generator_best_polish_comparison") or {}
    lines += ["", "## Generator-best polish vs baseline (charge asymmetry tracking)", ""]
    if cmpb.get("available"):
        bpi = cmpb.get("baseline_primary_indices") or {}
        gpi = cmpb.get("generator_best_polish_mini_cmc") or {}
        dz = cmpb.get("deltas") or {}
        lines += [
            f"- Baseline Fv charge asymmetry: **{bpi.get('Fv_charge_asymmetry')}** → Generator-best polish: **{gpi.get('Fv_charge_asymmetry')}** (Δ {dz.get('Fv_charge_asymmetry_polish_minus_baseline')})",
            f"- Baseline ADI: **{bpi.get('ADI_developability_index')}** → Polish mini-CMC ADI: **{gpi.get('ADI')}** (Δ {dz.get('ADI_polish_minus_baseline')})",
            f"- Primary non-regression (mini-CMC): ADI OK={cmpb.get('generator_best_polish_primary_non_regression', {}).get('ADI_not_below_baseline')}, "
            f"HPR OK={cmpb.get('generator_best_polish_primary_non_regression', {}).get('HPR_not_below_baseline')}",
            f"- Selected fallback: **{cmpb.get('selected_sequence_is_baseline_fallback')}**",
        ]
        for n in cmpb.get("interpretation_notes") or []:
            lines.append(f"- Note: {n}")
    else:
        lines.append(f"- ({cmpb.get('reason', 'unavailable')})")

    lines += [
        "",
        "## Non-Regression Evidence",
        "",
    ]
    for row in result.get("guard_results_top") or []:
        lines.append(
            f"- `{row.get('id')}`: passed={row.get('passed')} score={row.get('score')} reasons={','.join(row.get('reasons') or ['none'])}"
        )
    lines += [
        "",
        "## Decision Note",
        "",
        "- Smart-CMC is a policy layer and does not redefine locked standards, thresholds, or reference databases.",
        "- DeepFR-CTX-CMC polish is used as candidate generator only; final decision is made by Smart-CMC guarded policy.",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _report_display_name(result: Dict[str, Any]) -> str:
    dn = result.get("display_name")
    if dn and str(dn).strip():
        return str(dn).strip()
    return "VH/VL reference run"


def _render_console_style_report(
    out_path: Path,
    result: Dict[str, Any],
) -> None:
    baseline = result["baseline_snapshot"]
    selected = result.get("selected_candidate") or {}
    versioning = result.get("versioning") or {}
    drift = result.get("drift_parameters") or []
    vh_wt = baseline.get("vh_sequence") or ""
    vl_wt = baseline.get("vl_sequence") or ""
    disp = _report_display_name(result)
    lines: List[str] = [
        "# Smart-CMC ConsoleStyle Report",
        "",
        "---",
        "",
        "## §0 Overview and Metadata",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Protocol Version | {versioning.get('protocol_version')} |",
        f"| Analysis Version | {versioning.get('analysis_version')} |",
        f"| Report Format Version | {versioning.get('report_format_version')} |",
        f"| Analysis Track | {versioning.get('analysis_track')} |",
        f"| Molecule (report label) | **{disp}** |",
        f"| Origin | {result.get('origin')} |",
        f"| Policy | {result.get('policy', {}).get('name')} |",
        f"| Candidate Generator | {result.get('generator', {}).get('name')} ({result.get('generator', {}).get('role')}) |",
        "",
        "## §0b VH/VL sequences (baseline vs selected)",
        "",
        "*Report format 4.2.2+: original baseline and delivery sequences are both listed; **bold** in selected VH/VL marks substitutions vs baseline when a guarded FR candidate is adopted.*",
        "",
        "### Original (baseline input)",
        "",
        f"- **VH** ({len(vh_wt)} aa): `{vh_wt}`",
        f"- **VL** ({len(vl_wt)} aa): `{vl_wt}`",
        "",
        "### Selected (delivery sequence after Smart-CMC)",
        "",
    ]
    sel_eval = selected.get("evaluation") or {}
    vh_sel = sel_eval.get("vh_sequence") or vh_wt
    vl_sel = sel_eval.get("vl_sequence") or vl_wt
    is_opt_md = bool(selected and selected.get("id") != "baseline_fallback")

    def _md_chain_diff(sel: str, wt: str) -> str:
        if not is_opt_md or sel == wt:
            return sel
        parts: List[str] = []
        for i, aa in enumerate(sel):
            if i < len(wt) and aa != wt[i]:
                parts.append(f"**{aa}**")
            else:
                parts.append(aa)
        return "".join(parts)

    # Do not wrap selected sequences in backticks — Markdown bold would not render inside code spans.
    lines += [
        f"- **VH** ({len(vh_sel)} aa): {_md_chain_diff(vh_sel, vh_wt)}",
        f"- **VL** ({len(vl_sel)} aa): {_md_chain_diff(vl_sel, vl_wt)}",
    ]
    if not is_opt_md:
        lines.append("- *Delivery identical to baseline (fallback — no FR substitutions adopted).*")
    elif vh_sel == vh_wt and vl_sel == vl_wt:
        lines.append("- *Sequences match baseline.*")
    else:
        lines.append("- *Bold residues in selected VH/VL differ from §0b original.*")
    lines += [
        "",
        "## §1 Baseline Snapshot",
        "",
        f"- Instability Index: {baseline.get('raw_metrics', {}).get('instability_index')}",
        f"- ADI: {baseline.get('regular_ab_developability', {}).get('developability_index')}",
        f"- HPR combined: {baseline.get('hpr_combined')}",
    ]
    lines += md_lines_naturalness_and_p_abnativ(baseline)
    lines += [
        "",
        "## §2 Drift Parameters",
        "",
    ]
    if not drift:
        lines.append("- None")
    else:
        for d in drift:
            lines.append(
                f"- `{d.get('key')}`: risk={d.get('risk')}, priority={d.get('priority')}"
            )
    lines += [
        "",
        "## §3 Selected Candidate",
        "",
    ]
    if selected:
        selected_eval = selected.get("evaluation") or {}
        lines += [
            f"- Candidate ID: `{selected.get('id')}`",
            f"- Mutation count: {selected.get('mutation_count')}",
            f"- Guard score: {selected.get('guard_result', {}).get('score')}",
            f"- Instability Index: {selected_eval.get('raw_metrics', {}).get('instability_index')}",
            f"- ADI: {selected_eval.get('regular_ab_developability', {}).get('developability_index')}",
            f"- HPR combined: {selected_eval.get('hpr_combined')}",
        ]
        lines += md_lines_naturalness_and_p_abnativ(selected_eval)
    else:
        lines.append("- No candidate passed guarded policy.")

    cmpb = result.get("generator_best_polish_comparison") or {}
    lines += ["", "## §3b Generator-best FR polish vs baseline (informational)", ""]
    if cmpb.get("available"):
        bpi = cmpb.get("baseline_primary_indices") or {}
        gpi = cmpb.get("generator_best_polish_mini_cmc") or {}
        dz = cmpb.get("deltas") or {}
        chk = cmpb.get("generator_best_polish_primary_non_regression") or {}
        lines += [
            "| Metric | Baseline | Generator-best polish | Δ (polish − baseline) |",
            "|---|---:|---:|---:|",
            f"| Fv charge asymmetry | {bpi.get('Fv_charge_asymmetry')} | {gpi.get('Fv_charge_asymmetry')} | {dz.get('Fv_charge_asymmetry_polish_minus_baseline')} |",
            f"| ADI | {bpi.get('ADI_developability_index')} | {gpi.get('ADI')} | {dz.get('ADI_polish_minus_baseline')} |",
            f"| HPR combined | {bpi.get('HPR_combined')} | {gpi.get('HPR_combined')} | {dz.get('HPR_polish_minus_baseline')} |",
            f"| Instability index | {bpi.get('instability_index')} | {gpi.get('instability_index')} | {dz.get('instability_index_polish_minus_baseline')} |",
            "",
            f"- ADI not below baseline (mini-CMC): **{chk.get('ADI_not_below_baseline')}**",
            f"- HPR not below baseline (mini-CMC): **{chk.get('HPR_not_below_baseline')}**",
            f"- Charge asymmetry improved (lower is better): **{chk.get('Fv_charge_asymmetry_improved')}**",
            f"- Selected sequence is baseline fallback: **{cmpb.get('selected_sequence_is_baseline_fallback')}**",
            "",
        ]
        for n in cmpb.get("interpretation_notes") or []:
            lines.append(f"- {n}")
        gr = cmpb.get("generator_best_candidate_guard_reasons") or []
        if gr:
            lines.append(f"- Guard reasons (`selected_combo`): {', '.join(gr)}")
    else:
        lines.append(f"- ({cmpb.get('reason', 'comparison unavailable')})")

    lines += [
        "",
        "## §4 Non-Regression Evidence",
        "",
    ]
    for row in result.get("guard_results_top") or []:
        lines.append(
            f"- `{row.get('id')}`: passed={row.get('passed')} score={row.get('score')} reasons={','.join(row.get('reasons') or ['none'])}"
        )
    lines += [
        "",
        "## §5 Governance Note",
        "",
        "- This report uses frozen standards and references; no threshold or core standard is redefined.",
        "- DeepFR-CTX-CMC is used for candidate generation only; Smart-CMC policy performs final selection.",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# HTML Rendering Helpers (Ported from render_igg_cmc_snapshot_html.py)
# ─────────────────────────────────────────────────────────────────────────────

CSS = """\
:root{--ok:#059669;--warn:#d97706;--fail:#dc2626;--muted:#6b7280;--bg:#f9fafb;
     --card:#fff;--border:#e5e7eb;--accent:#4f46e5}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:#111;font-size:13px;line-height:1.55}
.page{max-width:900px;margin:0 auto;padding:24px 16px}
.cover{background:linear-gradient(135deg,#1e1b4b,#312e81);color:#fff;border-radius:10px;padding:32px 28px;margin-bottom:24px}
.cover h1{font-size:1.5rem;font-weight:700;margin-bottom:6px}
.cover .sub{font-size:0.85rem;opacity:.88;margin-bottom:12px}
.cover .meta{display:flex;gap:16px;flex-wrap:wrap;font-size:0.78rem;opacity:.82;align-items:center}
.header-meta{width:100%;margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid rgba(255,255,255,.22);
             display:flex;flex-direction:column;gap:4px;font-family:ui-monospace,monospace;font-size:0.72rem;opacity:.75}
.section{background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:16px;overflow:hidden}
.section h3{font-size:0.85rem;font-weight:700;padding:10px 16px;background:#f3f4f6;border-bottom:1px solid var(--border);color:#374151}
.section-body{padding:14px 16px}
table.kv{width:100%;border-collapse:collapse;font-size:0.82rem}
table.kv td{padding:6px 8px;vertical-align:top;border-bottom:1px solid #f3f4f6}
table.kv tr:nth-child(even){background:#f9fafb}
.lbl{color:#6b7280;font-weight:600;width:38%;white-space:nowrap}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:0.72rem;font-weight:700}
.badge-ok{background:#d1fae5;color:#065f46}.badge-warn{background:#fef3c7;color:#92400e}.badge-fail{background:#fee2e2;color:#991b1b}.badge-info{background:#dbeafe;color:#1e40af}
.seq-block{margin:10px 0;background:#f8f9fa;border:1px solid #e9ecef;border-radius:6px;padding:10px 12px}
.seq-label{font-size:0.78rem;font-weight:700;color:#495057;margin-bottom:6px}
.seq-len{font-weight:400;color:#6b7280}
.seq-body{font-family:'Consolas','Courier New',monospace;font-size:0.82em;letter-spacing:.03em;word-break:break-all;line-height:1.7;color:#111}
.data-table{width:100%;border-collapse:collapse;font-size:0.82rem;margin-top:8px}
.data-table th,.data-table td{padding:8px 10px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top}
.data-table th{background:#f3f4f6;color:#374151;font-weight:600;font-size:0.74rem}
.score-row{display:flex;align-items:flex-end;gap:28px;margin:8px 0 4px;flex-wrap:wrap}
.score-val{font-size:2rem;font-weight:800;color:var(--accent)}
.score-lbl{font-size:0.72rem;color:var(--muted);margin-bottom:4px}
.score-rank{font-size:1.05rem;font-weight:700;color:var(--ok)}
.interp{font-size:0.8rem;color:var(--muted);line-height:1.5;margin-top:6px}
.risk-low{color:var(--ok);font-weight:600}.risk-mod{color:var(--warn);font-weight:600}.risk-high{color:var(--fail);font-weight:600}
.flag-list{list-style:none;padding:0;margin:8px 0 0 0}
.flag-list li{padding:6px 10px;border-left:3px solid var(--warn);margin-bottom:6px;font-size:0.82rem;background:#fffbeb}
.flag-hint{font-size:0.72rem;color:var(--muted);margin-top:4px;line-height:1.45;max-width:52rem}
.param-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:10px;font-size:0.76rem}
@media(max-width:900px){.param-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.param-grid{grid-template-columns:1fr}}
.param-cell{border:1px solid var(--border);border-radius:6px;padding:8px 10px;background:#fafafa;line-height:1.35}
.param-title-row{display:flex;align-items:center;gap:6px;min-width:0}
.param-title-row .pn{font-size:0.66rem;color:var(--muted);flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
.param-cell .pv{margin-top:6px;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.param-cell .pv-val{font-size:0.95rem;font-weight:800;color:#111;letter-spacing:-0.02em}
.param-cell .pv .rk{font-size:0.68rem;font-weight:700}
.param-cell .gate{font-size:0.62rem;color:var(--muted);margin-top:6px;line-height:1.45}
.param-cell .gate-ref{margin-top:4px;font-size:0.6rem;color:var(--muted);opacity:.92}
.param-cell .interp2{font-size:0.62rem;color:var(--muted);margin-top:4px;line-height:1.35}
.param-panel-intro{margin-bottom:6px}
.param-panel-bullets{margin:0 0 12px 18px;padding:0;font-size:0.78rem;color:var(--muted);line-height:1.5}
.param-panel-bullets li{margin-bottom:4px}
.param-grid-hint{font-size:0.76rem;color:var(--muted);margin-bottom:6px}
.param-dot{display:inline-block;width:7px;height:7px;border-radius:50%;flex-shrink:0;margin-top:2px}
.param-dot.low{background:var(--ok)}.param-dot.mod{background:var(--warn)}.param-dot.high{background:var(--fail)}.param-dot.na{background:#94a3b8}
.idx-banner{margin-top:14px;padding:12px 14px;background:#eef2ff;border:1px solid #c7d2fe;border-radius:8px}
.idx-banner h4{margin:0 0 6px;font-size:0.82rem;color:#3730a3;font-weight:700}
.idx-banner .idx-note{font-size:0.76rem;color:#4338ca;line-height:1.45;margin-bottom:10px}
.grid-readme{margin-top:12px;padding:10px 12px;background:#fffbeb;border-left:3px solid var(--warn);font-size:0.78rem;color:#374151;line-height:1.5}
footer{text-align:center;color:var(--muted);font-size:0.75rem;margin-top:24px;padding-top:12px;border-top:1px solid var(--border)}
@media print{
  @page{margin:11mm 12mm;size:A4}
  html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  body{background:#fff!important;color:#111;font-size:10.5px;line-height:1.42}
  .page{max-width:100%;padding:0;margin:0}
  .cover{background:#1e1b4b!important;break-inside:avoid;page-break-inside:avoid;margin-bottom:10px;padding:18px 20px;border-radius:6px}
  .section{break-inside:auto!important;page-break-inside:auto!important;margin-bottom:10px;orphans:3;widows:3}
  .section h3{break-after:avoid;page-break-after:avoid}
  .section-body{padding:10px 12px}
  .param-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;break-inside:auto;page-break-inside:auto}
  .param-cell{break-inside:avoid;page-break-inside:avoid}
  table.data-table,table.kv{width:100%;font-size:9.5px}
  table.data-table th,table.data-table td,table.kv td{padding:4px 6px}
  .seq-body{font-size:9px;line-height:1.5}
  .seq-block{break-inside:auto}
  .idx-banner,.grid-readme{break-inside:avoid;page-break-inside:avoid}
  .score-row{gap:16px}
  .score-val{font-size:1.5rem}
  footer{margin-top:12px;padding-top:8px;break-inside:avoid}
}
"""

def e(s: Any) -> str:
    return html_module.escape("" if s is None else str(s), quote=True)

def risk_dot_class(risk: str) -> str:
    r = (risk or "").upper()
    if r == "LOW": return "low"
    if r == "MODERATE": return "mod"
    if r == "HIGH": return "high"
    return "na"

def risk_css_class(risk: str) -> str:
    r = (risk or "").upper()
    if r == "LOW": return "risk-low"
    if r == "MODERATE": return "risk-mod"
    if r == "HIGH": return "risk-high"
    return "muted"

def fmt_val(v: Any) -> str:
    if v is None: return "—"
    if isinstance(v, float): return f"{v:.4g}"
    return str(v)


def format_p_abnativ2_compact(pa: Optional[Dict[str, Any]]) -> str:
    """One-line summary for §0 KV table."""
    if not pa or not isinstance(pa, dict):
        return "—"
    bits: List[str] = []
    if pa.get("pairing_likelihood") is not None:
        bits.append(f"pairing L={fmt_val(pa['pairing_likelihood'])}")
    if pa.get("vh_humanness") is not None:
        bits.append(f"VH={fmt_val(pa['vh_humanness'])}")
    if pa.get("vl_humanness") is not None:
        bits.append(f"VL={fmt_val(pa['vl_humanness'])}")
    if pa.get("paired_humanness") is not None:
        bits.append(f"paired={fmt_val(pa['paired_humanness'])}")
    return " · ".join(bits) if bits else "—"


def md_lines_naturalness_and_p_abnativ(ev: Dict[str, Any]) -> List[str]:
    """Markdown bullets: AbNatiV Δ (sdAb only) and full p-AbNatiV2 for VH/VL."""
    out: List[str] = []
    is_sdab = bool(ev.get("sdab_developability"))
    if is_sdab:
        out.append(f"- **AbNatiV Δ**: {fmt_val(ev.get('abnativ_delta'))} (tier {ev.get('abnativ_tier') or '—'})")
    else:
        out.append(
            "- **AbNatiV Δ**: *Not computed on VH/VL IgG (single-domain naturalness); use **p-AbNatiV2** below.*"
        )
    pa = ev.get("p_abnativ2") if isinstance(ev.get("p_abnativ2"), dict) else {}
    if any(pa.get(k) is not None for k in ("vh_humanness", "vl_humanness", "paired_humanness", "pairing_likelihood")):
        out.append("- **p-AbNatiV2**")
        if pa.get("vh_humanness") is not None:
            out.append(f"  - VH humanness: {pa.get('vh_humanness')}")
        if pa.get("vl_humanness") is not None:
            out.append(f"  - VL humanness: {pa.get('vl_humanness')}")
        if pa.get("paired_humanness") is not None:
            out.append(f"  - Paired humanness: {pa.get('paired_humanness')}")
        if pa.get("pairing_likelihood") is not None:
            out.append(f"  - Pairing likelihood: {pa.get('pairing_likelihood')}")
    else:
        out.append("- **p-AbNatiV2**: — *(not computed)*")
    return out


def render_polish_comparison_html(result: Dict[str, Any]) -> str:
    cmpb = result.get("generator_best_polish_comparison") or {}
    if not cmpb.get("available"):
        return ""

    base = cmpb.get("baseline_primary_indices") or {}
    pol = cmpb.get("generator_best_polish_mini_cmc") or {}
    deltas = cmpb.get("deltas") or {}
    chk = cmpb.get("generator_best_polish_primary_non_regression") or {}
    notes = cmpb.get("interpretation_notes") or []
    fb = cmpb.get("selected_sequence_is_baseline_fallback")
    reasons = cmpb.get("generator_best_candidate_guard_reasons") or []

    def row(metric: str, bk: str, pk: str, dk: str) -> str:
        return (
            f"<tr><td>{e(metric)}</td><td>{e(fmt_val(base.get(bk)))}</td>"
            f"<td>{e(fmt_val(pol.get(pk)))}</td><td>{e(fmt_val(deltas.get(dk)))}</td></tr>"
        )

    rows_html = "".join(
        [
            row("Fv charge asymmetry (VH/VL)", "Fv_charge_asymmetry", "Fv_charge_asymmetry", "Fv_charge_asymmetry_polish_minus_baseline"),
            row("ADI / developability index", "ADI_developability_index", "ADI", "ADI_polish_minus_baseline"),
            row("HPR combined", "HPR_combined", "HPR_combined", "HPR_polish_minus_baseline"),
            row("Instability index", "instability_index", "instability_index", "instability_index_polish_minus_baseline"),
        ]
    )

    badge_fb = '<span class="badge badge-warn">Baseline retained</span>' if fb else '<span class="badge badge-ok">Polish adopted</span>'
    chk_lines = (
        f"<li>ADI not below baseline (mini-CMC): <strong>{e(chk.get('ADI_not_below_baseline'))}</strong></li>"
        f"<li>HPR not below baseline (mini-CMC): <strong>{e(chk.get('HPR_not_below_baseline'))}</strong></li>"
        f"<li>Fv charge asymmetry improved (lower): <strong>{e(chk.get('Fv_charge_asymmetry_improved'))}</strong></li>"
    )
    notes_html = "".join(f'<p class="interp">{e(n)}</p>' for n in notes)
    reasons_html = (
        f'<p class="interp"><strong>Guard reasons on <code>selected_combo</code>:</strong> {e(", ".join(reasons) if reasons else "—")}</p>'
    )

    return f"""<div class="section">
  <h3>§1c — Generator-best FR polish vs baseline (charge asymmetry &amp; primary indices)</h3>
  <div class="section-body">
  <p class="interp">DeepFR-CTX-CMC proposes an FR-only polish ({e(pol.get("mutation_count"))} mutations in generator scan). Mini-CMC numbers below come from <code>polish_result.json</code>; baseline numbers come from the full Smart-CMC baseline evaluation. Delivery sequence follows §1 only when balanced_guard accepts a candidate <strong>without</strong> violating primary non-regression rules.</p>
  <p class="interp">Selection vs baseline: {badge_fb}</p>
  <table class="data-table">
    <tr><th>Metric</th><th>Baseline</th><th>Generator-best polish</th><th>Δ (polish − baseline)</th></tr>
    {rows_html}
  </table>
  <p class="interp" style="margin-top:8px">For Fv charge asymmetry, a <strong>negative</strong> Δ means reduction (favorable). Pairing likelihood is not recomputed in generator mini-CMC; see full candidate re-evaluation in guard evidence.</p>
  <ul class="param-panel-bullets">{chk_lines}</ul>
  {notes_html}
  {reasons_html}
  </div>
</div>
"""


def imgt_tables(seg: Dict[str, Any]) -> str:
    if not seg or seg.get("error"):
        return '<p class="interp">IMGT segmentation unavailable.</p>'
    order = ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]
    out: List[str] = []
    for chain in ("VH", "VL"):
        block = seg.get(chain)
        if not isinstance(block, dict): continue
        rows = []
        for reg in order:
            seq = block.get(reg) or ""
            if not seq: continue
            rows.append(f"<tr><td>{e(reg)}</td><td>{len(seq)}</td><td style=\"font-family:ui-monospace,monospace;font-size:.72rem;word-break:break-all\">{e(seq)}</td></tr>")
        out.append(f'<div style="margin-top:12px"><strong>{chain}</strong> (IMGT)</div>')
        out.append('<table class="data-table" style="margin-top:6px"><tr><th>Region</th><th>Len</th><th>Sequence</th></tr>' + "".join(rows) + "</table>")
    return "\n".join(out)

def flag_hint(token: str) -> str:
    t = token.lower()
    if "deamidation" in t: return "Sequence scan reported asparagine deamidation–associated motifs; see liability counts and CDR advisories for position context."
    if "isomerization" in t: return "Sequence scan reported isomerization–sensitive motifs; advisory unless structure confirms exposure and process relevance."
    if "fv charge" in t or "charge asymmetry" in t: return "CMC advisor: VH/VL charge asymmetry outside reference band vs selected cohort; framework-only review recommended."
    if "germline" in t: return "Germline database miss or partial context; Vernier precompute may be unavailable."
    return "See §0–§5 for metric context."

def render_hpr_tcia_sequence_panel(data: Dict[str, Any]) -> str:
    hpr_err = data.get("hpr_error")
    tcia_err = data.get("tcia_error")
    hi = data.get("hpr_index") or {}
    vh_b = hi.get("vh") or {}
    vl_b = hi.get("vl") or {}
    cb = hi.get("combined") or {}
    rows_hpr = []
    if hpr_err:
        rows_hpr.append(f'<tr><td colspan="2" style="color:var(--fail);font-weight:600">HPR failed: {e(hpr_err)}</td></tr>')
    else:
        rows_hpr.append(f"<tr><td class=\"lbl\">HPR combined</td><td><strong>{e(fmt_val(cb.get('score')))}</strong> ({e(cb.get('found_9mers'))}/{e(cb.get('total_9mers'))} 9-mers matched)</td></tr>")
        rows_hpr.append(f"<tr><td class=\"lbl\">HPR VH</td><td>{e(fmt_val(vh_b.get('score')))} ({e(vh_b.get('found_9mers'))}/{e(vh_b.get('total_9mers'))})</td></tr>")
        rows_hpr.append(f"<tr><td class=\"lbl\">HPR VL</td><td>{e(fmt_val(vl_b.get('score')))} ({e(vl_b.get('found_9mers'))}/{e(vl_b.get('total_9mers'))})</td></tr>")
    
    tcia_v = data.get("tcia_score")
    tcia_r = data.get("tcia_risk_level") or ""
    if tcia_err:
        rows_hpr.append(f'<tr><td colspan="2" style="color:var(--fail);font-weight:600">TCIA failed: {e(tcia_err)}</td></tr>')
    else:
        rows_hpr.append(f"<tr><td class=\"lbl\">TCIA (sequence)</td><td><strong>{e(fmt_val(tcia_v))}</strong> &middot; risk <strong>{e(tcia_r)}</strong> (MHCII analyzer, offline / no IEDB)</td></tr>")
    
    abl = data.get("ablang_score")
    if abl is not None:
        rows_hpr.append(f'<tr><td class=\"lbl\">AbLang2 paired PLL</td><td>{e(fmt_val(abl))} <span class=\"interp\" style=\"font-size:.72rem\">(internal)</span></td></tr>')

    is_sdab_eval = bool(data.get("sdab_developability"))
    if is_sdab_eval and (data.get("abnativ_delta") is not None or data.get("abnativ_tier")):
        rows_hpr.append(
            f'<tr><td class=\"lbl\">AbNatiV Δ</td><td>{e(fmt_val(data.get("abnativ_delta")))} '
            f'<span class=\"interp\" style=\"font-size:.72rem\">(tier {e(data.get("abnativ_tier") or "—")}, sdAb)</span></td></tr>'
        )
    elif not is_sdab_eval:
        rows_hpr.append(
            '<tr><td class=\"lbl\">AbNatiV Δ</td><td><span class=\"interp\">Not computed for VH/VL IgG '
            "(single-domain metric); see <strong>p-AbNatiV2</strong> below.</span></td></tr>"
        )

    p_abnativ2 = data.get("p_abnativ2")
    if isinstance(p_abnativ2, dict) and any(
        p_abnativ2.get(k) is not None
        for k in ("vh_humanness", "vl_humanness", "paired_humanness", "pairing_likelihood")
    ):
        if p_abnativ2.get("vh_humanness") is not None:
            rows_hpr.append(
                f'<tr><td class=\"lbl\">p-AbNatiV2 VH humanness</td><td>{e(fmt_val(p_abnativ2.get("vh_humanness")))}</td></tr>'
            )
        if p_abnativ2.get("vl_humanness") is not None:
            rows_hpr.append(
                f'<tr><td class=\"lbl\">p-AbNatiV2 VL humanness</td><td>{e(fmt_val(p_abnativ2.get("vl_humanness")))}</td></tr>'
            )
        if p_abnativ2.get("paired_humanness") is not None:
            rows_hpr.append(
                f'<tr><td class=\"lbl\">p-AbNatiV2 paired humanness</td><td>{e(fmt_val(p_abnativ2.get("paired_humanness")))}</td></tr>'
            )
        if p_abnativ2.get("pairing_likelihood") is not None:
            rows_hpr.append(
                f'<tr><td class=\"lbl\">p-AbNatiV2 pairing likelihood</td><td>{e(fmt_val(p_abnativ2.get("pairing_likelihood")))} '
                f'<span class=\"interp\" style=\"font-size:.72rem\">(cross-attention)</span></td></tr>'
            )
    elif not is_sdab_eval:
        rows_hpr.append(
            '<tr><td colspan="2" class=\"interp\">p-AbNatiV2: not computed (model unavailable or failed).</td></tr>'
        )

    fv_path = data.get("fv_pdb_path")
    struct_ok = bool(fv_path and Path(str(fv_path)).exists())
    if struct_ok:
        struct_blurb = (
            "§2 reports an Fv coordinate model for this evaluation; structure-using tiles in §5 reference it where applicable."
        )
    else:
        struct_blurb = (
            "§2 has no Fv PDB for this export — structure-dependent §5 tiles remain <code>NOT_RUN</code> or sequence proxies (see §2)."
        )
    note_idx = (
        "<strong>Sequence-derived indices</strong> (VH/VL): HPR Index, TCIA, AbLang2, <strong>p-AbNatiV2</strong>. "
        "<strong>AbNatiV Δ</strong> applies to single-domain (VHH/sdAb) Smart-CMC runs only. "
        + struct_blurb
    )
    return f"""<div class="idx-banner"><h4>Sequence-derived indices</h4><p class="idx-note">{note_idx}</p><table class="kv">{"".join(rows_hpr)}</table></div>"""

def render_clinical_ada_section(rab: Dict[str, Any]) -> str:
    ada_ctx = rab.get("ada_context") or {}
    if not isinstance(ada_ctx, dict): return ""
    entries = ada_ctx.get("matched_clinical_entries") or []
    vh_g = ada_ctx.get("vh_germline") or "—"
    vl_g = ada_ctx.get("vl_germline") or "—"
    interp = ada_ctx.get("interpretation") or ""
    if not entries and vh_g == "—" and vl_g == "—": return ""
    rows = [f"<tr><td>{e(ent.get('name'))}</td><td>{e(ent.get('match_type'))}</td><td><strong>{e(ent.get('ada_display'))}</strong></td><td>{e(ent.get('target'))}</td></tr>" for ent in entries]
    table_body = "".join(rows) if rows else '<tr><td colspan="4" class="interp">No matched clinical entries.</td></tr>'
    return f"""<div class="section"><h3>§5b — Clinical ADA context (label-level literature)</h3><div class="section-body"><p class="interp" style="margin-bottom:10px;padding:10px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;color:#1e3a5f"><strong>Why this section exists:</strong> Approved-product ADA rates come from <strong>labels and trials</strong>, not from TCIA/HPR or developability gates.</p><p class="interp">Germline context used for literature linkage: VH <span class="mono">{e(vh_g)}</span> · VL <span class="mono">{e(vl_g)}</span></p><table class="data-table" style="margin-top:10px"><tr><th>Clinical entry</th><th>Match</th><th>Reported ADA</th><th>Target</th></tr>{table_body}</table><p class="interp" style="margin-top:12px">{e(interp)}</p></div></div>"""

def ada_summary_row_for_kv(rab: Dict[str, Any]) -> str:
    ada_ctx = rab.get("ada_context") or {}
    entries = ada_ctx.get("matched_clinical_entries") or []
    if not entries: return ""
    bits = [f"<strong>{e(ent.get('name'))}</strong>: {e(ent.get('ada_display'))}" for ent in entries[:4]]
    return '<tr><td class="lbl">Label-linked ADA (trials / labels)</td><td>' + " · ".join(bits) + ' <span class="interp" style="font-size:.75rem">(see §5b — not predicted from TCIA)</span></td></tr>'

def param_value_by_key(rab: Dict[str, Any], key: str) -> Any:
    for p in rab.get("parameters") or []:
        if p.get("key") == key: return p.get("value")
    return None

def render_param_cell(p: Dict[str, Any]) -> str:
    lab = p.get("label") or p.get("key") or "—"
    risk = p.get("risk") or "NOT_RUN"
    dc = risk_dot_class(risk)
    rc = risk_css_class(risk)
    interp = (p.get("interpretation") or "")[:220]
    val = fmt_val(p.get("value"))
    rk = risk if risk != "NOT_RUN" else "N/A"
    return f"""<div class="param-cell" title="{e(lab)}"><div class="param-title-row"><span class="param-dot {dc}"></span><span class="pn">{e(lab)}</span></div><div class="pv"><span class="pv-val">{e(val)}</span><span class="rk {rc}">{e(rk)}</span></div><div class="interp2">{e(interp)}</div></div>"""

def _render_console_style_html(
    out_path: Path,
    result: Dict[str, Any],
) -> None:
    gen_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    baseline = result["baseline_snapshot"]
    selected = result.get("selected_candidate") or {}
    versioning = result.get("versioning") or {}
    drift = result.get("drift_parameters") or []
    guard_rows = result.get("guard_results_top") or []
    
    # Primary subject is the selected candidate if available, otherwise baseline
    data = selected.get("evaluation") or baseline
    rab = data.get("regular_ab_developability") or {}
    rc = rab.get("reference_context") or {}
    primary = rc.get("primary") or "—"
    stats_file = rc.get("primary_stats_file") or "—"
    params = list(rab.get("parameters") or [])
    
    clinical = data.get("clinical_score")
    pct_txt = "—"
    if clinical is not None:
        try:
            pct_txt = f"Top {100 - round(float(clinical))}% of {primary.split(':')[0].strip()}"
        except:
            pct_txt = str(primary)
            
    dev_idx = rab.get("developability_index") or data.get("developability_index")
    hpr_s = f"{float(data.get('hpr_combined', 0)):.4f}" if data.get('hpr_combined') is not None else "—"
    tcia_line = f"{float(data.get('tcia_score', 0)):.4f} ({data.get('tcia_risk_level', '')})" if data.get('tcia_score') is not None else "—"
    _pa_kv = data.get("p_abnativ2")
    p_ab_compact = format_p_abnativ2_compact(_pa_kv if isinstance(_pa_kv, dict) else None)
    
    # §1 Sequences: Always show original (baseline) + selected (delivery); red marks on selected when FR differs
    vh = data.get("vh_sequence") or ""
    vl = data.get("vl_sequence") or ""
    is_opt = selected and selected.get("id") != "baseline_fallback"
    vh_wt = baseline.get("vh_sequence") or ""
    vl_wt = baseline.get("vl_sequence") or ""

    def _render_plain_seq_block(seq: str, label: str, note: str = "") -> str:
        note_html = (
            f'<div class="interp" style="font-size:0.72rem;margin-top:6px;color:var(--muted)">{e(note)}</div>'
            if note
            else ""
        )
        return f'<div class="seq-block"><div class="seq-label">{e(label)} <span class="seq-len">({len(seq)} aa)</span></div><div class="seq-body">{e(seq)}</div>{note_html}</div>'

    def _render_selected_chain(seq: str, wt: str, label: str) -> str:
        if seq == wt or not is_opt:
            note = (
                "Delivery sequence identical to baseline (Smart-CMC fallback — no FR substitutions adopted)."
                if not is_opt
                else ""
            )
            return _render_plain_seq_block(seq, f"{label} (selected)", note)
        diff_html: List[str] = []
        for i, aa in enumerate(seq):
            if i < len(wt) and aa != wt[i]:
                diff_html.append(
                    f'<strong style="color:var(--fail);text-decoration:underline">{e(aa)}</strong>'
                )
            else:
                diff_html.append(e(aa))
        return f"""<div class="seq-block">
            <div class="seq-label">{e(label)} (selected) <span class="seq-len">({len(seq)} aa)</span> <span class="badge badge-info" style="margin-left:8px">FR substitution(s)</span></div>
            <div class="seq-body">{"".join(diff_html)}</div>
            <div class="interp" style="font-size:0.7rem;margin-top:4px">Red underlined residues differ from baseline §1a.</div>
        </div>"""

    seq_intro_dual = (
        "§1a lists the original baseline input; §1b lists the Smart-CMC delivery pair. "
        "When a guarded FR candidate is adopted, §1b highlights substitutions vs §1a."
    )
    seq_section_html = f"""<div class="section"><h3>§1 — VH / VL sequences (baseline vs delivery)</h3><div class="section-body">
<p class="interp">{e(seq_intro_dual)}</p>
<h4 style="font-size:0.85rem;margin:14px 0 8px;color:#374151;border-bottom:1px solid var(--border);padding-bottom:6px">§1a — Original (baseline input)</h4>
{_render_plain_seq_block(vh_wt, "VH")}{_render_plain_seq_block(vl_wt, "VL")}
<h4 style="font-size:0.85rem;margin:18px 0 8px;color:#374151;border-bottom:1px solid var(--border);padding-bottom:6px">§1b — Selected (delivery sequence)</h4>
{_render_selected_chain(vh, vh_wt, "VH")}{_render_selected_chain(vl, vl_wt, "VL")}
</div></div>"""

    polish_cmp_html = render_polish_comparison_html(result)

    disp = _report_display_name(result)

    inst_ix = data.get("instability_index")
    inst_class = "risk-low" if inst_ix is not None and float(inst_ix) <= 40 else "risk-mod"
    
    grid_html = "".join(render_param_cell(p) for p in params)
    
    # §6 Engineering actions: Combine Smart-CMC summary with standard suggestions
    eng_lines = []
    if selected and selected.get("id") != "baseline_fallback":
        eng_lines.append(f'<div class="idx-banner" style="background:#f0fdf4;border-color:#bbf7d0;margin-bottom:16px">')
        eng_lines.append(f'<h4 style="color:#166534">Smart-CMC Optimization Summary</h4>')
        eng_lines.append(f'<p class="interp" style="color:#15803d">Selected Candidate: <strong>{e(selected.get("id"))}</strong> &middot; Guard Score: <strong>{e(selected.get("guard_result", {}).get("score"))}</strong></p>')
        eng_lines.append(f'<p class="interp" style="color:#15803d">Mutations: {e(selected.get("mutation_count"))} FR substitutions applied.</p>')
        
        muts = selected.get("mutations") or []
        if muts:
            mut_bits = []
            for m in muts:
                # Format: VH[15] R->K
                chain = m.get("chain", "?")
                pos = m.get("pos", "?")
                wt = m.get("wt", "?")
                mut = m.get("mut", "?")
                mut_bits.append(f"<code>{chain}[{pos}] {wt}&rarr;{mut}</code>")
            eng_lines.append(f'<p class="interp" style="color:#15803d; margin-top:8px"><strong>Applied mutations:</strong> {" &middot; ".join(mut_bits)}</p>')
        
        eng_lines.append(f'<p class="interp" style="color:#15803d; margin-top:8px; font-size:0.75rem"><em>Note: This candidate has undergone a full 27-parameter re-evaluation. See §5 for updated metrics.</em></p>')
        eng_lines.append('</div>')
    
    sugg = rab.get("fr_modification_suggestions") or data.get("mutation_suggestions") or []
    if sugg:
        eng_lines.append('<table class="data-table"><tr><th>Target</th><th>Priority</th><th>Direction</th><th>Recommendation</th></tr>')
        for s in sugg:
            eng_lines.append(f"<tr><td>{e(s.get('target'))}</td><td>{e(s.get('priority'))}</td><td>{e(s.get('direction'))}</td><td>{e(s.get('recommendation'))}</td></tr>")
        eng_lines.append("</table>")
    
    cdr_w = rab.get("cdr_warnings") or []
    if cdr_w:
        eng_lines.append("<p class=\"interp\" style=\"margin-top:12px\"><strong>CDR advisories</strong> (do not modify without validation)</p><ul class=\"param-panel-bullets\">")
        for w in cdr_w:
            eng_lines.append(f"<li>Position <strong>{e(w.get('position'))}</strong>: {e(w.get('finding'))} — {e(w.get('action'))}</li>")
        eng_lines.append("</ul>")

    flags = data.get("overall_flags") or []
    flag_items = "".join(f"<li>{e(f)}<div class=\"flag-hint\">{e(flag_hint(str(f)))}</div></li>" for f in flags)
    
    # §2 Structure modeling status
    pdb_path = data.get("fv_pdb_path")
    if pdb_path and Path(pdb_path).exists():
        p = Path(pdb_path)
        struct_html = f'<p class="interp"><strong>Fv model present.</strong> PDB: <code>{e(p.name)}</code> (co-located with this export).</p>'
        struct_html += (
            '<p class="interp">Surface- and geometry-dependent developability fields in §5 use this model when the tile definition requires a structure; '
            "other fields remain sequence-derived.</p>"
        )
    else:
        struct_html = (
            '<p class="interp"><strong>No Fv PDB in this run.</strong> §5 entries that require an atomic model read <code>NOT_RUN</code> or a sequence-level proxy; '
            "the sequence-index block above (HPR, TCIA, AbLang2, p-AbNatiV2) is unaffected.</p>"
        )
        struct_html += '<p class="interp">Re-run the orchestrator with <code>--predict-structure</code> to populate structure-augmented tiles.</p>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">
<title>InSynBio AbEngineCore | {e(disp)} — IgG/VH-VL CMC</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="page">
<div class="cover">
  <h1>InSynBio AbEngineCore</h1>
  <div class="sub">IgG / VH+VL CMC Developability Report &nbsp;|&nbsp; CMC Standard v1.3</div>
  <div style="font-size:1.12rem;font-weight:700;margin-top:12px;letter-spacing:.02em;color:#fff">{e(disp)}</div>
  <div class="meta">
    <div class="header-meta">
      <div>Report layout: igg-cmc-vhvl-parity-light-from-snapshot</div>
      <div>Build: 20260503-002</div>
      <div>Analysis: {e(versioning.get('analysis_version'))}</div>
      <div>Protocol: {e(versioning.get('protocol_version'))}</div>
      <div>Report format: {e(versioning.get('report_format_version'))}</div>
      <div>Analysis track: {e(versioning.get('analysis_track'))}</div>
      <div>AbEngineCore: 1.3.0</div>
      <div>CMC policy: balanced_guarded</div>
    </div>
    <span>Molecule: <strong>{e(disp)}</strong></span>
    <span>Generated: {e(gen_ts)}</span>
    <span>CONFIDENTIAL</span>
  </div>
</div>

<div class="section">
  <h3>§0 — Run summary</h3>
  <div class="section-body">
  <table class="kv">
    <tr><td class="lbl">Molecule (report label)</td><td><strong>{e(disp)}</strong></td></tr>
    <tr><td class="lbl">Developability index / 100</td><td>{e(dev_idx)}</td></tr>
    <tr><td class="lbl">Reference composite (0–100)</td><td>{e(clinical)}</td></tr>
    <tr><td class="lbl">Percentile summary</td><td>{e(pct_txt)}</td></tr>
    <tr><td class="lbl">Reference standard</td><td>{e(primary)}</td></tr>
    <tr><td class="lbl">Frozen stats file</td><td>{e(stats_file)}</td></tr>
    <tr><td class="lbl">Antibody origin</td><td>{e(result.get('origin'))}</td></tr>
    {ada_summary_row_for_kv(rab)}
    <tr><td class="lbl">HPR Index (summary)</td><td>{e(hpr_s)} <span class="interp" style="font-size:.75rem">(see detailed breakdown below)</span></td></tr>
    <tr><td class="lbl">TCIA (summary)</td><td>{e(tcia_line)} <span class="interp" style="font-size:.75rem">(see below)</span></td></tr>
    <tr><td class="lbl">p-AbNatiV2 (summary)</td><td>{e(p_ab_compact)} <span class="interp" style="font-size:.75rem">(VH/VL paired humanness; detail below)</span></td></tr>
  </table>
  {render_hpr_tcia_sequence_panel(data)}
  </div>
</div>

    {seq_section_html}

    {polish_cmp_html}

<div class="section">
  <h3>§1b — IMGT segmentation (FR / CDR)</h3>
  <div class="section-body">
  <p class="interp">Regions from pipeline IMGT segmentation (same path as console / humanization tooling).</p>
  {imgt_tables(data.get("imgt_segmentation") or {})}
  </div>
</div>

<div class="section">
  <h3>§2 — In-silico Fv structure modeling</h3>
  <div class="section-body">
  {struct_html}
  </div>
</div>

<div class="section">
  <h3>§3 — Reference clinical benchmark</h3>
  <div class="section-body">
  <div class="score-row">
    <div><div class="score-val">{e(dev_idx)}</div><div class="score-lbl">Developability Index / 100</div></div>
    <div>
      <div class="score-val" style="font-size:1.75rem">{e(clinical)}</div>
      <div class="score-lbl">Reference composite index (0–100)</div>
      <div class="score-rank" style="margin-top:8px">{e(pct_txt)}</div>
      <div class="score-lbl" style="margin-top:2px">Percentile rank vs selected reference panel</div>
    </div>
  </div>
  </div>
</div>

<div class="section">
  <h3>§4 — Key physicochemical metrics</h3>
  <div class="section-body">
  <table class="data-table">
    <tr><th>Metric</th><th>Value</th><th>Threshold / Note</th></tr>
    <tr><td>pI (Fab)</td><td>{e(data.get("pI_fab"))}</td><td>4.5–9.5 preferred</td></tr>
    <tr><td>Instability Index</td><td class="{inst_class}">{e(inst_ix)}</td><td>&lt; 40 recommended (Guruprasad et al. 1990)</td></tr>
    <tr><td>GRAVY</td><td>{e(data.get("GRAVY"))}</td><td>&lt; −0.1 preferred</td></tr>
    <tr><td>Deamidation sites (cohort count)</td><td>{e(fmt_val(param_value_by_key(rab, "deamidation_sites")))}</td><td>from §5 cohort context</td></tr>
    <tr><td>Oxidation sites (cohort count)</td><td>{e(fmt_val(param_value_by_key(rab, "oxidation_sites")))}</td><td></td></tr>
    <tr><td>Glycosylation sites (cohort count)</td><td>{e(fmt_val(param_value_by_key(rab, "glycosylation_sites")))}</td><td></td></tr>
  </table>
  </div>
</div>

<div class="section">
  <h3>§5 — Reference developability panel (25 tiles; 27 indicators)</h3>
  <div class="section-body">
  <p class="interp param-panel-intro">{e(rc.get("method_consistency_note") or "Values interpreted against frozen cohort distributions.")}</p>
  <ul class="param-panel-bullets"><li>{e(primary)} — primary stats file: <code>{e(stats_file)}</code></li></ul>
  <div class="param-grid">{grid_html}</div>
  </div>
</div>

{render_clinical_ada_section(rab)}

<div class="section">
  <h3>§6 — Engineering actions &amp; optimization suggestions</h3>
  <div class="section-body">
  <p class="interp">Framework-only policy; CDR liabilities remain advisory unless a redesign project is approved.</p>
  {"".join(eng_lines)}
  </div>
</div>

<div class="section">
  <h3>§7 — CMC flags</h3>
  <div class="section-body">
  <ul class="flag-list">{flag_items}</ul>
  </div>
</div>

<div class="section">
  <h3>§8 — Optimization roadmap</h3>
  <div class="section-body">
  <ul class="param-panel-bullets">
    <li><strong>Smart-CMC:</strong> Current result is the product of origin-aware drift detection and balanced guarded selection.</li>
    <li><strong>Fv modeling:</strong> Re-run with <code>predict_fv_structure: true</code> for structure-dependent tiles.</li>
    <li><strong>CDR advisories:</strong> Treat CDR scan findings as advisory.</li>
  </ul>
  </div>
</div>

<footer>InSynBio Research &nbsp;·&nbsp; {e(gen_ts)} &nbsp;·&nbsp; CONFIDENTIAL &nbsp;·&nbsp; Use Ctrl+P → Save as PDF to export.</footer>
</div>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")


def _predict_fv_structure(vh: str, vl: str, out_path: Path) -> Optional[Path]:
    try:
        payload = {"out_path": str(out_path), "H": vh, "L": vl, "model_type": "abody"}
        payload_path = out_path.with_suffix(".json")
        payload_path.write_text(json.dumps(payload), encoding="utf-8")
        
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "predict_one_immunebuilder.py"),
            "--json",
            str(payload_path),
        ]
        subprocess.run(cmd, check=True)
        if out_path.exists():
            return out_path
    except Exception as e:
        print(f"ERROR: Fv prediction failed: {e}")
    return None


def main() -> None:
    print(f"DEBUG: Smart-CMC Orchestrator v{SMART_CMC_ANALYSIS_VERSION} starting...")
    ap = argparse.ArgumentParser(
        description="Smart-CMC orchestrator: origin-aware drift detection + guarded FR-only repair"
    )
    ap.add_argument("--mode", choices=("sweep", "sources"), default="sweep")
    ap.add_argument("--origin", type=str, default="humanized")
    ap.add_argument("--species", type=str, help="Explicit species (dog, cat); overrides --origin if provided")
    ap.add_argument("--base-vh", type=str, help="Base VH sequence")
    ap.add_argument("--base-vl", type=str, help="Base VL sequence")
    ap.add_argument("--snapshot-json", type=Path, help="Optional JSON containing vh_sequence/vl_sequence")
    ap.add_argument("--sources-json", type=Path, help="Required for --mode sources")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument(
        "--display-name",
        type=str,
        default="",
        help="Antibody/molecule label for HTML/MD cover (default: out-dir folder name, underscores→spaces)",
    )
    ap.add_argument("--top-singles", type=int, default=16)
    ap.add_argument("--max-combo", type=int, default=4)
    ap.add_argument("--fv-weight", type=float, default=0.5)
    ap.add_argument("--allow-fv-only-improvement", action="store_true")
    ap.add_argument("--allow-soft-regressions", type=int, default=1)
    ap.add_argument("--max-instability-regression", type=float, default=0.5)
    ap.add_argument("--instability-safe-ceiling", type=float, default=DEFAULT_INSTABILITY_SAFE_CEILING)
    ap.add_argument("--max-hpr-drop", type=float, default=0.002)
    ap.add_argument("--max-adi-drop", type=float, default=1.0)
    ap.add_argument("--max-mutations", type=int, default=4)
    ap.add_argument("--abnativ-floor", type=float, default=None)
    ap.add_argument("--protocol-version", type=str, default=SMART_CMC_PROTOCOL_VERSION)
    ap.add_argument("--analysis-version", type=str, default=SMART_CMC_ANALYSIS_VERSION)
    ap.add_argument("--report-format-version", type=str, default=SMART_CMC_REPORT_FORMAT_VERSION)
    ap.add_argument(
        "--analysis-track",
        type=str,
        default="",
        help="Optional track label for origin-specific analysis stream (e.g. smart-cmc-phagedisplay)",
    )
    ap.add_argument(
        "--aligned-html-name",
        type=str,
        default="Adalimumab_Humira_CMC_Analysis_and_Optimization.html",
        help="Additional aligned HTML filename with fixed console style/version",
    )
    ap.add_argument("--predict-structure", action="store_true", help="Predict Fv structure for final candidate")
    ap.add_argument(
        "--baseline-only",
        action="store_true",
        help="Skip DeepFR-CTX-CMC polish; write baseline Smart-CMC JSON + console MD/HTML (engineered/natural cohort refs unchanged).",
    )
    args = ap.parse_args()

    if args.snapshot_json:
        snap = json.loads(args.snapshot_json.read_text(encoding="utf-8"))
        base_vh = str(snap.get("vh_sequence") or "").strip().upper()
        base_vl = str(snap.get("vl_sequence") or "").strip().upper()
        # If snapshot has origin, use it unless overridden
        if not args.origin or args.origin == "humanized":
            args.origin = snap.get("origin") or "humanized"
    else:
        base_vh = str(args.base_vh or "").strip().upper()
        base_vl = str(args.base_vl or "").strip().upper()

    # Species override
    if args.species:
        if args.species.lower() in {"dog", "canine"}:
            args.origin = "dog_clinical"
        elif args.species.lower() in {"cat", "feline"}:
            args.origin = "cat_clinical"

    norm_origin = _normalize_smart_origin(args.origin)
    is_sdab = _is_sdab_origin(norm_origin)

    if len(base_vh) < 80 or (not is_sdab and len(base_vl) < 70):
        raise SystemExit("Provide valid base VH/VL sequences, or base VH only for sdAb origins.")
    if args.mode == "sources" and not args.sources_json:
        raise SystemExit("--mode sources requires --sources-json")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    analysis_track = str(args.analysis_track or "").strip() or _analysis_track_from_origin(norm_origin)
    
    if is_sdab:
        # For sdAb, we use VHH reference context
        from core.cmc.vhh_cmc_engine import get_sdab_origin_ref, load_vhh_ref
        ref_path = get_sdab_origin_ref(norm_origin)
        ref_data = {"_meta": {"name": ref_path.name, "mode": "source_matched"}, "metrics": load_vhh_ref(ref_path)}
    else:
        ref_data = load_effective_primary_reference(norm_origin)
        # Patch pI ranges for pet clinical origins if using human clinical proxy
        if norm_origin in {"dog_clinical", "cat_clinical"} and "pI" in ref_data.get("metrics", {}):
            # InSynBio Petization Standard V1.2.0 pI targets
            # We use the typical range for p25-p75 and flag boundaries for p5-p95
            ref_data["metrics"]["pI"] = {
                "p5": 5.5,
                "p25": 6.5,
                "p50": 8.0,
                "p75": 9.5,
                "p95": 10.5,
                "mean": 8.0,
                "stdev": 1.5,
                "n": ref_data.get("n", 458)
            }
            if norm_origin == "dog_clinical":
                ref_data["_meta"]["name"] = "Canine clinical VH/VL reference (pI-patched proxy)"
            else:
                ref_data["_meta"]["name"] = "Feline clinical VH/VL reference (pI-patched proxy)"

    # 1) Baseline evaluation
    baseline_pdb = None
    if args.predict_structure and not is_sdab:
        baseline_pdb = _predict_fv_structure(base_vh, base_vl, args.out_dir / "baseline_fv.pdb")
    
    if is_sdab:
        baseline_eval = _evaluate_sdab_block(base_vh, norm_origin)
        # For sdAb, drift parameters are those with risk in {HIGH, MODERATE}
        drift_parameters = []
        for k, flag in baseline_eval["sdab_developability"]["risk_flags"].items():
            if flag in {"FAIL", "WARN"}:
                drift_parameters.append({
                    "key": k,
                    "label": k,
                    "value": baseline_eval["raw_metrics"].get(k),
                    "risk": "HIGH" if flag == "FAIL" else "MODERATE",
                    "gate_status": flag,
                    "priority": 2 if flag == "FAIL" else 1
                })
    else:
        baseline_eval = _evaluate_regular_block(base_vh, base_vl, norm_origin, fv_pdb_path=baseline_pdb)
        drift_parameters = _extract_drift_parameters(baseline_eval["regular_ab_developability"])

    generator_dir = args.out_dir / "_generator_deepfr_ctx_cmc"

    if args.baseline_only:
        selected_bo = {
            "id": "baseline_fallback",
            "source": "fallback",
            "mutation_count": 0,
            "vh": base_vh,
            "vl": base_vl,
            "score_hint": 0.0,
            "guard_result": {
                "passed": True,
                "reasons": ["baseline_only_export_no_deepfr_polish"],
                "evidence": {},
                "score": 0.0,
            },
            "evaluation": baseline_eval,
        }
        polish_cmp_bo = {
            "available": False,
            "reason": "baseline_only_export (DeepFR polish not run)",
        }
        display_name_bo = str(args.display_name or "").strip() or args.out_dir.name.replace("_", " ")
        ref_meta_bo = ref_data.get("_meta") if isinstance(ref_data, dict) else {}
        ref_name_bo = ref_meta_bo.get("name") if isinstance(ref_meta_bo, dict) else None
        ref_mode_bo = ref_meta_bo.get("mode") if isinstance(ref_meta_bo, dict) else None
        result_bo: Dict[str, Any] = {
            "system": "smart-cmc",
            "version": "phase1_cli_v1",
            "display_name": display_name_bo,
            "versioning": {
                "protocol_version": args.protocol_version,
                "analysis_version": args.analysis_version,
                "report_format_version": args.report_format_version,
                "analysis_track": analysis_track,
            },
            "origin": norm_origin,
            "policy": {
                "name": "baseline_only_export",
                "allow_soft_regressions": args.allow_soft_regressions,
                "max_instability_regression": args.max_instability_regression,
                "instability_safe_ceiling": args.instability_safe_ceiling,
                "max_hpr_drop": args.max_hpr_drop,
                "max_adi_drop": args.max_adi_drop,
                "max_mutations": args.max_mutations,
                "abnativ_floor": _effective_abnativ_floor(norm_origin, args.abnativ_floor),
                "hard_constraints": ["DeepFR generator skipped (--baseline-only)"],
            },
            "generator": {
                "name": "skipped",
                "role": "baseline_only_no_deepfr",
                "output_dir": str(generator_dir),
            },
            "reference_context": {
                "effective_reference": ref_name_bo,
                "reference_mode": ref_mode_bo,
                "n_count": ref_data.get("n") if isinstance(ref_data, dict) else None,
            },
            "baseline_snapshot": baseline_eval,
            "drift_parameters": drift_parameters,
            "candidate_count": 0,
            "guard_results_top": [],
            "selected_candidate": selected_bo,
            "non_regression_evidence": {},
            "generator_best_polish_comparison": polish_cmp_bo,
        }
        generator_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "smart_cmc_result.json").write_text(
            json.dumps(result_bo, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        _render_md_report(args.out_dir / "SMART_CMC_AUDIT.md", result_bo)
        _render_console_style_report(args.out_dir / "SMART_CMC_WEB_CONSOLE_STYLE.md", result_bo)
        _render_console_style_html(args.out_dir / "SMART_CMC_WEB_CONSOLE_STYLE.html", result_bo)
        _render_console_style_html(args.out_dir / args.aligned_html_name, result_bo)
        (args.out_dir / "smart_cmc_selected_sequence.json").write_text(
            json.dumps(
                {
                    "vh": selected_bo["vh"],
                    "vl": selected_bo["vl"],
                    "origin": norm_origin,
                    "source": selected_bo["source"],
                    "guard_score": selected_bo["guard_result"]["score"],
                    "versioning": result_bo.get("versioning"),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"Wrote {args.out_dir / 'smart_cmc_result.json'} (baseline-only)")
        print(f"Wrote {args.out_dir / 'SMART_CMC_AUDIT.md'}")
        print(f"Wrote {args.out_dir / 'SMART_CMC_WEB_CONSOLE_STYLE.md'}")
        print(f"Wrote {args.out_dir / 'SMART_CMC_WEB_CONSOLE_STYLE.html'}")
        print(f"Wrote {args.out_dir / args.aligned_html_name}")
        return

    # 2) Candidate generation by DeepFR-CTX-CMC polish
    generator_dir.mkdir(parents=True, exist_ok=True)
    polish_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_deepfr_ctx_cmc_polish.py"),
        "--mode",
        args.mode,
        "--origin",
        norm_origin,
        "--base-vh",
        base_vh,
        "--base-vl",
        base_vl,
        "--out-dir",
        str(generator_dir),
        "--top-singles",
        str(args.top_singles),
        "--max-combo",
        str(args.max_combo),
        "--fv-weight",
        str(args.fv_weight),
    ]
    if args.allow_fv_only_improvement:
        polish_cmd.append("--allow-fv-only-improvement")
    if args.mode == "sources" and args.sources_json:
        polish_cmd += ["--sources-json", str(args.sources_json)]
    
    # If sdAb, we need to handle the empty VL in the generator
    if is_sdab:
        # We'll pass a dummy VL or update the generator to handle empty VL
        # For now, let's assume the generator can handle it if we pass ""
        pass

    subprocess.run(polish_cmd, check=True)

    scan_payload = json.loads((generator_dir / "deepfr_ctx_cmc_scan.json").read_text(encoding="utf-8"))
    polish_result = json.loads((generator_dir / "polish_result.json").read_text(encoding="utf-8"))
    candidates = _collect_candidates_from_scan(base_vh, base_vl, scan_payload, polish_result)
    if not candidates:
        raise RuntimeError("No candidate collected from DeepFR-CTX-CMC generator.")

    # 3) Candidate re-evaluation + balanced guarded selection
    guard_rows: List[Dict[str, Any]] = []
    selected: Optional[Dict[str, Any]] = None
    for c in candidates:
        if is_sdab:
            cand_eval = _evaluate_sdab_block(c["vh"], norm_origin)
        else:
            cand_eval = _evaluate_regular_block(c["vh"], c["vl"], norm_origin)
            
        guard = _apply_balanced_guard(
            baseline_eval,
            cand_eval,
            origin=norm_origin,
            mutation_count=int(c.get("mutation_count") or 0),
            allow_soft_regressions=args.allow_soft_regressions,
            max_instability_regression=args.max_instability_regression,
            instability_safe_ceiling=args.instability_safe_ceiling,
            max_hpr_drop=args.max_hpr_drop,
            max_adi_drop=args.max_adi_drop,
            max_mutations=args.max_mutations,
            abnativ_floor=_effective_abnativ_floor(norm_origin, args.abnativ_floor),
        )
        row = {
            "id": c["id"],
            "source": c["source"],
            "mutation_count": c["mutation_count"],
            "score_hint": c["score_hint"],
            "passed": guard.passed,
            "score": guard.score,
            "reasons": guard.reasons,
            "evidence": guard.evidence,
        }
        guard_rows.append(row)
        if guard.passed:
            if selected is None or guard.score > selected["guard_result"]["score"]:
                selected = {
                    **c,
                    "guard_result": {
                        "passed": guard.passed,
                        "reasons": guard.reasons,
                        "evidence": guard.evidence,
                        "score": guard.score,
                    },
                    "evaluation": cand_eval,
                }

    guard_rows.sort(key=lambda x: (-int(x["passed"]), -x["score"], x["id"]))
    
    # 4) Final re-evaluation of selected candidate (with structure if requested)
    if selected and selected.get("id") != "baseline_fallback":
        if is_sdab:
            final_eval = _evaluate_sdab_block(selected["vh"], norm_origin)
        else:
            final_pdb = None
            if args.predict_structure:
                final_pdb = _predict_fv_structure(selected["vh"], selected["vl"], args.out_dir / "selected_fv.pdb")
            
            # Re-evaluate with structure to get full metrics for report
            final_eval = _evaluate_regular_block(selected["vh"], selected["vl"], norm_origin, fv_pdb_path=final_pdb)
        selected["evaluation"] = final_eval

    if selected is None:
        selected = {
            "id": "baseline_fallback",
            "source": "fallback",
            "mutation_count": 0,
            "vh": base_vh,
            "vl": base_vl,
            "score_hint": 0.0,
            "guard_result": {
                "passed": True,
                "reasons": ["no_candidate_passed_balanced_guard"],
                "evidence": {},
                "score": 0.0,
            },
            "evaluation": baseline_eval,
        }

    polish_comparison = _build_generator_best_polish_comparison(
        baseline_eval, polish_result, guard_rows, selected
    )

    ref_meta = ref_data.get("_meta") if isinstance(ref_data, dict) else {}
    ref_name = ref_meta.get("name") if isinstance(ref_meta, dict) else None
    ref_mode = ref_meta.get("mode") if isinstance(ref_meta, dict) else None
    display_name = str(args.display_name or "").strip() or args.out_dir.name.replace("_", " ")
    result_payload: Dict[str, Any] = {
        "system": "smart-cmc",
        "version": "phase1_cli_v1",
        "display_name": display_name,
        "versioning": {
            "protocol_version": args.protocol_version,
            "analysis_version": args.analysis_version,
            "report_format_version": args.report_format_version,
            "analysis_track": analysis_track,
        },
        "origin": norm_origin,
        "policy": {
            "name": "balanced_guarded",
            "allow_soft_regressions": args.allow_soft_regressions,
            "max_instability_regression": args.max_instability_regression,
            "instability_safe_ceiling": args.instability_safe_ceiling,
            "max_hpr_drop": args.max_hpr_drop,
            "max_adi_drop": args.max_adi_drop,
            "max_mutations": args.max_mutations,
            "abnativ_floor": _effective_abnativ_floor(norm_origin, args.abnativ_floor),
            "hard_constraints": [
                "no hard-gate failure increase",
                "overall gate not worsened",
                "instability regression constrained unless candidate remains below safe ceiling",
                "HPR drop constrained by origin track",
                "ADI drop constrained by dynamic baseline-dependent limits",
                "mutation count constrained",
                "AbNatiV floor enforced for sdAb tracks",
            ],
        },
        "generator": {
            "name": "deepfr-ctx-cmc-polish",
            "role": "candidate_generator_only",
            "output_dir": str(generator_dir),
        },
        "reference_context": {
            "effective_reference": ref_name,
            "reference_mode": ref_mode,
            "n_count": ref_data.get("n") if isinstance(ref_data, dict) else None,
        },
        "baseline_snapshot": baseline_eval,
        "drift_parameters": drift_parameters,
        "candidate_count": len(candidates),
        "guard_results_top": guard_rows[:20],
        "selected_candidate": selected,
        "non_regression_evidence": selected.get("guard_result", {}).get("evidence", {}),
        "generator_best_polish_comparison": polish_comparison,
    }

    (args.out_dir / "smart_cmc_result.json").write_text(
        json.dumps(result_payload, indent=2), encoding="utf-8"
    )
    _render_md_report(args.out_dir / "SMART_CMC_AUDIT.md", result_payload)
    _render_console_style_report(args.out_dir / "SMART_CMC_WEB_CONSOLE_STYLE.md", result_payload)
    _render_console_style_html(args.out_dir / "SMART_CMC_WEB_CONSOLE_STYLE.html", result_payload)
    _render_console_style_html(args.out_dir / args.aligned_html_name, result_payload)
    (args.out_dir / "smart_cmc_selected_sequence.json").write_text(
        json.dumps(
            {
                "vh": selected["vh"] if "vh" in selected else selected.get("vh_sequence"),
                "vl": selected["vl"] if "vl" in selected else selected.get("vl_sequence"),
                "origin": norm_origin,
                "source": selected["source"],
                "guard_score": selected["guard_result"]["score"],
                "versioning": result_payload.get("versioning"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {args.out_dir / 'smart_cmc_result.json'}")
    print(f"Wrote {args.out_dir / 'SMART_CMC_AUDIT.md'}")
    print(f"Wrote {args.out_dir / 'SMART_CMC_WEB_CONSOLE_STYLE.md'}")
    print(f"Wrote {args.out_dir / 'SMART_CMC_WEB_CONSOLE_STYLE.html'}")
    print(f"Wrote {args.out_dir / args.aligned_html_name}")
    print(f"Wrote {args.out_dir / 'smart_cmc_selected_sequence.json'}")


if __name__ == "__main__":
    main()
