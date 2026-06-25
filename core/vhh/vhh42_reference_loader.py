"""
VHH42 frozen reference data — read-only loaders + optional input benchmarking.

Does not change humanization scoring; safe to import from pipelines and reports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]

VHH_UNION = PROJECT_ROOT / "data" / "vhh_clinical_39_union"
REFERENCE_STATS = PROJECT_ROOT / "data" / "reference" / "VHH42_reference_stats_v1.json"
SUPPLEMENT_JSON = VHH_UNION / "vhh42_sabdab_supplement.json"


def kabat_fr_cdr_segments_for_vhh(seq: str) -> Optional[Dict[str, str]]:
    """
    Kabat FR/CDR strings for a VHH sequence (ANARCII + KabatDict).
    Returns None if ANARCII is unavailable or numbering fails.
    """
    try:
        from anarcii import Anarcii
        from core.humanization.kabat_utils import cdr_span, kabat_from_anarcii
    except ImportError:
        return None

    s = (seq or "").strip().upper().replace(" ", "").replace("\n", "")
    if not s:
        return None

    a = Anarcii(seq_type="antibody", mode="accuracy")
    a.number([s])
    entry = a.to_scheme("kabat").get("Sequence 1", {})
    if entry.get("error") or entry.get("chain_type") != "H":
        return None
    kd = kabat_from_anarcii(entry["numbering"])
    return {
        "fr1": cdr_span(kd, 1, 25),
        "cdr1": cdr_span(kd, 26, 35),
        "fr2": cdr_span(kd, 36, 49),
        "cdr2": cdr_span(kd, 50, 65),
        "fr3": cdr_span(kd, 66, 94),
        "cdr3": cdr_span(kd, 95, 102),
    }


def load_sabdab_supplement_entries() -> List[Dict[str, Any]]:
    """Load the 3 SAbDab / Database-B supplement rows (frozen JSON)."""
    if not SUPPLEMENT_JSON.exists():
        return []
    with open(SUPPLEMENT_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("entries") or [])


def annotate_input_vs_vhh42_population(seq: str) -> Dict[str, Any]:
    """
    Compare input sequence metrics to frozen VHH42 p5/p95 (sequence-only, BioPython).
    """
    out: Dict[str, Any] = {"available": False}
    s = (seq or "").strip()
    if not s:
        return {**out, "reason": "empty sequence"}

    if not REFERENCE_STATS.exists():
        return {**out, "reason": "missing VHH42_reference_stats_v1.json"}

    with open(REFERENCE_STATS, encoding="utf-8") as f:
        data = json.load(f)
    metrics = data.get("metrics") or {}

    try:
        from Bio.SeqUtils.ProtParam import ProteinAnalysis
    except ImportError:
        return {**out, "reason": "biopython not available"}

    try:
        pa = ProteinAnalysis(s)
        snap = {
            "pI": round(pa.isoelectric_point(), 2),
            "GRAVY": round(pa.gravy(), 4),
            "instability_index": round(pa.instability_index(), 2),
            "net_charge_pH7": round(pa.charge_at_pH(7), 2),
        }
    except Exception as e:
        return {**out, "reason": f"ProtParam failed: {e}"}

    flags: List[str] = []
    for key in ("pI", "GRAVY", "instability_index", "net_charge_pH7"):
        m = metrics.get(key) or {}
        p5, p95 = m.get("p5"), m.get("p95")
        v = snap[key]
        if p5 is not None and v < p5:
            flags.append(f"{key} below VHH42 p5 ({p5})")
        if p95 is not None and v > p95:
            flags.append(f"{key} above VHH42 p95 ({p95})")

    return {
        "available": True,
        "reference_meta": data.get("_meta") or {},
        "input_metrics": snap,
        "outlier_flags": flags,
        "data_files": {
            "reference_stats": str(REFERENCE_STATS.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "cmc_csv": "data/vhh_clinical_39_union/vhh42_cmc_metrics.csv",
            "germline_json": "data/vhh_clinical_39_union/vhh42_germline_assignments.json",
            "fr3_rule": "data/vhh_clinical_39_union/vhh_fr3_packing_rule.json",
        },
    }
