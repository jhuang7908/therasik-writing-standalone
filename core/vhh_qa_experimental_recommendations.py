"""


QA v3.0，：
- （directed evolution）
- 
- 
-  ΔTm / ΔΔG
"""

from typing import Dict, List, Any, Optional


def generate_experimental_recommendations(
    qa_v3_result: Dict[str, Any],
    conformation_risk: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    
    
    Args:
        qa_v3_result: QA v3.0
        conformation_risk: （）
    
    Returns:
        experimental_recommendations
    """
    recommendations = {
        "directed_evolution": {
            "recommended": False,
            "priority": "low",
            "reason": "",
            "details": []
        },
        "yeast_display_validation": {
            "recommended": False,
            "priority": "medium",
            "reason": "",
            "details": []
        },
        "multi_template_comparison": {
            "recommended": False,
            "priority": "low",
            "reason": "",
            "details": []
        },
        "thermodynamic_analysis": {
            "recommended": False,
            "priority": "low",
            "reason": "",
            "details": []
        },
        "summary": {
            "overall_risk": "low",
            "critical_issues": [],
            "recommended_actions": []
        }
    }
    
    # QA
    errors = qa_v3_result.get("errors", [])
    warnings = qa_v3_result.get("warnings", [])
    checks = qa_v3_result.get("checks", {})
    summary_score = qa_v3_result.get("summary_score", {})
    
    biological_feasibility = summary_score.get("biological_feasibility", 100)
    risk_level = summary_score.get("risk_level", "low")
    
    # 1. Directed Evolution
    # grafting impact，directed evolution
    structural_compat = checks.get("structural_compat", {})
    grafting_impact = checks.get("grafting_impact", {})
    
    impact_norm = grafting_impact.get("impact_score_normalized", 0)
    if impact_norm >= 0.4 or structural_compat.get("errors"):
        recommendations["directed_evolution"]["recommended"] = True
        recommendations["directed_evolution"]["priority"] = "high"
        recommendations["directed_evolution"]["reason"] = "grafting impact，directed evolution"
        recommendations["directed_evolution"]["details"].append(
            f"Grafting impact normalized score: {impact_norm:.3f}"
        )
        if structural_compat.get("errors"):
            recommendations["directed_evolution"]["details"].extend(
                structural_compat.get("errors", [])
            )
    
    # 2. 
    # biological feasibility < 80 ranking sanity，
    ranking_sanity = checks.get("ranking_sanity", {})
    
    if biological_feasibility < 80 or ranking_sanity.get("errors") or impact_norm >= 0.2:
        recommendations["yeast_display_validation"]["recommended"] = True
        recommendations["yeast_display_validation"]["priority"] = "high" if biological_feasibility < 70 else "medium"
        recommendations["yeast_display_validation"]["reason"] = "，"
        recommendations["yeast_display_validation"]["details"].append(
            f"Biological feasibility: {biological_feasibility:.1f}/100"
        )
        if ranking_sanity.get("errors"):
            recommendations["yeast_display_validation"]["details"].extend(
                ranking_sanity.get("errors", [])
            )
    
    # 3. 
    # ranking sanity，
    if ranking_sanity.get("errors") or ranking_sanity.get("warnings"):
        recommendations["multi_template_comparison"]["recommended"] = True
        recommendations["multi_template_comparison"]["priority"] = "medium"
        recommendations["multi_template_comparison"]["reason"] = "，"
        recommendations["multi_template_comparison"]["details"].extend(
            ranking_sanity.get("errors", []) + ranking_sanity.get("warnings", [])
        )
    
    # 4. （ΔTm / ΔΔG）
    # grafting impact，
    if conformation_risk:
        overall_feasibility = conformation_risk.get("overall_structural_feasibility", {})
        feasibility_score = overall_feasibility.get("score", 100)
        
        if feasibility_score < 70 or impact_norm >= 0.3:
            recommendations["thermodynamic_analysis"]["recommended"] = True
            recommendations["thermodynamic_analysis"]["priority"] = "high" if feasibility_score < 60 else "medium"
            recommendations["thermodynamic_analysis"]["reason"] = "，（ΔTm/ΔΔG）"
            recommendations["thermodynamic_analysis"]["details"].append(
                f"Overall structural feasibility: {feasibility_score:.1f}/100"
            )
            recommendations["thermodynamic_analysis"]["details"].append(
                f"Grafting impact normalized: {impact_norm:.3f}"
            )
    
    # 
    recommendations["summary"]["overall_risk"] = risk_level
    recommendations["summary"]["critical_issues"] = errors[:5]  # 5
    recommendations["summary"]["recommended_actions"] = [
        {
            "action": "directed_evolution",
            "priority": recommendations["directed_evolution"]["priority"],
            "recommended": recommendations["directed_evolution"]["recommended"]
        },
        {
            "action": "yeast_display_validation",
            "priority": recommendations["yeast_display_validation"]["priority"],
            "recommended": recommendations["yeast_display_validation"]["recommended"]
        },
        {
            "action": "multi_template_comparison",
            "priority": recommendations["multi_template_comparison"]["priority"],
            "recommended": recommendations["multi_template_comparison"]["recommended"]
        },
        {
            "action": "thermodynamic_analysis",
            "priority": recommendations["thermodynamic_analysis"]["priority"],
            "recommended": recommendations["thermodynamic_analysis"]["recommended"]
        }
    ]
    
    return recommendations

















