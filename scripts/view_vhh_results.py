#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""VHH"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JSON_FILE = PROJECT_ROOT / "data" / "germlines" / "vicugna_pacos_ig_aa" / "vhh_numbered" / "vhh_numbered_and_split.json"

with open(JSON_FILE, encoding='utf-8') as f:
    data = json.load(f)

r = data['results'][0]
print('（VHH）:')
print(f'  ID: {r["id"][:60]}')
print(f'  : {r["length"]}aa')
print(f'  VHH: {r["vhh_score"]}')
print('  :')
for region, seq in r['regions'].items():
    if seq:
        display = seq[:40] + '...' if len(seq) > 40 else seq
        print(f'    {region}: {len(seq)}aa - {display}')
print('  Hallmark:')
for pos, aa in r['hallmarks'].items():
    print(f'    {pos}: {aa}')

print(f'\n: {data["success_count"]}VHH')


















