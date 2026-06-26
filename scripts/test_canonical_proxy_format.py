#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Canonical Proxy 
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.report_blocks.canonical_proxy_background_customer import render_canonical_proxy_background_customer_block

# 1: 
print("=" * 80)
print("1: ")
print("=" * 80)
mock_data = {
    'canonical_proxy_cdr1': {
        'length': 8,
        'cluster_id': 'cdr1_L8_C9',
        'proxy_score': 1.0000
    },
    'canonical_proxy_cdr2': {
        'length': 8,
        'cluster_id': 'cdr2_L8_C22',
        'proxy_score': 1.0000
    }
}
result1 = render_canonical_proxy_background_customer_block(mock_data)
print(":")
print(result1)
print()
print(":")
print(f"  -  \\n\\n: {result1.startswith(chr(10) + chr(10))}")
print(f"  -  \\n : {result1.endswith(chr(10))}")
print(f"  - : {'\\n\\n| CDR |' in result1}")
print(f"  - : {result1.rstrip().endswith('|') and result1.endswith(chr(10))}")
print()

# 2: 
print("=" * 80)
print("2: ")
print("=" * 80)
result2 = render_canonical_proxy_background_customer_block(None)
print(":")
print(result2)
print()
print(":")
print(f"  -  \\n\\n: {result2.startswith(chr(10) + chr(10))}")
print(f"  -  \\n : {result2.endswith(chr(10))}")
print(f"  - : {'\\n\\n| CDR |' in result2}")
print(f"  - : {result2.rstrip().endswith('|') and result2.endswith(chr(10))}")
print()

print("=" * 80)
print("✅ ")
print("=" * 80)

