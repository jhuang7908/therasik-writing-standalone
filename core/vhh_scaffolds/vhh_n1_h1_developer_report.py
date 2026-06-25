"""
core.vhh_scaffolds.vhh_n1_h1_developer_report

：
-  run_vhh_n1_h1 ，""。
-  / Cursor / ，。
- ：
  -  & CDR/FR 
  - N1 / H1  graft （ + ）
  - scaffold （true_native / consensus / engineered + parent ）
  -  True/False （""）
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime

from .pipeline_vhh_n1_h1 import run_vhh_n1_h1


def build_vhh_n1_h1_developer_report(
    sequence: str,
    *,
    sample_id: Optional[str] = None,
    native_template_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    ""， dump  JSON。
    """

    core = run_vhh_n1_h1(
        sequence,
        sample_id=sample_id,
        native_template_id=native_template_id,
    )

    #  meta
    report: Dict[str, Any] = {
        "meta": {
            "report_type": "VHH_N1_H1_DEVELOPER_REPORT",
            "version": "v1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "pipeline": core["meta"]["pipeline"],
            "sample_id": core["meta"]["sample_id"],
        },
        "input": core["input"],
    }

    # 1) （CDR/FR）
    parser = core["parser"]
    regions = parser["regions"]

    report["numbering_and_segmentation"] = {
        "parser_method": parser["method"],
        "sequence_length": core["input"]["length"],
        "regions": regions,
        "reliability_flags": {
            "has_imgt_numbering": core["reliability"]["flags"]["has_imgt_numbering"],
            "is_vhh_like": core["reliability"]["flags"]["is_vhh_like"],
            "sequence_length_in_vhh_range": core["reliability"]["flags"]["sequence_length_in_vhh_range"],
        },
        #  IMGT ，
        "notes": [
            " parser_method （unknown）， ANARCI。",
            " IMGT ， ANARCI  numbering 。",
        ],
    }

    # 2) N1 / H1 graft （）
    n1 = core["n1_graft"]
    h1 = core["h1_graft"]

    report["graft_summary"] = {
        "n1": {
            "framework_id": n1["framework_id"],
            "layer": n1["layer"],
            "description": n1["description"],
            "grafted_length": n1["grafted_length"],
            "grafted_sequence": n1["grafted_sequence"],
            "grafted_regions": n1["grafted_regions"],
            "mutations_summary": n1["mutations_summary"],
        },
        "h1": {
            "framework_id": h1["framework_id"],
            "layer": h1["layer"],
            "description": h1["description"],
            "grafted_length": h1["grafted_length"],
            "grafted_sequence": h1["grafted_sequence"],
            "grafted_regions": h1["grafted_regions"],
            "mutations_summary": h1["mutations_summary"],
        },
    }

    # 3) scaffold （ true_native / consensus / engineered）
    sp = core["scaffold_provenance"]

    report["scaffold_provenance"] = {
        "N1": sp["N1"],   #  flags / source / design / annotations
        "H1": sp["H1"],
        "native": sp["native"],  #  None
    }

    # 4) 
    report["reliability"] = core["reliability"]
    report["provenance"] = core["provenance"]
    report["native_template"] = core["native_template"]  #  None

    return report

