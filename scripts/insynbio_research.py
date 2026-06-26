#!/usr/bin/env python3
"""InSynBio research pipeline orchestrator."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECTS_JSON = ROOT / "config" / "insynbio_research_projects.json"


def load_projects() -> dict[str, Any]:
    return json.loads(PROJECTS_JSON.read_text(encoding="utf-8")).get("projects", {})


def resolve(project: dict[str, Any], key: str) -> Path:
    return (ROOT / project[key]).resolve()


def resolve_manuscript_input(
    project: dict[str, Any],
    *,
    override: Path | None = None,
    use_docx: bool = False,
) -> Path:
    if override is not None:
        p = override.resolve()
        if not p.exists():
            raise SystemExit(f"Input not found: {p}")
        return p
    if use_docx and project.get("manuscript_docx"):
        docx = resolve(project, "manuscript_docx")
        if docx.exists():
            return docx
        print(f"Note: DOCX missing ({docx.name}), falling back to MD")
    return resolve(project, "manuscript_md")


def run_py(script: Path, *args: str, cwd: Path | None = None) -> None:
    cmd = [sys.executable, str(script), *args]
    print("\n>>", " ".join(cmd))
    if subprocess.run(cmd, cwd=str(cwd or ROOT)).returncode != 0:
        raise SystemExit(1)


def _passport_checkpoint(project_id: str, stage: int, artifact: str) -> None:
    """Write a Material Passport checkpoint if the passport file exists for this project."""
    passport_script = ROOT / "scripts" / "insynbio_material_passport.py"
    if not passport_script.exists():
        return
    # Only write if a passport file exists (don't create one automatically)
    passport_path = ROOT / "services" / "writing_memory" / f"{project_id}_passport.json"
    if not passport_path.exists():
        return
    try:
        subprocess.run(
            [sys.executable, str(passport_script), "--checkpoint",
             "--project", project_id,
             "--stage", str(stage),
             "--artifact", artifact],
            cwd=str(ROOT), timeout=15, capture_output=True,
        )
        print(f"  [Passport] Stage {stage} checkpoint: {artifact}")
    except Exception:
        pass  # Passport failure never blocks pipeline


def _require(project: dict[str, Any], key: str, workflow: str) -> Path:
    if key not in project:
        raise SystemExit(
            f"Workflow '{workflow}' requires project key '{key}'.\n"
            f"Add it to config/insynbio_research_projects.json for project '{project.get('_id', '?')}'."
        )
    return resolve(project, key)


def _optional_run(project: dict[str, Any], key: str, workflow: str) -> bool:
    """Run script at project[key] if present; skip with notice if missing."""
    if key not in project:
        print(f"  [SKIP] workflow={workflow}: no '{key}' in project config")
        return False
    run_py(resolve(project, key))
    return True


def workflow_literature(project: dict[str, Any]) -> None:
    ok = _optional_run(project, "literature_script", "literature")
    if ok:
        _passport_checkpoint(project["_id"], 1, "literature_script")


def workflow_format(project: dict[str, Any]) -> None:
    ok = _optional_run(project, "format_script", "format")
    if ok:
        _passport_checkpoint(project["_id"], 2, "format_script")


def workflow_bundle(project: dict[str, Any], *, audit_only: bool) -> None:
    if "bundle_profile" not in project or "workspace" not in project:
        print("  [SKIP] workflow=bundle: no bundle_profile/workspace in project config")
        return
    args = ["--profile", project["bundle_profile"], "--workspace", str(resolve(project, "workspace"))]
    if audit_only:
        args.append("--audit-only")
    else:
        args.append("--skip-format")
    run_py(ROOT / "scripts" / "build_submission_bundle.py", *args)


def workflow_manuscript_to_slides(
    project: dict[str, Any],
    *,
    out_name: str = "slides_plan_draft.md",
    input_path: Path | None = None,
    use_docx: bool = False,
    deck_key: str = "deck_dir",
) -> Path:
    deck = resolve(project, deck_key)
    src = resolve_manuscript_input(project, override=input_path, use_docx=use_docx)
    out = deck / out_name
    run_py(
        ROOT / "scripts" / "insynbio_manuscript_to_slides.py",
        "--input",
        str(src),
        "--out",
        str(out),
        "--paper-type",
        project.get("paper_type", "review"),
    )
    print(f"  Source: {src.name}")
    return out


def workflow_paper2ppt(project: dict[str, Any], *, plan: str, heroes: bool) -> None:
    deck = resolve(project, "deck_dir")
    plan_path = deck / plan
    if not plan_path.exists():
        raise SystemExit(f"Missing plan: {plan_path}")
    out = deck / "outputs_editable" / "review_deck.pptx"
    args = [
        "--plan",
        str(plan_path),
        "--out",
        str(out),
        "--paper-type",
        project.get("paper_type", "review"),
        "--lang",
        project.get("lang", "en"),
    ]
    hero = deck / "outputs_therasik_gemini_full" / "images"
    if heroes and hero.exists():
        args.extend(["--hero-images-dir", str(hero)])
    run_py(ROOT / "scripts" / "insynbio_paper2ppt.py", *args)


def workflow_scholarone_deck(project: dict[str, Any]) -> Path:
    deck_dir = resolve(project, "scholarone_deck_dir")
    build = deck_dir / "build_deck.py"
    if not build.exists():
        raise SystemExit(f"Missing: {build}")
    run_py(build, cwd=deck_dir)
    out = deck_dir / "outputs" / "Review_B_DeNovo_Presentation.pptx"
    if out.exists():
        print(f"  ScholarOne deck: {out}")
    return out


def _internal_dir(project: dict[str, Any]) -> Path:
    d = resolve(project, "workspace") / "submission_internal"
    d.mkdir(parents=True, exist_ok=True)
    return d


def workflow_figure_audit(project: dict[str, Any]) -> None:
    ws = resolve(project, "workspace")
    fig_glob = ws / "ScholarOne_Upload" / "Review_B_DeNovo" / "04_Figures_Tables" / "Figures"
    paths: list[str] = []
    if fig_glob.exists():
        paths.extend(str(p) for p in fig_glob.rglob("*") if p.suffix.lower() in {".tif", ".tiff", ".png"})
    if not paths:
        paths = [str(ws / "ScholarOne_Upload")]
    out = _internal_dir(project) / "figure_audit.json"
    run_py(ROOT / "scripts" / "insynbio_figure.py", "audit", *paths, "--out", str(out))


def workflow_paper_reader(project: dict[str, Any], *, input_path: Path | None = None, translate: str | None = None) -> None:
    src = resolve_manuscript_input(project, override=input_path)
    out = resolve(project, "workspace") / "reader" / "manuscript_reader.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    qc = out.with_suffix(".qc.json")
    args = [
        ROOT / "scripts" / "insynbio_paper_reader.py",
        "--input",
        str(src),
        "--out",
        str(out),
        "--qc-out",
        str(qc),
    ]
    if translate:
        args.extend(["--translate", translate])
    run_py(*args)
    print(f"  Reader: {out}")
    print(f"  QC: {qc}")


def workflow_rigor_audit(project: dict[str, Any], *, input_path: Path | None = None) -> None:
    src = resolve_manuscript_input(project, override=input_path)
    out = _internal_dir(project) / "manuscript_rigor.json"
    run_py(
        ROOT / "scripts" / "insynbio_rigor.py",
        "manuscript",
        "--input",
        str(src),
        "--with-polish-scan",
        "--journal",
        project.get("journal_key", "antibody_therapeutics"),
        "--out",
        str(out),
    )


def workflow_polish_scan(project: dict[str, Any], *, input_path: Path | None = None) -> None:
    src = resolve_manuscript_input(project, override=input_path)
    journal = project.get("journal_key", "antibody_therapeutics")
    out = _internal_dir(project) / "polish_scan.json"
    run_py(
        ROOT / "scripts" / "insynbio_polishing.py",
        "scan",
        "--input",
        str(src),
        "--journal",
        journal,
        "--out",
        str(out),
    )


def workflow_patent_outline(project: dict[str, Any], *, input_path: Path | None = None) -> None:
    src = resolve_manuscript_input(project, override=input_path)
    out = _internal_dir(project) / "patent_outline_draft.json"
    run_py(
        ROOT / "scripts" / "insynbio_paper_to_patent.py",
        "--input",
        str(src),
        "--out",
        str(out),
    )


def workflow_citation_library(project: dict[str, Any]) -> None:
    run_py(ROOT / "scripts" / "insynbio_citation.py", "build-library")


_PROJECT_TEMPLATE = {
    "label": "FILL_ME: Short project title",
    "manuscript_md": "paper/<project_id>/manuscript.md",
    "manuscript_docx": "paper/<project_id>/manuscript_FINAL.docx",
    "workspace": "paper/<project_id>",
    "paper_type": "FILL_ME: original_article | review | letter | case_report | methods",
    "lang": "en",
    "journal_key": "FILL_ME: see config/insynbio_therasik_brands.json or use custom",
    "_optional_keys": {
        "bundle_profile": "FILL_ME: submission bundle profile name (see journal-submission-bundle)",
        "deck_dir": "paper/<project_id>/deck_ppt",
        "scholarone_deck_dir": "paper/<project_id>/ScholarOne_Upload/deck_ppt",
        "literature_script": "scripts/fetch_<project_id>_literature.py",
        "format_script": "paper/<project_id>/format_submission.py",
    },
}


def cmd_init_project(project_id: str) -> None:
    """Scaffold a new project entry in insynbio_research_projects.json."""
    raw = json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
    if project_id in raw.get("projects", {}):
        raise SystemExit(f"Project '{project_id}' already exists.")
    entry = dict(_PROJECT_TEMPLATE)
    entry["manuscript_md"] = entry["manuscript_md"].replace("<project_id>", project_id)
    entry["manuscript_docx"] = entry["manuscript_docx"].replace("<project_id>", project_id)
    entry["workspace"] = entry["workspace"].replace("<project_id>", project_id)
    if "_optional_keys" in entry:
        del entry["_optional_keys"]
    raw.setdefault("projects", {})[project_id] = entry
    PROJECTS_JSON.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    ws = ROOT / "paper" / project_id
    ws.mkdir(parents=True, exist_ok=True)
    print(f"Project '{project_id}' scaffolded in config/insynbio_research_projects.json")
    print(f"Workspace dir created: {ws}")
    print(f"Edit all FILL_ME fields in the config, then: python scripts/insynbio_research.py --project {project_id} --workflow full")


def main() -> None:
    projects = load_projects()
    # Tag each project with its id for error messages
    for pid, cfg in projects.items():
        cfg["_id"] = pid

    ap = argparse.ArgumentParser(description="InSynBio research suite orchestrator")
    ap.add_argument("--list-projects", action="store_true")
    ap.add_argument("--init-project", metavar="PROJECT_ID",
                    help="Scaffold a new project entry (template) in research_projects.json")
    ap.add_argument("--project", choices=list(projects) or None)
    ap.add_argument(
        "--workflow",
        default="full",
        choices=[
            "literature",
            "format",
            "bundle",
            "manuscript-to-slides",
            "manuscript-to-slides-scholarone",
            "paper2ppt",
            "scholarone-deck",
            "figure-audit",
            "paper-reader",
            "polish-scan",
            "patent-outline",
            "citation-library",
            "rigor-audit",
            "submission-writer",
            "full",
        ],
    )
    ap.add_argument("--brand", choices=["insynbio", "therasik", "nextvivo"], default="insynbio",
                    help="Brand axis (format/tone); shared modules unchanged")
    ap.add_argument("--input", type=Path, help="Override manuscript .md/.docx/.pdf for manuscript-to-slides")
    ap.add_argument("--use-docx", action="store_true", help="Use manuscript_docx from project config")
    ap.add_argument("--audit-only", action="store_true")
    ap.add_argument("--skip-literature", action="store_true")
    ap.add_argument("--skip-format", action="store_true")
    ap.add_argument("--skip-bundle", action="store_true")
    ap.add_argument("--skip-paper2ppt", action="store_true")
    ap.add_argument("--with-scholarone-deck", action="store_true", help="full: also run ScholarOne deck_ppt build")
    ap.add_argument("--draft-slides", action="store_true")
    ap.add_argument("--no-heroes", action="store_true")
    ap.add_argument("--translate", choices=["kimi", "deepseek"], help="paper-reader: translate ZH blocks")
    args = ap.parse_args()

    if args.list_projects:
        for pid, cfg in projects.items():
            print(f"  {pid:<24} {cfg.get('label', '')}")
        return
    if args.init_project:
        cmd_init_project(args.init_project)
        return
    if not args.project:
        ap.error("--project required")

    p = projects[args.project]
    wf = args.workflow
    if args.brand != "insynbio":
        print(f"Brand: {args.brand} (shared research modules; content skills via insynbio-therasik-suite)")

    if wf == "literature":
        workflow_literature(p)
    elif wf == "format":
        workflow_format(p)
    elif wf == "bundle":
        workflow_bundle(p, audit_only=args.audit_only)
        _passport_checkpoint(p["_id"], 5, "submission_bundle")
    elif wf == "manuscript-to-slides":
        workflow_manuscript_to_slides(
            p,
            input_path=args.input,
            use_docx=args.use_docx,
            deck_key="deck_dir",
        )
    elif wf == "paper2ppt":
        workflow_paper2ppt(p, plan="slides_plan.md", heroes=not args.no_heroes)
    elif wf == "scholarone-deck":
        workflow_scholarone_deck(p)
    elif wf == "manuscript-to-slides-scholarone":
        workflow_manuscript_to_slides(
            p,
            out_name="slides_plan_draft.md",
            input_path=args.input,
            use_docx=args.use_docx,
            deck_key="scholarone_deck_dir",
        )
    elif wf == "figure-audit":
        workflow_figure_audit(p)
    elif wf == "paper-reader":
        workflow_paper_reader(p, input_path=args.input, translate=args.translate)
    elif wf == "polish-scan":
        workflow_polish_scan(p, input_path=args.input)
    elif wf == "patent-outline":
        workflow_patent_outline(p, input_path=args.input)
    elif wf == "citation-library":
        workflow_citation_library(p)
    elif wf == "rigor-audit":
        workflow_rigor_audit(p, input_path=args.input)
        _passport_checkpoint(p["_id"], 4, "rigor_audit")
    elif wf == "submission-writer":
        ws = Path(p.get("workspace", "paper/" + p["_id"]))
        ms = resolve(p, "manuscript_md") if "manuscript_md" in p else None
        sw = ROOT / "scripts" / "insynbio_submission_writer.py"
        # Map project journal_key to submission_writer preset key
        jk_map = {
            "antibody_therapeutics": "at",
            "nature_methods": "nature_methods",
            "cell": "cell",
            "plos_biology": "plos_biol",
        }
        jk = jk_map.get(p.get("journal_key", ""), "generic")
        if ms and ms.exists():
            run_py(sw, "highlights", "--journal", jk,
                   "--manuscript", str(ms), "--out", str(ws / "highlights_draft.md"))
        run_py(sw, "abstract", "--journal", jk,
               "--template", "--out", str(ws / "specs" / "abstract_spec.json"))
        run_py(sw, "cover-letter", "--journal", jk,
               "--template", "--out", str(ws / "specs" / "cover_spec.json"))
        run_py(sw, "response", "--template",
               "--out", str(ws / "specs" / "response_spec.json"))
        _passport_checkpoint(p["_id"], 6, "submission_writer")
        print(f"\n  Scaffolded: {ws}/specs/  (fill FILL_ME fields, then run individual subcommands)")
    elif wf == "full":
        if not args.skip_literature:
            workflow_literature(p)
        if not args.skip_format:
            workflow_format(p)
        if not args.skip_bundle:
            workflow_bundle(p, audit_only=False)
        if args.draft_slides:
            workflow_manuscript_to_slides(
                p,
                input_path=args.input,
                use_docx=args.use_docx,
            )
        if not args.skip_paper2ppt:
            plan = "slides_plan.md"
            if args.draft_slides and not (resolve(p, "deck_dir") / plan).exists():
                plan = "slides_plan_draft.md"
            workflow_paper2ppt(p, plan=plan, heroes=not args.no_heroes)
        if args.with_scholarone_deck:
            workflow_scholarone_deck(p)
    print("\nOK:", wf)


if __name__ == "__main__":
    main()
