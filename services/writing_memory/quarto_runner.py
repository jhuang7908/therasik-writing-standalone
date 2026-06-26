"""Quarto manuscript renderer for the writing_memory service.

Converts a structured manuscript JSON (the same shape produced by
`/draft_section` + `/finalize_package`) into a Quarto `.qmd` source,
then runs `quarto render` to produce DOCX / PDF / HTML / JATS.

Public API:
    is_quarto_available() -> bool
    render_manuscript(manuscript: dict, *, fmt: str = "docx") -> Path
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

SERVICE_ROOT = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = SERVICE_ROOT / "quarto_templates" / "default"

_QUARTO_FALLBACKS: tuple[Path, ...] = (
    Path("C:/Program Files/Quarto/bin/quarto.exe"),
    Path("/usr/local/bin/quarto"),
    Path("/opt/quarto/bin/quarto"),
    Path("/opt/homebrew/bin/quarto"),
)


def _resolve_quarto() -> str | None:
    cli = shutil.which("quarto")
    if cli:
        return cli
    for cand in _QUARTO_FALLBACKS:
        if cand.is_file():
            return str(cand)
    return None


def is_quarto_available() -> bool:
    return _resolve_quarto() is not None


def _yaml_quote(value: Any) -> str:
    if value is None:
        return "~"
    s = str(value)
    if any(c in s for c in ":\n\"'#"):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def _build_qmd(manuscript: dict[str, Any], *, output_format: str) -> str:
    """Render manuscript dict to a Quarto `.qmd` Markdown source."""
    title = manuscript.get("title") or "Untitled manuscript"
    authors = manuscript.get("authors") or "[FILL: authors]"
    abstract = manuscript.get("abstract_text") or ""
    sections = manuscript.get("sections") or []
    references = manuscript.get("reference_list") or []
    figure_legends = manuscript.get("figure_legends") or []
    journal = manuscript.get("target_journal") or "frontiers_immunology"
    article_type = manuscript.get("article_type") or "research"
    declarations = manuscript.get("declarations") or {}

    yaml_lines = [
        "---",
        f"title: {_yaml_quote(title)}",
        f"author: {_yaml_quote(authors)}",
        f"date: today",
        f"date-format: 'YYYY-MM-DD'",
        f"format:",
        f"  {output_format}:",
        f"    toc: false",
        f"    number-sections: false",
        f"    reference-location: section",
        f"keywords: [{journal}, {article_type}]",
        "---",
        "",
    ]

    body: list[str] = []

    if abstract:
        body.append("# Abstract\n")
        body.append(abstract.strip())
        body.append("")

    for sec in sections:
        if isinstance(sec, dict):
            heading = sec.get("title") or sec.get("key", "Section").title()
            text = sec.get("text") or ""
        else:
            heading, text = "Section", str(sec)
        body.append(f"# {heading}\n")
        body.append(text.strip())
        body.append("")

    if declarations:
        body.append("# Declarations\n")
        for key, val in declarations.items():
            if not val:
                continue
            label = key.replace("_", " ").title()
            if isinstance(val, list):
                if not val:
                    continue
                val = "; ".join(
                    f"{item.get('author', '?')}: {item.get('roles', '?')}"
                    if isinstance(item, dict) else str(item)
                    for item in val
                )
            body.append(f"**{label}.** {val}\n")
        body.append("")

    if figure_legends:
        body.append("# Figure Legends\n")
        for leg in figure_legends:
            if isinstance(leg, dict):
                num = leg.get("figure_number", "?")
                ftitle = leg.get("title") or ""
                full = leg.get("rendered_full") or leg.get("legend_text") or ""
                body.append(f"**Figure {num}.** {ftitle}")
                if full:
                    body.append("")
                    body.append(full)
                body.append("")

    if references:
        body.append("# References\n")
        for i, ref in enumerate(references, 1):
            body.append(f"{i}. {ref}\n")

    return "\n".join(yaml_lines + body)


def render_manuscript(
    manuscript: dict[str, Any],
    *,
    fmt: str = "docx",
    workdir: Path | None = None,
) -> dict[str, Any]:
    """Render manuscript JSON to `fmt` (docx | pdf | html | jats).

    Returns dict with `output_path`, `qmd_path`, `quarto_available`, `stderr`.
    """
    quarto_bin = _resolve_quarto()
    if not quarto_bin:
        return {
            "quarto_available": False,
            "error": "quarto CLI not found",
            "output_path": None,
            "qmd_path": None,
        }

    fmt = fmt.lower()
    if fmt not in {"docx", "pdf", "html", "jats"}:
        raise ValueError(f"Unsupported fmt: {fmt}")

    workdir = workdir or Path(tempfile.mkdtemp(prefix="quarto_render_"))
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    qmd_path = workdir / "manuscript.qmd"
    qmd_path.write_text(_build_qmd(manuscript, output_format=fmt), encoding="utf-8")

    result = subprocess.run(
        [quarto_bin, "render", str(qmd_path), "--to", fmt],
        cwd=str(workdir),
        capture_output=True,
        text=True,
        timeout=300,
    )

    expected_ext = {"docx": ".docx", "pdf": ".pdf", "html": ".html", "jats": ".xml"}[fmt]
    candidates = list(workdir.glob(f"manuscript{expected_ext}"))
    output_path = candidates[0] if candidates else None

    return {
        "quarto_available": True,
        "output_path": str(output_path) if output_path else None,
        "qmd_path": str(qmd_path),
        "fmt": fmt,
        "exit_code": result.returncode,
        "stderr": result.stderr[-2000:] if result.stderr else "",
        "stdout": result.stdout[-2000:] if result.stdout else "",
    }


__all__ = [
    "is_quarto_available",
    "render_manuscript",
]
