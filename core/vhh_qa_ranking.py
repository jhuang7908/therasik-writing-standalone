"""
QA

，bug

: 3.0.0
:
  - FR identitycombined score
  - VHH hallmark
  - （impact_score）ranking
  - Combined score
"""

from typing import Dict, List, Any, Tuple

# 
RANKING_SANITY_VERSION = "3.0.0"
RANKING_SANITY_THRESHOLDS = {
    "fr_identity_diff": 0.05,  # FR identity
    "combined_score_diff": 0.02,  # Combined score
    "impact_score_diff": 2.0,  # Impact score（）
    "impact_score_normalized_diff": 0.15  # Impact score
}


def qa_ranking_sanity(candidates: List[Dict[str, Any]]) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """
    
    
    Args:
        candidates: ，combined score（best first）
    
    Returns:
        (errors, warnings, sanity_details)
    """
    errors = []
    warnings = []
    sanity_details = {
        "ranking_issues": [],
        "score_consistency": {}
    }
    
    if not candidates or len(candidates) < 1:
        return errors, warnings, sanity_details
    
    best = candidates[0]
    others = candidates[1:min(3, len(candidates))]  # 3
    
    # 
    best_scores = best.get("alignment_scores", {}) or best.get("scores", {})
    best_fr = best_scores.get("framework_identity", 0)
    best_combined = best_scores.get("combined_score", 0)
    best_flags = best.get("flags", {}) or {}
    best_has_hallmark = best_flags.get("has_vhh_hallmark", True)  # 
    
    # hallmark（FR2）
    template = best.get("template", {})
    if isinstance(template, dict):
        template_flags = template.get("flags", {}) or {}
        best_has_hallmark = template_flags.get("has_vhh_hallmark", best_has_hallmark)
    
    # 
    for i, c in enumerate(others, 1):
        c_scores = c.get("alignment_scores", {}) or c.get("scores", {})
        c_fr = c_scores.get("framework_identity", 0) or c_scores.get("fr_identity", 0)
        c_combined = c_scores.get("combined_score", 0) or c_scores.get("combined", 0)
        c_flags = c.get("flags", {}) or {}
        c_has_hallmark = c_flags.get("has_vhh_hallmark", True)
        
        template_c = c.get("template", {})
        if isinstance(template_c, dict):
            template_c_flags = template_c.get("flags", {}) or {}
            c_has_hallmark = template_c_flags.get("has_vhh_hallmark", c_has_hallmark)
        
        # 1：FR identity，combined score
        fr_gap = c_fr - best_fr
        combined_gap = best_combined - c_combined
        
        # v3.2：errorwarning
        if fr_gap >= 0.10 and combined_gap <= 0.03:
            # silent failure：
            issue = {
                "type": "fr_identity_mismatch_critical",
                "rank": i + 1,
                "candidate_id": c.get("template_id", f"candidate_{i+1}"),
                "fr_identity_diff": fr_gap,
                "combined_score_diff": combined_gap,
                "severity": "error"
            }
            sanity_details["ranking_issues"].append(issue)
            errors.append(
                f"Ranking sanity violated — FR identity vs combined inconsistency: "
                f" {c.get('template_id', f'#{i+1}')}  FR identity ({c_fr:.2%})  "
                f"{best.get('template_id', '#1')} ({best_fr:.2%})，={fr_gap:.2%}，"
                f" ({best_combined:.3f} vs {c_combined:.3f}，={combined_gap:.3f})。"
                f"scoring model，。"
            )
        elif fr_gap >= 0.05 and combined_gap <= 0.02:
            # warning
            issue = {
                "type": "fr_identity_mismatch",
                "rank": i + 1,
                "candidate_id": c.get("template_id", f"candidate_{i+1}"),
                "fr_identity_diff": fr_gap,
                "combined_score_diff": combined_gap,
                "severity": "warning"
            }
            sanity_details["ranking_issues"].append(issue)
            warnings.append(
                f" {c.get('template_id', f'#{i+1}')}  FR identity ({c_fr:.2%})  "
                f"{best.get('template_id', '#1')} ({best_fr:.2%})， "
                f"({best_combined:.3f} vs {c_combined:.3f})，。"
            )
        
        # 2：VHH hallmark，
        if not best_has_hallmark and c_has_hallmark:
            issue = {
                "type": "hallmark_mismatch",
                "rank": i + 1,
                "candidate_id": c.get("template_id", f"candidate_{i+1}"),
                "best_has_hallmark": False,
                "candidate_has_hallmark": True
            }
            sanity_details["ranking_issues"].append(issue)
            errors.append(
                f" {best.get('template_id', '#1')}  VHH hallmark， "
                f"{c.get('template_id', f'#{i+1}')}  hallmark，"
                "VHH，。"
            )
        
        # 3：（impact_score）ranking
        # impact_score（）- qa_v3
        # ：candidatesqa_v3，
        best_qa_v3 = best.get("qa_v3", {})
        c_qa_v3 = c.get("qa_v3", {})
        
        if best_qa_v3 and c_qa_v3:
            best_impact_norm = best_qa_v3.get("checks", {}).get("grafting_impact", {}).get("impact_score_normalized", 0)
            c_impact_norm = c_qa_v3.get("checks", {}).get("grafting_impact", {}).get("impact_score_normalized", 0)
            
            # ，，
            if c_impact_norm < best_impact_norm - RANKING_SANITY_THRESHOLDS["impact_score_normalized_diff"]:
                issue = {
                    "type": "structural_risk_mismatch",
                    "rank": i + 1,
                    "candidate_id": c.get("template_id", f"candidate_{i+1}"),
                    "best_impact_normalized": best_impact_norm,
                    "candidate_impact_normalized": c_impact_norm,
                    "impact_diff": best_impact_norm - c_impact_norm
                }
                sanity_details["ranking_issues"].append(issue)
                errors.append(
                    f" {c.get('template_id', f'#{i+1}')}  (impact_score_normalized={c_impact_norm:.3f}) "
                    f" {best.get('template_id', '#1')} ({best_impact_norm:.3f})，"
                    "。，。"
                )
    
    # combined score（）
    if best_scores:
        # combined score（）
        # ，
        required_fields = ["framework_identity", "combined_score"]
        missing_fields = [f for f in required_fields if f not in best_scores]
        
        if missing_fields:
            warnings.append(
                f": {missing_fields}，。"
            )
    
    return errors, warnings, sanity_details

