"""
Analyze CDR3 Hydrophobicity and Global Humanness Score (Proxy for T20).

1. Calculate Gravy Index (Hydrophobicity) for CDR3 sequences.
2. Correlate CDR3 Hydrophobicity with FR2 Humanization status.
3. Compare Global Human Identity across the defined clusters.

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR4_CDR3_data.csv (contains 'h3_sequence')
  - paper/raw data/TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv

Outputs:
  - paper/raw data/MicroAnalysis/TheraSAbDab_19VHH_Hydrophobicity_Analysis.txt
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IN_CDR3_DATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR4_CDR3_data.csv"
IN_METADATA = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"
OUT_REPORT = PROJECT_ROOT / "paper" / "raw data" / "MicroAnalysis" / "TheraSAbDab_19VHH_Hydrophobicity_Analysis.txt"

# Kyte-Doolittle Hydrophobicity Scale
KD_SCALE = {
    'A': 1.8, 'R': -4.5, 'N': -3.5, 'D': -3.5, 'C': 2.5,
    'Q': -3.5, 'E': -3.5, 'G': -0.4, 'H': -3.2, 'I': 4.5,
    'L': 3.8, 'K': -3.9, 'M': 1.9, 'F': 2.8, 'P': -1.6,
    'S': -0.8, 'T': -0.7, 'W': -0.9, 'Y': -1.3, 'V': 4.2
}

def calculate_hydrophobicity(seq):
    if not isinstance(seq, str) or len(seq) == 0: return 0.0
    scores = [KD_SCALE.get(aa, 0.0) for aa in seq]
    return sum(scores) / len(seq)

def load_data():
    df_cdr3 = pd.read_csv(IN_CDR3_DATA)
    # Check column names
    if 'h3_sequence' in df_cdr3.columns:
        df_cdr3['cdr3_sequence'] = df_cdr3['h3_sequence']
    if 'h3_length' in df_cdr3.columns:
        df_cdr3['cdr3_length'] = df_cdr3['h3_length']
        
    df_meta = pd.read_csv(IN_METADATA)
    
    # Merge on antibody_id
    # df_cdr3 usually has duplicates if not careful, drop potential dupes
    df_cdr3 = df_cdr3.drop_duplicates("antibody_id")
    
    df_merged = df_cdr3.merge(df_meta[["antibody_id", "global_human_identity_pct", "fr2_human_pct"]], on="antibody_id")
    return df_merged

def main():
    df = load_data()
    
    # Calculate Hydrophobicity
    df["CDR3_Hydrophobicity"] = df["cdr3_sequence"].apply(calculate_hydrophobicity)
    
    lines = []
    lines.append("="*80)
    lines.append("CDR3 HYDROPHOBICITY & HUMANIZATION ANALYSIS")
    lines.append("="*80)
    
    # 1. Correlation: CDR3 Hydrophobicity vs FR2 Humanization
    # Note: Higher Hydrophobicity -> More hydrophobic -> Needs more solubility compensation (Lower FR2 Human%)?
    corr, p = stats.spearmanr(df["CDR3_Hydrophobicity"], df["fr2_human_pct"])
    lines.append(f"1. Correlation: CDR3 Hydrophobicity vs FR2 Human Identity")
    lines.append(f"   rho = {corr:.3f}, p = {p:.4f}")
    if p > 0.05:
        lines.append("   -> No significant direct correlation.")
    else:
        lines.append("   -> Significant correlation found.")
    lines.append("   (Expected: Negative correlation. More hydrophobic CDR3 -> Lower FR2 Human%)")
        
    lines.append("")
    
    # 2. Critical Length Analysis (Len = 11)
    # Check molecules near the threshold (10-12)
    lines.append("2. Critical Threshold Analysis (CDR3 Length 10-13)")
    lines.append(f"{'ID':<15} | {'Len':<3} | {'Hydro':<6} | {'FR2_Human%':<10} | {'Status'}")
    lines.append("-" * 60)
    
    critical_df = df[(df["cdr3_length"] >= 10) & (df["cdr3_length"] <= 13)].sort_values("cdr3_length")
    
    for _, row in critical_df.iterrows():
        status = "Human-like" if row["fr2_human_pct"] > 80 else "Alpaca-like"
        lines.append(f"{row['antibody_id']:<15} | {row['cdr3_length']:<3} | {row['CDR3_Hydrophobicity']:<6.2f} | {row['fr2_human_pct']:<10.1f} | {status}")
        
    lines.append("")
    
    # 3. Global Human Score (T20 Proxy) by Strategy
    lines.append("3. Global Human Identity (Proxy for T20) by Strategy")
    # Using 'strategy_group' from df_cdr3 part
    strat_col = "strategy_group"
    
    groups = df.groupby(strat_col)["global_human_identity_pct"].agg(['mean', 'std', 'count'])
    lines.append(groups.to_string())
    
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Analysis complete: {OUT_REPORT}")

if __name__ == "__main__":
    main()
