#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH Hallmark 

 vhh_germline_assets_clean.jsonl  VHH hallmark ，
 CSV 。
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def analyze_hallmark_distribution(jsonl_path: Path) -> Dict[str, Any]:
    """
     hallmark 
    
    Returns:
        
    """
    label_counts = Counter()
    score_distribution = []
    position_distribution = {
        "37": Counter(),
        "44": Counter(),
        "45": Counter(),
        "47": Counter(),
    }
    
    total_records = 0
    records_with_hallmark = 0
    
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            record = json.loads(line)
            total_records += 1
            
            vhh_hallmark = record.get("vhh_hallmark")
            if not vhh_hallmark:
                continue
            
            records_with_hallmark += 1
            
            # 
            label = vhh_hallmark.get("label", "unknown")
            label_counts[label] += 1
            
            # 
            score = vhh_hallmark.get("score", 0.0)
            score_distribution.append(score)
            
            # 
            kabat_positions = vhh_hallmark.get("kabat_positions", {})
            for pos in ["37", "44", "45", "47"]:
                aa = kabat_positions.get(pos, "-")
                position_distribution[pos][aa] += 1
    
    return {
        "total_records": total_records,
        "records_with_hallmark": records_with_hallmark,
        "label_counts": dict(label_counts),
        "score_distribution": {
            "min": min(score_distribution) if score_distribution else 0.0,
            "max": max(score_distribution) if score_distribution else 0.0,
            "mean": sum(score_distribution) / len(score_distribution) if score_distribution else 0.0,
            "median": sorted(score_distribution)[len(score_distribution) // 2] if score_distribution else 0.0,
        },
        "position_distribution": {
            pos: dict(aa_counts) for pos, aa_counts in position_distribution.items()
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description=" VHH Hallmark "
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean.jsonl",
        help=" clean germline assets JSONL ",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "qc" / "vhh_hallmark_distribution.csv",
        help=" CSV ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" VHH Hallmark ")
    print("=" * 80)
    print()
    
    if not args.input.exists():
        print(f"  ❌ : {args.input}")
        return
    
    # 
    print(f"[1/2]  hallmark ...")
    stats = analyze_hallmark_distribution(args.input)
    
    print(f"  : {stats['total_records']}")
    print(f"   hallmark : {stats['records_with_hallmark']}")
    print()
    
    print("  :")
    for label, count in sorted(stats["label_counts"].items()):
        percentage = count / stats["records_with_hallmark"] * 100 if stats["records_with_hallmark"] > 0 else 0.0
        print(f"    {label}: {count} ({percentage:.1f}%)")
    print()
    
    print("  :")
    score_dist = stats["score_distribution"]
    print(f"    min: {score_dist['min']:.4f}")
    print(f"    max: {score_dist['max']:.4f}")
    print(f"    mean: {score_dist['mean']:.4f}")
    print(f"    median: {score_dist['median']:.4f}")
    print()
    
    print("  :")
    for pos in ["37", "44", "45", "47"]:
        aa_counts = stats["position_distribution"][pos]
        print(f"     {pos}:")
        for aa, count in sorted(aa_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            percentage = count / stats["records_with_hallmark"] * 100 if stats["records_with_hallmark"] > 0 else 0.0
            print(f"      {aa}: {count} ({percentage:.1f}%)")
    print()
    
    #  CSV
    print(f"[2/2]  CSV...")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        # 
        writer.writerow(["", "", "", ""])
        writer.writerow([])
        writer.writerow([""])
        total = stats["records_with_hallmark"]
        for label, count in sorted(stats["label_counts"].items()):
            percentage = count / total * 100 if total > 0 else 0.0
            writer.writerow([label, "", count, f"{percentage:.2f}%"])
        
        writer.writerow([])
        writer.writerow([""])
        score_dist = stats["score_distribution"]
        writer.writerow(["min", "", "", f"{score_dist['min']:.4f}"])
        writer.writerow(["max", "", "", f"{score_dist['max']:.4f}"])
        writer.writerow(["mean", "", "", f"{score_dist['mean']:.4f}"])
        writer.writerow(["median", "", "", f"{score_dist['median']:.4f}"])
        
        writer.writerow([])
        writer.writerow([""])
        writer.writerow(["", "", "", ""])
        for pos in ["37", "44", "45", "47"]:
            aa_counts = stats["position_distribution"][pos]
            for aa, count in sorted(aa_counts.items(), key=lambda x: x[1], reverse=True):
                percentage = count / total * 100 if total > 0 else 0.0
                writer.writerow([pos, aa, count, f"{percentage:.2f}%"])
    
    print(f"  ✅ : {args.output}")
    print()
    
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()










