#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Canonical Proxy Background Report Block (Customer Version)

 CDR Canonical Proxy 。
 canonical_proxy_background.py ，。
"""

from __future__ import annotations

from typing import Dict, Any, Optional


def render_canonical_proxy_background_customer_block(
    canonical_proxy: Optional[Dict[str, Any]],
) -> str:
    """
     Canonical Proxy 
    
    Args:
        canonical_proxy: germline record（ canonical_proxy_cdr1  canonical_proxy_cdr2 ）
             None， N/A
    
    Returns:
        Markdown 
    """
    lines = []
    
    # 
    lines.append("")
    lines.append("")
    lines.append("## CDR Canonical Proxy（）")
    lines.append("")
    
    # （）
    lines.append(
        "Canonical Proxy  scaffold  CDR  germline ，"
        "。，， canonical structural class。"
    )
    lines.append("")
    lines.append(
        "， CDR ， Canonical Proxy ，"
        " scaffold ，。"
    )
    lines.append("")
    
    # （ lines.append("") ）
    # （： "Canonical Proxy Score"）
    # ：Length  Canonical  IMGT  bucket， Query CDR 
    if canonical_proxy is None:
        lines.append("| CDR | Canonical Length (IMGT bucket) | Cluster ID | Canonical Proxy Score |")
        lines.append("|-----|-------------------------------|------------|----------------------|")
        lines.append("| CDR1 | N/A | N/A | N/A |")
        lines.append("| CDR2 | N/A | N/A | N/A |")
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
        
        lines.append("| CDR | Canonical Length (IMGT bucket) | Cluster ID | Canonical Proxy Score |")
        lines.append("|-----|-------------------------------|------------|----------------------|")
        lines.append(f"| CDR1 | {cdr1_length} | {cdr1_cluster_id} | {cdr1_proxy_score_str} |")
        lines.append(f"| CDR2 | {cdr2_length} | {cdr2_cluster_id} | {cdr2_proxy_score_str} |")
    
    # 
    lines.append("")
    
    #  \n 
    result = "\n".join(lines)
    if not result.endswith("\n"):
        result += "\n"
    
    return result


def get_canonical_proxy_data_for_client_report(
    result: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
     result  canonical proxy （）
    
    Args:
        result: 
    
    Returns:
        germline record（ canonical_proxy ）， None
    """
    from core.report_blocks.canonical_proxy_background import find_germline_record_by_scaffold_id
    from core.germline_assets_loader import load_all_clean_germline_assets
    from pathlib import Path
    import json
    
    #  result  scaffold_id
    scaffold_id = None
    
    # 1: stage1.selected_scaffold.scaffold_id
    stage1 = result.get("stage1", {})
    if stage1:
        selected_scaffold = stage1.get("selected_scaffold", {})
        if selected_scaffold:
            scaffold_id = selected_scaffold.get("scaffold_id")
    
    # 2: best_match.id
    if not scaffold_id:
        best_match = result.get("best_match", {})
        if best_match:
            scaffold_id = best_match.get("id")
    
    # 3: matching_result.best_match.id
    if not scaffold_id:
        matching_result = result.get("matching_result", {})
        if matching_result:
            best_match = matching_result.get("best_match", {})
            if best_match:
                scaffold_id = best_match.get("id")
    
    if not scaffold_id:
        return None
    
    try:
        #  germline assets
        germline_assets = load_all_clean_germline_assets(include_canonical_proxy=True)
        
        #  scaffold （）
        PROJECT_ROOT = Path(__file__).resolve().parents[2]
        scaffold_library_path = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds" / "human_vh3_scaffolds.json"
        scaffold_library = None
        if scaffold_library_path.exists():
            with open(scaffold_library_path, "r", encoding="utf-8") as f:
                scaffold_library = json.load(f)
        
        #  germline record
        germline_record = find_germline_record_by_scaffold_id(
            scaffold_id,
            germline_assets,
            scaffold_library=scaffold_library,
        )
        
        return germline_record
    except Exception as e:
        print(f"  ⚠️  Warning:  canonical proxy : {e}")
        return None

