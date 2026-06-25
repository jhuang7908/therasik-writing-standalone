"""
core.vhh_scaffolds.export_h1_report

：
-  run_vhh_to_h1()  VHH → NVHH-H1 
- "/" + 
- ：
  -  JSON 
  -  / 
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime

from .pipeline_vhh_h1 import run_vhh_to_h1


def build_vhh_h1_report(sequence: str, *,
                        sample_id: Optional[str] = None,
                        native_template_id: Optional[str] = None) -> Dict[str, Any]:
    """
    ：" JSON "。

    ：
        sequence:  VHH 
        sample_id: ，（ EGFR_7D12）
        native_template_id: ， true_native （PDB_xxxx）
    """

    pipeline = run_vhh_to_h1(sequence)

    meta = pipeline["parser"].get("meta", {})
    parser_method = pipeline["parser"].get("method", "unknown")

    # =====  / True or False =====
    used_anarci = bool(meta.get("used_anarci", False))
    hallmark_detected = bool(meta.get("hallmark_detected", False))
    seq_len = int(meta.get("sequence_length", pipeline["input"]["length"]))

    reliability_flags: Dict[str, bool] = {
        #  ANARCI（IMGT ）
        "has_imgt_numbering": used_anarci,
        #  VHH hallmark（FR2 ）
        "is_vhh_like": hallmark_detected,
        #  VHH （）
        "sequence_length_in_vhh_range": 105 <= seq_len <= 140,
        #  scaffold（NVHH-H1）
        "used_engineered_scaffold": True,
        #  true_native ，
        "has_true_native_template": native_template_id is not None,
    }

    # =====  =====
    report: Dict[str, Any] = {
        "meta": {
            "pipeline": "VHH → NVHH-H1 v1.0",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "sample_id": sample_id,
        },
        "input": pipeline["input"],          # 
        "parser": pipeline["parser"],        # CDR/FR 
        "framework": pipeline["framework"],  # NVHH-H1 scaffold 
        "graft": pipeline["graft"],          # 
        "reliability": {
            "flags": reliability_flags,
            "parser_method": parser_method,
        },
        "provenance": {
            "native_template_id": native_template_id,  # ，
            "consensus_scaffold_id": "NVHH-N1",        #  N1，
            "engineered_scaffold_id": pipeline["framework"]["id"],  # NVHH-H1
        },
    }

    return report

