#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Canonical Proxy 
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.report_blocks.canonical_proxy_background_customer import (
    render_canonical_proxy_background_customer_block,
    get_canonical_proxy_data_for_client_report,
)


def main():
    print("=" * 80)
    print(" Canonical Proxy ")
    print("=" * 80)
    print()
    
    # 1: 
    print("[ 1]  canonical proxy （ N/A）")
    print("-" * 80)
    block1 = render_canonical_proxy_background_customer_block(None)
    print(block1)
    print()
    
    # 2: （）
    print("[ 2]  canonical proxy （）")
    print("-" * 80)
    mock_data = {
        "canonical_proxy_cdr1": {
            "length": 8,
            "cluster_id": "cdr1_L8_C9",
            "proxy_score": 1.0000,
        },
        "canonical_proxy_cdr2": {
            "length": 8,
            "cluster_id": "cdr2_L8_C22",
            "proxy_score": 1.0000,
        },
    }
    block2 = render_canonical_proxy_background_customer_block(mock_data)
    print(block2)
    print()
    
    # 3:  result.json 
    print("[ 3]  result_stage12.json ")
    print("-" * 80)
    result_path = PROJECT_ROOT / "output" / "result_stage12.json"
    if result_path.exists():
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        
        canonical_proxy_data = get_canonical_proxy_data_for_client_report(result)
        if canonical_proxy_data:
            print(f"  ✅  canonical proxy ")
            print(f"  - CDR1: {canonical_proxy_data.get('canonical_proxy_cdr1', {}).get('proxy_score', 'N/A')}")
            print(f"  - CDR2: {canonical_proxy_data.get('canonical_proxy_cdr2', {}).get('proxy_score', 'N/A')}")
            block3 = render_canonical_proxy_background_customer_block(canonical_proxy_data)
            print()
            print(block3)
        else:
            print("  ⚠️   canonical proxy ")
    else:
        print(f"  ⚠️  : {result_path}")
    
    print()
    print("=" * 80)
    print("✅ ")
    print("=" * 80)


if __name__ == "__main__":
    main()













