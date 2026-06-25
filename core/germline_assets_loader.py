#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Germline Assets Loader

 data/germlines/v1_clean/  germline 。

， germline 。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 
V1_CLEAN_DIR = PROJECT_ROOT / "data" / "germlines" / "v1_clean"
VHH_V1_DIR = PROJECT_ROOT / "data" / "germlines" / "vhh_v1"

#  v1_clean
CLEAN_JSONL = V1_CLEAN_DIR / "germline_assets_clean.jsonl"
PROXY_JSONL = V1_CLEAN_DIR / "germline_assets_clean_with_canonical_proxy.jsonl"
CLUSTERS_DIR = V1_CLEAN_DIR / "clusters"
QC_DIR = V1_CLEAN_DIR / "qc"
MANIFEST_JSON = V1_CLEAN_DIR / "manifest.json"


def get_germline_dir(version: str = "v1_clean") -> Path:
    """
     germline 
    
    Args:
        version: "v1_clean"  "vhh_v1"
    
    Returns:
        
    """
    if version == "vhh_v1":
        return VHH_V1_DIR
    else:
        return V1_CLEAN_DIR


def get_germline_paths(version: str = "v1_clean", include_canonical_proxy: bool = False) -> tuple[Path, Path, Path, Path]:
    """
     germline 
    
    Args:
        version: "v1_clean"  "vhh_v1"
        include_canonical_proxy:  canonical_proxy
    
    Returns:
        (clean_jsonl, proxy_jsonl, clusters_dir, manifest_json)
    """
    base_dir = get_germline_dir(version)
    
    if version == "vhh_v1":
        clean_jsonl = base_dir / "vhh_germline_assets_clean.jsonl"
        proxy_jsonl = base_dir / "vhh_germline_assets_clean_with_canonical_proxy.jsonl"
    else:
        clean_jsonl = base_dir / "germline_assets_clean.jsonl"
        proxy_jsonl = base_dir / "germline_assets_clean_with_canonical_proxy.jsonl"
    
    clusters_dir = base_dir / "clusters"
    manifest_json = base_dir / "manifest.json"
    
    jsonl_path = proxy_jsonl if include_canonical_proxy else clean_jsonl
    
    return jsonl_path, clusters_dir, manifest_json, base_dir


def load_manifest() -> Dict[str, Any]:
    """
     manifest.json
    
    Returns:
        manifest 
    """
    if not MANIFEST_JSON.exists():
        raise FileNotFoundError(
            f"manifest.json : {MANIFEST_JSON}\n"
            f" data/germlines/v1_clean/ "
        )
    
    with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def load_clean_germline_assets(
    include_canonical_proxy: bool = False,
    version: str = "v1_clean",
) -> Iterator[Dict[str, Any]]:
    """
     clean germline assets
    
    Args:
        include_canonical_proxy:  canonical_proxy 
        version: "v1_clean"  "vhh_v1"
    
    Yields:
         germline 
    """
    jsonl_path, _, _, _ = get_germline_paths(version, include_canonical_proxy)
    
    if not jsonl_path.exists():
        raise FileNotFoundError(
            f"Germline assets : {jsonl_path}\n"
            f" data/germlines/{version}/ "
        )
    
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def load_all_clean_germline_assets(
    include_canonical_proxy: bool = False,
    version: str = "v1_clean",
) -> List[Dict[str, Any]]:
    """
     clean germline assets（）
    
    Args:
        include_canonical_proxy:  canonical_proxy 
        version: "v1_clean"  "vhh_v1"
    
    Returns:
         germline 
    """
    return list(load_clean_germline_assets(include_canonical_proxy=include_canonical_proxy, version=version))


def load_germline_by_id(
    sequence_id: str,
    include_canonical_proxy: bool = False,
) -> Optional[Dict[str, Any]]:
    """
     sequence_id  germline 
    
    Args:
        sequence_id:  ID
        include_canonical_proxy:  canonical_proxy 
    
    Returns:
        germline ， None
    """
    for record in load_clean_germline_assets(include_canonical_proxy=include_canonical_proxy):
        if record.get("sequence_id") == sequence_id:
            return record
    return None


def load_canonical_proxy_clusters(version: str = "v1_clean") -> Dict[str, List[Dict[str, Any]]]:
    """
     canonical proxy clusters
    
    Args:
        version: "v1_clean"  "vhh_v1"
    
    Returns:
        {
            "CDR1": [cluster1, cluster2, ...],
            "CDR2": [cluster1, cluster2, ...],
        }
    """
    #  summary CSV （， JSON）
    import csv
    
    _, clusters_dir, _, _ = get_germline_paths(version, False)
    clusters = {"CDR1": [], "CDR2": []}
    
    for cdr_name in ["CDR1", "CDR2"]:
        summary_path = clusters_dir / f"{cdr_name.lower()}_cluster_summary.csv"
        if not summary_path.exists():
            continue
        
        with open(summary_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                clusters[cdr_name].append({
                    "cluster_id": row["cluster_id"],
                    "length": int(row["length"]),
                    "cluster_size": int(row["cluster_size"]),
                    "cluster_percentile": float(row["cluster_percentile"]),
                    "intra_cluster_identity": float(row["intra_cluster_identity"]),
                    "proxy_score": float(row["proxy_score"]),
                    "representative": row["representative"],
                })
    
    return clusters


def load_canonical_proxy_lookup(version: str = "v1_clean") -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
     canonical proxy lookup table
    
    Args:
        version: "v1_clean"  "vhh_v1"
    
    Returns:
        {
            "CDR1": {sequence_id: canonical_proxy_dict, ...},
            "CDR2": {sequence_id: canonical_proxy_dict, ...},
        }
    """
    import csv
    
    _, clusters_dir, _, _ = get_germline_paths(version, False)
    lookup = {"CDR1": {}, "CDR2": {}}
    
    for cdr_name in ["CDR1", "CDR2"]:
        assignments_path = clusters_dir / f"{cdr_name.lower()}_cluster_assignments.csv"
        summary_path = clusters_dir / f"{cdr_name.lower()}_cluster_summary.csv"
        
        if not assignments_path.exists() or not summary_path.exists():
            continue
        
        #  summary 
        summary_index = {}
        with open(summary_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                summary_index[row["cluster_id"]] = {
                    "cluster_size": int(row["cluster_size"]),
                    "cluster_percentile": float(row["cluster_percentile"]),
                    "proxy_score": float(row["proxy_score"]),
                }
        
        #  assignments
        with open(assignments_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                seq_id = row["sequence_id"]
                cluster_id = row["cluster_id"]
                length = int(row["length"])
                
                cluster_info = summary_index.get(cluster_id, {})
                lookup[cdr_name][seq_id] = {
                    "cdr": cdr_name,
                    "length": length,
                    "cluster_id": cluster_id,
                    "cluster_size": cluster_info.get("cluster_size", 0),
                    "cluster_percentile": cluster_info.get("cluster_percentile", 0.0),
                    "proxy_score": cluster_info.get("proxy_score", 0.0),
                }
    
    return lookup


def get_germline_assets_path(
    asset_type: str = "clean",
    include_canonical_proxy: bool = False,
) -> Path:
    """
     germline assets 
    
    Args:
        asset_type: "clean"  "proxy"
        include_canonical_proxy:  canonical_proxy（ asset_type="clean" ）
    
    Returns:
        
    """
    if asset_type == "proxy" or include_canonical_proxy:
        return PROXY_JSONL
    else:
        return CLEAN_JSONL


def validate_germline_assets_directory() -> tuple[bool, List[str]]:
    """
     germline assets 
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    # 
    if not V1_CLEAN_DIR.exists():
        errors.append(f": {V1_CLEAN_DIR}")
        return False, errors
    
    # 
    required_files = [
        ("manifest.json", MANIFEST_JSON),
        ("germline_assets_clean.jsonl", CLEAN_JSONL),
        ("germline_assets_clean_with_canonical_proxy.jsonl", PROXY_JSONL),
    ]
    
    for name, path in required_files:
        if not path.exists():
            errors.append(f": {name} ({path})")
    
    #  clusters 
    if not CLUSTERS_DIR.exists():
        errors.append(f"clusters : {CLUSTERS_DIR}")
    else:
        required_cluster_files = [
            "cdr1_cluster_assignments.csv",
            "cdr1_cluster_summary.csv",
            "cdr1_representatives.fasta",
            "cdr2_cluster_assignments.csv",
            "cdr2_cluster_summary.csv",
            "cdr2_representatives.fasta",
        ]
        for filename in required_cluster_files:
            path = CLUSTERS_DIR / filename
            if not path.exists():
                errors.append(f"cluster : {filename} ({path})")
    
    #  qc 
    if not QC_DIR.exists():
        errors.append(f"qc : {QC_DIR}")
    else:
        qc_file = QC_DIR / "canonical_proxy_qc.csv"
        if not qc_file.exists():
            errors.append(f"QC : canonical_proxy_qc.csv ({qc_file})")
    
    return len(errors) == 0, errors
