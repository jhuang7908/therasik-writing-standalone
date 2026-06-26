"""
VHH germline distance matrix builder (MVP v2)

 JSON ：
- from scripts.vhh_germline_library import get_human_vh3_entries, get_camelid_vhh_entries

：
  segmentation.json （IMGT ），：
  {
    "id": "EGFR_7D12",
    "v_sequence": "QVQLVESGGGLV...",
    "imgt_positions": [1, 2, 3, ...],
    "regions": ["FR1", "FR1", "FR1", "CDR1", ...]
  }

：
  distance_matrix.json：
  {
    "input_vhh_id": "EGFR_7D12",
    "rows": [
      {
        "type": "human",
        "germline_id": "HUMAN_IGHV3-23*01",
        "identity_frac": 0.85,
        "hallmark_penalty": 0.0,
        "vernier_penalty": 2.0,
        "total_score": 0.25,
        "aligned_positions": 80
      },
      ...
    ]
  }
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

from scripts.vhh_germline_library import (
    get_camelid_vhh_entries,
    get_human_vh3_entries,
)

# VHH hallmark  IMGT （）
VHH_HALLMARK_POS = {37, 44, 45, 47}
# Vernier zone ，
VERNIER_POS = {27, 29, 30, 48, 49, 71, 73, 78, 94}


def _extract_fr_map(segmentation: Dict) -> Dict[int, str]:
    """
     segmentation  FR1+FR2+FR3  {imgt_pos: aa} 。

    segmentation ：
      - "v_sequence":  V  AA 
      - "imgt_positions":  IMGT 
      - "regions": （ FR1/CDR1/...）
    """
    v_seq: str = segmentation["v_sequence"]
    imgt_positions: List[int] = segmentation["imgt_positions"]
    regions: List[str] = segmentation["regions"]

    if not (len(v_seq) == len(imgt_positions) == len(regions)):
        raise ValueError(
            f"segmentation ：v_seq={len(v_seq)}, "
            f"imgt_positions={len(imgt_positions)}, regions={len(regions)}"
        )

    fr_map: Dict[int, str] = {}
    for pos, reg, aa in zip(imgt_positions, regions, v_seq):
        if reg.startswith("FR"):
            fr_map[int(pos)] = aa
    return fr_map


def _build_gl_fr_map_for_vhh(segmentation: Dict, gl_sequence: str) -> Dict[int, str]:
    """
     VHH segmentation  FR mask， germline  FR 。
    ：germline  VHH  IMGT （MVP ）。
    """
    v_seq: str = segmentation["v_sequence"]
    imgt_positions: List[int] = segmentation["imgt_positions"]
    regions: List[str] = segmentation["regions"]

    if len(gl_sequence) < len(v_seq):
        # ，，
        # （）
        gl_sequence = gl_sequence + "-" * (len(v_seq) - len(gl_sequence))

    fr_map: Dict[int, str] = {}
    for idx, (pos, reg) in enumerate(zip(imgt_positions, regions)):
        if not reg.startswith("FR"):
            continue
        if idx >= len(gl_sequence):
            continue
        aa_gl = gl_sequence[idx]
        fr_map[int(pos)] = aa_gl

    return fr_map


def _score_pair(
    vhh_fr_map: Dict[int, str],
    gl_fr_map: Dict[int, str],
) -> Dict:
    """
     {imgt_pos: aa}  FR map ：
      - identity_frac:  FR 
      - hallmark_penalty: VHH hallmark （）
      - vernier_penalty: Vernier 
      - total_score: ，（）
    """
    common_pos = sorted(set(vhh_fr_map.keys()) & set(gl_fr_map.keys()))
    if not common_pos:
        return {
            "identity_frac": 0.0,
            "hallmark_penalty": 999.0,
            "vernier_penalty": 0.0,
            "total_score": 999.0,
            "aligned_positions": 0,
        }

    same = 0
    hallmark_penalty = 0.0
    vernier_penalty = 0.0

    for p in common_pos:
        a = vhh_fr_map[p]
        b = gl_fr_map[p]

        if a == b:
            same += 1

        # hallmark ： VHH hydrophilic， human germline /
        if p in VHH_HALLMARK_POS and a != b:
            hallmark_penalty += 3.0  # ， VHH 

        # Vernier: ， penalty（，）
        if p in VERNIER_POS and a != b:
            vernier_penalty += 1.0

    identity_frac = same / len(common_pos)
    # ：1 - identity + penalty（MVP ）
    total = (1.0 - identity_frac) + hallmark_penalty + 0.5 * vernier_penalty

    return {
        "identity_frac": identity_frac,
        "hallmark_penalty": hallmark_penalty,
        "vernier_penalty": vernier_penalty,
        "total_score": total,
        "aligned_positions": len(common_pos),
    }


def build_vhh_germline_distance_matrix(segmentation: Dict) -> Dict:
    """
    ： VHH segmentation， JSON germline 。
    """
    vhh_id = segmentation.get("id", "unknown_vhh")

    # 1)  VHH FR 
    vhh_fr_map = _extract_fr_map(segmentation)

    # 2)  human + camelid germline entries
    human_entries = get_human_vh3_entries()
    camelid_entries = get_camelid_vhh_entries()

    rows: List[Dict] = []

    # 2.1 VHH → camelid（，）
    for entry in camelid_entries:
        gl_seq = entry.get("sequence_aa")
        if not gl_seq:
            continue

        gl_fr_map = _build_gl_fr_map_for_vhh(segmentation, gl_seq)
        score = _score_pair(vhh_fr_map, gl_fr_map)
        rows.append(
            {
                "type": entry.get("species", "camelid"),
                "germline_id": entry.get("id", "unknown_camelid"),
                **score,
            }
        )

    # 2.2 VHH → human（ germline ）
    for entry in human_entries:
        gl_seq = entry.get("sequence_aa")
        if not gl_seq:
            continue

        gl_fr_map = _build_gl_fr_map_for_vhh(segmentation, gl_seq)
        score = _score_pair(vhh_fr_map, gl_fr_map)
        rows.append(
            {
                "type": entry.get("species", "human"),
                "germline_id": entry.get("id", "unknown_human"),
                **score,
            }
        )

    rows_sorted = sorted(rows, key=lambda r: r["total_score"])

    result = {
        "input_vhh_id": vhh_id,
        "rows": rows_sorted,
    }
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Build VHH germline distance matrix using JSON germline libraries."
    )
    parser.add_argument(
        "--segmentation",
        type=str,
        required=True,
        help="Path to VHH segmentation JSON (IMGT )",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Path to output distance matrix JSON",
    )
    args = parser.parse_args()

    seg_path = Path(args.segmentation)
    out_path = Path(args.output)

    segmentation = json.loads(seg_path.read_text(encoding="utf-8"))

    result = build_vhh_germline_distance_matrix(segmentation)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[VHH] distance matrix written to {out_path}")


if __name__ == "__main__":
    main()




















