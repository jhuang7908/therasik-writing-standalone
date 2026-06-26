#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH Special FR Library v1

 vhh_germline_assets_clean_with_canonical_proxy.jsonl ，
 scaffold ， scaffold 。

 native human FR ， --mode vhh  scaffold 。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def convert_germline_to_scaffold(record: Dict[str, Any]) -> Dict[str, Any]:
    """
     germline  scaffold 
    
    Args:
        record: germline （ segments, vhh_hallmark, canonical_proxy ）
    
    Returns:
        scaffold ， human_vh3_scaffolds.json 
    """
    sequence_id = record.get("sequence_id", "")
    segments = record.get("segments", {})
    
    #  FR 
    fr1 = segments.get("FR1", "")
    fr2 = segments.get("FR2", "")
    fr3 = segments.get("FR3", "")
    fr4 = ""  # VHH  FR4
    
    # 
    framework_full = fr1 + fr2 + fr3 + fr4
    
    #  scaffold_id（ sequence_id）
    #  sequence_id  scaffold_id
    scaffold_id = f"VHH_FR_{sequence_id.replace('|', '_').replace('*', '_').replace(' ', '_')}"
    # ，
    if len(scaffold_id) > 80:
        scaffold_id = scaffold_id[:80]
    
    scaffold = {
        "scaffold_id": scaffold_id,
        "n_members": 1,
        "member_ids": [sequence_id],
        "consensus": {
            "fr1": fr1,
            "fr2": fr2,
            "fr3": fr3,
            "fr4": fr4,
            "framework_full": framework_full,
        },
        #  VHH ，
        "vhh_hallmark": record.get("vhh_hallmark"),
        "canonical_proxy_cdr1": record.get("canonical_proxy_cdr1"),
        "canonical_proxy_cdr2": record.get("canonical_proxy_cdr2"),
        # （，）
        "imgt_map": record.get("imgt_map", {}),
        "kabat_map": record.get("kabat_map", {}),
    }
    
    return scaffold


def main():
    parser = argparse.ArgumentParser(
        description=" VHH Special FR Library v1"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean_with_canonical_proxy.jsonl",
        help=" canonical_proxy  JSONL ",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_special_fr_library_v1.jsonl",
        help=" scaffold  JSONL ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" VHH Special FR Library v1")
    print("=" * 80)
    print()
    
    if not args.input.exists():
        print(f"❌ : {args.input}")
        return
    
    # 
    print(f"[1/3] : {args.input}")
    records = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    
    print(f"  ✅  {len(records)} ")
    print()
    
    #  scaffold 
    print(f"[2/3]  scaffold ...")
    scaffolds = []
    pass_count = 0
    
    for record in records:
        # 
        segments = record.get("segments", {})
        if not all(k in segments for k in ["FR1", "FR2", "FR3"]):
            print(f"  ⚠️ : {record.get('sequence_id', 'unknown')}  FR ")
            continue
        
        scaffold = convert_germline_to_scaffold(record)
        scaffolds.append(scaffold)
        pass_count += 1
    
    print(f"  ✅ : {pass_count}  scaffolds")
    print()
    
    #  JSONL
    print(f"[3/3]  scaffold : {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for scaffold in scaffolds:
            f.write(json.dumps(scaffold, ensure_ascii=False) + "\n")
    
    print(f"  ✅  {len(scaffolds)}  scaffolds")
    print()
    
    # 
    print(":")
    print(f"  : {len(records)}")
    print(f"  : {pass_count}")
    print(f"  /: {len(records) - pass_count}")
    
    # 
    if scaffolds:
        print()
        print(" scaffold ():")
        example = scaffolds[0]
        print(f"  scaffold_id: {example['scaffold_id']}")
        print(f"  n_members: {example['n_members']}")
        print(f"  framework_full : {len(example['consensus']['framework_full'])}")
        print(f"   vhh_hallmark: {'vhh_hallmark' in example}")
        print(f"   canonical_proxy: {'canonical_proxy_cdr1' in example}")
    
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)
    
    if pass_count != len(records):
        print(f"⚠️ :  ({pass_count}) !=  ({len(records)})")
    else:
        print(f"✅ :  = {pass_count} = ")


if __name__ == "__main__":
    main()










