"""
render.py — InSynBio Unified Rendering API
============================================
Thin entry points that let project scripts produce .md + .pdf + .html
using the shared theme, without embedding any styling logic themselves.

Usage
-----
    from core.reporting.render import render_pdf, render_html, write_report_bundle

    render_pdf("path/to/report.md")                         # default InSynBio theme
    render_html("path/to/report.md")                        # HTML with CSS vars
    write_report_bundle("report.md", out_dir="./output")    # all three at once

Dual-report usage
-----------------
    from core.reporting.render import write_dual_bundle

    # One call → client_v1.0.pdf + internal_v1.0.pdf (+ matching .html)
    write_dual_bundle(
        spec,                    # ReportSpec (audience will be overridden)
        markdown_text,           # raw internal Markdown source
        out_dir="./output",
        formats=["pdf", "html"],
    )

Tagging convention in source Markdown
--------------------------------------
Wrap internal-only paragraphs with:

    <!-- INTERNAL_ONLY_START -->
    Algorithm details, raw tool output, file paths, etc.
    <!-- INTERNAL_ONLY_END -->

These blocks are removed automatically in the client version.

Version history
---------------
  v1.0  2026-04-02  Initial
  v1.1  2026-04-02  Added write_dual_bundle(), render_pdf_from_text(),
                    render_html_from_text() — dual-report architecture
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Optional

from core.reporting.theme import THEME
from core.reporting.translation import sanitize_for_client, client_reliability_block


def _resolve(p: str | Path) -> Path:
    return Path(p).resolve()


# ─────────────────────────────────────────────────────────────────────────────
# Markdown → PDF  (via fpdf2 engine, reads THEME tokens)
# ─────────────────────────────────────────────────────────────────────────────

def render_pdf(
    md_path: str | Path,
    out_path: Optional[str | Path] = None,
    *,
    theme: str = "insynbio",
    doc_number: str = "",
    page_title: str = "",
) -> Path:
    """Convert a Markdown file to PDF using fpdf2 with InSynBio theme.

    This wraps scripts/md_to_pdf.py but injects shared theme tokens so
    that colors, fonts, and spacing stay consistent.
    """
    md_path = _resolve(md_path)
    if out_path is None:
        out_path = md_path.with_suffix(".pdf")
    else:
        out_path = _resolve(out_path)

    suite_root = Path(__file__).resolve().parents[2]
    scripts = suite_root / "scripts"
    sys.path.insert(0, str(scripts))

    try:
        from md_to_pdf import MdPDF, parse_and_render

        _patch_md_pdf_colors()

        pdf = MdPDF()
        if page_title:
            pdf._page_title = page_title
        if doc_number:
            pdf._doc_number = doc_number

        text = md_path.read_text(encoding="utf-8")
        pdf.add_page()
        parse_and_render(text, pdf)
        pdf.output(str(out_path))
    finally:
        sys.path.remove(str(scripts))

    return out_path


def _patch_md_pdf_colors():
    """Monkey-patch md_to_pdf constants to use shared THEME tokens.

    This ensures md_to_pdf.py renders with the same visual identity as
    the ReportLab generators without modifying its source file.
    """
    import md_to_pdf as mod

    mod.H_COLORS = THEME.h_colors_rgb
    mod.TABLE_HEADER_BG = THEME.table_header_bg_rgb
    mod.TABLE_ALT_BG = THEME.table_alt_bg_rgb
    mod.TABLE_BORDER = THEME.table_border_rgb
    mod.TABLE_FONT_SIZE = int(THEME.cell_size)
    mod.CODE_BG = THEME.rgb("code_bg")

    mod.STOP_CELL_BG = THEME.rgb("stop_bg")
    mod.WARN_CELL_BG = THEME.rgb("warn_bg")
    mod.GO_CELL_BG   = THEME.rgb("go_bg")
    mod.STOP_COLOR   = THEME.rgb("stop_fg")
    mod.WARN_COLOR   = THEME.rgb("warn_fg")
    mod.GO_COLOR     = THEME.rgb("go_fg")


# ─────────────────────────────────────────────────────────────────────────────
# Markdown → HTML
# ─────────────────────────────────────────────────────────────────────────────

def render_html(
    md_path: str | Path,
    out_path: Optional[str | Path] = None,
    *,
    theme: str = "insynbio",
) -> Path:
    """Convert a Markdown file to a standalone HTML page with InSynBio styling."""
    md_path = _resolve(md_path)
    if out_path is None:
        out_path = md_path.with_suffix(".html")
    else:
        out_path = _resolve(out_path)

    try:
        import markdown as md_lib
    except ImportError:
        raise ImportError("pip install markdown   (required for HTML rendering)")

    text = md_path.read_text(encoding="utf-8")
    body = md_lib.markdown(
        text,
        extensions=["tables", "fenced_code", "toc", "attr_list"],
    )

    html = _HTML_TEMPLATE.replace("/* __THEME_CSS_VARS__ */", THEME.to_css_vars())
    html = html.replace("<!-- __BODY__ -->", body)

    out_path.write_text(html, encoding="utf-8")
    return out_path


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>InSynBio Report</title>
<style>
/* __THEME_CSS_VARS__ */

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--isb-font);
  color: var(--isb-body);
  font-size: var(--isb-body-size);
  line-height: 1.6;
  max-width: 960px;
  margin: 2rem auto;
  padding: 0 1.5rem;
}
h1 {
  font-size: var(--isb-h1-size);
  color: var(--isb-navy);
  border-bottom: 2px solid var(--isb-navy);
  padding-bottom: 4px;
  margin: 1.4em 0 0.5em;
}
h2 {
  font-size: var(--isb-h2-size);
  color: var(--isb-blue);
  margin: 1.2em 0 0.4em;
}
h3 {
  font-size: 10pt;
  color: var(--isb-navy);
  margin: 1em 0 0.3em;
}
p { margin: 0.4em 0; }
code {
  font-family: var(--isb-font-mono);
  background: var(--isb-code-bg);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 0.9em;
}
pre {
  background: var(--isb-code-bg);
  padding: 10px 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.88em;
  line-height: 1.45;
  margin: 0.5em 0;
}
pre code { background: none; padding: 0; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.5em 0;
  font-size: 9pt;
}
thead th {
  background: var(--isb-blue);
  color: #fff;
  font-weight: 600;
  padding: 6px 8px;
  text-align: center;
  border: 1px solid var(--isb-grid);
}
tbody td {
  padding: 5px 8px;
  border: 1px solid var(--isb-grid);
  vertical-align: top;
}
tbody tr:nth-child(even) { background: var(--isb-row-alt); }
blockquote {
  border-left: 3px solid var(--isb-blue);
  padding: 4px 12px;
  color: var(--isb-muted);
  margin: 0.5em 0;
}
hr {
  border: none;
  border-top: 1px solid var(--isb-grid);
  margin: 1em 0;
}
ul, ol { padding-left: 1.5em; margin: 0.4em 0; }
</style>
</head>
<body>
<!-- __BODY__ -->
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Markdown builder helper
# ─────────────────────────────────────────────────────────────────────────────

def build_report_markdown(
    spec,
    sections: list[str],
) -> str:
    """Assemble a Markdown document from a ReportSpec and section strings.

    Parameters
    ----------
    spec : ReportSpec
        Report metadata (fills in a header block).
    sections : list[str]
        Each entry is a Markdown string representing one report section.

    Returns
    -------
    str
        Full Markdown document.
    """
    header = (
        f"# {spec.title or spec.report_id}\n\n"
        f"****: {spec.report_id}  \n"
        f"****: {spec.version}  \n"
        f"****: {spec.report_date.isoformat()}  \n"
        f"****: {spec.institution} {spec.engine}  \n"
        f"****: {spec.confidentiality}\n\n---\n\n"
    )
    return header + "\n\n".join(sections)


# ─────────────────────────────────────────────────────────────────────────────
# In-memory render helpers (text → file, no existing .md required)
# ─────────────────────────────────────────────────────────────────────────────

def render_pdf_from_text(
    text: str,
    out_path: str | Path,
    *,
    doc_number: str = "",
    page_title: str = "",
) -> Path:
    """Write *text* to a temporary .md then render to PDF.

    Useful for dual-bundle where the client version is generated in memory
    and should not be persisted as a .md file on disk.
    """
    import tempfile
    out_path = _resolve(out_path)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    try:
        render_pdf(tmp_path, out_path, doc_number=doc_number, page_title=page_title)
    finally:
        tmp_path.unlink(missing_ok=True)
    return out_path


def render_html_from_text(
    text: str,
    out_path: str | Path,
) -> Path:
    """Write *text* to a temporary .md then render to HTML."""
    import tempfile
    out_path = _resolve(out_path)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    try:
        render_html(tmp_path, out_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# Bundle: one call → .md + .pdf + .html
# ─────────────────────────────────────────────────────────────────────────────

def write_report_bundle(
    md_path: str | Path,
    out_dir: Optional[str | Path] = None,
    *,
    doc_number: str = "",
    page_title: str = "",
) -> dict[str, Path]:
    """Generate PDF + HTML alongside an existing Markdown file.

    Returns a dict with keys ``md``, ``pdf``, ``html`` pointing to the
    output file paths.
    """
    md_path = _resolve(md_path)
    if out_dir is None:
        out_dir = md_path.parent
    else:
        out_dir = _resolve(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

    stem = md_path.stem
    pdf_out = out_dir / f"{stem}.pdf"
    html_out = out_dir / f"{stem}.html"

    render_pdf(md_path, pdf_out, doc_number=doc_number, page_title=page_title)
    render_html(md_path, html_out)

    return {"md": md_path, "pdf": pdf_out, "html": html_out}


# ─────────────────────────────────────────────────────────────────────────────
# Dual-bundle: internal + client from a single source Markdown
# ─────────────────────────────────────────────────────────────────────────────

def write_dual_bundle(
    md_path: str | Path,
    out_dir: Optional[str | Path] = None,
    *,
    doc_number: str = "",
    page_title: str = "",
    formats: list[str] | None = None,
    inject_reliability: bool = True,
    reliability_lang: str = "zh",
    reliability_anchor: str = "## ",
) -> dict[str, dict[str, Path]]:
    """Generate **internal** and **client** report bundles from one source.

    The source ``.md`` is treated as the internal (full-disclosure) version.
    A sanitised client version is derived automatically:

    1. ``<!-- INTERNAL_ONLY_START/END -->`` blocks are stripped.
    2. All ``CONTENT_TRANSLATION_RULES`` substitutions are applied.
    3. If *inject_reliability* is True and the source does NOT already
       contain a ``## `` section, a standard reliability
       statement is inserted before *reliability_anchor* (or appended).

    Parameters
    ----------
    md_path : str | Path
        Path to the internal Markdown source.
    out_dir : str | Path, optional
        Output directory.  Defaults to same directory as *md_path*.
    doc_number : str
        Document number injected into the PDF header.
    page_title : str
        Page title injected into the PDF header.
    formats : list of str, optional
        Which formats to generate.  Subset of ``["md", "pdf", "html"]``.
        Defaults to ``["md", "pdf", "html"]``.
    inject_reliability : bool
        If True, automatically inject the standard reliability statement
        into the client version if not already present.
    reliability_lang : str
        Language for the auto-injected reliability block ("zh" | "en").
    reliability_anchor : str
        Section heading before which the reliability block is inserted.
        If the heading is not found, the block is appended at the end.

    Returns
    -------
    dict
        ``{"internal": {"md": Path, "pdf": Path, ...},
           "client":   {"md": Path, "pdf": Path, ...}}``

        Keys within each sub-dict depend on *formats*.
    """
    if formats is None:
        formats = ["md", "pdf", "html"]

    md_path = _resolve(md_path)
    if out_dir is None:
        out_dir = md_path.parent
    else:
        out_dir = _resolve(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

    stem = md_path.stem
    internal_text = md_path.read_text(encoding="utf-8")

    # ── Build client text ──────────────────────────────────────────────
    client_text = sanitize_for_client(internal_text)

    if inject_reliability and "" not in client_text:
        reliability_md = client_reliability_block(reliability_lang)
        if reliability_anchor in client_text:
            client_text = client_text.replace(
                reliability_anchor,
                reliability_md + "\n\n" + reliability_anchor,
                1,
            )
        else:
            client_text = client_text + "\n\n" + reliability_md

    # ── Output filenames ───────────────────────────────────────────────
    int_stem = f"{stem}_internal"
    cli_stem = f"{stem}_client"

    results: dict[str, dict[str, Path]] = {"internal": {}, "client": {}}

    # ── Markdown ───────────────────────────────────────────────────────
    if "md" in formats:
        int_md = out_dir / f"{int_stem}.md"
        cli_md = out_dir / f"{cli_stem}.md"
        int_md.write_text(internal_text, encoding="utf-8")
        cli_md.write_text(client_text, encoding="utf-8")
        results["internal"]["md"] = int_md
        results["client"]["md"] = cli_md

    # ── PDF ────────────────────────────────────────────────────────────
    if "pdf" in formats:
        try:
            int_pdf = out_dir / f"{int_stem}.pdf"
            cli_pdf = out_dir / f"{cli_stem}.pdf"
            render_pdf(md_path, int_pdf, doc_number=doc_number, page_title=page_title)
            render_pdf_from_text(
                client_text, cli_pdf,
                doc_number=doc_number,
                page_title=page_title,
            )
            results["internal"]["pdf"] = int_pdf
            results["client"]["pdf"] = cli_pdf
        except Exception as exc:
            print(f"[render] PDF generation skipped: {exc}", file=__import__("sys").stderr)

    # ── HTML ───────────────────────────────────────────────────────────
    if "html" in formats:
        try:
            int_html = out_dir / f"{int_stem}.html"
            cli_html = out_dir / f"{cli_stem}.html"
            render_html(md_path, int_html)
            render_html_from_text(client_text, cli_html)
            results["internal"]["html"] = int_html
            results["client"]["html"] = cli_html
        except Exception as exc:
            print(f"[render] HTML generation skipped: {exc}", file=__import__("sys").stderr)

    return results
