#!/usr/bin/env python3
"""
Germline Template Libraries Inventory Tool
：germline
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime

# 
PROJECT_ROOT = Path(__file__).resolve.parents[1]
GERMLINES_DIR = PROJECT_ROOT / "data" / "germlines"


def count_fasta_sequences(fasta_path: Path) -> int:
    """FASTA"""
    if not fasta_path.exists:
        return 0
    count = 0
    try:
        with open(fasta_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('>'):
                    count += 1
    except Exception:
        pass
    return count


def count_json_sequences(json_path: Path) -> int:
    """JSON"""
    if not json_path.exists:
        return 0
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                if 'entries' in data:
                    return len(data['entries'])
                elif 'count' in data:
                    return data['count']
                elif 'translated_count' in data:
                    return data['translated_count']
            elif isinstance(data, list):
                return len(data)
    except Exception:
        pass
    return 0


def count_jsonl_sequences(jsonl_path: Path) -> int:
    """JSONL"""
    if not jsonl_path.exists:
        return 0
    count = 0
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip
                if line:
                    try:
                        json.loads(line)
                        count += 1
                    except:
                        pass
    except Exception:
        pass
    return count


def scan_species_ig_aa(species_dir: Path) -> Dict[str, Any]:
    """IG_AA"""
    species_name = species_dir.name.replace('_ig_aa', '')
    
    result = {
        "species": species_name,
        "species_display": species_name.replace('_', ' ').title,
        "directory": str(species_dir.relative_to(PROJECT_ROOT)),
        "libraries": {}
    }
    
    # summary
    summary_file = species_dir / f"{species_name}_ig_aa_summary.json"
    if summary_file.exists:
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)
                result["source"] = summary.get("source_dir", "IMGT")
                result["total_sequences"] = summary.get("total_sequences", 0)
                result["total_translated"] = summary.get("total_translated", 0)
                
                # summary
                if "files" in summary:
                    for seq_type, info in summary["files"].items:
                        result["libraries"][seq_type] = {
                            "count": info.get("count", 0),
                            "translated_count": info.get("translated_count", 0),
                            "fasta_file": info.get("fasta_file", ""),
                            "json_file": info.get("json_file", ""),
                            "format": "amino_acid",
                            "source": "IMGT"
                        }
        except Exception as e:
            print(f"Warning: Failed to read {summary_file}: {e}", file=sys.stderr)
    
    # 
    for seq_type in ["IGHV", "IGHD", "IGHJ", "IGKV", "IGKJ", "IGLV", "IGLJ"]:
        if seq_type not in result["libraries"]:
            fasta_file = species_dir / f"{seq_type}_aa.fasta"
            json_file = species_dir / f"{seq_type}_aa.json"
            
            fasta_count = count_fasta_sequences(fasta_file)
            json_count = count_json_sequences(json_file)
            
            if fasta_count > 0 or json_count > 0:
                result["libraries"][seq_type] = {
                    "count": max(fasta_count, json_count),
                    "translated_count": max(fasta_count, json_count),
                    "fasta_file": str(fasta_file.relative_to(PROJECT_ROOT)) if fasta_file.exists else "",
                    "json_file": str(json_file.relative_to(PROJECT_ROOT)) if json_file.exists else "",
                    "format": "amino_acid",
                    "source": "IMGT"
                }
    
    return result


def scan_vhh_libraries -> Dict[str, Any]:
    """VHH"""
    vhh_dir = GERMLINES_DIR / "vhh_v1"
    result = {
        "category": "VHH",
        "libraries": []
    }
    
    # VHH Scaffold Library v1
    scaffold_lib = vhh_dir / "vhh_scaffold_library_v1.jsonl"
    if scaffold_lib.exists:
        count = count_jsonl_sequences(scaffold_lib)
        result["libraries"].append({
            "id": "vhh_scaffold_library_v1",
            "name": "VHH Scaffold Library v1",
            "type": "scaffold",
            "count": count,
            "file_path": str(scaffold_lib.relative_to(PROJECT_ROOT)),
            "format": "JSONL",
            "status": "production",
            "suitable_for": ["VHH"],
            "source": "vhh_germline_assets_clean_with_canonical_proxy.jsonl"
        })
    
    # VHH Special FR Templates v1
    special_fr = vhh_dir / "vhh_special_fr_templates_v1.jsonl"
    if special_fr.exists:
        count = count_jsonl_sequences(special_fr)
        result["libraries"].append({
            "id": "vhh_special_fr_templates_v1",
            "name": "VHH Special FR Templates v1",
            "type": "special_fr",
            "count": count,
            "file_path": str(special_fr.relative_to(PROJECT_ROOT)),
            "format": "JSONL",
            "status": "production",
            "suitable_for": ["VHH"],
            "source": "vhh_germline_assets_clean_with_canonical_proxy.jsonl"
        })
    
    # Human VH3 VHH-SAFE Templates
    human_safe = GERMLINES_DIR / "human_ig_aa" / "vh_scaffolds" / "human_vh3_vhh_safe_templates.json"
    if human_safe.exists:
        count = count_json_sequences(human_safe)
        result["libraries"].append({
            "id": "human_vh3_vhh_safe_templates",
            "name": "Human VH3 VHH-SAFE Templates",
            "type": "engineered",
            "count": count,
            "file_path": str(human_safe.relative_to(PROJECT_ROOT)),
            "format": "JSON",
            "status": "production",
            "suitable_for": ["VHH", "humanized_VHH"],
            "source": "human_vh3_scaffolds"
        })
    
    # Vicugna Pacos VHH Scaffolds
    alpaca_vhh = GERMLINES_DIR / "vicugna_pacos_ig_aa" / "vhh_scaffolds" / "vhh_scaffolds.json"
    if alpaca_vhh.exists:
        count = count_json_sequences(alpaca_vhh)
        result["libraries"].append({
            "id": "vicugna_pacos_vhh_scaffolds",
            "name": "Vicugna Pacos VHH Scaffolds",
            "type": "scaffold",
            "count": count,
            "file_path": str(alpaca_vhh.relative_to(PROJECT_ROOT)),
            "format": "JSON",
            "status": "production",
            "suitable_for": ["VHH"],
            "source": "vicugna_pacos_ig_aa"
        })
    
    return result


def scan_vh_scaffold_libraries -> Dict[str, Any]:
    """VH scaffold"""
    result = {
        "category": "VH_Scaffolds",
        "libraries": []
    }
    
    # Human VH3 Scaffolds
    human_vh3 = GERMLINES_DIR / "human_ig_aa" / "vh_scaffolds" / "human_vh3_scaffolds.json"
    if human_vh3.exists:
        count = count_json_sequences(human_vh3)
        result["libraries"].append({
            "id": "human_vh3_scaffolds",
            "name": "Human VH3 Scaffolds",
            "type": "scaffold",
            "count": count,
            "file_path": str(human_vh3.relative_to(PROJECT_ROOT)),
            "format": "JSON",
            "status": "production",
            "suitable_for": ["VH"],
            "source": "human_ig_aa"
        })
    
    return result


def scan_fc_libraries -> Dict[str, Any]:
    """Fc"""
    fc_dir = GERMLINES_DIR / "fc_aa"
    result = {
        "category": "Fc_Constant_Regions",
        "libraries": []
    }
    
    # Fc
    for species_dir in fc_dir.iterdir:
        if not species_dir.is_dir or species_dir.name in ["annotated", "fc_database", "qc"]:
            continue
        
        species = species_dir.name
        for const_type in ["IGHC", "IGKC", "IGLC"]:
            fasta_file = species_dir / f"{const_type}_{species}.fasta"
            if fasta_file.exists:
                count = count_fasta_sequences(fasta_file)
                result["libraries"].append({
                    "id": f"{const_type}_{species}",
                    "name": f"{const_type} {species.title}",
                    "type": const_type,
                    "species": species,
                    "count": count,
                    "file_path": str(fasta_file.relative_to(PROJECT_ROOT)),
                    "format": "FASTA",
                    "status": "production",
                    "suitable_for": ["constant_region", "Fc"],
                    "source": "IMGT_constant_regions"
                })
    
    return result


def main:
    """"""
    print("🔍 germline...")
    
    inventory = {
        "metadata": {
            "title": "Germline Template Libraries Inventory",
            "version": "1.0.0",
            "generated_at": datetime.now.isoformat,
            "project": "Antibody Engineer Suite",
            "description": "Complete inventory of all reliable germline template libraries"
        },
        "summary": {
            "total_species": 0,
            "total_libraries": 0,
            "total_sequences": 0,
            "by_category": defaultdict(int),
            "by_suitable_for": defaultdict(int)
        },
        "categories": {}
    }
    
    # VHH
    print("  📚 VHH...")
    vhh_data = scan_vhh_libraries
    inventory["categories"]["VHH"] = vhh_data
    for lib in vhh_data["libraries"]:
        inventory["summary"]["total_libraries"] += 1
        inventory["summary"]["total_sequences"] += lib["count"]
        inventory["summary"]["by_category"]["VHH"] += lib["count"]
        for suitable in lib.get("suitable_for", []):
            inventory["summary"]["by_suitable_for"][suitable] += lib["count"]
    
    # VH scaffold
    print("  📚 VH scaffold...")
    vh_scaffold_data = scan_vh_scaffold_libraries
    if vh_scaffold_data["libraries"]:
        inventory["categories"]["VH_Scaffolds"] = vh_scaffold_data
        for lib in vh_scaffold_data["libraries"]:
            inventory["summary"]["total_libraries"] += 1
            inventory["summary"]["total_sequences"] += lib["count"]
            inventory["summary"]["by_category"]["VH"] += lib["count"]
            for suitable in lib.get("suitable_for", []):
                inventory["summary"]["by_suitable_for"][suitable] += lib["count"]
    
    # IG
    print("  🌍 IG...")
    species_libraries = {}
    for species_dir in sorted(GERMLINES_DIR.iterdir):
        if not species_dir.is_dir:
            continue
        if species_dir.name.endswith("_ig_aa"):
            species_data = scan_species_ig_aa(species_dir)
            species_libraries[species_data["species"]] = species_data
            inventory["summary"]["total_species"] += 1
            
            # 
            for seq_type, lib_info in species_data["libraries"].items:
                inventory["summary"]["total_libraries"] += 1
                count = lib_info.get("count", 0)
                inventory["summary"]["total_sequences"] += count
                
                # 
                if seq_type == "IGHV":
                    category = "VH" if "vhh" not in species_data["species"].lower else "VHH"
                    inventory["summary"]["by_category"][category] += count
                    inventory["summary"]["by_suitable_for"][category] += count
                elif seq_type in ["IGKV", "IGLV"]:
                    inventory["summary"]["by_category"]["VL"] += count
                    inventory["summary"]["by_suitable_for"]["VL"] += count
                elif seq_type in ["IGHJ", "IGKJ", "IGLJ"]:
                    inventory["summary"]["by_category"]["J_chain"] += count
                    inventory["summary"]["by_suitable_for"]["J_chain"] += count
                elif seq_type == "IGHD":
                    inventory["summary"]["by_category"]["D_region"] += count
    
    inventory["categories"]["Species_IG"] = {
        "category": "Species_IG",
        "species": species_libraries
    }
    
    # Fc
    print("  🔗 Fc...")
    fc_data = scan_fc_libraries
    inventory["categories"]["Fc_Constant_Regions"] = fc_data
    for lib in fc_data["libraries"]:
        inventory["summary"]["total_libraries"] += 1
        inventory["summary"]["total_sequences"] += lib["count"]
        inventory["summary"]["by_category"]["Fc"] += lib["count"]
        for suitable in lib.get("suitable_for", []):
            inventory["summary"]["by_suitable_for"][suitable] += lib["count"]
    
    # defaultdictdict
    inventory["summary"]["by_category"] = dict(inventory["summary"]["by_category"])
    inventory["summary"]["by_suitable_for"] = dict(inventory["summary"]["by_suitable_for"])
    
    # JSON
    output_json = PROJECT_ROOT / "reports" / "germlines" / "germline_libraries_inventory.json"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON: {output_json}")
    
    # MD
    output_md = PROJECT_ROOT / "reports" / "germlines" / "germline_libraries_inventory.md"
    md_content = generate_markdown_report(inventory)
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"✅ Markdown: {output_md}")
    
    print(f"\n📊 :")
    print(f"  : {inventory['summary']['total_species']}")
    print(f"  : {inventory['summary']['total_libraries']}")
    print(f"  : {inventory['summary']['total_sequences']}")
    print(f"\n✅ ！")


def generate_markdown_report(inventory: Dict[str, Any]) -> str:
    """Markdown"""
    lines = []
    meta = inventory["metadata"]
    summary = inventory["summary"]
    
    lines.append(f"# Germline")
    lines.append("")
    lines.append(f"****: {meta['generated_at']}")
    lines.append(f"****: {meta['version']}")
    lines.append(f"****: {meta['project']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 
    lines.append("## 1. ")
    lines.append("")
    lines.append(f"- ****: {summary['total_species']}")
    lines.append(f"- ****: {summary['total_libraries']}")
    lines.append(f"- ****: {summary['total_sequences']:,}")
    lines.append("")
    lines.append("****:")
    lines.append("- ****（amino acid sequences）")
    lines.append("- ****（MVP）")
    lines.append("- **IMGT**")
    lines.append("")
    
    # 
    lines.append("### 1.1 ")
    lines.append("")
    lines.append("|  |  |  |")
    lines.append("|------|--------|------|")
    total = summary['total_sequences']
    for category, count in sorted(summary['by_category'].items, key=lambda x: x[1], reverse=True):
        pct = (count / total * 100) if total > 0 else 0
        lines.append(f"| {category} | {count:,} | {pct:.1f}% |")
    lines.append("")
    
    # 
    lines.append("### 1.2 ")
    lines.append("")
    lines.append("|  |  |")
    lines.append("|---------|--------|")
    for suitable, count in sorted(summary['by_suitable_for'].items, key=lambda x: x[1], reverse=True):
        lines.append(f"| {suitable} | {count:,} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # VHH
    if "VHH" in inventory["categories"]:
        lines.append("## 2. VHH")
        lines.append("")
        lines.append("****: VHH，scaffoldengineered")
        lines.append("")
        vhh_data = inventory["categories"]["VHH"]
        for lib in vhh_data["libraries"]:
            lines.append(f"### 2.{vhh_data['libraries'].index(lib) + 1} {lib['name']}")
            lines.append("")
            lines.append(f"- **ID**: `{lib['id']}`")
            lines.append(f"- ****: {lib['type']}")
            lines.append(f"- ****: {lib['count']}")
            lines.append(f"- ****: {lib['format']}")
            lines.append(f"- ****: {lib['status']}")
            lines.append(f"- ****: {', '.join(lib.get('suitable_for', []))}")
            lines.append(f"- ****: {lib.get('source', 'N/A')}")
            lines.append(f"- ****: `{lib['file_path']}`")
            lines.append("")
        lines.append("---")
        lines.append("")
    
    # VH Scaffold
    if "VH_Scaffolds" in inventory["categories"]:
        lines.append("## 2.5 VH Scaffold")
        lines.append("")
        lines.append("****: VHscaffold，VH")
        lines.append("")
        vh_scaffold_data = inventory["categories"]["VH_Scaffolds"]
        for lib in vh_scaffold_data["libraries"]:
            lines.append(f"### 2.5.{vh_scaffold_data['libraries'].index(lib) + 1} {lib['name']}")
            lines.append("")
            lines.append(f"- **ID**: `{lib['id']}`")
            lines.append(f"- ****: {lib['type']}")
            lines.append(f"- ****: {lib['count']}")
            lines.append(f"- ****: {lib['format']}")
            lines.append(f"- ****: {lib['status']}")
            lines.append(f"- ****: {', '.join(lib.get('suitable_for', []))}")
            lines.append(f"- ****: {lib.get('source', 'N/A')}")
            lines.append(f"- ****: `{lib['file_path']}`")
            lines.append("")
        lines.append("---")
        lines.append("")
    
    # IG
    if "Species_IG" in inventory["categories"]:
        lines.append("## 3. IG")
        lines.append("")
        lines.append("****: germline，V、D、J，")
        lines.append("")
        species_data = inventory["categories"]["Species_IG"]["species"]
        
        for species, data in sorted(species_data.items):
            lines.append(f"### 3.{list(species_data.keys).index(species) + 1} {data['species_display']}")
            lines.append("")
            lines.append(f"- ****: {data['species']}")
            lines.append(f"- ****: {data.get('total_sequences', 0)}")
            lines.append(f"- ****: {data.get('total_translated', 0)}")
            lines.append(f"- ****: {data.get('source', 'IMGT')}")
            lines.append("")
            
            lines.append("|  |  |  |")
            lines.append("|---------|------|---------|")
            for seq_type, lib_info in sorted(data["libraries"].items):
                count = lib_info.get("count", 0)
                if seq_type == "IGHV":
                    suitable = "VH" if "vhh" not in species.lower else "VHH"
                elif seq_type in ["IGKV", "IGLV"]:
                    suitable = "VL"
                elif seq_type in ["IGHJ", "IGKJ", "IGLJ"]:
                    suitable = "J_chain (FR4)"
                elif seq_type == "IGHD":
                    suitable = "D_region"
                else:
                    suitable = "N/A"
                lines.append(f"| {seq_type} | {count} | {suitable} |")
            lines.append("")
        lines.append("---")
        lines.append("")
    
    # Fc
    if "Fc_Constant_Regions" in inventory["categories"]:
        lines.append("## 4. Fc")
        lines.append("")
        lines.append("****: ，IGHC、IGKC（κ）、IGLC（λ）")
        lines.append("")
        fc_data = inventory["categories"]["Fc_Constant_Regions"]
        
        # 
        by_species = defaultdict(list)
        for lib in fc_data["libraries"]:
            by_species[lib["species"]].append(lib)
        
        for species, libs in sorted(by_species.items):
            lines.append(f"### 4.{list(by_species.keys).index(species) + 1} {species.title}")
            lines.append("")
            lines.append("|  |  |  |")
            lines.append("|------|------|---------|")
            for lib in sorted(libs, key=lambda x: x["type"]):
                lines.append(f"| {lib['type']} | {lib['count']} | `{lib['file_path']}` |")
            lines.append("")
        lines.append("---")
        lines.append("")
    
    # 
    lines.append("## 5. ")
    lines.append("")
    lines.append("### 5.1 VHH")
    lines.append("")
    lines.append("****: VHH，scaffold、engineeredVHH")
    lines.append("")
    vhh_libs = []
    if "VHH" in inventory["categories"]:
        for lib in inventory["categories"]["VHH"]["libraries"]:
            vhh_libs.append({
                "name": lib["name"],
                "count": lib["count"],
                "file_path": lib["file_path"],
                "type": lib["type"]
            })
    if "Species_IG" in inventory["categories"]:
        for species, data in inventory["categories"]["Species_IG"]["species"].items:
            if "vhh" in species.lower or "vicugna" in species.lower:
                for seq_type, lib_info in data["libraries"].items:
                    if seq_type == "IGHV":
                        vhh_libs.append({
                            "name": f"{data['species_display']} IGHV",
                            "count": lib_info.get("count", 0),
                            "file_path": lib_info.get("fasta_file", ""),
                            "type": "germline"
                        })
    
    lines.append("|  |  |  |  |")
    lines.append("|--------|------|------|---------|")
    for lib in vhh_libs:
        lib_type = lib.get("type", "N/A")
        lines.append(f"| {lib['name']} | {lib_type} | {lib['count']} | `{lib.get('file_path', 'N/A')}` |")
    lines.append("")
    
    lines.append("### 5.2 VH")
    lines.append("")
    lines.append("****: VH，IGHV germlineHuman VH3 scaffold")
    lines.append("")
    vh_libs = []
    # VH Scaffold
    if "VH_Scaffolds" in inventory["categories"]:
        for lib in inventory["categories"]["VH_Scaffolds"]["libraries"]:
            vh_libs.append({
                "name": lib["name"],
                "count": lib["count"],
                "file_path": lib["file_path"],
                "type": lib["type"]
            })
    # IGHV
    if "Species_IG" in inventory["categories"]:
        for species, data in inventory["categories"]["Species_IG"]["species"].items:
            if "vhh" not in species.lower and "vicugna" not in species.lower:
                for seq_type, lib_info in data["libraries"].items:
                    if seq_type == "IGHV":
                        vh_libs.append({
                            "name": f"{data['species_display']} IGHV",
                            "count": lib_info.get("count", 0),
                            "file_path": lib_info.get("fasta_file", ""),
                            "type": "germline"
                        })
    
    lines.append("|  |  |  |  |")
    lines.append("|--------|------|------|---------|")
    for lib in vh_libs:
        lib_type = lib.get("type", "germline")
        lines.append(f"| {lib['name']} | {lib_type} | {lib['count']} | `{lib.get('file_path', 'N/A')}` |")
    lines.append("")
    
    lines.append("### 5.3 VL")
    lines.append("")
    vl_libs = []
    if "Species_IG" in inventory["categories"]:
        for species, data in inventory["categories"]["Species_IG"]["species"].items:
            for seq_type, lib_info in data["libraries"].items:
                if seq_type in ["IGKV", "IGLV"]:
                    vl_libs.append({
                        "name": f"{data['species_display']} {seq_type}",
                        "count": lib_info.get("count", 0),
                        "file_path": lib_info.get("fasta_file", "")
                    })
    
    lines.append("|  |  |  |")
    lines.append("|--------|------|---------|")
    for lib in vl_libs:
        lines.append(f"| {lib['name']} | {lib['count']} | `{lib.get('file_path', 'N/A')}` |")
    lines.append("")
    
    lines.append("### 5.4 J（FR4）")
    lines.append("")
    j_libs = []
    if "Species_IG" in inventory["categories"]:
        for species, data in inventory["categories"]["Species_IG"]["species"].items:
            for seq_type, lib_info in data["libraries"].items:
                if seq_type in ["IGHJ", "IGKJ", "IGLJ"]:
                    j_libs.append({
                        "name": f"{data['species_display']} {seq_type}",
                        "count": lib_info.get("count", 0),
                        "file_path": lib_info.get("fasta_file", "")
                    })
    
    lines.append("|  |  |  |")
    lines.append("|--------|------|---------|")
    for lib in j_libs:
        lines.append(f"| {lib['name']} | {lib['count']} | `{lib.get('file_path', 'N/A')}` |")
    lines.append("")
    
    lines.append("### 5.5 Fc")
    lines.append("")
    if "Fc_Constant_Regions" in inventory["categories"]:
        lines.append("|  |  |  |  |")
        lines.append("|------|------|------|---------|")
        for lib in inventory["categories"]["Fc_Constant_Regions"]["libraries"]:
            lines.append(f"| {lib['type']} | {lib['species']} | {lib['count']} | `{lib['file_path']}` |")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append(f"****: {meta['generated_at']}")
    lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    main

