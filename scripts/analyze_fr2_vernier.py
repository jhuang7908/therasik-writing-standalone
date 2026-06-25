"""
Check for Vernier Zone residues in FR2.
Foote & Winter (1992) defined Vernier Zone residues as FR residues underlying CDRs.
For Heavy Chain, these are typically:
FR1: 2, 27, 28, 29, 30
FR2: 47, 48, 49 (Kabat) -> IMGT 53, 54, 55?
FR3: 67, 69, 71, 73, 78, 93, 94

Goal:
1. Map Kabat 47, 48, 49 to IMGT.
   - Kabat 47 (Trp/Phe) -> IMGT 47? No, IMGT 47 is usually Trp.
   - Kabat 48 (Val) -> IMGT 48?
   - Kabat 49 (Ala/Ser) -> IMGT 49?
   Let's check the sequence alignment in our data.
   Our FR2 ends with ...W-V-S/A (Pos 47, 48, 49 in our extraction).
   If these are indeed Vernier residues, we should check their conservation.

2. Analyze Pos 48 and 49 in our dataset (Short vs Long).
   - Pos 47 has already been analyzed as a Hallmark (and it is also a Vernier!).
   - Pos 48 (Val/Ile) -> Structural support for CDR2?
   - Pos 49 (Ser/Ala/Gly) -> Structural support for CDR2?

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/raw data/TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv

Outputs:
  - paper/raw data/MicroAnalysis/TheraSAbDab_19VHH_FR2_Vernier_Analysis.txt
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_METADATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"
OUT_REPORT = PROJECT_ROOT / "paper" / "raw data" / "MicroAnalysis" / "TheraSAbDab_19VHH_FR2_Vernier_Analysis.txt"

def load_data():
    df_seq = pd.read_csv(IN_FR_SEQ)
    df_meta = pd.read_csv(IN_METADATA)
    df_merged = df_seq.merge(df_meta[["antibody_id", "h3_length"]], on="antibody_id")
    df_merged = df_merged.rename(columns={"h3_length": "H3_Len"})
    return df_merged

def analyze_fr2_vernier(df):
    lines = []
    lines.append("="*80)
    lines.append("FR2 VERNIER ZONE ANALYSIS (Pos 48, 49)")
    lines.append("Note: Pos 47 is both a Hallmark and a Vernier residue (analyzed previously).")
    lines.append("="*80)
    
    short_group = df[df["H3_Len"] <= 11]
    long_group = df[df["H3_Len"] > 11]
    
    # Extract Pos 48 and 49 (Last 2 residues of FR2)
    # FR2 sequences in our file are 17aa.
    # Pos 48 is index 15 (2nd to last)
    # Pos 49 is index 16 (last)
    
    for pos_name, idx in [("Pos 48", 15), ("Pos 49", 16)]:
        lines.append(f"## {pos_name} Analysis")
        
        res_s = [s[idx] for s in short_group["fr2_sequence"]]
        cnt_s = pd.Series(res_s).value_counts()
        
        res_l = [s[idx] for s in long_group["fr2_sequence"]]
        cnt_l = pd.Series(res_l).value_counts()
        
        lines.append(f"  Short (N={len(short_group)}): {cnt_s.to_dict()}")
        lines.append(f"  Long  (N={len(long_group)}): {cnt_l.to_dict()}")
        
        # Check Human vs Alpaca Reference
        # Human IGHV3-23: Pos 48=V, Pos 49=S
        # Alpaca IGHV3-3: Pos 48=A, Pos 49=A
        lines.append(f"  -> Ref: Human(V, S) / Alpaca(A, A)")
        lines.append("")
        
    return lines

def main():
    df = load_data()
    report = analyze_fr2_vernier(df)
    OUT_REPORT.write_text("\n".join(report), encoding="utf-8")
    print(f"Analysis complete: {OUT_REPORT}")

if __name__ == "__main__":
    main()
