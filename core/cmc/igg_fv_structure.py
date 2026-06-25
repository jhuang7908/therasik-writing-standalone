"""
Optional Fv structure prediction for CMC IgG using ABodyBuilder2 (ImmuneBuilder).

Used by api/routers/cmc.py when the client requests predict_fv_structure.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict


def predict_fv_to_pdb(vh: str, vl: str, dest_pdb: Path) -> Dict[str, Any]:
    """
    Run ABodyBuilder2, copy the written PDB to ``dest_pdb``, return metadata.

    On success: ``ok`` is True; ``plddt_eq`` and ``vh_vl_angle_deg`` mirror
    ``core.humanization.engine._run_abodybuilder2``.

    On failure: ``ok`` is False and ``error`` contains a short message (no raise).
    """
    try:
        from core.humanization.engine import _run_abodybuilder2

        out = _run_abodybuilder2(vh.strip().upper(), vl.strip().upper())
        tmp = out.get("pdb_path")
        if not tmp or not os.path.isfile(tmp):
            return {"ok": False, "error": "Predictor did not produce a PDB file."}
        dest_pdb.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp, dest_pdb)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return {
            "ok": True,
            "method": "ABodyBuilder2",
            "plddt_eq": out.get("plddt"),
            "vh_vl_angle_deg": out.get("vh_vl_angle_deg"),
        }
    except Exception as e:  # noqa: BLE001 — soft-fail for optional CMC add-on
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
