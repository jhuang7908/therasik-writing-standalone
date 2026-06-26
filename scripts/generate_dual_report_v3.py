"""
VHH  v3.0

 CURSOR_REPORT_ENGINE v3.0 ，：
1. Client Report（）
2. Developer Report（）
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_mutation_tier_classifier import (
    classify_all_mutations,
    generate_three_final_sequences,
    TieredMutation,
)
from core.segmentation.json_validator import (
    validate_json_for_delivery,
    SegmentationProvenanceValidationError,
)


def generate_client_report(
    result: Dict[str, Any],
    output_dir: Path,
    project_id: str = "VHH_Project",
) -> Path:
    """
     Client Report（）
    
    Args:
        result: 
        output_dir: 
        project_id: ID
    
    Returns:
        
    
    Raises:
        SegmentationProvenanceValidationError: JSON
    """
    # JSON：segmentation_provenance
    try:
        is_valid, errors = validate_json_for_delivery(result, strict=True)
        if not is_valid:
            error_msg = "JSON，。\n" + "\n".join(f"  - {e}" for e in errors)
            raise SegmentationProvenanceValidationError(error_msg)
    except SegmentationProvenanceValidationError:
        raise
    except Exception as e:
        # ，（）
        print(f"[WARN] JSON: {e}，...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    #  Client Report 
    template_path = PROJECT_ROOT / "reports" / "templates" / "vhh_client_report_template.md"
    if not template_path.exists():
        # ，
        template = _get_client_report_template()
    else:
        template = template_path.read_text(encoding="utf-8")
    
    # 
    report_data = _build_client_report_data(result, project_id)
    
    # 
    report_content = _fill_template(template, report_data)
    
    # ：
    report_content = _sanitize_client_report(report_content)
    
    # 
    report_path = output_dir / f"{project_id}_Client_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.write_text(report_content, encoding="utf-8")
    
    # ：
    _assert_client_report_sanitized(report_path)
    
    # ：Canonical Proxy 
    _assert_canonical_proxy_section_unique(report_path)
    
    print(f"[INFO] Client Report generated: {report_path}")
    return report_path


def generate_developer_report(
    result: Dict[str, Any],
    output_dir: Path,
    project_id: str = "VHH_Project",
) -> Path:
    """
     Developer Report（）
    
    Args:
        result: 
        output_dir: 
        project_id: ID
    
    Returns:
        
    
    Raises:
        SegmentationProvenanceValidationError: JSON
    """
    # JSON：segmentation_provenance
    try:
        is_valid, errors = validate_json_for_delivery(result, strict=True)
        if not is_valid:
            error_msg = "JSON，。\n" + "\n".join(f"  - {e}" for e in errors)
            raise SegmentationProvenanceValidationError(error_msg)
    except SegmentationProvenanceValidationError:
        raise
    except Exception as e:
        # ，（）
        print(f"[WARN] JSON: {e}，...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    #  Developer Report 
    template_path = PROJECT_ROOT / "reports" / "templates" / "vhh_developer_report_template.md"
    if not template_path.exists():
        # ，
        template = _get_developer_report_template()
    else:
        template = template_path.read_text(encoding="utf-8")
    
    # （）
    report_data = _build_developer_report_data(result, project_id)
    
    # 
    report_content = _fill_template(template, report_data)
    
    # 
    report_path = output_dir / f"{project_id}_Developer_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.write_text(report_content, encoding="utf-8")
    
    print(f"[INFO] Developer Report generated: {report_path}")
    return report_path


def _extract_mutations_from_result(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """ result （）"""
    # 1:  mutations.list
    mutations = result.get("mutations", {})
    if isinstance(mutations, dict):
        mut_list = mutations.get("list", [])
        if mut_list:
            return mut_list
    
    # 2:  best_match （ calculate_mutations ）
    best_match = result.get("best_match") or {}
    if not isinstance(best_match, dict):
        best_match = {}
    input_seq = result.get("input", {}).get("sequence", "")
    humanized_seq = best_match.get("humanized_sequence", "")
    
    if input_seq and humanized_seq:
        try:
            #  calculate_mutations 
            from scripts.generate_egfr_cro_report_cn_enhanced import calculate_mutations, get_region_for_position
            
            mutations_data = calculate_mutations(input_seq, humanized_seq, mode="VHH_FR_ONLY")
            mut_list = mutations_data.get("mutations", [])
            
            # 
            formatted_mutations = []
            for mut in mut_list:
                formatted_mutations.append({
                    "position": mut.get("position", 0),
                    "from_aa": mut.get("from", mut.get("from_aa", "")),
                    "to_aa": mut.get("to", mut.get("to_aa", "")),
                    "from": mut.get("from", mut.get("from_aa", "")),
                    "to": mut.get("to", mut.get("to_aa", "")),
                    "region": mut.get("region", "Unknown"),
                })
            return formatted_mutations
        except Exception as e:
            print(f"[WARN]  calculate_mutations : {e}，")
            # ：
            if len(input_seq) == len(humanized_seq):
                mut_list = []
                for i, (orig_aa, hum_aa) in enumerate(zip(input_seq, humanized_seq), 1):
                    if orig_aa != hum_aa:
                        #  get_region_for_position 
                        try:
                            from scripts.generate_egfr_cro_report_cn_enhanced import get_region_for_position
                            region = get_region_for_position(i)
                        except:
                            region = "FR1"  # 
                        
                        mut_list.append({
                            "position": i,
                            "from_aa": orig_aa,
                            "to_aa": hum_aa,
                            "from": orig_aa,
                            "to": hum_aa,
                            "region": region,
                        })
                return mut_list
    
    return []


def _extract_sequence_regions(result: Dict[str, Any]) -> Dict[str, str]:
    """ result （）"""
    # 1:  sequence_analysis.original_regions
    seq_analysis = result.get("sequence_analysis", {})
    if seq_analysis:
        orig_regions = seq_analysis.get("original_regions", {})
        if orig_regions:
            return orig_regions
    
    # 2:  extract_sequence_regions 
    input_seq = result.get("input", {}).get("sequence", "")
    if input_seq:
        try:
            from scripts.generate_egfr_cro_report_cn_enhanced import extract_sequence_regions
            regions = extract_sequence_regions(input_seq)
            if regions:
                return regions
        except Exception as e:
            print(f"[WARN]  extract_sequence_regions : {e}，")
        
        # 3: （ IMGT ）
        #  IMGT （）
        if len(input_seq) >= 117:  #  VHH 
            return {
                "FR1": input_seq[0:26] if len(input_seq) >= 26 else input_seq[:25],
                "CDR1": input_seq[26:38] if len(input_seq) >= 38 else "",
                "FR2": input_seq[38:55] if len(input_seq) >= 55 else "",
                "CDR2": input_seq[55:65] if len(input_seq) >= 65 else "",
                "FR3": input_seq[65:104] if len(input_seq) >= 104 else "",
                "CDR3": input_seq[104:117] if len(input_seq) >= 117 else "",
                "FR4": input_seq[117:] if len(input_seq) > 117 else "",
            }
        else:
            # ， CDR 
            cdrs = result.get("cdrs", {})
            if cdrs:
                #  CDR 
                cdr1 = cdrs.get("CDR1", "")
                cdr2 = cdrs.get("CDR2", "")
                cdr3 = cdrs.get("CDR3", "")
                
                # （ IMGT ）
                return {
                    "FR1": "",
                    "CDR1": cdr1,
                    "FR2": "",
                    "CDR2": cdr2,
                    "FR3": "",
                    "CDR3": cdr3,
                    "FR4": "",
                }
    
    return {}


def _build_client_report_data(result: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    """ Client Report （）"""
    input_data = result.get("input", {})
    sequence = (
        input_data.get("sequence", "") or
        result.get("input_sequence", "") or
        result.get("sequence", "")
    )
    
    if not sequence:
        raise ValueError(" result ")
    
    # 
    mutations = _extract_mutations_from_result(result)
    
    # 
    regions = _extract_sequence_regions(result)
    segmentation = {"regions": regions}
    
    # 
    cmc_risks = result.get("cmc", {}).get("hotspots", []) or []
    immunogenicity_risks = result.get("immunogenicity", {}).get("high_risk_epitopes", []) or []
    
    # （，）
    if mutations:
        try:
            tiered_mutations = classify_all_mutations(
                mutations, sequence, segmentation, cmc_risks, immunogenicity_risks
            )
        except Exception as e:
            print(f"[WARN] : {e}，")
            tiered_mutations = {0: [], 1: [], 2: [], 3: []}
    else:
        tiered_mutations = {0: [], 1: [], 2: [], 3: []}
    
    # 
    try:
        three_sequences = generate_three_final_sequences(sequence, tiered_mutations)
    except Exception as e:
        print(f"[WARN] : {e}，")
        three_sequences = {
            "seq1": {"sequence": sequence, "mutations": [], "description": "Base Humanized（）"},
            "seq2": {"sequence": sequence, "mutations": [], "description": "Safety-Optimized（）"},
            "seq3": {"sequence": sequence, "mutations": [], "description": "Affinity-Optimized（）"},
        }
    
    # 
    #  target（）
    target = (
        result.get("target") or
        result.get("input", {}).get("target") or
        "Unknown"
    )
    
    data = {
        "project_id": project_id,
        "target": target,
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "engine_version": "VHH Humanization Engine v2.2.0",
        "qa_version": result.get("qa", {}).get("version", "v3.5"),
        
        # 
        "seq_length": len(sequence),
        "input_sequence": sequence,
        "pi": _calculate_pi(sequence),
        "gravy": _calculate_gravy(sequence),
        "cys_count": sequence.count("C"),
        
        # IMGT 
        "imgt_table_rows": _build_imgt_table(result),
        
        # 
        "seq1_sequence": three_sequences["seq1"]["sequence"],
        "seq1_description": three_sequences["seq1"]["description"],
        "seq1_mutations": _format_mutations_table(three_sequences["seq1"]["mutations"]),
        
        "seq2_sequence": three_sequences["seq2"]["sequence"],
        "seq2_description": three_sequences["seq2"]["description"],
        "seq2_mutations": _format_mutations_table(three_sequences["seq2"]["mutations"]),
        
        "seq3_sequence": three_sequences["seq3"]["sequence"],
        "seq3_description": three_sequences["seq3"]["description"],
        "seq3_mutations": _format_mutations_table(three_sequences["seq3"]["mutations"]),
        
        # 
        "tier0_mutations": _format_tiered_mutations(tiered_mutations.get(0, [])),
        "tier1_mutations": _format_tiered_mutations(tiered_mutations.get(1, [])),
        "tier2_mutations": _format_tiered_mutations(tiered_mutations.get(2, [])),
        "tier3_mutations": _format_tiered_mutations(tiered_mutations.get(3, [])),
        
        # （ 8 ）
        "optional_mutations_menu": _format_optional_mutations_menu(
            tiered_mutations.get(2, []) + tiered_mutations.get(3, [])
        ),
        
        # 
        "germline_section": _build_germline_section(result),
        "hallmark_section": _build_hallmark_section(result),
        "cmc_section": _build_cmc_section(result),
        "immunogenicity_section": _build_immunogenicity_section(result),
        "developability_section": _build_developability_section(result),
        "qa_summary": _build_qa_summary(result),
        "final_recommendation": _build_final_recommendation(result, three_sequences),
        "glossary": _build_glossary(),
        
        # （）
        "structural_risk_level": _classify_risk_level_from_qa(result),
        "structural_risk_value": _get_structural_risk_value(result),
        "cmc_risk_level": _classify_cmc_risk_level(result),
        "cmc_risk_count": len(cmc_risks),
        "immunogenicity_risk_level": _classify_immuno_risk_level(result),
        "immunogenicity_risk_value": _get_immuno_risk_value(result),
        "developability_score": _get_developability_score(result),
        "developability_level": _classify_developability_level(result),
        
        # Germline 
        "fr1_identity": _get_fr_identity(result, "fr1"),
        "fr2_identity": _get_fr_identity(result, "fr2"),
        "fr3_identity": _get_fr_identity(result, "fr3"),
        "fr4_identity": _get_fr_identity(result, "fr4"),
        "template_selection_reasoning": _get_template_selection_reasoning(result),
        
        # Vernier 
        "vernier_analysis_section": _build_vernier_analysis_section(result),
        
        # Canonical Proxy 
        "canonical_proxy_section": _build_canonical_proxy_section(result),
    }
    
    return data


def _build_developer_report_data(result: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    """ Developer Report （）"""
    #  Client Report 
    client_data = _build_client_report_data(result, project_id)
    
    # 
    best_match = result.get("best_match") or {}
    if not isinstance(best_match, dict):
        best_match = {}
    
    developer_data = {
        **client_data,
        # 
        "imgt_residue_vector": result.get("segmentation", {}).get("imgt_numbering", {}),
        "germline_similarity_matrix": best_match.get("similarity_matrix", {}),
        "vernier_zone_risk_matrix": result.get("qa", {}).get("v3_5", {}).get("vernier_risk", {}),
        "hallmark_scoring": result.get("qa", {}).get("v3_5", {}).get("hallmark_score", {}),
        "cmc_full_scan": result.get("cmc", {}).get("full_scan", []),
        "immunogenicity_full_matrix": result.get("immunogenicity", {}).get("mhc_matrix", {}),
        "developability_full_scores": result.get("developability", {}).get("full_scores", {}),
        "affinity_optimization_all_candidates": result.get("affinity", {}).get("candidates", []),
        "tier_classification_logs": result.get("tier_classification", {}).get("logs", []),
        "mutation_conflict_matrix": result.get("mutations", {}).get("conflict_matrix", {}),
        "stability_raw_scores": result.get("developability", {}).get("stability_raw", {}),
        "aggregation_raw_scores": result.get("developability", {}).get("aggregation_raw", {}),
        "process_logs": result.get("process_log", []),
        "algorithm_version": "VHH Humanization Engine v2.2.0",
        "algorithm_parameters": result.get("parameters", {}),
        "dependencies": {
            "IEDB": "v2.24",
            "TANGO": "v1.0",
            "IgFold": "v1.0",
            "ANARCI": "v1.3",
        },
    }
    
    return developer_data


def _fill_template(template: str, data: Dict[str, Any]) -> str:
    """"""
    content = template
    for key, value in data.items():
        placeholder = f"{{{{{key}}}}}"
        if placeholder in content:
            if isinstance(value, (list, dict)):
                # 
                value_str = json.dumps(value, indent=2, ensure_ascii=False)
            else:
                value_str = str(value)
            content = content.replace(placeholder, value_str)
    return content


# （）

def _calculate_pi(sequence: str) -> float:
    """"""
    try:
        from Bio.SeqUtils import IsoelectricPoint
        from Bio.SeqUtils.ProtParam import ProteinAnalysis
        from Bio.Seq import Seq
        
        seq_obj = Seq(sequence)
        prot_analysis = ProteinAnalysis(str(seq_obj))
        pi = prot_analysis.isoelectric_point()
        return round(pi, 2)
    except ImportError:
        #  BioPython，
        pos_charged = sequence.count("K") + sequence.count("R") + sequence.count("H")
        neg_charged = sequence.count("D") + sequence.count("E")
        # 
        if pos_charged > neg_charged:
            return round(8.0 + (pos_charged - neg_charged) * 0.1, 2)
        else:
            return round(6.0 - (neg_charged - pos_charged) * 0.1, 2)
    except Exception as e:
        print(f"[WARN] pI : {e}，")
        return 8.5


def _calculate_gravy(sequence: str) -> float:
    """ GRAVY（Grand Average of Hydropathicity）"""
    try:
        from Bio.SeqUtils.ProtParam import ProteinAnalysis
        from Bio.Seq import Seq
        
        seq_obj = Seq(sequence)
        prot_analysis = ProteinAnalysis(str(seq_obj))
        gravy = prot_analysis.gravy()
        return round(gravy, 3)
    except ImportError:
        #  BioPython，
        # Kyte-Doolittle （）
        hydropathy = {
            "I": 4.5, "V": 4.2, "L": 3.8, "F": 2.8, "C": 2.5, "M": 1.9,
            "A": 1.8, "G": -0.4, "T": -0.7, "S": -0.8, "W": -0.9, "Y": -1.3,
            "P": -1.6, "H": -3.2, "E": -3.5, "Q": -3.5, "D": -3.5, "N": -3.5,
            "K": -3.9, "R": -4.5,
        }
        total = sum(hydropathy.get(aa, 0.0) for aa in sequence)
        return round(total / len(sequence) if sequence else 0.0, 3)
    except Exception as e:
        print(f"[WARN] GRAVY : {e}，")
        return -0.3


def _build_imgt_table(result: Dict[str, Any]) -> str:
    """ IMGT """
    regions = _extract_sequence_regions(result)
    rows = []
    for region_name in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]:
        seq = regions.get(region_name, "")
        if seq:
            rows.append(f"| {region_name} | {seq} | {len(seq)} |")
    
    if not rows:
        # ， CDR 
        cdrs = result.get("cdrs", {})
        if cdrs:
            rows.append(f"| CDR1 | {cdrs.get('CDR1', '')} | {len(cdrs.get('CDR1', ''))} |")
            rows.append(f"| CDR2 | {cdrs.get('CDR2', '')} | {len(cdrs.get('CDR2', ''))} |")
            rows.append(f"| CDR3 | {cdrs.get('CDR3', '')} | {len(cdrs.get('CDR3', ''))} |")
    
    return "\n".join(rows) if rows else "| - | - | - |"


def _format_mutations_table(mutations: List[TieredMutation]) -> str:
    """"""
    if not mutations:
        return ""
    rows = []
    for mut in mutations:
        rows.append(
            f"| {mut.position} | {mut.from_aa}→{mut.to_aa} | {mut.region} | "
            f"{mut.risk_level} | {mut.rationale} |"
        )
    header = "|  |  |  |  |  |\n|------|------|------|----------|--------|"
    return header + "\n" + "\n".join(rows)


def _format_tiered_mutations(mutations: List[TieredMutation]) -> str:
    """"""
    if not mutations:
        return ""
    rows = []
    for mut in mutations:
        warning_text = f" {mut.warning}" if mut.warning else ""
        rows.append(
            f"| {mut.position} | {mut.from_aa}→{mut.to_aa} | {mut.region} | "
            f"{mut.risk_level} | {mut.rationale}{warning_text} |"
        )
    header = "|  |  |  |  |  |\n|------|------|------|----------|--------|"
    return header + "\n" + "\n".join(rows)


def _format_optional_mutations_menu(mutations: List[TieredMutation], max_count: int = 8) -> str:
    """（ 8 ）"""
    if not mutations:
        return ""
    selected = mutations[:max_count]
    rows = []
    for mut in selected:
        rows.append(
            f"| {mut.position} | {mut.from_aa}→{mut.to_aa} | {mut.region} | "
            f"{mut.tier} | {mut.risk_level} | {mut.rationale} |"
        )
    header = "|  |  |  | Tier |  |  |\n|------|------|------|------|----------|--------|"
    return header + "\n" + "\n".join(rows)


def _build_germline_section(result: Dict[str, Any]) -> str:
    """ Germline """
    best_match = result.get("best_match") or {}
    if not isinstance(best_match, dict):
        best_match = {}
    template = best_match.get("template", {}) or {}
    
    template_id = template.get("template_id") or template.get("id") or best_match.get("template_id", "N/A")
    source_scaffold = template.get("source_scaffold") or best_match.get("alpaca_scaffold", "N/A")
    
    alignment_scores = best_match.get("alignment_scores", {}) or {}
    fr1_identity = alignment_scores.get("fr1_identity", 0.0) * 100
    fr2_identity = alignment_scores.get("fr2_identity", 0.0) * 100
    fr3_identity = alignment_scores.get("fr3_identity", 0.0) * 100
    framework_identity = alignment_scores.get("framework_identity", 0.0) * 100
    
    section = f"""**：** {template_id}
** Scaffold：** {source_scaffold}

**：**
- FR1 Identity: {fr1_identity:.1f}%
- FR2 Identity: {fr2_identity:.1f}%
- FR3 Identity: {fr3_identity:.1f}%
-  Identity: {framework_identity:.1f}%

**：**  Identity ({framework_identity:.1f}%) 。"""
    
    return section


def _build_hallmark_section(result: Dict[str, Any]) -> str:
    """ Hallmark """
    best_match = result.get("best_match") or {}
    if not isinstance(best_match, dict):
        best_match = {}
    alignment_scores = best_match.get("alignment_scores", {}) or {}
    hallmark_score = alignment_scores.get("vhh_hallmark_score", 0.0)
    
    cdr_compatibility = best_match.get("cdr_compatibility", {}) or {}
    key_positions = cdr_compatibility.get("key_position_matches", {}) or {}
    
    fr1_26 = "✅" if key_positions.get("fr1_26", False) else "❌"
    fr2_55 = "✅" if key_positions.get("fr2_55", False) else "❌"
    fr3_104 = "✅" if key_positions.get("fr3_104", False) else "❌"
    
    section = f"""**VHH Hallmark Score：** {hallmark_score:.2f} {'✅ ' if hallmark_score >= 0.9 else '⚠️ ' if hallmark_score >= 0.7 else '❌ '}

**：**
- FR1_26: {fr1_26}
- FR2_55: {fr2_55}
- FR3_104: {fr3_104}

**：** {'VHH Hallmark ' if hallmark_score >= 0.9 else 'VHH Hallmark ，'}"""
    
    return section


def _build_cmc_section(result: Dict[str, Any]) -> str:
    """ CMC """
    cmc = result.get("cmc", {}) or {}
    hotspots = cmc.get("hotspots", []) or []
    
    if not hotspots:
        return "**CMC ：** 0 \n\n**：**  CMC 。"
    
    # 
    high_risk = [h for h in hotspots if h.get("risk_level", "").lower() == "high"]
    medium_risk = [h for h in hotspots if h.get("risk_level", "").lower() == "medium"]
    low_risk = [h for h in hotspots if h.get("risk_level", "").lower() == "low"]
    
    section = f"""**CMC ：** {len(hotspots)} 
- ：{len(high_risk)} 
- ：{len(medium_risk)} 
- ：{len(low_risk)} 

**：**
"""
    if high_risk:
        for h in high_risk[:5]:  # 5
            pos = h.get("position", "N/A")
            risk_type = h.get("type", "N/A")
            section += f"-  {pos}: {risk_type}\n"
    else:
        section += "- \n"
    
    return section


def _build_immunogenicity_section(result: Dict[str, Any]) -> str:
    """"""
    immuno = result.get("immunogenicity", {}) or {}
    best_match = result.get("best_match") or {}
    if not isinstance(best_match, dict):
        best_match = {}
    match_immuno = best_match.get("immunogenicity", {}) or {}
    
    global_score = immuno.get("global_score") or match_immuno.get("fr_immuno_risk", "N/A")
    hotspot_count = immuno.get("high_risk_epitopes", []) or []
    if isinstance(hotspot_count, list):
        hotspot_count = len(hotspot_count)
    
    fr_risk = match_immuno.get("fr_immuno_risk", "unknown")
    
    section = f"""**：** {global_score}
**FR ：** {fr_risk}
**：** {hotspot_count} 

**：** {'，' if fr_risk == 'low' else '，' if fr_risk == 'medium' else '，'}"""
    
    return section


def _build_developability_section(result: Dict[str, Any]) -> str:
    """ Developability """
    dev = result.get("developability", {}) or {}
    best_match = result.get("best_match") or {}
    if not isinstance(best_match, dict):
        best_match = {}
    match_dev = best_match.get("developability", {}) or {}
    
    #  developability score
    dev_score = (
        dev.get("scores", {}).get("overall") or
        dev.get("score") or
        match_dev.get("score") or
        best_match.get("alignment_scores", {}).get("developability_score") or
        "N/A"
    )
    
    dev_grade = match_dev.get("grade", "N/A")
    dev_risk = match_dev.get("risk", "unknown")
    
    if isinstance(dev_score, (int, float)):
        score_text = f"{dev_score:.2f}"
        level_text = "" if dev_score >= 0.8 else "" if dev_score >= 0.6 else "" if dev_score >= 0.4 else ""
    else:
        score_text = str(dev_score)
        level_text = "N/A"
    
    section = f"""**Developability ：** {score_text} ({level_text})
**Grade：** {dev_grade}
**Risk Level：** {dev_risk}

**：** {'Developability ，' if isinstance(dev_score, (int, float)) and dev_score >= 0.6 else 'Developability ，' if isinstance(dev_score, (int, float)) else 'Developability '}"""
    
    return section


def _build_qa_summary(result: Dict[str, Any]) -> str:
    """ QA """
    qa = result.get("qa", {}) or {}
    qa_v35 = qa.get("v3_5", {}) or qa.get("v3_4", {}) or {}
    
    ok = qa_v35.get("ok", False)
    errors = qa_v35.get("errors", []) or []
    warnings = qa_v35.get("warnings", []) or []
    
    structural_risk = qa_v35.get("structural_risk_components", {}) or {}
    total_risk = structural_risk.get("total_risk", 0.0)
    
    section = f"""**QA ：** {'✅ ' if ok else '❌ '}
**：** {total_risk:.3f} ({'' if total_risk < 0.3 else '' if total_risk < 0.6 else ''})
**：** {len(errors)} 
**：** {len(warnings)} 

"""
    
    if errors:
        section += "**：**\n"
        for i, err in enumerate(errors[:5], 1):  # 5
            if isinstance(err, dict):
                section += f"{i}. {err.get('message', str(err))}\n"
            else:
                section += f"{i}. {err}\n"
        section += "\n"
    
    if warnings:
        section += "**：**\n"
        for i, warn in enumerate(warnings[:5], 1):  # 5
            if isinstance(warn, dict):
                section += f"{i}. {warn.get('message', str(warn))}\n"
            else:
                section += f"{i}. {warn}\n"
    
    return section


def _build_final_recommendation(result: Dict[str, Any], three_sequences: Dict[str, Any]) -> str:
    """"""
    return (
        "**：Seq2 (Safety-Optimized)**\n\n"
        "：\n"
        "- 、、CMC \n"
        "- （Lead Optimization）\n"
        "-  Seq1， Seq2/Seq3"
    )


def _build_glossary() -> str:
    """"""
    return """
- **FR (Framework Region)**: ，，
- **CDR (Complementarity Determining Region)**: ，，
- **Vernier Zone**: Vernier ， CDR ，
- **Hallmark Residues**: VHH ， VHH ， FR2  37/44/45/47 
- **CMC Liabilities**: ，（N-X-S/T）、（D-G）、（M/W）
- **MHC-II Epitope**: MHC-II ， T ，
- **Aggregation Risk**: ，，
- **Affinity Optimization**: ，（、）
- **Tier **: 
  - Tier 0: （CDR 、VHH hallmark、Vernier ）
  - Tier 1: （ FR mismatch、 CMC、）
  - Tier 2: （/CMC/， paratope）
  - Tier 3: /（CDR aromatic enrichment、apex rigidification，）
"""


# 

def _classify_risk_level_from_qa(result: Dict[str, Any]) -> str:
    """ QA """
    qa = result.get("qa", {}) or {}
    qa_v35 = qa.get("v3_5", {}) or qa.get("v3_4", {}) or {}
    structural_risk = qa_v35.get("structural_risk_components", {}) or {}
    total_risk = structural_risk.get("total_risk", 0.0)
    
    if total_risk < 0.3:
        return ""
    elif total_risk < 0.6:
        return ""
    else:
        return ""


def _get_structural_risk_value(result: Dict[str, Any]) -> str:
    """"""
    qa = result.get("qa", {}) or {}
    qa_v35 = qa.get("v3_5", {}) or qa.get("v3_4", {}) or {}
    structural_risk = qa_v35.get("structural_risk_components", {}) or {}
    total_risk = structural_risk.get("total_risk", 0.0)
    return f"{total_risk:.3f}"


def _classify_cmc_risk_level(result: Dict[str, Any]) -> str:
    """ CMC """
    cmc = result.get("cmc", {}) or {}
    hotspots = cmc.get("hotspots", []) or []
    high_risk_count = sum(1 for h in hotspots if h.get("risk_level", "").lower() == "high")
    
    if high_risk_count == 0:
        return ""
    elif high_risk_count <= 2:
        return ""
    else:
        return ""


def _classify_immuno_risk_level(result: Dict[str, Any]) -> str:
    """"""
    best_match = result.get("best_match") or {}
    if not isinstance(best_match, dict):
        best_match = {}
    match_immuno = best_match.get("immunogenicity", {}) or {}
    fr_risk = match_immuno.get("fr_immuno_risk", "unknown")
    
    if fr_risk == "low":
        return ""
    elif fr_risk == "medium":
        return ""
    elif fr_risk == "high":
        return ""
    else:
        return ""


def _get_immuno_risk_value(result: Dict[str, Any]) -> str:
    """"""
    immuno = result.get("immunogenicity", {}) or {}
    global_score = immuno.get("global_score")
    if global_score is not None:
        return f"{global_score:.3f}"
    return "N/A"


def _get_developability_score(result: Dict[str, Any]) -> str:
    """ Developability """
    dev = result.get("developability", {}) or {}
    best_match = result.get("best_match") or {}
    if not isinstance(best_match, dict):
        best_match = {}
    match_dev = best_match.get("developability", {}) or {}
    
    dev_score = (
        dev.get("scores", {}).get("overall") or
        dev.get("score") or
        match_dev.get("score") or
        best_match.get("alignment_scores", {}).get("developability_score")
    )
    
    if dev_score is not None:
        return f"{dev_score:.2f}"
    return "N/A"


def _classify_developability_level(result: Dict[str, Any]) -> str:
    """ Developability """
    dev_score = _get_developability_score(result)
    if dev_score == "N/A":
        return ""
    
    try:
        score = float(dev_score)
        if score >= 0.8:
            return ""
        elif score >= 0.6:
            return ""
        elif score >= 0.4:
            return ""
        else:
            return ""
    except ValueError:
        return ""


def _get_fr_identity(result: Dict[str, Any], fr_name: str) -> str:
    """ FR Identity"""
    best_match = result.get("best_match") or {}
    if not isinstance(best_match, dict):
        best_match = {}
    alignment_scores = best_match.get("alignment_scores", {}) or {}
    fr_key = f"{fr_name}_identity"
    identity = alignment_scores.get(fr_key, 0.0)
    return f"{identity * 100:.1f}%"


def _get_template_selection_reasoning(result: Dict[str, Any]) -> str:
    """"""
    best_match = result.get("best_match") or {}
    if not isinstance(best_match, dict):
        best_match = {}
    alignment_scores = best_match.get("alignment_scores", {}) or {}
    framework_identity = alignment_scores.get("framework_identity", 0.0) * 100
    combined_score = alignment_scores.get("combined_score", 0.0)
    
    return f" Identity ({framework_identity:.1f}%)  ({combined_score:.3f}) 。"


def _build_canonical_proxy_section(result: Dict[str, Any]) -> str:
    """
     Canonical Proxy （）
    """
    from core.report_blocks.canonical_proxy_background_customer import (
        render_canonical_proxy_background_customer_block,
        get_canonical_proxy_data_for_client_report,
    )
    
    try:
        canonical_proxy_data = get_canonical_proxy_data_for_client_report(result)
        if canonical_proxy_data is None:
            #  console，
            print("[WARN]  canonical proxy ， N/A")
    except Exception as e:
        #  console，
        print(f"[WARN]  canonical proxy : {e}")
        canonical_proxy_data = None
    
    return render_canonical_proxy_background_customer_block(canonical_proxy_data)


def _build_vernier_analysis_section(result: Dict[str, Any]) -> str:
    """ Vernier Zone """
    best_match = result.get("best_match") or {}
    if not isinstance(best_match, dict):
        best_match = {}
    alignment_scores = best_match.get("alignment_scores", {}) or {}
    fr2_hydrophobicity_mismatch = alignment_scores.get("fr2_hydrophobicity_mismatch", 0.0)
    
    section = f"""**FR2 ：** {fr2_hydrophobicity_mismatch:.3f}

**：** {'FR2 ' if fr2_hydrophobicity_mismatch < 0.2 else 'FR2 ，' if fr2_hydrophobicity_mismatch < 0.3 else 'FR2 ，'}

**Vernier ：**  Vernier （V37, V39, V45, V47, V91）。"""
    
    return section


def _get_client_report_template() -> str:
    """ Client Report """
    return """# VHH （Client Report v3.0）

**：** {{{{project_id}}}}  
**：** {{{{target}}}}  
**：** {{{{analysis_date}}}}  

---

## 0. 

**：**
- ：{{{{seq_length}}}} aa
-  (pI)：{{{{pi}}}}
- GRAVY：{{{{gravy}}}}

**：**
- ：
- CMC ：-
- ：

---

## 1.  QC

```text
{{{{input_sequence}}}}
```

---

## 2. IMGT 

|  |  |  |
|------|------|------|
{{{{imgt_table_rows}}}}

---

{{{{germline_section}}}}

---

{{{{canonical_proxy_section}}}}

---

## 9. （Tier 0–3）

### Tier 0（）
{{{{tier0_mutations}}}}

### Tier 1（）
{{{{tier1_mutations}}}}

### Tier 2（）
{{{{tier2_mutations}}}}

### Tier 3（/）
{{{{tier3_mutations}}}}

---

## 10. 

### Seq1: Base Humanized
{{{{seq1_description}}}}

**：**
```text
{{{{seq1_sequence}}}}
```

**：**
{{{{seq1_mutations}}}}

---

### Seq2: Safety-Optimized
{{{{seq2_description}}}}

**：**
```text
{{{{seq2_sequence}}}}
```

**：**
{{{{seq2_mutations}}}}

---

### Seq3: Affinity-Optimized
{{{{seq3_description}}}}

**：**
```text
{{{{seq3_sequence}}}}
```

**：**
{{{{seq3_mutations}}}}

---

## 11. 

{{{{optional_mutations_menu}}}}

---

## 12. 

{{{{final_recommendation}}}}

---

## 13.  Glossary

{{{{glossary}}}}
"""


def _sanitize_client_report(report_content: str) -> str:
    """
    ：
    
    ：
    - ：scripts/, core/, projects/, .py, .md, , 
    - ：, , 
    - ：, ,  X 
    """
    lines = report_content.split('\n')
    sanitized_lines = []
    
    # 
    forbidden_keywords = [
        'scripts/',
        'core/',
        'projects/',
        '.py',
        '.md',
        '',
        '',
        '',
        '',
        '',
        '',
        ' ',
        '',
        'generate_',
        '_build_',
        '_get_',
        '_format_',
        '_calculate_',
        '_classify_',
        '_extract_',
        'PROJECT_ROOT',
        'template_path',
        'report_path',
        'output_dir',
    ]
    
    for line in lines:
        # 
        line_lower = line.lower()
        contains_forbidden = any(keyword.lower() in line_lower for keyword in forbidden_keywords)
        
        if not contains_forbidden:
            sanitized_lines.append(line)
        else:
            # ，（）
            continue
    
    return '\n'.join(sanitized_lines)


def _assert_canonical_proxy_section_unique(report_path: Path) -> None:
    """
    ： Canonical Proxy 
    
    Raises:
        ValueError:  Canonical Proxy 
    """
    report_content = report_path.read_text(encoding="utf-8")
    
    #  Canonical Proxy 
    import re
    matches = re.findall(r'##\s+CDR\s+Canonical\s+Proxy', report_content, re.IGNORECASE)
    
    if len(matches) > 1:
        error_msg = (
            f" Canonical Proxy （{len(matches)} ），。\n"
            f": {report_path}\n"
            f"， {{canonical_proxy_section}} 。"
        )
        raise ValueError(error_msg)


def _assert_client_report_sanitized(report_path: Path) -> None:
    """
    ：
    
    Raises:
        ValueError: 
    """
    import re
    
    # 
    report_content = report_path.read_text(encoding="utf-8")
    report_content_lower = report_content.lower()
    
    # （）
    forbidden_patterns = [
        r'scripts/',
        r'core/',
        r'projects/',
        r'\.py\b',
        r'\.md\b',
        r'',
        r'',
        r'',
        r'',
        r'',
        r'\s+\d+\s+',
        r'generate_',
        r'_build_',
        r'_get_',
        r'_format_',
        r'_calculate_',
        r'_classify_',
        r'_extract_',
        r'PROJECT_ROOT',
        r'template_path',
        r'report_path',
        r'output_dir',
    ]
    
    violations = []
    for pattern in forbidden_patterns:
        matches = re.findall(pattern, report_content_lower, re.IGNORECASE)
        if matches:
            violations.append(f": {pattern} ( {len(matches)} )")
    
    if violations:
        error_msg = (
            f"，。\n"
            f": {report_path}\n"
            f":\n" + "\n".join(f"  - {v}" for v in violations)
        )
        raise ValueError(error_msg)


def _get_developer_report_template() -> str:
    """ Developer Report """
    return """# VHH （Developer Report v3.0）

**：** {{{{project_id}}}}  
**：** {{{{target}}}}  
**：** {{{{analysis_date}}}}  

---

## Client Report 

（ Client Report ）

---

## 

### IMGT Residue Vector
```json
{{{{imgt_residue_vector}}}}
```

### Germline Similarity Matrix
```json
{{{{germline_similarity_matrix}}}}
```

### CMC 
```json
{{{{cmc_full_scan}}}}
```

### 
```json
{{{{immunogenicity_full_matrix}}}}
```

### 
```json
{{{{affinity_optimization_all_candidates}}}}
```

---

## 

**：** {{{{algorithm_version}}}}  
**：** {{{{algorithm_parameters}}}}  
**：** {{{{dependencies}}}}

---

## 

{{{{process_logs}}}}
"""


def main():
    """"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate dual reports (Client + Developer)")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to result.json")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output directory")
    parser.add_argument("--project-id", "-p", type=str, default="VHH_Project", help="Project ID")
    parser.add_argument("--client-only", action="store_true", help="Generate Client Report only")
    parser.add_argument("--developer-only", action="store_true", help="Generate Developer Report only")
    
    args = parser.parse_args()
    
    # 
    with open(args.input, "r", encoding="utf-8") as f:
        result = json.load(f)
    
    # 
    if not args.developer_only:
        generate_client_report(result, args.output, args.project_id)
    
    if not args.client_only:
        generate_developer_report(result, args.output, args.project_id)
    
    print("[INFO] Report generation completed.")


if __name__ == "__main__":
    main()

