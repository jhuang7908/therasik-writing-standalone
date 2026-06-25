#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Layer 1: Canonical Proxy Layer

 IMGT length、cluster frequency  intra-cluster identity  CDR1/CDR2 。

：
- 
- "canonical class "
- 、、
- 100% 
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def calculate_sequence_identity(seq1: str, seq2: str) -> float:
    """
     identity（）
    
    Args:
        seq1, seq2: 
    
    Returns:
        identity (0.0-1.0)
    """
    if not seq1 or not seq2:
        return 0.0
    
    if len(seq1) != len(seq2):
        return 0.0
    
    matches = sum(1 for a, b in zip(seq1, seq2) if a == b)
    return matches / len(seq1) if len(seq1) > 0 else 0.0


def cluster_sequences_by_identity(
    sequences: List[Tuple[str, str]],  # [(seq_id, sequence), ...]
    identity_threshold: float = 0.80,
) -> List[Dict[str, Any]]:
    """
     identity 
    
    Args:
        sequences: [(seq_id, sequence), ...]
        identity_threshold: （ 0.80， 80% identity）
    
    Returns:
        [{
            "cluster_id": str,
            "sequences": [(seq_id, sequence), ...],
            "cluster_size": int,
            "representative": str,  # 
            "intra_cluster_identity": float,  #  identity
        }, ...]
    """
    if not sequences:
        return []
    
    clusters = []
    assigned = set()
    
    # （）
    length_groups = defaultdict(list)
    for seq_id, seq in sequences:
        length_groups[len(seq)].append((seq_id, seq))
    
    # 
    for length, seqs_in_length in length_groups.items():
        # 
        for seq_id, seq in seqs_in_length:
            if seq_id in assigned:
                continue
            
            #  cluster
            cluster = {
                "cluster_id": f"L{length}_C{len(clusters) + 1}",
                "sequences": [(seq_id, seq)],
                "cluster_size": 1,
                "representative": seq,
                "intra_cluster_identity": 1.0,
            }
            assigned.add(seq_id)
            
            # 
            for other_id, other_seq in seqs_in_length:
                if other_id in assigned:
                    continue
                
                identity = calculate_sequence_identity(seq, other_seq)
                if identity >= identity_threshold:
                    cluster["sequences"].append((other_id, other_seq))
                    assigned.add(other_id)
            
            #  cluster 
            cluster["cluster_size"] = len(cluster["sequences"])
            
            #  identity
            if cluster["cluster_size"] > 1:
                identities = []
                for i, (_, s1) in enumerate(cluster["sequences"]):
                    for j, (_, s2) in enumerate(cluster["sequences"]):
                        if i < j:
                            identities.append(calculate_sequence_identity(s1, s2))
                cluster["intra_cluster_identity"] = (
                    sum(identities) / len(identities) if identities else 1.0
                )
            
            #  representative
            seq_counts = Counter(s for _, s in cluster["sequences"])
            cluster["representative"] = seq_counts.most_common(1)[0][0]
            
            clusters.append(cluster)
    
    return clusters


def calculate_cluster_percentile(
    cluster_size: int,
    all_cluster_sizes: List[int],
) -> float:
    """
     cluster  percentile（ cluster  cluster ）
    
    Args:
        cluster_size:  cluster 
        all_cluster_sizes:  cluster 
    
    Returns:
        percentile (0.0-1.0)
    """
    if not all_cluster_sizes:
        return 0.0
    
    sorted_sizes = sorted(all_cluster_sizes, reverse=True)
    rank = sorted_sizes.index(cluster_size) + 1 if cluster_size in sorted_sizes else len(sorted_sizes)
    
    # percentile = ( -  + 1) / 
    percentile = (len(sorted_sizes) - rank + 1) / len(sorted_sizes)
    return percentile


def calculate_proxy_score(
    cluster_size: int,
    cluster_percentile: float,
    intra_cluster_identity: float,
) -> float:
    """
     proxy_score
    
    ：
    - cluster_size（）
    - cluster_percentile（）
    - intra_cluster_identity（）
    
    Args:
        cluster_size: cluster 
        cluster_percentile: cluster 
        intra_cluster_identity:  identity
    
    Returns:
        proxy_score (0.0-1.0)
    """
    #  cluster_size（ 100， 100  100 ）
    normalized_size = min(cluster_size / 100.0, 1.0)
    
    # 
    # size : 0.3, percentile : 0.3, identity : 0.4
    proxy_score = (
        0.3 * normalized_size +
        0.3 * cluster_percentile +
        0.4 * intra_cluster_identity
    )
    
    return round(proxy_score, 4)


def build_canonical_proxy_layer(
    clean_germline_jsonl_path: Path,
    identity_threshold: float = 0.80,
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Dict[str, Any]]]:
    """
     Canonical Proxy Layer
    
    Args:
        clean_germline_jsonl_path: clean germline assets JSONL 
        identity_threshold:  identity （ 0.80）
    
    Returns:
        (clusters_by_cdr, lookup_table)
        
        clusters_by_cdr: {
            "CDR1": [cluster1, cluster2, ...],
            "CDR2": [cluster1, cluster2, ...],
        }
        
        lookup_table: {
            "CDR1": {
                "seq_id": canonical_proxy_dict,
                ...
            },
            "CDR2": {
                "seq_id": canonical_proxy_dict,
                ...
            },
        }
    """
    # 1.  clean germline assets
    sequences_by_cdr = defaultdict(list)  # {"CDR1": [(seq_id, cdr_seq), ...], ...}
    
    with open(clean_germline_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            record = json.loads(line)
            seq_id = record.get("sequence_id", "")
            segments = record.get("segments", {})
            
            #  CDR1  CDR2
            for cdr_name in ["CDR1", "CDR2"]:
                cdr_seq = segments.get(cdr_name, "")
                if cdr_seq:
                    sequences_by_cdr[cdr_name].append((seq_id, cdr_seq))
    
    # 2.  CDR 
    clusters_by_cdr = {}
    lookup_table = defaultdict(dict)
    
    for cdr_name in ["CDR1", "CDR2"]:
        sequences = sequences_by_cdr.get(cdr_name, [])
        
        if not sequences:
            clusters_by_cdr[cdr_name] = []
            continue
        
        # 
        clusters = cluster_sequences_by_identity(sequences, identity_threshold)
        
        #  cluster （ percentile ）
        all_cluster_sizes = [c["cluster_size"] for c in clusters]
        
        #  cluster 
        enriched_clusters = []
        for cluster in clusters:
            length = len(cluster["representative"])
            cluster_size = cluster["cluster_size"]
            cluster_percentile = calculate_cluster_percentile(cluster_size, all_cluster_sizes)
            intra_cluster_identity = cluster["intra_cluster_identity"]
            proxy_score = calculate_proxy_score(
                cluster_size,
                cluster_percentile,
                intra_cluster_identity,
            )
            
            enriched_cluster = {
                "cluster_id": f"cdr{cdr_name[-1]}_L{length}_C{len(enriched_clusters) + 1}",
                "length": length,
                "cluster_size": cluster_size,
                "cluster_percentile": round(cluster_percentile, 4),
                "intra_cluster_identity": round(intra_cluster_identity, 4),
                "proxy_score": proxy_score,
                "representative": cluster["representative"],
                "sequence_count": cluster_size,
            }
            enriched_clusters.append(enriched_cluster)
            
            #  lookup table
            for seq_id, seq in cluster["sequences"]:
                lookup_table[cdr_name][seq_id] = {
                    "cdr": cdr_name,
                    "length": length,
                    "cluster_id": enriched_cluster["cluster_id"],
                    "cluster_size": cluster_size,
                    "cluster_percentile": round(cluster_percentile, 4),
                    "proxy_score": proxy_score,
                }
        
        clusters_by_cdr[cdr_name] = enriched_clusters
    
    return clusters_by_cdr, dict(lookup_table)


def annotate_sequence_with_canonical_proxy(
    sequence_id: str,
    cdr1_seq: str,
    cdr2_seq: str,
    lookup_table: Dict[str, Dict[str, Dict[str, Any]]],
) -> Dict[str, Any]:
    """
     canonical_proxy 
    
    Args:
        sequence_id:  ID
        cdr1_seq: CDR1 
        cdr2_seq: CDR2 
        lookup_table:  build_canonical_proxy_layer  lookup table
    
    Returns:
        {
            "CDR1": canonical_proxy_dict,
            "CDR2": canonical_proxy_dict,
        }
    """
    result = {}
    
    for cdr_name, cdr_seq in [("CDR1", cdr1_seq), ("CDR2", cdr2_seq)]:
        if cdr_seq and sequence_id in lookup_table.get(cdr_name, {}):
            result[cdr_name] = lookup_table[cdr_name][sequence_id]
        else:
            # ，
            result[cdr_name] = {
                "cdr": cdr_name,
                "length": len(cdr_seq) if cdr_seq else 0,
                "cluster_id": "unknown",
                "cluster_size": 0,
                "cluster_percentile": 0.0,
                "proxy_score": 0.0,
            }
    
    return result

