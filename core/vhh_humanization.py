"""
VHH

VHHhuman-VHH，Human VH3 VHH-SAFE
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.numbering.imgt_anarcii import (
    imgt_number_anarcii,
    imgt_number_anarcii_indexed,
    build_pos_to_aa_map,
    IMGTNumberingError,
)
from core.cdr_canonical import (
    classify_all_cdrs, 
    match_canonical_compatibility,
    get_key_position_residues,
    check_key_position_compatibility
)
# 
from core.utils.config_loader import get_config_lazy as get_config
from core.scaffolds import (
    load_alpaca_vhh_scaffolds,
    load_human_vhh_safe_templates,
    load_alignment_matrix,
    load_clinical_vhh_templates,
    load_clinical_germline_anchors,
    load_fr3_packing_rule
)
from core.utils.fallback import mark_fallback

# IMGT
IMGT_REGIONS = {
    "FR1": {"start": 1, "end": 26},
    "CDR1": {"start": 27, "end": 38},
    "FR2": {"start": 39, "end": 55},
    "CDR2": {"start": 56, "end": 65},
    "FR3": {"start": 66, "end": 104},
    "CDR3": {"start": 105, "end": 117},
    "FR4": {"start": 118, "end": 128},
}


class VHHHumanizationError(RuntimeError):
    """VHH"""
    pass


# scaffolds loader，
# load_alpaca_scaffolds, load_human_templates, load_alignment_matrix  core/scaffolds.py


def split_regions(rows: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    IMGTFRCDR。

    CDR：IMGT。
      IMGT CDR1 = 27-38（position 37）。
      IMGT CDR2 = 56-65。IMGT CDR3 = 105-117。
      Position 37CDR1，CDR1（FR-only policy）。
      VHH hallmarksIMGT 44/45/47（FR2，37）。

    V2.1 ： IMGT 55 (Kabat 50) 。
     CDR2 (IMGT 56-65)  IMGT 55  17aa（ Kabat CDR2 >= 17aa），
     IMGT 55  FR2 ， CDR2 ，。
    """
    regions = {
        "FR1": [],
        "CDR1": [],
        "FR2": [],
        "CDR2": [],
        "FR3": [],
        "CDR3": [],
        "FR4": [],
    }

    # ： CDR2  (IMGT 56-65)
    cdr2_raw_len = 0
    has_imgt_55 = False
    for row in rows:
        pos = row.get("pos")
        aa = row.get("aa")
        if not isinstance(pos, int) or not isinstance(aa, str) or aa == "-":
            continue
        if IMGT_REGIONS["CDR2"]["start"] <= pos <= IMGT_REGIONS["CDR2"]["end"]:
            cdr2_raw_len += 1
        if pos == 55:
            has_imgt_55 = True

    # ： CDR2  55  >= 17， 55  CDR2
    protect_imgt_55_as_cdr2 = has_imgt_55 and (cdr2_raw_len + 1 >= 17)

    for row in rows:
        pos = row.get("pos")
        aa = row.get("aa")

        if not isinstance(pos, int) or not isinstance(aa, str) or aa == "-":
            continue

        # 
        if IMGT_REGIONS["FR1"]["start"] <= pos <= IMGT_REGIONS["FR1"]["end"]:
            regions["FR1"].append(aa)
        elif IMGT_REGIONS["CDR1"]["start"] <= pos <= IMGT_REGIONS["CDR1"]["end"]:
            regions["CDR1"].append(aa)
        elif IMGT_REGIONS["FR2"]["start"] <= pos <= IMGT_REGIONS["FR2"]["end"]:
            if pos == 55 and protect_imgt_55_as_cdr2:
                regions["CDR2"].append(aa)  #  CDR2 
            else:
                regions["FR2"].append(aa)
        elif IMGT_REGIONS["CDR2"]["start"] <= pos <= IMGT_REGIONS["CDR2"]["end"]:
            regions["CDR2"].append(aa)
        elif IMGT_REGIONS["FR3"]["start"] <= pos <= IMGT_REGIONS["FR3"]["end"]:
            regions["FR3"].append(aa)
        elif IMGT_REGIONS["CDR3"]["start"] <= pos <= IMGT_REGIONS["CDR3"]["end"]:
            regions["CDR3"].append(aa)
        elif IMGT_REGIONS["FR4"]["start"] <= pos <= IMGT_REGIONS["FR4"]["end"]:
            regions["FR4"].append(aa)

    # 
    return {k: "".join(v) for k, v in regions.items()}


def find_best_matching_scaffold(vhh_seq: str, alpaca_scaffolds: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], float]:
    """
    VHHscaffold
    
    Returns:
        (scaffold_dict, identity_score)
    """
    try:
        input_rows = imgt_number_anarcii(vhh_seq)
        input_pos_map = build_pos_to_aa_map(input_rows)
    except IMGTNumberingError:
        return None, 0.0
    
    best_scaffold = None
    best_identity = 0.0
    
    for scaffold in alpaca_scaffolds:
        scaffold_framework = scaffold.get("consensus", {}).get("framework_full", "")
        if not scaffold_framework:
            continue

        # P0 fix: identity must be computed on IMGT positions, not on raw
        # concatenated strings. Linear index comparison breaks when templates
        # have different segment lengths/insertions.
        try:
            scaffold_rows = imgt_number_anarcii(scaffold_framework)
            scaffold_pos_map = build_pos_to_aa_map(scaffold_rows)
            identity = _compute_dynamic_alignment(input_pos_map, scaffold_pos_map).get("framework_identity", 0.0)
        except Exception:
            continue
        
        if identity > best_identity:
            best_identity = identity
            best_scaffold = scaffold
    
    return best_scaffold, best_identity


def extract_template_key_positions(template: Dict[str, Any]) -> Dict[str, str]:
    """
    Human
    
    Args:
        template: Human
    
    Returns:
        
    """
    # 
    # FR，IMGT
    try:
        framework_full = template['consensus']['framework_full']
        rows = imgt_number_anarcii(framework_full)
        pos_map = build_pos_to_aa_map(rows)
        return get_key_position_residues(pos_map)
    except Exception:
        return {}


def _compute_dynamic_alignment(input_pos_map: Dict[int, str], template_pos_map: Dict[int, str]) -> Dict[str, float]:
    """
    FR（）
    """
    # FR positions based on IMGT numbering
    # FR1: 1-26, FR2: 39-55, FR3: 66-104, FR4: 118-129
    fr_positions = list(range(1, 27)) + list(range(39, 56)) + list(range(66, 105)) + list(range(118, 130))
    fr2_positions = list(range(39, 56))
    
    fr_match = 0
    fr_total = 0
    fr_shared_total = 0
    fr_shared_match = 0
    fr2_match = 0
    fr2_total = 0
    
    for p in fr_positions:
        if p in input_pos_map and p in template_pos_map:
            fr_total += 1
            fr_shared_total += 1
            if input_pos_map[p] == template_pos_map[p]:
                fr_match += 1
                fr_shared_match += 1
        elif p in input_pos_map or p in template_pos_map:
            fr_total += 1
            
    for p in fr2_positions:
        if p in input_pos_map and p in template_pos_map:
            fr2_total += 1
            if input_pos_map[p] == template_pos_map[p]:
                fr2_match += 1
        elif p in input_pos_map or p in template_pos_map:
            fr2_total += 1
            
    fr_identity = fr_match / fr_total if fr_total > 0 else 0
    fr_identity_on_shared = fr_shared_match / fr_shared_total if fr_shared_total > 0 else 0
    fr_coverage = fr_shared_total / len(fr_positions) if fr_positions else 0
    fr2_identity = fr2_match / fr2_total if fr2_total > 0 else 0
    
    return {
        'framework_identity': fr_identity,
        'fr_identity_on_shared_positions': fr_identity_on_shared,
        'fr_coverage': fr_coverage,
        'fr2_identity': fr2_identity,
        'cdr_compatibility_score': 1.0,  # 
        'key_position_score': 1.0,       # 
        'vhh_hallmark_score': 1.0,       # 
    }

def select_human_templates(
    alpaca_scaffold_id: str,
    panel: str,
    alignment_index: Dict[str, Dict[str, Dict[str, Any]]],
    human_templates: List[Dict[str, Any]],
    top_k: int = 3,
    vhh_cdr_canonical: Optional[Dict[str, Dict[str, Any]]] = None,
    vhh_key_positions: Optional[Dict[str, str]] = None,
    use_cdr_filtering: bool = True,
    hard_min_cdr_score: Optional[float] = None,
    soft_min_cdr_score: Optional[float] = None,
    extreme_cdr3_mode: bool = False,
    input_pos_map: Optional[Dict[int, str]] = None,
    vhh_cdr3_seq: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    CDRHuman（FR）
    
    ：
    - Stage 1: FR - FR identityFR2 hallmark
    - Stage 2: CDR - CDR，
    - Stage 3: Developability - FRCMC
    
    Args:
        alpaca_scaffold_id: scaffold ID
        panel: （'A', 'B', 'C'  'all'）
        alignment_index: 
        human_templates: Human
        top_k: k
        vhh_cdr_canonical: VHHCDR（，）
        vhh_key_positions: VHH（）
        use_cdr_filtering: CDR（True，）
    
    Returns:
        Human（）
    """
    # 
    cfg = get_config()
    if hard_min_cdr_score is None:
        hard_min_cdr_score = cfg.parameters.hard_min_cdr_score
    if soft_min_cdr_score is None:
        soft_min_cdr_score = cfg.parameters.soft_min_cdr_score
        
    import logging
    logger = logging.getLogger(__name__)
    
    candidates = []
    
    # ── V2.2 Primary Selector (42 clinical VHHs) ──
    #  pos_map，42VHH
    if input_pos_map is not None:
        clinical_templates = load_clinical_vhh_templates()
        if clinical_templates:
            clinical_candidates = []
            for t in clinical_templates:
                t_pos_map = {int(k): v for k, v in t['imgt_positions'].items()}
                scores = _compute_dynamic_alignment(input_pos_map, t_pos_map)
                
                cdr_compatibility_score = 1.0
                key_position_score = 1.0
                cdr_warnings = []
                
                template_key_positions = extract_template_key_positions(t)
                if use_cdr_filtering and vhh_cdr_canonical:
                    compatibility = match_canonical_compatibility(
                        vhh_cdr_canonical,
                        None,
                        template_key_positions
                    )
                    cdr_compatibility_score = compatibility['compatibility_score']
                    key_position_score = compatibility.get('key_position_score', 1.0)
                    cdr_warnings = compatibility.get('warnings', [])
                    
                scores['cdr_compatibility_score'] = cdr_compatibility_score
                scores['key_position_score'] = key_position_score
                scores['_cdr_warnings'] = cdr_warnings
                
                result = t.copy()
                result['alignment_scores'] = scores
                result['_template_key_positions'] = template_key_positions
                result['_cdr_compatibility_score'] = cdr_compatibility_score
                
                clinical_candidates.append((t['template_id'], scores, result))
                
            if clinical_candidates:
                max_fr = max(c[1]['framework_identity'] for c in clinical_candidates)
                # V5.0 (2026-05-16): FR identity cutoff lowered from 0.70 to 0.65 (per
                # VHH_HUMANIZATION_DESIGN_STANDARD V5.0). Permissive 0.60 allowed via env.
                import os as _os_v5
                _v5_cutoff = 0.60 if _os_v5.environ.get("ABENGINECORE_VHH_PERMISSIVE_CUTOFF") == "1" else 0.65
                if max_fr >= _v5_cutoff:
                    logger.info(f"V5.0 Primary selector matched {len(clinical_candidates)} clinical VHHs with max FR identity {max_fr:.1%} (cutoff {_v5_cutoff:.0%})")
                    candidates = clinical_candidates
                else:
                    logger.warning(
                        f"V5.0 Primary selector failed (max FR identity {max_fr:.1%} < {_v5_cutoff:.0%}). "
                        f"VH3-SAFE fallback is DEPRECATED in V5.0; entering DeepFR-CTX-VHH 9aa context voting fallback path. "
                        f"Set ABENGINECORE_VHH_PERMISSIVE_CUTOFF=1 to use 0.60 cutoff."
                    )
                    
    # ── Fallback Selector (90 VH3 templates) — DEPRECATED in V5.0 ──
    # V5.0 (2026-05-16): The 90 synthetic VH3-SAFE templates are DEPRECATED.
    # If clinical-VHH selector finds nothing >= 0.65 FR identity, we return [] and
    # the caller (humanize_vhh_one_donor / api routers) will route the donor to the
    # no-template fallback path (DeepFR-CTX-VHH 9aa context voting via
    # surface_reshaping_trigger / ctx_guard). The legacy VH3-SAFE library can be
    # re-enabled for archival reproducibility only.
    import os as _os_v5b
    _legacy_vh3_safe_allowed = _os_v5b.environ.get("ABENGINECORE_ALLOW_VH3_SAFE_LEGACY") == "1"
    if not candidates and not _legacy_vh3_safe_allowed:
        logger.warning(
            "V5.0 select_human_templates: returning [] — no clinical-VHH template met FR cutoff "
            "and VH3-SAFE legacy library is disabled. Caller should route to DeepFR-CTX-VHH 9aa fallback."
        )
        return [], {"v5_no_template_fallback_required": True}
    if not candidates:
        if alpaca_scaffold_id not in alignment_index:
            return [], {"v5_legacy_vh3_safe_used": True, "warning": "V5.0 DEPRECATED path used"}

        # scaffold
        alignments = alignment_index[alpaca_scaffold_id]
        
        # ID
        def extract_plan_from_template_id(template_id: str) -> str:
            """ID（A/B/C）"""
            if template_id.endswith('_SAFE_A'):
                return 'A'
            elif template_id.endswith('_SAFE_B'):
                return 'B'
            elif template_id.endswith('_SAFE_C'):
                return 'C'
            return ''
        
        # Debug: 
        plan_distribution = {'A': 0, 'B': 0, 'C': 0, 'unknown': 0}
        for tid in alignments.keys():
            plan = extract_plan_from_template_id(tid)
            if plan in plan_distribution:
                plan_distribution[plan] += 1
            else:
                plan_distribution['unknown'] += 1
        
        logger.debug(
            f"[select_human_templates] Scaffold {alpaca_scaffold_id}, Panel {panel}: "
            f"Total templates={len(alignments)}, "
            f"Plan distribution: A={plan_distribution['A']}, B={plan_distribution['B']}, C={plan_distribution['C']}, unknown={plan_distribution['unknown']}"
        )
        
        # 
        if panel.upper() in ['A', 'B', 'C']:
            # ID（human_plan）
            filtered = {}
            for tid, scores in alignments.items():
                plan = extract_plan_from_template_id(tid)
                if plan.upper() == panel.upper():
                    filtered[tid] = scores
            
            logger.debug(
                f"[select_human_templates] After filtering panel {panel}: {len(filtered)} templates"
            )
        else:
            filtered = alignments
        
        # 
        for template_id, scores in filtered.items():
            # 
            template = next((t for t in human_templates if t['template_id'] == template_id), None)
            if not template:
                continue
            
            # 
            template_key_positions = extract_template_key_positions(template)
            
            # FR：CDR，
            cdr_compatibility_score = 1.0  # 
            key_position_score = 1.0
            cdr_warnings = []
            
            if use_cdr_filtering and vhh_cdr_canonical:
                compatibility = match_canonical_compatibility(
                    vhh_cdr_canonical,
                    None,
                    template_key_positions
                )
                
                cdr_compatibility_score = compatibility['compatibility_score']
                key_position_score = compatibility.get('key_position_score', 1.0)
                cdr_warnings = compatibility.get('warnings', [])
                
                # Unknown CDR，warning
                for cdr_name in ['CDR1', 'CDR2']:
                    cdr_info = vhh_cdr_canonical.get(cdr_name.lower(), {})
                    canonical_class = cdr_info.get('canonical_class', '')
                    if canonical_class == 'Unknown' or canonical_class == 'non_canonical':
                        cdr_warnings.append(
                            f"{cdr_name}({canonical_class})，"
                        )
            
            # scores（）
            scores['cdr_compatibility_score'] = cdr_compatibility_score
            scores['key_position_score'] = key_position_score
            scores['_cdr_warnings'] = cdr_warnings
            
            result = template.copy()
            result['alignment_scores'] = scores
            result['_template_key_positions'] = template_key_positions
            result['_cdr_compatibility_score'] = cdr_compatibility_score  # 
            candidates.append((template_id, scores, result))
    
    # （： + fallback + V2.2 Germline Anchoring）
    # ：combined_score = 0.5 * framework_identity + 0.25 * cdr_compatibility_score + 0.25 * dev_score
    # fallback， ADA  FR3 Packing 
    
    fr3_packing_rule = load_fr3_packing_rule()
    ada_anchors = load_clinical_germline_anchors()
    
    def calculate_combined_score(item):
        template_id, scores, template = item
        framework_identity = scores.get('framework_identity', 0)
        cdr_compat = scores.get('cdr_compatibility_score', 1.0)
        key_pos_score = scores.get('key_position_score', 1.0)
        
        # CDR，cdr_compat1.0
        if not use_cdr_filtering:
            cdr_compat = 1.0
        
        # Developability（）
        dev_score = template.get('developability', {}).get('score', 0.5)
        
        # （scoring profile）
        cfg = get_config()
        weights = cfg.parameters.get_scoring_weights()
        
        # FR（profile）
        fr_immuno_score = 1.0
        if 'fr_immunogenicity' in weights:
            # FR
            immuno = template.get('immunogenicity', {})
            fr_immuno_risk = immuno.get('fr_immuno_risk', 'low')
            # （low=1.0, medium=0.8, high=0.6）
            risk_scores = {'low': 1.0, 'medium': 0.8, 'high': 0.6}
            fr_immuno_score = risk_scores.get(fr_immuno_risk, 1.0)
        
        # FR：FR identity，CDR
        # ：FR 0.6, CDR 0.15, Developability 0.25
        # ，
        fr_weight = weights.get('framework_identity', 0.6)  # 0.6（）
        cdr_weight = weights.get('cdr_compatibility', 0.15)  # 0.15（）
        dev_weight = weights.get('developability', 0.25)  # 0.25
        
        # ：FR + CDR（P2-10: ）
        # ： [0, 1]
        main_sum = fr_weight + cdr_weight + dev_weight
        if main_sum > 0:
            main_combined = (
                (fr_weight * framework_identity +
                 cdr_weight * cdr_compat +
                 dev_weight * dev_score) / main_sum
            )
        else:
            main_combined = 0.5  # fallback
        
        # ── V2.2 Germline Anchoring (ADA risk penalty, P2-10: ) ──
        # ADA penalty ，
        germline = template.get('germline')
        ada_penalty = 1.0
        if germline and ada_anchors:
            ada_risk = ada_anchors.get(germline, {}).get('ada_majority_risk', 'UNKNOWN')
            if ada_risk == 'HIGH':
                ada_penalty = 0.8
            elif ada_risk == 'MEDIUM':
                ada_penalty = 0.9
            elif ada_risk == 'UNKNOWN':
                ada_penalty = 0.95
            # LOW -> 1.0
        
        # ── V2.2 FR3 Packing Score ──
        fr3_packing_score = 1.0
        if input_pos_map and fr3_packing_rule and 'tier_definitions' in fr3_packing_rule:
            t_pos_map = {int(k): v for k, v in template.get('imgt_positions', {}).items()}
            if t_pos_map:
                total_weight = 0
                match_weight = 0
                for t_name, t_info in fr3_packing_rule['tier_definitions'].items():
                    w = t_info.get('weight', 1.0)
                    for p in t_info.get('positions', []):
                        if p in input_pos_map and p in t_pos_map:
                            total_weight += w
                            if input_pos_map[p] == t_pos_map[p]:
                                match_weight += w
                if total_weight > 0:
                    fr3_packing_score = match_weight / total_weight
                    # Blend FR3 packing into main score (e.g., 15% weight)
                    main_combined = 0.85 * main_combined + 0.15 * fr3_packing_score
        
        # P2-10: ADA penalty applied symmetrically to (main + secondary items)
        combined = ada_penalty * main_combined
        
        # profilefr_immunogenicity，
        if 'fr_immunogenicity' in weights:
            combined += ada_penalty * weights['fr_immunogenicity'] * fr_immuno_score
        
        # Fallback（）
        fallback_penalty_factor = 1.0
        if template.get('_is_fallback', False):
            fallback_penalty_factor = cfg.parameters.fallback_penalty_template
            combined *= fallback_penalty_factor
        
        if scores.get('_numbering_fallback', False):
            fallback_penalty_factor *= cfg.parameters.fallback_penalty_numbering
            combined *= cfg.parameters.fallback_penalty_numbering

        # VHH-aware template ranking: typical CDR3 length / stabilizing Cys motifs
        cdr3_adj = 0.0
        if vhh_cdr3_seq:
            L3 = len(vhh_cdr3_seq.strip())
            if 10 <= L3 <= 24:
                cdr3_adj += 0.012
            elif L3 > 32:
                cdr3_adj -= 0.008
            if vhh_cdr3_seq.count("C") >= 2 and re.search(r"C.{2,12}C", vhh_cdr3_seq.upper()):
                cdr3_adj += 0.014
        combined = max(0.0, min(1.0, combined + cdr3_adj))
        
        # scores
        scores['developability_score'] = dev_score
        scores['scoring_details'] = {
            'framework_identity': round(framework_identity, 3),
            'cdr_compatibility_score': round(cdr_compat, 3),
            'key_position_score': round(key_pos_score, 3),
            'developability_score': round(dev_score, 3),
            'ada_penalty': round(ada_penalty, 3),
            'fr3_packing_score': round(fr3_packing_score, 3),
            'fallback_penalty_factor': round(fallback_penalty_factor, 3),
            'cdr3_length_score_adj': round(cdr3_adj, 4),
            'combined_score': round(combined, 3),
        }
        
        return combined
    
    # FR：framework_identity，FR
    sorted_candidates = sorted(
        candidates,
        key=lambda x: x[1].get('framework_identity', 0),
        reverse=True
    )
    
    # FR：primary，CDR
    # CDR，Unknown CDRFR
    primary = []
    quality_flags = {
        'cdr_compatibility_fallback': False,  # FRfallback
        'extreme_cdr3_mode': extreme_cdr3_mode,
        'developability_risk': 'low',
        'fr_immuno_risk': 'low',
        'cdr_warnings': [],  # CDR
    }
    
    for template_id, scores, template in sorted_candidates:
        # P2-11 (observe-only): keep ranking behavior unchanged, but log low
        # FR coordinate overlap so downstream can evaluate whether to enforce
        # coverage gates in a future governed upgrade.
        fr_cov = scores.get('fr_coverage')
        if isinstance(fr_cov, (int, float)) and fr_cov < 0.8:
            logger.warning(
                f"[select_human_templates] Low FR coverage template={template_id} "
                f"coverage={fr_cov:.3f} (<0.8); ranking behavior unchanged (observe-only)."
            )
        # primary（FR）
        primary.append((template_id, scores, template))
        
        # CDR（）
        cdr_warnings = scores.get('_cdr_warnings', [])
        if cdr_warnings:
            # ，
            for warning in cdr_warnings:
                if warning not in quality_flags['cdr_warnings']:
                    quality_flags['cdr_warnings'].append(warning)
        
        # Developability
        dev_grade = template.get('developability', {}).get('grade', 'C')
        dev_score = template.get('developability', {}).get('score', 0.5)
        
        # FR
        fr_immuno_risk = template.get('immunogenicity', {}).get('fr_immuno_risk', 'low')
        
        # （）
        if dev_grade == 'C' or dev_score < 0.6:
            quality_flags['developability_risk'] = 'high'
        elif dev_grade == 'B' and quality_flags['developability_risk'] == 'low':
            quality_flags['developability_risk'] = 'medium'
        
        if fr_immuno_risk == 'high':
            quality_flags['fr_immuno_risk'] = 'high'
        elif fr_immuno_risk == 'medium' and quality_flags['fr_immuno_risk'] == 'low':
            quality_flags['fr_immuno_risk'] = 'medium'
    
    # primary
    # P0 fix: keep FR-priority semantics explicit in sort key.
    def sort_key(item):
        template_id, scores, template = item
        combined = calculate_combined_score(item)
        framework_identity = float(scores.get("framework_identity", 0.0))
        
        # Developability
        dev_grade = template.get('developability', {}).get('grade', 'C')
        fr_immuno_risk = template.get('immunogenicity', {}).get('fr_immuno_risk', 'low')
        
        # ：A > B > C
        grade_priority = {'A': 3, 'B': 2, 'C': 1}.get(dev_grade, 1)
        
        # ：low > medium > high
        immuno_priority = {'low': 3, 'medium': 2, 'high': 1}.get(fr_immuno_risk, 1)
        
        # （FR）： framework_identity， combined，
        # / tie-breaker。
        return (framework_identity, combined, grade_priority, immuno_priority)
    
    primary_sorted = sorted(
        primary,
        key=sort_key,
        reverse=True
    )[:top_k]
    
    # 
    results = []
    for template_id, scores, template in primary_sorted:
        # 
        scoring_details = scores.get('scoring_details', {})
        template['alignment_scores']['combined_score'] = scoring_details.get('combined_score', 0)
        template['alignment_scores']['scoring'] = scoring_details
        
        # 
        template.pop('_cdr_compatibility_score', None)
        template.pop('_is_fallback', None)
        
        results.append(template)
    
    return results, quality_flags


def rebuild_v_region_from_regions(regions: Dict[str, str]) -> str:
    """
    IMGTFR/CDR，FR4。
    
    Args:
        regions: ，FR1-4CDR1-3
        
    Returns:
        V
    """
    from core.vhh_qa_validation import V_REGION_ORDER
    
    seq_parts = []
    for region in V_REGION_ORDER:
        part = regions.get(region, "")
        if part is None:
            part = ""
        seq_parts.append(part)
    return "".join(seq_parts)


def _humanized_regions_for_qa(
    humanized_seq: str,
    species: str,
    template: Dict[str, Any],
    vhh_cdrs: Dict[str, str],
) -> Dict[str, str]:
    """
    Build IMGT region map for the *final* humanized string (after tier-back / reshape).
    Must satisfy rebuild_v_region_from_regions(regions) == humanized_seq.upper().
    """
    from core.vhh_qa_validation import V_REGION_ORDER, rebuild_v_region_from_regions
    from core.segmentation.anarcii_adapter import run_anarcii_imgt

    seq = (humanized_seq or "").strip().upper()
    if not seq:
        return {k: "" for k in V_REGION_ORDER}
    try:
        rseg, _, _ = run_anarcii_imgt(
            seq=seq,
            species=species,
            chain="H",
            allow_partial=True,
            max_mismatches=0,
        )
        if rseg:
            out = {k: (rseg.get(k) or "") for k in V_REGION_ORDER}
            if rebuild_v_region_from_regions(out) == seq:
                return out
    except Exception:
        pass
    c = (template or {}).get("consensus", {}) or {}
    return {
        "FR1": c.get("fr1", ""),
        "CDR1": vhh_cdrs.get("CDR1", ""),
        "FR2": c.get("fr2", ""),
        "CDR2": vhh_cdrs.get("CDR2", ""),
        "FR3": c.get("fr3", ""),
        "CDR3": vhh_cdrs.get("CDR3", ""),
        "FR4": c.get("fr4", "") or "WGQGTQVTVSS",
    }


def _sync_sequence_analysis_with_final_best(result: Dict[str, Any], species: str) -> None:
    """After best humanized sequence is final (incl. surface reshape), re-segment for QA."""
    from core.vhh_qa_validation import V_REGION_ORDER, rebuild_v_region_from_regions
    from core.segmentation.anarcii_adapter import run_anarcii_imgt

    best = result.get("best_match") or {}
    final = (best.get("humanized_sequence") or "").strip().upper()
    if not final:
        return
    try:
        rseg, _, _ = run_anarcii_imgt(
            seq=final,
            species=species,
            chain="H",
            allow_partial=True,
            max_mismatches=0,
        )
        if not rseg:
            return
        hum = {k: (rseg.get(k) or "") for k in V_REGION_ORDER}
        if rebuild_v_region_from_regions(hum) != final:
            return
        sa = result.setdefault("sequence_analysis", {})
        sa["humanized_sequence"] = final
        sa["humanized_length"] = len(final)
        sa["humanized_regions"] = hum
        cands = result.get("candidates")
        if cands:
            cands[0]["humanized_sequence"] = final
            cands[0]["humanized_length"] = len(final)
            cands[0]["humanized_regions"] = hum
    except Exception:
        return


def apply_tier_back_mutations(
    original_seq: str,
    humanized_seq: str,
    protected_kabat: set,
    species: str = "alpaca",
) -> Tuple[str, List[Dict]]:
    """
    V2.5 §3.3 / §2 Tier  + Hallmark 。

     graft_cdrs_to_template() 。
    1.  protected_kabat  Kabat ：
       -  VHH ，
          VHH 。
    2. V2.5 Hallmark ：
       -  Tier 0 FR2 Hallmark  (44, 45, 47)。
       -  VHH  VHH ，
          (44E/Q, 45A, 47G)。
         ： 37  CDR1（IMGT 27-38）， FR-only graft ， Hallmark 。

    : config/tier_system_config.json Tier 0/1/2 
              + get_cdr3_aware_protected_positions() 

    Args:
        original_seq:     VHH 
        humanized_seq:    graft_cdrs_to_template() 
        protected_kabat:  VHH  Kabat 
        species:         VHH （ ANARCI ）

    Returns:
        (corrected_seq, back_mutations)
        corrected_seq:   
        back_mutations:  
    """
    if not protected_kabat:
        return humanized_seq, []

    try:
        from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map

        def _pos_to_aa_from_rows(rows: list) -> Dict[int, str]:
            """ imgt_number_anarcii()  row dict  {imgt_pos: aa}。"""
            out: Dict[int, str] = {}
            for r in rows:
                aa = r.get("aa", "-")
                if aa and aa != "-":
                    out[r["pos"]] = aa  # base position only; insertions overwrite (FR )
            return out

        def _pos_to_linear_from_rows(rows: list) -> Dict[int, int]:
            """ row dict  {imgt_pos: linear_index}（non-gap residues only）。"""
            out: Dict[int, int] = {}
            idx = 0
            for r in rows:
                aa = r.get("aa", "-")
                if aa and aa != "-":
                    pos = r["pos"]
                    if pos not in out:
                        out[pos] = idx
                    idx += 1
            return out

        orig_rows = imgt_number_anarcii(original_seq)
        hum_rows  = imgt_number_anarcii(humanized_seq)

        orig_map         = _pos_to_aa_from_rows(orig_rows)
        hum_map          = _pos_to_aa_from_rows(hum_rows)
        hum_pos_to_linear = _pos_to_linear_from_rows(hum_rows)

        seq_list = list(humanized_seq)
        back_mutations: List[Dict] = []
        
        # V2.5 hallmark policy (3 FR2 hallmarks only; pos37 is CDR1, not corrected)
        HALLMARK_CORRECTIONS = {
            44: {"allowed": {"E", "G", "A", "S", "D", "Q"}, "default": "E"},
            45: {"allowed": {"A", "R", "L", "K", "Q"}, "default": "A"},  # A=97.6% clinical norm
            47: {"allowed": {"F", "Y", "L", "W", "G"}, "default": "G"},
        }

        for kabat_pos in sorted(protected_kabat):
            orig_aa = orig_map.get(kabat_pos)
            hum_aa  = hum_map.get(kabat_pos)
            if orig_aa is None or hum_aa is None:
                continue
                
            linear_i = hum_pos_to_linear.get(kabat_pos)
            if linear_i is None or linear_i >= len(seq_list):
                continue
                
            # V2.5 Hallmark Auto-Correction Logic
            target_aa = orig_aa
            correction_note = ""
            
            if kabat_pos in HALLMARK_CORRECTIONS:
                rules = HALLMARK_CORRECTIONS[kabat_pos]
                if orig_aa not in rules["allowed"]:
                    target_aa = rules["default"]
                    correction_note = f" [V2.5 Auto-Correction: Original '{orig_aa}' is unsafe for VHH solubility, forced to '{target_aa}']"

            if target_aa == hum_aa:
                continue  # ，

            seq_list[linear_i] = target_aa
            back_mutations.append({
                "kabat_position": kabat_pos,
                "from_aa": hum_aa,
                "to_aa": target_aa,
                "linear_index": linear_i,
                "rationale": f"Tier-protected back-mutation (Kabat {kabat_pos}): Human {hum_aa} → Target {target_aa}{correction_note}",
                "standard_ref": "VHH_HUMANIZATION_DESIGN_STANDARD V2.5 §2/§3.3",
            })

        return "".join(seq_list), back_mutations

    except Exception as e:
        # ：， + 
        return humanized_seq, [{"error": f"Tier （）: {e}"}]


def graft_cdrs_to_template(vhh_cdrs: Dict[str, str], human_template: Dict[str, Any]) -> str:
    """
    VHHCDRHuman
    
    Args:
        vhh_cdrs: VHHCDR {'CDR1': '...', 'CDR2': '...', 'CDR3': '...'}
        human_template: Human
    
    Returns:
        （FR1-4CDR1-3）
    """
    consensus = human_template['consensus']
    
    # FR1-3
    fr1 = consensus.get('fr1', '')
    fr2 = consensus.get('fr2', '')
    fr3 = consensus.get('fr3', '')
    fr4 = consensus.get('fr4', '')
    
    # FR4，framework_full
    if not fr4:
        framework_full = consensus.get('framework_full', '')
        if framework_full:
            # FR1+FR2+FR3
            fr1_len = len(fr1)
            fr2_len = len(fr2)
            fr3_len = len(fr3)
            expected_fr123_len = fr1_len + fr2_len + fr3_len
            
            # framework_fullFR1+FR2+FR3，FR4
            if len(framework_full) > expected_fr123_len:
                # framework_fullFR4
                # ：framework_fullCDR，
                # ：framework_full，FR411
                if len(framework_full) >= expected_fr123_len + 10:
                    fr4 = framework_full[-11:]  # FR411
                else:
                    fr4 = framework_full[expected_fr123_len:]
        
        # ，FR4（VHHFR4）
        if not fr4:
            fr4 = "WGQGTQVTVSS"  # VHH FR4
    
    # ，FR4
    regions = {
        'FR1': fr1,
        'CDR1': vhh_cdrs.get('CDR1', ''),
        'FR2': fr2,
        'CDR2': vhh_cdrs.get('CDR2', ''),
        'FR3': fr3,
        'CDR3': vhh_cdrs.get('CDR3', ''),
        'FR4': fr4,
    }
    
    humanized_seq = rebuild_v_region_from_regions(regions)
    
    return humanized_seq


def humanize_vhh(
    seq: str,
    panel: str = "A",
    top_k: int = 3,
    species: str = "alpaca",
    return_all_templates: bool = False,
    scoring_profile: Optional[str] = None,
    extra_protected: Optional[set] = None,
    enforce_prescreen: bool = True,
) -> dict:
    """
    ：VHH → human-VHH + 
    
    Args:
        seq: VHH
        panel: 
            - 'A': （44→Q, 45→R）
            - 'B': （44→Q, 45→A, 47→G）
            - 'C': VHH（44=Q, 45=A, 47=G）
            - 'all': 
        top_k: k
        species: （'alpaca'）
        return_all_templates: 
        scoring_profile: Scoring profile（，'default', 'developability_strict', 'minimized_immunogenicity'）
        extra_protected: P1-4 union semantics — extra IMGT base positions to
            preserve. The final protection set is the UNION of the strategy/
            CDR3-aware dynamic set AND ``extra_protected``. Provenance is
            written to ``result["_protected_provenance"]``.
        enforce_prescreen: P0-2 hard gate — when True (default), run
            ``_vhh_feasibility_prescreen`` immediately after CDR extraction
            and short-circuit with ``route="surface_reshaping_only"`` on a
            hard-gate hit (no graft attempted). Callers that have already
            performed prescreen (e.g. ``api/routers/humanization.py``) MUST
            pass ``enforce_prescreen=False`` to avoid double gating.
    
    Returns:
        dict，：
        {
            'success': bool,
            'input': {
                'sequence': str,
                'length': int,
                'species': str,
            },
            'best_match': {
                'alpaca_scaffold': str,
                'alpaca_identity': float,
                'human_template': str,
                'humanized_sequence': str,
                'alignment_scores': dict,
            },
            'candidates': [
                {
                    'template_id': str,
                    'humanized_sequence': str,
                    'alignment_scores': dict,
                },
                ...
            ],
            'cdrs': {
                'CDR1': str,
                'CDR2': str,
                'CDR3': str,
            },
            'cdr_canonical': {
                'CDR1': {...},  # CDR
                'CDR2': {...},
                'CDR3': {...},
            },
            'best_by_plan': {  # panel='all'
                'A': {...},    # A
                'B': {...},    # B
                'C': {...},    # C
            },
            'error': str ()
        }
    """
    result = {
        'success': False,
        'input': {
            'sequence': seq,
            'length': len(seq),
            'species': species,
        },
        'best_match': None,
        'candidates': [],
        'cdrs': {},
        'error': None,
    }
    
    try:
        # 0. scoring profile（）
        cfg = get_config()
        if scoring_profile:
            if cfg.parameters.scoring:
                if scoring_profile in cfg.parameters.scoring.profiles:
                    cfg.parameters.scoring.active_profile = scoring_profile
                else:
                    raise VHHHumanizationError(
                        f"Unknown scoring profile: {scoring_profile}. "
                        f"Available profiles: {list(cfg.parameters.scoring.profiles.keys())}"
                    )
            else:
                raise VHHHumanizationError(
                    "Scoring profiles not configured. Please configure scoring in config.yaml"
                )
        
        # 1. 
        alpaca_scaffolds = load_alpaca_vhh_scaffolds()
        human_templates = load_human_vhh_safe_templates()
        alignment_index = load_alignment_matrix()
        
        # 2. VHHIMGT（provenance）
        try:
            from core.segmentation.anarcii_adapter import run_anarcii_imgt
            
            vhh_regions, rows, segmentation_provenance = run_anarcii_imgt(
                seq=seq,
                species=species,
                chain="H",
                allow_partial=True,
                max_mismatches=0
            )
            
            # provenanceresult
            result['segmentation_provenance'] = segmentation_provenance
            
            vhh_cdrs = {
                'CDR1': vhh_regions.get('CDR1', ''),
                'CDR2': vhh_regions.get('CDR2', ''),
                'CDR3': vhh_regions.get('CDR3', ''),
            }
            result['cdrs'] = vhh_cdrs
            
            # 
            pos_map = build_pos_to_aa_map(rows)
            vhh_key_positions = get_key_position_residues(pos_map)
        except (IMGTNumberingError, RuntimeError, ImportError) as e:
            result['error'] = f"IMGT: {e}"
            return result
        
        # ── P0-2: Feasibility prescreen hard gate ─────────────────────────────
        # When enforce_prescreen=True (CLI/engine default), evaluate the
        # standard §0.4 hard-gate rules immediately after CDR extraction.
        # If the donor scores `surface_reshaping_only`, short-circuit before
        # any graft / template work and surface the prescreen verdict for the
        # caller. API callers (`api/routers/humanization._humanize_vhh_impl`)
        # have already routed through their own 5-way prescreen and MUST pass
        # `enforce_prescreen=False` to avoid double gating.
        prescreen_record: Optional[Dict[str, Any]] = None
        if enforce_prescreen:
            try:
                from core.humanization.engine import (
                    _vhh_feasibility_prescreen,
                    _vhh_mini_cmc,
                )
                _donor_mini_cmc = _vhh_mini_cmc(seq)
                _prescreen = _vhh_feasibility_prescreen(vhh_cdrs, _donor_mini_cmc)
                prescreen_record = {
                    "recommendation": _prescreen.get("recommendation"),
                    "triggered_rules": _prescreen.get("triggered_rules", []),
                    "feasibility_note": _prescreen.get("feasibility_note", ""),
                    "feasibility_score": _prescreen.get("feasibility_score"),
                    "raw_metrics": {
                        "cdr1_len": len(vhh_cdrs.get("CDR1", "")),
                        "cdr2_len": len(vhh_cdrs.get("CDR2", "")),
                        "cdr3_len": len(vhh_cdrs.get("CDR3", "")),
                        "SAP_proxy": _donor_mini_cmc.get("SAP_proxy"),
                        "instability_index": _donor_mini_cmc.get("instability_index"),
                        "pI": _donor_mini_cmc.get("pI"),
                    },
                }
                result["prescreen"] = prescreen_record
                if _prescreen.get("recommendation") == "surface_reshaping_only":
                    # Hard gate hit — short-circuit before scaffold matching.
                    # success=True signals "decision made correctly"; downstream
                    # callers must check `route` before consuming `best_match`.
                    result["success"] = True
                    result["route"] = "surface_reshaping_only"
                    result["best_match"] = None
                    result["candidates"] = []
                    return result
                # For non-hard-gate recommendations (humanization /
                # borderline / humanization_plus_*), continue normally; the
                # prescreen record stays in the result for transparency.
                result["route"] = _prescreen.get("recommendation") or "humanization"
            except Exception as _pe:
                # Prescreen failure must not silently bypass the gate; record
                # the issue and continue with route="humanization" (the
                # caller can inspect `prescreen.error`).
                result["prescreen"] = {
                    "recommendation": None,
                    "triggered_rules": [],
                    "feasibility_note": (
                        "Prescreen could not run; proceeding with standard "
                        f"CDR-graft humanization. Reason: {_pe}"
                    ),
                    "error": str(_pe),
                    "raw_metrics": {},
                }
                result["route"] = "humanization"
        else:
            result["route"] = "humanization"
            result["prescreen"] = {
                "recommendation": "skipped_by_caller",
                "triggered_rules": [],
                "feasibility_note": (
                    "Prescreen skipped because enforce_prescreen=False "
                    "(caller has performed its own gating)."
                ),
                "raw_metrics": {},
            }

        # 3. scaffold
        best_scaffold, scaffold_identity = find_best_matching_scaffold(seq, alpaca_scaffolds)
        
        if not best_scaffold:
            result['error'] = "scaffold"
            return result
        
        # 3.5. CDR（）
        cdr_canonical = classify_all_cdrs(vhh_cdrs, key_positions=vhh_key_positions)
        result['cdr_canonical'] = cdr_canonical
        result['key_positions'] = vhh_key_positions
        # VHH hallmark positions: IMGT 44/45/47 (FR2 only; pos37 is CDR1, preserved by graft)
        _p44 = pos_map.get(44, "?")
        _p45 = pos_map.get(45, "?")
        _p47 = pos_map.get(47, "?")
        result['hallmarks'] = {
            "pos44": _p44,
            "pos45": _p45,
            "pos47": _p47,
            "all_ok": (
                _p44 in ("E", "G", "A", "S", "D", "Q") and
                _p45 in ("A", "R", "L", "K", "Q") and
                _p47 in ("F", "Y", "L", "W", "G")
            ),
        }
        
        # 3.6. CDR3（CDR3≥3Cys）
        cdr3_seq = vhh_cdrs.get('CDR3', '')
        cdr3_len = len(cdr3_seq)
        cdr3_cys_count = cdr3_seq.count('C')
        
        extreme_cdr3_mode = False
        risk_flags = {}
        
        if cdr3_len >= 20 or cdr3_cys_count >= 3:
            extreme_cdr3_mode = True
            risk_flags['long_cdr3'] = (cdr3_len >= 20)
            risk_flags['noncanonical_disulfide_suspected'] = (cdr3_cys_count >= 3)
            # CDR3：top_k >= 10
            if top_k < 10:
                top_k = 10
        
        result['risk_flags'] = risk_flags
        
        # 4. Human（P1-3: panel='all'  A/B/C ）
        panel_upper = panel.upper()
        requested_panels = ['A', 'B', 'C'] if panel_upper == 'ALL' else [panel_upper]
        _panel_to_strategy = {"A": "S1", "B": "S2", "C": "S3"}

        # Build original regions for QA system (FR+CDR breakdown of input sequence)
        orig_regions_for_qa = vhh_regions if isinstance(vhh_regions, dict) else {}

        quality_flags_by_panel: Dict[str, Dict[str, Any]] = {}
        protected_provenance_by_panel: Dict[str, Dict[str, Any]] = {}
        all_ranked_templates_for_germline: List[Dict[str, Any]] = []
        candidates: List[Dict[str, Any]] = []
        best_by_plan: Dict[str, Dict[str, Any]] = {}

        def _candidate_combined_score(cand: Dict[str, Any]) -> float:
            al = cand.get('alignment_scores', {}) if isinstance(cand.get('alignment_scores'), dict) else {}
            sd = al.get('scoring_details', {}) if isinstance(al.get('scoring_details'), dict) else {}
            cs = sd.get('combined_score')
            if cs is None:
                cs = al.get('combined_score')
            try:
                return float(cs)
            except (TypeError, ValueError):
                return -99.0

        for panel_i in requested_panels:
            human_candidates_i, quality_flags_i = select_human_templates(
                best_scaffold['scaffold_id'],
                panel_i,
                alignment_index,
                human_templates,
                top_k,
                vhh_cdr_canonical=cdr_canonical,
                vhh_key_positions=vhh_key_positions,
                use_cdr_filtering=True,
                extreme_cdr3_mode=extreme_cdr3_mode,
                input_pos_map=pos_map,
                vhh_cdr3_seq=cdr3_seq,
            )
            if not human_candidates_i:
                continue

            quality_flags_by_panel[panel_i] = quality_flags_i
            all_ranked_templates_for_germline.extend(human_candidates_i)

            # 4.5. 
            for candidate in human_candidates_i:
                template_key_positions = candidate.get('_template_key_positions', {})
                compatibility = match_canonical_compatibility(
                    cdr_canonical,
                    None,
                    template_key_positions
                )
                candidate['cdr_compatibility'] = compatibility
                candidate.pop('_template_key_positions', None)

            # 5.  panel （P1-4: union ；P1-3: ）
            strategy_i = _panel_to_strategy.get(panel_i, "S1")
            dyn_i = get_cdr3_aware_protected_positions(cdr3_len, strategy_i, cdr3_seq=cdr3_seq)
            dynamic_set_i = set(dyn_i.get("protected_positions") or [])
            extra_set_i = set(extra_protected) if extra_protected else set()
            protected_i = dynamic_set_i | extra_set_i
            protected_provenance_by_panel[panel_i] = {
                "from_dynamic": sorted(dynamic_set_i),
                "from_extra": sorted(extra_set_i),
                "union": sorted(protected_i),
                "strategy": strategy_i,
                "cdr3_tier": dyn_i.get("cdr3_tier"),
                "cdr3_len": cdr3_len,
                "dynamic_upgrades": dyn_i.get("dynamic_upgrades", []),
                "extra_provided": extra_protected is not None,
                "panel": panel_i,
            }

            panel_candidates: List[Dict[str, Any]] = []
            for template in human_candidates_i:
                humanized_seq = graft_cdrs_to_template(vhh_cdrs, template)

                # ── V2.2 §2/§3.3 Tier  ─────────────────────────────
                tier_back_muts: List[Dict] = []
                if protected_i:
                    humanized_seq, tier_back_muts = apply_tier_back_mutations(
                        original_seq=seq,
                        humanized_seq=humanized_seq,
                        protected_kabat=protected_i,
                        species=species,
                    )

                # IMGT regions for QA: must match final sequence
                hum_regions = _humanized_regions_for_qa(
                    humanized_seq, species, template, vhh_cdrs
                )

                # P1-5:  candidate  SAP 
                hydro_i = _compute_hydro_patch_max9(humanized_seq)
                sap_check_i = check_sap_against_strategy(hydro_i, strategy_i)
                reshape_i: Dict[str, Any] = {}
                humanized_seq_pre_reshape: Optional[str] = None
                if sap_check_i.get("action") == "RESHAPE":
                    reshape_i = surface_reshaping_trigger(humanized_seq, hydro_i, strategy_i)
                    if reshape_i.get("success") and reshape_i.get("reshaped_sequence"):
                        humanized_seq_pre_reshape = humanized_seq
                        humanized_seq = reshape_i["reshaped_sequence"]
                        hum_regions = _humanized_regions_for_qa(
                            humanized_seq, species, template, vhh_cdrs
                        )

                candidate_payload = {
                    'template_id': template['template_id'],
                    'source_scaffold': template['source_scaffold'],
                    'safe_plan': template['safe_plan'],
                    'plan_name': template['plan_name'],
                    'panel': panel_i,
                    'humanized_sequence': humanized_seq,
                    'humanized_length': len(humanized_seq),
                    'humanized_regions': hum_regions,
                    'alignment_scores': template['alignment_scores'],
                    'mutations': template.get('mutations', {}),
                    'cdr_compatibility': template.get('cdr_compatibility', {}),
                    'tier_back_mutations': tier_back_muts,
                    'v22_sap_check': sap_check_i,
                    'v22_reshaping': reshape_i if reshape_i else None,
                }
                if humanized_seq_pre_reshape:
                    candidate_payload['humanized_sequence_pre_reshape'] = humanized_seq_pre_reshape
                panel_candidates.append(candidate_payload)

            if not panel_candidates:
                continue

            # panel  combined_score ， best_by_plan
            panel_candidates.sort(key=_candidate_combined_score, reverse=True)
            candidates.extend(panel_candidates)
            best_i = panel_candidates[0]
            best_by_plan[panel_i] = {
                'template_id': best_i['template_id'],
                'humanized_sequence': best_i['humanized_sequence'],
                'humanized_length': best_i['humanized_length'],
                'alignment_scores': best_i['alignment_scores'],
                'safe_plan': best_i['safe_plan'],
                'plan_name': best_i['plan_name'],
                'combined_score': _candidate_combined_score(best_i),
                'cdr_compatibility': best_i.get('cdr_compatibility', {}),
                'v22_sap_check': best_i.get('v22_sap_check'),
                'v22_reshaping': best_i.get('v22_reshaping'),
            }

        if not candidates:
            result['error'] = f"Human（: {panel}，scaffold）"
            return result

        # quality flags:  panel ；ALL  panel 
        if panel_upper == 'ALL':
            result['quality_flags_by_panel'] = quality_flags_by_panel
            # ：
            result['quality_flags'] = quality_flags_by_panel.get('A') or next(iter(quality_flags_by_panel.values()))
            result['_protected_provenance_by_panel'] = protected_provenance_by_panel
        else:
            result['quality_flags'] = quality_flags_by_panel.get(panel_upper, {})
            result["_protected_provenance"] = protected_provenance_by_panel.get(panel_upper, {})
        
        # 6. （overall best）
        candidates.sort(key=_candidate_combined_score, reverse=True)
        best_candidate = candidates[0]
        
        result['success'] = True
        
        # 
        affinity_risk_factors = []
        if scaffold_identity < 0.85:
            affinity_risk_factors.append(f"identity({scaffold_identity:.1%})，CDR")
        if cdr_canonical.get('CDR1', {}).get('canonical_class') == 'non_canonical':
            affinity_risk_factors.append("CDR1，")
        if best_candidate.get('cdr_compatibility', {}).get('key_position_score', 1.0) < 0.9:
            affinity_risk_factors.append("，CDR")
        
        affinity_risk_level = 'high' if len(affinity_risk_factors) >= 2 else 'medium' if len(affinity_risk_factors) >= 1 else 'low'
        
        # 
        scoring = best_candidate['alignment_scores'].get('scoring', {})
        
        # developabilityimmunogenicity
        best_template = None
        for template in human_templates:
            if template['template_id'] == best_candidate['template_id']:
                best_template = template
                break
        
        # developability
        if best_template:
            best_dev_info = best_template.get('developability', {})
            best_dev_score = best_dev_info.get('score', 0.5)
            best_dev_grade = best_dev_info.get('grade', 'C')
            developability_risk = 'high' if best_dev_grade == 'C' or best_dev_score < 0.6 else 'medium' if best_dev_grade == 'B' else 'low'
            developability_notes = f"Grade {best_dev_grade}, Score {best_dev_score:.3f}"
            
            # immunogenicity
            best_immuno_info = best_template.get('immunogenicity', {})
            best_fr_immuno_risk = best_immuno_info.get('fr_immuno_risk', 'low')
            fr_immuno_notes = f"FR immunogenicity risk: {best_fr_immuno_risk}"
        else:
            # 
            best_dev_score = scoring.get('developability_score', 0.5)
            best_dev_grade = 'C' if best_dev_score < 0.6 else 'B' if best_dev_score < 0.8 else 'A'
            developability_risk = 'high' if best_dev_score < 0.6 else 'medium' if best_dev_score < 0.8 else 'low'
            developability_notes = f"Grade {best_dev_grade}, Score {best_dev_score:.3f}"
            best_fr_immuno_risk = 'low'
            fr_immuno_notes = "FR immunogenicity risk: low (default)"
        
        result['best_match'] = {
            'alpaca_scaffold': best_scaffold['scaffold_id'],
            'alpaca_identity': round(scaffold_identity, 3),
            'template': {
                'template_id': best_candidate['template_id'],
                'source_scaffold': best_candidate.get('source_scaffold', ''),
                'safe_plan': best_candidate['safe_plan'],
                'plan_name': best_candidate['plan_name'],
            },
            'humanized_sequence': best_candidate['humanized_sequence'],
            'humanized_length': best_candidate['humanized_length'],
            'alignment_scores': best_candidate['alignment_scores'],
            'safe_plan': best_candidate['safe_plan'],
            'plan_name': best_candidate['plan_name'],
            'combined_score': scoring.get('combined_score', best_candidate['alignment_scores'].get('combined_score', 0)),
            'cdr_compatibility': best_candidate.get('cdr_compatibility', {}),
            'developability': {
                'score': best_dev_score,
                'grade': best_dev_grade,
                'risk': developability_risk,
                'notes': developability_notes,
            },
            'template_id': best_candidate['template_id'],  # template_idprovenance
            'developability_score': scoring.get('developability_score', best_dev_score),
            'immunogenicity': {
                'fr_immuno_risk': best_fr_immuno_risk,
                'fr_hotspot_count': best_template.get('immunogenicity', {}).get('fr_hotspot_count', 0) if best_template else 0,
                'notes': fr_immuno_notes,
            },
            'scoring': scoring,  # 
            'affinity_risk': {
                'level': affinity_risk_level,
                'factors': affinity_risk_factors,
                'recommendation': 'Display（/）'
            },
        }
        
        # 6.5. germline.candidates（，scores.overallprepare_json_data）
        from core.germline_data_builder import build_germline_candidates
        
        # germline（alignment_scores）
        # ：scores.overallprepare_json_datacandidates
        germline_data = build_germline_candidates(
            candidates=all_ranked_templates_for_germline,
            best_match=result['best_match'],
            top_n=10
        )
        result['germline'] = germline_data
        
        # ：germline_selection_proofprepare_json_data，candidates
        
        # panel='all'，
        if panel_upper == 'ALL' and best_by_plan:
            result['best_by_plan'] = best_by_plan
        
        if return_all_templates:
            result['candidates'] = candidates
        else:
            result['candidates'] = candidates[:top_k]

        # Build sequence_analysis for QA system compatibility (VH/VL QA expects this structure)
        _best_hum_regions = best_candidate.get('humanized_regions', {})
        result['sequence_analysis'] = {
            'original_sequence': seq,
            'original_length': len(seq),
            'original_regions': orig_regions_for_qa,
            'humanized_sequence': best_candidate.get('humanized_sequence', ''),
            'humanized_length': best_candidate.get('humanized_length', 0),
            'humanized_regions': _best_hum_regions,
        }
        result['mutations'] = {'list': []}  # Placeholder; VHH QA doesn't need full mutation list

        try:
            from core.vhh.vhh42_reference_loader import annotate_input_vs_vhh42_population
            result["vhh42_benchmark"] = annotate_input_vs_vhh42_population(seq)
        except Exception:
            result["vhh42_benchmark"] = {"available": False, "reason": "optional benchmark skipped"}

        # ── V2.2 （P1-5）─────────────────────────────────────────
        # ： best_candidate  candidate-level 。
        # /， candidate 。
        _best_sap = best_candidate.get("v22_sap_check")
        _best_reshape = best_candidate.get("v22_reshaping")
        if _best_sap is not None:
            result["v22_sap_check"] = _best_sap
        if _best_reshape:
            result["v22_reshaping"] = _best_reshape
            _pre = best_candidate.get("humanized_sequence_pre_reshape")
            if _pre:
                result["best_match"]["humanized_sequence_pre_reshape"] = _pre
        # Align humanized_regions / sequence_analysis with the final string (incl. reshape)
        if result.get("success"):
            _sync_sequence_analysis_with_final_best(result, species)

    except Exception as e:
        result['error'] = f": {e}"
        import traceback
        result['traceback'] = traceback.format_exc()
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# V4.0 
# : docs/VHH_HUMANIZATION_DESIGN_STANDARD.md §3.3 / §4 / §5
# : data/reference/VHH68_reference_stats_v1.json (VHH68_CMC_Benchmark_v1.0)
#           config/tier_system_config.json (Tier 0/1/2 position definitions)
# ═══════════════════════════════════════════════════════════════════════════════

_SAP_THRESHOLDS: Optional[Dict] = None

def _load_sap_thresholds() -> Dict:
    """ VHH68 SAP （V4.0 ）。"""
    global _SAP_THRESHOLDS
    if _SAP_THRESHOLDS is None:
        threshold_path = PROJECT_ROOT / "data" / "reference" / "VHH68_reference_stats_v1.json"
        if threshold_path.exists():
            with open(threshold_path, encoding="utf-8") as f:
                ref = json.load(f)
            sap_stats = (ref.get("metrics_camelid68") or {}).get("SAP_score") or {}
            _SAP_THRESHOLDS = {
                "thresholds": {
                    "p50": {"value": float(sap_stats.get("p50", 0.714)), "tier": "green"},
                    "p75": {"value": float(sap_stats.get("p75", 0.714)), "tier": "yellow"},
                    "p90": {"value": float(sap_stats.get("p90", 0.771)), "tier": "red"},
                },
                "source": "VHH68_CMC_Benchmark_v1.0",
            }
        else:
            # ： V4.0 （p50/p75/p90）
            _SAP_THRESHOLDS = {
                "thresholds": {
                    "p50": {"value": 0.714, "tier": "green"},
                    "p75": {"value": 0.714, "tier": "yellow"},
                    "p90": {"value": 0.771, "tier": "red"},
                }
            }
    return _SAP_THRESHOLDS


def _compute_hydro_patch_max9(seq: str) -> float:
    """
     SAP： 9aa 。
    : F/I/L/M/V/W/Y（ VHH42_reference_stats_v1.json ）。
     [0, 1]（ / ）。
    """
    HYDROPHOBIC = set("FILMVWY")
    if len(seq) < 9:
        return 0.0
    max_score = 0.0
    for i in range(len(seq) - 8):
        window = seq[i:i + 9]
        score = sum(1 for aa in window if aa in HYDROPHOBIC) / 9.0
        if score > max_score:
            max_score = score
    return round(max_score, 3)


def get_cdr3_aware_protected_positions(
    cdr3_len: int,
    strategy: str,
    cdr3_seq: Optional[str] = None,
) -> Dict[str, Any]:
    """
    §3.3 CDR3  Vernier Tier 。

    V4.0 ：
      CDR3 ≤ 6 aa（）: 71、73、78 → S1 （high FR3 contact mode）
      CDR3 7-10 aa（）: 73、78 → S1 （short-loop FR3 mode）
      CDR3 11-17 aa（）:  Tier ，
      CDR3 18-21 aa（）: 73、78 → S2 ，
      CDR3 > 21 aa（）: ""， 49（ Cys ）

    : 42  VHH CDR3 （5-22 aa， 13/16/17 aa）

    Returns:
        {
          "protected_positions": set[int],  #  Kabat 
          "cdr3_tier": "short"|"medium"|"long"|"extra_long",
          "dynamic_upgrades": list[str],    # 
          "strategy": str,
        }
    """
    tier_cfg = json.loads((PROJECT_ROOT / "config" / "tier_system_config.json").read_text(encoding="utf-8"))

    # ：Tier 0（）
    tier0_positions = {int(p) for p in tier_cfg["tier_0_critical"]["positions"]}
    tier1_positions = {int(p) for p in tier_cfg["tier_1_high_priority"]["positions"]}

    # 
    strategy_base: Dict[str, set] = {
        "S1": set(tier0_positions),
        "S2": tier0_positions | tier1_positions,
        "S3": tier0_positions | tier1_positions | {int(p) for p in tier_cfg["tier_2_medium_priority"]["positions"]},
    }

    protected = set(strategy_base.get(strategy, tier0_positions))
    dynamic_upgrades: List[str] = []

    if cdr3_len <= 6:
        cdr3_tier = "short"
        #  CDR3：high FR3 contact mode，71/73/78 
        for pos in (71, 73, 78):
            if pos not in protected:
                protected.add(pos)
                dynamic_upgrades.append(
                    f"Pos {pos}  (CDR3={cdr3_len}aa ≤6, high FR3 contact mode)"
                )
    elif cdr3_len <= 10:
        cdr3_tier = "short"
        #  CDR3：73/78 
        for pos in (73, 78):
            if pos not in protected:
                protected.add(pos)
                dynamic_upgrades.append(
                    f"Pos {pos}  (CDR3={cdr3_len}aa 7-10, short-loop FR3 mode)"
                )
    elif cdr3_len <= 17:
        cdr3_tier = "medium"
        # ，
    elif cdr3_len <= 21:
        cdr3_tier = "long"
        #  CDR3：73/78  S2 
        if strategy in ("S1", "S2"):
            for pos in (73, 78):
                if pos not in protected:
                    protected.add(pos)
                    dynamic_upgrades.append(
                        f"Pos {pos}  (CDR3={cdr3_len}aa 18-21, §3.3  CDR3 , S2 )"
                    )
    else:
        cdr3_tier = "extra_long"
        #  CDR3：， 73/78
        for pos in (73, 78):
            if pos not in protected:
                protected.add(pos)
                dynamic_upgrades.append(
                    f"Pos {pos}  (CDR3={cdr3_len}aa >21, §3.3  CDR3 )"
                )

    # P2-8 refinement (owner request):  CDR3>17 ，
    #  Cys （VHH-specific extra disulfide motif）， 49，
    # 。
    # ：CDR3  >17  cdr3_seq  "C.{1,12}C"（）。
    if cdr3_len > 17:
        has_disulfide_motif = False
        cdr3_text = (cdr3_seq or "").strip().upper()
        try:
            import re
            if cdr3_text and re.search(r"C.{1,12}C", cdr3_text):
                has_disulfide_motif = True
        except Exception:
            pass
        if has_disulfide_motif:
            if 49 not in protected:
                protected.add(49)
                dynamic_upgrades.append(
                    f"Pos 49  (CDR3={cdr3_len}aa >17, CDR3 )"
                )
        elif cdr3_tier == "extra_long":
            dynamic_upgrades.append(
                f"Pos 49 not added (CDR3={cdr3_len}aa >21 but no Cys pair detected)"
            )

    return {
        "protected_positions": protected,
        "cdr3_tier": cdr3_tier,
        "dynamic_upgrades": dynamic_upgrades,
        "strategy": strategy,
        "cdr3_len": cdr3_len,
    }


def check_sap_against_strategy(hydro_patch: float, strategy: str) -> Dict[str, Any]:
    """
    §4.1 + §5 SAP ， S1/S2/S3 。

    V4.0 （data/reference/VHH68_reference_stats_v1.json）:
      （≤ p50=0.714）: ，S3 
      （p50–p75=0.714）: ，S2 ；S3 
      （p75–p90=0.771）: ，S1 ；S2/S3 ，
      （> p90）:  Surface Reshaping

    : VHH68_CMC_Benchmark_v1.0，SAP_score 

    Returns:
        {
          "hydro_patch": float,
          "strategy": str,
          "tier": "green"|"yellow"|"red"|"over_red",
          "pass": bool,
          "action": "PASS"|"WARN"|"RESHAPE",
          "message": str,
          "thresholds": {p50, p75, p90},
        }
    """
    thresholds = _load_sap_thresholds()["thresholds"]
    p50 = thresholds["p50"]["value"]
    p75 = thresholds["p75"]["value"]
    p90 = thresholds["p90"]["value"]

    if hydro_patch <= p50:
        tier = "green"
    elif hydro_patch <= p75:
        tier = "yellow"
    elif hydro_patch <= p90:
        tier = "red"
    else:
        tier = "over_red"

    # -（V2.2 §5）
    strategy_rules = {
        "S1": {"target": p90, "target_name": "p90", "fail_tier": "over_red"},
        "S2": {"target": p75, "target_name": "p75", "fail_tier": "red"},
        "S3": {"target": p50, "target_name": "p50", "fail_tier": "yellow"},
    }
    rule = strategy_rules.get(strategy, strategy_rules["S2"])

    if tier == "green":
        passed, action = True, "PASS"
        msg = f"SAP {hydro_patch} ≤ p50({p50}) — ，。{strategy} 。"
    elif tier == "yellow":
        if strategy == "S3":
            passed, action = False, "RESHAPE"
            msg = f"SAP {hydro_patch} > p50({p50}) — 。S3  ≤p50，。"
        else:
            passed, action = True, "WARN"
            msg = f"SAP {hydro_patch}  (p50={p50}–p75={p75})。{strategy} ，。"
    elif tier == "red":
        if strategy in ("S2", "S3"):
            passed, action = False, "RESHAPE"
            msg = f"SAP {hydro_patch} > p75({p75}) — 。{strategy}  ≤{rule['target_name']}，。"
        else:  # S1
            passed, action = True, "WARN"
            msg = f"SAP {hydro_patch}  (p75={p75}–p90={p90})。S1 ，。"
    else:  # over_red
        passed, action = False, "RESHAPE"
        msg = f"SAP {hydro_patch} > p90({p90}) — 。。"

    return {
        "hydro_patch": hydro_patch,
        "strategy": strategy,
        "tier": tier,
        "pass": passed,
        "action": action,
        "message": msg,
        "thresholds": {"p50": p50, "p75": p75, "p90": p90},
        "standard_ref": "VHH_HUMANIZATION_DESIGN_STANDARD V4.0 §4.1 §5",
        "data_ref": "VHH68_reference_stats_v1.json (VHH68_CMC_Benchmark_v1.0)",
    }


def _build_linear_to_imgt_map(seq: str) -> Tuple[Dict[int, int], Dict[int, str], Optional[str]]:
    """Build linear_index → IMGT(base position) and linear_index → ins_code maps
    using ANARCI numbering. Insertion-code safe: residues at IMGT 111A/112A/...
    are recorded with their base position (111, 112) and a non-empty ins_code,
    so callers can distinguish base-position protected residues from insertions
    that fall on the same numeric label.

    Returns:
        (linear_to_imgt, linear_to_inscode, error_message_or_None)
        - linear_to_imgt[i]   = IMGT base position (int) for seq[i] within the
                                ANARCI-numbered region; absent for residues
                                outside the numbered region (signal peptide,
                                tail tags).
        - linear_to_inscode[i]= IMGT insertion code (' ' for base positions,
                                'A'/'B'/... for insertions).
        - error_message       = None on success; otherwise a short reason
                                string explaining why mapping is unavailable.
    """
    seq_clean = seq.strip().upper().replace(" ", "").replace("\n", "").replace("\r", "")
    if not seq_clean:
        return {}, {}, "empty sequence after cleaning"

    linear_to_imgt: Dict[int, int] = {}
    linear_to_inscode: Dict[int, str] = {}

    try:
        payload = imgt_number_anarcii_indexed(seq_clean)
    except IMGTNumberingError as exc:
        return linear_to_imgt, linear_to_inscode, f"ANARCI numbering failed: {exc}"
    except ImportError as exc:
        return linear_to_imgt, linear_to_inscode, f"ANARCI import failed: {exc}"
    except Exception as exc:  # noqa: BLE001
        return linear_to_imgt, linear_to_inscode, f"ANARCI unexpected error: {exc}"

    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    if not rows:
        return linear_to_imgt, linear_to_inscode, "ANARCI returned no numbered rows"

    for r in rows:
        li = r.get("seq_idx")
        pos = r.get("pos")
        if not isinstance(li, int) or not isinstance(pos, int):
            continue
        if li < 0 or li >= len(seq_clean):
            continue
        linear_to_imgt[li] = int(pos)
        ins = r.get("ins_code", " ")
        linear_to_inscode[li] = str(ins) if ins is not None else " "

    if not linear_to_imgt:
        return linear_to_imgt, linear_to_inscode, "ANARCI mapping is empty after parsing"

    return linear_to_imgt, linear_to_inscode, None


# ── V5.0 (2026-05-16): DeepFR-CTX-VHH 9-mer voting infrastructure ─────────────
_V5_9MER_DB_CACHE: Optional[Dict[str, int]] = None
_V5_HARD_PROTECTED_AA = frozenset("GPC")  # G/P/C: NEVER substitute (V5.0 rule)
_V5_PTM_FORBIDDEN_MOTIFS = frozenset({
    "NG", "NS", "DG", "DP", "QG", "GG", "GP", "NF", "DS",
})
_V5_NEUTRAL_AA = frozenset("ACFGILMNPQSTVWY")
_V5_NEGATIVE_AA = frozenset("DE")
_V5_POSITIVE_AA = frozenset("KRH")


def _v5_load_9mer_db() -> Dict[str, int]:
    """
    Load (cached) clinical 9-mer frequency database for DeepFR-CTX-VHH voting.
    Returns empty dict if DB is unavailable — caller MUST handle this case.
    """
    global _V5_9MER_DB_CACHE
    if _V5_9MER_DB_CACHE is not None:
        return _V5_9MER_DB_CACHE
    db_path = PROJECT_ROOT / "config" / "clinical_842_9mer_db.json"
    try:
        if db_path.exists():
            data = json.loads(db_path.read_text(encoding="utf-8"))
            _V5_9MER_DB_CACHE = data.get("9mers", {}) if isinstance(data, dict) else {}
        else:
            _V5_9MER_DB_CACHE = {}
    except Exception:
        _V5_9MER_DB_CACHE = {}
    return _V5_9MER_DB_CACHE


def _v5_charge_class(aa: str) -> str:
    if aa in _V5_NEGATIVE_AA:
        return "neg"
    if aa in _V5_POSITIVE_AA:
        return "pos"
    return "neu"


def _v5_introduces_ptm_motif(seq: str, pos: int, new_aa: str) -> bool:
    """Check whether mutating seq[pos] to new_aa creates a forbidden dipeptide motif."""
    mutated = seq[:pos] + new_aa + seq[pos + 1:]
    # Check the dipeptide ending at pos and starting at pos
    if pos >= 1 and mutated[pos - 1:pos + 1] in _V5_PTM_FORBIDDEN_MOTIFS:
        return True
    if pos + 2 <= len(mutated) and mutated[pos:pos + 2] in _V5_PTM_FORBIDDEN_MOTIFS:
        return True
    return False


def _v5_vote_for_position(seq: str, target_pos: int, db: Dict[str, int]) -> List[Tuple[str, int]]:
    """
    DeepFR-CTX-VHH 9-mer voting: for the given position, score all 20 amino acids
    by summing the clinical-9-mer frequency over every 9-mer window that overlaps
    target_pos.

    Returns a list of (aa, score) sorted descending by score.
    """
    AAS = "ACDEFGHIKLMNPQRSTVWY"
    scores: Dict[str, int] = {}
    n = len(seq)
    if n < 9 or not db:
        for aa in AAS:
            scores[aa] = 0
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    start_idx = max(0, target_pos - 8)
    end_idx = min(n - 9, target_pos)
    for aa in AAS:
        mutated_seq = seq[:target_pos] + aa + seq[target_pos + 1:]
        total = 0
        for wi in range(start_idx, end_idx + 1):
            total += db.get(mutated_seq[wi:wi + 9], 0)
        scores[aa] = total
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def surface_reshaping_trigger(seq: str, hydro_patch: float, strategy: str) -> Dict[str, Any]:
    """
    Surface Reshaping Protocol — V5.0 (2026-05-16) DeepFR-CTX-VHH 9-aa voting.

    V5.0 Algorithm (replaces V2.2 fixed-substitution table):
      1. Number the input via ANARCI to build linear_index → IMGT(base, ins_code).
      2. Identify FR-region residues in the highest-SAP 9-aa window.
      3. For each candidate position (skip CDR / Tier 0/1 protected / G,P,C):
         - Run 9-mer voting against config/clinical_842_9mer_db.json
         - Filter candidates: must (a) differ from original, (b) not introduce PTM
           motif (NG, NS, DG, DP, QG, GG, GP, NF, DS), (c) not flip charge class,
           (d) reduce local SAP by >= 0.01
         - Pick the highest-voted candidate that passes all filters
      4. If voting DB yields no usable candidate (sparse coverage), fall back to
         the V2.2 conservative substitution table (F→Y, L→S, …).
      5. Iterate up to 10 times or until SAP enters the strategy-permitted band.

    Hard-protected residues (NEVER substituted): G, P, C.

    Coordinate convention (P0-1 fix):
      - In/out of CDR is determined by IMGT base position via the ANARCI map
        (CDR1=27–38, CDR2=56–65, CDR3=105–117). Residues at IMGT 111A/B,
        112A/B/C, etc. are CDR-3 by base position 111/112 and are protected.
      - Protected positions are interpreted as IMGT base positions, matching
        apply_tier_back_mutations() and pos_map.get(44/45/47) usage elsewhere
        in this module. tier_system_config.json names the field "kabat" but
        the runtime semantics across the VHH pipeline are IMGT.
      - Residues outside the ANARCI-numbered region (signal peptide / tail
        tags) are treated as protected (skipped) — conservative default.

    Insertion-code safety (the bug this fixes):
      Pre-fix code used `pos_1 = linear_index + 1` as a Kabat/IMGT proxy. For
      VHH with long CDR3 (≥ 17 aa, IMGT inserts 111A/111B/112A/...), every
      FR3 residue downstream of CDR3 had its linear_index inflated by the
      number of insertions, so Tier 1 positions (e.g. IMGT 71/73/78) were
      no longer recognised as protected and could be edited by reshaping.
      With ANARCI-driven mapping, base position 71/73/78 are protected
      regardless of CDR3 length.

    Returns:
        {
          "success": bool,
          "reshaped_sequence": str,
          "mutations": list[dict],
          "final_sap": float,
          "final_tier": str,
          "iterations": int,
          "note": str,
          "coord_provenance": "imgt_anarcii_v1" | "skipped:<reason>",
        }
    """
    # Tier protection — IMGT base positions (see docstring "Coordinate convention").
    # Pos 37 is in CDR1 (IMGT 27–38) and is preserved by the CDR mask, not Tier 0.
    TIER0_IMGT = {28, 29, 44, 45, 47, 94}
    TIER1_IMGT = {34, 36, 40, 42, 49, 71, 73, 78}
    PROTECTED_IMGT = TIER0_IMGT | TIER1_IMGT

    CDR_IMGT_RANGES = [(27, 38), (56, 65), (105, 117)]

    CONSERVATIVE_SUBS = {
        "F": "Y",  # Phe → Tyr (retain aromatic, add hydroxyl)
        "L": "S",  # Leu → Ser
        "I": "T",  # Ile → Thr (must leave hydrophobic set FILMVWY)
        "M": "Q",  # Met → Gln (must leave hydrophobic set FILMVWY)
        "V": "T",  # Val → Thr
        "W": "Y",  # Trp → Tyr
    }
    HYDROPHOBIC_SET = set("FILMVWY")

    seq_clean = seq.strip().upper().replace(" ", "").replace("\n", "").replace("\r", "")
    if not seq_clean:
        return {
            "success": False,
            "reshaped_sequence": seq,
            "mutations": [],
            "final_sap": float(hydro_patch),
            "final_tier": "unknown",
            "iterations": 0,
            "note": "Surface reshaping skipped: empty sequence.",
            "coord_provenance": "skipped:empty_sequence",
        }

    # ── P0-1: ANARCI-driven linear ↔ IMGT mapping ─────────────────────────────
    linear_to_imgt, linear_to_inscode, map_err = _build_linear_to_imgt_map(seq_clean)
    if map_err is not None:
        # Conservative fallback: refuse to reshape if we cannot trust coordinates.
        # Pre-fix behaviour silently used `linear_index + 1` which corrupted Tier
        # protection for sequences with CDR3 insertions; refusing is safer.
        return {
            "success": False,
            "reshaped_sequence": seq_clean,
            "mutations": [],
            "final_sap": float(hydro_patch),
            "final_tier": "unknown",
            "iterations": 0,
            "note": (
                "Surface reshaping skipped: cannot establish trusted IMGT mapping "
                f"({map_err}). Refusing to edit FR positions without ANARCI-verified "
                "coordinates to avoid silent Tier 0/1 corruption."
            ),
            "coord_provenance": f"skipped:{map_err}",
        }

    def _imgt_pos(li: int) -> Optional[int]:
        return linear_to_imgt.get(li)

    def in_cdr_imgt(li: int) -> bool:
        pos = _imgt_pos(li)
        if pos is None:
            # Unmapped residue — tail tag etc. Treat as "not CDR" but
            # in_protected_imgt() below will block it from edits.
            return False
        return any(lo <= pos <= hi for lo, hi in CDR_IMGT_RANGES)

    def in_protected_imgt(li: int) -> bool:
        pos = _imgt_pos(li)
        if pos is None:
            # Unmapped residue: refuse to edit — could be FR4 tail or tag.
            return True
        # Protect the base position; insertions at protected base positions are
        # by definition CDR loops (e.g. 111A/112A live inside CDR3) and are
        # already excluded by in_cdr_imgt(). Non-CDR insertions do not occur in
        # canonical VHH numbering, but if they did, protecting them is conservative.
        return pos in PROTECTED_IMGT

    seq_list = list(seq_clean)
    mutations: List[Dict] = []
    max_iterations = 10

    for iteration in range(max_iterations):
        current_seq = "".join(seq_list)
        current_hydro = _compute_hydro_patch_max9(current_seq)
        current_check = check_sap_against_strategy(current_hydro, strategy)

        if current_check["action"] != "RESHAPE":
            return {
                "success": True,
                "reshaped_sequence": current_seq,
                "mutations": mutations,
                "final_sap": current_hydro,
                "final_tier": current_check["tier"],
                "iterations": iteration,
                "note": f"Surface reshape converged: {len(mutations)} substitutions, SAP {hydro_patch:.3f}->{current_hydro:.3f}",
                "coord_provenance": "imgt_anarcii_v1",
                "algorithm_version": "V5.0_DeepFR_CTX_VHH_9aa_voting",
                "standard_ref": "VHH_HUMANIZATION_DESIGN_STANDARD V5.0 (2026-05-16)",
            }

        # Locate the highest-SAP 9-aa window, then pick the first eligible
        # substitution within (or after) the window.
        # V5.0: replace fixed CONSERVATIVE_SUBS with DeepFR-CTX-VHH 9-mer voting.
        best_pos: Optional[int] = None
        best_aa: Optional[str] = None
        n = len(seq_list)
        if n >= 9:
            max_w_score, max_w_start = 0.0, 0
            for wi in range(n - 8):
                ws = sum(1 for a in seq_list[wi:wi + 9] if a in HYDROPHOBIC_SET) / 9.0
                if ws > max_w_score:
                    max_w_score, max_w_start = ws, wi
            # V5.0: skip G/P/C hard-protected and only consider hydrophobic residues
            for li in range(max_w_start, max_w_start + 9):
                aa = seq_list[li]
                if aa in _V5_HARD_PROTECTED_AA:
                    continue
                if aa in HYDROPHOBIC_SET and not in_cdr_imgt(li) and not in_protected_imgt(li):
                    best_pos, best_aa = li, aa
                    break
            if best_pos is None:
                for li, aa in enumerate(seq_list):
                    if aa in _V5_HARD_PROTECTED_AA:
                        continue
                    if aa in HYDROPHOBIC_SET and not in_cdr_imgt(li) and not in_protected_imgt(li):
                        best_pos, best_aa = li, aa
                        break

        if best_pos is None or best_aa is None:
            break

        # V5.0 — DeepFR-CTX-VHH 9-mer voting for the substitution AA at best_pos
        current_seq_str = "".join(seq_list)
        _9mer_db = _v5_load_9mer_db()
        ranked = _v5_vote_for_position(current_seq_str, best_pos, _9mer_db)

        sub_aa: Optional[str] = None
        rationale_method: str = ""
        # Compute base SAP for ΔSAP filter
        base_sap_local = _compute_hydro_patch_max9(current_seq_str)
        orig_charge_class = _v5_charge_class(best_aa)

        for cand_aa, cand_votes in ranked:
            if cand_aa == best_aa:
                continue
            if cand_aa in _V5_HARD_PROTECTED_AA:
                continue
            if cand_aa in HYDROPHOBIC_SET:
                continue  # don't swap hydrophobic for another hydrophobic
            if _v5_charge_class(cand_aa) != orig_charge_class:
                continue  # V5.0 charge-class flip forbidden
            if _v5_introduces_ptm_motif(current_seq_str, best_pos, cand_aa):
                continue
            # ΔSAP filter: must reduce local SAP
            mutated_seq = current_seq_str[:best_pos] + cand_aa + current_seq_str[best_pos + 1:]
            new_sap = _compute_hydro_patch_max9(mutated_seq)
            if new_sap >= base_sap_local - 0.01:
                continue
            sub_aa = cand_aa
            rationale_method = (
                f"V5.0 DeepFR-CTX-VHH 9-mer vote ({cand_votes} votes, ΔSAP={new_sap - base_sap_local:.3f})"
                if cand_votes > 0 else
                f"V5.0 9-mer DB sparse — picked first valid neutral non-hydrophobic (ΔSAP={new_sap - base_sap_local:.3f})"
            )
            break

        # V5.0 fallback to V2.2 conservative substitution table when voting yields no candidate
        if sub_aa is None:
            sub_aa = CONSERVATIVE_SUBS.get(best_aa)
            if sub_aa is None:
                break  # no fallback available either
            # Re-check V5.0 hard-protected and PTM rules even on fallback
            if sub_aa in _V5_HARD_PROTECTED_AA:
                break
            if _v5_introduces_ptm_motif(current_seq_str, best_pos, sub_aa):
                break
            rationale_method = "V5.0 fallback: V2.2 conservative substitution table (9-mer DB sparse)"

        ins = (linear_to_inscode.get(best_pos, " ") or " ").strip()
        imgt_pos_int = linear_to_imgt.get(best_pos)
        imgt_label = (
            f"{imgt_pos_int}{ins}" if (imgt_pos_int is not None and ins) else
            (str(imgt_pos_int) if imgt_pos_int is not None else "unmapped")
        )
        mutations.append({
            "position_1indexed": best_pos + 1,
            "imgt_pos": imgt_label,
            "from_aa": best_aa,
            "to_aa": sub_aa,
            "rationale": f"FR surface reshape ({best_aa}->{sub_aa} @ IMGT {imgt_label}): {rationale_method}",
            "standard_ref": "VHH_HUMANIZATION_DESIGN_STANDARD V5.0 §V5.0 Change 5 (DeepFR-CTX-VHH 9aa voting)",
            "method": "deepfr_ctx_vhh_9aa_voting" if "DeepFR-CTX-VHH" in rationale_method else "v22_fallback_table",
        })
        seq_list[best_pos] = sub_aa

    final_seq = "".join(seq_list)
    final_hydro = _compute_hydro_patch_max9(final_seq)
    final_check = check_sap_against_strategy(final_hydro, strategy)

    success = final_check["action"] != "RESHAPE"
    if not mutations:
        note = (
            f"：SAP  CDR  Tier 0/1 ，"
            f" FR 。SAP={final_hydro:.3f} ({final_check['tier']})。"
            f"：（FR ）。"
        )
    else:
        note = (
            f"{'' if success else '（， CDR/）'}："
            f"{len(mutations)}  FR ，SAP {hydro_patch:.3f}→{final_hydro:.3f} ({final_check['tier']})"
        )

    return {
        "success": success,
        "reshaped_sequence": final_seq,
        "mutations": mutations,
        "final_sap": final_hydro,
        "final_tier": final_check["tier"],
        "iterations": max_iterations,
        "note": note,
        "coord_provenance": "imgt_anarcii_v1",
        "algorithm_version": "V5.0_DeepFR_CTX_VHH_9aa_voting",
        "standard_ref": "VHH_HUMANIZATION_DESIGN_STANDARD V5.0 (2026-05-16)",
    }

