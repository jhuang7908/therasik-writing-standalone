#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""VHH scaffold"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JSON_FILE = PROJECT_ROOT / "data" / "germlines" / "vicugna_pacos_ig_aa" / "vhh_scaffolds" / "vhh_scaffolds.json"

with open(JSON_FILE, encoding='utf-8') as f:
    data = json.load(f)

print('=' * 80)
print('VHH Scaffold')
print('=' * 80)
print(f'\nscaffold: {len(data)}')
print()

# Cluster
sizes = [s['n_members'] for s in data]
print('Cluster:')
print(f'  : {min(sizes)}')
print(f'  : {max(sizes)}')
print(f'  : {sum(sizes)/len(sizes):.1f}')
print()

# 5scaffold
print('5scaffold:')
for i, s in enumerate(data[:5], 1):
    print(f'  {s["scaffold_id"]}: {s["n_members"]}')
    full = s["consensus"]["framework_full"]
    print(f'    : {len(full)}aa')
    print(f'    : {full[:60]}...')
    print()

print('=' * 80)


















