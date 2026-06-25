"""
Corrected Micro-Level Analysis: Hallmark & Vernier Zone Comparison.

Methodology:
1. Use Motif-Based Alignment to locate key positions (instead of fixed indices).
   - FR2 Start Anchor: Pos 36 (Trp/Phe) -> Hallmarks at +1, +8, +9, +11.
   - FR3 Start Anchor: Pos 66 (Arg/Lys) in 'RFT'/'KGR' motif -> Vernier at +5 (Pos 71).
2. Divide VHHs into Short (<=10) and Long (>10) CDR3 groups.
3. Analyze AA distribution at these corrected positions.

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/raw data/TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv

Outputs:
  - paper/raw data/MicroAnalysis/TheraSAbDab_19VHH_Hallmark_Vernier_Analysis_Corrected.txt
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_METADATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"
OUT_REPORT = PROJECT_ROOT / "paper" / "raw data" / "MicroAnalysis" / "TheraSAbDab_19VHH_Hallmark_Vernier_Analysis_Corrected.txt"

if not OUT_REPORT.parent.exists():
    OUT_REPORT.parent.mkdir(parents=True)

def load_data():
    df_seq = pd.read_csv(IN_FR_SEQ)
    df_meta = pd.read_csv(IN_METADATA)
    # Merge H3 Length
    df_merged = df_seq.merge(df_meta[["antibody_id", "h3_length"]], on="antibody_id")
    df_merged = df_merged.rename(columns={"h3_length": "H3_Len"})
    return df_merged

def find_fr2_hallmarks(seq):
    """
    Locate FR2 Hallmarks (37, 44, 45, 47) using Pos 36 (W/F) as anchor.
    FR2 typically starts with W or F.
    """
    # Heuristic: FR2 is ~17aa. Starts with W/F.
    # Check first residue
    anchor = -1
    if seq[0] in ['W', 'F', 'Y', 'L', 'V', 'M', 'I', 'A']: # Allow some variability, but usually W/F
        anchor = 0
    
    if anchor == -1:
        return {37:'-', 44:'-', 45:'-', 47:'-'}
        
    # Pos 36 is index 0.
    # Pos 37 = index 1
    # Pos 44 = index 8
    # Pos 45 = index 9
    # Pos 47 = index 11
    
    try:
        return {
            37: seq[anchor + 1],
            44: seq[anchor + 8],
            45: seq[anchor + 9],
            47: seq[anchor + 11]
        }
    except IndexError:
        return {37:'-', 44:'-', 45:'-', 47:'-'}

def find_fr3_vernier(seq):
    """
    Locate FR3 Vernier (Pos 71) using Pos 66 (R/K) as anchor.
    Look for motifs: RFT, KGR, RFA, KFT...
    """
    # Common motifs for FR3 start (Pos 66-68)
    motifs = ["RFT", "KGR", "RFA", "KFT", "QFT", "RLT", "RVS"]
    
    anchor = -1
    for motif in motifs:
        idx = seq.find(motif)
        if idx != -1:
            anchor = idx
            break
            
    # Fallback: Look for just R or K followed by hydrophobic
    if anchor == -1:
        # Try finding first R or K in the first 10 residues
        for i, aa in enumerate(seq[:10]):
            if aa in ['R', 'K']:
                anchor = i
                break
                
    if anchor == -1:
        return {71: '-'}
        
    # Pos 66 is anchor.
    # Pos 71 is anchor + 5.
    try:
        return {71: seq[anchor + 5]}
    except IndexError:
        return {71: '-'}

def analyze_group(df, group_name):
    hallmark_data = []
    vernier_data = []
    
    for _, row in df.iterrows():
        # FR2
        h_res = find_fr2_hallmarks(row["fr2_sequence"])
        hallmark_data.append(h_res)
        
        # FR3
        v_res = find_fr3_vernier(row["fr3_sequence"])
        vernier_data.append(v_res)
        
    # Calculate Frequencies
    lines = []
    lines.append(f"Group: {group_name} (N={len(df)})")
    
    # Hallmarks
    for pos in [37, 44, 45, 47]:
        res_list = [d[pos] for d in hallmark_data]
        counts = pd.Series(res_list).value_counts()
        top_str = ", ".join([f"{aa}:{cnt}" for aa, cnt in counts.items()])
        lines.append(f"  Pos {pos} (Hallmark): {top_str}")
        
    # Vernier
    for pos in [71]:
        res_list = [d[pos] for d in vernier_data]
        counts = pd.Series(res_list).value_counts()
        top_str = ", ".join([f"{aa}:{cnt}" for aa, cnt in counts.items()])
        lines.append(f"  Pos {pos} (Vernier):  {top_str}")
        
    lines.append("")
    return lines

def main():
    df = load_data()
    
    short_group = df[df["H3_Len"] <= 10]
    long_group = df[df["H3_Len"] > 10]
    
    report = []
    report.append("="*80)
    report.append("CORRECTED MICRO-LEVEL ANALYSIS: HALLMARK & VERNIER RESIDUES")
    report.append("Method: Motif-based alignment to correct for CDR2-tail inclusion.")
    report.append("="*80)
    report.append("")
    
    report.extend(analyze_group(short_group, "Short CDR3 (<=10aa)"))
    report.extend(analyze_group(long_group, "Long CDR3 (>10aa)"))
    
    report.append("-" * 80)
    report.append("INTERPRETATION GUIDE:")
    report.append("Pos 37: Human=V, Camelid=F/Y")
    report.append("Pos 44: Human=G, Camelid=E")
    report.append("Pos 45: Human=L, Camelid=R")
    report.append("Pos 47: Human=W, Camelid=F/G/L")
    report.append("Pos 71: Key Vernier Zone (Structural Support)")
    report.append("-" * 80)
    
    OUT_REPORT.write_text("\n".join(report), encoding="utf-8")
    print(f"Analysis complete: {OUT_REPORT}")

if __name__ == "__main__":
    main()
