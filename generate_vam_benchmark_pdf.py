"""
Generate: Therasik VAM Benchmark Research Report (PDF)
，， ReportLab 
"""
import os, math
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.graphics.shapes import (
    Drawing, Rect, String, Line, Circle, Polygon, Group
)
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderPDF
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing

# ─── Font setup (CJK) ───────────────────────────────────────────────
# Try to register a CJK font; fall back to Helvetica if unavailable
CJK_FONT = "Helvetica"
CJK_BOLD = "Helvetica-Bold"
FONT_REGISTERED = False

def _try_register(name, bold_name, paths):
    global CJK_FONT, CJK_BOLD, FONT_REGISTERED
    for p, pb in paths:
        if os.path.exists(p) and os.path.exists(pb):
            try:
                pdfmetrics.registerFont(TTFont(name, p))
                pdfmetrics.registerFont(TTFont(bold_name, pb))
                CJK_FONT = name
                CJK_BOLD = bold_name
                FONT_REGISTERED = True
                return True
            except Exception:
                pass
    return False

WIN_FONTS = r"C:\Windows\Fonts"
_try_register("SimSun", "SimHei", [
    (f"{WIN_FONTS}\\simsun.ttc", f"{WIN_FONTS}\\simhei.ttf"),
    (f"{WIN_FONTS}\\simsun.ttf", f"{WIN_FONTS}\\simhei.ttf"),
])
if not FONT_REGISTERED:
    _try_register("MicrosoftYaHei", "MicrosoftYaHeiBold", [
        (f"{WIN_FONTS}\\msyh.ttc", f"{WIN_FONTS}\\msyhbd.ttc"),
        (f"{WIN_FONTS}\\msyh.ttf", f"{WIN_FONTS}\\msyhbd.ttf"),
    ])

# ─── Color palette ──────────────────────────────────────────────────
C_PRIMARY   = colors.HexColor("#0d9488")
C_ACCENT    = colors.HexColor("#6d28d9")
C_DANGER    = colors.HexColor("#dc2626")
C_AMBER     = colors.HexColor("#d97706")
C_LIGHT_BG  = colors.HexColor("#f9fafb")
C_BORDER    = colors.HexColor("#e5e7eb")
C_TEXT      = colors.HexColor("#111827")
C_MUTED     = colors.HexColor("#6b7280")
C_GREEN     = colors.HexColor("#059669")
C_INDIGO    = colors.HexColor("#4f46e5")

W, H = A4  # 595 x 842 pt

# ─── Styles ─────────────────────────────────────────────────────────
def make_styles:
    s = {}
    F, B = CJK_FONT, CJK_BOLD

    s["title"]    = ParagraphStyle("title",    fontName=B, fontSize=28, textColor=C_TEXT,   spaceAfter=8,  leading=34)
    s["subtitle"] = ParagraphStyle("subtitle", fontName=F, fontSize=13, textColor=C_MUTED,  spaceAfter=20, leading=20)
    s["h2"]       = ParagraphStyle("h2",       fontName=B, fontSize=17, textColor=C_TEXT,   spaceBefore=28, spaceAfter=10, leading=24)
    s["h3"]       = ParagraphStyle("h3",       fontName=B, fontSize=13, textColor=C_TEXT,   spaceBefore=16, spaceAfter=6,  leading=20)
    s["body"]     = ParagraphStyle("body",     fontName=F, fontSize=11, textColor=C_TEXT,   spaceAfter=8,  leading=18, alignment=TA_JUSTIFY)
    s["small"]    = ParagraphStyle("small",    fontName=F, fontSize=9,  textColor=C_MUTED,  spaceAfter=4,  leading=14)
    s["caption"]  = ParagraphStyle("caption",  fontName=F, fontSize=9,  textColor=C_MUTED,  spaceAfter=12, leading=13, alignment=TA_CENTER)
    s["badge"]    = ParagraphStyle("badge",    fontName=B, fontSize=10, textColor=colors.white)
    s["th"]       = ParagraphStyle("th",       fontName=B, fontSize=9,  textColor=C_MUTED)
    s["td"]       = ParagraphStyle("td",       fontName=F, fontSize=10, textColor=C_TEXT)
    s["td_good"]  = ParagraphStyle("td_good",  fontName=B, fontSize=10, textColor=C_GREEN)
    s["td_bad"]   = ParagraphStyle("td_bad",   fontName=B, fontSize=10, textColor=C_DANGER)
    s["td_mid"]   = ParagraphStyle("td_mid",   fontName=B, fontSize=10, textColor=C_AMBER)
    s["footer"]   = ParagraphStyle("footer",   fontName=F, fontSize=8,  textColor=C_MUTED, alignment=TA_CENTER)
    return s

ST = make_styles

# ─── Flowable helpers ───────────────────────────────────────────────
def HR(color=C_BORDER, thickness=1):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=8, spaceBefore=4)

def SP(h=8):
    return Spacer(1, h)

def P(text, style="body"):
    return Paragraph(text, ST[style])


# ─── Custom Flowables ───────────────────────────────────────────────
class ColorBlock(Flowable):
    """Colored background info box."""
    def __init__(self, paragraphs, bg=C_LIGHT_BG, border=C_BORDER, radius=8, pad=12):
        super.__init__
        self.paragraphs = paragraphs
        self.bg = bg
        self.border = border
        self.radius = radius
        self.pad = pad

    def wrap(self, aw, ah):
        self._aw = aw
        inner_w = aw - 2 * self.pad
        total_h = self.pad
        for para in self.paragraphs:
            w, h = para.wrap(inner_w, ah)
            total_h += h + 4
        total_h += self.pad
        self._h = total_h
        return aw, total_h

    def draw(self):
        c = self.canv
        c.saveState
        c.setFillColor(self.bg)
        c.setStrokeColor(self.border)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, self._aw, self._h, self.radius, fill=1, stroke=1)
        c.restoreState
        y = self._h - self.pad
        inner_w = self._aw - 2 * self.pad
        for para in self.paragraphs:
            w, h = para.wrap(inner_w, self._h)
            y -= h
            para.drawOn(c, self.pad, y)
            y -= 4


class KPIRow(Flowable):
    """A row of KPI cards."""
    def __init__(self, items, height=80):
        """items: list of (label, value, desc, color)"""
        super.__init__
        self.items = items
        self._h = height

    def wrap(self, aw, ah):
        self._aw = aw
        return aw, self._h

    def draw(self):
        c = self.canv
        n = len(self.items)
        gap = 8
        card_w = (self._aw - gap * (n - 1)) / n
        for i, (label, value, desc, col) in enumerate(self.items):
            x = i * (card_w + gap)
            y = 0
            c.saveState
            c.setFillColor(C_LIGHT_BG)
            c.setStrokeColor(C_BORDER)
            c.setLineWidth(0.5)
            c.roundRect(x, y, card_w, self._h, 6, fill=1, stroke=1)
            # Accent top bar
            c.setFillColor(col)
            c.roundRect(x, y + self._h - 4, card_w, 4, 3, fill=1, stroke=0)
            c.setFillColor(C_MUTED)
            c.setFont(CJK_FONT, 7)
            c.drawCentredString(x + card_w / 2, y + self._h - 18, label.upper)
            c.setFillColor(C_TEXT)
            c.setFont(CJK_BOLD, 22)
            c.drawCentredString(x + card_w / 2, y + self._h - 44, value)
            c.setFillColor(C_MUTED)
            c.setFont(CJK_FONT, 7.5)
            # Wrap desc text
            words = desc
            c.drawCentredString(x + card_w / 2, y + 10, words)
            c.restoreState


class FunnelChart(Flowable):
    """5-stage funnel visualization."""
    STAGES = [
        ("1", "AI ",     " + ",   "10,000+", colors.HexColor("#dbeafe"), colors.HexColor("#2563eb")),
        ("2", "",   " Non-binder",     "~3,000",  colors.HexColor("#e0e7ff"), colors.HexColor("#4f46e5")),
        ("3", "3D AI ", "3D ",        "~500",    colors.HexColor("#f3e8ff"), colors.HexColor("#7e22ce")),
        ("4", ""," + CMC ",     "~150",    colors.HexColor("#ccfbf1"), colors.HexColor("#0d9488")),
        ("5", " MD ",  " + ",   "Top 10",  colors.HexColor("#d1fae5"), colors.HexColor("#059669")),
    ]

    def __init__(self, width=420, row_h=40, gap=6, indent_step=16):
        super.__init__
        self._fw = width
        self._row_h = row_h
        self._gap = gap
        self._indent = indent_step
        self._fh = len(self.STAGES) * (row_h + gap) - gap + 20

    def wrap(self, aw, ah):
        self._aw = aw
        return aw, self._fh

    def draw(self):
        c = self.canv
        for i, (num, title, desc, count, bg, fg) in enumerate(self.STAGES):
            indent = i * self._indent
            y = self._fh - 20 - (i + 1) * (self._row_h + self._gap) + self._gap
            row_w = self._aw - indent
            c.saveState
            # Background
            c.setFillColor(bg)
            c.setStrokeColor(fg)
            c.setLineWidth(0.8)
            c.roundRect(indent, y, row_w, self._row_h, 6, fill=1, stroke=1)
            # Number circle
            cx = indent + 22
            cy = y + self._row_h / 2
            c.setFillColor(fg)
            c.circle(cx, cy, 13, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont(CJK_BOLD, 11)
            c.drawCentredString(cx, cy - 4, num)
            # Title
            c.setFillColor(C_TEXT)
            c.setFont(CJK_BOLD, 10.5)
            c.drawString(indent + 44, y + self._row_h / 2 + 3, title)
            c.setFillColor(C_MUTED)
            c.setFont(CJK_FONT, 8)
            c.drawString(indent + 44, y + self._row_h / 2 - 11, desc)
            # Count badge
            c.setFillColor(fg)
            c.setFont(CJK_BOLD, 9)
            c.drawRightString(self._aw - 8, y + self._row_h / 2 - 4, count)
            c.restoreState


class HitRateChart(Flowable):
    """Horizontal bar chart showing hit rate progression."""
    BARS = [
        ("",          74.5, C_MUTED),
        ("AI ",          77.8, C_INDIGO),
        ("",       78.5, C_ACCENT),
        (" + MD ",   82.4, C_GREEN),
    ]

    def __init__(self, width=380, row_h=30, gap=10):
        super.__init__
        self._fw = width
        self._row_h = row_h
        self._gap = gap
        self._fh = len(self.BARS) * (row_h + gap) + 30

    def wrap(self, aw, ah):
        self._aw = aw
        self._bar_w = aw - 160 - 60  # label_w=160, value_w=60
        return aw, self._fh

    def draw(self):
        c = self.canv
        label_w = 165
        val_w = 50
        bar_area = self._aw - label_w - val_w - 10
        max_val = 100.0
        for i, (label, pct, col) in enumerate(self.BARS):
            y = self._fh - 30 - (i + 1) * (self._row_h + self._gap)
            bar_len = (pct / max_val) * bar_area
            # Background track
            c.setFillColor(C_BORDER)
            c.roundRect(label_w, y + 8, bar_area, 14, 4, fill=1, stroke=0)
            # Filled bar
            c.setFillColor(col)
            c.roundRect(label_w, y + 8, bar_len, 14, 4, fill=1, stroke=0)
            # Label
            c.setFillColor(C_TEXT)
            c.setFont(CJK_FONT, 9)
            c.drawString(0, y + 12, label)
            # Value
            c.setFillColor(col)
            c.setFont(CJK_BOLD, 10)
            c.drawString(label_w + bar_area + 6, y + 12, f"{pct}%")


class CorrelationBarChart(Flowable):
    """Bar chart showing Spearman rho per tool."""
    TOOLS = [
        ("EvoEF2\n", -0.21, C_DANGER),
        ("PRODIGY\n", -0.18, C_AMBER),
        ("ThermoMPNN\n", 0.09, colors.HexColor("#6b7280")),
        ("AbLang\n(AI)", 0.31, C_PRIMARY),
    ]

    def __init__(self, width=400, height=180):
        super.__init__
        self._fw = width
        self._fh = height + 40

    def wrap(self, aw, ah):
        self._aw = aw
        return aw, self._fh

    def draw(self):
        c = self.canv
        n = len(self.TOOLS)
        margin_l, margin_r = 50, 20
        margin_b, margin_t = 55, 20
        chart_w = self._aw - margin_l - margin_r
        chart_h = self._fh - margin_b - margin_t
        bar_w = chart_w / n * 0.5
        bar_gap = chart_w / n

        # Axes
        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.8)
        c.line(margin_l, margin_b, margin_l, margin_b + chart_h)
        c.line(margin_l, margin_b, margin_l + chart_w, margin_b)

        # Zero line
        zero_y = margin_b + chart_h * 0.35
        c.setStrokeColor(C_MUTED)
        c.setDash([3, 3])
        c.line(margin_l, zero_y, margin_l + chart_w, zero_y)
        c.setDash

        # Y axis labels
        c.setFont(CJK_FONT, 7)
        c.setFillColor(C_MUTED)
        for val, label in [(-0.3, "-0.3"), (-0.2, "-0.2"), (-0.1, "-0.1"),
                           (0.0, "0"), (0.1, "+0.1"), (0.2, "+0.2"), (0.3, "+0.3"), (0.4, "+0.4")]:
            py = zero_y + val * chart_h / 0.7
            c.drawRightString(margin_l - 4, py - 3, label)
            c.setStrokeColor(C_BORDER)
            c.setLineWidth(0.3)
            c.line(margin_l - 2, py, margin_l + chart_w, py)

        # Bars
        for i, (name, rho, col) in enumerate(self.TOOLS):
            bx = margin_l + i * bar_gap + (bar_gap - bar_w) / 2
            bar_h = abs(rho) * chart_h / 0.7
            if rho >= 0:
                by = zero_y
            else:
                by = zero_y - bar_h

            c.setFillColor(col)
            c.setStrokeColor(colors.white)
            c.setLineWidth(0.5)
            c.roundRect(bx, by, bar_w, bar_h if bar_h > 1 else 1, 3, fill=1, stroke=1)

            # Value label on bar
            c.setFillColor(col)
            c.setFont(CJK_BOLD, 8.5)
            label_y = by + bar_h + 3 if rho >= 0 else by - 12
            c.drawCentredString(bx + bar_w / 2, label_y, f"ρ={rho:+.2f}")

            # Tool name (multi-line)
            c.setFillColor(C_TEXT)
            c.setFont(CJK_FONT, 7.5)
            lines = name.split("\n")
            for j, ln in enumerate(lines):
                c.drawCentredString(bx + bar_w / 2, margin_b - 14 - j * 10, ln)

        # Axis title
        c.setFillColor(C_MUTED)
        c.setFont(CJK_FONT, 8)
        c.drawCentredString(margin_l + chart_w / 2, 2, " (pKD)  Spearman  ρ")


class AUCBarChart(Flowable):
    """AUC scores per tool per target - grouped bars."""
    # Per-target AUC for 3 tools (EvoEF2, ThermoMPNN, AbLang)
    TARGETS = ["T-1", "T-2", "T-3", "T-4", "T-5", "T-6"]
    EVOEF2  = [0.41, 0.62, 0.38, 0.71, 0.33, 0.55]
    THERMO  = [0.57, 0.54, 0.61, 0.58, 0.52, 0.63]
    ABLANG  = [0.66, 0.71, 0.68, 0.74, 0.61, 0.69]

    def __init__(self, width=440, height=160):
        super.__init__
        self._fw = width
        self._fh = height + 50

    def wrap(self, aw, ah):
        self._aw = aw
        return aw, self._fh

    def draw(self):
        c = self.canv
        n_groups = len(self.TARGETS)
        n_bars = 3
        margin_l, margin_r = 40, 20
        margin_b, margin_t = 45, 15
        chart_w = self._aw - margin_l - margin_r
        chart_h = self._fh - margin_b - margin_t
        group_w = chart_w / n_groups
        bar_w = group_w * 0.22

        # Axes
        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.8)
        c.line(margin_l, margin_b, margin_l, margin_b + chart_h)
        c.line(margin_l, margin_b, margin_l + chart_w, margin_b)

        # Y axis grid
        for val in [0.5, 0.6, 0.7, 0.8]:
            py = margin_b + val * chart_h
            c.setStrokeColor(C_BORDER)
            c.setDash([2, 3])
            c.line(margin_l, py, margin_l + chart_w, py)
            c.setDash
            c.setFillColor(C_MUTED)
            c.setFont(CJK_FONT, 7)
            c.drawRightString(margin_l - 3, py - 3, f"{val:.1f}")

        # Random AUC=0.5 reference
        c.setStrokeColor(C_DANGER)
        c.setDash([4, 3])
        c.setLineWidth(0.8)
        ref_y = margin_b + 0.5 * chart_h
        c.line(margin_l, ref_y, margin_l + chart_w, ref_y)
        c.setDash
        c.setFillColor(C_DANGER)
        c.setFont(CJK_FONT, 7)
        c.drawString(margin_l + 2, ref_y + 2, " AUC = 0.50")

        # Bars
        palette = [C_DANGER, C_MUTED, C_PRIMARY]
        names   = ["EvoEF2", "ThermoMPNN", "AbLang"]
        data    = [self.EVOEF2, self.THERMO, self.ABLANG]
        for gi, target in enumerate(self.TARGETS):
            gx = margin_l + gi * group_w
            for bi in range(n_bars):
                bx = gx + bi * (bar_w + 1) + (group_w - n_bars * (bar_w + 1)) / 2
                val = data[bi][gi]
                bh = val * chart_h
                c.setFillColor(palette[bi])
                c.roundRect(bx, margin_b, bar_w, bh, 2, fill=1, stroke=0)
            # Group label
            c.setFillColor(C_TEXT)
            c.setFont(CJK_FONT, 8)
            c.drawCentredString(gx + group_w / 2, margin_b - 12, target)

        # Legend
        lx = margin_l + 10
        for i, (name, col) in enumerate(zip(names, palette)):
            c.setFillColor(col)
            c.rect(lx + i * 95, self._fh - 12, 10, 8, fill=1, stroke=0)
            c.setFillColor(C_TEXT)
            c.setFont(CJK_FONT, 8)
            c.drawString(lx + i * 95 + 13, self._fh - 12, name)

        # Axis title
        c.setFillColor(C_MUTED)
        c.setFont(CJK_FONT, 7.5)
        c.drawCentredString(margin_l + chart_w / 2, 2, " Binder/Non-binder  AUC（3 ）")


# ─── Page header / footer callbacks ─────────────────────────────────
def on_first_page(canvas, doc):
    canvas.saveState
    # Top color bar
    canvas.setFillColor(C_PRIMARY)
    canvas.rect(0, H - 8, W, 8, fill=1, stroke=0)
    # Footer
    canvas.setFillColor(C_MUTED)
    canvas.setFont(CJK_FONT, 8)
    canvas.drawCentredString(W / 2, 22, "© 2026 Therasik · InSynBio  · ，")
    canvas.restoreState

def on_later_pages(canvas, doc):
    canvas.saveState
    canvas.setFillColor(C_BORDER)
    canvas.rect(0, H - 3, W, 3, fill=1, stroke=0)
    canvas.setFillColor(C_MUTED)
    canvas.setFont(CJK_FONT, 8)
    canvas.drawString(doc.leftMargin, 22, "Therasik VAM  · 2026")
    canvas.drawRightString(W - doc.rightMargin, 22, f" {doc.page} ")
    canvas.restoreState


# ─── Document builder ────────────────────────────────────────────────
def build_pdf(out_path):
    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.2 * cm,
        title="Therasik VAM  2026",
        author="Therasik · InSynBio ",
        subject="",
    )

    story = []

    # ── Cover block ─────────────────────────────────────────────────
    story.append(SP(20))
    story.append(P('<font color="#6d28d9"><b> · 2026  4 </b></font>', "small"))
    story.append(SP(6))
    story.append(P("", "title"))
    story.append(P('\u6253\u7834\u201c\u552f\u80fd\u91cf\u8bba\u201d\u2014\u2014 AI-MD \u591a\u5c3a\u5ea6\u5e8f\u8d2f\u7b5b\u9009\u67b6\u6784\u7684\u5efa\u7acb', "subtitle"))
    story.append(HR(C_ACCENT, 2))
    story.append(SP(4))
    story.append(P(
        " <b>854 </b>，（VAM）。"
        "：<b></b>， 74.5%  82.4%+。",
        "body"
    ))
    story.append(SP(12))

    # ── KPI row ─────────────────────────────────────────────────────
    story.append(KPIRow([
        ("",   "854",  "",         C_ACCENT),
        ("",   "6",    "",       C_PRIMARY),
        ("",   "4",    "··AI·MD",           C_INDIGO),
        ("", "+7.9%","74.5% → 82.4%+",            C_GREEN),
    ], height=75))

    story.append(SP(20))

    # ── Section 1: Background ────────────────────────────────────────
    story.append(P("、", "h2"))
    story.append(HR)
    story.append(P(
        "（Virtual Affinity Maturation, VAM），，"
        " Top-K 。，。"
        "：",
        "body"
    ))
    tbl_data = [
        [P("", "th"), P("", "th")],
        [P("Q1", "td"), P("（pKD）？", "td")],
        [P("Q2", "td"), P(" Binder/Non-binder ？", "td")],
        [P("Q3", "td"), P("？", "td")],
    ]
    tbl = Table(tbl_data, colWidths=["15%", "85%"])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(tbl)

    # ── Section 2: Data Overview ─────────────────────────────────────
    story.append(P("、", "h2"))
    story.append(HR)
    story.append(ColorBlock([
        P("<b>：</b>， 6 。", "body"),
        P("<b>：</b>、， CDR 。", "body"),
        P("<b>：</b> pKD  Binder/Non-binder 。", "body"),
    ], bg=colors.HexColor("#f0fdfa"), border=colors.HexColor("#99f6e4")))
    story.append(SP(8))

    tbl_data2 = [
        [P(" ID", "th"), P("", "th"), P("Binder ", "th"), P("", "th"), P("pKD ", "th")],
        [P("T-1", "td"), P("168", "td"), P("76.2%", "td"), P("", "td"), P("6.2 – 9.8", "td")],
        [P("T-2", "td"), P("142", "td"), P("71.8%", "td"), P("", "td"), P("5.9 – 10.1", "td")],
        [P("T-3", "td"), P("119", "td"), P("68.1%", "td"), P("", "td"), P("< 6 – 9.3", "td")],
        [P("T-4", "td"), P("156", "td"), P("82.1%", "td"), P("", "td"), P("7.1 – 11.2", "td")],
        [P("T-5", "td"), P("134", "td"), P("64.9%", "td"), P("", "td"), P("< 6 – 8.7", "td")],
        [P("T-6", "td"), P("135", "td"), P("79.3%", "td"), P("", "td"), P("6.8 – 10.4", "td")],
        [P("", "th"), P("854", "th"), P("73.7%", "th"), P("—", "th"), P("—", "th")],
    ]
    tbl2 = Table(tbl_data2, colWidths=["16%", "14%", "16%", "28%", "26%"])
    tbl2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_LIGHT_BG),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f0fdfa")),
        ("FONTNAME", (0, -1), (-1, -1), CJK_BOLD),
        ("BOX", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, C_LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(tbl2)

    # ── Section 3: pKD Correlation ───────────────────────────────────
    story.append(PageBreak)
    story.append(P("、pKD ", "h2"))
    story.append(HR)
    story.append(P(
        "， pKD  Spearman  ρ。"
        " ρ 。<b></b>。",
        "body"
    ))
    story.append(SP(6))
    story.append(CorrelationBarChart(width=doc.width, height=160))
    story.append(P(" 1   pKD  Spearman （ 6 ）", "caption"))

    story.append(ColorBlock([
        P(
            "<b>：</b>EvoEF2  PRODIGY  ρ  <b>−0.21</b>  <b>−0.18</b>。"
            " Top-K ，<b></b>，"
            "。",
            "body"
        ),
        P(
            "：（Induced Fit），。",
            "body"
        ),
    ], bg=colors.HexColor("#fff1f2"), border=colors.HexColor("#fca5a5")))

    # ── Section 4: AUC Analysis ──────────────────────────────────────
    story.append(P("、Binder/Non-binder （AUC）", "h2"))
    story.append(HR)
    story.append(P(
        "（pKD >  = Binder）， ROC-AUC 。"
        "AUC > 0.70 ；AUC < 0.55 。",
        "body"
    ))
    story.append(SP(6))
    story.append(AUCBarChart(width=doc.width, height=150))
    story.append(P(" 2   Binder/Non-binder  AUC （ 0.50）", "caption"))

    # AUC summary table
    tbl_auc = [
        [P("", "th"), P(" AUC", "th"), P("", "th"), P("", "th")],
        [P("EvoEF2",      "td"), P("0.50",  "td_mid"), P("0.33 – 0.71", "td"), P("，", "td")],
        [P("PRODIGY",     "td"), P("0.48",  "td_bad"), P("0.28 – 0.66", "td"), P("", "td")],
        [P("ThermoMPNN",  "td"), P("0.57",  "td_mid"), P("0.52 – 0.63", "td"), P("，", "td")],
        [P("AbLang",      "td"), P("0.68",  "td_good"), P("0.61 – 0.74", "td"), P("，", "td")],
    ]
    tbl3 = Table(tbl_auc, colWidths=["22%", "22%", "26%", "30%"])
    tbl3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (2, -1), "CENTER"),
    ]))
    story.append(tbl3)

    # ── Section 5: Sequential Gating ────────────────────────────────
    story.append(PageBreak)
    story.append(P("、", "h2"))
    story.append(HR)
    story.append(P(
        "，（Sequential Gating）。"
        "，：AI ，，"
        "<b></b> Non-binder，MD  Top-10。",
        "body"
    ))
    story.append(SP(6))
    story.append(HitRateChart(width=doc.width, row_h=28, gap=10))
    story.append(P(" 3  （Binder/Total）", "caption"))

    story.append(ColorBlock([
        P("<b>：</b>", "h3"),
        P("•  AI （Gate 1）： 74.5% → 77.8%（+3.3 pp）", "body"),
        P("• （Gate 2）：77.8% → 78.5%（+0.7 pp）", "body"),
        P("•  + MD （Gate 3-5）：78.5% → <b>82.4%+</b>（+3.9 pp）", "body"),
        P("• （74.5%）， <b> 30% </b>，。", "body"),
    ], bg=colors.HexColor("#f0fdfa"), border=colors.HexColor("#6ee7b7")))

    # ── Section 6: 5-Stage Cascade Engine ───────────────────────────
    story.append(SP(12))
    story.append(P("、", "h2"))
    story.append(HR)
    story.append(P(
        "，Therasik  VAM ，，"
        "、。",
        "body"
    ))
    story.append(SP(8))
    story.append(FunnelChart(width=doc.width))
    story.append(P(" 4  Therasik ", "caption"))

    # Decision rules table
    story.append(P("", "h3"))
    tbl_rules = [
        [P("", "th"), P("", "th"), P("", "th"), P("", "th")],
        [P("Stage 1\nAI ", "td"),   P("", "td"), P("\n+", "td"), P("AbLang ≥ P25\nThermoMPNN ΔΔG ≤ P75", "td")],
        [P("Stage 2\n", "td"),  P(" Non-binder", "td"),  P("\n",  "td"), P("<5%", "td")],
        [P("Stage 3\n3D AI",   "td"),   P("",       "td"),  P("\n3D ",    "td"), P(" Top 20%",       "td")],
        [P("Stage 4\nCMC",     "td"),   P("",   "td"),  P(" + pI/\n",    "td"), P(" + pI 5–8.5",      "td")],
        [P("Stage 5\nMD ", "td"),   P("", "td"),  P("\n+MM/GBSA",      "td"), P(" Top 10 ",     "td")],
    ]
    tbl4 = Table(tbl_rules, colWidths=["16%", "24%", "24%", "36%"])
    tbl4.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 1), (0, -1), CJK_BOLD),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tbl4)

    # ── Section 7: Conclusions ───────────────────────────────────────
    story.append(PageBreak)
    story.append(P("、", "h2"))
    story.append(HR)

    conclusions = [
        ("C1", "",
         "EvoEF2 / PRODIGY  ρ ， Top-K 。"
         "，。"),
        ("C2", "AI ",
         "AbLang  AUC 0.68，。 Stage 1-3 。"),
        ("C3", "",
         "ThermoMPNN  AUC 0.57，，，"
         "。"),
        ("C4", " MD （≤20）",
         "MM/GBSA ， Stage 3 ，"
         "。"),
        ("C5", "",
         "，。"
         " 5  +7.9 pp， 30% 。"),
    ]
    for cid, title, text in conclusions:
        story.append(KeepTogether([
            ColorBlock([
                P(f'<b><font color="#6d28d9">{cid}</font>  {title}</b>', "body"),
                P(text, "body"),
            ], bg=C_LIGHT_BG, border=C_BORDER),
            SP(6),
        ]))

    # ── Disclaimer / Footer ──────────────────────────────────────────
    story.append(SP(20))
    story.append(HR(C_BORDER))
    story.append(P(
        "， Therasik 。"
        "、 InSynBio ，。"
        " Therasik ，。",
        "small"
    ))
    story.append(P("© 2026 Therasik · InSynBio  · ", "footer"))

    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    print(f"PDF generated: {out_path}")


if __name__ == "__main__":
    out = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_VAM_Benchmark_Report.pdf"
    build_pdf(out)
