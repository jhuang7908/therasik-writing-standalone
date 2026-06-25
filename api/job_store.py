"""
api/job_store.py  —  In-memory job registry + file storage helpers.
For demo use only (resets on restart). Replace with Redis/DB for production.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional

# In-memory job store: job_id → {status, progress, result, report_url, error}
jobs: Dict[str, Dict[str, Any]] = {}

STORAGE_ROOT = Path(__file__).resolve().parents[1] / ".job_storage"
STORAGE_ROOT.mkdir(exist_ok=True)


def job_dir(job_id: str) -> Path:
    d = STORAGE_ROOT / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def reports_category_dir(job_id: str, category: str) -> Path:
    """Classified report subtree: ``.job_storage/{job_id}/reports/{category}/``."""
    p = job_dir(job_id) / "reports" / category
    p.mkdir(parents=True, exist_ok=True)
    return p


def files_url_for_path(job_id: str, file_path: Path) -> str:
    """Build ``/files/{job_id}/relative/path`` from a path under the job directory.
    Note: does NOT include the /api prefix — callers that use apiJoin() already add it.
    """
    base = job_dir(job_id).resolve()
    try:
        rel = file_path.resolve().relative_to(base).as_posix()
    except ValueError:
        rel = file_path.name
    return f"/files/{job_id}/{rel}"


def save_result(
    job_id: str,
    result: Dict[str, Any],
    report_url: Optional[str],
    elapsed_sec: float,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist job outcome for GET /jobs/{job_id}. Include ``extra`` when the
    synchronous JSON response would carry JobStatus.extra (e.g. zip_url) so
    async polling returns the same download fields."""
    row: Dict[str, Any] = {
        "status":      "done",
        "progress":    100,
        "elapsed_sec": elapsed_sec,
        "result":      result,
        "report_url":  report_url,
    }
    if extra is not None:
        row["extra"] = extra
    jobs[job_id] = row
    persist_job_snapshot(job_id)
def persist_job_snapshot(job_id: str) -> None:
    """Write current ``jobs[job_id]`` to disk so GET /jobs survives uvicorn --reload / process restart."""
    row = jobs.get(job_id)
    if not row:
        return
    try:
        p = job_dir(job_id) / "job_snapshot.json"
        safe = json.loads(json.dumps(row, default=str))
        p.write_text(json.dumps(safe, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
def load_job_snapshot(job_id: str) -> Optional[Dict[str, Any]]:
    """Recover job row written by :func:`persist_job_snapshot`."""
    p = STORAGE_ROOT / job_id / "job_snapshot.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
def ensure_job_in_memory(job_id: str) -> bool:
    """If ``job_id`` is missing from RAM but snapshot exists, restore it."""
    if job_id in jobs:
        return True
    snap = load_job_snapshot(job_id)
    if snap:
        # Background jobs run in process-local Python threads. After uvicorn --reload
        # or a server restart, a persisted "running" snapshot is only a stale UI
        # record; the worker thread cannot be resumed.
        if str(snap.get("status") or "").lower() in {"queued", "running", "cancelling"}:
            snap["status"] = "failed"
            snap["error"] = (
                "Job was interrupted by API server reload/restart. "
                "Please rerun the analysis; avoid editing/reloading the server during a background job."
            )
            snap["progress_note"] = "Stale job snapshot recovered after server restart; worker is no longer running."
            try:
                p = STORAGE_ROOT / job_id / "job_snapshot.json"
                p.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass
        jobs[job_id] = snap
        return True
    return False
def request_job_cancel(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Mark an async job for cancellation.    - ``queued`` → immediately ``cancelled`` (worker exits without heavy work).
    - ``running`` / ``cancelling`` → ``cancelling`` until the worker cooperates:
      pipelines check ``cancel_requested`` before/after long steps (cannot kill threads mid-call).    Returns ``None`` if ``job_id`` is unknown; otherwise a JSON-serializable dict.
    """
    if not ensure_job_in_memory(job_id):
        return None
    row = jobs[job_id]
    st = (row.get("status") or "").lower()
    if st in ("done", "failed", "cancelled"):
        return {
            "ok": False,
            "job_id": job_id,
            "status": st,
            "message": "Job already finished",
        }
    row["cancel_requested"] = True
    if st == "queued":
        row["status"] = "cancelled"
        row["progress"] = 0
        row["progress_note"] = "Cancelled before execution"
        persist_job_snapshot(job_id)
        return {
            "ok": True,
            "job_id": job_id,
            "status": "cancelled",
            "message": "Worker will not start this job",
        }
    row["status"] = "cancelling"
    msg = (
        "Cancellation recorded. Work stops before the heavy engine if possible; "
        "if already inside HumanizationEngine / ImmuneBuilder, the current step may finish "
        "(Python threads cannot be force-killed)."
    )
    row["progress_note"] = msg
    persist_job_snapshot(job_id)
    return {"ok": True, "job_id": job_id, "status": "cancelling", "message": msg}