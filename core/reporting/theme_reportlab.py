"""
theme_reportlab.py — ReportLab style adapter
==============================================
Reads color/font/size tokens from ``core.reporting.theme.THEME``
and produces ready-to-use ReportLab ParagraphStyles, TableStyles,
and helper functions.

Project PDF generators should import from HERE, not redefine styles.

Usage
-----
    from core.reporting.theme_reportlab import RL  # singleton

    story.append(Paragraph("Title", RL.TITLE))
    story.append(RL.hr())
    story.append(RL.make_table(data, col_widths))
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, SimpleDocTemplate
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from core.reporting.theme import THEME
from core.reporting.spec import ReportSpec


def _hex(c: str):
    return colors.HexColor(c)


class _ReportLabTheme:
    """Lazily-initialized ReportLab theme tied to THEME tokens.

    Any attribute access (style names, FONT, FONTBD, or shorthand methods)
    triggers one-time font registration and style construction.
    """

    _STYLE_ATTRS = {
        "TITLE", "SUBTITLE", "H1", "H2", "H3", "BODY", "BODYSM", "BULLET",
        "CODE", "SEQ", "META", "NOTE", "CELL", "CELLBD", "CELLC", "CELLRD",
        "CELLHDR", "SEQ_HDR",
    }

    def __init__(self):
        self._initialized = False
        self._FONT = None
        self._FONTBD = None

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if not self._initialized:
            self._do_init()
            return getattr(self, name)
        raise AttributeError(f"_ReportLabTheme has no attribute {name!r}")

    def _do_init(self):
        self._initialized = True
        self._FONT = self._register_font(
            "MainFont",
            THEME.font_regular_resolved(),
            THEME.font_fallback_regular,
        )
        self._FONTBD = self._register_font(
            "MainFontBd",
            THEME.font_bold_resolved(),
            THEME.font_fallback_bold,
        )
        self._build_styles()

    def _ensure_init(self):
        if not self._initialized:
            self._do_init()

    @staticmethod
    def _register_font(name: str, path: str, fallback: str) -> str:
        if path and os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                pass
        return fallback

    def _S(self, name: str, **kw) -> ParagraphStyle:
        kw.setdefault("fontName", self._FONT)
        return ParagraphStyle(name, **kw)

    def _build_styles(self):
        T = THEME
        F, FB = self._FONT, self._FONTBD

        self.TITLE = self._S("ISB_TITLE", fontName=FB, fontSize=T.title_size,
            leading=26, textColor=_hex(T.navy), spaceAfter=6, alignment=TA_CENTER)
        self.SUBTITLE = self._S("ISB_SUBTITLE", fontSize=11, leading=14,
            textColor=_hex(T.subtitle), spaceAfter=8, alignment=TA_CENTER)
        self.H1 = self._S("ISB_H1", fontName=FB, fontSize=T.h1_size,
            leading=T.h1_leading, textColor=_hex(T.navy), spaceBefore=14, spaceAfter=5)
        self.H2 = self._S("ISB_H2", fontName=FB, fontSize=T.h2_size,
            leading=T.h2_leading, textColor=_hex(T.blue), spaceBefore=10, spaceAfter=4)
        self.H3 = self._S("ISB_H3", fontName=FB, fontSize=T.h3_size,
            leading=14, textColor=_hex(T.navy), spaceBefore=8, spaceAfter=3)
        self.BODY = self._S("ISB_BODY", fontSize=T.body_size,
            leading=T.body_leading, spaceAfter=4, alignment=TA_LEFT, textColor=_hex(T.body))
        self.BODYSM = self._S("ISB_BODYSM", fontSize=9, leading=14,
            spaceAfter=3, alignment=TA_LEFT, textColor=_hex(T.body))
        self.BULLET = self._S("ISB_BULLET", fontSize=T.body_size,
            leading=14, spaceAfter=3, leftIndent=16, textColor=_hex(T.body))
        self.CODE = ParagraphStyle("ISB_CODE", fontName=THEME.font_mono,
            fontSize=T.code_size, leading=12, spaceAfter=3, leftIndent=8,
            rightIndent=8, backColor=_hex(T.code_bg), textColor=_hex(T.body))
        self.SEQ = ParagraphStyle("ISB_SEQ", fontName=THEME.font_mono,
            fontSize=T.code_size, leading=12, spaceAfter=2, leftIndent=8,
            rightIndent=8, backColor=_hex(T.seq_bg), textColor=_hex(T.body))
        self.META = self._S("ISB_META", fontSize=T.meta_size, leading=12,
            textColor=_hex(T.muted), spaceAfter=3)
        self.NOTE = self._S("ISB_NOTE", fontSize=T.note_size, leading=12,
            textColor=_hex(T.muted), spaceAfter=3, leftIndent=10, alignment=TA_LEFT)
        self.CELL = self._S("ISB_CELL", fontSize=T.cell_size,
            leading=T.cell_leading, textColor=_hex(T.body))
        self.CELLBD = self._S("ISB_CELLBD", fontName=FB, fontSize=T.cell_size,
            leading=T.cell_leading, textColor=_hex(T.body))
        self.CELLC = self._S("ISB_CELLC", fontSize=T.cell_size,
            leading=T.cell_leading, textColor=_hex(T.body), alignment=TA_CENTER)
        self.CELLRD = self._S("ISB_CELLRD", fontName=FB, fontSize=T.cell_size,
            leading=T.cell_leading, textColor=_hex(T.accent), alignment=TA_CENTER)
        self.CELLHDR = ParagraphStyle("ISB_CELLHDR", fontName=FB,
            fontSize=T.cell_size, leading=T.cell_leading,
            textColor=colors.white, alignment=TA_CENTER)
        self.SEQ_HDR = self._S("ISB_SEQ_HDR", fontName=FB, fontSize=9,
            leading=12, textColor=_hex(T.blue), spaceAfter=2, leftIndent=8)

    # ── Shorthand constructors ───────────────────────────────────────────

    @property
    def FONT(self):
        self._ensure_init()
        return self._FONT

    @property
    def FONTBD(self):
        self._ensure_init()
        return self._FONTBD

    def h1(self, t):
        self._ensure_init(); return Paragraph(t, self.H1)
    def h2(self, t):
        self._ensure_init(); return Paragraph(t, self.H2)
    def h3(self, t):
        self._ensure_init(); return Paragraph(t, self.H3)
    def p(self, t, style=None):
        self._ensure_init(); return Paragraph(t, style or self.BODY)
    def sp(self, n=6):
        return Spacer(1, n)
    def hr(self):
        return HRFlowable(width="100%", thickness=THEME.hr_thickness,
                          color=_hex(THEME.hrule), spaceAfter=6, spaceBefore=2)
    def bullet(self, t):
        self._ensure_init(); return Paragraph(f"• {t}", self.BULLET)
    def note(self, t):
        self._ensure_init(); return Paragraph(t, self.NOTE)

    def seq_block(self, label, sequence, footnote=None):
        self._ensure_init()
        elems = [Paragraph(label, self.SEQ_HDR)]
        for i in range(0, len(sequence), 70):
            elems.append(Paragraph(sequence[i:i+70], self.SEQ))
        if footnote:
            elems.append(Paragraph(footnote, self.NOTE))
        return elems

    # ── Table ────────────────────────────────────────────────────────────

    def make_table(self, data, col_widths=None, hdr_rows=1):
        self._ensure_init()
        t = Table(data, colWidths=col_widths, repeatRows=hdr_rows)
        n = len(data)
        style = [
            ("BACKGROUND", (0,0), (-1, hdr_rows-1), _hex(THEME.blue)),
            ("TEXTCOLOR",  (0,0), (-1, hdr_rows-1), colors.white),
            ("FONTNAME",   (0,0), (-1, hdr_rows-1), self._FONTBD),
            ("FONTSIZE",   (0,0), (-1,-1), THEME.cell_size),
            ("LEADING",    (0,0), (-1,-1), THEME.cell_leading),
            ("GRID",       (0,0), (-1,-1), THEME.table_grid_thin, _hex(THEME.grid)),
            ("LINEABOVE",  (0,0), (-1,0),  THEME.table_grid_thick, _hex(THEME.navy)),
            ("VALIGN",     (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING",(0,0), (-1,-1), 5),
            ("RIGHTPADDING",(0,0),(-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ]
        for i in range(hdr_rows, n):
            if (i - hdr_rows) % 2 == 1:
                style.append(("BACKGROUND", (0,i), (-1,i), _hex(THEME.row_alt)))
        t.setStyle(TableStyle(style))
        return t

    # ── Page chrome ──────────────────────────────────────────────────────

    def page_header_footer(self, spec: ReportSpec):
        """Return an ``onLaterPages`` callback for SimpleDocTemplate.build()."""
        self._ensure_init()
        font = self._FONT
        def _draw(canvas, doc):
            canvas.saveState()
            w, h = A4
            canvas.setStrokeColor(_hex(THEME.blue))
            canvas.setLineWidth(0.5)
            canvas.line(2*cm, h - THEME.header_line_y_offset*cm,
                        w - 2*cm, h - THEME.header_line_y_offset*cm)
            canvas.setFont(font, THEME.header_font_size)
            canvas.setFillColor(_hex(THEME.muted))
            canvas.drawString(2*cm, h - THEME.header_text_y_offset*cm,
                              spec.header_left())
            canvas.drawRightString(w - 2*cm, h - THEME.header_text_y_offset*cm,
                                   spec.header_right())
            canvas.line(2*cm, THEME.footer_line_y_offset*cm,
                        w - 2*cm, THEME.footer_line_y_offset*cm)
            canvas.drawCentredString(w/2, THEME.footer_text_y_offset*cm,
                                     spec.footer_center(doc.page))
            canvas.restoreState()
        return _draw

    def build_doc(self, story, spec: ReportSpec, out_path: str):
        """Convenience: build a complete PDF with standard margins and chrome."""
        self._ensure_init()
        doc = SimpleDocTemplate(
            out_path,
            pagesize=A4,
            leftMargin=THEME.page_margin_lr * cm,
            rightMargin=THEME.page_margin_lr * cm,
            topMargin=THEME.page_margin_top * cm,
            bottomMargin=THEME.page_margin_bot * cm,
            title=spec.title,
            author=f"{spec.institution} {spec.engine}",
        )
        doc.build(
            story,
            onFirstPage=lambda c, d: None,
            onLaterPages=self.page_header_footer(spec),
        )
        return out_path

    def cover_page(self, spec: ReportSpec):
        """Return story elements for a standard InSynBio cover page."""
        self._ensure_init()
        elems = [
            Spacer(1, 40),
            Paragraph(spec.title or spec.report_id, self.TITLE),
        ]
        if spec.subtitle:
            elems.append(Paragraph(spec.subtitle, self.TITLE))
        elems += [
            Spacer(1, 10),
            Paragraph(
                f"：{spec.report_id}  ·  ：{spec.version}",
                self.SUBTITLE),
            Paragraph(
                f"：{spec.report_date.isoformat()}  ·  "
                f"：{spec.institution} {spec.engine}",
                self.SUBTITLE),
            Paragraph(f"{spec.confidentiality}", self.SUBTITLE),
            Spacer(1, 8),
            self.hr(),
            Spacer(1, 8),
        ]
        meta_data = [
            [Paragraph(k, self.META), Paragraph(v, self.META)]
            for k, v in spec.cover_meta_rows()
        ]
        meta_tbl = Table(meta_data, colWidths=[4.5*cm, 11.5*cm])
        meta_tbl.setStyle(TableStyle([
            ("ALIGN",         (0,0), (0,-1), "RIGHT"),
            ("ALIGN",         (1,0), (1,-1), "LEFT"),
            ("FONT",          (0,0), (0,-1), self._FONTBD, 9),
            ("FONT",          (1,0), (1,-1), self._FONT,   9),
            ("TEXTCOLOR",     (0,0), (0,-1), _hex(THEME.blue)),
            ("TEXTCOLOR",     (1,0), (1,-1), _hex(THEME.body)),
            ("TOPPADDING",    (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        elems.append(meta_tbl)
        return elems


# Module-level singleton
RL = _ReportLabTheme()
