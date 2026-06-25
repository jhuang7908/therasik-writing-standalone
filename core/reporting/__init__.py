"""
InSynBio Unified Reporting Framework
=====================================
Single source of truth for report styles, metadata, naming, and rendering.

Usage
-----
    from core.reporting import theme, spec, render

    # Build Markdown content, then render:
    render.render_pdf("report.md")
    render.render_pdf("report.md", theme="insynbio")

    # Or bundle all outputs at once:
    render.write_report_bundle("report.md", out_dir="./output")
"""

from core.reporting.spec import ReportSpec, ReportFamily, Audience
from core.reporting.theme import THEME
from core.reporting import render

__all__ = ["ReportSpec", "ReportFamily", "Audience", "THEME", "render"]
