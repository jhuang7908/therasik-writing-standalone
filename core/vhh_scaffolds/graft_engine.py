"""
core.vhh_scaffolds.graft_engine

：
-  VHH  FR/CDR
-  CDR1/2/3  scaffold ( NVHH-H1)
-  +  +  + "/"

 v1 ，：、 CDR graft。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional

from .cdr_parser import parse_cdrs
from .registry import get_scaffold


@dataclass
class GraftResult:
    original_sequence: str
    framework_id: str
    method: str
    grafted_sequence: str
    original_regions: Dict[str, str]
    grafted_regions: Dict[str, str]
    framework_fr: Dict[str, str]
    provenance: Dict[str, Any]
    mutations_summary: Dict[str, Any]


def graft_cdrs(
    sequence: str,
    framework_id: str = "NVHH-H1",
) -> GraftResult:
    """
     VHH  CDR1/2/3  scaffold。
     scaffold  FR1-4 （framework_sequences ）。
    """

    # 1)  CDR/FR
    parsed = parse_cdrs(sequence)
    regions = parsed["regions"]

    # 
    for key in ("FR1", "FR2", "FR3", "FR4", "CDR1", "CDR2", "CDR3"):
        if not regions.get(key):
            raise ValueError(f"Missing region {key} from input sequence; cannot graft safely.")

    # 2)  scaffold
    scaffold = get_scaffold(framework_id)
    fw_seqs = scaffold.data.get("framework_sequences") or {}

    required_fr_keys = ["FR1", "FR2", "FR3", "FR4"]
    for k in required_fr_keys:
        if k not in fw_seqs:
            raise ValueError(f"Scaffold {framework_id} missing framework_sequences[{k}]")

    # 3)  FR/CDR 
    grafted_regions = {
        "FR1": fw_seqs["FR1"],
        "CDR1": regions["CDR1"],
        "FR2": fw_seqs["FR2"],
        "CDR2": regions["CDR2"],
        "FR3": fw_seqs["FR3"],
        "CDR3": regions["CDR3"],
        "FR4": fw_seqs["FR4"],
    }

    # ，FR4
    from core.vhh_qa_validation import rebuild_v_region_from_regions
    grafted_sequence = rebuild_v_region_from_regions(grafted_regions)

    # 4) "/"（ region ）
    mutations_summary: Dict[str, Any] = {
        "FR1": _summarize_region_replacement("FR1", regions["FR1"], fw_seqs["FR1"]),
        "FR2": _summarize_region_replacement("FR2", regions["FR2"], fw_seqs["FR2"]),
        "FR3": _summarize_region_replacement("FR3", regions["FR3"], fw_seqs["FR3"]),
        "FR4": _summarize_region_replacement("FR4", regions["FR4"], fw_seqs["FR4"]),
        # CDR ，
        "CDR1": {"type": "cdr_preserved", "length": len(regions["CDR1"])},
        "CDR2": {"type": "cdr_preserved", "length": len(regions["CDR2"])},
        "CDR3": {"type": "cdr_preserved", "length": len(regions["CDR3"])},
    }

    # 5) ：（ true_native → N1 → H1 ）
    provenance: Dict[str, Any] = {
        "framework_id": framework_id,
        "framework_layer": scaffold.layer,
        "framework_source_path": str(scaffold.source_path),
        "notes": [
            "CDR1/2/3  input 。",
            "FR1/2/3/4  scaffold.framework_sequences。",
        ],
    }

    return GraftResult(
        original_sequence=sequence,
        framework_id=framework_id,
        method="v1_cdr_graft",
        grafted_sequence=grafted_sequence,
        original_regions=regions,
        grafted_regions=grafted_regions,
        framework_fr={
            "FR1": fw_seqs["FR1"],
            "FR2": fw_seqs["FR2"],
            "FR3": fw_seqs["FR3"],
            "FR4": fw_seqs["FR4"],
        },
        provenance=provenance,
        mutations_summary=mutations_summary,
    )


def _summarize_region_replacement(
    region_name: str,
    orig: str,
    new: str,
) -> Dict[str, Any]:
    """
     FR （ diff）。
    """
    return {
        "type": "framework_replacement",
        "region": region_name,
        "orig_length": len(orig),
        "new_length": len(new),
        "length_changed": len(orig) != len(new),
        "note": " per-residue diff 。"
    }

