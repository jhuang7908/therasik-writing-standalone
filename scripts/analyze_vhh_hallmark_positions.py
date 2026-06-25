"""
Analyze VHH hallmark positions (IMGT 37, 44, 45, 47) to determine humanization status.

These positions are critical for VHH vs conventional VH distinction:
  - IMGT 37 (FR2): Human VH = E/Q, Camelid VHH = F/Y
  - IMGT 44 (FR2): Human VH = G, Camelid VHH = E
  - IMGT 45 (FR2): Human VH = L, Camelid VHH = C/R
  - IMGT 47 (FR2-CDR2 junction): Human VH = W, Camelid VHH = G/F

Analysis of these positions can reveal:
  1. Whether molecules retain camelid VHH hallmarks
  2. Whether they have been humanized at these positions
  3. If they are hybrid/chimeric at key positions

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_ANARCII_numbering_full.csv
  - paper/tables/Table1_slice3_19_clinical_vhh_master.csv

Outputs:
  - paper/raw data/TheraSAbDab_19VHH_hallmark_positions.csv
  - paper/raw data/TheraSAbDab_19VHH_hallmark_analysis_report.txt
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

IN_NUMBERING = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_ANARCII_numbering_full.csv"
IN_TABLE1 = PROJECT_ROOT / "paper" / "tables" / "Table1_slice3_19_clinical_vhh_master.csv"

OUT_DIR = PROJECT_ROOT / "paper" / "raw data"
OUT_CSV = OUT_DIR / "TheraSAbDab_19VHH_hallmark_positions.csv"
OUT_REPORT = OUT_DIR / "TheraSAbDab_19VHH_hallmark_analysis_report.txt"


# VHH hallmark positions and expected residues
HALLMARK_POSITIONS = {
    37: {"human": {"E", "Q"}, "camelid": {"F", "Y"}, "name": "FR2-VHH-signature-1"},
    44: {"human": {"G"}, "camelid": {"E"}, "name": "FR2-VHH-signature-2"},
    45: {"human": {"L"}, "camelid": {"C", "R"}, "name": "FR2-VHH-signature-3"},
    47: {"human": {"W"}, "camelid": {"G", "F"}, "name": "FR2-CDR2-junction"},
}


def _parse_imgt_position(label: str) -> int:
    if not label:
        return 0
    m = re.match(r"^(\d+)", label.strip())
    return int(m.group(1)) if m else 0


def extract_hallmark_residues(numbering_df: pd.DataFrame) -> pd.DataFrame:
    """Extract residues at VHH hallmark positions for all molecules."""
    records = []
    for ab_id in numbering_df["antibody_id"].unique():
        sub = numbering_df[numbering_df["antibody_id"] == ab_id].copy()
        sub["imgt_pos_num"] = sub["imgt_position"].apply(_parse_imgt_position)
        
        hallmark_residues = {}
        for pos in HALLMARK_POSITIONS:
            residue_row = sub[sub["imgt_pos_num"] == pos]
            if not residue_row.empty:
                hallmark_residues[f"pos_{pos}"] = residue_row.iloc[0]["aa"]
            else:
                hallmark_residues[f"pos_{pos}"] = "-"  # missing
        
        records.append({"antibody_id": ab_id, **hallmark_residues})
    
    return pd.DataFrame(records)


def classify_hallmark_status(hallmark_df: pd.DataFrame, t1_df: pd.DataFrame) -> pd.DataFrame:
    """Classify each molecule based on hallmark positions."""
    merged = hallmark_df.merge(
        t1_df[["antibody_id", "strategy_group", "h2_class", "clinical_status"]],
        on="antibody_id",
        how="left",
    )
    
    # Classify each position
    for pos in HALLMARK_POSITIONS:
        col = f"pos_{pos}"
        human_set = HALLMARK_POSITIONS[pos]["human"]
        camelid_set = HALLMARK_POSITIONS[pos]["camelid"]
        
        def classify_residue(aa: str) -> str:
            aa = aa.strip().upper()
            if aa in human_set:
                return "human"
            elif aa in camelid_set:
                return "camelid"
            elif aa == "-":
                return "missing"
            else:
                return "other"
        
        merged[f"pos_{pos}_status"] = merged[col].apply(classify_residue)
    
    # Compute overall humanization score (0-4, higher = more humanized)
    def compute_humanization_score(row) -> int:
        score = 0
        for pos in HALLMARK_POSITIONS:
            if row[f"pos_{pos}_status"] == "human":
                score += 1
        return score
    
    merged["humanization_score"] = merged.apply(compute_humanization_score, axis=1)
    
    # Classify overall status
    def classify_overall(score: int) -> str:
        if score == 4:
            return "fully_humanized"
        elif score == 3:
            return "mostly_humanized"
        elif score == 2:
            return "hybrid"
        elif score == 1:
            return "mostly_camelid"
        else:
            return "fully_camelid"
    
    merged["overall_status"] = merged["humanization_score"].apply(classify_overall)
    
    return merged


def build_report(classified_df: pd.DataFrame) -> list[str]:
    """Build human-readable hallmark analysis report."""
    lines = []
    lines.append("=" * 80)
    lines.append("VHH Hallmark Position Analysis (19 Clinical VHHs)")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Analyzed positions (IMGT numbering):")
    for pos, info in HALLMARK_POSITIONS.items():
        lines.append(f"  - IMGT {pos} ({info['name']}): Human={', '.join(info['human'])}, Camelid={', '.join(info['camelid'])}")
    lines.append("")
    
    # Overall distribution
    lines.append("## 1. Overall Humanization Status Distribution")
    lines.append("")
    status_counts = classified_df["overall_status"].value_counts()
    for status in ["fully_humanized", "mostly_humanized", "hybrid", "mostly_camelid", "fully_camelid"]:
        count = status_counts.get(status, 0)
        lines.append(f"  {status}: {count} molecules")
    lines.append("")
    
    # By reported strategy
    lines.append("## 2. Hallmark Status by Reported Strategy")
    lines.append("")
    for strategy in ["BM", "SR", "Native"]:
        sub = classified_df[classified_df["strategy_group"] == strategy]
        if sub.empty:
            continue
        lines.append(f"### {strategy} (n={len(sub)})")
        lines.append(f"  Humanization score: median={sub['humanization_score'].median():.1f}, range={sub['humanization_score'].min()}-{sub['humanization_score'].max()}")
        status_dist = sub["overall_status"].value_counts().to_dict()
        for status in ["fully_humanized", "mostly_humanized", "hybrid", "mostly_camelid", "fully_camelid"]:
            count = status_dist.get(status, 0)
            if count > 0:
                lines.append(f"  - {status}: {count}")
        lines.append("")
    
    # Individual molecule details
    lines.append("## 3. Individual Molecule Hallmark Profiles")
    lines.append("")
    for _, row in classified_df.sort_values(["strategy_group", "humanization_score"], ascending=[True, False]).iterrows():
        lines.append(f"{row['antibody_id']} ({row['strategy_group']}, {row['overall_status']}):")
        lines.append(f"  Humanization score: {row['humanization_score']}/4")
        for pos in HALLMARK_POSITIONS:
            residue = row[f"pos_{pos}"]
            status = row[f"pos_{pos}_status"]
            lines.append(f"  - IMGT {pos}: {residue} ({status})")
        lines.append("")
    
    # Key findings
    lines.append("## 4. Key Findings")
    lines.append("")
    
    # Check if hallmark status correlates with reported strategy
    bm_scores = classified_df[classified_df["strategy_group"] == "BM"]["humanization_score"].tolist()
    sr_scores = classified_df[classified_df["strategy_group"] == "SR"]["humanization_score"].tolist()
    native_scores = classified_df[classified_df["strategy_group"] == "Native"]["humanization_score"].tolist()
    
    if bm_scores and sr_scores and native_scores:
        lines.append(f"1. BM strategy: avg humanization score = {sum(bm_scores)/len(bm_scores):.1f}")
        lines.append(f"2. SR strategy: avg humanization score = {sum(sr_scores)/len(sr_scores):.1f}")
        lines.append(f"3. Native strategy: avg humanization score = {sum(native_scores)/len(native_scores):.1f}")
        lines.append("")
        
        if max(bm_scores) - min(native_scores) < 2:
            lines.append("⚠️  No clear separation between strategies based on hallmark positions!")
            lines.append("   All molecules have similar humanization scores at VHH-specific residues.")
        else:
            lines.append("✓ Hallmark positions show some correlation with reported strategies.")
    
    lines.append("")
    lines.append("=" * 80)
    
    return lines


def main() -> None:
    numbering_df = pd.read_csv(IN_NUMBERING)
    t1_df = pd.read_csv(IN_TABLE1)
    
    # Extract hallmark residues
    hallmark_df = extract_hallmark_residues(numbering_df)
    
    # Classify
    classified_df = classify_hallmark_status(hallmark_df, t1_df)
    classified_df.to_csv(OUT_CSV, index=False)
    print(f"Wrote: {OUT_CSV}")
    
    # Report
    report_lines = build_report(classified_df)
    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Wrote: {OUT_REPORT}")


if __name__ == "__main__":
    main()
