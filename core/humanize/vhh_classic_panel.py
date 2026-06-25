"""
VHH Classic Germline FR Panel - Main Function

scaffoldVHH（）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from core.data.vhh_classic_scaffolds import (
    get_classic_scaffold,
    get_classic_j_region,
    get_all_scaffold_ids,
    get_all_j_region_ids,
    validate_scaffold_integrity,
    validate_j_region_integrity,
)
from core.humanize.mutations_rules import (
    apply_all_mutation_rules,
    MutationRecord,
)
from core.humanize.rulebook_v1 import RuleMode, get_rules_by_mode, RULEBOOK_V1
from core.numbering.dual_numbering import (
    get_dual_numbering,
    build_numbering_maps_json,
    DualNumberingError,
)
from core.numbering.imgt_anarcii import (
    imgt_number_anarcii,
    build_pos_to_aa_map,
    IMGTNumberingError,
)
from core.analysis.cdr_canonical import (
    extract_cdr_features,
    get_scaffold_canonical_profiles,
    build_canonical_compatibility,
)
from core.analysis.vhh_gate import run_vhh_gate
from core.preflight.vhh_cys_check import run_vhh_cys_preflight_check


class VHHClassicPanelError(RuntimeError):
    """VHH Classic Panel"""
    pass


def normalize_query_schema(query: Dict[str, Any]) -> Dict[str, Any]:
    """
    query schema，
    
    Args:
        query: query（）
    
    Returns:
        query
    """
    normalized = {}
    
    # segments（）
    if "segments" in query:
        segments = query["segments"]
    elif "regions" in query:
        segments = query["regions"]
    else:
        segments = {}
    
    normalized["segments"] = {
        "FR1": segments.get("FR1", segments.get("fr1", "")),
        "CDR1": segments.get("CDR1", segments.get("cdr1", "")),
        "FR2": segments.get("FR2", segments.get("fr2", "")),
        "CDR2": segments.get("CDR2", segments.get("cdr2", "")),
        "FR3": segments.get("FR3", segments.get("fr3", "")),
        "CDR3": segments.get("CDR3", segments.get("cdr3", "")),
        "FR4": segments.get("FR4", segments.get("fr4", "")),
    }
    
    # numbering_maps
    if "numbering_maps" in query:
        normalized["numbering_maps"] = query["numbering_maps"]
    elif "numbering" in query:
        # numbering，maps
        normalized["numbering_maps"] = query.get("numbering", {})
    else:
        normalized["numbering_maps"] = {}
    
    # query
    for key, value in query.items():
        if key not in ("segments", "regions", "numbering_maps", "numbering"):
            normalized[key] = value
    
    return normalized


def build_kabat_map_from_numbering(
    numbering_maps: Dict[str, Any],
    sequence: str,
) -> Dict[int, str]:
    """
    numbering_mapsKabat
    
    Args:
        numbering_maps: 
        sequence: （fallback）
    
    Returns:
        {kabat_pos: aa} （kabat_pos，）
    """
    kabat_map = {}
    
    # 1: numbering_maps
    if "kabat" in numbering_maps:
        kabat_list = numbering_maps["kabat"]
        if isinstance(kabat_list, list):
            for item in kabat_list:
                if isinstance(item, dict):
                    pos_str = item.get("pos", "")
                    aa = item.get("aa", "")
                    if pos_str and aa:
                        # （35A）
                        try:
                            pos_num = int(''.join(filter(str.isdigit, str(pos_str))))
                            kabat_map[pos_num] = aa
                        except ValueError:
                            continue
    
    # 2: residue_index_map
    if not kabat_map and "residue_index_map" in numbering_maps:
        residue_map = numbering_maps["residue_index_map"]
        for idx, info in residue_map.items():
            if isinstance(info, dict):
                kabat_label = info.get("kabat_label", "")
                aa = info.get("aa", "")
                if kabat_label and aa:
                    try:
                        pos_num = int(''.join(filter(str.isdigit, str(kabat_label))))
                        kabat_map[pos_num] = aa
                    except ValueError:
                        continue
    
    # 3: numbering_mapskabat_to_imgt，query
    if not kabat_map:
        try:
            imgt_rows, kabat_rows, mapping = get_dual_numbering(sequence)
            for row in kabat_rows:
                pos = row.get("pos")
                aa = row.get("aa", "")
                if pos is not None and aa and aa != "-":
                    try:
                        pos_num = int(pos)
                        kabat_map[pos_num] = aa
                    except (ValueError, TypeError):
                        continue
        except Exception:
            pass
    
    return kabat_map


def apply_mutations_to_sequence(
    sequence: str,
    mutations: List[MutationRecord],
    numbering_maps: Dict[str, Any],
) -> str:
    """
    
    
    ：Kabat，
    。
    
    Args:
        sequence: 
        mutations: 
        numbering_maps: 
    
    Returns:
        
    """
    if not mutations:
        return sequence
    
    # Kabat
    try:
        imgt_rows, kabat_rows, mapping = get_dual_numbering(sequence)
        
        # Kabat
        kabat_to_seq_idx = {}
        seq_pos = 0
        
        for row in kabat_rows:
            pos = row.get("pos")
            aa = row.get("aa", "")
            if pos is not None and aa and aa != "-":
                try:
                    # （）
                    pos_num = int(''.join(filter(str.isdigit, str(pos))))
                    if 0 <= seq_pos < len(sequence):
                        kabat_to_seq_idx[pos_num] = seq_pos
                        seq_pos += 1
                except (ValueError, TypeError):
                    continue
    except Exception:
        # ，numbering_maps
        kabat_to_seq_idx = {}
        
        # residue_index_map
        if "residue_index_map" in numbering_maps:
            residue_map = numbering_maps["residue_index_map"]
            for seq_idx, info in residue_map.items():
                if isinstance(info, dict):
                    kabat_label = info.get("kabat_label", "")
                    if kabat_label:
                        try:
                            pos_num = int(''.join(filter(str.isdigit, str(kabat_label))))
                            if isinstance(seq_idx, int):
                                kabat_to_seq_idx[pos_num] = seq_idx
                        except ValueError:
                            continue
    
    # 
    seq_list = list(sequence)
    applied_count = 0
    
    for mutation in mutations:
        kabat_pos = mutation.numbering.get("kabat")
        if kabat_pos is None:
            continue
        
        seq_idx = kabat_to_seq_idx.get(kabat_pos)
        if seq_idx is not None and 0 <= seq_idx < len(seq_list):
            if seq_list[seq_idx] == mutation.from_aa:
                seq_list[seq_idx] = mutation.to_aa
                applied_count += 1
    
    # ，
    if applied_count == 0:
        return sequence
    
    return "".join(seq_list)


def generate_vhh_classic_panel(
    query: Dict[str, Any],
    panel_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    VHH Classic Panel（Rulebook v1.0）
    
    Args:
        query: query，：
            - segments: {FR1, CDR1, FR2, CDR2, FR3, CDR3, FR4}
            - numbering_maps: 
        panel_config: （）
            - scaffolds: scaffold ID（4）
            - j_regions: J region ID（2）
            - mode: "mvp"  "expert"（"mvp"）
    
    Returns:
        {
            "classic_panel": [...],
            "rulebook_summary": {...},
            "pipeline_version": "v1.0",
            "timestamp": "...",
        }
    """
    """
    VHH Classic Panel
    
    Args:
        query: query，：
            - segments: {FR1, CDR1, FR2, CDR2, FR3, CDR3, FR4}
            - numbering_maps: 
        panel_config: （）
            - scaffolds: scaffold ID（4）
            - j_regions: J region ID（2）
    
    Returns:
        {
            "classic_panel": [
                {
                    "scaffold_id": "IGHV3-23*01",
                    "j_region_id": "IGHJ4",
                    "sequence_final": "...",
                    "sequence_grafted_pre_mutation": "...",
                    "mutations": [...],
                    "mutation_summary": {...},
                    "qa": {...},
                    "provenance": {...},
                },
                ...
            ],
            "pipeline_version": "v1.0",
            "timestamp": "...",
        }
    """
    # query schema
    normalized_query = normalize_query_schema(query)
    segments = normalized_query["segments"]
    numbering_maps = normalized_query.get("numbering_maps", {})
    
    # ========================================================================
    # P0 | VHH_CYS_PREFLIGHT_CHECK (Non-bypassable)
    # ========================================================================
    # VHH//，
    # ，
    cys_check_result = run_vhh_cys_preflight_check(normalized_query, numbering_maps)
    
    # action=abort，sequence_final
    if cys_check_result.get("action") == "abort":
        # （blocked variants）
        if panel_config is None:
            panel_config = {}
        
        scaffold_ids = panel_config.get("scaffolds", get_all_scaffold_ids())
        j_region_ids = panel_config.get("j_regions", get_all_j_region_ids())
        
        # blocked variants（sequence_final）
        blocked_variants = []
        for scaffold_id in scaffold_ids:
            for j_region_id in j_region_ids:
                blocked_variants.append({
                    "scaffold_id": scaffold_id,
                    "j_region_id": j_region_id,
                    "blocked_reason": {
                        "code": "P0_PREFLIGHT_FAILED",
                        "details": [msg["code"] for msg in cys_check_result.get("messages", [])],
                    },
                    "preflight_ref": {
                        "vhh_cys_check_status": cys_check_result.get("status", "fail"),
                        "vhh_cys_check_severity": cys_check_result.get("severity", "error"),
                    },
                })
        
        # blocked panel，sequence_final
        return {
            "preflight_checks": {
                "vhh_cys_check": cys_check_result,
            },
            "classic_panel": blocked_variants,  # blocked_reasonvariants
            "pipeline_version": "v1.0",
            "timestamp": datetime.now().isoformat(),
        }
    
    # ========================================================================
    # Gate (Pre-flight Check) - Read-only layer
    # ========================================================================
    # Gatepanel，、
    # Gatescaffold choice、graft/mutation、
    # sequence_final
    gate_result = run_vhh_gate(normalized_query)
    
    # CDR
    cdr1 = segments.get("CDR1", "")
    cdr2 = segments.get("CDR2", "")
    cdr3 = segments.get("CDR3", "")
    
    # CDR
    if not all([cdr1, cdr2, cdr3]):
        raise VHHClassicPanelError("Missing CDR sequences in query")
    
    # ========================================================================
    # Canonical Analysis (Read-only layer)
    # ========================================================================
    # CDR
    query_features = extract_cdr_features(normalized_query)
    
    # scaffold canonical profiles
    scaffold_profiles = get_scaffold_canonical_profiles()
    
    # canonical
    canonical_compat = build_canonical_compatibility(query_features, scaffold_profiles)
    
    # ========================================================================
    # Panel Generation
    # ========================================================================
    # 
    if panel_config is None:
        panel_config = {}
    
    scaffold_ids = panel_config.get("scaffolds", get_all_scaffold_ids())
    j_region_ids = panel_config.get("j_regions", get_all_j_region_ids())
    
    # （MVP）
    mode_str = panel_config.get("mode", "mvp").lower()
    mode = RuleMode.MVP if mode_str == "mvp" else RuleMode.EXPERT
    
    # queryKabat
    # query
    query_sequence = (
        segments.get("FR1", "") +
        cdr1 +
        segments.get("FR2", "") +
        cdr2 +
        segments.get("FR3", "") +
        cdr3 +
        segments.get("FR4", "")
    )
    
    query_kabat_map = build_kabat_map_from_numbering(numbering_maps, query_sequence)
    
    # numbering_maps，
    if not query_kabat_map:
        try:
            imgt_rows, kabat_rows, mapping = get_dual_numbering(query_sequence)
            numbering_maps = build_numbering_maps_json(imgt_rows, kabat_rows, mapping)
            query_kabat_map = build_kabat_map_from_numbering(numbering_maps, query_sequence)
        except Exception as e:
            raise VHHClassicPanelError(f"Failed to build Kabat map: {e}") from e
    
    # scaffold × J region
    classic_panel = []
    
    for scaffold_id in scaffold_ids:
        # scaffold
        if not validate_scaffold_integrity(scaffold_id):
            raise VHHClassicPanelError(f"Scaffold integrity check failed: {scaffold_id}")
        
        scaffold = get_classic_scaffold(scaffold_id)
        
        for j_region_id in j_region_ids:
            # J region
            if not validate_j_region_integrity(j_region_id):
                raise VHHClassicPanelError(f"J region integrity check failed: {j_region_id}")
            
            j_region = get_classic_j_region(j_region_id)
            
            # 1. Graft：FR1+CDR1+FR2+CDR2+FR3+CDR3+FR4
            sequence_grafted = (
                scaffold.fr1 +
                cdr1 +
                scaffold.fr2 +
                cdr2 +
                scaffold.fr3 +
                cdr3 +
                j_region.fr4
            )
            
            # 2. scaffoldKabat
            scaffold_sequence = scaffold.fr1 + scaffold.fr2 + scaffold.fr3
            try:
                imgt_rows_scaffold, kabat_rows_scaffold, mapping_scaffold = get_dual_numbering(scaffold_sequence)
                scaffold_kabat_map = build_kabat_map_from_numbering(
                    build_numbering_maps_json(imgt_rows_scaffold, kabat_rows_scaffold, mapping_scaffold),
                    scaffold_sequence
                )
            except Exception as e:
                raise VHHClassicPanelError(f"Failed to number scaffold {scaffold_id}: {e}") from e
            
            # 3. （Rulebook v1.0）
            mutations, mutation_summary = apply_all_mutation_rules(
                query_kabat_map=query_kabat_map,
                scaffold_fr2=scaffold.fr2,
                scaffold_kabat_map=scaffold_kabat_map,
                numbering_maps=numbering_maps,
                mode=mode,
            )
            
            # 4. 
            sequence_final = apply_mutations_to_sequence(
                sequence_grafted,
                mutations,
                numbering_maps,
            )
            
            # 5. QA
            cdr_integrity_ok = (
                cdr1 in sequence_final and
                cdr2 in sequence_final and
                cdr3 in sequence_final
            )
            
            numbering_consistency_ok = len(query_kabat_map) > 0 and len(scaffold_kabat_map) > 0
            
            # 6. canonical（，sequence_final）
            canonical_info = canonical_compat.get(scaffold_id, {})
            
            # 7. 
            result_entry = {
                "scaffold_id": scaffold_id,
                "j_region_id": j_region_id,
                "sequence_final": sequence_final,
                "sequence_grafted_pre_mutation": sequence_grafted,
                "mutations": [
                    {
                        "rule_id": mut.rule_id,
                        "numbering": mut.numbering,
                        "from_aa": mut.from_aa,
                        "to_aa": mut.to_aa,
                        "rationale": mut.rationale,
                        "evidence_level": mut.evidence_level,
                        # Rulebook v1.0 
                        "layer": mut.layer,
                        "risk_level": mut.risk_level,
                        "purpose": mut.purpose,
                        "trigger_explanation": mut.trigger_explanation,
                    }
                    for mut in mutations
                ],
                "mutation_summary": mutation_summary,
                "canonical_risk_level": canonical_info.get("risk_level", "unknown"),
                "canonical_rationale": canonical_info.get("rationale", "Canonical analysis not available"),
                "preflight_ref": {
                    "vhh_cys_check_status": cys_check_result.get("status", "unknown"),
                    "vhh_cys_check_severity": cys_check_result.get("severity", "unknown"),
                },
                "qa": {
                    "cdr_integrity_ok": cdr_integrity_ok,
                    "numbering_consistency_ok": numbering_consistency_ok,
                },
                "provenance": {
                    "scaffold_sha256": scaffold.sequence_sha256,
                    "j_region_sha256": j_region.sequence_sha256,
                    "pipeline_version": "v1.0",
                    "timestamp": datetime.now().isoformat(),
                },
            }
            
            classic_panel.append(result_entry)
    
    # ========================================================================
    # Rulebook Summary ()
    # ========================================================================
    # 
    triggered_rules = set()
    for entry in classic_panel:
        for mut in entry.get("mutations", []):
            triggered_rules.add(mut.get("rule_id"))
    
    # mode
    available_rules = get_rules_by_mode(mode)
    available_rule_ids = {rule.rule_id for rule in available_rules}
    
    # （expert_mode）
    disabled_high_risk_rules = []
    if mode == RuleMode.MVP:
        expert_rules = get_rules_by_mode(RuleMode.EXPERT)
        for rule in expert_rules:
            if rule.risk_level.value in ("medium", "high") and rule.rule_id not in triggered_rules:
                disabled_high_risk_rules.append({
                    "rule_id": rule.rule_id,
                    "layer": rule.layer.value,
                    "risk_level": rule.risk_level.value,
                    "reason": f"Not enabled in {mode.value} mode (requires expert_mode)",
                })
    
    rulebook_summary = {
        "rulebook_version": "v1.0",
        "mode": mode.value,
        "triggered_rules": sorted(list(triggered_rules)),
        "available_rules": sorted(list(available_rule_ids)),
        "disabled_high_risk_rules": disabled_high_risk_rules,
        "total_mutations": sum(len(entry.get("mutations", [])) for entry in classic_panel),
    }
    
    final_result = {
        "preflight_checks": {
            "vhh_cys_check": cys_check_result,  # P0（）
        },
        "gate": gate_result,  # Gate（read-only）
        "classic_panel": classic_panel,
        "cdr_features": query_features,
        "canonical_compatibility": canonical_compat,
        "canonical_profiles": scaffold_profiles,
        "rulebook_summary": rulebook_summary,  # Rulebook v1.0 
        "pipeline_version": "v1.0",
        "timestamp": datetime.now().isoformat(),
    }
    
    return final_result

