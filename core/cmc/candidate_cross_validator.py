"""
core/cmc/candidate_cross_validator.py
======================================
Cross-metric validator and net-score ranker for Smart-CMC FR mutation candidates.

Problem solved:
  Optimizing metric X (e.g. hydrophobic patch) can inadvertently push a currently-passing
  metric Y (e.g. instability_index) into WARN or FAIL. Without a global re-evaluation step,
  these trade-off harms are invisible until the client runs the analysis.

Solution:
  For every candidate mutation, apply the substitution in-silico, recompute ALL miniCMC
  metrics, and compare flags. Candidates that cause a PASS→FAIL regression are rejected.
  Candidates that cause PASS→WARN regressions are demoted to LOW priority and annotated.
  All survivors are ranked by net_score (improvement minus harm penalty).

Public API:
  validate_and_rank_vhh_candidates(seq, candidates, base_metrics, base_flags) -> list
  validate_and_rank_igg_candidates(vh, vl, candidates, base_metrics, base_flags) -> list

Cross-harm levels:
  "NONE"      — no metric harmed; candidate is clean
  "WARN_ONLY" — one or more passing metrics downgraded to WARN; priority demoted to LOW
  "FAIL"      — one or more passing metrics pushed to FAIL; candidate excluded
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# ── miniCMC metric set monitored for cross-harm (VHH) ────────────────────────
_VHH_MINICMC_METRICS = (
    "pI", "GRAVY", "instability_index", "net_charge_pH7",
    "hydro_patch_max9", "charge_patch_max7", "SAP_score", "agg_motifs",
)

# ── miniCMC metric set monitored for cross-harm (IgG) ────────────────────────
_IGG_MINICMC_METRICS = (
    "pI", "GRAVY", "instability_index", "net_charge_pH7",
    "hydro_patch_max9", "charge_patch_max7", "SAP_score", "agg_motifs",
)

# ── flag ranking for comparison ───────────────────────────────────────────────
_FLAG_RANK = {"PASS": 0, "WARN": 1, "FAIL": 2, "NA": -1}

# ── net-score weights ─────────────────────────────────────────────────────────
_IMPROVE_FAIL_TO_WARN  =  3.0   # target metric improved: FAIL→WARN
_IMPROVE_WARN_TO_PASS  =  5.0   # target metric improved: WARN→PASS
_IMPROVE_FAIL_TO_PASS  =  7.0   # target metric improved: FAIL→PASS (skip-level)
_IMPROVE_METRIC_DELTA  =  1.0   # raw metric value improved (quantitative)
_HARM_PASS_TO_WARN     = -2.0   # collateral: previously-passing metric degraded to WARN
_HARM_WARN_TO_FAIL     = -5.0   # collateral: previously-WARN metric degraded to FAIL
_HARM_PASS_TO_FAIL     = -10.0  # hard veto penalty (candidate will be excluded)


def _flag_delta_score(old_flag: str, new_flag: str) -> float:
    """Score for flag transition (positive = improvement, negative = harm)."""
    old_r = _FLAG_RANK.get(old_flag, -1)
    new_r = _FLAG_RANK.get(new_flag, -1)
    if old_r < 0 or new_r < 0:
        return 0.0
    delta = old_r - new_r  # positive means improvement
    if delta == 2:   # e.g. FAIL→PASS (skip-level)
        return _IMPROVE_FAIL_TO_PASS
    if delta == 1:   # FAIL→WARN or WARN→PASS
        return _IMPROVE_FAIL_TO_WARN if old_flag == "FAIL" else _IMPROVE_WARN_TO_PASS
    if delta == -1:  # PASS→WARN or WARN→FAIL
        return _HARM_PASS_TO_WARN if old_flag == "PASS" else _HARM_WARN_TO_FAIL
    if delta == -2:  # PASS→FAIL
        return _HARM_PASS_TO_FAIL
    return 0.0


def _apply_mutation(seq: str, lin0: int, new_aa: str) -> str:
    """Apply a single-point substitution at 0-based linear position."""
    if not (0 <= lin0 < len(seq)):
        return seq
    return seq[:lin0] + new_aa.upper() + seq[lin0 + 1:]


# ─────────────────────────────────────────────────────────────────────────────
# VHH path
# ─────────────────────────────────────────────────────────────────────────────

def validate_and_rank_vhh_candidates(
    seq: str,
    candidates: List[Dict[str, Any]],
    base_metrics: Dict[str, Any],
    base_flags: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    Validate Smart-CMC candidates for a single VHH sequence.

    For each candidate:
      1. Apply the mutation in-silico.
      2. Recompute all miniCMC metrics via compute_vhh_metrics_full.
      3. Compare new flags against base flags.
      4. Annotate with cross_harm_level, cross_harm_metrics, net_score, trade_off_note.
      5. Exclude candidates with any PASS→FAIL regression.
      6. Demote PASS→WARN regressions to priority=LOW.
      7. Return survivors sorted by net_score descending.

    Parameters
    ----------
    seq           : full VHH sequence
    candidates    : list from get_vhh_fr_suggestions()
    base_metrics  : metrics dict from evaluate_single_vhh (pre-mutation)
    base_flags    : flags dict from compute_flags (pre-mutation)

    Returns
    -------
    Annotated and ranked candidate list (excluded candidates omitted).
    """
    try:
        from core.cmc.vhh_cmc_engine import compute_vhh_metrics_full, compute_flags
    except ImportError:
        # Engine unavailable — return candidates unchanged with a warning note
        for c in candidates:
            c.setdefault("cross_harm_level", "NA")
            c.setdefault("cross_harm_metrics", [])
            c.setdefault("net_score", 0.0)
            c.setdefault("trade_off_note", "Cross-validation unavailable (engine import error)")
        return candidates

    validated: List[Dict[str, Any]] = []

    for cand in candidates:
        lin0 = int(cand.get("linear_pos", -1))
        new_aa = str(cand.get("suggested_aa", "")).strip().upper()
        target_metric = str(cand.get("category", ""))

        if lin0 < 0 or not new_aa or len(seq) == 0:
            # Cannot validate — annotate and keep as-is
            cand = dict(cand)
            cand["cross_harm_level"] = "NA"
            cand["cross_harm_metrics"] = []
            cand["net_score"] = 0.0
            cand["trade_off_note"] = "Position unresolvable; manual verification required."
            validated.append(cand)
            continue

        try:
            mutated = _apply_mutation(seq, lin0, new_aa)
            new_metrics = compute_vhh_metrics_full(mutated)
            new_flags = compute_flags(new_metrics)
        except Exception as e:
            cand = dict(cand)
            cand["cross_harm_level"] = "NA"
            cand["cross_harm_metrics"] = []
            cand["net_score"] = 0.0
            cand["trade_off_note"] = f"Re-evaluation failed: {e}"
            validated.append(cand)
            continue

        cand = dict(cand)
        cross_harm_metrics: List[str] = []
        net_score: float = 0.0
        has_fail_cross = False

        for mkey in _VHH_MINICMC_METRICS:
            old_flag = base_flags.get(mkey, "PASS")
            new_flag = new_flags.get(mkey, "PASS")
            delta = _flag_delta_score(old_flag, new_flag)

            is_target = (mkey == target_metric
                         or mkey in (target_metric + "_score",)
                         or target_metric in (mkey + "_score",))

            if is_target:
                net_score += delta
                # Also add quantitative delta bonus
                base_val = base_metrics.get(mkey)
                new_val = new_metrics.get(mkey)
                if base_val is not None and new_val is not None:
                    try:
                        bv = float(base_val) if not isinstance(base_val, list) else float(len(base_val))
                        nv = float(new_val) if not isinstance(new_val, list) else float(len(new_val))
                        if nv < bv:  # lower is better for most metrics (GRAVY, instability, hydro)
                            net_score += _IMPROVE_METRIC_DELTA
                    except Exception:
                        pass
            else:
                # Cross-metric check
                old_r = _FLAG_RANK.get(old_flag, -1)
                new_r = _FLAG_RANK.get(new_flag, -1)
                if new_r > old_r and new_r >= 0:  # degradation
                    cross_harm_metrics.append(
                        f"{mkey}: {old_flag}→{new_flag}"
                    )
                    net_score += delta  # penalty applied
                    if old_flag == "PASS" and new_flag == "FAIL":
                        has_fail_cross = True

        # Determine cross-harm level
        if has_fail_cross:
            cross_harm_level = "FAIL"
        elif cross_harm_metrics:
            cross_harm_level = "WARN_ONLY"
        else:
            cross_harm_level = "NONE"

        # Build trade-off note
        if cross_harm_level == "FAIL":
            trade_off_note = (
                "EXCLUDED — this mutation pushes one or more currently-passing metrics into FAIL: "
                + "; ".join(cross_harm_metrics)
            )
            # Exclude from output
            continue
        elif cross_harm_level == "WARN_ONLY":
            trade_off_note = (
                "TRADE-OFF WARN — metric(s) degraded from IN-RANGE to borderline: "
                + "; ".join(cross_harm_metrics)
                + ". Proceed only if primary benefit outweighs collateral risk."
            )
            cand["priority"] = "LOW"
        else:
            trade_off_note = "Clean — no cross-metric regressions detected."

        cand["cross_harm_level"] = cross_harm_level
        cand["cross_harm_metrics"] = cross_harm_metrics
        cand["net_score"] = round(net_score, 3)
        cand["trade_off_note"] = trade_off_note
        validated.append(cand)

    # Sort: clean HIGH before clean MEDIUM, then WARN_ONLY, lowest net_score last
    def _sort_key(c: Dict[str, Any]) -> Tuple:
        harm_rank = {"NONE": 0, "WARN_ONLY": 1, "NA": 2}.get(c.get("cross_harm_level", "NA"), 2)
        prio_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}.get(c.get("priority", "LOW"), 3)
        return (harm_rank, prio_rank, -c.get("net_score", 0.0))

    validated.sort(key=_sort_key)
    return validated


# ─────────────────────────────────────────────────────────────────────────────
# IgG path
# ─────────────────────────────────────────────────────────────────────────────

def validate_and_rank_igg_candidates(
    vh: str,
    vl: str,
    candidates: List[Dict[str, Any]],
    base_metrics: Dict[str, Any],
    base_flags: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    Validate Smart-CMC candidates for a VH/VL IgG Fv.

    Each candidate must include:
      - linear_pos : 0-based position in the CHAIN (VH or VL)
      - chain       : "VH" or "VL"
      - suggested_aa: single-letter AA

    Uses the same flag-comparison logic as the VHH path, but applies mutations
    per-chain and recomputes the combined Fv metrics.

    Parameters
    ----------
    vh           : VH amino acid sequence
    vl           : VL amino acid sequence
    candidates   : list of candidate dicts (from fr_mutation_sites enumeration)
    base_metrics : pre-mutation metrics dict
    base_flags   : pre-mutation flags dict

    Returns
    -------
    Annotated and ranked candidate list (FAIL-cross candidates excluded).
    """
    try:
        from core.cmc.cmc_metrics import (
            compute_pI, compute_GRAVY, compute_instability_index,
            compute_net_charge, compute_hydro_patch_max9,
            compute_charge_patch_max7, compute_aggregation_motifs,
        )
    except ImportError:
        for c in candidates:
            c.setdefault("cross_harm_level", "NA")
            c.setdefault("cross_harm_metrics", [])
            c.setdefault("net_score", 0.0)
            c.setdefault("trade_off_note", "Cross-validation unavailable (engine import error)")
        return candidates

    def _recompute_igg(vh_s: str, vl_s: str) -> Dict[str, Any]:
        fv = (vh_s or "") + (vl_s or "")
        return {
            "pI":                compute_pI(fv),
            "GRAVY":             compute_GRAVY(fv),
            "instability_index": compute_instability_index(fv),
            "net_charge_pH7":    compute_net_charge(fv, 7.0),
            "hydro_patch_max9":  compute_hydro_patch_max9(fv),
            "charge_patch_max7": compute_charge_patch_max7(fv),
            "agg_motifs":        compute_aggregation_motifs(fv),
        }

    def _igg_flag(mkey: str, val: Any) -> str:
        """Minimal gating for IgG Fv metrics — uses Clinical Reference gates."""
        try:
            from core.cmc.regular_ab_developability import _IGG_THRESHOLDS  # type: ignore
            thres = _IGG_THRESHOLDS.get(mkey)
            if not thres or val is None:
                return "PASS"
            warn_lo, fail_lo, warn_hi, fail_hi = thres
            v = float(len(val)) if isinstance(val, list) else float(val)
            if fail_lo is not None and v < fail_lo:
                return "FAIL"
            if fail_hi is not None and v > fail_hi:
                return "FAIL"
            if warn_lo is not None and v < warn_lo:
                return "WARN"
            if warn_hi is not None and v > warn_hi:
                return "WARN"
            return "PASS"
        except Exception:
            return base_flags.get(mkey, "PASS")  # fallback to base

    validated: List[Dict[str, Any]] = []

    for cand in candidates:
        lin0 = int(cand.get("linear_pos", -1))
        new_aa = str(cand.get("suggested_aa", "")).strip().upper()
        chain = str(cand.get("chain", "VH")).upper()
        target_metric = str(cand.get("category", "") or cand.get("metric_key", ""))

        if lin0 < 0 or not new_aa:
            cand = dict(cand)
            cand["cross_harm_level"] = "NA"
            cand["cross_harm_metrics"] = []
            cand["net_score"] = 0.0
            cand["trade_off_note"] = "Position unresolvable; manual verification required."
            validated.append(cand)
            continue

        try:
            mut_vh = _apply_mutation(vh, lin0, new_aa) if chain == "VH" else vh
            mut_vl = _apply_mutation(vl, lin0, new_aa) if chain == "VL" else vl
            new_metrics = _recompute_igg(mut_vh, mut_vl)
        except Exception as e:
            cand = dict(cand)
            cand["cross_harm_level"] = "NA"
            cand["cross_harm_metrics"] = []
            cand["net_score"] = 0.0
            cand["trade_off_note"] = f"Re-evaluation failed: {e}"
            validated.append(cand)
            continue

        cand = dict(cand)
        cross_harm_metrics: List[str] = []
        net_score: float = 0.0
        has_fail_cross = False

        for mkey in _IGG_MINICMC_METRICS:
            old_flag = base_flags.get(mkey, "PASS")
            new_flag = _igg_flag(mkey, new_metrics.get(mkey))
            delta = _flag_delta_score(old_flag, new_flag)

            is_target = mkey == target_metric or target_metric in mkey or mkey in target_metric

            if is_target:
                net_score += delta
                base_val = base_metrics.get(mkey)
                new_val = new_metrics.get(mkey)
                if base_val is not None and new_val is not None:
                    try:
                        bv = float(base_val) if not isinstance(base_val, list) else float(len(base_val))
                        nv = float(new_val) if not isinstance(new_val, list) else float(len(new_val))
                        if nv < bv:
                            net_score += _IMPROVE_METRIC_DELTA
                    except Exception:
                        pass
            else:
                old_r = _FLAG_RANK.get(old_flag, -1)
                new_r = _FLAG_RANK.get(new_flag, -1)
                if new_r > old_r and new_r >= 0:
                    cross_harm_metrics.append(f"{mkey}: {old_flag}→{new_flag}")
                    net_score += delta
                    if old_flag == "PASS" and new_flag == "FAIL":
                        has_fail_cross = True

        if has_fail_cross:
            cross_harm_level = "FAIL"
        elif cross_harm_metrics:
            cross_harm_level = "WARN_ONLY"
        else:
            cross_harm_level = "NONE"

        if cross_harm_level == "FAIL":
            continue  # excluded
        elif cross_harm_level == "WARN_ONLY":
            trade_off_note = (
                "TRADE-OFF WARN — metric(s) degraded from IN-RANGE to borderline: "
                + "; ".join(cross_harm_metrics)
                + ". Proceed only if primary benefit outweighs collateral risk."
            )
            cand["priority"] = "LOW"
        else:
            trade_off_note = "Clean — no cross-metric regressions detected."

        cand["cross_harm_level"] = cross_harm_level
        cand["cross_harm_metrics"] = cross_harm_metrics
        cand["net_score"] = round(net_score, 3)
        cand["trade_off_note"] = trade_off_note
        validated.append(cand)

    def _sort_key(c: Dict[str, Any]) -> Tuple:
        harm_rank = {"NONE": 0, "WARN_ONLY": 1, "NA": 2}.get(c.get("cross_harm_level", "NA"), 2)
        prio_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}.get(c.get("priority", "LOW"), 3)
        return (harm_rank, prio_rank, -c.get("net_score", 0.0))

    validated.sort(key=_sort_key)
    return validated
