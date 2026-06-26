"""
EGFR VHH （Evidence-first, Fail-fast）

Single Source of Truth：JSON 
MD/HTML  JSON ，、""。

Evidence-first： *_provenance + evidence
 provenance  evidence ，。

Fail-fast： fallback、、，
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# IMGT
MIN_IMGT_VH_LENGTH = 70  # IMGT VH（FR1+FR2+FR3）

# VHH-SAFE（ generate_human_vhh_safe_templates.py ）
SAFE_PLAN_DEFINITIONS = {
    "A": {
        "name": "",
        "description": "44→Q, 45→R",
        "mutations": {
            44: "Q",
            45: "R"
        },
        "functional_meaning": "，FR24445，"
    },
    "B": {
        "name": "",
        "description": "44→Q, 45→R, 47→G",
        "mutations": {
            44: "Q",
            45: "R",
            47: "G"
        },
        "functional_meaning": "，FR2 hallmark（44/45/47），VHH，"
    },
    "C": {
        "name": "VHH",
        "description": "scaffold: 44=Q, 45=R, 47=G",
        "mutations": {
            44: "Q",
            45: "R",
            47: "G"
        },
        "functional_meaning": "VHHFR2 hallmark，VHH，VHH"
    }
}

# FR2 hallmark
HALLMARK_FUNCTIONAL_EXPLANATIONS = {
    44: {
        "name": "FR2 Hallmark Position 44",
        "typical_natural": "A, L, V ()",
        "safe_mutation": "Q (，)",
        "functional_impact": "Q。Q，FR2，。",
        "vhh_significance": "VHH44100%Q，VHHhallmark。"
    },
    45: {
        "name": "FR2 Hallmark Position 45",
        "typical_natural": "A, L, V ()",
        "safe_mutation": "R (，)",
        "functional_impact": "R。R，FR2，CDR3。",
        "vhh_significance": "VHH45AR，R。"
    },
    47: {
        "name": "FR2 Hallmark Position 47",
        "typical_natural": "L, V, I, F ()",
        "safe_mutation": "G (，)",
        "functional_impact": "G，FR2。GFR2VHH，。",
        "vhh_significance": "VHH47100%G，VHH。"
    }
}


def extract_safe_plan_from_template_id(template_id: str) -> Optional[str]:
    """
     template_id  SAFE （A/B/C）
    
    Args:
        template_id: ID， "HUMAN_VH3_SCF_10_SAFE_A"
    
    Returns:
        'A', 'B', 'C'  None（）
    """
    if not template_id:
        return None
    
    #  SAFE_A, SAFE_B, SAFE_C
    template_id_upper = template_id.upper()
    if "_SAFE_A" in template_id_upper or template_id_upper.endswith("_SAFE_A"):
        return "A"
    elif "_SAFE_B" in template_id_upper or template_id_upper.endswith("_SAFE_B"):
        return "B"
    elif "_SAFE_C" in template_id_upper or template_id_upper.endswith("_SAFE_C"):
        return "C"
    
    return None


def calculate_file_sha256(file_path: Path) -> str:
    """SHA256"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def step1_read_and_normalize_input(fasta_path: Path) -> Tuple[str, Dict[str, Any]]:
    """
    Step 1：
    
    Returns:
        (sequence, input_provenance)
    """
    if not fasta_path.exists():
        raise FileNotFoundError(f"FASTA: {fasta_path}")
    
    # FASTA
    sequence = ""
    sequence_id = ""
    with open(fasta_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                sequence_id = line[1:].strip()
            else:
                sequence += line
    
    # ：//
    sequence = sequence.replace(" ", "").replace("\n", "").replace("\r", "").upper()
    
    # 20AA（X，）
    valid_aa = set("ACDEFGHIKLMNPQRSTVWYX")
    invalid_chars = []
    for char in sequence:
        if char not in valid_aa:
            invalid_chars.append(char)
    
    aa_alphabet_check = {
        "valid": len(invalid_chars) == 0,
        "invalid_chars": list(set(invalid_chars))
    }
    
    # SHA256
    sha256 = calculate_file_sha256(fasta_path)
    
    # provenance
    input_provenance = {
        "source_file": str(fasta_path.relative_to(PROJECT_ROOT)) if fasta_path.is_relative_to(PROJECT_ROOT) else str(fasta_path),
        "absolute_path": str(fasta_path.resolve()),
        "sha256": sha256,
        "sequence_id": sequence_id or "unknown",
        "length": len(sequence),
        "aa_alphabet_check": aa_alphabet_check,
        "loaded_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    
    # Fail
    if not aa_alphabet_check["valid"]:
        raise ValueError(
            f": {invalid_chars}。"
            "20（ACDEFGHIKLMNPQRSTVWY）X。"
        )
    
    if len(sequence) == 0:
        raise ValueError("FASTA")
    
    return sequence, input_provenance


def step2_segment_target_sequence(sequence: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Step 2： IMGT （ANARCII，）
    
    Returns:
        (segmentation, segmentation_provenance)
    """
    try:
        from core.segmentation.anarcii_adapter import run_anarcii_imgt
        
        segmentation, numbering, provenance = run_anarcii_imgt(
            seq=sequence,
            species="camelid",
            chain="H",
            allow_partial=True,
            max_mismatches=0,
        )
        
        # 20
        numbering_first_20 = []
        for row in numbering[:20]:
            numbering_first_20.append({
                "pos": str(row.get("pos", "")),
                "aa": row.get("aa", ""),
            })
        
        # provenanceboundaries
        boundaries = provenance.get("evidence", {}).get("boundaries", {})
        
        # ：regions
        reconstructed = ""
        for region in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]:
            reconstructed += segmentation.get(region, "")
        
        reconstruction_check = {
            "matches_input": reconstructed == sequence,
            "reconstructed_length": len(reconstructed),
            "input_length": len(sequence),
        }
        
        # segmentation
        segmentation_dict = {
            "scheme": "imgt",
            "regions": segmentation,
            "boundaries": boundaries,
            "numbering_first_20": numbering_first_20,
            "reconstruction_check": reconstruction_check,
        }
        
        # provenance
        segmentation_provenance = {
            "method": provenance.get("method", "unknown"),
            "package": provenance.get("implementation", {}).get("package", "unknown"),
            "package_version": provenance.get("implementation", {}).get("version", "unknown"),
            "scheme": "imgt",
            "executed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        
        # Fail
        method = segmentation_provenance.get("method")
        if method != "anarcii" and not method.startswith("fallback:"):
            raise ValueError(
                f"segmentation_provenance.method = '{method}' != 'anarcii' "
                "fallback。ANARCII。"
            )
        
        if not reconstruction_check["matches_input"]:
            raise ValueError(
                f"：={reconstruction_check['reconstructed_length']}, "
                f"={reconstruction_check['input_length']}。"
            )
        
        return segmentation_dict, segmentation_provenance
        
    except Exception as e:
        raise RuntimeError(f"Step 2 (IMGT) : {e}") from e


def step3_load_germline_library(germline_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Step 3：germline 
    
    Returns:
        (library_data, germline_library_provenance)
    """
    if not germline_path.exists():
        raise FileNotFoundError(f"Germline: {germline_path}")
    
    # 
    with open(germline_path, "r", encoding="utf-8") as f:
        library_data = json.load(f)
    
    # SHA256
    sha256 = calculate_file_sha256(germline_path)
    
    # entry_count
    entry_count = 0
    if isinstance(library_data, list):
        entry_count = len(library_data)
    elif isinstance(library_data, dict):
        if "entries" in library_data:
            entry_count = len(library_data["entries"])
        elif "templates" in library_data:
            entry_count = len(library_data["templates"])
        else:
            entry_count = len([k for k in library_data.keys() if not k.startswith("_")])
    
    # provenance
    germline_library_provenance = {
        "library_name": "human_VH3_germline_library",
        "source": "internal_consensus_scaffold",
        "version": "v1.0",
        "path": str(germline_path.relative_to(PROJECT_ROOT)) if germline_path.is_relative_to(PROJECT_ROOT) else str(germline_path),
        "absolute_path": str(germline_path.resolve()),
        "entry_count": entry_count,
        "sha256": sha256,
        "loaded_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    
    # Fail
    if entry_count == 0:
        raise ValueError(f"Germlineentry_count=0，")
    
    if not sha256:
        raise ValueError("Germlinesha256")
    
    return library_data, germline_library_provenance


def step4_number_germline_templates(
    library_data: Dict[str, Any],
    template_ids: List[str],
) -> Dict[str, Any]:
    """
    Step 4： germline  IMGT （ANARCII，/）
    
    Args:
        library_data: 
        template_ids: ID
    
    Returns:
        germline_numbering
    """
    from core.segmentation.germline_numbering import number_germline_sequence_anarcii
    
    # template_id
    template_sequence_map = {}
    
    if isinstance(library_data, list):
        for entry in library_data:
            entry_id = entry.get("id") or entry.get("template_id")
            # 
            sequence = (
                entry.get("sequence_aa") or
                entry.get("sequence") or
                entry.get("consensus", {}).get("framework_full") or
                entry.get("framework_full")
            )
            if entry_id and sequence:
                template_sequence_map[entry_id] = sequence
    elif isinstance(library_data, dict):
        entries = library_data.get("entries", []) or library_data.get("templates", [])
        for entry in entries:
            entry_id = entry.get("id") or entry.get("template_id")
            sequence = (
                entry.get("sequence_aa") or
                entry.get("sequence") or
                entry.get("consensus", {}).get("framework_full") or
                entry.get("framework_full")
            )
            if entry_id and sequence:
                template_sequence_map[entry_id] = sequence
    
    # （）
    numberings = {}
    provenance = None
    failed_templates = []
    
    for template_id in template_ids:
        sequence = template_sequence_map.get(template_id)
        if not sequence:
            failed_templates.append({"template_id": template_id, "reason": "sequence_not_found"})
            continue
        
        try:
            numbering_dict, provenance_dict = number_germline_sequence_anarcii(
                sequence=sequence,
                template_id=template_id,
                scheme="imgt",
            )
            
            # 20
            positions_first_20 = numbering_dict.get("positions", [])[:20]
            numbering_dict["positions_first_20"] = positions_first_20
            
            numberings[template_id] = numbering_dict
            
            # provenanceprovenance
            if provenance is None:
                provenance = provenance_dict
        except Exception as e:
            # （）
            failed_templates.append({"template_id": template_id, "reason": str(e)})
            continue
    
    if not numberings:
        raise ValueError("Step 4 (germline) ：")
    
    if not provenance:
        raise ValueError("Step 4 (germline) ：numbering_provenance")
    
    # Fail
    method = provenance.get("method")
    if method != "anarcii" and not method.startswith("fallback:"):
        raise ValueError(
            f"germline_numbering.numbering_provenance.method = '{method}' != 'anarcii' "
            "fallback。ANARCII。"
        )
    
    result = {
        "numberings": numberings,
        "numbering_provenance": provenance,
    }
    
    # ，result
    if failed_templates:
        result["failed_templates"] = failed_templates[:10]  # 10
        result["failed_count"] = len(failed_templates)
    
    return result


def filter_imgt_compatible_templates_before_numbering(
    library_data: Dict[str, Any],
    min_length: int = 70,
) -> Tuple[List[str], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    ：IMGT
    
    IF sequence_length < MIN_IMGT_VH_LENGTH:
        exclude_from_germline_selection
        record_in_excluded_templates(reason="non-IMGT-compatible length")
    
    ：
    - ❌ germline
    - ✅ fr_only_templates.json，
    - ❌ "/"
    
    Args:
        library_data: 
        min_length: IMGT VH
    
    Returns:
        (eligible_templates, excluded_templates, fr_only_templates)
        - eligible_templates: ID
        - excluded_templates: 
        - fr_only_templates: FR-only（）
    """
    # template_id
    template_sequence_map = {}
    template_data_map = {}
    
    if isinstance(library_data, list):
        for entry in library_data:
            entry_id = entry.get("id") or entry.get("template_id")
            sequence = (
                entry.get("sequence_aa") or
                entry.get("sequence") or
                entry.get("consensus", {}).get("framework_full") or
                entry.get("framework_full")
            )
            if entry_id and sequence:
                template_sequence_map[entry_id] = sequence
                template_data_map[entry_id] = entry
    elif isinstance(library_data, dict):
        entries = library_data.get("entries", []) or library_data.get("templates", [])
        for entry in entries:
            entry_id = entry.get("id") or entry.get("template_id")
            sequence = (
                entry.get("sequence_aa") or
                entry.get("sequence") or
                entry.get("consensus", {}).get("framework_full") or
                entry.get("framework_full")
            )
            if entry_id and sequence:
                template_sequence_map[entry_id] = sequence
                template_data_map[entry_id] = entry
    
    eligible_templates = []
    excluded_templates = []
    fr_only_templates = []
    
    for template_id, sequence in template_sequence_map.items():
        sequence_length = len(sequence)
        
        if sequence_length < min_length:
            # IMGT，
            excluded_info = {
                "template_id": template_id,
                "sequence_length": sequence_length,
                "min_required": min_length,
                "reason": "non-IMGT-compatible length",
            }
            excluded_templates.append(excluded_info)
            
            # fr_only_templates
            template_data = template_data_map.get(template_id, {})
            fr_only_entry = {
                "template_id": template_id,
                "sequence_length": sequence_length,
                "sequence": sequence,
                "exclusion_reason": "non-IMGT-compatible length",
                "original_data": template_data,
            }
            fr_only_templates.append(fr_only_entry)
        else:
            # ，eligible
            eligible_templates.append(template_id)
    
    return eligible_templates, excluded_templates, fr_only_templates


def step5_align_target_vs_germlines(
    target_numbering_rows: List[Dict[str, Any]],
    target_boundaries: Dict[str, List[int]],
    germline_numberings: Dict[str, Dict[str, Any]],
    mask_regions: List[str] = ["CDR1", "CDR2", "CDR3"],
    safe_plan_filter: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Step 5： vs  germline  IMGT 
    
    Args:
        target_numbering: IMGT
        target_boundaries: boundaries
        germline_numberings: germline
        mask_regions: mask（CDR）
        safe_plan_filter:  SAFE （'A', 'B', 'C'），
    
    Returns:
        (germline_candidates, germline_alignment_provenance)
    """
    # positionaa
    target_pos_map = {}
    for row in target_numbering_rows:
        pos = row.get("pos")
        aa = row.get("aa")
        if pos and aa:
            try:
                target_pos_map[int(pos)] = aa
            except (ValueError, TypeError):
                continue
    
    # （mask_regions）
    positions_to_compare = set()
    for region, bounds in target_boundaries.items():
        if region not in mask_regions:
            start, end = bounds
            for pos in range(start, end + 1):
                positions_to_compare.add(pos)
    
    # germline
    candidates = []
    
    for template_id, germline_numbering in germline_numberings.items():
        #  safe_plan_filter，
        if safe_plan_filter:
            template_safe_plan = extract_safe_plan_from_template_id(template_id)
            if template_safe_plan != safe_plan_filter:
                continue
        positions = germline_numbering.get("positions", [])
        boundaries = germline_numbering.get("boundaries", {})
        
        # germlinepositionaa
        germline_pos_map = {}
        for pos_data in positions:
            pos = pos_data.get("pos")
            aa = pos_data.get("aa")
            if pos and aa:
                try:
                    germline_pos_map[int(pos)] = aa
                except (ValueError, TypeError):
                    continue
        
        # match/total
        region_counts = {}
        first_10_mismatches = []
        
        for region in ["FR1", "FR2", "FR3", "FR4"]:
            if region not in boundaries:
                region_counts[region] = {"match": 0, "total": 0}
                continue
            
            start, end = boundaries[region]
            match = 0
            total = 0
            
            for pos in range(start, end + 1):
                if pos in positions_to_compare:
                    total += 1
                    target_aa = target_pos_map.get(pos)
                    germline_aa = germline_pos_map.get(pos)
                    
                    if target_aa and germline_aa:
                        if target_aa == germline_aa:
                            match += 1
                        elif len(first_10_mismatches) < 10:
                            first_10_mismatches.append({
                                "pos": str(pos),
                                "query": target_aa,
                                "ref": germline_aa,
                            })
            
            region_counts[region] = {"match": match, "total": total}
        
        # framework_identity（FR）
        total_match = sum(r["match"] for r in region_counts.values())
        total_positions = sum(r["total"] for r in region_counts.values())
        framework_identity = total_match / total_positions if total_positions > 0 else 0.0
        
        # IMGT
        imgt_positions_compared = len(positions_to_compare & set(germline_pos_map.keys()) & set(target_pos_map.keys()))
        
        candidates.append({
            "template_id": template_id,
            "region_counts": region_counts,
            "framework_identity": round(framework_identity, 4),
            "evidence": {
                "imgt_positions_compared": imgt_positions_compared,
                "first_10_mismatches": first_10_mismatches[:10],
            },
        })
    
    # alignment_provenance
    alignment_provenance = {
        "algorithm": "imgt_position_identity",
        "scheme": "imgt",
        "mask_regions": mask_regions,
        "gap_policy": "disallow",
        "executed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    
    # Fail
    if not candidates:
        raise ValueError("Step 5 () ：")
    
    for cand in candidates:
        if cand["evidence"]["imgt_positions_compared"] == 0:
            raise ValueError(
                f"Step 5 () ：{cand['template_id']}"
                "imgt_positions_compared=0，IMGT position-level"
            )
    
    return candidates, alignment_provenance


def enrich_selected_template_with_details(
    selected_template_id: str,
    library_data: Optional[Dict[str, Any]],
    germline_numberings: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    ：
    - template_sequence（FR-only  V-domain）
    - diff_vs_parent_scaffold（）
    - diff_vs_natural_germline_consensus（）
    - functional_explanations（FR2 hallmark ）
    
    Args:
        selected_template_id: ID
        library_data: 
        germline_numberings: germline（）
    
    Returns:
        
    """
    details = {
        "template_sequence": None,
        "diff_vs_parent_scaffold": [],
        "diff_vs_natural_germline_consensus": [],
        "functional_explanations": [],
    }
    
    # 
    template_entry = None
    if library_data:
        if isinstance(library_data, list):
            template_entry = next(
                (e for e in library_data if (e.get("id") or e.get("template_id")) == selected_template_id),
                None
            )
        elif isinstance(library_data, dict):
            entries = library_data.get("entries", []) or library_data.get("templates", [])
            template_entry = next(
                (e for e in entries if (e.get("id") or e.get("template_id")) == selected_template_id),
                None
            )
    
    if not template_entry:
        return details
    
    # 1.  template_sequence
    consensus = template_entry.get("consensus", {})
    framework_full = consensus.get("framework_full") or consensus.get("framework_full")
    if framework_full:
        details["template_sequence"] = {
            "framework_full": framework_full,
            "fr1": consensus.get("fr1", ""),
            "fr2": consensus.get("fr2", ""),
            "fr3": consensus.get("fr3", ""),
            "fr4": consensus.get("fr4", ""),
        }
    
    # 2.  SAFE  mutations
    safe_plan = template_entry.get("safe_plan", "")
    mutations = template_entry.get("mutations", {})
    parent_scaffold_id = template_entry.get("source_scaffold") or template_entry.get("parent_scaffold")
    
    #  SAFE_PLAN_DEFINITIONS （ mutations ）
    expected_mutations = {}
    if safe_plan in SAFE_PLAN_DEFINITIONS:
        plan_def = SAFE_PLAN_DEFINITIONS[safe_plan]
        expected_mutations = plan_def.get("mutations", {})
    
    #  mutations  mutations（ mutations ）
    all_mutations = expected_mutations.copy()
    for pos_key, mutation_info in mutations.items():
        if isinstance(pos_key, str) and pos_key.startswith("pos_"):
            pos_num = int(pos_key.replace("pos_", ""))
        else:
            try:
                pos_num = int(pos_key)
            except (ValueError, TypeError):
                continue
        all_mutations[pos_num] = mutation_info
    
    # 3.  diff_vs_parent_scaffold
    #  SAFE_PLAN_DEFINITIONS 
    if safe_plan in SAFE_PLAN_DEFINITIONS and selected_template_id in (germline_numberings or {}):
        template_numbering = germline_numberings[selected_template_id]
        boundaries = template_numbering.get("boundaries", {})
        positions = template_numbering.get("positions", [])
        
        # 
        pos_to_aa = {}
        for pos_data in positions:
            pos = pos_data.get("pos")
            aa = pos_data.get("aa", "")
            if pos:
                try:
                    pos_int = int(pos)
                    pos_to_aa[pos_int] = aa
                except (ValueError, TypeError):
                    continue
        
        #  SAFE_PLAN_DEFINITIONS 
        plan_def = SAFE_PLAN_DEFINITIONS[safe_plan]
        expected_mutations = plan_def.get("mutations", {})
        
        # ：，
        for pos_num, expected_aa in expected_mutations.items():
            actual_aa = pos_to_aa.get(pos_num)
            
            if actual_aa and actual_aa != expected_aa:
                # ，，
                # ， parent scaffold  actual_aa，SAFE  expected_aa
                #  expected_aa， actual_aa -> expected_aa
                # ， mutations  original
                original = None
                modified = expected_aa
                
                #  mutations  original
                for pos_key, mut_info in mutations.items():
                    if isinstance(pos_key, str) and pos_key.startswith("pos_"):
                        if int(pos_key.replace("pos_", "")) == pos_num:
                            if isinstance(mut_info, dict):
                                original = mut_info.get("original")
                                modified = mut_info.get("modified", expected_aa)
                            break
                
                #  mutations ， parent 
                #  SAFE ，，
                # ，： expected_aa，
                # 。：
                #  actual_aa == expected_aa，， original
                if actual_aa == expected_aa:
                    # ， original（ natural ）
                    if pos_num in HALLMARK_FUNCTIONAL_EXPLANATIONS:
                        typical_natural = HALLMARK_FUNCTIONAL_EXPLANATIONS[pos_num].get("typical_natural", "")
                        #  "L, V, I ()"  original
                        original = typical_natural.split("(")[0].strip().split(",")[0].strip() if typical_natural else "?"
                    else:
                        original = "?"
                    modified = actual_aa
                else:
                    # ，
                    original = actual_aa
                    modified = expected_aa
            elif actual_aa == expected_aa:
                # ， original
                if pos_num in HALLMARK_FUNCTIONAL_EXPLANATIONS:
                    typical_natural = HALLMARK_FUNCTIONAL_EXPLANATIONS[pos_num].get("typical_natural", "")
                    original = typical_natural.split("(")[0].strip().split(",")[0].strip() if typical_natural else "?"
                else:
                    original = "?"
                modified = actual_aa
            else:
                continue
            
            if original and modified:
                # 
                region = "FR2"  # ， SAFE  FR2
                if boundaries:
                    for reg_name, (start, end) in boundaries.items():
                        if start <= pos_num <= end:
                            region = reg_name
                            break
                
                details["diff_vs_parent_scaffold"].append({
                    "pos": pos_num,
                    "from": original,
                    "to": modified,
                    "region": region,
                })
                
                # （ FR2 hallmark ）
                if pos_num in HALLMARK_FUNCTIONAL_EXPLANATIONS:
                    explanation = HALLMARK_FUNCTIONAL_EXPLANATIONS[pos_num].copy()
                    explanation["mutation"] = f"{original}→{modified}"
                    details["functional_explanations"].append(explanation)
    
    # 4. diff_vs_natural_germline_consensus（）
    natural_germline_sources = (
        template_entry.get("natural_germline_sources", []) or
        template_entry.get("germline_sources", []) or
        []
    )
    
    if natural_germline_sources:
        details["diff_vs_natural_germline_consensus"] = {
            "natural_germline_sources": natural_germline_sources,
            "note": "Natural germline consensusnatural_germline_sources，natural germline。",
        }
    
    return details


def step6_rank_and_select_best_template_for_safe_plan(
    candidates: List[Dict[str, Any]],
    safe_plan: str,
    objective: str = "maximize_framework_identity",
    library_data: Optional[Dict[str, Any]] = None,
    germline_numberings: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Step 6： SAFE 
    
    Args:
        candidates:  SAFE 
        safe_plan: SAFE （'A', 'B', 'C'）
        objective: 
        library_data: ，（ parent_scaffold, natural_germline_sources）
    
    Returns:
         SAFE 
    """
    # framework_identity
    sorted_candidates = sorted(
        candidates,
        key=lambda x: (
            x["framework_identity"],
            x["region_counts"]["FR2"]["match"],
            x["region_counts"]["FR3"]["match"],
        ),
        reverse=True,
    )
    
    # ranked_candidates（，10）
    ranked_candidates = []
    for rank, cand in enumerate(sorted_candidates, 1):
        ranked_candidates.append({
            "template_id": cand["template_id"],
            "rank": rank,
            "framework_identity": round(cand["framework_identity"], 4),
            "region_counts": cand["region_counts"],
        })
    
    # 
    if not sorted_candidates:
        raise ValueError(f"Step 6 () ：SAFE_{safe_plan} ")
    
    selected = sorted_candidates[0]
    
    #  library_data 
    parent_scaffold = None
    natural_germline_sources = []
    
    if library_data:
        # 
        template_entry = None
        if isinstance(library_data, list):
            template_entry = next(
                (e for e in library_data if (e.get("id") or e.get("template_id")) == selected["template_id"]),
                None
            )
        elif isinstance(library_data, dict):
            entries = library_data.get("entries", []) or library_data.get("templates", [])
            template_entry = next(
                (e for e in entries if (e.get("id") or e.get("template_id")) == selected["template_id"]),
                None
            )
        
        if template_entry:
            parent_scaffold = (
                template_entry.get("source_scaffold") or
                template_entry.get("parent_scaffold") or
                template_entry.get("scaffold_id")
            )
            natural_germline_sources = (
                template_entry.get("natural_germline_sources", []) or
                template_entry.get("germline_sources", []) or
                []
            )
    
    # 
    template_details = enrich_selected_template_with_details(
        selected_template_id=selected["template_id"],
        library_data=library_data,
        germline_numberings=germline_numberings,
    ) if germline_numberings else {}
    
    #  SAFE 
    result = {
        "candidate_count": len(candidates),
        "alignment_provenance": {
            "scheme": "imgt",
            "method": "anarcii",
            "mask_regions": ["CDR1", "CDR2", "CDR3"],
        },
        "ranked_candidates": ranked_candidates,
        "selected": {
            "template_id": selected["template_id"],
            "rank": 1,
            "framework_identity": round(selected["framework_identity"], 4),
            "parent_scaffold": parent_scaffold,
            "natural_germline_sources": natural_germline_sources,
            **template_details,  # 
        },
    }
    
    return result


def step6_rank_and_select_best_template(
    candidates: List[Dict[str, Any]],
    objective: str = "maximize_framework_identity",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Step 6：（，）
    
    ： step6_parallel_safe_paths_selection
    
    Args:
        candidates: 
        objective: 
    
    Returns:
        (germline_selection_proof, germline_selected)
    """
    # framework_identity
    sorted_candidates = sorted(
        candidates,
        key=lambda x: (
            x["framework_identity"],
            x["region_counts"]["FR2"]["match"],
            x["region_counts"]["FR3"]["match"],
        ),
        reverse=True,
    )
    
    # ranked_top10
    ranked_top10 = []
    for rank, cand in enumerate(sorted_candidates[:10], 1):
        ranked_top10.append({
            "template_id": cand["template_id"],
            "rank": rank,
            "framework_identity": cand["framework_identity"],
        })
    
    # 
    if not sorted_candidates:
        raise ValueError("Step 6 () ：")
    
    selected = sorted_candidates[0]
    selected_dict = {
        "template_id": selected["template_id"],
        "rank": 1,
        "framework_identity": selected["framework_identity"],
    }
    
    # selection_proof
    selection_proof = {
        "objective": objective,
        "score_source_path": "germline_candidates[].framework_identity",
        "tie_breakers": [
            "germline_candidates[].region_counts.FR2.match",
            "germline_candidates[].region_counts.FR3.match",
        ],
        "eligible_candidate_count": len(candidates),
        "ranked_top10": ranked_top10,
        "selected": selected_dict,
        "consistency_checks": {
            "selected_in_ranked_top10": selected_dict["template_id"] in [c["template_id"] for c in ranked_top10],
        },
    }
    
    # germline
    germline_dict = {
        "selected": {
            "id": selected["template_id"],
            "framework_identity": selected["framework_identity"],
            "reason": f"framework_identity ({selected['framework_identity']:.4f})",
        },
        "top_candidates": [
            {
                "id": cand["template_id"],
                "framework_identity": cand["framework_identity"],
            }
            for cand in sorted_candidates[:10]
        ],
    }
    
    # Fail
    if not selection_proof["consistency_checks"]["selected_in_ranked_top10"]:
        raise ValueError(
            "Step 6 () ：selectedTop10"
        )
    
    if selection_proof["eligible_candidate_count"] == 0:
        raise ValueError("Step 6 () ：eligible_candidate_count=0")
    
    return selection_proof, germline_dict


def step6_parallel_safe_paths_selection(
    all_candidates: List[Dict[str, Any]],
    library_data: Optional[Dict[str, Any]] = None,
    germline_numberings: Optional[Dict[str, Dict[str, Any]]] = None,
    objective: str = "maximize_framework_identity",
) -> Dict[str, Any]:
    """
    Step 6： A/B/C  SAFE ，
    
    Args:
        all_candidates: （）
        library_data: ，
        objective: 
    
    Returns:
        germline_selection ， SAFE_A/SAFE_B/SAFE_C 
    """
    #  SAFE 
    candidates_by_plan = {"A": [], "B": [], "C": []}
    
    for candidate in all_candidates:
        template_id = candidate.get("template_id", "")
        safe_plan = extract_safe_plan_from_template_id(template_id)
        if safe_plan in candidates_by_plan:
            candidates_by_plan[safe_plan].append(candidate)
    
    #  SAFE 
    germline_selection = {}
    
    for safe_plan in ["A", "B", "C"]:
        plan_candidates = candidates_by_plan[safe_plan]
        
        if not plan_candidates:
            # ，
            germline_selection[f"SAFE_{safe_plan}"] = {
                "candidate_count": 0,
                "error": "No candidates found for this SAFE plan",
            }
            continue
        
        # 
        plan_result = step6_rank_and_select_best_template_for_safe_plan(
            candidates=plan_candidates,
            safe_plan=safe_plan,
            objective=objective,
            library_data=library_data,
            germline_numberings=germline_numberings,
        )
        
        germline_selection[f"SAFE_{safe_plan}"] = plan_result
    
    # ：（）
    for plan in ["A", "B", "C"]:
        if f"SAFE_{plan}" not in germline_selection:
            raise ValueError(f"Step 6 () ：SAFE_{plan} ")
    
    # ：
    has_selected = any(
        plan_result.get("selected", {}).get("template_id")
        for plan_result in germline_selection.values()
        if "selected" in plan_result
    )
    
    if not has_selected:
        raise ValueError("Step 6 () ： SAFE ")
    
    return germline_selection


def build_safe_strategies_comparison(
    germline_selection: Dict[str, Any],
    germline_numberings: Dict[str, Dict[str, Any]],
    library_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
     SAFE 
    
    Args:
        germline_selection: germline_selection 
        germline_numberings: germline 
        library_data: 
    
    Returns:
        safe_strategies ， fr2_mutations
    """
    safe_strategies = {}
    
    for plan in ["A", "B", "C"]:
        plan_key = f"SAFE_{plan}"
        plan_result = germline_selection.get(plan_key, {})
        selected = plan_result.get("selected", {})
        
        if not selected or not selected.get("template_id"):
            continue
        
        template_id = selected.get("template_id")
        
        # 
        plan_def = SAFE_PLAN_DEFINITIONS.get(plan, {})
        expected_mutations = plan_def.get("mutations", {})
        
        # 
        template_numbering = germline_numberings.get(template_id, {})
        positions = template_numbering.get("positions", [])
        boundaries = template_numbering.get("boundaries", {})
        
        # 
        pos_to_aa = {}
        for pos_data in positions:
            pos = pos_data.get("pos")
            aa = pos_data.get("aa", "")
            if pos:
                try:
                    pos_int = int(pos)
                    pos_to_aa[pos_int] = aa
                except (ValueError, TypeError):
                    continue
        
        #  fr2_mutations 
        fr2_mutations = []
        
        for pos_num, expected_aa in expected_mutations.items():
            actual_aa = pos_to_aa.get(pos_num)
            
            # ，（）
            if actual_aa or pos_num in expected_mutations:
                #  original（ natural  mutations ）
                original = None
                
                #  original
                if library_data:
                    template_entry = None
                    if isinstance(library_data, list):
                        template_entry = next(
                            (e for e in library_data if (e.get("id") or e.get("template_id")) == template_id),
                            None
                        )
                    elif isinstance(library_data, dict):
                        entries = library_data.get("entries", []) or library_data.get("templates", [])
                        template_entry = next(
                            (e for e in entries if (e.get("id") or e.get("template_id")) == template_id),
                            None
                        )
                    
                    if template_entry:
                        mutations = template_entry.get("mutations", {})
                        pos_key = f"pos_{pos_num}"
                        if pos_key in mutations:
                            mut_info = mutations[pos_key]
                            if isinstance(mut_info, dict):
                                original = mut_info.get("original")
                
                #  original，
                if not original:
                    if pos_num in HALLMARK_FUNCTIONAL_EXPLANATIONS:
                        typical_natural = HALLMARK_FUNCTIONAL_EXPLANATIONS[pos_num].get("typical_natural", "")
                        original = typical_natural.split("(")[0].strip().split(",")[0].strip() if typical_natural else "?"
                    else:
                        original = "?"
                
                # 
                meaning = ""
                if pos_num in HALLMARK_FUNCTIONAL_EXPLANATIONS:
                    exp = HALLMARK_FUNCTIONAL_EXPLANATIONS[pos_num]
                    meaning = f"{exp.get('functional_impact', '')} {exp.get('vhh_significance', '')}"
                
                # （ "Y/S"）
                to_aa = expected_aa
                if "/" in expected_aa:
                    #  "Y/S"，
                    to_aa = actual_aa
                
                fr2_mutations.append({
                    "imgt_pos": pos_num,
                    "from": original,
                    "to": to_aa,
                    "meaning": meaning.strip(),
                })
        
        safe_strategies[plan_key] = {
            "template_id": template_id,
            "fr2_mutations": fr2_mutations,
        }
    
    return safe_strategies


def validate_all_provenances(json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
     Validator：provenance
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    # 1. validate_input_provenance
    if "input_provenance" not in json_data:
        errors.append(" input_provenance")
    else:
        ip = json_data["input_provenance"]
        if not ip.get("sha256"):
            errors.append("input_provenance.sha256 ")
        if not ip.get("aa_alphabet_check", {}).get("valid"):
            errors.append("input_provenance.aa_alphabet_check.valid != true")
    
    # 2. validate_segmentation_provenance
    if "segmentation_provenance" not in json_data:
        errors.append(" segmentation_provenance")
    else:
        sp = json_data["segmentation_provenance"]
        if sp.get("method") != "anarcii" and not sp.get("method", "").startswith("fallback:"):
            errors.append(f"segmentation_provenance.method = '{sp.get('method')}' != 'anarcii'")
    
    # 3. validate_germline_library_provenance
    if "germline_library_provenance" not in json_data:
        errors.append(" germline_library_provenance")
    else:
        glp = json_data["germline_library_provenance"]
        if not glp.get("sha256"):
            errors.append("germline_library_provenance.sha256 ")
        if glp.get("entry_count", 0) == 0:
            errors.append("germline_library_provenance.entry_count == 0")
    
    # 4. validate_germline_numbering_provenance
    if "germline_numbering" not in json_data:
        errors.append(" germline_numbering")
    else:
        gn = json_data["germline_numbering"]
        np = gn.get("numbering_provenance", {})
        if np.get("method") != "anarcii" and not np.get("method", "").startswith("fallback:"):
            errors.append(f"germline_numbering.numbering_provenance.method = '{np.get('method')}' != 'anarcii'")
        if not gn.get("numberings"):
            errors.append("germline_numbering.numberings ")
    
    # 5. validate_alignment_provenance
    if "germline_alignment_provenance" not in json_data:
        errors.append(" germline_alignment_provenance")
    if "germline_candidates" not in json_data:
        errors.append(" germline_candidates")
    else:
        if len(json_data["germline_candidates"]) == 0:
            errors.append("germline_candidates ")
    
    # 6. validate_selection_proof
    if "germline_selection_proof" not in json_data:
        errors.append(" germline_selection_proof")
    else:
        gsp = json_data["germline_selection_proof"]
        if gsp.get("eligible_candidate_count", 0) == 0:
            errors.append("germline_selection_proof.eligible_candidate_count == 0")
        if not gsp.get("consistency_checks", {}).get("selected_in_ranked_top10"):
            errors.append("germline_selection_proof.consistency_checks.selected_in_ranked_top10 != true")
    
    return len(errors) == 0, errors


def render_md_from_json(json_data: Dict[str, Any]) -> str:
    """
    JSONMD（JSON，）
    """
    lines = []
    
    # 
    lines.append("# EGFR VHH ")
    lines.append("")
    lines.append(f"****: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # （JSON）
    input_prov = json_data.get("input_provenance", {})
    lines.append("## 1. ")
    lines.append("")
    lines.append(f"- **ID**: {input_prov.get('sequence_id', 'N/A')}")
    lines.append(f"- ****: {input_prov.get('length', 0)} aa")
    lines.append(f"- ****: {input_prov.get('source_file', 'N/A')}")
    lines.append(f"- **SHA256**: `{input_prov.get('sha256', 'N/A')[:16]}...`")
    lines.append("")
    
    # IMGT（JSON）
    seg = json_data.get("segmentation", {})
    seg_prov = json_data.get("segmentation_provenance", {})
    lines.append("## 2. IMGT ")
    lines.append("")
    lines.append(f"- ****: {seg_prov.get('method', 'N/A')}")
    lines.append(f"- ****: {seg.get('scheme', 'N/A')}")
    lines.append("")
    lines.append("### ")
    boundaries = seg.get("boundaries", {})
    for region, bounds in boundaries.items():
        lines.append(f"- **{region}**: {bounds[0]}-{bounds[1]}")
    lines.append("")
    
    # Germline（JSON）
    glp = json_data.get("germline_library_provenance", {})
    lines.append("## 3. Germline ")
    lines.append("")
    lines.append(f"- ****: {glp.get('library_name', 'N/A')}")
    lines.append(f"- ****: {glp.get('version', 'N/A')}")
    lines.append(f"- ****: {glp.get('entry_count', 0)}")
    lines.append(f"- **SHA256**: `{glp.get('sha256', 'N/A')[:16]}...`")
    lines.append("")
    
    # Germline （JSON）
    germline_selection = json_data.get("germline_selection", {})
    gsp = json_data.get("germline_selection_proof", {})
    safe_plan_definitions = json_data.get("safe_plan_definitions", {})
    
    lines.append("## 4. Germline （A/B/C ）")
    lines.append("")
    
    # ========== 、（） ==========
    lines.append("### ")
    lines.append("")
    lines.append("**SAFE_A / SAFE_B / SAFE_C ， VH3  FR2 。**")
    lines.append("")
    lines.append(" FR2  hallmark ，CDR ， FR 。")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    #  SAFE 
    if safe_plan_definitions:
        lines.append("### SAFE ")
        lines.append("")
        lines.append("|  |  |  |  |")
        lines.append("|------|------|----------|----------|")
        for plan_key in ["A", "B", "C"]:
            plan_def = safe_plan_definitions.get(plan_key, {})
            if plan_def:
                name = plan_def.get("name", "")
                description = plan_def.get("description", "")
                functional_meaning = plan_def.get("functional_meaning", "")
                lines.append(f"| **{plan_key}** | {name} | {description} | {functional_meaning} |")
        lines.append("")
    
    #  SAFE 
    lines.append("###  SAFE ")
    lines.append("")
    lines.append("|  | ID | Framework Identity | Parent Scaffold |  |")
    lines.append("|------|--------|-------------------|----------------|--------|")
    
    for plan in ["A", "B", "C"]:
        plan_key = f"SAFE_{plan}"
        plan_result = germline_selection.get(plan_key, {})
        selected = plan_result.get("selected", {})
        
        if selected and selected.get("template_id"):
            template_id = selected.get("template_id", "N/A")
            framework_identity = selected.get("framework_identity", 0.0)
            parent_scaffold = selected.get("parent_scaffold", "N/A")
            candidate_count = plan_result.get("candidate_count", 0)
            
            lines.append(
                f"| **SAFE_{plan}** | {template_id} | {framework_identity:.4f} | "
                f"{parent_scaffold} | {candidate_count} |"
            )
        else:
            lines.append(f"| **SAFE_{plan}** | - | - | - | 0 |")
    
    lines.append("")
    
    # ========== 、 ==========
    safe_strategies = json_data.get("safe_strategies", {})
    if safe_strategies:
        lines.append("### （ IMGT ）")
        lines.append("")
        lines.append("， IMGT ：")
        lines.append("")
        
        for plan in ["A", "B", "C"]:
            plan_key = f"SAFE_{plan}"
            strategy = safe_strategies.get(plan_key, {})
            
            if strategy and strategy.get("fr2_mutations"):
                template_id = strategy.get("template_id", "N/A")
                mutations = strategy.get("fr2_mutations", [])
                
                lines.append(f"#### SAFE_{plan} ({template_id})")
                lines.append("")
                lines.append("| IMGT  |  |  |  |")
                lines.append("|-----------|----|----|----------|")
                
                for mut in mutations:
                    imgt_pos = mut.get("imgt_pos", "?")
                    from_aa = mut.get("from", "?")
                    to_aa = mut.get("to", "?")
                    meaning = mut.get("meaning", "")
                    #  meaning
                    if len(meaning) > 80:
                        meaning = meaning[:77] + "..."
                    lines.append(f"| {imgt_pos} | {from_aa} | {to_aa} | {meaning} |")
                
                lines.append("")
        
        lines.append("---")
        lines.append("")
    
    # ========== 、/ ==========
    lines.append("### SAFE_A / SAFE_B / SAFE_C ")
    lines.append("")
    
    # SAFE_A
    lines.append("#### SAFE_A（）")
    lines.append("")
    lines.append("**， VH **")
    lines.append("")
    lines.append("- **FR2 ，**：")
    lines.append("  - ")
    lines.append("  -  VH ")
    lines.append("")
    lines.append("- ****：")
    lines.append("  - ''")
    lines.append("  - ")
    lines.append("")
    lines.append("- ****：")
    lines.append("  - ")
    lines.append("  - ")
    lines.append("")
    
    # SAFE_B
    lines.append("#### SAFE_B（）")
    lines.append("")
    lines.append("** hallmark  VHH **")
    lines.append("")
    lines.append("- **' VH ''VHH '**")
    lines.append("")
    lines.append("- ****：")
    lines.append("  - ")
    lines.append("  - ")
    lines.append("")
    lines.append("- ****：")
    lines.append("  -  VHH （）")
    lines.append("")
    
    # SAFE_C
    lines.append("#### SAFE_C（ VHH ）")
    lines.append("")
    lines.append("**FR2 hallmark  VHH **")
    lines.append("")
    lines.append("- ****：")
    lines.append("  - ")
    lines.append("  - ")
    lines.append("  -  VH ")
    lines.append("")
    lines.append("- ****：")
    lines.append("  - ")
    lines.append("")
    lines.append("- ****：")
    lines.append("  - /")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    
    #  SAFE_A 
    safe_a_result = germline_selection.get("SAFE_A", {})
    safe_a_selected = safe_a_result.get("selected", {})
    
    if safe_a_selected and safe_a_selected.get("template_id"):
        lines.append("### ：SAFE_A（）")
        lines.append("")
        lines.append(f"- **ID**: {safe_a_selected.get('template_id', 'N/A')}")
        lines.append(f"- ****: {safe_a_selected.get('rank', 'N/A')}")
        lines.append(f"- **Framework Identity**: {safe_a_selected.get('framework_identity', 0.0):.4f}")
        
        parent_scaffold = safe_a_selected.get("parent_scaffold")
        if parent_scaffold:
            lines.append(f"- **Parent Scaffold**: {parent_scaffold}")
        
        natural_germline_sources = safe_a_selected.get("natural_germline_sources", [])
        if natural_germline_sources:
            lines.append(f"- **Natural Germline Sources**: {', '.join(natural_germline_sources)}")
        
        lines.append("")
        
        # SAFE_A  Top （ ranked_candidates ）
        ranked_candidates = safe_a_result.get("ranked_candidates", [])
        if ranked_candidates:
            lines.append("#### SAFE_A （10）")
            lines.append("")
            lines.append("|  | ID | Framework Identity |")
            lines.append("|------|--------|-------------------|")
            for item in ranked_candidates[:10]:
                lines.append(
                    f"| {item.get('rank', 'N/A')} | {item.get('template_id', 'N/A')} | "
                    f"{item.get('framework_identity', 0.0):.4f} |"
                )
            lines.append("")
        
        # （ region_counts ）
        if ranked_candidates:
            first_candidate = ranked_candidates[0]
            region_counts = first_candidate.get("region_counts", {})
            if region_counts:
                lines.append("#### ")
                lines.append("")
                lines.append("|  | Match | Total | Identity |")
                lines.append("|------|-------|-------|----------|")
                for region in ["FR1", "FR2", "FR3", "FR4"]:
                    region_data = region_counts.get(region, {})
                    match = region_data.get("match", 0)
                    total = region_data.get("total", 0)
                    identity = match / total if total > 0 else 0.0
                    lines.append(f"| {region} | {match} | {total} | {identity:.4f} |")
                lines.append("")
        
        # 
        template_sequence = safe_a_selected.get("template_sequence")
        if template_sequence:
            lines.append("#### （FR-only）")
            lines.append("")
            if template_sequence.get("framework_full"):
                lines.append(f"- ****: `{template_sequence['framework_full']}`")
            if template_sequence.get("fr1"):
                lines.append(f"- **FR1**: `{template_sequence['fr1']}`")
            if template_sequence.get("fr2"):
                lines.append(f"- **FR2**: `{template_sequence['fr2']}`")
            if template_sequence.get("fr3"):
                lines.append(f"- **FR3**: `{template_sequence['fr3']}`")
            if template_sequence.get("fr4"):
                lines.append(f"- **FR4**: `{template_sequence['fr4']}`")
            lines.append("")
        
        #  Parent Scaffold 
        diff_vs_parent = safe_a_selected.get("diff_vs_parent_scaffold", [])
        if diff_vs_parent:
            lines.append("####  Parent Scaffold ")
            lines.append("")
            lines.append("|  |  |  |  |")
            lines.append("|------|----|----|------|")
            for diff in diff_vs_parent:
                lines.append(f"| {diff.get('pos')} | {diff.get('from')} | {diff.get('to')} | {diff.get('region')} |")
            lines.append("")
        
        # 
        functional_explanations = safe_a_selected.get("functional_explanations", [])
        if functional_explanations:
            lines.append("#### FR2 Hallmark ")
            lines.append("")
            for exp in functional_explanations:
                lines.append(f"**{exp.get('name', '')}** (: {exp.get('mutation', '')})")
                lines.append("")
                lines.append(f"- ****: {exp.get('typical_natural', '')}")
                lines.append(f"- **SAFE **: {exp.get('safe_mutation', '')}")
                lines.append(f"- ****: {exp.get('functional_impact', '')}")
                lines.append(f"- **VHH **: {exp.get('vhh_significance', '')}")
                lines.append("")
        
        #  Natural Germline Consensus 
        diff_vs_natural = safe_a_selected.get("diff_vs_natural_germline_consensus", {})
        if diff_vs_natural:
            lines.append("####  Natural Germline Consensus ")
            lines.append("")
            natural_sources = diff_vs_natural.get("natural_germline_sources", [])
            if natural_sources:
                lines.append(f"- **Natural Germline Sources**: {', '.join(natural_sources)}")
            note = diff_vs_natural.get("note", "")
            if note:
                lines.append(f"- ****: {note}")
            lines.append("")
    else:
        lines.append("### ⚠️ ：SAFE_A（）")
        lines.append("")
    
    # ========== 、 ==========
    lines.append("###  SAFE_A ？")
    lines.append("")
    lines.append(
        "** SAFE_A ，"
        "SAFE_B  SAFE_C ，；"
        "，。**"
    )
    lines.append("")
    lines.append("****：")
    lines.append("- ✅ ")
    lines.append("- ✅ （''）")
    lines.append("- ✅  SAFE_A ")
    lines.append("- ✅ ")
    lines.append("")
    
    # ， germline_selection_proof（）
    if gsp and not safe_a_selected:
        selected = gsp.get("selected", {})
        if selected and selected.get("template_id"):
            lines.append("### （）")
            lines.append("")
            lines.append(f"- **ID**: {selected.get('template_id', 'N/A')}")
            lines.append(f"- ****: {selected.get('rank', 'N/A')}")
            lines.append(f"- **Framework Identity**: {selected.get('framework_identity', 0.0):.4f}")
            lines.append("")
            
            # Top 10 （JSON）
            lines.append("#### Top 10 ")
            lines.append("")
            lines.append("|  | ID | Framework Identity |")
            lines.append("|------|--------|-------------------|")
            for item in gsp.get("ranked_top10", []):
                lines.append(
                    f"| {item.get('rank', 'N/A')} | {item.get('template_id', 'N/A')} | "
                    f"{item.get('framework_identity', 0.0):.4f} |"
                )
            lines.append("")
    
    return "\n".join(lines)


def validate_md_matches_json(md_content: str, json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    MDJSON
    """
    errors = []
    
    # 
    gsp = json_data.get("germline_selection_proof", {})
    selected = gsp.get("selected", {})
    
    # selected template_id
    selected_id = selected.get("template_id", "")
    if selected_id and selected_id not in md_content:
        errors.append(f"MDselected template_id: {selected_id}")
    
    # framework_identity
    framework_identity = selected.get("framework_identity", 0.0)
    if f"{framework_identity:.4f}" not in md_content:
        errors.append(f"MDframework_identity: {framework_identity:.4f}")
    
    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="EGFR VHH ")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="FASTA"
    )
    parser.add_argument(
        "--germline",
        type=Path,
        required=True,
        help="Germline"
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help=""
    )
    
    args = parser.parse_args()
    
    # 
    args.out.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("EGFR VHH （Evidence-first, Fail-fast）")
    print("=" * 80)
    print()
    
    json_data = {}
    
    try:
        # Step 1: 
        print("[Step 1/6] ...")
        sequence, input_provenance = step1_read_and_normalize_input(args.input)
        json_data["input_provenance"] = input_provenance
        json_data["input_sequence"] = sequence
        print(f"  ✅ : {len(sequence)} aa")
        print()
        
        # Step 2: IMGT
        print("[Step 2/6] IMGT（ANARCII）...")
        segmentation, segmentation_provenance = step2_segment_target_sequence(sequence)
        json_data["segmentation"] = segmentation
        json_data["segmentation_provenance"] = segmentation_provenance
        print(f"  ✅ : {segmentation_provenance.get('method')}")
        print()
        
        # Step 3: Germline
        print("[Step 3/6] Germline...")
        library_data, germline_library_provenance = step3_load_germline_library(args.germline)
        json_data["germline_library_provenance"] = germline_library_provenance
        print(f"  ✅ : {germline_library_provenance.get('entry_count')}")
        print()
        
        # Step 4:  - IMGT（）
        print("[Step 4/6] ：IMGT...")
        eligible_template_ids, excluded_templates, fr_only_templates = filter_imgt_compatible_templates_before_numbering(
            library_data=library_data,
            min_length=MIN_IMGT_VH_LENGTH,
        )
        json_data["germline_filtering"] = {
            "min_imgt_vh_length": MIN_IMGT_VH_LENGTH,
            "eligible_count": len(eligible_template_ids),
            "excluded_count": len(excluded_templates),
            "excluded_templates": excluded_templates,
        }
        print(f"  ✅ IMGT: {len(eligible_template_ids)}")
        print(f"  ⚠️  : {len(excluded_templates)} ( < {MIN_IMGT_VH_LENGTH}aa)")
        
        # fr_only_templates
        if fr_only_templates:
            fr_only_path = args.out / "fr_only_templates.json"
            with open(fr_only_path, "w", encoding="utf-8") as f:
                json.dump(fr_only_templates, f, indent=2, ensure_ascii=False)
            print(f"  📁 FR-only: {fr_only_path}")
        print()
        
        # Step 4.5: GermlineIMGT（）
        print("[Step 4.5/6] GermlineIMGT（ANARCII，）...")
        # IMGT
        germline_numbering = step4_number_germline_templates(library_data, eligible_template_ids)
        json_data["germline_numbering"] = germline_numbering
        print(f"  ✅ : {len(germline_numbering.get('numberings', {}))}")
        print()
        
        # Step 5: vs Germline（IMGT）
        print("[Step 5/6]  vs Germline IMGT（）...")
        # numbering（）
        from core.segmentation.anarcii_adapter import run_anarcii_imgt
        _, full_numbering_rows, _ = run_anarcii_imgt(sequence, species="camelid", chain="H")
        
        # 
        full_numbering = []
        for row in full_numbering_rows:
            full_numbering.append({
                "pos": str(row.get("pos", "")),
                "aa": row.get("aa", ""),
            })
        
        # IMGT（SAFE，）
        all_candidates, alignment_provenance = step5_align_target_vs_germlines(
            target_numbering_rows=full_numbering,
            target_boundaries=segmentation.get("boundaries", {}),
            germline_numberings=germline_numbering.get("numberings", {}),
            safe_plan_filter=None,  # ，
        )
        json_data["germline_candidates"] = all_candidates
        json_data["germline_alignment_provenance"] = alignment_provenance
        print(f"  ✅ : {len(all_candidates)}")
        print()
        
        # Step 6:  A/B/C  SAFE ，
        print("[Step 6/6]  A/B/C  SAFE ...")
        germline_selection = step6_parallel_safe_paths_selection(
            all_candidates=all_candidates,
            library_data=library_data,
            germline_numberings=germline_numbering.get("numberings", {}),
            objective="maximize_framework_identity",
        )
        json_data["germline_selection"] = germline_selection
        
        #  safe_plan_definitions  JSON
        json_data["safe_plan_definitions"] = SAFE_PLAN_DEFINITIONS
        
        #  safe_strategies （）
        safe_strategies = build_safe_strategies_comparison(
            germline_selection=germline_selection,
            germline_numberings=germline_numbering.get("numberings", {}),
            library_data=library_data,
        )
        json_data["safe_strategies"] = safe_strategies
        
        #  safe_strategies （）
        safe_strategies = build_safe_strategies_comparison(
            germline_selection=germline_selection,
            germline_numberings=germline_numbering.get("numberings", {}),
            library_data=library_data,
        )
        json_data["safe_strategies"] = safe_strategies
        
        # 
        for plan in ["A", "B", "C"]:
            plan_key = f"SAFE_{plan}"
            plan_result = germline_selection.get(plan_key, {})
            selected = plan_result.get("selected", {})
            if selected and selected.get("template_id"):
                print(f"  ✅ SAFE_{plan} : {selected['template_id']}")
                print(f"     Framework Identity: {selected['framework_identity']:.4f}")
                print(f"     : {plan_result.get('candidate_count', 0)}")
            else:
                print(f"  ⚠️  SAFE_{plan}: ")
        print()
        
        # ， germline_selection_proof  germline 
        #  SAFE_A 
        safe_a_result = germline_selection.get("SAFE_A", {})
        safe_a_selected = safe_a_result.get("selected", {})
        
        if safe_a_selected and safe_a_selected.get("template_id"):
            #  selection_proof （）
            old_selection_proof = {
                "objective": "maximize_framework_identity",
                "score_source_path": "germline_candidates[].framework_identity",
                "tie_breakers": [
                    "germline_candidates[].region_counts.FR2.match",
                    "germline_candidates[].region_counts.FR3.match",
                ],
                "eligible_candidate_count": safe_a_result.get("candidate_count", 0),
                "ranked_top10": [
                    {
                        "template_id": cand.get("template_id"),
                        "rank": cand.get("rank"),
                        "framework_identity": cand.get("framework_identity"),
                    }
                    for cand in safe_a_result.get("ranked_candidates", [])[:10]
                ],
                "selected": {
                    "template_id": safe_a_selected.get("template_id"),
                    "rank": safe_a_selected.get("rank", 1),
                    "framework_identity": safe_a_selected.get("framework_identity", 0.0),
                },
                "consistency_checks": {
                    "selected_in_ranked_top10": True,
                },
            }
            
            old_germline_dict = {
                "selected": {
                    "id": safe_a_selected.get("template_id"),
                    "framework_identity": safe_a_selected.get("framework_identity", 0.0),
                    "reason": f"framework_identity ({safe_a_selected.get('framework_identity', 0.0):.4f})",
                },
                "top_candidates": [
                    {
                        "id": cand.get("template_id"),
                        "framework_identity": cand.get("framework_identity", 0.0),
                    }
                    for cand in safe_a_result.get("ranked_candidates", [])[:10]
                ],
            }
            
            json_data["germline_selection_proof"] = old_selection_proof
            json_data["germline"] = old_germline_dict
        
        # provenance
        print("[] provenance...")
        is_valid, errors = validate_all_provenances(json_data)
        if not is_valid:
            print("  ❌ :")
            for error in errors:
                print(f"    - {error}")
            raise ValueError("Provenance")
        print("  ✅ provenance")
        print()
        
        # JSON
        result_json_path = args.out / "result.json"
        with open(result_json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON: {result_json_path}")
        print()
        
        # MD
        print("[] JSONMD...")
        md_content = render_md_from_json(json_data)
        
        # MDJSON
        md_valid, md_errors = validate_md_matches_json(md_content, json_data)
        if not md_valid:
            print("  ❌ MDJSON:")
            for error in md_errors:
                print(f"    - {error}")
            raise ValueError("MDJSON")
        
        # MD
        report_md_path = args.out / "report.md"
        with open(report_md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"✅ MD: {report_md_path}")
        print()
        
        print("=" * 80)
        print("✅ ！")
        print("=" * 80)
        print(f"\n:")
        print(f"  - JSON: {result_json_path}")
        print(f"  - MD: {report_md_path}")
        
    except Exception as e:
        print(f"\n❌ : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

