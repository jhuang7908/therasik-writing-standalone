#!/usr/bin/env python3
"""
Extract IMGT-decomposed VHH/VH-like regions for Lofacimig VH1 from in-repo sequences.

Primary AA source
-----------------
``reports/Comparison_TwoVHH_contiguous/Lofacimig/meta.json`` (single-domain heavy chain,
seq_len=130). Cross-checked against the prefix of
``data/design_rules/multispecific_linker_pipeline/esmfold_input.fasta``.

Important
---------
NCATS describes full drug **493 aa / chain** (tandem VH-VH-G1 homodimer). Repository linker
exports contain VH1 + flexible linker only; **VH2 is not present** as plain AA in those files.
Do **not** merge this output into VHH42 single-domain stats without owner-approved governance.

Run (needs ``conda activate anarcii`` for ANARCII):
    python scripts/extract_lofacimig_vhh_regions.py --out-dir data/sequence_provenance/lofacimig
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

from core.numbering.imgt_anarcii import IMGTNumberingError, imgt_number_anarcii
from core.vhh_humanization import split_regions


DEFAULT_LINKER = "GGGGSGGGGSGGGGS"


def _load_meta_vh1() -> Tuple[str, Dict[str, Any]]:
    p = SUITE / "reports/Comparison_TwoVHH_contiguous/Lofacimig/meta.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    seq = (raw.get("sequence") or "").strip().upper().replace(" ", "")
    if not seq:
        raise SystemExit(f"No sequence in {p}")
    meta = {
        "path": str(p.relative_to(SUITE)),
        "seq_len_recorded": raw.get("seq_len"),
        "format": raw.get("format"),
    }
    return seq, meta


def _parse_esmfold_entry() -> Dict[str, Any]:
    """Parse multispecific esmfold FASTA; detect VH1/linker/tail."""
    p = SUITE / "data/design_rules/multispecific_linker_pipeline/esmfold_input.fasta"
    text = p.read_text(encoding="utf-8")
    m = re.search(r">Lofacimig\s*\n([A-Za-z]+)", text)
    if not m:
        raise SystemExit(f"No >Lofacimig record in {p}")
    raw_line = m.group(1).strip().upper()
    if DEFAULT_LINKER in raw_line:
        parts = raw_line.split(DEFAULT_LINKER, 1)
        vh1_prefix = parts[0]
        tail = parts[1] if len(parts) > 1 else ""
    else:
        vh1_prefix = raw_line
        tail = ""
    tail_clean = re.sub(r"[^A-Z]", "", tail)
    return {
        "path": str(p.relative_to(SUITE)),
        "full_raw_upper": raw_line,
        "vh1_prefix": vh1_prefix,
        "post_linker_tail": tail_clean,
        "post_linker_status": (
            "invalid_or_placeholder"
            if len(tail_clean) < 20
            else "review_required"
        ),
    }


def _imgt_split(seq: str) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    rows = imgt_number_anarcii(seq)
    return rows, split_regions(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Lofacimig VH1 IMGT region extraction")
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=SUITE / "data/sequence_provenance/lofacimig",
        help="Output directory (JSON + FASTA + README if missing pieces)",
    )
    args = ap.parse_args()
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    vh1, meta_src = _load_meta_vh1()
    esm = _parse_esmfold_entry()

    if vh1 != esm["vh1_prefix"]:
        raise SystemExit(
            "Sequence mismatch: meta.json VH1 != esmfold prefix before linker.\n"
            f"  meta len={len(vh1)}  esm len={len(esm['vh1_prefix'])}"
        )

    try:
        imgt_rows, regions = _imgt_split(vh1)
    except IMGTNumberingError as e:
        raise SystemExit(f"IMGT numbering failed: {e}") from e

    row_count = len(imgt_rows)

    bundle: Dict[str, Any] = {
        "inn": "Lofacimig",
        "note_ncats_modality": (
            "Therapeutic is tandem VH-VH-G1 (homodimer); this artifact is VH1 single-domain "
            "extract only — see data/_reconciliation/LOFACIMIG_STATUS.md."
        ),
        "sources": {
            "vh1_primary": meta_src,
            "esmfold_construct_line": esm,
        },
        "canonical_vh1_sequence": {
            "amino_acids": vh1,
            "length": len(vh1),
            "imgt_numbered_residue_rows": row_count,
        },
        "imgt_regions_vh1": regions,
        "cdr_lengths": {k: len(regions[k]) for k in ("CDR1", "CDR2", "CDR3")},
        "warnings": [
            "VH2 + CH1 domains not available from linked FASTA (post-linker tail incomplete).",
            "Do not promote into VHH42 aggregate stats without explicit standard approval.",
        ],
    }

    json_path = out_dir / "lofacimig_vh1_imgt_regions_v1.json"
    json_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")

    fasta_lines = [
        ">Lofacimig_VH1_full_domain|imgt_single_chain|source_reports_meta_json",
        vh1,
        ">Lofacimig_VH1_FR1|imgt",
        regions["FR1"],
        ">Lofacimig_VH1_CDR1|imgt",
        regions["CDR1"],
        ">Lofacimig_VH1_FR2|imgt",
        regions["FR2"],
        ">Lofacimig_VH1_CDR2|imgt",
        regions["CDR2"],
        ">Lofacimig_VH1_FR3|imgt",
        regions["FR3"],
        ">Lofacimig_VH1_CDR3|imgt",
        regions["CDR3"],
        ">Lofacimig_VH1_FR4|imgt",
        regions["FR4"],
    ]
    fasta_path = out_dir / "lofacimig_vh1_imgt_regions_v1.fasta"
    fasta_path.write_text("\n".join(fasta_lines) + "\n", encoding="utf-8")

    readme = out_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Lofacimig — sequence provenance (VH1 extraction)\n\n"
            "Generated by `scripts/extract_lofacimig_vhh_regions.py`.\n\n"
            "**VH1 AA** is taken from `reports/Comparison_TwoVHH_contiguous/Lofacimig/meta.json` "
            "(cross-checked to the prefix of `esmfold_input.fasta` before the G4S linker).\n\n"
            "**VH2 / full 493 aa chain** is not reconstructed here; retrieve from patents / WHO INN "
            "primary sources per `data/_reconciliation/LOFACIMIG_STATUS.md` if promotion is required.\n",
            encoding="utf-8",
        )

    print(f"Wrote {json_path.relative_to(SUITE)}")
    print(f"Wrote {fasta_path.relative_to(SUITE)}")
    print("CDR lengths:", bundle["cdr_lengths"])
    for w in bundle["warnings"]:
        print("WARN:", w)


if __name__ == "__main__":
    main()
