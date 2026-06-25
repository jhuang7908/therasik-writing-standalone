"""
api/routers/annotate.py — Server-side VH/VL FR/CDR segmentation (AbEngineCore stack).

IMGT: imgt_number_anarcii + split_regions (IMGT-aware CDR2/55 rule).
Kabat / Chothia: single ANARCII session, to_scheme(), kabat_from_anarcii + vhvl_scheme_regions.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from api.models import AnnotateVHVLRequest, AnnotateVHVLResponse

router = APIRouter(prefix="/annotate", tags=["Annotation"])

_ALLOWED = frozenset({"imgt", "kabat", "chothia"})


def _imgt_rows_to_api(rows: list) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        ins = (r.get("ins_code") or "").strip()
        out.append({"pos": int(r["pos"]), "ins": ins, "aa": str(r.get("aa", ""))})
    return out


def _anarcii_numbering_to_api(numbering: list) -> list[dict]:
    """Raw ANARCII numbering list -> {pos, ins, aa} for JSON."""
    out: list[dict] = []
    if not numbering:
        return out
    for item in numbering:
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        pos_info, aa = item[0], item[1]
        if aa in ("-", None) or pos_info is None:
            continue
        if not isinstance(pos_info, tuple) or len(pos_info) < 1:
            continue
        try:
            pos_i = int(pos_info[0])
        except (TypeError, ValueError):
            continue
        ins_raw = pos_info[1] if len(pos_info) > 1 else " "
        ins = (ins_raw or "").strip()
        out.append({"pos": pos_i, "ins": ins, "aa": str(aa)})
    return out


@router.post(
    "/vh_vl",
    response_model=AnnotateVHVLResponse,
    summary="VH+VL FR/CDR segmentation (IMGT, Kabat, or Chothia)",
)
def annotate_vh_vl(req: AnnotateVHVLRequest):
    """
    Number VH and VL with the server ANARCI-class stack, then return FR1–FR4 / CDR1–CDR3 strings.
    First call may take tens of seconds while the model loads into memory.
    """
    t0 = time.time()
    try:
        from core.numbering.imgt_anarcii import (
            IMGTNumberingError,
            imgt_number_anarcii,
            _get_anarcii_obj,
        )
        from core.humanization.kabat_utils import kabat_from_anarcii
        from core.numbering.vhvl_scheme_regions import (
            split_regions_chothia_vh,
            split_regions_chothia_vl,
            split_regions_kabat_vh,
            split_regions_kabat_vl,
        )
        from core.vhh_humanization import split_regions as split_regions_imgt
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"IMGT numbering stack not available on server: {e}",
        ) from e

    vh = (req.vh_sequence or "").strip().upper().replace(" ", "")
    vl = (req.vl_sequence or "").strip().upper().replace(" ", "")
    if len(vh) < 90 or len(vh) > 150:
        raise HTTPException(status_code=422, detail="VH length out of plausible range (90–150 aa)")
    if len(vl) < 85 or len(vl) > 135:
        raise HTTPException(status_code=422, detail="VL length out of plausible range (85–135 aa)")

    scheme = (req.scheme or "imgt").strip().lower()
    if scheme not in _ALLOWED:
        raise HTTPException(
            status_code=422,
            detail=f"scheme must be one of {sorted(_ALLOWED)}",
        )

    vh_num_api: list[dict] | None = None
    vl_num_api: list[dict] | None = None
    try:
        if scheme == "imgt":
            rows_h = imgt_number_anarcii(vh)
            rows_l = imgt_number_anarcii(vl)
            vh_regions = split_regions_imgt(rows_h)
            vl_regions = split_regions_imgt(rows_l)
            vh_num_api = _imgt_rows_to_api(rows_h)
            vl_num_api = _imgt_rows_to_api(rows_l)
        else:
            obj = _get_anarcii_obj()
            obj.number([("vh", vh), ("vl", vl)])
            converted = obj.to_scheme(scheme)
            ent_h = converted.get("vh") if isinstance(converted, dict) else None
            ent_l = converted.get("vl") if isinstance(converted, dict) else None
            if not isinstance(ent_h, dict) or not isinstance(ent_l, dict):
                raise HTTPException(status_code=500, detail="ANARCI conversion returned unexpected shape")
            num_h = ent_h.get("numbering") or []
            num_l = ent_l.get("numbering") or []
            if not num_h or not num_l:
                raise HTTPException(
                    status_code=422,
                    detail="Numbering failed for VH or VL (empty numbering — check sequences)",
                )
            vh_num_api = _anarcii_numbering_to_api(num_h)
            vl_num_api = _anarcii_numbering_to_api(num_l)
            kd_h = kabat_from_anarcii(num_h)
            kd_l = kabat_from_anarcii(num_l)
            if scheme == "kabat":
                vh_regions = split_regions_kabat_vh(kd_h)
                vl_regions = split_regions_kabat_vl(kd_l)
            else:
                vh_regions = split_regions_chothia_vh(kd_h)
                vl_regions = split_regions_chothia_vl(kd_l)
    except IMGTNumberingError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e

    germline_block = None
    if req.include_germline:
        try:
            from core.numbering.germline_quick_assign import assign_vh_vl_germlines

            germline_block = assign_vh_vl_germlines(vh, vl, req.species)
        except Exception as e:
            germline_block = {"error": f"{type(e).__name__}: {e}"}

    elapsed = round(time.time() - t0, 2)
    return AnnotateVHVLResponse(
        vh_regions=vh_regions,
        vl_regions=vl_regions,
        scheme=scheme,
        engine="anarci",
        elapsed_sec=elapsed,
        germline=germline_block,
        vh_numbering=vh_num_api,
        vl_numbering=vl_num_api,
    )


def _hallmarks_from_imgt_rows(rows: list):
    """Return four-site display residues: IMGT 37 context + FR2 hallmark 44/45/47."""
    from core.numbering.imgt_anarcii import build_pos_to_aa_map

    if not rows:
        return None
    pos_map = build_pos_to_aa_map(rows)
    out = {}
    for p in (37, 44, 45, 47):
        if p in pos_map:
            out[str(p)] = pos_map[p]
    return out or None


@router.post(
    "/vhh",
    response_model=dict,
    summary="VHH FR/CDR segmentation + germline matching (IMGT/Kabat/Chothia)",
)
def annotate_vhh(req: dict):
    """
    Number VHH with the same ANARCI-class stack as POST /annotate/vh_vl (VH chain only).

    Request body (JSON):
      - vhh_sequence: str (100–150 aa)
      - scheme: "imgt" | "kabat" | "chothia" (default: "imgt")
      - species: console keys — human, mouse, rat, rabbit, dog, alpaca, camel, llama (default: "alpaca")
      - include_hallmarks: bool (default: true) — four-site display residues 37/44/45/47
      - include_germline: bool (default: true) — closest IGHV vs IMGT library for species

    Response (JSON):
      - vhh_sequence, scheme, engine, elapsed_sec
      - regions: {FR1..FR4, CDR1..CDR3}
      - numbering: [{pos, ins, aa}, ...]
      - hallmarks: {"37": "...", "44": "...", "45": "...", "47": "..."} or null
      - germline: same shape as VH-only slice from assign_vh_vl_germlines (chain: vhh)
    """
    t0 = time.time()
    try:
        from core.numbering.imgt_anarcii import IMGTNumberingError, imgt_number_anarcii, _get_anarcii_obj
        from core.humanization.kabat_utils import kabat_from_anarcii
        from core.numbering.vhvl_scheme_regions import split_regions_chothia_vh, split_regions_kabat_vh
        from core.vhh_humanization import split_regions as split_regions_imgt
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"VHH segmentation stack not available: {e}",
        ) from e

    data = req.dict() if hasattr(req, "dict") else req

    seq = (data.get("vhh_sequence") or "").strip().upper().replace(" ", "")
    scheme = (data.get("scheme") or "imgt").strip().lower()
    species = (data.get("species") or "alpaca").strip().lower()
    include_hallmarks = data.get("include_hallmarks", True)
    include_germline = data.get("include_germline", True)
    if data.get("include_germline_match") is False:
        include_germline = False

    if len(seq) < 100 or len(seq) > 150:
        raise HTTPException(status_code=422, detail="VHH length out of plausible range (100–150 aa)")
    if scheme not in _ALLOWED:
        raise HTTPException(status_code=422, detail=f"scheme must be one of {sorted(_ALLOWED)}")

    try:
        try:
            rows_imgt = imgt_number_anarcii(seq)
        except IMGTNumberingError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

        hallmarks = _hallmarks_from_imgt_rows(rows_imgt) if include_hallmarks else None

        vh_num_api: list[dict] | None = None
        engine = "anarci"

        if scheme == "imgt":
            vhh_regions = split_regions_imgt(rows_imgt)
            vh_num_api = _imgt_rows_to_api(rows_imgt)
        else:
            obj = _get_anarcii_obj()
            obj.number([("vh", seq)])
            converted = obj.to_scheme(scheme)
            ent_h = converted.get("vh") if isinstance(converted, dict) else None
            if not isinstance(ent_h, dict):
                raise HTTPException(status_code=500, detail="ANARCI conversion returned unexpected shape")
            num_h = ent_h.get("numbering") or []
            if not num_h:
                raise HTTPException(status_code=422, detail="Numbering failed for VHH (empty numbering)")
            vh_num_api = _anarcii_numbering_to_api(num_h)
            kd_h = kabat_from_anarcii(num_h)
            if scheme == "kabat":
                vhh_regions = split_regions_kabat_vh(kd_h)
            else:
                vhh_regions = split_regions_chothia_vh(kd_h)

        germline_block = None
        if include_germline:
            try:
                from core.numbering.germline_quick_assign import assign_vhh_closest_ighv

                germline_block = assign_vhh_closest_ighv(seq, species)
            except Exception as e:
                germline_block = {"error": f"{type(e).__name__}: {e}"}

        elapsed = round(time.time() - t0, 2)
        return {
            "vhh_sequence": seq,
            "scheme": scheme,
            "engine": engine,
            "elapsed_sec": elapsed,
            "regions": vhh_regions,
            "numbering": vh_num_api or [],
            "hallmarks": hallmarks,
            "germline": germline_block,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"VHH segmentation failed: {type(e).__name__}: {e}",
        ) from e
