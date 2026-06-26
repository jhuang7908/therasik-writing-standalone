"""Get Kabat numbering for VGRW-SR-R2 VHH and extract CDR boundaries."""
import sys
import json

from anarcii import Anarcii

seq = 'QVQLVQSGAEVVKPGSSVKLSCKASGFNIKDTYIHWVKQRPEQGREWIGRIYPTNGYTRYDPKFQDRATITADTSTSTAYLEVSRLRSEDTAVYYCSRWGGDGFYAMDYWGQGASVTVSS'

a = Anarcii()
result = a.number(seq)

entry = result['Sequence']
numbering = entry['numbering']

cdr_h1_range = range(26, 36)   # Kabat H26-H35
cdr_h2_range = range(50, 66)   # Kabat H50-H65
cdr_h3_range = range(95, 103)  # Kabat H95-H102

seq_idx = 0
kabat_map = []
for (num, ins), aa in numbering:
    if aa == '-':
        continue
    kabat_label = f"{num}{ins.strip()}" if ins.strip() else str(num)
    
    region = 'FR'
    if num in cdr_h1_range:
        region = 'CDR1'
    elif num in cdr_h2_range:
        region = 'CDR2'
    elif num in cdr_h3_range:
        region = 'CDR3'
    
    kabat_map.append({
        'seq_idx': seq_idx,
        'kabat': kabat_label,
        'aa': aa,
        'region': region
    })
    seq_idx += 1

sys.stderr.write("=== Full Kabat Numbering ===\n")
sys.stderr.write(f"{'SeqIdx':>6} {'Kabat':>6} {'AA':>3} {'Region':>6}\n")
for row in kabat_map:
    sys.stderr.write(f"{row['seq_idx']:>6} {row['kabat']:>6} {row['aa']:>3} {row['region']:>6}\n")

sys.stderr.write("\n=== CDR Summary ===\n")
for cdr_name in ['CDR1', 'CDR2', 'CDR3']:
    positions = [r for r in kabat_map if r['region'] == cdr_name]
    if positions:
        seq_start = positions[0]['seq_idx']
        seq_end = positions[-1]['seq_idx']
        kabat_start = positions[0]['kabat']
        kabat_end = positions[-1]['kabat']
        cdr_seq = ''.join(r['aa'] for r in positions)
        sys.stderr.write(f"{cdr_name}: Kabat {kabat_start}-{kabat_end}, SeqIdx {seq_start}-{seq_end}, {len(positions)}aa: {cdr_seq}\n")

json.dump(kabat_map, sys.stdout, indent=2)
