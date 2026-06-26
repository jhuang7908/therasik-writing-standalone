#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""ANARCII"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Human VH3
vh_file = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_numbered" / "human_vh_numbered_and_split.json"
print("=" * 80)
print("ANARCII")
print("=" * 80)

if vh_file.exists():
    with open(vh_file, encoding='utf-8') as f:
        data = json.load(f)
    print(f"\n[1] Human VH3:")
    print(f"  : {data['total_vh3']}")
    print(f"  : {data['success_count']}")
    print(f"  : {data['failed_count']}")
    print(f"  : {data['success_count']/data['total_vh3']*100:.1f}%")
else:
    print(f"\n[1] Human VH3: {vh_file}")

# VHH-SAFE
templates_file = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds" / "human_vh3_vhh_safe_templates.json"
print(f"\n[2] VHH-SAFE:")
if templates_file.exists():
    with open(templates_file, encoding='utf-8') as f:
        templates = json.load(f)
    print(f"  : {len(templates)}")
    print(f"  : 30 scaffolds × 3  = 90")
    
    # 
    incomplete = [t for t in templates if not t.get('consensus', {}).get('framework_full')]
    print(f"  : {len(incomplete)}")
    
    if incomplete:
        print(f"  :")
        for t in incomplete[:3]:
            print(f"    - {t['template_id']}")
    
    # 
    templates_with_mutations = [t for t in templates if t.get('mutations')]
    print(f"  : {len(templates_with_mutations)}")
    
    if templates_with_mutations:
        avg_mutations = sum(len(t.get('mutations', {})) for t in templates_with_mutations) / len(templates_with_mutations)
        print(f"  : {avg_mutations:.1f}")
else:
    print(f"  : {templates_file}")

# VHH
alpaca_file = PROJECT_ROOT / "data" / "germlines" / "vicugna_pacos_ig_aa" / "vhh_numbered" / "vhh_numbered_and_split.json"
print(f"\n[3] VHH:")
if alpaca_file.exists():
    with open(alpaca_file, encoding='utf-8') as f:
        alpaca_data = json.load(f)
    print(f"  VHH: {alpaca_data['total_vhh']}")
    print(f"  : {alpaca_data['success_count']}")
    print(f"  : {alpaca_data['failed_count']}")
    print(f"  : {alpaca_data['success_count']/alpaca_data['total_vhh']*100:.1f}%")
else:
    print(f"  VHH: {alpaca_file}")

print("\n" + "=" * 80)
print("")
print("=" * 80)


















