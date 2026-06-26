"""Step A: purge boilerplate → Vale lint → Quarto DOCX from figdraft/revised JSON."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent.parent))

os.environ["PATH"] = (
    r"C:\Program Files\Quarto\bin;"
    + os.environ.get("PATH", "")
    + ";"
    + r"C:\Users\NextVivo\AppData\Local\Microsoft\WinGet\Packages"
    r"\errata-ai.Vale_Microsoft.Winget.Source_8wekyb3d8bbwe"
)

from services.writing_memory.vale_runner import lint_text, purge_ai_boilerplate
from services.writing_memory.quarto_runner import is_quarto_available, render_manuscript

SRC = Path(__file__).parent / "huNSG_QUAD_revised.json"
if not SRC.exists():
    SRC = Path(__file__).parent / "huNSG_QUAD_figdraft_20260527T011815Z.json"
OUT_DIR = Path(__file__).parent / "_pipeline_out"
OUT_DIR.mkdir(exist_ok=True)

def main() -> int:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    plan = d.get("plan") or {}
    refs = d.get("merged_reference_list") or []
    title = (
        plan.get("suggested_title")
        or "Development of human innate immune responses in a humanized mouse model "
           "expressing four human myelopoiesis transgenes"
    )

    sections_out: list[dict] = []
    purge_log: list[dict] = []
    lint_all: list[dict] = []

    for s in d.get("sections") or []:
        key = s.get("key", "?")
        text = s.get("text") or ""
        if key not in ("methods", "materials_methods") and text:
            cleaned, removed = purge_ai_boilerplate(text)
            if removed:
                purge_log.append({"section": key, "n_removed": len(removed), "samples": removed[:8]})
                text = cleaned
        summary = lint_text(text)
        lint_all.append({"section": key, **summary.as_dict()})
        sections_out.append({"key": key, "title": key.title(), "text": text})

    abstract = next((x["text"] for x in sections_out if x["key"] == "abstract"), "")
    body_sections = [x for x in sections_out if x["key"] != "abstract"]

    manuscript = {
        "title": title,
        "target_journal": d.get("target_journal") or "frontiers_immunology",
        "article_type": "research",
        "authors": "[FILL: Author names, affiliations]",
        "abstract_text": abstract,
        "sections": body_sections,
        "reference_list": refs,
        "declarations": {
            "data_availability": "[FILL: Data availability statement]",
            "competing_interests": "The authors declare no competing interests.",
            "ethics_statement": (
                "Animal experiments were approved by the Institutional Animal Ethics Committee."
            ),
        },
    }

    report = {
        "source": str(SRC),
        "finalized_at": datetime.now(timezone.utc).isoformat(),
        "purge_log": purge_log,
        "lint_by_section": lint_all,
        "total_lint_findings": sum(x.get("total", 0) for x in lint_all),
    }
    report_path = OUT_DIR / "finalize_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if not is_quarto_available():
        print("Quarto not available — saved report only:", report_path)
        return 1

    workdir = OUT_DIR / "quarto"
    workdir.mkdir(exist_ok=True)
    rendered = render_manuscript(manuscript, fmt="docx", workdir=workdir)
    out = rendered.get("output_path")
    if out:
        dest = OUT_DIR / "huNSG_QUAD_final.docx"
        Path(out).replace(dest)
        print(f"Purge: {len(purge_log)} sections touched")
        print(f"Vale total findings: {report['total_lint_findings']}")
        print(f"DOCX: {dest}")
        print(f"Report: {report_path}")
        return 0
    print("Quarto failed:", rendered.get("stderr"))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
