"""
Generate Sequence Logos for FR1 and FR4.
Groups: Short (<11) vs Long (>=11) CDR3.

Steps:
1. Extract FR1 and FR4 sequences.
2. Group by CDR3 length threshold (11).
3. Align sequences (FR1 is usually 25aa, FR4 is 11aa).
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
    
    # 1. FR1 Sequences (25aa)
    # Filter for standard length to ensure alignment
    fr1_short = [s for s in short_group["fr1_sequence"] if len(s)==25]
    fr1_long = [s for s in long_group["fr1_sequence"] if len(s)==25]
    
    write_fasta(fr1_short, OUT_DIR / "FR1_Short_CDR3_lt11.fasta", "Short")
    write_fasta(fr1_long, OUT_DIR / "FR1_Long_CDR3_ge11.fasta", "Long")
    
    # 2. FR4 Sequences (11aa)
    # Filter for standard length
    fr4_short = [s for s in short_group["fr4_sequence"] if len(s)==11]
    fr4_long = [s for s in long_group["fr4_sequence"] if len(s)==11]
    
    write_fasta(fr4_short, OUT_DIR / "FR4_Short_CDR3_lt11.fasta", "Short")
    write_fasta(fr4_long, OUT_DIR / "FR4_Long_CDR3_ge11.fasta", "Long")

if __name__ == "__main__":
    main()
