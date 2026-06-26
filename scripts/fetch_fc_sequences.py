#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetch_fc_sequences.py

UniProtIgG Fc

：IMGTFc，Fc（UniProt）
"""

from __future__ import annotations

import json
import requests
import argparse
from pathlib import Path
from typing import Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "germlines" / "fc_aa"

# UniProtIgG FcUniProt ID
# UniProt ID
UNIPROT_FC_IDS = {
    "Mus_musculus": {
        "IgG1": "P01868",  # Mouse IgG1 heavy chain constant region
        "IgG2a": "P01863",  # Mouse IgG2a heavy chain constant region
        "IgG2b": "P01867",  # Mouse IgG2b heavy chain constant region
        "IgG3": "P03987",   # Mouse IgG3 heavy chain constant region
    },
    "Rattus_norvegicus": {
        "IgG1": "P20760",   # Rat IgG1 heavy chain constant region
        "IgG2a": "P20761",  # Rat IgG2a heavy chain constant region
        "IgG2b": "P20762",  # Rat IgG2b heavy chain constant region
        "IgG2c": "P20763",  # Rat IgG2c heavy chain constant region
    },
    "Oryctolagus_cuniculus": {
        "IgG": "P01870",    # Rabbit IgG heavy chain constant region
    },
    "Bos_taurus": {
        "IgG1": "P01811",   # Bovine IgG1 heavy chain constant region
        "IgG2": "P01812",   # Bovine IgG2 heavy chain constant region
    },
    "Canis_lupus_familiaris": {
        "IgG": "P01820",    # Dog IgG heavy chain constant region
    },
    "Felis_catus": {
        "IgG": "P01821",    # Cat IgG heavy chain constant region
    },
    "Homo_sapiens": {
        "IgG1": "P01857",   # Human IgG1 heavy chain constant region
        "IgG2": "P01859",   # Human IgG2 heavy chain constant region
        "IgG3": "P01860",   # Human IgG3 heavy chain constant region
        "IgG4": "P01861",   # Human IgG4 heavy chain constant region
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


def extract_fc_region(sequence: str, species: str, ig_type: str) -> str:
    """
    Fc
    
    Fc（hinge region）
    IgG，Fc200-250
    """
    # ，
    fc_start_positions = {
        "Mus_musculus": {"IgG1": 220, "IgG2a": 220, "IgG2b": 220, "IgG3": 220},
        "Rattus_norvegicus": {"IgG1": 220, "IgG2a": 220, "IgG2b": 220, "IgG2c": 220},
        "Oryctolagus_cuniculus": {"IgG": 220},
        "Bos_taurus": {"IgG1": 220, "IgG2": 220},
        "Canis_lupus_familiaris": {"IgG": 220},
        "Felis_catus": {"IgG": 220},
        "Homo_sapiens": {"IgG1": 220, "IgG2": 220, "IgG3": 220, "IgG4": 220},
    }
    
    # Fc
    # Fc
    # ：CPPCP, CPAP, EPKSC
    
    # 1：
    if species in fc_start_positions and ig_type in fc_start_positions[species]:
        start_pos = fc_start_positions[species][ig_type]
        if start_pos < len(sequence):
            return sequence[start_pos:]
    
    # 2：
    hinge_patterns = ["CPPCP", "CPAP", "EPKSC", "DKTHT"]
    for pattern in hinge_patterns:
        pos = sequence.find(pattern)
        if pos > 100 and pos < 300:  # 
            # Fc
            fc_start = pos + len(pattern)
            return sequence[fc_start:]
    
    # 3：，（Fc）
    if len(sequence) > 200:
        return sequence[200:]
    
    # ，
    return sequence


def save_fc_sequences(output_dir: Path, species: str, fc_data: Dict):
    """Fc"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # FASTA
    fasta_file = output_dir / f"{species.lower()}_fc_aa.fasta"
    with fasta_file.open('w', encoding='utf-8') as f:
        for ig_type, data in fc_data.items():
            if data and 'fc_sequence' in data:
                header = f"{species}_{ig_type}_Fc|{data.get('uniprot_id', 'unknown')}"
                f.write(f">{header}\n")
                seq = data['fc_sequence']
                for i in range(0, len(seq), 80):
                    f.write(f"{seq[i:i+80]}\n")
    
    # JSON
    json_file = output_dir / f"{species.lower()}_fc_aa.json"
    json_data = {
        "species": species,
        "entries": [
            {
                "ig_type": ig_type,
                "uniprot_id": data.get("uniprot_id", ""),
                "full_sequence_length": len(data.get("sequence", "")),
                "fc_sequence": data.get("fc_sequence", ""),
                "fc_sequence_length": len(data.get("fc_sequence", "")),
                "header": data.get("header", ""),
            }
            for ig_type, data in fc_data.items()
            if data and 'fc_sequence' in data
        ],
    }
    
    json_file.write_text(
        json.dumps(json_data, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    return fasta_file, json_file


def main():
    parser = argparse.ArgumentParser(
        description="UniProtIgG Fc"
    )
    parser.add_argument(
        "--species",
        nargs="+",
        choices=list(UNIPROT_FC_IDS.keys()) + ["all"],
        default=["all"],
        help="（：all）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help=f"（：{OUTPUT_DIR}）",
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 
    if "all" in args.species:
        species_to_process = list(UNIPROT_FC_IDS.keys())
    else:
        species_to_process = [s for s in args.species if s in UNIPROT_FC_IDS]
    
    print(f"[INFO] UniProtFc")
    print(f"[INFO] ：{output_dir}")
    print(f"[INFO] ：{', '.join(species_to_process)}")
    print(f"[NOTE] IMGTFc，Fc\n")
    
    all_results = {}
    
    for species in species_to_process:
        print(f"\n[INFO] ：{species}")
        
        if species not in UNIPROT_FC_IDS:
            print(f"[WARN]  {species} UniProt ID")
            continue
        
        fc_data = {}
        for ig_type, uniprot_id in UNIPROT_FC_IDS[species].items():
            print(f"  [FETCH] {ig_type} ({uniprot_id})...")
            data = get_uniprot_sequence(uniprot_id)
            
            if data:
                # Fc
                fc_sequence = extract_fc_region(data["sequence"], species, ig_type)
                data["fc_sequence"] = fc_sequence
                fc_data[ig_type] = data
                print(f"    [OK] ，Fc：{len(fc_sequence)}")
            else:
                print(f"    [FAIL] ")
                fc_data[ig_type] = None
        
        # 
        if any(fc_data.values()):
            fasta_file, json_file = save_fc_sequences(output_dir, species, fc_data)
            all_results[species] = {
                "fasta_file": str(fasta_file),
                "json_file": str(json_file),
                "count": sum(1 for v in fc_data.values() if v),
            }
            print(f"  [SAVED] {species} Fc")
    
    # 
    if all_results:
        summary_file = output_dir / "fc_aa_summary.json"
        summary = {
            "note": "Fc sequences fetched from UniProt (amino acid sequences, not DNA)",
            "total_species": len(all_results),
            "species": all_results,
        }
        summary_file.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        print(f"\n[SUCCESS] ！")
        print(f"[INFO]  {len(all_results)} ")
        print(f"[INFO] ：{summary_file}")
        print(f"\n[NOTE] （DNA），UniProt")
    
    return 0


if __name__ == "__main__":
    exit(main())


















