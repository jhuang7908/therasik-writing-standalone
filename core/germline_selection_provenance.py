"""
Germline

germline_selection_proof，、。
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional


def build_germline_selection_proof(
    candidates: List[Dict[str, Any]],
    best_match: Dict[str, Any],
    objective: str = "maximize_combined_score",
) -> Dict[str, Any]:
    """
    germline_selection_proof
    
    Args:
        candidates: （，best first）
        best_match: best_match
        objective: （"maximize_combined_score"）
    
    Returns:
        germline_selection_proof
    """
    # 
    ranked_candidates = []
    for rank, candidate in enumerate(candidates[:10], 1):  # 10
        alignment_scores = candidate.get("alignment_scores", {}) or {}
        scoring_details = alignment_scores.get("scoring_details", {}) or {}
        
        # 
        combined_score = scoring_details.get("combined_score") or alignment_scores.get("combined_score", 0.0)
        framework_identity = alignment_scores.get("framework_identity", 0.0)
        cdr_compatibility_score = alignment_scores.get("cdr_compatibility_score", 1.0)
        key_position_score = alignment_scores.get("key_position_score", 1.0)
        developability_score = alignment_scores.get("developability_score") or scoring_details.get("developability_score", 0.5)
        
        ranked_candidates.append({
            "template_id": candidate.get("template_id", "UNKNOWN"),
            "rank": rank,
            "combined_score": round(combined_score, 3),
            "framework_identity": round(framework_identity, 3),
            "cdr_compatibility_score": round(cdr_compatibility_score, 3),
            "key_position_score": round(key_position_score, 3),
            "developability_score": round(developability_score, 3),
        })
    
    # 
    selected_template_id = (
        best_match.get("template", {}).get("template_id") or
        best_match.get("template_id") or
        best_match.get("human_template", "UNKNOWN")
    )
    
    best_alignment_scores = best_match.get("alignment_scores", {}) or {}
    best_scoring_details = best_alignment_scores.get("scoring_details", {}) or {}
    selected_combined_score = (
        best_scoring_details.get("combined_score") or
        best_alignment_scores.get("combined_score") or
        best_match.get("combined_score", 0.0)
    )
    
    # 
    selected_rank = 1
    for candidate in ranked_candidates:
        if candidate["template_id"] == selected_template_id:
            selected_rank = candidate["rank"]
            break
    
    # 
    best_match_template_id = (
        best_match.get("template", {}).get("template_id") or
        best_match.get("template_id") or
        "UNKNOWN"
    )
    
    consistency_checks = {
        "best_match_template_id_equals_selected": (
            best_match_template_id == selected_template_id
        ),
        "best_match_score_equals_selected": (
            abs(best_alignment_scores.get("combined_score", 0.0) - selected_combined_score) < 0.001
        ),
        "germline_table_overall_populated": len(ranked_candidates) > 0,
    }
    
    # provenance
    proof = {
        "objective": objective,
        "score_source_path": "candidates[].alignment_scores.scoring_details.combined_score",
        "tie_breakers": [
            "candidates[].alignment_scores.framework_identity",
            "candidates[].alignment_scores.key_position_score",
            "candidates[].alignment_scores.cdr_compatibility_score",
            "candidates[].alignment_scores.developability_score",
        ],
        "eligible_candidate_count": len(candidates),
        "ranked_top10": ranked_candidates,
        "selected": {
            "template_id": selected_template_id,
            "rank": selected_rank,
            "combined_score": round(selected_combined_score, 3),
        },
        "consistency_checks": consistency_checks,
    }
    
    return proof

