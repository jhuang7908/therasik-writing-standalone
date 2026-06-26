#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 cluster （ canonical_proxy ）

 canonical_proxy_clusters.json ：
- cluster_assignments.csv
- cluster_summary.csv
- representatives.fasta
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def export_cluster_files(
    clusters_json_path: Path,
    output_dir: Path,
):
    """
     cluster 
    
     CDR ：
    - {cdr}_cluster_assignments.csv: seq_id, cluster_id, length
    - {cdr}_cluster_summary.csv: cluster_id, length, cluster_size, percentile, identity, proxy_score, representative
    - {cdr}_representatives.fasta: cluster 
    """
    #  clusters
    with open(clusters_json_path, "r", encoding="utf-8") as f:
        clusters_by_cdr = json.load(f)
    
    #  lookup table  assignments
    lookup_path = clusters_json_path.parent / "canonical_proxy_lookup.json"
    with open(lookup_path, "r", encoding="utf-8") as f:
        lookup_table = json.load(f)
    
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


def main():
    parser = argparse.ArgumentParser(
        description=" cluster （ canonical_proxy ）"
    )
    parser.add_argument(
        "--clusters_json",
        type=Path,
        default=PROJECT_ROOT / "output" / "canonical_proxy_clusters.json",
        help=" clusters JSON ",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=PROJECT_ROOT / "output_clusters",
        help="",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" cluster ")
    print("=" * 80)
    print()
    
    export_cluster_files(args.clusters_json, args.output_dir)
    
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()













