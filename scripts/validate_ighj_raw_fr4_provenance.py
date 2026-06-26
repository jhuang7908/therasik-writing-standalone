#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 IGHJ raw FR4 （）

 IMGT 118-128  IGHJ ， query VH。
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_ighj_raw(json_path: Path) -> Dict[str, Dict[str, str]]:
    """ IGHJ raw JSON"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_anarcii_imgt(seq: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
     ANARCII  IMGT 
    
    Returns:
        (success, result_dict, error_message)
        result_dict: {
            "numbering": [...],
            "pos_to_seq_index": {imgt_pos: seq_index},  # IMGT 
            "pos_to_aa": {imgt_pos: aa},  # IMGT 
        }
    """
    try:
        from anarcii import Anarcii
    except ImportError:
        return False, None, "anarcii package not found"
    
    seq_clean = seq.strip().upper().replace(" ", "").replace("\n", "").replace("\r", "")
    if not seq_clean:
        return False, None, "Empty sequence"
    
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
        result = anarcii_obj.number(seq_clean)
        
        # 
        key = next(iter(result.keys()))
        seq_info = result.get(key, {})
        numbering = seq_info.get("numbering", [])
        
        if not numbering:
            return False, None, "Empty numbering result"
        
        # 
        pos_to_seq_index = {}  # IMGT  -> （0-based）
        pos_to_aa = {}  # IMGT  -> 
        
        seq_index = 0  # （ gap）
        for item in numbering:
            if not isinstance(item, tuple) or len(item) < 2:
                continue
            pos_info, aa = item[0], item[1]
            
            if pos_info is None:
                continue
            
            if isinstance(pos_info, tuple) and len(pos_info) >= 1:
                pos_num = pos_info[0]
                try:
                    pos_int = int(pos_num)
                    if aa and aa != "-":
                        # ，
                        pos_to_seq_index[pos_int] = seq_index
                        pos_to_aa[pos_int] = str(aa)
                        seq_index += 1
                except (ValueError, TypeError):
                    continue
        
        return True, {
            "numbering": numbering,
            "pos_to_seq_index": pos_to_seq_index,
            "pos_to_aa": pos_to_aa,
        }, None
        
    except Exception as e:
        return False, None, f"ANARCII numbering failed: {e}"


def find_imgt117_end(query_vh_seq: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """
     query VH  IMGT 117 
    
    Returns:
        (success, seq_index, error_message)
        seq_index: query_vh_seq  IMGT 117 （0-based）
    """
    success, result, error = run_anarcii_imgt(query_vh_seq)
    
    if not success:
        return False, None, f"Query numbering failed: {error}"
    
    pos_to_seq_index = result.get("pos_to_seq_index", {})
    
    #  IMGT 117
    if 117 not in pos_to_seq_index:
        return False, None, "no_imgt117_in_query"
    
    seq_index_117 = pos_to_seq_index[117]
    return True, seq_index_117, None


def validate_ighj_with_provenance(
    ighj_id: str,
    ighj_aa: str,
    query_prefix: str,
) -> Dict[str, any]:
    """
     IGHJ ， FR4 
    
    Returns:
        {
            "ighj_id": str,
            "ighj_len": int,
            "anarcii_success": bool,
            "imgt_has_118": bool,
            "fr4_118_128": str,
            "motif_118_121": str,
            "fr4_all_from_j": bool,
            "fail_reason": str | None,
        }
    """
    result = {
        "ighj_id": ighj_id,
        "ighj_len": len(ighj_aa),
        "anarcii_success": False,
        "imgt_has_118": False,
        "fr4_118_128": "",
        "motif_118_121": "",
        "fr4_all_from_j": False,
        "fail_reason": None,
    }
    
    # ：query_prefix + IGHJ
    test_seq = query_prefix + ighj_aa
    query_prefix_len = len(query_prefix)
    
    #  ANARCII IMGT 
    success, imgt_result, error = run_anarcii_imgt(test_seq)
    
    if not success:
        result["fail_reason"] = f"numbering_error: {error}"
        return result
    
    result["anarcii_success"] = True
    
    pos_to_seq_index = imgt_result.get("pos_to_seq_index", {})
    pos_to_aa = imgt_result.get("pos_to_aa", {})
    
    #  118
    if 118 not in pos_to_seq_index:
        result["fail_reason"] = "no_118"
        return result
    
    result["imgt_has_118"] = True
    
    #  FR4 118-128 
    fr4_aa_list = []
    fr4_positions = []
    for pos in range(118, 129):  # 118-128
        if pos in pos_to_aa:
            fr4_aa_list.append(pos_to_aa[pos])
            fr4_positions.append(pos)
        else:
            fr4_aa_list.append("-")  # gap
    
    result["fr4_118_128"] = "".join(fr4_aa_list)
    
    #  motif 118-121（ fr4_118_128[0:4]）
    if len(fr4_aa_list) >= 4:
        result["motif_118_121"] = "".join(fr4_aa_list[:4])
    else:
        result["motif_118_121"] = "".join(fr4_aa_list)
    
    #  provenance：FR4  J 
    fr4_all_from_j = True
    fr4_from_query_positions = []
    
    for pos in fr4_positions:
        if pos in pos_to_seq_index:
            seq_index = pos_to_seq_index[pos]
            #  < query_prefix_len， query， J
            if seq_index < query_prefix_len:
                fr4_all_from_j = False
                fr4_from_query_positions.append(pos)
    
    result["fr4_all_from_j"] = fr4_all_from_j
    
    #  PASS/FAIL
    if result["anarcii_success"] and result["imgt_has_118"] and result["fr4_all_from_j"]:
        # PASS
        result["fail_reason"] = None
    else:
        # FAIL
        if not result["imgt_has_118"]:
            result["fail_reason"] = "no_118"
        elif not result["fr4_all_from_j"]:
            result["fail_reason"] = f"fr4_from_query: positions {fr4_from_query_positions}"
        else:
            result["fail_reason"] = "unknown_error"
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description=" IGHJ raw FR4 （）"
    )
    parser.add_argument(
        "--ighj_json",
        type=Path,
        default=PROJECT_ROOT / "data" / "ighj_aa_raw.json",
        help="IGHJ raw JSON ",
    )
    parser.add_argument(
        "--query_vh",
        type=str,
        help=" VH ",
    )
    parser.add_argument(
        "--query_vh_file",
        type=Path,
        help=" VH （FASTA ）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output" / "ighj_raw_validation_provenance.csv",
        help=" CSV ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" IGHJ raw FR4 （）")
    print("=" * 80)
    print()
    
    #  IGHJ raw
    ighj_json_path = Path(args.ighj_json)
    if not ighj_json_path.is_absolute():
        ighj_json_path = PROJECT_ROOT / ighj_json_path
    
    if not ighj_json_path.exists():
        print(f"❌ IGHJ JSON : {ighj_json_path}")
        return
    
    print(f"[1/4]  IGHJ raw: {ighj_json_path}")
    ighj_data = load_ighj_raw(ighj_json_path)
    print(f"  ✅  {len(ighj_data)}  IGHJ ")
    print()
    
    #  VH 
    print(f"[2/4]  VH ...")
    if args.query_vh:
        query_vh_seq = args.query_vh
    elif args.query_vh_file:
        query_vh_path = Path(args.query_vh_file)
        if not query_vh_path.is_absolute():
            query_vh_path = PROJECT_ROOT / query_vh_path
        
        with open(query_vh_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            query_vh_seq = "".join([line.strip() for line in lines if not line.startswith(">")])
    else:
        # 
        default_fasta = PROJECT_ROOT / "projects" / "EGFR_7D12_VHH" / "input" / "egfr_vhh.fasta"
        if default_fasta.exists():
            with open(default_fasta, "r", encoding="utf-8") as f:
                lines = f.readlines()
                query_vh_seq = "".join([line.strip() for line in lines if not line.startswith(">")])
            print(f"  : {default_fasta}")
        else:
            print(f"  ❌ ，: {default_fasta}")
            return
    
    print(f"  : {len(query_vh_seq)} aa")
    print()
    
    #  IMGT 117 
    print(f"[3/4]  query VH  IMGT 117 ...")
    success, imgt117_index, error = find_imgt117_end(query_vh_seq)
    
    if not success:
        print(f"  ❌ : {error}")
        return
    
    print(f"  ✅ IMGT 117 : {imgt117_index} (0-based)")
    
    #  query  IMGT 117 
    query_prefix = query_vh_seq[:imgt117_index + 1]
    print(f"  Query prefix : {len(query_prefix)} aa")
    print()
    
    #  IGHJ
    print(f"[4/4]  {len(ighj_data)}  IGHJ （ FR4 ）...")
    results = []
    
    for ighj_id, ighj_entry in sorted(ighj_data.items()):
        ighj_aa = ighj_entry.get("aa", "")
        if not ighj_aa:
            print(f"  ⚠️   {ighj_id}: ")
            continue
        
        result = validate_ighj_with_provenance(ighj_id, ighj_aa, query_prefix)
        results.append(result)
        
        status = "✅ PASS" if result["fail_reason"] is None else "❌ FAIL"
        fr4_info = f"fr4={result['fr4_118_128']}, all_from_j={result['fr4_all_from_j']}"
        print(f"  {status} {ighj_id}: {fr4_info}")
        if result["fail_reason"]:
            print(f"     : {result['fail_reason']}")
    
    print()
    
    # 
    pass_count = sum(1 for r in results if r["fail_reason"] is None)
    fail_count = len(results) - pass_count
    
    print("=" * 80)
    print("")
    print("=" * 80)
    print(f"✅ PASS: {pass_count} ")
    print(f"❌ FAIL: {fail_count} ")
    print()
    
    #  CSV
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "ighj_id", "ighj_len", "anarcii_success", "imgt_has_118",
            "fr4_118_128", "motif_118_121", "fr4_all_from_j", "fail_reason"
        ])
        writer.writeheader()
        for result in results:
            writer.writerow({
                "ighj_id": result["ighj_id"],
                "ighj_len": result["ighj_len"],
                "anarcii_success": result["anarcii_success"],
                "imgt_has_118": result["imgt_has_118"],
                "fr4_118_128": result["fr4_118_128"],
                "motif_118_121": result["motif_118_121"],
                "fr4_all_from_j": result["fr4_all_from_j"],
                "fail_reason": result["fail_reason"] or "",
            })
    
    print(f"✅ : {output_path}")
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()













