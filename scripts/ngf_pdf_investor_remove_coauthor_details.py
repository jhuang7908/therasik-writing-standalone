# -*- coding: utf-8 -*-
r"""
/：“”/，
。（/Genomab ）。

  python scripts/ngf_pdf_investor_remove_coauthor_details.py
  NGF_PDF=.pdf 。 TheraPet_NGF_Proposal_v12_references.pdf  v10。

: Antibody_Engineer_Suite/_NGF_.pdf
       Documents/

:  + （ redact  TTF ， mupdf ）。
：，「」、「 key」， / 。
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = [
    Path.home() / "Documents" / "TheraPet_NGF_Proposal_v12_references.pdf",
    Path(
        r"C:\Users\NextVivo\AppData\Roaming\Claude\local-agent-mode-sessions\54c4cb55-7338-4617-8790-8e06a25e10cb"
        r"\e6e926a6-8c05-4e6a-957e-931ebcca9fb9\local_d4a6c91e-75d0-4491-beb6-8c8ae7299bda\outputs"
        r"\_NGF_v10.pdf"
    ),
]
OUT1 = ROOT / "_NGF_.pdf"
OUT2 = Path.home() / "Documents" / "_NGF_.pdf"
FONT = Path(r"C:\Windows\Fonts\msyh.ttc")
FN = "ngf_msyh"  # embedded name


def _src() -> Path:
    p = os.environ.get("NGF_PDF", "")
    if p:
        return Path(p)
    for d in DEFAULTS:
        if d.is_file():
            return d
    raise SystemExit(
        "No input. Set NGF_PDF=... or add TheraPet_NGF_Proposal_v12_references.pdf under Documents."
    )


# (search_string, replacement) —  key 
REPL: list[tuple[str, str]] = [
    # 
    (
        "",
        "（/）",
    ),
    # +
    ("", "（/）",),
    # 
    ("", "/（",),
    ("", "（",),
    ("", "",),  # 「」
]


def _covered(qv: fitz.Quad, kept: list[fitz.Quad]) -> bool:
    r_cur = qv.rect
    cx = (r_cur.x0 + r_cur.x1) / 2.0
    cy = (r_cur.y0 + r_cur.y1) / 2.0
    for oq in kept:
        b = oq.rect
        if b.x0 - 0.3 <= cx <= b.x1 + 0.3 and b.y0 - 0.3 <= cy <= b.y1 + 0.3:
            return True
    return False


def _expand(r: fitz.Rect, page: fitz.Page, margin: float = 1.2) -> fitz.Rect:
    o = fitz.Rect(r.x0 - margin, r.y0 - margin, r.x1 + margin, r.y1 + margin) & page.rect
    return o


def main() -> int:
    if not FONT.is_file():
        print("Need CJK font:", FONT)
        return 1
    sp = str(FONT)
    src = _src()
    doc = fitz.open(src)
    n_pages = len(doc)
    for j in range(n_pages):
        doc[j].insert_font(FN, sp)

    work: list[tuple[int, fitz.Rect, str, int]] = []  # page, rect, new, keylen
    kept: list[fitz.Quad] = []  # larger rects already chosen

    for key, new in REPL:
        for pi in range(n_pages):
            page = doc[pi]
            hits = page.search_for(key, quads=True) or page.search_for(key) or []
            for r0 in hits:
                if isinstance(r0, fitz.Quad):
                    qv: fitz.Quad = r0
                    r = qv.rect
                else:
                    r = fitz.Rect(r0)
                    qv = r.quad
                if _covered(qv, kept):
                    continue
                klen = len(key)
                work.append((pi, r, new, klen))
                kept.append(qv)
    if not work:
        print("No substrings found — PDF text may have changed.", src)
        doc.close()
        return 1
    work.sort(key=lambda t: t[0] * 1000 + t[1].y0)  # page, then y, stable
    n_red = 0
    for pi, r, new, _ in work:
        p = doc[pi]
        rr = _expand(r, p, 0.5)
        p.add_redact_annot(rr, fill=(1, 1, 1), cross_out=False)  # no text here
        n_red += 1
    for pi in range(n_pages):
        doc[pi].apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)  # text=0, white only
    n_ins = 0
    for pi, r, new, klen in sorted(work, key=lambda t: (t[0], t[1].y0, t[1].x0)):
        p = doc[pi]
        ex = _expand(fitz.Rect(r), p, 1.0)
        w = ex.width
        h = ex.height
        h = max(26.0, h, min(140.0, 16.0 * (1 + len(new) // 32)))
        box = fitz.Rect(ex.x0, ex.y0, ex.x0 + max(w, 230), ex.y0 + h)
        box.intersect(
            fitz.Rect(
                p.rect.x0,
                p.rect.y0,
                p.rect.x1,
                p.rect.y1,
            )
        )  # type: ignore[assignment]
        if box.is_empty:
            continue
        fs = 8.2 if len(new) > 45 else 9.0
        ovr = p.insert_textbox(
            box,
            new,
            fontname=FN,
            fontfile=sp,
            fontsize=fs,
            lineheight=1.1,
            color=(0, 0, 0),
        )
        n_ins += 1
        if ovr < 0:
            b2 = fitz.Rect(
                box.x0,
                box.y0,
                box.x1,
                min(box.y1 + 28.0, p.rect.y1 - 2.0),
            )
            p.insert_textbox(
                b2,
                new,
                fontname=FN,
                fontfile=sp,
                fontsize=fs - 0.6,
                lineheight=1.05,
                color=(0, 0, 0),
            )

    doc.save(OUT1.as_posix(), garbage=2, deflate=True)
    doc.close()
    print("Wrote", OUT1, f"(redact regions {n_red}, ins {n_ins}) from", src.name)
    if OUT2.parent.is_dir():
        shutil.copy2(OUT1, OUT2)
        print("Copy", OUT2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
