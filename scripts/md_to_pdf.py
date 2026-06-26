"""
md_to_pdf.py  —  Convert a Markdown file to PDF with Chinese font support.

Usage:
    python scripts/md_to_pdf.py <input.md> [output.pdf]

Requirements:
    pip install fpdf2 markdown

Color/font tokens are read from core.reporting.theme when available,
falling back to hard-coded defaults for standalone usage.
"""
import sys
import re
import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

FONT_DIR = r"C:\Windows\Fonts"
# Use SimHei (TTF) which is more reliable for subsetting than YaHei (TTC)
FONT_REGULAR = os.path.join(FONT_DIR, "simhei.ttf") 
FONT_BOLD    = os.path.join(FONT_DIR, "simhei.ttf")
FONT_MONO    = os.path.join(FONT_DIR, "simhei.ttf")

# Try to import shared InSynBio theme; fall back to hardcoded defaults.
try:
    _suite = os.path.join(os.path.dirname(__file__), "..")
    if _suite not in sys.path:
        sys.path.insert(0, _suite)
    from core.reporting.theme import THEME as _T
    _USE_THEME = True
except ImportError:
    _T = None
    _USE_THEME = False

MARGIN = 12
LINE_HEIGHT = 5

if _USE_THEME:
    CODE_BG         = _T.rgb("code_bg")
    TABLE_HEADER_BG = _T.table_header_bg_rgb
    TABLE_ALT_BG    = _T.table_alt_bg_rgb
    TABLE_BORDER    = _T.table_border_rgb
    STOP_CELL_BG    = _T.rgb("stop_bg")
    WARN_CELL_BG    = _T.rgb("warn_bg")
    GO_CELL_BG      = _T.rgb("go_bg")
    STOP_COLOR      = _T.rgb("stop_fg")
    WARN_COLOR      = _T.rgb("warn_fg")
    GO_COLOR        = _T.rgb("go_fg")
    H_COLORS        = _T.h_colors_rgb
    TABLE_FONT_SIZE = int(_T.cell_size)
else:
    CODE_BG = (245, 245, 245)
    TABLE_HEADER_BG = (52, 100, 145)
    TABLE_ALT_BG = (235, 242, 250)
    TABLE_BORDER = (200, 210, 220)
    STOP_CELL_BG = (253, 232, 232)
    WARN_CELL_BG = (255, 248, 225)
    GO_CELL_BG   = (232, 248, 232)
    STOP_COLOR   = (190, 40, 40)
    WARN_COLOR   = (200, 140, 0)
    GO_COLOR     = (30, 130, 50)
    H_COLORS = {1: (30, 70, 130), 2: (40, 90, 150), 3: (60, 110, 170)}
    TABLE_FONT_SIZE = 8


class MdPDF(FPDF):

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.alias_nb_pages()
        self.set_auto_page_break(auto=True, margin=14)
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self._register_fonts()
        self._page_title = ""
        self._doc_number = ""

    def _register_fonts(self):
        # Use a more robust way to register fonts, specifying index for TTC if needed
        # and ensuring they are treated as Unicode.
        try:
            self.add_font("CJK", "", FONT_REGULAR)
            self.add_font("CJK", "B", FONT_BOLD)
            self.add_font("CJKm", "", FONT_MONO)
        except Exception as e:
            print(f"Warning: Could not load default Chinese fonts: {e}")
            # Fallback to standard fonts if CJK fails, though Chinese will be broken
            self.add_font("CJK", "", "Arial") 

    # ------------------------------------------------------------------ chrome
    def header(self):
        if not (self._page_title or self._doc_number):
            return
        self.set_text_color(140, 140, 140)
        usable = self._usable_w()
        left_text = self._page_title or ""
        right_text = self._doc_number or ""

        # Auto-shrink font if title + doc_number won't fit at default 8pt
        font_size = 8
        self.set_font("CJK", "B", font_size)
        left_w = self.get_string_width(left_text)
        right_w = self.get_string_width(right_text)
        gap = 4  # minimum gap between title and doc number (mm)
        while left_w + right_w + gap > usable and font_size > 5.5:
            font_size -= 0.5
            self.set_font("CJK", "B", font_size)
            left_w = self.get_string_width(left_text)
            right_w = self.get_string_width(right_text)

        right_col = max(right_w + 2, usable * 0.25)
        left_col = usable - right_col
        self.cell(left_col, 6, left_text, align="L")
        self.cell(right_col, 6, right_text, align="R")
        self.ln(1)
        self.set_draw_color(*TABLE_BORDER)
        self.set_line_width(0.2)
        self.line(MARGIN, self.get_y(), self.w - MARGIN, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-11)
        self.set_font("CJK", "", 7)
        self.set_text_color(140, 140, 140)
        self.cell(0, 8, f"— {self.page_no()} / {{nb}} —", align="C")
        self.set_text_color(0, 0, 0)

    # ------------------------------------------------------------------ helpers
    def _usable_w(self):
        return self.w - 2 * MARGIN

    def _set_body(self, size=9):
        self.set_font("CJK", "", size)
        self.set_text_color(30, 30, 30)

    def _set_bold(self, size=9):
        self.set_font("CJK", "B", size)
        self.set_text_color(30, 30, 30)

    def _set_mono(self, size=8):
        self.set_font("CJKm", "", size)
        self.set_text_color(30, 30, 30)

    @staticmethod
    def _sanitize(text: str) -> str:
        replacements = {
            "✓": "PASS", "✅": "PASS", "❌": "FAIL", "⚠️": "WARN", "⚠": "WARN",
            "🔴": "[H]", "🟡": "[M]", "🟢": "[L]",
            "★": "*", "☆": "*",
            "→": "->", "←": "<-", "↑": "(up)", "↓": "(low)", "↕": "(+/-)",
            "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
            "\u2014": "--", "\u2013": "-",
            "†": "+", "‡": "++", "×": "x", "÷": "/", "≤": "<=", "≥": ">=",
            "±": "+/-", "°": " deg", "Å": "A",
            "💾": "[save]", "📁": "[dir]", "📄": "[file]", "📑": "[pdf]",
            "⭐": "*", "✦": "*", "✧": "*", "⚪": "o", "⚫": "o",
            "\u2082": "2", "\u2081": "1", "\u2083": "3",
            "…": "...", "•": "*", # Replace bullet with asterisk
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        return "".join(c if ord(c) < 0x10000 else "?" for c in text)

    def _strip_inline(self, text):
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*",     r"\1", text)
        text = re.sub(r"`(.+?)`",        r"\1", text)
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
        text = re.sub(r"^\s*[\*>\-]+\s*", "", text)
        return self._sanitize(text).strip()

    # ------------------------------------------------------------------ blocks
    def add_heading(self, text, level):
        size  = {1: 14, 2: 11, 3: 9.5, 4: 9}.get(level, 9)
        color = H_COLORS.get(level, (50, 50, 50))
        min_follow = {1: 60, 2: 35, 3: 25, 4: 18}.get(level, 18)
        heading_h  = size * 0.5 + 4
        if self.get_y() + heading_h + min_follow > self.h - 18:
            self.add_page()
        self.ln({1: 4, 2: 3, 3: 2, 4: 1.5}.get(level, 1.5))
        self.set_font("CJK", "B", size)
        self.set_text_color(*color)
        clean = self._strip_inline(text)
        usable = self._usable_w()
        if level == 1:
            text_w = self.get_string_width(clean)
            if text_w > usable:
                shrunk = size
                while text_w > usable and shrunk > 10:
                    shrunk -= 0.5
                    self.set_font("CJK", "B", shrunk)
                    text_w = self.get_string_width(clean)
                size = shrunk
            self.cell(0, size * 0.45, clean, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_draw_color(*color)
            self.set_line_width(0.4)
            self.line(MARGIN, self.get_y(), self.w - MARGIN, self.get_y())
        elif level == 2:
            self.set_fill_color(230, 238, 250)
            text_w = self.get_string_width("  " + clean)
            if text_w > usable:
                shrunk = size
                while text_w > usable and shrunk > 8:
                    shrunk -= 0.5
                    self.set_font("CJK", "B", shrunk)
                    text_w = self.get_string_width("  " + clean)
            self.cell(0, size * 0.48, "  " + clean, fill=True,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            self.cell(0, size * 0.48, clean, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1.0)
        self.set_text_color(30, 30, 30)

    def add_paragraph(self, text):
        clean = text.strip()
        if not clean:
            return
        plain = re.sub(r"\*\*(.+?)\*\*", r"\1", clean)
        plain = re.sub(r"\*(.+?)\*",     r"\1", plain)
        plain = re.sub(r"`(.+?)`",        r"\1", plain)
        plain = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", plain)
        plain = self._sanitize(plain)
        alert = self._detect_alert(plain)
        if alert:
            self._render_alert_box(plain, alert)
            return
        self._set_body(9)
        self.multi_cell(0, 4.2, plain, align="L")
        self.ln(0.8)

    # ---- alert boxes ----
    @staticmethod
    def _detect_alert(text):
        s = text.strip()
        if s.startswith("[STOP]"):
            return "STOP"
        if s.startswith("[WARN]"):
            return "WARN"
        if s.startswith("[GO]"):
            return "GO"
        return None

    def _render_alert_box(self, text, alert_type):
        colors = {
            "STOP": (STOP_COLOR, STOP_CELL_BG, (120, 20, 20)),
            "WARN": (WARN_COLOR, WARN_CELL_BG, (100, 80, 0)),
            "GO":   (GO_COLOR,   GO_CELL_BG,   (20, 90, 30)),
        }
        accent, bg, txt_c = colors[alert_type]
        usable = self._usable_w()
        self.set_font("CJK", "", 9.5)
        lines = self.multi_cell(usable - 10, 5.0, text,
                                dry_run=True, output="LINES")
        box_h = max(len(lines) * 5.0 + 6, 12)
        if self.get_y() + box_h > self.h - 25:
            self.add_page()
        y0 = self.get_y()
        self.set_fill_color(*bg)
        self.set_draw_color(*accent)
        self.set_line_width(0.4)
        self.rect(MARGIN, y0, usable, box_h, "FD")
        self.set_fill_color(*accent)
        self.rect(MARGIN, y0, 3, box_h, "F")
        self.set_font("CJK", "B", 9.5)
        self.set_text_color(*txt_c)
        self.set_xy(MARGIN + 5, y0 + 3)
        self.multi_cell(usable - 10, 5.0, text, align="L")
        self.set_y(y0 + box_h + 2)
        self.set_text_color(30, 30, 30)

    # ---- other blocks ----
    def add_bullet(self, text, level=0):
        clean = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        clean = re.sub(r"\*(.+?)\*",     r"\1", clean)
        clean = re.sub(r"`(.+?)`",        r"\1", clean)
        clean = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", clean)
        clean = self._sanitize(clean).strip()
        if not clean:
            return
        indent = MARGIN + level * 4
        bullet = "-" if level == 0 else "-" # Use hyphen instead of bullet character
        self._set_body(8.5)
        self.set_x(indent)
        self.cell(3, 4.0, bullet)
        avail = self.w - indent - 3 - MARGIN
        self.multi_cell(avail, 4.0, clean, align="L")
        self.ln(0.3)

    def add_code_block(self, lines):
        if not lines:
            return
        self.ln(1)
        self._set_mono(7.5)
        line_h = 4.0
        self.set_fill_color(*CODE_BG)
        self.set_draw_color(*TABLE_BORDER)
        self.set_line_width(0.15)
        usable = self._usable_w()
        total_h = len(lines) * line_h + 4
        if self.get_y() + total_h > self.h - 18:
            self.add_page()
        y0 = self.get_y()
        self.rect(MARGIN, y0, usable, total_h, style="FD")
        self.set_xy(MARGIN + 2.5, y0 + 2)
        for line in lines:
            self.set_x(MARGIN + 2.5)
            self.cell(usable - 5, line_h, self._sanitize(line[:130]),
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1.5)

    def add_blockquote(self, text):
        clean = re.sub(r"[>\*`]", "", text).strip()
        clean = self._sanitize(clean)
        if not clean:
            return

        indent = MARGIN + 7    # 3 mm left bar + 4 mm gap to text
        avail  = self.w - indent - MARGIN
        line_h = 5.0

        # Pre-wrap to exact lines — avoids set_left_margin side-effects that
        # cause get_y() to be wrong and the vertical bar to overshoot.
        self.set_font("CJK", "", 9.5)
        wrapped = self.multi_cell(avail, line_h, clean, dry_run=True, output="LINES")

        total_h = len(wrapped) * line_h + 4
        if self.get_y() + total_h > self.h - 25:
            self.add_page()

        self.set_draw_color(100, 130, 200)
        self.set_line_width(0.8)
        self.set_text_color(70, 90, 130)
        y0 = self.get_y()

        for ln in wrapped:
            self.set_x(indent)
            self.cell(avail, line_h, ln, align="L",
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        y1 = self.get_y()
        self.line(MARGIN + 3, y0, MARGIN + 3, y1)

        # Restore draw state so subsequent borders/rules are not affected.
        self.set_draw_color(*TABLE_BORDER)
        self.set_line_width(0.2)
        self.set_text_color(30, 30, 30)
        self.ln(1)

    def add_image(self, img_path, caption=""):
        """Embed an image file into the PDF, scaled to fit page width."""
        if not os.path.isfile(img_path):
            self.add_paragraph(f"[Image not found: {img_path}]")
            return
        usable = self._usable_w()
        try:
            from PIL import Image as PILImage
            with PILImage.open(img_path) as im:
                iw, ih = im.size
        except Exception:
            iw, ih = 1600, 900

        scale = usable / (iw * 0.264583)
        img_h_mm = ih * 0.264583 * scale
        max_h = self.h - self.get_y() - 25
        if img_h_mm > max_h:
            self.add_page()
        self.image(img_path, x=MARGIN, w=usable)
        if caption:
            self.set_font("CJK", "", 7.5)
            self.set_text_color(100, 100, 100)
            self.multi_cell(0, 3.5, self._sanitize(caption), align="C")
            self.set_text_color(30, 30, 30)
        self.ln(2)

    def add_hr(self):
        self.ln(1.5)
        self.set_draw_color(*TABLE_BORDER)
        self.set_line_width(0.2)
        self.line(MARGIN, self.get_y(), self.w - MARGIN, self.get_y())
        self.ln(1.5)

    # ================================================================ TABLE ENGINE
    @staticmethod
    def _clean_cell(txt: str) -> str:
        txt = re.sub(r"\*\*(.+?)\*\*", r"\1", str(txt))
        txt = re.sub(r"\*(.+?)\*",     r"\1", txt)
        txt = re.sub(r"`(.+?)`",        r"\1", txt)
        txt = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", txt)
        return txt.strip()

    def _measure_col_widths(self, rows, n_cols, usable, font_size):
        """
        Two-pass content-weighted column width with word-break minimum protection.

        1. natural[c] = widest single-line cell in column c
        2. min_w[c]   = widest unbreakable token in column c  (floor = MIN_COL)
        3. If natural fits ─> proportional slack distribution
        4. Else allocate minimums first, distribute remaining by (natural-min)
        """
        PAD = 2.5
        MIN_COL = 10.0 # Reduced from 15.0

        natural = [0.0] * n_cols
        min_w   = [0.0] * n_cols

        for ri, row in enumerate(rows):
            style = "B" if ri == 0 else ""
            self.set_font("CJK", style, font_size)
            for ci, cell in enumerate(row[:n_cols]):
                txt = self._sanitize(self._clean_cell(cell))
                w = self.get_string_width(txt) + PAD
                
                # Cap natural width for long sequences to prevent table overflow
                if len(txt) > 30 and " " not in txt:
                    w = min(w, usable * 0.5) 
                
                natural[ci] = max(natural[ci], w)
                for tok in re.split(r'[\s,;/（）()、，：:·\-]', txt):
                    if tok:
                        tw = self.get_string_width(tok) + PAD
                        # Cap min width for long tokens
                        if len(tok) > 20:
                            tw = min(tw, usable * 0.3)
                        min_w[ci] = max(min_w[ci], tw)

        min_w = [max(m, MIN_COL) for m in min_w]
        total_nat = sum(natural) or usable

        if total_nat <= usable:
            slack = usable - total_nat
            return [w + slack * (w / total_nat) for w in natural]

        total_min = sum(min_w)
        if total_min >= usable:
            return [m * usable / total_min for m in min_w]

        remaining = usable - total_min
        deltas = [max(0.0, n - m) for n, m in zip(natural, min_w)]
        td = sum(deltas) or 1.0
        return [m + remaining * (d / td) for m, d in zip(min_w, deltas)]

    def _row_height(self, row, col_widths, n_cols, line_h, font_size, is_header):
        max_lines = 1
        style = "B" if is_header else ""
        self.set_font("CJK", style, font_size)
        for ci, cell in enumerate(row[:n_cols]):
            txt = self._sanitize(self._clean_cell(cell))
            inner_w = col_widths[ci] - 2.0
            if inner_w < 4:
                continue
            lines = self.multi_cell(inner_w, line_h, txt,
                                    dry_run=True, output="LINES")
            max_lines = max(max_lines, len(lines))
        return line_h * max_lines + 2.0

    @staticmethod
    def _cell_alert(txt):
        if "[STOP]" in txt:
            return STOP_CELL_BG, STOP_COLOR
        if "[WARN]" in txt:
            return WARN_CELL_BG, WARN_COLOR
        if "[GO]" in txt:
            return GO_CELL_BG, GO_COLOR
        return None, None

    def add_table(self, rows):
        if not rows or not rows[0]:
            return
        self.ln(1)
        n_cols = len(rows[0])

        font_size = TABLE_FONT_SIZE
        if n_cols >= 6:
            font_size = min(font_size, 7)
        elif n_cols >= 5:
            font_size = min(font_size, 7.5)
        line_h = max(3.5, font_size * 0.48)

        usable = self._usable_w()
        self.set_draw_color(*TABLE_BORDER)
        self.set_line_width(0.15)

        col_widths = self._measure_col_widths(rows, n_cols, usable, font_size)

        # Anti-orphan: ensure header + at least one data row fit before starting.
        if len(rows) >= 2:
            h_hdr  = self._row_height(rows[0], col_widths, n_cols, line_h, font_size, True)
            h_row1 = self._row_height(rows[1], col_widths, n_cols, line_h, font_size, False)
            if self.get_y() + h_hdr + h_row1 > self.h - 18:
                self.add_page()

        for ri, row in enumerate(rows):
            rh = self._row_height(row, col_widths, n_cols, line_h,
                                  font_size, ri == 0)
            if self.get_y() + rh > self.h - 18:
                self.add_page()

            y = self.get_y()
            x = MARGIN

            for ci, cell_text in enumerate(row[:n_cols]):
                w = col_widths[ci]
                txt = self._sanitize(self._clean_cell(cell_text))

                if ri == 0:
                    self.set_fill_color(*TABLE_HEADER_BG)
                else:
                    alert_bg, _ = self._cell_alert(txt)
                    if alert_bg:
                        self.set_fill_color(*alert_bg)
                    elif ri % 2 == 1:
                        self.set_fill_color(*TABLE_ALT_BG)
                    else:
                        self.set_fill_color(255, 255, 255)

                self.rect(x, y, w, rh, style="DF")

                inner_w = w - 2.0
                if inner_w >= 5:
                    if ri == 0:
                        self.set_font("CJK", "B", font_size)
                        self.set_text_color(255, 255, 255)
                    else:
                        self.set_font("CJK", "", font_size)
                        _, alert_tc = self._cell_alert(txt)
                        if alert_tc:
                            self.set_text_color(*alert_tc)
                        else:
                            self.set_text_color(30, 30, 30)

                    self.set_xy(x + 1.0, y + 1.0)
                    # Use wrap_mode="CHAR" to prevent long sequences from overflowing
                    try:
                        self.multi_cell(inner_w, line_h, txt, border=0, align="L", wrap_mode="CHAR")
                    except TypeError:
                        # Fallback for older fpdf2 versions
                        self.multi_cell(inner_w, line_h, txt, border=0, align="L")

                x += w

            self.set_y(y + rh)

        self.set_text_color(30, 30, 30)
        self.ln(1.5)


# ─────────────────────────────────────────────── parser ────────────────────────
def parse_and_render(md_text: str, pdf: MdPDF, md_dir: str = "."):
    lines = md_text.splitlines()
    i = 0
    in_code = False
    code_lines = []
    table_rows = []
    in_table = False
    pending_para = []

    def flush_para():
        nonlocal pending_para
        if pending_para:
            pdf.add_paragraph(" ".join(pending_para))
            pending_para = []

    def flush_table():
        nonlocal table_rows, in_table
        if table_rows:
            pdf.add_table(table_rows)
        table_rows = []
        in_table = False

    while i < len(lines):
        raw = lines[i]
        stripped = raw.rstrip()

        if stripped.startswith("```"):
            flush_para()
            flush_table()
            if in_code:
                pdf.add_code_block(code_lines)
                code_lines = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(raw)
            i += 1
            continue

        if re.match(r"^---+\s*$", stripped):
            flush_para()
            flush_table()
            pdf.add_hr()
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.+)", stripped)
        if m:
            flush_para()
            flush_table()
            pdf.add_heading(m.group(2), len(m.group(1)))
            i += 1
            continue

        img_m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", stripped)
        if img_m:
            flush_para()
            flush_table()
            caption = img_m.group(1)
            img_rel = img_m.group(2)
            img_abs = os.path.join(md_dir, img_rel) if not os.path.isabs(img_rel) else img_rel
            pdf.add_image(img_abs, caption)
            i += 1
            continue

        if "|" in stripped and stripped.startswith("|"):
            flush_para()
            if re.match(r"^\|[\s:\-|]+\|?\s*$", stripped):
                i += 1
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not in_table:
                in_table = True
                table_rows = [cells]
            else:
                table_rows.append(cells)
            i += 1
            continue
        else:
            if in_table:
                flush_table()

        if stripped.startswith(">"):
            flush_para()
            bq = stripped.lstrip(">").strip()
            bq_lines = [bq]
            j = i + 1
            while j < len(lines) and lines[j].startswith(">"):
                bq_lines.append(lines[j].lstrip(">").strip())
                j += 1
            pdf.add_blockquote(" ".join(bq_lines))
            i = j
            continue

        m = re.match(r"^(\s*)[-*+]\s+(.+)", stripped)
        if m:
            flush_para()
            flush_table()
            level = len(m.group(1)) // 2
            pdf.add_bullet(m.group(2), level)
            i += 1
            continue

        m = re.match(r"^\d+\.\s+(.+)", stripped)
        if m:
            flush_para()
            flush_table()
            pdf.add_bullet(m.group(1), 0)
            i += 1
            continue

        if not stripped:
            flush_para()
            flush_table()
            i += 1
            continue

        pending_para.append(stripped)
        i += 1

    flush_para()
    flush_table()
    if in_code and code_lines:
        pdf.add_code_block(code_lines)


# ───────────────────────────────────────────────── main ───────────────────────
def convert(md_path: str, pdf_path: str):
    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()

    pdf = MdPDF()
    m = re.search(r"^# (.+)", md_text, re.MULTILINE)
    if m:
        pdf._page_title = m.group(1).strip()[:60]
    m_doc = re.search(r"[：:]\*{0,2}\s*([A-Z0-9\-]+)", md_text)
    if m_doc:
        pdf._doc_number = m_doc.group(1).strip()

    pdf.add_page()
    md_dir = os.path.dirname(os.path.abspath(md_path))
    parse_and_render(md_text, pdf, md_dir)
    pdf.output(pdf_path)
    print(f"PDF written: {pdf_path}")


def batch_convert(md_paths: list, verbose: bool = True) -> list:
    results = []
    for md_path in md_paths:
        md_p = os.path.abspath(md_path)
        if not os.path.exists(md_p):
            if verbose:
                print(f"[SKIP] Not found: {md_p}")
            results.append((md_p, None, False))
            continue
        pdf_p = os.path.splitext(md_p)[0] + ".pdf"
        try:
            convert(md_p, pdf_p)
            results.append((md_p, pdf_p, True))
        except Exception as e:
            print(f"[ERROR] {os.path.basename(md_p)}: {e}")
            results.append((md_p, pdf_p, False))
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/md_to_pdf.py <input.md> [output.pdf]")
        sys.exit(1)
    md_in = sys.argv[1]
    pdf_out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(md_in)[0] + ".pdf"
    convert(md_in, pdf_out)
