"""
Generate Sequence Logos for FR2 and FR3 (Vernier Zone).
Groups: Short (<11) vs Long (>=11) CDR3.

Steps:
1. Extract FR2 and FR3 sequences.
2. Group by CDR3 length threshold (11).
3. Align sequences (simple length-based or motif-based).
4. Output FASTA files for WebLogo generation.
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_METADATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"
OUT_DIR = PROJECT_ROOT / "paper" / "raw data" / "Logos"

if not OUT_DIR.exists():
    OUT_DIR.mkdir(parents=True)

def load_data():
    df_seq = pd.read_csv(IN_FR_SEQ)
    df_meta = pd.read_csv(IN_METADATA)
    df_merged = df_seq.merge(df_meta[["antibody_id", "h3_length"]], on="antibody_id")
    df_merged = df_merged.rename(columns={"h3_length": "H3_Len"})
    return df_merged

def write_fasta(sequences, filename, label_prefix="Seq"):
    with open(filename, 'w') as f:
        for i, seq in enumerate(sequences):
            f.write(f">{label_prefix}_{i+1}\n{seq}\n")
    print(f"Wrote {len(sequences)} sequences to {filename}")

def main():
    df = load_data()
    
    # Split by Threshold 11
    short_group = df[df["H3_Len"] < 11]
    long_group = df[df["H3_Len"] >= 11]
    
    # 1. FR2 Sequences (17aa)
    # Ensure all are same length for Logo
    fr2_short = [s for s in short_group["fr2_sequence"] if len(s)==17]
    fr2_long = [s for s in long_group["fr2_sequence"] if len(s)==17]
    
    write_fasta(fr2_short, OUT_DIR / "FR2_Short_CDR3_lt11.fasta", "Short")
    write_fasta(fr2_long, OUT_DIR / "FR2_Long_CDR3_ge11.fasta", "Long")
    
    # 2. FR3 Start Sequences (Vernier Zone Focus)
    # Extract first 15aa of FR3 to cover Pos 66-80 (including 71)
    # Note: Our FR3 includes CDR2 tail (~8aa). 
    # So Vernier 71 is around index 13.
    # Let's take first 20aa to be safe.
    fr3_short = [s[:20] for s in short_group["fr3_sequence"]]
    fr3_long = [s[:20] for s in long_group["fr3_sequence"]]
    
    write_fasta(fr3_short, OUT_DIR / "FR3_Start_Short_CDR3_lt11.fasta", "Short")
    write_fasta(fr3_long, OUT_DIR / "FR3_Start_Long_CDR3_ge11.fasta", "Long")

if __name__ == "__main__":
    main()
