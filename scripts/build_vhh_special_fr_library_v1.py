#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH Special FR Library v1

 vhh_germline_assets_clean_with_canonical_proxy.jsonl  VHH 。

：
1.  proxy_agg = min(proxy_cdr1, proxy_cdr2)
2. ：vhh_like  (ambiguous AND score >= 0.5) AND proxy_agg >= 0.80
3.  fr_sequence ，
4.  fr_id
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def calculate_proxy_agg(record: Dict[str, Any]) -> float:
    """
     proxy_agg = min(proxy_cdr1, proxy_cdr2)
    
    Args:
        record: germline 
    
    Returns:
        proxy_agg (0.0-1.0)
    """
    proxy_cdr1 = record.get("canonical_proxy_cdr1", {})
    proxy_cdr2 = record.get("canonical_proxy_cdr2", {})
    
    score1 = proxy_cdr1.get("proxy_score", 0.0) if isinstance(proxy_cdr1, dict) else 0.0
    score2 = proxy_cdr2.get("proxy_score", 0.0) if isinstance(proxy_cdr2, dict) else 0.0
    
    return min(score1, score2)


def get_fr_sequence(record: Dict[str, Any]) -> str:
    """
     FR ：FR1 + FR2 + FR3
    
    Args:
        record: germline 
    
    Returns:
        fr_sequence
    """
    segments = record.get("segments", {})
    fr1 = segments.get("FR1", "")
    fr2 = segments.get("FR2", "")
    fr3 = segments.get("FR3", "")
    return fr1 + fr2 + fr3


def passes_filter(record: Dict[str, Any], proxy_agg: float) -> bool:
    """
    
    
    ：
    - (vhh_hallmark.label == "vhh_like" OR (vhh_hallmark.label == "ambiguous" AND vhh_hallmark.score >= 0.5))
    - AND proxy_agg >= 0.80
    
    Args:
        record: germline 
        proxy_agg:  proxy_agg
    
    Returns:
        True 
    """
    #  proxy_agg
    if proxy_agg < 0.80:
        return False
    
    #  vhh_hallmark
    vhh_hallmark = record.get("vhh_hallmark", {})
    if not vhh_hallmark:
        return False
    
    label = vhh_hallmark.get("label", "")
    score = vhh_hallmark.get("score", 0.0)
    
    # ：vhh_like  (ambiguous AND score >= 0.5)
    if label == "vhh_like":
        return True
    elif label == "ambiguous" and score >= 0.5:
        return True
    
    return False


def select_representative(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
     fr_sequence 
    
    （）：
    a) proxy_agg 
    b) vhh_hallmark.score 
    c) sequence_id 
    
    Args:
        records:  fr_sequence 
    
    Returns:
        
    """
    #  proxy_agg
    records_with_agg = []
    for record in records:
        proxy_agg = calculate_proxy_agg(record)
        vhh_hallmark = record.get("vhh_hallmark", {})
        hallmark_score = vhh_hallmark.get("score", 0.0) if vhh_hallmark else 0.0
        sequence_id = record.get("sequence_id", "")
        
        records_with_agg.append({
            "record": record,
            "proxy_agg": proxy_agg,
            "hallmark_score": hallmark_score,
            "sequence_id": sequence_id,
        })
    
    # ：proxy_agg  -> hallmark_score  -> sequence_id 
    records_with_agg.sort(
        key=lambda x: (-x["proxy_agg"], -x["hallmark_score"], x["sequence_id"])
    )
    
    return records_with_agg[0]["record"]


def main():
    parser = argparse.ArgumentParser(
        description=" VHH Special FR Library v1"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean_with_canonical_proxy.jsonl",
        help=" canonical_proxy  JSONL ",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_special_fr_library_v1.jsonl",
        help=" scaffold  JSONL ",
    )
    parser.add_argument(
        "--qc_csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "qc" / "vhh_special_fr_library_v1_summary.csv",
        help=" QC CSV ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" VHH Special FR Library v1")
    print("=" * 80)
    print()
    
    if not args.input.exists():
        print(f"❌ : {args.input}")
        return
    
    # Step 1: 
    print(f"[1/6] : {args.input}")
    all_records = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                all_records.append(json.loads(line))
    
    input_count = len(all_records)
    print(f"  ✅  {input_count} ")
    print()
    
    # Step 2:  proxy_agg 
    print(f"[2/6]  proxy_agg ...")
    candidates = []
    proxy_agg_values = []
    
    for record in all_records:
        proxy_agg = calculate_proxy_agg(record)
        proxy_agg_values.append(proxy_agg)
        
        if passes_filter(record, proxy_agg):
            candidates.append(record)
    
    candidate_count = len(candidates)
    print(f"  ✅ : {candidate_count} ()")
    print()
    
    # Step 3:  fr_sequence 
    print(f"[3/6]  fr_sequence ...")
    fr_sequence_groups = defaultdict(list)
    
    for record in candidates:
        fr_sequence = get_fr_sequence(record)
        fr_sequence_groups[fr_sequence].append(record)
    
    print(f"  ✅ : {len(fr_sequence_groups)}  FR ")
    print()
    
    # Step 4: 
    print(f"[4/6] ...")
    representatives = []
    dedup_info = []  #  QC
    
    for fr_sequence, records in fr_sequence_groups.items():
        representative = select_representative(records)
        representatives.append((fr_sequence, representative, len(records)))
        
        # 
        proxy_agg = calculate_proxy_agg(representative)
        dedup_info.append({
            "fr_sequence": fr_sequence,
            "representative": representative,
            "cluster_size": len(records),
            "proxy_agg": proxy_agg,
        })
    
    print(f"  ✅ : {len(representatives)} ")
    print()
    
    # Step 5:  fr_id 
    print(f"[5/6]  fr_id ...")
    output_records = []
    qc_records = []
    
    #  fr_sequence （）
    representatives.sort(key=lambda x: x[0])
    
    for idx, (fr_sequence, representative, cluster_size) in enumerate(representatives, 1):
        fr_id = f"VHH_FR_{idx:04d}"
        
        # 
        sequence_id = representative.get("sequence_id", "")
        segments = representative.get("segments", {})
        vhh_hallmark = representative.get("vhh_hallmark", {})
        canonical_proxy_cdr1 = representative.get("canonical_proxy_cdr1", {})
        canonical_proxy_cdr2 = representative.get("canonical_proxy_cdr2", {})
        proxy_agg = calculate_proxy_agg(representative)
        
        # 
        output_record = {
            "fr_id": fr_id,
            "template_type": "vhh_special_fr",
            "source_sequence_id": sequence_id,
            "fr_sequence": fr_sequence,
            "segments": {
                "FR1": segments.get("FR1", ""),
                "FR2": segments.get("FR2", ""),
                "FR3": segments.get("FR3", ""),
            },
            "vhh_hallmark": vhh_hallmark,
            "canonical_proxy": {
                "cdr1": canonical_proxy_cdr1,
                "cdr2": canonical_proxy_cdr2,
                "agg": round(proxy_agg, 4),
            },
        }
        
        output_records.append(output_record)
        
        # QC 
        qc_records.append({
            "fr_id": fr_id,
            "source_sequence_id": sequence_id,
            "hallmark_label": vhh_hallmark.get("label", ""),
            "hallmark_score": vhh_hallmark.get("score", 0.0),
            "proxy_agg": round(proxy_agg, 4),
            "fr_length": len(fr_sequence),
            "dedup_cluster_size": cluster_size,
        })
    
    print(f"  ✅ : {len(output_records)} ")
    print()
    
    # Step 6: 
    print(f"[6/6] ...")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for record in output_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  ✅  JSONL: {args.output}")
    
    #  QC CSV
    args.qc_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(args.qc_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "fr_id", "source_sequence_id", "hallmark_label", "hallmark_score",
            "proxy_agg", "fr_length", "dedup_cluster_size"
        ])
        writer.writeheader()
        writer.writerows(qc_records)
    print(f"  ✅  QC CSV: {args.qc_csv}")
    print()
    
    # 
    print("=" * 80)
    print("")
    print("=" * 80)
    print(f": {input_count}")
    print(f"（）: {candidate_count}")
    print(f" FR : {len(output_records)}")
    print()
    
    # Hallmark label 
    label_counts = Counter(r["hallmark_label"] for r in qc_records)
    print("Hallmark label :")
    for label, count in sorted(label_counts.items()):
        percentage = count / len(qc_records) * 100 if len(qc_records) > 0 else 0.0
        print(f"  {label}: {count} ({percentage:.1f}%)")
    print()
    
    # Proxy_agg 
    proxy_agg_list = [r["proxy_agg"] for r in qc_records]
    if proxy_agg_list:
        proxy_agg_list_sorted = sorted(proxy_agg_list)
        min_agg = proxy_agg_list_sorted[0]
        median_agg = proxy_agg_list_sorted[len(proxy_agg_list_sorted) // 2]
        max_agg = proxy_agg_list_sorted[-1]
        
        print("Proxy_agg :")
        print(f"  min: {min_agg:.4f}")
        print(f"  median: {median_agg:.4f}")
        print(f"  max: {max_agg:.4f}")
    
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()










