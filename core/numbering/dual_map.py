"""
Sequence-level dual mapping (IMGT ↔ Kabat) using ANARCII

Builds residue-level alignment mapping from real ANARCII numbering results.
"""

from __future__ import annotations

import sys
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from anarcii import Anarcii
    HAS_ANARCII = True
except ImportError:
    HAS_ANARCII = False
    Anarcii = None

# Global ANARCII object (lazy initialization)
_anarcii_obj: Optional[Anarcii] = None

def _get_anarcii_obj() -> Anarcii:
    """Get global ANARCII object (lazy initialization)."""
    global _anarcii_obj
    
    if not HAS_ANARCII:
        raise ImportError("anarcii package is not installed. Install with: pip install anarcii")
    
    if _anarcii_obj is None:
        _anarcii_obj = Anarcii(
            seq_type="antibody",
            mode="accuracy",
            batch_size=32,
            cpu=True,
            ncpu=-1,
            verbose=False,
        )
    
    return _anarcii_obj


class DualMapError(RuntimeError):
    """Dual mapping related errors"""
    pass


def build_dual_map(sequence: str) -> Tuple[List[Dict[str, Any]], str, Optional[str]]:
    """
    Build residue-level dual mapping from sequence using ANARCII.
    
    Runs ANARCII for IMGT numbering, then converts to Kabat scheme, and builds alignment.
    
    Args:
        sequence: Amino acid sequence string
        
    Returns:
        (dual_map, status, chain_type)
        
        dual_map: List of dicts, each containing:
            - seq_idx: 0-based index in original sequence
            - aa: amino acid at this position
            - imgt_pos: IMGT position (e.g., "37", "37A", or None)
            - kabat_pos: Kabat position (e.g., "37", "52A", or None)
            - flags: list of flags (e.g., ["imgt_gap", "kabat_gap", "insertion", "truncated"])
        
        status: "full" | "partial" | "conflict" | "failed"
        chain_type: "H" | "L" | "K" | None (antibody chain type, or None if not antibody)
    
    Raises:
        DualMapError: If numbering fails
    """
    if not HAS_ANARCII:
        raise DualMapError("ANARCII is not available. Install with: pip install anarcii")
    
    if not sequence or not isinstance(sequence, str):
        raise DualMapError("Sequence must be a non-empty string")
    
    seq_clean = sequence.strip().upper().replace(" ", "").replace("\n", "").replace("\r", "").replace("*", "")
    if not seq_clean:
        raise DualMapError("Sequence is empty after cleaning")
    
    # Get ANARCII object
    try:
        anarcii_obj = _get_anarcii_obj()
    except ImportError as e:
        raise DualMapError(f"ANARCII is not available: {e}") from e
    
    # Run ANARCII for IMGT scheme
    try:
        result_imgt = anarcii_obj.number(seq_clean)
    except Exception as e:
        raise DualMapError(f"ANARCII IMGT numbering failed: {e}") from e
    
    if not isinstance(result_imgt, dict) or len(result_imgt) == 0:
        raise DualMapError("ANARCII IMGT returned empty or invalid result")
    
    # Get the first key (usually "Sequence")
    key = next(iter(result_imgt.keys()))
    seq_info_imgt = result_imgt.get(key, {})
    
    if not isinstance(seq_info_imgt, dict):
        raise DualMapError("ANARCII IMGT returned unexpected result format")
    
    numbering_imgt = seq_info_imgt.get("numbering", [])
    chain_type = seq_info_imgt.get("chain_type", None)
    
    if not numbering_imgt:
        return [], "failed", None
    
    # Convert to Kabat scheme
    try:
        result_kabat = anarcii_obj.to_scheme('kabat')
    except Exception as e:
        raise DualMapError(f"ANARCII Kabat conversion failed: {e}") from e
    
    if not isinstance(result_kabat, dict) or len(result_kabat) == 0:
        raise DualMapError("ANARCII Kabat returned empty or invalid result")
    
    seq_info_kabat = result_kabat.get(key, {})
    
    if not isinstance(seq_info_kabat, dict):
        raise DualMapError("ANARCII Kabat returned unexpected result format")
    
    numbering_kabat = seq_info_kabat.get("numbering", [])
    
    if not numbering_kabat:
        return [], "failed", chain_type
    
    # Build dual_map by aligning through sequence
    # ANARCII numbering: each item is ((pos, ins_code), aa)
    # The numbering list is aligned to sequence (gaps are "-")
    # We need to map sequence positions to numbering positions
    
    dual_map: List[Dict[str, Any]] = []
    
    # Build maps: numbering_index -> (pos_label, aa)
    # Then align to sequence by matching AA
    imgt_numbering_map: Dict[int, Tuple[str, str]] = {}  # numbering_idx -> (pos_label, aa)
    kabat_numbering_map: Dict[int, Tuple[str, str]] = {}
    
    # Parse IMGT numbering
    for idx, item in enumerate(numbering_imgt):
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        pos_info, aa = item[0], item[1]
        if aa == "-" or pos_info is None:
            continue
        if not isinstance(pos_info, tuple) or len(pos_info) < 1:
            continue
        
        pos = pos_info[0]
        ins_code = pos_info[1] if len(pos_info) > 1 else " "
        
        if ins_code and ins_code.strip():
            pos_label = f"{pos}{ins_code.strip()}"
        else:
            pos_label = str(pos)
        
        imgt_numbering_map[idx] = (pos_label, aa)
    
    # Parse Kabat numbering
    for idx, item in enumerate(numbering_kabat):
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        pos_info, aa = item[0], item[1]
        if aa == "-" or pos_info is None:
            continue
        if not isinstance(pos_info, tuple) or len(pos_info) < 1:
            continue
        
        pos = pos_info[0]
        ins_code = pos_info[1] if len(pos_info) > 1 else " "
        
        if ins_code and ins_code.strip():
            pos_label = f"{pos}{ins_code.strip()}"
        else:
            pos_label = str(pos)
        
        kabat_numbering_map[idx] = (pos_label, aa)
    
    # ANARCII numbering is aligned to sequence
    # Each item in numbering corresponds to a sequence position (gaps are "-")
    # We build dual_map by iterating through numbering and matching to sequence
    
    # Build sequence position maps
    seq_to_imgt: Dict[int, str] = {}  # seq_idx -> pos_label
    seq_to_kabat: Dict[int, str] = {}  # seq_idx -> pos_label
    
    # Process IMGT numbering: align by matching AA
    seq_pos = 0
    for num_idx, item in enumerate(numbering_imgt):
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        
        pos_info, aa = item[0], item[1]
        
        # Skip gaps
        if aa == "-" or pos_info is None:
            continue
        
        if not isinstance(pos_info, tuple) or len(pos_info) < 1:
            continue
        
        # Match to sequence
        if seq_pos < len(seq_clean) and aa == seq_clean[seq_pos]:
            pos = pos_info[0]
            ins_code = pos_info[1] if len(pos_info) > 1 else " "
            
            if ins_code and ins_code.strip():
                pos_label = f"{pos}{ins_code.strip()}"
            else:
                pos_label = str(pos)
            
            seq_to_imgt[seq_pos] = pos_label
            seq_pos += 1
    
    # Process Kabat numbering: align by matching AA
    seq_pos = 0
    for num_idx, item in enumerate(numbering_kabat):
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        
        pos_info, aa = item[0], item[1]
        
        if aa == "-" or pos_info is None:
            continue
        
        if not isinstance(pos_info, tuple) or len(pos_info) < 1:
            continue
        
        if seq_pos < len(seq_clean) and aa == seq_clean[seq_pos]:
            pos = pos_info[0]
            ins_code = pos_info[1] if len(pos_info) > 1 else " "
            
            if ins_code and ins_code.strip():
                pos_label = f"{pos}{ins_code.strip()}"
            else:
                pos_label = str(pos)
            
            seq_to_kabat[seq_pos] = pos_label
            seq_pos += 1
    
    # Build dual_map for all sequence positions
    imgt_gaps = 0
    kabat_gaps = 0
    insertions = 0
    
    for seq_idx in range(len(seq_clean)):
        flags = []
        
        imgt_pos = seq_to_imgt.get(seq_idx)
        if imgt_pos is None:
            flags.append("imgt_gap")
            imgt_gaps += 1
        
        kabat_pos = seq_to_kabat.get(seq_idx)
        if kabat_pos is None:
            flags.append("kabat_gap")
            kabat_gaps += 1
        
        # Check for insertions (positions ending with letter)
        if imgt_pos and re.search(r'[A-Z]$', imgt_pos):
            flags.append("imgt_insertion")
            insertions += 1
        if kabat_pos and re.search(r'[A-Z]$', kabat_pos):
            flags.append("kabat_insertion")
            insertions += 1
        
        # Check for truncation
        if seq_idx == len(seq_clean) - 1:
            if not imgt_pos or not kabat_pos:
                flags.append("truncated")
        
        dual_map.append({
            "seq_idx": seq_idx,
            "aa": seq_clean[seq_idx],
            "imgt_pos": imgt_pos,
            "kabat_pos": kabat_pos,
            "flags": flags if flags else []
        })
    
    # Determine status
    total_positions = len(dual_map)
    positions_with_both = sum(1 for entry in dual_map if entry["imgt_pos"] and entry["kabat_pos"])
    
    if total_positions == 0:
        status = "failed"
    elif imgt_gaps > total_positions * 0.5 or kabat_gaps > total_positions * 0.5:
        status = "failed"
    elif positions_with_both < total_positions * 0.7:
        status = "partial"
    elif insertions > 0 or (imgt_gaps > 0 and kabat_gaps == 0) or (kabat_gaps > 0 and imgt_gaps == 0):
        status = "conflict"
    else:
        status = "full"
    
    return dual_map, status, chain_type


def resolve_functional_sites_on_sequence(
    dual_map: List[Dict[str, Any]],
    functional_sites: List[Dict[str, Any]],
    chain_type: Optional[str] = None
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Resolve functional sites positions on sequence using dual_map.
    
    Args:
        dual_map: Result from build_dual_map()
        functional_sites: List of functional site definitions from YAML
        chain_type: Chain type ("H" or "L") for filtering sites by chain_scope
        
    Returns:
        (resolved_sites, conflicts)
        
        resolved_sites: Dict mapping site_id to resolved info
        conflicts: List of conflict dicts
    """
    resolved_sites = {}
    conflicts = []
    
    # Filter sites by chain_type and chain_scope using unified gating function
    from core.features.scope import rule_applies
    
    filtered_sites = []
    for site in functional_sites:
        chain_scope = site.get("chain_scope", [])
        
        # Use unified gating function
        if rule_applies(chain_type, chain_scope):
            filtered_sites.append(site)
    
    functional_sites = filtered_sites
    
    # Build alias mapping: old site_id -> new site_id
    # This handles backward compatibility (e.g., VL_LAMBDA_* -> VL_GENERIC_*)
    alias_to_site_id: Dict[str, str] = {}
    for site in functional_sites:
        site_id = site.get("site_id", "")
        aliases = site.get("aliases", [])
        if aliases:
            for alias in aliases:
                alias_to_site_id[alias] = site_id
    
    # Create lookup maps: position -> seq_idx
    imgt_to_seq_idx: Dict[str, int] = {}
    kabat_to_seq_idx: Dict[str, int] = {}
    
    for entry in dual_map:
        if entry["imgt_pos"]:
            # Handle both "37" and "37A" formats
            imgt_to_seq_idx[entry["imgt_pos"]] = entry["seq_idx"]
            # Also add integer version if it's a simple number
            try:
                int_pos = int(entry["imgt_pos"])
                if str(int_pos) not in imgt_to_seq_idx:
                    imgt_to_seq_idx[str(int_pos)] = entry["seq_idx"]
            except ValueError:
                pass
        
        if entry["kabat_pos"]:
            kabat_to_seq_idx[entry["kabat_pos"]] = entry["seq_idx"]
            try:
                int_pos = int(entry["kabat_pos"])
                if str(int_pos) not in kabat_to_seq_idx:
                    kabat_to_seq_idx[str(int_pos)] = entry["seq_idx"]
            except ValueError:
                pass
    
    for site in functional_sites:
        site_id = site.get("site_id")
        role = site.get("role")
        imgt_positions = site.get("imgt_positions", [])
        kabat_positions = site.get("kabat_positions", [])  # Optional, may be empty
        anchor_scheme = site.get("anchor_scheme", "imgt")  # Default to IMGT
        
        # ===== IMGT  =====
        # 1.  IMGT positions (anchor positions)  residues
        anchor_positions = imgt_positions  # Use IMGT as anchor by default
        resolved_residues = []
        imgt_missing = []
        imgt_found = []
        
        # Check for one-to-many mapping (conflict detection)
        imgt_pos_to_residues: Dict[str, List[Dict[str, Any]]] = {}
        
        for pos in anchor_positions:
            pos_str = str(pos)
            # Try exact match first, then integer match
            seq_idx = None
            if pos_str in imgt_to_seq_idx:
                seq_idx = imgt_to_seq_idx[pos_str]
            elif str(int(pos)) in imgt_to_seq_idx:
                seq_idx = imgt_to_seq_idx[str(int(pos))]
            
            if seq_idx is not None:
                entry = dual_map[seq_idx]
                imgt_found.append(pos_str)
                residue = {
                    "seq_idx": seq_idx,
                    "aa": entry["aa"],
                    "imgt_pos": entry["imgt_pos"],
                    "kabat_pos": entry["kabat_pos"]
                }
                resolved_residues.append(residue)
                
                # Track IMGT position -> residues mapping for conflict detection
                imgt_pos_key = str(entry["imgt_pos"]) if entry["imgt_pos"] else pos_str
                if imgt_pos_key not in imgt_pos_to_residues:
                    imgt_pos_to_residues[imgt_pos_key] = []
                imgt_pos_to_residues[imgt_pos_key].append(residue)
            else:
                imgt_missing.append(pos_str)
        
        # 2.  resolved_residues  kabat_positions
        # ( dual_map ， kabat_positions )
        resolved_kabat_positions = []
        kabat_pos_to_residues: Dict[str, List[Dict[str, Any]]] = {}
        for residue in resolved_residues:
            if residue["kabat_pos"]:
                kabat_pos_str = str(residue["kabat_pos"])
                resolved_kabat_positions.append(kabat_pos_str)
                if kabat_pos_str not in kabat_pos_to_residues:
                    kabat_pos_to_residues[kabat_pos_str] = []
                kabat_pos_to_residues[kabat_pos_str].append(residue)
        
        # 3. Check for one-to-many mapping conflicts (one IMGT pos -> multiple Kabat pos)
        has_one_to_many = False
        for imgt_pos_key, residues_list in imgt_pos_to_residues.items():
            unique_kabat_pos = set(r["kabat_pos"] for r in residues_list if r["kabat_pos"])
            if len(unique_kabat_pos) > 1:
                has_one_to_many = True
                conflicts.append({
                    "site_id": site_id,
                    "description": f"IMGT position {imgt_pos_key} maps to multiple Kabat positions: {sorted(unique_kabat_pos)}"
                })
        
        # 4. Determine mapping status ()
        anchor_pos_count = len(anchor_positions)
        resolved_count = len(resolved_residues)
        
        if has_one_to_many:
            mapping_status = "conflict"
        elif resolved_count == anchor_pos_count:
            # All anchor positions found
            all_have_kabat = all(r["kabat_pos"] for r in resolved_residues)
            if all_have_kabat:
                # Check for scheme_shift: IMGT and Kabat positions are different numbers
                has_scheme_shift = False
                for residue in resolved_residues:
                    if residue["imgt_pos"] and residue["kabat_pos"]:
                        # Extract numeric parts (remove insertion codes)
                        imgt_num = re.sub(r'[A-Z]$', '', str(residue["imgt_pos"]))
                        kabat_num = re.sub(r'[A-Z]$', '', str(residue["kabat_pos"]))
                        if imgt_num != kabat_num:
                            has_scheme_shift = True
                            break
                
                if has_scheme_shift:
                    mapping_status = "scheme_shift"
                else:
                    mapping_status = "full"
            else:
                mapping_status = "partial"
        else:
            # Partial match
            mapping_status = "partial"
        
        # 5. Check for insertion conflicts
        for residue in resolved_residues:
            if residue["imgt_pos"] and residue["kabat_pos"]:
                imgt_has_ins = bool(re.search(r'[A-Z]$', residue["imgt_pos"]))
                kabat_has_ins = bool(re.search(r'[A-Z]$', residue["kabat_pos"]))
                
                if imgt_has_ins != kabat_has_ins:
                    conflicts.append({
                        "site_id": site_id,
                        "description": f"Insertion mismatch: IMGT {residue['imgt_pos']} vs Kabat {residue['kabat_pos']}"
                    })
                    if mapping_status != "conflict":
                        mapping_status = "conflict"
        
        # 6. ： resolved_residues  position 
        resolved_imgt_pos_set = set(str(pos) for pos in imgt_found)
        resolved_kabat_pos_set = set(resolved_kabat_positions)
        
        # ：resolved_residues  residue  imgt_pos  resolved_imgt_positions 
        actual_imgt_pos_set = set(
            str(r["imgt_pos"]) for r in resolved_residues 
            if r["imgt_pos"] is not None
        )
        if not actual_imgt_pos_set.issubset(resolved_imgt_pos_set):
            raise ValueError(
                f"Site {site_id}: resolved_residues contains IMGT positions not in resolved_imgt_positions. "
                f"Actual: {actual_imgt_pos_set}, Expected subset of: {resolved_imgt_pos_set}"
            )
        
        # ：resolved_residues  residue  kabat_pos  resolved_kabat_positions 
        actual_kabat_pos_set = set(
            str(r["kabat_pos"]) for r in resolved_residues 
            if r["kabat_pos"] is not None
        )
        if not actual_kabat_pos_set.issubset(resolved_kabat_pos_set):
            raise ValueError(
                f"Site {site_id}: resolved_residues contains Kabat positions not in resolved_kabat_positions. "
                f"Actual: {actual_kabat_pos_set}, Expected subset of: {resolved_kabat_pos_set}"
            )
        
        # Normalize site_id to ensure correct naming (not alias)
        from core.features.scope import normalize_site_id
        normalized_site_id = normalize_site_id(site_id, chain_type, alias_to_site_id)
        
        resolved_sites[normalized_site_id] = {
            "site_id": normalized_site_id,  # Use normalized site_id in output
            "role": role,
            "imgt_positions": imgt_positions,
            "kabat_positions": kabat_positions,  # Optional, may be empty
            "anchor_scheme": anchor_scheme,
            "chain_scope": site.get("chain_scope", []),
            "resolved_imgt_positions": [str(pos) for pos in imgt_found],
            "resolved_kabat_positions": resolved_kabat_positions,  #  resolved_residues 
            "mapping_status": mapping_status,
            "resolved_residues": resolved_residues
        }
        
        # Update conflicts to use normalized site_id
        for conflict in conflicts:
            if conflict.get("site_id") == site_id:
                conflict["site_id"] = normalized_site_id
    
    return resolved_sites, conflicts






