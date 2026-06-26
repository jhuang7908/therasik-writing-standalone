#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""VHH-SAFE"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map, IMGTNumberingError

scaffolds_file = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds" / "human_vh3_scaffolds.json"
templates_file = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds" / "human_vh3_vhh_safe_templates.json"

print("=" * 80)
print("VHH-SAFE")
print("=" * 80)

# scaffolds
with open(scaffolds_file, encoding='utf-8') as f:
    scaffolds = json.load(f)

print(f"\nscaffold: {len(scaffolds)}")

# scaffoldANARCII
print(f"\nscaffold:")
print("-" * 80)

failed_scaffolds = []
for scaffold in scaffolds:
    scaffold_id = scaffold["scaffold_id"]
    framework = scaffold["consensus"]["framework_full"]
    
    try:
        rows = imgt_number_anarcii(framework)
        pos_map = build_pos_to_aa_map(rows)
        
        # 
        key_positions = [37, 44, 45, 47]
        missing_positions = [pos for pos in key_positions if pos not in pos_map]
        
        if missing_positions:
            print(f"  {scaffold_id}: ， {missing_positions}")
        else:
            print(f"  {scaffold_id}: ✓ ，")
            
    except IMGTNumberingError as e:
        print(f"  {scaffold_id}: ✗  - {e}")
        failed_scaffolds.append((scaffold_id, str(e)))
    except Exception as e:
        print(f"  {scaffold_id}: ✗  - {e}")
        failed_scaffolds.append((scaffold_id, str(e)))

if failed_scaffolds:
    print(f"\nscaffold ({len(failed_scaffolds)}):")
    for sid, error in failed_scaffolds:
        print(f"  - {sid}: {error}")
else:
    print(f"\n✓ scaffold！")

# 
print(f"\n:")
print("-" * 80)
with open(templates_file, encoding='utf-8') as f:
    templates = json.load(f)

print(f": {len(templates)}")
print(f": {len(scaffolds)} × 3 = {len(scaffolds) * 3}")

# scaffold
templates_by_scaffold = {}
for t in templates:
    sid = t['source_scaffold']
    if sid not in templates_by_scaffold:
        templates_by_scaffold[sid] = []
    templates_by_scaffold[sid].append(t)

print(f"\nscaffold:")
for sid in sorted(templates_by_scaffold.keys()):
    count = len(templates_by_scaffold[sid])
    expected = 3
    status = "✓" if count == expected else "✗"
    print(f"  {status} {sid}: {count} ({expected})")

print("\n" + "=" * 80)
print("")
print("=" * 80)


















