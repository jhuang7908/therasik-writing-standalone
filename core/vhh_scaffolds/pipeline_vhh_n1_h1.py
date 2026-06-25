"""
core.vhh_scaffolds.pipeline_vhh_n1_h1

：
-  VHH 
- ：
  1)  VHH  CDR/FR 
  2) CDR → NVHH-N1  graft 
  3) CDR → NVHH-H1  graft 
- ： true_native  ID（ '4W6Y_B'），/

： H1 " VHH  CDR graft  H1"，
 N1， N1/H1 。
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime

from .cdr_parser import parse_cdrs
from .graft_engine import graft_cdrs
from .registry import get_scaffold
from .scaffold_provenance import build_scaffold_provenance


def run_vhh_n1_h1(
    sequence: str,
    *,
    sample_id: Optional[str] = None,
    native_template_id: Optional[str] = None,
    n1_id: str = "NVHH-N1",
    h1_id: str = "NVHH-H1",
) -> Dict[str, Any]:
    """
    ：
    -  VHH（CDR/FR）
    -  N1  graft
    -  H1  graft
    - ， JSON /  / 
    """

    seq = sequence.strip().replace(" ", "").replace("*", "")
    if not seq:
        raise ValueError("Empty input sequence for VHH → N1/H1 pipeline.")

    # 1)  VHH
    parsed = parse_cdrs(seq)
    regions = parsed["regions"]
    parser_meta = parsed.get("meta", {})
    parser_method = parsed.get("method", "unknown")

    # 2)  N1 / H1 scaffold
    n1_scaffold = get_scaffold(n1_id)
    h1_scaffold = get_scaffold(h1_id)

    # 3) ： true_native （，）
    native_info: Optional[Dict[str, Any]] = None
    if native_template_id:
        try:
            native_scaffold = get_scaffold(native_template_id)
            native_info = {
                "id": native_template_id,
                "layer": native_scaffold.layer,
                "source_path": str(native_scaffold.source_path),
                "description": native_scaffold.data.get("description", ""),
                "sequence_length": len(native_scaffold.data.get("sequence", "")),
                "framework_sequences": native_scaffold.data.get("framework_sequences"),
            }
        except Exception as e:
            # ，
            native_info = {
                "id": native_template_id,
                "error": f"Failed to load native scaffold: {e}",
            }

    # 4)  N1 graft（）
    n1_graft = graft_cdrs(seq, framework_id=n1_id)

    # 5)  H1 graft（）
    h1_graft = graft_cdrs(seq, framework_id=h1_id)

    # 6) 
    seq_len = int(parser_meta.get("sequence_length", len(seq)))
    used_anarci = bool(parser_meta.get("used_anarci", False))
    hallmark_detected = bool(parser_meta.get("hallmark_detected", False))

    reliability_flags: Dict[str, bool] = {
        "has_imgt_numbering": used_anarci,
        "is_vhh_like": hallmark_detected,
        "sequence_length_in_vhh_range": 105 <= seq_len <= 140,
        "used_consensus_scaffold": True,
        "used_engineered_scaffold": True,
        "has_true_native_template": native_info is not None,
    }

    # 7) 
    result: Dict[str, Any] = {
        "meta": {
            "pipeline": "VHH → NVHH-N1 → NVHH-H1 v1.0",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "sample_id": sample_id,
        },
        "input": {
            "sequence": seq,
            "length": len(seq),
        },
        "parser": {
            "method": parser_method,
            "meta": parser_meta,
            "regions": regions,
        },
        "native_template": native_info,
        "n1_graft": {
            "framework_id": n1_graft.framework_id,
            "layer": n1_scaffold.layer,
            "description": n1_scaffold.data.get("description", ""),
            "grafted_sequence": n1_graft.grafted_sequence,
            "grafted_length": len(n1_graft.grafted_sequence),
            "grafted_regions": n1_graft.grafted_regions,
            "framework_fr": n1_graft.framework_fr,
            "mutations_summary": n1_graft.mutations_summary,
            "provenance": n1_graft.provenance,
        },
        "h1_graft": {
            "framework_id": h1_graft.framework_id,
            "layer": h1_scaffold.layer,
            "description": h1_scaffold.data.get("description", ""),
            "grafted_sequence": h1_graft.grafted_sequence,
            "grafted_length": len(h1_graft.grafted_sequence),
            "grafted_regions": h1_graft.grafted_regions,
            "framework_fr": h1_graft.framework_fr,
            "mutations_summary": h1_graft.mutations_summary,
            "provenance": h1_graft.provenance,
        },
        "reliability": {
            "flags": reliability_flags,
            "parser_method": parser_method,
        },
        # ： N1 / H1（ native_template）
        "scaffold_provenance": {
            "N1": build_scaffold_provenance(n1_id),
            "H1": build_scaffold_provenance(h1_id),
            "native": (
                build_scaffold_provenance(native_template_id)
                if native_template_id
                else None
            ),
        },
        "provenance": {
            "native_template_id": native_template_id,
            "consensus_scaffold_id": n1_id,
            "engineered_scaffold_id": h1_id,
            "notes": [
                "CDR1/2/3 。",
                "N1  VHH （NVHH-N1）， natural-like 。",
                "H1  VHH （NVHH-H1），。",
            ],
        },
    }

    return result

