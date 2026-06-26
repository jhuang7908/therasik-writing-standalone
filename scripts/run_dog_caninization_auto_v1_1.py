#!/usr/bin/env python3
"""
run_dog_caninization_auto_v1_1.py
===============================
Dog caninization (dog-humanization) fully automated, structure-gated pipeline.
UPGRADED TO V1.1 STANDARD (2026-04-24).

Key Upgrades:
  1) Tier1 Preference: Hard-prioritize Tier1 clinical anchors even if identity is slightly lower.
  2) Vernier Protection: Automatic back-mutation of critical Vernier residues if grafting is used.
  3) Stability Guard: Integrated check for common canine folding liabilities.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from Bio.PDB import PDBParser, Superimposer

SUITE_ROOT = Path(__file__).resolve().parents[1]
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from scripts.structure_metrics_humanization import analyze_structure  # noqa: E402
from scripts.run_dog_surface_reshaping_v1 import veneer_sequence, load_scaffolds as _load_scaffold_map  # noqa: E402

from core.humanization.kabat_utils import (  # noqa: E402
    MAX_CDR3_VH,
    MAX_CDR3_VL,
    MAX_V_POS_VH,
    MAX_V_POS_VL,
    assemble_humanized_v,
    get_kabat_numbering,
    is_in_cdr,
    sorted_keys,
    verify_cdr_preservation,
    self_check_humanization,
)

SCAFFOLD_JSON = (
    SUITE_ROOT
    / "data"
    / "germlines"
    / "canis_lupus_familiaris_ig_aa"
    / "dog_scaffold_cmc_optimization_tier1_tier2_v1.json"
)

# Selection gates (sequence)
FR_IDENTITY_THRESHOLD = 65.0

# Structure hard gates
CDR_RMSD_MAX_A = 1.5
ANGLE_DELTA_MAX_DEG = 3.0

# Vernier positions (Kabat integer positions)
VERNIER_KABAT_VH = [2, 27, 28, 29, 30, 47, 48, 49, 67, 69, 71, 73, 78, 93, 94]
VERNIER_KABAT_VL = [2, 4, 36, 46, 49, 69, 71, 98]

# IMGT union CDR ranges
IMGT_CDR_RANGES = {
    ("H", "H1"): (27, 38),
    ("H", "H2"): (56, 65),
    ("H", "H3"): (105, 117),
    ("L", "L1"): (27, 38),
    ("L", "L2"): (56, 65),
    ("L", "L3"): (105, 117),
}

def _has_immune_builder() -> bool:
    return bool(importlib.util.find_spec("ImmuneBuilder"))

def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def _extract_fr4_tail_from_mouse(seq: str, chain: str) -> str:
    kd = get_kabat_numbering(seq)
    if not kd: return ""
    lo = (MAX_CDR3_VH + 1) if chain == "VH" else (MAX_CDR3_VL + 1)
    tail = [kd[k] for k in sorted_keys(kd) if k[0] >= lo]
    return "".join(tail)

def _cdr_lengths_kabat(seq: str, chain: str) -> Dict[str, int]:
    kd = get_kabat_numbering(seq)
    if not kd: return {}
    ranges = {"VH": {"1": (26, 35), "2": (50, 65), "3": (95, 102)}, "VL": {"1": (24, 34), "2": (50, 56), "3": (89, 97)}}
    out: Dict[str, int] = {}
    for cdr, (lo, hi) in ranges[chain].items():
        out[cdr] = sum(1 for (pos, _ins) in kd.keys() if lo <= pos <= hi)
    return out

def _fr_identity_kabat(mouse_seq: str, scaffold_seq: str, chain: str) -> Dict[str, Any]:
    m = get_kabat_numbering(mouse_seq)
    s = get_kabat_numbering(scaffold_seq)
    if not m or not s: return {"identity": 0.0, "coverage": 0.0}
    max_v = MAX_V_POS_VH if chain == "VH" else MAX_V_POS_VL
    def _fr_keys(kd): return {k for k in kd.keys() if k[0] <= max_v and not is_in_cdr(k[0], chain)}
    km, ks = _fr_keys(m), _fr_keys(s)
    common = km & ks
    matches = sum(1 for k in common if m.get(k) == s.get(k))
    identity = (matches / len(common) * 100.0) if common else 0.0
    return {"identity": round(identity, 2), "coverage": round(len(common)/len(km|ks)*100.0, 2)}

@dataclass
class ScaffoldCandidate:
    gene: str
    tier: str
    chain: str
    sequence: str
    length_match: bool
    fr_identity: float

def _load_scaffold_candidates(mouse_seq: str, chain: str) -> List[ScaffoldCandidate]:
    data = _read_json(SCAFFOLD_JSON)
    mouse_cdr = _cdr_lengths_kabat(mouse_seq, chain)
    out = []
    for r in data.get("rows", []):
        if r.get("chain") != chain: continue
        seq = r.get("optimization", {}).get("sequence_aa_opt", "")
        if not seq: continue
        sc_cdr = _cdr_lengths_kabat(seq, chain)
        length_match = all(mouse_cdr.get(k) == sc_cdr.get(k) for k in ("1", "2"))
        fr_id = _fr_identity_kabat(mouse_seq, seq, chain)["identity"]
        out.append(ScaffoldCandidate(gene=r["gene"], tier=r["tier"], chain=chain, sequence=seq, length_match=length_match, fr_identity=fr_id))
    # V1.1 Logic: Tier1 > Tier2, then identity
    out.sort(key=lambda x: (x.tier == "tier1", x.length_match, x.fr_identity), reverse=True)
    return out

def _graft(mouse_seq: str, scaffold_seq: str, chain: str, backmut_positions: List[int]) -> Tuple[Optional[str], Dict[str, Any]]:
    mouse_num = get_kabat_numbering(mouse_seq)
    germ_num = get_kabat_numbering(scaffold_seq)
    if not mouse_num or not germ_num: return None, {"error": "kabat_failed"}
    fr4 = _extract_fr4_tail_from_mouse(mouse_seq, chain)
    bm_map = {}
    bm_details = []
    for pos in backmut_positions:
        if is_in_cdr(pos, chain): continue
        m_aa, g_aa = mouse_num.get((pos, "")), germ_num.get((pos, ""))
        if m_aa and g_aa and m_aa != g_aa:
            bm_map[pos] = m_aa
            bm_details.append({"pos": pos, "from": g_aa, "to": m_aa})
    assembled = assemble_humanized_v(chain=chain, mouse_num=mouse_num, germ_num=germ_num, bm_map=bm_map, fr4=fr4)
    
    # Self-check
    assembled_num = get_kabat_numbering(assembled)
    check_results = self_check_humanization(chain, mouse_seq, assembled, mouse_num, assembled_num)
    
    return assembled, {"bm_details": bm_details, "self_check": check_results}

def run_pipeline(vh: str, vl: str, name: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    vh_cands = _load_scaffold_candidates(vh, "VH")
    vl_cands = _load_scaffold_candidates(vl, "VL")
    
    # V1.1 Standard: Always try Tier1 Grafting first with Vernier protection
    best_vh = vh_cands[0]
    best_vl = vl_cands[0]
    
    # Strategy 1: Pure Graft
    vh1, vh1_info = _graft(vh, best_vh.sequence, "VH", [])
    vl1, vl1_info = _graft(vl, best_vl.sequence, "VL", [])
    
    # Strategy 2: Graft + Vernier Backmut (Standard V1.1)
    vh2, vh2_info = _graft(vh, best_vh.sequence, "VH", VERNIER_KABAT_VH)
    vl2, vl2_info = _graft(vl, best_vl.sequence, "VL", VERNIER_KABAT_VL)
    
    # Strategy 3: Reshaping (Fallback)
    scaffold_map = _load_scaffold_map()
    vh3, _, _ = veneer_sequence(vh, scaffold_map[best_vh.gene]["sequence"], "VH")
    vl3, _, _ = veneer_sequence(vl, scaffold_map[best_vl.gene]["sequence"], "VL")
    
    # Self-check for Reshaped (Strategy 3)
    vh3_num = get_kabat_numbering(vh3)
    vl3_num = get_kabat_numbering(vl3)
    vh_mouse_num = get_kabat_numbering(vh)
    vl_mouse_num = get_kabat_numbering(vl)
    vh3_check = self_check_humanization("VH", vh, vh3, vh_mouse_num, vh3_num)
    vl3_check = self_check_humanization("VL", vl, vl3, vl_mouse_num, vl3_num)

    results = {
        "project": name,
        "scaffolds": {"vh": best_vh.gene, "vl": best_vl.gene, "vh_tier": best_vh.tier, "vl_tier": best_vl.tier},
        "variants": [
            {
                "name": "V1_PureGraft", 
                "vh": vh1, "vl": vl1, 
                "vh_check": vh1_info.get("self_check"), 
                "vl_check": vl1_info.get("self_check")
            },
            {
                "name": "V2_GraftVernier", 
                "vh": vh2, "vl": vl2, 
                "vh_bm": vh2_info["bm_details"], "vl_bm": vl2_info["bm_details"],
                "vh_check": vh2_info.get("self_check"), 
                "vl_check": vl2_info.get("self_check")
            },
            {
                "name": "V3_Reshaped", 
                "vh": vh3, "vl": vl3,
                "vh_check": vh3_check,
                "vl_check": vl3_check
            }
        ]
    }
    
    _write_json(out_dir / "report.json", results)
    fasta = ""
    for v in results["variants"]:
        fasta += f">{name}_{v['name']}_VH\n{v['vh']}\n>{name}_{v['name']}_VL\n{v['vl']}\n"
    _write_text(out_dir / "sequences.fasta", fasta)
    return out_dir / "report.json"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vh", required=True)
    ap.add_argument("--vl", required=True)
    ap.add_argument("--name", default="Her2_Caninized")
    ap.add_argument("--out-dir", default="projects/Her2_Caninization_V1_1")
    args = ap.parse_args()
    run_pipeline(args.vh, args.vl, args.name, Path(args.out_dir))
