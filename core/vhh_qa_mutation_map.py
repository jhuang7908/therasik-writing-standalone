"""
VHH

（mutation map），：
- FR1–FR2–FR3–FR4 
-  IMGT 
- （germline adoption, structure-preserving, risk-induced, deviation from germline）
"""

from typing import Dict, List, Any, Tuple, Optional

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

# 
V_REGION_ORDER = ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]


def rebuild_v_region_from_regions(regions: Dict[str, str]) -> str:
    """IMGTFR/CDR"""
    seq_parts = []
    for region in V_REGION_ORDER:
        part = regions.get(region, "")
        if part is None:
            part = ""
        seq_parts.append(part)
    return "".join(seq_parts)


def classify_mutation(
    region: str,
    imgt_pos: int,
    orig_aa: str,
    hum_aa: str,
    template_info: Optional[Dict[str, Any]] = None
) -> str:
    """
    
    
    Args:
        region: （FR1, FR2, FR3, FR4）
        imgt_pos: IMGT
        orig_aa: 
        hum_aa: 
        template_info: （）
    
    Returns:
        ：
        - "germline_adoption": germline
        - "structure_preserving": 
        - "risk_induced": （CMC）
        - "deviation_from_germline": germline（VHH）
    """
    # germline adoption
    if template_info:
        template_seq = template_info.get("consensus", {}).get(region.lower(), "")
        if template_seq:
            # region
            region_start = IMGT_REGIONS[region]["start"]
            local_idx = imgt_pos - region_start
            if 0 <= local_idx < len(template_seq) and template_seq[local_idx] == hum_aa:
                return "germline_adoption"
    
    # 
    # （BLOSUM62）
    conservative_substitutions = {
        "A": ["S", "G"],
        "S": ["A", "T", "N"],
        "T": ["S", "N"],
        "N": ["S", "T", "D"],
        "D": ["N", "E"],
        "E": ["D", "Q"],
        "Q": ["E", "N"],
        "K": ["R"],
        "R": ["K"],
        "I": ["L", "V"],
        "L": ["I", "V", "M"],
        "V": ["I", "L", "A"],
        "M": ["L", "I"],
        "F": ["Y", "W"],
        "Y": ["F", "W"],
        "W": ["F", "Y"]
    }
    
    if orig_aa in conservative_substitutions and hum_aa in conservative_substitutions[orig_aa]:
        return "structure_preserving"
    
    # 
    # （deamidation, oxidation, isomerization hotspots）
    high_risk_aas = {"N", "D", "Q", "M", "W", "C"}
    if hum_aa in high_risk_aas and orig_aa not in high_risk_aas:
        return "risk_induced"
    
    # deviation from germline
    # VHH，germline
    if template_info:
        template_seq = template_info.get("consensus", {}).get(region.lower(), "")
        if template_seq:
            region_start = IMGT_REGIONS[region]["start"]
            local_idx = imgt_pos - region_start
            if 0 <= local_idx < len(template_seq) and template_seq[local_idx] != hum_aa:
                return "deviation_from_germline"
    
    # 
    return "structure_preserving"


def generate_mutation_map(
    orig_regions: Dict[str, str],
    hum_regions: Dict[str, str],
    mutations: List[Dict[str, Any]],
    template_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    
    
    Args:
        orig_regions: 
        hum_regions: 
        mutations: 
        template_info: （）
    
    Returns:
        mutation_map：
        {
            "regions": {
                "FR1": {"start": 1, "end": 26, "sequence": "...", "mutations": [...]},
                ...
            },
            "mutations_by_category": {
                "germline_adoption": [...],
                "structure_preserving": [...],
                "risk_induced": [...],
                "deviation_from_germline": [...]
            },
            "summary": {
                "total_mutations": int,
                "by_category": {...},
                "by_region": {...}
            }
        }
    """
    mutation_map = {
        "regions": {},
        "mutations_by_category": {
            "germline_adoption": [],
            "structure_preserving": [],
            "risk_induced": [],
            "deviation_from_germline": []
        },
        "summary": {
            "total_mutations": 0,
            "by_category": {},
            "by_region": {}
        }
    }
    
    # 
    for region_name in ["FR1", "FR2", "FR3", "FR4"]:
        region_seq = hum_regions.get(region_name, "")
        region_bounds = IMGT_REGIONS.get(region_name, {})
        
        mutation_map["regions"][region_name] = {
            "start": region_bounds.get("start", 0),
            "end": region_bounds.get("end", 0),
            "sequence": region_seq,
            "mutations": []
        }
    
    # 
    for mut in mutations:
        region = mut.get("region", "")
        imgt_pos = mut.get("position", 0)
        orig_aa = mut.get("from", "")
        hum_aa = mut.get("to", "")
        
        if not region or not imgt_pos or not orig_aa or not hum_aa:
            continue
        
        # 
        mut_category = classify_mutation(region, imgt_pos, orig_aa, hum_aa, template_info)
        
        mutation_entry = {
            "region": region,
            "imgt_position": imgt_pos,
            "from": orig_aa,
            "to": hum_aa,
            "category": mut_category,
            "local_position": imgt_pos - IMGT_REGIONS.get(region, {}).get("start", 0) + 1
        }
        
        # 
        if region in mutation_map["regions"]:
            mutation_map["regions"][region]["mutations"].append(mutation_entry)
        
        # 
        mutation_map["mutations_by_category"][mut_category].append(mutation_entry)
    
    # 
    mutation_map["summary"]["total_mutations"] = len(mutations)
    mutation_map["summary"]["by_category"] = {
        cat: len(muts) for cat, muts in mutation_map["mutations_by_category"].items()
    }
    mutation_map["summary"]["by_region"] = {
        region: len(info["mutations"]) 
        for region, info in mutation_map["regions"].items()
    }
    
    return mutation_map

