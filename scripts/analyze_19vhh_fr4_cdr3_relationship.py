"""
Analyze the relationship between FR4 sequences and CDR3 length.

Hypothesis: FR4 may vary to accommodate different CDR3 lengths, since FR4 (IMGT 118-128)
immediately follows CDR3 (IMGT 105-117) and must structurally connect to the constant region.

Key analyses:
  1. FR4 sequence variation vs CDR3 length
  2. FR4 length vs CDR3 length correlation
  3. FR4 conservation patterns grouped by CDR3 length bins
  4. Position-by-position FR4 conservation analysis
  5. Check if FR4-CDR3 junction residues are conserved

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/raw data/TheraSAbDab_19VHH_ANARCII_CDR_boundaries.csv
  - paper/tables/Table1_slice3_19_clinical_vhh_master.csv

Outputs:
  - paper/raw data/TheraSAbDab_19VHH_FR4_CDR3_relationship.txt
  - paper/raw data/TheraSAbDab_19VHH_FR4_CDR3_data.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent

IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_CDR = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_ANARCII_CDR_boundaries.csv"
IN_TABLE1 = PROJECT_ROOT / "paper" / "tables" / "Table1_slice3_19_clinical_vhh_master.csv"

OUT_DIR = PROJECT_ROOT / "paper" / "raw data"
OUT_REPORT = OUT_DIR / "TheraSAbDab_19VHH_FR4_CDR3_relationship.txt"
OUT_DATA = OUT_DIR / "TheraSAbDab_19VHH_FR4_CDR3_data.csv"


def compute_identity(seq1: str, seq2: str) -> float:
    """Compute pairwise identity."""
    if not seq1 or not seq2:
        return 0.0
    min_len = min(len(seq1), len(seq2))
    if min_len == 0:
        return 0.0
    matches = sum(1 for i in range(min_len) if seq1[i] == seq2[i])
    return (matches / min_len) * 100.0


def build_report(merged_df: pd.DataFrame) -> list[str]:
    """Build comprehensive FR4-CDR3 relationship report."""
    lines = []
    lines.append("=" * 80)
    lines.append("FR4-CDR3 Relationship Analysis: Does FR4 Vary with CDR3 Length?")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Hypothesis: FR4 may need to adapt structurally to accommodate different CDR3 lengths")
    lines.append("")
    
    # Overall statistics
    lines.append("## 1. Overall FR4 and CDR3 Statistics")
    lines.append("")
    lines.append(f"FR4 length:")
    lines.append(f"  - Range: {merged_df['fr4_length'].min()}-{merged_df['fr4_length'].max()}aa")
    lines.append(f"  - Median: {merged_df['fr4_length'].median():.0f}aa")
    lines.append(f"  - Unique lengths: {merged_df['fr4_length'].nunique()}")
    lines.append("")
    lines.append(f"CDR3 length:")
    lines.append(f"  - Range: {merged_df['h3_length'].min()}-{merged_df['h3_length'].max()}aa")
    lines.append(f"  - Median: {merged_df['h3_length'].median():.0f}aa")
    lines.append(f"  - Unique lengths: {merged_df['h3_length'].nunique()}")
    lines.append("")
    
    # Check correlation
    from scipy import stats
    if len(merged_df) > 2:
        corr, pval = stats.spearmanr(merged_df['fr4_length'], merged_df['h3_length'])
        lines.append(f"FR4 length vs CDR3 length correlation:")
        lines.append(f"  - Spearman's rho: {corr:.3f}")
        lines.append(f"  - P-value: {pval:.4f}")
        if pval < 0.05:
            lines.append(f"  ✓ SIGNIFICANT correlation detected!")
        else:
            lines.append(f"  ✗ No significant correlation")
    lines.append("")
    
    # FR4 sequences grouped by CDR3 length
    lines.append("## 2. FR4 Sequences Grouped by CDR3 Length")
    lines.append("")
    
    # Bin CDR3 lengths
    merged_df['cdr3_bin'] = pd.cut(
        merged_df['h3_length'], 
        bins=[0, 10, 15, 20, 100], 
        labels=['short (≤10)', 'medium (11-15)', 'long (16-20)', 'very_long (>20)']
    )
    
    for bin_label in ['short (≤10)', 'medium (11-15)', 'long (16-20)', 'very_long (>20)']:
        sub = merged_df[merged_df['cdr3_bin'] == bin_label]
        if sub.empty:
            continue
        lines.append(f"CDR3 {bin_label} (n={len(sub)}):")
        lines.append(f"  FR4 lengths: {', '.join(str(x) for x in sorted(sub['fr4_length'].unique()))}aa")
        
        # FR4 consensus for this group
        fr4_seqs = sub['fr4_sequence'].tolist()
        if fr4_seqs:
            # Build consensus
            max_len = max(len(s) for s in fr4_seqs)
            consensus = []
            for pos in range(max_len):
                residues = [s[pos] for s in fr4_seqs if pos < len(s)]
                if residues:
                    from collections import Counter
                    most_common = Counter(residues).most_common(1)[0][0]
                    consensus.append(most_common)
            consensus_seq = "".join(consensus)
            lines.append(f"  FR4 consensus: {consensus_seq}")
        
        # Show individual sequences
        for _, row in sub.iterrows():
            lines.append(f"    {row['antibody_id']:20s}: CDR3={row['h3_length']:2d}aa, FR4={row['fr4_length']:2d}aa, {row['fr4_sequence']}")
    lines.append("")
    
    # FR4 conservation by CDR3 length bin
    lines.append("## 3. FR4 Conservation by CDR3 Length Category")
    lines.append("")
    
    for bin_label in ['short (≤10)', 'medium (11-15)', 'long (16-20)', 'very_long (>20)']:
        sub = merged_df[merged_df['cdr3_bin'] == bin_label]
        if len(sub) < 2:
            continue
        
        # Compute pairwise FR4 identity within this group
        fr4_seqs = sub['fr4_sequence'].tolist()
        identities = []
        for i in range(len(fr4_seqs)):
            for j in range(i+1, len(fr4_seqs)):
                identities.append(compute_identity(fr4_seqs[i], fr4_seqs[j]))
        
        if identities:
            lines.append(f"CDR3 {bin_label}:")
            lines.append(f"  FR4 pairwise identity: {np.mean(identities):.1f}% (range: {min(identities):.1f}-{max(identities):.1f}%)")
    lines.append("")
    
    # Position-by-position FR4 analysis
    lines.append("## 4. FR4 Position-by-Position Conservation")
    lines.append("")
    
    fr4_seqs = merged_df['fr4_sequence'].tolist()
    max_len = max(len(s) for s in fr4_seqs)
    
    lines.append(f"FR4 position conservation (total {max_len} positions):")
    for pos in range(max_len):
        residues = [s[pos] for s in fr4_seqs if pos < len(s)]
        if not residues:
            continue
        from collections import Counter
        counts = Counter(residues)
        total = len(residues)
        most_common_aa, most_common_count = counts.most_common(1)[0]
        conservation_pct = (most_common_count / total) * 100.0
        
        if conservation_pct < 100.0:  # Only show variable positions
            variants_str = ", ".join(f"{aa}:{c}" for aa, c in counts.most_common())
            lines.append(f"  Pos {pos+1:2d}: {most_common_aa} ({conservation_pct:.0f}%) | {variants_str}")
    lines.append("")
    
    # FR4-CDR3 junction analysis
    lines.append("## 5. CDR3-FR4 Junction Residues")
    lines.append("")
    lines.append("Last 2 residues of CDR3 and first 2 residues of FR4:")
    for _, row in merged_df.iterrows():
        cdr3_seq = row['h3_sequence']
        fr4_seq = row['fr4_sequence']
        cdr3_tail = cdr3_seq[-2:] if len(cdr3_seq) >= 2 else cdr3_seq
        fr4_head = fr4_seq[:2] if len(fr4_seq) >= 2 else fr4_seq
        lines.append(f"  {row['antibody_id']:20s}: CDR3[...{cdr3_tail}] → FR4[{fr4_head}...] (CDR3={row['h3_length']:2d}aa)")
    lines.append("")
    
    # Check if FR4 first residue is conserved
    fr4_first_residues = [s[0] if len(s) > 0 else "" for s in merged_df['fr4_sequence'].tolist()]
    from collections import Counter
    first_res_counts = Counter(fr4_first_residues)
    lines.append("FR4 first residue distribution:")
    for aa, count in first_res_counts.most_common():
        lines.append(f"  {aa}: {count} ({100.0*count/len(fr4_first_residues):.1f}%)")
    lines.append("")
    
    # Strategy analysis
    lines.append("## 6. FR4 Variation by Strategy")
    lines.append("")
    for strategy in ["BM", "SR", "Native"]:
        sub = merged_df[merged_df["strategy_group"] == strategy]
        if sub.empty:
            continue
        lines.append(f"{strategy} (n={len(sub)}):")
        lines.append(f"  CDR3 length: {sub['h3_length'].median():.0f}aa (range: {sub['h3_length'].min()}-{sub['h3_length'].max()})")
        lines.append(f"  FR4 length: {sub['fr4_length'].median():.0f}aa (range: {sub['fr4_length'].min()}-{sub['fr4_length'].max()})")
        
        # FR4 pairwise identity within strategy
        if len(sub) > 1:
            fr4_seqs = sub['fr4_sequence'].tolist()
            identities = []
            for i in range(len(fr4_seqs)):
                for j in range(i+1, len(fr4_seqs)):
                    identities.append(compute_identity(fr4_seqs[i], fr4_seqs[j]))
            if identities:
                lines.append(f"  FR4 pairwise identity: {np.mean(identities):.1f}%")
    lines.append("")
    
    # Key Findings
    lines.append("## 7. Key Findings")
    lines.append("")
    
    # Check if FR4 length varies
    fr4_length_variance = merged_df['fr4_length'].nunique()
    if fr4_length_variance > 1:
        lines.append(f"1. FR4 length is VARIABLE: {fr4_length_variance} different lengths detected")
        lines.append(f"   Range: {merged_df['fr4_length'].min()}-{merged_df['fr4_length'].max()}aa")
    else:
        lines.append(f"1. FR4 length is INVARIANT: all molecules have {merged_df['fr4_length'].iloc[0]}aa FR4")
    lines.append("")
    
    # Check correlation strength
    if len(merged_df) > 2:
        corr, pval = stats.spearmanr(merged_df['fr4_length'], merged_df['h3_length'])
        if abs(corr) > 0.5 and pval < 0.05:
            lines.append(f"2. STRONG correlation between FR4 and CDR3 length (rho={corr:.3f}, p={pval:.4f})")
            lines.append(f"   → FR4 DOES adapt to CDR3 length variations")
        elif abs(corr) > 0.3:
            lines.append(f"2. MODERATE correlation between FR4 and CDR3 length (rho={corr:.3f}, p={pval:.4f})")
            lines.append(f"   → Some structural coupling between FR4 and CDR3")
        else:
            lines.append(f"2. WEAK/NO correlation between FR4 and CDR3 length (rho={corr:.3f}, p={pval:.4f})")
            lines.append(f"   → FR4 length is INDEPENDENT of CDR3 length")
    lines.append("")
    
    # FR4 sequence conservation
    fr4_seqs = merged_df['fr4_sequence'].tolist()
    all_identities = []
    for i in range(len(fr4_seqs)):
        for j in range(i+1, len(fr4_seqs)):
            all_identities.append(compute_identity(fr4_seqs[i], fr4_seqs[j]))
    
    if all_identities:
        median_fr4_identity = np.median(all_identities)
        lines.append(f"3. FR4 sequence conservation: {median_fr4_identity:.1f}% median pairwise identity")
        if median_fr4_identity > 90.0:
            lines.append(f"   → FR4 is HIGHLY CONSERVED despite CDR3 length variation")
        elif median_fr4_identity > 70.0:
            lines.append(f"   → FR4 shows MODERATE conservation")
        else:
            lines.append(f"   → FR4 is HIGHLY VARIABLE")
    lines.append("")
    
    # Final verdict
    lines.append("## 8. FINAL VERDICT: Does FR4 Adapt to CDR3 Length?")
    lines.append("")
    
    if len(merged_df) > 2:
        corr, pval = stats.spearmanr(merged_df['fr4_length'], merged_df['h3_length'])
        
        if abs(corr) > 0.5 and pval < 0.05:
            lines.append("✓ YES - FR4 length shows significant correlation with CDR3 length")
            lines.append("")
            lines.append("Evidence:")
            lines.append(f"  - Spearman correlation: {corr:.3f} (p={pval:.4f})")
            lines.append(f"  - CDR3 range: {merged_df['h3_length'].min()}-{merged_df['h3_length'].max()}aa")
            lines.append(f"  - FR4 range: {merged_df['fr4_length'].min()}-{merged_df['fr4_length'].max()}aa")
            lines.append("")
            lines.append("Interpretation:")
            lines.append("  FR4 structurally adapts to accommodate different CDR3 loop lengths.")
            lines.append("  This explains FR4 sequence diversity independent of humanization strategy.")
        else:
            lines.append("✗ NO - FR4 length is independent of CDR3 length")
            lines.append("")
            lines.append("Evidence:")
            lines.append(f"  - Spearman correlation: {corr:.3f} (p={pval:.4f}, not significant)")
            lines.append(f"  - FR4 median identity: {median_fr4_identity:.1f}%")
            lines.append("")
            lines.append("Interpretation:")
            lines.append("  FR4 uses a fixed-length scaffold regardless of CDR3 variation.")
            lines.append("  FR4 sequence diversity is driven by:")
            lines.append("    a) Junction optimization (CDR3-FR4 interface)")
            lines.append("    b) Constant region compatibility")
            lines.append("    c) Expression/stability requirements")
            lines.append("    d) Individual molecule-specific engineering")
    
    lines.append("")
    lines.append("=" * 80)
    
    return lines


def main() -> None:
    fr_df = pd.read_csv(IN_FR_SEQ)
    cdr_df = pd.read_csv(IN_CDR)
    t1 = pd.read_csv(IN_TABLE1)
    
    # Merge data
    merged = fr_df.merge(cdr_df[["antibody_id", "cdr3_start_imgt", "cdr3_end_imgt", "cdr3_length", "cdr3_sequence"]], on="antibody_id", how="left")
    merged = merged.merge(t1[["antibody_id", "strategy_group", "h2_class"]], on="antibody_id", how="left")
    
    # Rename CDR3 columns to match analysis code
    merged = merged.rename(columns={
        "cdr3_length": "h3_length",
        "cdr3_sequence": "h3_sequence",
    })
    
    # Compute FR4 length
    merged["fr4_length"] = merged["fr4_sequence"].apply(len)
    
    # Save data
    merged.to_csv(OUT_DATA, index=False)
    print(f"Wrote: {OUT_DATA}")
    
    # Build report
    report_lines = build_report(merged)
    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Wrote: {OUT_REPORT}")


if __name__ == "__main__":
    main()
