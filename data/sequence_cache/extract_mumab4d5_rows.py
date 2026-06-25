"""Row-major extraction of SEQ ID NO:5 and NO:6 from US5821337.pdf."""
from collections import defaultdict
import re
import fitz

PDF = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\sequence_cache\US5821337.pdf"

CDR_VL = ("RASQDVNTAVA", "SASFLYS", "QQHYTTPP")
CDR_VH = ("GFNIKDTYIH", "RIYPTNGYTRYADSVK", "SRWGGDGFYAMDY")


def words_to_aas(tokens: list[str]) -> list[str]:
    """OCR token list -> one-letter amino acids (one pass)."""
    aa = []
    i, n = 0, len(tokens)

    def peek(k: int) -> str:
        return tokens[i + k] if i + k < n else ""

    while i < n:
        t = tokens[i].strip()
        if not t or t in ("5,821,337", "-continued", "i.", "A.", "R.", "n.", "u.", "Gl"):
            i += 1
            continue
        if re.fullmatch(r"\d+", t.replace("O", "0")) or t in ("1O", "2O", "3O", "4O", "5O", "6O", "7O", "8O", "9O", "1OO", "115", "109", "120"):
            i += 1
            continue

        # 3-letter
        three = {
            "Ser": "S", "Thr": "T", "Tyr": "Y", "Trp": "W", "Phe": "F", "His": "H",
            "Lys": "K", "Arg": "Arg", "Leu": "L", "Ile": "I", "Val": "Val", "Met": "M",
            "Cys": "C", "Pro": "P", "Gln": "Q", "Glu": "E", "Asp": "D", "Asn": "N",
            "Ala": "A", "Gly": "G",
            "Wa": "V", "Va": "V",
        }
        if t in three:
            x = three[t]
            if x == "Arg":
                aa.append("R")
            elif x == "Val":
                aa.append("V")
            else:
                aa.append(x)
            i += 1
            continue

        if t == "As" and peek(1) in ("p", "n"):
            aa.append("D" if peek(1) == "p" else "N")
            i += 2
            continue
        if t == "A" and peek(1) == "rig":
            aa.append("R")
            i += 2
            continue
        if t == "rig":
            aa.append("R")
            i += 1
            continue
        if t == "G" and peek(1) == "1" and peek(2).lower() == "y":
            aa.append("G")
            i += 3
            continue
        if t == "G" and peek(1) in ("in", "ln"):
            aa.append("Q")
            i += 2
            continue
        if t == "G" and peek(1) == "u":
            aa.append("E")
            i += 2
            continue
        if t == "G" and peek(1) == "|" and peek(2) == "n":
            aa.append("Q")
            i += 3
            continue
        if t == "G|" and peek(1) == "n":
            aa.append("Q")
            i += 2
            continue
        if t == "A" and peek(1) == "1" and peek(2).lower() == "a":
            aa.append("A")
            i += 3
            continue
        if t == "Ph" and peek(1) == "e":
            aa.append("F")
            i += 2
            continue
        if t == "Th" and peek(1) == "r":
            aa.append("T")
            i += 2
            continue
        if t == "Se" and peek(1) == "r":
            aa.append("S")
            i += 2
            continue
        if t == "Ty" and peek(1) == "r":
            aa.append("Y")
            i += 2
            continue
        if t == "Tr" and peek(1) == "p":
            aa.append("W")
            i += 2
            continue
        if t == "Me" and peek(1) == "t":
            aa.append("M")
            i += 2
            continue
        if t == "Ly" and peek(1) == "s":
            aa.append("K")
            i += 2
            continue
        if t == "Le" and peek(1) == "u":
            aa.append("L")
            i += 2
            continue
        if t == "Cy" and peek(1) == "s":
            aa.append("C")
            i += 2
            continue
        if t == "H" and peek(1) == "is":
            aa.append("H")
            i += 2
            continue
        if t == "P" and peek(1) == "ro":
            aa.append("P")
            i += 2
            continue
        if t == "I" and peek(1) == "le":
            aa.append("I")
            i += 2
            continue
        if t == "As" and peek(1) == "p":
            aa.append("D")
            i += 2
            continue
        if t == "As" and peek(1) == "in":
            aa.append("N")
            i += 2
            continue
        if t == "A" and peek(1) == "s" and peek(2) == "p":
            aa.append("D")
            i += 3
            continue
        if t == "A" and peek(1) == "s" and peek(2) == "n":
            aa.append("N")
            i += 3
            continue

        i += 1
    return aa


def page_row_tokens(doc: fitz.Document, pno: int, y_lo: float, y_hi: float) -> list[list[str]]:
    page = doc[pno]
    words = page.get_text("words")
    rows: dict[int, list[tuple[float, str]]] = defaultdict(list)
    for w in words:
        x0, y0 = w[0], w[1]
        if not (y_lo <= y0 <= y_hi):
            continue
        key = int(round(y0 / 2) * 2)
        rows[key].append((x0, w[4].strip()))
    out = []
    for key in sorted(rows.keys()):
        line = [t for _, t in sorted(rows[key], key=lambda z: z[0]) if t]
        # split composite tokens
        flat: list[str] = []
        for t in line:
            flat.append(t)
        out.append(flat)
    return out


def rows_to_aa(row_tokens: list[list[str]]) -> str:
    s = []
    for row in row_tokens:
        s.extend(words_to_aas(row))
    return "".join(s)


def main():
    doc = fitz.open(PDF)

    # Page 50: VL middle+end: y 455-750; VL start row: y 730-736
    p50_lo = page_row_tokens(doc, 49, 728, 752)
    p50_mid = page_row_tokens(doc, 49, 450, 720)

    # Page 51: VL end y 50-280; VH y 300-560
    p51_vl_end = page_row_tokens(doc, 50, 50, 285)
    p51_vh = page_row_tokens(doc, 50, 285, 570)

    doc.close()

    # First row of VL (y~733)
    start_aa = rows_to_aa(p50_lo)
    mid_aa = rows_to_aa(p50_mid)
    end_aa = rows_to_aa(p51_vl_end)
    vh_aa = rows_to_aa(p51_vh)

    print("start (728-752):", start_aa[:80], "len", len(start_aa))
    print("mid (450-720):", mid_aa[:80], "len", len(mid_aa))
    print("end (50-285):", end_aa[:80], "len", len(end_aa))
    print("vh blob:", vh_aa[:100], "len", len(vh_aa))

    # Correct order for VL: patent prints top-to-bottom; on page 50 lower y is higher on page.
    # Row y=455 is visually ABOVE row y=733. So reading order: mid (455...) first, then start row (733)? 
    # That can't be right — SEQ ID NO:5 starts at Asp at first row of the sequence block.
    # From layout: LEFT column goes SEQ3, SEQ4, then SEQ5 header, then the first row of SEQ5 is at bottom left (y=733).
    # RIGHT column at same y completes the row. So the FIRST row of actual SEQ5 sequence is y=733 (lower on page = higher y value).
    # The y=455 block is ABOVE on the page = SMALLER y = comes FIRST in vertical reading order for a single column,
    # but the patent has TWO columns: left column is read top to bottom, so left column y=455 text comes before left column y=733.

    # So order: (1) left column from y=455 to y=720 (SEQ4 tail + SEQ5 middle?), (2) then left y=733 row...

    # Actually SEQ ID NO:4 ends at line 85 "Cy s A 1 a". SEQ ID NO:5 starts line 86. The sequence for NO:5:
    # - Metadata lines 87-92
    # - First residue row: could be y=733 full width

    # So the visual order on paper: top of SEQ5 sequence body is NOT at y=455 — the y=455 region might be RIGHT column 
    # continuation of earlier sequences OR the middle of VL.

    # Empirical: concatenate start_aa + mid_aa + end_aa and search for CDR1
    for label, piece in [("start+mid+end", start_aa + mid_aa + end_aa), ("mid+start+end", mid_aa + start_aa + end_aa), ("start+end+mid", start_aa + end_aa + mid_aa)]:
        p = piece
        if CDR_VL[0] in p:
            print(label, "CONTAINS CDR1 at", p.find(CDR_VL[0]))

    blob_candidates = [
        mid_aa + start_aa + end_aa,
        start_aa + mid_aa + end_aa,
        start_aa + end_aa + mid_aa,
    ]
    for i, blob in enumerate(blob_candidates):
        if CDR_VL[0] in blob and all(c in blob for c in CDR_VL):
            print("candidate", i, "len", len(blob))
            ix = blob.find(CDR_VL[0])
            vl = blob[ix - 23 : ix + 86]  # 23 FR1 + 11 CDR1 + ... need 109 total from FR1 start
            # FR1 length to CDR1: 23 residues before RASQ...
            fr1_start = ix - 23
            vl109 = blob[fr1_start : fr1_start + 109]
            print("VL109:", vl109, len(vl109))

    # VH: find EVQL in vh_aa
    for tag, blob in [("p51_vh", vh_aa)]:
        if CDR_VH[0] in blob:
            ix = blob.find("EVQL")
            if ix < 0:
                ix = blob.find(CDR_VH[0]) - 30
            vh120 = blob[ix : ix + 120]
            print("VH120:", vh120, len(vh120), "CDRs", all(c in vh120 for c in CDR_VH))


if __name__ == "__main__":
    main()
