#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH 
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    print("=" * 80)
    print(" VHH ")
    print("=" * 80)
    print()
    
    # 
    files_to_check = {
        "vhh_scaffold_library_v1.jsonl": PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_scaffold_library_v1.jsonl",
        "vhh_special_fr_templates_v1.jsonl": PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_special_fr_templates_v1.jsonl",
        "vhh_special_fr_templates_v1_summary.csv": PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "qc" / "vhh_special_fr_templates_v1_summary.csv",
    }
    
    print(":")
    all_exist = True
    for name, path in files_to_check.items():
        exists = path.exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {name}: {path}")
        if not exists:
            all_exist = False
    
    print()
    
    #  manifest.json
    manifest_path = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        vhh_assets = manifest.get("vhh_assets", {})
        if vhh_assets:
            print("✅ manifest.json  vhh_assets ")
            print(f"  scaffold_library: {vhh_assets.get('scaffold_library')}")
            print(f"  special_fr_templates: {vhh_assets.get('special_fr_templates')}")
        else:
            print("❌ manifest.json  vhh_assets ")
    else:
        print("❌ manifest.json ")
    
    print()
    print("=" * 80)
    
    if all_exist:
        print("✅ ")
    else:
        print("❌ ")

if __name__ == "__main__":
    main()










