#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
： Canonical Proxy Layer

 canonical_proxy 。
"""

from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.canonical.canonical_proxy_layer import annotate_sequence_with_canonical_proxy
from core.germline_assets_loader import load_canonical_proxy_lookup

#  lookup table（ v1_clean ）
lookup_table = load_canonical_proxy_lookup()
with open(lookup_path, "r", encoding="utf-8") as f:
    lookup_table = json.load(f)

# ： canonical_proxy
example_seq_id = "M99641|IGHV1-18*01|Homo"
cdr1_seq = "GYTFTSYG"
cdr2_seq = "ISAYNGNT"

canonical_proxy = annotate_sequence_with_canonical_proxy(
    example_seq_id,
    cdr1_seq,
    cdr2_seq,
    lookup_table,
)

print("=" * 80)
print("Canonical Proxy Layer ")
print("=" * 80)
print()
print(f" ID: {example_seq_id}")
print(f"CDR1: {cdr1_seq}")
print(f"CDR2: {cdr2_seq}")
print()
print("Canonical Proxy :")
print(json.dumps(canonical_proxy, indent=2, ensure_ascii=False))
print()
print("=" * 80)

