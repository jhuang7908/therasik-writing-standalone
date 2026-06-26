#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
annotate_constant_regions.py

（CH1、Hinge、CH2、CH3、C）
CH4
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FC_AA_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa"
OUTPUT_DIR = FC_AA_DIR / "annotated"


def load_fasta(path: Path) -> Dict[str, str]:
    """FASTA"""
    seqs = {}
    header = None
    buf = []
    
    if not path.exists():
        return {}
    
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
        elif not line.startswith("#"):
            buf.append(line)
    
    if header is not None:
        seqs[header] = "".join(buf)
    
    return seqs


def parse_header(header: str) -> Dict:
    """header，"""
    info = {
        "species": None,
        "igg_type": None,
        "domain": None,
        "allele": None,
        "length": None,
        "original_header": header
    }
    
    # 
    if header.startswith("Human_"):
        info["species"] = "human"
    elif header.startswith("Mouse_"):
        info["species"] = "mouse"
    elif header.startswith("Dog_"):
        info["species"] = "dog"
    elif header.startswith("Cat_"):
        info["species"] = "cat"
    
    # IgG
    ighg_match = re.search(r'IGHG(\d+[A-Z]?)', header)
    if ighg_match:
        info["igg_type"] = f"IgG{ighg_match.group(1)}"
    
    # （）
    # ：，group_sequences_by_igg
    
    if "_CH1_" in header or ("CH1" in header and "CH2" not in header and "CH3" not in header and "CH4" not in header):
        info["domain"] = "CH1"
    elif "_CH2_" in header or ("CH2" in header and "CH3" not in header and "CH4" not in header):
        info["domain"] = "CH2"
    elif "_CH3_" in header or ("CH3" in header and "CH4" not in header):
        info["domain"] = "CH3"
    elif "_CH4_" in header or "CH4" in header:
        info["domain"] = "CH4"
    elif "_Hinge_" in header or ("Hinge" in header):
        info["domain"] = "Hinge"
    elif "_Unknown_" in header:
        # header
        length_match = re.search(r'(\d+)aa', header)
        if length_match:
            seq_len = int(length_match.group(1))
            if seq_len < 20:
                info["domain"] = "Hinge"
            else:
                info["domain"] = "C_terminal"
        else:
            # ，Unknown，
            info["domain"] = "Unknown"
    else:
        info["domain"] = "Unknown"
    
    # 
    allele_match = re.search(r'\*(\d+)', header)
    if allele_match:
        info["allele"] = allele_match.group(1)
    
    # 
    length_match = re.search(r'(\d+)aa', header)
    if length_match:
        info["length"] = int(length_match.group(1))
    
    return info


def group_sequences_by_igg(seqs: Dict[str, str], species: str) -> Dict:
    """IgG"""
    groups = defaultdict(lambda: {
        "CH1": [],
        "Hinge": [],
        "CH2": [],
        "CH3": [],
        "CH4": [],
        "C_terminal": []
    })
    
    for header, seq in seqs.items():
        info = parse_header(header)
        
        if info["species"] != species:
            continue
        
        key = f"{info['igg_type']}*{info['allele']}" if info['allele'] else info['igg_type']
        
        domain = info["domain"]
        
        # domainUnknown，
        if domain == "Unknown":
            seq_len = len(seq)
            if seq_len < 20:
                domain = "Hinge"
            else:
                # C（CH3）
                domain = "C_terminal"
        
        if domain in groups[key]:
            groups[key][domain].append({
                "header": header,
                "sequence": seq,
                "length": len(seq),
                "info": info
            })
    
    return groups


def create_annotated_sequence(group_key: str, domains: Dict, species: str) -> Optional[Dict]:
    """"""
    # CH4
    has_ch4 = len(domains["CH4"]) > 0
    
    # 
    full_sequence = ""
    annotations = []
    current_pos = 1
    
    # CH1
    if domains["CH1"]:
        ch1 = domains["CH1"][0]  # 
        full_sequence += ch1["sequence"]
        annotations.append({
            "region": "CH1",
            "start": current_pos,
            "end": current_pos + len(ch1["sequence"]) - 1,
            "length": len(ch1["sequence"]),
            "header": ch1["header"]
        })
        current_pos += len(ch1["sequence"])
    
    # Hinge
    if domains["Hinge"]:
        hinge = domains["Hinge"][0]
        full_sequence += hinge["sequence"]
        annotations.append({
            "region": "Hinge",
            "start": current_pos,
            "end": current_pos + len(hinge["sequence"]) - 1,
            "length": len(hinge["sequence"]),
            "header": hinge["header"]
        })
        current_pos += len(hinge["sequence"])
    
    # CH2
    if domains["CH2"]:
        ch2 = domains["CH2"][0]
        full_sequence += ch2["sequence"]
        annotations.append({
            "region": "CH2",
            "start": current_pos,
            "end": current_pos + len(ch2["sequence"]) - 1,
            "length": len(ch2["sequence"]),
            "header": ch2["header"]
        })
        current_pos += len(ch2["sequence"])
    
    # CH3
    if domains["CH3"]:
        ch3 = domains["CH3"][0]
        full_sequence += ch3["sequence"]
        annotations.append({
            "region": "CH3",
            "start": current_pos,
            "end": current_pos + len(ch3["sequence"]) - 1,
            "length": len(ch3["sequence"]),
            "header": ch3["header"]
        })
        current_pos += len(ch3["sequence"])
    
    # CH4 ()
    if domains["CH4"]:
        ch4 = domains["CH4"][0]
        full_sequence += ch4["sequence"]
        annotations.append({
            "region": "CH4",
            "start": current_pos,
            "end": current_pos + len(ch4["sequence"]) - 1,
            "length": len(ch4["sequence"]),
            "header": ch4["header"]
        })
        current_pos += len(ch4["sequence"])
    
    # C_terminal
    if domains["C_terminal"]:
        for c_term in domains["C_terminal"]:
            full_sequence += c_term["sequence"]
            annotations.append({
                "region": "C_terminal",
                "start": current_pos,
                "end": current_pos + len(c_term["sequence"]) - 1,
                "length": len(c_term["sequence"]),
                "header": c_term["header"]
            })
            current_pos += len(c_term["sequence"])
    
    if not full_sequence:
        return None
    
    return {
        "species": species,
        "igg_type": group_key,
        "full_sequence": full_sequence,
        "total_length": len(full_sequence),
        "has_ch4": has_ch4,
        "regions": annotations,
        "structure": {
            "has_ch1": len(domains["CH1"]) > 0,
            "has_hinge": len(domains["Hinge"]) > 0,
            "has_ch2": len(domains["CH2"]) > 0,
            "has_ch3": len(domains["CH3"]) > 0,
            "has_ch4": has_ch4,
            "has_c_terminal": len(domains["C_terminal"]) > 0
        }
    }


def main():
    print("=" * 80)
    print("")
    print("=" * 80)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_annotated = {}
    ch4_found = []
    
    species_list = ["human", "mouse", "dog"]
    
    for species in species_list:
        print(f"\n{'='*80}")
        print(f": {species.upper()}")
        print(f"{'='*80}")
        
        species_path = FC_AA_DIR / species
        if not species_path.exists():
            continue
        
        ighc_file = species_path / f"IGHC_{species}.fasta"
        if not ighc_file.exists():
            continue
        
        print(f"\n[1] ")
        print("-" * 80)
        seqs = load_fasta(ighc_file)
        print(f"   {len(seqs)} ")
        
        print(f"\n[2] ")
        print("-" * 80)
        groups = group_sequences_by_igg(seqs, species)
        print(f"   {len(groups)} IgG/")
        
        species_annotated = {}
        
        for group_key, domains in sorted(groups.items()):
            # CH4
            if len(domains["CH4"]) > 0:
                ch4_found.append({
                    "species": species,
                    "igg_type": group_key,
                    "ch4_headers": [d["header"] for d in domains["CH4"]]
                })
                print(f"  ⚠️ {group_key}: CH4！")
            
            annotated = create_annotated_sequence(group_key, domains, species)
            if annotated:
                species_annotated[group_key] = annotated
                structure = annotated["structure"]
                regions = [r["region"] for r in annotated["regions"]]
                print(f"  {group_key}: {annotated['total_length']}aa - {', '.join(regions)}")
        
        all_annotated[species] = species_annotated
        
        # JSON
        json_file = OUTPUT_DIR / f"{species}_IGHC_annotated.json"
        json_file.write_text(
            json.dumps(species_annotated, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        print(f"\n  [] JSON: {json_file}")
        
        # FASTA
        fasta_file = OUTPUT_DIR / f"{species}_IGHC_annotated.fasta"
        with fasta_file.open('w', encoding='utf-8') as f:
            for group_key, annotated in sorted(species_annotated.items()):
                # 
                f.write(f">{group_key}|{species}|Full|{annotated['total_length']}aa\n")
                for i in range(0, len(annotated['full_sequence']), 80):
                    f.write(f"{annotated['full_sequence'][i:i+80]}\n")
                
                # 
                for region in annotated['regions']:
                    seq = annotated['full_sequence'][region['start']-1:region['end']]
                    f.write(f">{group_key}|{species}|{region['region']}|{region['start']}-{region['end']}|{region['length']}aa\n")
                    for i in range(0, len(seq), 80):
                        f.write(f"{seq[i:i+80]}\n")
        
        print(f"  [] FASTA: {fasta_file}")
    
    # 
    summary = {
        "total_species": len(all_annotated),
        "ch4_found": ch4_found,
        "summary": {
            species: {
                "igg_types": len(annotated),
                "total_sequences": sum(len(a["regions"]) for a in annotated.values())
            }
            for species, annotated in all_annotated.items()
        }
    }
    
    summary_file = OUTPUT_DIR / "annotation_summary.json"
    summary_file.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    print(f"\n{'='*80}")
    print("！")
    print(f"{'='*80}")
    
    if ch4_found:
        print(f"\n⚠️  {len(ch4_found)} CH4:")
        for item in ch4_found:
            print(f"  - {item['species']} {item['igg_type']}")
    else:
        print(f"\n✅ CH4（，IgGCH1-CH3）")
    
    print(f"\n: {OUTPUT_DIR}")
    print(f": {summary_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())

