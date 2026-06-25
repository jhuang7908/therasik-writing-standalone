"""
IMGT-based VH/VL region segmentation for IgG CMC reports (same numbering path as humanization/VHH).

Uses ANARCII IMGT rows + ``split_regions`` from ``core.vhh_humanization`` for FR/CDR strings.
"""
from __future__ import annotations

from typing import Any, Dict


def segment_vh_vl_imgt(vh_seq: str, vl_seq: str) -> Dict[str, Any]:
    """
    Return FR/CDR strings per chain. On failure, ``error`` is set and region dicts may be empty.

    Keys:
      scheme: "IMGT"
      VH / VL: mapping FR1, CDR1, FR2, CDR2, FR3, CDR3, FR4 -> sequence string
      error: optional error message
    """
    out: Dict[str, Any] = {"scheme": "IMGT", "VH": {}, "VL": {}, "error": None}
    vh = (vh_seq or "").strip().upper()
    vl = (vl_seq or "").strip().upper()
    if not vh and not vl:
        out["error"] = "Empty VH and VL sequences."
        return out
    try:
        from core.numbering.imgt_anarcii import imgt_number_anarcii
        from core.vhh_humanization import split_regions

        if vh:
            out["VH"] = split_regions(imgt_number_anarcii(vh))
        if vl:
            out["VL"] = split_regions(imgt_number_anarcii(vl))
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"
    return out
