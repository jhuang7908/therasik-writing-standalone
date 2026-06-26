#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH Triad Ranking 
"""

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    csv_path = PROJECT_ROOT / "output" / "vhh_triad_ranking_debug.csv"
    md_path = PROJECT_ROOT / "output" / "vhh_triad_ranking_summary.md"
    
    print("=" * 80)
    print(" VHH Triad Ranking ")
    print("=" * 80)
    print()
    
    # CSV
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        
        print(f"CSV : {len(rows)}")
        
        vhh_scaffold = sum(1 for r in rows if r["source_library"] == "vhh_scaffold_library")
        human_vh3 = sum(1 for r in rows if r["source_library"] == "human_vh3_scaffolds")
        special_fr = sum(1 for r in rows if r["source_library"] == "special_fr_templates")
        with_notes = sum(1 for r in rows if r["notes"])
        
        print(f"  vhh_scaffold_library: {vhh_scaffold} ")
        print(f"  human_vh3_scaffolds: {human_vh3} ")
        print(f"  special_fr_templates: {special_fr} ")
        print(f"  notes: {with_notes} ")
        
        if vhh_scaffold == 20 and human_vh3 == 20 and special_fr == 20:
            print("  ✅ 20")
        else:
            print("  ⚠️ ")
    else:
        print(f"❌ CSV: {csv_path}")
    
    print()
    
    # MD
    if md_path.exists():
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "Case A" in content and "Case B" in content and "Case C" in content:
            print("✅ Summary MD case")
        else:
            print("❌ Summary MD case")
    else:
        print(f"❌ Summary MD: {md_path}")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()










