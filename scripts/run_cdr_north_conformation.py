#!/usr/bin/env python3
"""
Compute "CDR N conformation" for a VHH sequence.

In this repo, we provide two related outputs:
1) A simple canonical classification (canonical_1/2/3/short/long/...) with confidence
   via `core.cdr_canonical.classify_all_cdrs`.
2) A North-style label for H1/H2 (e.g. H1-13-1, H2-10-1) using the repo's heuristics
   from `scripts/analyze_slice3_north_canonical.py` (length-based, IMGT-length input).

Usage:
  python scripts/run_cdr_north_conformation.py ^
    --fasta projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_partial_hallmark.fasta ^
    --out_prefix projects/anti_HSA_VHH/cdr_north_conformation
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map
from core.vhh_humanization import split_regions
from core.cdr_canonical import classify_all_cdrs, get_key_position_residues


def read_first_fasta_sequence(path: Path) -> tuple[str, str]:
    header = ""
    seq_parts: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if seq_parts:
                break
            header = line[1:].strip()
            continue
        seq_parts.append(line)
    seq = "".join(seq_parts).strip().upper()
    if not seq:
        raise ValueError(f"No sequence found in FASTA: {path}")
    return header, seq


def north_h1_label(imgt_cdr1_len: int) -> str:
    return {7: "H1-12-1", 8: "H1-13-1", 9: "H1-14-1"}.get(imgt_cdr1_len, "unknown")


def north_h2_label(imgt_cdr2_len: int) -> str:
    return {7: "H2-9-1", 8: "H2-10-1", 10: "H2-12-1"}.get(imgt_cdr2_len, "unknown")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fasta", required=True, help="Input FASTA (single VHH sequence recommended)")
    ap.add_argument("--out_prefix", required=True, help="Output path prefix (without extension)")
    args = ap.parse_args()

    fasta_path = Path(args.fasta)
    out_prefix = Path(args.out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)

    header, seq = read_first_fasta_sequence(fasta_path)

    rows = imgt_number_anarcii(seq)
    regions = split_regions(rows)
    pos_map = build_pos_to_aa_map(rows)
    key_pos = get_key_position_residues(pos_map)

    cdrs = {k: regions.get(k, "") for k in ["CDR1", "CDR2", "CDR3"]}
    canonical = classify_all_cdrs(cdrs, key_positions=key_pos)

    h1 = north_h1_label(len(cdrs["CDR1"]))
    h2 = north_h2_label(len(cdrs["CDR2"]))

    payload = {
        "input": {
            "fasta": str(fasta_path),
            "header": header,
            "sequence_length": len(seq),
        },
        "cdrs_imgt": cdrs,
        "key_positions_imgt": key_pos,
        "canonical_simple": {
            "cdr1": {
                "canonical_class": canonical["CDR1"]["canonical_class"],
                "length": canonical["CDR1"]["length"],
                "confidence": canonical["CDR1"]["confidence"],
            },
            "cdr2": {
                "canonical_class": canonical["CDR2"]["canonical_class"],
                "length": canonical["CDR2"]["length"],
                "confidence": canonical["CDR2"]["confidence"],
            },
            "cdr3": {
                "canonical_class": canonical["CDR3"]["canonical_class"],
                "length": canonical["CDR3"]["length"],
                "confidence": canonical["CDR3"]["confidence"],
                "vhh_like": canonical["CDR3"]["features"].get("vhh_like", False),
                "is_long_cdr3": canonical["CDR3"]["features"].get("is_long_cdr3", False),
            },
        },
        "north_labels": {
            "H1": h1,
            "H2": h2,
            "H3": "not_applicable",
            "notes": "Repo heuristic based on IMGT CDR lengths (see scripts/analyze_slice3_north_canonical.py).",
        },
    }

    json_path = out_prefix.with_suffix(".json")
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = out_prefix.with_suffix(".md")
    md = []
    md.append("# CDR  N （North / Canonical）\n")
    md.append(f"- ****: `{fasta_path.as_posix()}`\n")
    if header:
        md.append(f"- **FASTA header**: `{header}`\n")
    md.append(f"- ****: {len(seq)} aa\n")
    md.append("\n## CDR （IMGT ）\n")
    md.append(f"- **CDR1** ({len(cdrs['CDR1'])} aa): `{cdrs['CDR1']}`\n")
    md.append(f"- **CDR2** ({len(cdrs['CDR2'])} aa): `{cdrs['CDR2']}`\n")
    md.append(f"- **CDR3** ({len(cdrs['CDR3'])} aa): `{cdrs['CDR3']}`\n")
    md.append("\n## North （H1/H2）\n")
    md.append(f"- **H1**: **{h1}** (IMGT CDR1 ={len(cdrs['CDR1'])})\n")
    md.append(f"- **H2**: **{h2}** (IMGT CDR2 ={len(cdrs['CDR2'])})\n")
    md.append("- **H3**: （H3/CDR3 North canonical class）\n")
    md.append("\n##  canonical_simple（）\n")
    md.append(f"- **CDR1**: **{canonical['CDR1']['canonical_class']}**, ={canonical['CDR1']['confidence']:.3f}\n")
    md.append(f"- **CDR2**: **{canonical['CDR2']['canonical_class']}**, ={canonical['CDR2']['confidence']:.3f}\n")
    md.append(f"- **CDR3**: **{canonical['CDR3']['canonical_class']}**, ={canonical['CDR3']['confidence']:.3f}\n")
    md.append("\n## （IMGT）\n")
    md.append(
        f"- FR1-26={key_pos.get('fr1_26','-')} | CDR1(27)={key_pos.get('cdr1_start','-')} | "
        f"FR2-55={key_pos.get('fr2_55','-')} | CDR2(56)={key_pos.get('cdr2_start','-')} | "
        f"FR3-104={key_pos.get('fr3_104','-')}\n"
    )
    md_path.write_text("".join(md), encoding="utf-8")

    print(f"Wrote:\\n- {json_path}\\n- {md_path}")


if __name__ == "__main__":
    main()

