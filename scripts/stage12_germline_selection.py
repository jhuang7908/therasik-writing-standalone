"""
Stage 1 & Stage 2: Germline/Framework （）

Stage 1:  scaffold  scaffold
Stage 2:  scaffold  SAFE_A/B/C 
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# SAFE 
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
        "name": "FR2",
        "description": "FR2（camelid VHH FR2 graft）",
        "graft_type": "fr2_segment",
        "functional_meaning": "FR2camelid VHHFR2，VHH，VHH"
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


def calculate_file_sha256(file_path: Path) -> str:
    """SHA256"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def read_fasta(fasta_path: Path) -> Tuple[str, str]:
    """FASTA，ID"""
    sequence = ""
    sequence_id = ""
    with open(fasta_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                sequence_id = line[1:].split()[0] if line[1:] else "unknown"
            else:
                sequence += line.upper()
    return sequence_id, sequence.replace(" ", "").replace("\n", "").replace("\r", "")


def stage1_select_scaffold(
    query_seq: str,
    scaffold_library_path: str | None = None,
    *,
    scheme: str = "imgt",
    method: str = "anarcii",
    mask_regions: tuple[str, ...] = ("CDR1", "CDR2", "CDR3"),
    min_vh_len: int = 75,
    top_k: int = 10,
    germline_db: str = "v1_clean",
    vhh_hallmark_weight: float = 0.15,
    use_special_fr_templates: bool = False,
) -> dict:
    """
    Stage 1:  scaffold  scaffold
    
    Args:
        query_seq:  VHH 
        scaffold_library_path: scaffold 。 None  germline_db="vhh_v1"，
             manifest.json  scaffold_library（） special_fr_templates（ use_special_fr_templates=True）
        scheme: IMGT 
        method: （anarcii）
        mask_regions:  mask 
        min_vh_len:  VH 
        top_k:  top K 
        germline_db: germline （"v1_clean"  "vhh_v1"）
        vhh_hallmark_weight: VHH hallmark （ vhh_v1 ）
        use_special_fr_templates:  True  germline_db="vhh_v1"， special_fr_templates  scaffold_library
    
    Returns:
        
    """
    from core.segmentation.anarcii_adapter import run_anarcii_imgt
    
    #  scaffold_library_path  None  vhh_v1 ， manifest 
    if scaffold_library_path is None and germline_db == "vhh_v1":
        manifest_path = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            
            vhh_assets = manifest.get("vhh_assets", {})
            if use_special_fr_templates:
                scaffold_library_path = PROJECT_ROOT / vhh_assets.get("special_fr_templates", "")
            else:
                scaffold_library_path = PROJECT_ROOT / vhh_assets.get("scaffold_library", "")
            
            if not scaffold_library_path or not scaffold_library_path.exists():
                raise FileNotFoundError(
                    f" manifest  scaffold : {scaffold_library_path}\n"
                    f" manifest.json  vhh_assets "
                )
        else:
            raise FileNotFoundError(
                f"manifest.json : {manifest_path}\n"
                f" scaffold ， scaffold_library_path"
            )
    elif scaffold_library_path is None:
        raise ValueError(
            f"scaffold_library_path  None（ germline_db='vhh_v1'）"
        )
    else:
        scaffold_library_path = Path(scaffold_library_path)
    
    if not scaffold_library_path.exists():
        raise FileNotFoundError(f"Scaffold: {scaffold_library_path}")
    
    # 1.  provenance
    input_provenance = {
        "sequence_length": len(query_seq),
        "sha256": hashlib.sha256(query_seq.encode()).hexdigest()[:16] + "...",
        "loaded_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    
    # 2.  IMGT 
    try:
        segmentation_result, numbering_rows, provenance = run_anarcii_imgt(
            query_seq, species="camelid", chain="H"
        )
        
        segmentation_provenance = {
            "method": provenance.get("method", "anarcii"),
            "package": provenance.get("implementation", {}).get("package", "unknown"),
            "package_version": provenance.get("implementation", {}).get("version", "unknown"),
            "scheme": scheme,
            "executed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        
        # （ provenance  evidence ）
        boundaries = provenance.get("evidence", {}).get("boundaries", {})
        if not boundaries:
            #  evidence ， segmentation_result 
            boundaries = segmentation_result.get("boundaries", {})
        
        # 
        target_pos_map = {}
        for row in numbering_rows:
            pos = row.get("pos")
            aa = row.get("aa", "")
            if pos:
                try:
                    target_pos_map[int(pos)] = aa
                except (ValueError, TypeError):
                    continue
        
    except Exception as e:
        raise RuntimeError(f"IMGT: {e}") from e
    
    # 3.  scaffold （ JSON  JSONL ）
    scaffold_library = []
    with open(scaffold_library_path, "r", encoding="utf-8") as f:
        if scaffold_library_path.suffix.lower() == ".jsonl":
            # JSONL ： JSON 
            for line in f:
                line = line.strip()
                if line:
                    scaffold_library.append(json.loads(line))
        else:
            # JSON ：
            scaffold_library = json.load(f)
    
    scaffold_library_provenance = {
        "path": str(scaffold_library_path.relative_to(PROJECT_ROOT)) if scaffold_library_path.is_relative_to(PROJECT_ROOT) else str(scaffold_library_path),
        "absolute_path": str(scaffold_library_path.resolve()),
        "entry_count": len(scaffold_library) if isinstance(scaffold_library, list) else 0,
        "sha256": calculate_file_sha256(scaffold_library_path),
        "version": "v1.0",
        "loaded_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    
    # 4.  scaffold 
    candidates = []
    excluded_scaffolds = []
    
    for scaffold in scaffold_library:
        scaffold_id = scaffold.get("scaffold_id", "")
        consensus = scaffold.get("consensus", {})
        framework_full = consensus.get("framework_full", "")
        
        # 
        if len(framework_full) < min_vh_len:
            excluded_scaffolds.append({
                "scaffold_id": scaffold_id,
                "reason": "length_below_minimum",
                "length": len(framework_full),
                "min_required": min_vh_len,
            })
            continue
        
        #  scaffold  IMGT 
        try:
            _, scaffold_numbering_rows, _ = run_anarcii_imgt(
                framework_full, species="human", chain="H"
            )
        except Exception as e:
            excluded_scaffolds.append({
                "scaffold_id": scaffold_id,
                "reason": "numbering_failed",
                "error": str(e),
            })
            continue
        
        #  scaffold 
        scaffold_pos_map = {}
        for row in scaffold_numbering_rows:
            pos = row.get("pos")
            aa = row.get("aa", "")
            if pos:
                try:
                    scaffold_pos_map[int(pos)] = aa
                except (ValueError, TypeError):
                    continue
        
        # IMGT position-level FR identity （mask CDR）
        positions_to_compare = set(target_pos_map.keys()) & set(scaffold_pos_map.keys())
        
        #  CDR （ boundaries ）
        cdr_positions = set()
        for region in mask_regions:
            if region in boundaries:
                start, end = boundaries[region]
                for pos in range(start, end + 1):
                    cdr_positions.add(pos)
        
        #  FR 
        fr_positions = positions_to_compare - cdr_positions
        
        # 
        region_counts = {}
        first_mismatches = []
        
        for region in ["FR1", "FR2", "FR3", "FR4"]:
            if region not in boundaries:
                region_counts[region] = {"match": 0, "total": 0}
                continue
            
            start, end = boundaries[region]
            match = 0
            total = 0
            
            for pos in range(start, end + 1):
                if pos in fr_positions:
                    total += 1
                    target_aa = target_pos_map.get(pos)
                    scaffold_aa = scaffold_pos_map.get(pos)
                    
                    if target_aa and scaffold_aa:
                        if target_aa == scaffold_aa:
                            match += 1
                        elif len(first_mismatches) < 10:
                            first_mismatches.append({
                                "pos": pos,
                                "query": target_aa,
                                "ref": scaffold_aa,
                            })
            
            region_counts[region] = {"match": match, "total": total}
        
        #  framework_identity
        total_match = sum(r["match"] for r in region_counts.values())
        total_positions = sum(r["total"] for r in region_counts.values())
        framework_identity = total_match / total_positions if total_positions > 0 else 0.0
        
        #  score_components
        score_components = {
            "framework_identity": round(framework_identity, 4),
        }
        
        #  total_score（ framework_identity）
        total_score = framework_identity
        
        candidates.append({
            "scaffold_id": scaffold_id,
            "framework_identity": round(framework_identity, 4),
            "region_counts": region_counts,
            "imgt_positions_compared": len(fr_positions),
            "first_mismatches": first_mismatches[:10],
            "score_components": score_components,
            "total_score": total_score,
            "total_score_old": total_score,  # 
        })
    
    # 5.  canonical_proxy 
    from core.germline_assets_loader import load_all_clean_germline_assets
    from core.scoring.canonical_proxy import (
        apply_canonical_proxy_to_score,
        canonical_proxy_score_breakdown,
    )
    
    #  canonical_proxy  germline assets
    try:
        germline_assets = load_all_clean_germline_assets(include_canonical_proxy=True, version=germline_db)
        #  sequence_id -> germline_record 
        # （， "M99641|IGHV1-18*01"）
        sequence_id_to_germline = {}
        prefix_to_germline = {}  # 
        
        for asset in germline_assets:
            seq_id = asset.get("sequence_id", "")
            if seq_id:
                sequence_id_to_germline[seq_id] = asset
                # （）
                parts = seq_id.split("|")
                if len(parts) >= 2:
                    prefix = f"{parts[0]}|{parts[1]}"
                    # ，
                    if prefix not in prefix_to_germline or len(seq_id) > len(prefix_to_germline[prefix].get("sequence_id", "")):
                        prefix_to_germline[prefix] = asset
    except Exception as e:
        print(f"  ⚠️  Warning:  canonical_proxy : {e}")
        sequence_id_to_germline = {}
        prefix_to_germline = {}
    
    #  canonical_proxy 
    canonical_proxy_config = {
        "enabled": True,
        "agg_mode": "min",  # ：
        "weight": 0.10,  # 10% 
        "floor_if_missing": 0.0,
    }
    
    #  VHH hallmark （ vhh_v1 ）
    vhh_hallmark_config = {
        "enabled": germline_db == "vhh_v1",
        "weight": vhh_hallmark_weight if germline_db == "vhh_v1" else 0.0,
    }
    
    #  candidate  canonical_proxy 
    for candidate in candidates:
        scaffold_id = candidate["scaffold_id"]
        
        #  scaffold_library  scaffold 
        scaffold_entry = None
        for scaffold in scaffold_library:
            if scaffold.get("scaffold_id") == scaffold_id:
                scaffold_entry = scaffold
                break
        
        #  scaffold  member_ids  germline
        germline_record = None
        if scaffold_entry:
            member_ids = scaffold_entry.get("member_ids", [])
            # member_ids : "M99652|IGHV3-11*01|Homo sapiens|..."
            # germline assets  sequence_id : "M99641|IGHV1-18*01|Homo"
            #  sequence_id（）
            for member_id in member_ids:
                #  sequence_id（， "M99652|IGHV3-11*01"）
                parts = member_id.split("|")
                if len(parts) >= 2:
                    prefix = f"{parts[0]}|{parts[1]}"
                    
                    # 1: （ + "Homo"）
                    candidate_ids = [
                        f"{prefix}|Homo",  # 
                        prefix,  # 
                    ]
                    
                    for candidate_id in candidate_ids:
                        if candidate_id in sequence_id_to_germline:
                            germline_record = sequence_id_to_germline[candidate_id]
                            break
                    
                    if germline_record:
                        break
                    
                    # 2: 
                    if prefix in prefix_to_germline:
                        germline_record = prefix_to_germline[prefix]
                        break
        
        #  scaffold （）
        if scaffold_entry:
            #  scaffold  canonical_proxy  vhh_hallmark，
            if "canonical_proxy_cdr1" in scaffold_entry or "canonical_proxy_cdr2" in scaffold_entry:
                candidate.update({
                    "canonical_proxy_cdr1": scaffold_entry.get("canonical_proxy_cdr1"),
                    "canonical_proxy_cdr2": scaffold_entry.get("canonical_proxy_cdr2"),
                })
            
            if vhh_hallmark_config["enabled"] and "vhh_hallmark" in scaffold_entry:
                candidate["vhh_hallmark"] = scaffold_entry.get("vhh_hallmark")
        
        #  scaffold ， germline_record 
        if germline_record:
            #  candidate 
            if "canonical_proxy_cdr1" not in candidate or not candidate.get("canonical_proxy_cdr1"):
                candidate.update({
                    "canonical_proxy_cdr1": germline_record.get("canonical_proxy_cdr1"),
                    "canonical_proxy_cdr2": germline_record.get("canonical_proxy_cdr2"),
                })
            
            #  vhh_v1 ， VHH hallmark （）
            if vhh_hallmark_config["enabled"] and "vhh_hallmark" not in candidate:
                vhh_hallmark = germline_record.get("vhh_hallmark")
                if vhh_hallmark:
                    candidate["vhh_hallmark"] = vhh_hallmark
        
        #  canonical_proxy 
        candidate = apply_canonical_proxy_to_score(candidate, canonical_proxy_config)
        
        #  VHH hallmark （）
        if vhh_hallmark_config["enabled"] and "vhh_hallmark" in candidate:
            hallmark_score = candidate["vhh_hallmark"].get("score", 0.0)
            hallmark_weight = vhh_hallmark_config["weight"]
            
            #  score_components
            if "score_components" not in candidate:
                candidate["score_components"] = {}
            candidate["score_components"]["vhh_hallmark"] = round(hallmark_score, 4)
            
            #  total_score
            # total_score = framework_identity * (1 - canonical_proxy_weight - vhh_hallmark_weight) 
            #              + canonical_proxy_agg * canonical_proxy_weight 
            #              + vhh_hallmark_score * vhh_hallmark_weight
            framework_identity = candidate.get("framework_identity", 0.0)
            framework_weight = 1.0 - canonical_proxy_config["weight"] - hallmark_weight
            canonical_proxy_agg = candidate.get("canonical_proxy_agg", 0.0)
            
            new_total_score = (
                framework_identity * framework_weight +
                canonical_proxy_agg * canonical_proxy_config["weight"] +
                hallmark_score * hallmark_weight
            )
            candidate["total_score"] = round(new_total_score, 4)
    
    # 5.  top K（ total_score ）
    # ，
    candidates_with_old_rank = []
    candidates_sorted_old = sorted(candidates, key=lambda x: x["framework_identity"], reverse=True)
    for old_rank, cand in enumerate(candidates_sorted_old, 1):
        cand["rank_old"] = old_rank
        candidates_with_old_rank.append(cand)
    
    # 
    candidates_with_old_rank.sort(key=lambda x: x["total_score"], reverse=True)
    ranked_top10 = []
    for rank, cand in enumerate(candidates_with_old_rank[:top_k], 1):
        #  canonical_proxy 
        proxy_breakdown = canonical_proxy_score_breakdown(
            cand,
            mode=canonical_proxy_config.get("agg_mode", "min")
        )
        
        ranked_top10.append({
            "rank": rank,
            "rank_old": cand.get("rank_old", rank),  # 
            "scaffold_id": cand["scaffold_id"],
            "framework_identity": cand["framework_identity"],
            "region_counts": cand["region_counts"],
            "imgt_positions_compared": cand["imgt_positions_compared"],
            "first_mismatches": cand["first_mismatches"],
            "score_components": cand.get("score_components", {}),
            "total_score": cand.get("total_score", cand["framework_identity"]),
            "total_score_old": cand.get("total_score_old", cand["framework_identity"]),
            "canonical_proxy": {
                "proxy_cdr1": proxy_breakdown.get("proxy_cdr1", 0.0),
                "proxy_cdr2": proxy_breakdown.get("proxy_cdr2", 0.0),
                "proxy_agg": proxy_breakdown.get("proxy_agg", 0.0),
                "agg_mode": proxy_breakdown.get("agg_mode", "min"),
            },
            "vhh_hallmark": cand.get("vhh_hallmark") if vhh_hallmark_config["enabled"] else None,
        })
    
    # 
    if not ranked_top10:
        raise ValueError("Stage 1 : ranked_top10 ")
    
    selected_scaffold = ranked_top10[0]
    
    if selected_scaffold["imgt_positions_compared"] == 0:
        raise ValueError(f"Stage 1 : selected_scaffold {selected_scaffold['scaffold_id']}  imgt_positions_compared=0")
    
    #  alignment provenance
    scaffold_alignment_provenance = {
        "algorithm": "imgt_position_identity",
        "scheme": scheme,
        "method": method,
        "mask_regions": list(mask_regions),
        "executed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    
    # 6. （query  selected_scaffold）
    from core.numbering.dual_numbering import get_dual_numbering, build_numbering_maps_json
    from core.numbering.dual_numbering_validation import validate_dual_numbering
    
    numbering_maps = {}
    mapping_validation = {}
    
    # Query 
    try:
        query_imgt_rows, query_kabat_rows, query_mapping = get_dual_numbering(query_seq)
        numbering_maps["query"] = build_numbering_maps_json(query_imgt_rows, query_kabat_rows, query_mapping)
        
        # 
        query_validation = validate_dual_numbering(query_seq, query_imgt_rows, query_kabat_rows, query_mapping)
        mapping_validation["query"] = query_validation
        
        # Gate C0: 
        check_c_details = query_validation.get("check_c", {}).get("details", {})
        hallmark_v2 = check_c_details.get("hallmark_positions_v2", {})
        for pos, info in hallmark_v2.items():
            kabat = info.get("kabat", {})
            imgt = info.get("imgt", {})
            mapping_info = info.get("mapping", {})
            
            # 1:  residue_present=false  out_of_domain=false， aa  null
            if not kabat.get("residue_present") and not kabat.get("out_of_domain", False) and kabat.get("aa") is not None:
                raise ValueError(f"Query Gate C0 : Kabat {pos} residue_present=false  out_of_domain=false  aa  null")
            # 2:  out_of_domain=true， residue_present  false
            if kabat.get("out_of_domain", False) and kabat.get("residue_present"):
                raise ValueError(f"Query Gate C0 : Kabat {pos} out_of_domain=true  residue_present=true")
            # 3:  residue_present=true， out_of_domain  false
            if kabat.get("residue_present") and kabat.get("out_of_domain", False):
                raise ValueError(f"Query Gate C0 : Kabat {pos} residue_present=true  out_of_domain=true")
            # 4: IMGT  residue_present=false， aa  null
            if not imgt.get("residue_present") and imgt.get("aa") is not None:
                raise ValueError(f"Query Gate C0 : IMGT {pos} residue_present=false  aa  null")
            
            # 5:  mapping.status="gap"， mapping.mapped  false
            if mapping_info.get("status") == "gap" and mapping_info.get("mapped"):
                raise ValueError(f"Query Gate C0 : Kabat {pos} mapping.status=gap  mapped=true")
            
            # 6:  mapping.status="mapped"， residue_present  true
            if mapping_info.get("status") == "mapped":
                if not kabat.get("residue_present") or not imgt.get("residue_present"):
                    raise ValueError(f"Query Gate C0 : Kabat {pos} mapping.status=mapped  residue_present  true")
        
        # Gate C1: Query  hallmark 
        for pos in ["37", "44", "45", "47"]:
            info = hallmark_v2.get(pos, {})
            mapping_status = info.get("mapping", {}).get("status")
            if mapping_status not in ["mapped", "already_satisfied"]:
                raise ValueError(f"Query Gate C1 : Kabat {pos} mapping.status={mapping_status}， 'mapped'  'already_satisfied'")
        
        # （Check A ，Check B ）
        if not query_validation["check_a"]["pass"]:
            raise ValueError("Query : Check A () ")
        # Check B ，
        if not query_validation["check_b"]["pass"]:
            print(f"  ⚠️  Warning: Query Check B ()  {len(query_validation['check_b']['details']['mismatches'])} ")
    except Exception as e:
        raise RuntimeError(f"Query : {e}") from e
    
    # Selected scaffold 
    selected_scaffold_id = selected_scaffold["scaffold_id"]
    selected_scaffold_entry = None
    for scaffold in scaffold_library:
        if scaffold.get("scaffold_id") == selected_scaffold_id:
            selected_scaffold_entry = scaffold
            break
    
    if not selected_scaffold_entry:
        raise ValueError(f" selected_scaffold {selected_scaffold_id}")
    
    scaffold_framework = selected_scaffold_entry.get("consensus", {}).get("framework_full", "")
    if not scaffold_framework:
        raise ValueError(f"Selected scaffold {selected_scaffold_id}  framework_full ")
    
    try:
        scaffold_imgt_rows, scaffold_kabat_rows, scaffold_mapping = get_dual_numbering(scaffold_framework)
        numbering_maps["selected_scaffold"] = build_numbering_maps_json(scaffold_imgt_rows, scaffold_kabat_rows, scaffold_mapping)
        
        # 
        scaffold_validation = validate_dual_numbering(scaffold_framework, scaffold_imgt_rows, scaffold_kabat_rows, scaffold_mapping)
        mapping_validation["selected_scaffold"] = scaffold_validation
        
        # Gate C0: 
        check_c_details = scaffold_validation.get("check_c", {}).get("details", {})
        hallmark_v2 = check_c_details.get("hallmark_positions_v2", {})
        for pos, info in hallmark_v2.items():
            kabat = info.get("kabat", {})
            imgt = info.get("imgt", {})
            mapping_info = info.get("mapping", {})
            
            # 1:  residue_present=false  out_of_domain=false， aa  null
            if not kabat.get("residue_present") and not kabat.get("out_of_domain", False) and kabat.get("aa") is not None:
                raise ValueError(f"Scaffold Gate C0 : Kabat {pos} residue_present=false  out_of_domain=false  aa  null")
            # 2:  out_of_domain=true， residue_present  false
            if kabat.get("out_of_domain", False) and kabat.get("residue_present"):
                raise ValueError(f"Scaffold Gate C0 : Kabat {pos} out_of_domain=true  residue_present=true")
            # 3:  residue_present=true， out_of_domain  false
            if kabat.get("residue_present") and kabat.get("out_of_domain", False):
                raise ValueError(f"Scaffold Gate C0 : Kabat {pos} residue_present=true  out_of_domain=true")
            # 4: IMGT  residue_present=false， aa  null
            if not imgt.get("residue_present") and imgt.get("aa") is not None:
                raise ValueError(f"Scaffold Gate C0 : IMGT {pos} residue_present=false  aa  null")
            
            # 5:  mapping.status="gap"， mapping.mapped  false
            if mapping_info.get("status") == "gap" and mapping_info.get("mapped"):
                raise ValueError(f"Scaffold Gate C0 : Kabat {pos} mapping.status=gap  mapped=true")
            
            # 6:  mapping.status="mapped"， residue_present  true
            if mapping_info.get("status") == "mapped":
                if not kabat.get("residue_present") or not imgt.get("residue_present"):
                    raise ValueError(f"Scaffold Gate C0 : Kabat {pos} mapping.status=mapped  residue_present  true")
        
        # Gate C2: Scaffold  gap，""（ Stage 2 ）
        # ，
        
        # （Check A ，Check B ）
        if not scaffold_validation["check_a"]["pass"]:
            raise ValueError("Selected scaffold : Check A () ")
        # Check B ，
        if not scaffold_validation["check_b"]["pass"]:
            print(f"  ⚠️  Warning: Selected scaffold Check B ()  {len(scaffold_validation['check_b']['details']['mismatches'])} ")
    except Exception as e:
        raise RuntimeError(f"Selected scaffold : {e}") from e
    
    # 
    return {
        "input_provenance": input_provenance,
        "segmentation_provenance": segmentation_provenance,
        "scaffold_library_provenance": scaffold_library_provenance,
        "excluded_scaffolds": excluded_scaffolds,
        "numbering_maps": numbering_maps,
        "mapping_validation": mapping_validation,
        "stage1": {
            "scaffold_alignment_provenance": scaffold_alignment_provenance,
            "ranked_top10": ranked_top10,
            "canonical_proxy_config": {
                "enabled": canonical_proxy_config.get("enabled", True),
                "agg_mode": canonical_proxy_config.get("agg_mode", "min"),
                "weight": canonical_proxy_config.get("weight", 0.10),
                "formula": "0.6 * percentile + 0.4 * rep_identity",
            },
            "vhh_hallmark_config": {
                "enabled": vhh_hallmark_config.get("enabled", False),
                "weight": vhh_hallmark_config.get("weight", 0.0),
            },
            "germline_asset_version": germline_db,
            "selected_scaffold": {
                "scaffold_id": selected_scaffold["scaffold_id"],
                "rank": selected_scaffold["rank"],
                "framework_identity": selected_scaffold["framework_identity"],
                "region_counts": selected_scaffold["region_counts"],
            },
        },
    }


def stage2_generate_safe_variants(
    selected_scaffold: dict,
    scaffold_library: List[Dict[str, Any]],
    numbering_maps: dict | None = None,
    *,
    scheme: str = "imgt",
    method: str = "anarcii",
    safe_rules: dict | None = None,
) -> dict:
    """
    Stage 2:  scaffold  SAFE_A/B/C 
    
    Args:
        selected_scaffold: Stage 1  scaffold 
        scaffold_library: scaffold 
        scheme: IMGT 
        method: 
        safe_rules: SAFE （ None， SAFE_PLAN_DEFINITIONS）
    
    Returns:
         SAFE 
    """
    from core.segmentation.anarcii_adapter import run_anarcii_imgt
    
    if safe_rules is None:
        safe_rules = SAFE_PLAN_DEFINITIONS
    
    #  run_anarcii_imgt 
    
    scaffold_id = selected_scaffold["scaffold_id"]
    
    #  scaffold
    scaffold_entry = None
    for entry in scaffold_library:
        if entry.get("scaffold_id") == scaffold_id:
            scaffold_entry = entry
            break
    
    if not scaffold_entry:
        raise ValueError(f"Stage 2 :  scaffold {scaffold_id}")
    
    consensus = scaffold_entry.get("consensus", {})
    framework_full = consensus.get("framework_full", "")
    fr1 = consensus.get("fr1", "")
    fr2 = consensus.get("fr2", "")
    fr3 = consensus.get("fr3", "")
    fr4 = consensus.get("fr4", "")
    
    #  scaffold  IMGT 
    try:
        _, numbering_rows, _ = run_anarcii_imgt(
            framework_full, species="human", chain="H"
        )
    except Exception as e:
        raise RuntimeError(f"Stage 2 : scaffold {scaffold_id} IMGT : {e}") from e
    
    # 
    pos_to_aa = {}
    for row in numbering_rows:
        pos = row.get("pos")
        aa = row.get("aa", "")
        if pos:
            try:
                pos_to_aa[int(pos)] = aa
            except (ValueError, TypeError):
                continue
    
    # （FR2  39-55）
    fr2_start = 39
    fr2_end = 55
    
    #  camelid VHH FR2 （ SAFE_C）
    camelid_fr2_library_path = PROJECT_ROOT / "data" / "germlines" / "vicugna_pacos_ig_aa" / "vhh_scaffolds" / "vhh_scaffolds.json"
    camelid_fr2_sequence = None
    camelid_fr2_pos_to_aa = {}
    if camelid_fr2_library_path.exists():
        with open(camelid_fr2_library_path, "r", encoding="utf-8") as f:
            camelid_scaffolds = json.load(f)
            #  scaffold  FR2（ VHH_SCF_04  cluster）
            if camelid_scaffolds:
                # ，；， scaffolds 
                if isinstance(camelid_scaffolds, list) and len(camelid_scaffolds) > 0:
                    first_scaffold = camelid_scaffolds[0]
                elif isinstance(camelid_scaffolds, dict):
                    # 
                    if "scaffolds" in camelid_scaffolds and isinstance(camelid_scaffolds["scaffolds"], list):
                        first_scaffold = camelid_scaffolds["scaffolds"][0]
                    else:
                        first_scaffold = camelid_scaffolds
                else:
                    first_scaffold = None
                
                if first_scaffold:
                    camelid_fr2_sequence = first_scaffold.get("consensus", {}).get("fr2", "")
                    # ，（）
                    camelid_framework_full = first_scaffold.get("consensus", {}).get("framework_full", "")
                    
                    #  IMGT 
                    if camelid_framework_full:
                        try:
                            _, camelid_fw_rows, _ = run_anarcii_imgt(
                                camelid_framework_full, species="human", chain="H"
                            )
                            for row in camelid_fw_rows:
                                pos = row.get("pos")
                                aa = row.get("aa", "")
                                if pos and fr2_start <= pos <= fr2_end and aa and aa != "-":
                                    try:
                                        camelid_fr2_pos_to_aa[int(pos)] = aa
                                    except (ValueError, TypeError):
                                        continue
                        except Exception as e:
                            raise RuntimeError(f"Stage 2 : camelid  IMGT : {e}") from e
                    elif camelid_fr2_sequence:
                        # Fallback:  FR2，
                        temp_framework = "QVQLVESGGGVVQPGRSLRLSCAAS" + camelid_fr2_sequence + "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC"
                        try:
                            _, camelid_fw_rows, _ = run_anarcii_imgt(
                                temp_framework, species="human", chain="H"
                            )
                            for row in camelid_fw_rows:
                                pos = row.get("pos")
                                aa = row.get("aa", "")
                                if pos and fr2_start <= pos <= fr2_end and aa and aa != "-":
                                    try:
                                        camelid_fr2_pos_to_aa[int(pos)] = aa
                                    except (ValueError, TypeError):
                                        continue
                        except Exception as e:
                            raise RuntimeError(f"Stage 2 : camelid FR2 IMGT : {e}") from e
    
    #  SAFE 
    safe_variants = {}
    
    for plan_key in ["A", "B", "C"]:
        plan_def = safe_rules.get(plan_key, {})
        
        # 
        modified_pos_to_aa = pos_to_aa.copy()
        diff_vs_scaffold = []
        physiology_explanations = []
        
        # SAFE_C  FR2 
        if plan_key == "C" and plan_def.get("graft_type") == "fr2_segment":
            if not camelid_fr2_sequence or not camelid_fr2_pos_to_aa:
                raise ValueError("Stage 2 : SAFE_C  camelid VHH FR2 ，")
            
            #  FR2 
            for pos in range(fr2_start, fr2_end + 1):
                if pos in camelid_fr2_pos_to_aa:
                    original_aa = pos_to_aa.get(pos, "")
                    new_aa = camelid_fr2_pos_to_aa[pos]
                    if original_aa != new_aa:
                        modified_pos_to_aa[pos] = new_aa
                    
                    #  diff_vs_scaffold
                    diff_vs_scaffold.append({
                        "imgt_pos": pos,
                        "from": original_aa,
                        "to": new_aa,
                        "region": "FR2",
                    })
            
            # 
            physiology_explanations.append({
                "imgt_pos": None,
                "name": "FR2",
                "mutation": f"FR2camelid VHH FR2",
                "functional_impact": "FR2camelid VHHFR2，VHH",
                "vhh_significance": "VHH，camelid VHHFR2"
            })
        
        else:
            # SAFE_A  SAFE_B 
            # ：SAFE_PLAN_DEFINITIONS  Kabat ， IMGT
            mutations_raw = plan_def.get("mutations", {})
            
            #  numbering_maps  Kabat -> IMGT 
            kabat_to_imgt_map = {}
            if numbering_maps and "selected_scaffold" in numbering_maps:
                scaffold_maps = numbering_maps["selected_scaffold"]
                if "error" not in scaffold_maps and "kabat_to_imgt" in scaffold_maps:
                    for kabat_key, imgt_value in scaffold_maps["kabat_to_imgt"].items():
                        # kabat_key : "kabat_37"
                        # imgt_value : "imgt_??"  "gap"
                        if kabat_key.startswith("kabat_"):
                            try:
                                kabat_pos = int(kabat_key.replace("kabat_", ""))
                                if imgt_value != "gap" and imgt_value.startswith("imgt_"):
                                    imgt_pos = int(imgt_value.replace("imgt_", ""))
                                    kabat_to_imgt_map[kabat_pos] = imgt_pos
                            except (ValueError, TypeError):
                                continue
            
            # ： Kabat -> IMGT 
            if plan_key == "B":
                print(f"\n[DEBUG] SAFE_B Kabat -> IMGT :")
                for kabat_pos in [37, 44, 45, 47]:
                    if kabat_pos in kabat_to_imgt_map:
                        imgt_pos = kabat_to_imgt_map[kabat_pos]
                        print(f"  Kabat {kabat_pos} -> IMGT {imgt_pos}")
                    else:
                        print(f"  Kabat {kabat_pos} -> NOT FOUND ( gap)")
                print(f"[DEBUG] Scaffold IMGT  37 : {37 in pos_to_aa}")
                print(f"[DEBUG] Scaffold IMGT  44 : {44 in pos_to_aa}")
                print(f"[DEBUG] Scaffold IMGT  45 : {45 in pos_to_aa}")
                print(f"[DEBUG] Scaffold IMGT  47 : {47 in pos_to_aa}")
            
            #  Kabat  IMGT 
            mutations_kabat = {}
            mutations_imgt = {}
            for k, v in mutations_raw.items():
                if isinstance(k, str):
                    try:
                        kabat_pos = int(k)
                    except (ValueError, TypeError):
                        raise ValueError(f"Stage 2 : {plan_key}  mutations ， {k}")
                else:
                    kabat_pos = k
                
                mutations_kabat[kabat_pos] = v
                
                #  IMGT 
                if kabat_pos in kabat_to_imgt_map:
                    imgt_pos = kabat_to_imgt_map[kabat_pos]
                    mutations_imgt[imgt_pos] = v
                else:
                    # ， gap
                    if numbering_maps and "selected_scaffold" in numbering_maps:
                        scaffold_maps = numbering_maps["selected_scaffold"]
                        if "error" not in scaffold_maps:
                            #  gap
                            gaps = scaffold_maps.get("gaps", {})
                            kabat_missing = gaps.get("kabat_missing", [])
                            if str(kabat_pos) in kabat_missing:
                                #  gap，
                                if kabat_pos == 37:
                                    #  37  gap，
                                    continue
                                else:
                                    raise ValueError(
                                        f"Stage 2 : {plan_key}  Kabat  {kabat_pos}  gap，。"
                                    )
                    
                    #  gap，
                    if kabat_pos == 37:
                        #  37  gap，
                        continue
                    else:
                        raise ValueError(
                            f"Stage 2 : {plan_key}  Kabat  {kabat_pos}  IMGT 。"
                            f"： gap 。"
                            f": {list(kabat_to_imgt_map.keys())}"
                        )
            
            # （ IMGT ）
            for imgt_pos, target_aa in mutations_imgt.items():
                original_aa = pos_to_aa.get(imgt_pos)
                
                if original_aa is None:
                    # 
                    raise ValueError(
                        f"Stage 2 : {plan_key}  IMGT  {imgt_pos}  scaffold {scaffold_id}  IMGT 。"
                        f": {sorted(pos_to_aa.keys())}"
                    )
                
                #  B ： S， S
                # ： Kabat  37
                if plan_key == "B":
                    #  Kabat 
                    kabat_pos_37 = None
                    for kabat_pos, mapped_imgt_pos in kabat_to_imgt_map.items():
                        if mapped_imgt_pos == imgt_pos and kabat_pos == 37:
                            kabat_pos_37 = kabat_pos
                            break
                    
                    if kabat_pos_37 is not None and original_aa == "S":
                        target_aa = "S"
                
                # （）
                if original_aa != target_aa:
                    modified_pos_to_aa[imgt_pos] = target_aa
                
                # 
                region = "FR2"  # 
                if fr2_start <= imgt_pos <= fr2_end:
                    region = "FR2"
                elif imgt_pos < fr2_start:
                    region = "FR1"
                elif imgt_pos > fr2_end:
                    region = "FR3"
                
                #  Kabat （）
                kabat_pos_for_record = None
                for kabat_pos, mapped_imgt_pos in kabat_to_imgt_map.items():
                    if mapped_imgt_pos == imgt_pos:
                        kabat_pos_for_record = kabat_pos
                        break
                
                #  diff_vs_scaffold（，）
                diff_vs_scaffold.append({
                    "imgt_pos": imgt_pos,
                    "kabat_pos": kabat_pos_for_record,  #  Kabat 
                    "from": original_aa,
                    "to": target_aa,
                    "region": region,
                })
                
                # （）
                # ：HALLMARK_FUNCTIONAL_EXPLANATIONS  Kabat 
                if original_aa != target_aa and kabat_pos_for_record in HALLMARK_FUNCTIONAL_EXPLANATIONS:
                    exp = HALLMARK_FUNCTIONAL_EXPLANATIONS[kabat_pos_for_record]
                    physiology_explanations.append({
                        "imgt_pos": imgt_pos,
                        "kabat_pos": kabat_pos_for_record,
                        "name": exp.get("name", ""),
                        "mutation": f"{original_aa}→{target_aa}",
                        "functional_impact": exp.get("functional_impact", ""),
                        "vhh_significance": exp.get("vhh_significance", ""),
                    })
        
        # 
        all_positions = sorted(set(pos_to_aa.keys()) | set(modified_pos_to_aa.keys()))
        modified_framework_list = []
        
        for pos in all_positions:
            aa = modified_pos_to_aa.get(pos, pos_to_aa.get(pos, ""))
            if aa:
                modified_framework_list.append(aa)
        
        modified_framework_full = "".join(modified_framework_list)
        
        #  FR2
        modified_fr2_list = []
        for pos in range(fr2_start, fr2_end + 1):
            if pos in modified_pos_to_aa:
                modified_fr2_list.append(modified_pos_to_aa[pos])
            elif pos in pos_to_aa:
                modified_fr2_list.append(pos_to_aa[pos])
        
        modified_fr2 = "".join(modified_fr2_list)
        
        #  SAFE_C，， camelid FR2
        if plan_key == "C" and plan_def.get("graft_type") == "fr2_segment" and camelid_fr2_sequence:
            modified_fr2 = camelid_fr2_sequence
            # （FR1 + camelid FR2 + FR3 + FR4）
            modified_framework_full = fr1 + modified_fr2 + fr3 + fr4
        
        #  FR2 ， FR2
        if not modified_fr2:
            modified_fr2 = fr2
        
        safe_variants[f"SAFE_{plan_key}"] = {
            "template_id": f"{scaffold_id}_SAFE_{plan_key}",
            "sequence": {
                "framework_full": modified_framework_full,
                "fr1": fr1,
                "fr2": modified_fr2,
                "fr3": fr3,
                "fr4": fr4,
            },
            "diff_vs_scaffold": diff_vs_scaffold,
            "physiology_explanations": physiology_explanations,
        }
    
    # 
    if len(safe_variants) != 3:
        raise ValueError(f"Stage 2 : 3， {len(safe_variants)} ")
    
    #  diff_vs_scaffold 
    # diff_vs_scaffold （）
    
    # SAFE_A  44, 45
    expected_positions_a = {44, 45}
    all_positions_a = {d["imgt_pos"] for d in safe_variants["SAFE_A"]["diff_vs_scaffold"]}
    
    if not expected_positions_a.issubset(all_positions_a):
        raise ValueError(
            f"Stage 2 : SAFE_A  diff_vs_scaffold  {expected_positions_a}， {all_positions_a}"
        )
    # SAFE_A  2 （）
    if len(all_positions_a) < 2:
        raise ValueError(
            f"Stage 2 : SAFE_A  diff_vs_scaffold  2 ， {len(all_positions_a)} "
        )
    
    # SAFE_B （44, 45, 47）
    expected_positions_b = {44, 45, 47}  # ，
    all_positions_b = {d["imgt_pos"] for d in safe_variants["SAFE_B"]["diff_vs_scaffold"]}
    
    # 
    if not expected_positions_b.issubset(all_positions_b):
        raise ValueError(
            f"Stage 2 : SAFE_B  diff_vs_scaffold  {expected_positions_b}， {all_positions_b}"
        )
    # SAFE_B  3 （44, 45, 47， 37 ）
    if len(all_positions_b) < 3:
        raise ValueError(
            f"Stage 2 : SAFE_B  diff_vs_scaffold  3 ， {len(all_positions_b)} "
        )
    
    # SAFE_C  FR2 ， FR2 
    all_positions_c = {d["imgt_pos"] for d in safe_variants["SAFE_C"]["diff_vs_scaffold"]}
    # SAFE_C  5 （FR2 ）
    if len(all_positions_c) < 5:
        raise ValueError(
            f"Stage 2 : SAFE_C  diff_vs_scaffold  5 （FR2）， {len(all_positions_c)} "
        )
    
    # 
    seq_a = safe_variants["SAFE_A"]["sequence"]["framework_full"]
    seq_b = safe_variants["SAFE_B"]["sequence"]["framework_full"]
    seq_c = safe_variants["SAFE_C"]["sequence"]["framework_full"]
    
    # ：
    print(f"\n[DEBUG] Scaffold original at key positions:")
    for pos in [37, 44, 45, 47]:
        if pos in pos_to_aa:
            print(f"  Position {pos}: {pos_to_aa[pos]}")
    
    print(f"\n[DEBUG] SAFE_A actual mutations (from != to):")
    for d in safe_variants["SAFE_A"]["diff_vs_scaffold"]:
        if d["from"] != d["to"]:
            print(f"  Position {d['imgt_pos']}: {d['from']} -> {d['to']}")
    
    print(f"\n[DEBUG] SAFE_B actual mutations (from != to):")
    for d in safe_variants["SAFE_B"]["diff_vs_scaffold"]:
        if d["from"] != d["to"]:
            print(f"  Position {d['imgt_pos']}: {d['from']} -> {d['to']}")
    
    print(f"\n[DEBUG] SAFE_C actual mutations (from != to):")
    for d in safe_variants["SAFE_C"]["diff_vs_scaffold"]:
        if d["from"] != d["to"]:
            print(f"  Position {d['imgt_pos']}: {d['from']} -> {d['to']}")
    
    print(f"\n[DEBUG] FR2 sequences:")
    print(f"  SAFE_A FR2: {safe_variants['SAFE_A']['sequence']['fr2']}")
    print(f"  SAFE_B FR2: {safe_variants['SAFE_B']['sequence']['fr2']}")
    print(f"  SAFE_C FR2: {safe_variants['SAFE_C']['sequence']['fr2']}")
    
    # （ SAFE_A  SAFE_B  scaffold ，）
    if seq_a == seq_b:
        print(f"  ⚠️  Warning: SAFE_A  SAFE_B （， scaffold  SAFE_B ）")
        # 
        safe_variants["SAFE_A"]["note"] = " SAFE_B （scaffold ）"
        safe_variants["SAFE_B"]["note"] = " SAFE_A （scaffold ）"
    
    if seq_b == seq_c or seq_a == seq_c:
        raise ValueError(
            f"Stage 2 : SAFE_C  SAFE_A/B 。\n"
            f"SAFE_B == SAFE_C: {seq_b == seq_c}\n"
            f"SAFE_A == SAFE_C: {seq_a == seq_c}\n"
            f"SAFE_A FR2: {safe_variants['SAFE_A']['sequence']['fr2']}\n"
            f"SAFE_B FR2: {safe_variants['SAFE_B']['sequence']['fr2']}\n"
            f"SAFE_C FR2: {safe_variants['SAFE_C']['sequence']['fr2']}"
        )
    
    # ：diff_vs_scaffold 
    for plan_key, variant in safe_variants.items():
        scaffold_seq = framework_full
        variant_seq = variant["sequence"]["framework_full"]
        
        #  diff_vs_scaffold 
        for diff in variant["diff_vs_scaffold"]:
            pos = diff["imgt_pos"]
            from_aa = diff["from"]
            to_aa = diff["to"]
            
            # ： scaffold  from_aa
            if pos in pos_to_aa:
                if pos_to_aa[pos] != from_aa:
                    raise ValueError(
                        f"Stage 2 : {plan_key}  {pos} "
                        f"diff_vs_scaffold  from={from_aa}, "
                        f" scaffold  {pos_to_aa[pos]}"
                    )
    
    return {
        "safe_strategy_definitions": safe_rules,
        "safe_variants": safe_variants,
    }

