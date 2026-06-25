"""
VHH  v1.0

：
-  CDR2/CDR3 
- （、、CDR3）
-  developability/CMC/
-  mild/moderate/aggressive 

：
-  CDR2 / CDR3 ， CDR3（VHH ）
- ：  developability/CMC/ ：
  - （Y/W/F/H）
  - （K/R/E/D）
  -  CDR3 （G/P ）
- " – "
-  mild / moderate / aggressive 
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Tuple, Optional


AROMATIC_SET = {"Y", "W", "F", "H"}
POS_CHARGED = {"K", "R", "H"}
NEG_CHARGED = {"D", "E"}
HYDROPHOBIC = {"F", "W", "Y", "L", "I", "V", "M"}
FLEXIBLE = {"G", "S"}
RIGID = {"P"}


@dataclass
class Hotspot:
    position: int          # 1-based
    aa: str
    region: str            # FR/CDR1/CDR2/CDR3...
    region_type: str       # "CDR" / "FR"
    score: float
    features: Dict[str, Any]


@dataclass
class MutationCandidate:
    position: int
    from_aa: str
    to_aa: str
    region: str
    region_type: str
    affinity_gain_score: float
    risk_penalty: float
    net_score: float
    rationale: str


@dataclass
class AffinityVariant:
    name: str              # mild_1 / moderate_1 / aggressive_1
    sequence: str
    mutations: List[MutationCandidate]
    predicted_affinity_score: float
    developability_penalty: float
    cmc_penalty: float
    immunogenicity_penalty: float
    overall_score: float


# -------------------------
# 1) Hotspot Identification
# -------------------------

def identify_affinity_hotspots(
    sequence: str,
    segmentation: Dict[str, Any],
    qa: Dict[str, Any],
) -> List[Hotspot]:
    """
     + segmentation（IMGT ） VHH 。
     CDR2 / CDR3，、、/。
    
    Args:
        sequence: 
        segmentation: （ sequence_analysis.original_regions  regions）
        qa: QA （，）
    
    Returns:
        ， score 
    """
    #  regions
    regions_dict = {}
    
    # 1:  sequence_analysis.original_regions
    seq_analysis = segmentation.get("sequence_analysis", {}) or {}
    orig_regions = seq_analysis.get("original_regions", {}) or {}
    if orig_regions:
        regions_dict = orig_regions
    
    # 2:  regions 
    if not regions_dict:
        regions_list = segmentation.get("regions", [])
        if regions_list:
            for r in regions_list:
                name = r.get("name", "")
                seq = r.get("sequence", "")
                if name and seq:
                    regions_dict[name] = seq
    
    # 3:  regions 
    if not regions_dict:
        regions_dict = segmentation.get("regions", {}) or {}
    
    if not regions_dict:
        return []
    
    hotspots: List[Hotspot] = []
    
    # （）
    region_order = ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]
    current_pos = 1
    
    for region_name in region_order:
        if region_name not in regions_dict:
            continue
        
        seq = regions_dict[region_name]
        if not seq:
            continue
        
        region_type = "CDR" if "CDR" in region_name.upper() else "FR"
        
        #  CDR 
        if region_type != "CDR":
            current_pos += len(seq)
            continue
        
        # 
        for i, aa in enumerate(seq):
            pos = current_pos + i  # （1-based）
            features = _compute_local_features(sequence, pos)
            score = _compute_hotspot_score(region_name, aa, features)
            
            if score > 0:
                hotspots.append(
                    Hotspot(
                        position=pos,
                        aa=aa,
                        region=region_name,
                        region_type=region_type,
                        score=score,
                        features=features,
                    )
                )
        
        current_pos += len(seq)
    
    #  score 
    hotspots.sort(key=lambda h: h.score, reverse=True)
    return hotspots


def _compute_local_features(sequence: str, pos: int) -> Dict[str, Any]:
    """ pos （，）."""
    L = len(sequence)
    idx = pos - 1
    
    if idx < 0 or idx >= L:
        return {
            "aa": "-",
            "left": "-",
            "right": "-",
            "is_aromatic": False,
            "is_pos_charged": False,
            "is_neg_charged": False,
            "is_hydrophobic": False,
            "is_flexible": False,
            "is_rigid": False,
            "neighbor_aromatic_count": 0,
        }
    
    aa = sequence[idx]
    left = sequence[idx - 1] if idx - 1 >= 0 else "-"
    right = sequence[idx + 1] if idx + 1 < L else "-"
    
    features = {
        "aa": aa,
        "left": left,
        "right": right,
        "is_aromatic": aa in AROMATIC_SET,
        "is_pos_charged": aa in POS_CHARGED,
        "is_neg_charged": aa in NEG_CHARGED,
        "is_hydrophobic": aa in HYDROPHOBIC,
        "is_flexible": aa in FLEXIBLE,
        "is_rigid": aa in RIGID,
        "neighbor_aromatic_count": sum(
            1 for x in (left, right) if x in AROMATIC_SET
        ),
    }
    return features


def _compute_hotspot_score(region_name: str, aa: str, feat: Dict[str, Any]) -> float:
    """
     VHH CDR ""。
     = 。
    """
    score = 0.0
    
    # CDR3 > CDR2 > CDR1
    if "CDR3" in region_name.upper():
        score += 1.5
    elif "CDR2" in region_name.upper():
        score += 1.0
    else:
        score += 0.5
    
    # ， ⇒  Y/W/F/H
    if not feat["is_aromatic"] and feat["neighbor_aromatic_count"] == 0:
        score += 1.0
    
    # （G/S） ⇒  aromatic 
    if feat["is_flexible"]:
        score += 0.5
    
    # ， ⇒ ，
    if feat["is_hydrophobic"] and all(
        n in HYDROPHOBIC or n == "-" for n in (feat["left"], feat["right"])
    ):
        score -= 0.5
    
    return max(score, 0.0)


# -------------------------
# 2) Mutation Proposals
# -------------------------

def generate_affinity_mutation_candidates(
    sequence: str,
    hotspots: List[Hotspot],
    max_candidates_per_hotspot: int = 3,
) -> List[MutationCandidate]:
    """
     hotspot 。
    （）
    
    Args:
        sequence: 
        hotspots: 
        max_candidates_per_hotspot: 
    
    Returns:
        ， net_score 
    """
    candidates: List[MutationCandidate] = []
    
    for h in hotspots:
        aa = h.aa
        pos = h.position
        
        # 1)  ⇒  Y/W/F/H
        if aa not in AROMATIC_SET:
            for to_aa in ["Y", "W", "F", "H"]:
                cand = _build_mutation_candidate(
                    from_aa=aa,
                    to_aa=to_aa,
                    hotspot=h,
                    base_gain=1.0,
                    rationale="Introduce aromatic residue to enhance paratope-epitope interactions.",
                )
                candidates.append(cand)
        
        # 2)  Gly/Ser ⇒  P  loop （CDR3 ）
        if aa in {"G", "S"} and "CDR3" in h.region.upper():
            cand = _build_mutation_candidate(
                from_aa=aa,
                to_aa="P",
                hotspot=h,
                base_gain=0.8,
                rationale="Rigidify CDR3 apex with Proline.",
            )
            candidates.append(cand)
        
        # 3) ， charge tuning（，）
        # 
    
    #  + 
    uniq: Dict[Tuple[int, str, str], MutationCandidate] = {}
    for c in candidates:
        key = (c.position, c.from_aa, c.to_aa)
        if key not in uniq or c.net_score > uniq[key].net_score:
            uniq[key] = c
    
    result = list(uniq.values())
    result.sort(key=lambda x: x.net_score, reverse=True)
    
    if max_candidates_per_hotspot > 0:
        #  position ， N 
        grouped: Dict[int, List[MutationCandidate]] = {}
        for c in result:
            grouped.setdefault(c.position, []).append(c)
        
        final: List[MutationCandidate] = []
        for pos, lst in grouped.items():
            final.extend(lst[:max_candidates_per_hotspot])
        #  net_score 
        final.sort(key=lambda x: x.net_score, reverse=True)
        return final
    
    return result


def _build_mutation_candidate(
    from_aa: str,
    to_aa: str,
    hotspot: Hotspot,
    base_gain: float,
    rationale: str,
) -> MutationCandidate:
    """
     hotspot score + base_gain  affinity_gain_score，。
    """
    affinity_gain_score = base_gain * hotspot.score
    #  0， filter 
    risk_penalty = 0.0
    net_score = affinity_gain_score - risk_penalty
    
    return MutationCandidate(
        position=hotspot.position,
        from_aa=from_aa,
        to_aa=to_aa,
        region=hotspot.region,
        region_type=hotspot.region_type,
        affinity_gain_score=affinity_gain_score,
        risk_penalty=risk_penalty,
        net_score=net_score,
        rationale=rationale,
    )


# -------------------------
# 3) （ dev/cmc/imm）
# -------------------------

def filter_mutations_by_global_risk(
    sequence: str,
    candidates: List[MutationCandidate],
    developability: Dict[str, Any],
    cmc: Dict[str, Any],
    imm: Dict[str, Any],
) -> List[MutationCandidate]:
    """
     developability/CMC/。
     heuristics：
      -  N-X-S/T motif
      -  CMC hotspot 
      - （）
    
    Args:
        sequence: 
        candidates: 
        developability: developability 
        cmc: CMC 
        imm: 
    
    Returns:
        ， net_score 
    """
    #  CMC hotspots 
    cmc_positions = set()
    cmc_data = cmc or {}
    
    # 
    hotspots = cmc_data.get("hotspots", []) or []
    if isinstance(hotspots, list):
        for h in hotspots:
            if isinstance(h, dict):
                pos = h.get("position") or h.get("pos")
                if pos:
                    cmc_positions.add(int(pos))
            elif isinstance(h, (int, str)):
                try:
                    cmc_positions.add(int(h))
                except (ValueError, TypeError):
                    pass
    
    L = len(sequence)
    filtered: List[MutationCandidate] = []
    
    for c in candidates:
        idx = c.position - 1
        # 
        if idx < 0 or idx >= L:
            continue
        
        # 1)  N-X-S/T motif
        new_seq_list = list(sequence)
        new_seq_list[idx] = c.to_aa
        new_seq = "".join(new_seq_list)
        risk_penalty = 0.0
        
        if _creates_nglyc_motif(new_seq, c.position):
            risk_penalty += 1.5  # 
        
        # 2)  CMC hotspot，
        if c.position in cmc_positions or (c.position - 1) in cmc_positions or (c.position + 1) in cmc_positions:
            risk_penalty += 0.7
        
        # 3) ：，
        if c.to_aa in AROMATIC_SET:
            left = sequence[idx - 1] if idx - 1 >= 0 else "-"
            right = sequence[idx + 1] if idx + 1 < L else "-"
            if left in HYDROPHOBIC and right in HYDROPHOBIC:
                risk_penalty += 0.5
        
        # 
        c.risk_penalty = risk_penalty
        c.net_score = c.affinity_gain_score - risk_penalty
        
        # 
        if c.net_score > 0.1:
            filtered.append(c)
    
    # 
    filtered.sort(key=lambda x: x.net_score, reverse=True)
    return filtered


def _creates_nglyc_motif(seq: str, pos: int) -> bool:
    """
     N-X-S/T motif (N-linked glycosylation risk).
    pos: 1-based
    """
    L = len(seq)
    idx = pos - 1
    
    if idx < 0 or idx + 2 >= L:
        return False
    
    #  N-X-S/T
    if idx >= 0 and idx + 2 < L:
        tri = seq[idx : idx + 3]
        if len(tri) == 3 and tri[0] == "N" and tri[2] in {"S", "T"}:
            return True
    
    #  N-X-S/T（ S/T）
    if idx - 2 >= 0:
        tri = seq[idx - 2 : idx + 1]
        if len(tri) == 3 and tri[0] == "N" and tri[2] in {"S", "T"}:
            return True
    
    #  N-X-S/T（ N）
    if idx + 2 < L:
        tri = seq[idx : idx + 3]
        if len(tri) == 3 and tri[0] == "N" and tri[2] in {"S", "T"}:
            return True
    
    return False


# -------------------------
# 4)  → 
# -------------------------

def construct_affinity_variants(
    sequence: str,
    mutations: List[MutationCandidate],
    mild_max_mut: int = 2,
    moderate_max_mut: int = 4,
    aggressive_max_mut: int = 7,
) -> Dict[str, List[AffinityVariant]]:
    """
    ：
      - mild  ： net_score  top N（）
      - moderate： k 
      - aggressive：
    
    Args:
        sequence: 
        mutations: 
        mild_max_mut: mild 
        moderate_max_mut: moderate 
        aggressive_max_mut: aggressive 
    
    Returns:
         mild/moderate/aggressive 
    """
    variants: Dict[str, List[AffinityVariant]] = {
        "mild": [],
        "moderate": [],
        "aggressive": [],
    }
    
    # 、 pos 
    mutations_sorted = sorted(mutations, key=lambda m: m.net_score, reverse=True)
    
    def _build_variant(name: str, max_mut: int) -> Optional[AffinityVariant]:
        used_positions = set()
        chosen: List[MutationCandidate] = []
        seq_list = list(sequence)
        
        for m in mutations_sorted:
            if len(chosen) >= max_mut:
                break
            if m.position in used_positions:
                continue
            used_positions.add(m.position)
            chosen.append(m)
            seq_list[m.position - 1] = m.to_aa
        
        if not chosen:
            return None
        
        new_seq = "".join(seq_list)
        #  proxy： = ∑ net_score
        predicted_affinity_score = sum(m.net_score for m in chosen)
        # ： dev/cmc/imm penalty 
        dev_penalty = 0.0
        cmc_penalty = 0.0
        imm_penalty = 0.0
        overall_score = predicted_affinity_score - (dev_penalty + cmc_penalty + imm_penalty)
        
        return AffinityVariant(
            name=name,
            sequence=new_seq,
            mutations=chosen,
            predicted_affinity_score=predicted_affinity_score,
            developability_penalty=dev_penalty,
            cmc_penalty=cmc_penalty,
            immunogenicity_penalty=imm_penalty,
            overall_score=overall_score,
        )
    
    mild_variant = _build_variant("mild_1", mild_max_mut)
    if mild_variant:
        variants["mild"].append(mild_variant)
    
    moderate_variant = _build_variant("moderate_1", moderate_max_mut)
    if moderate_variant:
        variants["moderate"].append(moderate_variant)
    
    aggressive_variant = _build_variant("aggressive_1", aggressive_max_mut)
    if aggressive_variant:
        variants["aggressive"].append(aggressive_variant)
    
    return variants


# -------------------------
# 5) ： v1.0
# -------------------------

def run_affinity_optimization_v1(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    ： VHH pipeline result（ segmentation / qa / developability / cmc / immunogenicity）
    ：affinity ， result["affinity"]
    
    Args:
        result:  VHH 
    
    Returns:
        ，：
        - hotspots: 
        - candidates: 
        - variants: mild/moderate/aggressive 
        - narrative: 
    """
    seq = result.get("input", {}).get("sequence", "")
    if not seq:
        # 
        best_match = result.get("best_match", {}) or {}
        seq = best_match.get("humanized_sequence", "") or best_match.get("sequence", "")
    
    #  segmentation
    segmentation = result.get("segmentation", {}) or {}
    if not segmentation:
        #  sequence_analysis 
        seq_analysis = result.get("sequence_analysis", {}) or {}
        if seq_analysis:
            segmentation = {"sequence_analysis": seq_analysis}
        else:
            # ， best_match 
            #  original_regions 
            pass
    
    qa = result.get("qa", {}) or {}
    dev = result.get("developability", {}) or {}
    cmc = result.get("cmc", {}) or {}
    imm = result.get("immunogenicity", {}) or {}
    
    if not seq:
        return {
            "hotspots": [],
            "candidates": [],
            "variants": {},
            "narrative": "，。",
        }
    
    if not segmentation:
        return {
            "hotspots": [],
            "candidates": [],
            "variants": {},
            "narrative": "IMGT，。",
        }
    
    hotspots = identify_affinity_hotspots(seq, segmentation, qa)
    raw_candidates = generate_affinity_mutation_candidates(seq, hotspots)
    filtered_candidates = filter_mutations_by_global_risk(seq, raw_candidates, dev, cmc, imm)
    variants = construct_affinity_variants(seq, filtered_candidates)
    
    summary = _summarize_affinity_optimization(hotspots, filtered_candidates, variants)
    
    return {
        "hotspots": [asdict(h) for h in hotspots],
        "candidates": [asdict(c) for c in filtered_candidates],
        "variants": {
            k: [asdict(v) for v in vs] for k, vs in variants.items()
        },
        "narrative": summary,
    }


def _summarize_affinity_optimization(
    hotspots: List[Hotspot],
    candidates: List[MutationCandidate],
    variants: Dict[str, List[AffinityVariant]],
) -> str:
    """"""
    if not hotspots:
        return "CDR，。"
    
    n_hot = len(hotspots)
    n_cand = len(candidates)
    n_mild = len(variants.get("mild", []))
    n_mod = len(variants.get("moderate", []))
    n_aggr = len(variants.get("aggressive", []))
    
    parts = []
    parts.append(
        f"VHHCDR， {n_hot} ，"
        f" {n_cand} 。"
    )
    
    if n_mild or n_mod or n_aggr:
        parts.append(
            f"CMC、developability，："
            f"mild（{n_mild} ）、moderate（{n_mod} ）、aggressive（{n_aggr} ）。"
        )
        parts.append(
            "mild、CMC；"
            "moderateaggressive、CMC。"
        )
    else:
        parts.append(
            "，CMC/，"
            "。"
        )
    
    return " ".join(parts)


# 
if __name__ == "__main__":
    # ： result.json 
    import json
    from pathlib import Path
    
    # 
    example_result = {
        "input": {
            "sequence": "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS",
        },
        "sequence_analysis": {
            "original_regions": {
                "FR1": "QVQLVESGGGLVQVGGSLRLSRALS",
                "CDR1": "GFWYNH",
                "FR2": "MGWFRQAPGKEREGVAV",
                "CDR2": "ITADSGST",
                "FR3": "TYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYC",
                "CDR3": "AAGGVGWPYFDY",
                "FR4": "WGQGTQVTVSS",
            },
        },
        "qa": {},
        "developability": {},
        "cmc": {"hotspots": []},
        "immunogenicity": {},
    }
    
    affinity_result = run_affinity_optimization_v1(example_result)
    
    print("\n" + "="*60)
    print("Affinity Optimization Result:")
    print("="*60)
    print(f"Hotspots: {len(affinity_result['hotspots'])}")
    print(f"Candidates: {len(affinity_result['candidates'])}")
    print(f"Variants - Mild: {len(affinity_result['variants'].get('mild', []))}")
    print(f"Variants - Moderate: {len(affinity_result['variants'].get('moderate', []))}")
    print(f"Variants - Aggressive: {len(affinity_result['variants'].get('aggressive', []))}")
    print("\nNarrative:")
    print(affinity_result['narrative'])
    print("="*60)

