"""
api/routers/structure.py — Fv structure prediction via ImmuneBuilder ABodyBuilder2 (batch/async).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from api.job_store import job_dir, jobs, save_result, persist_job_snapshot
from api.models import FvImmuneBuilderRequest, FvPairItem, VhhStructureRequest

router = APIRouter(prefix="/structure", tags=["Structure"])

_AA = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]+$")


def _sanitize_pair_id(raw: str, index: int) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", (raw or "").strip())[:48]
    return s if s else f"pair_{index + 1}"


def _predict_cmd(json_path: Path) -> List[str]:
    """
    Resolve Python + predict_one_immunebuilder.py.
    Override with env INSYNBIO_IMMUNEBUILDER_PYTHON (absolute path to python.exe).
    """
    script = ROOT / "scripts" / "predict_one_immunebuilder.py"
    if not script.is_file():
        raise FileNotFoundError(f"Missing script: {script}")
    exe = (os.environ.get("INSYNBIO_IMMUNEBUILDER_PYTHON") or "").strip()
    if exe:
        return [exe, str(script), "--json", str(json_path)]
    return [
        "conda",
        "run",
        "-n",
        "anarcii",
        "--no-capture-output",
        "python",
        str(script),
        "--json",
        str(json_path),
    ]


def _run_fv_immunebuilder_impl(job_id: str, pairs: List[FvPairItem]) -> None:
    if jobs.get(job_id, {}).get("status") == "cancelled":
        return
    prev = jobs.get(job_id, {})
    jobs[job_id] = {
        "status": "running",
        "progress": 5,
        "cancel_requested": bool(prev.get("cancel_requested")),
    }
    persist_job_snapshot(job_id)
    t0 = time.time()
    out = job_dir(job_id)
    n = len(pairs)
    results: List[Dict[str, Any]] = []

    for i, p in enumerate(pairs):
        if jobs.get(job_id, {}).get("cancel_requested"):
            elapsed = round(time.time() - t0, 2)
            payload: Dict[str, Any] = {
                "tool": "ABodyBuilder2 (ImmuneBuilder)",
                "job_id": job_id,
                "pairs": results,
                "cancelled": True,
            }
            jobs[job_id] = {
                "status": "cancelled",
                "progress": jobs[job_id].get("progress", 5),
                "result": payload,
                "elapsed_sec": elapsed,
                "progress_note": "Cancelled — ImmuneBuilder stops before remaining pairs",
            }
            persist_job_snapshot(job_id)
            return
        jobs[job_id]["progress"] = min(95, 5 + int(90 * (i + 1) / max(n, 1)))
        persist_job_snapshot(job_id)
        vh = "".join(p.vh.split()).upper()
        vl = "".join(p.vl.split()).upper()
        if not _AA.match(vh) or not _AA.match(vl):
            results.append(
                {
                    "pair_id": p.pair_id,
                    "ok": False,
                    "error": "Non-standard amino-acid characters in VH or VL",
                }
            )
            continue

        safe = _sanitize_pair_id(p.pair_id, i)
        pdb_name = f"{safe}_fv.pdb"
        pdb_path = out / pdb_name
        payload: Dict[str, Any] = {
            "H": vh,
            "L": vl,
            "out_path": str(pdb_path),
            "model_type": "abody",
        }
        json_path = out / f"_{safe}_payload.json"
        json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        cmd = _predict_cmd(json_path)
        try:
            r = subprocess.run(
                cmd,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=7200,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            results.append({"pair_id": p.pair_id, "ok": False, "error": "ImmuneBuilder timeout"})
            continue
        except FileNotFoundError as e:
            results.append({"pair_id": p.pair_id, "ok": False, "error": str(e)})
            continue

        if r.returncode != 0 or not pdb_path.is_file():
            err = (r.stderr or r.stdout or "").strip() or f"exit {r.returncode}"
            results.append({"pair_id": p.pair_id, "ok": False, "error": err[:4000]})
            continue

        url = f"/files/{job_id}/{pdb_name}"
        results.append(
            {
                "pair_id": p.pair_id,
                "ok": True,
                "pdb_url": url,
                "pdb_filename": pdb_name,
                "log": (r.stdout or "").strip()[:2000],
            }
        )

    elapsed = round(time.time() - t0, 2)
    payload: Dict[str, Any] = {
        "tool": "ABodyBuilder2 (ImmuneBuilder)",
        "job_id": job_id,
        "pairs": results,
    }
    ok_any = any(x.get("ok") for x in results)
    if not ok_any:
        jobs[job_id] = {
            "status": "failed",
            "progress": 0,
            "error": json.dumps(results, ensure_ascii=False)[:8000],
            "result": payload,
            "elapsed_sec": elapsed,
        }
        persist_job_snapshot(job_id)
        return

    save_result(job_id, payload, None, elapsed)


@router.post("/fv_immunebuilder/async", summary="Fv prediction (ImmuneBuilder); poll GET /jobs/{job_id}")
def fv_immunebuilder_async(req: FvImmuneBuilderRequest) -> Dict[str, str]:
    job_id = f"fv-ib-{uuid.uuid4().hex[:10]}"
    jobs[job_id] = {"status": "queued", "progress": 0}
    persist_job_snapshot(job_id)

    def _worker() -> None:
        try:
            _run_fv_immunebuilder_impl(job_id, list(req.pairs))
        except Exception as e:
            import traceback

            jobs[job_id] = {
                "status": "failed",
                "progress": 0,
                "error": f"{type(e).__name__}: {e}\n{traceback.format_exc()}"[:12000],
            }
            persist_job_snapshot(job_id)

    threading.Thread(target=_worker, daemon=True).start()
    return {"job_id": job_id, "status": "queued", "poll_url": f"/jobs/{job_id}"}


# ── VHH / NanoBodyBuilder2 ────────────────────────────────────────────────────

def _run_nbb2_impl(job_id: str, seq: str, seq_name: str) -> None:
    """Single VHH structure prediction via NanoBodyBuilder2 (subprocess)."""
    if jobs.get(job_id, {}).get("status") == "cancelled":
        return
    prev = jobs.get(job_id, {})
    jobs[job_id] = {"status": "running", "progress": 5, "cancel_requested": bool(prev.get("cancel_requested"))}
    persist_job_snapshot(job_id)
    t0 = time.time()
    out = job_dir(job_id)
    out.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", (seq_name or "vhh"))[:48] or "vhh"
    pdb_name = f"{safe_name}_nbb2.pdb"
    pdb_path = out / pdb_name
    payload_json: Dict[str, Any] = {
        "H": seq.strip().upper(),
        "out_path": str(pdb_path),
        "model_type": "nanobody",
    }
    json_path = out / "_nbb2_payload.json"
    json_path.write_text(json.dumps(payload_json, ensure_ascii=False), encoding="utf-8")

    jobs[job_id]["progress"] = 20
    jobs[job_id]["progress_note"] = "Running NanoBodyBuilder2…"
    persist_job_snapshot(job_id)

    script = ROOT / "scripts" / "predict_one_immunebuilder.py"
    exe = (os.environ.get("INSYNBIO_IMMUNEBUILDER_PYTHON") or "").strip()
    cmd = (
        [exe, str(script), "--json", str(json_path)]
        if exe
        else ["conda", "run", "-n", "anarcii", "--no-capture-output", "python", str(script), "--json", str(json_path)]
    )

    try:
        r = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=7200,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        jobs[job_id] = {"status": "failed", "progress": 0, "error": "NanoBodyBuilder2 timeout (>2 h)."}
        persist_job_snapshot(job_id)
        return
    except FileNotFoundError as e:
        jobs[job_id] = {"status": "failed", "progress": 0, "error": str(e)}
        persist_job_snapshot(job_id)
        return

    if r.returncode != 0 or not pdb_path.is_file():
        err = (r.stderr or r.stdout or "").strip() or f"exit {r.returncode}"
        jobs[job_id] = {"status": "failed", "progress": 0, "error": err[:6000]}
        persist_job_snapshot(job_id)
        return

    pdb_url = f"/files/{job_id}/{pdb_name}"
    elapsed = round(time.time() - t0, 2)
    result: Dict[str, Any] = {
        "tool": "NanoBodyBuilder2 (ImmuneBuilder)",
        "job_id": job_id,
        "sequence_name": seq_name or "",
        "vhh_sequence": seq.strip().upper(),
        "pdb_url": pdb_url,
        "pdb_filename": pdb_name,
        "log": (r.stdout or "").strip()[:2000],
    }
    save_result(job_id, result, None, elapsed)


@router.post(
    "/nanobodybuilder2/async",
    summary="VHH structure prediction (NanoBodyBuilder2); poll GET /jobs/{job_id}",
)
def nanobodybuilder2_async(req: VhhStructureRequest) -> Dict[str, str]:
    seq = "".join(req.vhh_sequence.split()).upper()
    if not _AA.match(seq):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Non-standard amino-acid characters in VHH sequence.")
    job_id = f"vhh-struct-{uuid.uuid4().hex[:10]}"
    jobs[job_id] = {"status": "queued", "progress": 0}
    persist_job_snapshot(job_id)

    seq_name = (req.sequence_name or "").strip() or "vhh"

    def _worker() -> None:
        try:
            _run_nbb2_impl(job_id, seq, seq_name)
        except Exception as e:
            import traceback
            jobs[job_id] = {
                "status": "failed",
                "progress": 0,
                "error": f"{type(e).__name__}: {e}\n{traceback.format_exc()}"[:12000],
            }
            persist_job_snapshot(job_id)

    threading.Thread(target=_worker, daemon=True).start()
    return {"job_id": job_id, "status": "queued", "poll_url": f"/jobs/{job_id}"}
