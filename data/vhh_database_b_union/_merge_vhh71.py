import csv
import json
from pathlib import Path
import os
import sys

root = Path(r'd:/InSynBio-AI-Research/Antibody_Engineer_Suite')
vhh42_path = root / 'data/vhh_clinical_39_union/vhh_39_cdr_fr_segments.csv'
vhh29_path = root / 'data/vhh_database_b_union/vhh29_cdr_segments.csv'
out_path = root / 'data/vhh_database_b_union/vhh71_merged_cdr_segments.csv'

merged = []

# VHH42
with open(vhh42_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sid = row.get('Name', '').strip()
        if not sid: continue
        merged.append({
            'safe_id': f"{sid}_clinical",
            'CDR1': row.get('CDR1', ''),
            'CDR2': row.get('CDR2', ''),
            'CDR3': row.get('CDR3', '')
        })

# VHH29
with open(vhh29_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sid = row.get('safe_id', '').strip()
        if not sid: continue
        merged.append({
            'safe_id': f"{sid}_db_b",
            'CDR1': row.get('CDR1', ''),
            'CDR2': row.get('CDR2', ''),
            'CDR3': row.get('CDR3', '')
        })

print(f"Total merged sequences: {len(merged)}")
with open(out_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['safe_id', 'CDR1', 'CDR2', 'CDR3'])
    writer.writeheader()
    writer.writerows(merged)
print(f"Written to {out_path}")
