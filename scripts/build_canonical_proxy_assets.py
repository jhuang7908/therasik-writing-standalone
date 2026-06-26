#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Canonical Proxy  Germline Assets

 clean germline assets  cluster ， canonical_proxy 。
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_cluster_assignments(assignments_csv_path: Path) -> Dict[str, Dict[str, Any]]:
    """
     cluster assignments
    
    Returns:
        {sequence_id: {"cluster_id": str, "length": int}}
    """
    assignments = {}
    with open(assignments_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            seq_id = row["sequence_id"]
            assignments[seq_id] = {
                "cluster_id": row["cluster_id"],
                "length": int(row["length"]),
            }
    return assignments


def load_cluster_summary(summary_csv_path: Path) -> Dict[str, Dict[str, Any]]:
    """
     cluster summary
    
    Returns:
        {cluster_id: {"cluster_size": int, "cluster_percentile": float, "representative": str, ...}}
    """
    summary = {}
    with open(summary_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cluster_id = row["cluster_id"]
            summary[cluster_id] = {
                "cluster_size": int(row["cluster_size"]),
                "cluster_percentile": float(row["cluster_percentile"]),
                "intra_cluster_identity": float(row["intra_cluster_identity"]),
                "proxy_score": float(row["proxy_score"]),
                "representative": row["representative"],
                "length": int(row["length"]),
            }
    return summary


def calculate_sequence_identity(seq1: str, seq2: str) -> float:
    """ identity"""
    if not seq1 or not seq2 or len(seq1) != len(seq2):
        return 0.0
    matches = sum(1 for a, b in zip(seq1, seq2) if a == b)
    return matches / len(seq1) if len(seq1) > 0 else 0.0


def calculate_cluster_percentile_by_length(
    cluster_size: int,
    length: int,
    all_clusters_by_length: Dict[int, List[int]],
) -> float:
    """
     cluster percentile
    
    Args:
        cluster_size:  cluster 
        length: CDR 
        all_clusters_by_length: {length: [cluster_size1, cluster_size2, ...]}
    
    Returns:
        percentile (0.0-1.0)
    """
    if length not in all_clusters_by_length:
        return 0.0
    
    sizes = all_clusters_by_length[length]
    if not sizes:
        return 0.0
    
    sorted_sizes = sorted(sizes, reverse=True)
    rank = sorted_sizes.index(cluster_size) + 1 if cluster_size in sorted_sizes else len(sorted_sizes)
    percentile = (len(sorted_sizes) - rank + 1) / len(sorted_sizes)
    return percentile


def calculate_proxy_score(
    cluster_percentile: float,
    rep_identity: float,
) -> float:
    """
     proxy_score = 0.6 * percentile + 0.4 * rep_identity
    """
    return round(0.6 * cluster_percentile + 0.4 * rep_identity, 4)


def build_canonical_proxy_assets(
    clean_jsonl_path: Path,
    cdr1_assignments_path: Path,
    cdr1_summary_path: Path,
    cdr2_assignments_path: Path,
    cdr2_summary_path: Path,
    output_jsonl_path: Path,
    qc_csv_path: Path,
):
    """
     canonical_proxy  germline assets
    """
    # 1.  cluster 
    print("[1/5]  cluster ...")
    cdr1_assignments = load_cluster_assignments(cdr1_assignments_path)
    cdr1_summary = load_cluster_summary(cdr1_summary_path)
    cdr2_assignments = load_cluster_assignments(cdr2_assignments_path)
    cdr2_summary = load_cluster_summary(cdr2_summary_path)
    
    print(f"  ✅ CDR1: {len(cdr1_assignments)} assignments, {len(cdr1_summary)} clusters")
    print(f"  ✅ CDR2: {len(cdr2_assignments)} assignments, {len(cdr2_summary)} clusters")
    print()
    
    # 2.  cluster sizes（ percentile ）
    print("[2/5] ...")
    cdr1_sizes_by_length = defaultdict(list)
    cdr2_sizes_by_length = defaultdict(list)
    
    for cluster_id, cluster_info in cdr1_summary.items():
        length = cluster_info["length"]
        size = cluster_info["cluster_size"]
        cdr1_sizes_by_length[length].append(size)
    
    for cluster_id, cluster_info in cdr2_summary.items():
        length = cluster_info["length"]
        size = cluster_info["cluster_size"]
        cdr2_sizes_by_length[length].append(size)
    
    print(f"  ✅ CDR1 : {dict(cdr1_sizes_by_length)}")
    print(f"  ✅ CDR2 : {dict(cdr2_sizes_by_length)}")
    print()
    
    # 3. 
    print("[3/5]  clean germline assets...")
    output_records = []
    qc_records = []
    
    with open(clean_jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            record = json.loads(line)
            seq_id = record.get("sequence_id", "")
            segments = record.get("segments", {})
            
            cdr1_seq = segments.get("CDR1", "")
            cdr2_seq = segments.get("CDR2", "")
            
            #  CDR1
            canonical_proxy_cdr1 = None
            if cdr1_seq and seq_id in cdr1_assignments:
                assignment = cdr1_assignments[seq_id]
                cluster_id = assignment["cluster_id"]
                length = assignment["length"]
                
                if cluster_id in cdr1_summary:
                    cluster_info = cdr1_summary[cluster_id]
                    representative = cluster_info["representative"]
                    
                    #  rep_identity
                    rep_identity = calculate_sequence_identity(cdr1_seq, representative)
                    
                    #  percentile
                    cluster_percentile = calculate_cluster_percentile_by_length(
                        cluster_info["cluster_size"],
                        length,
                        cdr1_sizes_by_length,
                    )
                    
                    #  proxy_score
                    proxy_score = calculate_proxy_score(cluster_percentile, rep_identity)
                    
                    canonical_proxy_cdr1 = {
                        "cdr": "CDR1",
                        "length": length,
                        "cluster_id": cluster_id,
                        "cluster_size": cluster_info["cluster_size"],
                        "cluster_percentile": round(cluster_percentile, 4),
                        "rep_identity": round(rep_identity, 4),
                        "proxy_score": proxy_score,
                    }
            
            #  CDR2
            canonical_proxy_cdr2 = None
            if cdr2_seq and seq_id in cdr2_assignments:
                assignment = cdr2_assignments[seq_id]
                cluster_id = assignment["cluster_id"]
                length = assignment["length"]
                
                if cluster_id in cdr2_summary:
                    cluster_info = cdr2_summary[cluster_id]
                    representative = cluster_info["representative"]
                    
                    #  rep_identity
                    rep_identity = calculate_sequence_identity(cdr2_seq, representative)
                    
                    #  percentile
                    cluster_percentile = calculate_cluster_percentile_by_length(
                        cluster_info["cluster_size"],
                        length,
                        cdr2_sizes_by_length,
                    )
                    
                    #  proxy_score
                    proxy_score = calculate_proxy_score(cluster_percentile, rep_identity)
                    
                    canonical_proxy_cdr2 = {
                        "cdr": "CDR2",
                        "length": length,
                        "cluster_id": cluster_id,
                        "cluster_size": cluster_info["cluster_size"],
                        "cluster_percentile": round(cluster_percentile, 4),
                        "rep_identity": round(rep_identity, 4),
                        "proxy_score": proxy_score,
                    }
            
            #  canonical_proxy 
            record["canonical_proxy_cdr1"] = canonical_proxy_cdr1
            record["canonical_proxy_cdr2"] = canonical_proxy_cdr2
            
            output_records.append(record)
            
            # QC 
            qc_records.append({
                "sequence_id": seq_id,
                "cdr1_cluster_id": canonical_proxy_cdr1["cluster_id"] if canonical_proxy_cdr1 else "",
                "cdr1_proxy_score": canonical_proxy_cdr1["proxy_score"] if canonical_proxy_cdr1 else 0.0,
                "cdr2_cluster_id": canonical_proxy_cdr2["cluster_id"] if canonical_proxy_cdr2 else "",
                "cdr2_proxy_score": canonical_proxy_cdr2["proxy_score"] if canonical_proxy_cdr2 else 0.0,
            })
    
    print(f"  ✅ : {len(output_records)} ")
    print()
    
    # 4.  JSONL
    print("[4/5]  JSONL...")
    output_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_jsonl_path, "w", encoding="utf-8") as f:
        for record in output_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  ✅ : {output_jsonl_path}")
    print()
    
    # 5.  QC CSV
    print("[5/5]  QC CSV...")
    qc_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(qc_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "sequence_id", "cdr1_cluster_id", "cdr1_proxy_score",
            "cdr2_cluster_id", "cdr2_proxy_score"
        ])
        writer.writeheader()
        writer.writerows(qc_records)
    print(f"  ✅ : {qc_csv_path}")
    print()
    
    # 
    cdr1_annotated = sum(1 for r in output_records if r.get("canonical_proxy_cdr1"))
    cdr2_annotated = sum(1 for r in output_records if r.get("canonical_proxy_cdr2"))
    
    print("=" * 80)
    print("")
    print("=" * 80)
    print(f": {len(output_records)}")
    print(f"CDR1 : {cdr1_annotated} ")
    print(f"CDR2 : {cdr2_annotated} ")
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description=" Canonical Proxy  Germline Assets"
    )
    parser.add_argument(
        "--clean_jsonl",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "v1_clean" / "germline_assets_clean.jsonl",
        help=" clean germline assets JSONL ",
    )
    parser.add_argument(
        "--cdr1_assignments",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "v1_clean" / "clusters" / "cdr1_cluster_assignments.csv",
        help="CDR1 cluster assignments CSV ",
    )
    parser.add_argument(
        "--cdr1_summary",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "v1_clean" / "clusters" / "cdr1_cluster_summary.csv",
        help="CDR1 cluster summary CSV ",
    )
    parser.add_argument(
        "--cdr2_assignments",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "v1_clean" / "clusters" / "cdr2_cluster_assignments.csv",
        help="CDR2 cluster assignments CSV ",
    )
    parser.add_argument(
        "--cdr2_summary",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "v1_clean" / "clusters" / "cdr2_cluster_summary.csv",
        help="CDR2 cluster summary CSV ",
    )
    parser.add_argument(
        "--output_jsonl",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "v1_clean" / "germline_assets_clean_with_canonical_proxy.jsonl",
        help=" JSONL ",
    )
    parser.add_argument(
        "--qc_csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "v1_clean" / "qc" / "canonical_proxy_qc.csv",
        help=" QC CSV ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" Canonical Proxy  Germline Assets")
    print("=" * 80)
    print()
    
    build_canonical_proxy_assets(
        args.clean_jsonl,
        args.cdr1_assignments,
        args.cdr1_summary,
        args.cdr2_assignments,
        args.cdr2_summary,
        args.output_jsonl,
        args.qc_csv,
    )


if __name__ == "__main__":
    main()

