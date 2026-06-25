"""
core/immunogenicity/ada_risk_scorer.py
──────────────────────────────────────
Clinical ADA Risk Scorer — V2.1

GOVERNING STANDARD: docs/ADA_RISK_SCORING_STANDARD_V2.1.md  (LOCKED)
CONFIG FILE:        config/immunogenicity_risk_v2.json        (LOCKED)

All parameter changes MUST follow the Evolution Protocol in
docs/ABENGINECORE_GOVERNANCE.md. Do NOT modify _DEFAULTS or _FH_WEIGHTS
directly — update the JSON config and file a PROPOSAL entry first.

Converts the outputs of MHCII_Analyzer, SurfaceImmunogenicity, and germline/
structural features into a calibrated composite clinical ADA risk score (0-1).

DUAL-TRACK ARCHITECTURE (V2.1)
───────────────────────────────
  FH track  (origin="natural")   — fully human antibodies
  HU track  (origin="engineered") — humanised/chimeric antibodies

  HU Composite (standard V2 formula, calibrated on CLEAN-138 HU subset n=84):
    z = 0.40·G + 0.30·F + 0.05·I + 0.15·E + 0.10·P
        + 0.10·(G×F) + 0.05·(G×I)
        + VL_modulator(origin) + CMC_veto + profile_adj
    score = sigmoid(3.0 · (z − 0.25))

  FH Composite (V2.1, calibrated on FH subgroup n=54):
    I_fh   = min(interface_n_pairs / 100, 1)   # wider scale prevents saturation
    VL_dev = max(0, 1 − vl_identity)           # SHM proxy — positive risk signal
    z = 0.35·I_fh + 0.30·P + 0.20·VL_dev + 0.10·E + 0.05·F + 0.00·G
        + CMC_veto + profile_adj
    score = sigmoid(3.0 · (z − 0.32))          # midpoint_fh=0.32 prevents HIGH inflation

Risk tiers (both tracks):
    HIGH   : score >= 0.67
    MEDIUM : 0.64 <= score < 0.67
    LOW    : score < 0.64

Calibration (CLEAN-138, high-sensitivity assay subset):
    Spearman ρ: ALL=+0.22  FH=+0.39  HU=+0.26

Standard version: ADA_RISK_SCORING_STANDARD_V2.1 (2026-04-09)
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ─── Paths ────────────────────────────────────────────────────────────────────

_SUITE = Path(__file__).resolve().parents[2]
_ADA_CSV    = _SUITE / "data" / "reference" / "ada_calibration" / "known_ada_rates.csv"
_CAL_CACHE  = _SUITE / "data" / "reference" / "ada_calibration" / "calibrated_params.json"
_V2_CONFIG  = _SUITE / "config" / "immunogenicity_risk_v2.json"

# ─── Default model parameters (V2, calibrated on CLEAN-124 Tier A+B) ────────

_DEFAULTS = {
    # Component weights (HU / pooled baseline)
    "w_G": 0.40,    # germline distance (1 − VH_identity)
    "w_F": 0.30,    # inverse exposure (1 − frac_exposed_vh)
    "w_I": 0.05,    # VH-VL interface contact density
    "w_E": 0.15,    # MHC-II high-risk epitope count
    "w_C": 0.00,    # cluster density (zeroed — no signal in CLEAN-124)
    "w_P": 0.10,    # surface hydrophilic patch count
    # Normalisation scales
    "interface_scale":  60,
    "epitope_scale":    40,
    "patch_scale":      14,
    # Synergy
    "syn_GF": 0.10,  # germline distance × inverse exposure
    "syn_GI": 0.05,  # germline distance × interface density
    # VL modulator (subgroup-specific direction)
    "vl_natural_w":     -0.05,  # natural: more human VL → lower risk
    "vl_engineered_w":  +0.15,  # engineered: reversed signal (CDR/FR mismatch)
    "vl_ref_natural":    0.95,
    "vl_ref_engineered": 0.90,
    # CMC veto gates
    "instab_gate":  42,    "instab_penalty": 0.04,
    "hydro_gate":   0.70,  "hydro_penalty":  0.07,
    # Sigmoid shape
    "slope":    3.0,
    "midpoint": 0.25,
    # Risk tier thresholds (calibrated)
    "threshold_high":   0.67,
    "threshold_medium": 0.64,
    # V1 backward-compat keys (kept for legacy callers)
    "w_B": 0.0, "w_S": 0.0, "w_N": 0.0,
    "net_burden_scale": 0.5, "synergy": 0.0,
}

# ─── FH-specific weight matrix (Fully Human, origin="natural") ───────────────
# Calibrated on 138-antibody FH subgroup (n=54).
# Key findings (Spearman vs clinical ADA, high-sens assay subset):
#   Interface contacts (I):      rho=+0.369  → primary driver
#   VL germline deviation (VL):  rho=+0.264  (treated as 1-VL_identity)
#   Surface patches (P):         rho=+0.311
#   MHC-II epitopes (E):         rho=+0.134  (weaker in FH — SHM-derived)
#   VH germline distance (G):    rho=~0.05   (near-zero; FH VH ≈ human)
#
# VL note: in FH the scorer uses (1 - vl_identity) directly as a POSITIVE
# risk component (not the old tiny modulator), so low VL identity correctly
# raises the composite score.
# FH-specific calibration adjustments only — weights remain in the main _DEFAULTS.
# Key insight: FH antibodies average interface_n_pairs ≈ 71 (> default scale 60),
# causing I to saturate at 1.0 for most FH antibodies and lose discriminative power.
# Fix: use a wider interface scale for FH so the signal is preserved.
# VL modulator also re-anchored to the actual FH VL identity mean (~0.85) with
# a larger weight (0.20 vs old 0.05) so low VL identity meaningfully raises risk.
_FH_WEIGHTS = {
    "interface_scale_fh": 100,  # FH avg n_pairs ≈ 71; scale 60 saturates → use 100
    "w_I_fh":   0.35,   # interface density — strongest FH signal; boosted from 20% to 35%
    "w_F_fh":   0.05,   # F (1-frac_exposed_vh) has no FH signal; reduced from 10% to 5%
    "w_P_fh":   0.30,   # surface patches — strong FH signal; boosted from 25% to 30%
    "w_E_fh":   0.10,   # MHC-II epitopes; kept at 10%
    "w_G_fh":   0.00,   # VH germline distance; zeroed for FH (near-zero signal, rho~0.05)
    # VL modulator: (1 - vl_id) * weight — properly inverted, anchored at FH mean
    "vl_fh_w":  0.20,   # properly captures the -0.264 negative correlation of VL identity
    # midpoint kept at 0.25 to preserve absolute score comparability with HU
    "midpoint_fh": 0.32,  # Adjusted from 0.25 to 0.32 to re-center FH scores and avoid HIGH-risk inflation
}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _load_params() -> Dict:
    """Load V2 config if available, then calibrated thresholds, then defaults."""
    params = dict(_DEFAULTS)
    if _V2_CONFIG.exists():
        try:
            v2 = json.loads(_V2_CONFIG.read_text())
            if "components" in v2:
                for comp_key, comp_val in v2["components"].items():
                    if "weight" in comp_val:
                        short = comp_key.split("_")[0]
                        params[f"w_{short}"] = comp_val["weight"]
            if "sigmoid" in v2:
                params["slope"] = v2["sigmoid"].get("slope", params["slope"])
                params["midpoint"] = v2["sigmoid"].get("midpoint", params["midpoint"])
            if "thresholds" in v2:
                params["threshold_high"] = v2["thresholds"].get("high", params["threshold_high"])
                params["threshold_medium"] = v2["thresholds"].get("medium", params["threshold_medium"])
            if "synergy_terms" in v2:
                params["syn_GF"] = v2["synergy_terms"].get("GxF", 0)
                params["syn_GI"] = v2["synergy_terms"].get("GxI", 0)
            if "vl_modulator" in v2:
                params["vl_natural_w"] = v2["vl_modulator"].get("natural", -0.05)
                params["vl_engineered_w"] = v2["vl_modulator"].get("engineered", 0.15)
            if "cmc_veto_gates" in v2:
                for gate_name, gate_val in v2["cmc_veto_gates"].items():
                    if "instability" in gate_name:
                        params["instab_gate"] = gate_val.get("gate", 42)
                        params["instab_penalty"] = gate_val.get("penalty", 0.04)
                    elif "hydro" in gate_name:
                        params["hydro_gate"] = gate_val.get("gate", 0.70)
                        params["hydro_penalty"] = gate_val.get("penalty", 0.07)
            logger.info("ADAScorer V2: loaded config from %s", _V2_CONFIG)
        except Exception as exc:
            logger.warning("ADAScorer: V2 config load failed (%s), using defaults", exc)
    if _CAL_CACHE.exists():
        try:
            cal = json.loads(_CAL_CACHE.read_text())
            params.update({k: v for k, v in cal.items()
                          if k.startswith("threshold")})
            logger.info("ADAScorer: loaded calibrated thresholds from %s", _CAL_CACHE)
        except Exception:
            pass
    return params


def _infer_disease_class(targets: Optional[str]) -> str:
    t = str(targets or "").upper()
    if any(k in t for k in (
        "PDCD1", "CD274", "CTLA4", "EGFR", "ERBB2", "MS4A1", "CD19",
        "CD20", "CD22", "CD33", "CD38", "CD52", "BCMA", "DLL3", "NRG1",
    )):
        return "oncology"
    if any(k in t for k in (
        "TNF", "IL", "IFN", "TSLP", "C5", "IGE", "CGRP", "SOST", "FGF23",
        "RANKL", "PCSK9",
    )):
        return "immunology"
    if any(k in t for k in ("RSV", "SARS", "COVID", "EBOLA", "CDIFF", "C. DIFF")):
        return "infectious"
    return "other"


def _infer_route(
    disease_class: str,
    format_type: Optional[str],
    modality: Optional[str],
    route: Optional[str],
) -> str:
    if route:
        return str(route).lower()
    fmt = str(format_type or "").lower()
    mod = str(modality or "").lower()
    if "intravitreal" in fmt or "ophthalm" in mod or "vegf" in mod:
        return "ivt"
    if "fab" in fmt or "fragment" in fmt or "vhh" in fmt or "scfv" in fmt:
        return "iv"
    if disease_class == "oncology":
        return "iv"
    if disease_class in {"immunology", "metabolic"}:
        return "sc"
    if disease_class == "infectious":
        return "iv"
    return "unknown"


def _infer_half_life_class(
    fc_isotype: Optional[str],
    format_type: Optional[str],
    modality: Optional[str],
    half_life_class: Optional[str],
) -> str:
    if half_life_class:
        return str(half_life_class).lower()
    fmt = str(format_type or "").lower()
    mod = str(modality or "").lower()
    iso = str(fc_isotype or "").upper()
    if any(k in fmt for k in ("fab", "fragment", "vhh", "scfv")):
        return "short"
    if any(k in mod for k in ("adc", "radiolabeled")):
        return "short"
    if iso in {"G1", "G2", "G4"}:
        return "standard"
    return "unknown"


def _profile_adjustments(
    disease_class: str,
    route: str,
    origin: str,
    half_life_class: str,
    assay_method: Optional[str] = None,
    trial_duration_weeks: Optional[float] = None,
) -> Dict[str, float]:
    adj = {
        "midpoint_shift": 0.0,
        "threshold_shift": 0.0,
        "wG_shift": 0.0,
        "wF_shift": 0.0,
        "wE_shift": 0.0,
        "wP_shift": 0.0,
    }

    # Disease adjustments
    if disease_class == "oncology":
        adj["midpoint_shift"] += 0.03
    elif disease_class == "immunology":
        adj["midpoint_shift"] -= 0.02
        adj["wE_shift"] += 0.03
    elif disease_class == "infectious":
        adj["midpoint_shift"] += 0.01

    # Route adjustments
    if route == "sc":
        adj["midpoint_shift"] -= 0.02
    elif route == "ivt":
        adj["midpoint_shift"] += 0.03

    # Origin
    if str(origin).lower() == "natural":
        adj["wG_shift"] -= 0.01
    elif str(origin).lower() == "engineered":
        adj["wG_shift"] += 0.01

    # Half-life
    if half_life_class == "extended":
        adj["midpoint_shift"] -= 0.02

    # Assay sensitivity (ECL and Bridging are more sensitive, lower the midpoint to increase score)
    method = str(assay_method or "").lower()
    if "ecl" in method or "bridging" in method:
        adj["midpoint_shift"] -= 0.02
    elif "elisa" in method and "bridge" not in method:
        adj["midpoint_shift"] += 0.01

    # Trial duration (Longer trials increase cumulative risk)
    if trial_duration_weeks is not None:
        if trial_duration_weeks > 52:    # > 1 year
            adj["midpoint_shift"] -= 0.03
        elif trial_duration_weeks > 24:  # > 6 months
            adj["midpoint_shift"] -= 0.01
        elif trial_duration_weeks < 4:   # Phase 1 single dose
            adj["midpoint_shift"] += 0.05

    return adj


# ─── Main class ───────────────────────────────────────────────────────────────


class ADAScorer:
    """
    Composite clinical ADA risk scorer.

    Parameters
    ----------
    params : dict, optional
        Override any default parameters. Keys match _DEFAULTS.
        E.g. ADAScorer(params={"w_B": 0.5, "threshold_high": 0.6})
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = _load_params()
        if params:
            self.params.update(params)

    # ── scoring ───────────────────────────────────────────────────────────────

    def score(
        self,
        mhc_result: Dict,
        surf_result: Dict,
        *,
        germline_identity_vh: Optional[float] = None,
        germline_identity_vl: Optional[float] = None,
        interface_n_pairs: Optional[float] = None,
        instability_index: Optional[float] = None,
        hydro_patch_max9: Optional[float] = None,
        origin: str = "engineered",
        targets: Optional[str] = None,
        fc_isotype: Optional[str] = None,
        format_type: Optional[str] = None,
        modality: Optional[str] = None,
        route: Optional[str] = None,
        half_life_class: Optional[str] = None,
        assay_method: Optional[str] = None,
        trial_duration_weeks: Optional[float] = None,
    ) -> Dict:
        """
        Compute clinical ADA risk score (V2 architecture).

        Parameters
        ----------
        mhc_result  : dict from MHCII_Analyzer.run()
        surf_result : dict from SurfaceImmunogenicity.run()
        germline_identity_vh : VH germline identity (0-1). If None, G=0.
        germline_identity_vl : VL germline identity (0-1). If None, VL modulator=0.
        interface_n_pairs    : VH-VL interface contact pairs. If None, I=0.
        instability_index    : Sequence instability index. If None, no veto.
        hydro_patch_max9     : Max hydrophobic patch score. If None, no veto.
        origin               : "natural" or "engineered" (controls VL direction).
        targets/fc_isotype/format_type/modality : metadata for auto-profile routing.
        route                : explicit route override ("iv", "sc", "ivt", ...).
        half_life_class      : explicit half-life class ("short", "standard", "extended").
        assay_method         : e.g., "ELISA", "ECL", "Bridging". Influences sensitivity.
        trial_duration_weeks : Duration of clinical trial. Influences cumulative ADA.
        """
        p = self.params
        disease_class = _infer_disease_class(targets)
        route_class = _infer_route(disease_class, format_type, modality, route)
        hl_class = _infer_half_life_class(fc_isotype, format_type, modality, half_life_class)
        adj = _profile_adjustments(
            disease_class, route_class, origin, hl_class,
            assay_method=assay_method,
            trial_duration_weeks=trial_duration_weeks
        )

        w_G = max(0.0, p["w_G"] + adj["wG_shift"])
        w_F = max(0.0, p["w_F"] + adj["wF_shift"])
        w_E = max(0.0, p["w_E"] + adj["wE_shift"])
        w_P = max(0.0, p.get("w_P", 0.0) + adj["wP_shift"])
        midpoint = p["midpoint"] + adj["midpoint_shift"]
        threshold_high = min(0.95, max(0.05, p["threshold_high"] + adj["threshold_shift"]))
        threshold_medium = min(
            threshold_high - 0.01,
            max(0.01, p["threshold_medium"] + adj["threshold_shift"]),
        )

        # ── Shared normalised components ──────────────────────────────────
        vh_id = float(germline_identity_vh) if germline_identity_vh is not None else 1.0
        G = max(0.0, min(1.0 - vh_id, 1.0))          # VH germline distance

        frac_vh = surf_result.get("frac_exposed_vh")
        if frac_vh is not None:
            F = max(0.0, min(1.0 - float(frac_vh), 1.0))
        else:
            n_patches = int(surf_result.get("n_hydrophilic_patches") or 0)
            F = max(0.0, 1.0 - min(n_patches / float(p.get("patch_scale", 14)), 1.0))

        n_pairs = float(interface_n_pairs) if interface_n_pairs is not None else 0.0
        I = min(n_pairs / max(p.get("interface_scale", 60), 1), 1.0)

        summary = mhc_result.get("summary", {})
        n_high = int(
            summary.get("n_high", 0)
            or mhc_result.get("n_risk_positions_high", 0)
            or mhc_result.get("n_strong_binders", 0)
        )
        E = min(n_high / max(p.get("epitope_scale", 40), 1), 1.0)

        n_patches_total = int(surf_result.get("n_hydrophilic_patches") or 0)
        P = min(n_patches_total / max(p.get("patch_scale", 14), 1), 1.0)

        vl_id = float(germline_identity_vl) if germline_identity_vl is not None else None

        # ── CMC veto penalties (shared) ───────────────────────────────────
        cmc_pen = 0.0
        if instability_index is not None and instability_index > p.get("instab_gate", 42):
            cmc_pen += p.get("instab_penalty", 0.04)
        if hydro_patch_max9 is not None and hydro_patch_max9 > p.get("hydro_gate", 0.70):
            cmc_pen += p.get("hydro_penalty", 0.07)

        # ══════════════════════════════════════════════════════════════════
        #  DUAL-TRACK COMPOSITE
        #  FH (origin="natural") uses a structurally-calibrated weight
        #  matrix derived from 54-antibody subgroup analysis.
        #  HU (origin="engineered") uses the legacy V2 formula.
        # ══════════════════════════════════════════════════════════════════
        orig = str(origin).lower()

        if orig == "natural":
            # ── FH track ─────────────────────────────────────────────────
            # FH antibodies: ADA driven by structural flaws, not foreign sequence.
            # Key adjustments vs pooled formula:
            #   1. interface_scale = 100 (FH avg n_pairs ≈ 71 > default 60 → saturates)
            #   2. Redistribute weight from F→I and F→P (F has no FH signal, rho≈-0.12)
            #   3. VL: use (1-vl_id)*0.20 instead of tiny modulator (properly captures
            #      the -0.264 negative correlation of VL identity with ADA in FH)
            fw = _FH_WEIGHTS

            # Recompute I with FH-appropriate scale
            I_fh = min(n_pairs / max(fw["interface_scale_fh"], 1), 1.0)

            # VL deviation: (1-vl_id) is a POSITIVE risk signal for FH
            # (low VL identity → more SHM → higher ADA)
            VL_dev = max(0.0, min(1.0 - vl_id, 1.0)) if vl_id is not None else 0.0

            z = (fw["w_G_fh"] * G
                 + fw["w_F_fh"] * F
                 + fw["w_I_fh"] * I_fh
                 + fw["w_E_fh"] * E
                 + fw["w_P_fh"] * P
                 + fw["vl_fh_w"] * VL_dev
                 + cmc_pen)

            effective_midpoint = fw.get("midpoint_fh", midpoint) + adj["midpoint_shift"]
            vl_mod = VL_dev
            syn_gf = syn_gi = 0.0
            track = "FH"

        else:
            # ── HU track (original V2 formula) ───────────────────────────
            z = (w_G * G
                 + w_F * F
                 + p.get("w_I", 0) * I
                 + w_E * E
                 + p.get("w_C", 0) * min(int(mhc_result.get("n_clusters") or 0) / 5.0, 1.0)
                 + w_P * P)

            syn_gf = p.get("syn_GF", 0) * G * F
            syn_gi = p.get("syn_GI", 0) * G * I
            z += syn_gf + syn_gi

            # VL modulator — HU: CDR/FR mismatch raises risk when VL < reference
            vl_mod = 0.0
            if vl_id is not None:
                vl_mod = p.get("vl_engineered_w", 0.15) * (vl_id - p.get("vl_ref_engineered", 0.90))
                z += vl_mod

            z += cmc_pen
            effective_midpoint = midpoint + adj["midpoint_shift"]
            track = "HU"

        # ── Sigmoid → [0, 1] ─────────────────────────────────────────────
        clinical_score = _sigmoid(p["slope"] * (z - effective_midpoint))
        risk = self._tier(
            clinical_score,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
        )

        return {
            "clinical_ada_score": round(clinical_score, 4),
            "clinical_ada_risk": risk,
            "track": track,
            "profile": {
                "disease_class": disease_class,
                "route": route_class,
                "half_life_class": hl_class,
                "midpoint_shift": round(adj["midpoint_shift"], 4),
                "threshold_shift": round(adj["threshold_shift"], 4),
            },
            "components": {
                "G_germline_dist":  round(G, 4),
                "F_inverse_exp":    round(F, 4),
                "I_interface":      round(I, 4),
                "E_epitopes":       round(E, 4),
                "P_patches":        round(P, 4),
                "VL_deviation":     round(vl_mod if track == "FH" else (1.0 - vl_id if vl_id else 0.0), 4),
                "w_G_effective":    round(w_G if track == "HU" else 0.0, 4),
                "w_F_effective":    round(w_F if track == "HU" else 0.0, 4),
                "w_I_effective":    round(_FH_WEIGHTS["w_I_fh"] if track == "FH" else p.get("w_I", 0), 4),
                "w_VL_effective":   round(_FH_WEIGHTS["vl_fh_w"] if track == "FH" else p.get("vl_engineered_w", 0.15), 4),
                "w_E_effective":    round(w_E, 4),
                "w_P_effective":    round(w_P, 4),
                "syn_GF":           round(syn_gf, 4),
                "syn_GI":           round(syn_gi, 4),
                "cmc_penalty":      round(cmc_pen, 4),
                "z_composite":      round(z, 4),
            },
        }

    def _tier(
        self,
        score: float,
        *,
        threshold_high: Optional[float] = None,
        threshold_medium: Optional[float] = None,
    ) -> str:
        p = self.params
        th = p["threshold_high"] if threshold_high is None else threshold_high
        tm = p["threshold_medium"] if threshold_medium is None else threshold_medium
        if score >= th:
            return "HIGH"
        if score >= tm:
            return "MEDIUM"
        return "LOW"

    # ── calibration ───────────────────────────────────────────────────────────

    def calibrate(
        self,
        scores_df: "pd.DataFrame",
        save: bool = True,
    ) -> Dict:
        """
        Calibrate HIGH/MEDIUM/LOW thresholds using the known ADA dataset.

        Parameters
        ----------
        scores_df : DataFrame with columns:
                      antibody, clinical_ada_score
                    (i.e., output of run_mhcii_immunogenicity_70 joined with known_ada_rates)
        save : if True, persists calibrated params to _CAL_CACHE

        Returns
        -------
        dict with optimised thresholds and evaluation metrics
        """
        ada_ref = self._load_ada_ref()
        if ada_ref.empty:
            logger.warning("ADA reference CSV not found or empty; calibration skipped")
            return {}

        merged = scores_df.merge(ada_ref, on="antibody", how="inner")
        if len(merged) < 5:
            logger.warning("Only %d matching antibodies for calibration; need ≥5", len(merged))
            return {}

        scores = merged["clinical_ada_score"].values
        ada    = merged["ada_rate_pct"].values

        # Binarize ADA: >10% = immunogenic, ≤10% = non-immunogenic
        # (10% is a commonly used clinical significance threshold)
        THRESHOLD_PCT = 10.0
        y = (ada > THRESHOLD_PCT).astype(int)

        best_bal_acc  = -1.0
        best_thigh    = 0.55
        best_tmed     = 0.25

        # Grid search over threshold combinations
        for t_high in np.arange(0.3, 0.9, 0.05):
            for t_med in np.arange(0.1, t_high - 0.05, 0.05):
                # Predicted: HIGH or MEDIUM = positive
                y_pred = (scores >= t_med).astype(int)
                tp = int(((y == 1) & (y_pred == 1)).sum())
                tn = int(((y == 0) & (y_pred == 0)).sum())
                fp = int(((y == 0) & (y_pred == 1)).sum())
                fn = int(((y == 1) & (y_pred == 0)).sum())
                sens = tp / (tp + fn + 1e-9)
                spec = tn / (tn + fp + 1e-9)
                bal  = (sens + spec) / 2
                if bal > best_bal_acc:
                    best_bal_acc = bal
                    best_thigh   = round(t_high, 3)
                    best_tmed    = round(t_med, 3)

        self.params["threshold_high"]   = best_thigh
        self.params["threshold_medium"] = best_tmed

        # Correlation metrics
        try:
            from scipy.stats import spearmanr, pearsonr
            sp_r, sp_p = spearmanr(scores[~np.isnan(scores)], ada[~np.isnan(scores)])
            pe_r, pe_p = pearsonr(scores[~np.isnan(scores)], np.log1p(ada[~np.isnan(scores)]))
        except ImportError:
            sp_r = sp_p = pe_r = pe_p = float("nan")

        result = {
            "n_antibodies": int(len(merged)),
            "optimal_threshold_high":   best_thigh,
            "optimal_threshold_medium": best_tmed,
            "balanced_accuracy": round(best_bal_acc, 4),
            "spearman_r": round(sp_r, 4) if not math.isnan(sp_r) else None,
            "pearson_r_log_ada": round(pe_r, 4) if not math.isnan(pe_r) else None,
        }

        logger.info("ADAScorer calibration: %s", result)

        if save:
            _CAL_CACHE.parent.mkdir(parents=True, exist_ok=True)
            save_params = {k: v for k, v in self.params.items()
                           if k in ("threshold_high", "threshold_medium")}
            _CAL_CACHE.write_text(json.dumps(save_params, indent=2))
            logger.info("Calibrated thresholds saved to %s", _CAL_CACHE)

        return result

    @staticmethod
    def _load_ada_ref() -> "pd.DataFrame":
        if not _ADA_CSV.exists():
            return pd.DataFrame()
        try:
            df = pd.read_csv(_ADA_CSV, comment="#")
            return df[["antibody", "ada_rate_pct"]].dropna()
        except Exception as exc:
            logger.warning("Could not read ADA reference CSV: %s", exc)
            return pd.DataFrame()

    def load_ada_reference(self) -> "pd.DataFrame":
        """Return the known-ADA reference table (for inspection)."""
        return self._load_ada_ref()

    def params_summary(self) -> str:
        """Human-readable parameter summary."""
        p = self.params
        v2 = _V2_CONFIG.exists()
        lines = [
            "ADAScorer V2 parameters" + (" [V2 CONFIG]" if v2 else " [DEFAULT]"),
            f"  Weights   : G={p['w_G']} F={p['w_F']} I={p.get('w_I',0)} E={p['w_E']} C={p.get('w_C',0)} P={p.get('w_P',0)}",
            f"  Synergy   : GxF={p.get('syn_GF',0)} GxI={p.get('syn_GI',0)}",
            f"  VL mod    : natural={p.get('vl_natural_w',0)} eng={p.get('vl_engineered_w',0)}",
            f"  CMC veto  : instab>{p.get('instab_gate',42)}→+{p.get('instab_penalty',0)}, hydro>{p.get('hydro_gate',0.7)}→+{p.get('hydro_penalty',0)}",
            f"  sigmoid   : slope={p['slope']}, midpoint={p['midpoint']}",
            f"  Thresholds: HIGH≥{p['threshold_high']}, MEDIUM≥{p['threshold_medium']}",
        ]
        return "\n".join(lines)


# ─── Public tier banding (V2.1 standard §6) ────────────────────────────────
# Base thresholds: HIGH ≥ 0.67, MEDIUM ∈ [0.64, 0.67), LOW < 0.64
# Per-molecule `ADAScorer.score()` may apply small threshold_shift from profile;
# for final tier always use the returned `clinical_ada_risk` field.


def get_clinical_ada_tier_thresholds() -> Dict[str, float]:
    """
    Active cutoffs for `clinical_ada_score` on [0, 1] (after loading V2 config / cal cache).

    Returns
    -------
    threshold_medium : lower bound of MEDIUM (scores below this are LOW)
    threshold_high   : lower bound of HIGH  (scores at or above are HIGH)
    """
    p = _load_params()
    return {
        "threshold_medium": float(p["threshold_medium"]),
        "threshold_high": float(p["threshold_high"]),
    }


def clinical_ada_score_to_tier(score: float) -> str:
    """
    Map a composite `clinical_ada_score` in [0, 1] to ``LOW`` | ``MEDIUM`` | ``HIGH``
    using the same base thresholds as `ADAScorer._tier` (no per-profile shift).

    For tiers computed with disease/route/assay adjustments, use the ``clinical_ada_risk``
    field from `ADAScorer.score()` instead.
    """
    return ADAScorer()._tier(float(score))


def clinical_ada_tier_definitions() -> Dict[str, Dict[str, Any]]:
    """
    Structured LOW / MEDIUM / HIGH numeric bands for UI, tables, and QA summaries.

    Bands follow ADA_RISK_SCORING_STANDARD_V2.1 §6 (defaults HIGH≥0.67, MEDIUM≥0.64).
    """
    t = get_clinical_ada_tier_thresholds()
    tm, th = t["threshold_medium"], t["threshold_high"]
    return {
        "LOW": {
            "tier": "LOW",
            "clinical_ada_score": f"[0, {tm})",
            "rule": f"clinical_ada_score < {tm}",
        },
        "MEDIUM": {
            "tier": "MEDIUM",
            "clinical_ada_score": f"[{tm}, {th})",
            "rule": f"{tm} <= clinical_ada_score < {th}",
        },
        "HIGH": {
            "tier": "HIGH",
            "clinical_ada_score": f"[{th}, 1]",
            "rule": f"clinical_ada_score >= {th}",
        },
    }
