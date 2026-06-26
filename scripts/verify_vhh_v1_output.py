#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH v1 

：
1.  264
2.  vhh_hallmark 
3.  canonical_proxy_cdr1  canonical_proxy_cdr2
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    jsonl_path = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean_with_canonical_proxy.jsonl"
    
    print("=" * 80)
    print(" VHH v1 ")
    print("=" * 80)
    print()
    
    if not jsonl_path.exists():
        print(f"❌ : {jsonl_path}")
        return
    
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    
    print(f": {len(records)}")
    
    # 
    has_hallmark = 0
    has_proxy_cdr1 = 0
    has_proxy_cdr2 = 0
    pass_count = 0
    
    for record in records:
        if "vhh_hallmark" in record:
            has_hallmark += 1
        if "canonical_proxy_cdr1" in record and record["canonical_proxy_cdr1"]:
            has_proxy_cdr1 += 1
        if "canonical_proxy_cdr2" in record and record["canonical_proxy_cdr2"]:
            has_proxy_cdr2 += 1
        
        # （）
        if ("vhh_hallmark" in record and 
            "canonical_proxy_cdr1" in record and record["canonical_proxy_cdr1"] and
            "canonical_proxy_cdr2" in record and record["canonical_proxy_cdr2"]):
            pass_count += 1
    
    print(f" vhh_hallmark: {has_hallmark} / {len(records)}")
    print(f" canonical_proxy_cdr1: {has_proxy_cdr1} / {len(records)}")
    print(f" canonical_proxy_cdr2: {has_proxy_cdr2} / {len(records)}")
    print(f" (PASS): {pass_count} / {len(records)}")
    print()
    
    if len(records) == 264 and pass_count == 264:
        print("✅ ！")
        print(f"  - : {len(records)} = 264 ✓")
        print(f"  - PASS : {pass_count} = 264 ✓")
    else:
        print("❌ ！")
        if len(records) != 264:
            print(f"  - : {len(records)} != 264")
        if pass_count != 264:
            print(f"  - PASS : {pass_count} != 264")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()










