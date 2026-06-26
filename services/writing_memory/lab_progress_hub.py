"""
Project-scoped lab progress reports for PI / Grant visibility.

Stores archived experiment reports under data/hub/{project_id}_lab_progress.json.
Linked to platform hub schema (asset_type=dataset, source_module=lab).
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HUB_ROOT = Path(__file__).resolve().parent / "data" / "hub"


def _safe_project_id(project_id: str | None) -> str:
    pid = (project_id or "default").strip() or "default"
    return re.sub(r"[^\w\-]", "_", pid)


def _hub_path(project_id: str | None) -> Path:
    _HUB_ROOT.mkdir(parents=True, exist_ok=True)
    return _HUB_ROOT / f"{_safe_project_id(project_id)}_lab_progress.json"


def _load_store(project_id: str | None) -> dict[str, Any]:
    path = _hub_path(project_id)
    if not path.is_file():
        return {"hub_version": "1.0.0", "project_id": project_id or "default", "reports": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {"hub_version": "1.0.0", "project_id": project_id or "default", "reports": []}
    data.setdefault("reports", [])
    return data


def _save_store(project_id: str | None, data: dict[str, Any]) -> None:
    path = _hub_path(project_id)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def append_progress_report(project_id: str | None, report: dict[str, Any]) -> dict[str, Any]:
    """Append a lab progress report (newest first). Default visibility: pi_only."""
    data = _load_store(project_id)
    now = datetime.now(timezone.utc).isoformat()
    report = dict(report)
    report.setdefault("report_id", uuid.uuid4().hex[:12])
    report.setdefault("created_at", now)
    report.setdefault("visibility", "pi_only")
    report.setdefault("source_module", "lab")
    data["project_id"] = project_id or "default"
    data["reports"].insert(0, report)
    # Keep last 100 reports per project
    data["reports"] = data["reports"][:100]
    _save_store(project_id, data)
    return report


def list_progress_reports(
    project_id: str | None,
    *,
    limit: int = 20,
    visibility: str | None = None,
) -> dict[str, Any]:
    """List archived lab reports for PI / Grant dashboard."""
    data = _load_store(project_id)
    reports = data.get("reports") or []
    if visibility:
        reports = [r for r in reports if r.get("visibility") == visibility]
    return {
        "project_id": data.get("project_id") or project_id or "default",
        "count": min(len(reports), limit),
        "reports": reports[:limit],
        "updated_at": data.get("updated_at"),
    }


def get_progress_report(project_id: str | None, report_id: str) -> dict[str, Any] | None:
    """Fetch one archived report by id."""
    data = _load_store(project_id)
    for r in data.get("reports") or []:
        if str(r.get("report_id")) == str(report_id):
            return r
    return None


def _norm_title(title: str | None) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def _dedupe_key(report: dict[str, Any]) -> str:
    """Same title + experiment ref → one archived row (keep newest)."""
    title = _norm_title(report.get("title"))
    ref = re.sub(r"\s+", " ", (report.get("experiment_ref") or "").strip().lower())
    return f"{title}|{ref}"


def report_has_charts(report: dict[str, Any]) -> bool:
    """True only when embedded image figures exist (not text-only 'Figure N' placeholders)."""
    html = str(report.get("html") or "")
    if "data:image" in html and re.search(
        r"<figure[\s\S]*?<img[^>]+src=[\"']data:image",
        html,
        re.IGNORECASE,
    ):
        return True
    snap = report.get("source_snapshot") or {}
    return blocks_have_charts(snap.get("result_blocks"))


def blocks_have_charts(result_blocks: list[dict[str, Any]] | None) -> bool:
    for block in result_blocks or []:
        if not isinstance(block, dict):
            continue
        if str(block.get("chartUrl") or block.get("chart_url") or "").strip():
            return True
        for f in block.get("files") or []:
            if not isinstance(f, dict):
                continue
            data = str(f.get("data") or "")
            if data.startswith("data:image"):
                return True
    return False


def delete_progress_report(project_id: str | None, report_id: str) -> bool:
    data = _load_store(project_id)
    before = len(data.get("reports") or [])
    data["reports"] = [
        r for r in (data.get("reports") or [])
        if str(r.get("report_id")) != str(report_id)
    ]
    if len(data["reports"]) == before:
        return False
    _save_store(project_id, data)
    return True


_MAX_REPORT_HISTORY = 8


def _history_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "saved_at": now,
        "title": row.get("title"),
        "html": row.get("html"),
        "qc_status": row.get("qc_status"),
        "language": row.get("language"),
        "has_charts": row.get("has_charts"),
        "python_statistics": row.get("python_statistics"),
        "discussion_analysis": row.get("discussion_analysis"),
        "source_snapshot": row.get("source_snapshot"),
    }


def update_progress_report(
    project_id: str | None,
    report_id: str,
    patch: dict[str, Any],
    *,
    record_history: bool = True,
) -> dict[str, Any] | None:
    """Patch an archived report; optionally push current state to history stack."""
    data = _load_store(project_id)
    for row in data.get("reports") or []:
        if str(row.get("report_id")) != str(report_id):
            continue
        if record_history:
            hist = list(row.get("history") or [])
            hist.insert(0, _history_snapshot(row))
            row["history"] = hist[:_MAX_REPORT_HISTORY]
        row.update(patch)
        row["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_store(project_id, data)
        return row
    return None


def rollback_progress_report(project_id: str | None, report_id: str) -> dict[str, Any] | None:
    """Restore the most recent history snapshot (push current state to history)."""
    data = _load_store(project_id)
    for row in data.get("reports") or []:
        if str(row.get("report_id")) != str(report_id):
            continue
        hist = list(row.get("history") or [])
        if not hist:
            return None
        prev = hist.pop(0)
        cur_snap = _history_snapshot(row)
        hist.insert(0, cur_snap)
        row["history"] = hist[:_MAX_REPORT_HISTORY]
        for key in (
            "html", "title", "qc_status", "language", "has_charts",
            "python_statistics", "discussion_analysis", "source_snapshot",
        ):
            if key in prev:
                row[key] = prev[key]
        row["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
        row["updated_at"] = row["rolled_back_at"]
        _save_store(project_id, data)
        return row
    return None


def dedupe_progress_reports(project_id: str | None) -> dict[str, Any]:
    """Remove duplicate archives (same title + experiment_ref); keep newest."""
    data = _load_store(project_id)
    reports = data.get("reports") or []
    seen: set[str] = set()
    kept: list[dict[str, Any]] = []
    for r in reports:
        key = _dedupe_key(r)
        if key in seen:
            continue
        seen.add(key)
        kept.append(r)
    removed = len(reports) - len(kept)
    data["reports"] = kept
    if removed:
        _save_store(project_id, data)
    return {
        "removed": removed,
        "remaining": len(kept),
        "project_id": data.get("project_id") or project_id or "default",
    }


def build_experiment_report_markdown(payload: dict[str, Any]) -> str:
    """Build a formal experiment progress report (Markdown) for archive / download."""
    title = (payload.get("title") or "Experimental Progress Report").strip()
    sop_ref = (payload.get("experiment_ref") or payload.get("sop_ref") or "").strip()
    obs = (payload.get("observations") or "").strip()
    conclusion = (payload.get("conclusion") or "").strip()
    qc = (payload.get("qc_status") or "Pending").strip()
    stats = (payload.get("statistics_analysis") or "").strip()
    rationality = (payload.get("rationality_analysis") or "").strip()
    pubmed = (payload.get("pubmed_digest") or "").strip()
    author = (payload.get("author") or "Lab member").strip()
    project_id = (payload.get("project_id") or "").strip()
    results = payload.get("result_blocks") or []
    generated_at = payload.get("generated_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# {title}",
        "",
        "## Metadata",
        f"- **Generated:** {generated_at}",
        f"- **Author:** {author}",
        f"- **Project ID:** {project_id or '(not set)'}",
        f"- **Reference SOP / Plan:** {sop_ref or '(none)'}",
        f"- **QC Status:** {qc}",
        "",
    ]
    if obs:
        lines += ["## Experimental Context", obs, ""]
    if results:
        lines.append("## Results")
        for i, block in enumerate(results, 1):
            label = (block.get("label") or f"Result {i}").strip()
            notes = (block.get("notes") or "").strip()
            files = block.get("files") or []
            lines.append(f"### {label}")
            if notes:
                lines.append(notes)
            if files:
                names = ", ".join(f.get("name", "file") for f in files if isinstance(f, dict))
                if names:
                    lines.append(f"\n*Attachments:* {names}")
            lines.append("")
    if stats:
        lines += ["## Statistical Summary (AI-assisted)", stats, ""]
    if rationality:
        lines += ["## Rationality & QC Review (AI-assisted)", rationality, ""]
    if conclusion:
        lines += ["## Overall Conclusion", conclusion, ""]
    if pubmed:
        lines += ["## Literature Context (PubMed)", pubmed, ""]
    lines += [
        "---",
        "*Archived via InSynBio Lab IDE. PI-visible in Grant module when project ID is linked.*",
        "",
    ]
    return "\n".join(lines)
