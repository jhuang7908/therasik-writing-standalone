#!/usr/bin/env python
"""
FGF23-23F1128 VAM Unattended Pipeline Orchestrator (VAM V1.4 / Boltz baseline).

Chains all deterministic, server-automatable stages with checkpoint/resume.
Human-gated steps (Boltz model choice, final candidate tiering, report sign-off)
are NOT part of this script — they happen before and after it.

Stage order:
  setup      setup_fgf23_vam_numbering.py     (ANARCI CDR positions → numbering JSON)
  relax      run_fgf23_relax.py               (OpenMM energy minimization + short NVT)
  ala        run_fgf23_ala_scan.py            (EvoEF2 CDR alanine scan)
  saturation run_fgf23_saturation.py          (EvoEF2 19-AA saturation, top-2 CDR loops)
  stage4     run_fgf23_stage4_postfilter.py   (CHECK6/2.5/7/Thermo/AbLang2/CHECK8)
  stage5     run_fgf23_stage5_mmgbsa.py       (MM/GBSA confirmation, CUDA preferred)

Quick-start (server, env affmat active):
  # Full run from scratch:
  python scripts/run_fgf23_vam_pipeline.py

  # Resume after interruption:
  python scripts/run_fgf23_vam_pipeline.py --resume

  # GPU MM/GBSA:
  OPENMM_DEFAULT_PLATFORM=CUDA python scripts/run_fgf23_vam_pipeline.py --from-stage stage5 --resume

  # Skip CHECK8 for speed:
  python scripts/run_fgf23_vam_pipeline.py --resume --skip-check8

  # Server paths override:
  python scripts/run_fgf23_vam_pipeline.py --resume \\
      --suite-root /srv/AbEngineCore \\
      --project-dir /srv/projects/fgf23

  # Dry-run to validate paths:
  python scripts/run_fgf23_vam_pipeline.py --dry-run

Estimated server runtimes (8-core CPU / A100 GPU):
  setup:      ~2  min   (CPU, anarcii env — run separately once)
  relax:      ~3  min GPU  / ~20 min CPU
  ala:        ~35 min CPU  (EvoEF2 sequential, ~55 CDR positions)
  saturation: ~4  h   CPU  (EvoEF2 sequential, ~950 mutations)
  stage4:     ~1  h   (AbLang2 + CMC gates, resume-safe)
  stage5:     ~45 min GPU  / ~10 h CPU  (~25 mutants × 300 NVT steps)

  Total GPU: ~6 h end-to-end | Total CPU: ~15 h
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STAGE_ORDER = ["setup", "relax", "ala", "saturation", "stage4", "stage5"]

STAGE_SCRIPTS = {
    "setup":      "scripts/setup_fgf23_vam_numbering.py",
    "relax":      "scripts/run_fgf23_relax.py",
    "ala":        "scripts/run_fgf23_ala_scan.py",
    "saturation": "scripts/run_fgf23_saturation.py",
    "stage4":     "scripts/run_fgf23_stage4_postfilter.py",
    "stage5":     "scripts/run_fgf23_stage5_mmgbsa.py",
}

STAGE_DONE_FLAGS = {
    "setup":      "vam_boltz_scan/FGF23/FGF23_numbering.json",
    "relax":      "vam_boltz_scan/FGF23/FGF23_relaxed.pdb",
    "ala":        "vam_boltz_scan/FGF23/stage2_ala_scan/stage2_ala_scan.json",
    "saturation": "vam_boltz_scan/FGF23/stage3_saturation/stage3_saturation.json",
    "stage4":     "vam_boltz_scan/FGF23/stage4_postfilter/stage4_shortlist.json",
    "stage5":     "vam_boltz_scan/FGF23/stage5_mmgbsa/stage5_mmgbsa_beneficial.json",
}

STAGE_DESCRIPTIONS = {
    "setup":      "ANARCI CDR numbering → FGF23_numbering.json",
    "relax":      "OpenMM energy minimization (FF14SB + GBn2)",
    "ala":        "EvoEF2 CDR alanine scan",
    "saturation": "EvoEF2 19-AA saturation (top-2 CDR loops)",
    "stage4":     "Gate cascade: CHECK6/2.5/7/AbLang2/CHECK8",
    "stage5":     "MM/GBSA confirmation (OpenMM, CUDA preferred)",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stage_done(stage: str, project_dir: Path) -> bool:
    flag = STAGE_DONE_FLAGS.get(stage)
    if flag is None:
        return False
    return (project_dir / flag).is_file()


def _run_stage(
    stage: str,
    suite_root: Path,
    project_dir: Path,
    *,
    resume: bool,
    dry_run: bool,
    skip_check8: bool,
    relax_steps: int,
    mmgbsa_steps: int,
) -> bool:
    """Run a single stage. Returns True on success."""
    script = suite_root / STAGE_SCRIPTS[stage]
    cmd = [sys.executable, str(script)]

    # Stage-specific args
    if stage == "relax":
        cmd += ["--steps", str(relax_steps)]
        if str(project_dir) != str(suite_root / "projects/fgf 23"):
            cmd += ["--in-pdb",
                    str(project_dir / "boltz/FGF23/boltz_results_FGF23/predictions/FGF23/FGF23_model_0.pdb"),
                    "--out-pdb",
                    str(project_dir / "vam_boltz_scan/FGF23/FGF23_relaxed.pdb")]
    elif stage in ("saturation", "stage4", "stage5") and resume:
        cmd += ["--resume"]
    elif stage == "stage4" and skip_check8:
        cmd += ["--skip-check8"]
    elif stage == "stage5":
        cmd += ["--steps", str(mmgbsa_steps), "--suite-root", str(suite_root)]
    if dry_run:
        cmd += ["--dry-run"]

    print(f"\n{'─'*72}", flush=True)
    print(f"[pipeline] STAGE: {stage}", flush=True)
    print(f"[pipeline] CMD  : {' '.join(cmd)}", flush=True)
    print(f"[pipeline] START: {_utc_now()}", flush=True)
    t0 = time.time()

    result = subprocess.run(cmd, cwd=str(suite_root))
    elapsed = round(time.time() - t0, 1)
    success = result.returncode == 0

    print(f"[pipeline] END  : {_utc_now()}", flush=True)
    print(f"[pipeline] {'OK' if success else 'FAILED'}  ({elapsed}s)", flush=True)
    return success


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--resume",      action="store_true",
                   help="Skip stages whose done-flag file already exists.")
    p.add_argument("--from-stage",  choices=STAGE_ORDER, default=None,
                   help="Force-start from this stage (still skips if --resume and done).")
    p.add_argument("--dry-run",     action="store_true",
                   help="Pass --dry-run to each stage; no compute is performed.")
    p.add_argument("--skip-check8", action="store_true",
                   help="Skip OpenMM clash gate in Stage 4.")
    p.add_argument("--relax-steps", type=int, default=2000,
                   help="NVT steps in relax stage (default 2000).")
    p.add_argument("--mmgbsa-steps",type=int, default=300,
                   help="NVT steps per MM/GBSA mutant (default 300).")
    p.add_argument("--suite-root",  type=Path, default=ROOT,
                   help="AbEngineCore root on this machine (default: repo ROOT).")
    p.add_argument("--project-dir", type=Path, default=None,
                   help="FGF23 project dir override (default: <suite-root>/projects/fgf 23).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    suite_root  = args.suite_root.resolve()
    project_dir = (args.project_dir or suite_root / "projects/fgf 23").resolve()

    print("═" * 72, flush=True)
    print("FGF23-23F1128 VAM Pipeline  (VAM V1.4 / Boltz baseline)", flush=True)
    print(f"Suite root  : {suite_root}", flush=True)
    print(f"Project dir : {project_dir}", flush=True)
    print(f"Started     : {_utc_now()}", flush=True)
    print("═" * 72, flush=True)

    # Determine start index
    start_idx = 0
    if args.from_stage:
        start_idx = STAGE_ORDER.index(args.from_stage)

    pipeline_log = []
    for stage in STAGE_ORDER[start_idx:]:
        desc = STAGE_DESCRIPTIONS[stage]

        if args.resume and _stage_done(stage, project_dir):
            flag = STAGE_DONE_FLAGS[stage]
            print(f"\n[pipeline] SKIP {stage}  ({flag} exists)", flush=True)
            pipeline_log.append({"stage": stage, "status": "SKIPPED", "reason": "done_flag_exists"})
            continue

        success = _run_stage(
            stage, suite_root, project_dir,
            resume=args.resume,
            dry_run=args.dry_run,
            skip_check8=args.skip_check8,
            relax_steps=args.relax_steps,
            mmgbsa_steps=args.mmgbsa_steps,
        )

        pipeline_log.append({
            "stage": stage,
            "status": "OK" if success else "FAILED",
            "ts": _utc_now(),
        })

        if not success:
            print(f"\n[pipeline] ABORT — stage '{stage}' failed. Fix and re-run with --resume.",
                  file=sys.stderr, flush=True)
            _write_log(pipeline_log, project_dir)
            return 1

    _write_log(pipeline_log, project_dir)

    print("\n" + "═" * 72, flush=True)
    print("FGF23 VAM Pipeline COMPLETE", flush=True)
    print(f"Results in : {project_dir / 'vam_boltz_scan/FGF23'}", flush=True)
    print("Next step  : Human review of stage5_mmgbsa_beneficial.json → candidate selection", flush=True)
    print("═" * 72, flush=True)
    return 0


def _write_log(log: list[dict], project_dir: Path) -> None:
    try:
        log_path = project_dir / "vam_boltz_scan/FGF23/pipeline_log.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps({"log": log, "updated_at": _utc_now()}, indent=2),
                            encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
