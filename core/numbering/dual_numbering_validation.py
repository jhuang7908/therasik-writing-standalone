"""


4：
- Check A: 
- Check B: 
- Check C: 
- Check D: 
"""

from __future__ import annotations

from typing import List, Dict, Any, Tuple, Optional


class ValidationError(Exception):
    """"""
    pass


def check_a_reconstruction(
    original_seq: str,
    imgt_rows: List[Dict[str, Any]],
    kabat_rows: List[Dict[str, Any]],
) -> Tuple[bool, Dict[str, Any]]:
    """
    Check A: 
    
     IMGT  Kabat ，。
    
    Returns:
        (pass, details)
    """
    details = {
        "imgt_reconstruction": {"pass": False, "reconstructed": "", "original": original_seq},
        "kabat_reconstruction": {"pass": False, "reconstructed": "", "original": original_seq},
    }
    
    # IMGT 
    imgt_reconstructed = ""
    for row in imgt_rows:
        aa = row.get("aa", "")
        if aa and aa != "-":
            imgt_reconstructed += aa
    
    details["imgt_reconstruction"]["reconstructed"] = imgt_reconstructed
    details["imgt_reconstruction"]["pass"] = (imgt_reconstructed == original_seq)
    
    # Kabat 
    kabat_reconstructed = ""
    for row in kabat_rows:
        aa = row.get("aa", "")
        if aa and aa != "-":
            kabat_reconstructed += aa
    
    details["kabat_reconstruction"]["reconstructed"] = kabat_reconstructed
    details["kabat_reconstruction"]["pass"] = (kabat_reconstructed == original_seq)
    
    all_pass = details["imgt_reconstruction"]["pass"] and details["kabat_reconstruction"]["pass"]
    
    return all_pass, details


def check_b_residue_index_alignment(
    original_seq: str,
    residue_index_map: Dict[int, Dict[str, Any]],
    imgt_rows: List[Dict[str, Any]],
    kabat_rows: List[Dict[str, Any]],
) -> Tuple[bool, Dict[str, Any]]:
    """
    Check B: 
    
     i， IMGT  Kabat ，。
    
    Returns:
        (pass, details)
    """
    details = {
        "total_residues": len(original_seq),
        "checked_residues": 0,
        "mismatches": [],
        "gaps": [],
    }
    
    # 
    imgt_label_to_aa = {}
    for row in imgt_rows:
        pos = row.get("pos")
        ins_code = row.get("ins_code", " ").strip()
        aa = row.get("aa", "")
        if aa and aa != "-":
            label = f"{pos}{ins_code}" if ins_code else str(pos)
            imgt_label_to_aa[label] = aa
    
    kabat_label_to_aa = {}
    for row in kabat_rows:
        pos = row.get("pos")
        ins_code = row.get("ins_code", " ").strip()
        aa = row.get("aa", "")
        if aa and aa != "-":
            label = f"{pos}{ins_code}" if ins_code else str(pos)
            kabat_label_to_aa[label] = aa
    
    # 
    for residue_idx in range(len(original_seq)):
        original_aa = original_seq[residue_idx]
        
        if residue_idx not in residue_index_map:
            details["mismatches"].append({
                "residue_idx": residue_idx,
                "original_aa": original_aa,
                "error": "missing_in_residue_index_map"
            })
            continue
        
        mapping = residue_index_map[residue_idx]
        imgt_label = mapping.get("imgt_label")
        kabat_label = mapping.get("kabat_label")
        is_gap = mapping.get("is_gap", False)
        
        if is_gap:
            details["gaps"].append({
                "residue_idx": residue_idx,
                "imgt_label": imgt_label,
                "kabat_label": kabat_label,
            })
            continue
        
        details["checked_residues"] += 1
        
        #  IMGT 
        if imgt_label is None:
            details["mismatches"].append({
                "residue_idx": residue_idx,
                "original_aa": original_aa,
                "error": "imgt_label_missing"
            })
            continue
        
        #  Kabat 
        if kabat_label is None:
            details["mismatches"].append({
                "residue_idx": residue_idx,
                "original_aa": original_aa,
                "error": "kabat_label_missing"
            })
            continue
        
        # 
        imgt_aa = imgt_label_to_aa.get(imgt_label)
        kabat_aa = kabat_label_to_aa.get(kabat_label)
        
        # ：IMGT  Kabat 
        #  mapping  aa，
        mapped_aa = mapping.get("aa", original_aa)
        
        if imgt_aa is not None and imgt_aa != original_aa:
            details["mismatches"].append({
                "residue_idx": residue_idx,
                "original_aa": original_aa,
                "imgt_label": imgt_label,
                "imgt_aa": imgt_aa,
                "error": "imgt_aa_mismatch"
            })
        
        if kabat_aa is not None and kabat_aa != original_aa:
            details["mismatches"].append({
                "residue_idx": residue_idx,
                "original_aa": original_aa,
                "kabat_label": kabat_label,
                "kabat_aa": kabat_aa,
                "error": "kabat_aa_mismatch"
            })
        
        # ：IMGT  Kabat （）
        # 
        # ，，
        if imgt_aa is not None and kabat_aa is not None and imgt_aa != kabat_aa:
            # ，
            if imgt_aa == original_aa and kabat_aa != original_aa:
                details["mismatches"].append({
                    "residue_idx": residue_idx,
                    "original_aa": original_aa,
                    "imgt_label": imgt_label,
                    "imgt_aa": imgt_aa,
                    "kabat_label": kabat_label,
                    "kabat_aa": kabat_aa,
                    "error": "kabat_aa_mismatch_with_imgt"
                })
            elif kabat_aa == original_aa and imgt_aa != original_aa:
                details["mismatches"].append({
                    "residue_idx": residue_idx,
                    "original_aa": original_aa,
                    "imgt_label": imgt_label,
                    "imgt_aa": imgt_aa,
                    "kabat_label": kabat_label,
                    "kabat_aa": kabat_aa,
                    "error": "imgt_aa_mismatch_with_kabat"
                })
            else:
                # ，
                details["mismatches"].append({
                    "residue_idx": residue_idx,
                    "original_aa": original_aa,
                    "imgt_label": imgt_label,
                    "imgt_aa": imgt_aa,
                    "kabat_label": kabat_label,
                    "kabat_aa": kabat_aa,
                    "error": "both_imgt_kabat_aa_mismatch"
                })
    
    all_pass = len(details["mismatches"]) == 0
    
    return all_pass, details


def check_c_hallmark_debug(
    imgt_rows: List[Dict[str, Any]],
    kabat_rows: List[Dict[str, Any]],
    mapping: Dict[str, Any],
    hallmark_positions: List[int] = [44, 45, 47],  # FR2 hallmarks; pos37 is CDR1
) -> Tuple[bool, Dict[str, Any]]:
    """
    Check C: （V2 Schema）
    
     VHH FR2 hallmarks IMGT 44/45/47  debug 。
    (pos37 is CDR1, not a hallmark — preserved by FR-only graft)
     V2 schema： slot_defined  residue_present。
    
    Returns:
        (pass, details)
    """
    details = {
        "hallmark_positions": {},  # （）
        "hallmark_positions_v2": {},  # 
    }
    
    #  Kabat 
    kabat_label_to_info = {}
    for row in kabat_rows:
        pos = row.get("pos")
        ins_code = row.get("ins_code", " ").strip()
        aa = row.get("aa", "")
        label = f"{pos}{ins_code}" if ins_code else str(pos)
        kabat_label_to_info[label] = {
            "pos": pos,
            "ins_code": ins_code,
            "aa": aa,
            "label": label,
        }
    
    #  IMGT 
    imgt_label_to_info = {}
    for row in imgt_rows:
        pos = row.get("pos")
        ins_code = row.get("ins_code", " ").strip()
        aa = row.get("aa", "")
        label = f"{pos}{ins_code}" if ins_code else str(pos)
        imgt_label_to_info[label] = {
            "pos": pos,
            "ins_code": ins_code,
            "aa": aa,
            "label": label,
        }
    
    # ：mapping  kabat_to_imgt （）
    # ：{"37": "37", "44": "44", ...}
    kabat_to_imgt = mapping.get("kabat_to_imgt", {})
    
    #  mapping  JSON （"kabat_37" -> "imgt_37"），
    #  validate_dual_numbering  mapping，
    
    all_pass = True
    
    for kabat_pos in hallmark_positions:
        # ========== V2 Schema  ==========
        # 1.  Kabat 
        # slot_defined: hallmark 
        kabat_slot_defined = True
        
        #  Kabat （）
        found_kabat_labels = []
        for label in kabat_label_to_info.keys():
            try:
                label_pos = int(label.rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
                if label_pos == kabat_pos:
                    found_kabat_labels.append(label)
            except (ValueError, AttributeError):
                continue
        
        # residue_present:  gap （ IMGT V-domain）
        # out_of_domain: ， IMGT V-domain
        kabat_residue_present = False
        kabat_out_of_domain = False
        kabat_label = None
        kabat_aa = None
        
        if found_kabat_labels:
            kabat_label = found_kabat_labels[0]
            kabat_info = kabat_label_to_info[kabat_label]
            kabat_aa_raw = kabat_info["aa"]
            if kabat_aa_raw and kabat_aa_raw != "-":
                # ， IMGT V-domain
                #  IMGT 
                has_imgt_mapping = (kabat_label in kabat_to_imgt and 
                                   kabat_to_imgt[kabat_label] is not None)
                
                if has_imgt_mapping:
                    #  →  V-domain → residue_present=true
                    kabat_residue_present = True
                    kabat_aa = kabat_aa_raw
                else:
                    #  →  V-domain → out_of_domain=true, residue_present=false
                    kabat_out_of_domain = True
                    kabat_aa = kabat_aa_raw  # 
        
        # 2.  IMGT 
        imgt_label = None
        imgt_slot_defined = True  # IMGT 
        imgt_residue_present = False
        imgt_aa = None
        
        # 
        # ：kabat_to_imgt （ "37"），（ "37"） None
        if kabat_label and kabat_label in kabat_to_imgt:
            mapped_imgt_label_str = kabat_to_imgt[kabat_label]
            if mapped_imgt_label_str:
                # mapped_imgt_label_str （ "37"），
                imgt_label = mapped_imgt_label_str
                imgt_info = imgt_label_to_info.get(imgt_label)
                if imgt_info:
                    imgt_aa_raw = imgt_info["aa"]
                    if imgt_aa_raw and imgt_aa_raw != "-":
                        imgt_residue_present = True
                        imgt_aa = imgt_aa_raw
        
        # 3. （）
        mapping_status = None
        mapping_mapped = False
        mapping_reason = None
        
        if not kabat_residue_present and not kabat_out_of_domain:
            # Kabat （gap）→ gap
            mapping_status = "gap"
            mapping_mapped = False
            mapping_reason = "gap"
        elif kabat_out_of_domain:
            # Kabat  IMGT  → gap + out_of_domain
            mapping_status = "gap"
            mapping_mapped = False
            mapping_reason = "kabat_residue_out_of_imgt_domain"
        elif imgt_label is None:
            # ，（）→ unmapped（）
            mapping_status = "unmapped"
            mapping_mapped = False
            mapping_reason = "unmapped"
        elif not imgt_residue_present:
            # IMGT  gap
            mapping_status = "gap"
            mapping_mapped = False
            mapping_reason = "gap"
        elif imgt_aa == kabat_aa:
            # 
            mapping_status = "already_satisfied"
            mapping_mapped = True
            mapping_reason = "already_satisfied"
        else:
            # 
            mapping_status = "mapped"
            mapping_mapped = True
            mapping_reason = "mapped"
        
        #  V2 （ out_of_domain）
        hallmark_v2 = {
            "kabat": {
                "label": str(kabat_pos) if kabat_label is None else kabat_label,
                "slot_defined": kabat_slot_defined,
                "residue_present": kabat_residue_present,
                "out_of_domain": kabat_out_of_domain,
                "aa": kabat_aa,
            },
            "imgt": {
                "label": imgt_label,
                "slot_defined": imgt_slot_defined,
                "residue_present": imgt_residue_present,
                "aa": imgt_aa,
            },
            "mapping": {
                "status": mapping_status,
                "mapped": mapping_mapped,
                "reason": mapping_reason,
            }
        }
        
        details["hallmark_positions_v2"][str(kabat_pos)] = hallmark_v2
        
        # ========== （）==========
        # 
        details["hallmark_positions"][kabat_pos] = {
            "exists": kabat_residue_present,  # ，deprecated
            "kabat_label": kabat_label,
            "aa": kabat_aa,
            "mapped_imgt_label": imgt_label,
            "mapped_imgt_aa": imgt_aa,
            "reason": mapping_reason,
        }
        
        # （Gate C0: ）
        # 1:  residue_present=false  out_of_domain=false， aa  null
        if not kabat_residue_present and not kabat_out_of_domain and kabat_aa is not None:
            all_pass = False
        # 2:  out_of_domain=true， residue_present  false
        if kabat_out_of_domain and kabat_residue_present:
            all_pass = False
        # 3:  residue_present=true， out_of_domain  false
        if kabat_residue_present and kabat_out_of_domain:
            all_pass = False
        # 4: IMGT  residue_present=false， aa  null
        if not imgt_residue_present and imgt_aa is not None:
            all_pass = False
        
        # 5:  mapping.status="gap"， mapping.mapped  false
        if mapping_status == "gap" and mapping_mapped:
            all_pass = False
        
        # 6:  mapping.status="mapped"， residue_present  true
        if mapping_status == "mapped" and (not kabat_residue_present or not imgt_residue_present):
            all_pass = False
        
        # 7:  mapping.status="unmapped"，，
        # （ fail， Gate C1 ）
    
    return all_pass, details


def check_d_variant_diff_traceability(
    scaffold_seq: str,
    variant_seq: str,
    scaffold_numbering: Dict[str, Any],
    variant_numbering: Dict[str, Any],
    diff_vs_scaffold: List[Dict[str, Any]],
) -> Tuple[bool, Dict[str, Any]]:
    """
    Check D: 
    
     diff_vs_scaffold  mutation ， from/to 。
    
    Returns:
        (pass, details)
    """
    details = {
        "total_mutations": len(diff_vs_scaffold),
        "verified_mutations": 0,
        "failed_mutations": [],
    }
    
    #  scaffold  variant  IMGT 
    scaffold_imgt_pos_to_aa = {}
    for row in scaffold_numbering.get("imgt_rows", []):
        pos = row.get("pos")
        aa = row.get("aa", "")
        if pos and aa and aa != "-":
            scaffold_imgt_pos_to_aa[pos] = aa
    
    variant_imgt_pos_to_aa = {}
    for row in variant_numbering.get("imgt_rows", []):
        pos = row.get("pos")
        aa = row.get("aa", "")
        if pos and aa and aa != "-":
            variant_imgt_pos_to_aa[pos] = aa
    
    #  mutation
    for mutation in diff_vs_scaffold:
        imgt_pos = mutation.get("imgt_pos")
        from_aa = mutation.get("from")
        to_aa = mutation.get("to")
        
        if imgt_pos is None:
            details["failed_mutations"].append({
                "mutation": mutation,
                "error": "missing_imgt_pos"
            })
            continue
        
        #  from 
        scaffold_aa = scaffold_imgt_pos_to_aa.get(imgt_pos)
        if scaffold_aa != from_aa:
            details["failed_mutations"].append({
                "mutation": mutation,
                "error": "from_aa_mismatch",
                "expected": scaffold_aa,
                "actual": from_aa,
            })
            continue
        
        #  to 
        variant_aa = variant_imgt_pos_to_aa.get(imgt_pos)
        if variant_aa != to_aa:
            details["failed_mutations"].append({
                "mutation": mutation,
                "error": "to_aa_mismatch",
                "expected": variant_aa,
                "actual": to_aa,
            })
            continue
        
        details["verified_mutations"] += 1
    
    all_pass = len(details["failed_mutations"]) == 0
    
    return all_pass, details


def validate_dual_numbering(
    original_seq: str,
    imgt_rows: List[Dict[str, Any]],
    kabat_rows: List[Dict[str, Any]],
    mapping: Dict[str, Any],
) -> Dict[str, Any]:
    """
    
    
    Returns:
        
    """
    results = {
        "check_a": {},
        "check_b": {},
        "check_c": {},
        "all_passed": False,
    }
    
    # Check A: 
    check_a_pass, check_a_details = check_a_reconstruction(original_seq, imgt_rows, kabat_rows)
    results["check_a"] = {
        "pass": check_a_pass,
        "details": check_a_details,
    }
    
    # Check B: 
    residue_index_map = mapping.get("residue_index_map", {})
    check_b_pass, check_b_details = check_b_residue_index_alignment(
        original_seq, residue_index_map, imgt_rows, kabat_rows
    )
    results["check_b"] = {
        "pass": check_b_pass,
        "details": check_b_details,
    }
    
    # Check C: 
    check_c_pass, check_c_details = check_c_hallmark_debug(imgt_rows, kabat_rows, mapping)
    results["check_c"] = {
        "pass": check_c_pass,
        "details": check_c_details,
    }
    
    results["all_passed"] = check_a_pass and check_b_pass and check_c_pass
    
    return results

