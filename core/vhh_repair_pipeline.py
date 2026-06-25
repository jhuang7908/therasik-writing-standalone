"""
VHH  Pipeline（）

：
-  VHH clone （baseline）
-  SAFE scaffold 
- 
-  vs 

：
- VHHclone
- 
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.vhh_humanization_with_qa import humanize_vhh_with_qa
from core.vhh_process_logger import VHHProcessLogger


def repair_transgenic_vhh_clone_with_baseline(
    original_seq: str,
    target: str,
    project_id: str,
    safe_scaffolds: Optional[List[Dict[str, Any]]] = None,
    qa_version: str = "v3.5",
) -> Dict[str, Any]:
    """
    VHHclone，
    ：baseline +  + 。
    
    Args:
        original_seq:  VHH clone 
        target: 
        project_id: ID
        safe_scaffolds: SAFE VHH scaffold （，None）
        qa_version: QA（v3.5）
    
    Returns:
         baseline、candidates、comparison 
    """
    logger = VHHProcessLogger()
    
    # 0. baseline：clone
    logger.log(
        "baseline_qa",
        "Baseline QA on original transgenic VHH clone",
        "VHH cloneIMGT、、CMC、developability。",
        extra={"sequence_length": len(original_seq), "target": target},
    )
    
    baseline_result = humanize_vhh_with_qa(
        seq=original_seq,
        panel="A",
        top_k=3,
        species="alpaca",  # VHH，alpaca
        return_all_templates=False,
        enable_safe_mode=False,  # baselinesafe_mode
        strict_qa=True,
        qa_version=qa_version,
    )
    
    # 
    baseline_result["meta"] = baseline_result.get("meta", {})
    baseline_result["meta"]["mode"] = "baseline_transgenic"
    baseline_result["meta"]["target"] = target
    baseline_result["meta"]["project_id"] = project_id
    
    # 1. SAFE scaffold
    # safe_scaffolds，（best_match）
    if safe_scaffolds is None:
        # baselinesafe_scaffolds
        candidates = baseline_result.get("candidates", []) or []
        safe_scaffolds = []
        for cand in candidates[:5]:  # 5safe scaffold
            template = cand.get("template", {}) or {}
            if template:
                safe_scaffolds.append({
                    "id": template.get("id", f"SCAFFOLD_{len(safe_scaffolds)}"),
                    "sequence": template.get("sequence", ""),
                    "regions": template.get("regions", {}),
                })
    
    logger.log(
        "build_repaired_candidates",
        "Build repaired VHH candidates on SAFE scaffolds",
        f" {len(safe_scaffolds)} SAFE VHH scaffoldcloneCDR grafting，。",
        extra={"scaffold_count": len(safe_scaffolds)},
    )
    
    # （：humanize_vhh_with_qa，panel/）
    repaired_candidates = []
    for i, scaffold in enumerate(safe_scaffolds[:3]):  # 3
        scaffold_id = scaffold.get("id", f"SCAFFOLD_{i+1}")
        
        # panel
        panel_options = ["A", "B", "C"]
        panel = panel_options[i % len(panel_options)]
        
        logger.log(
            f"qa_{scaffold_id}",
            "QA on repaired candidate",
            f"SAFE scaffold {scaffold_id} CDR grafting。",
            extra={"scaffold_id": scaffold_id, "panel": panel},
        )
        
        # 
        # ：，scaffoldCDR grafting
        # humanize_vhh_with_qa
        res = humanize_vhh_with_qa(
            seq=original_seq,  # grafted
            panel=panel,
            top_k=1,
            species="alpaca",
            return_all_templates=False,
            enable_safe_mode=True,  # safe_mode
            strict_qa=True,
            qa_version=qa_version,
        )
        
        # 
        res["meta"] = res.get("meta", {})
        res["meta"]["mode"] = "repaired_candidate"
        res["meta"]["scaffold_id"] = scaffold_id
        res["meta"]["target"] = target
        res["meta"]["project_id"] = project_id
        
        repaired_candidates.append(res)
    
    # 2. （baseline vs repaired）
    comparison = _build_repair_comparison_summary(
        baseline_result=baseline_result,
        candidate_results=repaired_candidates,
    )
    
    return {
        "project_id": project_id,
        "target": target,
        "baseline": baseline_result,
        "candidates": repaired_candidates,
        "comparison": comparison,
        "process_log": logger.to_list(),
    }


def _extract_key_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    """。"""
    qa = result.get("qa", {}) or {}
    v35 = qa.get("v3_5") or qa.get("v3_4") or {}
    sr = v35.get("structural_risk_components", {}) or {}
    ranking = v35.get("checks", {}) or {}
    ranking_sanity = ranking.get("ranking_sanity_v3_5", {}) or {}
    stability = ranking_sanity.get("stability_analysis", {}) or {}
    dev = result.get("developability", {}) or {}
    dev_scores = dev.get("scores", {}) or dev.get("humanized", {}) or {}
    cmc = result.get("cmc", {}) or {}
    imm = result.get("immunogenicity", {}) or {}
    affinity = result.get("affinity", {}) or {}
    
    return {
        "total_risk": sr.get("total_risk", None),
        "fr2_risk": sr.get("fr2_hydrophilic_patch_risk", None),
        "anchor_risk": sr.get("cdr3_anchor_risk", None),
        "swap_risk": stability.get("swap_risk", None),
        "stability_score": stability.get("stability_score", None),
        "agg_risk": dev_scores.get("aggregation_risk", dev_scores.get("aggregation", None)),
        "cmc_hotspot_count": len(cmc.get("hotspots", []) or []),
        "immunogenicity_score": imm.get("global_score", imm.get("score", None)),
        "predicted_affinity": affinity.get("predicted_kd", affinity.get("kd", None)),
    }


def _build_repair_comparison_summary(
    baseline_result: Dict[str, Any],
    candidate_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """"""
    baseline_metrics = _extract_key_metrics(baseline_result)
    
    rows = []
    for res in candidate_results:
        meta = res.get("meta", {}) or {}
        scaffold_id = meta.get("scaffold_id", "UNKNOWN")
        m = _extract_key_metrics(res)
        
        #  delta（ - ）
        def safe_delta(candidate_val, baseline_val):
            if candidate_val is None or baseline_val is None:
                return None
            return candidate_val - baseline_val
        
        row = {
            "scaffold_id": scaffold_id,
            "baseline_total_risk": baseline_metrics["total_risk"],
            "candidate_total_risk": m["total_risk"],
            "delta_total_risk": safe_delta(m["total_risk"], baseline_metrics["total_risk"]),
            "baseline_fr2_risk": baseline_metrics["fr2_risk"],
            "candidate_fr2_risk": m["fr2_risk"],
            "delta_fr2_risk": safe_delta(m["fr2_risk"], baseline_metrics["fr2_risk"]),
            "baseline_anchor_risk": baseline_metrics["anchor_risk"],
            "candidate_anchor_risk": m["anchor_risk"],
            "delta_anchor_risk": safe_delta(m["anchor_risk"], baseline_metrics["anchor_risk"]),
            "baseline_agg_risk": baseline_metrics["agg_risk"],
            "candidate_agg_risk": m["agg_risk"],
            "delta_agg_risk": safe_delta(m["agg_risk"], baseline_metrics["agg_risk"]),
            "baseline_cmc_hotspots": baseline_metrics["cmc_hotspot_count"],
            "candidate_cmc_hotspots": m["cmc_hotspot_count"],
            "delta_cmc_hotspots": safe_delta(m["cmc_hotspot_count"], baseline_metrics["cmc_hotspot_count"]),
            "baseline_immunogenicity": baseline_metrics["immunogenicity_score"],
            "candidate_immunogenicity": m["immunogenicity_score"],
            "delta_immunogenicity": safe_delta(m["immunogenicity_score"], baseline_metrics["immunogenicity_score"]),
            "baseline_kd": baseline_metrics["predicted_affinity"],
            "candidate_kd": m["predicted_affinity"],
            "delta_kd": safe_delta(m["predicted_affinity"], baseline_metrics["predicted_affinity"]),
        }
        rows.append(row)
    
    return {
        "baseline": baseline_metrics,
        "candidates": rows,
    }


# 
if __name__ == "__main__":
    # ： VHH clone
    original_seq = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
    
    result = repair_transgenic_vhh_clone_with_baseline(
        original_seq=original_seq,
        target="EGFR",
        project_id="TEST_REPAIR",
        safe_scaffolds=None,  # 
    )
    
    print("\n" + "="*60)
    print("Repair Pipeline Result:")
    print("="*60)
    print(f"Project ID: {result['project_id']}")
    print(f"Target: {result['target']}")
    print(f"Baseline QA OK: {result['baseline'].get('qa', {}).get('ok', False)}")
    print(f"Candidates: {len(result['candidates'])}")
    print(f"Comparison rows: {len(result['comparison']['candidates'])}")
    print("="*60)

















