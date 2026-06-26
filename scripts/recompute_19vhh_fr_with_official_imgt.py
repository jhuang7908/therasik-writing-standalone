"""
Recompute FR germline identity using OFFICIAL IMGT germline databases.

This is the GOLD STANDARD analysis using authoritative IMGT data:
  - Human: d:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/germlines/human_ig_aa/IGHV_aa.fasta
  - Vicugna pacos: d:/InSynBio-AI-Research/Antibody_Engineer_Suite/data/germlines/vicugna_pacos_ig_aa/IGHV_aa.fasta

Previous analysis used a small subset (178 human VH3, 84 camelid VHH).
This analysis uses the COMPLETE IMGT germline databases.

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/tables/Table1_slice3_19_clinical_vhh_master.csv
  - data/germlines/human_ig_aa/IGHV_aa.fasta
  - data/germlines/vicugna_pacos_ig_aa/IGHV_aa.fasta

Outputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_germline_identity_OFFICIAL_IMGT.csv
  - paper/raw data/TheraSAbDab_19VHH_FR_germline_identity_OFFICIAL_IMGT_report.txt
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
OUT_CSV = OUT_DIR / "TheraSAbDab_19VHH_FR_germline_identity_OFFICIAL_IMGT.csv"
OUT_REPORT = OUT_DIR / "TheraSAbDab_19VHH_FR_germline_identity_OFFICIAL_IMGT_report.txt"


def read_fasta(fasta_path: Path) -> dict[str, str]:
    """Read FASTA file and return dict of {header: sequence}."""
    if not fasta_path.exists():
        print(f"Warning: {fasta_path} not found")
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
            current_seq.append(line.upper().replace(" ", "").replace("-", ""))  # remove gaps
    if current_header and current_seq:
        sequences[current_header] = "".join(current_seq)
    return sequences


def compute_identity(seq1: str, seq2: str) -> float:
    """Compute pairwise identity (matches / max_length * 100)."""
    if not seq1 or not seq2:
        return 0.0
    max_len = max(len(seq1), len(seq2))
    matches = sum(1 for i in range(min(len(seq1), len(seq2))) if seq1[i] == seq2[i])
    return (matches / max_len) * 100.0


def find_best_germline_match(query_seq: str, germline_db: dict[str, str]) -> tuple[str, float, int]:
    """Find best-matching germline and return (germline_name, identity%, matches)."""
    if not query_seq or not germline_db:
        return ("", 0.0, 0)
    best_name = ""
    best_identity = 0.0
    best_matches = 0
    for name, seq in germline_db.items():
        identity = compute_identity(query_seq, seq)
        matches = sum(1 for i in range(min(len(query_seq), len(seq))) if query_seq[i] == seq[i])
        if identity > best_identity:
            best_identity = identity
            best_name = name
            best_matches = matches
    return (best_name, best_identity, best_matches)


def analyze_fr_germline_identity(fr_df: pd.DataFrame, human_db: dict, vicugna_db: dict, t1_df: pd.DataFrame) -> pd.DataFrame:
    """Compute FR-level germline identity for each antibody."""
    records = []
    for _, row in fr_df.iterrows():
        ab_id = row["antibody_id"]
        
        # Concatenate all FR regions for global FR identity
        fr_concat = row["fr1_sequence"] + row["fr2_sequence"] + row["fr3_sequence"] + row["fr4_sequence"]
        
        # Find best human germline match
        best_human, human_identity, human_matches = find_best_germline_match(fr_concat, human_db)
        
        # Find best vicugna germline match
        best_vicugna, vicugna_identity, vicugna_matches = find_best_germline_match(fr_concat, vicugna_db)
        
        # Get strategy from Table1
        strategy = t1_df.loc[t1_df["antibody_id"] == ab_id, "strategy_group"].values
        strategy = strategy[0] if len(strategy) > 0 else "Unknown"
        
        h2_class = t1_df.loc[t1_df["antibody_id"] == ab_id, "h2_class"].values
        h2_class = h2_class[0] if len(h2_class) > 0 else "unknown"
        
        clinical_status = t1_df.loc[t1_df["antibody_id"] == ab_id, "clinical_status"].values
        clinical_status = clinical_status[0] if len(clinical_status) > 0 else ""
        
        # Table1 global human_identity for comparison
        global_human_identity = t1_df.loc[t1_df["antibody_id"] == ab_id, "human_identity"].values
        global_human_identity = float(global_human_identity[0]) * 100.0 if len(global_human_identity) > 0 else 0.0
        
        records.append(
            {
                "antibody_id": ab_id,
                "strategy_group": strategy,
                "h2_class": h2_class,
                "clinical_status": clinical_status,
                "fr_total_length": len(fr_concat),
                "best_human_germline": best_human,
                "fr_human_identity_pct": human_identity,
                "fr_human_matches": human_matches,
                "best_vicugna_germline": best_vicugna,
                "fr_vicugna_identity_pct": vicugna_identity,
                "fr_vicugna_matches": vicugna_matches,
                "global_human_identity_pct": global_human_identity,
                "fr_human_minus_vicugna": human_identity - vicugna_identity,
            }
        )
    
    return pd.DataFrame(records)


def build_report(identity_df: pd.DataFrame, human_count: int, vicugna_count: int) -> list[str]:
    """Build human-readable germline identity report."""
    lines = []
    lines.append("=" * 80)
    lines.append("FR Germline Identity Analysis - OFFICIAL IMGT Data (19 Clinical VHHs)")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"IMGT Germline Databases:")
    lines.append(f"  - Human IGHV: {human_count} germlines (complete IMGT collection)")
    lines.append(f"  - Vicugna pacos IGHV: {vicugna_count} germlines (complete IMGT collection)")
    lines.append("")
    lines.append("Strategy Validation Thresholds (classical theory):")
    lines.append("  - BM: FR human identity ≥ 75% (CDR grafted onto human framework)")
    lines.append("  - SR: FR human identity 50-70% (camelid framework + surface humanization)")
    lines.append("  - Native: FR human identity < 50% (minimal humanization)")
    lines.append("")
    
    # Summary by strategy
    lines.append("## 1. FR Germline Identity by Reported Strategy")
    lines.append("")
    for strategy in ["BM", "SR", "Native"]:
        sub = identity_df[identity_df["strategy_group"] == strategy]
        if sub.empty:
            continue
        lines.append(f"### {strategy} (n={len(sub)})")
        lines.append(f"  FR human identity: median={sub['fr_human_identity_pct'].median():.1f}%, "
                     f"range={sub['fr_human_identity_pct'].min():.1f}-{sub['fr_human_identity_pct'].max():.1f}%")
        lines.append(f"  FR vicugna identity: median={sub['fr_vicugna_identity_pct'].median():.1f}%, "
                     f"range={sub['fr_vicugna_identity_pct'].min():.1f}-{sub['fr_vicugna_identity_pct'].max():.1f}%")
        lines.append(f"  Global human identity (from Table1): median={sub['global_human_identity_pct'].median():.1f}%")
        lines.append("")
    
    # Individual profiles
    lines.append("## 2. Individual Antibody FR Germline Identity")
    lines.append("")
    for _, row in identity_df.sort_values(["strategy_group", "fr_human_identity_pct"], ascending=[True, False]).iterrows():
        lines.append(f"{row['antibody_id']} ({row['strategy_group']}, {row['h2_class']}):")
        lines.append(f"  FR human identity: {row['fr_human_identity_pct']:.1f}% ({row['fr_human_matches']}/{row['fr_total_length']} matches)")
        lines.append(f"  Best human match: {row['best_human_germline'][:80]}")
        lines.append(f"  FR vicugna identity: {row['fr_vicugna_identity_pct']:.1f}% ({row['fr_vicugna_matches']}/{row['fr_total_length']} matches)")
        lines.append(f"  Best vicugna match: {row['best_vicugna_germline'][:80]}")
        lines.append(f"  Global human identity: {row['global_human_identity_pct']:.1f}%")
        lines.append(f"  FR human - vicugna: {row['fr_human_minus_vicugna']:+.1f}%")
        lines.append("")
    
    # Validation
    lines.append("## 3. Strategy Classification Validation (using OFFICIAL IMGT data)")
    lines.append("")
    
    bm_sub = identity_df[identity_df["strategy_group"] == "BM"]
    sr_sub = identity_df[identity_df["strategy_group"] == "SR"]
    native_sub = identity_df[identity_df["strategy_group"] == "Native"]
    
    bm_wrong = bm_sub[bm_sub["fr_human_identity_pct"] < 75.0]
    sr_wrong = sr_sub[(sr_sub["fr_human_identity_pct"] < 50.0) | (sr_sub["fr_human_identity_pct"] >= 75.0)]
    native_wrong = native_sub[native_sub["fr_human_identity_pct"] >= 50.0]
    
    if not bm_wrong.empty:
        lines.append("⚠️  BM molecules with FR human identity < 75% (may be misclassified):")
        for _, r in bm_wrong.iterrows():
            lines.append(f"  - {r['antibody_id']}: FR human={r['fr_human_identity_pct']:.1f}%, vicugna={r['fr_vicugna_identity_pct']:.1f}%")
        lines.append("")
    else:
        lines.append("✓ All BM molecules have FR human identity ≥ 75%")
        lines.append("")
    
    if not sr_wrong.empty:
        lines.append("⚠️  SR molecules outside expected range (50-70%):")
        for _, r in sr_wrong.iterrows():
            lines.append(f"  - {r['antibody_id']}: FR human={r['fr_human_identity_pct']:.1f}%, vicugna={r['fr_vicugna_identity_pct']:.1f}%")
        lines.append("")
    else:
        lines.append("✓ All SR molecules have FR human identity in 50-70% range")
        lines.append("")
    
    if not native_wrong.empty:
        lines.append("⚠️  Native molecules with FR human identity ≥ 50% (may be misclassified):")
        for _, r in native_wrong.iterrows():
            lines.append(f"  - {r['antibody_id']}: FR human={r['fr_human_identity_pct']:.1f}%, vicugna={r['fr_vicugna_identity_pct']:.1f}%")
        lines.append("")
    else:
        lines.append("✓ All Native molecules have FR human identity < 50%")
        lines.append("")
    
    # Key findings
    lines.append("## 4. Key Findings (using OFFICIAL IMGT germline databases)")
    lines.append("")
    lines.append(f"1. BM strategy: FR human identity = {bm_sub['fr_human_identity_pct'].median():.1f}% (expected ≥75%)")
    lines.append(f"2. SR strategy: FR human identity = {sr_sub['fr_human_identity_pct'].median():.1f}% (expected 50-70%)")
    lines.append(f"3. Native strategy: FR human identity = {native_sub['fr_human_identity_pct'].median():.1f}% (expected <50%)")
    lines.append("")
    
    total_correct = len(identity_df) - len(bm_wrong) - len(sr_wrong) - len(native_wrong)
    lines.append(f"4. Strategy classification accuracy: {total_correct}/{len(identity_df)} ({100.0*total_correct/len(identity_df):.1f}%)")
    lines.append("")
    
    # Compare with global human_identity
    lines.append("5. FR identity vs Global identity comparison:")
    for strategy in ["BM", "SR", "Native"]:
        sub = identity_df[identity_df["strategy_group"] == strategy]
        if sub.empty:
            continue
        fr_median = sub["fr_human_identity_pct"].median()
        global_median = sub["global_human_identity_pct"].median()
        lines.append(f"   {strategy}: FR={fr_median:.1f}%, Global={global_median:.1f}% (delta={global_median-fr_median:+.1f}%)")
    lines.append("")
    lines.append("=" * 80)
    
    return lines


def main() -> None:
    # Load inputs
    fr_df = pd.read_csv(IN_FR_SEQ)
    t1 = pd.read_csv(IN_TABLE1)
    
    print("Loading OFFICIAL IMGT germline databases...")
    human_db = read_fasta(IN_HUMAN_IGHV)
    vicugna_db = read_fasta(IN_VICUGNA_IGHV)
    
    print(f"  Human IGHV germlines: {len(human_db)}")
    print(f"  Vicugna pacos IGHV germlines: {len(vicugna_db)}")
    
    if not human_db or not vicugna_db:
        print("ERROR: Failed to load germline databases!")
        return
    
    # Analyze
    print("Computing FR germline identities...")
    identity_df = analyze_fr_germline_identity(fr_df, human_db, vicugna_db, t1)
    identity_df.to_csv(OUT_CSV, index=False)
    print(f"Wrote: {OUT_CSV}")
    
    # Report
    report_lines = build_report(identity_df, len(human_db), len(vicugna_db))
    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Wrote: {OUT_REPORT}")


if __name__ == "__main__":
    main()
