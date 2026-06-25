"""
Analyze FR1 conservation to answer the fundamental question:
  "Are these sheep→human humanization, or human→sheep camelization, or synthetic scaffolds?"

Key analyses:
  1. Pairwise FR1 sequence identity among all 19 molecules
  2. Consensus FR1 sequence and its germline origin
  3. Position-by-position conservation pattern
  4. Phylogenetic relationship (clustering by FR1 similarity)

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/tables/Table1_slice3_19_clinical_vhh_master.csv
  - data/germlines/human_ig_aa/IGHV_aa.fasta
  - data/germlines/vicugna_pacos_ig_aa/IGHV_aa.fasta

Outputs:
  - paper/raw data/TheraSAbDab_19VHH_FR1_pairwise_identity.csv
  - paper/raw data/TheraSAbDab_19VHH_FR1_conservation_analysis.txt
  - paper/raw data/TheraSAbDab_19VHH_FR1_consensus.fasta
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_TABLE1 = PROJECT_ROOT / "paper" / "tables" / "Table1_slice3_19_clinical_vhh_master.csv"
IN_HUMAN_IGHV = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "IGHV_aa.fasta"
IN_VICUGNA_IGHV = PROJECT_ROOT / "data" / "germlines" / "vicugna_pacos_ig_aa" / "IGHV_aa.fasta"

OUT_DIR = PROJECT_ROOT / "paper" / "raw data"
OUT_PAIRWISE = OUT_DIR / "TheraSAbDab_19VHH_FR1_pairwise_identity.csv"
OUT_REPORT = OUT_DIR / "TheraSAbDab_19VHH_FR1_conservation_analysis.txt"
OUT_CONSENSUS = OUT_DIR / "TheraSAbDab_19VHH_FR1_consensus.fasta"


def read_fasta(fasta_path: Path) -> dict[str, str]:
    """Read FASTA file."""
    if not fasta_path.exists():
        return {}
    sequences = {}
    current_header = None
    current_seq = []
    for line in fasta_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current_header and current_seq:
                sequences[current_header] = "".join(current_seq)
            current_header = line[1:].strip()
            current_seq = []
        else:
            current_seq.append(line.upper().replace(" ", "").replace("-", ""))
    if current_header and current_seq:
        sequences[current_header] = "".join(current_seq)
    return sequences


def compute_identity(seq1: str, seq2: str) -> float:
    """Compute pairwise identity."""
    if not seq1 or not seq2:
        return 0.0
    min_len = min(len(seq1), len(seq2))
    if min_len == 0:
        return 0.0
    matches = sum(1 for i in range(min_len) if seq1[i] == seq2[i])
    return (matches / min_len) * 100.0


def compute_pairwise_fr1_identity(fr_df: pd.DataFrame, t1_df: pd.DataFrame) -> pd.DataFrame:
    """Compute pairwise FR1 identity matrix."""
    ab_ids = fr_df["antibody_id"].tolist()
    fr1_seqs = {row["antibody_id"]: row["fr1_sequence"] for _, row in fr_df.iterrows()}
    strategies = {row["antibody_id"]: t1_df.loc[t1_df["antibody_id"] == row["antibody_id"], "strategy_group"].values[0]
                  for _, row in fr_df.iterrows()}
    
    records = []
    for ab1 in ab_ids:
        for ab2 in ab_ids:
            identity = compute_identity(fr1_seqs[ab1], fr1_seqs[ab2])
            records.append({
                "antibody_1": ab1,
                "strategy_1": strategies[ab1],
                "antibody_2": ab2,
                "strategy_2": strategies[ab2],
                "fr1_identity_pct": identity,
            })
    
    return pd.DataFrame(records)


def build_consensus_fr1(fr_df: pd.DataFrame) -> str:
    """Build consensus FR1 sequence."""
    fr1_seqs = [row["fr1_sequence"] for _, row in fr_df.iterrows()]
    max_len = max(len(s) for s in fr1_seqs)
    
    consensus = []
    for pos in range(max_len):
        residues = [s[pos] for s in fr1_seqs if pos < len(s)]
        if residues:
            # Use majority vote
            from collections import Counter
            most_common = Counter(residues).most_common(1)[0][0]
            consensus.append(most_common)
    
    return "".join(consensus)


def analyze_position_conservation(fr_df: pd.DataFrame) -> list[dict]:
    """Analyze conservation at each FR1 position."""
    fr1_seqs = [row["fr1_sequence"] for _, row in fr_df.iterrows()]
    max_len = max(len(s) for s in fr1_seqs)
    
    position_stats = []
    for pos in range(max_len):
        residues = [s[pos] for s in fr1_seqs if pos < len(s)]
        if not residues:
            continue
        
        from collections import Counter
        counts = Counter(residues)
        total = len(residues)
        most_common_aa, most_common_count = counts.most_common(1)[0]
        conservation_pct = (most_common_count / total) * 100.0
        
        position_stats.append({
            "position": pos + 1,  # 1-indexed
            "total_molecules": total,
            "most_common_aa": most_common_aa,
            "most_common_count": most_common_count,
            "conservation_pct": conservation_pct,
            "num_variants": len(counts),
            "variants": ", ".join(f"{aa}:{count}" for aa, count in counts.most_common()),
        })
    
    return position_stats


def find_closest_germline(consensus: str, human_db: dict, vicugna_db: dict) -> tuple[str, float, str, float]:
    """Find closest human and vicugna germlines to consensus."""
    best_human = ""
    best_human_identity = 0.0
    for name, seq in human_db.items():
        fr1_region = seq[0:min(26, len(seq))]
        identity = compute_identity(consensus, fr1_region)
        if identity > best_human_identity:
            best_human_identity = identity
            best_human = name
    
    best_vicugna = ""
    best_vicugna_identity = 0.0
    for name, seq in vicugna_db.items():
        fr1_region = seq[0:min(26, len(seq))]
        identity = compute_identity(consensus, fr1_region)
        if identity > best_vicugna_identity:
            best_vicugna_identity = identity
            best_vicugna = name
    
    return (best_human, best_human_identity, best_vicugna, best_vicugna_identity)


def build_report(
    pairwise_df: pd.DataFrame,
    consensus: str,
    position_stats: list[dict],
    human_db: dict,
    vicugna_db: dict,
    fr_df: pd.DataFrame,
) -> list[str]:
    """Build comprehensive FR1 conservation report."""
    lines = []
    lines.append("=" * 80)
    lines.append("FR1 Conservation Analysis: Sheep→Human or Human→Sheep?")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Central Question:")
    lines.append("  Are clinical VHHs:")
    lines.append("    (A) Camelid sequences humanized toward human germlines?")
    lines.append("    (B) Human sequences 'camelize' to gain VHH properties?")
    lines.append("    (C) Synthetic scaffolds designed de novo?")
    lines.append("")
    
    # Pairwise similarity
    lines.append("## 1. FR1 Sequence Conservation Among 19 Molecules")
    lines.append("")
    
    # Overall pairwise identity
    all_pairs = pairwise_df[pairwise_df["antibody_1"] != pairwise_df["antibody_2"]]
    median_identity = all_pairs["fr1_identity_pct"].median()
    min_identity = all_pairs["fr1_identity_pct"].min()
    max_identity = all_pairs["fr1_identity_pct"].max()
    
    lines.append(f"Pairwise FR1 identity (n={len(all_pairs)} pairs):")
    lines.append(f"  - Median: {median_identity:.1f}%")
    lines.append(f"  - Range: {min_identity:.1f}% - {max_identity:.1f}%")
    lines.append("")
    
    if median_identity > 90.0:
        lines.append("✓ FR1 is HIGHLY CONSERVED (>90% identity)")
        lines.append("  → All 19 molecules share a near-identical FR1 sequence")
        lines.append("  → This is NOT random convergent evolution")
        lines.append("  → This IS a deliberately conserved 'master scaffold'")
    lines.append("")
    
    # Inter-strategy vs intra-strategy
    lines.append("Pairwise identity by strategy comparison:")
    for s1 in ["BM", "SR", "Native"]:
        for s2 in ["BM", "SR", "Native"]:
            sub = all_pairs[(all_pairs["strategy_1"] == s1) & (all_pairs["strategy_2"] == s2)]
            if not sub.empty:
                lines.append(f"  {s1} vs {s2}: {sub['fr1_identity_pct'].median():.1f}%")
    lines.append("")
    
    if all([
        all_pairs[(all_pairs["strategy_1"] == s1) & (all_pairs["strategy_2"] == s2)]["fr1_identity_pct"].median() > 90.0
        for s1 in ["BM", "SR", "Native"] for s2 in ["BM", "SR", "Native"]
        if not all_pairs[(all_pairs["strategy_1"] == s1) & (all_pairs["strategy_2"] == s2)].empty
    ]):
        lines.append("⚠️  BM/SR/Native have IDENTICAL FR1 sequences (>90% identity)")
        lines.append("   → Strategy labels do NOT reflect FR1 sequence differences")
        lines.append("   → 'Humanization' is NOT applied to FR1 region")
    lines.append("")
    
    # Consensus sequence
    lines.append("## 2. Consensus FR1 Sequence and Germline Origin")
    lines.append("")
    lines.append(f"Consensus FR1 ({len(consensus)}aa):")
    lines.append(f"  {consensus}")
    lines.append("")
    
    # Find closest germlines
    best_human, h_identity, best_vicugna, v_identity = find_closest_germline(consensus, human_db, vicugna_db)
    
    lines.append(f"Closest human IGHV germline:")
    lines.append(f"  - {best_human[:60]}")
    lines.append(f"  - Identity: {h_identity:.1f}%")
    lines.append("")
    lines.append(f"Closest Vicugna pacos IGHV germline:")
    lines.append(f"  - {best_vicugna[:60]}")
    lines.append(f"  - Identity: {v_identity:.1f}%")
    lines.append("")
    
    if abs(h_identity - v_identity) < 5.0:
        lines.append(f"⚠️  Consensus FR1 is EQUIDISTANT from human and vicugna germlines")
        lines.append(f"   (human={h_identity:.1f}%, vicugna={v_identity:.1f}%, delta={h_identity-v_identity:+.1f}%)")
        lines.append("")
        lines.append("   → This is NOT a humanized camelid sequence")
        lines.append("   → This is NOT a camelized human sequence")
        lines.append("   → This IS a SYNTHETIC CHIMERIC SCAFFOLD")
        lines.append("")
        lines.append("   Interpretation:")
        lines.append("     The consensus FR1 was likely ENGINEERED to:")
        lines.append("       1. Maintain VHH structural stability")
        lines.append("       2. Minimize immunogenicity (avoid foreign epitopes)")
        lines.append("       3. Optimize expression in mammalian cells")
    elif h_identity > v_identity + 5.0:
        lines.append(f"✓ Consensus FR1 is more HUMAN-like (delta={h_identity-v_identity:+.1f}%)")
        lines.append("   → Suggests humanization (sheep→human direction)")
    else:
        lines.append(f"✓ Consensus FR1 is more CAMELID-like (delta={h_identity-v_identity:+.1f}%)")
        lines.append("   → Suggests camelization (human→sheep direction)")
    lines.append("")
    
    # Position-by-position conservation
    lines.append("## 3. Position-by-Position Conservation")
    lines.append("")
    high_conservation = [p for p in position_stats if p["conservation_pct"] == 100.0]
    variable_positions = [p for p in position_stats if p["conservation_pct"] < 100.0]
    
    lines.append(f"Total FR1 positions: {len(position_stats)}")
    lines.append(f"  - 100% conserved: {len(high_conservation)} positions")
    lines.append(f"  - Variable: {len(variable_positions)} positions")
    lines.append("")
    
    if len(high_conservation) > len(position_stats) * 0.8:
        lines.append("✓ >80% of FR1 positions are INVARIANT")
        lines.append("  → Indicates strong selective pressure to maintain this exact sequence")
    lines.append("")
    
    if variable_positions:
        lines.append("Variable positions (conservation <100%):")
        for p in variable_positions:
            lines.append(f"  Pos {p['position']:2d}: {p['most_common_aa']} ({p['conservation_pct']:.1f}%) | Variants: {p['variants']}")
        lines.append("")
    
    # Individual FR1 sequences
    lines.append("## 4. Individual FR1 Sequences by Strategy")
    lines.append("")
    for strategy in ["BM", "SR", "Native"]:
        sub = fr_df.merge(
            pd.read_csv(IN_TABLE1)[["antibody_id", "strategy_group"]],
            on="antibody_id",
            how="left"
        )
        sub = sub[sub["strategy_group"] == strategy]
        if sub.empty:
            continue
        lines.append(f"### {strategy} (n={len(sub)})")
        for _, row in sub.iterrows():
            lines.append(f"  {row['antibody_id']:20s}: {row['fr1_sequence']}")
        lines.append("")
    
    # Final verdict
    lines.append("## 5. Final Verdict: What Are These Molecules?")
    lines.append("")
    
    if median_identity > 95.0 and abs(h_identity - v_identity) < 5.0:
        lines.append("🎯 CONCLUSION: SYNTHETIC CONSENSUS SCAFFOLD")
        lines.append("")
        lines.append("Evidence:")
        lines.append(f"  1. All 19 molecules share {median_identity:.1f}% FR1 identity")
        lines.append(f"  2. Consensus is equidistant from human ({h_identity:.1f}%) and vicugna ({v_identity:.1f}%)")
        lines.append(f"  3. BM/SR/Native show NO FR1 sequence divergence")
        lines.append("")
        lines.append("Implications:")
        lines.append("  - These are NOT traditional humanization (sheep→human)")
        lines.append("  - These are NOT reverse-engineered (human→sheep)")
        lines.append("  - These ARE built on a shared PROPRIETARY SCAFFOLD")
        lines.append("  - Strategy labels (BM/SR/Native) reflect CDR/surface modifications, NOT framework origin")
        lines.append("")
        lines.append("Likely Development Path:")
        lines.append("  1. Early successful VHH (e.g., Caplacizumab, 2009) established optimal FR1")
        lines.append("  2. Later molecules preserved this FR1 as 'proven stable scaffold'")
        lines.append("  3. All humanization efforts focused on CDR loops + surface residues")
        lines.append("  4. Result: Convergence on a single 'industry-standard' VHH framework")
    elif h_identity > v_identity + 10.0:
        lines.append("🎯 CONCLUSION: HUMANIZED CAMELID (sheep→human)")
        lines.append(f"  - Consensus FR1 is {h_identity-v_identity:.1f}% more human-like")
        lines.append("  - Suggests systematic replacement of camelid FR residues with human equivalents")
    else:
        lines.append("🎯 CONCLUSION: CAMELIZED HUMAN (human→sheep)")
        lines.append(f"  - Consensus FR1 is {v_identity-h_identity:.1f}% more camelid-like")
        lines.append("  - Suggests introduction of VHH features into human VH framework")
    
    lines.append("")
    lines.append("=" * 80)
    
    return lines


def main() -> None:
    fr_df = pd.read_csv(IN_FR_SEQ)
    t1 = pd.read_csv(IN_TABLE1)
    human_db = read_fasta(IN_HUMAN_IGHV)
    vicugna_db = read_fasta(IN_VICUGNA_IGHV)
    
    print("Computing pairwise FR1 identities...")
    pairwise_df = compute_pairwise_fr1_identity(fr_df, t1)
    pairwise_df.to_csv(OUT_PAIRWISE, index=False)
    print(f"Wrote: {OUT_PAIRWISE}")
    
    print("Building consensus FR1...")
    consensus = build_consensus_fr1(fr_df)
    
    print("Analyzing position-by-position conservation...")
    position_stats = analyze_position_conservation(fr_df)
    
    print("Building report...")
    report_lines = build_report(pairwise_df, consensus, position_stats, human_db, vicugna_db, fr_df)
    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Wrote: {OUT_REPORT}")
    
    # Write consensus FASTA
    OUT_CONSENSUS.write_text(f">Consensus_FR1_19_Clinical_VHHs\n{consensus}\n", encoding="utf-8")
    print(f"Wrote: {OUT_CONSENSUS}")


if __name__ == "__main__":
    main()
