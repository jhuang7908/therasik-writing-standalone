#!/usr/bin/env python3
"""
run_dog_caninization_auto_v1.py
===============================
Dog caninization (dog-humanization) fully automated, structure-gated pipeline.

Priority logic (per USER policy):
  1) Prefer Tier1/Tier2 dog scaffolds for CDR grafting (length gate first, then FR identity).
  2) If no qualified scaffold, fall back to surface reshaping (veneering) which should work
     for any antibody (mutate surface FR residues only, preserve CDR/core).
  3) Structure hard-gate is REQUIRED. If grafting fails the gate, automatically attempt:
       - Vernier-zone backmutations (mouse residues at Vernier positions)
       - If still fails, surface reshaping fallback

Hard gates (structure):
  - CDR RMSD after framework alignment: max per CDR <= 1.5 Å
  - VH/VL angle deviation <= 3.0°
  - Canonical class consistency (H1/H2/L1) between mouse vs candidate

Outputs (default):
  projects/<name>/dog_caninization_auto_v1/
    - report.json / report.md
    - sequences.fasta
    - structures/mouse.pdb
    - structures/<stage>.pdb
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

# Vernier positions (Kabat integer positions) — aligned with structure_metrics_humanization
VERNIER_KABAT_VH = [2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94]
VERNIER_KABAT_VL = [2, 4, 36, 46, 49, 69, 71, 98]

# IMGT union CDR ranges (used for RMSD gate on ImmuneBuilder IMGT-numbered PDBs)
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
    if not kd:
        return ""
    lo = (MAX_CDR3_VH + 1) if chain == "VH" else (MAX_CDR3_VL + 1)
    tail = [kd[k] for k in sorted_keys(kd) if k[0] >= lo]
    return "".join(tail)


def _cdr_lengths_kabat(seq: str, chain: str) -> Dict[str, int]:
    kd = get_kabat_numbering(seq)
    if not kd:
        return {}
    ranges = {"VH": {"1": (26, 35), "2": (50, 65), "3": (95, 102)}, "VL": {"1": (24, 34), "2": (50, 56), "3": (89, 97)}}
    out: Dict[str, int] = {}
    for cdr, (lo, hi) in ranges[chain].items():
        out[cdr] = sum(1 for (pos, _ins) in kd.keys() if lo <= pos <= hi)
    return out


def _fr_identity_kabat(mouse_seq: str, scaffold_seq: str, chain: str) -> Dict[str, Any]:
    """
    FR-only identity on Kabat keys, limited to FR1-3 (V-region) and excluding CDRs.
    Reports identity, coverage, and n_compared for auditability.
    """
    m = get_kabat_numbering(mouse_seq)
    s = get_kabat_numbering(scaffold_seq)
    if not m or not s:
        return {"identity": 0.0, "coverage": 0.0, "n_compared": 0, "n_union": 0, "n_common": 0}

    max_v = MAX_V_POS_VH if chain == "VH" else MAX_V_POS_VL

    def _fr_keys(kd):
        return {k for k in kd.keys() if k[0] <= max_v and not is_in_cdr(k[0], chain)}

    km = _fr_keys(m)
    ks = _fr_keys(s)
    common = km & ks
    union = km | ks

    matches = sum(1 for k in common if m.get(k) == s.get(k))
    identity = (matches / len(common) * 100.0) if common else 0.0
    coverage = (len(common) / len(union) * 100.0) if union else 0.0

    return {
        "identity": round(identity, 2),
        "coverage": round(coverage, 2),
        "n_compared": int(len(common)),
        "n_union": int(len(union)),
        "n_common": int(len(common)),
    }


@dataclass
class ScaffoldCandidate:
    gene: str
    tier: str
    chain: str  # VH/VL
    sequence: str  # CMC-optimized scaffold sequence (V-region)
    cdr_len: Dict[str, int]
    length_match: bool
    fr_identity: float
    fr_coverage: float


def _load_scaffold_rows() -> List[Dict[str, Any]]:
    data = _read_json(SCAFFOLD_JSON)
    return list(data.get("rows") or [])


def _scaffold_candidates_for_chain(mouse_seq: str, chain: str) -> List[ScaffoldCandidate]:
    rows = _load_scaffold_rows()
    mouse_cdr = _cdr_lengths_kabat(mouse_seq, chain)
    out: List[ScaffoldCandidate] = []
    for r in rows:
        if str(r.get("chain")) != chain:
            continue
        gene = str(r.get("gene") or "")
        tier = str(r.get("tier") or "")
        seq = str(((r.get("optimization") or {}).get("sequence_aa_opt")) or "")
        if not gene or not seq:
            continue
        sc_cdr = _cdr_lengths_kabat(seq, chain)

        # Length gate: check CDR1/CDR2 only (CDR3 will be grafted)
        length_match = True
        for k in ("1", "2"):
            if mouse_cdr.get(k) != sc_cdr.get(k):
                length_match = False
                break

        fr_id = _fr_identity_kabat(mouse_seq, seq, chain)
        out.append(
            ScaffoldCandidate(
                gene=gene,
                tier=tier,
                chain=chain,
                sequence=seq,
                cdr_len=sc_cdr,
                length_match=length_match,
                fr_identity=float(fr_id["identity"]),
                fr_coverage=float(fr_id["coverage"]),
            )
        )
    out.sort(key=lambda x: (x.length_match, x.fr_identity, x.fr_coverage), reverse=True)
    return out


def _graft_with_optional_vernier_backmut(
    mouse_seq: str,
    scaffold_seq: str,
    chain: str,
    apply_vernier_backmut: bool,
) -> Tuple[Optional[str], Dict[str, Any]]:
    mouse_num = get_kabat_numbering(mouse_seq)
    germ_num = get_kabat_numbering(scaffold_seq)
    if not mouse_num or not germ_num:
        return None, {"error": "kabat_numbering_failed"}

    fr4_tail = _extract_fr4_tail_from_mouse(mouse_seq, chain)

    bm_map: Dict[int, str] = {}
    bm_details: List[Dict[str, Any]] = []
    if apply_vernier_backmut:
        vernier = VERNIER_KABAT_VH if chain == "VH" else VERNIER_KABAT_VL
        for pos in vernier:
            if is_in_cdr(pos, chain):
                continue
            mouse_aa = mouse_num.get((pos, ""))
            germ_aa = germ_num.get((pos, ""))
            if not mouse_aa or not germ_aa:
                continue
            if mouse_aa != germ_aa:
                bm_map[pos] = mouse_aa
                bm_details.append({"kabat_pos": pos, "from": germ_aa, "to": mouse_aa, "reason": "vernier_backmutation"})

    assembled = assemble_humanized_v(chain=chain, mouse_num=mouse_num, germ_num=germ_num, bm_map=bm_map, fr4=fr4_tail)

    # Hard gate: CDR preservation (Kabat)
    assembled_num = get_kabat_numbering(assembled)
    errors = verify_cdr_preservation(assembled_num, mouse_num, chain=chain) if assembled_num else ["kabat_numbering_failed_after_assembly"]
    if errors:
        return None, {"error": "cdr_preservation_failed", "details": errors, "bm_details": bm_details}

    return assembled, {"bm_details": bm_details, "fr4_tail_used": fr4_tail}


def _model_pdb(vh: str, vl: str, out_pdb: Path) -> Dict[str, Any]:
    if out_pdb.exists():
        return {"pdb_path": str(out_pdb), "cached": True}

    if not _has_immune_builder():
        return {"error": "ImmuneBuilder not available"}

    from ImmuneBuilder import ABodyBuilder2  # type: ignore

    out_pdb.parent.mkdir(parents=True, exist_ok=True)
    predictor = ABodyBuilder2(numbering_scheme="imgt")
    ab = predictor.predict({"H": vh, "L": vl})
    # Prefer unrefined save to avoid OpenMM issues on some setups
    if hasattr(ab, "save_single_unrefined"):
        ab.save_single_unrefined(str(out_pdb))
    else:
        ab.save(str(out_pdb))
    return {"pdb_path": str(out_pdb), "cached": False}


def _parse_pdb(path: Path):
    parser = PDBParser(QUIET=True)
    return parser.get_structure(path.stem, str(path))


def _all_resids(chain) -> List[int]:
    return [r.id[1] for r in chain if r.id[0] == " "]


def _ca_atoms_for_resids(chain, res_ids) -> List[Any]:
    out = []
    for rid in res_ids:
        try:
            r = chain[(" ", int(rid), " ")]
            if "CA" in r:
                out.append(r["CA"])
        except Exception:
            continue
    return out


def _framework_resids(structure, chain_id: str) -> List[int]:
    ids = set(_all_resids(structure[0][chain_id]))
    cdr = set()
    for (c, _name), (a, b) in IMGT_CDR_RANGES.items():
        if c == chain_id:
            cdr |= set(range(a, b + 1))
    return sorted(ids - cdr)


def _cdr_rmsds_after_framework_align(pdb_ref: Path, pdb_mov: Path) -> Dict[str, Optional[float]]:
    s_ref = _parse_pdb(pdb_ref)
    s_mov = _parse_pdb(pdb_mov)

    fw_h = _framework_resids(s_ref, "H")
    fw_l = _framework_resids(s_ref, "L")
    fw1 = _ca_atoms_for_resids(s_ref[0]["H"], fw_h) + _ca_atoms_for_resids(s_ref[0]["L"], fw_l)
    fw2 = _ca_atoms_for_resids(s_mov[0]["H"], fw_h) + _ca_atoms_for_resids(s_mov[0]["L"], fw_l)
    n = min(len(fw1), len(fw2))
    if n < 10:
        return {name: None for (_c, name) in IMGT_CDR_RANGES.keys()}

    sup = Superimposer()
    sup.set_atoms(fw1[:n], fw2[:n])
    sup.apply(s_mov[0].get_atoms())

    def _rmsd(a: np.ndarray, b: np.ndarray) -> float:
        d = a - b
        return float(np.sqrt(np.mean(np.sum(d * d, axis=1))))

    out: Dict[str, Optional[float]] = {}
    for (chain_id, name), (a, b) in IMGT_CDR_RANGES.items():
        c1 = _ca_atoms_for_resids(s_ref[0][chain_id], range(a, b + 1))
        c2 = _ca_atoms_for_resids(s_mov[0][chain_id], range(a, b + 1))
        m = min(len(c1), len(c2))
        if m < 3:
            out[name] = None
            continue
        out[name] = _rmsd(np.array([x.coord for x in c1[:m]]), np.array([x.coord for x in c2[:m]]))
    return out


def _structure_metrics(pdb_path: Path) -> Dict[str, Any]:
    m = analyze_structure(pdb_path, chain_vh="H", chain_vl="L", skip_sasa=True)
    return {
        "canonical": dict(m.canonical or {}),
        "canonical_north": dict(m.canonical_north or {}),
        "canonical_north_score": dict(m.canonical_north_score or {}),
        "vh_vl_angle_deg": m.vh_vl_angle_deg,
        "errors": list(m.errors or []),
    }


def _canonical_pass(mouse_can: Dict[str, str], cand_can: Dict[str, str]) -> Tuple[bool, Dict[str, Any]]:
    keys = ["H1", "H2", "L1"]
    cmp: Dict[str, Any] = {}
    ok = True
    for k in keys:
        mv = mouse_can.get(k, "?")
        cv = cand_can.get(k, "?")
        match = mv == cv
        cmp[k] = {"mouse": mv, "candidate": cv, "match": match}
        if not match:
            ok = False
    return ok, cmp


def _rmsd_pass(per_cdr: Dict[str, Optional[float]]) -> Tuple[bool, float]:
    vals = [v for v in per_cdr.values() if isinstance(v, (int, float)) and v == v]  # v==v filters NaN
    if not vals:
        return False, float("nan")
    mx = float(max(vals))
    return mx <= CDR_RMSD_MAX_A, mx


def _angle_pass(mouse_deg: Optional[float], cand_deg: Optional[float]) -> Tuple[bool, Optional[float]]:
    if mouse_deg is None or cand_deg is None:
        return False, None
    delta = float(abs(cand_deg - mouse_deg))
    return delta <= ANGLE_DELTA_MAX_DEG, delta


def _fasta(name: str, seq: str) -> str:
    return f">{name}\n{seq}\n"


def run_pipeline(mouse_vh: str, mouse_vl: str, project_name: str, out_dir: Path) -> Path:
    out_dir = out_dir.resolve()
    structures_dir = out_dir / "structures"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load scaffold map for veneering (gene -> {sequence,...})
    scaffold_map = _load_scaffold_map()

    # Candidates per chain
    vh_cands = _scaffold_candidates_for_chain(mouse_vh, "VH")
    vl_cands = _scaffold_candidates_for_chain(mouse_vl, "VL")

    def _best_for_veneering(cands: List[ScaffoldCandidate]) -> Optional[ScaffoldCandidate]:
        return cands[0] if cands else None

    best_vh = vh_cands[0] if vh_cands else None
    best_vl = vl_cands[0] if vl_cands else None

    # Decide qualified scaffolds for grafting (length match + FR identity threshold)
    qualified_vh = next((c for c in vh_cands if c.length_match and c.fr_identity >= FR_IDENTITY_THRESHOLD), None)
    qualified_vl = next((c for c in vl_cands if c.length_match and c.fr_identity >= FR_IDENTITY_THRESHOLD), None)

    plan = {
        "vh": {
            "qualified_scaffold": qualified_vh.gene if qualified_vh else None,
            "best_scaffold": best_vh.gene if best_vh else None,
        },
        "vl": {
            "qualified_scaffold": qualified_vl.gene if qualified_vl else None,
            "best_scaffold": best_vl.gene if best_vl else None,
        },
    }

    # Donors for surface reshaping (always available safety net)
    vh_best = _best_for_veneering(vh_cands)
    vl_best = _best_for_veneering(vl_cands)
    if not vh_best or not vl_best:
        raise RuntimeError("No dog scaffolds available for surface reshaping fallback.")
    vh_donor = scaffold_map[vh_best.gene]["sequence"]
    vl_donor = scaffold_map[vl_best.gene]["sequence"]

    # Stage builders (produce full sequences VH/VL)
    stages: List[Dict[str, Any]] = []

    def _stage_add(name: str, vh_seq: str, vl_seq: str, meta: Dict[str, Any]) -> None:
        stages.append({"name": name, "vh": vh_seq, "vl": vl_seq, "meta": meta})

    # Stage 1: Prefer CDR grafting if qualified; otherwise DO surface reshaping () immediately.
    # We must not "pass" by leaving the mouse sequence unchanged.
    stage1_meta: Dict[str, Any] = {"strategy": {}, "grafting": {}, "veneering": {}}

    # VH
    if qualified_vh:
        seq, info = _graft_with_optional_vernier_backmut(mouse_vh, qualified_vh.sequence, "VH", apply_vernier_backmut=False)
        if not seq:
            stage1_meta["strategy"]["VH"] = "graft_failed_pre_gate_to_reshaping"
            vh1, muts, notes = veneer_sequence(mouse_vh, vh_donor, "VH")
            stage1_meta["veneering"]["VH"] = {"donor": vh_best.gene, "mutation_count": len(muts), "mutations": muts, "notes": notes}
            stage1_meta["grafting"]["VH"] = {"scaffold": qualified_vh.gene, "error": info}
        else:
            vh1 = seq
            stage1_meta["strategy"]["VH"] = "graft"
            stage1_meta["grafting"]["VH"] = {"scaffold": qualified_vh.gene, "vernier_backmut": False, **info}
    else:
        vh1, muts, notes = veneer_sequence(mouse_vh, vh_donor, "VH")
        stage1_meta["strategy"]["VH"] = "surface_reshaping_no_qualified_scaffold"
        stage1_meta["veneering"]["VH"] = {"donor": vh_best.gene, "mutation_count": len(muts), "mutations": muts, "notes": notes}

    # VL
    if qualified_vl:
        seq, info = _graft_with_optional_vernier_backmut(mouse_vl, qualified_vl.sequence, "VL", apply_vernier_backmut=False)
        if not seq:
            stage1_meta["strategy"]["VL"] = "graft_failed_pre_gate_to_reshaping"
            vl1, muts, notes = veneer_sequence(mouse_vl, vl_donor, "VL")
            stage1_meta["veneering"]["VL"] = {"donor": vl_best.gene, "mutation_count": len(muts), "mutations": muts, "notes": notes}
            stage1_meta["grafting"]["VL"] = {"scaffold": qualified_vl.gene, "error": info}
        else:
            vl1 = seq
            stage1_meta["strategy"]["VL"] = "graft"
            stage1_meta["grafting"]["VL"] = {"scaffold": qualified_vl.gene, "vernier_backmut": False, **info}
    else:
        vl1, muts, notes = veneer_sequence(mouse_vl, vl_donor, "VL")
        stage1_meta["strategy"]["VL"] = "surface_reshaping_no_qualified_scaffold"
        stage1_meta["veneering"]["VL"] = {"donor": vl_best.gene, "mutation_count": len(muts), "mutations": muts, "notes": notes}

    _stage_add("stage1_primary_graft_or_reshape", vh1, vl1, stage1_meta)

    # Stage 2: If any grafting used, try Vernier backmutations on grafted chains
    if qualified_vh or qualified_vl:
        stage2_meta: Dict[str, Any] = {"strategy": {}, "grafting": {}}
        if qualified_vh:
            seq, info = _graft_with_optional_vernier_backmut(mouse_vh, qualified_vh.sequence, "VH", apply_vernier_backmut=True)
            vh2 = seq or vh1
            stage2_meta["strategy"]["VH"] = "graft_vernier_backmut"
            stage2_meta["grafting"]["VH"] = {"scaffold": qualified_vh.gene, "vernier_backmut": True, **info}
        else:
            vh2 = vh1
        if qualified_vl:
            seq, info = _graft_with_optional_vernier_backmut(mouse_vl, qualified_vl.sequence, "VL", apply_vernier_backmut=True)
            vl2 = seq or vl1
            stage2_meta["strategy"]["VL"] = "graft_vernier_backmut"
            stage2_meta["grafting"]["VL"] = {"scaffold": qualified_vl.gene, "vernier_backmut": True, **info}
        else:
            vl2 = vl1
        _stage_add("stage2_graft_vernier_backmut", vh2, vl2, stage2_meta)

    # Stage 3: Surface reshaping fallback for BOTH chains (universal safety net).
    # Even if Stage 1 already reshaped one chain, this stage is the "all-in reshaping" final fallback.
    stage3_meta: Dict[str, Any] = {"strategy": {"VH": "surface_reshaping", "VL": "surface_reshaping"}, "veneering": {}}
    vh3, vh_muts, vh_notes = veneer_sequence(mouse_vh, vh_donor, "VH")
    vl3, vl_muts, vl_notes = veneer_sequence(mouse_vl, vl_donor, "VL")
    stage3_meta["veneering"]["VH"] = {"donor": vh_best.gene, "mutation_count": len(vh_muts), "mutations": vh_muts, "notes": vh_notes}
    stage3_meta["veneering"]["VL"] = {"donor": vl_best.gene, "mutation_count": len(vl_muts), "mutations": vl_muts, "notes": vl_notes}
    _stage_add("stage3_surface_reshaping_fallback", vh3, vl3, stage3_meta)

    # Structure gating (hard)
    mouse_pdb = structures_dir / "mouse.pdb"
    _model_pdb(mouse_vh, mouse_vl, mouse_pdb)
    mouse_struct = _structure_metrics(mouse_pdb)
    mouse_angle = mouse_struct.get("vh_vl_angle_deg")
    mouse_can = mouse_struct.get("canonical") or {}

    chosen: Optional[Dict[str, Any]] = None
    stage_reports: List[Dict[str, Any]] = []

    for st in stages:
        name = st["name"]
        pdb_path = structures_dir / f"{name}.pdb"
        model_info = _model_pdb(st["vh"], st["vl"], pdb_path)
        struct = _structure_metrics(pdb_path)

        rmsds = _cdr_rmsds_after_framework_align(mouse_pdb, pdb_path)
        rmsd_ok, rmsd_max = _rmsd_pass(rmsds)
        angle_ok, angle_delta = _angle_pass(mouse_angle, struct.get("vh_vl_angle_deg"))
        can_ok, can_cmp = _canonical_pass(mouse_can, struct.get("canonical") or {})

        report = {
            "stage": name,
            "pdb": str(pdb_path),
            "model": model_info,
            "meta": st["meta"],
            "structure": {
                "mouse": mouse_struct,
                "candidate": struct,
                "cdr_rmsd_A": {k: (round(v, 3) if isinstance(v, float) else None) for k, v in rmsds.items()},
                "cdr_rmsd_max_A": (round(rmsd_max, 3) if isinstance(rmsd_max, float) else None),
                "cdr_rmsd_pass": bool(rmsd_ok),
                "angle_delta_deg": (round(angle_delta, 2) if isinstance(angle_delta, (int, float)) else None),
                "angle_pass": bool(angle_ok),
                "canonical_compare": can_cmp,
                "canonical_pass": bool(can_ok),
            },
            "pass": bool(rmsd_ok and angle_ok and can_ok),
        }
        stage_reports.append(report)

        if report["pass"]:
            chosen = report
            break

    if chosen is None:
        chosen = stage_reports[-1]  # last fallback still failed; report it

    # Final report
    payload = {
        "artifact_id": "dog_caninization_auto_v1",
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "project_name": project_name,
        "inputs": {
            "mouse_vh_len": len(mouse_vh),
            "mouse_vl_len": len(mouse_vl),
            "scaffold_source": str(SCAFFOLD_JSON.relative_to(SUITE_ROOT)),
        },
        "selection_policy": {
            "priority": ["grafting", "grafting_vernier_backmut", "surface_reshaping_fallback"],
            "sequence_gates": {"fr_identity_threshold_pct": FR_IDENTITY_THRESHOLD, "cdr_length_gate": "CDR1+CDR2 exact match"},
            "structure_hard_gates": {
                "cdr_rmsd_max_A": CDR_RMSD_MAX_A,
                "vh_vl_angle_delta_deg": ANGLE_DELTA_MAX_DEG,
                "canonical_match": ["H1", "H2", "L1"],
            },
        },
        "plan": plan,
        "vh_candidates_top5": [c.__dict__ for c in vh_cands[:5]],
        "vl_candidates_top5": [c.__dict__ for c in vl_cands[:5]],
        "stages": stage_reports,
        "chosen_stage": chosen["stage"],
        "overall_pass": bool(chosen.get("pass")),
    }

    out_json = out_dir / "report.json"
    _write_json(out_json, payload)

    # FASTA output (chosen sequences)
    chosen_stage_name = payload["chosen_stage"]
    chosen_seq = next((s for s in stages if s["name"] == chosen_stage_name), stages[-1])
    fasta = _fasta(f"{project_name}|mouse|VH", mouse_vh) + _fasta(f"{project_name}|mouse|VL", mouse_vl)
    fasta += _fasta(f"{project_name}|chosen|VH", chosen_seq["vh"]) + _fasta(f"{project_name}|chosen|VL", chosen_seq["vl"])
    _write_text(out_dir / "sequences.fasta", fasta)

    # Markdown report
    md: List[str] = []
    md.append("# Dog caninization — Auto Pipeline (v1)")
    md.append("")
    md.append(f"- Project: `{project_name}`")
    md.append(f"- Built at: `{payload['built_at']}`")
    md.append(f"- Chosen stage: `{payload['chosen_stage']}`")
    md.append(f"- Overall pass (structure-gated): `{payload['overall_pass']}`")
    md.append("")
    md.append("## Selection gates")
    md.append("")
    md.append(f"- FR identity threshold: **{FR_IDENTITY_THRESHOLD}%** (FR-only, Kabat, exclude CDR, FR1–FR3)")
    md.append(f"- Structure gates: **CDR RMSD max ≤ {CDR_RMSD_MAX_A} Å**, **angle Δ ≤ {ANGLE_DELTA_MAX_DEG}°**, canonical match (H1/H2/L1)")
    md.append("")
    md.append("## Plan")
    md.append("")
    md.append(f"- VH qualified scaffold: `{plan['vh']['qualified_scaffold']}`; best: `{plan['vh']['best_scaffold']}`")
    md.append(f"- VL qualified scaffold: `{plan['vl']['qualified_scaffold']}`; best: `{plan['vl']['best_scaffold']}`")
    md.append("")
    md.append("## Stage results (structure gates)")
    md.append("")
    md.append("| stage | pass | cdr_rmsd_max (Å) | angle_delta (°) | canonical_pass |")
    md.append("|---|---:|---:|---:|---:|")
    for st in stage_reports:
        s = st["structure"]
        md.append(
            "| `{stage}` | {p} | {r} | {a} | {c} |".format(
                stage=st["stage"],
                p="✅" if st["pass"] else "❌",
                r=s.get("cdr_rmsd_max_A"),
                a=s.get("angle_delta_deg"),
                c="✅" if s.get("canonical_pass") else "❌",
            )
        )
    md.append("")
    md.append("## Notes")
    md.append("")
    md.append("- If grafting fails, the pipeline automatically falls back to surface reshaping for both chains.")
    md.append("- FR4 tail is taken from the mouse input sequence (best-effort) to keep modeling consistent.")
    _write_text(out_dir / "report.md", "\n".join(md))

    return out_json


def main() -> int:
    ap = argparse.ArgumentParser(description="Dog caninization auto pipeline (structure gated)")
    ap.add_argument("--vh", type=str, default=None, help="Mouse VH amino acid sequence")
    ap.add_argument("--vl", type=str, default=None, help="Mouse VL amino acid sequence")
    ap.add_argument("--name", type=str, default="MyAntibody", help="Project name")
    ap.add_argument("--out-dir", type=str, default=None, help="Output directory (default: projects/<name>/dog_caninization_auto_v1)")
    args = ap.parse_args()

    if not _has_immune_builder():
        print("[FATAL] ImmuneBuilder is required for structure hard-gating, but it is not available.")
        return 2

    if not args.vh or not args.vl:
        # Demo mode
        args.name = args.name or "Pembrolizumab_Demo"
        args.vh = "QVQLVQSGVEVKKPGASVKVSCKASGYTFTNYYMYWVRQAPGQGLEWMGINPSNGGTNFNEKFKNRVTLTTDSSTTTAYMELKSLQFDDTAVYYCARRDYRFDMGFDYWGQGTTVTVSS"
        args.vl = "EIVLTQSPATLSLSPGERATLSCRASKGVSTSGYSYLHWYQQKPGQAPRLLIYLASYLESGVPARFSGSGSGTDFTLTISSLEPEDFAVYYCQHSRDLPLTFGGGTKVEIK"

    out_dir = Path(args.out_dir) if args.out_dir else (SUITE_ROOT / "projects" / args.name / "dog_caninization_auto_v1")
    out_json = run_pipeline(args.vh, args.vl, args.name, out_dir=out_dir)
    print(f"[OK] wrote report: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

