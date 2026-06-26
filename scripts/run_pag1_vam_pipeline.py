#!/usr/bin/env python
"""PAG-1 VAM unattended pipeline orchestrator (Boltz baseline, VAM V1.7).

Chains the *fully deterministic* VAM stages into one resume-safe, server-runnable
job with a hard machine-audit gate. Human-decision stages (Stage-0 model choice,
cross-tool conflict / artifact judgement, combination selection, final tiering)
are intentionally NOT included here.

Stage order (each is checkpointed; --resume skips DONE stages):
  ala         scripts/run_pag1_ala_scan_boltz.py            (EvoEF2 CDR alanine scan)
  saturation  scripts/run_pag1_stage3_saturation_boltz.py   (EvoEF2 19-AA saturation)
  stage4      scripts/run_pag1_vam_postfilter_boltz.py       (CHECK6/2.5/7/Thermo/AntiFold/AbLang2/CHECK8)
  audit       scripts/validate_pag1_stage4_audit.py          (HARD GATE — abort on FAIL)
  stage5      scripts/run_pag1_stage5_mmgbsa_boltz.py         (MM/GBSA per-mutant)
  rebaseline  scripts/recalc_pag1_stage5_persite_baseline_boltz.py (per-site WT-self correction)

Precondition (checked, not produced here): each clone must have a relaxed Boltz
complex with QC PASS under the QC dir. Structure prediction + relax + model choice
remain a human-gated upstream step.

Usage (repo root, env affmat):
  conda run -n affmat python scripts/run_pag1_vam_pipeline.py --resume
  conda run -n affmat python scripts/run_pag1_vam_pipeline.py --clone 008 --resume
  conda run -n affmat python scripts/run_pag1_vam_pipeline.py --from-stage stage5 --resume
  conda run -n affmat python scripts/run_pag1_vam_pipeline.py --dry-run

VPS Stage-5 path override:
  python scripts/run_pag1_vam_pipeline.py --from-stage stage5 --resume \
      --vam-dir /srv/projects/pag1_vam/vam_boltz_scan \
      --qc-dir  /srv/projects/pag1_vam/boltz_relaxed_qc \
      --suite-root /root/Antibody-Engineer-Suite-MVP
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

CLONES = ["001", "008", "7M16"]
RELAXED_PDBS = {c: f"{c}_relaxed.pdb" for c in CLONES}
STAGE_ORDER = ["ala", "saturation", "stage4", "audit", "stage5", "rebaseline"]
HARD_GATE_STAGES = {"audit"}

# Execution mode of every stage in this orchestrator. All are SERVER-AUTO
# (deterministic thresholds, resume-safe). Human-judgement steps are intentionally
# NOT part of this pipeline and are listed in HUMAN_GATES.
STAGE_MODE = {
    "ala":        ("SERVER-AUTO", "EvoEF2 CDR alanine scan — deterministic ΔΔG"),
    "saturation": ("SERVER-AUTO", "EvoEF2 19-AA saturation — deterministic ΔΔG"),
    "stage4":     ("SERVER-AUTO", "Gate cascade CHECK6/2.5/7/Thermo/AntiFold/AbLang2/CHECK8 — fixed thresholds"),
    "audit":      ("SERVER-AUTO", "Machine audit — deterministic PASS/FAIL HARD GATE"),
    "stage5":     ("SERVER-AUTO", "MM/GBSA per-mutant — resume-safe"),
    "rebaseline": ("SERVER-AUTO", "Per-site WT-self baseline correction — V1.7 invariant"),
}

# Human decision points — deliberately OUTSIDE this pipeline.
HUMAN_GATES = [
    ("UPSTREAM  (before this pipeline)",
     "Structure prediction + relax + Boltz model choice; Stage-0 ipTM/PAE gate is "
     "auto-judged but a FAIL (which model / re-predict / change strategy) is a human call."),
    ("AFTER stage5/rebaseline",
     "Cross-tool conflict & artifact judgement — EvoEF2 vs MM/GBSA sign conflicts, "
     "desolvation artifacts (charge→hydrophobic), Met oxidation liability. MM/GBSA is "
     "noise-limited (±2–3 kcal/mol) on flexible peptides → cannot auto-decide sign."),
    ("AFTER single-point synthesis",
     "Combination (epistasis) selection — which single-point winners to combine."),
    ("BEFORE delivery",
     "Final candidate tiering, CHECK8-WARN acceptance, and client-report wording."),
]


def _print_mode_map(plan: list[str]) -> None:
    print("\n[pipeline] ── EXECUTION MODE MAP ──")
    print("[pipeline] SERVER-AUTO (this pipeline, no human input):")
    for stage in plan:
        mode, desc = STAGE_MODE[stage]
        gate = " [HARD GATE]" if stage in HARD_GATE_STAGES else ""
        print(f"[pipeline]   • {stage:11s} {mode}{gate} — {desc}")
    print("[pipeline] HUMAN-JUDGEMENT (NOT run here — you decide):")
    for when, what in HUMAN_GATES:
        print(f"[pipeline]   ! {when}: {what}")
    print("[pipeline] ───────────────────────")

DEFAULT_VAM_DIR = ROOT / "projects/PAG project/vam_boltz_scan"
DEFAULT_QC_DIR = ROOT / "projects/PAG project/boltz_relaxed_qc"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _precheck_structures(qc_dir: Path, clones: list[str]) -> list[str]:
    """Return list of problems (empty = OK). Verifies relaxed PDB + QC PASS exist."""
    problems: list[str] = []
    for cid in clones:
        pdb = qc_dir / RELAXED_PDBS[cid]
        if not pdb.is_file():
            problems.append(f"{cid}: missing relaxed PDB {pdb}")
            continue
        qc = qc_dir / f"{cid}_qc_results.json"
        if not qc.is_file():
            problems.append(f"{cid}: missing QC json {qc.name} (cannot confirm structure gate)")
            continue
        try:
            status = json.loads(qc.read_text(encoding="utf-8")).get("qc_status")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{cid}: QC json unreadable ({exc})")
            continue
        if status != "PASS":
            problems.append(f"{cid}: structure QC status={status} (expected PASS)")
    return problems


def _build_cmd(stage: str, args: argparse.Namespace) -> list[str]:
    py = args.python
    clones = args.clone
    s = "scripts"
    if stage == "ala":
        # nargs="+" style
        return [py, f"{s}/run_pag1_ala_scan_boltz.py", "--clone", *clones]
    if stage == "saturation":
        cmd = [py, f"{s}/run_pag1_stage3_saturation_boltz.py", "--clone", *clones]
        if args.resume:
            cmd.append("--resume")
        return cmd
    if stage == "stage4":
        # action="append" style: repeat --clone per id
        cmd = [py, f"{s}/run_pag1_vam_postfilter_boltz.py"]
        for c in clones:
            cmd += ["--clone", c]
        if args.resume:
            cmd.append("--resume")
        if args.skip_ablang:
            cmd.append("--skip-ablang")
        if args.check8_iterations is not None:
            cmd += ["--check8-iterations", str(args.check8_iterations)]
        return cmd
    if stage == "audit":
        # audits all clones; deterministic PASS/FAIL gate
        return [py, f"{s}/validate_pag1_stage4_audit.py"]
    if stage == "stage5":
        cmd = [py, f"{s}/run_pag1_stage5_mmgbsa_boltz.py",
               "--suite-root", str(args.suite_root),
               "--vam-dir", str(args.vam_dir),
               "--haddock-root", str(args.qc_dir),
               "--mmgbsa-steps", str(args.mmgbsa_steps)]
        for c in clones:
            cmd += ["--clone", c]
        if args.resume:
            cmd.append("--resume")
        return cmd
    if stage == "rebaseline":
        cmd = [py, f"{s}/recalc_pag1_stage5_persite_baseline_boltz.py",
               "--suite-root", str(args.suite_root),
               "--vam-dir", str(args.vam_dir),
               "--haddock-root", str(args.qc_dir),
               "--mmgbsa-steps", str(args.mmgbsa_steps)]
        for c in clones:
            cmd += ["--clone", c]
        if args.resume:
            cmd.append("--resume")
        return cmd
    raise ValueError(f"unknown stage {stage}")


def _load_checkpoint(path: Path) -> dict:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _save_checkpoint(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clone", nargs="+", choices=CLONES, default=CLONES,
                    help="Clone(s) to process (default: all three).")
    ap.add_argument("--from-stage", choices=STAGE_ORDER, default="ala",
                    help="First stage to run (default: ala).")
    ap.add_argument("--to-stage", choices=STAGE_ORDER, default="rebaseline",
                    help="Last stage to run (default: rebaseline).")
    ap.add_argument("--resume", action="store_true",
                    help="Skip stages marked DONE in checkpoint and pass --resume to sub-steps.")
    ap.add_argument("--force", action="store_true",
                    help="Re-run stages even if checkpoint marks them DONE.")
    ap.add_argument("--skip-ablang", action="store_true",
                    help="Defer AbLang2 in Stage-4 bulk (backfill separately).")
    ap.add_argument("--check8-iterations", type=int, default=500)
    ap.add_argument("--mmgbsa-steps", type=int, default=300)
    ap.add_argument("--vam-dir", type=Path, default=DEFAULT_VAM_DIR,
                    help="vam_boltz_scan dir (override for VPS).")
    ap.add_argument("--qc-dir", type=Path, default=DEFAULT_QC_DIR,
                    help="Relaxed-PDB QC dir holding {clone}_relaxed.pdb.")
    ap.add_argument("--suite-root", type=Path, default=ROOT,
                    help="Repo root on this machine (for Stage-5 wrappers).")
    ap.add_argument("--python", default=sys.executable, help="Python interpreter for sub-steps.")
    ap.add_argument("--skip-precheck", action="store_true",
                    help="Skip structure QC precondition check (not recommended).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the plan and per-stage commands; run nothing.")
    args = ap.parse_args(argv)

    i0 = STAGE_ORDER.index(args.from_stage)
    i1 = STAGE_ORDER.index(args.to_stage)
    if i0 > i1:
        print(f"ERROR: --from-stage {args.from_stage} is after --to-stage {args.to_stage}", file=sys.stderr)
        return 2
    plan = STAGE_ORDER[i0:i1 + 1]

    ckpt_path = args.vam_dir / "pipeline_run.json"
    ckpt = _load_checkpoint(ckpt_path)
    ckpt.setdefault("clones", args.clone)
    ckpt.setdefault("stages", {})

    print(f"[pipeline] clones={args.clone} plan={plan}")
    print(f"[pipeline] vam_dir={args.vam_dir}")
    print(f"[pipeline] qc_dir={args.qc_dir}")
    print(f"[pipeline] checkpoint={ckpt_path}")

    # Structure precondition (only needed if compute stages are in plan)
    needs_structures = any(st in plan for st in ("ala", "saturation", "stage4", "stage5", "rebaseline"))
    if needs_structures and not args.skip_precheck:
        problems = _precheck_structures(args.qc_dir, args.clone)
        if problems:
            print("[pipeline] STRUCTURE PRECHECK FAILED (human-gated upstream step incomplete):", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            print("[pipeline] Provide relaxed Boltz PDBs + QC PASS, or use --skip-precheck to override.",
                  file=sys.stderr)
            return 3
        print("[pipeline] structure precheck PASS for all selected clones.")

    _print_mode_map(plan)

    if args.dry_run:
        print("\n[pipeline] DRY-RUN plan:")
        for stage in plan:
            cmd = _build_cmd(stage, args)
            gate = " [HARD GATE]" if stage in HARD_GATE_STAGES else ""
            done = ckpt["stages"].get(stage, {}).get("status") == "DONE"
            skips = args.resume and done and not args.force and stage not in HARD_GATE_STAGES
            mark = " (DONE, would skip)" if skips else (
                " (always re-runs: hard gate)" if stage in HARD_GATE_STAGES else "")
            print(f"  {stage}{gate}{mark}:\n    {' '.join(cmd)}")
        return 0

    for stage in plan:
        st_rec = ckpt["stages"].get(stage, {})
        # Hard-gate stages (audit) always re-run: cheap, deterministic, and the
        # safety gate must reflect the current Stage-4 state.
        if (args.resume and not args.force and st_rec.get("status") == "DONE"
                and stage not in HARD_GATE_STAGES):
            print(f"\n[pipeline] SKIP {stage} (checkpoint DONE @ {st_rec.get('finished_at')})")
            continue

        cmd = _build_cmd(stage, args)
        gate = " [HARD GATE]" if stage in HARD_GATE_STAGES else ""
        print(f"\n[pipeline] === RUN {stage}{gate} ===")
        print(f"[pipeline] $ {' '.join(cmd)}")
        ckpt["stages"][stage] = {"status": "RUNNING", "started_at": _utc_now(),
                                 "cmd": " ".join(cmd)}
        _save_checkpoint(ckpt_path, ckpt)

        t0 = time.time()
        rc = subprocess.run(cmd, cwd=str(args.suite_root if stage in ("stage5", "rebaseline") else ROOT)).returncode
        elapsed = round(time.time() - t0, 1)

        if rc != 0:
            ckpt["stages"][stage] = {"status": "FAIL", "rc": rc,
                                     "finished_at": _utc_now(), "elapsed_s": elapsed,
                                     "cmd": " ".join(cmd)}
            _save_checkpoint(ckpt_path, ckpt)
            if stage in HARD_GATE_STAGES:
                print(f"\n[pipeline] HARD GATE '{stage}' FAILED (rc={rc}). "
                      f"Pipeline ABORTED — do not trust downstream Stage-5 results.", file=sys.stderr)
            else:
                print(f"\n[pipeline] stage '{stage}' FAILED (rc={rc}). Pipeline ABORTED.", file=sys.stderr)
            return rc

        ckpt["stages"][stage] = {"status": "DONE", "rc": 0,
                                 "finished_at": _utc_now(), "elapsed_s": elapsed,
                                 "cmd": " ".join(cmd)}
        _save_checkpoint(ckpt_path, ckpt)
        print(f"[pipeline] {stage} DONE ({elapsed}s)")

        if stage == "audit":
            print("[pipeline] HARD GATE passed — Stage-4 shortlist is trustworthy; "
                  "Stage-5 may proceed automatically.")

    print(f"\n[pipeline] COMPLETE — SERVER-AUTO stages {plan} finished for clones {args.clone}.")
    print("[pipeline] ⚠ HUMAN DECISION REQUIRED NEXT (not automated):")
    for when, what in HUMAN_GATES:
        if when.startswith("UPSTREAM"):
            continue
        print(f"[pipeline]   ! {when}: {what}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
