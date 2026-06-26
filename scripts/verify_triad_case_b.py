#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Triad Case B 
"""

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    csv_path = PROJECT_ROOT / "output" / "vhh_triad_ranking_debug.csv"
    md_path = PROJECT_ROOT / "output" / "vhh_triad_ranking_summary.md"
    
    print("=" * 80)
    print(" Triad Case B ")
    print("=" * 80)
    print()
    
    # CSV
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        
        case_b_rows = [r for r in rows if r["source_library"] == "human_vh3_scaffolds"]
        print(f"Case B : {len(case_b_rows)}")
        print(f"Case B hallmark_available=1: {sum(1 for r in case_b_rows if r['hallmark_available'] == '1')}")
        print(f"Case B hallmark_available=0: {sum(1 for r in case_b_rows if r['hallmark_available'] == '0')}")
        print()
        print("Case B 3:")
        for i, r in enumerate(case_b_rows[:3], 1):
            print(f"  {i}. {r['scaffold_id']}, FI={r['framework_identity']}, Proxy={r['proxy_agg']}, Hallmark={r['vhh_hallmark_score'] or 'N/A'}")
    else:
        print(f"❌ CSV: {csv_path}")
    
    print()
    
    # MD
    if md_path.exists():
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "Case B (VH3) lacks hallmark; compare using total_score_norm." in content:
            print("✅ Summary MD ")
        else:
            print("❌ Summary MD ")
        
        if "## Case B" in content:
            print("✅ Summary MD  Case B ")
        else:
            print("❌ Summary MD  Case B ")
    else:
        print(f"❌ Summary MD: {md_path}")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()










