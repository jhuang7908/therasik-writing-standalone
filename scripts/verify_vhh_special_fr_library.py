#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH Special FR Library v1

。
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    jsonl_path = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_special_fr_library_v1.jsonl"
    
    print("=" * 80)
    print(" VHH Special FR Library v1")
    print("=" * 80)
    print()
    
    if not jsonl_path.exists():
        print(f"❌ : {jsonl_path}")
        return
    
    scaffolds = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                scaffolds.append(json.loads(line))
    
    print(f" scaffold : {len(scaffolds)}")
    print()
    
    if not scaffolds:
        print("❌ ")
        return
    
    # 
    example = scaffolds[0]
    print(" scaffold ():")
    print(f"  scaffold_id: {example.get('scaffold_id', 'N/A')}")
    print(f"  n_members: {example.get('n_members', 'N/A')}")
    print(f"  member_ids: {example.get('member_ids', [])}")
    
    consensus = example.get("consensus", {})
    print(f"  consensus.fr1 : {len(consensus.get('fr1', ''))}")
    print(f"  consensus.fr2 : {len(consensus.get('fr2', ''))}")
    print(f"  consensus.fr3 : {len(consensus.get('fr3', ''))}")
    print(f"  consensus.framework_full : {len(consensus.get('framework_full', ''))}")
    
    print(f"   vhh_hallmark: {'vhh_hallmark' in example}")
    print(f"   canonical_proxy_cdr1: {'canonical_proxy_cdr1' in example}")
    print(f"   canonical_proxy_cdr2: {'canonical_proxy_cdr2' in example}")
    print()
    
    # 
    has_consensus = 0
    has_framework_full = 0
    has_hallmark = 0
    has_proxy = 0
    
    for scaffold in scaffolds:
        if "consensus" in scaffold:
            has_consensus += 1
            if scaffold["consensus"].get("framework_full"):
                has_framework_full += 1
        if "vhh_hallmark" in scaffold:
            has_hallmark += 1
        if "canonical_proxy_cdr1" in scaffold and "canonical_proxy_cdr2" in scaffold:
            has_proxy += 1
    
    print(":")
    print(f"   consensus: {has_consensus} / {len(scaffolds)}")
    print(f"   framework_full: {has_framework_full} / {len(scaffolds)}")
    print(f"   vhh_hallmark: {has_hallmark} / {len(scaffolds)}")
    print(f"   canonical_proxy: {has_proxy} / {len(scaffolds)}")
    print()
    
    if (len(scaffolds) == 264 and 
        has_consensus == 264 and 
        has_framework_full == 264 and
        has_hallmark == 264 and
        has_proxy == 264):
        print("✅ ！")
        print(f"  -  scaffold : {len(scaffolds)} = 264 ✓")
        print(f"  -  ✓")
    else:
        print("❌ ！")
        if len(scaffolds) != 264:
            print(f"  -  scaffold : {len(scaffolds)} != 264")
        if has_consensus != 264:
            print(f"  -  consensus: {has_consensus} != 264")
        if has_framework_full != 264:
            print(f"  -  framework_full: {has_framework_full} != 264")
        if has_hallmark != 264:
            print(f"  -  vhh_hallmark: {has_hallmark} != 264")
        if has_proxy != 264:
            print(f"  -  canonical_proxy: {has_proxy} != 264")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()










