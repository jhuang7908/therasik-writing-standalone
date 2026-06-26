"""
Load Module 4 smoke-test summary for the Intelligence IDE (Account panel).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_QA_FILE = Path(__file__).resolve().parent / "data" / "qa" / "smoke_latest.json"


def load_smoke_summary() -> dict[str, Any]:
    if not _QA_FILE.is_file():
        return {
            "ok": False,
            "configured": False,
            "message": "No smoke record on server. Run scripts/smoke_intelligence_module4.py and redeploy data/qa/smoke_latest.json.",
        }
    try:
        data = json.loads(_QA_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "configured": False, "message": f"Invalid QA file: {exc}"}

    cases = data.get("cases") or []
    summary = data.get("summary") or {}
    fails = [c for c in cases if c.get("status") == "FAIL"]
    warns = [c for c in cases if c.get("status") == "WARN"]
    overall = "PASS"
    if summary.get("fail", 0) > 0 or fails:
        overall = "FAIL"
    elif summary.get("warn", 0) > 0 or warns:
        overall = "WARN"

    return {
        "ok": True,
        "configured": True,
        "overall": overall,
        "generated_at": data.get("generated_at"),
        "base": data.get("base"),
        "project_id": data.get("project_id"),
        "username": data.get("username"),
        "elapsed_s": data.get("elapsed_s"),
        "summary": summary,
        "warn_cases": warns[:6],
        "fail_cases": fails[:6],
        "cases_total": len(cases),
        "ide_version": "v2.2.0",
    }
