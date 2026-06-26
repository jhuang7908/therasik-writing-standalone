#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_vhh_germline_assets_v1.py

 +  + IMGT  VHH germline （ v1_clean ）

：data/germlines/vhh_v1/raw_fasta/*.fasta
：data/germlines/vhh_v1/vhh_germline_assets_clean.jsonl
      data/germlines/vhh_v1/qc/vhh_germline_assets_dropped.csv

 v1_clean ：
- IMGT+Kabat 
- segments（FR1/CDR1/FR2/CDR2/FR3）
-  20AA
-  qa_status
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# IMGT 
IMGT_REGIONS = {
    "FR1": {"start": 1, "end": 26},
    "CDR1": {"start": 27, "end": 38},
    "FR2": {"start": 39, "end": 55},
    "CDR2": {"start": 56, "end": 65},
    "FR3": {"start": 66, "end": 104},
    "CDR3": {"start": 105, "end": 117},
    "FR4": {"start": 118, "end": 128},
}

#  20 
STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")

# VHH hallmark （ vhh_hallmarks.json）
VHH_HALLMARK_POSITIONS = {
    37: {
        "typical_vhh_aas": ["F", "Y", "V"],
        "typical_human_vh_aas": ["V", "I", "L"],
    },
    44: {
        "typical_vhh_aas": ["E", "Q", "D"],
        "typical_human_vh_aas": ["G"],
    },
    45: {
        "typical_vhh_aas": ["R", "K"],
        "typical_human_vh_aas": ["L"],
    },
    47: {
        "typical_vhh_aas": ["W"],
        "typical_human_vh_aas": ["W"],
    },
}

# 
INPUT_DIR = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "raw_fasta"
OUTPUT_DIR = PROJECT_ROOT / "data" / "germlines" / "vhh_v1"
OUTPUT_JSONL = OUTPUT_DIR / "vhh_germline_assets_clean.jsonl"
OUTPUT_DROPPED_CSV = OUTPUT_DIR / "qc" / "vhh_germline_assets_dropped.csv"


def load_fasta_sequences(fasta_path: Path) -> Dict[str, str]:
    """
     FASTA ， {header: sequence} 
    """
    sequences = {}
    if not fasta_path.exists():
        return sequences
    
    name = None
    seq = []
    
    with open(fasta_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    sequences[name] = "".join(seq)
                name = line[1:].split()[0]  #  ID
                seq = []
            else:
                seq.append(line.upper())
        if name is not None:
            sequences[name] = "".join(seq)
    
    return sequences


def run_anarcii_numbering(seq: str, scheme: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
     ANARCII 
    
    Args:
        seq: 
        scheme: "imgt"  "kabat"
    
    Returns:
        (success, result_dict, error_message)
        result_dict: {"numbering": [...], "pos_to_aa": {pos: aa}, ...}
    """
    try:
        from anarcii import Anarcii
    except ImportError:
        return False, None, "anarcii package not found"
    
    seq_clean = seq.strip().upper().replace(" ", "").replace("\n", "").replace("\r", "")
    if not seq_clean:
        return False, None, "Empty sequence"
    
    # 
    if any(c not in STANDARD_AA for c in seq_clean):
        non_standard = [c for c in set(seq_clean) if c not in STANDARD_AA]
        return False, None, f"Unexpected characters: {non_standard}"
    
    try:
        anarcii_obj = Anarcii(
            seq_type="antibody",
            mode="accuracy",
            batch_size=32,
            cpu=True,
            ncpu=-1,
            verbose=False,
        )
        
        # 
        result = anarcii_obj.number(seq_clean)
        
        if scheme == "kabat":
            result = anarcii_obj.to_scheme('kabat')
        
        # 
        key = next(iter(result.keys()))
        seq_info = result.get(key, {})
        numbering = seq_info.get("numbering", [])
        
        if not numbering:
            return False, None, "Empty numbering result"
        
        #  pos_to_aa 
        pos_to_aa = {}
        for item in numbering:
            if not isinstance(item, tuple) or len(item) < 2:
                continue
            pos_info, aa = item[0], item[1]
            if pos_info is None or aa == "-":
                continue
            if not isinstance(pos_info, tuple) or len(pos_info) < 1:
                continue
            
            pos = pos_info[0]
            try:
                pos_num = int(pos)
            except (ValueError, TypeError):
                continue
            
            #  Kabat，（ 35A, 35B）
            if scheme == "kabat" and len(pos_info) > 1:
                ins_code = pos_info[1]
                if ins_code and ins_code.strip():
                    pos_label = f"{pos_num}{ins_code.strip()}"
                else:
                    pos_label = str(pos_num)
            else:
                pos_label = str(pos_num)
            
            pos_to_aa[pos_label] = aa
        
        return True, {
            "numbering": numbering,
            "pos_to_aa": pos_to_aa,
            "scheme": scheme,
        }, None
        
    except Exception as e:
        return False, None, f"Numbering error: {str(e)}"


def extract_segments_from_imgt(imgt_pos_to_aa: Dict[str, str]) -> Dict[str, str]:
    """
     IMGT  FR1/CDR1/FR2/CDR2/FR3 
    
    Args:
        imgt_pos_to_aa: {imgt_pos: aa} （pos ， "1", "27"）
    
    Returns:
        {"FR1": "...", "CDR1": "...", "FR2": "...", "CDR2": "...", "FR3": "..."}
    """
    segments = {}
    
    for region_name, region_info in IMGT_REGIONS.items():
        if region_name == "CDR3" or region_name == "FR4":
            continue  #  CDR3  FR4
        
        start_pos = region_info["start"]
        end_pos = region_info["end"]
        
        region_aa_list = []
        for pos in range(start_pos, end_pos + 1):
            pos_str = str(pos)
            if pos_str in imgt_pos_to_aa:
                aa = imgt_pos_to_aa[pos_str]
                if aa and aa != "-":
                    region_aa_list.append(aa)
        
        segments[region_name] = "".join(region_aa_list)
    
    return segments


def check_standard_aa_only(seq: str) -> bool:
    """
     20 
    """
    if not seq:
        return False
    return all(c in STANDARD_AA for c in seq.upper())


def calculate_vhh_hallmark_score(imgt_map: Dict[str, str]) -> Dict[str, Any]:
    """
     VHH hallmark 
    
    Args:
        imgt_map: {imgt_pos: aa} （pos ， "37", "44"）
    
    Returns:
        {
            "kabat_positions": {"37": "Y", "44": "Q", "45": "R", "47": "W"},
            "score": 0.0-1.0,
            "label": "vhh_like" | "vh_like" | "ambiguous"
        }
    """
    hallmark_positions = {}
    matches = 0
    total = 0
    
    for pos in [37, 44, 45, 47]:
        pos_str = str(pos)
        aa = imgt_map.get(pos_str, "-")
        hallmark_positions[str(pos)] = aa
        
        if aa and aa != "-":
            total += 1
            hallmark_def = VHH_HALLMARK_POSITIONS.get(pos, {})
            typical_vhh_aas = hallmark_def.get("typical_vhh_aas", [])
            if aa in typical_vhh_aas:
                matches += 1
    
    #  score（）
    score = matches / total if total > 0 else 0.0
    
    # 
    if score >= 0.75:  # 3/4  4/4 
        label = "vhh_like"
    elif score <= 0.25:  # 0/4  1/4 
        label = "vh_like"
    else:  # 2/4 
        label = "ambiguous"
    
    return {
        "kabat_positions": hallmark_positions,  # ： IMGT ， kabat_positions 
        "score": round(score, 4),
        "label": label,
    }


def process_sequence(seq_id: str, seq: str) -> Dict[str, Any]:
    """
    ： + 
    
    Returns:
        、
    """
    result = {
        "sequence_id": seq_id,
        "sequence_length": len(seq),
        "imgt_success": False,
        "kabat_success": False,
        "imgt_map": {},
        "kabat_map": {},
        "segments": {},
        "success_flags": {
            "imgt_numbering": False,
            "kabat_numbering": False,
            "segmentation": False,
        },
        "error_messages": {},
    }
    
    # 1. IMGT 
    imgt_success, imgt_result, imgt_error = run_anarcii_numbering(seq, "imgt")
    result["imgt_success"] = imgt_success
    result["success_flags"]["imgt_numbering"] = imgt_success
    
    if imgt_success and imgt_result:
        result["imgt_map"] = imgt_result["pos_to_aa"]
    else:
        result["error_messages"]["imgt"] = imgt_error or "Unknown error"
    
    # 2. Kabat 
    kabat_success, kabat_result, kabat_error = run_anarcii_numbering(seq, "kabat")
    result["kabat_success"] = kabat_success
    result["success_flags"]["kabat_numbering"] = kabat_success
    
    if kabat_success and kabat_result:
        result["kabat_map"] = kabat_result["pos_to_aa"]
    else:
        result["error_messages"]["kabat"] = kabat_error or "Unknown error"
    
    # 3.  segments（ IMGT ）
    if imgt_success and imgt_result:
        segments = extract_segments_from_imgt(imgt_result["pos_to_aa"])
        result["segments"] = segments
        result["success_flags"]["segmentation"] = len(segments) > 0
        
        # 4.  VHH hallmark 
        vhh_hallmark = calculate_vhh_hallmark_score(imgt_result["pos_to_aa"])
        result["vhh_hallmark"] = vhh_hallmark
    
    return result


def validate_germline_record(record: Dict[str, Any]) -> Tuple[bool, str]:
    """
     germline 
    
    Returns:
        (is_valid, reason)
        is_valid: True ，False 
        reason:  is_valid=False，； is_valid=True，
    """
    #  1: IMGT  Kabat 
    success_flags = record.get("success_flags", {})
    imgt_success = success_flags.get("imgt_numbering", False)
    kabat_success = success_flags.get("kabat_numbering", False)
    
    if not imgt_success:
        return False, "imgt_numbering_failed"
    
    if not kabat_success:
        return False, "kabat_numbering_failed"
    
    #  2: segments  > 0
    segments = record.get("segments", {})
    required_regions = ["FR1", "CDR1", "FR2", "CDR2", "FR3"]
    
    for region in required_regions:
        if region not in segments:
            return False, f"missing_segment_{region}"
        
        region_seq = segments[region]
        if not region_seq or len(region_seq) == 0:
            return False, f"empty_segment_{region}"
    
    #  3:  segments  AA
    for region in required_regions:
        region_seq = segments[region]
        if not check_standard_aa_only(region_seq):
            non_standard = [c for c in set(region_seq.upper()) if c not in STANDARD_AA]
            return False, f"non_standard_aa_in_{region}:{','.join(non_standard)}"
    
    # 
    return True, ""


def main():
    print("=" * 80)
    print("VHH Germline  +  + IMGT  (v1)")
    print("=" * 80)
    print()
    
    # 1.  FASTA 
    print(f"[1/5]  FASTA : {INPUT_DIR}")
    if not INPUT_DIR.exists():
        print(f"  ❌ : {INPUT_DIR}")
        return
    
    all_sequences = {}
    fasta_files = list(INPUT_DIR.glob("*.fasta"))
    
    if not fasta_files:
        print(f"  ❌  FASTA ")
        return
    
    for fasta_path in fasta_files:
        print(f"  : {fasta_path.name}")
        seqs = load_fasta_sequences(fasta_path)
        all_sequences.update(seqs)
        print(f"     {len(seqs)} ")
    
    print(f"  ✅  {len(all_sequences)} ")
    print()
    
    # 2. （ + ）
    print(f"[2/5]  {len(all_sequences)} （ + ）...")
    processed_records = []
    
    for i, (seq_id, seq) in enumerate(all_sequences.items(), 1):
        if i % 50 == 0:
            print(f"  : {i}/{len(all_sequences)}")
        
        record = process_sequence(seq_id, seq)
        processed_records.append(record)
    
    print(f"  ✅ ")
    print()
    
    # 3. 
    print(f"[3/5]  {len(processed_records)} ...")
    clean_records = []
    dropped_records = []
    
    for record in processed_records:
        is_valid, reason = validate_germline_record(record)
        
        if is_valid:
            #  qa_status 
            record["qa_status"] = "PASS_CLEAN"
            clean_records.append(record)
        else:
            dropped_records.append({
                "sequence_id": record.get("sequence_id", "unknown"),
                "reason": reason,
            })
    
    print(f"  ✅ : PASS {len(clean_records)} , DROP {len(dropped_records)} ")
    print()
    
    # 4.  DROP 
    print("[4/5] DROP ...")
    drop_reasons = Counter(r["reason"] for r in dropped_records)
    for reason, count in sorted(drop_reasons.items()):
        print(f"  {reason}: {count} ")
    print()
    
    # 5. 
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "qc").mkdir(parents=True, exist_ok=True)
    
    #  clean JSONL
    print(f"[5/5] ...")
    print(f"   clean JSONL: {OUTPUT_JSONL}")
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for record in clean_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  ✅  {len(clean_records)}  clean ")
    
    #  dropped CSV
    print(f"   dropped CSV: {OUTPUT_DROPPED_CSV}")
    with open(OUTPUT_DROPPED_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sequence_id", "reason"])
        writer.writeheader()
        writer.writerows(dropped_records)
    print(f"  ✅  {len(dropped_records)}  dropped ")
    print()
    
    # 6. 
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)
    print(f"✅ PASS: {len(clean_records)} ")
    print(f"❌ DROP: {len(dropped_records)} ")
    print()
    print("DROP :")
    for reason, count in sorted(drop_reasons.items()):
        print(f"  {reason}: {count} ")
    print()
    print(f":")
    print(f"  - {OUTPUT_JSONL}")
    print(f"  - {OUTPUT_DROPPED_CSV}")
    print("=" * 80)


if __name__ == "__main__":
    main()













