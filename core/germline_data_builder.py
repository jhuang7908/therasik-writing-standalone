"""
Germline

candidatesgermline.candidates，scores.overall。
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional


def build_germline_candidates(
    candidates: List[Dict[str, Any]],
    best_match: Optional[Dict[str, Any]] = None,
    top_n: int = 10,
) -> Dict[str, Any]:
    """
    candidatesgermline.candidates，scores.overall
    
    Args:
        candidates: （，best first）
        best_match: （，selected）
        top_n: n
    
    Returns:
        germline：
        {
            "summary_top_n": int,
            "candidates": [
                {
                    "id": str,
                    "family": str,
                    "scores": {
                        "framework_identity": float,
                        "vhh_hallmark": float,
                        "immunogenicity_baseline": float,
                        "developability_baseline": float,
                        "overall": float  # alignment_scores.scoring_details.combined_score
                    },
                    "comment_short": str
                }
            ],
            "selected": {...}
        }
    """
    germline_candidates = []
    selected_id = None
    
    if best_match:
        selected_id = (
            best_match.get("template", {}).get("template_id") or
            best_match.get("template_id") or
            "UNKNOWN"
        )
    
    # candidates
    for i, candidate in enumerate(candidates[:top_n], 1):
        template_id = candidate.get("template_id", "UNKNOWN")
        alignment_scores = candidate.get("alignment_scores", {}) or {}
        scoring_details = alignment_scores.get("scoring_details", {}) or {}
        
        # combined_score（scoring_details，alignment_scores）
        combined_score = (
            scoring_details.get("combined_score") or
            alignment_scores.get("combined_score", 0.0)
        )
        
        # 
        framework_identity = alignment_scores.get("framework_identity", 0.0)
        vhh_hallmark = alignment_scores.get("vhh_hallmark_score", 1.0)
        
        # developabilityimmunogenicity baseline
        developability_baseline = alignment_scores.get("developability_score", 0.5)
        immunogenicity_baseline = 0.0  # ，
        
        # family（template_id，）
        family = "Human VH3"  # 
        if "VH3" in template_id:
            family = "Human VH3"
        elif "VH1" in template_id:
            family = "Human VH1"
        elif "VH2" in template_id:
            family = "Human VH2"
        elif "VH4" in template_id:
            family = "Human VH4"
        elif "VH5" in template_id:
            family = "Human VH5"
        elif "VH6" in template_id:
            family = "Human VH6"
        
        # comment
        comment_short = "VHH"
        if selected_id and template_id == selected_id:
            comment_short = "【】"
        
        germline_candidates.append({
            "id": template_id,
            "family": family,
            "scores": {
                "framework_identity": round(framework_identity, 3),
                "vhh_hallmark": round(vhh_hallmark, 3),
                "immunogenicity_baseline": round(immunogenicity_baseline, 3),
                "developability_baseline": round(developability_baseline, 3),
                "overall": round(combined_score, 3),  # ：combined_score
            },
            "comment_short": comment_short,
        })
    
    # selected
    selected = None
    if best_match and selected_id:
        best_alignment_scores = best_match.get("alignment_scores", {}) or {}
        best_scoring_details = best_alignment_scores.get("scoring_details", {}) or {}
        selected_combined_score = (
            best_scoring_details.get("combined_score") or
            best_alignment_scores.get("combined_score") or
            best_match.get("combined_score", 0.0)
        )
        
        selected_framework_identity = best_alignment_scores.get("framework_identity", 0.0)
        selected_vhh_hallmark = best_alignment_scores.get("vhh_hallmark_score", 0.0)
        
        # best_matchdevelopabilityimmunogenicity
        best_dev = best_match.get("developability", {}) or {}
        selected_dev_baseline = best_dev.get("score", 0.5)
        
        best_immuno = best_match.get("immunogenicity", {}) or {}
        selected_immuno_baseline = 0.0  # 
        
        # family
        selected_family = "Human VH3"
        if "VH3" in selected_id:
            selected_family = "Human VH3"
        elif "VH1" in selected_id:
            selected_family = "Human VH1"
        elif "VH2" in selected_id:
            selected_family = "Human VH2"
        elif "VH4" in selected_id:
            selected_family = "Human VH4"
        elif "VH5" in selected_id:
            selected_family = "Human VH5"
        elif "VH6" in selected_id:
            selected_family = "Human VH6"
        
        selected = {
            "id": selected_id,
            "family": selected_family,
            "scores": {
                "framework_identity": round(selected_framework_identity, 3),
                "vhh_hallmark": round(selected_vhh_hallmark, 3),
                "immunogenicity_baseline": round(selected_immuno_baseline, 3),
                "developability_baseline": round(selected_dev_baseline, 3),
                "overall": round(selected_combined_score, 3),
            },
            "ranking": {
                "framework_identity_position": "3",  # ，
            },
            "comments": {
                "immunogenicity": "",  # 
                "developability": "",  # 
            },
        }
    
    return {
        "summary_top_n": top_n,
        "candidates": germline_candidates,
        "selected": selected or {},
    }













