"""
theme.py — InSynBio Unified Visual Theme
==========================================
SINGLE SOURCE OF TRUTH for all color tokens, font paths, and spacing
constants used across:
  - ReportLab PDF generators   (hex strings → colors.HexColor)
  - fpdf2 md_to_pdf.py         (RGB tuples)
  - HTML/CSS report templates   (hex strings)

Every report renderer imports from here.  Do NOT redefine these
constants in project-level scripts.

Visual identity reference:
  - Primary:   #1F3864  ( / navy)
  - Secondary: #2E5496  ( / blue)
  - Accent:    #C00000  ()
  - Body:      #222222  ()
  - Muted:     #555555  ()
  - Alt row:   #EEF2F9  ()
  - Grid:      #BBBBBB  ()
  - HR rule:   #AAAAAA  ()
  - Code bg:   #F5F5F5  ()
  - Seq bg:    #F0F4F0  ()
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


@dataclass(frozen=True)
class InSynBioTheme:
    """Immutable design-token container."""

    # ── Colors (hex) ─────────────────────────────────────────────────────
    navy: str       = "#1F3864"
    blue: str       = "#2E5496"
    accent: str     = "#C00000"
    body: str       = "#222222"
    muted: str      = "#555555"
    subtitle: str   = "#444444"
    row_alt: str    = "#EEF2F9"
    grid: str       = "#BBBBBB"
    hrule: str      = "#AAAAAA"
    code_bg: str    = "#F5F5F5"
    seq_bg: str     = "#F0F4F0"
    highlight_row: str = "#FFF3EC"

    stop_bg: str    = "#FDECEA"
    warn_bg: str    = "#FFF8E1"
    go_bg: str      = "#E8F5E9"
    stop_fg: str    = "#BE2828"
    warn_fg: str    = "#C88C00"
    go_fg: str      = "#1E8232"

    # ── Fonts (Windows paths, fallbacks) ─────────────────────────────────
    font_regular_path: str = r"C:\Windows\Fonts\msyh.ttc"
    font_bold_path: str    = r"C:\Windows\Fonts\msyhbd.ttc"
    font_mono: str         = "Courier"
    font_fallback_regular: str = "Helvetica"
    font_fallback_bold: str    = "Helvetica-Bold"

    # ── Spacing / sizing ─────────────────────────────────────────────────
    page_margin_lr: float  = 2.2    # cm
    page_margin_top: float = 2.3    # cm
    page_margin_bot: float = 2.2    # cm

    h1_size: float   = 13.0
    h2_size: float   = 11.0
    h3_size: float   = 10.0
    body_size: float  = 10.0
    cell_size: float  = 9.0
    note_size: float  = 8.5
    code_size: float  = 8.5
    meta_size: float  = 9.0
    title_size: float = 20.0

    h1_leading: float   = 17.0
    h2_leading: float   = 15.0
    body_leading: float = 15.0
    cell_leading: float = 12.0

    table_grid_thin: float  = 0.4
    table_grid_thick: float = 0.8
    hr_thickness: float     = 0.5

    # ── Header / footer ──────────────────────────────────────────────────
    header_font_size: float = 7.5
    header_line_y_offset: float = 1.55    # cm from top
    header_text_y_offset: float = 1.30
    footer_line_y_offset: float = 1.35    # cm from bottom
    footer_text_y_offset: float = 0.90

    # ── Helpers ──────────────────────────────────────────────────────────

    def rgb(self, attr: str) -> tuple[int, int, int]:
        """Return RGB tuple for a named color attribute.

        Useful for fpdf2 which takes (R, G, B) instead of hex strings.
        """
        return _hex_to_rgb(getattr(self, attr))

    @property
    def h_colors_rgb(self) -> dict[int, tuple[int, int, int]]:
        """Heading-level → RGB for fpdf2 md_to_pdf renderer."""
        return {
            1: self.rgb("navy"),
            2: self.rgb("blue"),
            3: _hex_to_rgb("#3C6EB4"),
        }

    @property
    def table_header_bg_rgb(self) -> tuple[int, int, int]:
        return self.rgb("blue")

    @property
    def table_alt_bg_rgb(self) -> tuple[int, int, int]:
        return self.rgb("row_alt")

    @property
    def table_border_rgb(self) -> tuple[int, int, int]:
        return self.rgb("grid")

    def font_regular_resolved(self) -> str:
        """Return the actual font file path, falling back gracefully."""
        if os.path.exists(self.font_regular_path):
            return self.font_regular_path
        for alt in [r"C:\Windows\Fonts\msyhbd.ttc",
                    r"C:\Windows\Fonts\simsun.ttc"]:
            if os.path.exists(alt):
                return alt
        return ""

    def font_bold_resolved(self) -> str:
        if os.path.exists(self.font_bold_path):
            return self.font_bold_path
        return ""

    def to_css_vars(self) -> str:
        """Emit CSS custom properties for HTML report templates."""
        return f"""\
:root {{
  --isb-navy:       {self.navy};
  --isb-blue:       {self.blue};
  --isb-accent:     {self.accent};
  --isb-body:       {self.body};
  --isb-muted:      {self.muted};
  --isb-row-alt:    {self.row_alt};
  --isb-grid:       {self.grid};
  --isb-code-bg:    {self.code_bg};
  --isb-seq-bg:     {self.seq_bg};
  --isb-stop-bg:    {self.stop_bg};
  --isb-warn-bg:    {self.warn_bg};
  --isb-go-bg:      {self.go_bg};
  --isb-stop-fg:    {self.stop_fg};
  --isb-warn-fg:    {self.warn_fg};
  --isb-go-fg:      {self.go_fg};
  --isb-font:       'Microsoft YaHei', 'Noto Sans SC', sans-serif;
  --isb-font-mono:  'Courier New', Courier, monospace;
  --isb-h1-size:    {self.h1_size}pt;
  --isb-h2-size:    {self.h2_size}pt;
  --isb-body-size:  {self.body_size}pt;
}}"""


# Module-level singleton — all renderers import this.
THEME = InSynBioTheme()
