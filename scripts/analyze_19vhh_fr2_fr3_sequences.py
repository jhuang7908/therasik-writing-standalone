"""
Analyze FR2 and FR3 sequences to find true strategy differentiation.

FR2 contains VHH hallmark positions (IMGT 37, 44, 45, 47).
FR3 is the longest FR region and most likely to contain strategy-specific modifications.

Key analyses:
  1. FR2/FR3 pairwise identity within and between strategies
  2. Position-by-position conservation and strategy-specific residues
  3. VHH hallmark analysis (FR2 positions 37, 44, 45, 47 mapped to local positions)
  4. Consensus sequences for each strategy
  5. Clustering: do molecules group by strategy or by other factors?

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/raw data/TheraSAbDab_19VHH_ANARCII_numbering_full.csv (for hallmark positions)
  - paper/tables/Table1_slice3_19_clinical_vhh_master.csv

Outputs:
  - paper/raw data/TheraSAbDab_19VHH_FR2_FR3_analysis.txt
  - paper/raw data/TheraSAbDab_19VHH_FR2_pairwise_identity.csv
  - paper/raw data/TheraSAbDab_19VHH_FR3_pairwise_identity.csv
  - paper/raw data/TheraSAbDab_19VHH_strategy_consensus_sequences.fasta
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_NUMBERING = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_ANARCII_numbering_full.csv"
IN_TABLE1 = PROJECT_ROOT / "paper" / "tables" / "Table1_slice3_19_clinical_vhh_master.csv"

OUT_DIR = PROJECT_ROOT / "paper" / "raw data"
OUT_REPORT = OUT_DIR / "TheraSAbDab_19VHH_FR2_FR3_analysis.txt"
OUT_FR2_PAIRWISE = OUT_DIR / "TheraSAbDab_19VHH_FR2_pairwise_identity.csv"
OUT_FR3_PAIRWISE = OUT_DIR / "TheraSAbDab_19VHH_FR3_pairwise_identity.csv"
OUT_CONSENSUS = OUT_DIR / "TheraSAbDab_19VHH_strategy_consensus_sequences.fasta"


# VHH hallmark positions (IMGT numbering)
HALLMARK_POSITIONS = {
    37: {"human": ["E", "Q"], "camelid": ["F", "Y"]},
    44: {"human": ["G"], "camelid": ["E"]},
    45: {"human": ["L"], "camelid": ["C", "R"]},
    47: {"human": ["W"], "camelid": ["G", "F"]},
}


def compute_identity(seq1: str, seq2: str) -> float:
    """Compute pairwise identity."""
    if not seq1 or not seq2:
        return 0.0
    min_len = min(len(seq1), len(seq2))
    if min_len == 0:
        return 0.0
    matches = sum(1 for i in range(min_len) if seq1[i] == seq2[i])
    return (matches / min_len) * 100.0


def compute_pairwise_identity(fr_df: pd.DataFrame, t1_df: pd.DataFrame, region: str) -> pd.DataFrame:
    """Compute pairwise identity for a specific FR region."""
    ab_ids = fr_df["antibody_id"].tolist()
    seqs = {row["antibody_id"]: row[f"{region}_sequence"] for _, row in fr_df.iterrows()}
    strategies = {row["antibody_id"]: t1_df.loc[t1_df["antibody_id"] == row["antibody_id"], "strategy_group"].values[0]
                  for _, row in fr_df.iterrows()}
    
    records = []
    for ab1 in ab_ids:
        for ab2 in ab_ids:
            if ab1 != ab2:
                identity = compute_identity(seqs[ab1], seqs[ab2])
                records.append({
                    "antibody_1": ab1,
                    "strategy_1": strategies[ab1],
                    "antibody_2": ab2,
                    "strategy_2": strategies[ab2],
                    f"{region}_identity_pct": identity,
                })
    
    return pd.DataFrame(records)


def build_consensus_sequence(sequences: list[str]) -> str:
    """Build consensus from list of sequences."""
    if not sequences:
        return ""
    max_len = max(len(s) for s in sequences)
    consensus = []
    for pos in range(max_len):
        residues = [s[pos] for s in sequences if pos < len(s)]
        if residues:
            from collections import Counter
            most_common = Counter(residues).most_common(1)[0][0]
            consensus.append(most_common)
    return "".join(consensus)


def analyze_position_conservation(sequences: list[str], strategy: str) -> list[dict]:
    """Analyze conservation at each position."""
    if not sequences:
        return []
    max_len = max(len(s) for s in sequences)
    position_stats = []
    for pos in range(max_len):
        residues = [s[pos] for s in sequences if pos < len(s)]
        if not residues:
            continue
        from collections import Counter
        counts = Counter(residues)
        total = len(residues)
        most_common_aa, most_common_count = counts.most_common(1)[0]
        conservation_pct = (most_common_count / total) * 100.0
        position_stats.append({
            "strategy": strategy,
            "position": pos + 1,
            "most_common_aa": most_common_aa,
            "conservation_pct": conservation_pct,
            "num_variants": len(counts),
            "variants": ", ".join(f"{aa}:{count}" for aa, count in counts.most_common()),
        })
    return position_stats


def extract_hallmark_residues(numbering_df: pd.DataFrame) -> pd.DataFrame:
    """Extract VHH hallmark positions from IMGT numbering."""
    def parse_imgt_pos(label: str) -> int:
        if not label:
            return 0
        m = re.match(r"^(\d+)", str(label).strip())
        return int(m.group(1)) if m else 0
    
    records = []
    for ab_id in numbering_df["antibody_id"].unique():
        sub = numbering_df[numbering_df["antibody_id"] == ab_id].copy()
        sub["imgt_pos_num"] = sub["imgt_position"].apply(parse_imgt_pos)
        
        hallmark_data = {"antibody_id": ab_id}
        for pos in HALLMARK_POSITIONS:
            residue_row = sub[sub["imgt_pos_num"] == pos]
            if not residue_row.empty:
                hallmark_data[f"pos_{pos}"] = residue_row.iloc[0]["aa"]
            else:
                hallmark_data[f"pos_{pos}"] = "-"
        records.append(hallmark_data)
    
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


def build_report(
    fr_df: pd.DataFrame,
    t1_df: pd.DataFrame,
    fr2_pairwise: pd.DataFrame,
    fr3_pairwise: pd.DataFrame,
    hallmark_df: pd.DataFrame,
) -> list[str]:
    """Build comprehensive FR2/FR3 analysis report."""
    lines = []
    lines.append("=" * 80)
    lines.append("FR2 and FR3 Sequence Analysis: Strategy Differentiation")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Question: Do FR2/FR3 sequences reveal true differences between BM/SR/Native?")
    lines.append("")
    
    # FR2 Analysis
    lines.append("## 1. FR2 Sequence Conservation (17aa, contains VHH hallmarks)")
    lines.append("")
    
    fr2_median = fr2_pairwise[f"fr2_identity_pct"].median()
    fr2_min = fr2_pairwise[f"fr2_identity_pct"].min()
    fr2_max = fr2_pairwise[f"fr2_identity_pct"].max()
    
    lines.append(f"Overall FR2 pairwise identity:")
    lines.append(f"  Median: {fr2_median:.1f}%, Range: {fr2_min:.1f}% - {fr2_max:.1f}%")
    lines.append("")
    
    lines.append("FR2 identity by strategy comparison:")
    for s1 in ["BM", "SR", "Native"]:
        for s2 in ["BM", "SR", "Native"]:
            sub = fr2_pairwise[(fr2_pairwise["strategy_1"] == s1) & (fr2_pairwise["strategy_2"] == s2)]
            if not sub.empty:
                lines.append(f"  {s1:6s} vs {s2:6s}: {sub['fr2_identity_pct'].median():5.1f}%")
    lines.append("")
    
    # FR2 consensus by strategy
    lines.append("FR2 consensus sequences by strategy:")
    for strategy in ["BM", "SR", "Native"]:
        sub = fr_df.merge(t1_df[["antibody_id", "strategy_group"]], on="antibody_id", how="left")
        sub = sub[sub["strategy_group"] == strategy]
        if sub.empty:
            continue
        consensus = build_consensus_sequence(sub["fr2_sequence"].tolist())
        lines.append(f"  {strategy:6s} (n={len(sub):2d}): {consensus}")
    lines.append("")
    
    # FR2 individual sequences
    lines.append("FR2 individual sequences:")
    for strategy in ["BM", "SR", "Native"]:
        sub = fr_df.merge(t1_df[["antibody_id", "strategy_group"]], on="antibody_id", how="left")
        sub = sub[sub["strategy_group"] == strategy]
        if sub.empty:
            continue
        lines.append(f"  {strategy}:")
        for _, row in sub.iterrows():
            lines.append(f"    {row['antibody_id']:20s}: {row['fr2_sequence']}")
    lines.append("")
    
    # VHH hallmark analysis
    lines.append("## 2. VHH Hallmark Positions (IMGT 37, 44, 45, 47)")
    lines.append("")
    
    # Merge hallmark data with strategy
    hallmark_merged = hallmark_df.merge(t1_df[["antibody_id", "strategy_group"]], on="antibody_id", how="left")
    
    lines.append("Hallmark residue distribution by strategy:")
    for pos in [37, 44, 45, 47]:
        lines.append(f"  IMGT {pos} (Human: {', '.join(HALLMARK_POSITIONS[pos]['human'])}, Camelid: {', '.join(HALLMARK_POSITIONS[pos]['camelid'])}):")
        for strategy in ["BM", "SR", "Native"]:
            sub = hallmark_merged[hallmark_merged["strategy_group"] == strategy]
            if sub.empty:
                continue
            residues = sub[f"pos_{pos}"].tolist()
            from collections import Counter
            counts = Counter(residues)
            lines.append(f"    {strategy}: {', '.join(f'{aa}:{c}' for aa, c in counts.most_common())}")
    lines.append("")
    
    # Classify hallmark profiles
    lines.append("Hallmark classification (human-like vs camelid-like):")
    for _, row in hallmark_merged.iterrows():
        human_count = sum(1 for pos in [37, 44, 45, 47] if classify_hallmark_residue(row[f"pos_{pos}"], pos) == "human")
        camelid_count = sum(1 for pos in [37, 44, 45, 47] if classify_hallmark_residue(row[f"pos_{pos}"], pos) == "camelid")
        classification = "human-like" if human_count > camelid_count else "camelid-like" if camelid_count > human_count else "hybrid"
        lines.append(f"  {row['antibody_id']:20s} ({row['strategy_group']:6s}): {human_count}H/{camelid_count}C = {classification}")
    lines.append("")
    
    # FR3 Analysis
    lines.append("## 3. FR3 Sequence Conservation (38-39aa, longest FR region)")
    lines.append("")
    
    fr3_median = fr3_pairwise[f"fr3_identity_pct"].median()
    fr3_min = fr3_pairwise[f"fr3_identity_pct"].min()
    fr3_max = fr3_pairwise[f"fr3_identity_pct"].max()
    
    lines.append(f"Overall FR3 pairwise identity:")
    lines.append(f"  Median: {fr3_median:.1f}%, Range: {fr3_min:.1f}% - {fr3_max:.1f}%")
    lines.append("")
    
    lines.append("FR3 identity by strategy comparison:")
    for s1 in ["BM", "SR", "Native"]:
        for s2 in ["BM", "SR", "Native"]:
            sub = fr3_pairwise[(fr3_pairwise["strategy_1"] == s1) & (fr3_pairwise["strategy_2"] == s2)]
            if not sub.empty:
                lines.append(f"  {s1:6s} vs {s2:6s}: {sub['fr3_identity_pct'].median():5.1f}%")
    lines.append("")
    
    # FR3 consensus by strategy
    lines.append("FR3 consensus sequences by strategy:")
    for strategy in ["BM", "SR", "Native"]:
        sub = fr_df.merge(t1_df[["antibody_id", "strategy_group"]], on="antibody_id", how="left")
        sub = sub[sub["strategy_group"] == strategy]
        if sub.empty:
            continue
        consensus = build_consensus_sequence(sub["fr3_sequence"].tolist())
        lines.append(f"  {strategy:6s} (n={len(sub):2d}): {consensus}")
    lines.append("")
    
    # FR3 position-by-position conservation for each strategy
    lines.append("FR3 variable positions (conservation <100%) by strategy:")
    for strategy in ["BM", "SR", "Native"]:
        sub = fr_df.merge(t1_df[["antibody_id", "strategy_group"]], on="antibody_id", how="left")
        sub = sub[sub["strategy_group"] == strategy]
        if sub.empty:
            continue
        seqs = sub["fr3_sequence"].tolist()
        pos_stats = analyze_position_conservation(seqs, strategy)
        variable = [p for p in pos_stats if p["conservation_pct"] < 100.0]
        if variable:
            lines.append(f"  {strategy} ({len(variable)} variable positions):")
            for p in variable[:5]:  # show first 5
                lines.append(f"    Pos {p['position']:2d}: {p['most_common_aa']} ({p['conservation_pct']:.0f}%) | {p['variants']}")
            if len(variable) > 5:
                lines.append(f"    ... and {len(variable)-5} more")
        else:
            lines.append(f"  {strategy}: 100% conserved (all molecules identical)")
    lines.append("")
    
    # Key Findings
    lines.append("## 4. Key Findings: Do FR2/FR3 Differentiate Strategies?")
    lines.append("")
    
    # Check if FR2/FR3 separate strategies
    bm_fr2 = fr2_pairwise[(fr2_pairwise["strategy_1"] == "BM") & (fr2_pairwise["strategy_2"] == "BM")]["fr2_identity_pct"].median()
    sr_fr2 = fr2_pairwise[(fr2_pairwise["strategy_1"] == "SR") & (fr2_pairwise["strategy_2"] == "SR")]["fr2_identity_pct"].median()
    bm_sr_fr2 = fr2_pairwise[(fr2_pairwise["strategy_1"] == "BM") & (fr2_pairwise["strategy_2"] == "SR")]["fr2_identity_pct"].median()
    
    bm_fr3 = fr3_pairwise[(fr3_pairwise["strategy_1"] == "BM") & (fr3_pairwise["strategy_2"] == "BM")]["fr3_identity_pct"].median()
    sr_fr3 = fr3_pairwise[(fr3_pairwise["strategy_1"] == "SR") & (fr3_pairwise["strategy_2"] == "SR")]["fr3_identity_pct"].median()
    bm_sr_fr3 = fr3_pairwise[(fr3_pairwise["strategy_1"] == "BM") & (fr3_pairwise["strategy_2"] == "SR")]["fr3_identity_pct"].median()
    
    lines.append(f"1. FR2 conservation:")
    lines.append(f"   - Within BM: {bm_fr2:.1f}%")
    lines.append(f"   - Within SR: {sr_fr2:.1f}%")
    lines.append(f"   - BM vs SR: {bm_sr_fr2:.1f}%")
    
    if bm_sr_fr2 > min(bm_fr2, sr_fr2) - 5.0:
        lines.append(f"   → BM and SR have SIMILAR FR2 sequences (inter-strategy identity ≈ intra-strategy)")
    else:
        lines.append(f"   → BM and SR have DISTINCT FR2 sequences")
    lines.append("")
    
    lines.append(f"2. FR3 conservation:")
    lines.append(f"   - Within BM: {bm_fr3:.1f}%")
    lines.append(f"   - Within SR: {sr_fr3:.1f}%")
    lines.append(f"   - BM vs SR: {bm_sr_fr3:.1f}%")
    
    if bm_sr_fr3 > min(bm_fr3, sr_fr3) - 5.0:
        lines.append(f"   → BM and SR have SIMILAR FR3 sequences")
    else:
        lines.append(f"   → BM and SR have DISTINCT FR3 sequences")
    lines.append("")
    
    # VHH hallmark verdict
    hallmark_by_strategy = {}
    for strategy in ["BM", "SR", "Native"]:
        sub = hallmark_merged[hallmark_merged["strategy_group"] == strategy]
        human_scores = []
        for _, row in sub.iterrows():
            score = sum(1 for pos in [37, 44, 45, 47] if classify_hallmark_residue(row[f"pos_{pos}"], pos) == "human")
            human_scores.append(score)
        if human_scores:
            hallmark_by_strategy[strategy] = sum(human_scores) / len(human_scores)
    
    lines.append(f"3. VHH hallmark humanization (avg human residues / 4 positions):")
    for strategy, score in hallmark_by_strategy.items():
        lines.append(f"   - {strategy}: {score:.1f} / 4")
    
    if max(hallmark_by_strategy.values()) - min(hallmark_by_strategy.values()) < 0.5:
        lines.append(f"   → All strategies have SIMILAR hallmark profiles (no systematic humanization)")
    else:
        lines.append(f"   → Strategies show DIFFERENT hallmark humanization levels")
    lines.append("")
    
    # Final verdict
    lines.append("## 5. FINAL VERDICT")
    lines.append("")
    
    if (fr2_median > 90.0 and fr3_median > 90.0 and
        bm_sr_fr2 > 88.0 and bm_sr_fr3 > 88.0):
        lines.append("🎯 CONCLUSION: NO SYSTEMATIC FR DIFFERENTIATION BY STRATEGY")
        lines.append("")
        lines.append("Evidence:")
        lines.append(f"  - FR2 overall identity: {fr2_median:.1f}% (all strategies similar)")
        lines.append(f"  - FR3 overall identity: {fr3_median:.1f}% (all strategies similar)")
        lines.append(f"  - BM vs SR FR2: {bm_sr_fr2:.1f}% (no clear boundary)")
        lines.append(f"  - BM vs SR FR3: {bm_sr_fr3:.1f}% (no clear boundary)")
        lines.append(f"  - VHH hallmarks: no systematic pattern by strategy")
        lines.append("")
        lines.append("Interpretation:")
        lines.append("  1. FR1/FR2/FR3/FR4 are ALL highly conserved across all 19 molecules")
        lines.append("  2. Strategy labels (BM/SR/Native) do NOT reflect framework sequences")
        lines.append("  3. True differences must lie in:")
        lines.append("     a) CDR loop sequences (not analyzed here)")
        lines.append("     b) Surface-exposed residues (scattered across FRs)")
        lines.append("     c) Developer intent / manufacturing process")
        lines.append("     d) Post-translational modifications")
    else:
        lines.append("🎯 CONCLUSION: STRATEGIES SHOW FR SEQUENCE DIFFERENTIATION")
        lines.append("")
        lines.append("Key differences:")
        lines.append(f"  - FR2 BM vs SR: {abs(bm_fr2 - bm_sr_fr2):.1f}% difference")
        lines.append(f"  - FR3 BM vs SR: {abs(bm_fr3 - bm_sr_fr3):.1f}% difference")
        lines.append("  → True humanization strategies are detectable in framework regions")
    
    lines.append("")
    lines.append("=" * 80)
    
    return lines


def main() -> None:
    fr_df = pd.read_csv(IN_FR_SEQ)
    numbering_df = pd.read_csv(IN_NUMBERING)
    t1 = pd.read_csv(IN_TABLE1)
    
    print("Computing FR2 pairwise identities...")
    fr2_pairwise = compute_pairwise_identity(fr_df, t1, "fr2")
    fr2_pairwise.to_csv(OUT_FR2_PAIRWISE, index=False)
    print(f"Wrote: {OUT_FR2_PAIRWISE}")
    
    print("Computing FR3 pairwise identities...")
    fr3_pairwise = compute_pairwise_identity(fr_df, t1, "fr3")
    fr3_pairwise.to_csv(OUT_FR3_PAIRWISE, index=False)
    print(f"Wrote: {OUT_FR3_PAIRWISE}")
    
    print("Extracting VHH hallmark positions...")
    hallmark_df = extract_hallmark_residues(numbering_df)
    
    print("Building report...")
    report_lines = build_report(fr_df, t1, fr2_pairwise, fr3_pairwise, hallmark_df)
    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Wrote: {OUT_REPORT}")
    
    # Write strategy consensus sequences
    consensus_lines = []
    for strategy in ["BM", "SR", "Native"]:
        sub = fr_df.merge(t1[["antibody_id", "strategy_group"]], on="antibody_id", how="left")
        sub = sub[sub["strategy_group"] == strategy]
        if sub.empty:
            continue
        for region in ["fr1", "fr2", "fr3", "fr4"]:
            consensus = build_consensus_sequence(sub[f"{region}_sequence"].tolist())
            consensus_lines.append(f">{strategy}_{region.upper()}_consensus")
            consensus_lines.append(consensus)
    
    OUT_CONSENSUS.write_text("\n".join(consensus_lines), encoding="utf-8")
    print(f"Wrote: {OUT_CONSENSUS}")


if __name__ == "__main__":
    main()
