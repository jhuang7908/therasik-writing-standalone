#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
build_human_vhh_fr_index.py

：
-  human VHH FR （FASTA） ANARCII （IMGT）
-  index JSON：
  core/scaffolds/human_vhh_fr_index.json

：
-  ANARCII 
- 
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Iterable

# 
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

#  IMGT 
from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map, IMGTNumberingError
from core.vhh_humanization import split_regions, IMGT_REGIONS


# ===== 1.  FASTA  =====
def read_fasta(path: str) -> Iterable[Tuple[str, str]]:
    """FASTA，(seq_id, sequence)"""
    seq_id = None
    chunks: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if seq_id is not None and chunks:
                    yield seq_id, "".join(chunks).replace(" ", "")
                seq_id = line[1:].strip()
                chunks = []
            else:
                chunks.append(line)
        if seq_id is not None and chunks:
            yield seq_id, "".join(chunks).replace(" ", "")


# ===== 2. ANARCII （） =====
def run_anarcii_imgt(seq: str) -> List[Tuple[int, str, str]]:
    """
     ANARCII  IMGT 。
    
    : [(pos, aa, region_name), ...]
    """
    try:
        # 
        rows = imgt_number_anarcii(seq)
        
        # 
        numbering = []
        for row in rows:
            pos = row.get("pos")
            aa = row.get("aa")
            
            if not isinstance(pos, int) or not isinstance(aa, str) or aa == "-":
                continue
            
            # 
            region = _get_region_from_pos(pos)
            numbering.append((pos, aa, region))
        
        return numbering
        
    except IMGTNumberingError as e:
        raise RuntimeError(f"IMGT numbering failed: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error during IMGT numbering: {e}") from e


def _get_region_from_pos(pos: int) -> str:
    """IMGT"""
    if IMGT_REGIONS["FR1"]["start"] <= pos <= IMGT_REGIONS["FR1"]["end"]:
        return "FR1"
    elif IMGT_REGIONS["CDR1"]["start"] <= pos <= IMGT_REGIONS["CDR1"]["end"]:
        return "CDR1"
    elif IMGT_REGIONS["FR2"]["start"] <= pos <= IMGT_REGIONS["FR2"]["end"]:
        return "FR2"
    elif IMGT_REGIONS["CDR2"]["start"] <= pos <= IMGT_REGIONS["CDR2"]["end"]:
        return "CDR2"
    elif IMGT_REGIONS["FR3"]["start"] <= pos <= IMGT_REGIONS["FR3"]["end"]:
        return "FR3"
    elif IMGT_REGIONS["CDR3"]["start"] <= pos <= IMGT_REGIONS["CDR3"]["end"]:
        return "CDR3"
    elif IMGT_REGIONS["FR4"]["start"] <= pos <= IMGT_REGIONS["FR4"]["end"]:
        return "FR4"
    else:
        return "UNKNOWN"


def extract_imgt_maps(numbering) -> Tuple[Dict[int, str], Dict[str, Tuple[int, int]]]:
    """
     ANARCII ：
    - residue_map: {IMGT_position(int): aa}
    - regions: {FR1/CDR1/...: (start, end)}

    numbering : [(pos, aa, region), ...]
    """
    residue_map: Dict[int, str] = {}
    region_bounds: Dict[str, List[int]] = {}

    for pos, aa, region in numbering:
        pos = int(pos)
        residue_map[pos] = aa
        if region not in region_bounds:
            region_bounds[region] = [pos, pos]
        else:
            region_bounds[region][0] = min(region_bounds[region][0], pos)
            region_bounds[region][1] = max(region_bounds[region][1], pos)

    regions: Dict[str, Tuple[int, int]] = {}
    for name, (start, end) in region_bounds.items():
        regions[name] = (int(start), int(end))

    return residue_map, regions


# ===== 3. VHH hallmark & developability  =====
def extract_hallmarks(residue_map: Dict[int, str]) -> Dict[int, str]:
    """VHHhallmark：37 / 44 / 45 / 47（IMGT）"""
    hallmarks: Dict[int, str] = {}
    for pos in [37, 44, 45, 47]:
        aa = residue_map.get(pos)
        if aa:
            hallmarks[pos] = aa
    return hallmarks


def estimate_dev_score(seq: str) -> float:
    """
     developability ：
     0.5， TANGO/CamSol 。
    """
    return 0.5


# ===== 4.  =====
def build_human_vhh_fr_index(
    fasta_path: str,
    out_path: str,
    panel_id: str = "HUMAN_VHH_FR_PANEL_V1",
):
    """VHH FR"""
    index = {
        "panel_id": panel_id,
        "scaffolds": []
    }

    success_count = 0
    error_count = 0
    
    for seq_id, seq in read_fasta(fasta_path):
        print(f"[INFO] Processing scaffold: {seq_id} (len={len(seq)})")
        
        try:
            # 
            rows = imgt_number_anarcii(seq)
            numbering = run_anarcii_imgt(seq)
            residue_map, regions = extract_imgt_maps(numbering)
            
            # （）
            region_seqs = split_regions(rows)
            
            hallmarks = extract_hallmarks(residue_map)
            dev_score = estimate_dev_score(seq)

            scaffold_entry = {
                "id": seq_id,
                "source": "human_vhh_fr_panel",
                "sequence": seq,
                "imgt_positions": {str(k): v for k, v in residue_map.items()},
                "regions": {k: [int(v[0]), int(v[1])] for k, v in regions.items()},
                "region_sequences": region_seqs,  # 
                "hallmark_positions": {str(k): v for k, v in hallmarks.items()},
                "developability_score": float(dev_score),
            }
            index["scaffolds"].append(scaffold_entry)
            success_count += 1
            print(f"  ✅ Success: {seq_id}")
            
        except Exception as e:
            error_count += 1
            print(f"  ❌ Error processing {seq_id}: {e}")
            continue

    # 
    out_path_obj = Path(out_path)
    out_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    # JSON
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"\n[DONE] Built human VHH FR index:")
    print(f"  - Total scaffolds: {len(index['scaffolds'])}")
    print(f"  - Success: {success_count}")
    print(f"  - Errors: {error_count}")
    print(f"  - Output: {out_path}")
    return index


def main():
    parser = argparse.ArgumentParser(
        description="Build human VHH FR index via ANARCII (IMGT)."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Input FASTA file of human VHH FR panel (amino acid).",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output JSON index path, e.g. core/scaffolds/human_vhh_fr_index.json",
    )
    parser.add_argument(
        "--panel-id",
        default="HUMAN_VHH_FR_PANEL_V1",
        help="Panel identifier stored in JSON.",
    )
    args = parser.parse_args()

    build_human_vhh_fr_index(args.input, args.output, panel_id=args.panel_id)


if __name__ == "__main__":
    main()
















