"""
Fix NGF  PDF: (1) number references 1–8, (2) replace Webster with Brown 7–8, (3) match 11pt body.
Uses PyMuPDF; no Word. Process only from original v10 that still contains "Webster".
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import fitz

DEFAULT_SRC = Path(
    os.environ.get(
        "NGF_PDF",
        r"C:\Users\NextVivo\AppData\Roaming\Claude\local-agent-mode-sessions\54c4cb55-7338-4617-8790-8e06a25e10cb"
        r"\e6e926a6-8c05-4e6a-957e-931ebcca9fb9\local_d4a6c91e-75d0-4491-beb6-8c8ae7299bda\outputs"
        r"\_NGF_v10.pdf",
    )
)
ROOT = Path(__file__).resolve().parents[1]
OUT_PDF = ROOT / "_NGF_v12_refs_from_pdf.pdf"
DOCS_PDF = Path.home() / "Documents" / "TheraPet_NGF_Proposal_v12_references.pdf"

# Page 24 in document = 0-based index 23
PAGE_24 = 23
# Webster block (two display lines) — y0 must stay >= 230 so  (y~214–228) is untouched
REDACT_WEBSTER = fitz.Rect(54.0, 230.0, 536.0, 270.0)
# Item [8] is placed *below* item [7] using insert_textbox() return value = unused height in the box
# (over-large box → large unused), so 7&8 are not left with a blank "dead zone" between them.
BROWN7_BOX_TOP = 228.0
BROWN_BOX_RIGHT = 550.0
BROWN_BOX_LEFT = 56.0
# Extra space (pt) between the last line of [7] and the first line of [8] — same order as 
BROWN_7_8_GAP = 3.0
EDITABLE_REFS_OUT = Path(__file__).resolve().parents[1] / "TheraPet_NGF_refs_7_8_PASTE_INTO_WORD.txt"
DOCS_REFS_OUT = Path.home() / "Documents" / "TheraPet_NGF_refs_7_8_PASTE_INTO_WORD.txt"

# Reference line height / font: match Gearing line (v10) ~ 11.0 pt
FONTSIZE = 11.0
# Baseline: bottom of char box ~ rect.y1 - small nudge
BASELINE_F = 0.2  # of line height, subtracted from y1
# Number column: left of body (body starts x~56.7)
NUM_X = 40.0

FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
]

# (page_index 0-based, search needle for first line of the entry)
# Order = reference list 1..6. Must match the published v10 layout.
REF_MARKERS: list[tuple[int, str]] = [
    (22, "Gearing DP, Virtue"),
    (22, "Lascelles BDX, Knazovicky"),
    (23, "Corral MJ, Moyaert"),
    (23, "EMA / CVMP"),
    (23, "FDA / CVM"),
    (23, ""),
]

BROWN_7 = (
    "Brown DC, Boston R, Coyne JC, Farrar JT. A novel approach to the use of animals in studies of pain: "
    "validation of the canine brief pain inventory in canine bone cancer. "
    "Pain Med. 2009, 10(1): 133-142. PMID: 18823385. DOI: 10.1111/j.1526-4637.2008.00513.x。"
)
BROWN_8 = (
    "Brown DC, Boston RC, Coyne JC, Farrar JT. Ability of the Canine Brief Pain Inventory to detect response to "
    "treatment in dogs with osteoarthritis. J Am Vet Med Assoc. 2008, 233(8): 1278-1283. "
    "PMID: 19180716. DOI: 10.2460/javma.233.8.1278。"
)


def _pick_font() -> str:
    for f in FONT_CANDIDATES:
        if f.is_file():
            return str(f)
    return ""


def _baseline_y(rect: fitz.Rect) -> float:
    h = rect.y1 - rect.y0
    return rect.y1 - max(1.0, h * BASELINE_F)


def _process_doc(doc: fitz.open, fpath: str) -> int:
    """Insert 1.–6. on correct pages, then 7.–8. for Brown."""
    doc[22].insert_font("ngf", fpath)

    n = 1
    for pg_idx, needle in REF_MARKERS:
        p = doc[pg_idx]
        h = p.search_for(needle)
        if not h:
            print(f"Missing ref marker: {needle!r} on page {pg_idx+1}")
            return 1
        r0 = fitz.Rect(h[0])
        yb = _baseline_y(r0)
        p.insert_text(
            (NUM_X, yb),
            f"{n}. ",
            fontname="ngf",
            fontfile=fpath,
            fontsize=FONTSIZE,
            color=(0, 0, 0),
        )
        n += 1
    if n != 7:
        print("Expected 6 pref entries, got", n - 1)
        return 1

    p = doc[PAGE_24]
    t = p.get_text()
    if "Webster" not in t:
        print("No 'Webster' in source — use original v10 PDF. Abort.")
        return 1

    p.add_redact_annot(REDACT_WEBSTER, fill=(1, 1, 1))
    p.apply_redactions()

    # 7. / 8. — body x=56; "n." in column NUM_X. Item 8 y-position follows item 7 text height (tight).
    y7 = BROWN7_BOX_TOP + 0.85 * FONTSIZE
    p.insert_text(
        (NUM_X, y7),
        "7. ",
        fontname="ngf",
        fontfile=fpath,
        fontsize=FONTSIZE,
        color=(0, 0, 0),
    )

    page_h = p.rect.y1
    r7 = fitz.Rect(
        BROWN_BOX_LEFT,
        BROWN7_BOX_TOP,
        BROWN_BOX_RIGHT,
        min(BROWN7_BOX_TOP + 500.0, page_h - 6.0),
    )
    fs7 = FONTSIZE
    lh = 1.2
    rc1 = -1.0
    # rc >= 0: text committed; return value = unused space in rect (tall box is OK for tight vertical gap)
    while fs7 >= 7.5:
        rc1 = p.insert_textbox(
            r7,
            BROWN_7,
            fontname="ngf",
            fontfile=fpath,
            fontsize=fs7,
            lineheight=lh,
            color=(0, 0, 0),
        )
        if rc1 >= 0:
            break
        fs7 -= 0.4
    if rc1 < 0:
        print("Could not place Brown [7] text; box too small.")
        return 1

    # y where [8] starts: immediately under real end of [7] text, + small gap
    y8_top = (r7.y1 - rc1) + BROWN_7_8_GAP
    p.insert_text(
        (NUM_X, y8_top + 0.85 * fs7),
        "8. ",
        fontname="ngf",
        fontfile=fpath,
        fontsize=fs7,
        color=(0, 0, 0),
    )

    r8h = 220.0
    rc2 = -1.0
    fs8 = fs7
    while fs8 >= 7.5 and r8h < 500.0:
        r8 = fitz.Rect(
            BROWN_BOX_LEFT,
            y8_top,
            BROWN_BOX_RIGHT,
            min(y8_top + r8h, page_h - 4.0),
        )
        rc2 = p.insert_textbox(
            r8,
            BROWN_8,
            fontname="ngf",
            fontfile=fpath,
            fontsize=fs8,
            lineheight=lh,
            color=(0, 0, 0),
        )
        if rc2 >= 0:
            break
        fs8 -= 0.4
        r8h += 50.0
    if rc2 < 0:
        print("Could not place Brown [8] text; increase r8h or lower fs.")
        return 1

    _write_editable_refs()
    return 0


def _write_editable_refs() -> None:
    s = (
        " 7.–8.（ Word  PDF，； PDF  Word ）\n\n"
        "7. " + BROWN_7 + "\n\n"
        "8. " + BROWN_8 + "\n"
    )
    for path in (EDITABLE_REFS_OUT, DOCS_REFS_OUT):
        try:
            path.write_text(s, encoding="utf-8")
        except OSError as e:
            print("Note: could not write", path, e)
    print("Editable copy:", EDITABLE_REFS_OUT)
    print("Editable copy:", DOCS_REFS_OUT)


def main() -> int:
    fpath = _pick_font()
    if not fpath:
        print("No CJK font under C:\\\\Windows\\\\Fonts. Install msyh/simsun.")
        return 1
    if not DEFAULT_SRC.is_file():
        print("Input PDF not found:", DEFAULT_SRC)
        return 1

    doc = fitz.open(DEFAULT_SRC)
    err = _process_doc(doc, fpath)
    if err:
        doc.close()
        return err
    doc.save(OUT_PDF.as_posix(), garbage=2, deflate=True)
    doc.close()
    print("Wrote:", OUT_PDF)
    if DOCS_PDF.parent.is_dir():
        shutil.copy2(OUT_PDF, DOCS_PDF)
        print("Copy:", DOCS_PDF)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
