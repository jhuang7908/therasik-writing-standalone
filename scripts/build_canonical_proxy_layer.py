#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Canonical Proxy Layer

 clean germline assets  CDR1/CDR2  canonical proxy 。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from core.canonical.canonical_proxy_layer import (
    build_canonical_proxy_layer,
)


def main():
    parser = argparse.ArgumentParser(
        description=" Canonical Proxy Layer"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "v1_clean" / "germline_assets_clean.jsonl",
        help=" clean germline assets JSONL ",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="",
    )
    parser.add_argument(
        "--identity_threshold",
        type=float,
        default=0.80,
        help=" identity （ 0.80）",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" Canonical Proxy Layer")
    print("=" * 80)
    print()
    
    # 1.  canonical proxy layer
    print(f"[1/3]  Canonical Proxy Layer...")
    print(f"  : {args.input}")
    print(f"  Identity : {args.identity_threshold}")
    print()
    
    clusters_by_cdr, lookup_table = build_canonical_proxy_layer(
        args.input,
        identity_threshold=args.identity_threshold,
    )
    
    # 
    cdr1_clusters = clusters_by_cdr.get("CDR1", [])
    cdr2_clusters = clusters_by_cdr.get("CDR2", [])
    
    print(f"  ✅ CDR1: {len(cdr1_clusters)}  clusters")
    print(f"  ✅ CDR2: {len(cdr2_clusters)}  clusters")
    print()
    
    # 2. 
    print("[2/3] ...")
    
    # CDR1 
    if cdr1_clusters:
        cdr1_sizes = [c["cluster_size"] for c in cdr1_clusters]
        cdr1_lengths = Counter(c["length"] for c in cdr1_clusters)
        print(f"  CDR1:")
        print(f"     clusters: {len(cdr1_clusters)}")
        print(f"     sequences: {sum(cdr1_sizes)}")
        print(f"    Cluster : min={min(cdr1_sizes)}, max={max(cdr1_sizes)}, median={sorted(cdr1_sizes)[len(cdr1_sizes)//2]}")
        print(f"    : {dict(cdr1_lengths.most_common(5))}")
    
    # CDR2 
    if cdr2_clusters:
        cdr2_sizes = [c["cluster_size"] for c in cdr2_clusters]
        cdr2_lengths = Counter(c["length"] for c in cdr2_clusters)
        print(f"  CDR2:")
        print(f"     clusters: {len(cdr2_clusters)}")
        print(f"     sequences: {sum(cdr2_sizes)}")
        print(f"    Cluster : min={min(cdr2_sizes)}, max={max(cdr2_sizes)}, median={sorted(cdr2_sizes)[len(cdr2_sizes)//2]}")
        print(f"    : {dict(cdr2_lengths.most_common(5))}")
    print()
    
    # 3. 
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    #  clusters
    clusters_json_path = args.output_dir / "canonical_proxy_clusters.json"
    print(f"[3/3]  clusters: {clusters_json_path}")
    with open(clusters_json_path, "w", encoding="utf-8") as f:
        json.dump(clusters_by_cdr, f, indent=2, ensure_ascii=False)
    print(f"  ✅ ")
    
    #  lookup table
    lookup_json_path = args.output_dir / "canonical_proxy_lookup.json"
    print(f"   lookup table: {lookup_json_path}")
    with open(lookup_json_path, "w", encoding="utf-8") as f:
        json.dump(lookup_table, f, indent=2, ensure_ascii=False)
    print(f"  ✅ ")
    print()
    
    # 
    print("=" * 80)
    print("")
    print("=" * 80)
    
    #  clusters
    if cdr1_clusters:
        top_cdr1 = sorted(cdr1_clusters, key=lambda x: x["cluster_size"], reverse=True)[:3]
        print("\nCDR1 Top 3 Clusters:")
        for i, cluster in enumerate(top_cdr1, 1):
            print(f"  {i}. {cluster['cluster_id']}:")
            print(f"     size={cluster['cluster_size']}, length={cluster['length']}")
            print(f"     percentile={cluster['cluster_percentile']}, identity={cluster['intra_cluster_identity']}")
            print(f"     proxy_score={cluster['proxy_score']}")
            print(f"     representative: {cluster['representative']}")
    
    if cdr2_clusters:
        top_cdr2 = sorted(cdr2_clusters, key=lambda x: x["cluster_size"], reverse=True)[:3]
        print("\nCDR2 Top 3 Clusters:")
        for i, cluster in enumerate(top_cdr2, 1):
            print(f"  {i}. {cluster['cluster_id']}:")
            print(f"     size={cluster['cluster_size']}, length={cluster['length']}")
            print(f"     percentile={cluster['cluster_percentile']}, identity={cluster['intra_cluster_identity']}")
            print(f"     proxy_score={cluster['proxy_score']}")
            print(f"     representative: {cluster['representative']}")
    
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()

