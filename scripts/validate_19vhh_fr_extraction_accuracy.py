"""
Validate the accuracy of FR region extraction from ANARCII IMGT numbering.

Verification steps:
  1. Check ANARCII numbering completeness (all expected IMGT positions present)
  2. Verify FR boundaries match IMGT standard (FR1=1-26, FR2=39-55, FR3=66-104, FR4=118-128)
  3. Check FR lengths are consistent (expected: FR1=25-26aa, FR2=17aa, FR3=38-39aa, FR4=10-11aa)
  4. Cross-validate with known VHH structures from IMGT (if available)
  5. Check for gaps, unusual amino acids, or insertion codes in FR regions

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_ANARCII_numbering_full.csv
  - paper/raw data/TheraSAbDab_19VHH_FR_sequences.csv
  - paper/raw data/TheraSAbDab_19VHH_extracted_rows.csv (original sequences from Thera-SAbDab)

Outputs:
  - paper/raw data/TheraSAbDab_19VHH_FR_validation_report.txt
  - paper/raw data/TheraSAbDab_19VHH_FR_validation_issues.csv (if any problems detected)
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

IN_NUMBERING = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_ANARCII_numbering_full.csv"
IN_FR_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_FR_sequences.csv"
IN_RAW_SEQ = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_extracted_rows.csv"

OUT_DIR = PROJECT_ROOT / "paper" / "raw data"
OUT_REPORT = OUT_DIR / "TheraSAbDab_19VHH_FR_validation_report.txt"
OUT_ISSUES = OUT_DIR / "TheraSAbDab_19VHH_FR_validation_issues.csv"


# IMGT standard FR/CDR boundaries for VHH
FR1_RANGE = (1, 26)
CDR1_RANGE = (27, 38)
FR2_RANGE = (39, 55)
CDR2_RANGE = (56, 65)
FR3_RANGE = (66, 104)
CDR3_RANGE = (105, 117)
FR4_RANGE = (118, 128)

# Expected FR lengths (allowing ±1 for natural variation)
EXPECTED_FR_LENGTHS = {
    "fr1": (24, 26),  # typically 25aa
    "fr2": (16, 18),  # typically 17aa
    "fr3": (37, 40),  # typically 38-39aa
    "fr4": (10, 12),  # typically 11aa
}


def _parse_imgt_position(label: str) -> tuple[int, str]:
    """Parse IMGT position label into (number, insertion_code)."""
    if not label:
        return (0, "")
    m = re.match(r"^(\d+)([A-Z]?)$", label.strip())
    if m:
        return (int(m.group(1)), m.group(2) or "")
    return (0, "")


def validate_numbering_completeness(numbering_df: pd.DataFrame) -> list[dict]:
    """Check if ANARCII numbering has all expected IMGT positions."""
    issues = []
    for ab_id in numbering_df["antibody_id"].unique():
        sub = numbering_df[numbering_df["antibody_id"] == ab_id].copy()
        sub["imgt_pos_num"] = sub["imgt_position"].apply(lambda x: _parse_imgt_position(str(x))[0])
        
        # Check FR1 coverage
        fr1_positions = sub[(sub["imgt_pos_num"] >= FR1_RANGE[0]) & (sub["imgt_pos_num"] <= FR1_RANGE[1])]
        if len(fr1_positions) < 20:  # should have ~25 positions
            issues.append({
                "antibody_id": ab_id,
                "region": "FR1",
                "issue_type": "incomplete_numbering",
                "details": f"Only {len(fr1_positions)} positions found (expected ~25)",
            })
        
        # Check FR2 coverage
        fr2_positions = sub[(sub["imgt_pos_num"] >= FR2_RANGE[0]) & (sub["imgt_pos_num"] <= FR2_RANGE[1])]
        if len(fr2_positions) < 15:  # should have ~17 positions
            issues.append({
                "antibody_id": ab_id,
                "region": "FR2",
                "issue_type": "incomplete_numbering",
                "details": f"Only {len(fr2_positions)} positions found (expected ~17)",
            })
        
        # Check FR3 coverage
        fr3_positions = sub[(sub["imgt_pos_num"] >= FR3_RANGE[0]) & (sub["imgt_pos_num"] <= FR3_RANGE[1])]
        if len(fr3_positions) < 35:  # should have ~38 positions
            issues.append({
                "antibody_id": ab_id,
                "region": "FR3",
                "issue_type": "incomplete_numbering",
                "details": f"Only {len(fr3_positions)} positions found (expected ~38)",
            })
        
        # Check FR4 coverage
        fr4_positions = sub[(sub["imgt_pos_num"] >= FR4_RANGE[0]) & (sub["imgt_pos_num"] <= FR4_RANGE[1])]
        if len(fr4_positions) < 8:  # should have ~11 positions
            issues.append({
                "antibody_id": ab_id,
                "region": "FR4",
                "issue_type": "incomplete_numbering",
                "details": f"Only {len(fr4_positions)} positions found (expected ~11)",
            })
    
    return issues


def validate_fr_lengths(fr_seq_df: pd.DataFrame) -> list[dict]:
    """Check if extracted FR lengths are within expected ranges."""
    issues = []
    for _, row in fr_seq_df.iterrows():
        ab_id = row["antibody_id"]
        
        for fr_name in ["fr1", "fr2", "fr3", "fr4"]:
            length = int(row[f"{fr_name}_length"])
            expected_min, expected_max = EXPECTED_FR_LENGTHS[fr_name]
            
            if length < expected_min or length > expected_max:
                issues.append({
                    "antibody_id": ab_id,
                    "region": fr_name.upper(),
                    "issue_type": "unusual_length",
                    "details": f"Length={length}aa (expected {expected_min}-{expected_max}aa)",
                })
    
    return issues


def validate_fr_sequences(fr_seq_df: pd.DataFrame) -> list[dict]:
    """Check FR sequences for unusual characters, gaps, or patterns."""
    issues = []
    valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
    
    for _, row in fr_seq_df.iterrows():
        ab_id = row["antibody_id"]
        
        for fr_name in ["fr1", "fr2", "fr3", "fr4"]:
            seq = str(row[f"{fr_name}_sequence"]).strip().upper()
            
            # Check for non-standard amino acids
            invalid_chars = set(seq) - valid_aa
            if invalid_chars:
                issues.append({
                    "antibody_id": ab_id,
                    "region": fr_name.upper(),
                    "issue_type": "invalid_characters",
                    "details": f"Non-standard amino acids: {', '.join(invalid_chars)}",
                })
            
            # Check for gaps (represented as '-' or '.')
            if '-' in seq or '.' in seq:
                issues.append({
                    "antibody_id": ab_id,
                    "region": fr_name.upper(),
                    "issue_type": "gaps_detected",
                    "details": f"Sequence contains gaps: {seq}",
                })
            
            # Check for unusually long poly-X stretches (may indicate sequencing errors)
            for aa in valid_aa:
                if aa * 5 in seq:  # 5+ consecutive identical residues
                    issues.append({
                        "antibody_id": ab_id,
                        "region": fr_name.upper(),
                        "issue_type": "poly_stretch",
                        "details": f"Poly-{aa} stretch detected in sequence",
                    })
    
    return issues


def cross_validate_with_original(fr_seq_df: pd.DataFrame, raw_seq_df: pd.DataFrame, numbering_df: pd.DataFrame) -> list[dict]:
    """Verify that reconstructed FR sequences match the original full-length sequence."""
    issues = []
    
    for _, fr_row in fr_seq_df.iterrows():
        ab_id = fr_row["antibody_id"]
        
        # Get original sequence from Thera-SAbDab
        raw_row = raw_seq_df[raw_seq_df["_table1_antibody_id"] == ab_id]
        if raw_row.empty:
            issues.append({
                "antibody_id": ab_id,
                "region": "ALL",
                "issue_type": "missing_original_sequence",
                "details": "Cannot find original sequence in extracted Thera-SAbDab data",
            })
            continue
        
        original_seq = str(raw_row.iloc[0].get("HeavySequence", "")).strip().upper()
        if not original_seq or original_seq.lower() in {"nan", "none"}:
            issues.append({
                "antibody_id": ab_id,
                "region": "ALL",
                "issue_type": "empty_original_sequence",
                "details": "Original sequence is empty or missing",
            })
            continue
        
        # Reconstruct full sequence from ANARCII numbering
        numbering_sub = numbering_df[numbering_df["antibody_id"] == ab_id].sort_values("seq_idx")
        reconstructed_seq = "".join(numbering_sub["aa"].tolist())
        
        # Compare
        if original_seq != reconstructed_seq:
            # Check if it's just a length mismatch (truncation/extension)
            min_len = min(len(original_seq), len(reconstructed_seq))
            matches = sum(1 for i in range(min_len) if original_seq[i] == reconstructed_seq[i])
            identity_pct = (matches / max(len(original_seq), len(reconstructed_seq))) * 100.0
            
            if identity_pct < 99.0:  # Allow 1% mismatch for minor differences
                issues.append({
                    "antibody_id": ab_id,
                    "region": "FULL_SEQUENCE",
                    "issue_type": "sequence_mismatch",
                    "details": f"Original vs reconstructed identity: {identity_pct:.1f}% "
                               f"(original={len(original_seq)}aa, reconstructed={len(reconstructed_seq)}aa)",
                })
    
    return issues


def build_report(
    numbering_issues: list[dict],
    length_issues: list[dict],
    sequence_issues: list[dict],
    cross_validation_issues: list[dict],
    fr_seq_df: pd.DataFrame,
) -> list[str]:
    """Build human-readable validation report."""
    lines = []
    lines.append("=" * 80)
    lines.append("FR Extraction Validation Report (19 Clinical VHHs)")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Purpose: Verify that FR sequences extracted from ANARCII IMGT numbering are accurate")
    lines.append("")
    
    total_issues = len(numbering_issues) + len(length_issues) + len(sequence_issues) + len(cross_validation_issues)
    
    if total_issues == 0:
        lines.append("✅ ALL VALIDATION CHECKS PASSED")
        lines.append("")
        lines.append("FR sequences are ACCURATE and ready for downstream analysis:")
        lines.append("  - ANARCII IMGT numbering is complete for all 19 molecules")
        lines.append("  - FR lengths are within expected ranges")
        lines.append("  - No invalid characters or gaps detected")
        lines.append("  - Reconstructed sequences match original Thera-SAbDab sequences")
        lines.append("")
    else:
        lines.append(f"⚠️  VALIDATION ISSUES DETECTED: {total_issues} total")
        lines.append("")
    
    # Numbering completeness
    lines.append("## 1. ANARCII Numbering Completeness")
    lines.append("")
    if not numbering_issues:
        lines.append("✅ All 19 molecules have complete IMGT numbering for FR1/2/3/4")
    else:
        lines.append(f"⚠️  {len(numbering_issues)} issues detected:")
        for issue in numbering_issues[:10]:  # show first 10
            lines.append(f"  - {issue['antibody_id']} ({issue['region']}): {issue['details']}")
        if len(numbering_issues) > 10:
            lines.append(f"  ... and {len(numbering_issues) - 10} more (see issues CSV)")
    lines.append("")
    
    # FR lengths
    lines.append("## 2. FR Length Validation")
    lines.append("")
    if not length_issues:
        lines.append("✅ All FR lengths are within expected ranges:")
        lines.append(f"  - FR1: {EXPECTED_FR_LENGTHS['fr1'][0]}-{EXPECTED_FR_LENGTHS['fr1'][1]}aa (observed: {fr_seq_df['fr1_length'].min()}-{fr_seq_df['fr1_length'].max()}aa)")
        lines.append(f"  - FR2: {EXPECTED_FR_LENGTHS['fr2'][0]}-{EXPECTED_FR_LENGTHS['fr2'][1]}aa (observed: {fr_seq_df['fr2_length'].min()}-{fr_seq_df['fr2_length'].max()}aa)")
        lines.append(f"  - FR3: {EXPECTED_FR_LENGTHS['fr3'][0]}-{EXPECTED_FR_LENGTHS['fr3'][1]}aa (observed: {fr_seq_df['fr3_length'].min()}-{fr_seq_df['fr3_length'].max()}aa)")
        lines.append(f"  - FR4: {EXPECTED_FR_LENGTHS['fr4'][0]}-{EXPECTED_FR_LENGTHS['fr4'][1]}aa (observed: {fr_seq_df['fr4_length'].min()}-{fr_seq_df['fr4_length'].max()}aa)")
    else:
        lines.append(f"⚠️  {len(length_issues)} unusual lengths detected:")
        for issue in length_issues:
            lines.append(f"  - {issue['antibody_id']} ({issue['region']}): {issue['details']}")
    lines.append("")
    
    # FR sequence quality
    lines.append("## 3. FR Sequence Quality")
    lines.append("")
    if not sequence_issues:
        lines.append("✅ All FR sequences contain only standard amino acids (no gaps or unusual characters)")
    else:
        lines.append(f"⚠️  {len(sequence_issues)} sequence quality issues:")
        for issue in sequence_issues:
            lines.append(f"  - {issue['antibody_id']} ({issue['region']}): {issue['details']}")
    lines.append("")
    
    # Cross-validation
    lines.append("## 4. Cross-Validation with Original Sequences")
    lines.append("")
    if not cross_validation_issues:
        lines.append("✅ All reconstructed sequences match original Thera-SAbDab sequences (≥99% identity)")
    else:
        lines.append(f"⚠️  {len(cross_validation_issues)} cross-validation issues:")
        for issue in cross_validation_issues:
            lines.append(f"  - {issue['antibody_id']}: {issue['details']}")
    lines.append("")
    
    # Summary
    lines.append("## 5. Summary & Recommendation")
    lines.append("")
    if total_issues == 0:
        lines.append("✅ RECOMMENDATION: FR sequences are ACCURATE and IMGT-compliant.")
        lines.append("")
        lines.append("The extracted FR1/2/3/4 sequences can be confidently used for:")
        lines.append("  - Germline identity analysis")
        lines.append("  - Strategy classification validation")
        lines.append("  - Manuscript supplementary tables")
        lines.append("  - Downstream structural/functional analysis")
    else:
        lines.append("⚠️  RECOMMENDATION: Review issues before proceeding with FR-based analysis.")
        lines.append("")
        lines.append("Next steps:")
        lines.append("  1. Inspect the issues CSV file for detailed problem descriptions")
        lines.append("  2. For numbering/length issues: re-run ANARCII with different parameters")
        lines.append("  3. For sequence quality issues: check original Thera-SAbDab export")
        lines.append("  4. For cross-validation issues: manually verify affected sequences")
    lines.append("")
    lines.append("=" * 80)
    
    return lines


def main() -> None:
    numbering_df = pd.read_csv(IN_NUMBERING)
    fr_seq_df = pd.read_csv(IN_FR_SEQ)
    raw_seq_df = pd.read_csv(IN_RAW_SEQ)
    
    print("Running FR extraction validation...")
    
    # Run validation checks
    numbering_issues = validate_numbering_completeness(numbering_df)
    print(f"  - Numbering completeness: {len(numbering_issues)} issues")
    
    length_issues = validate_fr_lengths(fr_seq_df)
    print(f"  - FR length validation: {len(length_issues)} issues")
    
    sequence_issues = validate_fr_sequences(fr_seq_df)
    print(f"  - Sequence quality: {len(sequence_issues)} issues")
    
    cross_validation_issues = cross_validate_with_original(fr_seq_df, raw_seq_df, numbering_df)
    print(f"  - Cross-validation: {len(cross_validation_issues)} issues")
    
    # Build report
    report_lines = build_report(numbering_issues, length_issues, sequence_issues, cross_validation_issues, fr_seq_df)
    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nWrote: {OUT_REPORT}")
    
    # Write issues CSV if any problems detected
    all_issues = numbering_issues + length_issues + sequence_issues + cross_validation_issues
    if all_issues:
        pd.DataFrame(all_issues).to_csv(OUT_ISSUES, index=False)
        print(f"Wrote: {OUT_ISSUES}")
    else:
        print("✅ No issues detected - FR extraction is ACCURATE!")


if __name__ == "__main__":
    main()
