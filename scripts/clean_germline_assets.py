#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 germline （ FR1/CDR1/FR2/CDR2/FR3 ）

（）：
- success_flags.imgt_success == true  success_flags.kabat_success == true
- segments.FR1, CDR1, FR2, CDR2, FR3  > 0
-  segments  20AA（ X/*/-）
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#  20 
STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")


def check_standard_aa_only(seq: str) -> bool:
    """
     20 
    
    Args:
        seq: 
    
    Returns:
        True  AA，False 
    """
    if not seq:
        return False
    return all(c in STANDARD_AA for c in seq.upper())


def validate_germline_record(record: Dict[str, Any]) -> Tuple[bool, str]:
    """
     germline 
    
    Returns:
        (is_valid, reason)
        is_valid: True ，False 
        reason:  is_valid=False，； is_valid=True，
    """
    #  1: IMGT  Kabat 
    success_flags = record.get("success_flags", {})
    imgt_success = success_flags.get("imgt_numbering", False)
    kabat_success = success_flags.get("kabat_numbering", False)
    
    if not imgt_success:
        return False, "imgt_numbering_failed"
    
    if not kabat_success:
        return False, "kabat_numbering_failed"
    
    #  2: segments  > 0
    segments = record.get("segments", {})
    required_regions = ["FR1", "CDR1", "FR2", "CDR2", "FR3"]
    
    for region in required_regions:
        if region not in segments:
            return False, f"missing_segment_{region}"
        
        region_seq = segments[region]
        if not region_seq or len(region_seq) == 0:
            return False, f"empty_segment_{region}"
    
    #  3:  AA
    # ：record ， segments 
    #  segments 
    
    #  segments  AA
    for region in required_regions:
        region_seq = segments[region]
        if not check_standard_aa_only(region_seq):
            non_standard = [c for c in set(region_seq.upper()) if c not in STANDARD_AA]
            return False, f"non_standard_aa_in_{region}:{','.join(non_standard)}"
    
    #  4:  record ，
    # ：JSONL ，
    #  imgt_map  kabat_map 
    
    # 
    return True, ""


def main():
    parser = argparse.ArgumentParser(
        description=" germline （ FR1/CDR1/FR2/CDR2/FR3 ）"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "output" / "germline_numbering_segments.jsonl",
        help=" JSONL ",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" germline ")
    print("=" * 80)
    print()
    
    # 1.  JSONL
    print(f"[1/4]  JSONL: {args.input}")
    if not args.input.exists():
        print(f"  ❌ : {args.input}")
        return
    
    records = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    
    print(f"  ✅  {len(records)} ")
    print()
    
    # 2. 
    print(f"[2/4]  {len(records)} ...")
    clean_records = []
    dropped_records = []
    
    for record in records:
        is_valid, reason = validate_germline_record(record)
        
        if is_valid:
            #  qa_status 
            record["qa_status"] = "PASS_CLEAN"
            clean_records.append(record)
        else:
            dropped_records.append({
                "sequence_id": record.get("sequence_id", "unknown"),
                "reason": reason,
            })
    
    print(f"  ✅ : PASS {len(clean_records)} , DROP {len(dropped_records)} ")
    print()
    
    # 3.  DROP 
    print("[3/4] DROP ...")
    drop_reasons = Counter(r["reason"] for r in dropped_records)
    for reason, count in sorted(drop_reasons.items()):
        print(f"  {reason}: {count} ")
    print()
    
    # 4. 
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    #  clean JSONL
    clean_jsonl_path = args.output_dir / "germline_assets_clean.jsonl"
    print(f"[4/4]  clean JSONL: {clean_jsonl_path}")
    with open(clean_jsonl_path, "w", encoding="utf-8") as f:
        for record in clean_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  ✅  {len(clean_records)}  clean ")
    
    #  dropped CSV
    dropped_csv_path = args.output_dir / "germline_assets_dropped.csv"
    print(f"   dropped CSV: {dropped_csv_path}")
    with open(dropped_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sequence_id", "reason"])
        writer.writeheader()
        writer.writerows(dropped_records)
    print(f"  ✅  {len(dropped_records)}  dropped ")
    print()
    
    # 5. 
    print("=" * 80)
    print("")
    print("=" * 80)
    print(f"✅ PASS: {len(clean_records)} ")
    print(f"❌ DROP: {len(dropped_records)} ")
    print()
    print("DROP :")
    for reason, count in sorted(drop_reasons.items()):
        print(f"  {reason}: {count} ")
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()













