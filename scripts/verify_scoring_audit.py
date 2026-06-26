#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    report_path = PROJECT_ROOT / "output" / "scoring_context_audit.md"
    
    print("=" * 80)
    print("")
    print("=" * 80)
    print()
    
    if report_path.exists():
        content = report_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        
        print(f"✅ : {report_path}")
        print(f"   : {report_path.stat().st_size} bytes")
        print(f"   : {len(lines)} ")
        print()
        
        # 
        sections = [
            "Framework Identity ",
            "Canonical Proxy ",
            "VHH Hallmark ",
            "",
            "",
            "",
            "",
            "",
        ]
        
        print(":")
        for section in sections:
            if section in content:
                print(f"  ✅ {section}")
            else:
                print(f"  ❌ {section} ()")
    else:
        print(f"❌ : {report_path}")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()










