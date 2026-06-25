"""
VHHQA v3.3

v3.3：
- （minor/major）
- 4
- 
- QA
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# v3.0/v3.2
from core.vhh_qa_validation import (
    rebuild_v_region_from_regions,
    _collect_fr_differences,
    V_REGION_ORDER,
    IMGT_REGIONS,
    validate_vhh_humanization_result  # v2.0
)
from core.vhh_qa_structural_rules import (
    check_cdr1_fr2_compatibility,
    check_cdr3_fr3_compatibility,
    check_cdr2_compatibility
)
from core.vhh_qa_grafting import qa_grafting_impact
from core.vhh_qa_mutation_map import generate_mutation_map
from core.vhh_qa_conformation_risk import generate_conformation_risk_summary
from core.vhh_qa_experimental_recommendations import generate_experimental_recommendations


def auto_build_mutations_from_regions(
    orig_regions: Dict[str, str],
    hum_regions: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    regionsmutations.list
    
    ，mutations.listregions
    
    Args:
        orig_regions: 
        hum_regions: 
    
    Returns:
        mutations， {"region": str, "position": int, "from": str, "to": str}
    """
    mutations = []
    
    # IMGT（position）
    IMGT_REGION_STARTS = {
        "FR1": 1,   # IMGT 1-26
        "CDR1": 27, # IMGT 27-38
        "FR2": 39,  # IMGT 39-55
        "CDR2": 56, # IMGT 56-65
        "FR3": 66,  # IMGT 66-104
        "CDR3": 105, # IMGT 105-117
        "FR4": 118, # IMGT 118+
    }
    
    # FR（VHH FR-only）
    for region in ["FR1", "FR2", "FR3", "FR4"]:
        o = orig_regions.get(region, "") or ""
        h = hum_regions.get(region, "") or ""
        
        region_start = IMGT_REGION_STARTS.get(region, 0)
        min_len = min(len(o), len(h))
        
        for i in range(min_len):
            if o[i] != h[i]:
                # positionIMGT（1-based）
                imgt_pos = region_start + i
                mutations.append({
                    "region": region,
                    "position": imgt_pos,
                    "from": o[i],
                    "to": h[i]
                })
    
    return mutations


def _create_warning(level: str, category: str, message: str) -> Dict[str, str]:
    """
    warning
    
    Args:
        level: "minor" | "major"
        category: "delta_risk" | "structural" | "ranking" | "fallback" | ...
        message: 
    
    Returns:
        warning
    """
    return {
        "level": level,
        "category": category,
        "message": message
    }


def _qa_structural_compat_cdr3_fr3_v3_3(
    cdr3_len: int,
    fr3_len: int
) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    v3.3：CDR3-FR3（P06）
    
    ：
    - CDR3 2-14aa: FR3≥35aa，35-36aaminor_warning
    - CDR3 15-24aa: FR3≥38aa，<38aaerror
    - CDR3 ≥25aa: FR3≥40aa，<40aaerror
    """
    errors = []
    warnings = []
    
    if 2 <= cdr3_len <= 14:
        # CDR3
        if fr3_len < 35:
            warnings.append(_create_warning(
                "major",
                "structural",
                f"CDR3={cdr3_len}aa, FR3={fr3_len}aa ，"
                "。"
            ))
        elif 35 <= fr3_len < 37:
            warnings.append(_create_warning(
                "minor",
                "structural",
                f"CDR3={cdr3_len}aa, FR3={fr3_len}aa ，"
                "，。"
            ))
        # fr3_len >= 37: 
    
    elif 15 <= cdr3_len <= 24:
        # CDR3
        if fr3_len < 38:
            warnings.append(_create_warning(
                "major",
                "structural",
                f"CDR3  ({cdr3_len} aa)，FR3  {fr3_len} aa，"
                "，。"
            ))
        elif 38 <= fr3_len < 40:
            warnings.append(_create_warning(
                "major",
                "structural",
                f"CDR3={cdr3_len}aa, FR3={fr3_len}aa ，"
                "。"
            ))
    
    elif cdr3_len >= 25:
        # CDR3
        if fr3_len < 40:
            warnings.append(_create_warning(
                "major",
                "structural",
                f"CDR3  ({cdr3_len} aa)，FR3  {fr3_len} aa，"
                "，。"
            ))
        elif 40 <= fr3_len < 42:
            warnings.append(_create_warning(
                "major",
                "structural",
                f"CDR3={cdr3_len}aa, FR3={fr3_len}aa ，"
                "。"
            ))
    
    return errors, warnings


def _check_developability_delta_v3_3(
    orig_score: float,
    hum_score: float,
    score_type: str = "aggregate"
) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    v3.3：Developability delta（P04）
    
    ：
    - Δ <= -0.10: error（）
    - -0.10 < Δ <= -0.05: major warning（）
    - -0.05 < Δ < 0: minor warning（）
    - Δ >= 0: 
    """
    errors = []
    warnings = []
    
    delta_dev = hum_score - orig_score  # 
    
    if delta_dev <= -0.10:
        warnings.append(_create_warning(
            "major",
            "delta_risk",
            f" developability  (Δ={delta_dev:.3f})，"
            f" {orig_score:.3f}  {hum_score:.3f}，。"
        ))
    elif -0.10 < delta_dev <= -0.05:
        warnings.append(_create_warning(
            "major",
            "delta_risk",
            f" developability  (Δ={delta_dev:.3f})，"
            "。"
        ))
    elif -0.05 < delta_dev < 0:
        warnings.append(_create_warning(
            "minor",
            "delta_risk",
            f" developability  (Δ={delta_dev:.3f})，"
            "，。"
        ))
    # delta_dev >= 0: 
    
    return errors, warnings


def _qa_ranking_sanity_v3_3(
    candidates: List[Dict[str, Any]],
    errors: List[str],
    warnings: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    v3.3：Ranking sanity（P08）
    
    ：
    - fr_gap >= 0.10 & comb_gap <= 0.03: error
    - 0.05 <= fr_gap < 0.10 & comb_gap <= 0.03: major warning
    - 0.03 <= fr_gap < 0.05 & comb_gap <= 0.02: minor warning
    """
    sanity_details = {
        "ranking_issues": [],
        "score_consistency": {}
    }
    
    if not candidates or len(candidates) < 2:
        return sanity_details
    
    best = candidates[0]
    others = candidates[1:min(3, len(candidates))]
    
    # 
    best_scores = best.get("alignment_scores", {}) or best.get("scores", {})
    best_fr = best_scores.get("framework_identity", 0) or best_scores.get("fr_identity", 0)
    best_combined = best_scores.get("combined_score", 0) or best_scores.get("combined", 0)
    best_final = best_scores.get("final", best_combined)  # final score
    
    # 
    for i, c in enumerate(others, 1):
        c_scores = c.get("alignment_scores", {}) or c.get("scores", {})
        c_fr = c_scores.get("framework_identity", 0) or c_scores.get("fr_identity", 0)
        c_combined = c_scores.get("combined_score", 0) or c_scores.get("combined", 0)
        c_final = c_scores.get("final", c_combined)  # final score
        
        fr_gap = c_fr - best_fr
        comb_gap = best_final - c_final  # final score
        
        # v3.3
        if fr_gap >= 0.10 and comb_gap <= 0.03:
            #  → major warning（）
            issue = {
                "type": "fr_identity_mismatch_critical",
                "rank": i + 1,
                "candidate_id": c.get("template_id", f"candidate_{i+1}"),
                "fr_identity_diff": fr_gap,
                "combined_score_diff": comb_gap,
                "severity": "major"
            }
            sanity_details["ranking_issues"].append(issue)
            warnings.append(_create_warning(
                "major",
                "ranking",
                f"Ranking sanity: FR identity 。"
                f" {c.get('template_id', f'#{i+1}')} FR identity ({c_fr:.2f}) "
                f" {best.get('template_id', '#1')} ({best_fr:.2f})，"
                f" ({best_final:.3f} vs {c_final:.3f})，。"
            ))
        elif 0.05 <= fr_gap < 0.10 and comb_gap <= 0.03:
            #  → major warning
            issue = {
                "type": "fr_identity_mismatch_major",
                "rank": i + 1,
                "candidate_id": c.get("template_id", f"candidate_{i+1}"),
                "fr_identity_diff": fr_gap,
                "combined_score_diff": comb_gap,
                "severity": "major"
            }
            sanity_details["ranking_issues"].append(issue)
            warnings.append(_create_warning(
                "major",
                "ranking",
                f" {c.get('template_id', f'#{i+1}')}  FR identity ({c_fr:.2f}) "
                f" {best.get('template_id', '#1')} ({best_fr:.2f})，"
                f" ({best_final:.3f} vs {c_final:.3f})，"
                "。"
            ))
        elif 0.03 <= fr_gap < 0.05 and comb_gap <= 0.02:
            #  → minor warning
            issue = {
                "type": "fr_identity_mismatch_minor",
                "rank": i + 1,
                "candidate_id": c.get("template_id", f"candidate_{i+1}"),
                "fr_identity_diff": fr_gap,
                "combined_score_diff": comb_gap,
                "severity": "minor"
            }
            sanity_details["ranking_issues"].append(issue)
            warnings.append(_create_warning(
                "minor",
                "ranking",
                f" {c.get('template_id', f'#{i+1}')}  FR identity  "
                f"({c_fr:.2f} vs {best_fr:.2f})， "
                f"({best_final:.3f} vs {c_final:.3f})，"
                "。"
            ))
    
    return sanity_details


def compute_final_score(candidate: Dict[str, Any]) -> float:
    """
    final score（structural riskhallmark penalty）
    
    final_score = combined - 0.20 * structural_risk - hallmark_penalty
    
    Args:
        candidate: 
    
    Returns:
        final score
    """
    scores = candidate.get("alignment_scores", {}) or candidate.get("scores", {})
    base = scores.get("combined_score", 0) or scores.get("combined", 0)
    
    # Structural risk (0~1，)
    structural_risk = scores.get("structural_risk", 0.0)
    
    # Hallmark penalty
    hallmark_penalty = 0.0
    flags = candidate.get("flags", {}) or {}
    template = candidate.get("template", {})
    if isinstance(template, dict):
        template_flags = template.get("flags", {}) or {}
        flags = {**flags, **template_flags}
    
    if not flags.get("has_vhh_hallmark", True):
        hallmark_penalty += 0.15
    elif flags.get("reduced_hallmark", False):
        hallmark_penalty += 0.05
    
    final = base - 0.20 * structural_risk - hallmark_penalty
    
    # candidatescores
    if "scores" not in candidate:
        candidate["scores"] = {}
    candidate["scores"]["final"] = final
    
    return final


def validate_vhh_humanization_result_v3_3(
    result: Dict[str, Any],
    strict: bool = True
) -> Dict[str, Any]:
    """
    VHHQA v3.3
    
    v3.3：
    - （minor/major）
    - 4
    - 
    - QA
    """
    errors: List[str] = []
    warnings: List[Dict[str, str]] = []  # v3.3: warnings
    
    # 
    seq_analysis = result.get("sequence_analysis", {})
    orig_regions = seq_analysis.get("original_regions", {}) or {}
    hum_regions = seq_analysis.get("humanized_regions", {}) or {}
    
    # v2.0（）
    qa_v2 = validate_vhh_humanization_result(result, strict=False)
    v2_errors = qa_v2.get("errors", [])
    # v3.3: ，FR3
    # CDR3≤14FR3≥35，FR3errorwarning
    cdr3_len = len(hum_regions.get("CDR3", ""))
    fr3_len = len(hum_regions.get("FR3", ""))
    
    # v3.3 ： v2.0 errors  minor warning，
    for e in v2_errors:
        warnings.append(_create_warning("minor", "integrity", e))
    
    # v2warningsv3.3（minor）
    for w in qa_v2.get("warnings", []):
        if isinstance(w, str):
            warnings.append(_create_warning("minor", "integrity", w))
        elif isinstance(w, dict):
            warnings.append(w)
    
    # === v3.3: mutations.list（） ===
    mutations = result.get("mutations", {})
    if isinstance(mutations, dict):
        mut_list = mutations.get("list", [])
    else:
        mut_list = mutations if isinstance(mutations, list) else []
    
    # mutations.list，
    if len(mut_list) == 0 and orig_regions and hum_regions:
        auto_mutations = auto_build_mutations_from_regions(orig_regions, hum_regions)
        if len(auto_mutations) > 0:
            if isinstance(mutations, dict):
                mutations["list"] = auto_mutations
            else:
                result["mutations"] = {"list": auto_mutations}
            mut_list = auto_mutations
    
    # === （v3.3） ===
    structural_errors = []
    structural_warnings = []
    
    if orig_regions and hum_regions:
        cdr1_len = len(hum_regions.get("CDR1", ""))
        cdr2_len = len(hum_regions.get("CDR2", ""))
        cdr3_len = len(hum_regions.get("CDR3", ""))
        fr2_len = len(hum_regions.get("FR2", ""))
        fr3_len = len(hum_regions.get("FR3", ""))
        
        # CDR1–FR2 （v3.2）
        if cdr1_len > 0 and fr2_len > 0:
            if cdr1_len < 5 or fr2_len < 13:
                structural_errors.append(
                    f"CDR1–FR2VHH: CDR1={cdr1_len}aa（5aa），"
                    f"FR2={fr2_len}aa（13aa，15-19aa）。"
                    f"，fail。"
                )
            else:
                is_compat, note, rule_strength = check_cdr1_fr2_compatibility(cdr1_len, fr2_len)
                if not is_compat:
                    if rule_strength == "strong":
                        structural_errors.append(
                            f"CDR1 ={cdr1_len}  FR2 ={fr2_len} （{note}），"
                            f"。"
                        )
                    else:
                        structural_warnings.append(_create_warning(
                            "minor",
                            "structural",
                            f"CDR1 ={cdr1_len}  FR2 ={fr2_len} ，"
                            f"。"
                        ))
        
        # CDR3–FR3 （v3.3 - P06）
        if cdr3_len > 0 and fr3_len > 0:
            cdr3_errors, cdr3_warnings = _qa_structural_compat_cdr3_fr3_v3_3(cdr3_len, fr3_len)
            structural_errors.extend(cdr3_errors)
            structural_warnings.extend(cdr3_warnings)
        
        # CDR2 
        if cdr2_len > 0 and fr2_len > 0 and fr3_len > 0:
            is_compat, note, rule_strength = check_cdr2_compatibility(cdr2_len, fr2_len, fr3_len)
            if not is_compat:
                structural_warnings.append(_create_warning(
                    "minor",
                    "structural",
                    f"CDR2 ={cdr2_len}  FR2/FR3 ，。"
                ))
    
    # === Grafting Impact ===
    grafting_errors = []
    grafting_warnings = []
    impact_details = {}
    
    if orig_regions and hum_regions:
        grafting_errors_list, grafting_warnings_list, impact_details = qa_grafting_impact(
            orig_regions, hum_regions
        )
        grafting_errors.extend(grafting_errors_list)
        # grafting warningsv3.3
        for w in grafting_warnings_list:
            if isinstance(w, str):
                # impact_score_normalizedlevel
                impact_norm = impact_details.get("impact_score_normalized", 0)
                level = "major" if impact_norm >= 0.2 else "minor"
                grafting_warnings.append(_create_warning(level, "grafting", w))
            elif isinstance(w, dict):
                grafting_warnings.append(w)
    
    # === Delta（v3.3 - P04） ===
    delta_errors = []
    delta_warnings = []
    
    best_match = result.get("best_match", {})
    developability = best_match.get("developability", {})
    immunogenicity = best_match.get("immunogenicity", {})
    
    orig_developability = result.get("original_developability", {})
    orig_immunogenicity = result.get("original_immunogenicity", {})
    
    if developability and orig_developability:
        score_type = developability.get("score_type", "aggregate")
        orig_score = orig_developability.get("score", 0.5)
        hum_score = developability.get("score", 0.5)
        
        dev_errors, dev_warnings = _check_developability_delta_v3_3(orig_score, hum_score, score_type)
        delta_errors.extend(dev_errors)
        delta_warnings.extend(dev_warnings)
    
    if immunogenicity and orig_immunogenicity:
        # Immunogenicity（v3.2）
        risk_order = {"low": 1, "medium": 2, "high": 3}
        orig_risk = orig_immunogenicity.get("fr_immuno_risk", "low")
        hum_risk = immunogenicity.get("fr_immuno_risk", "low")
        
        orig_risk_val = risk_order.get(orig_risk, 1)
        hum_risk_val = risk_order.get(hum_risk, 1)
        delta_imm = hum_risk_val - orig_risk_val
        
        if delta_imm > 0:
            delta_warnings.append(_create_warning(
                "major",
                "delta_risk",
                f"（{orig_risk}{hum_risk}），"
                " FR ，。"
            ))
    
    # === Ranking Sanity（v3.3 - P08） ===
    ranking_errors = []
    ranking_warnings = []
    ranking_sanity_details = {"ranking_issues": [], "score_consistency": {}}
    
    candidates = result.get("candidates", [])
    if candidates:
        # final score（）
        for cand in candidates:
            if "scores" not in cand:
                cand["scores"] = {}
            if "final" not in cand.get("scores", {}):
                compute_final_score(cand)
        
        # candidatesfinal score
        sorted_candidates = sorted(
            candidates,
            key=lambda x: x.get("scores", {}).get("final", 
                x.get("scores", {}).get("combined", 0) or
                x.get("alignment_scores", {}).get("combined_score", 0)),
            reverse=True
        )
        
        ranking_sanity_details = _qa_ranking_sanity_v3_3(sorted_candidates, ranking_errors, ranking_warnings)
    
    # === errorswarnings ===
    errors.extend(structural_errors)
    errors.extend(delta_errors)
    errors.extend(grafting_errors)
    errors.extend(ranking_errors)
    
    warnings.extend(structural_warnings)
    warnings.extend(delta_warnings)
    warnings.extend(grafting_warnings)
    warnings.extend(ranking_warnings)
    
    # === summary score ===
    biological_feasibility = 100.0
    if len(errors) > 0:
        biological_feasibility -= len(errors) * 15
    if len([w for w in warnings if w.get("level") == "major"]) > 0:
        biological_feasibility -= len([w for w in warnings if w.get("level") == "major"]) * 5
    if len([w for w in warnings if w.get("level") == "minor"]) > 0:
        biological_feasibility -= len([w for w in warnings if w.get("level") == "minor"]) * 2
    
    biological_feasibility = max(0, min(100, biological_feasibility))
    
    if biological_feasibility >= 80:
        risk_level = "low"
    elif biological_feasibility >= 60:
        risk_level = "medium"
    else:
        risk_level = "high"
    
    # === Mutation Map、Conformation Risk、Experimental Recommendations ===
    mutation_map = {}
    conformation_risk = {}
    experimental_recommendations = {}
    
    if orig_regions and hum_regions:
        mutations_list = result.get("mutations", {}).get("list", [])
        template_info = result.get("best_match", {}).get("template", {})
        mutation_map = generate_mutation_map(
            orig_regions, hum_regions, mutations_list, template_info
        )
        conformation_risk = generate_conformation_risk_summary(hum_regions, None)
    
    # qa_v3_3
    temp_qa_v3_3 = {
        "errors": errors,
        "warnings": warnings,
        "checks": {
            "structural_compat": {"errors": structural_errors, "warnings": structural_warnings},
            "grafting_impact": {"errors": grafting_errors, "warnings": grafting_warnings},
            "ranking_sanity": {"errors": ranking_errors, "warnings": ranking_warnings},
            "delta_risk": {"errors": delta_errors, "warnings": delta_warnings}
        },
        "summary_score": {
            "biological_feasibility": round(biological_feasibility, 1),
            "risk_level": risk_level
        }
    }
    experimental_recommendations = generate_experimental_recommendations(
        temp_qa_v3_3, conformation_risk
    )
    
    # === qa_v3_3 ===
    qa_v3_3 = {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,  # v3.3:  [{level, category, message}]
        "checks": {
            "integrity": {
                "ok": len([e for e in errors if "FR4" in e or "CDR" in e or "" in e or "" in e]) == 0,
                "errors": [e for e in errors if "FR4" in e or "CDR" in e or "" in e or "" in e],
                "warnings": [w for w in warnings if w.get("category") == "integrity"]
            },
            "structural_compat": {
                "ok": len(structural_errors) == 0,
                "errors": structural_errors,
                "warnings": structural_warnings
            },
            "grafting_impact": {
                "ok": len(grafting_errors) == 0,
                "errors": grafting_errors,
                "warnings": grafting_warnings,
                "impact_score": impact_details.get("impact_score", 0),
                "impact_score_normalized": impact_details.get("impact_score_normalized", 0),
                "interface_changes": impact_details.get("interface_changes", []),
                "total_interface_positions": impact_details.get("total_interface_positions", 0)
            },
            "ranking_sanity": {
                "ok": len(ranking_errors) == 0,
                "errors": ranking_errors,
                "warnings": ranking_warnings,
                "details": ranking_sanity_details
            },
            "delta_risk": {
                "ok": len(delta_errors) == 0,
                "errors": delta_errors,
                "warnings": delta_warnings
            }
        },
        "summary_score": {
            "biological_feasibility": round(biological_feasibility, 1),
            "risk_level": risk_level
        },
        "mutation_map": mutation_map,
        "conformation_risk_summary": conformation_risk,
        "experimental_recommendations": experimental_recommendations,
        "meta": {
            "version": "3.3.0",
            "ruleset": "VHH_QA_V3.3_CANONICAL",
            "rules_version": "3.3.0",
            "rules_source": [
                "SAbDab VHH canonical classes",
                "IMGT numbering notes",
                "Internal VHH structure database (73 alpaca VHH cases)",
                "Internal VHH grafting case statistics (300 cases)",
                "Human VH3 VHH-SAFE template panel statistics"
            ],
            "scope": "VHH humanization (Human VH3 VHH-SAFE template panel)",
            "customizable": False
        }
    }
    
    return qa_v3_3

