#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 germline  IMGT/Kabat  + FR1/CDR1/FR2/CDR2/FR3 

（IMGT + Kabat）， IMGT 。
 QA，。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
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


def load_germline_sequences(input_path: Path) -> Dict[str, str]:
    """
     germline （ FASTA  JSON）
    
    Returns:
        {sequence_id: sequence_aa}
    """
    sequences = {}
    
    if input_path.suffix.lower() == ".json":
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        #  JSON 
        if isinstance(data, dict):
            #  "entries" （ IGHV_aa.json ）
            if "entries" in data and isinstance(data["entries"], list):
                for entry in data["entries"]:
                    if isinstance(entry, dict):
                        seq_id = entry.get("id") or entry.get("name") or entry.get("gene")
                        seq = entry.get("sequence") or entry.get("aa") or entry.get("sequence_aa")
                        if seq_id and seq:
                            sequences[seq_id] = seq
            else:
                # 
                for key, value in data.items():
                    if isinstance(value, dict):
                        # {"id": {"sequence": "...", ...}}
                        seq = value.get("sequence") or value.get("aa") or value.get("sequence_aa")
                        if seq:
                            sequences[key] = seq
                    elif isinstance(value, str):
                        # {"id": "sequence"}
                        sequences[key] = value
        elif isinstance(data, list):
            # ，
            for entry in data:
                if isinstance(entry, dict):
                    seq_id = entry.get("id") or entry.get("name") or entry.get("gene")
                    seq = entry.get("sequence") or entry.get("aa") or entry.get("sequence_aa")
                    if seq_id and seq:
                        sequences[seq_id] = seq
    
    elif input_path.suffix.lower() == ".fasta":
        with open(input_path, "r", encoding="utf-8") as f:
            current_id = None
            current_seq = []
            for line in f:
                line = line.strip()
                if line.startswith(">"):
                    if current_id and current_seq:
                        sequences[current_id] = "".join(current_seq)
                    current_id = line[1:].split()[0]  #  ID
                    current_seq = []
                else:
                    current_seq.append(line.upper())
            if current_id and current_seq:
                sequences[current_id] = "".join(current_seq)
    
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
    standard_aa = set("ACDEFGHIKLMNPQRSTVWY")
    if any(c not in standard_aa for c in seq_clean):
        non_standard = [c for c in set(seq_clean) if c not in standard_aa]
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


def calculate_coverage(imgt_pos_to_aa: Dict[str, str], start_pos: int, end_pos: int) -> float:
    """
     IMGT 
    
    Args:
        imgt_pos_to_aa: {imgt_pos: aa} 
        start_pos: 
        end_pos: 
    
    Returns:
        （0.0-1.0）
    """
    expected_count = end_pos - start_pos + 1
    present_count = 0
    
    for pos in range(start_pos, end_pos + 1):
        pos_str = str(pos)
        if pos_str in imgt_pos_to_aa:
            aa = imgt_pos_to_aa[pos_str]
            if aa and aa != "-":
                present_count += 1
    
    if expected_count == 0:
        return 0.0
    
    return present_count / expected_count


def classify_failure(
    imgt_success: bool,
    kabat_success: bool,
    coverage_1_104: float,
    coverage_1_117: float,
    error_imgt: Optional[str],
    error_kabat: Optional[str],
) -> str:
    """
    
    
    Returns:
        ， "success"
    """
    if not imgt_success:
        if error_imgt and "Unexpected characters" in error_imgt:
            return "unexpected_chars"
        elif error_imgt and "Empty" in error_imgt:
            return "numbering_fail_empty"
        else:
            return "numbering_fail"
    
    if not kabat_success:
        if error_kabat and "Unexpected characters" in error_kabat:
            return "unexpected_chars"
        elif error_kabat and "Empty" in error_kabat:
            return "numbering_fail_empty"
        else:
            return "kabat_numbering_fail"
    
    # 
    if coverage_1_104 < 0.95:
        return "truncated_before_104"
    
    if coverage_1_117 < 0.95:
        return "truncated_before_117"
    
    return "success"


def process_sequence(seq_id: str, seq: str) -> Dict[str, Any]:
    """
    
    
    Returns:
        、、
    """
    result = {
        "sequence_id": seq_id,
        "sequence_length": len(seq),
        "imgt_success": False,
        "kabat_success": False,
        "imgt_map": {},
        "kabat_map": {},
        "segments": {},
        "coverage_imgt_1_104": 0.0,
        "coverage_imgt_1_117": 0.0,
        "success_flags": {
            "imgt_numbering": False,
            "kabat_numbering": False,
            "segmentation": False,
        },
        "failure_classification": "unknown",
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
        
        # 4. 
        result["coverage_imgt_1_104"] = calculate_coverage(imgt_result["pos_to_aa"], 1, 104)
        result["coverage_imgt_1_117"] = calculate_coverage(imgt_result["pos_to_aa"], 1, 117)
    
    # 5. 
    result["failure_classification"] = classify_failure(
        imgt_success,
        kabat_success,
        result["coverage_imgt_1_104"],
        result["coverage_imgt_1_117"],
        result["error_messages"].get("imgt"),
        result["error_messages"].get("kabat"),
    )
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description=" germline  IMGT/Kabat  + FR1/CDR1/FR2/CDR2/FR3 "
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "IGHV_aa.fasta",
        help=" germline （FASTA  JSON）",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" germline  IMGT/Kabat  + FR1/CDR1/FR2/CDR2/FR3 ")
    print("=" * 80)
    print()
    
    # 1. 
    print(f"[1/4]  germline : {args.input}")
    if not args.input.exists():
        print(f"  ❌ : {args.input}")
        return
    
    sequences = load_germline_sequences(args.input)
    print(f"  ✅  {len(sequences)} ")
    print()
    
    # 2. 
    print(f"[2/4]  {len(sequences)} ...")
    results = []
    success_count = 0
    failure_count = 0
    
    for i, (seq_id, seq) in enumerate(sequences.items(), 1):
        if i % 50 == 0:
            print(f"  : {i}/{len(sequences)}")
        
        result = process_sequence(seq_id, seq)
        results.append(result)
        
        if result["failure_classification"] == "success":
            success_count += 1
        else:
            failure_count += 1
    
    print(f"  ✅ :  {success_count} ， {failure_count} ")
    print()
    
    # 3. 
    print("[3/4] ...")
    failure_stats = {}
    for result in results:
        failure_class = result["failure_classification"]
        failure_stats[failure_class] = failure_stats.get(failure_class, 0) + 1
    
    for failure_class, count in sorted(failure_stats.items()):
        print(f"  {failure_class}: {count} ")
    print()
    
    # 4. 
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    #  JSONL
    jsonl_path = args.output_dir / "germline_numbering_segments.jsonl"
    print(f"[4/4]  JSONL: {jsonl_path}")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(f"  ✅  {len(results)} ")
    
    #  CSV 
    csv_path = args.output_dir / "germline_numbering_summary.csv"
    print(f"   CSV : {csv_path}")
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "sequence_id",
            "sequence_length",
            "imgt_success",
            "kabat_success",
            "FR1_len",
            "CDR1_len",
            "FR2_len",
            "CDR2_len",
            "FR3_len",
            "coverage_imgt_1_104",
            "coverage_imgt_1_117",
            "failure_classification",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            segments = result.get("segments", {})
            writer.writerow({
                "sequence_id": result["sequence_id"],
                "sequence_length": result["sequence_length"],
                "imgt_success": result["imgt_success"],
                "kabat_success": result["kabat_success"],
                "FR1_len": len(segments.get("FR1", "")),
                "CDR1_len": len(segments.get("CDR1", "")),
                "FR2_len": len(segments.get("FR2", "")),
                "CDR2_len": len(segments.get("CDR2", "")),
                "FR3_len": len(segments.get("FR3", "")),
                "coverage_imgt_1_104": round(result["coverage_imgt_1_104"], 4),
                "coverage_imgt_1_117": round(result["coverage_imgt_1_117"], 4),
                "failure_classification": result["failure_classification"],
            })
    
    print(f"  ✅ ")
    print()
    
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()
