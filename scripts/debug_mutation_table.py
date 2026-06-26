import pandas as pd
import numpy as np
from pathlib import Path
import json
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed

# Setup
PROJECT_ROOT = Path('.').resolve()
MASTER_CSV = PROJECT_ROOT / "reports" / "slice3_vhh_observed_strategy_labels.csv"
TRUE_MASTER = PROJECT_ROOT / "data" / "slice3_vhh_paper_grade_master_table_plus_cdr3_features.csv"
HUMAN_LIB = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean.jsonl"

# Load Data
df = pd.read_csv(MASTER_CSV)
df_seq = pd.read_csv(TRUE_MASTER)
df = pd.merge(df, df_seq[['antibody_id', 'vh_fr1_fr3']], on='antibody_id', how='left')

# Load Human Lib
human_germlines = {}
with open(HUMAN_LIB, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            rec = json.loads(line)
            # Key: IGHV3-23*01
            full_id = rec.get('sequence_id', '')
            short_id = full_id.split('|')[1] if '|' in full_id else full_id
            human_germlines[short_id] = rec.get('imgt_map', {})
        except: pass

# Debug function for Caplacizumab
target_id = "Caplacizumab"
row = df[df['antibody_id'] == target_id].iloc[0]
seq = row['vh_fr1_fr3']
h_id_full = row['best_human_template_id']
h_id = h_id_full.split('|')[1] if '|' in h_id_full else h_id_full

print(f"--- DEBUG: {target_id} ---")
print(f"Seq Length: {len(seq)}")
print(f"Human Template: {h_id}")

# Run Numbering
numbered = imgt_number_anarcii_indexed(seq)
print(f"Numbered Rows: {len(numbered['rows'])}")

# Check Hallmark Pos 45
# IMGT 45 is Hallmark. VHH should be R, Human (IGHV3-7*01) should be L.
q_map = {int(r['pos']): r['aa'] for r in numbered['rows'] if str(r['pos']).isdigit()}
h_map = human_germlines.get(h_id, {})

pos = 45
q_aa = q_map.get(pos, '-')
h_aa = h_map.get(str(pos), '?')

print(f"Pos {pos}: Query='{q_aa}' vs Human='{h_aa}'")

if q_aa != h_aa:
    print("MISMATCH DETECTED (Correct behavior)")
else:
    print("NO MISMATCH (Bug exists)")
