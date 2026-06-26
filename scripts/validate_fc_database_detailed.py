#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
validate_fc_database_detailed.py

fc_database，
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FC_DATABASE_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa" / "fc_database"
UNIPROT_FC_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa"


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


def load_uniprot_fc(species: str) -> Dict[str, str]:
    """UniProtFc"""
    json_file = UNIPROT_FC_DIR / f"{species.lower()}_fc_aa.json"
    
    if not json_file.exists():
        return {}
    
    try:
        data = json.loads(json_file.read_text(encoding="utf-8"))
        fc_seqs = {}
        for entry in data.get("entries", []):
            ig_type = entry.get("ig_type", "")
            fc_seq = entry.get("fc_sequence", "")
            if fc_seq:
                fc_seqs[ig_type] = fc_seq
        return fc_seqs
    except Exception as e:
        print(f"[WARN] UniProt Fc {json_file}: {e}")
        return {}


def extract_fc_components(seqs: Dict[str, str], species: str, igg_type: str) -> Dict:
    """IgGFc"""
    components = {
        "CH2": [],
        "CH3": [],
        "Unknown_short": [],  # 
        "Unknown_long": []    # C
    }
    
    pattern = f"{species.capitalize()}_IGHG{igg_type.replace('IgG', '')}_"
    
    for header, seq in seqs.items():
        if pattern in header:
            if "_CH2_" in header:
                components["CH2"].append((header, seq))
            elif "_CH3_" in header:
                components["CH3"].append((header, seq))
            elif "_Unknown_" in header:
                if len(seq) < 20:
                    components["Unknown_short"].append((header, seq))
                else:
                    components["Unknown_long"].append((header, seq))
    
    return components


def main():
    print("=" * 80)
    print("fc_databaseIGHG、IGKCIGLC")
    print("=" * 80)
    
    species_list = ["human", "mouse", "dog"]
    species_map = {
        "human": "Homo_sapiens",
        "mouse": "Mus_musculus",
        "dog": "Canis_lupus_familiaris"
    }
    
    all_results = {}
    
    for species in species_list:
        print(f"\n{'='*80}")
        print(f": {species.upper()}")
        print(f"{'='*80}")
        
        species_dir = FC_DATABASE_DIR / species
        if not species_dir.exists():
            print(f"[WARN] : {species_dir}")
            continue
        
        results = {
            "species": species,
            "ighg": {},
            "igkc": {},
            "iglc": {}
        }
        
        # 1. IGHG
        print(f"\n[1] IGHG（）")
        print("-" * 80)
        
        ighg_file = species_dir / f"IGHC_{species}.fasta"
        if ighg_file.exists():
            ighg_seqs = load_fasta(ighg_file)
            print(f"   {len(ighg_seqs)} IGHG")
            
            # UniProt
            uniprot_fc = load_uniprot_fc(species_map[species])
            print(f"  UniProt {len(uniprot_fc)} IgGFc")
            
            # IgG
            for igg_type in ["IgG1", "IgG2", "IgG3", "IgG4"]:
                components = extract_fc_components(ighg_seqs, species, igg_type)
                
                if not any(components.values()):
                    continue
                
                print(f"\n  {igg_type}:")
                print(f"    CH2: {len(components['CH2'])}")
                print(f"    CH3: {len(components['CH3'])}")
                print(f"    : {len(components['Unknown_short'])}")
                print(f"    C: {len(components['Unknown_long'])}")
                
                # 
                if components["CH2"] and components["CH3"]:
                    ch2_header, ch2_seq = components["CH2"][0]
                    ch3_header, ch3_seq = components["CH3"][0]
                    
                    # Fc
                    c_terminal = ""
                    if components["Unknown_long"]:
                        c_terminal = components["Unknown_long"][0][1]
                    
                    fc_assembled = ch2_seq + ch3_seq + c_terminal
                    
                    print(f"    CH2: {len(ch2_seq)} aa")
                    print(f"    CH3: {len(ch3_seq)} aa")
                    print(f"    C: {len(c_terminal)} aa")
                    print(f"    Fc: {len(fc_assembled)} aa")
                    
                    # UniProt
                    uniprot_key = igg_type
                    if uniprot_key in uniprot_fc:
                        uniprot_seq = uniprot_fc[uniprot_key]
                        print(f"    UniProt Fc: {len(uniprot_seq)} aa")
                        
                        # CH3UniProt
                        ch3_in_uniprot = uniprot_seq.find(ch3_seq)
                        if ch3_in_uniprot >= 0:
                            print(f"    CH3UniProt: {ch3_in_uniprot}")
                            print(f"    UniProt Fc: {uniprot_seq[:20]}...")
                            print(f"    CH3: {ch3_seq[:20]}...")
                        else:
                            # CH3UniProt
                            ch3_start = ch3_seq[1:]  # 
                            ch3_in_uniprot = uniprot_seq.find(ch3_start)
                            if ch3_in_uniprot >= 0:
                                print(f"    CH3()UniProt: {ch3_in_uniprot}")
                                print(f"    UniProt Fc: {uniprot_seq[:ch3_in_uniprot]}...")
                                print(f"    : {ch3_in_uniprot} aa")
                        
                        # CUniProt
                        if c_terminal:
                            c_in_uniprot = uniprot_seq.find(c_terminal)
                            if c_in_uniprot >= 0:
                                print(f"    CUniProt: {c_in_uniprot}")
                        
                        results["ighg"][igg_type] = {
                            "ch2_length": len(ch2_seq),
                            "ch3_length": len(ch3_seq),
                            "c_terminal_length": len(c_terminal),
                            "assembled_fc_length": len(fc_assembled),
                            "uniprot_fc_length": len(uniprot_seq),
                            "ch3_position_in_uniprot": ch3_in_uniprot if ch3_in_uniprot >= 0 else None
                        }
                    else:
                        print(f"    : UniProt {uniprot_key} ")
        
        # 2. IGKCIGLC
        for chain_type in ["IGKC", "IGLC"]:
            print(f"\n[{2 if chain_type == 'IGKC' else 3}] {chain_type}（{'κ' if chain_type == 'IGKC' else 'λ'}）")
            print("-" * 80)
            
            chain_file = species_dir / f"{chain_type}_{species}.fasta"
            if chain_file.exists():
                chain_seqs = load_fasta(chain_file)
                print(f"   {len(chain_seqs)} {chain_type}")
                
                for header, seq in list(chain_seqs.items())[:3]:
                    print(f"    {header[:60]}...")
                    print(f"      : {len(seq)} aa")
                    print(f"      20aa: {seq[:20]}...")
                
                results[chain_type.lower()] = {
                    "count": len(chain_seqs),
                    "lengths": [len(seq) for seq in chain_seqs.values()]
                }
            else:
                print(f"  [WARN] : {chain_file}")
        
        all_results[species] = results
    
    # 
    report_file = FC_DATABASE_DIR / "validation_report_detailed.json"
    report_file.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    print(f"\n{'='*80}")
    print("！")
    print(f": {report_file}")
    print(f"{'='*80}")
    
    return 0


if __name__ == "__main__":
    exit(main())


















