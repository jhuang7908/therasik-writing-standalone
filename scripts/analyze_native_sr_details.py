import pandas as pd
import numpy as np
from pathlib import Path
import json
import re

# 1. Load Data
df = pd.read_csv('reports/slice3_vhh_observed_strategy_labels.csv')

# Re-apply Classification Logic
def get_class(row):
    if row['delta_human_minus_alpaca_fr23'] > 0:
        return 'BM'
    elif row['vh_identity_global'] > 0.85:
        return 'SR'
    else:
        return 'Native'

df['my_class'] = df.apply(get_class, axis=1)

# Load Human & Alpaca Libraries for Baseline
project_root = Path('.').resolve()
human_path = project_root / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean.jsonl"
alpaca_path = project_root / "data" / "germlines" / "vicugna_pacos_ig_aa" / "vhh_scaffolds" / "vhh_scaffolds.json"

def get_identity(s1, s2):
    if not s1 or not s2: return 0.0
    s1, s2 = s1.upper(), s2.upper()
    l = max(len(s1), len(s2))
    m = sum(1 for a,b in zip(s1, s2) if a==b)
    return m/l

human_seqs = []
if human_path.exists():
    with open(human_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                rec = json.loads(line)
                # Correct key is 'sequence_id'
                if '|Homo' in rec.get('sequence_id', ''):
                    seg = rec.get('segments', {})
                    seq = (seg.get('FR1','') + seg.get('FR2','') + seg.get('FR3','')).strip()
                    if seq: human_seqs.append(seq)
            except: pass

alpaca_seqs = []
if alpaca_path.exists():
    alpaca_data = json.loads(alpaca_path.read_text(encoding='utf-8'))
    for s in alpaca_data:
        c = s.get('consensus', {})
        seq = (c.get('fr1','') + c.get('fr2','') + c.get('fr3','')).strip()
        if seq: alpaca_seqs.append(seq)

# ---------------------------------------------------------
# Q1: Baseline
# ---------------------------------------------------------
print("\n=== Q1: Baseline (Pure Alpaca vs Human) ===")
if human_seqs and alpaca_seqs:
    best_alpaca_to_human_ids = []
    for a_seq in alpaca_seqs:
        best_id = 0.0
        for h_seq in human_seqs:
            score = get_identity(a_seq, h_seq)
            if score > best_id: best_id = score
        best_alpaca_to_human_ids.append(best_id)

    print(f"Comparison of {len(alpaca_seqs)} Alpaca Scaffolds against {len(human_seqs)} Human VH Templates:")
    print(f"  - Max Similarity (The 'most human-like' pure Alpaca): {max(best_alpaca_to_human_ids):.1%}")
    print(f"  - Mean Similarity: {np.mean(best_alpaca_to_human_ids):.1%}")
    print(f"  - Min Similarity: {min(best_alpaca_to_human_ids):.1%}")
else:
    print("Baseline calculation skipped (data missing).")

# ---------------------------------------------------------
# Q2: Native
# ---------------------------------------------------------
print("\n=== Q2: Native VHH Analysis (N=4) ===")
natives = df[df['my_class']=='Native']
if not natives.empty:
    print(natives[['antibody_id', 'vh_identity_global', 'best_alpaca_fr123_identity']].to_string(index=False))
    print(f"Average Native Global Identity to Human: {natives['vh_identity_global'].mean():.1%}")
    print(f"Average Native Identity to Alpaca Scaffold: {natives['best_alpaca_fr123_identity'].mean():.1%}")
else:
    print("No Native VHHs found.")

# ---------------------------------------------------------
# Q3: SR Breakdown (Hallmark Check)
# ---------------------------------------------------------
print("\n=== Q3: SR Strategy Breakdown (N=7) ===")
srs = df[df['my_class']=='SR'].copy()

def check_vhh_hallmarks(row):
    # Heuristic check for VHH Hallmarks in query sequences
    # Pos 37 (FR1 end): F or Y (Human is V)
    # Pos 44 (FR2): E or Q (Human is G)
    # Pos 45 (FR2): R (Human is L)
    # Pos 47 (FR2): F, G, L, W (Human is W, but VHH often F/G/L)
    
    fr1 = row['fr1_query']
    fr2 = row['fr2_query']
    
    traits = []
    
    # Check 37 (last few residues of FR1)
    if fr1:
        # Typical FR1 ends ...SCKAS (26). Wait, ANARCII numbering is structural.
        # Let's assume the provided fr1/fr2 are correctly segmented.
        # Pos 37 is usually near the end of FR1 or start of FR2 depending on def,
        # but in IMGT, FR1 ends at 26, CDR1 27-38. So 37 is in CDR1?
        # WAIT. IMGT Hallmark 37 is in CDR1? No.
        # IMGT Definition: FR1 (1-26), CDR1 (27-38), FR2 (39-55).
        # Ah, "Hallmark 37" usually refers to Kabat 37 which is IMGT 42?
        # NO. VHH Hallmarks are IMGT 42, 49, 50, 52 (which are FR2).
        # Let's use the standard VHH Hallmark list: 
        # IMGT 42 (Kabat 37): VHH = F/Y, Human = V
        # IMGT 49 (Kabat 44): VHH = E/Q, Human = G
        # IMGT 50 (Kabat 45): VHH = R/C, Human = L
        # IMGT 52 (Kabat 47): VHH = F/G/L, Human = W
        
        # We need to look into FR2 (IMGT 39-55).
        # Let's try to map residues in FR2 string.
        # FR2 typically length 17 (39-55).
        # 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55
        # 0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16
        
        # So:
        # IMGT 42 is index 3
        # IMGT 49 is index 10
        # IMGT 50 is index 11
        # IMGT 52 is index 13
        
        if len(fr2) >= 14:
            h42 = fr2[3]  # Kabat 37
            h49 = fr2[10] # Kabat 44
            h50 = fr2[11] # Kabat 45
            h52 = fr2[13] # Kabat 47
            
            h_count = 0
            details = []
            
            # 42 (K37): VHH=F/Y (Hu=V)
            if h42 in ['F', 'Y']: 
                h_count += 1
                details.append(f"Y42")
            
            # 49 (K44): VHH=E/Q (Hu=G)
            if h49 in ['E', 'Q']:
                h_count += 1
                details.append(f"E44")
            
            # 50 (K45): VHH=R (Hu=L)
            if h50 in ['R']:
                h_count += 1
                details.append(f"R45")
                
            # 52 (K47): VHH=F/L/G (Hu=W) -- W is human
            if h52 in ['F', 'L', 'G'] and h52 != 'W':
                h_count += 1
                details.append(f"{h52}47")
                
            return h_count, "+".join(details)
            
    return 0, ""

srs[['hallmark_count', 'hallmark_details']] = srs.apply(lambda r: pd.Series(check_vhh_hallmarks(r)), axis=1)

# Metric: FR2 Origin
# If Delta FR2 < -0.05, it's Alpaca.
srs['fr2_status'] = srs.apply(lambda r: 'Alpaca' if (r['best_human_fr2_identity'] - r['best_alpaca_fr2_identity']) < -0.02 else 'Human/Mixed', axis=1)

cols = ['antibody_id', 'vh_identity_global', 'fr2_status', 'hallmark_count', 'hallmark_details']
print(srs[cols].sort_values('vh_identity_global', ascending=False).to_string(index=False))

print("\n--- Strategy Interpretation ---")
for _, row in srs.iterrows():
    strategies = []
    
    # 1. FR2 Status
    if row['fr2_status'] == 'Alpaca':
        strategies.append("FR2-Alpaca")
    
    # 2. Hallmark Retention
    if row['hallmark_count'] >= 2:
        strategies.append("Hallmark-Retention")
    elif row['hallmark_count'] == 1:
        strategies.append("Partial-Hallmarks")
        
    # 3. Surface Resurfacing inference
    # If it's SR class (high identity) but NOT FR2-Alpaca and NO Hallmarks, it implies
    # the framework is very human-like (possibly human FR2), so it must be Resurfacing of a humanized scaffold
    # OR it's a VHH that naturally looks human.
    if not strategies:
        strategies.append("Surface-Resurfacing-Only")
        
    print(f"{row['antibody_id']}: {', '.join(strategies)} ({row['hallmark_details']})")
