"""
Analyze FR regions SEPARATELY to identify true humanization patterns.

Hypothesis:
  - FR4: Must be human (constant region interface)
  - FR2: Likely camelid (contains VHH hallmark positions)
  - FR1+FR3: The "tunable" regions that may distinguish BM/SR/Native strategies

This analysis computes germline identity for each FR region independently
to identify which regions are truly humanized vs conserved.

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/tables/Table1_slice3_19_clinical_vhh_master.csv
  - data/germlines/human_ig_aa/IGHV_aa.fasta
  - data/germlines/vicugna_pacos_ig_aa/IGHV_aa.fasta

Outputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_regional_identity.csv
  - paper/raw data/TheraSAbDab_19VHH_FR_regional_identity_report.txt
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
OUT_CSV = OUT_DIR / "TheraSAbDab_19VHH_FR_regional_identity.csv"
OUT_REPORT = OUT_DIR / "TheraSAbDab_19VHH_FR_regional_identity_report.txt"


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
            current_seq.append(line.upper().replace(" ", "").replace("-", ""))
    if current_header and current_seq:
        sequences[current_header] = "".join(current_seq)
    return sequences


def compute_identity(seq1: str, seq2: str) -> float:
    """Compute pairwise identity (matches / min_length * 100) for aligned regions."""
    if not seq1 or not seq2:
        return 0.0
    min_len = min(len(seq1), len(seq2))
    if min_len == 0:
        return 0.0
    matches = sum(1 for i in range(min_len) if seq1[i] == seq2[i])
    return (matches / min_len) * 100.0


def find_best_regional_match(query_seq: str, germline_db: dict[str, str], region_name: str) -> tuple[str, float]:
    """Find best-matching germline for a specific FR region."""
    if not query_seq or not germline_db:
        return ("", 0.0)
    
    best_name = ""
    best_identity = 0.0
    
    for name, full_seq in germline_db.items():
        # Extract corresponding region from germline (approximate positions)
        # FR1: positions 0-25, FR2: 38-54, FR3: 65-103, FR4: 117-127 (0-indexed)
        if region_name == "fr1":
            germline_region = full_seq[0:min(26, len(full_seq))]
        elif region_name == "fr2":
            germline_region = full_seq[38:min(55, len(full_seq))]
        elif region_name == "fr3":
            germline_region = full_seq[65:min(104, len(full_seq))]
        elif region_name == "fr4":
            germline_region = full_seq[117:min(128, len(full_seq))]
        else:
            germline_region = ""
        
        if not germline_region:
            continue
        
        identity = compute_identity(query_seq, germline_region)
        if identity > best_identity:
            best_identity = identity
            best_name = name
    
    return (best_name, best_identity)


def analyze_regional_identity(fr_df: pd.DataFrame, human_db: dict, vicugna_db: dict, t1_df: pd.DataFrame) -> pd.DataFrame:
    """Compute germline identity for each FR region separately."""
    records = []
    
    for _, row in fr_df.iterrows():
        ab_id = row["antibody_id"]
        
        # Get strategy and metadata
        strategy = t1_df.loc[t1_df["antibody_id"] == ab_id, "strategy_group"].values
        strategy = strategy[0] if len(strategy) > 0 else "Unknown"
        
        h2_class = t1_df.loc[t1_df["antibody_id"] == ab_id, "h2_class"].values
        h2_class = h2_class[0] if len(h2_class) > 0 else "unknown"
        
        global_human_identity = t1_df.loc[t1_df["antibody_id"] == ab_id, "human_identity"].values
        global_human_identity = float(global_human_identity[0]) * 100.0 if len(global_human_identity) > 0 else 0.0
        
        # Analyze each FR region separately
        record = {
            "antibody_id": ab_id,
            "strategy_group": strategy,
            "h2_class": h2_class,
            "global_human_identity_pct": global_human_identity,
        }
        
        for fr_name in ["fr1", "fr2", "fr3", "fr4"]:
            query_seq = row[f"{fr_name}_sequence"]
            
            _, human_identity = find_best_regional_match(query_seq, human_db, fr_name)
            _, vicugna_identity = find_best_regional_match(query_seq, vicugna_db, fr_name)
            
            record[f"{fr_name}_human_pct"] = human_identity
            record[f"{fr_name}_vicugna_pct"] = vicugna_identity
            record[f"{fr_name}_delta_human_minus_vicugna"] = human_identity - vicugna_identity
        
        # Compute FR1+FR3 combined identity
        fr13_concat = row["fr1_sequence"] + row["fr3_sequence"]
        fr13_human = []
        fr13_vicugna = []
        for name, full_seq in human_db.items():
            fr1_region = full_seq[0:min(26, len(full_seq))]
            fr3_region = full_seq[65:min(104, len(full_seq))]
            combined = fr1_region + fr3_region
            fr13_human.append(compute_identity(fr13_concat, combined))
        for name, full_seq in vicugna_db.items():
            fr1_region = full_seq[0:min(26, len(full_seq))]
            fr3_region = full_seq[65:min(104, len(full_seq))]
            combined = fr1_region + fr3_region
            fr13_vicugna.append(compute_identity(fr13_concat, combined))
        
        record["fr1_fr3_human_pct"] = max(fr13_human) if fr13_human else 0.0
        record["fr1_fr3_vicugna_pct"] = max(fr13_vicugna) if fr13_vicugna else 0.0
        record["fr1_fr3_delta"] = record["fr1_fr3_human_pct"] - record["fr1_fr3_vicugna_pct"]
        
        records.append(record)
    
    return pd.DataFrame(records)


def build_report(regional_df: pd.DataFrame) -> list[str]:
    """Build comprehensive regional identity report."""
    lines = []
    lines.append("=" * 80)
    lines.append("FR Regional Germline Identity Analysis (19 Clinical VHHs)")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Hypothesis Test:")
    lines.append("  - FR4 should be predominantly human (constant region interface)")
    lines.append("  - FR2 should retain camelid features (VHH hallmark positions)")
    lines.append("  - FR1+FR3 should differentiate BM/SR/Native strategies")
    lines.append("")
    
    # Summary statistics by region
    lines.append("## 1. Regional Identity Summary (All 19 Molecules)")
    lines.append("")
    lines.append("| Region  | Human Identity (%) | Vicugna Identity (%) | Delta (Human-Vicugna) |")
    lines.append("|---------|-------------------|----------------------|----------------------|")
    for region in ["fr1", "fr2", "fr3", "fr4", "fr1_fr3"]:
        human_col = f"{region}_human_pct"
        vicugna_col = f"{region}_vicugna_pct"
        delta_col = f"{region}_delta" if region == "fr1_fr3" else f"{region}_delta_human_minus_vicugna"
        
        if human_col in regional_df.columns:
            h_median = regional_df[human_col].median()
            v_median = regional_df[vicugna_col].median()
            d_median = regional_df[delta_col].median()
            region_label = "FR1+FR3" if region == "fr1_fr3" else region.upper()
            lines.append(f"| {region_label:7} | {h_median:17.1f} | {v_median:20.1f} | {d_median:20.1f} |")
    lines.append("")
    
    # Test hypothesis: FR4 is human, FR2 is camelid
    lines.append("## 2. Hypothesis Validation")
    lines.append("")
    
    fr4_human_median = regional_df["fr4_human_pct"].median()
    fr4_vicugna_median = regional_df["fr4_vicugna_pct"].median()
    fr2_human_median = regional_df["fr2_human_pct"].median()
    fr2_vicugna_median = regional_df["fr2_vicugna_pct"].median()
    
    lines.append(f"### FR4 (Constant Region Interface):")
    lines.append(f"  - Human identity: {fr4_human_median:.1f}%")
    lines.append(f"  - Vicugna identity: {fr4_vicugna_median:.1f}%")
    if fr4_human_median > fr4_vicugna_median:
        lines.append(f"  ✓ FR4 is MORE human-like (delta={fr4_human_median-fr4_vicugna_median:+.1f}%)")
    else:
        lines.append(f"  ✗ FR4 is NOT more human-like (delta={fr4_human_median-fr4_vicugna_median:+.1f}%)")
    lines.append("")
    
    lines.append(f"### FR2 (VHH Hallmark Region):")
    lines.append(f"  - Human identity: {fr2_human_median:.1f}%")
    lines.append(f"  - Vicugna identity: {fr2_vicugna_median:.1f}%")
    if fr2_vicugna_median > fr2_human_median:
        lines.append(f"  ✓ FR2 is MORE camelid-like (delta={fr2_human_median-fr2_vicugna_median:+.1f}%)")
    else:
        lines.append(f"  ✗ FR2 is NOT more camelid-like (delta={fr2_human_median-fr2_vicugna_median:+.1f}%)")
    lines.append("")
    
    # Strategy differentiation by FR1+FR3
    lines.append("## 3. Strategy Differentiation by FR1+FR3 Identity")
    lines.append("")
    for strategy in ["BM", "SR", "Native"]:
        sub = regional_df[regional_df["strategy_group"] == strategy]
        if sub.empty:
            continue
        lines.append(f"### {strategy} (n={len(sub)})")
        lines.append(f"  FR1+FR3 human identity: median={sub['fr1_fr3_human_pct'].median():.1f}%, "
                     f"range={sub['fr1_fr3_human_pct'].min():.1f}-{sub['fr1_fr3_human_pct'].max():.1f}%")
        lines.append(f"  FR1+FR3 vicugna identity: median={sub['fr1_fr3_vicugna_pct'].median():.1f}%, "
                     f"range={sub['fr1_fr3_vicugna_pct'].min():.1f}-{sub['fr1_fr3_vicugna_pct'].max():.1f}%")
        lines.append(f"  FR1+FR3 delta (H-V): median={sub['fr1_fr3_delta'].median():.1f}%")
        lines.append("")
    
    # Individual profiles
    lines.append("## 4. Individual Molecule Regional Profiles")
    lines.append("")
    for _, row in regional_df.sort_values(["strategy_group", "fr1_fr3_human_pct"], ascending=[True, False]).iterrows():
        lines.append(f"{row['antibody_id']} ({row['strategy_group']}, {row['h2_class']}):")
        lines.append(f"  FR1: H={row['fr1_human_pct']:.1f}%, V={row['fr1_vicugna_pct']:.1f}%, Δ={row['fr1_delta_human_minus_vicugna']:+.1f}%")
        lines.append(f"  FR2: H={row['fr2_human_pct']:.1f}%, V={row['fr2_vicugna_pct']:.1f}%, Δ={row['fr2_delta_human_minus_vicugna']:+.1f}%")
        lines.append(f"  FR3: H={row['fr3_human_pct']:.1f}%, V={row['fr3_vicugna_pct']:.1f}%, Δ={row['fr3_delta_human_minus_vicugna']:+.1f}%")
        lines.append(f"  FR4: H={row['fr4_human_pct']:.1f}%, V={row['fr4_vicugna_pct']:.1f}%, Δ={row['fr4_delta_human_minus_vicugna']:+.1f}%")
        lines.append(f"  FR1+FR3: H={row['fr1_fr3_human_pct']:.1f}%, V={row['fr1_fr3_vicugna_pct']:.1f}%, Δ={row['fr1_fr3_delta']:+.1f}%")
        lines.append(f"  Global: {row['global_human_identity_pct']:.1f}%")
        lines.append("")
    
    # Key findings
    lines.append("## 5. Key Findings")
    lines.append("")
    
    # Test if FR1+FR3 can separate strategies
    bm_fr13 = regional_df[regional_df["strategy_group"] == "BM"]["fr1_fr3_human_pct"].median()
    sr_fr13 = regional_df[regional_df["strategy_group"] == "SR"]["fr1_fr3_human_pct"].median()
    native_fr13 = regional_df[regional_df["strategy_group"] == "Native"]["fr1_fr3_human_pct"].median()
    
    lines.append(f"1. FR1+FR3 human identity by strategy:")
    lines.append(f"   - BM: {bm_fr13:.1f}%")
    lines.append(f"   - SR: {sr_fr13:.1f}%")
    lines.append(f"   - Native: {native_fr13:.1f}%")
    lines.append("")
    
    if max(bm_fr13, sr_fr13, native_fr13) - min(bm_fr13, sr_fr13, native_fr13) > 5.0:
        lines.append("✓ FR1+FR3 shows >5% separation between strategies")
    else:
        lines.append("✗ FR1+FR3 does NOT separate strategies (all ~30%, similar to full FR)")
        lines.append("   → Conclusion: There may be NO true 'Native' strategy")
        lines.append("   → All molecules likely underwent some level of humanization")
    lines.append("")
    
    # Check if all deltas are similar (human ≈ vicugna for all regions)
    all_deltas = []
    for region in ["fr1", "fr2", "fr3", "fr4"]:
        delta_col = f"{region}_delta_human_minus_vicugna"
        all_deltas.extend(regional_df[delta_col].abs().tolist())
    median_abs_delta = pd.Series(all_deltas).median()
    
    lines.append(f"2. Overall regional bias (|Human-Vicugna| delta):")
    lines.append(f"   - Median absolute delta: {median_abs_delta:.1f}%")
    if median_abs_delta < 3.0:
        lines.append("   → All FR regions are EQUALLY distant from human and vicugna germlines")
        lines.append("   → Suggests synthetic/engineered scaffolds, not simple germline humanization")
    lines.append("")
    lines.append("=" * 80)
    
    return lines


def main() -> None:
    fr_df = pd.read_csv(IN_FR_SEQ)
    t1 = pd.read_csv(IN_TABLE1)
    
    print("Loading IMGT germline databases...")
    human_db = read_fasta(IN_HUMAN_IGHV)
    vicugna_db = read_fasta(IN_VICUGNA_IGHV)
    
    print(f"  Human IGHV: {len(human_db)} germlines")
    print(f"  Vicugna pacos IGHV: {len(vicugna_db)} germlines")
    
    if not human_db or not vicugna_db:
        print("ERROR: Failed to load germline databases!")
        return
    
    print("Analyzing regional identities...")
    regional_df = analyze_regional_identity(fr_df, human_db, vicugna_db, t1)
    regional_df.to_csv(OUT_CSV, index=False)
    print(f"Wrote: {OUT_CSV}")
    
    report_lines = build_report(regional_df)
    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Wrote: {OUT_REPORT}")


if __name__ == "__main__":
    main()
