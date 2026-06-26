#!/usr/bin/env python3
"""
build_atlas_structure_summary.py
=================================

Consolidate structure data from 840_combined_assessment.csv into a single
atlas_structure_summary.json with normalized fields for:
- PDB path, source (experimental/engineered/predicted)
- VH-VL angle, RMSD statistics
- Structure quality indicators

Output: data/humanization_assay/atlas_structure_summary.json

Usage:
  python scripts/build_atlas_structure_summary.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd

SUITE = Path(__file__).resolve().parents[1]


def main() -> int:
    print("[atlas] Loading 840 antibody structure data...")
    
    # Read 840 dataset
    data_path = SUITE / "data" / "humanization_assay" / "842_combined_assessment.csv"
    df = pd.read_csv(data_path)
    
    print(f"  Loaded {len(df)} records")
    
    # Build summary
    summary: Dict[str, Any] = {
        "_meta": {
            "version": "1.0",
            "generated_date": "2026-04-18",
            "source": "842_combined_assessment.csv",
            "n_antibodies": len(df),
            "fields": ["antibody_id", "origin", "pdb_path", "vh_vl_angle_deg", "interface_metrics", "structure_errors"],
            "notes": "Consolidation of structure metrics for offline QC, benchmarking, and clinical analysis",
        },
        "antibodies": [],
        "statistics": {
            "n_with_pdb_path": 0,
            "n_with_angle_data": 0,
            "n_with_errors": 0,
            "origins": {},
        }
    }
    
    for idx, row in df.iterrows():
        ab_id = row.get("antibody_id", f"ab_{idx}")
        origin = row.get("origin", "unknown")
        pdb_path = row.get("pdb_path")
        
        entry: Dict[str, Any] = {
            "antibody_id": ab_id,
            "origin": origin,
            "pdb_path": pdb_path,
        }
        
        # VH-VL angle
        if pd.notna(row.get("vh_vl_angle_deg")):
            entry["vh_vl_angle_deg"] = round(float(row["vh_vl_angle_deg"]), 2)
            summary["statistics"]["n_with_angle_data"] += 1
        
        # Interface metrics
        interface_metrics: Dict[str, Any] = {}
        for col in ["interface_n_pairs", "interface_mean_dist_A", "interface_min_dist_A", "vernier_sasa_total"]:
            if pd.notna(row.get(col)):
                interface_metrics[col] = round(float(row[col]), 4) if row[col] != int(row[col]) else int(row[col])
        if interface_metrics:
            entry["interface_metrics"] = interface_metrics
        
        # Structure errors
        if pd.notna(row.get("structure_errors")) and row["structure_errors"]:
            entry["structure_errors"] = str(row["structure_errors"])
            summary["statistics"]["n_with_errors"] += 1
        
        if pdb_path:
            summary["statistics"]["n_with_pdb_path"] += 1
        
        # Track origins
        if origin not in summary["statistics"]["origins"]:
            summary["statistics"]["origins"][origin] = 0
        summary["statistics"]["origins"][origin] += 1
        
        summary["antibodies"].append(entry)
    
    # Write output
    out_path = SUITE / "data" / "humanization_assay" / "atlas_structure_summary.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    
    print(f"\n[atlas] Written {out_path}")
    print(f"  Total antibodies: {len(summary['antibodies'])}")
    print(f"  With PDB path: {summary['statistics']['n_with_pdb_path']}")
    print(f"  With angle data: {summary['statistics']['n_with_angle_data']}")
    print(f"  With structure errors: {summary['statistics']['n_with_errors']}")
    print(f"  Origins: {summary['statistics']['origins']}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
