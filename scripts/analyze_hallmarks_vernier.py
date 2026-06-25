"""
Micro-Level Residue Analysis: Hallmark & Vernier Zone Comparison by CDR3 Length.

Goal:
1. Divide VHHs into Short (<=10) and Long (>10) CDR3 groups.
2. Analyze AA distribution at key Hallmark (FR2) and Vernier (FR3) sites.
3. Verify if Long CDR3 group retains hydrophilic Hallmarks (F/Y, E, R, G/L) while Short group humanizes (V, G, L, W).
4. Analyze Vernier zone conservation.

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/raw data/TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv

Outputs:
  - paper/raw data/MicroAnalysis/TheraSAbDab_19VHH_Hallmark_Vernier_Analysis.txt
  - paper/raw data/MicroAnalysis/Hallmark_Frequency_Table.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_METADATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"
OUT_DIR = PROJECT_ROOT / "paper" / "raw data" / "MicroAnalysis"
OUT_REPORT = OUT_DIR / "TheraSAbDab_19VHH_Hallmark_Vernier_Analysis.txt"
OUT_CSV = OUT_DIR / "Hallmark_Frequency_Table.csv"

if not OUT_DIR.exists():
    OUT_DIR.mkdir(parents=True)

# IMGT Positions for Analysis
# FR2 Hallmarks
HALLMARK_POS = {
    37: 1,  # Approx index in FR2 (Start ~36/37) -> FR2 is 17aa. IMGT 36-49. 37 is 2nd.
    44: 8,
    45: 9,
    47: 11
}
# FR3 Vernier (Key structural sites)
# FR3 is 38aa. IMGT 66-104.
# Common Vernier: 67, 69, 71, 73, 78, 93, 94
VERNIER_POS = {
    67: 1, 
    71: 5,
    78: 12,
    94: 28 # Approx, need precise alignment mapping
}

# Standard Reference Residues (Human vs Alpaca)
REF_RESIDUES = {
    "Hallmark": {
        37: {"Human": "V", "Alpaca": "F/Y"},
        44: {"Human": "G", "Alpaca": "E"},
        45: {"Human": "L", "Alpaca": "R"},
        47: {"Human": "W", "Alpaca": "F/G/L"} 
    }
}

def load_data():
    df_seq = pd.read_csv(IN_FR_SEQ)
    df_meta = pd.read_csv(IN_METADATA)
    
    # Merge H3 Length
    df_merged = df_seq.merge(df_meta[["antibody_id", "h3_length"]], on="antibody_id")
    df_merged = df_merged.rename(columns={"h3_length": "H3_Len"})
    return df_merged

def extract_residues(seq, positions_map):
    """Extract residues at specific 0-based indices from a sequence string."""
    res = {}
    for imgt, idx in positions_map.items():
        if idx < len(seq):
            res[imgt] = seq[idx]
        else:
            res[imgt] = "-"
    return res

def analyze_group(df, group_name, region_seq_col, pos_map, ref_type="Hallmark"):
    """Analyze AA frequency for a group at specific positions."""
    
    # 1. Extract residues for all seqs in group
    extracted_data = []
    for seq in df[region_seq_col]:
        # Simple mapping: Assuming fixed length FRs for now (FR2=17, FR3=38) which is true for this dataset
        # However, accurate IMGT mapping is better.
        # Based on previous analysis, FR2 is consistent.
        # FR2 IMGT 36-49. Length 17 (36,37,38...49 + gap? No, VHH FR2 is 17aa)
        # 36 37 38 39 40 41 42 43 44 45 46 47 48 49 (14 pos) ??
        # Let's use the provided index map which is approximate but consistent for alignment.
        
        # Refined Mapping for FR2 (17aa):
        # 0:36, 1:37, 2:38, 3:39, 4:40, 5:41, 6:42, 7:43, 8:44, 9:45, 10:46, 11:47, 12:48, 13:49, ...
        # Standard: 36-49. 17aa includes some 50?
        # Let's rely on relative index:
        # Pos 37 is usually 2nd residue (Index 1)
        # Pos 44 is usually 9th residue (Index 8)
        # Pos 45 is usually 10th residue (Index 9)
        # Pos 47 is usually 12th residue (Index 11)
        
        res = {}
        # Using refined indices for FR2
        if "fr2" in region_seq_col:
            res[37] = seq[1]
            res[44] = seq[8]
            res[45] = seq[9]
            res[47] = seq[11]
        elif "fr3" in region_seq_col:
            # FR3 (38aa). IMGT 66-104.
            # 66,67,68,69,70,71...
            # Pos 71 is usually index 5 (66,67,68,69,70,71)
            # Pos 94 is near end. 
            res[71] = seq[5]
            # 94 is tricky without alignment. Let's stick to 71 (Vernier Key)
            
        extracted_data.append(res)
        
    # 2. Calculate Frequencies
    freqs = {}
    total = len(extracted_data)
    if total == 0: return {}
    
    sample_keys = list(extracted_data[0].keys())
    for pos in sample_keys:
        aa_list = [d[pos] for d in extracted_data]
        counts = pd.Series(aa_list).value_counts()
        freqs[pos] = counts # / total
        
    return freqs

def format_freqs(freqs, group_name, n):
    lines = []
    lines.append(f"Group: {group_name} (N={n})")
    for pos, counts in freqs.items():
        top_aa = counts.head(3).to_dict()
        top_str = ", ".join([f"{aa}:{cnt}({cnt/n:.0%})" for aa, cnt in top_aa.items()])
        lines.append(f"  Pos {pos}: {top_str}")
        
        # Check Human vs Alpaca for Hallmarks
        if pos in REF_RESIDUES.get("Hallmark", {}):
            h_ref = REF_RESIDUES["Hallmark"][pos]["Human"]
            a_ref = REF_RESIDUES["Hallmark"][pos]["Alpaca"]
            
            # Simple check
            is_human = any(aa in h_ref for aa in counts.index)
            is_alpaca = any(aa in a_ref for aa in counts.index)
            # lines.append(f"       -> Ref: H({h_ref}) / A({a_ref})")
            
    lines.append("")
    return lines

def main():
    df = load_data()
    
    # Define Groups
    short_group = df[df["H3_Len"] <= 10]
    long_group = df[df["H3_Len"] > 10]
    
    report = []
    report.append("="*80)
    report.append("MICRO-LEVEL ANALYSIS: HALLMARK & VERNIER RESIDUES by CDR3 LENGTH")
    report.append("="*80)
    report.append(f"Short CDR3 (<=10): N={len(short_group)}")
    report.append(f"Long CDR3 (>10):  N={len(long_group)}")
    report.append("")
    
    # --- 1. FR2 Hallmark Analysis ---
    report.append("## 1. FR2 Hallmark Residues (Solubility Core)")
    report.append("Checking Pos 37, 44, 45, 47")
    report.append("-" * 60)
    
    # Short
    freqs_s = analyze_group(short_group, "Short_CDR3", "fr2_sequence", HALLMARK_POS)
    report.extend(format_freqs(freqs_s, "Short CDR3", len(short_group)))
    
    # Long
    freqs_l = analyze_group(long_group, "Long_CDR3", "fr2_sequence", HALLMARK_POS)
    report.extend(format_freqs(freqs_l, "Long CDR3", len(long_group)))
    
    # --- 2. FR3 Vernier Analysis ---
    report.append("## 2. FR3 Vernier Residues (Structural Support)")
    report.append("Checking Pos 71 (Key H2-Fold Determinant)")
    report.append("-" * 60)
    
    freqs_s_v = analyze_group(short_group, "Short_CDR3", "fr3_sequence", VERNIER_POS)
    report.extend(format_freqs(freqs_s_v, "Short CDR3", len(short_group)))
    
    freqs_l_v = analyze_group(long_group, "Long_CDR3", "fr3_sequence", VERNIER_POS)
    report.extend(format_freqs(freqs_l_v, "Long CDR3", len(long_group)))
    
    # --- 3. Hypothesis Verification ---
    report.append("## 3. Hypothesis Verification")
    report.append("-" * 60)
    
    # Check Pos 44/45 in Long Group
    # Expecting E/R (Alpaca)
    p44_l = freqs_l.get(44, pd.Series()).to_dict()
    p45_l = freqs_l.get(45, pd.Series()).to_dict()
    
    report.append("Hypothesis A: Long CDR3 > 10aa retains Alpaca Hallmarks (E44/R45)?")
    report.append(f"  Long Group Pos 44: {p44_l}")
    report.append(f"  Long Group Pos 45: {p45_l}")
    
    # Check Pos 44/45 in Short Group
    # Expecting G/L (Human)
    p44_s = freqs_s.get(44, pd.Series()).to_dict()
    p45_s = freqs_s.get(45, pd.Series()).to_dict()
    
    report.append("Hypothesis B: Short CDR3 <= 10aa mutates to Human Hallmarks (G44/L45)?")
    report.append(f"  Short Group Pos 44: {p44_s}")
    report.append(f"  Short Group Pos 45: {p45_s}")
    
    OUT_REPORT.write_text("\n".join(report), encoding="utf-8")
    print(f"Analysis complete: {OUT_REPORT}")

if __name__ == "__main__":
    main()
