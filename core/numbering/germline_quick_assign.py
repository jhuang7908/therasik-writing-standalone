"""
Quick closest-V assignment vs species germline libraries (IMGT aa_translated or *_ig_aa JSON).

Used by the demo API for Segmentation & Germline — not the full V4.4 clinical gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SUITE = Path(__file__).resolve().parents[2]

# Console / API keys → IMGT folder name under aa_translated/IG/<Species>/
SPECIES_TO_IMGT: Dict[str, str] = {
    "human": "Homo_sapiens",
    "mouse": "Mus_musculus",
    "rat": "Rattus_norvegicus",
    "rabbit": "Oryctolagus_cuniculus",
    "dog": "Canis_lupus_familiaris",
    "alpaca": "Vicugna_pacos",
    "camel": "Vicugna_pacos",
    "llama": "Vicugna_pacos",
}

# When aa_translated is missing, use JSON pack under data/germlines/<subdir>/
JSON_PACK_ONLY: Dict[str, str] = {
    "Rattus_norvegicus": "rattus_norvegicus_ig_aa",
}


def _load_json_vgenes(suite: Path, subdir: str, fname: str) -> List[Tuple[str, str]]:
    p = suite / "data" / "germlines" / subdir / fname
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return []
    out: List[Tuple[str, str]] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        eid = e.get("id")
        seq = e.get("sequence_aa")
        if eid and seq and isinstance(seq, str):
            aa = "".join(c for c in seq.upper() if c.isalpha())
            if len(aa) >= 20:
                out.append((str(eid), aa))
    return out


def _best(seq: str, refs: List[Tuple[str, str]]) -> Tuple[str, float]:
    from core.resources.germline_resources import best_identity_percent

    if not seq or not refs:
        return "unknown", 0.0
    return best_identity_percent(seq, refs)


def assign_vh_vl_germlines(vh: str, vl: str, species_key: str) -> Dict[str, Any]:
    """
    Return closest IGHV and (IGKV vs IGLV winner) for the given species library.
    """
    from core.resources.germline_resources import (
        aa_ig_fasta,
        vl_identity_imgt,
        vh_identity_imgt,
    )

    sk0 = (species_key or "mouse").strip().lower()
    imgt = SPECIES_TO_IMGT.get(sk0)
    if not imgt:
        return {
            "error": "unknown_species",
            "species_requested": species_key,
            "allowed": sorted(SPECIES_TO_IMGT.keys()),
        }

    ighv_path = aa_ig_fasta(imgt, "IGHV")
    if ighv_path.exists():
        vh_part = vh_identity_imgt(vh, imgt)
        vl_part = vl_identity_imgt(vl, imgt)
        return {
            "species_key": sk0,
            "imgt_species": imgt,
            "source": "aa_translated",
            "vh": vh_part,
            "vl": vl_part,
        }

    sub = JSON_PACK_ONLY.get(imgt)
    if not sub:
        return {
            "species_key": sk0,
            "imgt_species": imgt,
            "error": "no_library",
            "detail": f"No aa_translated or JSON pack for {imgt}",
        }

    vh_refs = _load_json_vgenes(_SUITE, sub, "IGHV_aa.json")
    kv_refs = _load_json_vgenes(_SUITE, sub, "IGKV_aa.json")
    lv_refs = _load_json_vgenes(_SUITE, sub, "IGLV_aa.json")
    vh_n, vh_p = _best(vh, vh_refs)
    nk, pk = _best(vl, kv_refs)
    nl, pl = _best(vl, lv_refs)
    if pk >= pl and nk != "unknown":
        win, wp, loc = nk, pk, "IGKV"
    elif nl != "unknown":
        win, wp, loc = nl, pl, "IGLV"
    else:
        win, wp, loc = "unknown", 0.0, "unknown"

    return {
        "species_key": sk0,
        "imgt_species": imgt,
        "source": f"json:{sub}",
        "vh": {
            "closest_vh_germline": vh_n,
            "vh_germline_identity_pct": vh_p,
            "germline_search_db": f"data/germlines/{sub}/IGHV_aa.json",
        },
        "vl": {
            "closest_vl_germline": win,
            "vl_germline_identity_pct": wp,
            "vl_germline_locus": loc,
            "vl_igkv_candidate": nk,
            "vl_igkv_identity_pct": pk,
            "vl_iglv_candidate": nl,
            "vl_iglv_identity_pct": pl,
            "germline_vl_search_db": f"data/germlines/{sub}/IGKV_aa.json;data/germlines/{sub}/IGLV_aa.json",
        },
    }


def assign_vhh_closest_ighv(vhh_seq: str, species_key: str) -> Dict[str, Any]:
    """
    Closest IGHV (single chain) for VHH / nanobody segmentation demos — same IMGT libraries as VH/VL.
    Camelids: alpaca / camel / llama → Vicugna_pacos IGHV library.
    """
    from core.resources.germline_resources import aa_ig_fasta, vh_identity_imgt

    sk0 = (species_key or "alpaca").strip().lower()
    imgt = SPECIES_TO_IMGT.get(sk0)
    if not imgt:
        return {
            "error": "unknown_species",
            "species_requested": species_key,
            "allowed": sorted(SPECIES_TO_IMGT.keys()),
        }

    vh = (vhh_seq or "").strip().upper().replace(" ", "")
    if not vh:
        return {"error": "empty_sequence"}

    ighv_path = aa_ig_fasta(imgt, "IGHV")
    if ighv_path.exists():
        vh_part = vh_identity_imgt(vh, imgt)
        return {
            "species_key": sk0,
            "imgt_species": imgt,
            "source": "aa_translated",
            "chain": "vhh",
            "vh": vh_part,
        }

    sub = JSON_PACK_ONLY.get(imgt)
    if not sub:
        return {
            "species_key": sk0,
            "imgt_species": imgt,
            "error": "no_library",
            "detail": f"No aa_translated or JSON pack for {imgt}",
        }

    vh_refs = _load_json_vgenes(_SUITE, sub, "IGHV_aa.json")
    vh_n, vh_p = _best(vh, vh_refs)
    return {
        "species_key": sk0,
        "imgt_species": imgt,
        "source": f"json:{sub}",
        "chain": "vhh",
        "vh": {
            "closest_vh_germline": vh_n,
            "vh_germline_identity_pct": vh_p,
            "germline_search_db": f"data/germlines/{sub}/IGHV_aa.json",
        },
    }
