#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 curated IGHJ FR4 

：
- 6 （IGHJ1-6）
- fr4_len  11
- fr4_aa  ^WG.G
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def validate_curated_fr4(json_path: Path) -> tuple[bool, list[str]]:
    """
     curated FR4 JSON
    
    Returns:
        (all_pass, error_messages)
    """
    errors = []
    
    #  JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    #  1: 6 
    expected_genes = [f"IGHJ{i}*01" for i in range(1, 7)]
    missing_genes = [g for g in expected_genes if g not in data]
    if missing_genes:
        errors.append(f": {', '.join(missing_genes)}")
    
    # 
    for ighj_id in sorted(data.keys()):
        entry = data[ighj_id]
        
        #  2: fr4_len  11
        fr4_len = entry.get("fr4_len", 0)
        if fr4_len != 11:
            errors.append(f"{ighj_id}: fr4_len={fr4_len},  11")
        
        #  3: fr4_aa  ^WG.G
        fr4_aa = entry.get("fr4_aa", "")
        if not re.match(r'^WG.G', fr4_aa):
            errors.append(f"{ighj_id}: fr4_aa={fr4_aa},  ^WG.G")
        
        #  4: fr4_motif_4aa  fr4_aa[:4]
        fr4_motif_4aa = entry.get("fr4_motif_4aa", "")
        expected_motif = fr4_aa[:4] if fr4_aa else ""
        if fr4_motif_4aa != expected_motif:
            errors.append(f"{ighj_id}: fr4_motif_4aa={fr4_motif_4aa},  {expected_motif}")
    
    all_pass = len(errors) == 0
    return all_pass, errors


def main():
    parser = argparse.ArgumentParser(
        description=" curated IGHJ FR4 "
    )
    parser.add_argument(
        "--json_file",
        type=Path,
        default=PROJECT_ROOT / "data" / "ighj_curated_fr4.json",
        help=" JSON ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" curated IGHJ FR4 ")
    print("=" * 80)
    print()
    
    json_path = Path(args.json_file)
    if not json_path.is_absolute():
        json_path = PROJECT_ROOT / json_path
    
    if not json_path.exists():
        print(f"❌ JSON : {json_path}")
        return
    
    print(f": {json_path}")
    print()
    
    # 
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(":")
    for ighj_id in sorted(data.keys()):
        entry = data[ighj_id]
        print(f"  {ighj_id}: fr4_motif_4aa={entry.get('fr4_motif_4aa', 'N/A')}, fr4_len={entry.get('fr4_len', 0)}")
    print()
    
    # 
    all_pass, errors = validate_curated_fr4(json_path)
    
    print("=" * 80)
    if all_pass:
        print("✅ PASS: ")
    else:
        print("❌ FAIL: :")
        for error in errors:
            print(f"  - {error}")
    print("=" * 80)


if __name__ == "__main__":
    main()













