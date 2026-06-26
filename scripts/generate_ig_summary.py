#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
generate_ig_summary.py

Ig（IGHV, IGKV, IGLV, IGHC, IGKC, IGLC）
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GERMLINES_DIR = PROJECT_ROOT / "data" / "germlines"
FC_AA_DIR = GERMLINES_DIR / "fc_aa"

# 
SPECIES_MAP = {
    "human": {
        "dir_name": "human_ig_aa",
        "display_name": " (Homo sapiens)",
        "fc_dir": "human"
    },
    "mouse": {
        "dir_name": "mus_musculus_ig_aa",
        "display_name": " (Mus musculus)",
        "fc_dir": "mouse"
    },
    "dog": {
        "dir_name": "canis_lupus_familiaris_ig_aa",
        "display_name": " (Canis lupus familiaris)",
        "fc_dir": "dog"
    },
    "cat": {
        "dir_name": "felis_catus_ig_aa",
        "display_name": " (Felis catus)",
        "fc_dir": "cat"
    },
    "rat": {
        "dir_name": "rattus_norvegicus_ig_aa",
        "display_name": " (Rattus norvegicus)",
        "fc_dir": None  # 
    },
    "rabbit": {
        "dir_name": "oryctolagus_cuniculus_ig_aa",
        "display_name": " (Oryctolagus cuniculus)",
        "fc_dir": None
    },
    "cow": {
        "dir_name": "bos_taurus_ig_aa",
        "display_name": " (Bos taurus)",
        "fc_dir": None
    },
    "alpaca": {
        "dir_name": "vicugna_pacos_ig_aa",
        "display_name": " (Vicugna pacos)",
        "fc_dir": None
    },
    "shark": {
        "dir_name": "chondrichthyes_ig_aa",
        "display_name": " (Chondrichthyes)",
        "fc_dir": None
    }
}


def load_fasta_count(path: Path) -> int:
    """FASTA"""
    if not path.exists():
        return 0
    
    count = 0
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        count = content.count(">")
    except Exception:
        pass
    
    return count


def load_json_summary(path: Path) -> Optional[Dict]:
    """JSON"""
    if not path.exists():
        return None
    
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None


def get_variable_region_info(species_key: str, species_info: Dict) -> Dict:
    """"""
    dir_name = species_info["dir_name"]
    species_dir = GERMLINES_DIR / dir_name
    
    info = {
        "IGHV": {"count": 0, "file": None},
        "IGKV": {"count": 0, "file": None},
        "IGLV": {"count": 0, "file": None}
    }
    
    if not species_dir.exists():
        return info
    
    # summary
    summary_file = species_dir / f"{dir_name}_summary.json"
    summary = load_json_summary(summary_file)
    
    if summary and "files" in summary:
        for chain_type in ["IGHV", "IGKV", "IGLV"]:
            if chain_type in summary["files"]:
                file_info = summary["files"][chain_type]
                info[chain_type]["count"] = file_info.get("translated_count", file_info.get("count", 0))
                file_path = file_info.get("fasta_file", "")
                if file_path:
                    info[chain_type]["file"] = Path(file_path).name
    
    # summary，FASTA
    for chain_type in ["IGHV", "IGKV", "IGLV"]:
        if info[chain_type]["count"] == 0:
            fasta_file = species_dir / f"{chain_type}_aa.fasta"
            if fasta_file.exists():
                count = load_fasta_count(fasta_file)
                info[chain_type]["count"] = count
                info[chain_type]["file"] = fasta_file.name
    
    return info


def get_constant_region_info(species_key: str, species_info: Dict) -> Dict:
    """"""
    fc_dir_name = species_info.get("fc_dir")
    
    info = {
        "IGHC": {"count": 0, "file": None, "status": "N/A"},
        "IGKC": {"count": 0, "file": None, "status": "N/A"},
        "IGLC": {"count": 0, "file": None, "status": "N/A"}
    }
    
    if not fc_dir_name:
        return info
    
    fc_species_dir = FC_AA_DIR / fc_dir_name
    if not fc_species_dir.exists():
        return info
    
    for chain_type in ["IGHC", "IGKC", "IGLC"]:
        fasta_file = fc_species_dir / f"{chain_type}_{fc_dir_name}.fasta"
        if fasta_file.exists():
            count = load_fasta_count(fasta_file)
            info[chain_type]["count"] = count
            info[chain_type]["file"] = fasta_file.name
            info[chain_type]["status"] = "Available"
        else:
            info[chain_type]["status"] = "Missing"
    
    return info


def main():
    print("=" * 80)
    print("Ig")
    print("=" * 80)
    
    all_summary = {}
    
    for species_key, species_info in SPECIES_MAP.items():
        print(f"\n: {species_info['display_name']}")
        print("-" * 80)
        
        # 
        var_info = get_variable_region_info(species_key, species_info)
        print(f"  :")
        print(f"    IGHV: {var_info['IGHV']['count']}")
        print(f"    IGKV: {var_info['IGKV']['count']}")
        print(f"    IGLV: {var_info['IGLV']['count']}")
        
        # 
        const_info = get_constant_region_info(species_key, species_info)
        print(f"  :")
        print(f"    IGHC: {const_info['IGHC']['count']} ({const_info['IGHC']['status']})")
        print(f"    IGKC: {const_info['IGKC']['count']} ({const_info['IGKC']['status']})")
        print(f"    IGLC: {const_info['IGLC']['count']} ({const_info['IGLC']['status']})")
        
        all_summary[species_key] = {
            "display_name": species_info["display_name"],
            "variable_regions": var_info,
            "constant_regions": const_info,
            "total_variable": sum(v["count"] for v in var_info.values()),
            "total_constant": sum(c["count"] for c in const_info.values()),
            "total": sum(v["count"] for v in var_info.values()) + sum(c["count"] for c in const_info.values())
        }
    
    # JSON
    summary_file = GERMLINES_DIR / "ig_sequences_summary.json"
    summary_file.write_text(
        json.dumps(all_summary, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    # Markdown
    md_file = GERMLINES_DIR / "IG_SEQUENCES_SUMMARY.md"
    with md_file.open('w', encoding='utf-8') as f:
        f.write("# Ig\n\n")
        f.write("（Ig）。\n\n")
        f.write("## \n\n")
        f.write("- **IGHV**: （Variable region of heavy chain）\n")
        f.write("- **IGKV**: κ（Variable region of kappa light chain）\n")
        f.write("- **IGLV**: λ（Variable region of lambda light chain）\n")
        f.write("- **IGHC**: （Constant region of heavy chain）\n")
        f.write("- **IGKC**: κ（Constant region of kappa light chain）\n")
        f.write("- **IGLC**: λ（Constant region of lambda light chain）\n\n")
        
        f.write("## \n\n")
        f.write("|  | IGHV | IGKV | IGLV | IGHC | IGKC | IGLC |  |\n")
        f.write("|------|------|------|------|------|------|------|------|\n")
        
        for species_key, data in sorted(all_summary.items()):
            vr = data["variable_regions"]
            cr = data["constant_regions"]
            total = data["total"]
            
            f.write(f"| {data['display_name']} | "
                   f"{vr['IGHV']['count']} | "
                   f"{vr['IGKV']['count']} | "
                   f"{vr['IGLV']['count']} | "
                   f"{cr['IGHC']['count']} ({cr['IGHC']['status'][:1]}) | "
                   f"{cr['IGKC']['count']} ({cr['IGKC']['status'][:1]}) | "
                   f"{cr['IGLC']['count']} ({cr['IGLC']['status'][:1]}) | "
                   f"**{total}** |\n")
        
        f.write("\n****:  - A=Available（）, M=Missing（）, N=N/A（）\n\n")
        
        f.write("## \n\n")
        
        for species_key, data in sorted(all_summary.items()):
            f.write(f"### {data['display_name']}\n\n")
            
            f.write("#### \n\n")
            vr = data["variable_regions"]
            f.write(f"- **IGHV**: {vr['IGHV']['count']}")
            if vr['IGHV']['file']:
                f.write(f" (`{vr['IGHV']['file']}`)")
            f.write("\n")
            
            f.write(f"- **IGKV**: {vr['IGKV']['count']}")
            if vr['IGKV']['file']:
                f.write(f" (`{vr['IGKV']['file']}`)")
            f.write("\n")
            
            f.write(f"- **IGLV**: {vr['IGLV']['count']}")
            if vr['IGLV']['file']:
                f.write(f" (`{vr['IGLV']['file']}`)")
            f.write("\n")
            
            f.write(f"- ****: {data['total_variable']}\n\n")
            
            f.write("#### \n\n")
            cr = data["constant_regions"]
            f.write(f"- **IGHC**: {cr['IGHC']['count']} ({cr['IGHC']['status']})")
            if cr['IGHC']['file']:
                f.write(f" (`{cr['IGHC']['file']}`)")
            f.write("\n")
            
            f.write(f"- **IGKC**: {cr['IGKC']['count']} ({cr['IGKC']['status']})")
            if cr['IGKC']['file']:
                f.write(f" (`{cr['IGKC']['file']}`)")
            f.write("\n")
            
            f.write(f"- **IGLC**: {cr['IGLC']['count']} ({cr['IGLC']['status']})")
            if cr['IGLC']['file']:
                f.write(f" (`{cr['IGLC']['file']}`)")
            f.write("\n")
            
            f.write(f"- ****: {data['total_constant']}\n\n")
            
            f.write(f"****: {data['total']}\n\n")
            f.write("---\n\n")
        
        f.write("## \n\n")
        f.write("- ****: IMGT（DNA → AA）\n")
        f.write("- ****: IMGTUniProt\n\n")
        f.write("## \n\n")
        f.write("- ****: `data/germlines/{species}_ig_aa/`\n")
        f.write("- ****: `data/germlines/fc_aa/{species}/`\n")
        f.write("- **JSON**: `ig_sequences_summary.json`\n")
    
    print(f"\n{'='*80}")
    print("！")
    print(f"{'='*80}")
    print(f"\nJSON: {summary_file}")
    print(f"Markdown: {md_file}")
    
    # 
    print(f"\n:")
    print(f"{'':<20} {'IGHV':<8} {'IGKV':<8} {'IGLV':<8} {'IGHC':<10} {'IGKC':<10} {'IGLC':<10} {'':<8}")
    print("-" * 100)
    for species_key, data in sorted(all_summary.items()):
        vr = data["variable_regions"]
        cr = data["constant_regions"]
        print(f"{data['display_name']:<20} "
              f"{vr['IGHV']['count']:<8} "
              f"{vr['IGKV']['count']:<8} "
              f"{vr['IGLV']['count']:<8} "
              f"{cr['IGHC']['count']}({cr['IGHC']['status'][:1]}){'':<6} "
              f"{cr['IGKC']['count']}({cr['IGKC']['status'][:1]}){'':<6} "
              f"{cr['IGLC']['count']}({cr['IGLC']['status'][:1]}){'':<6} "
              f"{data['total']:<8}")
    
    return 0


if __name__ == "__main__":
    exit(main())


















