#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 IGHJ raw  FR4

 IGHJ ，（query_VH + IGHJ），
 IMGT ， 118（FR4 ）。
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
        result_dict: {"numbering": [...], "has_118": bool, "fr4_len": int, "motif_118_121": str}
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
        
        #  118
        has_118 = False
        fr4_len = 0
        motif_118_121 = ""
        
        # 
        pos_to_aa = {}
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
                        pos_to_aa[pos_int] = str(aa)
                except (ValueError, TypeError):
                    continue
        
        #  118
        if 118 in pos_to_aa:
            has_118 = True
            #  FR4 （ 118 ）
            max_pos = max(pos_to_aa.keys()) if pos_to_aa else 0
            fr4_len = max_pos - 118 + 1 if max_pos >= 118 else 0
            
            #  motif 118-121
            motif_chars = []
            for pos in [118, 119, 120, 121]:
                if pos in pos_to_aa:
                    motif_chars.append(pos_to_aa[pos])
                else:
                    motif_chars.append("-")
            motif_118_121 = "".join(motif_chars)
        
        return True, {
            "numbering": numbering,
            "has_118": has_118,
            "fr4_len": fr4_len,
            "motif_118_121": motif_118_121,
        }, None
        
    except Exception as e:
        return False, None, f"ANARCII numbering failed: {e}"


def validate_ighj(
    ighj_id: str,
    ighj_aa: str,
    query_vh_seq: str,
) -> Dict[str, any]:
    """
     IGHJ 
    
    Returns:
        {
            "ighj_id": str,
            "aa_len": int,
            "anarcii_success": bool,
            "imgt_has_118": bool,
            "fr4_len_detected": int,
            "motif_118_121": str,
            "fail_reason": str | None,
        }
    """
    result = {
        "ighj_id": ighj_id,
        "aa_len": len(ighj_aa),
        "anarcii_success": False,
        "imgt_has_118": False,
        "fr4_len_detected": 0,
        "motif_118_121": "",
        "fail_reason": None,
    }
    
    # ：query_VH + IGHJ
    test_seq = query_vh_seq + ighj_aa
    
    #  ANARCII IMGT 
    success, imgt_result, error = run_anarcii_imgt(test_seq)
    
    if not success:
        result["fail_reason"] = f"numbering_error: {error}"
        return result
    
    result["anarcii_success"] = True
    result["imgt_has_118"] = imgt_result.get("has_118", False)
    result["fr4_len_detected"] = imgt_result.get("fr4_len", 0)
    result["motif_118_121"] = imgt_result.get("motif_118_121", "")
    
    #  PASS/FAIL
    if result["anarcii_success"] and result["imgt_has_118"]:
        # PASS
        result["fail_reason"] = None
    else:
        # FAIL
        if not result["imgt_has_118"]:
            result["fail_reason"] = "no_118"
        else:
            result["fail_reason"] = "unknown_error"
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description=" IGHJ raw  FR4"
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
        help=" VH （，）",
    )
    parser.add_argument(
        "--query_vh_file",
        type=Path,
        help=" VH （FASTA ）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output" / "ighj_raw_validation.csv",
        help=" CSV ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" IGHJ raw  FR4")
    print("=" * 80)
    print()
    
    #  IGHJ raw
    ighj_json_path = Path(args.ighj_json)
    if not ighj_json_path.is_absolute():
        ighj_json_path = PROJECT_ROOT / ighj_json_path
    
    if not ighj_json_path.exists():
        print(f"❌ IGHJ JSON : {ighj_json_path}")
        return
    
    print(f"[1/3]  IGHJ raw: {ighj_json_path}")
    ighj_data = load_ighj_raw(ighj_json_path)
    print(f"  ✅  {len(ighj_data)}  IGHJ ")
    print()
    
    #  VH 
    print(f"[2/3]  VH ...")
    if args.query_vh:
        query_vh_seq = args.query_vh
    elif args.query_vh_file:
        query_vh_path = Path(args.query_vh_file)
        if not query_vh_path.is_absolute():
            query_vh_path = PROJECT_ROOT / query_vh_path
        
        #  FASTA 
        with open(query_vh_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            query_vh_seq = "".join([line.strip() for line in lines if not line.startswith(">")])
    else:
        # （EGFR 7D12 VHH）
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
    
    #  IGHJ
    print(f"[3/3]  {len(ighj_data)}  IGHJ ...")
    results = []
    
    for ighj_id, ighj_entry in sorted(ighj_data.items()):
        ighj_aa = ighj_entry.get("aa", "")
        if not ighj_aa:
            print(f"  ⚠️   {ighj_id}: ")
            continue
        
        result = validate_ighj(ighj_id, ighj_aa, query_vh_seq)
        results.append(result)
        
        status = "✅ PASS" if result["fail_reason"] is None else "❌ FAIL"
        print(f"  {status} {ighj_id}: has_118={result['imgt_has_118']}, fr4_len={result['fr4_len_detected']}")
    
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
            "ighj_id", "aa_len", "anarcii_success", "imgt_has_118",
            "fr4_len_detected", "motif_118_121", "fail_reason"
        ])
        writer.writeheader()
        for result in results:
            writer.writerow({
                "ighj_id": result["ighj_id"],
                "aa_len": result["aa_len"],
                "anarcii_success": result["anarcii_success"],
                "imgt_has_118": result["imgt_has_118"],
                "fr4_len_detected": result["fr4_len_detected"],
                "motif_118_121": result["motif_118_121"],
                "fail_reason": result["fail_reason"] or "",
            })
    
    print(f"✅ : {output_path}")
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()













