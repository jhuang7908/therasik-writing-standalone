"""
VHHQA

（QA Gate），

v3.0：
- FR–CDR/
- CDR grafting
- 
- qa_v3
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# v3.0
from core.vhh_qa_structural_rules import (
    check_cdr1_fr2_compatibility,
    check_cdr3_fr3_compatibility,
    check_cdr2_compatibility
)
from core.vhh_qa_grafting import qa_grafting_impact
from core.vhh_qa_ranking import qa_ranking_sanity
from core.vhh_qa_mutation_map import generate_mutation_map
from core.vhh_qa_conformation_risk import generate_conformation_risk_summary
from core.vhh_qa_experimental_recommendations import generate_experimental_recommendations

# IMGT（）
V_REGION_ORDER = ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]

# IMGT（）
IMGT_REGIONS = {
    "FR1": {"start": 1, "end": 26},
    "CDR1": {"start": 27, "end": 38},
    "FR2": {"start": 39, "end": 55},
    "CDR2": {"start": 56, "end": 65},
    "FR3": {"start": 66, "end": 104},
    "CDR3": {"start": 105, "end": 117},
    "FR4": {"start": 118, "end": 128},
}

# VHH hallmark（IMGT）
# ：IMGT 37  IMGT  CDR1 (27-38)，
#  VHH  Hallmark（ Kabat FR2），
#  split_regions  FR2 ， CDR  Hallmark 。
VHH_HALLMARK_POSITIONS = {
    # 3 FR2 hallmarks only. IMGT 37 is CDR1 (IMGT boundary 27-38) and is
    # preserved unchanged by the FR-only CDR graft — it is NOT a VHH hallmark.
    44: {"region": "FR2", "typical_vhh": ["E", "Q", "D", "G", "A", "S"], "typical_human": ["G"]},
    45: {"region": "FR2", "typical_vhh": ["A", "R", "L", "K", "Q"], "typical_human": ["L"],
         "note": "A is the clinical norm (41/42 approved VHHs); R/L are textbook but rare in practice."},
    47: {"region": "FR2", "typical_vhh": ["F", "Y", "L", "W", "G"], "typical_human": ["W"]},
}

# CDR3 anchor residuesFR3（IMGT 95-102）
CDR3_ANCHOR_RANGE = (95, 102)  # IMGT


def _validate_cdr_fr_only_imgt(result: Dict[str, Any], errors: List[str]) -> None:
    """
    CDR1–3 (IMGT) must be identical between donor and humanized sequence (FR-only policy).
    IMGT CDR1 = 27–38 (includes position 37). All positions in CDR1 must be preserved.
    """
    sa = result.get("sequence_analysis") or {}
    seq_o = (sa.get("original_sequence") or "").strip()
    best = result.get("best_match") or {}
    seq_h = (best.get("humanized_sequence") or "").strip()
    if not seq_o or not seq_h:
        return
    try:
        from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map
        from core.vhh_humanization import split_regions
    except Exception:
        return
    so, sh = seq_o.upper(), seq_h.upper()
    try:
        ro, rh = imgt_number_anarcii(so), imgt_number_anarcii(sh)
    except Exception:
        return
    reg_o = split_regions(ro)
    reg_h = split_regions(rh)
    for c in ("CDR2", "CDR3"):
        a, b = (reg_o.get(c) or ""), (reg_h.get(c) or "")
        if a == b:
            continue
        errors.append(
            f"{c} differs between donor and humanized sequence under IMGT (FR-only graft; CDRs must be identical). "
            "Unintended CDR change or segmentation issue."
        )
    mo, mh = build_pos_to_aa_map(ro), build_pos_to_aa_map(rh)
    cdr1_lo, cdr1_hi = IMGT_REGIONS["CDR1"]["start"], IMGT_REGIONS["CDR1"]["end"]
    for p in range(cdr1_lo, cdr1_hi + 1):
        a, b = mo.get(p), mh.get(p)
        if a == b:
            continue
        errors.append(
            f"CDR1 IMGT position {p} differs (donor {a!r} vs humanized {b!r}). "
            "FR-only policy: CDR1 (IMGT 27-38, including pos 37) must be preserved exactly from donor."
        )
        break


def _collect_fr_differences(orig_regions: Dict[str, str],
                            hum_regions: Dict[str, str]) -> List[Tuple[str, int, str, str]]:
    """
    FR (region_name, local_idx, orig_aa, hum_aa) 
    
    Args:
        orig_regions: 
        hum_regions: 
    
    Returns:
        ， (region_name, local_idx, orig_aa, hum_aa)
        local_idx （0-based）
    """
    diffs: List[Tuple[str, int, str, str]] = []
    for region in ["FR1", "FR2", "FR3", "FR4"]:
        o = (orig_regions or {}).get(region, "") or ""
        h = (hum_regions or {}).get(region, "") or ""
        length = min(len(o), len(h))
        for i in range(length):
            if o[i] != h[i]:
                diffs.append((region, i, o[i], h[i]))
        # ，warning
        if abs(len(o) - len(h)) > 2:
            # ，，
            pass
    return diffs


def rebuild_v_region_from_regions(regions: Dict[str, str]) -> str:
    """
    IMGTFR/CDR，FR4。
    
    Args:
        regions: ，FR1-4CDR1-3
        
    Returns:
        V
    """
    seq_parts = []
    for region in V_REGION_ORDER:
        part = regions.get(region, "")
        if part is None:
            part = ""
        seq_parts.append(part)
    return "".join(seq_parts)


def validate_vhh_humanization_result(result: Dict[str, Any], strict: bool = True) -> Dict[str, Any]:
    """
    VHH。
    
    Args:
        result: （sequence_analysis, mutations）
        strict: （True，error）
    
    Returns:
        {
          "ok": bool,
          "errors": [str],
          "warnings": [str]
        }
    """
    errors = []
    warnings = []
    
    # result
    if "sequence_analysis" not in result:
        errors.append("sequence_analysis")
        return {
            "ok": False,
            "errors": errors,
            "warnings": warnings
        }
    
    seq_analysis = result.get("sequence_analysis", {})
    orig = seq_analysis.get("original_regions", {})
    human = seq_analysis.get("humanized_regions", {})
    
    # 1. FR1–FR4 & CDR1–3
    required_regions = ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]
    for region in required_regions:
        if region not in human:
            errors.append(f" {region} in humanized_regions")
        elif not human.get(region):
            if region == "FR4":
                # FR4
                errors.append(f" {region} （0）- FR4")
            else:
                warnings.append(f" {region} （0）")
    
    # 2. （±3 aa）
    orig_len = len("".join(orig.values())) if orig else 0
    human_len = len("".join(human.values())) if human else 0
    
    if orig_len == 0:
        errors.append("0，")
    elif human_len == 0:
        errors.append("0")
    elif abs(orig_len - human_len) > 3:
        errors.append(
            f": original={orig_len}, humanized={human_len}, "
            f"={abs(orig_len - human_len)}"
        )
    
    # 3. CDR""（VHH FR-only）
    mutations = result.get("mutations", {})
    if isinstance(mutations, dict):
        mut_list = mutations.get("list", [])
    else:
        mut_list = mutations if isinstance(mutations, list) else []
    
    cdr_mut = [m for m in mut_list if m.get("region", "").startswith("CDR")]
    if cdr_mut:
        errors.append(
            f" {len(cdr_mut)} CDR，'FR-only'。"
            f"CDR: {[m.get('position') for m in cdr_mut[:5]]}"
        )
    
    # 4. CDR3（IMGT/VHH，）
    cdr3_len = len(human.get("CDR3", ""))
    if not (2 <= cdr3_len <= 35):
        errors.append(f"CDR3: {cdr3_len}（：2-35 aa）")
    
    # 5. FR2 hallmark（warning，error）
    fr2 = human.get("FR2", "")
    if len(fr2) < 10:
        warnings.append("FR2（<10 aa），")
    
    # 6. FR4
    fr4 = human.get("FR4", "")
    if not fr4:
        errors.append("FR4，FR4")
    elif len(fr4) < 5:
        warnings.append(f"FR4（{len(fr4)} aa），")
    
    # 7. 
    if human:
        rebuilt_seq = rebuild_v_region_from_regions(human)
        best_match = result.get("best_match", {})
        reported_seq = best_match.get("humanized_sequence", "")
        
        if reported_seq and rebuilt_seq.upper() != reported_seq.strip().upper():
            # （）
            if abs(len(rebuilt_seq) - len(reported_seq)) > 3:
                errors.append(
                    f"IMGT region reassembly length mismatch: rebuilt={len(rebuilt_seq)} aa, "
                    f"reported={len(reported_seq)} aa."
                )
            elif len(rebuilt_seq) == len(reported_seq):
                # Same length but different content: region map out of sync with final humanized string
                errors.append(
                    "IMGT region map does not reassemble to the reported humanized sequence (same length, "
                    f"differing content; {len(rebuilt_seq)} aa). Re-segment the final output for QA."
                )
    
    # ===  E1： fallback  ===
    best_match = result.get("best_match", {})
    template = best_match.get("template", {}) or {}
    quality_flags = result.get("quality_flags", {}) or {}
    
    # fallback（quality_flagstemplate）
    if quality_flags.get("uses_fallback_numbering") or quality_flags.get("uses_fallback_fr2"):
        warnings.append(
            "fallbackFR2，。"
        )
    
    # templatefallback
    if isinstance(template, dict):
        template_flags = template.get("flags", {}) or {}
        if template_flags.get("uses_fallback_numbering") or template_flags.get("uses_fallback_fr2"):
            warnings.append(
                "fallbackFR2，。"
            )
    
    # ===  E2： vs FR  ===
    # 
    orig_regions = orig or {}
    hum_regions = human or {}
    
    # FR
    fr_diffs = _collect_fr_differences(orig_regions, hum_regions)
    
    # 
    mutations = result.get("mutations", {})
    if isinstance(mutations, dict):
        mut_list = mutations.get("list", [])
    else:
        mut_list = mutations if isinstance(mutations, list) else []
    
    # FR
    fr_mutations = [m for m in mut_list if m.get("region", "").startswith("FR")]
    
    # 1）FRFR
    if len(fr_diffs) != len(fr_mutations):
        errors.append(
            f"FR ({len(fr_diffs)}) FR "
            f"({len(fr_mutations)}) ，。"
        )
    
    # 2）
    # ：mutationsposition1-basedIMGT，
    for m in fr_mutations:
        region = m.get("region", "")
        pos = m.get("position")  # 1-based IMGT
        orig_aa = m.get("from", "")
        new_aa = m.get("to", "")
        
        if not region or not orig_aa or not new_aa:
            continue
        
        # IMGT（0-based）
        # IMGT
        region_start_positions = {
            "FR1": 1,   # IMGT 1-26
            "CDR1": 27, # IMGT 27-38
            "FR2": 39,  # IMGT 39-55
            "CDR2": 56, # IMGT 56-65
            "FR3": 66,  # IMGT 66-104
            "CDR3": 105, # IMGT 105-117
            "FR4": 118, # IMGT 118+
        }
        
        region_start = region_start_positions.get(region, 0)
        if region_start > 0:
            local_idx = pos - region_start  # （0-based）
            
            # local_idx
            region_seq = hum_regions.get(region, "")
            if 0 <= local_idx < len(region_seq):
                # fr_diffs
                match = any(
                    (d_region == region and d_idx == local_idx and 
                     d_orig == orig_aa and d_hum == new_aa)
                    for (d_region, d_idx, d_orig, d_hum) in fr_diffs
                )
                
                if not match:
                    # （region，）
                    fuzzy_match = any(
                        (d_region == region and d_orig == orig_aa and d_hum == new_aa)
                        for (d_region, _d_idx, d_orig, d_hum) in fr_diffs
                    )
                    
                    if not fuzzy_match:
                        # 
                        orig_region_seq = orig_regions.get(region, "")
                        if local_idx < len(orig_region_seq) and local_idx < len(region_seq):
                            if orig_region_seq[local_idx] == orig_aa and region_seq[local_idx] == new_aa:
                                # ，fr_diffs（）
                                pass
                            else:
                                errors.append(
                                    f" {region} {pos} ({orig_aa}->{new_aa}) FR，"
                                    f": {orig_region_seq[local_idx] if local_idx < len(orig_region_seq) else 'N/A'}->"
                                    f"{region_seq[local_idx] if local_idx < len(region_seq) else 'N/A'}，"
                                    "。"
                                )
    
    # ===  E3：full_sequence  regions  ===
    # humanized_sequence
    hum_full = best_match.get("humanized_sequence", "") or ""
    if hum_full and hum_regions:
        rebuilt = rebuild_v_region_from_regions(hum_regions)
        if hum_full.strip() != rebuilt.strip():
            if abs(len(hum_full.strip()) - len(rebuilt.strip())) > 3:
                errors.append(
                    "humanized_sequence does not match IMGT reassembly of humanized_regions "
                    "(FR1–CDR1–…–FR4) — internal consistency check failed."
                )
    
    # === E4: CDR preservation (FR-only) — IMGT position-wise on donor vs product.
    # Since split_regions now redirects IMGT 37 into FR2 (not CDR1 graft),
    # CDR1 comparison no longer includes position 37 → no conflict expected.
    _validate_cdr_fr_only_imgt(result, errors)
    
    # === QA（） ===
    
    # === 1：FR/CDR（semantic-level QA） ===
    _check_vhh_hallmark_preservation(orig_regions, hum_regions, errors, warnings)
    _check_cdr_canonical_compatibility(result, errors, warnings)
    _check_cdr3_anchor_residues(orig_regions, hum_regions, errors, warnings)
    
    # === 2：immunogenicity/developabilityΔ ===
    _check_developability_immunogenicity_delta(result, errors, warnings)
    
    # === 3：FRQA ===
    _check_fr_selection_strategy(result, errors, warnings)
    
    # === 4：CDR graftingIMGT ===
    _check_imgt_coordinate_consistency(orig_regions, hum_regions, errors, warnings)
    
    return {
        "ok": len(errors) == 0 if strict else True,
        "errors": errors,
        "warnings": warnings,
    }


def _get_aa_at_imgt_position(regions: Dict[str, str], imgt_pos: int) -> Optional[str]:
    """
    IMGTregions
    
    Args:
        regions: 
        imgt_pos: IMGT（1-based）
    
    Returns:
        ，None
    """
    # 
    for region_name, bounds in IMGT_REGIONS.items():
        if bounds["start"] <= imgt_pos <= bounds["end"]:
            region_seq = regions.get(region_name, "")
            if not region_seq:
                return None
            # （0-based）
            local_idx = imgt_pos - bounds["start"]
            if 0 <= local_idx < len(region_seq):
                return region_seq[local_idx]
            return None
    return None


def _check_vhh_hallmark_preservation(
    orig_regions: Dict[str, str],
    hum_regions: Dict[str, str],
    errors: List[str],
    warnings: List[str]
) -> None:
    """
    VHH hallmark
    
    1：FR2（hallmark 44/45/47），fail
    """
    # FR2
    fr2_orig = orig_regions.get("FR2", "")
    fr2_hum = hum_regions.get("FR2", "")
    
    if not fr2_orig or not fr2_hum or len(fr2_hum) < 10:
        # FR2，hallmark
        return
    
    # hallmark
    orig_hallmarks = {}
    for pos, info in VHH_HALLMARK_POSITIONS.items():
        aa = _get_aa_at_imgt_position(orig_regions, pos)
        if aa:
            orig_hallmarks[pos] = aa
    
    # hallmark
    hum_hallmarks = {}
    for pos, info in VHH_HALLMARK_POSITIONS.items():
        aa = _get_aa_at_imgt_position(hum_regions, pos)
        if aa:
            hum_hallmarks[pos] = aa
    
    # hallmark（），
    if not orig_hallmarks and not hum_hallmarks:
        return
    
    # hallmark
    critical_hallmarks = [44, 45, 47]  # 44、45、47
    missing_critical = []
    
    for pos in critical_hallmarks:
        if pos not in hum_hallmarks:
            missing_critical.append(pos)
        elif pos in orig_hallmarks:
            # VHHhuman
            info = VHH_HALLMARK_POSITIONS[pos]
            orig_aa = orig_hallmarks.get(pos, "")
            hum_aa = hum_hallmarks[pos]
            
            # VHH，human，
            if orig_aa in info["typical_vhh"] and hum_aa in info["typical_human"]:
                if pos == 47:  # W，
                    errors.append(
                        f"VHH hallmark{pos}（{info['region']}）VHH{orig_aa}human{hum_aa}，"
                        f"{pos}（W），。。"
                    )
                else:
                    errors.append(
                        f"VHH hallmark{pos}（{info['region']}）VHH{orig_aa}human{hum_aa}，"
                        f"。"
                    )
    
    if missing_critical and len(hum_hallmarks) > 0:
        fr2_len = len(hum_regions.get("FR2", ""))
        if fr2_len >= 10:
            errors.append(
                f"Missing critical VHH hallmark positions: {missing_critical}. "
                "Template FR2 must contain hallmark positions 44/45/47 to support single-domain fold."
            )

    # Check hallmark pattern count (3 positions: IMGT 44/45/47)
    if orig_hallmarks and hum_hallmarks:
        vhh_pattern_count = 0
        for pos in VHH_HALLMARK_POSITIONS.keys():
            if pos in hum_hallmarks:
                hum_aa = hum_hallmarks[pos]
                info = VHH_HALLMARK_POSITIONS[pos]
                if hum_aa in info["typical_vhh"] or hum_aa == "W":
                    vhh_pattern_count += 1

        if vhh_pattern_count < 2:
            warnings.append(
                f"VHH hallmark pattern count is low ({vhh_pattern_count}/3). "
                "The final sequence does not conform to the solubilizing hallmark set (IMGT 44/45/47), "
                "which may increase aggregation risk in single-domain format."
            )


def _check_cdr_canonical_compatibility(
    result: Dict[str, Any],
    errors: List[str],
    warnings: List[str]
) -> None:
    """
    CDRFR
    
    1：VHHCDR？
    """
    cdr_canonical = result.get("cdr_canonical", {})
    if not cdr_canonical:
        warnings.append("CDR canonical conformation data unavailable — CDR–FR compatibility check skipped.")
        return
    
    # CDR1FR
    cdr1_info = cdr_canonical.get("CDR1", {})
    cdr1_len = cdr1_info.get("length", 0)
    
    if cdr1_len == 8:
        warnings.append(
            "CDR1 length is 8 aa — ensure the VH3 template FR1 context supports this canonical family."
        )
    elif cdr1_len not in [6, 7, 8, 9, 10, 11, 12]:
        warnings.append(
            f"CDR1 length {cdr1_len} aa is unusual — verify FR compatibility with structural data if available."
        )
    
    # CDR
    for cdr_name in ["CDR1", "CDR2", "CDR3"]:
        cdr_info = cdr_canonical.get(cdr_name, {})
        canonical_class = cdr_info.get("canonical_class", "")
        
        if canonical_class == "non_canonical":
            warnings.append(
                f"{cdr_name} is non-canonical ({cdr_info.get('length', 0)} aa) — "
                "confirm the human framework can accommodate this loop class."
            )


def _check_cdr3_anchor_residues(
    orig_regions: Dict[str, str],
    hum_regions: Dict[str, str],
    errors: List[str],
    warnings: List[str]
) -> None:
    """
    CDR3 anchor residuesFR3（IMGT 95-102）
    
    1：CDR3 anchor residuesFR3
    """
    # FR3IMGT 66-104，CDR3 anchor95-102
    fr3_start = IMGT_REGIONS["FR3"]["start"]  # 66
    anchor_start, anchor_end = CDR3_ANCHOR_RANGE  # 95, 102
    
    # FR3
    fr3_orig = orig_regions.get("FR3", "")
    fr3_hum = hum_regions.get("FR3", "")
    
    if not fr3_orig or not fr3_hum:
        return
    
    # anchorFR3
    # IMGT 95FR3 = 95 - 66 + 1 = 30 (1-based in FR3) = 29 (0-based)
    anchor_start_in_fr3 = anchor_start - fr3_start  # 95 - 66 = 29 (0-based)
    anchor_end_in_fr3 = anchor_end - fr3_start + 1  # 102 - 66 + 1 = 37 (0-based, exclusive)
    
    if len(fr3_hum) < anchor_end_in_fr3:
        errors.append(
            f"FR3（{len(fr3_hum)}aa），CDR3 anchor residues（IMGT 95-102）。"
            f"CDR3 anchor residuesFR3，。"
        )
        return
    
    # anchor（）
    orig_anchor = fr3_orig[anchor_start_in_fr3:anchor_end_in_fr3] if len(fr3_orig) >= anchor_end_in_fr3 else ""
    hum_anchor = fr3_hum[anchor_start_in_fr3:anchor_end_in_fr3]
    
    if orig_anchor and hum_anchor:
        # 
        differences = sum(1 for i in range(min(len(orig_anchor), len(hum_anchor))) 
                         if orig_anchor[i] != hum_anchor[i])
        
        if differences > 2:  # 
            warnings.append(
                f"CDR3 anchor residues（IMGT 95-102，FR3{anchor_start_in_fr3+1}-{anchor_end_in_fr3}）"
                f"{differences}，CDR3。"
            )


def _check_developability_immunogenicity_delta(
    result: Dict[str, Any],
    errors: List[str],
    warnings: List[str]
) -> None:
    """
    immunogenicity/developabilityΔ
    
    2：，
    Δ Immunogenicity < 0（）
    Δ Developability ≥ 0（）
    """
    best_match = result.get("best_match", {})
    developability = best_match.get("developability", {})
    immunogenicity = best_match.get("immunogenicity", {})
    
    # developabilityimmunogenicity（）
    # ：result
    # ，，
    
    orig_developability = result.get("original_developability", {})
    orig_immunogenicity = result.get("original_immunogenicity", {})
    
    # ，input
    # ，，
    if not orig_developability and not orig_immunogenicity:
        # ，Δ
        return
    
    # developability
    if developability and orig_developability:
        orig_grade = orig_developability.get("grade", "")
        hum_grade = developability.get("grade", "")
        orig_score = orig_developability.get("score", 0.5)
        hum_score = developability.get("score", 0.5)
        
        if orig_grade and hum_grade:
            # ：A > B > C
            grade_order = {"A": 3, "B": 2, "C": 1}
            orig_grade_val = grade_order.get(orig_grade, 0)
            hum_grade_val = grade_order.get(hum_grade, 0)
            
            if hum_grade_val < orig_grade_val:
                errors.append(
                    f"Developability：{orig_grade}{hum_grade}。"
                    f"developability，。"
                )
        
        if orig_score and hum_score and hum_score < orig_score - 0.1:  # 0.1
            warnings.append(
                f"Developability：{orig_score:.2f}{hum_score:.2f}。"
                f"CMC。"
            )
    
    # immunogenicity
    if immunogenicity and orig_immunogenicity:
        orig_risk = orig_immunogenicity.get("fr_immuno_risk", "low")
        hum_risk = immunogenicity.get("fr_immuno_risk", "low")
        
        if orig_risk and hum_risk:
            # ：low < medium < high
            risk_order = {"low": 1, "medium": 2, "high": 3}
            orig_risk_val = risk_order.get(orig_risk, 0)
            hum_risk_val = risk_order.get(hum_risk, 0)
            
            if hum_risk_val > orig_risk_val:
                errors.append(
                    f"Immunogenicity：{orig_risk}{hum_risk}。"
                    f"immunogenicity，。"
                )
            elif hum_risk_val == orig_risk_val and hum_risk == "high":
                warnings.append(
                    f"Immunogenicityhigh，。"
                )


def _check_fr_selection_strategy(
    result: Dict[str, Any],
    errors: List[str],
    warnings: List[str]
) -> None:
    """
    FR
    
    3：
    - top-1FR2VHH hallmark → fail
    - FR identityFR2/FR3 → fail
    - CDR anchor residues → fail
    """
    best_match = result.get("best_match", {})
    if not best_match:
        return
    
    template = best_match.get("template", {})
    scoring = best_match.get("scoring", {})
    
    # FR2 hallmark
    hum_regions = result.get("sequence_analysis", {}).get("humanized_regions", {})
    fr2 = hum_regions.get("FR2", "")
    
    if fr2 and len(fr2) >= 10:
        # FR2VHH hallmark
        # VHH（FR2hallmark）
        orig_regions = result.get("sequence_analysis", {}).get("original_regions", {})
        orig_fr2 = orig_regions.get("FR2", "")
        
        # VHH（hallmark）
        orig_hallmark_count = 0
        if orig_fr2 and len(orig_fr2) >= 10:
            for pos, info in VHH_HALLMARK_POSITIONS.items():
                if info["region"] == "FR2":
                    aa = _get_aa_at_imgt_position(orig_regions, pos)
                    if aa and aa in info["typical_vhh"]:
                        orig_hallmark_count += 1
        
        # VHH（≥2hallmark），
        if orig_hallmark_count >= 2:
            hallmark_count = 0
            for pos, info in VHH_HALLMARK_POSITIONS.items():
                if info["region"] == "FR2":
                    aa = _get_aa_at_imgt_position(hum_regions, pos)
                    if aa and aa in info["typical_vhh"]:
                        hallmark_count += 1
            
            if hallmark_count < 2:
                errors.append(
                    f"VHH{orig_hallmark_count}VHH hallmark，{hallmark_count}（≥2）。"
                    f"FR2，VHH hallmark。VHH hallmark。"
                )
    
    # FR identityFR2/FR3
    if scoring:
        framework_identity = scoring.get("framework_identity", 0)
        if framework_identity > 0.85:  # FR identity
            # FR2/FR3
            cdr_compatibility = best_match.get("cdr_compatibility", {})
            if cdr_compatibility:
                compatibility_score = cdr_compatibility.get("compatibility_score", 1.0)
                
                if compatibility_score < 0.7:  # CDR
                    errors.append(
                        f"FR identity（{framework_identity:.2%}），CDR（{compatibility_score:.2f}），"
                        f"FR2/FR3CDR。。"
                    )


def _check_imgt_coordinate_consistency(
    orig_regions: Dict[str, str],
    hum_regions: Dict[str, str],
    errors: List[str],
    warnings: List[str]
) -> None:
    """
    CDR graftingIMGT
    
    4：
    - CDR1position 26（IMGT 27）
    - CDR250-65（IMGT 56-65）
    - CDR395-102（IMGT 105-117，anchorFR395-102）
    """
    # ，（）
    total_len = sum(len(reg) for reg in orig_regions.values() if reg)
    if total_len < 50:  # ，
        return
    
    # CDR1（IMGT 27，27，1-based）
    fr1_end_imgt = IMGT_REGIONS["FR1"]["end"]  # 26
    
    # FR1
    fr1_orig = orig_regions.get("FR1", "")
    fr1_hum = hum_regions.get("FR1", "")
    
    if fr1_orig and fr1_hum and len(fr1_orig) > 10:  # 
        # FR1IMGT26
        if abs(len(fr1_orig) - 26) > 2 or abs(len(fr1_hum) - 26) > 2:
            errors.append(
                f"FR1：={len(fr1_orig)}aa，={len(fr1_hum)}aa，"
                f"26aa（IMGT 1-26）。CDR1（IMGT 27）。"
            )
    
    # CDR2（IMGT 56）
    fr2_end_imgt = IMGT_REGIONS["FR2"]["end"]  # 55
    
    # FR2
    fr2_orig = orig_regions.get("FR2", "")
    fr2_hum = hum_regions.get("FR2", "")
    
    if fr2_orig and fr2_hum and len(fr2_orig) > 5:  # 
        # FR2IMGT55
        expected_fr2_len = fr2_end_imgt - IMGT_REGIONS["FR2"]["start"] + 1  # 55 - 39 + 1 = 17
        if abs(len(fr2_orig) - expected_fr2_len) > 2 or abs(len(fr2_hum) - expected_fr2_len) > 2:
            warnings.append(
                f"FR2：={len(fr2_orig)}aa，={len(fr2_hum)}aa，"
                f"{expected_fr2_len}aa（IMGT 39-55）。CDR2（IMGT 56）。"
            )
    
    # CDR3（IMGT 105）
    fr3_end_imgt = IMGT_REGIONS["FR3"]["end"]  # 104
    
    # FR3
    fr3_orig = orig_regions.get("FR3", "")
    fr3_hum = hum_regions.get("FR3", "")
    
    if fr3_orig and fr3_hum and len(fr3_orig) > 10:  # 
        # FR3IMGT104
        expected_fr3_len = fr3_end_imgt - IMGT_REGIONS["FR3"]["start"] + 1  # 104 - 66 + 1 = 39
        if abs(len(fr3_orig) - expected_fr3_len) > 3 or abs(len(fr3_hum) - expected_fr3_len) > 3:
            errors.append(
                f"FR3：={len(fr3_orig)}aa，={len(fr3_hum)}aa，"
                f"{expected_fr3_len}aa（IMGT 66-104）。CDR3（IMGT 105）"
                f"CDR3 anchor residues（IMGT 95-102），。"
            )


def validate_vhh_humanization_result_v3(result: Dict[str, Any], strict: bool = True) -> Dict[str, Any]:
    """
    VHHQA v3.0
    
    v2.0，：
    1. FR–CDR/
    2. CDR grafting
    3. 
    4. qa_v3
    
    Args:
        result: 
        strict: （True，error）
    
    Returns:
        qa_v3：
        {
            "ok": bool,
            "errors": [str],
            "warnings": [str],
            "checks": {
                "integrity": {...},          # v2//CDR
                "structural_compat": {...},  # 1
                "grafting_impact": {...},    # 2
                "ranking_sanity": {...},     # 3
                "delta_risk": {...},         # 4
            },
            "summary_score": {
                "biological_feasibility": float,   # 0–100
                "risk_level": "low/medium/high",
            }
        }
    """
    # v2.0
    qa_v2 = validate_vhh_humanization_result(result, strict=False)  # ，
    
    errors = qa_v2.get("errors", [])
    warnings = qa_v2.get("warnings", [])
    
    # v3.0
    checks = {
        "integrity": {
            "ok": len([e for e in errors if "FR4" in e or "CDR" in e or "" in e]) == 0,
            "errors": [e for e in errors if "FR4" in e or "CDR" in e or "" in e],
            "warnings": [w for w in warnings if "FR4" in w or "" in w]
        },
        "structural_compat": {},
        "grafting_impact": {},
        "ranking_sanity": {},
        "delta_risk": {}
    }
    
    seq_analysis = result.get("sequence_analysis", {})
    orig_regions = seq_analysis.get("original_regions", {})
    hum_regions = seq_analysis.get("humanized_regions", {})
    
    # === 1：FR–CDR/ ===
    structural_errors = []
    structural_warnings = []
    
    if orig_regions and hum_regions:
        cdr1_len = len(hum_regions.get("CDR1", ""))
        cdr2_len = len(hum_regions.get("CDR2", ""))
        cdr3_len = len(hum_regions.get("CDR3", ""))
        fr2_len = len(hum_regions.get("FR2", ""))
        fr3_len = len(hum_regions.get("FR3", ""))
        
        # CDR1–FR2 
        if cdr1_len > 0 and fr2_len > 0:
            # v3.2：fail
            # VHHCDR1=5aa，FR2=13aa（15-19aa）
            if cdr1_len < 5 or fr2_len < 13:
                structural_errors.append(
                    f"CDR1–FR2VHH: CDR1={cdr1_len}aa（5aa），"
                    f"FR2={fr2_len}aa（13aa，15-19aa）。"
                    f"，fail。"
                )
            else:
                is_compat, note, rule_strength = check_cdr1_fr2_compatibility(cdr1_len, fr2_len)
                if not is_compat:
                    structural_warnings.append(
                        f"CDR1 ={cdr1_len}  FR2 ={fr2_len} ，"
                        f"。"
                        f"（: {rule_strength}，: 73VHH）"
                    )
        
        # CDR3–FR3 （CDR3）
        if cdr3_len > 0 and fr3_len > 0:
            is_compat, note, rule_strength = check_cdr3_fr3_compatibility(cdr3_len, fr3_len)
            if not is_compat:
                if cdr3_len >= 15 and fr3_len < 38:
                    structural_errors.append(
                        f"CDR3  ({cdr3_len} aa)， FR3  {fr3_len} aa，"
                        "， CDR3。"
                        "（，: 73VHH，）"
                    )
                else:
                    structural_warnings.append(
                        f"CDR3 ={cdr3_len}  FR3 ={fr3_len} ，"
                        f"。（: {rule_strength}）"
                    )
        
        # CDR2 
        if cdr2_len > 0 and fr2_len > 0 and fr3_len > 0:
            is_compat, note, rule_strength = check_cdr2_compatibility(cdr2_len, fr2_len, fr3_len)
            if not is_compat:
                structural_warnings.append(
                    f"CDR2 ={cdr2_len}  FR2/FR3 ，。"
                    f"（: {rule_strength}）"
                )
    
    checks["structural_compat"] = {
        "ok": len(structural_errors) == 0,
        "errors": structural_errors,
        "warnings": structural_warnings
    }
    errors.extend(structural_errors)
    warnings.extend(structural_warnings)
    
    # === 2：CDR grafting ===
    grafting_errors = []
    grafting_warnings = []
    impact_details = {}
    
    if orig_regions and hum_regions:
        grafting_errors, grafting_warnings, impact_details = qa_grafting_impact(
            orig_regions, hum_regions
        )
    
    checks["grafting_impact"] = {
        "ok": len(grafting_errors) == 0,
        "errors": grafting_errors,
        "warnings": grafting_warnings,
        "impact_score": impact_details.get("impact_score", 0),
        "impact_score_normalized": impact_details.get("impact_score_normalized", 0),
        "interface_changes": impact_details.get("interface_changes", []),
        "total_interface_positions": impact_details.get("total_interface_positions", 0),
        "thresholds": impact_details.get("thresholds", {})
    }
    errors.extend(grafting_errors)
    warnings.extend(grafting_warnings)
    
    # === 3： ===
    ranking_errors = []
    ranking_warnings = []
    ranking_details = {}
    
    candidates = result.get("candidates", [])
    if candidates:
        # candidatescombined_score
        sorted_candidates = sorted(
            candidates,
            key=lambda x: (x.get("alignment_scores", {}).get("combined_score", 0) or 
                          x.get("scores", {}).get("combined_score", 0)),
            reverse=True
        )
        
        ranking_errors, ranking_warnings, ranking_details = qa_ranking_sanity(sorted_candidates)
    
    checks["ranking_sanity"] = {
        "ok": len(ranking_errors) == 0,
        "errors": ranking_errors,
        "warnings": ranking_warnings,
        "ranking_issues": ranking_details.get("ranking_issues", [])
    }
    errors.extend(ranking_errors)
    warnings.extend(ranking_warnings)
    
    # === 4：Δ Developability / Δ Immunogenicity  ===
    delta_errors = []
    delta_warnings = []
    delta_details = {}
    
    best_match = result.get("best_match", {})
    developability = best_match.get("developability", {})
    immunogenicity = best_match.get("immunogenicity", {})
    
    # 
    orig_developability = result.get("original_developability", {})
    orig_immunogenicity = result.get("original_immunogenicity", {})
    
    if developability and orig_developability:
        # score
        score_type = developability.get("score_type", "aggregate")  # 
        orig_score = orig_developability.get("score", 0.5)
        hum_score = developability.get("score", 0.5)
        delta_dev = hum_score - orig_score
        
        # （300VHHbenchmarking）
        DELTA_DEV_THRESHOLDS = {
            "warning_major": -0.1,  # 
            "warning_minor": -0.05,  # 
            "based_on": "Internal benchmarking of 300 VHH cases",
            "score_type": score_type,
            "confidence_interval": "±0.02"  # 
        }
        
        delta_details["developability"] = {
            "original": orig_score,
            "humanized": hum_score,
            "delta": delta_dev,
            "score_type": score_type,
            "thresholds": DELTA_DEV_THRESHOLDS
        }
        
        if delta_dev < DELTA_DEV_THRESHOLDS["warning_major"]:
            delta_warnings.append(
                f" developability  (Δ={delta_dev:.3f})，"
                f" {orig_score:.3f}  {hum_score:.3f}，。"
                f"（300VHHbenchmarking）"
            )
        elif delta_dev < DELTA_DEV_THRESHOLDS["warning_minor"]:
            delta_warnings.append(
                f" developability  (Δ={delta_dev:.3f})，CMC。"
            )
    
    if immunogenicity and orig_immunogenicity:
        # ：low=1, medium=2, high=3
        risk_order = {"low": 1, "medium": 2, "high": 3}
        orig_risk = orig_immunogenicity.get("fr_immuno_risk", "low")
        hum_risk = immunogenicity.get("fr_immuno_risk", "low")
        
        orig_risk_val = risk_order.get(orig_risk, 1)
        hum_risk_val = risk_order.get(hum_risk, 1)
        delta_imm = hum_risk_val - orig_risk_val
        
        delta_details["immunogenicity"] = {
            "original": orig_risk,
            "humanized": hum_risk,
            "delta": delta_imm
        }
        
        if delta_imm > 0:  # 
            delta_errors.append(
                f" (Δ={delta_imm})，"
                f" {orig_risk}  {hum_risk}，。"
            )
        elif delta_imm == 0 and hum_risk == "high":
            delta_warnings.append(
                f" high，。"
            )
    
    checks["delta_risk"] = {
        "ok": len(delta_errors) == 0,
        "errors": delta_errors,
        "warnings": delta_warnings,
        "delta_details": delta_details
    }
    errors.extend(delta_errors)
    warnings.extend(delta_warnings)
    
    # === summary_score ===
    # （0-100）
    biological_feasibility = 100.0
    
    # 
    if len(errors) > 0:
        biological_feasibility -= min(50, len(errors) * 10)  # error10，50
    
    if len(warnings) > 0:
        biological_feasibility -= min(30, len(warnings) * 3)  # warning3，30
    
    # grafting impact（）
    impact_score_norm = impact_details.get("impact_score_normalized", 0)
    if impact_score_norm >= 0.4:  # ERROR
        biological_feasibility -= 20
    elif impact_score_norm >= 0.2:  # WARNING
        biological_feasibility -= 10
    
    biological_feasibility = max(0, biological_feasibility)
    
    # 
    if biological_feasibility >= 80:
        risk_level = "low"
    elif biological_feasibility >= 60:
        risk_level = "medium"
    else:
        risk_level = "high"
    
    summary_score = {
        "biological_feasibility": round(biological_feasibility, 1),
        "risk_level": risk_level
    }
    
    # ===  ===
    qa_v3_metadata = {
        "version": "3.2.0",
        "rules_version": "3.2.0",
        "rules_source": [
            "SAbDab VHH canonical classes",
            "IMGT numbering notes",
            "Internal VHH structure database (73 alpaca VHH cases)",
            "Internal VHH grafting case statistics (300 cases)",
            "Human VH3 VHH-SAFE template panel statistics"
        ],
        "scope": "VHH humanization (Human VH3 VHH-SAFE template panel)",
        "customizable": False,
        "thresholds": {
            "structural_compat": {
                "cdr3_long_fr3_short_error": "CDR3≥15aa + FR3<38aa",
                "rule_strength": {
                    "strong": "CDR3",
                    "weak": ""
                }
            },
            "grafting_impact": {
                "error": 0.4,  # normalized
                "warning": 0.2,  # normalized
                "based_on": "Internal benchmarking of 300 VHH cases"
            },
            "developability_delta": {
                "warning_major": -0.1,
                "warning_minor": -0.05,
                "based_on": "Internal benchmarking of 300 VHH cases"
            },
            "ranking_sanity": {
                "fr_identity_diff": 0.05,
                "combined_score_diff": 0.02,
                "impact_score_normalized_diff": 0.15
            }
        }
    }
    
    # === （mutation map）===
    mutation_map = {}
    if orig_regions and hum_regions:
        mutations_list = result.get("mutations", {}).get("list", [])
        template_info = result.get("best_match", {}).get("template", {})
        mutation_map = generate_mutation_map(
            orig_regions, hum_regions, mutations_list, template_info
        )
    
    # ===  ===
    conformation_risk = generate_conformation_risk_summary(hum_regions, None)  # qa_v3，
    
    # ===  ===
    # qa_v3
    temp_qa_v3 = {
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "summary_score": summary_score
    }
    experimental_recommendations = generate_experimental_recommendations(
        temp_qa_v3, conformation_risk
    )
    
    # qa_v3
    qa_v3 = {
        "ok": len(errors) == 0 if strict else True,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "summary_score": summary_score,
        "metadata": qa_v3_metadata,
        "mutation_map": mutation_map,
        "conformation_risk_summary": conformation_risk,
        "experimental_recommendations": experimental_recommendations
    }
    
    return qa_v3

