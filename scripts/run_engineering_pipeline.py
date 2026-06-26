#!/usr/bin/env python3
"""
run_engineering_pipeline.py — AEOS 
===========================================
，： →  → CMC →  QA → 。

：YAML  JSON ， PROJECT_ID、VH_SEQUENCE、VL_SEQUENCE、CONSTRAINTS、REPORT_PROFILE。

:
    python scripts/run_engineering_pipeline.py input.yaml
    python scripts/run_engineering_pipeline.py input.json

 (input.yaml):
    PROJECT_ID: my_antibody
    ANTIBODY_NAME: My Antibody
    VH_SEQUENCE: QVQLVQSGAEVKKPGASVKVSCKASGYTFTSYNMHWVRQAPGQGLEWMG...
    VL_SEQUENCE: DIVLTQSPASLAVSPGQRATITCRASESVDNYGISFMNWYQQKPGQPPK...
    SPECIES_ORIGIN: mouse
    CONSTRAINTS: FR_only
    REPORT_PROFILE: client
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

from core.pipeline_errors import (
    PipelineError,
    dependency_unavailable,
    missing_input,
    prerequisite_failed,
)

_REQUIRED = ["PROJECT_ID", "VH_SEQUENCE", "VL_SEQUENCE"]
_OPTIONAL = {"CONSTRAINTS": "FR_only", "REPORT_PROFILE": "client", "SPECIES_ORIGIN": "mouse"}


def _load_input(path: Path) -> dict:
    """Load YAML or JSON input."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
            return yaml.safe_load(text) or {}
        except ImportError:
            raise PipelineError(
                code="invalid_input",
                message="YAML input requires PyYAML. Install: pip install pyyaml",
                field="input_file",
            )
    return json.loads(text)


def _validate_input(data: dict) -> list[PipelineError]:
    """Validate required fields; return list of errors."""
    errors = []
    for field in _REQUIRED:
        val = data.get(field) or data.get(field.replace("_", ""))
        if not val or not str(val).strip():
            errors.append(missing_input(field))
    vh = (data.get("VH_SEQUENCE") or data.get("VHSEQUENCE") or "").strip()
    vl = (data.get("VL_SEQUENCE") or data.get("VLSEQUENCE") or "").strip()
    if vh and len(vh) < 80:
        errors.append(PipelineError("invalid_input", f"VH_SEQUENCE too short ({len(vh)} < 80)", "VH_SEQUENCE"))
    if vl and len(vl) < 80:
        errors.append(PipelineError("invalid_input", f"VL_SEQUENCE too short ({len(vl)} < 80)", "VL_SEQUENCE"))
    valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
    if vh and any(c not in valid_aa for c in vh.upper()):
        errors.append(PipelineError("invalid_input", "VH_SEQUENCE contains invalid amino acid characters", "VH_SEQUENCE"))
    if vl and any(c not in valid_aa for c in vl.upper()):
        errors.append(PipelineError("invalid_input", "VL_SEQUENCE contains invalid amino acid characters", "VL_SEQUENCE"))
    return errors


def _check_immunebuilder() -> PipelineError | None:
    """Check if ImmuneBuilder is available (IMMUNEBUILDER_PYTHON or current Python)."""
    python_exe = os.environ.get("IMMUNEBUILDER_PYTHON") or sys.executable
    try:
        r = subprocess.run(
            [python_exe, "-c", "from ImmuneBuilder import ABodyBuilder2"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode == 0:
            return None
        err = (r.stderr or r.stdout or "").strip()[:300]
        return dependency_unavailable(
            "ImmuneBuilder",
            f"Set IMMUNEBUILDER_PYTHON to Python with ImmuneBuilder+pdbfixer (e.g. miniconda3). Error: {err}",
        )
    except FileNotFoundError:
        return dependency_unavailable(
            "ImmuneBuilder",
            f"IMMUNEBUILDER_PYTHON={python_exe} not found. Set to valid Python path.",
        )
    except subprocess.TimeoutExpired:
        return dependency_unavailable("ImmuneBuilder", "Import timeout.")
    except Exception as e:
        return dependency_unavailable("ImmuneBuilder", str(e))


def _run_input_qc(vh: str, vl: str) -> PipelineError | None:
    """P1:  QC —  qc_humanization_inputs 。"""
    qc_script = SUITE / "scripts" / "qc_humanization_inputs.py"
    if not qc_script.exists():
        return None  #  QC 
    try:
        r = subprocess.run(
            [sys.executable, str(qc_script), "--vh", vh, "--vl", vl],
            cwd=str(SUITE),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if r.returncode == 0:
            return None
        err = (r.stderr or r.stdout or "").strip()[:500]
        return prerequisite_failed("input_qc", f"QC failed: {err}")
    except subprocess.TimeoutExpired:
        return prerequisite_failed("input_qc", "QC timeout (60s)")
    except Exception as e:
        return prerequisite_failed("input_qc", str(e))


def _run_humanization_pipeline(ab_id: str, vh: str, vl: str) -> int:
    """Run run_vhvl_v44_pipeline."""
    cmd = [
        sys.executable,
        str(SUITE / "scripts" / "run_vhvl_v44_pipeline.py"),
        "--id", ab_id,
        "--vh", vh,
        "--vl", vl,
    ]
    env = os.environ.copy()
    if str(SUITE) not in env.get("PYTHONPATH", ""):
        env["PYTHONPATH"] = str(SUITE) + (f";{env['PYTHONPATH']}" if env.get("PYTHONPATH") else "")
    r = subprocess.run(cmd, cwd=str(SUITE), env=env)
    return r.returncode


def _write_log(log_path: str, ab_id: str, status: str, entries: list, error: dict | None) -> None:
    """P2:  JSON 。"""
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    obj = {
        "pipeline": "run_engineering_pipeline",
        "antibody_id": ab_id,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "steps": entries,
        "error": error,
    }
    Path(log_path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _run_report_and_deliver(ab_id: str, zip_out: bool = False) -> int:
    """Run report_and_deliver (which checks results.json internally)."""
    cmd = [
        sys.executable,
        str(SUITE / "scripts" / "report_and_deliver.py"),
        ab_id,
    ]
    if zip_out:
        cmd.append("--zip")
    r = subprocess.run(cmd, cwd=str(SUITE))
    return r.returncode


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="AEOS ： → ")
    ap.add_argument("input", help="YAML or JSON input file")
    ap.add_argument("--zip", action="store_true", help=" ZIP ")
    ap.add_argument("--skip-structure", action="store_true", help="（ ImmuneBuilder ）")
    ap.add_argument("--skip-qc", action="store_true", help=" QC（， qc ）")
    ap.add_argument("--log", help=" JSON ")
    args = ap.parse_args()

    path = Path(args.input)
    if not path.exists():
        err = prerequisite_failed("input", f"Input file not found: {path}")
        print(err.to_dict(), flush=True)
        return 2

    try:
        data = _load_input(path)
    except PipelineError as e:
        print(json.dumps(e.to_dict(), ensure_ascii=False), flush=True)
        return 2
    except Exception as e:
        err = PipelineError("invalid_input", str(e), missing_field="input_file")
        print(json.dumps(err.to_dict(), ensure_ascii=False), flush=True)
        return 2

    # Normalize keys
    data = {k.replace(" ", "_").upper(): v for k, v in (data or {}).items()}
    data["VH_SEQUENCE"] = data.get("VH_SEQUENCE") or data.get("VHSEQUENCE") or ""
    data["VL_SEQUENCE"] = data.get("VL_SEQUENCE") or data.get("VLSEQUENCE") or ""
    data["PROJECT_ID"] = data.get("PROJECT_ID") or data.get("PROJECTID") or ""

    errors = _validate_input(data)
    if errors:
        for e in errors:
            print(json.dumps(e.to_dict(), ensure_ascii=False), flush=True)
        return 2

    ab_id = str(data["PROJECT_ID"]).strip().lower()
    vh = str(data["VH_SEQUENCE"]).replace(" ", "").replace("\n", "").upper().strip()
    vl = str(data["VL_SEQUENCE"]).replace(" ", "").replace("\n", "").upper().strip()

    log_entries: list[dict] = []
    _log = lambda step: log_entries.append({"step": step, "timestamp": datetime.now(timezone.utc).isoformat() + "Z"})

    _log("start")

    # P-1: Evidence Gate — pre-flight knowledge check
    ab_display = data.get("ANTIBODY_NAME") or ab_id
    target     = data.get("TARGET") or data.get("ANTIGEN") or ""
    try:
        from core.resources.evidence_gate import EvidenceGate, print_evidence_banner
        _gate = EvidenceGate(enable_network=bool(target))
        _evidence_ctx = _gate.check(antibody_name=ab_display, target=target)
        print_evidence_banner(_evidence_ctx)
        log_entries.append({
            "step": "evidence_gate",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "evidence": _evidence_ctx.to_dict(),
        })
    except Exception as e:
        print(f"[AEOS] Evidence gate skipped: {e}", flush=True)
        _evidence_ctx = None
    _log("evidence_gate_done")

    # P0:  —  ImmuneBuilder
    if not args.skip_structure:
        dep_err = _check_immunebuilder()
        if dep_err:
            _log("dependency_check_fail")
            if args.log:
                _write_log(args.log, ab_id, "fail", log_entries, dep_err.to_dict())
            print(json.dumps(dep_err.to_dict(), ensure_ascii=False), flush=True)
            return 2
    _log("dependency_check_ok")

    # P1:  QC — 
    if not args.skip_qc:
        qc_err = _run_input_qc(vh, vl)
        if qc_err:
            _log("qc_fail")
            if args.log:
                _write_log(args.log, ab_id, "fail", log_entries, qc_err.to_dict())
            print(json.dumps(qc_err.to_dict(), ensure_ascii=False), flush=True)
            return 2
    _log("qc_ok")

    # Step 1: Humanization pipeline ( developability, CMC, structure QA)
    print(f"[AEOS] Running humanization pipeline for {ab_id}...", flush=True)
    code = _run_humanization_pipeline(ab_id, vh, vl)
    if code != 0:
        _log("humanization_fail")
        if args.log:
            _write_log(args.log, ab_id, "fail", log_entries, {"exit_code": code})
        print(f"[AEOS] Humanization pipeline failed (exit {code})", flush=True)
        return code
    _log("humanization_ok")

    # Step 2: Report and deliver ( results.json)
    print(f"[AEOS] Running report and delivery for {ab_id}...", flush=True)
    code = _run_report_and_deliver(ab_id, zip_out=args.zip)
    if code != 0:
        _log("report_fail")
        if args.log:
            _write_log(args.log, ab_id, "fail", log_entries, {"exit_code": code})
        print(f"[AEOS] Report/delivery failed (exit {code})", flush=True)
        return code
    _log("report_ok")

    if args.log:
        _write_log(args.log, ab_id, "ok", log_entries, None)

    # Self-Evolution: emit RunEvent
    try:
        from core.evolution.event_collector import EventCollector
        _collector = EventCollector()
        _run_event = _collector.from_evidence_gate(
            project_id=ab_id,
            family="vhvl_humanization",
            entrypoint="run_engineering_pipeline.py",
            evidence_ctx=_evidence_ctx,
            exit_code=0,
        )
        _run_event.report_generated = True
        _collector.emit(_run_event)
    except Exception:
        pass

    print(f"[AEOS] Done. Delivery package: delivery_{ab_id}/", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
