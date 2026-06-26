#!/usr/bin/env python3
"""
compute_canonical_h1_h2_840.py
===============================

Compute real North-style canonical labels (H1-len-class, H2-len-class) for all 840 antibodies
in 842_combined_assessment.csv by:
1. Reading their VH + VL sequence
2. ANARCII IMGT numbering
3. Extracting CDR1 (H1) and CDR2 (H2) lengths
4. Mapping to North canonical labels based on length

Output: canonical_class_840_full.json with per-antibody H1/H2 canonical labels.

Usage:
  python scripts/compute_canonical_h1_h2_840.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict
from collections import defaultdict

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))


def _load_combined_assessment() -> Dict[str, Any]:
    """Load the 840 antibody dataset."""
    import pandas as pd
    path = SUITE / "data" / "humanization_assay" / "842_combined_assessment.csv"
    df = pd.read_csv(path)
    return df


def _number_vh_sequence(seq: str) -> Dict[int, str]:
    """Number a VH sequence using ANARCII, return CDR1/CDR2 lengths in IMGT."""
    from anarcii import Anarcii
    from core.numbering.imgt_anarcii import build_pos_to_aa_map, split_regions
    
    engine = Anarcii()
    result = engine.number([("vh_seq", seq)])
    vh_data = result.get("vh_seq", {})
    
    if not vh_data or not vh_data.get("numbering"):
        return None
    
    rows = vh_data["numbering"]
    regions = split_regions(rows)
    
    return {
        "cdr1_len": len(regions.get("CDR1", "")),
        "cdr2_len": len(regions.get("CDR2", "")),
    }


def north_h1_label(imgt_cdr1_len: int) -> str:
    """Map IMGT CDR1 length to North H1 canonical label."""
    mapping = {
        7: "H1-13-1",   # Most common human
        8: "H1-13-2",   # Less common variant
        9: "H1-14-1",   # Longer
        10: "H1-15-1",  # Rare longer
        5: "H1-11-1",   # Short
        6: "H1-12-1",   # Short variant
    }
    return mapping.get(imgt_cdr1_len, f"H1-{imgt_cdr1_len+6}-?")  # Approximate fallback


def north_h2_label(imgt_cdr2_len: int) -> str:
    """Map IMGT CDR2 length to North H2 canonical label."""
    # IMGT CDR2 is positions 48-56 (9 positions)
    # Human CDR2 typical lengths: 7 (9aa) → H2-9-?, 8 (10aa) → H2-10-?, etc.
    mapping = {
        7: "H2-9-1",    # Most common human
        8: "H2-10-1",   # Common
        9: "H2-11-1",   # Less common
        10: "H2-12-1",  # Longer variants
        6: "H2-8-1",    # Short
    }
    return mapping.get(imgt_cdr2_len, f"H2-{imgt_cdr2_len + 2}-?")  # Approximate fallback


def main() -> int:
    print("[canonical] Loading 840 antibody dataset...")
    df = _load_combined_assessment()
    print(f"  Loaded {len(df)} antibodies")
    
    print("[canonical] Computing H1/H2 North canonical labels...")
    
    output: Dict[str, Any] = {
        "_meta": {
            "version": "1.0",
            "generated_date": "2026-04-18",
            "source": "842_combined_assessment.csv",
            "total_antibodies": len(df),
            "method": "IMGT CDR length → North canonical mapping",
            "notes": "H1/H2 computed from actual IMGT numbering; H3/L1/L2/L3 sourced from existing 840_combined_assessment.csv",
        },
        "antibodies": {},
        "statistics": {
            "h1_distribution": defaultdict(int),
            "h2_distribution": defaultdict(int),
            "numbering_failures": [],
        }
    }
    
    anarcii_failures = 0
    
    for idx, row in df.iterrows():
        ab_id = row.get("antibody_id", f"ab_{idx}")
        vh_seq = row.get("vh_sequence") or row.get("heavy_chain_sequence")
        
        if not vh_seq:
            output["statistics"]["numbering_failures"].append(ab_id)
            anarcii_failures += 1
            continue
        
        try:
            cdr_info = _number_vh_sequence(vh_seq.strip())
            if not cdr_info:
                output["statistics"]["numbering_failures"].append(ab_id)
                anarcii_failures += 1
                continue
            
            h1_label = north_h1_label(cdr_info["cdr1_len"])
            h2_label = north_h2_label(cdr_info["cdr2_len"])
            
            output["antibodies"][ab_id] = {
                "antibody_id": ab_id,
                "origin": row.get("origin", "unknown"),
                "h1_canonical": h1_label,
                "h1_len_imgt": cdr_info["cdr1_len"],
                "h2_canonical": h2_label,
                "h2_len_imgt": cdr_info["cdr2_len"],
                # Retain existing H3/L values if present
                "h3_canonical": row.get("canonical_H3", ""),
                "l1_canonical": row.get("canonical_L1", ""),
                "l2_canonical": row.get("canonical_L2", ""),
                "l3_canonical": row.get("canonical_L3", ""),
            }
            
            output["statistics"]["h1_distribution"][h1_label] += 1
            output["statistics"]["h2_distribution"][h2_label] += 1
            
        except Exception as e:
            output["statistics"]["numbering_failures"].append({
                "antibody_id": ab_id,
                "error": str(e)[:100],
            })
            anarcii_failures += 1
        
        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(df)} antibodies...")
    
    # Convert defaultdicts to regular dicts
    output["statistics"]["h1_distribution"] = dict(output["statistics"]["h1_distribution"])
    output["statistics"]["h2_distribution"] = dict(output["statistics"]["h2_distribution"])
    
    # Summary statistics
    output["statistics"]["success_count"] = len(output["antibodies"])
    output["statistics"]["failure_count"] = anarcii_failures
    
    # Write output
    out_path = SUITE / "data" / "humanization_assay" / "canonical_class_840_full.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    
    print(f"\n[canonical] Written {out_path}")
    print(f"  Success: {output['statistics']['success_count']} / {len(df)}")
    print(f"  Failures: {anarcii_failures}")
    print(f"\n  H1 Distribution:")
    for label, count in sorted(output["statistics"]["h1_distribution"].items()):
        print(f"    {label}: {count}")
    print(f"\n  H2 Distribution:")
    for label, count in sorted(output["statistics"]["h2_distribution"].items()):
        print(f"    {label}: {count}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
