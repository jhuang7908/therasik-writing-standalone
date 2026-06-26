#!/usr/bin/env python3
"""
Pilot Benchmark v1: 7D12 VHH + 6JBT VH/VL 
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import sys

# 
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# 
try:
    from core.numbering.anarcii_adapter import number_sequence, get_engine_info, HAS_ANARCII
except ImportError:
    HAS_ANARCII = False
    print("⚠️  ANARCII，fallback")

# 
try:
    from core.explain.template_selection_explainer import (
        explain_template_selection,
        explain_template_selection_zh
    )
    HAS_EXPLAINER = True
except ImportError:
    HAS_EXPLAINER = False
    print("⚠️  ")

# 
try:
    from core.explain.decision_summary_builder import build_decision_summary
    HAS_DECISION_SUMMARY = True
except ImportError:
    HAS_DECISION_SUMMARY = False
    print("⚠️  ")

# ID
try:
    from core.utils.template_id_normalize import normalize_template_id_display
    HAS_TEMPLATE_ID_NORMALIZE = True
except ImportError:
    HAS_TEMPLATE_ID_NORMALIZE = False
    print("⚠️  ID")
    # fallback
    def normalize_template_id_display(template_id):
        return str(template_id) if template_id else ""


# IMGT
IMGT_BOUNDARIES = {
    "FR1": (1, 26),
    "CDR1": (27, 38),
    "FR2": (39, 55),
    "CDR2": (56, 65),
    "FR3": (66, 104),
    "CDR3": (105, 117),
    "FR4": (118, 128),
}


def read_fasta(fasta_path: Path) -> Tuple[str, str]:
    """FASTA，(header, sequence)"""
    if not fasta_path.exists():
        raise FileNotFoundError(f"FASTA: {fasta_path}")
    
    with open(fasta_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    header = ""
    sequence = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('>'):
            header = line[1:]
        else:
            sequence += line.upper()
    
    if not sequence:
        raise ValueError(f"FASTA: {fasta_path}")
    
    return header, sequence


def number_and_segment(sequence: str, chain_type: str = "H") -> Dict[str, Any]:
    """anarcii"""
    result = {
        "success": False,
        "error": None,
        "numbering": {},
        "regions": {},
        "engine_info": {}
    }
    
    if not HAS_ANARCII:
        result["error"] = "ANARCII"
        return result
    
    try:
        # 
        result["engine_info"] = get_engine_info()
        
        # IMGT
        pos_to_aa, residue_table = number_sequence(sequence, scheme="imgt")
        result["numbering"] = pos_to_aa
        
        # IMGT
        regions = {
            "FR1": [],
            "CDR1": [],
            "FR2": [],
            "CDR2": [],
            "FR3": [],
            "CDR3": [],
            "FR4": []
        }
        
        for pos_str, aa in pos_to_aa.items():
            if not pos_str or pos_str == "-":
                continue
            try:
                pos = int(pos_str)
            except (ValueError, TypeError):
                # （37A）
                try:
                    pos = int(pos_str.rstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
                except:
                    continue
            
            # 
            if 1 <= pos <= 26:
                regions["FR1"].append(aa)
            elif 27 <= pos <= 38:
                regions["CDR1"].append(aa)
            elif 39 <= pos <= 55:
                regions["FR2"].append(aa)
            elif 56 <= pos <= 65:
                regions["CDR2"].append(aa)
            elif 66 <= pos <= 104:
                regions["FR3"].append(aa)
            elif 105 <= pos <= 117:
                regions["CDR3"].append(aa)
            elif 118 <= pos <= 128:
                regions["FR4"].append(aa)
        
        # 
        result["regions"] = {k: "".join(v) for k, v in regions.items()}
        result["success"] = True
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def calculate_identity(seq1: str, seq2: str) -> float:
    """identity"""
    if not seq1 or not seq2:
        return 0.0
    min_len = min(len(seq1), len(seq2))
    if min_len == 0:
        return 0.0
    matches = sum(1 for i in range(min_len) if seq1[i] == seq2[i])
    return matches / min_len


def load_imgt_aa_json(lib_path: Path) -> List[Dict[str, Any]]:
    """IMGT amino_acid JSON，"""
    records = []
    missing_sequence_count = 0
    
    if not lib_path.exists():
        return records
    
    try:
        with open(lib_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # list
        if isinstance(data, list):
            raw_records = data
        # dict
        elif isinstance(data, dict):
            # 
            raw_records = []
            for key in ["entries", "records", "data", "libraries", "templates", "scaffolds", "sequences"]:
                if key in data and isinstance(data[key], list):
                    raw_records = data[key]
                    break
            # ，dictvalues
            if not raw_records:
                raw_records = [v for v in data.values() if isinstance(v, dict)]
            # ，dict
            if not raw_records:
                raw_records = [data]
        else:
            print(f"⚠️  : {type(data)}")
            return records
        
        # （）
        sequence_candidates = [
            "sequence_aa",  # IMGT
            "sequence",
            "aa_sequence",
            "v_sequence",
            "seq",
            "aa",
            "fr_sequence",
        ]
        
        # 
        for raw_record in raw_records:
            if not isinstance(raw_record, dict):
                continue
            
            # template_id
            template_id = (
                raw_record.get("id") or
                raw_record.get("template_id") or
                raw_record.get("scaffold_id") or
                raw_record.get("fr_id") or
                f"unknown_{len(records)}"
            )
            
            # （）
            sequence = None
            for candidate in sequence_candidates:
                if candidate in raw_record:
                    seq_value = raw_record[candidate]
                    if isinstance(seq_value, str) and len(seq_value) > 0:
                        # 
                        if any(aa in seq_value.upper() for aa in "ACDEFGHIKLMNPQRSTVWY"):
                            sequence = seq_value
                            break
            
            # ，consensus.framework_fullfr1-4
            if not sequence:
                if "consensus" in raw_record and isinstance(raw_record["consensus"], dict):
                    if "framework_full" in raw_record["consensus"]:
                        seq_value = raw_record["consensus"]["framework_full"]
                        if isinstance(seq_value, str) and seq_value:
                            sequence = seq_value
                    else:
                        # consensus.fr1-4
                        fr_parts = []
                        for fr in ["fr1", "fr2", "fr3", "fr4"]:
                            if fr in raw_record["consensus"]:
                                part = raw_record["consensus"][fr]
                                if isinstance(part, str) and part:
                                    fr_parts.append(part)
                        if len(fr_parts) == 4:
                            sequence = "".join(fr_parts)
            
            # ，
            if not sequence:
                missing_sequence_count += 1
                continue
            
            # 
            unified_record = {
                "template_id": template_id,
                "sequence": sequence,
                # （hallmark）
                "_raw": raw_record
            }
            records.append(unified_record)
        
        if missing_sequence_count > 0:
            print(f"  ⚠️  {missing_sequence_count} ，")
    
    except Exception as e:
        print(f"⚠️  IMGT amino_acid JSON {lib_path}: {e}")
    
    return records


def load_library(lib_path: Path, lib_format: str) -> List[Dict[str, Any]]:
    """"""
    records = []
    
    if not lib_path.exists():
        return records
    
    try:
        if lib_format.lower() == "jsonl":
            with open(lib_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        records.append(record)
                    except json.JSONDecodeError:
                        continue
        elif lib_format.lower() == "amino_acid":
            # IMGT amino_acid JSON
            records = load_imgt_aa_json(lib_path)
        elif lib_format.lower() == "json":
            with open(lib_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict):
                    # 
                    for key in ["entries", "records", "data", "libraries", "templates", "scaffolds"]:
                        if key in data and isinstance(data[key], list):
                            records = data[key]
                            break
                    if not records:
                        records = [data]
        else:
            print(f"⚠️  : {lib_format}")
    except Exception as e:
        print(f"⚠️   {lib_path}: {e}")
    
    return records


def extract_template_sequence(record: Dict[str, Any]) -> Optional[str]:
    """（：sequence > fr_sequence > consensus.framework_full > consensus.fr1-4 > sequence_aa）"""
    # 1: sequence（load_imgt_aa_json）
    if "sequence" in record:
        seq = record["sequence"]
        if isinstance(seq, str) and seq:
            return seq
    
    # 2: fr_sequence
    if "fr_sequence" in record:
        seq = record["fr_sequence"]
        if isinstance(seq, str) and seq:
            return seq
    
    # 3: sequence_aa（IMGT）
    if "sequence_aa" in record:
        seq = record["sequence_aa"]
        if isinstance(seq, str) and seq:
            return seq
    
    # 4: consensus.framework_full
    if "consensus" in record and isinstance(record["consensus"], dict):
        if "framework_full" in record["consensus"]:
            seq = record["consensus"]["framework_full"]
            if isinstance(seq, str) and seq:
                return seq
        
        # 5: consensus.fr1-4
        fr_parts = []
        for fr in ["fr1", "fr2", "fr3", "fr4"]:
            if fr in record["consensus"]:
                part = record["consensus"][fr]
                if isinstance(part, str) and part:
                    fr_parts.append(part)
        if len(fr_parts) == 4:
            return "".join(fr_parts)
    
    return None


def score_template(
    target_regions: Dict[str, str],
    template_seq: str,
    template_record: Dict[str, Any],
    template_id: str
) -> Dict[str, Any]:
    """"""
    score = {
        "template_id": template_id,
        "fr_identity": {},
        "cdr_length_match": {},
        "total_mutations": 0,
        "fr_mutations": 0,
        "mutations": [],
        "vhh_hallmark_score": None,
        "liabilities": [],
        "conservative_score": 0.0,
        "balanced_score": 0.0
    }
    
    # 
    template_numbering = number_and_segment(template_seq)
    if not template_numbering["success"]:
        return score
    
    template_regions = template_numbering["regions"]
    
    # FR identity
    fr_identities = {}
    for fr in ["FR1", "FR2", "FR3", "FR4"]:
        target_fr = target_regions.get(fr, "")
        template_fr = template_regions.get(fr, "")
        if target_fr and template_fr:
            identity = calculate_identity(target_fr, template_fr)
            fr_identities[fr] = identity
    score["fr_identity"] = fr_identities
    
    # CDR
    cdr_length_match = {}
    for cdr in ["CDR1", "CDR2", "CDR3"]:
        target_cdr = target_regions.get(cdr, "")
        template_cdr = template_regions.get(cdr, "")
        target_len = len(target_cdr)
        template_len = len(template_cdr)
        cdr_length_match[cdr] = {
            "target_length": target_len,
            "template_length": template_len,
            "match": target_len == template_len
        }
    score["cdr_length_match"] = cdr_length_match
    
    # （FR）
    mutations = []
    fr_mutations = 0
    for fr in ["FR1", "FR2", "FR3", "FR4"]:
        target_fr = target_regions.get(fr, "")
        template_fr = template_regions.get(fr, "")
        if target_fr and template_fr:
            min_len = min(len(target_fr), len(template_fr))
            for i in range(min_len):
                if target_fr[i] != template_fr[i]:
                    mutations.append({
                        "region": fr,
                        "position": i + 1,
                        "target": target_fr[i],
                        "template": template_fr[i]
                    })
                    fr_mutations += 1
    
    score["mutations"] = mutations
    score["fr_mutations"] = fr_mutations
    score["total_mutations"] = fr_mutations  # FR
    
    # VHH hallmark score
    if "vhh_hallmark" in template_record:
        hallmark = template_record["vhh_hallmark"]
        if isinstance(hallmark, dict) and "score" in hallmark:
            score["vhh_hallmark_score"] = hallmark["score"]
    
    # liabilities（）
    if "developability" in template_record:
        dev = template_record["developability"]
        if isinstance(dev, dict) and "liabilities" in dev:
            score["liabilities"] = dev["liabilities"]
    
    # 
    # Conservative: identity，，CDR
    avg_fr_identity = sum(fr_identities.values()) / len(fr_identities) if fr_identities else 0.0
    cdr_match_count = sum(1 for m in cdr_length_match.values() if m["match"])
    conservative_score = (avg_fr_identity * 0.5) + (cdr_match_count / 3.0 * 0.3) + ((1.0 - fr_mutations / 100.0) * 0.2)
    score["conservative_score"] = conservative_score
    
    # Balanced: hallmarkliabilities
    balanced_score = conservative_score
    if score["vhh_hallmark_score"] is not None:
        balanced_score = balanced_score * 0.8 + score["vhh_hallmark_score"] * 0.2
    if score["liabilities"]:
        # liabilities，
        balanced_score = balanced_score * 0.9
    score["balanced_score"] = balanced_score
    
    return score


def search_templates(
    target_regions: Dict[str, str],
    library_path: Path,
    library_format: str,
    top_n: int = 5
) -> List[Dict[str, Any]]:
    """Top N"""
    records = load_library(library_path, library_format)
    
    candidates = []
    missing_sequence_count = 0
    
    for record in records:
        template_seq = extract_template_sequence(record)
        if not template_seq:
            missing_sequence_count += 1
            continue
        
        # ID（）
        template_id = (
            record.get("template_id") or
            record.get("scaffold_id") or
            record.get("fr_id") or
            record.get("id", "unknown")
        )
        
        # （hallmark）
        raw_record = record.get("_raw", record)
        
        # 
        score = score_template(target_regions, template_seq, raw_record, template_id)
        candidates.append(score)
    
    if missing_sequence_count > 0:
        print(f"    ⚠️  {missing_sequence_count} ，")
    
    # balanced_score
    candidates.sort(key=lambda x: x["balanced_score"], reverse=True)
    
    return candidates[:top_n]


def benchmark_antibody(
    antibody_name: str,
    sequence: str,
    chain_type: str,
    library_ids: List[str],
    summary: Dict[str, Any]
) -> Dict[str, Any]:
    """benchmark"""
    result = {
        "antibody": antibody_name,
        "chain_type": chain_type,
        "numbering": {},
        "regions": {},
        "libraries": {},
        "best_library": None,
        "best_template": None
    }
    
    # 
    numbering_result = number_and_segment(sequence, chain_type)
    if not numbering_result["success"]:
        result["error"] = numbering_result["error"]
        return result
    
    result["numbering"] = numbering_result["numbering"]
    result["regions"] = numbering_result["regions"]
    result["engine_info"] = numbering_result["engine_info"]
    
    # 
    library_results = {}
    best_overall_score = -1.0
    best_library_id = None
    best_template = None
    
    for lib_id in library_ids:
        if lib_id not in summary["libraries"]:
            print(f"⚠️   {lib_id} summary，")
            continue
        
        lib_data = summary["libraries"][lib_id]
        lib_path = PROJECT_ROOT / lib_data["file_path"]
        lib_format = lib_data["format"]
        
        print(f"  : {lib_id}")
        candidates = search_templates(
            numbering_result["regions"],
            lib_path,
            lib_format,
            top_n=5
        )
        
        library_results[lib_id] = {
            "library_name": lib_data["name"],
            "candidates": candidates
        }
        
        # 
        if candidates:
            top_candidate = candidates[0]
            if top_candidate["balanced_score"] > best_overall_score:
                best_overall_score = top_candidate["balanced_score"]
                best_library_id = lib_id
                best_template = top_candidate
    
    result["libraries"] = library_results
    result["best_library"] = best_library_id
    result["best_template"] = best_template
    
    # （）
    if best_template and HAS_EXPLAINER:
        try:
            # 
            all_template_scores = []
            for lib_id, lib_result in library_results.items():
                all_template_scores.extend(lib_result.get("candidates", []))
            
            # （）
            policy_chain_type = "VHH" if chain_type == "H" and antibody_name == "7D12" else \
                              "VH" if chain_type == "H" else \
                              "VL" if chain_type in ["K", "L"] else "VH"
            
            # （）
            explanation_en = explain_template_selection(
                best_template,
                all_template_scores,
                policy_chain_type
            )
            explanation_zh = explain_template_selection_zh(
                best_template,
                all_template_scores,
                policy_chain_type
            )
            
            result["selection_explanation"] = explanation_en
            result["selection_explanation_zh"] = explanation_zh
        except Exception as e:
            print(f"  ⚠️  : {e}")
    
    # （，best_template）
    if best_template and HAS_DECISION_SUMMARY:
        try:
            decision_summary = build_decision_summary(result)
            if decision_summary:
                result["decision_summary"] = decision_summary
        except Exception as e:
            print(f"  ⚠️  : {e}")
    
    return result


def generate_report(results: Dict[str, Any]) -> str:
    """Markdown"""
    lines = []
    
    lines.append("# Pilot Benchmark v1 Report")
    lines.append("")
    lines.append(f"****: {datetime.now().isoformat()}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 7D12
    if "7d12" in results:
        lines.append("## 1. 7D12 VHH Benchmark")
        lines.append("")
        result_7d12 = results["7d12"]
        
        if "error" in result_7d12:
            lines.append(f"❌ ****: {result_7d12['error']}")
        else:
            # Decision Summary
            if result_7d12.get("decision_summary"):
                decision_summary = result_7d12["decision_summary"]
                lines.append("### Decision Summary")
                lines.append("")
                template_id_display = normalize_template_id_display(decision_summary.get('template_id', 'N/A'))
                lines.append(f"**Template ID**: {template_id_display}")
                lines.append(f"**Confidence Level**: {decision_summary.get('confidence_level', 'N/A')}")
                lines.append(f"**Risk Level**: {decision_summary.get('risk_level', 'N/A')}")
                lines.append("")
                
                # Usability Assessment (for Medium/High risk)
                risk_level = decision_summary.get('risk_level', '')
                if risk_level in ['Medium', 'High']:
                    lines.append("**Usability Assessment:**")
                    lines.append("")
                    if risk_level == 'Medium':
                        lines.append("- **English**: This template is **usable** and can proceed to experimental validation, but requires **careful consideration** of the noted concerns. The identified issues should be addressed through experimental validation and potential second-round optimization.")
                        lines.append("- ****: ****，，****。。")
                    else:  # High
                        lines.append("- **English**: This template **may be usable** with extensive experimental validation and comprehensive second-round optimization, but **higher risk should be carefully considered**. Proceeding requires thorough risk assessment.")
                        lines.append("- ****: ，****，****。。")
                    lines.append("")
                
                lines.append("**One-line Reason:**")
                lines.append("")
                lines.append(f"- **English**: {decision_summary.get('one_line_reason', {}).get('en', 'N/A')}")
                lines.append(f"- ****: {decision_summary.get('one_line_reason', {}).get('zh', 'N/A')}")
                lines.append("")
                if decision_summary.get('notes'):
                    lines.append("**Notes:**")
                    for note in decision_summary['notes']:
                        lines.append(f"- {note}")
                    lines.append("")
                
                # Rationales
                if decision_summary.get('rationales'):
                    rationales = decision_summary['rationales']
                    lines.append("**Risk Rationale (EN):**")
                    lines.append(rationales.get('risk', {}).get('en', 'N/A'))
                    lines.append("")
                    lines.append("**（）：**")
                    lines.append(rationales.get('risk', {}).get('zh', 'N/A'))
                    lines.append("")
                    lines.append("**Confidence Rationale (EN):**")
                    lines.append(rationales.get('confidence', {}).get('en', 'N/A'))
                    lines.append("")
                    lines.append("**（）：**")
                    lines.append(rationales.get('confidence', {}).get('zh', 'N/A'))
                    lines.append("")
                
                lines.append("---")
                lines.append("")
            
            lines.append("### ")
            
            lines.append("### ")
            lines.append("")
            if result_7d12.get("best_library"):
                best_lib = result_7d12["best_library"]
                best_template = result_7d12.get("best_template", {})
                lines.append(f"- ****: {best_lib}")
                template_id_display = normalize_template_id_display(best_template.get('template_id', 'N/A'))
                lines.append(f"- **ID**: {template_id_display}")
                lines.append(f"- **Balanced Score**: {best_template.get('balanced_score', 0.0):.3f}")
                lines.append(f"- **Conservative Score**: {best_template.get('conservative_score', 0.0):.3f}")
                lines.append("")
                
                # FR identity
                fr_identity = best_template.get("fr_identity", {})
                lines.append("#### FR Identity")
                lines.append("")
                for fr, identity in fr_identity.items():
                    lines.append(f"- {fr}: {identity:.3f}")
                lines.append("")
                
                # CDR
                cdr_match = best_template.get("cdr_length_match", {})
                lines.append("#### CDR")
                lines.append("")
                for cdr, match_info in cdr_match.items():
                    match_str = "✓" if match_info["match"] else "✗"
                    lines.append(f"- {cdr}: {match_str} (: {match_info['target_length']}, : {match_info['template_length']})")
                lines.append("")
                
                # 
                lines.append(f"#### ")
                lines.append("")
                lines.append(f"- **FR**: {best_template.get('fr_mutations', 0)}")
                lines.append(f"- ****: {best_template.get('total_mutations', 0)}")
                lines.append("")
                
                # Hallmark
                if best_template.get("vhh_hallmark_score") is not None:
                    lines.append(f"- **VHH Hallmark Score**: {best_template['vhh_hallmark_score']}")
                    lines.append("")
            
            # Template Selection Rationale
            if result_7d12.get("selection_explanation"):
                lines.append("### Template Selection Rationale")
                lines.append("")
                explanation = result_7d12.get("selection_explanation", {})
                explanation_zh = result_7d12.get("selection_explanation_zh", {})
                
                # 
                lines.append("#### English")
                lines.append("")
                if explanation.get("key_reasons"):
                    lines.append("**Key Reasons:**")
                    for reason in explanation["key_reasons"]:
                        lines.append(f"- {reason}")
                    lines.append("")
                if explanation.get("caution_notes"):
                    lines.append("**Caution Notes:**")
                    for note in explanation["caution_notes"]:
                        lines.append(f"- {note}")
                    lines.append("")
                
                # 
                lines.append("#### ")
                lines.append("")
                if explanation_zh.get("key_reasons"):
                    lines.append("**:**")
                    for reason in explanation_zh["key_reasons"]:
                        lines.append(f"- {reason}")
                    lines.append("")
                if explanation_zh.get("caution_notes"):
                    lines.append("**:**")
                    for note in explanation_zh["caution_notes"]:
                        lines.append(f"- {note}")
                    lines.append("")
            
            # Top
            lines.append("### Top")
            lines.append("")
            for lib_id, lib_result in result_7d12.get("libraries", {}).items():
                lines.append(f"#### {lib_result['library_name']} ({lib_id})")
                lines.append("")
                candidates = lib_result.get("candidates", [])
                if candidates:
                    lines.append("|  | Template ID | Balanced Score | FR Identity (Avg) | FR Mutations |")
                    lines.append("|------|-------------|----------------|-------------------|--------------|")
                    for i, cand in enumerate(candidates[:5], 1):
                        avg_fr_id = sum(cand.get("fr_identity", {}).values()) / len(cand.get("fr_identity", {})) if cand.get("fr_identity") else 0.0
                        template_id_display = normalize_template_id_display(cand.get('template_id', 'N/A'))
                        lines.append(f"| {i} | {template_id_display} | {cand.get('balanced_score', 0.0):.3f} | {avg_fr_id:.3f} | {cand.get('fr_mutations', 0)} |")
                else:
                    lines.append("")
                lines.append("")
        
        lines.append("---")
        lines.append("")
    
    # 6JBT
    if "6jbt_vh" in results:
        lines.append("## 2. 6JBT VH Benchmark")
        lines.append("")
        result_6jbt_vh = results["6jbt_vh"]
        
        if "error" in result_6jbt_vh:
            lines.append(f"❌ ****: {result_6jbt_vh['error']}")
        else:
            # Decision Summary
            if result_6jbt_vh.get("decision_summary"):
                decision_summary = result_6jbt_vh["decision_summary"]
                lines.append("### Decision Summary")
                lines.append("")
                template_id_display = normalize_template_id_display(decision_summary.get('template_id', 'N/A'))
                lines.append(f"**Template ID**: {template_id_display}")
                lines.append(f"**Confidence Level**: {decision_summary.get('confidence_level', 'N/A')}")
                lines.append(f"**Risk Level**: {decision_summary.get('risk_level', 'N/A')}")
                lines.append("")
                
                # Usability Assessment (for Medium/High risk)
                risk_level = decision_summary.get('risk_level', '')
                if risk_level in ['Medium', 'High']:
                    lines.append("**Usability Assessment:**")
                    lines.append("")
                    if risk_level == 'Medium':
                        lines.append("- **English**: This template is **usable** and can proceed to experimental validation, but requires **careful consideration** of the noted concerns. The identified issues should be addressed through experimental validation and potential second-round optimization.")
                        lines.append("- ****: ****，，****。。")
                    else:  # High
                        lines.append("- **English**: This template **may be usable** with extensive experimental validation and comprehensive second-round optimization, but **higher risk should be carefully considered**. Proceeding requires thorough risk assessment.")
                        lines.append("- ****: ，****，****。。")
                    lines.append("")
                
                lines.append("**One-line Reason:**")
                lines.append("")
                lines.append(f"- **English**: {decision_summary.get('one_line_reason', {}).get('en', 'N/A')}")
                lines.append(f"- ****: {decision_summary.get('one_line_reason', {}).get('zh', 'N/A')}")
                lines.append("")
                if decision_summary.get('notes'):
                    lines.append("**Notes:**")
                    for note in decision_summary['notes']:
                        lines.append(f"- {note}")
                    lines.append("")
                
                # Rationales
                if decision_summary.get('rationales'):
                    rationales = decision_summary['rationales']
                    lines.append("**Risk Rationale (EN):**")
                    lines.append(rationales.get('risk', {}).get('en', 'N/A'))
                    lines.append("")
                    lines.append("**（）：**")
                    lines.append(rationales.get('risk', {}).get('zh', 'N/A'))
                    lines.append("")
                    lines.append("**Confidence Rationale (EN):**")
                    lines.append(rationales.get('confidence', {}).get('en', 'N/A'))
                    lines.append("")
                    lines.append("**（）：**")
                    lines.append(rationales.get('confidence', {}).get('zh', 'N/A'))
                    lines.append("")
                
                lines.append("---")
                lines.append("")
            
            lines.append("### ")
            lines.append("")
            lines.append(f"- ****: {result_6jbt_vh.get('engine_info', {}).get('name', 'unknown')}")
            lines.append("")
            
            lines.append("### ")
            lines.append("")
            if result_6jbt_vh.get("best_library"):
                best_lib = result_6jbt_vh["best_library"]
                best_template = result_6jbt_vh.get("best_template", {})
                lines.append(f"- ****: {best_lib}")
                template_id_display = normalize_template_id_display(best_template.get('template_id', 'N/A'))
                lines.append(f"- **ID**: {template_id_display}")
                lines.append(f"- **Balanced Score**: {best_template.get('balanced_score', 0.0):.3f}")
                lines.append("")
                
                # FR identity
                fr_identity = best_template.get("fr_identity", {})
                if fr_identity:
                    lines.append("#### FR Identity")
                    lines.append("")
                    for fr, identity in fr_identity.items():
                        lines.append(f"- {fr}: {identity:.3f}")
                    lines.append("")
                
                # CDR
                cdr_match = best_template.get("cdr_length_match", {})
                if cdr_match:
                    lines.append("#### CDR")
                    lines.append("")
                    for cdr, match_info in cdr_match.items():
                        match_str = "✓" if match_info["match"] else "✗"
                        lines.append(f"- {cdr}: {match_str} (: {match_info['target_length']}, : {match_info['template_length']})")
                    lines.append("")
                
                # 
                lines.append(f"#### ")
                lines.append("")
                lines.append(f"- **FR**: {best_template.get('fr_mutations', 0)}")
                lines.append(f"- ****: {best_template.get('total_mutations', 0)}")
                lines.append("")
            
            # Template Selection Rationale
            if result_6jbt_vh.get("selection_explanation"):
                lines.append("### Template Selection Rationale")
                lines.append("")
                explanation = result_6jbt_vh.get("selection_explanation", {})
                explanation_zh = result_6jbt_vh.get("selection_explanation_zh", {})
                
                # 
                lines.append("#### English")
                lines.append("")
                if explanation.get("key_reasons"):
                    lines.append("**Key Reasons:**")
                    for reason in explanation["key_reasons"]:
                        lines.append(f"- {reason}")
                    lines.append("")
                if explanation.get("caution_notes"):
                    lines.append("**Caution Notes:**")
                    for note in explanation["caution_notes"]:
                        lines.append(f"- {note}")
                    lines.append("")
                
                # 
                lines.append("#### ")
                lines.append("")
                if explanation_zh.get("key_reasons"):
                    lines.append("**:**")
                    for reason in explanation_zh["key_reasons"]:
                        lines.append(f"- {reason}")
                    lines.append("")
                if explanation_zh.get("caution_notes"):
                    lines.append("**:**")
                    for note in explanation_zh["caution_notes"]:
                        lines.append(f"- {note}")
                    lines.append("")
        
        lines.append("---")
        lines.append("")
    
    # 6JBT VL
    if "6jbt_vl" in results:
        lines.append("## 3. 6JBT VL Benchmark")
        lines.append("")
        result_6jbt_vl = results["6jbt_vl"]
        
        if "error" in result_6jbt_vl:
            lines.append(f"❌ ****: {result_6jbt_vl['error']}")
        else:
            # Decision Summary
            if result_6jbt_vl.get("decision_summary"):
                decision_summary = result_6jbt_vl["decision_summary"]
                lines.append("### Decision Summary")
                lines.append("")
                template_id_display = normalize_template_id_display(decision_summary.get('template_id', 'N/A'))
                lines.append(f"**Template ID**: {template_id_display}")
                lines.append(f"**Confidence Level**: {decision_summary.get('confidence_level', 'N/A')}")
                lines.append(f"**Risk Level**: {decision_summary.get('risk_level', 'N/A')}")
                lines.append("")
                
                # Usability Assessment (for Medium/High risk)
                risk_level = decision_summary.get('risk_level', '')
                if risk_level in ['Medium', 'High']:
                    lines.append("**Usability Assessment:**")
                    lines.append("")
                    if risk_level == 'Medium':
                        lines.append("- **English**: This template is **usable** and can proceed to experimental validation, but requires **careful consideration** of the noted concerns. The identified issues should be addressed through experimental validation and potential second-round optimization.")
                        lines.append("- ****: ****，，****。。")
                    else:  # High
                        lines.append("- **English**: This template **may be usable** with extensive experimental validation and comprehensive second-round optimization, but **higher risk should be carefully considered**. Proceeding requires thorough risk assessment.")
                        lines.append("- ****: ，****，****。。")
                    lines.append("")
                
                lines.append("**One-line Reason:**")
                lines.append("")
                lines.append(f"- **English**: {decision_summary.get('one_line_reason', {}).get('en', 'N/A')}")
                lines.append(f"- ****: {decision_summary.get('one_line_reason', {}).get('zh', 'N/A')}")
                lines.append("")
                if decision_summary.get('notes'):
                    lines.append("**Notes:**")
                    for note in decision_summary['notes']:
                        lines.append(f"- {note}")
                    lines.append("")
                
                # Rationales
                if decision_summary.get('rationales'):
                    rationales = decision_summary['rationales']
                    lines.append("**Risk Rationale (EN):**")
                    lines.append(rationales.get('risk', {}).get('en', 'N/A'))
                    lines.append("")
                    lines.append("**（）：**")
                    lines.append(rationales.get('risk', {}).get('zh', 'N/A'))
                    lines.append("")
                    lines.append("**Confidence Rationale (EN):**")
                    lines.append(rationales.get('confidence', {}).get('en', 'N/A'))
                    lines.append("")
                    lines.append("**（）：**")
                    lines.append(rationales.get('confidence', {}).get('zh', 'N/A'))
                    lines.append("")
                
                lines.append("---")
                lines.append("")
            
            lines.append("### ")
            lines.append("")
            lines.append(f"- ****: {result_6jbt_vl.get('engine_info', {}).get('name', 'unknown')}")
            lines.append("")
            
            lines.append("### ")
            lines.append("")
            if result_6jbt_vl.get("best_library"):
                best_lib = result_6jbt_vl["best_library"]
                best_template = result_6jbt_vl.get("best_template", {})
                lines.append(f"- ****: {best_lib}")
                template_id_display = normalize_template_id_display(best_template.get('template_id', 'N/A'))
                lines.append(f"- **ID**: {template_id_display}")
                lines.append(f"- **Balanced Score**: {best_template.get('balanced_score', 0.0):.3f}")
                lines.append("")
                
                # FR identity
                fr_identity = best_template.get("fr_identity", {})
                if fr_identity:
                    lines.append("#### FR Identity")
                    lines.append("")
                    for fr, identity in fr_identity.items():
                        lines.append(f"- {fr}: {identity:.3f}")
                    lines.append("")
                
                # CDR
                cdr_match = best_template.get("cdr_length_match", {})
                if cdr_match:
                    lines.append("#### CDR")
                    lines.append("")
                    for cdr, match_info in cdr_match.items():
                        match_str = "✓" if match_info["match"] else "✗"
                        lines.append(f"- {cdr}: {match_str} (: {match_info['target_length']}, : {match_info['template_length']})")
                    lines.append("")
                
                # 
                lines.append(f"#### ")
                lines.append("")
                lines.append(f"- **FR**: {best_template.get('fr_mutations', 0)}")
                lines.append(f"- ****: {best_template.get('total_mutations', 0)}")
                lines.append("")
            
            # Template Selection Rationale
            if result_6jbt_vl.get("selection_explanation"):
                lines.append("### Template Selection Rationale")
                lines.append("")
                explanation = result_6jbt_vl.get("selection_explanation", {})
                explanation_zh = result_6jbt_vl.get("selection_explanation_zh", {})
                
                # 
                lines.append("#### English")
                lines.append("")
                if explanation.get("key_reasons"):
                    lines.append("**Key Reasons:**")
                    for reason in explanation["key_reasons"]:
                        lines.append(f"- {reason}")
                    lines.append("")
                if explanation.get("caution_notes"):
                    lines.append("**Caution Notes:**")
                    for note in explanation["caution_notes"]:
                        lines.append(f"- {note}")
                    lines.append("")
                
                # 
                lines.append("#### ")
                lines.append("")
                if explanation_zh.get("key_reasons"):
                    lines.append("**:**")
                    for reason in explanation_zh["key_reasons"]:
                        lines.append(f"- {reason}")
                    lines.append("")
                if explanation_zh.get("caution_notes"):
                    lines.append("**:**")
                    for note in explanation_zh["caution_notes"]:
                        lines.append(f"- {note}")
                    lines.append("")
        
        lines.append("---")
        lines.append("")
    
    # 
    lines.append("## 4. ")
    lines.append("")
    lines.append("| ID |  |  |")
    lines.append("|------|------|------|")
    
    # （）
    library_grades = results.get("library_grades", {})
    for lib_id, grade_info in library_grades.items():
        grade = grade_info.get("grade", "P2")
        reason = grade_info.get("reason", "")
        lines.append(f"| {lib_id} | {grade} | {reason} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("****:")
    lines.append("- **P0**: （）")
    lines.append("- **P1**: /")
    lines.append("- **P2**: ")
    lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Pilot Benchmark v1: 7D12 VHH + 6JBT VH/VL")
    parser.add_argument("--summary_json", type=Path, required=True,
                        help="Path to arsenal_summary_v1.json")
    parser.add_argument("--seq_7d12", type=Path, required=True,
                        help="Path to 7D12 VHH FASTA")
    parser.add_argument("--seq_6jbt_vh", type=Path, required=True,
                        help="Path to 6JBT VH FASTA")
    parser.add_argument("--seq_6jbt_vl", type=Path, default=None,
                        help="Path to 6JBT VL FASTA (optional)")
    parser.add_argument("--out_dir", type=Path, required=True,
                        help="Output directory")
    
    args = parser.parse_args()
    
    # 
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # summary
    print("🔍 arsenal summary...")
    with open(args.summary_json, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    results = {}
    
    # 7D12 VHH benchmark
    print("\n📊 7D12 VHH benchmark...")
    try:
        header_7d12, seq_7d12 = read_fasta(args.seq_7d12)
        print(f"  : {len(seq_7d12)}")
        
        library_ids_7d12 = [
            "human_vh3_vhh_safe_templates",
            "vhh_scaffold_library_v1",
            "vhh_special_fr_templates_v1"
        ]
        
        result_7d12 = benchmark_antibody(
            "7D12",
            seq_7d12,
            "H",
            library_ids_7d12,
            summary
        )
        results["7d12"] = result_7d12
        print(f"  ✅ ，: {result_7d12.get('best_library', 'N/A')}")
    except Exception as e:
        print(f"  ❌ : {e}")
        results["7d12"] = {"error": str(e)}
    
    # 6JBT VH benchmark
    print("\n📊 6JBT VH benchmark...")
    try:
        header_6jbt_vh, seq_6jbt_vh = read_fasta(args.seq_6jbt_vh)
        print(f"  : {len(seq_6jbt_vh)}")
        
        library_ids_6jbt_vh = [
            "human_vh3_scaffolds",
            "human_IGHV"
        ]
        
        result_6jbt_vh = benchmark_antibody(
            "6JBT_VH",
            seq_6jbt_vh,
            "H",
            library_ids_6jbt_vh,
            summary
        )
        results["6jbt_vh"] = result_6jbt_vh
        print(f"  ✅ ，: {result_6jbt_vh.get('best_library', 'N/A')}")
    except Exception as e:
        print(f"  ❌ : {e}")
        results["6jbt_vh"] = {"error": str(e)}
    
    # 6JBT VL benchmark（）
    if args.seq_6jbt_vl:
        print("\n📊 6JBT VL benchmark...")
        try:
            header_6jbt_vl, seq_6jbt_vl = read_fasta(args.seq_6jbt_vl)
            print(f"  : {len(seq_6jbt_vl)}")
            
            # kappalambda（）
            library_ids_6jbt_vl = ["human_IGKV"]  # kappa，
            
            result_6jbt_vl = benchmark_antibody(
                "6JBT_VL",
                seq_6jbt_vl,
                "K",
                library_ids_6jbt_vl,
                summary
            )
            results["6jbt_vl"] = result_6jbt_vl
            print(f"  ✅ ，: {result_6jbt_vl.get('best_library', 'N/A')}")
        except Exception as e:
            print(f"  ❌ : {e}")
            results["6jbt_vl"] = {"error": str(e)}
    
    # （）
    library_grades = {}
    for lib_id in summary["libraries"]:
        grade = "P2"  # P2
        reason = ""
        
        # 
        best_count = 0
        if results.get("7d12", {}).get("best_library") == lib_id:
            best_count += 1
        if results.get("6jbt_vh", {}).get("best_library") == lib_id:
            best_count += 1
        if results.get("6jbt_vl", {}).get("best_library") == lib_id:
            best_count += 1
        
        # ，P0
        if best_count >= 2:
            grade = "P0"
            reason = f"{best_count}"
        # ，P1
        elif best_count >= 1:
            grade = "P1"
            reason = "/"
        
        library_grades[lib_id] = {"grade": grade, "reason": reason}
    
    results["library_grades"] = library_grades
    
    # JSON
    json_path = args.out_dir / "pilot_results.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ JSON: {json_path}")
    
    # MD
    md_path = args.out_dir / "pilot_report.md"
    md_content = generate_report(results)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"✅ Markdown: {md_path}")
    
    print(f"\n✅ ！")


if __name__ == "__main__":
    main()

