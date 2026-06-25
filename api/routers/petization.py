"""
Internal-only petization API (dog/cat VH/VL).

Not part of the public VH/VL evaluation surface. Enable with:
  INSYNBIO_INTERNAL_PET_CONSOLE=1

Optional shared secret (header X-Internal-Pet-Token):
  INSYNBIO_INTERNAL_PET_TOKEN=<secret>
"""

from __future__ import annotations

import importlib.util
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from api.job_store import files_url_for_path, job_dir, reports_category_dir, save_result
from api.petization_report_html import build_petization_delivery_html
from core.reporting.report_qc_gate import run_report_qc

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_pipeline():
    path = ROOT / "scripts" / "run_petization_pipeline.py"
    if not path.exists():
        raise RuntimeError(f"Petization pipeline script missing: {path}")
    spec = importlib.util.spec_from_file_location("_petization_pipeline_mod", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load petization pipeline module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_PIPELINE = None


def _get_pipeline():
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = _load_pipeline()
    return _PIPELINE


def _enabled() -> bool:
    v = os.environ.get("INSYNBIO_INTERNAL_PET_CONSOLE", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def internal_pet_console_enabled() -> bool:
    """True when internal petization routes and `/internal/pet-console` HTML should respond."""
    return _enabled()


def require_internal_pet_console() -> None:
    if not _enabled():
        raise HTTPException(
            status_code=404,
            detail="Internal petization API is disabled (set INSYNBIO_INTERNAL_PET_CONSOLE=1).",
        )


def verify_optional_internal_token(
    x_internal_pet_token: Optional[str] = Header(None, alias="X-Internal-Pet-Token"),
) -> None:
    expected = os.environ.get("INSYNBIO_INTERNAL_PET_TOKEN", "").strip()
    if not expected:
        return
    if not x_internal_pet_token or x_internal_pet_token.strip() != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing internal petization token.")


router = APIRouter(
    prefix="/internal/petization",
    tags=["Internal Petization"],
    dependencies=[Depends(require_internal_pet_console), Depends(verify_optional_internal_token)],
)


class PetizationRunRequest(BaseModel):
    vh: str = Field(..., description="VH amino acid sequence")
    vl: str = Field(..., description="VL amino acid sequence")
    species: Literal["dog", "cat"]
    strategy: Literal[
        "auto",
        "graft_vernier",
        "surface_reshaping",
        "deep_fr_anchor",
    ] = "auto"
    vh_anchor_positions: str = Field(
        default="",
        description="Comma-separated Kabat FR positions for deep_fr_anchor (optional)",
    )
    vl_anchor_positions: str = Field(default="", description="Same for VL (optional)")
    project_name: str = Field("internal_petization", description="Internal project label")
    run_struct_qc: bool = Field(
        True,
        description="Run Phase 4.5 structure QC (pLDDT / RMSD / packing angle checks).",
    )
    force_vh_germline: Optional[str] = Field(None, description="Force a specific VH germline gene name")
    force_vl_germline: Optional[str] = Field(None, description="Force a specific VL germline gene name")


@router.get("/status")
def petization_status() -> Dict[str, Any]:
    """Lightweight probe: enabled flag without running the pipeline."""
    token_required = bool(os.environ.get("INSYNBIO_INTERNAL_PET_TOKEN", "").strip())
    return {
        "enabled": True,
        "token_required": token_required,
        "surface": "internal_petization_only",
    }


@router.post("/run")
def petization_run(body: PetizationRunRequest) -> Dict[str, Any]:
    pet = _get_pipeline()
    t0 = time.time()
    job_id = f"petization-{uuid.uuid4().hex[:8]}"
    out = job_dir(job_id)
    vh = (body.vh or "").strip().replace(" ", "").upper()
    vl = (body.vl or "").strip().replace(" ", "").upper()
    if len(vh) < 80 or len(vl) < 80:
        raise HTTPException(422, "VH and VL must be non-trivial amino acid sequences.")
    vh_anchors: List[int] = pet.parse_positions(body.vh_anchor_positions or "")
    vl_anchors: List[int] = pet.parse_positions(body.vl_anchor_positions or "")
    try:
        result = pet.run_petization(
            vh=vh,
            vl=vl,
            species=body.species,
            strategy=body.strategy,
            vh_anchor_positions=vh_anchors,
            vl_anchor_positions=vl_anchors,
            run_struct_qc=bool(body.run_struct_qc),
            struct_qc_out_dir=out / "struct_qc",
            struct_qc_label=body.project_name or job_id,
            force_vh_germline=body.force_vh_germline,
            force_vl_germline=body.force_vl_germline,
        )
        (out / "petization_result.json").write_text(
            __import__("json").dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        try:
            pet.write_outputs(result, out, body.project_name or job_id)
        except Exception:
            pass
        report_dir = reports_category_dir(job_id, "caninization")
        report_path = report_dir / "petization_report.html"
        html_body = build_petization_delivery_html(
            result=result,
            project_name=body.project_name or job_id,
            job_id=job_id,
            generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            strategy_requested=body.strategy,
        )
        try:
            qc = run_report_qc(html_body, report_family="caninization")
            html_body = qc.inject_qc_badge(html_body)
            qc_overall = qc.overall
        except Exception:
            qc_overall = "WARN"
        report_path.write_text(html_body, encoding="utf-8")
        report_url = f"{files_url_for_path(job_id, report_path)}?cb={int(time.time())}"
        elapsed = round(time.time() - t0, 2)
        save_result(job_id, result, report_url, elapsed, extra={"qc_overall": qc_overall})
        return {
            "job_id": job_id,
            "status": "done",
            "elapsed_sec": elapsed,
            "result": result,
            "report_url": report_url,
            "extra": {"qc_overall": qc_overall},
        }
    except SystemExit as e:
        raise HTTPException(422, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Petization failed: {e}") from e
