"""
core.vhh_scaffolds.pipeline_vhh_h1

：
-  VHH 
-  CDR Parser 
-  NVHH-H1  CDR 
-  dict， / JSON / 
"""

from __future__ import annotations

from typing import Any, Dict

from .cdr_parser import parse_cdrs
from .graft_engine import graft_cdrs
from .registry import get_scaffold


def run_vhh_to_h1(sequence: str, framework_id: str = "NVHH-H1") -> Dict[str, Any]:
    """
    ：
    -  parse_cdrs()  IMGT 
    -  graft_cdrs()  CDR1/2/3  scaffold（ NVHH-H1）
    - ， dump  JSON 
    """

    seq = sequence.strip().replace(" ", "").replace("*", "")
    if not seq:
        raise ValueError("Empty input sequence for VHH → H1 pipeline.")

    # 1)  VHH
    parsed = parse_cdrs(seq)
    regions = parsed["regions"]
    meta = parsed.get("meta", {})

    # 2)  scaffold （NVHH-H1）
    scaffold = get_scaffold(framework_id)

    # 3)  CDR graft
    graft_result = graft_cdrs(seq, framework_id=framework_id)

    # 4) 
    result: Dict[str, Any] = {
        "input": {
            "sequence": seq,
            "length": len(seq),
        },
        "parser": {
            "method": parsed.get("method", "unknown"),
            "meta": meta,
            "regions": regions,
        },
        "framework": {
            "id": framework_id,
            "layer": scaffold.layer,
            "description": scaffold.data.get("description", ""),
            "source_path": str(scaffold.source_path),
        },
        "graft": {
            "method": graft_result.method,
            "grafted_sequence": graft_result.grafted_sequence,
            "grafted_length": len(graft_result.grafted_sequence),
            "grafted_regions": graft_result.grafted_regions,
            "framework_fr": graft_result.framework_fr,
            "mutations_summary": graft_result.mutations_summary,
            "provenance": graft_result.provenance,
        },
    }

    # ： CMC、、
    return result

