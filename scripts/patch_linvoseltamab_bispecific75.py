"""
Populate bispecific_75_atlas/master_table.csv row for Linvoseltamab from KEGG DRUG D12222.

Source (verified fetch): https://www.kegg.jp/entry/D12222 — amino acid sequences as published
on KEGG DRUG for linvoseltamab (heavy chain x2 + common light chain).

Arm convention (matches atlas target_1 / target_2):
  arm1 = tumor arm (BCMA / TNFRSF17) = first heavy + common light
  arm2 = CD3 arm            = second heavy + common light

Kabat FR/CDR columns use classic atlas conventions (VH CDR1 Kabat 31-35, VL 24-34, etc.).
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

from anarcii import Anarcii

_SUITE = Path(__file__).resolve().parents[1]
if str(_SUITE) not in sys.path:
    sys.path.insert(0, str(_SUITE))

from core.humanization.kabat_utils import (  # noqa: E402
    kabat_from_anarcii,
    cdr_span,
    sorted_keys,
)

# Classic Kabat boundaries matching bispecific_75 master_table (see Elranatamab regression)
CDR_VH = [(31, 35), (50, 65), (95, 102)]
CDR_VL = [(24, 34), (50, 56), (89, 97)]

# KEGG D12222 — pasted verbatim from page text (spaces removed). Retrieved 2026-05-09.
HEAVY_BCMA_KEGG = (
    "EVQLVESGGGLVQPGGSLRLSCAASGFTFSNFWMTWVRQAPGKGLEWVANMNQDGSEKYYVDSVKGRFTISRDNAKSSLYLQMNSLRAED"
    "TAVYYCARDREYCISTSCYDDDFDYWGQGTLTVSSASTKGPSVFPLAPCSRSTSESTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAL"
    "QSSGLYSLSSVVTVPSSSLGTKTYTCNVDHKPSNTKVDKRVESKYGPP"
)

HEAVY_CD3_KEGG = (
    "EVQLVESGGGLVQPGRSLRLSCAASGFTFDDYSMHWVRQAPGKGLEWVSGISWNSGSKGYADSVKGRFTISRDNAKNSLYLQMNSLRAED"
    "TALYYCAKYGSGYGKFYHYGLDVWGQGTTVTVSSASTKGPSVFPLAPCSRSTSESTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVL"
    "QSSGLYSLSSVVTVPSSSLGTKTYTCNVDHKPSNTKVDKRVESKYGPP"
)

LIGHT_KEGG = (
    "DIQMTQSPSSLSASVGDRVTITCRASQSISSYLNWYQQKPGKAPKLLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQSYSTPPIT"
    "FGQGTRLEIKRTVAAPSVFIFPPSDEQLKSGTASVVCLLNNFYPREAKVQWKVDNALQSGNSQESVTEQDSKDSTYSLSSTLTLSKADYEKHKVYACE"
    "VTHQGLSSPVTKSFNRGEC"
)


def _trunc_heavy_ch1(h: str) -> str:
    """Trim hinge/Fc: IgG1 hinge begins with CPPC."""
    i = h.find("CPPC")
    return h[:i] if i > 0 else h


def _vh_variable(full_heavy_ch1: str) -> str:
    m = re.search(r"(WGQGT[LT]TVSS)", full_heavy_ch1)
    if not m:
        return full_heavy_ch1
    return full_heavy_ch1[: m.end()]


def _vl_variable(full_lc: str) -> str:
    for pat in (r"FGQGTKVEIK", r"FGGGTKVEIK"):
        m = re.search(pat, full_lc)
        if m:
            return full_lc[: m.end()]
    return full_lc


def _split_vh(kd: dict) -> tuple[str, ...]:
    def cat(lo: int, hi: int) -> str:
        return "".join(kd[k] for k in sorted_keys(kd) if lo <= k[0] <= hi)

    (a, b), (c, d), (e, f) = CDR_VH
    fr1 = cat(1, a - 1)
    c1 = cdr_span(kd, a, b)
    fr2 = cat(b + 1, c - 1)
    c2 = cdr_span(kd, c, d)
    fr3 = cat(d + 1, e - 1)
    c3 = cdr_span(kd, e, f)
    fr4 = cat(f + 1, 113)
    return fr1, c1, fr2, c2, fr3, c3, fr4


def _split_vl(kd: dict) -> tuple[str, ...]:
    def cat(lo: int, hi: int) -> str:
        return "".join(kd[k] for k in sorted_keys(kd) if lo <= k[0] <= hi)

    (a, b), (c, d), (e, f) = CDR_VL
    fr1 = cat(1, a - 1)
    c1 = cdr_span(kd, a, b)
    fr2 = cat(b + 1, c - 1)
    c2 = cdr_span(kd, c, d)
    fr3 = cat(d + 1, e - 1)
    c3 = cdr_span(kd, e, f)
    fr4 = cat(f + 1, 107)
    return fr1, c1, fr2, c2, fr3, c3, fr4


def build_row_fields() -> dict[str, str]:
    an = Anarcii(seq_type="antibody", mode="accuracy", verbose=False)

    h1 = _trunc_heavy_ch1(HEAVY_BCMA_KEGG)
    h2 = _trunc_heavy_ch1(HEAVY_CD3_KEGG)
    lc = LIGHT_KEGG

    vh1 = _vh_variable(h1)
    vh2 = _vh_variable(h2)
    vl = _vl_variable(lc)

    an.number([vh1])
    kd1 = kabat_from_anarcii(an.to_scheme("kabat")["Sequence 1"]["numbering"])
    an.number([vh2])
    kd2 = kabat_from_anarcii(an.to_scheme("kabat")["Sequence 1"]["numbering"])
    an.number([vl])
    kdl = kabat_from_anarcii(an.to_scheme("kabat")["Sequence 1"]["numbering"])

    af1, ac1, af2, ac2, af3, ac3, af4 = _split_vh(kd1)
    bf1, bc1, bf2, bc2, bf3, bc3, bf4 = _split_vh(kd2)
    lf1, lc1, lf2, lc2, lf3, lc3, lf4 = _split_vl(kdl)

    return {
        "vh1_seq": h1,
        "vl1_seq": lc,
        "vh2_seq": h2,
        "vl2_seq": lc,
        "arm1_vh_fr1": af1,
        "arm1_vh_cdr1": ac1,
        "arm1_vh_fr2": af2,
        "arm1_vh_cdr2": ac2,
        "arm1_vh_fr3": af3,
        "arm1_vh_cdr3": ac3,
        "arm1_vh_fr4": af4,
        "arm1_vl_fr1": lf1,
        "arm1_vl_cdr1": lc1,
        "arm1_vl_fr2": lf2,
        "arm1_vl_cdr2": lc2,
        "arm1_vl_fr3": lf3,
        "arm1_vl_cdr3": lc3,
        "arm1_vl_fr4": lf4,
        "arm2_vh_fr1": bf1,
        "arm2_vh_cdr1": bc1,
        "arm2_vh_fr2": bf2,
        "arm2_vh_cdr2": bc2,
        "arm2_vh_fr3": bf3,
        "arm2_vh_cdr3": bc3,
        "arm2_vh_fr4": bf4,
        "arm2_vl_fr1": lf1,
        "arm2_vl_cdr1": lc1,
        "arm2_vl_fr2": lf2,
        "arm2_vl_cdr2": lc2,
        "arm2_vl_fr3": lf3,
        "arm2_vl_cdr3": lc3,
        "arm2_vl_fr4": lf4,
        "analysis_note": "VH/VL from KEGG DRUG D12222 (https://www.kegg.jp/entry/D12222); Kabat splits via ANARCII.",
        "phase_bucket": "phase_II_plus",
        "phase_raw": "Preregistration",
    }


def main() -> None:
    atlas = _SUITE / "data/bispecific_75_atlas/master_table.csv"
    patch = build_row_fields()

    with atlas.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        fieldnames = list(r.fieldnames or [])
        rows = list(r)

    updated = False
    for row in rows:
        if row.get("antibody_id") == "Linvoseltamab":
            for k, v in patch.items():
                if k in row:
                    row[k] = v
            updated = True
            break

    if not updated:
        raise SystemExit("Linvoseltamab row not found")

    with atlas.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)

    print("Updated Linvoseltamab in", atlas)


if __name__ == "__main__":
    main()
