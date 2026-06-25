"""
Analyze if FR4 sequence variants correlate with CDR3 length or CDR2 canonical fold.

Question: Are FR4 sequence differences driven by:
  1. CDR3 length (short vs medium vs long)?
  2. CDR2 canonical fold (H2-9-1 vs H2-10-1)?
  3. Humanization strategy (BM/SR/Native)?

FR4 has 5 variable positions (1, 2, 6, 10, 11 out of 11 total):
  - Pos 1: W (84%), R (11%), S (5%)
  - Pos 2: G (95%), S (5%)
  - Pos 6: L (84%), Q (11%), M (5%)
  - Pos 10: S (89%), K (11%)
  - Pos 11: S (89%), P (11%)

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR4_CDR3_data.csv
  - paper/tables/Table1_slice3_19_clinical_vhh_master.csv

Outputs:
  - paper/raw data/TheraSAbDab_19VHH_FR4_variants_correlation.txt
  - paper/raw data/TheraSAbDab_19VHH_FR4_variants_table.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent

IN_FR4_CDR3 = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR4_CDR3_data.csv"
IN_TABLE1 = PROJECT_ROOT / "paper" / "tables" / "Table1_slice3_19_clinical_vhh_master.csv"

OUT_DIR = PROJECT_ROOT / "paper" / "raw data"
OUT_REPORT = OUT_DIR / "TheraSAbDab_19VHH_FR4_variants_correlation.txt"
OUT_TABLE = OUT_DIR / "TheraSAbDab_19VHH_FR4_variants_table.csv"


def extract_fr4_positions(fr4_seq: str) -> dict:
    """Extract residues at FR4 variable positions."""
    return {
        "fr4_pos1": fr4_seq[0] if len(fr4_seq) > 0 else "-",
        "fr4_pos2": fr4_seq[1] if len(fr4_seq) > 1 else "-",
        "fr4_pos6": fr4_seq[5] if len(fr4_seq) > 5 else "-",
        "fr4_pos10": fr4_seq[9] if len(fr4_seq) > 9 else "-",
        "fr4_pos11": fr4_seq[10] if len(fr4_seq) > 10 else "-",
    }


def classify_cdr3_length(length: int) -> str:
    """Classify CDR3 length into bins."""
    if length <= 10:
        return "short"
    elif length <= 15:
        return "medium"
    elif length <= 20:
        return "long"
    else:
        return "very_long"


def build_report(merged_df: pd.DataFrame) -> list[str]:
    """Build comprehensive FR4 variant correlation report."""
    lines = []
    lines.append("=" * 80)
    lines.append("FR4 Sequence Variants: Correlation with CDR3 Length and CDR2 Fold")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Question: Do FR4 sequence variants correlate with:")
    lines.append("  1. CDR3 length (structural constraint)?")
    lines.append("  2. CDR2 canonical fold (H2-9-1 vs H2-10-1)?")
    lines.append("  3. Humanization strategy (BM/SR/Native)?")
    lines.append("")
    
    # Overall FR4 variant distribution
    lines.append("## 1. FR4 Variable Positions Overview")
    lines.append("")
    lines.append("FR4 consensus: WGQGTLVTVSS")
    lines.append("Variable positions (conservation <100%):")
    lines.append("")
    
    for pos, col in [(1, "fr4_pos1"), (2, "fr4_pos2"), (6, "fr4_pos6"), (10, "fr4_pos10"), (11, "fr4_pos11")]:
        from collections import Counter
        counts = Counter(merged_df[col])
        total = len(merged_df)
        lines.append(f"Position {pos:2d}:")
        for aa, count in counts.most_common():
            lines.append(f"  {aa}: {count:2d} ({100.0*count/total:5.1f}%)")
    lines.append("")
    
    # Correlation 1: FR4 variants vs CDR3 length
    lines.append("## 2. FR4 Variants vs CDR3 Length")
    lines.append("")
    
    for pos, col in [(1, "fr4_pos1"), (6, "fr4_pos6"), (10, "fr4_pos10"), (11, "fr4_pos11")]:
        lines.append(f"Position {pos} by CDR3 length category:")
        for cdr3_bin in ["short", "medium", "long", "very_long"]:
            sub = merged_df[merged_df["cdr3_length_bin"] == cdr3_bin]
            if sub.empty:
                continue
            from collections import Counter
            counts = Counter(sub[col])
            residues_str = ", ".join(f"{aa}:{c}" for aa, c in counts.most_common())
            lines.append(f"  {cdr3_bin:10s} (n={len(sub):2d}): {residues_str}")
        lines.append("")
    
    # Check statistical association between FR4 pos1 (most variable) and CDR3 length
    lines.append("Statistical test: FR4 position 1 (W/R/S) vs CDR3 length")
    pos1_w = merged_df[merged_df["fr4_pos1"] == "W"]["h3_length"].tolist()
    pos1_r = merged_df[merged_df["fr4_pos1"] == "R"]["h3_length"].tolist()
    pos1_s = merged_df[merged_df["fr4_pos1"] == "S"]["h3_length"].tolist()
    
    if pos1_w and pos1_r:
        from scipy import stats
        stat, pval = stats.mannwhitneyu(pos1_w, pos1_r, alternative="two-sided")
        lines.append(f"  W (median CDR3={np.median(pos1_w):.0f}aa) vs R (median CDR3={np.median(pos1_r):.0f}aa): p={pval:.4f}")
    if pos1_w and pos1_s:
        stat, pval = stats.mannwhitneyu(pos1_w, pos1_s, alternative="two-sided")
        lines.append(f"  W (median CDR3={np.median(pos1_w):.0f}aa) vs S (median CDR3={np.median(pos1_s):.0f}aa): p={pval:.4f}")
    lines.append("")
    
    # Correlation 2: FR4 variants vs CDR2 canonical fold
    lines.append("## 3. FR4 Variants vs CDR2 Canonical Fold (H2-9-1 vs H2-10-1)")
    lines.append("")
    
    for pos, col in [(1, "fr4_pos1"), (6, "fr4_pos6"), (10, "fr4_pos10"), (11, "fr4_pos11")]:
        lines.append(f"Position {pos} by CDR2 fold:")
        for h2_class in merged_df["h2_class"].dropna().unique():
            sub = merged_df[merged_df["h2_class"] == h2_class]
            if sub.empty:
                continue
            from collections import Counter
            counts = Counter(sub[col])
            residues_str = ", ".join(f"{aa}:{c}" for aa, c in counts.most_common())
            lines.append(f"  {h2_class:10s} (n={len(sub):2d}): {residues_str}")
        lines.append("")
    
    # Correlation 3: FR4 variants vs humanization strategy
    lines.append("## 4. FR4 Variants vs Humanization Strategy")
    lines.append("")
    
    for pos, col in [(1, "fr4_pos1"), (6, "fr4_pos6"), (10, "fr4_pos10"), (11, "fr4_pos11")]:
        lines.append(f"Position {pos} by strategy:")
        for strategy in ["BM", "SR", "Native"]:
            sub = merged_df[merged_df["strategy_group"] == strategy]
            if sub.empty:
                continue
            from collections import Counter
            counts = Counter(sub[col])
            residues_str = ", ".join(f"{aa}:{c}" for aa, c in counts.most_common())
            lines.append(f"  {strategy:6s} (n={len(sub):2d}): {residues_str}")
        lines.append("")
    
    # Detailed molecule-by-molecule table
    lines.append("## 5. Individual Molecule FR4 Variant Profiles")
    lines.append("")
    lines.append("antibody_id           | CDR3_len | CDR2_fold | Strategy | FR4_pos1 | FR4_pos6 | FR4_pos10 | FR4_pos11 | FR4_full")
    lines.append("-" * 120)
    
    for _, row in merged_df.sort_values("h3_length").iterrows():
        lines.append(
            f"{row['antibody_id']:20s} | "
            f"{row['h3_length']:8d} | "
            f"{str(row['h2_class']):9s} | "
            f"{row['strategy_group']:8s} | "
            f"{row['fr4_pos1']:8s} | "
            f"{row['fr4_pos6']:8s} | "
            f"{row['fr4_pos10']:9s} | "
            f"{row['fr4_pos11']:9s} | "
            f"{row['fr4_sequence']}"
        )
    lines.append("")
    
    # Key findings
    lines.append("## 6. Key Findings")
    lines.append("")
    
    # Finding 1: CDR3 length correlation
    lines.append("1. FR4 variants vs CDR3 length:")
    
    # Check if short CDR3 molecules use different FR4 pos1
    short_cdr3 = merged_df[merged_df["cdr3_length_bin"] == "short"]
    long_cdr3 = merged_df[merged_df["cdr3_length_bin"].isin(["long", "very_long"])]
    
    from collections import Counter
    short_pos1 = Counter(short_cdr3["fr4_pos1"])
    long_pos1 = Counter(long_cdr3["fr4_pos1"])
    
    lines.append(f"   - Short CDR3 (≤10aa, n={len(short_cdr3)}): {dict(short_pos1)}")
    lines.append(f"   - Long CDR3 (≥16aa, n={len(long_cdr3)}): {dict(long_pos1)}")
    
    if short_pos1.most_common(1)[0][0] != long_pos1.most_common(1)[0][0]:
        lines.append(f"   → SHORT and LONG CDR3 use DIFFERENT FR4 position 1 residues!")
    else:
        lines.append(f"   → No clear correlation between FR4 variants and CDR3 length")
    lines.append("")
    
    # Finding 2: CDR2 fold correlation
    lines.append("2. FR4 variants vs CDR2 canonical fold:")
    
    h2_9_1 = merged_df[merged_df["h2_class"] == "H2-9-1"]
    h2_10_1 = merged_df[merged_df["h2_class"] == "H2-10-1"]
    
    if not h2_9_1.empty and not h2_10_1.empty:
        h2_9_1_pos1 = Counter(h2_9_1["fr4_pos1"])
        h2_10_1_pos1 = Counter(h2_10_1["fr4_pos1"])
        
        lines.append(f"   - H2-9-1 (n={len(h2_9_1)}): {dict(h2_9_1_pos1)}")
        lines.append(f"   - H2-10-1 (n={len(h2_10_1)}): {dict(h2_10_1_pos1)}")
        
        if h2_9_1_pos1.most_common(1)[0][0] != h2_10_1_pos1.most_common(1)[0][0]:
            lines.append(f"   → H2-9-1 and H2-10-1 use DIFFERENT FR4 variants!")
        else:
            lines.append(f"   → No correlation between CDR2 fold and FR4 variants")
    lines.append("")
    
    # Finding 3: Strategy correlation
    lines.append("3. FR4 variants vs humanization strategy:")
    
    bm_pos1 = Counter(merged_df[merged_df["strategy_group"] == "BM"]["fr4_pos1"])
    sr_pos1 = Counter(merged_df[merged_df["strategy_group"] == "SR"]["fr4_pos1"])
    native_pos1 = Counter(merged_df[merged_df["strategy_group"] == "Native"]["fr4_pos1"])
    
    lines.append(f"   - BM: {dict(bm_pos1)}")
    lines.append(f"   - SR: {dict(sr_pos1)}")
    lines.append(f"   - Native: {dict(native_pos1)}")
    
    if len(set([bm_pos1.most_common(1)[0][0], sr_pos1.most_common(1)[0][0], native_pos1.most_common(1)[0][0]])) > 1:
        lines.append(f"   → Strategies use DIFFERENT FR4 variants!")
    else:
        lines.append(f"   → No correlation between strategy and FR4 variants")
    lines.append("")
    
    # Final verdict
    lines.append("## 7. FINAL VERDICT")
    lines.append("")
    
    # Check strongest correlation
    pos1_w_cdr3 = merged_df[merged_df["fr4_pos1"] == "W"]["h3_length"]
    pos1_non_w_cdr3 = merged_df[merged_df["fr4_pos1"] != "W"]["h3_length"]
    
    if not pos1_w_cdr3.empty and not pos1_non_w_cdr3.empty:
        from scipy import stats
        stat, pval = stats.mannwhitneyu(pos1_w_cdr3, pos1_non_w_cdr3, alternative="two-sided")
        
        lines.append(f"Statistical analysis: FR4 position 1 (W vs non-W) vs CDR3 length")
        lines.append(f"  - W residues (n={len(pos1_w_cdr3)}): median CDR3 = {pos1_w_cdr3.median():.0f}aa")
        lines.append(f"  - Non-W residues (n={len(pos1_non_w_cdr3)}): median CDR3 = {pos1_non_w_cdr3.median():.0f}aa")
        lines.append(f"  - Mann-Whitney U test: p = {pval:.4f}")
        lines.append("")
        
        if pval < 0.05:
            lines.append("✓ SIGNIFICANT CORRELATION DETECTED!")
            lines.append("")
            if pos1_w_cdr3.median() > pos1_non_w_cdr3.median():
                lines.append("Conclusion:")
                lines.append("  FR4 position 1 = W is associated with LONGER CDR3 loops.")
                lines.append("  FR4 position 1 = R/S is associated with SHORTER CDR3 loops.")
            else:
                lines.append("Conclusion:")
                lines.append("  FR4 position 1 = W is associated with SHORTER CDR3 loops.")
                lines.append("  FR4 position 1 = R/S is associated with LONGER CDR3 loops.")
            lines.append("")
            lines.append("Interpretation:")
            lines.append("  FR4 position 1 (first residue after CDR3) ADAPTS to CDR3 length.")
            lines.append("  This suggests junction optimization for different CDR3 loop sizes.")
        else:
            lines.append("✗ NO SIGNIFICANT CORRELATION")
            lines.append("")
            lines.append("Conclusion:")
            lines.append("  FR4 sequence variants are NOT systematically driven by:")
            lines.append("    - CDR3 length")
            lines.append("    - CDR2 canonical fold")
            lines.append("    - Humanization strategy")
            lines.append("")
            lines.append("Interpretation:")
            lines.append("  FR4 variations are likely due to:")
            lines.append("    a) Individual molecule-specific optimization")
            lines.append("    b) Manufacturing/expression constraints")
            lines.append("    c) Developer preferences")
            lines.append("    d) Random evolutionary drift")
    
    lines.append("")
    lines.append("=" * 80)
    
    return lines


def main() -> None:
    fr4_cdr3_df = pd.read_csv(IN_FR4_CDR3)
    
    # FR4_CDR3_data.csv already has h2_class and strategy_group
    merged = fr4_cdr3_df.copy()
    
    # Extract FR4 variable positions
    fr4_positions = merged["fr4_sequence"].apply(extract_fr4_positions).apply(pd.Series)
    merged = pd.concat([merged, fr4_positions], axis=1)
    
    # Classify CDR3 length
    merged["cdr3_length_bin"] = merged["h3_length"].apply(classify_cdr3_length)
    
    # Save detailed table
    merged.to_csv(OUT_TABLE, index=False)
    print(f"Wrote: {OUT_TABLE}")
    
    # Build report
    report_lines = build_report(merged)
    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Wrote: {OUT_REPORT}")


if __name__ == "__main__":
    main()
