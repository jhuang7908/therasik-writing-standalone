#!/usr/bin/env python3
"""
run_engineering_api.py — AEOS Web API
=====================================
REST API： → 。

:
    pip install flask  # 
    python api/run_engineering_api.py

:
    POST /run
        Body: JSON { "project_id": "...", "vh_sequence": "...", "vl_sequence": "..." }
        Response: { "status": "ok"|"fail", "job_id": "...", "message": "..." }

    GET /status/<job_id>
        Response: { "status": "pending"|"running"|"ok"|"fail", "log": [...] }

    GET /report/<job_id>
        Response:  ZIP  404

： worker，。 Celery/RQ。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

try:
    from flask import Flask, request, jsonify, send_file
except ImportError:
    print("Error: Flask required. pip install flask")
    sys.exit(1)

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

app = Flask(__name__)
# ， Redis/DB
_jobs: dict[str, dict] = {}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "aeos"})


@app.route("/run", methods=["POST"])
def run_pipeline():
    """ JSON ， pipeline， job_id 。"""
    data = request.get_json() or {}
    project_id = (data.get("project_id") or data.get("PROJECT_ID") or "").strip()
    vh = (data.get("vh_sequence") or data.get("VH_SEQUENCE") or "").replace(" ", "").replace("\n", "").upper()
    vl = (data.get("vl_sequence") or data.get("VL_SEQUENCE") or "").replace(" ", "").replace("\n", "").upper()

    if not project_id:
        return jsonify({"PIPELINE_ERROR": True, "code": "missing_input", "field": "project_id"}), 400
    if not vh or len(vh) < 80:
        return jsonify({"PIPELINE_ERROR": True, "code": "invalid_input", "field": "vh_sequence"}), 400
    if not vl or len(vl) < 80:
        return jsonify({"PIPELINE_ERROR": True, "code": "invalid_input", "field": "vl_sequence"}), 400

    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {"status": "running", "project_id": project_id, "log": []}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "PROJECT_ID": project_id,
            "VH_SEQUENCE": vh,
            "VL_SEQUENCE": vl,
            "CONSTRAINTS": data.get("constraints", "FR_only"),
            "REPORT_PROFILE": data.get("report_profile", "client"),
        }, f, ensure_ascii=False)
        input_path = f.name

    try:
        r = subprocess.run(
            [sys.executable, str(SUITE / "scripts" / "run_engineering_pipeline.py"), input_path, "--zip"],
            cwd=str(SUITE),
            capture_output=True,
            text=True,
            timeout=3600,
        )
        Path(input_path).unlink(missing_ok=True)
        if r.returncode == 0:
            _jobs[job_id]["status"] = "ok"
            return jsonify({"status": "ok", "job_id": job_id, "message": "Pipeline completed"})
        _jobs[job_id]["status"] = "fail"
        _jobs[job_id]["log"] = (r.stderr or r.stdout or "")[:2000].split("\n")
        return jsonify({"status": "fail", "job_id": job_id, "message": r.stderr or r.stdout}), 500
    except subprocess.TimeoutExpired:
        Path(input_path).unlink(missing_ok=True)
        _jobs[job_id]["status"] = "fail"
        return jsonify({"status": "fail", "job_id": job_id, "message": "Timeout"}), 500
    except Exception as e:
        Path(input_path).unlink(missing_ok=True)
        _jobs[job_id]["status"] = "fail"
        return jsonify({"status": "fail", "job_id": job_id, "message": str(e)}), 500


@app.route("/status/<job_id>", methods=["GET"])
def status(job_id: str):
    if job_id not in _jobs:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(_jobs[job_id])


@app.route("/report/<project_id>", methods=["GET"])
def report(project_id: str):
    """ {project_id}_delivery_*.zip（）。"""
    candidates = list(SUITE.glob(f"{project_id}_delivery_*.zip"))
    if not candidates:
        return jsonify({"error": "Delivery package not found"}), 404
    zip_path = max(candidates, key=lambda p: p.stat().st_mtime)
    return send_file(str(zip_path), as_attachment=True, download_name=zip_path.name)


def main():
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
