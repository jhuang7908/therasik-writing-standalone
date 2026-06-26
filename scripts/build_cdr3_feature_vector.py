import pandas as pd
import numpy as np
import os
import re
from pathlib import Path

def compute_cdr3_features(df):
    """
    Compute engineering feature vector for CDR3 sequences.
    """
    if 'cdr3' not in df.columns:
        # Robustly infer column if not 'cdr3'
        possible_cols = [c for c in df.columns if 'cdr3' in c.lower() and 'len' not in c.lower()]
        if possible_cols:
            df['cdr3'] = df[possible_cols[0]]
        else:
            raise ValueError("Could not find CDR3 sequence column in dataframe.")

    # Fill NA to avoid errors
    df['cdr3'] = df['cdr3'].fillna('')

    # 1. cdr3_len
    df['cdr3_len_check'] = df['cdr3'].map(len)
    
    # 2. Hydrophobic fraction {A,I,L,M,F,W,V,Y}
    hydrophobic_set = set("AILMFWVY")
    def calc_frac(seq, aa_set):
        if not seq: return 0.0
        count = sum(1 for aa in seq if aa in aa_set)
        return count / len(seq)

    df['cdr3_hydrophobic_frac'] = df['cdr3'].apply(lambda x: calc_frac(x, hydrophobic_set))

    # 3. Aromatic fraction {F,W,Y}
    aromatic_set = set("FWY")
    df['cdr3_aromatic_frac'] = df['cdr3'].apply(lambda x: calc_frac(x, aromatic_set))

    # 4. Gly fraction
    df['cdr3_gly_frac'] = df['cdr3'].apply(lambda x: calc_frac(x, set("G")))

    # 5. Pro fraction
    df['cdr3_pro_frac'] = df['cdr3'].apply(lambda x: calc_frac(x, set("P")))

    # 6. GP fraction {G,P}
    df['cdr3_gp_frac'] = df['cdr3'].apply(lambda x: calc_frac(x, set("GP")))

    # 7. Cys count
    df['cdr3_cys_count'] = df['cdr3'].apply(lambda x: x.count('C'))

    # 8. N-gly motifs: NXS/T where X != P
    def count_ngly(seq):
        if not seq: return 0
        # IMGT CDR3 starts at 105 and ends at 117. 
        # Pattern: N followed by any AA except P, followed by S or T
        matches = re.findall(r'N[^P][ST]', seq)
        return len(matches)

    df['cdr3_ngly_motifs'] = df['cdr3'].apply(count_ngly)

    # 9. Max hydrophobic run
    def max_hydro_run(seq):
        if not seq: return 0
        max_run = 0
        current_run = 0
        for aa in seq:
            if aa in hydrophobic_set:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 0
        return max_run

    df['cdr3_max_hydrophobic_run'] = df['cdr3'].apply(max_hydro_run)

    # 10. Net charge estimate (K+R+H) - (D+E)
    def net_charge(seq):
        if not seq: return 0
        pos = sum(1 for aa in seq if aa in "KRH")
        neg = sum(1 for aa in seq if aa in "DE")
        return pos - neg

    df['cdr3_net_charge_est'] = df['cdr3'].apply(net_charge)

    # Self-checks
    mask = df['cdr3'] != ''
    if not (df.loc[mask, 'cdr3_len_check'] == df.loc[mask, 'cdr3'].str.len()).all():
        print("Warning: cdr3_len self-check failed for some rows.")
    
    return df

def main():
    input_path = Path("reports/slice3_vhh_paper_grade_master_table.csv")
    output_csv = Path("data/slice3_vhh_paper_grade_master_table_plus_cdr3_features.csv")
    output_summary_md = Path("output/slice3_cdr3_feature_summary.md")
    output_redflags_csv = Path("output/slice3_cdr3_feature_redflags.csv")

    os.makedirs("data", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    df = pd.read_csv(input_path)
    df = compute_cdr3_features(df)

    # Save master table
    df.to_csv(output_csv, index=False)
    print(f"Saved master table with features to {output_csv}")

    # Summary Table by Strategy
    strategy_col = 'strategy'
    if strategy_col not in df.columns:
        strategy_col = [c for c in df.columns if 'strategy' in c.lower()][0]
    
    feature_cols = [
        'cdr3_len_check', 'cdr3_hydrophobic_frac', 'cdr3_aromatic_frac', 
        'cdr3_gly_frac', 'cdr3_pro_frac', 'cdr3_gp_frac', 
        'cdr3_cys_count', 'cdr3_ngly_motifs', 'cdr3_max_hydrophobic_run', 
        'cdr3_net_charge_est'
    ]

    summary = df.groupby(strategy_col)[feature_cols].agg(['mean', 'median']).round(3)
    
    with open(output_summary_md, "w", encoding="utf-8") as f:
        f.write("# Slice 3 CDR3 Feature Summary by Design Strategy\n\n")
        f.write(summary.to_markdown())
        f.write("\n\n*Note: Means and medians aggregated per strategy group.*\n")
    
    print(f"Saved summary to {output_summary_md}")

    # Red-flag list
    # - ngly_motifs >= 1
    # - cys_count >= 1 (extra Cys)
    # - hydrophobic_frac >= 0.50 OR max_hydrophobic_run >= 4
    # - aromatic_frac >= 0.25
    redflags = df[
        (df['cdr3_ngly_motifs'] >= 1) | 
        (df['cdr3_cys_count'] >= 1) | 
        (df['cdr3_hydrophobic_frac'] >= 0.50) | 
        (df['cdr3_max_hydrophobic_run'] >= 4) | 
        (df['cdr3_aromatic_frac'] >= 0.25)
    ].copy()

    # Add flags for clarity
    redflags['flag_ngly'] = redflags['cdr3_ngly_motifs'] >= 1
    redflags['flag_cys'] = redflags['cdr3_cys_count'] >= 1
    redflags['flag_hydro'] = (redflags['cdr3_hydrophobic_frac'] >= 0.50) | (redflags['cdr3_max_hydrophobic_run'] >= 4)
    redflags['flag_aromatic'] = redflags['aromatic_frac'] >= 0.25 if 'aromatic_frac' in redflags else redflags['cdr3_aromatic_frac'] >= 0.25

    redflags.to_csv(output_redflags_csv, index=False)
    print(f"Saved red-flags to {output_redflags_csv}")

if __name__ == "__main__":
    main()
