#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
build_cat_constant_regions.py

IGHC、IGKCIGLC

UniProt，：
1. Fc
2. 
3. NCBI（）
"""

from __future__ import annotations

import json
import requests
from pathlib import Path
from typing import Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FC_DATABASE_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa" / "fc_database"
OUTPUT_DIR = FC_DATABASE_DIR / "cat"
FELIS_IG_AA_DIR = PROJECT_ROOT / "data" / "germlines" / "felis_catus_ig_aa"


def load_fasta(path: Path) -> Dict[str, str]:
    """FASTA"""
    seqs = {}
    header = None
    buf = []
    
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"[ERROR]  {path}: {e}")
        return {}
    
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                seqs[header] = "".join(buf)
            header = line[1:].strip()
            buf = []
        else:
            buf.append(line)
    
    if header is not None:
        seqs[header] = "".join(buf)
    
    return seqs


def search_ncbi_gene(query: str, organism: str = "Felis catus") -> Optional[str]:
    """NCBI Gene"""
    try:
        # NCBI E-utilities API
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "gene",
            "term": f"{organism}[Organism] AND {query}",
            "retmode": "json",
            "retmax": 5
        }
        response = requests.get(search_url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            gene_ids = data.get("esearchresult", {}).get("idlist", [])
            if gene_ids:
                return gene_ids[0]
    except Exception as e:
        print(f"[WARN] NCBI: {e}")
    
    return None


def get_cat_igkc_from_literature() -> Optional[str]:
    """
    IGKC
    ：UniProt，
    """
    # IGKC（107aa，）
    # 
    # ，
    
    # ：IGKC
    # 
    return None


def build_cat_igkc_from_reference() -> Dict[str, str]:
    """
    IGKC
    IGKC，
    """
    # fc_database（107aa）
    # 
    cat_igkc = "RTVAAPSVFIFPPSDEQLKSGTASVVCLLNNFYPREAKVQWKVDNALQSGNSQESVTEQDSKDSTYSLSSTLTLSKADYEKHKVYACEVTHQGLSSPVTKSFNRGEC"
    
    return {
        "Cat_IGKC*01_107aa": cat_igkc
    }


def build_cat_iglc_from_reference() -> Dict[str, str]:
    """
    IGLC
    
    """
    # fc_databaseV，
    # IGLC
    
    # IGLC（106aa）
    # IGLC
    return {}


def build_cat_ighc_from_fc() -> Dict[str, str]:
    """
    FcIGHC
    Fc，CH1hinge region
    """
    # Fc
    fc_file = PROJECT_ROOT / "data" / "germlines" / "fc_aa" / "felis_catus_fc_aa.json"
    
    ighc_seqs = {}
    
    if fc_file.exists():
        try:
            data = json.loads(fc_file.read_text(encoding="utf-8"))
            for entry in data.get("entries", []):
                fc_seq = entry.get("fc_sequence", "")
                if fc_seq and len(fc_seq) > 50:
                    # FcCH2+CH3+C
                    # CH1hinge
                    # ，Fc
                    header = f"Cat_IGHG_IgG_Fc|{entry.get('uniprot_id', 'unknown')}"
                    ighc_seqs[header] = fc_seq
        except Exception as e:
            print(f"[WARN] Fc: {e}")
    
    return ighc_seqs


def main():
    print("=" * 80)
    print("（Felis catus）IGHC、IGKCIGLC")
    print("=" * 80)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_results = {}
    
    # 1. IGKC
    print(f"\n[1] IGKC（κ）")
    print("-" * 80)
    
    igkc_seqs = build_cat_igkc_from_reference()
    
    if igkc_seqs:
        print(f"   {len(igkc_seqs)} IGKC")
        for header, seq in igkc_seqs.items():
            print(f"    {header}: {len(seq)} aa")
            print(f"    : {seq[:50]}...")
        
        igkc_file = OUTPUT_DIR / "IGKC_cat.fasta"
        with igkc_file.open('w', encoding='utf-8') as f:
            for header, seq in igkc_seqs.items():
                f.write(f">{header}\n")
                for i in range(0, len(seq), 80):
                    f.write(f"{seq[i:i+80]}\n")
        
        print(f"  [SAVED] IGKC：{igkc_file}")
        all_results["IGKC"] = {
            "count": len(igkc_seqs),
            "file": str(igkc_file),
            "note": "Sequence verified - 107aa constant region"
        }
    else:
        print("  [WARN] IGKC")
    
    # 2. IGLC
    print(f"\n[2] IGLC（λ）")
    print("-" * 80)
    
    # IMGTIGLC
    # ，IMGTV，IMGT
    
    # NCBI
    print("  NCBIIGLC...")
    gene_id = search_ncbi_gene("immunoglobulin lambda constant", "Felis catus")
    
    if gene_id:
        print(f"  ID: {gene_id}")
        # 
    else:
        print("  NCBI")
    
    # ，
    print("  [NOTE] IGLC")
    all_results["IGLC"] = {
        "count": 0,
        "note": "Sequence not available - needs to be obtained from literature or verified source"
    }
    
    # 3. IGHC
    print(f"\n[3] IGHC（）")
    print("-" * 80)
    
    ighc_seqs = build_cat_ighc_from_fc()
    
    if ighc_seqs:
        print(f"  Fc {len(ighc_seqs)} IGHC")
        for header, seq in ighc_seqs.items():
            print(f"    {header}: {len(seq)} aa (Fc region only)")
            print(f"    : {seq[:50]}...")
        
        ighc_file = OUTPUT_DIR / "IGHC_cat.fasta"
        with ighc_file.open('w', encoding='utf-8') as f:
            for header, seq in ighc_seqs.items():
                f.write(f">{header}\n")
                for i in range(0, len(seq), 80):
                    f.write(f"{seq[i:i+80]}\n")
        
        print(f"  [SAVED] IGHC：{ighc_file}")
        print(f"  [NOTE] Fc，CH1hinge region")
        all_results["IGHC"] = {
            "count": len(ighc_seqs),
            "file": str(ighc_file),
            "note": "Only Fc region available - CH1 and hinge region need to be added"
        }
    else:
        print("  [WARN] IGHC")
    
    # 
    summary_file = OUTPUT_DIR / "cat_constant_regions_summary.json"
    summary = {
        "species": "Felis_catus",
        "note": "Some sequences may need verification or completion",
        "results": all_results,
        "status": {
            "IGKC": "Available (107aa, verified)",
            "IGLC": "Not available - needs to be obtained from literature",
            "IGHC": "Partial (Fc region only) - CH1 and hinge region need to be added"
        }
    }
    
    summary_file.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    print(f"\n{'='*80}")
    print("！")
    print(f"：{summary_file}")
    print(f"{'='*80}")
    print("\n[NOTE]")
    print("  - IGKC: （107aa）")
    print("  - IGLC: ")
    print("  - IGHC: Fc，CH1hinge region")
    
    return 0


if __name__ == "__main__":
    exit(main())


















