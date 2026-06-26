#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QA ： V-domain 

 germline  scaffold ：
1. IMGT 
2. Check A：
3. V-domain （>= 95%）

：
- qa_vdomain_pass.csv：
- qa_vdomain_fail.csv：
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_fasta(fasta_path: Path) -> Dict[str, str]:
    """ FASTA ， {sequence_id: sequence}"""
    sequences = {}
    current_id = None
    current_seq = []
    
    with open(fasta_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith(">"):
                # 
                if current_id is not None:
                    sequences[current_id] = "".join(current_seq)
                
                # 
                current_id = line[1:].split()[0]  #  ID
                current_seq = []
            else:
                current_seq.append(line)
        
        # 
        if current_id is not None:
            sequences[current_id] = "".join(current_seq)
    
    return sequences


def run_imgt_numbering(seq: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
     ANARCII  IMGT 
    
    Returns:
        (imgt_rows, error_message)
        imgt_rows: [{"pos": int, "ins_code": str, "aa": str}, ...]
        error_message: None if success, error string if failed
    """
    try:
        from anarcii import Anarcii
    except ImportError:
        return None, "anarcii package not found"
    
    seq_clean = seq.strip().upper().replace(" ", "").replace("\n", "").replace("\r", "")
    if not seq_clean:
        return None, "Empty sequence"
    
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
            return None, "Empty numbering result"
        
        #  IMGT 
        imgt_rows: List[Dict[str, Any]] = []
        for item in numbering:
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
                "ins_code": str(ins_code).strip(),
                "aa": str(aa),
            })
        
        return imgt_rows, None
        
    except Exception as e:
        return None, f"ANARCII numbering failed: {e}"


def check_a_reconstruction(original_seq: str, imgt_rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Check A: IMGT 
    
    Returns:
        (pass, error_message)
    """
    # （ gap）
    reconstructed = ""
    for row in imgt_rows:
        aa = row.get("aa", "")
        if aa and aa != "-":
            reconstructed += aa
    
    if reconstructed != original_seq:
        return False, f"Reconstruction mismatch: len(original)={len(original_seq)}, len(reconstructed)={len(reconstructed)}"
    
    return True, ""


def calculate_vdomain_coverage(imgt_rows: List[Dict[str, Any]]) -> Tuple[float, int, int]:
    """
     V-domain 
    
    IMGT V-domain ：1-128（）
    
    Returns:
        (coverage, present_slots, expected_slots)
    """
    # IMGT V-domain ：1-128
    expected_slots = set(range(1, 129))
    
    # （ gap ）
    present_slots = set()
    for row in imgt_rows:
        pos = row.get("pos")
        aa = row.get("aa", "")
        if pos and aa and aa != "-":
            present_slots.add(pos)
    
    coverage = len(present_slots) / len(expected_slots) if expected_slots else 0.0
    
    return coverage, len(present_slots), len(expected_slots)


def process_sequence(seq_id: str, seq: str, min_coverage: float = 0.95) -> Dict[str, Any]:
    """
    
    
    Returns:
        {
            "sequence_id": str,
            "length": int,
            "imgt_coverage": float,
            "status": "PASS" | "FAIL",
            "fail_reason": str | None,
        }
    """
    result = {
        "sequence_id": seq_id,
        "length": len(seq),
        "imgt_coverage": 0.0,
        "status": "FAIL",
        "fail_reason": None,
    }
    
    # 1. IMGT 
    imgt_rows, error = run_imgt_numbering(seq)
    if error:
        result["fail_reason"] = f"numbering_error: {error}"
        return result
    
    # 2. Check A: 
    reconstruction_pass, recon_error = check_a_reconstruction(seq, imgt_rows)
    if not reconstruction_pass:
        result["fail_reason"] = f"reconstruction: {recon_error}"
        return result
    
    # 3. 
    coverage, present_slots, expected_slots = calculate_vdomain_coverage(imgt_rows)
    result["imgt_coverage"] = coverage
    
    if coverage < min_coverage:
        result["fail_reason"] = f"truncated_domain: coverage={coverage:.4f} < {min_coverage}"
        return result
    
    # 
    result["status"] = "PASS"
    result["fail_reason"] = None
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="QA ： V-domain "
    )
    parser.add_argument(
        "--germline_fasta",
        type=Path,
        help="Germline  FASTA ",
    )
    parser.add_argument(
        "--scaffold_fasta",
        type=Path,
        help="Scaffold  FASTA ",
    )
    parser.add_argument(
        "--min_coverage",
        type=float,
        default=0.95,
        help=" V-domain （: 0.95）",
    )
    parser.add_argument(
        "--out_dir",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="（: output/）",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("QA ： V-domain ")
    print("=" * 80)
    print()
    
    # 
    all_sequences = {}
    
    if args.germline_fasta:
        germline_path = Path(args.germline_fasta)
        if not germline_path.is_absolute():
            germline_path = PROJECT_ROOT / germline_path
        
        if not germline_path.exists():
            print(f"❌ Germline FASTA : {germline_path}")
            return
        
        print(f"[1/3]  Germline : {germline_path}")
        germline_seqs = load_fasta(germline_path)
        print(f"  ✅  {len(germline_seqs)} ")
        all_sequences.update(germline_seqs)
    
    if args.scaffold_fasta:
        scaffold_path = Path(args.scaffold_fasta)
        if not scaffold_path.is_absolute():
            scaffold_path = PROJECT_ROOT / scaffold_path
        
        if not scaffold_path.exists():
            print(f"❌ Scaffold FASTA : {scaffold_path}")
            return
        
        print(f"[2/3]  Scaffold : {scaffold_path}")
        scaffold_seqs = load_fasta(scaffold_path)
        print(f"  ✅  {len(scaffold_seqs)} ")
        all_sequences.update(scaffold_seqs)
    
    if not all_sequences:
        print("❌ ")
        return
    
    print()
    print(f"[3/3]  {len(all_sequences)} ...")
    print(f"  : {args.min_coverage:.1%}")
    print()
    
    # 
    pass_results = []
    fail_results = []
    
    for i, (seq_id, seq) in enumerate(all_sequences.items(), 1):
        if i % 10 == 0 or i == len(all_sequences):
            print(f"  : {i}/{len(all_sequences)} ({i/len(all_sequences)*100:.1f}%)")
        
        result = process_sequence(seq_id, seq, args.min_coverage)
        
        if result["status"] == "PASS":
            pass_results.append(result)
        else:
            fail_results.append(result)
    
    print()
    print("=" * 80)
    print("")
    print("=" * 80)
    print(f"✅ : {len(pass_results)} ")
    print(f"❌ : {len(fail_results)} ")
    print()
    
    #  CSV 
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    #  pass.csv
    pass_csv = args.out_dir / "qa_vdomain_pass.csv"
    with open(pass_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sequence_id", "length", "imgt_coverage", "status"])
        writer.writeheader()
        for result in pass_results:
            writer.writerow({
                "sequence_id": result["sequence_id"],
                "length": result["length"],
                "imgt_coverage": f"{result['imgt_coverage']:.6f}",
                "status": result["status"],
            })
    print(f"✅ : {pass_csv}")
    
    #  fail.csv
    fail_csv = args.out_dir / "qa_vdomain_fail.csv"
    with open(fail_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sequence_id", "length", "imgt_coverage", "fail_reason"])
        writer.writeheader()
        for result in fail_results:
            writer.writerow({
                "sequence_id": result["sequence_id"],
                "length": result["length"],
                "imgt_coverage": f"{result['imgt_coverage']:.6f}",
                "fail_reason": result["fail_reason"] or "",
            })
    print(f"✅ : {fail_csv}")
    
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()
