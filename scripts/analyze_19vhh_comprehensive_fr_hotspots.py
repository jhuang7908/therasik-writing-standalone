"""
Comprehensive analysis: FR germline, VHH hallmarks, Vernier zones vs CDR conformations.

Integrates multiple structural features:
  1. FR germline identity (best human/camelid match per FR region)
  2. VHH hallmark positions (IMGT 37, 44, 45, 47 in FR2)
  3. Vernier zone hot spots (CDR-contacting FR residues)
  4. CDR2 canonical fold (H2-9-1 vs H2-10-1)
  5. CDR3 length (5-21aa)
  6. Humanization strategy (BM/SR/Native)

Vernier zone positions (IMGT numbering):
  - FR1: 2, 4 (L/F variants)
  - FR2: 37, 47, 48 (hallmark overlap)
  - FR3: 66, 67, 68, 71, 78, 93, 94 (CDR3-contacting)
  - FR4: (no major Vernier positions)

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_regional_identity.csv
  - paper/raw data/TheraSAbDab_19VHH_ANARCII_numbering_full.csv
  - paper/raw data/TheraSAbDab_19VHH_FR4_CDR3_data.csv

Outputs:
  - paper/raw data/TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv
  - paper/raw data/TheraSAbDab_19VHH_FR_hotspots_correlation_report.txt
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent

IN_FR_REGIONAL = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_regional_identity.csv"
IN_NUMBERING = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_ANARCII_numbering_full.csv"
IN_FR4_CDR3 = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR4_CDR3_data.csv"

OUT_DIR = PROJECT_ROOT / "paper" / "raw data"
OUT_TABLE = OUT_DIR / "TheraSAbDab_19VHH_comprehensive_FR_hotspots.csv"
OUT_REPORT = OUT_DIR / "TheraSAbDab_19VHH_FR_hotspots_correlation_report.txt"


# VHH hallmark positions (IMGT numbering, in FR2)
HALLMARK_POSITIONS = {
    37: {"human": ["E", "Q"], "camelid": ["F", "Y"]},
    44: {"human": ["G"], "camelid": ["E"]},
    45: {"human": ["L"], "camelid": ["C", "R"]},
    47: {"human": ["W"], "camelid": ["G", "F"]},
}

# Vernier zone positions (IMGT numbering, CDR-contacting residues)
VERNIER_POSITIONS = {
    "FR1": [2, 4, 27, 28, 30],
    "FR2": [47, 48],  # 37 is hallmark, included separately
    "FR3": [66, 67, 68, 71, 78, 82, 83, 84, 87, 89, 91, 93, 94],
}


def parse_imgt_pos(label: str) -> int:
    """Parse IMGT position label to integer."""
    if not label:
        return 0
    m = re.match(r"^(\d+)", str(label).strip())
    return int(m.group(1)) if m else 0


def extract_residues_at_positions(numbering_df: pd.DataFrame, positions: list[int]) -> pd.DataFrame:
    """Extract residues at specified IMGT positions for all antibodies."""
    records = []
    for ab_id in numbering_df["antibody_id"].unique():
        sub = numbering_df[numbering_df["antibody_id"] == ab_id].copy()
        sub["imgt_pos_num"] = sub["imgt_position"].apply(parse_imgt_pos)
        
        residue_data = {"antibody_id": ab_id}
        for pos in positions:
            residue_row = sub[sub["imgt_pos_num"] == pos]
            if not residue_row.empty:
                residue_data[f"pos_{pos}"] = residue_row.iloc[0]["aa"]
            else:
                residue_data[f"pos_{pos}"] = "-"
        records.append(residue_data)
    
    return pd.DataFrame(records)


def classify_hallmark_residue(residue: str, pos: int) -> str:
    """Classify a hallmark residue as human, camelid, or other."""
    if pos not in HALLMARK_POSITIONS:
        return "unknown"
    if residue in HALLMARK_POSITIONS[pos]["human"]:
        return "human"
    elif residue in HALLMARK_POSITIONS[pos]["camelid"]:
        return "camelid"
    else:
        return "other"


def compute_hallmark_score(row: pd.Series) -> dict:
    """Compute hallmark humanization score (0-4, higher = more human)."""
    human_count = sum(1 for pos in [37, 44, 45, 47] if classify_hallmark_residue(row[f"pos_{pos}"], pos) == "human")
    camelid_count = sum(1 for pos in [37, 44, 45, 47] if classify_hallmark_residue(row[f"pos_{pos}"], pos) == "camelid")
    return {
        "hallmark_human_count": human_count,
        "hallmark_camelid_count": camelid_count,
        "hallmark_classification": "human-like" if human_count > camelid_count else "camelid-like" if camelid_count > human_count else "hybrid",
    }


def build_comprehensive_table(
    fr_regional_df: pd.DataFrame,
    numbering_df: pd.DataFrame,
    fr4_cdr3_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build comprehensive table with all FR features."""
    
    # Start with FR regional identity
    merged = fr_regional_df.copy()
    
    # Add CDR3 data (drop duplicate columns from FR regional data first)
    if "strategy_group" in merged.columns:
        merged = merged.drop(columns=["strategy_group"])
    if "h2_class" in merged.columns:
        merged = merged.drop(columns=["h2_class"])
    
    merged = merged.merge(
        fr4_cdr3_df[["antibody_id", "h3_length", "h3_sequence", "strategy_group", "h2_class"]],
        on="antibody_id",
        how="left"
    )
    
    # Extract hallmark positions
    hallmark_positions = [37, 44, 45, 47]
    hallmark_df = extract_residues_at_positions(numbering_df, hallmark_positions)
    merged = merged.merge(hallmark_df, on="antibody_id", how="left")
    
    # Compute hallmark scores
    hallmark_scores = merged.apply(compute_hallmark_score, axis=1).apply(pd.Series)
    merged = pd.concat([merged, hallmark_scores], axis=1)
    
    # Extract Vernier zone positions
    all_vernier_positions = sorted(set(
        VERNIER_POSITIONS["FR1"] + VERNIER_POSITIONS["FR2"] + VERNIER_POSITIONS["FR3"]
    ))
    vernier_df = extract_residues_at_positions(numbering_df, all_vernier_positions)
    merged = merged.merge(vernier_df, on="antibody_id", how="left")
    
    # Classify CDR3 length
    merged["cdr3_length_bin"] = pd.cut(
        merged["h3_length"],
        bins=[0, 10, 15, 20, 100],
        labels=["short", "medium", "long", "very_long"]
    )
    
    # Add best germline classification
    merged["fr1_germline_type"] = merged.apply(
        lambda row: "human" if row["fr1_human_pct"] > row["fr1_vicugna_pct"] + 5 
        else "camelid" if row["fr1_vicugna_pct"] > row["fr1_human_pct"] + 5
        else "shared",
        axis=1
    )
    
    merged["fr2_germline_type"] = merged.apply(
        lambda row: "human" if row["fr2_human_pct"] > row["fr2_vicugna_pct"] + 5
        else "camelid" if row["fr2_vicugna_pct"] > row["fr2_human_pct"] + 5
        else "shared",
        axis=1
    )
    
    merged["fr3_germline_type"] = merged.apply(
        lambda row: "human" if row["fr3_human_pct"] > row["fr3_vicugna_pct"] + 5
        else "camelid" if row["fr3_vicugna_pct"] > row["fr3_human_pct"] + 5
        else "shared",
        axis=1
    )
    
    merged["fr4_germline_type"] = merged.apply(
        lambda row: "human" if row["fr4_human_pct"] > row["fr4_vicugna_pct"] + 5
        else "camelid" if row["fr4_vicugna_pct"] > row["fr4_human_pct"] + 5
        else "shared",
        axis=1
    )
    
    return merged


def build_correlation_report(merged_df: pd.DataFrame) -> list[str]:
    """Build comprehensive correlation report."""
    lines = []
    lines.append("=" * 100)
    lines.append("Comprehensive FR Analysis: Germlines, Hallmarks, Vernier Zones vs CDR Conformations")
    lines.append("=" * 100)
    lines.append("")
    lines.append("Questions:")
    lines.append("  1. Do FR germline frameworks correlate with CDR2 fold or CDR3 length?")
    lines.append("  2. Do VHH hallmark positions correlate with CDR conformations?")
    lines.append("  3. Do Vernier zone residues adapt to different CDR structures?")
    lines.append("")
    
    # Section 1: FR Germline Type Distribution
    lines.append("## 1. FR Germline Type Distribution")
    lines.append("")
    
    for fr in ["fr1", "fr2", "fr3", "fr4"]:
        from collections import Counter
        germline_counts = Counter(merged_df[f"{fr}_germline_type"])
        lines.append(f"{fr.upper()} germline type:")
        for gtype, count in germline_counts.most_common():
            lines.append(f"  {gtype}: {count} ({100.0*count/len(merged_df):.1f}%)")
    lines.append("")
    
    # Section 2: FR Germline vs CDR2 Canonical Fold
    lines.append("## 2. FR Germline Type vs CDR2 Canonical Fold")
    lines.append("")
    
    for fr in ["fr1", "fr2", "fr3", "fr4"]:
        lines.append(f"{fr.upper()} germline by CDR2 fold:")
        for h2_class in ["H2-9-1", "H2-10-1"]:
            sub = merged_df[merged_df["h2_class"] == h2_class]
            if sub.empty:
                continue
            from collections import Counter
            germline_counts = Counter(sub[f"{fr}_germline_type"])
            germline_str = ", ".join(f"{g}:{c}" for g, c in germline_counts.most_common())
            lines.append(f"  {h2_class}: {germline_str}")
        lines.append("")
    
    # Section 3: FR Germline vs CDR3 Length
    lines.append("## 3. FR Germline Type vs CDR3 Length")
    lines.append("")
    
    for fr in ["fr1", "fr2", "fr3", "fr4"]:
        lines.append(f"{fr.upper()} germline by CDR3 length:")
        for cdr3_bin in ["short", "medium", "long", "very_long"]:
            sub = merged_df[merged_df["cdr3_length_bin"] == cdr3_bin]
            if sub.empty:
                continue
            from collections import Counter
            germline_counts = Counter(sub[f"{fr}_germline_type"])
            germline_str = ", ".join(f"{g}:{c}" for g, c in germline_counts.most_common())
            lines.append(f"  {cdr3_bin:10s} (n={len(sub):2d}): {germline_str}")
        lines.append("")
    
    # Section 4: VHH Hallmark Analysis
    lines.append("## 4. VHH Hallmark Positions vs CDR Conformations")
    lines.append("")
    
    lines.append("Hallmark humanization score by CDR2 fold:")
    for h2_class in ["H2-9-1", "H2-10-1"]:
        sub = merged_df[merged_df["h2_class"] == h2_class]
        if sub.empty:
            continue
        median_human = sub["hallmark_human_count"].median()
        median_camelid = sub["hallmark_camelid_count"].median()
        lines.append(f"  {h2_class}: {median_human:.1f}H / {median_camelid:.1f}C (median)")
    lines.append("")
    
    lines.append("Hallmark humanization score by CDR3 length:")
    for cdr3_bin in ["short", "medium", "long", "very_long"]:
        sub = merged_df[merged_df["cdr3_length_bin"] == cdr3_bin]
        if sub.empty:
            continue
        median_human = sub["hallmark_human_count"].median()
        median_camelid = sub["hallmark_camelid_count"].median()
        lines.append(f"  {cdr3_bin:10s} (n={len(sub):2d}): {median_human:.1f}H / {median_camelid:.1f}C")
    lines.append("")
    
    lines.append("Hallmark humanization score by strategy:")
    for strategy in ["BM", "SR", "Native"]:
        sub = merged_df[merged_df["strategy_group"] == strategy]
        if sub.empty:
            continue
        median_human = sub["hallmark_human_count"].median()
        median_camelid = sub["hallmark_camelid_count"].median()
        lines.append(f"  {strategy}: {median_human:.1f}H / {median_camelid:.1f}C")
    lines.append("")
    
    # Section 5: Vernier Zone Hotspots
    lines.append("## 5. Vernier Zone Residue Conservation")
    lines.append("")
    
    vernier_pos_list = sorted(set(
        VERNIER_POSITIONS["FR1"] + VERNIER_POSITIONS["FR2"] + VERNIER_POSITIONS["FR3"]
    ))
    
    lines.append("Conservation at Vernier zone positions:")
    for pos in vernier_pos_list[:10]:  # Show first 10
        col = f"pos_{pos}"
        if col not in merged_df.columns:
            continue
        from collections import Counter
        residue_counts = Counter(merged_df[col])
        if len(residue_counts) == 1 and "-" in residue_counts:
            continue
        total = len(merged_df)
        most_common, most_count = residue_counts.most_common(1)[0]
        conservation_pct = 100.0 * most_count / total
        variants_str = ", ".join(f"{aa}:{c}" for aa, c in residue_counts.most_common()[:3])
        lines.append(f"  IMGT {pos:3d}: {most_common} ({conservation_pct:.0f}%) | {variants_str}")
    lines.append(f"  ... ({len(vernier_pos_list)-10} more Vernier positions)")
    lines.append("")
    
    # Section 6: Key Findings
    lines.append("## 6. Key Correlation Findings")
    lines.append("")
    
    # Finding 1: FR1 germline universality
    fr1_shared = (merged_df["fr1_germline_type"] == "shared").sum()
    lines.append(f"1. FR1 germline framework:")
    lines.append(f"   - {fr1_shared}/{len(merged_df)} molecules have 'shared' FR1 (human = camelid)")
    if fr1_shared / len(merged_df) > 0.8:
        lines.append(f"   → FR1 is EVOLUTIONARILY CONSERVED across species")
    lines.append("")
    
    # Finding 2: Hallmark vs CDR2 fold
    h2_9_1_hallmarks = merged_df[merged_df["h2_class"] == "H2-9-1"]["hallmark_human_count"]
    h2_10_1_hallmarks = merged_df[merged_df["h2_class"] == "H2-10-1"]["hallmark_human_count"]
    
    if not h2_9_1_hallmarks.empty and not h2_10_1_hallmarks.empty:
        from scipy import stats
        stat, pval = stats.mannwhitneyu(h2_9_1_hallmarks, h2_10_1_hallmarks, alternative="two-sided")
        lines.append(f"2. VHH hallmarks vs CDR2 fold:")
        lines.append(f"   - H2-9-1: {h2_9_1_hallmarks.median():.1f} human hallmarks (median)")
        lines.append(f"   - H2-10-1: {h2_10_1_hallmarks.median():.1f} human hallmarks (median)")
        lines.append(f"   - Mann-Whitney U test: p = {pval:.4f}")
        if pval < 0.05:
            lines.append(f"   → SIGNIFICANT correlation: CDR2 fold predicts hallmark humanization!")
        else:
            lines.append(f"   → No correlation between CDR2 fold and hallmark humanization")
    lines.append("")
    
    # Finding 3: Hallmark vs CDR3 length
    short_hallmarks = merged_df[merged_df["cdr3_length_bin"] == "short"]["hallmark_human_count"]
    long_hallmarks = merged_df[merged_df["cdr3_length_bin"].isin(["long", "very_long"])]["hallmark_human_count"]
    
    if not short_hallmarks.empty and not long_hallmarks.empty:
        stat, pval = stats.mannwhitneyu(short_hallmarks, long_hallmarks, alternative="two-sided")
        lines.append(f"3. VHH hallmarks vs CDR3 length:")
        lines.append(f"   - Short CDR3 (≤10aa): {short_hallmarks.median():.1f} human hallmarks")
        lines.append(f"   - Long CDR3 (≥16aa): {long_hallmarks.median():.1f} human hallmarks")
        lines.append(f"   - Mann-Whitney U test: p = {pval:.4f}")
        if pval < 0.05:
            lines.append(f"   → SIGNIFICANT correlation: CDR3 length predicts hallmark humanization!")
        else:
            lines.append(f"   → No correlation between CDR3 length and hallmark humanization")
    lines.append("")
    
    # Section 7: Individual Molecule Summary
    lines.append("## 7. Individual Molecule Profiles (sorted by CDR3 length)")
    lines.append("")
    lines.append("antibody_id      | CDR3 | H2_fold | FR1_germ | FR2_germ | FR3_germ | FR4_germ | Hallmark | Strategy")
    lines.append("-" * 110)
    
    for _, row in merged_df.sort_values("h3_length").iterrows():
        lines.append(
            f"{row['antibody_id']:15s} | "
            f"{row['h3_length']:4d} | "
            f"{str(row['h2_class']):7s} | "
            f"{row['fr1_germline_type']:8s} | "
            f"{row['fr2_germline_type']:8s} | "
            f"{row['fr3_germline_type']:8s} | "
            f"{row['fr4_germline_type']:8s} | "
            f"{row['hallmark_human_count']:.0f}H/{row['hallmark_camelid_count']:.0f}C    | "
            f"{row['strategy_group']}"
        )
    lines.append("")
    
    # Final Summary
    lines.append("## 8. COMPREHENSIVE SUMMARY")
    lines.append("")
    lines.append("Framework germline usage:")
    for fr in ["fr1", "fr2", "fr3", "fr4"]:
        germline_counts = Counter(merged_df[f"{fr}_germline_type"])
        dominant = germline_counts.most_common(1)[0]
        lines.append(f"  {fr.upper()}: {dominant[0]} ({100.0*dominant[1]/len(merged_df):.0f}%)")
    lines.append("")
    
    lines.append("VHH hallmark patterns:")
    camelid_like = (merged_df["hallmark_classification"] == "camelid-like").sum()
    human_like = (merged_df["hallmark_classification"] == "human-like").sum()
    lines.append(f"  Camelid-like: {camelid_like}/{len(merged_df)} ({100.0*camelid_like/len(merged_df):.0f}%)")
    lines.append(f"  Human-like: {human_like}/{len(merged_df)} ({100.0*human_like/len(merged_df):.0f}%)")
    lines.append("")
    
    lines.append("=" * 100)
    
    return lines


def main() -> None:
    fr_regional_df = pd.read_csv(IN_FR_REGIONAL)
    numbering_df = pd.read_csv(IN_NUMBERING)
    fr4_cdr3_df = pd.read_csv(IN_FR4_CDR3)
    
    print("Building comprehensive FR hotspot table...")
    comprehensive_df = build_comprehensive_table(fr_regional_df, numbering_df, fr4_cdr3_df)
    
    comprehensive_df.to_csv(OUT_TABLE, index=False)
    print(f"Wrote: {OUT_TABLE}")
    
    print("Building correlation report...")
    report_lines = build_correlation_report(comprehensive_df)
    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Wrote: {OUT_REPORT}")


if __name__ == "__main__":
    main()
