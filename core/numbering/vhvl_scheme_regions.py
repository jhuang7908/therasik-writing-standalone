"""
VH/VL FR–CDR region strings from ANARCII numbering (Kabat or Chothia dict keys).

Uses kabat_utils.cdr_span() so insertion-code residues (e.g. 52A) stay in-range.
Boundaries:
  Kabat: CDR_RANGES_* from kabat_utils (humanization canonical).
  Chothia (``to_scheme('chothia')``): ANARCII still emits **Kabat integer positions** for
  residue keys; H1/H2/L1/L2 use Chothia loop ranges, while CDR3/FR4 use Kabat tail bands
  (VH 95–102 / 103+; VL 89–97 / 98+). Do not use IMGT 105–117 / 118+ on these dicts.
"""

from __future__ import annotations

from typing import Dict

from core.humanization.kabat_utils import KabatDict, cdr_span


def split_regions_kabat_vh(kd: KabatDict) -> Dict[str, str]:
    return {
        "FR1": cdr_span(kd, 1, 25),
        "CDR1": cdr_span(kd, 26, 35),
        "FR2": cdr_span(kd, 36, 49),
        "CDR2": cdr_span(kd, 50, 65),
        "FR3": cdr_span(kd, 66, 94),
        "CDR3": cdr_span(kd, 95, 102),
        "FR4": cdr_span(kd, 103, 500),
    }


def split_regions_kabat_vl(kd: KabatDict) -> Dict[str, str]:
    return {
        "FR1": cdr_span(kd, 1, 23),
        "CDR1": cdr_span(kd, 24, 34),
        "FR2": cdr_span(kd, 35, 49),
        "CDR2": cdr_span(kd, 50, 56),
        "FR3": cdr_span(kd, 57, 88),
        "CDR3": cdr_span(kd, 89, 97),
        "FR4": cdr_span(kd, 98, 500),
    }


def split_regions_chothia_vh(kd: KabatDict) -> Dict[str, str]:
    """Chothia heavy: loop boundaries (H1/H2) are Chothia; tail uses Kabat positions.

    ANARCII ``to_scheme('chothia')`` still emits **Kabat integer positions** (max ~113 for VH),
    not IMGT 1–128. Using IMGT-style 105–117 / 118+ here leaves FR4 empty and mislabels CDR3.
    CDR-H3 / FR4 therefore follow Kabat bands (95–102 / 103+), matching Chothia practice on
    Kabat-numbered structures.
    """
    return {
        "FR1": cdr_span(kd, 1, 25),
        "CDR1": cdr_span(kd, 26, 32),
        "FR2": cdr_span(kd, 33, 51),
        "CDR2": cdr_span(kd, 52, 56),
        "FR3": cdr_span(kd, 57, 94),
        "CDR3": cdr_span(kd, 95, 102),
        "FR4": cdr_span(kd, 103, 500),
    }


def split_regions_chothia_vl(kd: KabatDict) -> Dict[str, str]:
    """Chothia light: Chothia L1/L2 loops; CDR-L3 / FR4 use Kabat positions (89–97 / 98+).

    Same as VH: ``to_scheme('chothia')`` yields Kabat positions (max ~107 for typical VL).
    IMGT-style 105–117 / 118+ does not exist in that dict — FR4 was always empty.
    """
    return {
        "FR1": cdr_span(kd, 1, 23),
        "CDR1": cdr_span(kd, 24, 34),
        "FR2": cdr_span(kd, 35, 49),
        "CDR2": cdr_span(kd, 50, 56),
        "FR3": cdr_span(kd, 57, 88),
        "CDR3": cdr_span(kd, 89, 97),
        "FR4": cdr_span(kd, 98, 500),
    }
