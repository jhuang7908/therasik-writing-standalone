#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Germline Assets 

 germline  output/  output_clusters/  data/germlines/v1_clean/
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_manifest(
    clean_jsonl_path: Path,
    proxy_jsonl_path: Path,
    clusters_dir: Path,
    qc_csv_path: Path,
) -> Dict[str, Any]:
    """
     manifest.json
    
    、、
    """
    # 
    clean_count = 0
    proxy_count = 0
    
    if clean_jsonl_path.exists():
        with open(clean_jsonl_path, "r", encoding="utf-8") as f:
            clean_count = sum(1 for line in f if line.strip())
    
    if proxy_jsonl_path.exists():
        with open(proxy_jsonl_path, "r", encoding="utf-8") as f:
            proxy_count = sum(1 for line in f if line.strip())
    
    #  cluster 
    cluster_files = {}
    for cdr in ["cdr1", "cdr2"]:
        assignments = clusters_dir / f"{cdr}_cluster_assignments.csv"
        summary = clusters_dir / f"{cdr}_cluster_summary.csv"
        representatives = clusters_dir / f"{cdr}_representatives.fasta"
        
        cluster_files[cdr] = {
            "assignments": assignments.name if assignments.exists() else None,
            "summary": summary.name if summary.exists() else None,
            "representatives": representatives.name if representatives.exists() else None,
        }
    
    manifest = {
        "version": "v1_clean",
        "created_at": datetime.now().isoformat(),
        "description": "Clean human germline VH assets with canonical proxy annotations",
        "files": {
            "germline_assets_clean": {
                "path": "germline_assets_clean.jsonl",
                "record_count": clean_count,
                "description": "Clean germline sequences with IMGT/Kabat numbering and segmentation",
            },
            "germline_assets_clean_with_canonical_proxy": {
                "path": "germline_assets_clean_with_canonical_proxy.jsonl",
                "record_count": proxy_count,
                "description": "Clean germline sequences with canonical proxy annotations for CDR1/CDR2",
            },
            "clusters": {
                "cdr1": cluster_files["cdr1"],
                "cdr2": cluster_files["cdr2"],
                "description": "CDR1/CDR2 cluster assignments, summaries, and representative sequences",
            },
            "qc": {
                "canonical_proxy_qc": {
                    "path": "qc/canonical_proxy_qc.csv",
                    "description": "Quality control summary for canonical proxy annotations",
                },
            },
        },
        "statistics": {
            "total_clean_records": clean_count,
            "total_proxy_records": proxy_count,
        },
    }
    
    return manifest


def organize_germline_assets(
    source_output_dir: Path,
    source_clusters_dir: Path,
    target_dir: Path,
    create_manifest_file: bool = True,
):
    """
     germline assets 
    
    Args:
        source_output_dir:  output 
        source_clusters_dir:  output_clusters 
        target_dir:  (data/germlines/v1_clean)
        create_manifest_file:  manifest.json
    """
    print("=" * 80)
    print(" Germline Assets ")
    print("=" * 80)
    print()
    
    # 
    target_dir.mkdir(parents=True, exist_ok=True)
    clusters_dir = target_dir / "clusters"
    qc_dir = target_dir / "qc"
    clusters_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)
    
    print(f": {target_dir}")
    print()
    
    # 1.  clean JSONL
    print("[1/5]  clean germline assets...")
    source_clean = source_output_dir / "germline_assets_clean.jsonl"
    target_clean = target_dir / "germline_assets_clean.jsonl"
    
    if source_clean.exists():
        shutil.copy2(source_clean, target_clean)
        print(f"  ✅ {source_clean.name} -> {target_clean}")
    else:
        print(f"  ⚠️  : {source_clean}")
    print()
    
    # 2.  proxy JSONL
    print("[2/5]  canonical proxy assets...")
    source_proxy = source_output_dir / "germline_assets_clean_with_canonical_proxy.jsonl"
    target_proxy = target_dir / "germline_assets_clean_with_canonical_proxy.jsonl"
    
    if source_proxy.exists():
        shutil.copy2(source_proxy, target_proxy)
        print(f"  ✅ {source_proxy.name} -> {target_proxy}")
    else:
        print(f"  ⚠️  : {source_proxy}")
    print()
    
    # 3.  cluster 
    print("[3/5]  cluster ...")
    cluster_files = [
        "cdr1_cluster_assignments.csv",
        "cdr1_cluster_summary.csv",
        "cdr1_representatives.fasta",
        "cdr2_cluster_assignments.csv",
        "cdr2_cluster_summary.csv",
        "cdr2_representatives.fasta",
    ]
    
    for filename in cluster_files:
        source_file = source_clusters_dir / filename
        target_file = clusters_dir / filename
        
        if source_file.exists():
            shutil.copy2(source_file, target_file)
            print(f"  ✅ {filename} -> clusters/{filename}")
        else:
            print(f"  ⚠️  : {source_file}")
    print()
    
    # 4.  QC CSV
    print("[4/5]  QC ...")
    source_qc = source_output_dir / "canonical_proxy_qc.csv"
    target_qc = qc_dir / "canonical_proxy_qc.csv"
    
    if source_qc.exists():
        shutil.copy2(source_qc, target_qc)
        print(f"  ✅ canonical_proxy_qc.csv -> qc/canonical_proxy_qc.csv")
    else:
        print(f"  ⚠️  : {source_qc}")
    print()
    
    # 5.  manifest.json
    if create_manifest_file:
        print("[5/5]  manifest.json...")
        manifest = create_manifest(
            target_clean,
            target_proxy,
            clusters_dir,
            target_qc,
        )
        
        manifest_path = target_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ : {manifest_path}")
        print()
    
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)
    print()
    print(f":")
    print(f"  {target_dir}/")
    print(f"    ├── germline_assets_clean.jsonl")
    print(f"    ├── germline_assets_clean_with_canonical_proxy.jsonl")
    print(f"    ├── clusters/")
    print(f"    │   ├── cdr1_cluster_assignments.csv")
    print(f"    │   ├── cdr1_cluster_summary.csv")
    print(f"    │   ├── cdr1_representatives.fasta")
    print(f"    │   ├── cdr2_cluster_assignments.csv")
    print(f"    │   ├── cdr2_cluster_summary.csv")
    print(f"    │   └── cdr2_representatives.fasta")
    print(f"    ├── qc/")
    print(f"    │   └── canonical_proxy_qc.csv")
    print(f"    └── manifest.json")
    print()


def main():
    parser = argparse.ArgumentParser(
        description=" Germline Assets "
    )
    parser.add_argument(
        "--source_output",
        type=Path,
        default=PROJECT_ROOT / "output",
        help=" output ",
    )
    parser.add_argument(
        "--source_clusters",
        type=Path,
        default=PROJECT_ROOT / "output_clusters",
        help=" output_clusters ",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "v1_clean",
        help="",
    )
    parser.add_argument(
        "--no-manifest",
        action="store_true",
        help=" manifest.json",
    )
    
    args = parser.parse_args()
    
    organize_germline_assets(
        args.source_output,
        args.source_clusters,
        args.target,
        create_manifest_file=not args.no_manifest,
    )


if __name__ == "__main__":
    main()













