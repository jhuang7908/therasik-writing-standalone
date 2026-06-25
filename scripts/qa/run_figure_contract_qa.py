"""
run_figure_contract_qa.py
Check that every figure declared in the project database has a valid figure contract.

A figure contract requires at minimum:
  - figure_id
  - core_conclusion  : the main scientific claim (>= 5 words, non-placeholder)
  - evidence_chain   : list/description of evidence panels (non-placeholder)
  - export_format    : svg | pdf | png (editable formats preferred)

Optional but warned if missing:
  - panel_map         : mapping of panels (A, B, C...) to conclusions
  - statistics_reported : p-values, CIs, n, error bars declared
  - editable_text     : whether text elements are editable (True/False)
  - source_data       : path or note indicating where raw data live

Input:  {project_root}/00_project_database/figures.csv
        OR manuscript scan fallback (markdown image refs + Figure N labels)
Output: {qa_dir}/figure_contract_QA.md
        Status: PASS or FAIL on line 1
Exit:   0 = PASS, 1 = FAIL
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from datetime import datetime, timezone


REQUIRED_FIELDS = ["figure_id", "core_conclusion", "evidence_chain", "export_format"]
WARNED_FIELDS = ["panel_map", "statistics_reported", "editable_text", "source_data"]
PLACEHOLDER_VALUES = {"tbd", "todo", "n/a", "na", "-", "none", "unknown"}
VALID_EXPORT_FORMATS = {"svg", "pdf", "png", "tiff", "eps"}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", required=True)
    p.add_argument("--qa-dir", default=None)
    p.add_argument("--figures-csv", default=None)
    return p.parse_args()


def load_figures_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def scan_manuscript_figures(manuscript_path: Path) -> list[str]:
    """
    Fallback: scan manuscript.md for figure references.
    Returns list of unique figure_id strings found.
    """
    if not manuscript_path.exists():
        return []
    text = manuscript_path.read_text(encoding="utf-8")
    ids = []
    for m in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', text):
        alt = m.group(1).strip()
        ids.append(alt if alt else Path(m.group(2)).stem)
    for m in re.finditer(r'\b(?:Figure|Fig\.?)\s+(\d+[A-Za-z]?)', text):
        ids.append("Figure_" + m.group(1))
    seen: set[str] = set()
    result = []
    for fid in ids:
        if fid not in seen:
            seen.add(fid)
            result.append(fid)
    return result


def check_figure_contract(row: dict) -> tuple[list[str], list[str]]:
    """Returns (warnings, errors) for one figure row."""
    errors: list[str] = []
    warnings: list[str] = []

    for field in REQUIRED_FIELDS:
        val = (row.get(field) or row.get(field.replace("_", " "), "") or "").strip()
        if not val:
            errors.append(f"Missing required field '{field}'")
            continue
        if field in ("evidence_chain", "core_conclusion") and val.lower() in PLACEHOLDER_VALUES:
            errors.append(f"'{field}' is a placeholder value ({val!r})")

    cc = (row.get("core_conclusion") or "").strip()
    if cc and cc.lower() not in PLACEHOLDER_VALUES and len(cc.split()) < 5:
        warnings.append("core_conclusion is very short (< 5 words); ensure it is a full scientific claim")

    ef = (row.get("export_format") or "").strip().lower()
    if ef and ef not in VALID_EXPORT_FORMATS:
        warnings.append(f"export_format '{ef}' is non-standard; prefer svg, pdf, png, tiff, or eps")
    if ef in ("png", "tiff") :
        warnings.append(f"export_format '{ef}' is raster; prefer svg or pdf for journal submission (editable text)")

    for field in WARNED_FIELDS:
        val = (row.get(field) or "").strip()
        if not val:
            warnings.append(f"Recommended field '{field}' is empty")

    return warnings, errors


def write_report(out_file: Path, status: str, body_lines: list[str]) -> int:
    content = [f"Status: {status}", ""] + body_lines
    out_file.write_text("\n".join(content) + "\n", encoding="utf-8")
    return 0 if status == "PASS" else 1


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    qa_dir = Path(args.qa_dir) if args.qa_dir else project_root / "03_QA"
    qa_dir.mkdir(parents=True, exist_ok=True)

    figures_csv = (
        Path(args.figures_csv)
        if args.figures_csv
        else project_root / "00_project_database" / "figures.csv"
    )
    manuscript_path = project_root / "01_manuscript" / "manuscript.md"
    out_file = qa_dir / "figure_contract_QA.md"

    timestamp = datetime.now(timezone.utc).isoformat()
    header = ["# Figure Contract QA", "", f"Generated: {timestamp}", ""]

    # No figures.csv — fall back to manuscript scan
    if not figures_csv.exists():
        manuscript_ids = scan_manuscript_figures(manuscript_path)
        if not manuscript_ids:
            print("PASS: no figures declared")
            return write_report(out_file, "PASS", header + [
                "No figures declared. If this manuscript includes figures, create",
                "`00_project_database/figures.csv` with at minimum: figure_id,",
                "core_conclusion, evidence_chain, export_format.",
                "",
                "Source: manuscript scan (no figures.csv found)",
            ])
        else:
            print(f"FAIL: {len(manuscript_ids)} figures in manuscript but no figures.csv")
            body = header + [
                f"Found {len(manuscript_ids)} figure reference(s) in manuscript but no `figures.csv`.",
                "Create `00_project_database/figures.csv` with columns:",
                "figure_id, core_conclusion, evidence_chain, export_format,",
                "panel_map, statistics_reported, editable_text, source_data",
                "",
                "Figures found in manuscript:",
            ] + [f"  - {fid}" for fid in manuscript_ids] + [
                "",
                "Source: manuscript scan (no figures.csv found)",
            ]
            return write_report(out_file, "FAIL", body)

    figures = load_figures_csv(figures_csv)
    source_note = f"Source: `{figures_csv.relative_to(project_root)}`"

    if not figures:
        print("PASS: figures.csv is empty")
        return write_report(out_file, "PASS", header + [
            "figures.csv is empty. No figures to check.", "", source_note,
        ])

    body = header + [source_note, f"Total figures: {len(figures)}", ""]
    total_errors = 0
    total_warnings = 0

    for row in figures:
        fid = (row.get("figure_id") or row.get("id") or "(no id)").strip()
        warnings, errors = check_figure_contract(row)
        total_errors += len(errors)
        total_warnings += len(warnings)
        tag = "PASS" if not errors else "FAIL"
        body.append(f"## {fid}  [{tag}]")
        if errors:
            body.append("")
            body.append("**Errors (blocking):**")
            body += [f"  - {e}" for e in errors]
        if warnings:
            body.append("")
            body.append("**Warnings (non-blocking):**")
            body += [f"  - {w}" for w in warnings]
        body.append("")

    final_status = "FAIL" if total_errors else "PASS"
    summary = (
        f"All {len(figures)} figure(s) have valid contracts. Warnings: {total_warnings}."
        if not total_errors
        else f"{total_errors} contract error(s) across {len(figures)} figure(s). Warnings: {total_warnings}."
    )
    print(f"{final_status}: {summary}")
    return write_report(out_file, final_status, body)


if __name__ == "__main__":
    sys.exit(main())
