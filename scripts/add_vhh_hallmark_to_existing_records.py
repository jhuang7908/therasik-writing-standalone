#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH germline  VHH hallmark 

 Kabat  37/44/45/47  VHH hallmark 。
"""

from __future__ import annotations

import argparse
import json
import csv
from pathlib import Path
from collections import Counter
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# VHH hallmark （Kabat ）
VHH_HALLMARK_POSITIONS = {
    37: {
        "typical_vhh_aas": ["F", "Y", "V"],
        "typical_human_vh_aas": ["V", "I", "L"],
    },
    44: {
        "typical_vhh_aas": ["E", "Q", "D"],
        "typical_human_vh_aas": ["G"],
    },
    45: {
        "typical_vhh_aas": ["R", "K"],
        "typical_human_vh_aas": ["L"],
    },
    47: {
        "typical_vhh_aas": ["W"],
        "typical_human_vh_aas": ["W"],
    },
}


def calculate_vhh_hallmark_from_kabat(kabat_map: Dict[str, str]) -> Dict[str, Any]:
    """
     Kabat  VHH hallmark 
    
    Args:
        kabat_map: {kabat_pos: aa} （pos ， "37", "44"）
    
    Returns:
        {
            "kabat_positions": {"37": "Y", "44": "Q", "45": "R", "47": "W"},
            "score": 0.0-1.0,
            "label": "vhh_like" | "vh_like" | "ambiguous"
        }
    """
    hallmark_positions = {}
    matches = 0
    total = 0
    
    for pos in [37, 44, 45, 47]:
        pos_str = str(pos)
        aa = kabat_map.get(pos_str, "-")
        hallmark_positions[str(pos)] = aa
        
        if aa and aa != "-":
            total += 1
            hallmark_def = VHH_HALLMARK_POSITIONS.get(pos, {})
            typical_vhh_aas = hallmark_def.get("typical_vhh_aas", [])
            if aa in typical_vhh_aas:
                matches += 1
    
    #  score（）
    score = matches / total if total > 0 else 0.0
    
    # 
    if score >= 0.75:  # 3/4  4/4 
        label = "vhh_like"
    elif score <= 0.25:  # 0/4  1/4 
        label = "vh_like"
    else:  # 2/4 
        label = "ambiguous"
    
    return {
        "kabat_positions": hallmark_positions,
        "score": round(score, 4),
        "label": label,
    }


def main():
    parser = argparse.ArgumentParser(
        description=" VHH germline  VHH hallmark "
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean.jsonl",
        help=" clean JSONL ",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean.jsonl",
        help=" JSONL （）",
    )
    parser.add_argument(
        "--qc_csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "qc" / "vhh_hallmark_distribution.csv",
        help=" Hallmark  CSV ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" VHH germline  VHH hallmark ")
    print("=" * 80)
    print()
    
    if not args.input.exists():
        print(f"❌ : {args.input}")
        return
    
    # 
    print(f"[1/4] : {args.input}")
    records = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    
    print(f"  ✅  {len(records)} ")
    print()
    
    #  vhh_hallmark
    print(f"[2/4]  VHH hallmark ...")
    label_counts = Counter()
    pass_count = 0
    
    for record in records:
        kabat_map = record.get("kabat_map", {})
        
        if not kabat_map:
            print(f"  ⚠️ : {record.get('sequence_id', 'unknown')}  kabat_map")
            continue
        
        #  VHH hallmark
        vhh_hallmark = calculate_vhh_hallmark_from_kabat(kabat_map)
        record["vhh_hallmark"] = vhh_hallmark
        
        label_counts[vhh_hallmark["label"]] += 1
        pass_count += 1
    
    print(f"  ✅ : {pass_count} ")
    print()
    
    # 
    print(f"[3/4]  Hallmark ...")
    print(f"  vhh_like: {label_counts['vhh_like']} ")
    print(f"  vh_like: {label_counts['vh_like']} ")
    print(f"  ambiguous: {label_counts['ambiguous']} ")
    print()
    
    # 
    print(f"[4/4] : {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  ✅  {len(records)} ")
    print()
    
    #  QC CSV
    print(f"   Hallmark : {args.qc_csv}")
    args.qc_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(args.qc_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["", "", "", ""])
        writer.writerow([])
        writer.writerow([""])
        total = pass_count
        for label in ["vhh_like", "vh_like", "ambiguous"]:
            count = label_counts[label]
            percentage = count / total * 100 if total > 0 else 0.0
            writer.writerow([label, "", count, f"{percentage:.2f}%"])
    print(f"  ✅ ")
    print()
    
    # 
    if pass_count != len(records):
        print(f"⚠️ : PASS  ({pass_count}) !=  ({len(records)})")
    else:
        print(f"✅ : PASS  = {pass_count} = ")
    
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)
    print(f": {len(records)}")
    print(f"PASS : {pass_count}")
    print(f"Hallmark :")
    for label, count in sorted(label_counts.items()):
        percentage = count / pass_count * 100 if pass_count > 0 else 0.0
        print(f"  {label}: {count} ({percentage:.1f}%)")
    print("=" * 80)


if __name__ == "__main__":
    main()










