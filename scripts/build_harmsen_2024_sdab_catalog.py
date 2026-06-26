#!/usr/bin/env python3
"""Emit data/reference/harmsen_2024_cross_species_sdabs/v1/catalog.json"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from parse_supplement_spaced_vhh import SUPPLEMENT_ROWS, spaced_row_to_seq

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "reference" / "harmsen_2024_cross_species_sdabs" / "v1" / "catalog.json"

# Front. Immunol. 2024 Table 3 — KD (nM); null = ND in publication
ALBUMIN_KD = {
    "A6L": {"horse": 13.0, "dog": 3.2, "cat": 1.2, "swine": None},
    "A12L": {"horse": 13.0, "dog": 271.0, "cat": 31.0, "swine": 189.0},
    "A16L": {"horse": 11.0, "dog": 13.0, "cat": 2.0, "swine": None},
    "T6T16A12": {"horse": 0.65, "dog": 268.0, "cat": None, "swine": None},
}

# kd × 10^-5 (1/s) from Table 3 where reported
ALBUMIN_KD_OFF = {
    "A6L": {"horse": 966, "dog": 226, "cat": 87, "swine": None},
    "A12L": {"horse": 115, "dog": 1250, "cat": 82, "swine": 2489},
    "A16L": {"horse": 242, "dog": 510, "cat": 29, "swine": None},
    "T6T16A12": {"horse": 14, "dog": 620, "cat": None, "swine": None},
}

# Table 4 — Fab / Fc BLI
FAB_FC_ROWS = [
    {"sdAb": "G6L", "analyte": "Dog Fab", "kd_nm": None, "note": "binding not detectable"},
    {"sdAb": "G13L", "analyte": "Dog Fab", "kd_nm": 70.0, "r2": 0.916},
    {"sdAb": "G18L", "analyte": "Dog Fab", "kd_nm": 38.0, "r2": 0.911},
    {"sdAb": "G19L", "analyte": "Dog Fab", "kd_nm": 62.0, "r2": 0.941},
    {"sdAb": "G3L", "analyte": "Horse Fc", "kd_nm": 0.68, "r2": 0.980},
    {"sdAb": "G23L", "analyte": "Dog Fc", "kd_nm": 0.24, "r2": 0.992},
    {"sdAb": "G24L", "analyte": "Horse Fc", "kd_nm": 4.5, "r2": 0.997},
    {"sdAb": "G24L", "analyte": "Dog Fc", "kd_nm": 2.7, "r2": 0.992},
]


def main() -> None:
    seq_map = {k: spaced_row_to_seq(v) for k, v in SUPPLEMENT_ROWS.items()}

    entries = []
    for clone, seq in sorted(seq_map.items()):
        row: dict = {
            "clone_id": clone,
            "role": "albumin_binding" if clone.startswith("A") else "igg_binding_or_control",
            "vhh_sequence_aa": seq,
            "length_aa": len(seq),
        }
        if clone == "A6":
            row["yeast_expression_label"] = "A6L"
            row["albumin_kd_nm_bli"] = ALBUMIN_KD["A6L"]
            row["kd_offrate_x1e5_per_s"] = ALBUMIN_KD_OFF["A6L"]
        elif clone == "A12":
            row["yeast_expression_label"] = "A12L"
            row["albumin_kd_nm_bli"] = ALBUMIN_KD["A12L"]
            row["kd_offrate_x1e5_per_s"] = ALBUMIN_KD_OFF["A12L"]
        elif clone == "A16":
            row["yeast_expression_label"] = "A16L"
            row["albumin_kd_nm_bli"] = ALBUMIN_KD["A16L"]
            row["kd_offrate_x1e5_per_s"] = ALBUMIN_KD_OFF["A16L"]
        elif clone in {"G3", "G23", "G24"}:
            row["fab_fc_affinity_note"] = "KD in affinity_bli.fab_fc_table4 — Fc binders"
        elif clone in {"G6", "G13", "G18", "G19"}:
            row["fab_fc_affinity_note"] = "Fab binders — KD Table 4 (authors note heterogeneous Fab BLI)"

        entries.append(row)

    catalog = {
        "_meta": {
            "catalog_id": "harmsen_2024_cross_species_sdabs_v1",
            "doi": "10.3389/fimmu.2024.1346328",
            "journal": "Frontiers in Immunology",
            "year": 2024,
            "volume": 15,
            "article_title": (
                "Serum immunoglobulin or albumin binding single-domain antibodies that "
                "enable tailored half-life extension of biologics in multiple animal species"
            ),
            "article_url": (
                "https://www.frontiersin.org/journals/immunology/articles/"
                "10.3389/fimmu.2024.1346328/full"
            ),
            "first_authors": ["Michiel M. Harmsen", "Bart Ackerschott", "Hans de Smit"],
            "sequence_source": (
                "Supplementary Figure 1 — spaced IMGT alignment parsed to linear "
                "(gap tokens '-' omitted); hinge tails omitted from VHH sequence"
            ),
            "affinity_source": "Main text §3.5 — Table 3 (albumin), Table 4 (Fab/Fc BLI)",
            "genbank_accession_range": "PP062726–PP062739",
            "genbank_note": (
                "Publication lists bulk deposit; per-clone accession mapping not "
                "stored in this catalog — query NCBI for authoritative protein records."
            ),
            "schema_version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "affinity_bli": {
            "albumin_kd_nm_table3": ALBUMIN_KD,
            "albumin_kd_offrate_x1e5_per_s_table3": ALBUMIN_KD_OFF,
            "fab_fc_table4": FAB_FC_ROWS,
            "units": {"KD": "nM", "kd_offrate": "×10⁻⁵ s⁻¹"},
        },
        "sequences_supplementary_figure1": seq_map,
        "entries_curated": [
            {
                "clone": "A6",
                "yeast_label": "A6L",
                "type": "albumin",
                "length_aa": len(seq_map["A6"]),
                "sequence": seq_map["A6"],
                "albumin_kd_nm": ALBUMIN_KD["A6L"],
            },
            {
                "clone": "A12",
                "yeast_label": "A12L",
                "type": "albumin",
                "length_aa": len(seq_map["A12"]),
                "sequence": seq_map["A12"],
                "albumin_kd_nm": ALBUMIN_KD["A12L"],
            },
            {
                "clone": "A16",
                "yeast_label": "A16L",
                "type": "albumin",
                "length_aa": len(seq_map["A16"]),
                "sequence": seq_map["A16"],
                "albumin_kd_nm": ALBUMIN_KD["A16L"],
            },
            {
                "construct": "T6T16A12",
                "type": "TeNT_VHH_fusion_albumin_binder",
                "albumin_kd_nm": ALBUMIN_KD["T6T16A12"],
                "sequence_note": "Multimer — component sequences in earlier TeNT work (ref. 41 in article)",
            },
        ],
        "entries_all_clones": entries,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
