#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH v1 FASTA 

 vhh_special_fr_templates_v1.jsonl  vhh_scaffold_library_v1.jsonl  FASTA 。

：
- data/germlines/vhh_v1/exports/vhh_special_fr_templates_v1.fasta (82)
- data/germlines/vhh_v1/exports/vhh_scaffold_library_v1.fasta (264)
- data/germlines/vhh_v1/exports/vhh_special_fr_templates_v1.tsv (82)
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_framework_sequence(record: Dict[str, Any]) -> str:
    """
    （）
    
    ：
    1. sequence
    2. consensus.framework_full
    3. framework_full
    
    Args:
        record: scaffold 
    
    Returns:
        
    """
    # 1: sequence
    if "sequence" in record:
        return record["sequence"]
    
    # 2: consensus.framework_full
    consensus = record.get("consensus", {})
    if isinstance(consensus, dict) and "framework_full" in consensus:
        return consensus["framework_full"]
    
    # 3: framework_full
    if "framework_full" in record:
        return record["framework_full"]
    
    return ""


def export_special_fr_templates(
    input_path: Path,
    fasta_output_path: Path,
    tsv_output_path: Path,
) -> tuple[int, int]:
    """
     special FR templates
    
    Args:
        input_path:  JSONL 
        fasta_output_path:  FASTA 
        tsv_output_path:  TSV 
    
    Returns:
        (, FASTAbytes)
    """
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    
    #  FASTA
    fasta_lines = []
    tsv_lines = []
    tsv_lines.append("fr_id\tsource_sequence_id\thallmark_label\thallmark_score\tproxy_agg\tfr_length\n")
    
    for record in records:
        fr_id = record.get("fr_id", "UNKNOWN")
        source_sequence_id = record.get("source_sequence_id", "")
        fr_sequence = record.get("fr_sequence", "")
        
        # Hallmark 
        vhh_hallmark = record.get("vhh_hallmark", {})
        hallmark_label = vhh_hallmark.get("label", "na") if isinstance(vhh_hallmark, dict) else "na"
        hallmark_score = vhh_hallmark.get("score", 0.0) if isinstance(vhh_hallmark, dict) else 0.0
        
        # Canonical proxy 
        canonical_proxy = record.get("canonical_proxy", {})
        proxy_agg = canonical_proxy.get("agg", 0.0) if isinstance(canonical_proxy, dict) else 0.0
        
        # FASTA header
        header = f">{fr_id}|source={source_sequence_id}|hallmark={hallmark_label}:{hallmark_score:.2f}|proxy_agg={proxy_agg:.4f}"
        fasta_lines.append(header)
        fasta_lines.append(fr_sequence)
        
        # TSV （：fr_id, source_sequence_id, hallmark_label, hallmark_score, proxy_agg, fr_length）
        tsv_lines.append(f"{fr_id}\t{source_sequence_id}\t{hallmark_label}\t{hallmark_score:.4f}\t{proxy_agg:.4f}\t{len(fr_sequence)}\n")
    
    #  FASTA
    fasta_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(fasta_output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(fasta_lines) + "\n")
    
    fasta_size = fasta_output_path.stat().st_size
    
    #  TSV
    with open(tsv_output_path, "w", encoding="utf-8") as f:
        f.writelines(tsv_lines)
    
    return len(records), fasta_size


def export_scaffold_library(
    input_path: Path,
    fasta_output_path: Path,
) -> tuple[int, int]:
    """
     scaffold library
    
    Args:
        input_path:  JSONL 
        fasta_output_path:  FASTA 
    
    Returns:
        (, FASTAbytes)
    """
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    
    #  FASTA
    fasta_lines = []
    
    for record in records:
        scaffold_id = record.get("scaffold_id", "UNKNOWN")
        
        #  source_sequence_id（ member_ids ）
        member_ids = record.get("member_ids", [])
        origin_sequence_id = member_ids[0] if member_ids else "na"
        
        # 
        framework_sequence = get_framework_sequence(record)
        
        # Canonical proxy 
        canonical_proxy_cdr1 = record.get("canonical_proxy_cdr1", {})
        canonical_proxy_cdr2 = record.get("canonical_proxy_cdr2", {})
        
        #  proxy_agg = min(proxy_cdr1, proxy_cdr2)
        proxy_score1 = canonical_proxy_cdr1.get("proxy_score", 0.0) if isinstance(canonical_proxy_cdr1, dict) else 0.0
        proxy_score2 = canonical_proxy_cdr2.get("proxy_score", 0.0) if isinstance(canonical_proxy_cdr2, dict) else 0.0
        proxy_agg = min(proxy_score1, proxy_score2) if proxy_score1 > 0 and proxy_score2 > 0 else (proxy_score1 if proxy_score1 > 0 else proxy_score2)
        
        # Hallmark 
        vhh_hallmark = record.get("vhh_hallmark", {})
        if isinstance(vhh_hallmark, dict) and vhh_hallmark:
            hallmark_label = vhh_hallmark.get("label", "na")
            hallmark_score = vhh_hallmark.get("score", 0.0)
            hallmark_str = f"{hallmark_label}:{hallmark_score:.2f}"
        else:
            hallmark_str = "na"
        
        # FASTA header
        header = f">{scaffold_id}|source={origin_sequence_id}|proxy_agg={proxy_agg:.4f}|hallmark={hallmark_str}"
        fasta_lines.append(header)
        fasta_lines.append(framework_sequence)
    
    #  FASTA
    fasta_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(fasta_output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(fasta_lines) + "\n")
    
    fasta_size = fasta_output_path.stat().st_size
    
    return len(records), fasta_size


def main():
    parser = argparse.ArgumentParser(
        description=" VHH v1 FASTA "
    )
    parser.add_argument(
        "--templates_jsonl",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_special_fr_templates_v1.jsonl",
        help=" special FR templates JSONL ",
    )
    parser.add_argument(
        "--scaffold_jsonl",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_scaffold_library_v1.jsonl",
        help=" scaffold library JSONL ",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "exports",
        help="",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" VHH v1 FASTA ")
    print("=" * 80)
    print()
    
    # 
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # A)  special FR templates
    print("[A]  special FR templates...")
    if not args.templates_jsonl.exists():
        print(f"  ❌ : {args.templates_jsonl}")
        return
    
    fasta_a_path = args.output_dir / "vhh_special_fr_templates_v1.fasta"
    tsv_path = args.output_dir / "vhh_special_fr_templates_v1.tsv"
    
    count_a, size_a = export_special_fr_templates(
        args.templates_jsonl,
        fasta_a_path,
        tsv_path,
    )
    
    print(f"  ✅  {count_a} ")
    print(f"  ✅ FASTA : {fasta_a_path} ({size_a} bytes)")
    print(f"  ✅ TSV : {tsv_path}")
    print()
    
    # B)  scaffold library
    print("[B]  scaffold library...")
    if not args.scaffold_jsonl.exists():
        print(f"  ❌ : {args.scaffold_jsonl}")
        return
    
    fasta_b_path = args.output_dir / "vhh_scaffold_library_v1.fasta"
    
    count_b, size_b = export_scaffold_library(
        args.scaffold_jsonl,
        fasta_b_path,
    )
    
    print(f"  ✅  {count_b} ")
    print(f"  ✅ FASTA : {fasta_b_path} ({size_b} bytes)")
    print()
    
    # 
    print("=" * 80)
    print("")
    print("=" * 80)
    print(f": {count_a}/{count_b}")
    print(f"FASTA :")
    print(f"  vhh_special_fr_templates_v1.fasta: {size_a} bytes")
    print(f"  vhh_scaffold_library_v1.fasta: {size_b} bytes")
    print()
    
    #  3  header 
    print(" header :")
    print()
    
    #  special FR templates 
    with open(fasta_a_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        headers_a = [line.strip() for line in lines if line.startswith(">")]
        if headers_a:
            sample_a = random.sample(headers_a, min(3, len(headers_a)))
            print("vhh_special_fr_templates_v1.fasta:")
            for header in sample_a:
                print(f"  {header}")
            print()
    
    #  scaffold library 
    with open(fasta_b_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        headers_b = [line.strip() for line in lines if line.startswith(">")]
        if headers_b:
            sample_b = random.sample(headers_b, min(3, len(headers_b)))
            print("vhh_scaffold_library_v1.fasta:")
            for header in sample_b:
                print(f"  {header}")
    
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()










