"""
Extract muMAb4D5 murine VH/VL from US5821337.pdf (SEQ ID NO:5 = VL 109aa, NO:6 = VH 120aa).
Uses row-major order: group words by y, sort by x, merge OCR fragments to 1-letter codes.
"""
from __future__ import annotations

import re
import fitz  # PyMuPDF

PDF_PATH = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\sequence_cache\US5821337.pdf"

# Expected CDR substrings (same as humanized trastuzumab; Carter 1992 / 1FVC)
CDR_VL = ("RASQDVNTAVA", "SASFLYS", "QQHYTTPP")
CDR_VH = ("GFNIKDTYIH", "RIYPTNGYTRYADSVK", "SRWGGDGFYAMDY")


def tokenize_row(words: list[tuple[float, float, str]]) -> list[str]:
    """Merge adjacent single-char fragments into tokens."""
    row = sorted(words, key=lambda w: w[0])
    tokens: list[str] = []
    buf = ""
    for x, y, t in row:
        t = t.strip()
        if not t:
            continue
        # merge single-letter fragments like 'G' + '1' + 'y' -> 'G1y'
        if len(t) == 1 and t.isalpha():
            buf += t
        else:
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(t)
    if buf:
        tokens.append(buf)
    return tokens


def ocr_to_aa(tokens: list[str]) -> list[str]:
    """Convert one row of OCR tokens to one-letter amino acid list."""
    aa: list[str] = []
    i = 0
    n = len(tokens)

    def skip_num(t: str) -> bool:
        if re.fullmatch(r"\d+", t.replace("O", "0").replace("o", "0")):
            return True
        if t in ("1O", "2O", "3O", "4O", "5O", "6O", "7O", "8O", "9O", "1OO", "115", "109", "120"):
            return True
        return False

    while i < n:
        t = tokens[i]
        if skip_num(t) or t in ("i.", "A.", "R.", "n.", "u.", "-continued", "5,821,337"):
            i += 1
            continue
        # normalize
        t_low = t.lower().replace("1", "l").replace("|", "l")

        # multi-token lookahead for G1y, Gln, Glu, Asp, Asn, etc.
        def nxt(k: int) -> str:
            return tokens[i + k] if i + k < n else ""

        # Gly: G1y, G ly, Gl y
        if t in ("G", "Gl", "G1") and nxt(1).lower() in ("1y", "ly", "y") and nxt(2).lower() in ("", "y"):
            aa.append("G")
            i += 2 if nxt(1).lower() in ("1y", "ly") else 1
            if i < n and tokens[i].lower() == "y":
                i += 1
            continue
        if t == "G" and nxt(1) == "1" and nxt(2).lower() == "y":
            aa.append("G")
            i += 3
            continue

        # Gln: G + in
        if t == "G" and nxt(1) in ("in", "ln", "in."):
            aa.append("Q")
            i += 2
            continue
        # Glu: G + u
        if t == "G" and nxt(1) in ("u", "lu", "u."):
            aa.append("E")
            i += 2
            continue

        # Ala: A1a
        if t == "A" and nxt(1) == "1" and nxt(2).lower() == "a":
            aa.append("A")
            i += 3
            continue
        if t in ("A1a", "A1", "Ala"):
            aa.append("A")
            i += 1
            continue

        # Arg: A + rig, or Arg
        if t == "A" and nxt(1) == "rig":
            aa.append("R")
            i += 2
            continue
        if t == "rig":
            aa.append("R")
            i += 1
            continue
        if t == "Arg":
            aa.append("R")
            i += 1
            continue

        # Asp/Asn: As + p/n
        if t == "As":
            if nxt(1) in ("p", "P"):
                aa.append("D")
                i += 2
                continue
            aa.append("N")
            i += 2 if nxt(1) in ("n", "in") else 1
            continue
        if t == "Asn" or t == "Asp":
            aa.append("N" if "n" in t.lower() else "D")
            i += 1
            continue

        # Val: Wa, Va, Val
        if t in ("Wa", "Va", "Val"):
            aa.append("V")
            i += 1
            continue

        # Leu
        if t == "Le" and nxt(1) in ("u", "l"):
            aa.append("L")
            i += 2
            continue
        if t == "Leu":
            aa.append("L")
            i += 1
            continue

        # Ile
        if t == "I" and nxt(1) in ("le", "e"):
            aa.append("I")
            i += 2
            continue
        if t == "Ile":
            aa.append("I")
            i += 1
            continue

        # Phe
        if t == "Ph" and nxt(1) == "e":
            aa.append("F")
            i += 2
            continue
        if t == "Phe":
            aa.append("F")
            i += 1
            continue

        # Thr
        if t == "Th" and nxt(1) == "r":
            aa.append("T")
            i += 2
            continue
        if t == "Thr":
            aa.append("T")
            i += 1
            continue

        # Ser
        if t == "Se" and nxt(1) == "r":
            aa.append("S")
            i += 2
            continue
        if t in ("Ser", "Se"):
            aa.append("S")
            i += 1
            continue

        # Tyr
        if t == "Ty" and nxt(1) == "r":
            aa.append("Y")
            i += 2
            continue
        if t == "Tyr":
            aa.append("Y")
            i += 1
            continue

        # Trp
        if t == "Tr" and nxt(1) == "p":
            aa.append("W")
            i += 2
            continue
        if t == "Trp":
            aa.append("W")
            i += 1
            continue

        # Met
        if t == "Me" and nxt(1) == "t":
            aa.append("M")
            i += 2
            continue
        if t == "Met":
            aa.append("M")
            i += 1
            continue

        # Lys
        if t == "Ly" and nxt(1) == "s":
            aa.append("K")
            i += 2
            continue
        if t == "Lys":
            aa.append("K")
            i += 1
            continue

        # His
        if t == "H" and nxt(1) == "is":
            aa.append("H")
            i += 2
            continue
        if t == "His":
            aa.append("H")
            i += 1
            continue

        # Pro
        if t == "P" and nxt(1) == "ro":
            aa.append("P")
            i += 2
            continue
        if t == "Pro":
            aa.append("P")
            i += 1
            continue

        # Cys
        if t == "Cy" and nxt(1) == "s":
            aa.append("C")
            i += 2
            continue

        # Gln single token
        if t == "Gln" or t == "Gl":
            aa.append("Q" if t == "Gln" else "G")
            i += 1
            continue

        # Glu
        if t == "Glu":
            aa.append("E")
            i += 1
            continue

        # single letters that are fragments
        if len(t) == 1 and t.islower():
            i += 1
            continue

        i += 1

    return aa


def extract_page_rows(doc: fitz.Document, page_idx: int, y_min: float, y_max: float) -> list[list[str]]:
    page = doc[page_idx]
    words = page.get_text("words")
    rows: dict[int, list[tuple[float, float, str]]] = {}
    for w in words:
        x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
        if y0 < y_min or y0 > y_max:
            continue
        ry = int(round(y0 / 2.0) * 2)
        rows.setdefault(ry, []).append((x0, y0, text))

    sorted_ys = sorted(rows.keys())
    out: list[list[str]] = []
    for ry in sorted_ys:
        tokens = tokenize_row(rows[ry])
        if not tokens:
            continue
        aas = ocr_to_aa(tokens)
        if aas:
            out.append(aas)
    return out


def rows_to_string(rows: list[list[str]]) -> str:
    return "".join(a for row in rows for a in row)


def main() -> None:
    doc = fitz.open(PDF_PATH)

    # Page 50 (index 49): SEQ ID NO:5 body — left column ~y 733, right column 455-640, bottom 680+
    # Page 51 (index 50): tail of VL + full VH start

    # Collect flat amino acids from manual pipeline using row-merged extraction on full page 50-51
    page = doc[49]
    words = page.get_text("words")
    # SEQ ID NO:5: from y>= 455 (right col mid) OR y>=680 — actually merge ALL y on page 50 from 455 to 750
    bag: list[tuple[float, float, str]] = []
    for w in words:
        x0, y0 = w[0], w[1]
        if 455 <= y0 <= 750:
            bag.append((x0, y0, w[4]))

    # Group by y
    from collections import defaultdict

    rows_d: dict[int, list[tuple[float, float, str]]] = defaultdict(list)
    for x0, y0, t in bag:
        rows_d[int(round(y0 / 3.0) * 3)].append((x0, y0, t))

    seq5_parts: list[str] = []
    for yk in sorted(rows_d.keys()):
        toks = tokenize_row(rows_d[yk])
        aas = ocr_to_aa(toks)
        seq5_parts.extend(aas)

    # Page 50 top part: y 730-750 left column first row of SEQ ID NO:5 (before y=455 block in reading order — 
    # patent prints LEFT column first so y=733 row comes BEFORE y=455 in file order? No, y=733 > 455 so higher y is lower on page. 
    # In PDF, y increases downward. So y=455 is upper part, y=733 is lower part. 
    # So order should be y increasing: first y~455, then ... then y~733. That's WRONG for reading order of two columns!
    # The patent has TWO columns: left column top to bottom, then right column top to bottom OR interleaved rows.
    # From earlier analysis: LEFT column has SEQ ID NO:5 start at y=733, RIGHT column has continuation at same y.
    # So each ROW spans full width: left half then right half at same y.

    # Re-extract: for each y bucket, take ALL x order (left then right in one row)
    doc.close()

    doc = fitz.open(PDF_PATH)
    vl_aa: list[str] = []
    vh_aa: list[str] = []

    def collect_rows(pidx: int, y0_lo: float, y0_hi: float) -> list[list[str]]:
        page = doc[pidx]
        words = page.get_text("words")
        rd: dict[int, list[tuple[float, float, str]]] = defaultdict(list)
        for w in words:
            x0, y0 = w[0], w[1]
            if y0_lo <= y0 <= y0_hi:
                rd[int(round(y0 / 4.0) * 4)].append((x0, y0, w[4]))
        rows_out: list[list[str]] = []
        for yk in sorted(rd.keys()):
            toks = tokenize_row(rd[yk])
            aas = ocr_to_aa(toks)
            if aas:
                rows_out.append(aas)
        return rows_out

    # Page 50: rows 455-750 cover middle+end of VL; missing start at y~733 left+right
    r50 = collect_rows(49, 450, 760)
    s50 = "".join("".join(r) for r in r50)

    # Page 51: lines 1-19 = end of VL (before SEQ ID NO:6); y ~ 50-280
    r51_top = collect_rows(50, 40, 285)
    s51_top = "".join("".join(r) for r in r51_top)

    # SEQ ID NO:6: page 51 y ~ 300-560
    r51_vh = collect_rows(50, 285, 565)
    s51_vh = "".join("".join(r) for r in r51_vh)

    # Page 50 also need y~600-750 for first row DIVMTQS... — included in 450-760

    doc.close()

    # Assemble VL: patent order is complex; use s50 + s51_top and take first 109 aa that contain CDRs
    # Heuristic: find substring RASQDVNTAVA in concatenation
    blob = s50 + s51_top
    # Remove obvious VH prefix if any
    cdr1 = CDR_VL[0]
    ix = blob.find(cdr1)
    if ix < 0:
        print("Could not find VL CDR1 in blob; dumping blob head/tail")
        print(blob[:200], "...", blob[-200:])
        return

    # FR1 start: murine starts DIVMTQS per coordinate row1 — search backward from ix not reliable.
    # Take 109 aa: from (ix - 23) approx FR1 length — VL FR1 ~ residues 1-23, CDR1 starts 24
    # Kabat L: CDR1 starts at position 24. So residues 1-23 are FR1.
    start = max(0, ix - 23)
    vl = blob[start : start + 109]
    if len(vl) < 109:
        vl = blob[ix - 23 : ix + 86]  # 23+86=109 if CDR1 len 11... actually 23+11+109-34 = need different math
    # Simpler: take from first D of DIVMTQ if present
    d0 = blob.find("DIVMTQ")
    if d0 >= 0:
        vl = blob[d0 : d0 + 109]
    else:
        vl = blob[start : start + 109]

    print("VL raw length", len(vl), vl)
    print("CDR check VL:", all(c in vl for c in CDR_VL))

    # VH: s51_vh after "EVQ" or find GFNIKDTYIH
    hb = s51_vh
    ixh = hb.find(CDR_VH[0])
    if ixh < 0:
        print("VH blob:", hb[:300])
        return
    dvh = hb.find("EVQ")
    if dvh >= 0:
        vh = hb[dvh : dvh + 120]
    else:
        vh = hb[max(0, ixh - 30) : max(0, ixh - 30) + 120]

    print("VH raw length", len(vh), vh)
    print("CDR check VH:", all(c in vh for c in CDR_VH))

    # Refine: use only alphanumeric chain
    vl = re.sub(r"[^A-Z]", "", vl.upper())[:109]
    vh = re.sub(r"[^A-Z]", "", vh.upper())[:120]

    print("\n=== FINAL ===")
    print("muMAb4D5 VL (109):", vl)
    print("muMAb4D5 VH (120):", vh)


if __name__ == "__main__":
    main()
