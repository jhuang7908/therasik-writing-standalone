#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Canonical Proxy Background Report Block

 CDR Canonical Proxy 。
"""

from __future__ import annotations

from typing import Dict, Any, Optional


def render_canonical_proxy_background_block(
    canonical_proxy: Optional[Dict[str, Any]],
    agg_mode: str = "min",
    weight: float = 0.10,
) -> str:
    """
     Canonical Proxy 
    
    Args:
        canonical_proxy: germline record  canonical_proxy 
             None， N/A
        agg_mode: （"min"  "mean"）
        weight: canonical_proxy 
    
    Returns:
        Markdown 
    """
    lines = []
    lines.append("## CDR Canonical Proxy（）")
    lines.append("")
    
    # 
    lines.append(
        "Canonical Proxy  scaffold  CDR  germline ，"
        "。， canonical structural class。"
        " humanized variants  CDR ， Canonical Proxy  variant ，"
        " variant 。"
    )
    lines.append("")
    
    # 
    # ：Length  Canonical  IMGT  bucket， Query CDR 
    if canonical_proxy is None:
        lines.append("| CDR | Canonical Length (IMGT bucket) | Cluster ID | Proxy Score |")
        lines.append("|-----|-------------------------------|------------|-------------|")
        lines.append("| CDR1 | N/A | N/A | N/A |")
        lines.append("| CDR2 | N/A | N/A | N/A |")
        lines.append("")
        lines.append("*⚠️ ： canonical proxy *")
    else:
        #  CDR1 
        cdr1_info = canonical_proxy.get("canonical_proxy_cdr1", {})
        if isinstance(cdr1_info, dict):
            cdr1_length = cdr1_info.get("length", "N/A")
            cdr1_cluster_id = cdr1_info.get("cluster_id", "N/A")
            cdr1_proxy_score = cdr1_info.get("proxy_score", 0.0)
            cdr1_proxy_score_str = f"{cdr1_proxy_score:.4f}" if isinstance(cdr1_proxy_score, (int, float)) else "N/A"
        else:
            cdr1_length = "N/A"
            cdr1_cluster_id = "N/A"
            cdr1_proxy_score_str = "N/A"
        
        #  CDR2 
        cdr2_info = canonical_proxy.get("canonical_proxy_cdr2", {})
        if isinstance(cdr2_info, dict):
            cdr2_length = cdr2_info.get("length", "N/A")
            cdr2_cluster_id = cdr2_info.get("cluster_id", "N/A")
            cdr2_proxy_score = cdr2_info.get("proxy_score", 0.0)
            cdr2_proxy_score_str = f"{cdr2_proxy_score:.4f}" if isinstance(cdr2_proxy_score, (int, float)) else "N/A"
        else:
            cdr2_length = "N/A"
            cdr2_cluster_id = "N/A"
            cdr2_proxy_score_str = "N/A"
        
        lines.append("| CDR | Canonical Length (IMGT bucket) | Cluster ID | Proxy Score |")
        lines.append("|-----|-------------------------------|------------|-------------|")
        lines.append(f"| CDR1 | {cdr1_length} | {cdr1_cluster_id} | {cdr1_proxy_score_str} |")
        lines.append(f"| CDR2 | {cdr2_length} | {cdr2_cluster_id} | {cdr2_proxy_score_str} |")
        lines.append("")
        
        #  agg 
        lines.append(f"****: {agg_mode}（`proxy_agg = {agg_mode}(proxy_cdr1, proxy_cdr2)`）")
        lines.append(f"****: {weight}（`total_score = total_score_old + {weight} × proxy_agg`）")
    
    lines.append("")
    
    return "\n".join(lines)


def find_germline_record_by_scaffold_id(
    scaffold_id: str,
    germline_assets: list[Dict[str, Any]],
    scaffold_library: Optional[list[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """
     scaffold_id  germline record
    
    Args:
        scaffold_id: scaffold ID（ "HUMAN_VH3_SCF_10_SAFE_A"）
        germline_assets: germline assets 
    
    Returns:
         germline record， None
    """
    if not scaffold_id:
        return None
    
    #  scaffold_id  ID
    #  "HUMAN_VH3_SCF_10_SAFE_A" -> "HUMAN_VH3_SCF_10"
    base_scaffold_id = scaffold_id.split("_SAFE_")[0] if "_SAFE_" in scaffold_id else scaffold_id
    
    #  sequence_id  germline 
    sequence_id_to_germline = {}
    prefix_to_germline = {}
    for asset in germline_assets:
        seq_id = asset.get("sequence_id", "")
        if seq_id:
            sequence_id_to_germline[seq_id] = asset
            # （）
            parts = seq_id.split("|")
            if len(parts) >= 2:
                prefix = f"{parts[0]}|{parts[1]}"
                if prefix not in prefix_to_germline:
                    prefix_to_germline[prefix] = asset
    
    #  scaffold_library， member_ids 
    if scaffold_library:
        for scaffold in scaffold_library:
            if scaffold.get("scaffold_id") == base_scaffold_id:
                member_ids = scaffold.get("member_ids", [])
                if member_ids:
                    #  member_id
                    for member_id in member_ids:
                        # member_id : "M99652|IGHV3-11*01|Homo sapiens|..."
                        # 
                        parts = member_id.split("|")
                        if len(parts) >= 2:
                            prefix = f"{parts[0]}|{parts[1]}"
                            
                            # 
                            candidate_ids = [
                                f"{prefix}|Homo",  # 
                                prefix,  # 
                            ]
                            
                            for candidate_id in candidate_ids:
                                if candidate_id in sequence_id_to_germline:
                                    return sequence_id_to_germline[candidate_id]
                            
                            # 
                            if prefix in prefix_to_germline:
                                return prefix_to_germline[prefix]
                break
    
    #  scaffold_library ，
    #  SCF_XX  germline
    if "SCF_10" in base_scaffold_id:
        for asset in germline_assets:
            seq_id = asset.get("sequence_id", "")
            if "IGHV3-30" in seq_id:
                return asset
    elif "SCF_22" in base_scaffold_id:
        # 
        pass
    
    # ， None
    return None

