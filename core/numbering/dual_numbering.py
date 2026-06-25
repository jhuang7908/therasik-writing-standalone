"""
 - IMGT + Kabat

 IMGT  Kabat ，。
"""

from __future__ import annotations

from typing import List, Dict, Any, Tuple, Optional

try:
    from anarcii import Anarcii
    HAS_ANARCII = True
except ImportError:
    HAS_ANARCII = False
    Anarcii = None


class DualNumberingError(RuntimeError):
    """"""
    pass


def get_dual_numbering(seq: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
     IMGT  Kabat ，。
    
    Args:
        seq: 
    
    Returns:
        (imgt_rows, kabat_rows, mapping)
        
        imgt_rows: IMGT ， imgt_number_anarcii
        kabat_rows: Kabat ， imgt_rows
        mapping: {
            "imgt_to_kabat": {imgt_pos: kabat_pos},  # IMGT  -> Kabat 
            "kabat_to_imgt": {kabat_pos: imgt_pos},  # Kabat  -> IMGT 
            "residue_index_map": {residue_idx: {"imgt_pos": ..., "kabat_pos": ...}},  # 
            "gaps": {
                "imgt_missing": [pos, ...],  # IMGT 
                "kabat_missing": [pos, ...]  # Kabat 
            }
        }
    
    Raises:
        DualNumberingError: 
    """
    if not HAS_ANARCII:
        raise DualNumberingError("ANARCII is not available")
    
    if not seq or not isinstance(seq, str):
        raise DualNumberingError("Sequence must be a non-empty string")
    
    seq_clean = seq.strip().upper().replace(" ", "").replace("\n", "").replace("\r", "")
    if not seq_clean:
        raise DualNumberingError("Sequence is empty after cleaning")
    
    try:
        anarcii_obj = Anarcii(
            seq_type="antibody",
            mode="accuracy",
            batch_size=32,
            cpu=True,
            ncpu=-1,
            verbose=False,
        )
        
        #  IMGT 
        result_imgt = anarcii_obj.number(seq_clean)
        
        #  Kabat 
        result_kabat = anarcii_obj.to_scheme('kabat')
        
    except Exception as e:
        raise DualNumberingError(f"ANARCII numbering failed: {e}") from e
    
    #  IMGT 
    key = next(iter(result_imgt.keys()))
    seq_info_imgt = result_imgt.get(key, {})
    numbering_imgt = seq_info_imgt.get("numbering", [])
    chain_type = seq_info_imgt.get("chain_type", None)
    
    #  Kabat 
    seq_info_kabat = result_kabat.get(key, {})
    numbering_kabat = seq_info_kabat.get("numbering", [])
    
    if not numbering_imgt or not numbering_kabat:
        raise DualNumberingError("Empty numbering results")
    
    #  IMGT （ gap）
    imgt_rows: List[Dict[str, Any]] = []
    for item in numbering_imgt:
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        pos_info, aa = item[0], item[1]
        if pos_info is None:
            continue
        if not isinstance(pos_info, tuple) or len(pos_info) < 1:
            continue
        pos = pos_info[0]
        ins_code = pos_info[1] if len(pos_info) > 1 else " "
        try:
            pos_num = int(pos)
        except (ValueError, TypeError):
            continue
        imgt_rows.append({
            "pos": pos_num,
            "ins_code": str(ins_code),
            "aa": str(aa),  #  gap  "-"
            "chain_type": chain_type,
            "scheme": "imgt",
        })
    
    #  Kabat （ gap）
    kabat_rows: List[Dict[str, Any]] = []
    for item in numbering_kabat:
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        pos_info, aa = item[0], item[1]
        if pos_info is None:
            continue
        if not isinstance(pos_info, tuple) or len(pos_info) < 1:
            continue
        pos = pos_info[0]
        ins_code = pos_info[1] if len(pos_info) > 1 else " "
        try:
            pos_num = int(pos)
        except (ValueError, TypeError):
            continue
        kabat_rows.append({
            "pos": pos_num,
            "ins_code": str(ins_code),
            "aa": str(aa),  #  gap  "-"
            "chain_type": chain_type,
            "scheme": "kabat",
        })
    
    # 
    # ：ANARCII  numbering ，
    # 
    
    # ：{residue_index: {"imgt_label": ..., "kabat_label": ..., "aa": ...}}
    residue_index_map: Dict[int, Dict[str, Any]] = {}
    imgt_to_kabat: Dict[str, Optional[str]] = {}  # ，
    kabat_to_imgt: Dict[str, Optional[str]] = {}  # ，
    
    # ：
    # ANARCII  numbering ，
    #  IMGT  Kabat 
    
    # （）
    min_len = min(len(numbering_imgt), len(numbering_kabat))
    
    # 
    residue_idx = 0  # （ gap）
    for idx in range(min_len):
        imgt_item = numbering_imgt[idx]
        kabat_item = numbering_kabat[idx]
        
        if not isinstance(imgt_item, tuple) or not isinstance(kabat_item, tuple):
            continue
        
        imgt_pos_info, imgt_aa = imgt_item[0], imgt_item[1]
        kabat_pos_info, kabat_aa = kabat_item[0], kabat_item[1]
        
        #  gap： gap，（ residue_idx）
        if imgt_aa == "-" or kabat_aa == "-":
            # Gap ，
            continue
        
        if not isinstance(imgt_pos_info, tuple) or not isinstance(kabat_pos_info, tuple):
            continue
        
        imgt_pos = imgt_pos_info[0]
        imgt_ins = imgt_pos_info[1] if len(imgt_pos_info) > 1 else " "
        kabat_pos = kabat_pos_info[0]
        kabat_ins = kabat_pos_info[1] if len(kabat_pos_info) > 1 else " "
        
        try:
            imgt_pos_num = int(imgt_pos)
            kabat_pos_num = int(kabat_pos)
        except (ValueError, TypeError):
            continue
        
        # （， "35A", "35B"）
        imgt_label = f"{imgt_pos_num}{imgt_ins.strip()}" if imgt_ins.strip() else str(imgt_pos_num)
        kabat_label = f"{kabat_pos_num}{kabat_ins.strip()}" if kabat_ins.strip() else str(kabat_pos_num)
        
        # ：IMGT  Kabat （）
        # ，，（）
        
        # ： residue_idx 
        if residue_idx >= len(seq_clean):
            break
        
        # （）
        # ： IMGT  Kabat ，，
        imgt_to_kabat[imgt_label] = kabat_label
        kabat_to_imgt[kabat_label] = imgt_label
        
        residue_index_map[residue_idx] = {
            "imgt_label": imgt_label,
            "kabat_label": kabat_label,
            "aa": imgt_aa,  #  IMGT （）
            "is_gap": False
        }
        
        residue_idx += 1
    
    # （gap）
    #  IMGT  Kabat 
    all_imgt_positions = {row["pos"] for row in imgt_rows}
    all_kabat_positions = {row["pos"] for row in kabat_rows}
    
    # IMGT ： Kabat  IMGT 
    imgt_missing = []
    for kabat_pos in all_kabat_positions:
        if kabat_pos not in kabat_to_imgt:
            imgt_missing.append(kabat_pos)
    
    # Kabat ： IMGT  Kabat 
    kabat_missing = []
    for imgt_pos in all_imgt_positions:
        if imgt_pos not in imgt_to_kabat:
            kabat_missing.append(imgt_pos)
    
    mapping = {
        "imgt_to_kabat": imgt_to_kabat,
        "kabat_to_imgt": kabat_to_imgt,
        "residue_index_map": residue_index_map,
        "gaps": {
            "imgt_missing": sorted(imgt_missing),
            "kabat_missing": sorted(kabat_missing),
        }
    }
    
    return imgt_rows, kabat_rows, mapping


def build_numbering_maps_json(
    imgt_rows: List[Dict[str, Any]],
    kabat_rows: List[Dict[str, Any]],
    mapping: Dict[str, Any],
) -> Dict[str, Any]:
    """
     numbering_maps JSON 。
    
    Returns:
        {
            "scheme_primary": "imgt",
            "imgt": [{"pos": "1", "aa": "E"}, ...],  #  gap 
            "kabat": [{"pos": "1", "aa": "E"}, ...],  #  "35A"
            "imgt_to_kabat": {"imgt_1": "kabat_1", ...},
            "kabat_to_imgt": {"kabat_37": "imgt_??", ...},
            "residue_index_map": {0: {"imgt_label": "1", "kabat_label": "1", "aa": "E"}, ...},
            "gaps": {
                "imgt_missing": ["37", ...],
                "kabat_missing": ["...", ...]
            }
        }
    """
    # IMGT （）
    imgt_list = []
    for row in imgt_rows:
        pos = row["pos"]
        ins_code = row.get("ins_code", " ").strip()
        aa = row["aa"]
        label = f"{pos}{ins_code}" if ins_code else str(pos)
        imgt_list.append({
            "pos": label,  # ， "35A"
            "aa": aa,
        })
    
    # Kabat （）
    kabat_list = []
    for row in kabat_rows:
        pos = row["pos"]
        ins_code = row.get("ins_code", " ").strip()
        aa = row["aa"]
        label = f"{pos}{ins_code}" if ins_code else str(pos)
        kabat_list.append({
            "pos": label,  # ， "35A"
            "aa": aa,
        })
    
    # （）
    imgt_to_kabat_str = {}
    for imgt_label, kabat_label in mapping["imgt_to_kabat"].items():
        if kabat_label is not None:
            imgt_to_kabat_str[f"imgt_{imgt_label}"] = f"kabat_{kabat_label}"
        else:
            imgt_to_kabat_str[f"imgt_{imgt_label}"] = "gap"
    
    kabat_to_imgt_str = {}
    for kabat_label, imgt_label in mapping["kabat_to_imgt"].items():
        if imgt_label is not None:
            kabat_to_imgt_str[f"kabat_{kabat_label}"] = f"imgt_{imgt_label}"
        else:
            kabat_to_imgt_str[f"kabat_{kabat_label}"] = "gap"
    
    return {
        "scheme_primary": "imgt",
        "imgt": imgt_list,
        "kabat": kabat_list,
        "imgt_to_kabat": imgt_to_kabat_str,
        "kabat_to_imgt": kabat_to_imgt_str,
        "residue_index_map": mapping.get("residue_index_map", {}),
        "gaps": {
            "imgt_missing": [str(pos) for pos in mapping["gaps"]["imgt_missing"]],
            "kabat_missing": [str(pos) for pos in mapping["gaps"]["kabat_missing"]],
        }
    }

