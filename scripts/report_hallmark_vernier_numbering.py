#!/usr/bin/env python3
"""
Report IMGT numbering for:
- VHH hallmark positions (IMGT: 37, 44, 45, 47)
- Vernier zone positions (this repo provides:
    - vernier_anchor_positions from core/data/position_sets/imgt_position_sets.yaml
    - optionally, full vernier sets if available in data/vernier_zones/ later)

Outputs a concise Markdown + JSON under a project directory.

Usage:
  python scripts/report_hallmark_vernier_numbering.py ^
    --fasta projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_partial_hallmark.fasta ^
    --out_dir projects/anti_HSA_VHH
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed, build_pos_to_aa_map
from core.position_sets.load_imgt_position_sets import get_vhh_hallmarks, get_vernier_anchors


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fasta", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()

    fasta = Path(args.fasta)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    header, seq = read_first_fasta_sequence(fasta)

    numbered = imgt_number_anarcii_indexed(seq)
    rows = numbered["rows"]
    pos_map = build_pos_to_aa_map(rows)

    # Build pos -> seq_idx map
    pos_to_seq_idx: dict[int, int] = {}
    for r in rows:
        pos = r.get("pos")
        seq_idx = r.get("seq_idx")
        if isinstance(pos, int) and isinstance(seq_idx, int):
            # last-one-wins is fine (insertions handled separately elsewhere; we only track base pos)
            pos_to_seq_idx[pos] = seq_idx

    hallmark_positions = sorted(int(x) for x in get_vhh_hallmarks())
    vernier_positions = sorted(int(x) for x in get_vernier_anchors())

    def summarize_positions(pos_list: list[int]) -> list[dict]:
        out: list[dict] = []
        for p in pos_list:
            aa = pos_map.get(p, "-")
            seq_idx = pos_to_seq_idx.get(p, None)
            out.append(
                {
                    "imgt_pos": p,
                    "aa": aa,
                    "sequence_index": seq_idx,
                    "sequence_position": (seq_idx + 1) if isinstance(seq_idx, int) else None,
                }
            )
        return out

    payload = {
        "input": {
            "fasta": str(fasta),
            "header": header,
            "sequence_length": len(seq),
        },
        "hallmark_imgt_positions": hallmark_positions,
        "vernier_anchor_imgt_positions": vernier_positions,
        "hallmark": summarize_positions(hallmark_positions),
        "vernier_anchors": summarize_positions(vernier_positions),
        "notes": [
            "Vernier 'zone' can be defined structurally; this repo currently ships 'vernier_anchor_positions' (28,29,94) as protected anchors.",
            "If you want full vernier zone positions, we should compute them from a structure (distance-to-CDR) like projects/aD11/vernier_zone_analysis.py.",
        ],
    }

    json_path = out_dir / "hallmark_vernier_numbering.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = out_dir / "HallmarkVernier_IMGT.md"
    md_lines: list[str] = []
    md_lines.append("# Hallmark  Vernier zone （IMGT）\n\n")
    md_lines.append(f"- ****: `{fasta.as_posix()}`\n")
    if header:
        md_lines.append(f"- **FASTA header**: `{header}`\n")
    md_lines.append(f"- ****: {len(seq)} aa\n\n")

    md_lines.append("## VHH Hallmark（IMGT ）\n\n")
    md_lines.append("| IMGT |  |  |\n")
    md_lines.append("|---:|:---:|---:|\n")
    for r in payload["hallmark"]:
        md_lines.append(
            f"| {r['imgt_pos']} | {r['aa']} | {r['sequence_position'] if r['sequence_position'] else '-'} |\n"
        )

    md_lines.append("\n## Vernier anchors（IMGT ）\n\n")
    md_lines.append("| IMGT |  |  |\n")
    md_lines.append("|---:|:---:|---:|\n")
    for r in payload["vernier_anchors"]:
        md_lines.append(
            f"| {r['imgt_pos']} | {r['aa']} | {r['sequence_position'] if r['sequence_position'] else '-'} |\n"
        )

    md_lines.append("\n## \n\n")
    md_lines.append("- **Vernier zone** ：CDR、CDR。\n")
    md_lines.append("-  **vernier_anchor_positions**（28/29/94）“/”。\n")
    md_lines.append("- “ vernier zone ”，（CDR）， `projects/aD11/vernier_zone_analysis.py`。\n")

    md_path.write_text("".join(md_lines), encoding="utf-8")

    print(f"Wrote:\n- {json_path}\n- {md_path}")


if __name__ == "__main__":
    main()

