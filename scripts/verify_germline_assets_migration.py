#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Germline Assets 

 output/  data/germlines/v1_clean/
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.germline_assets_loader import (
    validate_germline_assets_directory,
    load_manifest,
    load_all_clean_germline_assets,
    load_canonical_proxy_lookup,
)

def main():
    print("=" * 80)
    print(" Germline Assets ")
    print("=" * 80)
    print()
    
    # 1. 
    print("[1] ...")
    is_valid, errors = validate_germline_assets_directory()
    if is_valid:
        print("  ✅ ")
    else:
        print(f"  ❌  {len(errors)} :")
        for error in errors:
            print(f"    - {error}")
        return
    print()
    
    # 2.  manifest
    print("[2]  manifest.json...")
    try:
        manifest = load_manifest()
        print(f"  ✅ : {manifest['version']}")
        print(f"  ✅ : {manifest['description']}")
        print(f"  ✅ : {manifest['statistics']['total_clean_records']}")
        print(f"  ✅ CDR1 clusters: {manifest['statistics']['cdr1_clusters']}")
        print(f"  ✅ CDR2 clusters: {manifest['statistics']['cdr2_clusters']}")
    except Exception as e:
        print(f"  ❌ : {e}")
        return
    print()
    
    # 3.  clean assets
    print("[3]  clean assets...")
    try:
        assets = load_all_clean_germline_assets(include_canonical_proxy=False)
        print(f"  ✅ : {len(assets)} ")
    except Exception as e:
        print(f"  ❌ : {e}")
        return
    print()
    
    # 4.  proxy assets
    print("[4]  proxy assets...")
    try:
        assets_with_proxy = load_all_clean_germline_assets(include_canonical_proxy=True)
        print(f"  ✅ : {len(assets_with_proxy)} ")
        if assets_with_proxy:
            first = assets_with_proxy[0]
            if "canonical_proxy_cdr1" in first:
                print(f"  ✅  canonical_proxy ")
    except Exception as e:
        print(f"  ❌ : {e}")
        return
    print()
    
    # 5.  lookup table
    print("[5]  canonical_proxy_lookup...")
    try:
        lookup = load_canonical_proxy_lookup()
        cdr1_count = len(lookup.get("CDR1", {}))
        cdr2_count = len(lookup.get("CDR2", {}))
        print(f"  ✅ CDR1 lookup: {cdr1_count} ")
        print(f"  ✅ CDR2 lookup: {cdr2_count} ")
    except Exception as e:
        print(f"  ❌ : {e}")
        return
    print()
    
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)
    print()
    print(":")
    print("  ✅ ")
    print("  ✅ ")
    print("  ✅ ")
    print()
    print(" core.germline_assets_loader ")
    print(" data/germlines/v1_clean/  germline ")

if __name__ == "__main__":
    main()













