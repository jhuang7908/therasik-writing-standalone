#!/usr/bin/env python3
"""
run_vhvl_v44_pipeline.py — DEPRECATED PARALLEL ENTRY
=====================================================

⚠️  THIS SCRIPT IS DEPRECATED.
    It implements a parallel, independent pipeline that is NOT synchronized
    with `HumanizationEngine` in `core/humanization/engine.py`.

    The unified entry point is:

        from core.humanization import HumanizationEngine
        engine = HumanizationEngine(workflow="vh_vl")
        result = engine.run(mouse_vh="...", mouse_vl="...", project_name="...")

    `HumanizationEngine.run()` includes:
      - Phase 1–5 full checklist
      - Automatic Round 2 + Option B rescue (V4.4.1)
      - All QA gates and audit trail

    This script is retained for reference only and will be removed in a future
    release. DO NOT use it for new projects.

    Historical usage:
      python scripts/run_vhvl_v44_pipeline.py --id fxy_2c2 --vh "QVQL..." --vl "DIQM..."
"""

import warnings
warnings.warn(
    "\n\n"
    "┌─────────────────────────────────────────────────────────────────────┐\n"
    "│  run_vhvl_v44_pipeline.py is DEPRECATED.                            │\n"
    "│                                                                     │\n"
    "│  Use the unified entry point instead:                               │\n"
    "│    from core.humanization import HumanizationEngine                 │\n"
    "│    engine = HumanizationEngine(workflow='vh_vl')                    │\n"
    "│    result = engine.run(mouse_vh=..., mouse_vl=...,                  │\n"
    "│                        project_name=...)                            │\n"
    "│                                                                     │\n"
    "│  This script will be removed in a future release.                   │\n"
    "└─────────────────────────────────────────────────────────────────────┘\n",
    DeprecationWarning,
    stacklevel=2,
)

from __future__ import annotations

print("DEBUG: Importing standard libs")
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

print("DEBUG: Setting up sys.path")
SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))
# ImmuneBuilder  ABARCII； anarci_compat  ARANCII， ImmuneBuilder 
_anarci_compat = SUITE / "reports" / "anarci_compat"
if _anarci_compat.exists():
    sys.path.insert(0, str(_anarci_compat))

print("DEBUG: Importing AA_RE")
AA_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]+$")

print("DEBUG: Importing core modules")
from core.humanization.engine import HumanizationEngine
from core.evaluation.evaluator import AbEvaluator
from core.qa.pipeline_qa import PipelineQA, QAViolation, ChecklistStatus

print("DEBUG: Imports done")

_THERA_GERMLINE_COUNTS: Dict[str, Dict[str, int]] | None = None
_THERA_GERMLINE_REPS: Dict[str, Dict[str, List[str]]] | None = None


def _load_thera_germline_counts() -> Dict[str, Dict[str, int]]:
    """
    Clinical/therapeutic germline usage counts (read-only asset).
    Source: data/thera_sabdab/out/thera_germline_mapping.csv
    """
    global _THERA_GERMLINE_COUNTS
    if _THERA_GERMLINE_COUNTS is not None:
        return _THERA_GERMLINE_COUNTS

    p = SUITE / "data" / "thera_sabdab" / "out" / "thera_germline_mapping.csv"
    if not p.exists():
        _THERA_GERMLINE_COUNTS = {"VH": {}, "VL": {}}
        return _THERA_GERMLINE_COUNTS

    by_chain: Dict[str, Dict[str, int]] = {"VH": {}, "VL": {}}
    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    for ln in lines[1:]:
        parts = [x.strip() for x in ln.split(",")]
        if len(parts) < 3:
            continue
        chain, germ, cnt = parts[0], parts[1], parts[2]
        if chain not in ("VH", "VL"):
            continue
        try:
            by_chain[chain][germ] = int(cnt)
        except Exception:
            continue

    _THERA_GERMLINE_COUNTS = by_chain
    return _THERA_GERMLINE_COUNTS


def _load_thera_germline_reps() -> Dict[str, Dict[str, List[str]]]:
    """
    Representative antibody names for each germline (customer-safe examples).
    Source: data/thera_sabdab/out/thera_representatives_by_germline.yaml
    """
    global _THERA_GERMLINE_REPS
    if _THERA_GERMLINE_REPS is not None:
        return _THERA_GERMLINE_REPS

    p = SUITE / "data" / "thera_sabdab" / "out" / "thera_representatives_by_germline.yaml"
    if not p.exists():
        _THERA_GERMLINE_REPS = {"VH": {}, "VL": {}}
        return _THERA_GERMLINE_REPS

    try:
        import yaml  # type: ignore
    except Exception:
        _THERA_GERMLINE_REPS = {"VH": {}, "VL": {}}
        return _THERA_GERMLINE_REPS

    obj = yaml.safe_load(p.read_text(encoding="utf-8", errors="ignore")) or {}
    vh = obj.get("vh") or {}
    vl = obj.get("vl") or {}

    def _norm(v: Any) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        if not isinstance(v, dict):
            return out
        for germ, items in v.items():
            if not isinstance(germ, str):
                continue
            names: List[str] = []
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict):
                        nm = it.get("INN") or it.get("Name")
                        if nm:
                            names.append(str(nm))
                    elif isinstance(it, str):
                        names.append(it)
            # de-dup while preserving order
            seen = set()
            uniq: List[str] = []
            for x in names:
                if x in seen:
                    continue
                seen.add(x)
                uniq.append(x)
            out[germ] = uniq
        return out

    _THERA_GERMLINE_REPS = {"VH": _norm(vh), "VL": _norm(vl)}
    return _THERA_GERMLINE_REPS


_CANONICAL_CLASS_INDEX: Dict[str, Any] | None = None


def _load_canonical_class_index() -> Dict[str, Any]:
    """
    Build germline → dominant canonical class index from the 458-antibody DB.

    Returns:
        {
          "VL": { "IGKV1-39*01": {"L1-6-?": 41, "L1-10-1": 10, ...}, ... },
          "VH": { "IGHV3-23*01": {"H1-8-?": 35, ...}, ... },
        }

    Loaded once and cached. Data source:
        data/humanization_assay/canonical_vernier_analysis.xlsx
    """
    global _CANONICAL_CLASS_INDEX
    if _CANONICAL_CLASS_INDEX is not None:
        return _CANONICAL_CLASS_INDEX

    xlsx = SUITE / "data" / "humanization_assay" / "canonical_vernier_analysis.xlsx"
    empty: Dict[str, Any] = {"VH": {}, "VL": {}}
    if not xlsx.exists():
        _CANONICAL_CLASS_INDEX = empty
        return empty

    try:
        import pandas as pd  # type: ignore
    except ImportError:
        _CANONICAL_CLASS_INDEX = empty
        return empty

    try:
        df = pd.read_excel(xlsx)
    except Exception:
        _CANONICAL_CLASS_INDEX = empty
        return empty

    idx: Dict[str, Dict[str, Dict[str, int]]] = {"VH": {}, "VL": {}}
    for _, row in df.iterrows():
        # VL canonical classes
        vl_germ = str(row.get("Best_VL_Germline") or "").strip()
        l1_cls = str(row.get("L1_Canonical") or "").strip()
        if vl_germ and l1_cls and vl_germ != "nan" and l1_cls != "nan":
            idx["VL"].setdefault(vl_germ, {})
            idx["VL"][vl_germ][l1_cls] = idx["VL"][vl_germ].get(l1_cls, 0) + 1

        # VH canonical classes
        vh_germ = str(row.get("Best_VH_Germline") or "").strip()
        h1_cls = str(row.get("H1_Canonical") or "").strip()
        h2_cls = str(row.get("H2_Canonical") or "").strip()
        if vh_germ and vh_germ != "nan":
            if h1_cls and h1_cls != "nan":
                idx["VH"].setdefault(vh_germ, {})
                idx["VH"][vh_germ][h1_cls] = idx["VH"][vh_germ].get(h1_cls, 0) + 1
            if h2_cls and h2_cls != "nan":
                key = f"H2:{h2_cls}"
                idx["VH"].setdefault(vh_germ, {})
                idx["VH"][vh_germ][key] = idx["VH"][vh_germ].get(key, 0) + 1

    _CANONICAL_CLASS_INDEX = idx  # type: ignore
    return idx  # type: ignore


def _assign_mouse_canonical_class(
    cdr_len: int,
    chain: str,
    cdr_id: int = 1,
) -> str:
    """
    Assign mouse CDR canonical class by length, using the length→class table
    from config/vh_vl_humanization_v490.json (step_2_1b).

    Fallback table for offline use (mirrors config):
        VL CDR1 length 10 → L1-10-1, length 11 → L1-11-1, etc.
    """
    if chain == "VL" and cdr_id == 1:
        tbl = {3: "L1-3-?", 5: "L1-5-?", 6: "L1-6-?", 7: "L1-7-?",
               8: "L1-8-?", 9: "L1-9-?", 10: "L1-10-1",
               11: "L1-11-1", 12: "L1-12-1"}
        return tbl.get(cdr_len, f"L1-{cdr_len}-?")
    if chain == "VH" and cdr_id == 1:
        return f"H1-{cdr_len}-?"
    if chain == "VH" and cdr_id == 2:
        return f"H2:{f'H2-{cdr_len}-?'}"
    return f"C{cdr_id}-{cdr_len}-?"


def _canonical_class_bonus(
    mouse_class: str, germline: str, chain: str
) -> float:
    """
    V4.4.1 step_2_1b scoring:
      class match + delta=0  → +20 (handled in caller by combining with delta penalty)
      class match            → +20 base (caller subtracts delta penalty separately)
      class mismatch         → −20
      germline not in index  → 0 (no data, neutral)
    """
    idx = _load_canonical_class_index()
    chain_idx = idx.get(chain, {})
    germ_classes = chain_idx.get(germline, {})
    if not germ_classes:
        return 0.0  # no data — neutral (don't penalise)

    total = sum(germ_classes.values())
    top2 = sorted(germ_classes.items(), key=lambda kv: kv[1], reverse=True)[:2]
    top2_classes = {cls for cls, _ in top2}

    if mouse_class in top2_classes:
        return 20.0
    return -20.0


def _clean_seq(seq: str) -> str:
    return re.sub(r"\s+", "", (seq or "").upper().strip())


def _assert_seq(seq: str, label: str) -> None:
    if not seq:
        raise ValueError(f"{label}: empty")
    if not AA_RE.match(seq):
        bad = sorted(set(re.sub(r"[ACDEFGHIKLMNPQRSTVWY]", "", seq)))
        raise ValueError(f"{label}: invalid aa chars: {bad}")
    if not (80 <= len(seq) <= 160):
        raise ValueError(f"{label}: unexpected length {len(seq)} (expected 80–160)")


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_developability_block(
    eval_v1: Dict[str, Any],
    eval_v2: Dict[str, Any] | None,
    eval_v3: Dict[str, Any] | None,
    eval_final: Dict[str, Any],
) -> Dict[str, Any]:
    """Build full developability block: pI per version + metrics_final (GRAVY, II, net_charge, SAP proxies)."""
    def _dev(ev: Dict[str, Any] | None) -> Dict[str, Any]:
        return (ev or {}).get("results", {}).get("developability", {}) or {}

    d1 = _dev(eval_v1)
    d2 = _dev(eval_v2)
    d3 = _dev(eval_v3)
    df = _dev(eval_final)

    pi_v1 = d1.get("pI_fab_estimate")
    pi_v2 = d2.get("pI_fab_estimate") if d2 else None
    pi_v3 = d3.get("pI_fab_estimate") if d3 else None
    gate_min, gate_max = 5.5, 9.5

    block: Dict[str, Any] = {
        "pI": {
            "v1": pi_v1,
            "v2": pi_v2,
            "v3": pi_v3,
            "gate_min": gate_min,
            "gate_max": gate_max,
            "v1_pass": bool(gate_min <= float(pi_v1) <= gate_max) if isinstance(pi_v1, (int, float)) else None,
            "v2_pass": bool(gate_min <= float(pi_v2) <= gate_max) if isinstance(pi_v2, (int, float)) else None,
            "v3_pass": bool(gate_min <= float(pi_v3) <= gate_max) if isinstance(pi_v3, (int, float)) else None,
        },
        "liabilities": (eval_final.get("results", {}).get("cdr_scan", {}) or {}).get("liabilities", []),
    }
    # CMC/developability metrics for final version (for report display)
    metrics_keys = ("GRAVY", "instability_index", "net_charge_pH7", "hydro_patch_max9", "charge_patch_max7")
    metrics_final = {k: df.get(k) for k in metrics_keys if df.get(k) is not None}
    if metrics_final:
        block["metrics_final"] = metrics_final
    return block


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _kabat_numbering(seq: str) -> Dict[Tuple[int, str], str]:
    from core.humanization.kabat_utils import get_kabat_numbering  # noqa: PLC0415
    return get_kabat_numbering(seq)


def _span(kd: Dict[Tuple[int, str], str], lo: int, hi: int) -> str:
    from core.humanization.kabat_utils import sorted_keys  # noqa: PLC0415
    return "".join(kd[k] for k in sorted_keys(kd) if lo <= k[0] <= hi)


def _cdr_lengths(kd: Dict[Tuple[int, str], str], chain: str) -> Dict[str, int]:
    from core.humanization.kabat_utils import CDR_RANGES_VH, CDR_RANGES_VL  # noqa: PLC0415
    ranges = CDR_RANGES_VH if chain == "VH" else CDR_RANGES_VL
    names = ["CDR1", "CDR2", "CDR3"]
    return {n: len(_span(kd, lo, hi)) for n, (lo, hi) in zip(names, ranges)}


def _fr_identity(mouse_kd: Dict[Tuple[int, str], str], germ_kd: Dict[Tuple[int, str], str], chain: str) -> float:
    if chain == "VH":
        ranges = [(1, 25), (36, 49), (66, 94)]
    else:
        ranges = [(1, 23), (35, 49), (57, 88)]
    m = "".join(_span(mouse_kd, lo, hi) for lo, hi in ranges)
    g = "".join(_span(germ_kd, lo, hi) for lo, hi in ranges)
    n = min(len(m), len(g))
    if n == 0:
        return 0.0
    matches = sum(1 for i in range(n) if m[i] == g[i])
    return round(100.0 * matches / n, 1)


def _vernier_similarity(mouse_kd: Dict[Tuple[int, str], str], germ_kd: Dict[Tuple[int, str], str], chain: str) -> float:
    vh_pos = [2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94]
    vl_pos = [2, 4, 36, 46, 49, 69, 71, 98]
    pos = vh_pos if chain == "VH" else vl_pos
    n = 0
    m = 0
    for p in pos:
        ma = mouse_kd.get((p, ""))
        ga = germ_kd.get((p, ""))
        if not ma or not ga:
            continue
        n += 1
        if ma == ga:
            m += 1
    return round(100.0 * m / n, 1) if n else 0.0


def _aa_class(aa: str) -> str:
    aa = (aa or "").upper()
    if aa in ("G", "P"):
        return "special"
    if aa in ("D", "E"):
        return "neg"
    if aa in ("K", "R", "H"):
        return "pos"
    if aa in ("S", "T", "N", "Q", "C"):
        return "polar"
    if aa in ("A", "V", "I", "L", "M", "F", "W", "Y"):
        return "hydrophobic"
    return "other"


def _imgt_in_cdr_union(cfg: Dict[str, Any], chain: str, imgt_pos: int) -> bool:
    """
    V4.4 CDR union ranges are defined in IMGT coordinates.
    """
    cu = cfg.get("cdr_union_ranges") or {}
    if not isinstance(cu, dict):
        return False
    c = cu.get(chain) or {}
    if not isinstance(c, dict):
        return False
    for k, default in (
        ("CDR1_union", [26, 38] if chain == "VH" else [27, 38]),
        ("CDR2_union", [55, 65] if chain == "VH" else [56, 65]),
        ("CDR3_union", [105, 117]),
    ):
        r = c.get(k, default)
        if isinstance(r, list) and len(r) == 2:
            lo, hi = int(r[0]), int(r[1])
            if lo <= int(imgt_pos) <= hi:
                return True
    return False


def _phase4_vernier_decisions(
    cfg: Dict[str, Any],
    v1_vh_seq: str,
    v1_vl_seq: str,
    mouse_vh_kd: Dict[Tuple[int, str], str],
    mouse_vl_kd: Dict[Tuple[int, str], str],
    germ_vh_kd: Dict[Tuple[int, str], str],
    germ_vl_kd: Dict[Tuple[int, str], str],
    sasa: Dict[str, float],
    contact: Dict[str, float],
    dist: Dict[str, float],
) -> Tuple[List[Dict[str, Any]], Dict[int, str], Dict[int, str]]:
    """
    Phase 4: decide Vernier back-mutations using V4.4 thresholds + HC/SC rules.

    Output:
    - decisions: 22 rows (VH14 + VL8), each includes in_cdr_union and decision label
    - bm_map_vh / bm_map_vl: {kabat_int_pos: mouse_aa} for positions requiring BACK_MUTATE
    """
    thr = {}
    try:
        thr = (cfg.get("step_2_3_vernier_score") or {}).get("thresholds") or {}
    except Exception:
        thr = {}
    if not isinstance(thr, dict):
        thr = {}
    SASA_keep = float(thr.get("SASA_buried_must_keep", 20))
    DIST_keep = float(thr.get("cdr_contact_distance_keep", 4.5))

    tier1_vh = {71, 94}
    tier1_vl = {71, 49}
    try:
        br = cfg.get("backmutation_rules") or {}
        hcs = br.get("hard_constraints") or []
        if isinstance(hcs, list):
            for it in hcs:
                if not isinstance(it, dict):
                    continue
                if it.get("id") == "HC3":
                    pv = it.get("positions_VH")
                    pl = it.get("positions_VL")
                    if isinstance(pv, list) and pv:
                        tier1_vh = {int(x) for x in pv if str(x).isdigit()}
                    if isinstance(pl, list) and pl:
                        tier1_vl = {int(x) for x in pl if str(x).isdigit()}
                    break
    except Exception as _e:
        print(f"[WARN] Vernier tier1 config parse failed ({type(_e).__name__}: {_e}); "
              f"using built-in defaults tier1_vh={tier1_vh} tier1_vl={tier1_vl}")

    vh_pos = [2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94]
    vl_pos = [2, 4, 36, 46, 49, 69, 71, 98]

    decisions: List[Dict[str, Any]] = []
    bm_vh: Dict[int, str] = {}
    bm_vl: Dict[int, str] = {}

    # Map Kabat base positions -> IMGT positions for overlap flag
    kab2imgt_vh: Dict[int, int] = {}
    kab2imgt_vl: Dict[int, int] = {}
    try:
        from core.numbering.dual_scheme import compute_dual_scheme_numbering  # noqa: PLC0415

        dvh = compute_dual_scheme_numbering(v1_vh_seq, chain_label="VH")
        for i in range(len(dvh.sequence)):
            if dvh.kabat[i].ins == "":
                kab2imgt_vh.setdefault(int(dvh.kabat[i].pos), int(dvh.imgt[i].pos))
        dvl = compute_dual_scheme_numbering(v1_vl_seq, chain_label="VL")
        for i in range(len(dvl.sequence)):
            if dvl.kabat[i].ins == "":
                kab2imgt_vl.setdefault(int(dvl.kabat[i].pos), int(dvl.imgt[i].pos))
    except Exception:
        kab2imgt_vh = {}
        kab2imgt_vl = {}

    def decide(chain: str, p: int, m_aa: str, h_aa: str) -> Tuple[str, List[str]]:
        key = f"{chain}_{p}"
        imgt_pos = (kab2imgt_vh.get(p) if chain == "VH" else kab2imgt_vl.get(p))
        in_u = _imgt_in_cdr_union(cfg, chain, int(imgt_pos)) if imgt_pos is not None else False
        if in_u:
            return "CDR_GRAFT", ["in_cdr_union"]
        if not m_aa or not h_aa or m_aa in ("-", "—") or h_aa in ("-", "—"):
            return "HUMAN", ["missing_residue"]
        if m_aa == h_aa:
            return "HUMAN", ["MATCH"]

        hits: List[str] = []
        # HC1: keep mouse if mouse is G/P
        if m_aa in ("G", "P"):
            hits.append("HC1")
        # HC1-inv: back-mutate if human introduces Pro
        if h_aa == "P" and m_aa != "P":
            hits.append("HC1_inv")
        # HC2: conservative handling of Cys at Vernier
        if "C" in (m_aa, h_aa):
            hits.append("HC2")
        # HC3: Tier1 default keep (needs evidence to override; we keep by default)
        if chain == "VH" and p in tier1_vh:
            hits.append("HC3")
        if chain == "VL" and p in tier1_vl:
            hits.append("HC3")
        # HC4: buried SASA
        s = sasa.get(key)
        if isinstance(s, (int, float)) and float(s) < SASA_keep:
            hits.append("HC4")
        # HC5: CDR proximity (skip dist==0, which indicates a CDR residue)
        d = dist.get(key)
        if isinstance(d, (int, float)) and float(d) != 0.0 and float(d) < DIST_keep:
            hits.append("HC5")

        if hits:
            return "BACK_MUTATE", hits

        # same-class differences still pass through structural evaluation; if no hard hits, accept human.
        return "HUMAN", ["ACCEPT_HUMAN_no_hard_hits"]

    # First pass decisions
    for p in vh_pos:
        m_aa = mouse_vh_kd.get((p, ""), "-")
        h_aa = germ_vh_kd.get((p, ""), "-")
        dec, hits = decide("VH", p, m_aa, h_aa)
        key = f"VH_{p}"
        imgt_pos = kab2imgt_vh.get(p)
        decisions.append(
            {
                "position": key,
                "kabat_pos": p,
                "imgt_pos": imgt_pos,
                "in_cdr_union": bool(_imgt_in_cdr_union(cfg, "VH", int(imgt_pos))) if imgt_pos is not None else False,
                "mouse_aa": m_aa,
                "human_aa": h_aa,
                "decision": dec,
                "rule_hits": hits,
                "sasa": float(sasa.get(key)) if key in sasa and sasa.get(key) is not None else None,
                "contact": float(contact.get(key)) if key in contact and contact.get(key) is not None else None,
                "dist_to_cdr": float(dist.get(key)) if key in dist and dist.get(key) is not None else None,
                "same_class": _aa_class(m_aa) == _aa_class(h_aa) and m_aa != h_aa,
            }
        )
        if dec == "BACK_MUTATE" and m_aa != "-" and not (imgt_pos is not None and _imgt_in_cdr_union(cfg, "VH", int(imgt_pos))):
            bm_vh[p] = m_aa

    for p in vl_pos:
        m_aa = mouse_vl_kd.get((p, ""), "-")
        h_aa = germ_vl_kd.get((p, ""), "-")
        dec, hits = decide("VL", p, m_aa, h_aa)
        key = f"VL_{p}"
        imgt_pos = kab2imgt_vl.get(p)
        decisions.append(
            {
                "position": key,
                "kabat_pos": p,
                "imgt_pos": imgt_pos,
                "in_cdr_union": bool(_imgt_in_cdr_union(cfg, "VL", int(imgt_pos))) if imgt_pos is not None else False,
                "mouse_aa": m_aa,
                "human_aa": h_aa,
                "decision": dec,
                "rule_hits": hits,
                "sasa": float(sasa.get(key)) if key in sasa and sasa.get(key) is not None else None,
                "contact": float(contact.get(key)) if key in contact and contact.get(key) is not None else None,
                "dist_to_cdr": float(dist.get(key)) if key in dist and dist.get(key) is not None else None,
                "same_class": _aa_class(m_aa) == _aa_class(h_aa) and m_aa != h_aa,
            }
        )
        if dec == "BACK_MUTATE" and m_aa != "-" and not (imgt_pos is not None and _imgt_in_cdr_union(cfg, "VL", int(imgt_pos))):
            bm_vl[p] = m_aa

    # SC3 coupling: if VH71 is kept mouse, also keep VH73/VH78 when they differ
    if 71 in bm_vh:
        for p in (73, 78):
            imgt_pos = kab2imgt_vh.get(p)
            if p not in bm_vh and not (imgt_pos is not None and _imgt_in_cdr_union(cfg, "VH", int(imgt_pos))):
                m_aa = mouse_vh_kd.get((p, ""), "-")
                h_aa = germ_vh_kd.get((p, ""), "-")
                if m_aa not in ("-", "—") and h_aa not in ("-", "—") and m_aa != h_aa:
                    bm_vh[p] = m_aa
                    for row in decisions:
                        if row.get("position") == f"VH_{p}":
                            row["decision"] = "BACK_MUTATE"
                            row["rule_hits"] = list(dict.fromkeys((row.get("rule_hits") or []) + ["SC3"]))

    return decisions, bm_vh, bm_vl


def _load_pairing_full() -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Load full pairing set from vh_vl_pairing_matrix.csv for pairing-as-final-reference."""
    p = SUITE / "data" / "humanization_assay" / "vh_vl_pairing_matrix.csv"
    full: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if not p.exists():
        return full
    try:
        lines = p.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) < 2:
            return full
        vl_cols = [c.strip().split("*")[0] for c in lines[0].split(",")[1:]]
        for ln in lines[1:]:
            parts = [x.strip() for x in ln.split(",")]
            if not parts:
                continue
            vh_norm = parts[0].split("*")[0].strip()
            for j, vl_raw in enumerate(vl_cols):
                if j + 1 >= len(parts):
                    break
                try:
                    cnt = int(parts[j + 1])
                except (ValueError, IndexError):
                    continue
                if cnt <= 0:
                    continue
                vl_norm = vl_raw.strip() if isinstance(vl_raw, str) else str(vl_raw)
                full[(vh_norm, vl_norm)] = {"count": cnt}
    except Exception:
        pass
    return full


_PAIRING_FULL_CACHE: Dict[Tuple[str, str], Dict[str, Any]] | None = None


def _lookup_pairing(vh_gene: str, vl_gene: str) -> Dict[str, Any] | None:
    """Check if VH+VL pair exists in clinical pairing DB. Used as final reference in germline selection."""
    global _PAIRING_FULL_CACHE
    if _PAIRING_FULL_CACHE is None:
        _PAIRING_FULL_CACHE = _load_pairing_full()
    vh_norm = (vh_gene or "").split("*")[0].strip()
    vl_norm = (vl_gene or "").split("*")[0].strip()
    return _PAIRING_FULL_CACHE.get((vh_norm, vl_norm))


def _select_germline(mouse_seq: str, chain: str, top_k: int = 5, set_selected: bool = True) -> List[Dict[str, Any]]:
    """
    V4.4 performance rule (HARD): NEVER number hundreds of germlines per project.
    We only compute Kabat numbering for the *project input* and then query a
    precomputed Kabat cache for human germlines.

    Build cache once:
      python scripts/build_germline_kabat_cache.py
    """
    mouse_kd = _kabat_numbering(mouse_seq)
    mouse_cdr = _cdr_lengths(mouse_kd, chain)

    if chain == "VH":
        cache_path = SUITE / "data" / "germlines" / "human_ig_aa" / "_cache" / "IGHV_kabat_cache.json"
        vernier_pos = [2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94]
    else:
        cache_path = SUITE / "data" / "germlines" / "human_ig_aa" / "_cache" / "IGKV_kabat_cache.json"
        vernier_pos = [2, 4, 36, 46, 49, 69, 71, 98]

    if not cache_path.exists():
        raise RuntimeError(
            f"Missing germline Kabat cache: {cache_path.relative_to(SUITE)}. "
            "Run: python scripts/build_germline_kabat_cache.py"
        )

    cache = _load_json(cache_path)
    genes = (cache.get("genes") or {}) if isinstance(cache, dict) else {}

    # Principle-1 HARD GATE: germline must have clinical usage evidence
    clinical_counts = _load_thera_germline_counts().get(chain, {})
    clinical_reps = _load_thera_germline_reps().get(chain, {})

    # Precompute mouse features used for ranking
    if chain == "VH":
        fr_ranges = [(1, 25), (36, 49), (66, 94)]
    else:
        fr_ranges = [(1, 23), (35, 49), (57, 88)]
    mouse_fr = "".join(_span(mouse_kd, lo, hi) for lo, hi in fr_ranges)
    mouse_vernier = {str(p): (mouse_kd.get((p, "")) or "") for p in vernier_pos}

    out: List[Dict[str, Any]] = []
    for gene, feat in genes.items():
        # Clinical evidence filter: if not in the clinical mapping, do NOT allow
        if gene not in clinical_counts:
            continue
        if not isinstance(feat, dict):
            continue
        g_cdr = feat.get("kabat_cdr_lengths") or {}
        if not isinstance(g_cdr, dict):
            continue

        # ── V4.4.1 step_2_1 + step_2_1b: CDR length pre-filter + canonical class gate ──
        # Step 2.1: CDR length tolerance ±2 (hard block: delta>2 never accepted).
        # Step 2.1b: Canonical class is the PRIMARY selection criterion.
        #   Scoring (applied on top of Vernier + FR identity):
        #     class match + delta=0  → +20 pts
        #     class match + delta=1  → +15 pts
        #     class match + delta=2  → +10 pts
        #     class mismatch         → −20 pts (regardless of delta)
        # VH: CDR1 + CDR2 gates. VL: CDR1 only (CDR2 always 7 in kappa).
        CDR_LEN_HARD_MAX = 2  # delta > 2 is always rejected
        if chain == "VH":
            c1_delta = abs(int(g_cdr.get("CDR1") or -1) - mouse_cdr["CDR1"])
            c2_delta = abs(int(g_cdr.get("CDR2") or -1) - mouse_cdr["CDR2"])
            if c1_delta > CDR_LEN_HARD_MAX or c2_delta > CDR_LEN_HARD_MAX:
                continue
            cdr1_ok = (c1_delta == 0)
            cdr2_ok = (c2_delta == 0)
        else:
            c1_delta = abs(int(g_cdr.get("CDR1") or -1) - mouse_cdr["CDR1"])
            if c1_delta > CDR_LEN_HARD_MAX:
                continue
            cdr1_ok = (c1_delta == 0)
            cdr2_ok = True

        g_fr = str(feat.get("fr_concat") or "")
        n = min(len(mouse_fr), len(g_fr))
        fr_id = 0.0
        if n:
            fr_id = round(100.0 * sum(1 for i in range(n) if mouse_fr[i] == g_fr[i]) / n, 1)

        g_ver = feat.get("vernier_residues") or {}
        if not isinstance(g_ver, dict):
            g_ver = {}
        n2 = 0
        m2 = 0
        for p in vernier_pos:
            ma = mouse_vernier.get(str(p)) or ""
            ga = str(g_ver.get(str(p)) or "")
            if not ma or not ga:
                continue
            n2 += 1
            if ma == ga:
                m2 += 1
        vernier = round(100.0 * m2 / n2, 1) if n2 else 0.0

        # ── Canonical class scoring (step_2_1b) ──────────────────────────
        if chain == "VL":
            mouse_cdr1_class = _assign_mouse_canonical_class(mouse_cdr["CDR1"], "VL", 1)
            cc_bonus = _canonical_class_bonus(mouse_cdr1_class, gene, "VL")
            # Graduated bonus: reduce by 5 pts per delta unit beyond 0
            if cc_bonus > 0 and c1_delta > 0:
                cc_bonus = max(10.0, cc_bonus - 5.0 * c1_delta)
        else:
            mouse_h1_class = _assign_mouse_canonical_class(mouse_cdr["CDR1"], "VH", 1)
            mouse_h2_class = f"H2:{_assign_mouse_canonical_class(mouse_cdr['CDR2'], 'VH', 2).replace('H2:', '')}"
            cc_h1 = _canonical_class_bonus(mouse_h1_class, gene, "VH")
            cc_h2 = _canonical_class_bonus(mouse_h2_class, gene, "VH")
            cc_bonus = round((cc_h1 + cc_h2) / 2.0, 1)
            if cc_bonus > 0:
                delta_total = c1_delta + c2_delta
                cc_bonus = max(10.0, cc_bonus - 5.0 * delta_total)

        # CDR length mismatch penalty (separate from canonical class bonus):
        # each delta unit subtracts 5 pts to maintain preference for exact length.
        if chain == "VH":
            cdr_len_penalty = 5.0 * (c1_delta + c2_delta)
        else:
            cdr_len_penalty = 5.0 * c1_delta

        score = round(0.6 * vernier + 0.4 * fr_id + cc_bonus - cdr_len_penalty, 2)

        entry: Dict[str, Any] = {
            "gene": gene,
            "fr_identity_pct": fr_id,
            "vernier_similarity_pct": vernier,
            "cdr1_length_match": cdr1_ok,
            "cdr2_length_match": cdr2_ok,
            "canonical_class_bonus": cc_bonus,
            "composite_score": score,
            "selected": False,
            # Customer-safe examples (names only). Counts are internal only.
            "clinical_precedent": (clinical_reps.get(gene) or [])[:5],
            "clinical_usage_count": int(clinical_counts.get(gene) or 0),
        }
        if chain == "VL":
            entry["mouse_cdr1_canonical_class"] = mouse_cdr1_class
        else:
            entry["mouse_h1_canonical_class"] = mouse_h1_class
            entry["mouse_h2_canonical_class"] = mouse_h2_class
        if not cdr1_ok or not cdr2_ok:
            entry["cdr_length_note"] = (
                "CDR（±2），CDRCDR。"
            )
        out.append(entry)

    out.sort(key=lambda x: (x.get("composite_score", 0.0), x.get("vernier_similarity_pct", 0.0)), reverse=True)
    if set_selected and out:
        out[0]["selected"] = True
        out[0]["selection_reason"] = "（）"
    for it in out[1:top_k]:
        it["rejection_reason"] = "（）"
    return out[:top_k]


def _select_best_pair_with_pairing_reference(
    vh_cand: List[Dict[str, Any]],
    vl_cand: List[Dict[str, Any]],
    pair_top_k: int = 3,
) -> Tuple[str, str]:
    """
    Select best VH+VL pair. Primary: composite score; final reference: clinical pairing existence.
    Germline ；，。
    """
    vh_top = [x for x in vh_cand[:pair_top_k] if x.get("gene")]
    vl_top = [x for x in vl_cand[:pair_top_k] if x.get("gene")]
    if not vh_top or not vl_top:
        vh_top = vh_cand[:1]
        vl_top = vl_cand[:1]
    best_score = -1.0
    best_vh = vh_top[0]["gene"]
    best_vl = vl_top[0]["gene"]
    best_pair = (best_vh, best_vl)
    PAIRING_BONUS = 5.0  # When pair exists in clinical DB, add to composite
    for vh in vh_top:
        for vl in vl_top:
            vh_g = vh.get("gene", "")
            vl_g = vl.get("gene", "")
            sc = (vh.get("composite_score") or 0.0) + (vl.get("composite_score") or 0.0)
            pair_row = _lookup_pairing(vh_g, vl_g)
            if pair_row:
                sc += PAIRING_BONUS
            if sc > best_score:
                best_score = sc
                best_pair = (vh_g, vl_g)
    vh_gene, vl_gene = best_pair
    pair_row = _lookup_pairing(vh_gene, vl_gene)
    sel_reason = (
        "，（）"
        if pair_row
        else "（）"
    )
    for x in vh_cand:
        x["selected"] = x.get("gene") == vh_gene
        if x["selected"]:
            x["selection_reason"] = sel_reason
        elif "rejection_reason" not in x:
            x["rejection_reason"] = "（）"
    for x in vl_cand:
        x["selected"] = x.get("gene") == vl_gene
        if x["selected"]:
            x["selection_reason"] = sel_reason
        elif "rejection_reason" not in x:
            x["rejection_reason"] = "（）"
    return vh_gene, vl_gene


def _germ_seq(gene: str, chain: str) -> str:
    if chain == "VH":
        db_path = SUITE / "data" / "germlines" / "human_ig_aa" / "IGHV_aa.json"
    else:
        db_path = SUITE / "data" / "germlines" / "human_ig_aa" / "IGKV_aa.json"
    db = _load_json(db_path)
    for e in (db.get("entries") or []):
        if (e.get("id") or e.get("name") or e.get("gene")) == gene:
            return _clean_seq(str(e.get("sequence_aa") or e.get("sequence") or ""))
    raise KeyError(f"germline not found: {gene}")


def _run_immunebuilder_via_script(vh_seq: str, vl_seq: str, out_path: Path) -> Tuple[bool, str]:
    """
     predict_one_immunebuilder.py  ABodyBuilder2，
    ImmuneBuilder 。 (,  stderr )。
    """
    script = SUITE / "scripts" / "predict_one_immunebuilder.py"
    if not script.exists():
        return False, ""
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"out_path": str(out_path), "H": vh_seq, "L": vl_seq}
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f, ensure_ascii=False)
            payload_path = f.name
        #  IMMUNEBUILDER_PYTHON，（“ ImmuneBuilder”）
        python_exe = os.environ.get("IMMUNEBUILDER_PYTHON") or sys.executable
        try:
            r = subprocess.run(
                [python_exe, str(script), "--json", payload_path],
                cwd=str(SUITE),
                capture_output=True,
                text=True,
                timeout=600,
            )
            if r.returncode == 0 and out_path.exists():
                return True, ""
            return False, (r.stderr or r.stdout or "").strip() or f"exit code {r.returncode}"
        finally:
            try:
                Path(payload_path).unlink(missing_ok=True)
            except Exception:
                pass
    except subprocess.TimeoutExpired:
        return False, " (600s)"
    except Exception as e:
        return False, str(e)


def _assemble_union_chain(
    chain: str,
    mouse_seq: str,
    germ_seq: str,
    bm_map: Dict[int, str],
    cfg: Dict[str, Any],
    fr4: str,
) -> str:
    """
    Assemble a humanized chain with CDR-Union grafting + optional back-mutations.

    IMPORTANT: Mouse CDR blocks MUST be cut by **Kabat** CDR ranges (CDR_RANGES_VH/VL).
    Using IMGT span [26,38] for VH CDR1 omits Kabat 34–35 when they map to IMGT ≥39
    (e.g. muMAb4D5 CDR1 ends …IH), which incorrectly splices germline FR2 (…MS…) and
    corrupts CDR1 — fixed 2026-03-26.
    """
    print(f"DEBUG: _assemble_union_chain called for {chain}")
    from core.numbering.dual_scheme import compute_dual_scheme_numbering  # noqa: PLC0415
    from core.humanization.kabat_utils import (  # noqa: PLC0415
        CDR_RANGES_VH,
        CDR_RANGES_VL,
        cdr_span,
        get_kabat_numbering,
        verify_cdr_substrings_mouse_in_assembled_v,
    )

    d_germ = compute_dual_scheme_numbering(germ_seq, chain_label=chain)
    kd_mouse = get_kabat_numbering(mouse_seq)

    rng = CDR_RANGES_VH if chain == "VH" else CDR_RANGES_VL
    (k1_lo, k1_hi), (k2_lo, k2_hi), (k3_lo, k3_hi) = rng[0], rng[1], rng[2]

    # Full mouse CDR strings (Kabat), then list() for out.extend
    mouse_cdr1 = list(cdr_span(kd_mouse, k1_lo, k1_hi))
    mouse_cdr2 = list(cdr_span(kd_mouse, k2_lo, k2_hi))
    mouse_cdr3 = list(cdr_span(kd_mouse, k3_lo, k3_hi))

    max_kabat_end = 102 if chain == "VH" else 97
    out: List[str] = []
    in_cdr_block: Optional[int] = None  # tracks which CDR block we have entered

    # 1. Process germline FR1 / CDR1 / FR2 / CDR2 / FR3 — CDR3 appended from mouse below
    #
    # BUG FIX (2026-03-27): The original `imgt_pos >= 105` cutoff was intended to stop
    # before IMGT CDR3 (IMGT 105+), but in IGHV3-23*01 (and similar germlines) the last
    # two FR3 residues at Kabat 93 and 94 map to IMGT 105 and 117 respectively — causing
    # them to be silently dropped, producing a VH 2 aa shorter than the mouse parent.
    #
    # Fix: use Kabat position as the primary boundary (kab_pos <= k3_lo - 1 = 94 for VH).
    # The IMGT cutoff was redundant given max_kabat_end already limits the range.
    for i in range(len(d_germ.sequence)):
        kab_pos = int(d_germ.kabat[i].pos)

        if kab_pos > max_kabat_end:
            continue
        # Germline V gene has no CDR3 — skip Kabat CDR3 window here
        if k3_lo <= kab_pos <= k3_hi:
            continue

        aa = d_germ.sequence[i]

        if k1_lo <= kab_pos <= k1_hi:
            if in_cdr_block != 1:
                out.extend(mouse_cdr1)
                in_cdr_block = 1
        elif k2_lo <= kab_pos <= k2_hi:
            if in_cdr_block != 2:
                out.extend(mouse_cdr2)
                in_cdr_block = 2
        else:
            in_cdr_block = None
            if kab_pos in bm_map:
                aa = bm_map[kab_pos]
            out.append(aa)

    out.extend(mouse_cdr3)

    v_region = "".join(out)
    seq = v_region + fr4

    # Substring check via kabat_utils (not verify_cdr_preservation on re-numbered chimera).
    sub_errs = verify_cdr_substrings_mouse_in_assembled_v(mouse_seq, v_region, chain)
    if sub_errs:
        raise ValueError(f"{chain} CDR preservation FAIL: " + "; ".join(sub_errs))

    # ─────────────────────────────────────────────────────────────────────────────
    # INVARIANT CHECK (added 2026-03-27 to prevent FR truncation bug):
    # The assembled V region (FR1+CDR1+FR2+CDR2+FR3+CDR3) MUST preserve the length
    # of the mouse parent sequence. A discrepancy indicates frame region loss.
    # ─────────────────────────────────────────────────────────────────────────────
    if len(v_region) < len(mouse_seq):
        # Extract FR regions from mouse for diagnostic output
        from core.humanization.kabat_utils import CDR_RANGES_VH, CDR_RANGES_VL, cdr_span
        rng = CDR_RANGES_VH if chain == "VH" else CDR_RANGES_VL
        mouse_fr = "".join(
            mouse_seq[i] for i in range(len(mouse_seq))
            if not (rng[0][0] <= (i+1) <= rng[0][1] or
                    rng[1][0] <= (i+1) <= rng[1][1] or
                    rng[2][0] <= (i+1) <= rng[2][1])
        )
        raise ValueError(
            f"{chain} V region length INVARIANT VIOLATION:\n"
            f"  mouse_seq length: {len(mouse_seq)} aa\n"
            f"  assembled v_region: {len(v_region)} aa (LOSS OF {len(mouse_seq) - len(v_region)} aa)\n"
            f"  Likely cause: germline FR truncation in assembly loop (e.g., premature IMGT cutoff).\n"
            f"  See: scripts/run_vhvl_v44_pipeline.py _assemble_union_chain() line ~934"
        )

    return seq


def _assemble_v1(mouse_vh: str, mouse_vl: str, vh_gene: str, vl_gene: str, cfg: Dict[str, Any]) -> Tuple[str, str]:
    """Assemble v1 = germline framework + CDR grafting (CDR Union ranges)."""

    fr4 = cfg.get("fr4_sources") or {}
    fr4_vh = str(fr4.get("VH_JH4_FR4") or "WGQGTLVTVSS")
    fr4_vl = str(fr4.get("VL_JK4_FR4") or "FGGGTKLEIK")

    v1_vh = _assemble_union_chain("VH", mouse_vh, _germ_seq(vh_gene, "VH"), bm_map={}, cfg=cfg, fr4=fr4_vh)
    v1_vl = _assemble_union_chain("VL", mouse_vl, _germ_seq(vl_gene, "VL"), bm_map={}, cfg=cfg, fr4=fr4_vl)
    return v1_vh, v1_vl


def _assemble_v2(
    mouse_vh: str,
    mouse_vl: str,
    vh_gene: str,
    vl_gene: str,
    bm_vh: Dict[int, str],
    bm_vl: Dict[int, str],
    cfg: Dict[str, Any],
) -> Tuple[str, str]:
    """Assemble v2 = germline framework + CDR-union graft + Vernier back-mutations."""
    fr4 = cfg.get("fr4_sources") or {}
    fr4_vh = str(fr4.get("VH_JH4_FR4") or "WGQGTLVTVSS")
    fr4_vl = str(fr4.get("VL_JK4_FR4") or "FGGGTKLEIK")
    v2_vh = _assemble_union_chain("VH", mouse_vh, _germ_seq(vh_gene, "VH"), bm_map=bm_vh, cfg=cfg, fr4=fr4_vh)
    v2_vl = _assemble_union_chain("VL", mouse_vl, _germ_seq(vl_gene, "VL"), bm_map=bm_vl, cfg=cfg, fr4=fr4_vl)
    return v2_vh, v2_vl


def _annotation(seq: str, chain: str, fr_source: str) -> Dict[str, Any]:
    kd = _kabat_numbering(seq)
    if chain == "VH":
        spans = [("FR1", 1, 25), ("CDR1", 26, 35), ("FR2", 36, 49), ("CDR2", 50, 65), ("FR3", 66, 94), ("CDR3", 95, 102), ("FR4", 103, 113)]
    else:
        spans = [("FR1", 1, 23), ("CDR1", 24, 34), ("FR2", 35, 49), ("CDR2", 50, 56), ("FR3", 57, 88), ("CDR3", 89, 97), ("FR4", 98, 107)]
    rows = [{"region": n, "kabat": f"{lo}-{hi}", "seq": _span(kd, lo, hi)} for n, lo, hi in spans]
    for r in rows:
        r["source"] = fr_source if r["region"].startswith("FR") else "** CDR**"
    return {
        "sequence": seq,
        "annotation": rows,
        "cdr_lengths": _cdr_lengths(kd, chain),
    }


def main() -> int:
    print("DEBUG: main started")
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--vh", required=True)
    ap.add_argument("--vl", required=True)
    ap.add_argument("--project-name", default=None)
    ap.add_argument("--force-germline-vh", help="Force specific VH germline (e.g. IGHV3-23*01)", default=None)
    ap.add_argument("--force-germline-vl", help="Force specific VL germline (e.g. IGKV1-39*01)", default=None)
    ap.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip verify_vhvl_v44_project at end (batch/compare runs; run verify manually before delivery).",
    )
    args = ap.parse_args()

    ab_id = args.id.strip().lower()
    mouse_vh = _clean_seq(args.vh)
    mouse_vl = _clean_seq(args.vl)
    _assert_seq(mouse_vh, "mouse_VH")
    _assert_seq(mouse_vl, "mouse_VL")

    cfg = _load_json(SUITE / "config" / "vh_vl_humanization_v490.json")

    project_dir = SUITE / "projects" / f"{ab_id}_Redesign"
    reports_dir = project_dir / "reports"
    sequences_dir = project_dir / "sequences"
    structures_dir = project_dir / "structures"
    internal_dir = project_dir / "internal"
    for d in (reports_dir, sequences_dir, structures_dir, internal_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Phase 1: Sequence QA + dual-scheme numbering QA
    from core.qa.pipeline_qa import PipelineQA, QAViolation  # noqa: PLC0415
    qa = PipelineQA(project=ab_id, step="vhvl_v44_pipeline")
    ok_vh = qa.check_sequence("vh", mouse_vh, chain="VH", label="mouse VH")
    ok_vl = qa.check_sequence("vl", mouse_vl, chain="VL", label="mouse VL")
    ok_dn1 = qa.check_dual_scheme_numbering("vh_dual", mouse_vh, chain="VH")
    ok_dn2 = qa.check_dual_scheme_numbering("vl_dual", mouse_vl, chain="VL")
    rep = qa.finalize(output_seq=mouse_vh + "|" + mouse_vl)
    if rep.n_fail or not (ok_vh and ok_vl and ok_dn1 and ok_dn2):
        raise QAViolation("Input/numbering hard gate failed")

    # Phase 2: Germline selection (internal candidate list)
    # Pairing existence in clinical DB used as final reference ()
    vh_cand = _select_germline(mouse_vh, chain="VH", set_selected=False)
    vl_cand = _select_germline(mouse_vl, chain="VL", set_selected=False)
    # When both force-germline are set, allow empty candidate list and inject forced germline (Option B / 842-only run)
    if args.force_germline_vh and args.force_germline_vl:
        if not vh_cand:
            vh_cand = [{"gene": args.force_germline_vh, "selected": True, "selection_reason": "User forced selection (Option A)", "composite_score": 0.0, "fr_identity_pct": None, "vernier_similarity_pct": None, "clinical_precedent": []}]
        if not vl_cand:
            vl_cand = [{"gene": args.force_germline_vl, "selected": True, "selection_reason": "User forced selection (Option A)", "composite_score": 0.0, "fr_identity_pct": None, "vernier_similarity_pct": None, "clinical_precedent": []}]
    if not vh_cand or not vl_cand:
        raise RuntimeError("No germline candidates after CDR length gate")
    vh_gene, vl_gene = _select_best_pair_with_pairing_reference(vh_cand, vl_cand)

    # Override if forced (Option A support)
    if args.force_germline_vh:
        vh_gene = args.force_germline_vh
        print(f"DEBUG: Forcing VH germline to {vh_gene}")
        found = False
        for c in vh_cand:
            c["selected"] = (c["gene"] == vh_gene)
            if c["selected"]:
                c["selection_reason"] = "User forced selection (Option A)"
                found = True
            else:
                c["rejection_reason"] = "Overridden by user force selection"
        if not found:
            vh_cand.insert(0, {
                "gene": vh_gene,
                "selected": True,
                "selection_reason": "User forced selection (Option A)",
                "composite_score": 0.0
            })

    if args.force_germline_vl:
        vl_gene = args.force_germline_vl
        print(f"DEBUG: Forcing VL germline to {vl_gene}")
        found = False
        for c in vl_cand:
            c["selected"] = (c["gene"] == vl_gene)
            if c["selected"]:
                c["selection_reason"] = "User forced selection (Option A)"
                found = True
            else:
                c["rejection_reason"] = "Overridden by user force selection"
        if not found:
            vl_cand.insert(0, {
                "gene": vl_gene,
                "selected": True,
                "selection_reason": "User forced selection (Option A)",
                "composite_score": 0.0
            })

    # Phase 4 (sequence-level): assemble v1 with CDR grafting (no BM yet)
    v1_vh, v1_vl = _assemble_v1(mouse_vh, mouse_vl, vh_gene, vl_gene, cfg)

    # If this project ID was run before, ensure we don't reuse stale structures.
    # When sequences/germlines change, the existing PDBs MUST be regenerated.
    results_path = project_dir / f"{ab_id}_results.json"
    force_mouse_pdb = False
    force_v1_pdb = False
    try:
        if results_path.exists():
            prev = _load_json(results_path)
            prev_seq = prev.get("sequences") if isinstance(prev, dict) else {}
            if isinstance(prev_seq, dict):
                pmvh = str(prev_seq.get("mouse_VH") or "")
                pmvl = str(prev_seq.get("mouse_VL") or "")
                pv1h = str(prev_seq.get("v1_VH") or "")
                pv1l = str(prev_seq.get("v1_VL") or "")
                if pmvh and pmvh != mouse_vh:
                    force_mouse_pdb = True
                if pmvl and pmvl != mouse_vl:
                    force_mouse_pdb = True
                if pv1h and pv1h != v1_vh:
                    force_v1_pdb = True
                if pv1l and pv1l != v1_vl:
                    force_v1_pdb = True
    except Exception:
        # Best-effort; if parsing fails, we will keep the default behavior.
        pass

    # Phase 3: Structure prediction —  predict_one_immunebuilder.py（）
    pdb_mouse = structures_dir / f"{ab_id}_mouse.pdb"
    pdb_v1 = structures_dir / f"{ab_id}_humanized_v1.pdb"
    if force_mouse_pdb and pdb_mouse.exists():
        try:
            pdb_mouse.unlink()
        except Exception:
            pass
    if not pdb_mouse.exists():
        ok, err = _run_immunebuilder_via_script(mouse_vh, mouse_vl, pdb_mouse)
        if not ok:
            if err:
                print(f"[Phase 3] predict_one_immunebuilder : {err[:500]}")
            try:
                from ImmuneBuilder import ABodyBuilder2  # noqa: PLC0415
                predictor = ABodyBuilder2(numbering_scheme="imgt")
                predictor.predict({"H": mouse_vh, "L": mouse_vl}).save(str(pdb_mouse))
            except ModuleNotFoundError as e:
                raise RuntimeError(
                    "Phase 3  ImmuneBuilder。 Python 。\n"
                    "：(1)  ImmuneBuilder  conda/venv ；"
                    "(2)  IMMUNEBUILDER_PYTHON=< Python > 。\n"
                    f": {err or 'N/A'}"
                ) from e
    if force_v1_pdb and pdb_v1.exists():
        try:
            pdb_v1.unlink()
        except Exception:
            pass
    if not pdb_v1.exists():
        ok, err = _run_immunebuilder_via_script(v1_vh, v1_vl, pdb_v1)
        if not ok:
            if err:
                print(f"[Phase 3] predict_one_immunebuilder v1 : {err[:500]}")
            try:
                predictor
            except NameError:
                from ImmuneBuilder import ABodyBuilder2  # noqa: PLC0415
                predictor = ABodyBuilder2(numbering_scheme="imgt")
            try:
                predictor.predict({"H": v1_vh, "L": v1_vl}).save(str(pdb_v1))
            except NameError:
                raise RuntimeError(
                    "Phase 3  ImmuneBuilder。 ImmuneBuilder 。"
                )

    # Phase 5a: Evaluate v1 (germline framework + CDR graft only)
    from core.evaluation.evaluator import AbEvaluator, AntibodyType  # noqa: PLC0415
    ev1 = AbEvaluator(
        project_name=f"{ab_id}_v44_v1",
        ab_type=AntibodyType.HUMANIZED,
        pdb_path=str(pdb_v1),
        ref_pdb_path=str(pdb_mouse),
        vh_seq=v1_vh,
        vl_seq=v1_vl,
        strict_qa=True,
        use_iedb=False,
    )
    r1 = ev1.run(modules=["structure_13param", "cdr_scan", "developability", "immunogenicity", "delta_vs_mouse"])
    eval_v1 = {
        "abenginecore_version": "1.0.0",
        "project_name": r1.project_name,
        "ab_type": r1.ab_type.value if hasattr(r1.ab_type, "value") else str(r1.ab_type),
        "overall_status": r1.overall_status,
        "modules_run": r1.modules_run,
        "overall_flags": r1.overall_flags,
        "generated_at": r1.generated_at,
        "results": r1.results,
    }

    # Phase 4: Vernier zone back-mutation decisions (based on humanized v1 structure)
    try:
        from scripts.structure_metrics_humanization import analyze_structure  # noqa: PLC0415
        m = analyze_structure(pdb_v1, chain_vh="H", chain_vl="L", skip_sasa=False)
        sasa = m.vernier_sasa_per_residue or {}
        packing = m.vernier_packing or {}
        dist = m.vernier_cdr_distances or {}
    except Exception as e:
        raise RuntimeError(f"Phase 3 metrics failed: {e}")

    m_vh_kd = _kabat_numbering(mouse_vh)
    m_vl_kd = _kabat_numbering(mouse_vl)
    g_vh_kd = _kabat_numbering(_germ_seq(vh_gene, "VH"))
    g_vl_kd = _kabat_numbering(_germ_seq(vl_gene, "VL"))
    decisions, bm_vh, bm_vl = _phase4_vernier_decisions(
        cfg=cfg,
        v1_vh_seq=v1_vh,
        v1_vl_seq=v1_vl,
        mouse_vh_kd=m_vh_kd,
        mouse_vl_kd=m_vl_kd,
        germ_vh_kd=g_vh_kd,
        germ_vl_kd=g_vl_kd,
        sasa=sasa,
        contact=packing,
        dist=dist,
    )

    # Assemble v2 (germline + CDR graft + Vernier back-mutations), then re-model & evaluate.
    v2_vh, v2_vl = _assemble_v2(mouse_vh, mouse_vl, vh_gene, vl_gene, bm_vh=bm_vh, bm_vl=bm_vl, cfg=cfg)
    has_bm = bool(bm_vh or bm_vl)

    pdb_v2 = structures_dir / f"{ab_id}_humanized_v2.pdb"
    if has_bm:
        if pdb_v2.exists():
            try:
                pdb_v2.unlink()
            except Exception:
                pass
        ok, err = _run_immunebuilder_via_script(v2_vh, v2_vl, pdb_v2)
        if not ok:
            if err:
                print(f"[Phase 3] predict_one_immunebuilder v2 : {err[:500]}")
            try:
                predictor
            except NameError:
                from ImmuneBuilder import ABodyBuilder2  # noqa: PLC0415
                predictor = ABodyBuilder2(numbering_scheme="imgt")
            predictor.predict({"H": v2_vh, "L": v2_vl}).save(str(pdb_v2))

        ev2 = AbEvaluator(
            project_name=f"{ab_id}_v44_v2",
            ab_type=AntibodyType.HUMANIZED,
            pdb_path=str(pdb_v2),
            ref_pdb_path=str(pdb_mouse),
            vh_seq=v2_vh,
            vl_seq=v2_vl,
            strict_qa=True,
            use_iedb=False,
        )
        r2 = ev2.run(modules=["structure_13param", "cdr_scan", "developability", "immunogenicity", "delta_vs_mouse"])
        eval_v2 = {
            "abenginecore_version": "1.0.0",
            "project_name": r2.project_name,
            "ab_type": r2.ab_type.value if hasattr(r2.ab_type, "value") else str(r2.ab_type),
            "overall_status": r2.overall_status,
            "modules_run": r2.modules_run,
            "overall_flags": r2.overall_flags,
            "generated_at": r2.generated_at,
            "results": r2.results,
        }
    else:
        eval_v2 = None

    p4_path = internal_dir / f"phase4_backmutation_{ab_id}.json"
    _write_json(p4_path, {
        "antibody": ab_id.upper(),
        "checklist_version": "V4.4.1",
        "phase": "4_backmutation",
        "recommended_vh": vh_gene,
        "recommended_vk": vl_gene,
        "bm_vh_count": len(bm_vh),
        "bm_vl_count": len(bm_vl),
        "bm_vh_map": bm_vh,
        "bm_vl_map": bm_vl,
        "backmutation_decisions": decisions,
    })

    # Build results.json (single source of truth)
    results_path = project_dir / f"{ab_id}_results.json"
    final_v = "v2" if has_bm else "v1"
    final_vh = v2_vh if has_bm else v1_vh
    final_vl = v2_vl if has_bm else v1_vl
    eval_final = eval_v2 if (has_bm and eval_v2 is not None) else eval_v1
    # Mutation list (customer-visible) — no rule codes, no numeric thresholds.
    muts_v1_v2: List[Dict[str, Any]] = []
    try:
        if has_bm:
            v1_vh_kd = _kabat_numbering(v1_vh)
            v1_vl_kd = _kabat_numbering(v1_vl)
            v2_vh_kd = _kabat_numbering(v2_vh)
            v2_vl_kd = _kabat_numbering(v2_vl)
            for p, mouse_aa in sorted(bm_vh.items()):
                fr = v1_vh_kd.get((p, "")) or "-"
                to = v2_vh_kd.get((p, "")) or mouse_aa
                if fr != "-" and to != "-" and fr != to:
                    muts_v1_v2.append(
                        {
                            "chain": "VH",
                            "kabat_pos": p,
                            "from": fr,
                            "to": to,
                            "region": "FR（Vernier）",
                            "rationale": "：（Vernier）",
                        }
                    )
            for p, mouse_aa in sorted(bm_vl.items()):
                fr = v1_vl_kd.get((p, "")) or "-"
                to = v2_vl_kd.get((p, "")) or mouse_aa
                if fr != "-" and to != "-" and fr != to:
                    muts_v1_v2.append(
                        {
                            "chain": "VL",
                            "kabat_pos": p,
                            "from": fr,
                            "to": to,
                            "region": "FR（Vernier）",
                            "rationale": "：（Vernier）",
                        }
                    )
    except Exception:
        muts_v1_v2 = []

    results: Dict[str, Any] = {
        "_meta": {
            "role": "single_source_of_truth",
            "pipeline_standard": "V4.4",
            "antibody_id": ab_id,
            "project": args.project_name or f"{ab_id.upper()} VH/VL ",
            "generated_at": datetime.now().strftime("%Y-%m-%d"),
            "final_version": final_v,
            "framework": {"VH": vh_gene, "VL": vl_gene},
        },
        "germline": {"VH_gene": vh_gene, "VL_gene": vl_gene},
        "sequences": {
            "mouse_VH": mouse_vh,
            "mouse_VL": mouse_vl,
            "v1_VH": v1_vh,
            "v1_VL": v1_vl,
            "v2_VH": v2_vh, "v2_VL": v2_vl,
            # keep renderer stable (pI optimization later can populate v3)
            "v3_VH": final_vh, "v3_VL": final_vl,
        },
        "sequence_annotation": {
            "_note": "Kabat  FR/CDR ，。",
            "numbering_scheme": "Kabat",
            "VH": _annotation(final_vh, "VH", fr_source=""),
            "VL": _annotation(final_vl, "VL", fr_source=""),
        },
        "germline_candidates": {
            "_note": "（/）",
            "VH_candidates": vh_cand,
            "VL_candidates": vl_cand,
            "golden_pair_exception_documented": True,
            "golden_pair_exception_rationale": "/；。",
        },
        "mutations": {"v1_to_v2": muts_v1_v2, "v2_to_v3": []},
        "_internal": {
            "evaluation_v1": eval_v1,
            "evaluation_v2": eval_v2,
            "phase4_backmutation_log": str(p4_path.relative_to(SUITE)).replace("\\", "/"),
        },
        # These are simplified “report-facing” fields (customer report uses PASS/WARN without numbers)
        "developability": _build_developability_block(eval_v1, eval_v2, None, eval_final),
        "immunogenicity": {
            "method": (eval_final.get("results", {}).get("immunogenicity", {}) or {}).get("method", "offline"),
            "risk_level": {
                "v1": (eval_v1.get("results", {}).get("immunogenicity", {}) or {}).get("mhcii_risk", "PENDING"),
                "v2": (eval_v2.get("results", {}).get("immunogenicity", {}) or {}).get("mhcii_risk", "PENDING") if isinstance(eval_v2, dict) else "—",
            },
            "recommended_followup": "PBMC T （）",
        },
        "structure": {
            "tool": "ABodyBuilder2",
            "mouse_pdb": str(pdb_mouse.relative_to(SUITE)).replace("\\", "/"),
            "v1_pdb": str(pdb_v1.relative_to(SUITE)).replace("\\", "/"),
            "v2_pdb": str(pdb_v2.relative_to(SUITE)).replace("\\", "/") if has_bm else None,
        },
        "deliverables": {
            "sequences_fasta": f"projects/{ab_id}_Redesign/{ab_id}_sequences.fasta",
            "results_json": f"projects/{ab_id}_Redesign/{ab_id}_results.json",
            "audit_report": f"projects/{ab_id}_Redesign/reports/{ab_id}_V44_Audit.md",
            "client_report_zh": f"projects/{ab_id}_Redesign/reports/{ab_id}_Client_zh.md",
            "mouse_pdb": f"projects/{ab_id}_Redesign/structures/{ab_id}_mouse.pdb",
            "final_pdb": f"projects/{ab_id}_Redesign/structures/{ab_id}_humanized_{final_v}.pdb",
        },
    }

    _write_json(results_path, results)

    # Write standard FASTA
    fasta = project_dir / f"{ab_id}_sequences.fasta"
    fasta_lines = [
        f">{ab_id}_mouse|VH|parent|reference",
        mouse_vh,
        f">{ab_id}_mouse|VL|parent|reference",
        mouse_vl,
        f">{ab_id}_v1|VH|humanized|{'final' if final_v=='v1' else 'intermediate'}",
        v1_vh,
        f">{ab_id}_v1|VL|humanized|{'final' if final_v=='v1' else 'intermediate'}",
        v1_vl,
    ]
    if has_bm:
        fasta_lines += [
            f">{ab_id}_v2|VH|humanized|final",
            v2_vh,
            f">{ab_id}_v2|VL|humanized|final",
            v2_vl,
        ]
    fasta.write_text("\n".join(fasta_lines) + "\n", encoding="utf-8")

    # Internal audit MD (minimal but fixed sections)
    audit_md = reports_dir / f"{ab_id}_V44_Audit.md"
    audit_md.write_text(
        "\n".join([
            f"# {ab_id.upper()} — V4.4 Internal QA Audit",
            "",
            f"- Generated: {datetime.now().strftime('%Y-%m-%d')}",
            f"- Project dir: `projects/{ab_id}_Redesign/`",
            "",
            "## Phase 1 — Sequence + Dual-scheme numbering QA",
            f"- Status: {'PASS' if rep.n_fail==0 else 'FAIL'} (fails={rep.n_fail}, warns={rep.n_warn})",
            "",
            "## Phase 2 — Germline selection (internal)",
            f"- Selected: VH=`{vh_gene}`, VL=`{vl_gene}`",
            "- Note: candidate scores/length gates recorded in results.json (internal).",
            "",
            "## Phase 3 — Structure modeling",
            f"- Mouse PDB: `{results['structure']['mouse_pdb']}`",
            f"- Humanized PDB (v1, germline-only): `{results['structure']['v1_pdb']}`",
            f"- Humanized PDB (v2, +Vernier BM): `{results['structure']['v2_pdb']}`" if results["structure"].get("v2_pdb") else "- Humanized PDB (v2): N/A (no BM applied)",
            "",
            "## Phase 4 — Vernier (22 sites) per-position decision log",
            f"- Log: `{results['_internal']['phase4_backmutation_log']}` (22 rows expected)",
            "",
            "## Phase 5 — QC summary (internal)",
            f"- AbEvaluator v1: `{ab_id}_v44_v1` (see results.json → _internal.evaluation_v1)",
            f"- AbEvaluator v2: `{ab_id}_v44_v2` (see results.json → _internal.evaluation_v2)" if results["_internal"].get("evaluation_v2") else "- AbEvaluator v2: N/A",
            "",
            "## Phase 6 — Pre-delivery gate",
            "- Run: `python scripts/verify_vhvl_v44_project.py <id> projects/<id>_Redesign --fix`",
        ]) + "\n",
        encoding="utf-8",
    )

    # Render client report (MD)
    from scripts.render_vhvl_v44_reports import main as render_main  # noqa: PLC0415
    old = sys.argv[:]
    sys.argv = ["render_vhvl_v44_reports.py", ab_id, str(project_dir), "--write"]
    render_main()
    sys.argv = old

    # PDF (avoid lock by writing __new)
    client_md = reports_dir / f"{ab_id}_Client_zh.md"
    if not client_md.exists():
        _en = reports_dir / f"{ab_id}_Client_en.md"
        if _en.exists():
            client_md = _en
    client_pdf_new = reports_dir / f"{(client_md.stem)}__new.pdf"
    if client_md.exists():
        try:
            from scripts.md_to_pdf import render_pdf  # noqa: PLC0415

            render_pdf(str(client_md), str(client_pdf_new))
        except ImportError:
            from scripts.md_to_pdf import convert  # noqa: PLC0415

            convert(str(client_md), str(client_pdf_new))
    else:
        print(f"[run_vhvl_v44_pipeline] skip PDF: no Client_zh/en.md for {ab_id}")

    # Package + verify
    from scripts.package_delivery import package_delivery  # noqa: PLC0415
    package_delivery(ab_id, project_dir, make_zip=True)
    #  results.json  fix（CMC 、Vernier Round2 、、）
    if not getattr(args, "skip_verify", False):
        from scripts.verify_vhvl_v44_project import verify  # noqa: PLC0415
        rc = verify(ab_id, project_dir, fix=True)
        if rc != 0:
            raise SystemExit(rc)
    else:
        print("[run_vhvl_v44_pipeline] --skip-verify: skipped verify_vhvl_v44_project")

    print(f"[OK] Completed: {project_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

