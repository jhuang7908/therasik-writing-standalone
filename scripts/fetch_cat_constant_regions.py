#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetch_cat_constant_regions.py

UniProt（Felis catus）IGHC、IGKCIGLC
"""

from __future__ import annotations

import json
import requests
import argparse
from pathlib import Path
from typing import Dict, Optional, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FC_DATABASE_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa" / "fc_database"
OUTPUT_DIR = FC_DATABASE_DIR / "cat"

# UniProtID
# ：ID，
CAT_UNIPROT_IDS = {
    "IGHC": {
        "IgG": "P01821",  # Cat IgG heavy chain constant region ()
    },
    "IGKC": {
        "IGKC": "P01834",  # Cat kappa light chain constant region ()
    },
    "IGLC": {
        "IGLC": "P01695",  # Cat lambda light chain constant region ()
    },
}


def get_uniprot_sequence(uniprot_id: str) -> Optional[Dict]:
    """UniProt"""
    try:
        # FASTA
        fasta_url = f"https://www.uniprot.org/uniprot/{uniprot_id}.fasta"
        response = requests.get(fasta_url, timeout=15)
        
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            header = lines[0]
            sequence = ''.join(lines[1:])
            
            # JSON
            json_url = f"https://www.uniprot.org/uniprot/{uniprot_id}.json"
            json_response = requests.get(json_url, timeout=15)
            metadata = {}
            if json_response.status_code == 200:
                metadata = json_response.json()
            
            return {
                "uniprot_id": uniprot_id,
                "header": header,
                "sequence": sequence,
                "metadata": metadata,
            }
        else:
            print(f"[WARN] UniProt {response.status_code} for {uniprot_id}")
    except Exception as e:
        print(f"[WARN] UniProt {uniprot_id}: {e}")
    
    return None


def search_uniprot(query: str, organism: str = "Felis catus") -> List[str]:
    """UniProt"""
    try:
        search_url = "https://www.uniprot.org/uniprot/"
        params = {
            "query": f"organism:{organism} AND {query}",
            "format": "list",
            "limit": 10
        }
        response = requests.get(search_url, params=params, timeout=15)
        
        if response.status_code == 200:
            uniprot_ids = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
            return uniprot_ids
    except Exception as e:
        print(f"[WARN] UniProt: {e}")
    
    return []


def extract_constant_region_from_full_chain(sequence: str, chain_type: str) -> str:
    """
    
    
    ：
    - CH1: 1，98aa
    - Hinge: CH1，12-19aa
    - CH2: hinge，110aa
    - CH3: CH2，107aa
    - C: CH3
    
    ：
    - CL: ，107aa（κ）106aa（λ）
    """
    # ，
    # ，
    
    # ，
    if len(sequence) < 150:
        return sequence
    
    # ，V（V120aa）
    # 
    return sequence


def save_fasta(output_path: Path, seqs: Dict[str, str]):
    """FASTA"""
    with output_path.open('w', encoding='utf-8') as f:
        for header, seq in seqs.items():
            f.write(f">{header}\n")
            for i in range(0, len(seq), 80):
                f.write(f"{seq[i:i+80]}\n")


def save_json(output_path: Path, data: dict):
    """JSON"""
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )


def main():
    parser = argparse.ArgumentParser(
        description="UniProtIGHC、IGKCIGLC"
    )
    parser.add_argument(
        "--search",
        action="store_true",
        help="UniProt（ID）",
    )
    
    args = parser.parse_args()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("（Felis catus）IGHC、IGKCIGLC")
    print("=" * 80)
    
    all_results = {}
    
    # 1. IGHC
    print(f"\n[1] IGHC（）")
    print("-" * 80)
    
    if args.search:
        print("  UniProtIGHC...")
        ighc_ids = search_uniprot("immunoglobulin heavy chain constant", "Felis catus")
        print(f"   {len(ighc_ids)} ID: {ighc_ids[:5]}")
        if ighc_ids:
            CAT_UNIPROT_IDS["IGHC"]["IgG"] = ighc_ids[0]
    
    ighc_seqs = {}
    for ig_type, uniprot_id in CAT_UNIPROT_IDS["IGHC"].items():
        print(f"   {ig_type} ({uniprot_id})...")
        data = get_uniprot_sequence(uniprot_id)
        
        if data:
            # 
            header_lower = data["header"].lower()
            if "felis" in header_lower or "cat" in header_lower or "catus" in header_lower:
                seq = data["sequence"]
                header = f"Cat_IGHG_{ig_type}|{uniprot_id}"
                ighc_seqs[header] = seq
                print(f"    [OK] ，：{len(seq)} aa")
                print(f"    30aa: {seq[:30]}...")
            else:
                print(f"    [WARN] （header: {data['header'][:80]}...）")
                # ，
                seq = data["sequence"]
                header = f"Cat_IGHG_{ig_type}|{uniprot_id}|VERIFY"
                ighc_seqs[header] = seq
        else:
            print(f"    [FAIL] ")
    
    if ighc_seqs:
        ighc_file = OUTPUT_DIR / "IGHC_cat.fasta"
        save_fasta(ighc_file, ighc_seqs)
        print(f"  [SAVED] IGHC：{ighc_file}")
        all_results["IGHC"] = {
            "count": len(ighc_seqs),
            "file": str(ighc_file)
        }
    
    # 2. IGKC
    print(f"\n[2] IGKC（κ）")
    print("-" * 80)
    
    if args.search:
        print("  UniProtIGKC...")
        igkc_ids = search_uniprot("immunoglobulin kappa chain constant", "Felis catus")
        print(f"   {len(igkc_ids)} ID: {igkc_ids[:5]}")
        if igkc_ids:
            CAT_UNIPROT_IDS["IGKC"]["IGKC"] = igkc_ids[0]
    
    igkc_seqs = {}
    for chain_type, uniprot_id in CAT_UNIPROT_IDS["IGKC"].items():
        print(f"   {chain_type} ({uniprot_id})...")
        data = get_uniprot_sequence(uniprot_id)
        
        if data:
            header_lower = data["header"].lower()
            if "felis" in header_lower or "cat" in header_lower or "catus" in header_lower:
                seq = data["sequence"]
                header = f"Cat_IGKC*01|{uniprot_id}"
                igkc_seqs[header] = seq
                print(f"    [OK] ，：{len(seq)} aa")
                print(f"    30aa: {seq[:30]}...")
            else:
                print(f"    [WARN] ")
                seq = data["sequence"]
                header = f"Cat_IGKC*01|{uniprot_id}|VERIFY"
                igkc_seqs[header] = seq
        else:
            print(f"    [FAIL] ")
    
    if igkc_seqs:
        igkc_file = OUTPUT_DIR / "IGKC_cat.fasta"
        save_fasta(igkc_file, igkc_seqs)
        print(f"  [SAVED] IGKC：{igkc_file}")
        all_results["IGKC"] = {
            "count": len(igkc_seqs),
            "file": str(igkc_file)
        }
    
    # 3. IGLC
    print(f"\n[3] IGLC（λ）")
    print("-" * 80)
    
    if args.search:
        print("  UniProtIGLC...")
        iglc_ids = search_uniprot("immunoglobulin lambda chain constant", "Felis catus")
        print(f"   {len(iglc_ids)} ID: {iglc_ids[:5]}")
        if iglc_ids:
            CAT_UNIPROT_IDS["IGLC"]["IGLC"] = iglc_ids[0]
    
    iglc_seqs = {}
    for chain_type, uniprot_id in CAT_UNIPROT_IDS["IGLC"].items():
        print(f"   {chain_type} ({uniprot_id})...")
        data = get_uniprot_sequence(uniprot_id)
        
        if data:
            header_lower = data["header"].lower()
            if "felis" in header_lower or "cat" in header_lower or "catus" in header_lower:
                seq = data["sequence"]
                header = f"Cat_IGLC*01|{uniprot_id}"
                iglc_seqs[header] = seq
                print(f"    [OK] ，：{len(seq)} aa")
                print(f"    30aa: {seq[:30]}...")
            else:
                print(f"    [WARN] ")
                seq = data["sequence"]
                header = f"Cat_IGLC*01|{uniprot_id}|VERIFY"
                iglc_seqs[header] = seq
        else:
            print(f"    [FAIL] ")
    
    if iglc_seqs:
        iglc_file = OUTPUT_DIR / "IGLC_cat.fasta"
        save_fasta(iglc_file, iglc_seqs)
        print(f"  [SAVED] IGLC：{iglc_file}")
        all_results["IGLC"] = {
            "count": len(iglc_seqs),
            "file": str(iglc_file)
        }
    
    # 
    if all_results:
        summary_file = OUTPUT_DIR / "cat_constant_regions_summary.json"
        summary = {
            "species": "Felis_catus",
            "source": "UniProt",
            "note": "Some sequences may need verification",
            "results": all_results
        }
        save_json(summary_file, summary)
        
        print(f"\n{'='*80}")
        print("！")
        print(f"：{summary_file}")
        print(f"{'='*80}")
        print("\n[NOTE] VERIFY，")
    else:
        print("\n[WARN] ，UniProt ID--search")
    
    return 0


if __name__ == "__main__":
    exit(main())


















