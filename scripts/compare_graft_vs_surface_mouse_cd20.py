#!/usr/bin/env python3
"""
Compare CDR graft vs surface reshaping on the web-console mouse anti-CD20 demo pair.

CDR graft: donor CDRs onto human germline FR (IGHV3-23*01 / IGKV1-39*01), optional Vernier back-mutations.
Surface reshaping: murine sequence with Kabat-defined FR surface positions mutated toward the same human scaffold.

Outputs JSON under projects/mouse_cd20_humanization/graft_surface_compare.json

Usage:
  conda activate anarcii
  python scripts/compare_graft_vs_surface_mouse_cd20.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

from scripts.run_petization_pipeline import (  # noqa: E402
    UNIVERSAL_PET_FR4,
    VERNIER_KABAT_VH,
    VERNIER_KABAT_VL,
    graft_sequence,
    surface_reshape_sequence,
)

from core.cmc.cmc_metrics import (  # noqa: E402
    compute_GRAVY,
    compute_aggregation_motifs,
    compute_instability_index,
    compute_net_charge,
    compute_pI,
)
from core.cmc.adi_score import compute_adi  # noqa: E402

# ---------------------------------------------------------------------------
# Mouse anti-CD20 (console demo mouse-cd20)
VH_MOUSE = (
    "QVQLQQSGPELVKPGASLKLSCTASGFNIKDTYIHWVKQRPEQGLEWIGRIYPTNGYTRYDPKFQDKATITADTSSNTAYLQVSRLTSEDTAVYYCSRWGGDGFYAMDYWGQGASVTVSS"
)
VL_MOUSE = (
    "DIQMTQSPSSLSASVGDRVTITCRASQDVNTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK"
)

HUMAN_IGHV = "IGHV3-23*01"
HUMAN_IGKV = "IGKV1-39*01"


def _load_human_v(seq_type: str, allele_id: str) -> str:
    path = SUITE / "data" / "germlines" / "human_ig_aa" / f"{seq_type}_aa.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for row in data.get("entries", data.get("rows", [])):
        if row.get("id") == allele_id:
            return row["sequence_aa"].strip().upper()
    raise SystemExit(f"Missing {allele_id} in {path}")


def _sid(a: str, b: str) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    return round(sum(x == y for x, y in zip(a, b)) / n * 100.0, 2)


def _fv_metrics(vh: str, vl: str) -> Dict[str, Any]:
    fv = vh + vl
    rm = {
        "pI": round(compute_pI(fv), 2),
        "GRAVY": round(compute_GRAVY(fv), 3),
        "instability_index": round(compute_instability_index(fv), 2),
        "net_charge_pH7": round(compute_net_charge(fv, pH=7.0), 2),
        "agg_motifs": compute_aggregation_motifs(fv),
    }
    try:
        rm["ADI"] = round(compute_adi(rm), 3)
    except Exception as exc:  # noqa: BLE001
        rm["ADI"] = None
        rm["ADI_error"] = str(exc)
    return rm


def main() -> None:
    vh_scaf = _load_human_v("IGHV", HUMAN_IGHV)
    vl_scaf = _load_human_v("IGKV", HUMAN_IGKV)

    fr4_vh = UNIVERSAL_PET_FR4["VH"]
    fr4_vl = UNIVERSAL_PET_FR4["VL_kappa"]

    out: Dict[str, Any] = {
        "input": {
            "vh_mouse": VH_MOUSE,
            "vl_mouse": VL_MOUSE,
            "scaffold_vh": HUMAN_IGHV,
            "scaffold_vl": HUMAN_IGKV,
            "fr4_vh": fr4_vh,
            "fr4_vl": fr4_vl,
        },
        "variants": {},
    }

    # 1) Pure CDR graft: human FR everywhere except donor CDRs (no back-mutations)
    vh_graft0, bm_vh0 = graft_sequence(VH_MOUSE, vh_scaf, "VH", [], fr4_strategy="universal_clinical")
    vl_graft0, bm_vl0 = graft_sequence(VL_MOUSE, vl_scaf, "VL", [], fr4_strategy="universal_clinical", locus="IGKV")

    # 2) CDR graft + Vernier back-mutations (classic lightweight graft)
    vh_graft_v, bm_vh_v = graft_sequence(
        VH_MOUSE, vh_scaf, "VH", VERNIER_KABAT_VH, fr4_strategy="universal_clinical"
    )
    vl_graft_v, bm_vl_v = graft_sequence(
        VL_MOUSE,
        vl_scaf,
        "VL",
        VERNIER_KABAT_VL,
        fr4_strategy="universal_clinical",
        locus="IGKV",
    )

    # 3) Surface reshaping: donor backbone, surface Kabat positions → scaffold
    vh_surf, mut_vh = surface_reshape_sequence(
        VH_MOUSE,
        vh_scaf,
        "VH",
        reshape_keys=None,
        fr4_strategy="universal_clinical",
    )
    vl_surf, mut_vl = surface_reshape_sequence(
        VL_MOUSE,
        vl_scaf,
        "VL",
        reshape_keys=None,
        fr4_strategy="universal_clinical",
        locus="IGKV",
    )

    variants: List[Tuple[str, str, str, Any, Any]] = [
        ("cdr_graft_pure", vh_graft0, vl_graft0, bm_vh0, bm_vl0),
        ("cdr_graft_vernier_bm", vh_graft_v, vl_graft_v, bm_vh_v, bm_vl_v),
        ("surface_reshaping", vh_surf, vl_surf, mut_vh, mut_vl),
    ]

    for name, vh, vl, extra_vh, extra_vl in variants:
        out["variants"][name] = {
            "vh": vh,
            "vl": vl,
            "vh_len": len(vh),
            "vl_len": len(vl),
            "vh_identity_vs_mouse": _sid(VH_MOUSE, vh),
            "vl_identity_vs_mouse": _sid(VL_MOUSE, vl),
            "metrics": _fv_metrics(vh, vl),
            "detail_vh": extra_vh,
            "detail_vl": extra_vl,
        }

    proj = SUITE / "projects" / "mouse_cd20_humanization"
    proj.mkdir(parents=True, exist_ok=True)
    dest = proj / "graft_surface_compare.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")

    slim = {
        k: {kk: vv for kk, vv in v.items() if kk not in ("vh", "vl")}
        for k, v in out["variants"].items()
    }
    print(json.dumps(slim, indent=2, default=str))
    print(f"\nWrote {dest}")


if __name__ == "__main__":
    main()
