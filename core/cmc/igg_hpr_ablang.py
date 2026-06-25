"""
IgG CMC snapshot — sequence humanness metrics aligned with VH/VL Phase 5 QC.

Exposes the same definitions as humanization reports:
  - HPR Index: variable-region 9-mer coverage vs local human-oas reference (see hpr_index).
  - AbLang2: paired pseudo-log-likelihood on (VH, VL) using ablang2-paired.

These are profile metrics for the submitted Fv (no donor comparison on this endpoint).

Single-domain VHH uses the same HPR machinery with an empty VL chain; AbLang2 paired
is not applicable for VHH (AbLang2 is VH/VL-paired).
"""

from __future__ import annotations

from typing import Any, Dict


def compute_vhh_cmc_hpr_ablang(vhh: str) -> Dict[str, Any]:
    """HPR Index for one VHH; AbLang2 paired N/A for single-domain nanobodies."""
    vhh = (vhh or "").strip().upper()
    out: Dict[str, Any] = {
        "hpr_index": None,
        "hpr_error": None,
        "ablang_score": None,
        "ablang_error": "not_applicable_single_domain_vhh",
    }
    try:
        from core.humanization.hpr_index import compute_hpr_index

        out["hpr_index"] = compute_hpr_index(vhh, "")
    except Exception as exc:  # noqa: BLE001
        out["hpr_error"] = f"{type(exc).__name__}: {exc}"
    return out


_ABLANG2_MODEL_CACHE = {}

def compute_igg_cmc_hpr_ablang(vh: str, vl: str) -> Dict[str, Any]:
    """Return HPR Index block + AbLang2 score for one VH/VL pair."""
    vh = (vh or "").strip().upper()
    vl = (vl or "").strip().upper()
    out: Dict[str, Any] = {
        "hpr_index": None,
        "hpr_error": None,
        "ablang_score": None,
        "ablang_error": None,
    }

    try:
        from core.humanization.hpr_index import compute_hpr_index

        out["hpr_index"] = compute_hpr_index(vh, vl)
    except Exception as exc:  # noqa: BLE001
        out["hpr_error"] = f"{type(exc).__name__}: {exc}"

    if not vh or not vl:
        out["ablang_error"] = "missing_vh_or_vl"
        return out

    try:
        import numpy as np  # type: ignore
        import ablang2  # type: ignore

        if "ablang2-paired" not in _ABLANG2_MODEL_CACHE:
            _ABLANG2_MODEL_CACHE["ablang2-paired"] = ablang2.pretrained("ablang2-paired")
        
        model = _ABLANG2_MODEL_CACHE["ablang2-paired"]
        pll = model([(vh, vl)], mode="pseudo_log_likelihood")
        out["ablang_score"] = round(float(np.squeeze(pll)), 3)
    except Exception as exc:  # noqa: BLE001
        out["ablang_error"] = f"{type(exc).__name__}: {exc}"

    return out
