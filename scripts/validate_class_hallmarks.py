"""
Validate New VHH Classes (1/2/3) against Micro-Level Hallmarks.

Goal:
Check if the new phylogenetic classes (Class 1/2/3) correspond to distinct hallmark patterns.
- Class 1 (Human-Clone): Expect Human Hallmarks (V37, G44, L45, W47).
- Class 2 (Long-CDR3 Stabilized): Expect Camelid Hallmarks (F37, E44, R45, G47).
- Class 3 (Intermediate): Expect Mixed/Intermediate patterns.

Inputs:
  - paper/raw data/Phylogeny/TheraSAbDab_19VHH_New_Classification_Table.csv
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv

Outputs:
  - paper/raw data/MicroAnalysis/TheraSAbDab_19VHH_Class_Hallmark_Validation.txt
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_CLASS_TABLE = PROJECT_ROOT / "paper" / "raw data" / "Phylogeny" / "TheraSAbDab_19VHH_New_Classification_Table.csv"
IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
OUT_REPORT = PROJECT_ROOT / "paper" / "raw data" / "MicroAnalysis" / "TheraSAbDab_19VHH_Class_Hallmark_Validation.txt"

# Hallmark Positions (Approximate indices for FR2)
# FR2 is 17aa. 
# Pos 37 (IMGT) ~ Index 1
# Pos 44 (IMGT) ~ Index 8
# Pos 45 (IMGT) ~ Index 9
# Pos 47 (IMGT) ~ Index 11
HALLMARK_INDICES = {
    37: 1,
    44: 8,
    45: 9,
    47: 11
}

def get_residues(seq, indices):
    res = {}
    for pos, idx in indices.items():
        if idx < len(seq):
            res[pos] = seq[idx]
        else:
            res[pos] = "-"
    return res

def main():
    # Load Data
    df_class = pd.read_csv(IN_CLASS_TABLE)
    df_seq = pd.read_csv(IN_FR_SEQ)
    
    # Merge
    df_class = df_class.drop_duplicates("antibody_id")
    df = df_class.merge(df_seq, on="antibody_id")
    
    # Check column names (handle suffix issue from previous merges in source files)
    # Based on error log: 'fr2_sequence_x' or 'fr2_sequence_y' might exist
    target_col = 'fr2_sequence'
    if target_col not in df.columns:
        if 'fr2_sequence_x' in df.columns: target_col = 'fr2_sequence_x'
        elif 'fr2_sequence_y' in df.columns: target_col = 'fr2_sequence_y'
    
    lines = []
    lines.append("="*80)
    lines.append("VALIDATION OF NEW VHH CLASSES AGAINST HALLMARK RESIDUES")
    lines.append("="*80)
    lines.append("")
    
    classes = sorted(df["New_Class"].unique())
    
    for cls in classes:
        sub = df[df["New_Class"] == cls]
        lines.append(f"## {cls} (N={len(sub)})")
        if 'h3_length' in sub.columns:
             lines.append(f"  Mean CDR3 Length: {sub['h3_length'].mean():.1f}")
        
        # Analyze Hallmarks
        hallmark_data = []
        for seq in sub[target_col]:
            hallmark_data.append(get_residues(seq, HALLMARK_INDICES))
            
        # Summarize
        for pos in [37, 44, 45, 47]:
            residues = [d[pos] for d in hallmark_data]
            counts = pd.Series(residues).value_counts()
            top_str = ", ".join([f"{aa}:{cnt}" for aa, cnt in counts.items()])
            lines.append(f"  Pos {pos}: {top_str}")
            
        lines.append("")
        
    # Interpretation
    lines.append("-" * 80)
    lines.append("INTERPRETATION GUIDE:")
    lines.append("Pos 37: Human=V, Camelid=F/Y")
    lines.append("Pos 44: Human=G, Camelid=E")
    lines.append("Pos 45: Human=L, Camelid=R")
    lines.append("Pos 47: Human=W, Camelid=F/G/L")
    lines.append("-" * 80)
    
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Validation complete: {OUT_REPORT}")

if __name__ == "__main__":
    main()
