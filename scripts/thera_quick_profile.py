#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/thera_quick_profile.py

Quick profile of Thera-SAbDab export (string statistics only, no ANARCII).
Outputs to stdout and JSON file.

Requirements:
- Must complete in ~10 seconds (string operations only)
- Must output unique_heavy_count / unique_light_count (validation gate)
"""

import sys
import json
import hashlib
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def is_na_value(val: Any) -> bool:
    """Check if value is NA/N/A/empty/null."""
    if pd.isna(val):
        return True
    if not isinstance(val, str):
        return False
    val_lower = val.strip().lower()
    return val_lower in ['', 'na', 'n/a', 'null', 'none', 'nan']


def get_sequence_hash(seq: str) -> str:
    """Get SHA256 hash of stripped sequence for deduplication."""
    if not seq or not isinstance(seq, str):
        return None
    seq_clean = seq.strip().upper()
    if not seq_clean:
        return None
    return hashlib.sha256(seq_clean.encode('utf-8')).hexdigest()


def calculate_length_stats(lengths: List[int]) -> Dict[str, float]:
    """Calculate min, median, p95, max from length list."""
    if not lengths:
        return {"min": 0, "median": 0, "p95": 0, "max": 0}
    
    sorted_lengths = sorted(lengths)
    n = len(sorted_lengths)
    
    stats = {
        "min": float(sorted_lengths[0]),
        "max": float(sorted_lengths[-1]),
        "median": float(sorted_lengths[n // 2] if n % 2 == 1 else (sorted_lengths[n // 2 - 1] + sorted_lengths[n // 2]) / 2),
        "p95": float(sorted_lengths[int(n * 0.95)] if n > 0 else 0)
    }
    return stats


def find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Find first matching column name from candidates."""
    for col in candidates:
        if col in df.columns:
            return col
    return None


def profile_thera_export(xlsx_path: Path, out_json_path: Path) -> Dict[str, Any]:
    """
    Quick profile of Thera-SAbDab export.
    
    Returns profile dictionary with statistics.
    """
    print(f"📖 Loading: {xlsx_path}")
    df = pd.read_excel(xlsx_path, engine='openpyxl')
    n_total = len(df)
    print(f"✅ Loaded {n_total} rows")
    
    # Auto-detect Heavy/Light columns
    vh_cols = ["HeavySequence", "VH", "Heavy", "Heavy sequence", "VH sequence", "VH_sequence", "Heavy_V_Sequence", "Heavy_Sequence"]
    vl_cols = ["LightSequence", "VL", "Light", "Light sequence", "VL sequence", "VL_sequence", "Light_V_Sequence", "Light_Sequence"]
    
    heavy_col = find_column(df, vh_cols)
    light_col = find_column(df, vl_cols)
    
    if not heavy_col:
        raise RuntimeError(f"CRITICAL: Could not find Heavy column. Tried: {vh_cols}")
    if not light_col:
        raise RuntimeError(f"CRITICAL: Could not find Light column. Tried: {vl_cols}")
    
    print(f"✅ Detected columns: Heavy={heavy_col}, Light={light_col}")
    
    # Process Heavy sequences
    print("\n🔬 Analyzing Heavy sequences...")
    heavy_non_empty = 0
    heavy_na_count = 0
    heavy_hashes: Set[str] = set()
    heavy_lengths: List[int] = []
    
    for idx, val in df[heavy_col].items():
        if is_na_value(val):
            heavy_na_count += 1
            continue
        
        seq_str = str(val).strip()
        if seq_str:
            heavy_non_empty += 1
            seq_hash = get_sequence_hash(seq_str)
            if seq_hash:
                heavy_hashes.add(seq_hash)
                heavy_lengths.append(len(seq_str))
    
    # Process Light sequences
    print("🔬 Analyzing Light sequences...")
    light_non_empty = 0
    light_na_count = 0
    light_hashes: Set[str] = set()
    light_lengths: List[int] = []
    
    for idx, val in df[light_col].items():
        if is_na_value(val):
            light_na_count += 1
            continue
        
        seq_str = str(val).strip()
        if seq_str:
            light_non_empty += 1
            seq_hash = get_sequence_hash(seq_str)
            if seq_hash:
                light_hashes.add(seq_hash)
                light_lengths.append(len(seq_str))
    
    # Calculate statistics
    heavy_unique_count = len(heavy_hashes)
    light_unique_count = len(light_hashes)
    
    heavy_length_stats = calculate_length_stats(heavy_lengths)
    light_length_stats = calculate_length_stats(light_lengths)
    
    # Estimate ANARCII calls (unique sequences)
    estimated_anarcii_calls = heavy_unique_count + light_unique_count
    
    # Build profile
    profile = {
        "n_total": n_total,
        "columns": {
            "heavy": heavy_col,
            "light": light_col
        },
        "heavy": {
            "non_empty": heavy_non_empty,
            "na_count": heavy_na_count,
            "unique_count": heavy_unique_count,  # Validation gate: must exist
            "length_stats": heavy_length_stats
        },
        "light": {
            "non_empty": light_non_empty,
            "na_count": light_na_count,
            "unique_count": light_unique_count,  # Validation gate: must exist
            "length_stats": light_length_stats
        },
        "estimated_anarcii_calls": estimated_anarcii_calls
    }
    
    return profile


def print_profile(profile: Dict[str, Any]):
    """Print profile to stdout in human-readable format."""
    print("\n" + "=" * 60)
    print("📊 Thera-SAbDab Export Profile")
    print("=" * 60)
    
    print(f"\n📋 Total rows: {profile['n_total']}")
    print(f"   Columns: Heavy={profile['columns']['heavy']}, Light={profile['columns']['light']}")
    
    print(f"\n🔵 Heavy Chain:")
    print(f"   Non-empty: {profile['heavy']['non_empty']}")
    print(f"   NA/empty: {profile['heavy']['na_count']}")
    print(f"   Unique sequences: {profile['heavy']['unique_count']} ⭐")
    h_len = profile['heavy']['length_stats']
    print(f"   Length: min={h_len['min']:.0f}, median={h_len['median']:.0f}, p95={h_len['p95']:.0f}, max={h_len['max']:.0f}")
    
    print(f"\n🟢 Light Chain:")
    print(f"   Non-empty: {profile['light']['non_empty']}")
    print(f"   NA/empty: {profile['light']['na_count']}")
    print(f"   Unique sequences: {profile['light']['unique_count']} ⭐")
    l_len = profile['light']['length_stats']
    print(f"   Length: min={l_len['min']:.0f}, median={l_len['median']:.0f}, p95={l_len['p95']:.0f}, max={l_len['max']:.0f}")
    
    print(f"\n⚙️  Estimated ANARCII calls: {profile['estimated_anarcii_calls']}")
    print("=" * 60)
    
    # Validation gate check
    if profile['heavy']['unique_count'] == 0 or profile['light']['unique_count'] == 0:
        print("\n❌ VALIDATION FAILED: unique_heavy_count or unique_light_count is 0")
        print("   Cannot proceed to Step 1. Check input data.")
        return False
    else:
        print("\n✅ VALIDATION PASSED: unique counts available")
        print("   Ready for Step 1 (prepare_thera_dataset.py)")
        return True


def main():
    parser = argparse.ArgumentParser(description="Quick profile of Thera-SAbDab export")
    parser.add_argument("--in_xlsx", default="data/thera_sabdab/thera_export.xlsx",
                        help="Input Thera-SAbDab export XLSX file")
    parser.add_argument("--out_json", default="data/thera_sabdab/out/thera_profile.json",
                        help="Output JSON profile file")
    
    args = parser.parse_args()
    
    in_xlsx = Path(args.in_xlsx)
    if not in_xlsx.is_absolute():
        in_xlsx = PROJECT_ROOT / in_xlsx
    
    out_json = Path(args.out_json)
    if not out_json.is_absolute():
        out_json = PROJECT_ROOT / out_json
    
    out_json.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Generate profile
        profile = profile_thera_export(in_xlsx, out_json)
        
        # Print to stdout
        validation_passed = print_profile(profile)
        
        # Write JSON
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2)
        print(f"\n💾 Profile saved to: {out_json}")
        
        # Exit code based on validation
        if not validation_passed:
            sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
