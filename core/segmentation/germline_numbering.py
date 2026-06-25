"""
GermlineIMGT

23：「germline  IMGT 」「 ANARCII 」
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

try:
    import anarcii
    ANARCII_AVAILABLE = True
    try:
        ANARCII_VERSION = anarcii.__version__
    except AttributeError:
        ANARCII_VERSION = "unknown"
except ImportError:
    ANARCII_AVAILABLE = False
    ANARCII_VERSION = None

try:
    from anarci import anarci as anarci_func
    ANARCI_AVAILABLE = True
    try:
        import anarci
        ANARCI_VERSION = getattr(anarci, "__version__", "unknown")
    except:
        ANARCI_VERSION = "unknown"
except ImportError:
    ANARCI_AVAILABLE = False
    ANARCI_VERSION = None


def number_germline_sequence_anarcii(
    sequence: str,
    template_id: str,
    scheme: str = "imgt",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    ANARCIIgermlineIMGT
    
    Args:
        sequence: 
        template_id: ID
        scheme: （"imgt"）
    
    Returns:
        (numbering_dict, provenance_dict)
        - numbering_dict: 
        - provenance_dict: provenance
    """
    method = "anarcii"
    package = "anarcii"
    package_version = ANARCII_VERSION if ANARCII_AVAILABLE else "not_installed"
    fallback_used = False
    
    # ANARCII
    if ANARCII_AVAILABLE:
        try:
            from core.numbering.imgt_anarcii import imgt_number_anarcii
            
            numbering_rows = imgt_number_anarcii(sequence)
            
            if not numbering_rows:
                raise ValueError("ANARCII")
            
            # 
            # IMGT：
            # FR1: 1-26, CDR1: 27-38, FR2: 39-55, CDR2: 56-65, FR3: 66-104, CDR3: 105-117, FR4: 118-128
            def get_region_from_pos(pos: int) -> str:
                """IMGT"""
                if 1 <= pos <= 26:
                    return "FR1"
                elif 27 <= pos <= 38:
                    return "CDR1"
                elif 39 <= pos <= 55:
                    return "FR2"
                elif 56 <= pos <= 65:
                    return "CDR2"
                elif 66 <= pos <= 104:
                    return "FR3"
                elif 105 <= pos <= 117:
                    return "CDR3"
                elif 118 <= pos <= 128:
                    return "FR4"
                else:
                    return "UNKNOWN"
            
            positions = []
            boundaries = {}
            
            current_region = None
            region_start_idx = None
            
            for idx, row in enumerate(numbering_rows):
                pos = row.get("pos")
                aa = row.get("aa", "")
                
                if not isinstance(pos, int):
                    continue
                
                region = get_region_from_pos(pos)
                
                positions.append({
                    "pos": str(pos),
                    "aa": aa,
                })
                
                # 
                if region != current_region:
                    # 
                    if current_region and current_region != "UNKNOWN" and region_start_idx is not None:
                        boundaries[current_region] = [region_start_idx + 1, idx]
                    
                    # 
                    if region != "UNKNOWN":
                        current_region = region
                        region_start_idx = idx
            
            # 
            if current_region and current_region != "UNKNOWN" and region_start_idx is not None:
                boundaries[current_region] = [region_start_idx + 1, len(positions)]
            
        except Exception as e:
            # ANARCII，fallbackANARCI
            if ANARCI_AVAILABLE:
                method = "fallback:anarci"
                package = "anarci"
                package_version = ANARCI_VERSION
                fallback_used = True
                
                try:
                    from anarci import anarci
                    numbering, _, _ = anarci([("seq", sequence)], scheme=scheme, output=False)
                    
                    if not numbering or not numbering[0] or not numbering[0][1]:
                        raise ValueError("ANARCI")
                    
                    residue_table = numbering[0][1]
                    
                    # ANARCI
                    positions = []
                    boundaries = {}
                    current_region = None
                    region_start = None
                    
                    for pos_data in residue_table:
                        if len(pos_data) < 4:
                            continue
                        
                        pos = pos_data[0]
                        aa = pos_data[1]
                        region = pos_data[3] if len(pos_data) > 3 else ""
                        
                        positions.append({
                            "pos": str(pos),
                            "aa": aa,
                        })
                        
                        if region != current_region:
                            if current_region and region_start is not None:
                                boundaries[current_region] = [region_start + 1, len(positions)]
                            current_region = region
                            region_start = len(positions) - 1
                    
                    # 
                    if current_region and region_start is not None:
                        boundaries[current_region] = [region_start + 1, len(positions)]
                    
                except Exception as e2:
                    raise RuntimeError(f"ANARCIIANARCI: ANARCII={e}, ANARCI={e2}")
            else:
                raise RuntimeError(f"ANARCIIANARCI: {e}")
    else:
        # ANARCII，ANARCI
        if ANARCI_AVAILABLE:
            method = "fallback:anarci"
            package = "anarci"
            package_version = ANARCI_VERSION
            fallback_used = True
            
            try:
                from anarci import anarci
                numbering, _, _ = anarci([("seq", sequence)], scheme=scheme, output=False)
                
                if not numbering or not numbering[0] or not numbering[0][1]:
                    raise ValueError("ANARCI")
                
                residue_table = numbering[0][1]
                
                # ANARCI
                positions = []
                boundaries = {}
                current_region = None
                region_start = None
                
                for pos_data in residue_table:
                    if len(pos_data) < 4:
                        continue
                    
                    pos = pos_data[0]
                    aa = pos_data[1]
                    region = pos_data[3] if len(pos_data) > 3 else ""
                    
                    positions.append({
                        "pos": str(pos),
                        "aa": aa,
                    })
                    
                    if region != current_region:
                        if current_region and region_start is not None:
                            boundaries[current_region] = [region_start + 1, len(positions)]
                        current_region = region
                        region_start = len(positions) - 1
                
                # 
                if current_region and region_start is not None:
                    boundaries[current_region] = [region_start + 1, len(positions)]
                
            except Exception as e:
                raise RuntimeError(f"ANARCI: {e}")
        else:
            raise RuntimeError("ANARCIIANARCI")
    
    # 
    numbering_dict = {
        "template_id": template_id,
        "scheme": scheme,
        "positions": positions,
        "boundaries": boundaries,
    }
    
    # provenance
    provenance_dict = {
        "method": method,
        "scheme": scheme,
        "package": package,
        "package_version": package_version,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "command_signature": f"{package}_number(sequence, scheme='{scheme}')",
        "executed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    
    if fallback_used:
        provenance_dict["fallback_reason"] = "anarcii_unavailable_or_failed"
    
    return numbering_dict, provenance_dict


def number_germline_templates(
    json_data: Dict[str, Any],
    template_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    germlineIMGT
    
    Args:
        json_data: JSON
        template_ids: ID（None，selectedranked_top10）
    
    Returns:
        germline_numbering，
    """
    # ID
    if template_ids is None:
        template_ids = []
        
        # selected
        germline = json_data.get("germline", {})
        selected = germline.get("selected", {})
        if selected and selected.get("id"):
            template_ids.append(selected["id"])
        
        # ranked_top10
        germline_selection_proof = json_data.get("germline_selection_proof", {})
        ranked_top10 = germline_selection_proof.get("ranked_top10", [])
        for item in ranked_top10:
            tid = item.get("template_id")
            if tid and tid not in template_ids:
                template_ids.append(tid)
    
    # candidates
    candidates = json_data.get("candidates", [])
    candidate_map = {}
    for candidate in candidates:
        template_id = candidate.get("template_id")
        if template_id:
            # humanized_sequencealignment_scores
            # ，germline
            # candidates，，
            candidate_map[template_id] = candidate
    
    # 
    try:
        from core.germline_library_provenance import load_germline_library_with_provenance
        library_data, _ = load_germline_library_with_provenance()
        
        # template_id
        template_sequence_map = {}
        
        if isinstance(library_data, list):
            for entry in library_data:
                entry_id = entry.get("id") or entry.get("template_id")
                sequence = entry.get("sequence_aa") or entry.get("sequence")
                if entry_id and sequence:
                    template_sequence_map[entry_id] = sequence
        elif isinstance(library_data, dict):
            entries = library_data.get("entries", []) or library_data.get("templates", [])
            for entry in entries:
                entry_id = entry.get("id") or entry.get("template_id")
                sequence = entry.get("sequence_aa") or entry.get("sequence")
                if entry_id and sequence:
                    template_sequence_map[entry_id] = sequence
        
    except Exception as e:
        # ，
        return {
            "error": f"germline: {e}",
            "numberings": {},
        }
    
    # 
    numberings = {}
    provenance = None
    
    for template_id in template_ids:
        sequence = template_sequence_map.get(template_id)
        if not sequence:
            # ，
            continue
        
        try:
            numbering_dict, provenance_dict = number_germline_sequence_anarcii(
                sequence=sequence,
                template_id=template_id,
                scheme="imgt",
            )
            numberings[template_id] = numbering_dict
            
            # provenanceprovenance
            if provenance is None:
                provenance = provenance_dict
        except Exception as e:
            # ，
            numberings[template_id] = {
                "template_id": template_id,
                "error": str(e),
            }
    
    result = {
        "numberings": numberings,
    }
    
    if provenance:
        result["numbering_provenance"] = provenance
    
    return result

