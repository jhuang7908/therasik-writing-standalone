"""
InSynBio Material Passport CLI — cross-session manuscript state tracker.

Adapted from ARS academic-pipeline Material Passport Schema 9 (v3.9.4).
Works for any biomedical domain: oncology, immunology, gene therapy, drug discovery,
structural biology, clinical, computational, or antibody engineering.

Passport JSON stored at: projects/<name>/material_passport.json

Usage:
    python scripts/insynbio_material_passport.py --init --project my_crispr_paper --domain gene_therapy
    python scripts/insynbio_material_passport.py --checkpoint --project my_crispr_paper --stage 2
    python scripts/insynbio_material_passport.py --add-claim --project my_crispr_paper \\
        --claim "Off-target rate < 0.1%" --section "Results §2.3" --evidence "Fig. 2B"
    python scripts/insynbio_material_passport.py --status --project my_crispr_paper
    python scripts/insynbio_material_passport.py --resume --project my_crispr_paper
    python scripts/insynbio_material_passport.py --verify-claims --project my_crispr_paper
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PASSPORT_VERSION = "1.0"
PROJECTS_ROOT = Path("projects")

STAGE_NAMES = {
    1: "domain_detect + literature_ssot",
    2: "manuscript_md",
    3: "style_calibration",
    4: "write_draft",
    5: "fact_gate",
    6: "integrity_audit",
    7: "word_typeset",
    8: "expert_signoff",
    9: "passport_snapshot",
    10: "submission_bundle",
    11: "presentation",
    12: "archived",
}


def _passport_path(project: str) -> Path:
    return PROJECTS_ROOT / project / "material_passport.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(project: str) -> dict:
    p = _passport_path(project)
    if not p.exists():
        sys.exit(f"ERROR: passport not found for project '{project}'. Run --init first.")
    return json.loads(p.read_text(encoding="utf-8"))


def _save(passport: dict) -> None:
    project = passport["project"]
    p = _passport_path(project)
    p.parent.mkdir(parents=True, exist_ok=True)
    passport["updated_at"] = _now()
    p.write_text(json.dumps(passport, indent=2, ensure_ascii=False), encoding="utf-8")


def cmd_init(args: argparse.Namespace) -> None:
    p = _passport_path(args.project)
    if p.exists() and not args.force:
        sys.exit(f"ERROR: passport already exists at {p}. Use --force to overwrite.")

    stages = {
        str(n): {"name": name, "status": "pending"}
        for n, name in STAGE_NAMES.items()
    }
    passport = {
        "passport_version": PASSPORT_VERSION,
        "project": args.project,
        "domain": args.domain,
        "target_journal": args.journal,
        "created_at": _now(),
        "updated_at": _now(),
        "current_stage": 1,
        "stages": stages,
        "style_profile": None,
        "decisions": [],
        "claims": [],
        "artifacts": {
            "corpus_json": None,
            "manuscript_md": None,
            "final_docx": None,
            "bundle_dir": None,
            "pptx": None,
        },
        "ars_resume_hash": None,
        "notes": [],
    }
    _save(passport)
    print(f"[Passport] Initialized → {_passport_path(args.project)}")
    print(f"[Passport] Project: {args.project} | Domain: {args.domain}")


def cmd_checkpoint(args: argparse.Namespace) -> None:
    passport = _load(args.project)
    stage_key = str(args.stage)
    if stage_key not in passport["stages"]:
        sys.exit(f"ERROR: invalid stage {args.stage}. Valid: 1–{max(STAGE_NAMES)}")

    passport["stages"][stage_key]["status"] = "complete"
    passport["stages"][stage_key]["completed_at"] = _now()
    if args.artifact:
        passport["stages"][stage_key]["artifact"] = args.artifact
        # also update artifacts dict for known keys
        art_map = {
            2: "manuscript_md", 7: "final_docx", 10: "bundle_dir", 11: "pptx",
        }
        if args.stage in art_map:
            passport["artifacts"][art_map[args.stage]] = args.artifact

    passport["current_stage"] = args.stage + 1
    if args.note:
        passport["notes"].append({"stage": args.stage, "note": args.note, "at": _now()})
    if args.ars_hash:
        passport["ars_resume_hash"] = args.ars_hash

    _save(passport)
    stage_name = STAGE_NAMES.get(args.stage, "unknown")
    print(f"[Passport] Stage {args.stage} ({stage_name}) → COMPLETE")
    next_stage = args.stage + 1
    if next_stage in STAGE_NAMES:
        print(f"[Passport] Next: Stage {next_stage} — {STAGE_NAMES[next_stage]}")


def cmd_add_claim(args: argparse.Namespace) -> None:
    passport = _load(args.project)
    claim_id = f"C{len(passport['claims']) + 1}"
    evidence_list = [{"raw": e.strip()} for e in args.evidence.split(",") if e.strip()] if args.evidence else []
    passport["claims"].append({
        "claim_id": claim_id,
        "text": args.claim,
        "source_section": args.section or "",
        "evidence": evidence_list,
        "status": "pending",
        "added_at": _now(),
    })
    _save(passport)
    print(f"[Passport] Claim {claim_id} added: \"{args.claim[:60]}...\"")
    print(f"[Passport] Evidence: {args.evidence or 'none — mark with --verify-claims later'}")


def cmd_status(args: argparse.Namespace) -> None:
    passport = _load(args.project)
    print(f"\n=== Material Passport: {passport['project']} ===")
    print(f"Domain     : {passport['domain']}")
    print(f"Journal    : {passport.get('target_journal') or '(not specified)'}")
    print(f"Stage      : {passport['current_stage']} — {STAGE_NAMES.get(passport['current_stage'], '?')}")
    print(f"Updated    : {passport['updated_at']}")
    print()
    print("Stage progress:")
    for n, name in STAGE_NAMES.items():
        s = passport["stages"].get(str(n), {})
        status = s.get("status", "pending")
        icon = "✓" if status == "complete" else ("→" if n == passport["current_stage"] else "·")
        artifact = s.get("artifact", "")
        artifact_str = f" [{artifact}]" if artifact else ""
        print(f"  {icon} {n:2d}. {name:<35} {status}{artifact_str}")
    print()
    pending_claims = [c for c in passport["claims"] if c["status"] == "pending"]
    print(f"Claims: {len(passport['claims'])} total, {len(pending_claims)} unverified")
    if passport.get("ars_resume_hash"):
        print(f"ARS hash   : {passport['ars_resume_hash']}")


def cmd_resume(args: argparse.Namespace) -> None:
    passport = _load(args.project)
    stage = passport["current_stage"]
    stage_name = STAGE_NAMES.get(stage, "?")
    print(f"\n[Passport] Resume: {passport['project']} | Stage {stage} — {stage_name}")
    print(f"Domain: {passport['domain']} | Journal: {passport.get('target_journal') or 'TBD'}")

    completed = [k for k, v in passport["stages"].items() if v.get("status") == "complete"]
    print(f"Completed stages: {', '.join(completed) or 'none'}")

    pending_claims = [c for c in passport["claims"] if c["status"] == "pending"]
    if pending_claims:
        print(f"\n{len(pending_claims)} unverified claims — run --verify-claims after reviewing evidence.")

    if passport.get("ars_resume_hash"):
        print(f"\nARS resume: resume_from_passport={passport['ars_resume_hash']}")

    print(f"\nNext action: complete Stage {stage} ({stage_name}), then:")
    print(f"  python scripts/insynbio_material_passport.py --checkpoint --project {passport['project']} --stage {stage}")


def cmd_verify_claims(args: argparse.Namespace) -> None:
    passport = _load(args.project)
    claims = passport["claims"]
    if not claims:
        print("[Passport] No claims registered. PASS (nothing to verify).")
        return

    unverified = []
    for c in claims:
        has_evidence = bool(c.get("evidence"))
        if not has_evidence or c["status"] == "pending":
            unverified.append(c)

    if unverified:
        print(f"[Passport] WARN: {len(unverified)} uncited/unverified claims:")
        for c in unverified:
            print(f"  [{c['claim_id']}] {c['text'][:80]}")
            print(f"        Section: {c.get('source_section', 'unknown')} | Evidence: {c.get('evidence') or 'NONE'}")
    else:
        print(f"[Passport] PASS — all {len(claims)} claims have evidence entries.")
        print("  (Human review of evidence quality still required before submission.)")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="insynbio_material_passport",
        description="Cross-session manuscript state tracker for biomedical writing",
    )
    sub = parser.add_subparsers(dest="cmd")

    # --init
    p_init = parser.add_argument_group("init")
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--project", required=True)
    parser.add_argument("--domain", default="general_biomedical")
    parser.add_argument("--journal", default=None)
    parser.add_argument("--force", action="store_true")

    # --checkpoint
    parser.add_argument("--checkpoint", action="store_true")
    parser.add_argument("--stage", type=int, default=None)
    parser.add_argument("--artifact", default=None)
    parser.add_argument("--note", default=None)
    parser.add_argument("--ars-hash", default=None, dest="ars_hash")

    # --add-claim
    parser.add_argument("--add-claim", action="store_true")
    parser.add_argument("--claim", default=None)
    parser.add_argument("--section", default=None)
    parser.add_argument("--evidence", default=None, help="Comma-separated evidence refs")

    # --status / --resume / --verify-claims
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--verify-claims", action="store_true")

    args = parser.parse_args()

    if args.init:
        cmd_init(args)
    elif args.checkpoint:
        if args.stage is None:
            sys.exit("ERROR: --checkpoint requires --stage N")
        cmd_checkpoint(args)
    elif args.add_claim:
        if not args.claim:
            sys.exit("ERROR: --add-claim requires --claim 'text'")
        cmd_add_claim(args)
    elif args.status:
        cmd_status(args)
    elif args.resume:
        cmd_resume(args)
    elif args.verify_claims:
        cmd_verify_claims(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
