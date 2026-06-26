#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 manifest.json
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
manifest_path = PROJECT_ROOT / "data" / "germlines" / "v1_clean" / "manifest.json"

print("=" * 80)
print(" manifest.json")
print("=" * 80)
print()

with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)

print("✅ manifest.json ")
print()
print(":")
print(f"  : {manifest['asset_type']}")
print(f"  : {manifest['version']}")
print(f"  : {manifest['description']}")
print()
print(":")
for key, value in manifest['includes'].items():
    if isinstance(value, list):
        print(f"  {key}: {', '.join(value)}")
    else:
        print(f"  {key}: {value}")
print()
print("Canonical Proxy :")
print(f"  : {manifest['canonical_proxy_definition']['proxy_score']}")
print(f"  : {', '.join(manifest['canonical_proxy_definition']['scope'])}")
print(f"  : {manifest['canonical_proxy_definition']['note']}")
print()
print(":")
for key, value in manifest['statistics'].items():
    print(f"  {key}: {value}")
print()
print(":")
print(f"  : {manifest['generated_by']['pipeline']}")
print(f"  : {manifest['generated_by']['date']}")
print()
print("=" * 80)
print("✅ manifest.json ！")
print("=" * 80)













