"""
JSON

JSON，germline_selection_proofgermline.candidates[].scores.overall
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List, Optional


def build_germline_selection_proof_from_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    datagermline_selection_proof
    
    Args:
        data: JSON，candidates[], best_match, germline
    
    Returns:
        germline_selection_proof
    """
    candidates = data.get("candidates", [])
    best_match = data.get("best_match", {})
    germline = data.get("germline", {})
    
    # 
    candidate_scores = []
    for candidate in candidates:
        template_id = candidate.get("template_id", "UNKNOWN")
        alignment_scores = candidate.get("alignment_scores", {}) or {}
        scoring_details = alignment_scores.get("scoring_details", {}) or {}
        
        # combined_score
        combined_score = (
            scoring_details.get("combined_score") or
            alignment_scores.get("combined_score", 0.0)
        )
        
        # tie-breaker
        framework_identity = alignment_scores.get("framework_identity", 0.0)
        key_position_score = alignment_scores.get("key_position_score", 1.0)
        cdr_compatibility_score = alignment_scores.get("cdr_compatibility_score", 1.0)
        developability_score = alignment_scores.get("developability_score") or scoring_details.get("developability_score", 0.5)
        
        candidate_scores.append({
            "template_id": template_id,
            "combined_score": combined_score,
            "framework_identity": framework_identity,
            "key_position_score": key_position_score,
            "cdr_compatibility_score": cdr_compatibility_score,
            "developability_score": developability_score,
            "candidate": candidate,  # candidate
        })
    
    # combined_score
    candidate_scores.sort(key=lambda x: x["combined_score"], reverse=True)
    
    # ranked_top10
    ranked_top10 = []
    for rank, item in enumerate(candidate_scores[:10], 1):
        ranked_top10.append({
            "template_id": item["template_id"],
            "rank": rank,
            "combined_score": round(item["combined_score"], 3),
            "framework_identity": round(item["framework_identity"], 3),
            "cdr_compatibility_score": round(item["cdr_compatibility_score"], 3),
            "key_position_score": round(item["key_position_score"], 3),
            "developability_score": round(item["developability_score"], 3),
        })
    
    # best_matchtemplate_idrank
    best_match_template = best_match.get("template", {}) or {}
    selected_template_id = (
        best_match_template.get("template_id") or
        best_match.get("template_id") or
        "UNKNOWN"
    )
    
    selected_rank = 1
    selected_combined_score = 0.0
    for item in candidate_scores:
        if item["template_id"] == selected_template_id:
            selected_rank = candidate_scores.index(item) + 1
            selected_combined_score = item["combined_score"]
            break
    
    # consistency_checks
    best_match_template_id = (
        best_match_template.get("template_id") or
        best_match.get("template_id") or
        "UNKNOWN"
    )
    
    # germline.candidates[].scores.overall
    germline_candidates = germline.get("candidates", [])
    germline_overall_filled = False
    if germline_candidates:
        # overall0
        first_candidate_overall = germline_candidates[0].get("scores", {}).get("overall", 0.0)
        germline_overall_filled = (first_candidate_overall != 0.0)
    
    consistency_checks = {
        "best_match_template_id_equals_selected": (
            best_match_template_id == selected_template_id
        ),
        "best_match_score_equals_selected": (
            abs(best_match.get("combined_score", 0.0) - selected_combined_score) < 0.001
        ),
        "germline_table_overall_populated": germline_overall_filled,
    }
    
    # provenance
    proof = {
        "objective": "maximize_combined_score",
        "score_source_path": "candidates[].alignment_scores.scoring_details.combined_score",
        "tie_breakers": [
            "candidates[].alignment_scores.framework_identity",
            "candidates[].alignment_scores.key_position_score",
            "candidates[].alignment_scores.cdr_compatibility_score",
            "candidates[].alignment_scores.developability_score",
        ],
        "eligible_candidate_count": len(candidates),
        "ranked_top10": ranked_top10,
        "selected": {
            "template_id": selected_template_id,
            "rank": selected_rank,
            "combined_score": round(selected_combined_score, 3),
        },
        "consistency_checks": consistency_checks,
    }
    
    return proof


def fix_germline_candidates_overall(data: Dict[str, Any]) -> None:
    """
    germline.candidates[].scores.overall
    
    germline.candidates，candidatescombined_score
    """
    germline = data.get("germline", {})
    if not germline:
        return
    
    candidates = data.get("candidates", [])
    if not candidates:
        return
    
    # template_idcandidate
    candidate_map = {}
    for candidate in candidates:
        template_id = candidate.get("template_id")
        if template_id:
            candidate_map[template_id] = candidate
    
    # germline.candidates
    germline_candidates = germline.get("candidates", [])
    for germline_cand in germline_candidates:
        template_id = germline_cand.get("id")
        if not template_id:
            continue
        
        # candidatestemplate_id
        matched_candidate = candidate_map.get(template_id)
        
        if matched_candidate:
            # ，combined_score
            alignment_scores = matched_candidate.get("alignment_scores", {}) or {}
            scoring_details = alignment_scores.get("scoring_details", {}) or {}
            combined_score = (
                scoring_details.get("combined_score") or
                alignment_scores.get("combined_score", 0.0)
            )
            
            # scores.overall
            if "scores" not in germline_cand:
                germline_cand["scores"] = {}
            germline_cand["scores"]["overall"] = round(combined_score, 3)
        else:
            # ，comment_short
            comment = germline_cand.get("comment_short", "")
            if "[NO_MATCH_IN_CANDIDATES]" not in comment:
                germline_cand["comment_short"] = f"{comment} [NO_MATCH_IN_CANDIDATES]"


def prepare_json_data(result: Dict[str, Any], purpose: str = "REPORT") -> Dict[str, Any]:
    """
    JSON，germline_selection_proofgermline.candidates[].scores.overall
    
    Args:
        result: 
        purpose: （"REPORT", "QA_CHECK"）
    
    Returns:
        JSON
    """
    # VHH QA  germline SHA256 / ；， cdr_canonical 
    if purpose == "QA_CHECK":
        json_data = dict(result)
        try:
            if ("germline" not in json_data or not json_data.get("germline")) and json_data.get(
                "candidates"
            ) and json_data.get("best_match"):
                from core.germline_data_builder import build_germline_candidates

                json_data["germline"] = build_germline_candidates(
                    candidates=json_data["candidates"],
                    best_match=json_data["best_match"],
                    top_n=10,
                )
            fix_germline_candidates_overall(json_data)
        except Exception:
            pass
        return json_data

    # result
    json_data = result.copy()
    
    # germline，（build_germline_candidates）
    if "germline" not in json_data or not json_data.get("germline"):
        from core.germline_data_builder import build_germline_candidates
        
        candidates = json_data.get("candidates", [])
        best_match = json_data.get("best_match", {})
        
        if candidates and best_match:
            json_data["germline"] = build_germline_candidates(
                candidates=candidates,
                best_match=best_match,
                top_n=10
            )
    
    # germline.candidates[].scores.overall
    fix_germline_candidates_overall(json_data)
    
    # germline_selection_proof
    if json_data.get("candidates") and json_data.get("best_match"):
        json_data["germline_selection_proof"] = build_germline_selection_proof_from_data(json_data)
    
    # 1：germline_library_provenance（）
    # ：，
    from core.germline_library_provenance import build_germline_library_provenance
    json_data["germline_library_provenance"] = build_germline_library_provenance(json_data)
    
    # germline_library_provenancesha256
    if not json_data["germline_library_provenance"].get("sha256"):
        raise ValueError(
            "germline_library_provenance.sha256 。"
            "SHA256。"
        )
    
    # 23：germlineIMGT（ANARCII）
    # ：，
    from core.segmentation.germline_numbering import number_germline_templates
    json_data["germline_numbering"] = number_germline_templates(json_data)
    
    # germline_numberingnumbering_provenance
    if "error" in json_data["germline_numbering"]:
        raise ValueError(
            f"germline_numbering: {json_data['germline_numbering'].get('error')}。"
            "germlineIMGT。"
        )
    
    numbering_provenance = json_data["germline_numbering"].get("numbering_provenance")
    if not numbering_provenance:
        raise ValueError(
            "germline_numbering.numbering_provenance 。"
            "ANARCII。"
        )
    
    if numbering_provenance.get("method") != "anarcii":
        method = numbering_provenance.get("method", "unknown")
        if not method.startswith("fallback:"):
            raise ValueError(
                f"germline_numbering.numbering_provenance.method = '{method}' != 'anarcii'。"
                "ANARCII（fallback）。"
            )
    
    return json_data

