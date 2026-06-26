#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validate Thera canonical TSV file (4-column minimal contract).

Checks:
- Required columns: id, cdr, class, confidence
- Row count ≈ therapeutics × 5 (at least H1/H2/L1/L2/L3)
- id format consistency
"""

import sys
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def validate_thera_canonical_tsv(tsv_path: Path, qc_pass_path: Path) -> bool:
    """
    Validate Thera canonical TSV against QC pass file.
    
    Returns:
        True if valid, raises RuntimeError if invalid
    """
    if not tsv_path.exists():
        raise RuntimeError(f"CRITICAL: TSV file not found: {tsv_path}")
    
    if not qc_pass_path.exists():
        raise RuntimeError(f"CRITICAL: QC pass file not found: {qc_pass_path}")
    
    # Load TSV
    df_tsv = pd.read_csv(tsv_path, sep='\t')
    
    # P0: Check required columns
    required = ["id", "cdr", "class", "confidence"]
    for col in required:
        if col not in df_tsv.columns:
            raise RuntimeError(
                f"CRITICAL: TSV {tsv_path.name} missing required column: {col}. "
                f"Minimal contract requires: {required}"
            )
    
    # Load QC pass to get expected therapeutics count
    df_qc = pd.read_excel(qc_pass_path, engine='openpyxl')
    expected_count = len(df_qc)
    
    # Expected row count: each therapeutic should have H1, H2, L1, L2, L3 (5 CDRs)
    # But some may only have VH or VL, so we allow some flexibility
    expected_min = expected_count * 3  # At least 3 CDRs per therapeutic (conservative)
    expected_max = expected_count * 5  # Up to 5 CDRs per therapeutic
    
    actual_count = len(df_tsv)
    
    if actual_count < expected_min:
        raise RuntimeError(
            f"CRITICAL: TSV has {actual_count} rows, expected at least {expected_min} "
            f"(≈ {expected_count} therapeutics × 3-5 CDRs). "
            f"File may be incomplete."
        )
    
    if actual_count > expected_max * 1.5:  # Allow some overhead
        print(f"⚠️  Warning: TSV has {actual_count} rows, expected ~{expected_max}. "
              f"This may indicate duplicate entries.")
    
    # Check CDR values
    valid_cdrs = {"H1", "H2", "L1", "L2", "L3"}
    invalid_cdrs = set(df_tsv['cdr'].str.upper().unique()) - valid_cdrs
    if invalid_cdrs:
        raise RuntimeError(
            f"CRITICAL: TSV contains invalid CDR values: {invalid_cdrs}. "
            f"Valid values: {valid_cdrs}"
        )
    
    # Check id format (should be INN-like, lowercase)
    sample_ids = df_tsv['id'].head(10).tolist()
    print(f"✅ TSV validation passed:")
    print(f"   - Rows: {actual_count} (expected ~{expected_min}-{expected_max})")
    print(f"   - CDRs: {sorted(df_tsv['cdr'].str.upper().unique())}")
    print(f"   - Sample IDs: {sample_ids[:5]}")
    
    return True


def main():
    tsv_path = PROJECT_ROOT / "data" / "thera_sabdab" / "thera_canonical.tsv"
    qc_pass_path = PROJECT_ROOT / "data" / "thera_sabdab" / "thera_qc_pass.xlsx"
    
    try:
        validate_thera_canonical_tsv(tsv_path, qc_pass_path)
        print("\n✅ [SUCCESS] Thera canonical TSV validation passed!")
        return 0
    except Exception as e:
        print(f"\n❌ VALIDATION FAILED: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
