#!/usr/bin/env python3
"""
Optional post-humanization FR surface reshaping toward selected human germlines.

Uses the same Kabat surface definitions as `run_dog_surface_reshaping_v1.veneer_sequence`:
solvent-exposed FR positions only (CDR preserved). Intended when checklist QC is
WARN/FAIL and the user requests `surface_reshape_on_qc_fail` on the API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

GERM_ROOT = SUITE / "data" / "germlines"


def load_human_germline_sequences(vh_germline_id: str, vl_germline_id: str) -> Tuple[str, str]:
    """Load amino acid sequences for OGRDB-style human germline IDs."""
    vh_id = (vh_germline_id or "").strip()
    vl_id = (vl_germline_id or "").strip()
    if not vh_id or not vl_id:
        return "", ""

    ighv = json.loads((GERM_ROOT / "ogrdb_human_IGHV_v2.json").read_text(encoding="utf-8"))
    igkv = json.loads((GERM_ROOT / "ogrdb_human_IGKV_v2.json").read_text(encoding="utf-8"))
    iglv = json.loads((GERM_ROOT / "ogrdb_human_IGLV_v2.json").read_text(encoding="utf-8"))

    vh_seq = ighv.get(vh_id) or ""
    if vl_id.upper().startswith("IGLV"):
        vl_seq = iglv.get(vl_id) or ""
    else:
        vl_seq = igkv.get(vl_id) or ""
    return str(vh_seq), str(vl_seq)


def apply_surface_reshape_fallback(
    humanized_vh: str,
    humanized_vl: str,
    germline_vh_seq: str,
    germline_vl_seq: str,
) -> Dict[str, Any]:
    """
    Apply Kabat-surface veneering: at each exposed FR position, use germline AA if different.

    Returns dict with reshaped sequences, per-chain mutation logs, and notes.
    """
    from scripts.run_dog_surface_reshaping_v1 import veneer_sequence  # noqa: PLC0415

    out: Dict[str, Any] = {
        "applied": False,
        "humanized_vh": humanized_vh,
        "humanized_vl": humanized_vl,
        "vh_mutations": [],
        "vl_mutations": [],
        "vh_notes": [],
        "vl_notes": [],
        "errors": [],
    }
    if not humanized_vh or not humanized_vl:
        out["errors"].append("Missing humanized VH or VL sequence.")
        return out
    if not germline_vh_seq or not germline_vl_seq:
        out["errors"].append("Missing germline VH or VL sequence from OGRDB lookup.")
        return out

    try:
        vh_new, mut_vh, notes_vh = veneer_sequence(humanized_vh, germline_vh_seq, "VH")
        vl_new, mut_vl, notes_vl = veneer_sequence(humanized_vl, germline_vl_seq, "VL")
    except Exception as e:
        out["errors"].append(str(e))
        return out

    out["vh_notes"] = notes_vh or []
    out["vl_notes"] = notes_vl or []
    out["vh_mutations"] = mut_vh or []
    out["vl_mutations"] = mut_vl or []
    out["humanized_vh"] = vh_new or humanized_vh
    out["humanized_vl"] = vl_new or humanized_vl
    out["applied"] = bool((mut_vh or mut_vl))
    return out


def verify_cdr_after_reshape(
    donor_vh: str,
    donor_vl: str,
    out_vh: str,
    out_vl: str,
) -> Dict[str, Any]:
    from core.humanization.kabat_utils import (  # noqa: PLC0415
        get_kabat_numbering,
        verify_cdr_preservation,
    )

    dvh = get_kabat_numbering(donor_vh) or {}
    dvl = get_kabat_numbering(donor_vl) or {}
    hvh = get_kabat_numbering(out_vh) or {}
    hvl = get_kabat_numbering(out_vl) or {}
    return {
        "vh": verify_cdr_preservation(hvh, dvh, "VH"),
        "vl": verify_cdr_preservation(hvl, dvl, "VL"),
    }
