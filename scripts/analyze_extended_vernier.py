"""
Extended Vernier Zone Analysis: FR1 (CDR1-Support) and FR3-Tail (CDR3-Support).

Goal:
Check if Vernier residues adjacent to CDRs correlate with CDR3 length groups (Short <=11 vs Long >11).

Regions:
1. FR1 Tail (Pos 27-30): Supports CDR1.
2. FR3 Tail (Pos 93-94): Supports CDR3. (Critical check!)

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/raw data/TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv

Outputs:
  - paper/raw data/MicroAnalysis/TheraSAbDab_19VHH_Extended_Vernier_Analysis.txt
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_METADATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"
OUT_REPORT = PROJECT_ROOT / "paper" / "raw data" / "MicroAnalysis" / "TheraSAbDab_19VHH_Extended_Vernier_Analysis.txt"

def load_data():
    df_seq = pd.read_csv(IN_FR_SEQ)
    df_meta = pd.read_csv(IN_METADATA)
    df_merged = df_seq.merge(df_meta[["antibody_id", "h3_length"]], on="antibody_id")
    df_merged = df_merged.rename(columns={"h3_length": "H3_Len"})
    return df_merged

def analyze_positions(df, region_col, positions_name, indices_from_end):
    """
    Extract residues from the end of a sequence.
    indices_from_end: list of negative integers (e.g. [-1] for last residue)
    """
    data = {}
    for offset in indices_from_end:
        # Convert offset to approx IMGT pos name for display
        pos_name = f"{positions_name}_{abs(offset)}" 
        
        residues = []
        for seq in df[region_col]:
            try:
                residues.append(seq[offset])
            except:
                residues.append("-")
        
        counts = pd.Series(residues).value_counts()
        data[pos_name] = counts
    return data

def format_counts(counts, n):
    return ", ".join([f"{aa}:{cnt}" for aa, cnt in counts.items()])

def main():
    df = load_data()
    
    # Split Groups (Threshold 11)
    short_group = df[df["H3_Len"] <= 11]
    long_group = df[df["H3_Len"] > 11]
    
    lines = []
    lines.append("="*80)
    lines.append("EXTENDED VERNIER ZONE ANALYSIS")
    lines.append("Comparing Short (<=11, N=5) vs Long (>11, N=14) CDR3 Groups")
    lines.append("="*80)
    lines.append("")
    
    # 1. FR1 Vernier (Pos 27-30) - Supports CDR1
    # FR1 is usually 25aa. Pos 27-30 are the last few residues.
    # IMGT 27, 28, 29, 30 usually correspond to seq[-4], seq[-3], seq[-2], seq[-1] of FR1
    lines.append("## 1. FR1 Vernier (Pos 27-30) - CDR1 Support")
    lines.append("Hypothesis: Should be conserved (independent of CDR3).")
    lines.append("-" * 60)
    
    fr1_indices = [-4, -3, -2, -1] # Pos 27, 28, 29, 30
    fr1_names = ["Pos 27", "Pos 28", "Pos 29", "Pos 30"]
    
    for idx, name in zip(fr1_indices, fr1_names):
        # Short
        res_s = [s[idx] for s in short_group["fr1_sequence"]]
        cnt_s = pd.Series(res_s).value_counts()
        
        # Long
        res_l = [s[idx] for s in long_group["fr1_sequence"]]
        cnt_l = pd.Series(res_l).value_counts()
        
        lines.append(f"{name}:")
        lines.append(f"  Short: {format_counts(cnt_s, len(short_group))}")
        lines.append(f"  Long:  {format_counts(cnt_l, len(long_group))}")
        lines.append("")

    # 2. FR3 Vernier (Pos 93-94) - Supports CDR3
    # FR3 ends right before CDR3.
    # Pos 94 is the last residue (seq[-1]). Pos 93 is seq[-2].
    lines.append("## 2. FR3 Vernier (Pos 93-94) - CDR3 Support")
    lines.append("Hypothesis: Might vary with CDR3 length?")
    lines.append("-" * 60)
    
    fr3_indices = [-2, -1] # Pos 93, 94
    fr3_names = ["Pos 93", "Pos 94"]
    
    for idx, name in zip(fr3_indices, fr3_names):
        # Short
        res_s = [s[idx] for s in short_group["fr3_sequence"]]
        cnt_s = pd.Series(res_s).value_counts()
        
        # Long
        res_l = [s[idx] for s in long_group["fr3_sequence"]]
        cnt_l = pd.Series(res_l).value_counts()
        
        lines.append(f"{name}:")
        lines.append(f"  Short: {format_counts(cnt_s, len(short_group))}")
        lines.append(f"  Long:  {format_counts(cnt_l, len(long_group))}")
        lines.append("")
        
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Analysis complete: {OUT_REPORT}")

if __name__ == "__main__":
    main()
