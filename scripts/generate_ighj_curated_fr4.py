#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 curated  IGHJ1-6 FR4 

 N-term + FR4  JSON 。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 
CURATED_DATA = {
    "IGHJ1": {
        "cdr3_nterm_aa": "AEYFQH",
        "fr4_aa": "WGQGTLVTVSS",
    },
    "IGHJ2": {
        "cdr3_nterm_aa": "YWYFDL",
        "fr4_aa": "WGRGTLVTVSS",
    },
    "IGHJ3": {
        "cdr3_nterm_aa": "AFDV",
        "fr4_aa": "WGQGTMVTVSS",
    },
    "IGHJ4": {
        "cdr3_nterm_aa": "YFDY",
        "fr4_aa": "WGQGTLVTVSS",
    },
    "IGHJ5": {
        "cdr3_nterm_aa": "NWFDP",
        "fr4_aa": "WGQGTLVTVSS",
    },
    "IGHJ6": {
        "cdr3_nterm_aa": "YYYYYGMDV",
        "fr4_aa": "WGQGTTVTVSS",
    },
}


def generate_curated_fr4_json() -> dict:
    """
     curated FR4 JSON 
    
    Returns:
        {ighj_id: {gene, allele, cdr3_nterm_aa, fr4_aa, fr4_motif_4aa, fr4_len, source}}
    """
    result = {}
    source = "curated_functional_set_user_provided_2025-12-13"
    
    for gene, data in CURATED_DATA.items():
        ighj_id = f"{gene}*01"
        fr4_aa = data["fr4_aa"]
        
        result[ighj_id] = {
            "gene": gene,
            "allele": "01",
            "cdr3_nterm_aa": data["cdr3_nterm_aa"],
            "fr4_aa": fr4_aa,
            "fr4_motif_4aa": fr4_aa[:4],
            "fr4_len": len(fr4_aa),
            "source": source,
        }
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description=" curated  IGHJ1-6 FR4 "
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "ighj_curated_fr4.json",
        help=" JSON ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" curated  IGHJ1-6 FR4 ")
    print("=" * 80)
    print()
    
    # 
    print("[1/2]  curated FR4 ...")
    curated_data = generate_curated_fr4_json()
    print(f"  ✅  {len(curated_data)} ")
    print()
    
    #  JSON
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[2/2]  JSON : {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(curated_data, f, indent=2, ensure_ascii=False)
    print(f"  ✅ ")
    print()
    
    # 
    print("=" * 80)
    print("")
    print("=" * 80)
    for ighj_id in sorted(curated_data.keys()):
        entry = curated_data[ighj_id]
        print(f"{ighj_id}:")
        print(f"  CDR3 N-term: {entry['cdr3_nterm_aa']}")
        print(f"  FR4: {entry['fr4_aa']} (len={entry['fr4_len']}, motif={entry['fr4_motif_4aa']})")
    print()
    
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()













