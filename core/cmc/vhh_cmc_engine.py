"""
core/cmc/vhh_cmc_engine.py
===========================
InSynBio AbEngineCore — Shared VHH CMC Engine

Provides all per-arm VHH CMC computation logic shared between:
  - scripts/run_vhh_cmc_eval.py       (single-chain VHH CMC)
  - scripts/run_bispecific_vhh_cmc.py (bispecific VHH-linker-VHH CMC, per-arm)

Public API
----------
  evaluate_single_vhh(name, seq, ref_stats, skip_percentile=False) -> dict
  compute_vhh_metrics_full(seq) -> dict
  compute_flags(metrics) -> dict
  compute_adi_vhh(flags) -> float
  adi_grade(score) -> str
  compute_percentile_ranks(metrics, ref_stats) -> dict
  load_vhh_ref(ref_path) -> dict

  Constants exported:
    _VHH_CONSERVED_CYS, _VHH_THRESHOLDS, _METRIC_LABELS,
    _METRIC_DISPLAY_ORDER, _FLAG_SCORES, _CAT_WEIGHTS, _METRIC_CAT,
    DEFAULT_VHH42_REF
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.cmc.cmc_metrics import (
    compute_pI, compute_GRAVY, compute_instability_index,
    compute_net_charge, compute_hydro_patch_max9,
    compute_charge_patch_max7, compute_aggregation_motifs,
    compute_hydro_cluster_count, compute_chemical_liabilities,
    CDRFingerprintEngine,
)

# ── default reference paths ────────────────────────────────────────────────────
_ENGINE_DIR = Path(__file__).resolve().parent
_SUITE_ROOT  = _ENGINE_DIR.parents[1]
DEFAULT_VHH42_REF = _SUITE_ROOT / "data" / "reference" / "VHH42_reference_stats_v1.json"
VHH_CLINICAL26_REF = _SUITE_ROOT / "data" / "reference" / "VHH_Clinical26_stats_v1.json"
ATLAS24_ENGVH_REF = _SUITE_ROOT / "data" / "reference" / "Atlas24_EngVH_stats_v1.json"
TRANSGENIC_SDAB_REF = _SUITE_ROOT / "data" / "reference" / "Transgenic_sdAb_stats_v1.json"

# ── VHH canonical disulfide positions (0-based, approximate IMGT 23/104) ─────
_VHH_CONSERVED_CYS = {21, 94}

# ── Metric gates: (warn_lo, fail_lo, warn_hi, fail_hi) ───────────────────────
# VHH_CMC_v1.1: SAP / hydro-patch upper gates calibrated from
# VHH68_CMC_Benchmark_v1.0; NOT from IgG Clinical Reference Cohort.
_VHH_THRESHOLDS: Dict[str, tuple] = {
    "pI":                  (4.5,  None,  9.5,  10.0),
    "GRAVY":               (None, None, -0.05,  0.10),
    "instability_index":   (None, None, 50.0,  65.0),
    "net_charge_pH7":      (-6.0, None,  7.0,  10.0),
    "hydro_patch_max9":    (None, None,  0.667, 0.778),
    "charge_patch_max7":   (None, None,  4.0,   6.0),
    "SAP_score":           (None, None,  0.771, 0.857),
    "agg_motifs":          (None, None,  5,     7),
    "hydro_cluster_count": (None, None,  3,     5),
    "glycosylation_sites": (None, None,  1,     2),
    "deamidation_sites":   (None, None,  3,     5),
    "isomerization_sites": (None, None,  3,     5),
    "oxidation_sites":     (None, None,  7,    10),
    "free_cys":            (None, None,  1,     3),
    "exposed_fr2_hydrophobicity": (None, None, -0.457, 0.043), # Parker scale (p75 / p75+0.5)
    # Structure-derived metrics — thresholds calibrated from VHH69 clinical structural benchmark
    # sap_sasa: clinical VHH p25=0.94, p75=1.00 → most VHHs are at 1.0; only extreme outliers flagged
    # psh: clinical VHH p25=14.8, p75=18.5, p95=22.4 → WARN above p75, FAIL above p95
    # ppc/pnc: p75=2.0, p95=2.0 → highly compressed; keep as supplementary display only
    "psh":                 (None, None, 18.5,  22.4),  # Hydrophobic SASA (p75/p95)
    "ppc":                 (None, None,  4.0,   6.0),  # Pos charge cluster (>4 is genuinely elevated)
    "pnc":                 (None, None,  4.0,   6.0),  # Neg charge cluster
}

_METRIC_LABELS: Dict[str, str] = {
    "pI":                  "Isoelectric point (pI)",
    "GRAVY":               "GRAVY (hydrophobicity index)",
    "instability_index":   "Instability index",
    "net_charge_pH7":      "Net charge at pH 7",
    "hydro_patch_max9":    "Hydrophobic patch (max 9-mer)",
    "charge_patch_max7":   "Charge patch (max 7-mer)",
    "SAP_score":           "SAP score (7-mer proxy)",
    "agg_motifs":          "Aggregation motifs (≥3 hydrophobic run)",
    "hydro_cluster_count": "Hydrophobic clusters (≥3 AILMFWV run)",
    "glycosylation_sites": "N-glycosylation sites (NXS/T)",
    "deamidation_sites":   "Deamidation sites (NG/NS)",
    "isomerization_sites": "Isomerization sites (DG/DS)",
    "oxidation_sites":     "Oxidation-prone residues (M/W count)",
    "free_cys":            "Free Cys (beyond conserved disulfide)",
    "vhh_cdr3_len":        "VHH CDR3 length",
    "vhh_cdr3_gravy":      "VHH CDR3 GRAVY",
    "vhh_cdr3_net_charge": "VHH CDR3 net charge",
    "vhh_cdr3_arom_density": "VHH CDR3 aromatic density",
    "vhh_all_cdr_gravy":   "VHH Total CDR GRAVY",
}

_METRIC_DISPLAY_ORDER: List[str] = list(_METRIC_LABELS.keys())

# ── ADI flag-discrete scoring (PASS=100/WARN=50/FAIL=0) ──────────────────────
_FLAG_SCORES: Dict[str, float] = {"PASS": 100.0, "WARN": 50.0, "FAIL": 0.0}
_CAT_WEIGHTS: Dict[str, float] = {
    "hydrophobicity": 0.30,
    "charge":         0.25,
    "chemical":       0.25,
    "aggregation":    0.20,
}
_METRIC_CAT: Dict[str, str] = {
    "pI":                  "charge",
    "GRAVY":               "hydrophobicity",
    "instability_index":   "aggregation",
    "net_charge_pH7":      "charge",
    "charge_patch_max7":   "charge",
    "hydro_patch_max9":    "hydrophobicity",
    "SAP_score":           "hydrophobicity",
    "exposed_fr2_hydrophobicity": "hydrophobicity",
    "agg_motifs":          "aggregation",
    "hydro_cluster_count": "aggregation",
    "glycosylation_sites": "chemical",
    "deamidation_sites":   "chemical",
    "isomerization_sites": "chemical",
    "oxidation_sites":     "chemical",
    "free_cys":            "chemical",
    "psh":                 "hydrophobicity",
    "ppc":                 "charge",
    "pnc":                 "charge",
}


# ═════════════════════════════════════════════════════════════════════════════
# Reference loading
# ═════════════════════════════════════════════════════════════════════════════

def load_vhh_ref(ref_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load VHH reference statistics JSON.
    Unwraps 'metrics' nesting if present.
    Falls back to DEFAULT_VHH42_REF if ref_path is None.
    """
    path = ref_path or DEFAULT_VHH42_REF
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if "metrics" in data and isinstance(data["metrics"], dict):
        return data["metrics"]
    return data


def get_sdab_origin_ref(origin: str) -> Path:
    """
    Return the source-matched sdAb reference path based on origin.

    | origin                                | reference                        | n  | metrics |
    |---------------------------------------|----------------------------------|----|---------|
    | 'camelid_vhh', 'humanized_vhh', ''   | VHH42 clinical camelid (default) | 42 | 14      |
    | 'clinical_vhh'                        | VHH Clinical-26 strict           | 26 | 6       |
    | 'engineered_vh', 'atlas24'            | Atlas-24 engineered VH           | 24 | 6       |
    | 'transgenic_sdab', 'transgenic'       | Transgenic sdAb                  | ~n | 6       |
    """
    o = (origin or "").strip().lower().replace("-", "_")
    if o in {"clinical_vhh"}:
        return VHH_CLINICAL26_REF
    if o in {"engineered_vh", "atlas24", "engineered"}:
        return ATLAS24_ENGVH_REF
    if o in {"transgenic_sdab", "transgenic", "porustobart"}:
        return TRANSGENIC_SDAB_REF
    # Default: VHH42 (most complete — 14 metrics, 42 clinical camelid VHHs)
    return DEFAULT_VHH42_REF


# ═════════════════════════════════════════════════════════════════════════════
# Metric computation
# ═════════════════════════════════════════════════════════════════════════════

def _sap_proxy(seq: str) -> float:
    """Sequence-proxy SAP: max fraction of AILMFWV in 7-mer window."""
    _H = frozenset("AILMFWV")
    s = seq.upper()
    if len(s) < 7:
        return round(sum(1 for a in s if a in _H) / 7.0, 3)
    return round(max(
        sum(1 for a in s[i:i+7] if a in _H) / 7.0
        for i in range(len(s) - 6)
    ), 3)


def compute_vhh_metrics_full(seq: str) -> Dict[str, Any]:
    """
    Compute all 15 CMC metrics for a single VHH sequence.

    Corrections vs raw cmc_metrics.py:
    - SAP_score:  7-mer hydrophobic proxy (not in base cmc_metrics)
    - free_cys:   excludes canonical VHH disulfide positions {21, 94}
    - _positions: 0-based liability site lists for reporting
    """
    s = seq.strip().upper()
    liab = compute_chemical_liabilities(s, vh_len=len(s))
    raw_cys = liab.get("free_cys", [])
    free_cys_filtered = [p for p in raw_cys
                         if all(abs(p - c) > 2 for c in _VHH_CONSERVED_CYS)]

    return {
        "pI":                  compute_pI(s),
        "GRAVY":               compute_GRAVY(s),
        "instability_index":   compute_instability_index(s),
        "net_charge_pH7":      compute_net_charge(s, 7.0),
        "hydro_patch_max9":    compute_hydro_patch_max9(s),
        "charge_patch_max7":   compute_charge_patch_max7(s),
        "SAP_score":           _sap_proxy(s),
        "SAP_mode":            "sequence_proxy_7mer",
        "agg_motifs":          compute_aggregation_motifs(s),
        "hydro_cluster_count": compute_hydro_cluster_count(s),
        "glycosylation_sites": len(liab.get("glycosylation_sites", [])),
        "deamidation_sites":   len(liab.get("deamidation_sites", [])),
        "isomerization_sites": len(liab.get("isomerization_sites", [])),
        "oxidation_sites":     len(liab.get("oxidation_sites", [])),
        "free_cys":            len(free_cys_filtered),
        "_positions": {
            "glycosylation":  liab.get("glycosylation_sites", []),
            "deamidation":    liab.get("deamidation_sites", []),
            "isomerization":  liab.get("isomerization_sites", []),
            "oxidation":      liab.get("oxidation_sites", []),
            "free_cys":       free_cys_filtered,
        },
    }


# ═════════════════════════════════════════════════════════════════════════════
# Risk flags
# ═════════════════════════════════════════════════════════════════════════════

def flag_metric(name: str, value: Any) -> str:
    """Return PASS / WARN / FAIL / NA for a single metric value."""
    thres = _VHH_THRESHOLDS.get(name)
    if not thres:
        return "PASS"
    if value is None:
        return "NA"
    warn_lo, fail_lo, warn_hi, fail_hi = thres
    v = float(len(value)) if isinstance(value, list) else float(value)
    if fail_lo is not None and v < fail_lo:
        return "FAIL"
    if fail_hi is not None and v > fail_hi:
        return "FAIL"
    if warn_lo is not None and v < warn_lo:
        return "WARN"
    if warn_hi is not None and v > warn_hi:
        return "WARN"
    return "PASS"


def compute_flags(metrics: Dict[str, Any]) -> Dict[str, str]:
    """Return PASS/WARN/FAIL for all 14 gated metrics."""
    return {k: flag_metric(k, metrics.get(k)) for k in _VHH_THRESHOLDS}


# ═════════════════════════════════════════════════════════════════════════════
# ADI — flag-discrete, 4-category weighted
# ═════════════════════════════════════════════════════════════════════════════

def compute_adi_vhh(flags: Dict[str, str]) -> float:
    """
    Compute ADI (0–100) from PASS/WARN/FAIL flags.

    Method: flag score per metric → category mean → weighted sum.
    Weights: hydrophobicity 30% / charge 25% / chemical 25% / aggregation 20%.
    Consistent with run_vhh_cmc_eval.py.
    """
    cat_scores: Dict[str, List[float]] = {k: [] for k in _CAT_WEIGHTS}
    for metric, flag in flags.items():
        cat = _METRIC_CAT.get(metric)
        if cat and flag in _FLAG_SCORES:
            cat_scores[cat].append(_FLAG_SCORES[flag])
    total = active = 0.0
    for cat, w in _CAT_WEIGHTS.items():
        vals = cat_scores[cat]
        if vals:
            total += (sum(vals) / len(vals)) * w
            active += w
    return round(total / active, 1) if active else 0.0


def adi_grade(score: float) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Acceptable"
    if score >= 40:
        return "Moderate risk"
    return "High risk"


# ═════════════════════════════════════════════════════════════════════════════
# Percentile ranks
# ═════════════════════════════════════════════════════════════════════════════

def _percentile_rank(value: float, p_dict: Dict[str, float]) -> str:
    """Return percentile band: <p5 | p5-p25 | p25-p75 ✓ | p75-p95 | >p95."""
    p5  = p_dict.get("p5",  float("-inf"))
    p25 = p_dict.get("p25", float("-inf"))
    p75 = p_dict.get("p75", float("inf"))
    p95 = p_dict.get("p95", float("inf"))
    if value < p5:
        return "<p5"
    if value <= p25:
        return "p5-p25"
    if value <= p75:
        return "p25-p75 ✓"
    if value <= p95:
        return "p75-p95"
    return ">p95"


def compute_percentile_ranks(
    metrics: Dict[str, Any],
    ref_stats: Dict[str, Any],
) -> Dict[str, str]:
    """Return percentile band string for each metric vs Clinical VHH Benchmark reference."""
    ranks: Dict[str, str] = {}
    for key in _METRIC_DISPLAY_ORDER:
        val = metrics.get(key)
        ref = ref_stats.get(key, {})
        if val is None or not ref:
            ranks[key] = "N/A"
            continue
        ranks[key] = _percentile_rank(float(val), ref)
    return ranks


# ═════════════════════════════════════════════════════════════════════════════
# Top-level per-VHH evaluation
# ═════════════════════════════════════════════════════════════════════════════

def evaluate_single_vhh(
    name: str,
    seq: str,
    ref_stats: Optional[Dict[str, Any]] = None,
    skip_percentile: bool = False,
    er_pi_warn: float = 8.5,
    er_pi_crit: float = 9.0,
    origin: str = "humanized_vhh",
) -> Dict[str, Any]:
    """
    Full industrial-grade CMC assessment for one VHH sequence.

    Parameters
    ----------
    name          : display name / ID
    seq           : amino acid sequence (uppercase or mixed)
    ref_stats     : Optional loaded reference dict. If None, uses get_sdab_origin_ref(origin).
    skip_percentile : skip percentile rank computation (speeds up large batches)
    er_pi_warn    : pI above this → 'warn' expression flag (default 8.5)
    er_pi_crit    : pI above this → 'critical' expression flag (default 9.0)
    origin        : 'humanized_vhh', 'engineered_vh', or 'transgenic'

    Returns
    -------
    dict with keys:
      name, sequence, length,
      metrics (15 + _positions),
      risk_flags (14 × PASS/WARN/FAIL),
      percentile_ranks,
      adi_score, adi_grade,
      n_warn, n_fail, overall_status,
      pi_flag ('pass' / 'warn' / 'critical'),
      reference_source (filename)
    """
    if ref_stats is None:
        ref_path = get_sdab_origin_ref(origin)
        ref_stats = load_vhh_ref(ref_path)
        ref_name = ref_path.name
    else:
        ref_name = "user_provided"

    metrics = compute_vhh_metrics_full(seq)
    
    _onorm = origin.strip().lower().replace("-", "_")
    _is_engvh = _onorm in {"engineered_vh", "atlas24", "engineered"}
    # Both engineered_vh (autonomous VH like KN035) and transgenic_sdab (transgenic-mouse-derived
    # SCAb like Porustobart/HBM4003) legitimately retain VH-canonical FR2 — they must NOT be
    # penalised for missing camelid hallmarks or for hydrophobic VH-type FR2.
    _is_vh_like_sdab = _is_engvh or _onorm in {"transgenic_sdab", "transgenic", "porustobart"}

    # VHH-specific checks (hallmark, FR2 hydrophobicity, Cys annotation)
    vhh_specific: Dict[str, Any] = {}
    try:
        vhh_specific = compute_vhh_specific_checks(seq)
        if _is_vh_like_sdab:
            _note_tag = "engineered_vh" if _is_engvh else "transgenic_sdab"
            # Override: VH-type residues at 44/45/47 are EXPECTED for autonomous VH / SCAb — not a defect
            vhh_specific["fr2_hallmark_ok"] = True  # suppress WARN
            vhh_specific["fr2_hallmark_flag"] = "N/A"
            vhh_specific["fr2_hallmark_note"] = f"VH-type FR2 retained ({_note_tag} — expected)"
            # FR2 hydrophobicity is also not penalised: VH FR2 is intrinsically hydrophobic
            vhh_specific["fr2_hydro_flag"] = "N/A"
            vhh_specific["fr2_hydro_note"] = f"Hydrophobic VH-type FR2 interface retained ({_note_tag})"
        
        # Inject FR2 hydro into core metrics so it affects Gate Score
        if vhh_specific.get("exposed_fr2_hydrophobicity") is not None:
            metrics["exposed_fr2_hydrophobicity"] = vhh_specific["exposed_fr2_hydrophobicity"]
    except Exception:
        pass

    flags   = compute_flags(metrics)
    # For VH-like sdAb (engineered_vh, transgenic_sdab), hydrophobic VH FR2 is expected.
    # Suppress the WARN/FAIL on exposed_fr2_hydrophobicity so it does not trigger Smart-CMC
    # hallmark-rescue suggestions or degrade Gate Score.
    if _is_vh_like_sdab:
        flags["exposed_fr2_hydrophobicity"] = "N/A"
    adi     = compute_adi_vhh(flags)
    grade   = adi_grade(adi)
    pct     = ({} if skip_percentile
               else compute_percentile_ranks(metrics, ref_stats))

    n_warn = sum(1 for v in flags.values() if v == "WARN")
    n_fail = sum(1 for v in flags.values() if v == "FAIL")

    # AbNatiV2 Naturalness Δ (V1.8) — store VH2, VHH2, and Δ
    abnativ_delta = None
    abnativ_tier = "UNKNOWN"
    abnativ_vh2_score = None
    abnativ_vhh2_score = None
    abnativ_error = None
    try:
        import queue as _queue
        import threading as _threading

        from core.vh2vhh.abnativ_naturalness_layer import score_naturalness_delta

        _abnativ_q: _queue.Queue = _queue.Queue()

        def _abnativ_worker() -> None:
            try:
                _abnativ_q.put(score_naturalness_delta(seq.strip().upper()))
            except Exception as _e:
                _abnativ_q.put(_e)

        _t = _threading.Thread(target=_abnativ_worker, daemon=True)
        _t.start()
        _t.join(240)  # 240s timeout — cold AbNatiV import+score can exceed 120s on first boot
        if not _abnativ_q.empty():
            _abres = _abnativ_q.get()
            if isinstance(_abres, Exception):
                abnativ_error = f"{type(_abres).__name__}: {_abres}"
            elif getattr(_abres, "error", None):
                _notes_str = f" ({', '.join(_abres.notes)})" if getattr(_abres, "notes", None) else ""
                abnativ_error = f"{_abres.error}{_notes_str}"
            else:
                abnativ_delta      = round(float(_abres.delta), 4)      if _abres.delta      is not None else None
                abnativ_vh2_score  = round(float(_abres.vh2_score), 4)  if _abres.vh2_score  is not None else None
                abnativ_vhh2_score = round(float(_abres.vhh2_score), 4) if _abres.vhh2_score is not None else None
                _raw_tier = getattr(_abres, "tier", "UNKNOWN")
                # EngVH: negative Δ (VH-like) is expected and correct → re-map tier
                if _is_vh_like_sdab and abnativ_delta is not None:
                    # VH-like sdAb (engineered_vh, transgenic_sdab): negative delta is EXPECTED
                    # (the molecule is intentionally more VH2-like than VHH2-like). Only flag
                    # if it is unexpectedly VHH-like (positive delta >0.3).
                    if abnativ_delta < 0:
                        abnativ_tier = "PASS"
                    elif abnativ_delta > 0.3:
                        abnativ_tier = "WARN"
                    else:
                        abnativ_tier = "PASS"
                else:
                    abnativ_tier = _raw_tier
        else:
            abnativ_error = "Timeout: AbNatiV inference exceeded 240s"
    except Exception as _e:
        abnativ_error = f"{type(_e).__name__}: {_e}"

    # HPR Index (V1.8)
    hpr_score = None
    try:
        import queue as _hq
        import threading as _ht

        from core.humanization.hpr_index import compute_hpr_index

        _hpr_q: _hq.Queue = _hq.Queue()

        def _hpr_worker() -> None:
            try:
                _hpr_q.put(compute_hpr_index(seq.strip().upper(), ""))
            except Exception as _e:
                _hpr_q.put(None)

        _ht2 = _ht.Thread(target=_hpr_worker, daemon=True)
        _ht2.start()
        _ht2.join(60)
        if not _hpr_q.empty():
            _hpr_res = _hpr_q.get()
            if _hpr_res is not None:
                hpr_score = (_hpr_res.get("combined") or {}).get("score")
    except Exception:
        pass

    pi_flag = (
        "critical" if metrics["pI"] >= er_pi_crit else
        "warn"     if metrics["pI"] >= er_pi_warn  else
        "pass"
    )

    # sdAb adaptation sites (L18S, F68Y) — relevant for engineered_vh
    engvh_adaptation: Dict[str, Any] = {}
    if _is_engvh:
        try:
            engvh_adaptation = compute_engvh_adaptation_check(seq)
        except Exception:
            pass

    # Atlas-24 Similarity Score (V1.6 §6.7) — only for engineered_vh origin
    atlas24_similarity: Optional[Dict[str, Any]] = None
    if _is_engvh:
        try:
            import threading as _at
            import queue as _aq
            from core.vh2vhh.engineered_vh_similarity import score_engineered_vh_similarity

            _a24_q: _aq.Queue = _aq.Queue()

            def _a24_worker() -> None:
                try:
                    _a24_q.put(score_engineered_vh_similarity(seq.strip().upper()))
                except Exception as _e:
                    _a24_q.put(None)

            _a24_t = _at.Thread(target=_a24_worker, daemon=True)
            _a24_t.start()
            _a24_t.join(30)
            if not _a24_q.empty():
                _a24_res = _a24_q.get()
                if _a24_res is not None:
                    atlas24_similarity = _a24_res.to_dict()
        except Exception:
            pass

    # CDR Fingerprint (V1.9)
    cdr_fp = CDRFingerprintEngine.compute_fingerprint(seq.strip().upper(), "")
    # Rename keys to be VHH-specific for the frontend
    vhh_cdr_fp = {k.replace("vh_", "vhh_"): v for k, v in cdr_fp.items() if k.startswith("vh_")}
    metrics.update(vhh_cdr_fp)

    return {
        "name":                      name,
        "sequence":                  seq.strip().upper(),
        "length":                    len(seq.strip()),
        "metrics":                   metrics,
        "risk_flags":                flags,
        "percentile_ranks":          pct,
        "adi_score":                 adi,
        "adi_grade":                 grade,
        "n_warn":                    n_warn,
        "n_fail":                    n_fail,
        "overall_status":            "FAIL" if n_fail > 0 else ("WARN" if n_warn > 0 else "PASS"),
        "pi_flag":                   pi_flag,
        "abnativ_delta":             abnativ_delta,
        "abnativ_tier":              abnativ_tier,
        "abnativ_vh2_score":          abnativ_vh2_score,
        "abnativ_vhh2_score":         abnativ_vhh2_score,
        "abnativ_error":             abnativ_error,
        "hpr_score":                 hpr_score,
        "reference_source":          ref_name,
        "sdab_origin":               origin,
        "ref_ranges":                _build_ref_ranges(ref_stats),
        "vhh_specific":              vhh_specific,
        "engvh_adaptation":          engvh_adaptation if _is_engvh else None,
        "atlas24_similarity":        atlas24_similarity,
        "cdr_fingerprint":           vhh_cdr_fp,
    }


# Kabat positions critical for VH→sdAb adaptation (from Atlas-24 + V1.8 standard)
_ENGVH_ADAPTATION_SITES: Dict[int, Dict[str, Any]] = {
    18: {
        "sdab_aa":    "S",
        "vh_typical": "L",
        "label":      "L18S (Kabat 18)",
        "function":   "Reduces VH-type FR1 aggregation tendency in autonomous single-domain context",
        "priority":   "HIGH",
    },
    68: {
        "sdab_aa":    "Y",
        "vh_typical": "F",
        "label":      "F68Y (Kabat 68)",
        "function":   "Improves thermal stability by introducing Tyr-mediated H-bond network in FR3",
        "priority":   "MEDIUM",
    },
}


def compute_engvh_adaptation_check(seq: str) -> Dict[str, Any]:
    """
    Check sdAb-specific adaptation sites for engineered autonomous VH molecules.

    Inspects Kabat positions 18 (L18S) and 68 (F68Y) — the two critical sdAb
    adaptation mutations defined in VH→VHH Conversion Standard V1.8 §2 Phase 4.5
    and observed in the Atlas-24 engVH clinical dataset.

    Uses ANARCI (via kabat_from_anarcii) for accurate Kabat numbering.
    Falls back to a sequence-position heuristic if ANARCI is unavailable.

    Returns
    -------
    dict with:
        sites      : list of {pos, label, found_aa, sdab_aa, status, function, priority}
        adapted    : int  — count of sites already showing sdAb-type residue
        missing    : int  — count of sites still showing VH-canonical residue
        other      : int  — count of sites with unexpected residue
        summary    : str  — human-readable summary
        anarci_ok  : bool — whether Kabat numbering succeeded
    """
    seq = seq.strip().upper()
    sites_out: List[Dict[str, Any]] = []
    anarci_ok = False

    # Try ANARCI first for accurate Kabat numbering
    kabat_dict: Dict[int, str] = {}
    try:
        from anarcii import Anarcii  # type: ignore[import]
        from core.humanization.kabat_utils import kabat_from_anarcii

        an = Anarcii()  # type: ignore[call-arg]
        res_an = an.number([("engvh", seq)])  # type: ignore[attr-defined]
        try:
            res_an = an.to_scheme("kabat")  # type: ignore[attr-defined]
        except Exception:
            pass
        entry = res_an.get("engvh", {}) if isinstance(res_an, dict) else {}
        numbering = entry.get("numbering", []) if entry else []
        kd = kabat_from_anarcii(numbering)
        kabat_dict = {pos: aa for (pos, ins), aa in kd.items() if ins == ""}
        anarci_ok = bool(kabat_dict)
    except Exception:
        pass

    # Heuristic fallback: approximate Kabat 18 ≈ seq[17], Kabat 68 ≈ seq[66]
    # (valid for canonical ~120aa VH domains; offset from most VHH sequences)
    if not kabat_dict:
        L = len(seq)
        if L >= 120:
            kabat_dict = {18: seq[17], 68: seq[66]}

    adapted = missing = other = 0
    for pos, info in sorted(_ENGVH_ADAPTATION_SITES.items()):
        found_aa = kabat_dict.get(pos, "?")
        if found_aa == info["sdab_aa"]:
            status = "ADAPTED"
            adapted += 1
        elif found_aa == info["vh_typical"] or found_aa == "?":
            status = "VH_CANONICAL" if found_aa != "?" else "UNKNOWN"
            missing += 1 if found_aa != "?" else 0
        else:
            status = "OTHER"
            other += 1
        sites_out.append({
            "kabat_pos":  pos,
            "label":      info["label"],
            "found_aa":   found_aa,
            "sdab_aa":    info["sdab_aa"],
            "vh_typical": info["vh_typical"],
            "status":     status,
            "function":   info["function"],
            "priority":   info["priority"],
        })

    if missing == 0:
        summary = f"Both sdAb adaptation sites present ({adapted}/2). Sequence is optimized."
    elif missing == 2:
        summary = "Neither sdAb adaptation mutation applied (L18S, F68Y absent). FR engineering recommended."
    else:
        missing_labels = [s["label"] for s in sites_out if s["status"] == "VH_CANONICAL"]
        summary = f"{missing}/2 adaptation site(s) absent: {', '.join(missing_labels)}. Partial FR engineering recommended."

    return {
        "sites":     sites_out,
        "adapted":   adapted,
        "missing":   missing,
        "other":     other,
        "summary":   summary,
        "anarci_ok": anarci_ok,
    }


# ── VHH-specific sequence checks (hallmark, cys, FR2 hydrophobicity) ──────────

# Parker hydrophobicity scale (used for FR2 exposed-surface estimate)
_PARKER_SCALE: Dict[str, float] = {
    "A": 0.5, "C": -1.0, "D": 3.0, "E": 3.0, "F": -2.5,
    "G": 0.0, "H": -0.5, "I": -1.8, "K": 3.0, "L": -1.8,
    "M": -1.3, "N": 0.2, "P": 0.0, "Q": 0.2, "R": 3.0,
    "S": 0.3, "T": 0.4, "V": -1.5, "W": -3.4, "Y": -2.3,
}

# VHH hallmark residues at Kabat positions 37/44/45/47 (VH-interface positions
# that VHH replaces with hydrophilic residues to compensate for absent VL).
# PASS residues: anything not strongly hydrophobic at each position.
_VHH_HALLMARK_KABAT_POS = (37, 44, 45, 47)
_VHH_HALLMARK_VH_FAIL = {
    37: {"W", "Y"},          # VH has W37; VHH typically F/Y → acceptable when ≠ W
    44: {"G"},               # VH has G44; VHH replaces with E/Q/L → fail if still G
    45: {"L"},               # VH has L45; VHH replaces with R/K  → fail if still L
    47: {"W", "L"},          # VH has W47; VHH replaces with G/F/S → fail if still W
}

# VHH68 reference for VHH-specific metrics (frozen, 2026-05-11)
_VHH68_SPECIFIC_REF = {
    "exposed_fr2_hydrophobicity": {"p25": -1.150, "p75": -0.457, "mean": -0.900, "stdev": 0.395, "n": 69},
    "nanobert_pll":               {"p25": -0.322, "p75": -0.247, "mean": -0.284, "stdev": 0.062, "n": 69},
    "cdr3_compactness_ca_dist":   None,  # structural only — not computable from sequence
}


def compute_vhh_specific_checks(seq: str) -> Dict[str, Any]:
    """
    Compute VHH-format-specific CMC parameters not included in the generic 14-metric panel.

    Parameters computed (sequence-based, no structure needed):
      fr2_hallmark_tetrad      : 4-char string of residues at Kabat 37/44/45/47
      fr2_hallmark_ok          : True if all 4 positions are VHH-type (not VH-canonical)
      fr2_hallmark_flag        : PASS / WARN / FAIL
      exposed_fr2_hydrophobicity: Parker-scale mean over the FR2 window (positions ~30-50
                                  in the linear sequence; approximate without full numbering)
      fr2_hydro_flag           : PASS / WARN / FAIL vs VHH68 p25/p75
      noncanonical_cys         : number of Cys beyond the 2 canonical Cys (VH-CDR3 disulfide
                                  in some VHH is a feature, not a risk — annotated accordingly)
      noncanonical_cys_flag    : INFO / WARN
      cdr3_length_estimate     : CDR3 residue count (estimated from sequence length heuristic)
      vhh_specific_ref         : VHH68 reference bands for these metrics

    Returns: dict with the above keys.
    """
    seq = seq.strip().upper()
    result: Dict[str, Any] = {}

    # ── 1. FR2 hallmark tetrad (requires ANARCI Kabat numbering) ────────────
    fr2_tetrad = None
    fr2_ok = False
    fr2_flag = "NOT_RUN"
    try:
        from anarcii import Anarcii  # type: ignore[import]
        an = Anarcii()  # type: ignore[call-arg]
        result_an = an.number([("vhh", seq)])  # type: ignore[attr-defined]
        try:
            result_an = an.to_scheme("kabat")  # type: ignore[attr-defined]
        except Exception:
            pass
        entry = result_an.get("vhh", {}) if isinstance(result_an, dict) else {}
        numbering = entry.get("numbering", []) if entry else []
        # Build {(pos, ins): aa} dict
        num_dict = {}
        for item in numbering:
            if len(item) >= 2 and isinstance(item[0], tuple):
                # anarcii format: ((pos, ins_code), aa)
                pos, ins = item[0][0], item[0][1]
                aa = item[1]
                num_dict[(int(pos), str(ins).strip())] = aa
            elif len(item) >= 3:
                # fallback: (pos, ins_code, aa)
                pos, ins, aa = item[0], item[1], item[2]
                num_dict[(int(pos), str(ins).strip())] = aa
        tetrad_residues = []
        for p in _VHH_HALLMARK_KABAT_POS:
            aa = num_dict.get((p, ""), num_dict.get((p, " "), "?"))
            tetrad_residues.append(aa if aa else "?")
        fr2_tetrad = "".join(tetrad_residues)
        fr2_ok = all(
            tetrad_residues[i] not in _VHH_HALLMARK_VH_FAIL.get(_VHH_HALLMARK_KABAT_POS[i], set())
            for i in range(4)
        )
        fr2_flag = "PASS" if fr2_ok else "WARN"
    except Exception as _e:
        fr2_flag = "NOT_RUN"

    result["fr2_hallmark_tetrad"] = fr2_tetrad
    result["fr2_hallmark_ok"] = fr2_ok
    result["fr2_hallmark_flag"] = fr2_flag

    # ── 2. Exposed FR2 hydrophobicity (Parker scale, FR2 window heuristic) ──
    # Without full ANARCI, approximate FR2 as positions ~(len*0.25)–(len*0.42)
    # For a 120aa VHH: FR2 ≈ positions 30–50 (0-indexed: 28–48)
    fr2_hydro = None
    fr2_hydro_flag = "NOT_RUN"
    try:
        L = len(seq)
        fr2_start = max(0, int(L * 0.25))
        fr2_end   = min(L, int(L * 0.43))
        fr2_window = seq[fr2_start:fr2_end]
        if fr2_window:
            fr2_hydro = round(
                sum(_PARKER_SCALE.get(aa, 0.0) for aa in fr2_window) / len(fr2_window), 3
            )
            ref = _VHH68_SPECIFIC_REF["exposed_fr2_hydrophobicity"]
            if fr2_hydro <= ref["p75"]:           # normal (negative = hydrophilic)
                fr2_hydro_flag = "PASS"
            elif fr2_hydro <= ref["p75"] + 0.5:   # slightly elevated
                fr2_hydro_flag = "WARN"
            else:
                fr2_hydro_flag = "FAIL"
    except Exception:
        pass

    result["exposed_fr2_hydrophobicity"] = fr2_hydro
    result["fr2_hydro_flag"] = fr2_hydro_flag

    # ── 3. Noncanonical Cys annotation ─────────────────────────────────────
    total_cys = seq.count("C")
    noncanon_cys = max(0, total_cys - 2)   # 2 canonical Cys for intra-domain disulfide
    # In VHH, extra disulfide between CDR3 and FR2 is common (feature, not risk)
    noncanon_note = "CDR3-FR2 extra disulfide (feature — common in camelid VHH)" if noncanon_cys > 0 else "None"
    result["noncanonical_cys"] = noncanon_cys
    result["noncanonical_cys_flag"] = "INFO" if noncanon_cys > 0 else "PASS"
    result["noncanonical_cys_note"] = noncanon_note

    # ── 4. CDR3 length estimate (sequence-length heuristic) ────────────────
    # Average VHH length: 120-130 aa. CDR3 starts ~aa 99-100 (IMGT)
    # For a precise count use ANARCI fr2_tetrad above; here approximate
    cdr3_est = None
    try:
        L = len(seq)
        # Last segment after C (canonical) ≈ CDR3 + FR4
        last_c_pos = seq.rfind("C", 80, L - 10)
        if last_c_pos > 0:
            # WGxG = FR4 start ≈ CDR3 end
            wg_pos = seq.find("WGQ", last_c_pos) or seq.find("WGA", last_c_pos) or seq.find("WGT", last_c_pos)
            if wg_pos > last_c_pos:
                cdr3_est = wg_pos - last_c_pos - 1
    except Exception:
        pass
    result["cdr3_length_estimate"] = cdr3_est

    # ── 5. Reference bands for VHH-specific metrics ─────────────────────────
    result["vhh_specific_ref"] = {
        "exposed_fr2_hydrophobicity": _VHH68_SPECIFIC_REF["exposed_fr2_hydrophobicity"],
        "source": "VHH clinical cohort",
    }

    return result


def _build_ref_ranges(ref_stats: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Build a display-ready reference-range dict from loaded ref_stats.
    Returns {metric: {p25, p75, p5, p95, mean}} for each metric present.
    Used to annotate CMC report tables with normal intervals.
    """
    out: Dict[str, Dict[str, Any]] = {}
    
    # Check both top-level and 'metrics' sub-dict
    source = ref_stats.get("metrics") or ref_stats or {}
    
    for k, v in source.items():
        if not isinstance(v, dict):
            continue
        row: Dict[str, Any] = {}
        for band in ("p5", "p25", "p50", "p75", "p95", "mean", "stdev"):
            if band in v and v[band] is not None:
                row[band] = v[band]
        if "p25" in row and "p75" in row:
            out[k] = row
            
    # Also merge CDR fingerprint ranges if available in 'loci'
    if "loci" in ref_stats:
        for locus, l_data in ref_stats["loci"].items():
            l_metrics = l_data.get("metrics", {})
            chain = "vhh" # VHH engine is single-chain
            for m_key, m_stats in l_metrics.items():
                full_key = None
                if m_key == "length": full_key = f"{chain}_cdr3_len"
                elif m_key == "gravy": full_key = f"{chain}_cdr3_gravy"
                elif m_key == "net_charge_pH7": full_key = f"{chain}_cdr3_net_charge"
                elif m_key == "aromatic_fraction": full_key = f"{chain}_cdr3_arom_density"
                
                if full_key and locus.endswith("cdr3") and isinstance(m_stats, dict):
                    row = {b: m_stats[b] for b in ("p5", "p25", "p50", "p75", "p95", "mean") if b in m_stats}
                    if "p25" in row:
                        out[full_key] = row
                
                # Total CDR load (all_cdr_gravy)
                if locus.endswith("all_cdr") and "gravy" in l_metrics and isinstance(l_metrics["gravy"], dict):
                    row = {b: l_metrics["gravy"][b] for b in ("p5", "p25", "p50", "p75", "p95", "mean") if b in l_metrics["gravy"]}
                    if "p25" in row:
                        out[f"{chain}_all_cdr_gravy"] = row
                        
    return out


# ═════════════════════════════════════════════════════════════════════════════
# Structure-based metrics (NanoBodyBuilder2 PDB, single-domain / VHH only)
# ═════════════════════════════════════════════════════════════════════════════

# IMGT CDR residue number ranges for VHH chain H (inclusive)
_IMGT_CDR_RANGES = {
    "H1": (27, 38),
    "H2": (56, 65),
    "H3": (105, 117),
}

_HYDRO_AA3 = {"ALA", "VAL", "ILE", "LEU", "MET", "PHE", "TRP", "TYR"}
_POS_AA3   = {"LYS", "ARG", "HIS"}
_NEG_AA3   = {"ASP", "GLU"}


def compute_vhh_structural_metrics(pdb_path: str) -> Dict[str, Any]:
    """
    Compute structure-based CMC metrics for a VHH PDB (chain H, IMGT numbering).

    Requires: BioPython (Bio.PDB.SASA.ShrakeRupley) — available in anarcii/affmat envs.

    Returns dict with keys:
        plddt_proxy (float | None)   — not re-computed here; caller injects from NanoBodyBuilder2
        psh (float)                  — total surface hydrophobic SASA (AILMFWVY; Å²×0.01 proxy)
        ppc (float)                  — max consecutive positive-charge cluster (count)
        pnc (float)                  — max consecutive negative-charge cluster (count)
        sap_sasa (float)             — max 7-residue window fraction of hydrophobic SASA
        cdr_sasa (dict)              — {H1, H2, H3}: mean per-residue SASA for each CDR loop (Å²)
        sap_mode (str)               — 'sasa_7mer'
        _struct_cmc_error (str|None) — error message if computation failed
    """
    try:
        import Bio.PDB as bpdb  # type: ignore
        from Bio.PDB.SASA import ShrakeRupley  # type: ignore
    except ImportError as exc:
        return {"_struct_cmc_error": f"BioPython unavailable: {exc}"}

    try:
        parser = bpdb.PDBParser(QUIET=True)  # type: ignore[attr-defined]
        structure = parser.get_structure("vhh", str(pdb_path))
        sr = ShrakeRupley()
        sr.compute(structure, level="R")
        model = structure[0]  # type: ignore[index]

        # Collect chain H residues only
        h_chain = None
        for ch in model.get_chains():
            if ch.id in ("H", "A"):   # NanoBodyBuilder2 typically uses "H"
                h_chain = ch
                break
        if h_chain is None:
            return {"_struct_cmc_error": "Chain H not found in PDB"}

        residues = [
            r for r in h_chain.get_residues()
            if r.get_resname() in set(list(_HYDRO_AA3) + list(_POS_AA3) + list(_NEG_AA3) +
                                      ["SER", "THR", "ASN", "GLN", "GLY", "PRO", "CYS",
                                       "ASP", "GLU", "LYS", "ARG", "HIS"])
            and r.id[0] == " "  # exclude heteroatoms
        ]

        # Per-residue SASA (Å²) indexed by IMGT resnum
        sasa_by_resnum: Dict[int, float] = {}
        res_order: list = []  # (resnum, resname, sasa) ordered by PDB position
        for r in residues:
            resnum = r.id[1]
            sasa_val = float(getattr(r, "sasa", 0.0) or 0.0)
            sasa_by_resnum[resnum] = sasa_val
            res_order.append((resnum, r.get_resname(), sasa_val))
        res_order.sort(key=lambda x: x[0])

        # psh: total SASA of hydrophobic residues × normalisation factor
        psh = sum(s for _, aa3, s in res_order if aa3 in _HYDRO_AA3) * 0.01

        # ppc / pnc: max consecutive charge cluster
        def _max_cluster(charge_set: set) -> int:
            best = cur = 0
            for _, aa3, _ in res_order:
                if aa3 in charge_set:
                    cur += 1
                    best = max(best, cur)
                else:
                    cur = 0
            return best

        ppc = float(_max_cluster(_POS_AA3))
        pnc = float(_max_cluster(_NEG_AA3))

        # sap_sasa: sliding 7-residue window, fraction of hydrophobic SASA
        sap_sasa = 0.0
        if len(res_order) >= 7:
            total_sasa_all = sum(s for _, _, s in res_order) or 1.0
            sap_sasa = max(
                sum(s for _, aa3, s in res_order[i:i+7] if aa3 in _HYDRO_AA3)
                / max(sum(s for _, _, s in res_order[i:i+7]), 1e-6)
                for i in range(len(res_order) - 6)
            )
        sap_sasa = round(sap_sasa, 4)

        # CDR SASA: mean per-residue SASA for each CDR loop
        cdr_sasa: Dict[str, Any] = {}
        for loop, (lo, hi) in _IMGT_CDR_RANGES.items():
            loop_sasa = [v for k, v in sasa_by_resnum.items() if lo <= k <= hi]
            cdr_sasa[loop] = round(sum(loop_sasa) / len(loop_sasa), 2) if loop_sasa else None

        # CDR3 compactness: Cα distance between first and last CDR3 residue
        cdr3_ca_dist: float | None = None
        cdr3_lo, cdr3_hi = _IMGT_CDR_RANGES["H3"]
        cdr3_residues = [
            r for r in h_chain.get_residues()
            if cdr3_lo <= r.id[1] <= cdr3_hi and r.id[0] == " " and "CA" in r
        ]
        if len(cdr3_residues) >= 2:
            ca_first = cdr3_residues[0]["CA"].get_vector()
            ca_last  = cdr3_residues[-1]["CA"].get_vector()
            cdr3_ca_dist = round(float((ca_last - ca_first).norm()), 2)

        return {
            "psh":                    round(psh, 3),
            "ppc":                    ppc,
            "pnc":                    pnc,
            "sap_sasa":               sap_sasa,
            "sap_mode":               "sasa_7mer",
            "cdr_sasa":               cdr_sasa,
            "cdr3_compactness_ca_dist": cdr3_ca_dist,
            "_struct_cmc_error":      None,
        }

    except Exception as exc:  # noqa: BLE001
        return {"_struct_cmc_error": f"{type(exc).__name__}: {exc}"}
