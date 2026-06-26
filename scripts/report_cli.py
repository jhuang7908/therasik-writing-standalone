"""
report_cli.py — InSynBio Unified Report CLI
=============================================
Single command-line entry point for rendering reports to PDF and HTML
using the shared InSynBio theme.

Usage
-----
    # Render a Markdown file to PDF (fpdf2 engine):
    python scripts/report_cli.py pdf report.md

    # Render a Markdown file to standalone HTML:
    python scripts/report_cli.py html report.md

    # Render both PDF + HTML alongside the .md:
    python scripts/report_cli.py bundle report.md

    # Specify output directory:
    python scripts/report_cli.py bundle report.md --outdir ./output

    # Set header text:
    python scripts/report_cli.py pdf report.md --title "" --doc-number "ISB-001"

    # ── Dual-report (internal + client) ──────────────────────────────────
    # Generate internal + client versions in one call:
    python scripts/report_cli.py dual report.md

    # Control output formats:
    python scripts/report_cli.py dual report.md --formats md html

    # Suppress auto-injected reliability statement (already present in source):
    python scripts/report_cli.py dual report.md --no-reliability

    # Full example:
    python scripts/report_cli.py dual projects/foo/report.md \\
        --outdir projects/foo/output \\
        --title "VHH Affinity Maturation Report" \\
        --doc-number "ISB-VAM-2026-004" \\
        --formats md pdf html
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE_ROOT))

from core.reporting.render import (
    render_pdf,
    render_html,
    write_report_bundle,
    write_dual_bundle,
)


def main():
    parser = argparse.ArgumentParser(
        prog="report_cli",
        description="InSynBio unified report renderer",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── pdf ──────────────────────────────────────────────────────────────
    pdf_p = sub.add_parser("pdf", help="Markdown → PDF")
    pdf_p.add_argument("input", help="Input Markdown file")
    pdf_p.add_argument("-o", "--output", help="Output PDF path")
    pdf_p.add_argument("--title", default="", help="Header left text")
    pdf_p.add_argument("--doc-number", default="", help="Header right text")

    # ── html ─────────────────────────────────────────────────────────────
    html_p = sub.add_parser("html", help="Markdown → HTML")
    html_p.add_argument("input", help="Input Markdown file")
    html_p.add_argument("-o", "--output", help="Output HTML path")

    # ── bundle ───────────────────────────────────────────────────────────
    bun_p = sub.add_parser("bundle", help="Markdown → PDF + HTML (side by side)")
    bun_p.add_argument("input", help="Input Markdown file")
    bun_p.add_argument("--outdir", help="Output directory (default: same as input)")
    bun_p.add_argument("--title", default="", help="Header left text")
    bun_p.add_argument("--doc-number", default="", help="Header right text")

    # ── dual ─────────────────────────────────────────────────────────────
    dual_p = sub.add_parser(
        "dual",
        help="Markdown → internal + client versions (PDF/HTML/MD)",
    )
    dual_p.add_argument("input", help="Input Markdown file (internal source)")
    dual_p.add_argument("--outdir", help="Output directory (default: same as input)")
    dual_p.add_argument("--title", default="", help="Header left text (PDF)")
    dual_p.add_argument("--doc-number", default="", help="Header right text (PDF)")
    dual_p.add_argument(
        "--formats",
        nargs="+",
        choices=["md", "pdf", "html"],
        default=["md", "pdf", "html"],
        metavar="FMT",
        help="Which formats to generate (default: md pdf html)",
    )
    dual_p.add_argument(
        "--no-reliability",
        action="store_true",
        help="Do NOT auto-inject the methodology reliability statement",
    )
    dual_p.add_argument(
        "--lang",
        choices=["zh", "en"],
        default="zh",
        help="Language for the auto-injected reliability statement (default: zh)",
    )

    args = parser.parse_args()

    # ── dispatch ──────────────────────────────────────────────────────────
    if args.command == "pdf":
        out = render_pdf(
            args.input,
            args.output,
            page_title=args.title,
            doc_number=args.doc_number,
        )
        print(f"PDF written: {out}")

    elif args.command == "html":
        out = render_html(args.input, args.output)
        print(f"HTML written: {out}")

    elif args.command == "bundle":
        paths = write_report_bundle(
            args.input,
            args.outdir,
            page_title=getattr(args, "title", ""),
            doc_number=getattr(args, "doc_number", ""),
        )
        for fmt, p in paths.items():
            print(f"  {fmt.upper():>4}: {p}")

    elif args.command == "dual":
        results = write_dual_bundle(
            args.input,
            args.outdir,
            page_title=args.title,
            doc_number=args.doc_number,
            formats=args.formats,
            inject_reliability=not args.no_reliability,
            reliability_lang=args.lang,
        )
        _print_dual_results(results)


def _print_dual_results(results: dict) -> None:
    """Pretty-print the file paths from write_dual_bundle()."""
    total = sum(len(v) for v in results.values())
    print(f"\n  Dual report bundle — {total} file(s) generated\n")
    for audience, paths in results.items():
        tag = "[INTERNAL]" if audience == "internal" else "[CLIENT  ]"
        for fmt, p in paths.items():
            print(f"  {tag}  {fmt.upper():>4}: {p}")
    print()


if __name__ == "__main__":
    main()
