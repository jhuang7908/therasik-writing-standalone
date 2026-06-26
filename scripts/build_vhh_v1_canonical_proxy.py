#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH v1 Canonical Proxy

 vhh_germline_assets_clean.jsonl  CDR1/CDR2  canonical proxy ，
 canonical proxy  JSONL 。

：
1.  canonical proxy layer（）
2.  cluster  clusters/
3.  canonical_proxy  JSONL
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from core.canonical.canonical_proxy_layer import (
    build_canonical_proxy_layer,
)


def export_cluster_files(
    clusters_by_cdr: dict,
    lookup_table: dict,
    output_dir: Path,
):
    """
     cluster 
    
     CDR ：
    - {cdr}_cluster_assignments.csv
    - {cdr}_cluster_summary.csv
    - {cdr}_representatives.fasta
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for cdr_name in ["CDR1", "CDR2"]:
        print(f" {cdr_name}...")
        
        clusters = clusters_by_cdr.get(cdr_name, [])
        cdr_lookup = lookup_table.get(cdr_name, {})
        
        # 1.  assignments.csv
        assignments_path = output_dir / f"{cdr_name.lower()}_cluster_assignments.csv"
        with open(assignments_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["sequence_id", "cluster_id", "length"])
            writer.writeheader()
            for seq_id, proxy_info in cdr_lookup.items():
                writer.writerow({
                    "sequence_id": seq_id,
                    "cluster_id": proxy_info["cluster_id"],
                    "length": proxy_info["length"],
                })
        print(f"  ✅ : {assignments_path} ({len(cdr_lookup)} )")
        
        # 2.  summary.csv
        summary_path = output_dir / f"{cdr_name.lower()}_cluster_summary.csv"
        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "cluster_id", "length", "cluster_size", "cluster_percentile",
                "intra_cluster_identity", "proxy_score", "representative"
            ])
            writer.writeheader()
            for cluster in clusters:
                writer.writerow({
                    "cluster_id": cluster["cluster_id"],
                    "length": cluster["length"],
                    "cluster_size": cluster["cluster_size"],
                    "cluster_percentile": cluster["cluster_percentile"],
                    "intra_cluster_identity": cluster["intra_cluster_identity"],
                    "proxy_score": cluster["proxy_score"],
                    "representative": cluster["representative"],
                })
        print(f"  ✅ : {summary_path} ({len(clusters)}  clusters)")
        
        # 3.  representatives.fasta
        fasta_path = output_dir / f"{cdr_name.lower()}_representatives.fasta"
        with open(fasta_path, "w", encoding="utf-8") as f:
            for cluster in clusters:
                cluster_id = cluster["cluster_id"]
                representative = cluster["representative"]
                f.write(f">{cluster_id}\n{representative}\n")
        print(f"  ✅ : {fasta_path} ({len(clusters)} )")


def calculate_sequence_identity(seq1: str, seq2: str) -> float:
    """ identity"""
    if not seq1 or not seq2 or len(seq1) != len(seq2):
        return 0.0
    matches = sum(1 for a, b in zip(seq1, seq2) if a == b)
    return matches / len(seq1) if len(seq1) > 0 else 0.0


def calculate_cluster_percentile_by_length(
    cluster_size: int,
    length: int,
    all_clusters_by_length: dict,
) -> float:
    """ cluster percentile"""
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
    """ proxy_score = 0.6 * percentile + 0.4 * rep_identity"""
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
    """ canonical_proxy  germline assets"""
    # 1.  cluster 
    print("[1/5]  cluster ...")
    cdr1_assignments = {}
    with open(cdr1_assignments_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cdr1_assignments[row["sequence_id"]] = {
                "cluster_id": row["cluster_id"],
                "length": int(row["length"]),
            }
    
    cdr1_summary = {}
    with open(cdr1_summary_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cdr1_summary[row["cluster_id"]] = {
                "cluster_size": int(row["cluster_size"]),
                "cluster_percentile": float(row["cluster_percentile"]),
                "intra_cluster_identity": float(row["intra_cluster_identity"]),
                "proxy_score": float(row["proxy_score"]),
                "representative": row["representative"],
                "length": int(row["length"]),
            }
    
    cdr2_assignments = {}
    with open(cdr2_assignments_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cdr2_assignments[row["sequence_id"]] = {
                "cluster_id": row["cluster_id"],
                "length": int(row["length"]),
            }
    
    cdr2_summary = {}
    with open(cdr2_summary_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cdr2_summary[row["cluster_id"]] = {
                "cluster_size": int(row["cluster_size"]),
                "cluster_percentile": float(row["cluster_percentile"]),
                "intra_cluster_identity": float(row["intra_cluster_identity"]),
                "proxy_score": float(row["proxy_score"]),
                "representative": row["representative"],
                "length": int(row["length"]),
            }
    
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
    
    print(f"  ✅ CDR1 : {len(cdr1_sizes_by_length)} ")
    print(f"  ✅ CDR2 : {len(cdr2_sizes_by_length)} ")
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
        description=" VHH v1 Canonical Proxy"
    )
    parser.add_argument(
        "--clean_jsonl",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean.jsonl",
        help=" clean germline assets JSONL ",
    )
    parser.add_argument(
        "--clusters_dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "clusters",
        help="clusters ",
    )
    parser.add_argument(
        "--output_jsonl",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean_with_canonical_proxy.jsonl",
        help=" canonical_proxy  JSONL ",
    )
    parser.add_argument(
        "--qc_csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "qc" / "canonical_proxy_qc.csv",
        help=" QC CSV ",
    )
    parser.add_argument(
        "--identity_threshold",
        type=float,
        default=0.80,
        help=" identity （ 0.80）",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" VHH v1 Canonical Proxy")
    print("=" * 80)
    print()
    
    # Step 1:  canonical proxy layer
    print(f"[Step 1/3]  Canonical Proxy Layer...")
    print(f"  : {args.clean_jsonl}")
    print(f"  Identity : {args.identity_threshold}")
    print()
    
    clusters_by_cdr, lookup_table = build_canonical_proxy_layer(
        args.clean_jsonl,
        identity_threshold=args.identity_threshold,
    )
    
    cdr1_clusters = clusters_by_cdr.get("CDR1", [])
    cdr2_clusters = clusters_by_cdr.get("CDR2", [])
    
    print(f"  ✅ CDR1: {len(cdr1_clusters)}  clusters")
    print(f"  ✅ CDR2: {len(cdr2_clusters)}  clusters")
    print()
    
    # Step 2:  cluster 
    print(f"[Step 2/3]  cluster ...")
    export_cluster_files(clusters_by_cdr, lookup_table, args.clusters_dir)
    print()
    
    # Step 3:  canonical_proxy  assets
    print(f"[Step 3/3]  canonical_proxy  assets...")
    build_canonical_proxy_assets(
        args.clean_jsonl,
        args.clusters_dir / "cdr1_cluster_assignments.csv",
        args.clusters_dir / "cdr1_cluster_summary.csv",
        args.clusters_dir / "cdr2_cluster_assignments.csv",
        args.clusters_dir / "cdr2_cluster_summary.csv",
        args.output_jsonl,
        args.qc_csv,
    )
    
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()










