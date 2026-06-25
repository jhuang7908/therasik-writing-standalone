"""
Alternative-route CDR grafting deliverable (V5.4.13).

When a rabbit/rat humanization run lands in the V5.4 "intermediate state"
(a high-identity ≥65% germline candidate exists but composite score selects
a different germline because of CMC/Vernier trade-offs), Standard
`VH_VL_HUMANIZATION_STANDARD_V4.4` mandates that BOTH routes be delivered:

  Route A (selected)        : composite-best CDR grafting
  Route A' (alternative)    : CDR grafting onto the ≥65% germline (this module)
  Route B (surface reshape) : structure-driven FR surface substitution

This helper produces the Route A' deliverable as a self-contained side
artefact: it does NOT rerun the full Phase 1-5 engine, and it does NOT
mutate the primary humanization result. It performs a pure CDR-grafting
assembly (ANARCII numbering + V5.1 Union CDR positions) on the alternative
VH germline, paired with the same VL germline that the primary route
selected, and then computes the same sequence-level mini-CMC and AbLang
humanness metrics used elsewhere in the pipeline.

The output is consumed by the API router and rendered into the report's
"Route comparison" block as a real, deliverable, head-to-head alternative.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SUITE = Path(__file__).resolve().parents[2]
GERM_ROOT = SUITE / "data" / "germlines"

# Mirror engine._CDR_POS_V51 (Union/IMGT runtime CDR positions).
_CDR_POS_V51_H = frozenset(range(26, 39)) | frozenset(range(50, 66)) | frozenset(range(105, 118))
_CDR_POS_V51_L = frozenset(range(26, 39)) | frozenset(range(50, 66)) | frozenset(range(105, 118))


def _load_human_vh(germline_id: str) -> str:
    try:
        d = json.loads((GERM_ROOT / "ogrdb_human_IGHV_v2.json").read_text(encoding="utf-8"))
        return str(d.get(germline_id) or "")
    except Exception:
        return ""


def _load_human_vl(germline_id: str) -> str:
    gid = (germline_id or "").upper()
    try:
        if gid.startswith("IGLV"):
            d = json.loads((GERM_ROOT / "ogrdb_human_IGLV_v2.json").read_text(encoding="utf-8"))
        else:
            d = json.loads((GERM_ROOT / "ogrdb_human_IGKV_v2.json").read_text(encoding="utf-8"))
        return str(d.get(germline_id) or "")
    except Exception:
        return ""


def _default_fr4(chain: str, is_lambda: bool) -> str:
    if (chain or "").upper() in ("VH", "H"):
        return "WGQGTLVTVSS"
    return "FGGGTKLTVL" if is_lambda else "FGGGTKLEIK"


def _graft_one(donor: str, germ: str, chain: str) -> Tuple[str, List[str]]:
    """CDR-graft donor onto germ framework using ANARCII (default IMGT).

    Returns (grafted_sequence, fr_diffs) where fr_diffs lists positions
    that received the human germline residue (FR humanizing changes).
    """
    if not donor or not germ:
        return "", []
    try:
        from anarcii import Anarcii  # noqa: PLC0415

        n = Anarcii()
        res = n.number(seqs=[("g", germ), ("d", donor)])
    except Exception:
        return "", []

    g_num = (res.get("g") or {}).get("numbering") or []
    d_pkg = res.get("d") or {}
    d_num = d_pkg.get("numbering") or []
    chain_type = d_pkg.get("chain_type") or ("H" if chain.upper() == "VH" else "K")

    cdr_pos = _CDR_POS_V51_H if chain_type.upper() in ("H", "VH") else _CDR_POS_V51_L

    g_dict = {pi: aa for pi, aa in g_num if aa != "-"}
    d_dict = {pi: aa for pi, aa in d_num if aa != "-"}

    all_keys = sorted(d_dict.keys(), key=lambda x: (x[0], (x[1] or "").strip()))
    grafted: List[str] = []
    fr_diffs: List[str] = []
    for pi in all_keys:
        pos, _ = pi
        if pos > 117:
            continue
        d_aa = d_dict[pi]
        g_aa = g_dict.get(pi)
        if pos in cdr_pos:
            grafted.append(d_aa)
        else:
            use_aa = g_aa if g_aa else d_aa
            grafted.append(use_aa)
            if g_aa and g_aa != d_aa:
                fr_diffs.append(f"pos{pos}:{d_aa}->{g_aa}")

    is_lambda = chain_type.upper() == "L" and not chain_type.upper().startswith("K")
    fr4 = _default_fr4(chain, is_lambda)
    return "".join(grafted) + fr4, fr_diffs


def _basic_cmc(seq: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "pI": None,
        "gravy": None,
        "instability_index": None,
        "liabilities": [],
        "liability_count": 0,
    }
    try:
        from Bio.SeqUtils.ProtParam import ProteinAnalysis  # type: ignore

        pa = ProteinAnalysis((seq or "").upper())
        pi = round(float(pa.isoelectric_point()), 2)
        gravy = round(float(pa.gravy()), 3)
        ii = round(float(pa.instability_index()), 2)
        liab: List[str] = []
        if not (5.5 <= pi <= 8.5):
            liab.append(f"pI_out_of_range:{pi}")
        if gravy > 0.2:
            liab.append(f"high_gravy:{gravy}")
        if ii > 45.0:
            liab.append(f"instability_index:{ii}")
        out.update({
            "pI": pi,
            "gravy": gravy,
            "instability_index": ii,
            "liabilities": liab,
            "liability_count": len(liab),
        })
    except Exception as e:
        out["error"] = str(e)
    return out


def _ablang_score(vh: str, vl: str) -> Optional[float]:
    """Mean log-likelihood (higher = more human). Returns None on failure."""
    try:
        import ablang  # type: ignore  # noqa: PLC0415

        h = ablang.pretrained("heavy")
        l = ablang.pretrained("light")
        h.freeze()
        l.freeze()
        sh = float(h([vh], mode="likelihood")[0].mean()) if vh else 0.0
        sl = float(l([vl], mode="likelihood")[0].mean()) if vl else 0.0
        return round((sh + sl) / 2.0, 3)
    except Exception:
        return None


def _fr_identity(donor: str, germ: str, chain: str) -> Optional[float]:
    """ANARCII-numbered, CDR-masked FR identity (% identical FR positions)."""
    try:
        from anarcii import Anarcii  # noqa: PLC0415

        n = Anarcii()
        res = n.number(seqs=[("d", donor), ("g", germ)])
    except Exception:
        return None
    d_num = (res.get("d") or {}).get("numbering") or []
    g_num = (res.get("g") or {}).get("numbering") or []
    if not d_num or not g_num:
        return None
    cdr_pos = _CDR_POS_V51_H if chain.upper() in ("VH", "H") else _CDR_POS_V51_L
    d_dict = {pi: aa for pi, aa in d_num if aa != "-"}
    g_dict = {pi: aa for pi, aa in g_num if aa != "-"}
    common = [pi for pi in d_dict if pi in g_dict and pi[0] not in cdr_pos and pi[0] <= 117]
    if not common:
        return None
    same = sum(1 for pi in common if d_dict[pi] == g_dict[pi])
    return round(100.0 * same / len(common), 1)


def build_alt_route_grafting_deliverable(
    donor_vh: str,
    donor_vl: str,
    alt_vh_germline_id: str,
    selected_vl_germline_id: str,
) -> Dict[str, Any]:
    """Build a Route A' (alternative ≥65% CDR grafting) deliverable.

    Pairs the alternative VH germline with the primary route's VL germline
    so the comparison is single-variable (VH route only).
    """
    out: Dict[str, Any] = {
        "applied": False,
        "alt_vh_germline": alt_vh_germline_id,
        "vl_germline": selected_vl_germline_id,
        "humanized_vh": "",
        "humanized_vl": "",
        "vh_fr_identity": None,
        "vl_fr_identity": None,
        "vh_fr_substitutions": 0,
        "vl_fr_substitutions": 0,
        "ablang_score": None,
        "basic_cmc": {},
        "errors": [],
        "note": "",
    }

    germ_vh_seq = _load_human_vh(alt_vh_germline_id)
    germ_vl_seq = _load_human_vl(selected_vl_germline_id)
    if not germ_vh_seq:
        out["errors"].append(f"Alt VH germline '{alt_vh_germline_id}' not found in OGRDB cache.")
        return out
    if not germ_vl_seq:
        out["errors"].append(f"VL germline '{selected_vl_germline_id}' not found in OGRDB cache.")
        return out

    hum_vh, vh_fr_diffs = _graft_one(donor_vh, germ_vh_seq, "VH")
    hum_vl, vl_fr_diffs = _graft_one(donor_vl, germ_vl_seq, "VL")
    if not hum_vh or not hum_vl:
        out["errors"].append("Grafting failed: ANARCII numbering returned empty result.")
        return out

    out["humanized_vh"] = hum_vh
    out["humanized_vl"] = hum_vl
    out["vh_fr_substitutions"] = len(vh_fr_diffs)
    out["vl_fr_substitutions"] = len(vl_fr_diffs)
    out["vh_fr_identity"] = _fr_identity(donor_vh, germ_vh_seq, "VH")
    out["vl_fr_identity"] = _fr_identity(donor_vl, germ_vl_seq, "VL")
    out["ablang_score"] = _ablang_score(hum_vh, hum_vl)
    out["basic_cmc"] = {
        "vh": _basic_cmc(hum_vh),
        "vl": _basic_cmc(hum_vl),
        "fab": _basic_cmc(hum_vh + hum_vl),
    }
    out["applied"] = True
    out["note"] = (
        f"Alternative ≥65% CDR-grafting onto {alt_vh_germline_id} (raw graft, "
        "no Phase 4 back-mutations). Pair with primary VL germline for "
        "single-variable head-to-head comparison."
    )
    return out
