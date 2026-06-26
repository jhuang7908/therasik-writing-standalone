#!/usr/bin/env python3
"""
CDR3
IMGT CDR3FR4
"""

import json

with open("output/7d12_verified_run/checkpoint_01_numbering.json") as f:
    numbering = json.load(f)

print("="*80)
print("CDR3")
print("="*80)

# 
current_cdr3 = numbering["imgt_cdrs"]["CDR3-IMGT"]
print(f"\nCDR3-IMGT: {current_cdr3}")
print(f": {len(current_cdr3)} aa")

# IMGT
# CDR3IMGT 105（Cys104）IMGT 117（Trp118）
# ：105-117 (13)

print("\n" + "="*80)
print("IMGT CDR3")
print("="*80)

print("""
IMGT CDR3：
- ：IMGT 105 (Cys 104)
- ：IMGT 117 (Trp/Phe 118)
- ： (5-25 aa)

motif:
- FR3: Cys 104 (C)
- CDR3: 105-117 ()
- FR4: Trp 118 (W) - WGQG motif
""")

imgt = numbering["imgt_numbering"]

# CDR3
print("\nIMGT:")
print(f"IMGT 104: {imgt.get('104', 'N/A')} (Cys)")
print(f"IMGT 105-117:")
cdr3_correct = ""
for i in range(105, 118):
    pos = str(i)
    if pos in imgt:
        aa = imgt[pos]
        cdr3_correct += aa
        print(f"  {pos}: {aa}")

print(f"IMGT 118: {imgt.get('118', 'N/A')} (Trp - FR4)")
print(f"IMGT 119-128: {imgt.get('119','')}{imgt.get('120','')}{imgt.get('121','')}{imgt.get('122','')}{imgt.get('123','')}{imgt.get('124','')}{imgt.get('125','')}{imgt.get('126','')}{imgt.get('127','')}{imgt.get('128','')} (FR4)")

print("\n" + "="*80)
print("CDR3-IMGT")
print("="*80)
print(f": {cdr3_correct}")
print(f": {len(cdr3_correct)} aa")
print(f"IMGT: 105-117")

print("\n" + "="*80)
print("")
print("="*80)
print(f"\n❌ （）:")
print(f"   : {current_cdr3}")
print(f"   : {len(current_cdr3)} aa")
print(f"   : FR4 (WGQGTQVTVSS)")

print(f"\n✅ :")
print(f"   : {cdr3_correct}")
print(f"   : {len(cdr3_correct)} aa")
print(f"   FR4")

# FR4
fr4 = ""
for i in range(118, 129):
    pos = str(i)
    if pos in imgt:
        fr4 += imgt[pos]

print(f"\n📌 FR4 (IMGT 118-128):")
print(f"   : {fr4}")
print(f"   : {len(fr4)} aa")
print(f"   motif: W-G-Q-G")

print("\n" + "="*80)
print("index")
print("="*80)

seq = numbering["input_sequence"]
print(f" (117 aa):")
print(f"{seq}")

# CDR3
# IMGT 105？
# IMGT numbering
imgt_to_seqidx = {}
seq_idx = 0
for imgt_pos in sorted([int(p) for p in imgt.keys()]):
    imgt_to_seqidx[imgt_pos] = seq_idx
    seq_idx += 1

cdr3_start_idx = imgt_to_seqidx.get(105, -1)
cdr3_end_idx = imgt_to_seqidx.get(117, -1) + 1

if cdr3_start_idx >= 0 and cdr3_end_idx > 0:
    cdr3_from_seq = seq[cdr3_start_idx:cdr3_end_idx]
    print(f"\n CDR3 (index {cdr3_start_idx}:{cdr3_end_idx}):")
    print(f"   {cdr3_from_seq}")
    
    fr4_start_idx = imgt_to_seqidx.get(118, -1)
    if fr4_start_idx >= 0:
        fr4_from_seq = seq[fr4_start_idx:]
        print(f"\nFR4 (index {fr4_start_idx}:):")
        print(f"   {fr4_from_seq}")

print("\n" + "="*80)
print("")
print("="*80)
print("""
：CDR3FR4

：
- FR3: IMGT 66-104
- CDR3: IMGT 105-117 (AAGGVGWPYFDY, 12 aa)
- FR4: IMGT 118-128 (WGQGTQVTVSS, 11 aa)

：
1. checkpoint_01_numbering.json
2. CDR3
3. CDR grafting
""")















