#!/usr/bin/env python3
"""
Build Arsenal Summary v1
germline
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

# 
PROJECT_ROOT = Path(__file__).resolve().parents[1]


# （）
USE_CASE_RULES = {
    # VHH
    "vhh_humanization": {
        "conditions": [
            lambda lib: "humanized_VHH" in lib.get("suitable_for", []),
            lambda lib: "VHH-SAFE" in lib.get("name", "").upper() or "VHH-SAFE" in lib.get("id", "").upper(),
        ],
        "use_cases": ["VHH_humanization", "VHH_scaffold_selection"],
        "readiness": "high"
    },
    # VHH scaffold
    "vhh_scaffold_selection": {
        "conditions": [
            lambda lib: lib.get("category") == "VHH" and lib.get("type") in ["scaffold", "special_fr"],
        ],
        "use_cases": ["VHH_scaffold_selection"],
        "readiness": "medium"
    },
    # VH
    "vh_humanization": {
        "conditions": [
            lambda lib: lib.get("category") == "Species_IG" and lib.get("gene_type") == "IGHV" and lib.get("species") == "human",
        ],
        "use_cases": ["VH_humanization"],
        "readiness": "medium"
    },
    # VK
    "vk_humanization": {
        "conditions": [
            lambda lib: lib.get("category") == "Species_IG" and lib.get("gene_type") == "IGKV" and lib.get("species") == "human",
        ],
        "use_cases": ["VK_humanization"],
        "readiness": "medium"
    },
    # VL
    "vl_humanization": {
        "conditions": [
            lambda lib: lib.get("category") == "Species_IG" and lib.get("gene_type") == "IGLV" and lib.get("species") == "human",
        ],
        "use_cases": ["VL_humanization"],
        "readiness": "medium"
    },
    # VH（）
    "vh_speciesization": {
        "conditions": [
            lambda lib: lib.get("category") == "Species_IG" and lib.get("gene_type") == "IGHV" and lib.get("species") != "human",
        ],
        "use_cases": ["VH_speciesization"],
        "readiness": "medium"
    },
    # VL（）
    "vl_speciesization": {
        "conditions": [
            lambda lib: lib.get("category") == "Species_IG" and lib.get("gene_type") in ["IGKV", "IGLV"] and lib.get("species") != "human",
        ],
        "use_cases": ["VL_speciesization"],
        "readiness": "medium"
    },
    # Fc
    "fc_swap": {
        "conditions": [
            lambda lib: lib.get("category") == "Fc_Constant_Regions",
        ],
        "use_cases": ["Fc_swap", "speciesization_constant_region"],
        "readiness": "medium"
    },
    # 
    "dogization": {
        "conditions": [
            lambda lib: lib.get("category") == "Fc_Constant_Regions" and lib.get("species") == "dog",
        ],
        "use_cases": ["dogization_full_IgG"],
        "readiness": "medium"
    },
    # 
    "catization": {
        "conditions": [
            lambda lib: lib.get("category") == "Fc_Constant_Regions" and lib.get("species") == "cat",
        ],
        "use_cases": ["catization_full_IgG"],
        "readiness": "medium"
    },
    # VH scaffold
    "vh_scaffold_selection": {
        "conditions": [
            lambda lib: lib.get("category") == "VH_Scaffolds",
        ],
        "use_cases": ["VH_scaffold_selection"],
        "readiness": "medium"
    },
}


def derive_use_cases_and_readiness(lib: Dict[str, Any]) -> tuple[List[str], str]:
    """use_casesreadiness"""
    use_cases = set()
    readiness_levels = []
    
    for rule_name, rule in USE_CASE_RULES.items():
        # 
        if any(condition(lib) for condition in rule["conditions"]):
            use_cases.update(rule["use_cases"])
            readiness_levels.append(rule["readiness"])
    
    # readiness（：high > medium > low）
    if not readiness_levels:
        readiness = "low"
    elif "high" in readiness_levels:
        readiness = "high"
    elif "medium" in readiness_levels:
        readiness = "medium"
    else:
        readiness = "low"
    
    return sorted(list(use_cases)), readiness


def derive_key_features(lib: Dict[str, Any], schema_audit: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """key_features_claimable（，schema audit）"""
    lib_id = lib.get("id", "")
    features = {}
    
    # schema audit
    audit_data = None
    if schema_audit and "libraries" in schema_audit:
        audit_data = schema_audit["libraries"].get(lib_id)
    
    # imgt_numberable
    if lib.get("source") == "IMGT" or "imgt" in str(lib.get("source", "")).lower():
        features["imgt_numberable"] = "assumed_yes_from_imgt_source"
    else:
        features["imgt_numberable"] = "unknown"
    
    # dual_numbering_available（schema audit）
    if audit_data and audit_data.get("has_dual_numbering_map"):
        if "imgt_map" in str(audit_data.get("dual_numbering_field_candidates", [])) and \
           "kabat_map" in str(audit_data.get("dual_numbering_field_candidates", [])):
            features["dual_numbering_available"] = "present_via_imgt_map_and_kabat_map"
        else:
            features["dual_numbering_available"] = "present"
    else:
        features["dual_numbering_available"] = "unknown"
    
    # cdr_boundaries（schema audit）
    if audit_data and audit_data.get("has_sequence_field"):
        # consensus.fr1-4
        field_candidates = audit_data.get("sequence_field_candidates", [])
        has_consensus_fr = any("consensus.fr" in str(f) for f in field_candidates) or \
                          any("consensus.framework_full" in str(f) for f in field_candidates)
        if has_consensus_fr:
            features["cdr_boundaries"] = "computable_from_consensus_fr_segments"
        elif lib.get("source") == "IMGT" or lib.get("format") == "amino_acid":
            features["cdr_boundaries"] = "computable"
        else:
            features["cdr_boundaries"] = "unknown"
    elif lib.get("source") == "IMGT" or lib.get("format") == "amino_acid":
        features["cdr_boundaries"] = "computable"
    else:
        features["cdr_boundaries"] = "unknown"
    
    # cdr_canonical
    features["cdr_canonical"] = "unknown"
    
    # vernier_zone
    features["vernier_zone"] = "unknown"
    
    # hallmark（schema audit）
    if audit_data and audit_data.get("has_hallmark"):
        # VHH
        if lib.get("category") == "VHH" or "vhh" in lib_id.lower():
            features["hallmark"] = "present_vhh_hallmark"
        else:
            features["hallmark"] = "present"
    else:
        features["hallmark"] = "unknown"
    
    # fr_clustered（schema audit）
    if audit_data and audit_data.get("has_cluster_id"):
        # canonical_proxycluster_id
        cluster_candidates = audit_data.get("cluster_field_candidates", [])
        has_canonical_proxy_cluster = any("canonical_proxy" in str(f) and "cluster_id" in str(f) 
                                         for f in cluster_candidates)
        if has_canonical_proxy_cluster:
            features["fr_clustered"] = "present_via_canonical_proxy_cluster_id"
        else:
            features["fr_clustered"] = "present"
    else:
        features["fr_clustered"] = "unknown"
    
    # canonical_proxy（schema audit）
    if audit_data and audit_data.get("has_canonical_proxy"):
        features["canonical_proxy"] = "present"
    else:
        source_str = str(lib.get("source", "")).lower()
        if "canonical_proxy" in source_str:
            features["canonical_proxy"] = "hinted_by_source_name"
        else:
            features["canonical_proxy"] = "unknown"
    
    return features


def normalize_file_path(file_path: str) -> str:
    """（）"""
    if not file_path:
        return ""
    # 
    return file_path.replace("\\", "/")


def process_library(lib_id: str, lib_data: Dict[str, Any], category: str, schema_audit: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """，"""
    # 
    name = lib_data.get("name", lib_id)
    lib_type = lib_data.get("type", "unknown")
    count = lib_data.get("count", 0)
    file_path = normalize_file_path(lib_data.get("file_path", ""))
    format_type = lib_data.get("format", "unknown")
    status = lib_data.get("status", "unknown")
    suitable_for = lib_data.get("suitable_for", [])
    source = lib_data.get("source", "")
    
    # species
    species = lib_data.get("species")
    if not species and category == "Species_IG":
        # species
        species = lib_data.get("species_display", "").lower().replace(" ", "_")
    
    # gene_type（Species_IG）
    gene_type = None
    if category == "Species_IG":
        # librarieskey
        for key in ["IGHV", "IGHD", "IGHJ", "IGKV", "IGKJ", "IGLV", "IGLJ"]:
            if key in str(lib_data):
                gene_type = key
                break
    
    # （）
    lib_obj = {
        "id": lib_id,
        "name": name,
        "category": category,
        "type": lib_type,
        "species": species,
        "gene_type": gene_type,
        "suitable_for": suitable_for,
        "source": source,
    }
    
    # use_casesreadiness
    use_cases, readiness = derive_use_cases_and_readiness(lib_obj)
    
    # key_features（schema audit）
    key_features = derive_key_features(lib_obj, schema_audit)
    
    # 
    result = {
        "name": name,
        "category": category,
        "type": lib_type,
        "species": species,
        "count": count,
        "file_path": file_path,
        "format": format_type,
        "status": status,
        "suitable_for": suitable_for,
        "source": source,
        "use_cases": use_cases,
        "readiness": readiness,
        "key_features_claimable": key_features,
    }
    
    return result


def extract_all_libraries(inventory: Dict[str, Any], schema_audit: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """inventory"""
    libraries = {}
    
    # VHH
    if "VHH" in inventory.get("categories", {}):
        for lib in inventory["categories"]["VHH"].get("libraries", []):
            lib_id = lib.get("id")
            if lib_id:
                libraries[lib_id] = process_library(lib_id, lib, "VHH", schema_audit)
    
    # VH_Scaffolds
    if "VH_Scaffolds" in inventory.get("categories", {}):
        for lib in inventory["categories"]["VH_Scaffolds"].get("libraries", []):
            lib_id = lib.get("id")
            if lib_id:
                libraries[lib_id] = process_library(lib_id, lib, "VH_Scaffolds", schema_audit)
    
    # Species_IG
    if "Species_IG" in inventory.get("categories", {}):
        species_data = inventory["categories"]["Species_IG"].get("species", {})
        for species_name, species_info in species_data.items():
            for gene_type, gene_info in species_info.get("libraries", {}).items():
                # ID
                lib_id = f"{species_name}_{gene_type}"
                
                # 
                # json_file，fasta_file
                file_path = gene_info.get("json_file", "") or gene_info.get("fasta_file", "")
                # 
                if file_path:
                    try:
                        file_path_obj = Path(file_path)
                        if file_path_obj.is_absolute():
                            # 
                            try:
                                file_path = str(file_path_obj.relative_to(PROJECT_ROOT))
                            except ValueError:
                                # ，
                                file_path = normalize_file_path(file_path)
                        else:
                            file_path = normalize_file_path(file_path)
                    except Exception:
                        file_path = normalize_file_path(file_path)
                else:
                    file_path = ""
                
                lib_data = {
                    "name": f"{species_info.get('species_display', species_name)} {gene_type}",
                    "type": "germline",
                    "count": gene_info.get("count", 0),
                    "file_path": file_path,
                    "format": gene_info.get("format", "amino_acid"),
                    "status": "production",
                    "suitable_for": [],
                    "source": gene_info.get("source", "IMGT"),
                    "species": species_name,
                    "gene_type": gene_type,
                }
                
                libraries[lib_id] = process_library(lib_id, lib_data, "Species_IG", schema_audit)
    
    # Fc_Constant_Regions
    if "Fc_Constant_Regions" in inventory.get("categories", {}):
        for lib in inventory["categories"]["Fc_Constant_Regions"].get("libraries", []):
            lib_id = lib.get("id")
            if lib_id:
                libraries[lib_id] = process_library(lib_id, lib, "Fc_Constant_Regions", schema_audit)
    
    return libraries


def build_arsenal_summary(inventory_json_path: Path, inventory_md_path: Optional[Path], out_dir: Path) -> Dict[str, Any]:
    """arsenal summary"""
    # inventory JSON
    with open(inventory_json_path, 'r', encoding='utf-8') as f:
        inventory = json.load(f)
    
    # inventory MD（）
    md_generated_at = None
    if inventory_md_path and inventory_md_path.exists():
        with open(inventory_md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
            # 
            for line in md_content.split('\n'):
                if '' in line or 'generated_at' in line.lower():
                    # ISO
                    import re
                    match = re.search(r'(\d{4}-\d{2}-\d{2}T[\d:\.]+)', line)
                    if match:
                        md_generated_at = match.group(1)
                    break
    
    # schema audit（）
    schema_audit = None
    schema_audit_path = out_dir / "schema_audit_v1.json"
    if schema_audit_path.exists():
        try:
            with open(schema_audit_path, 'r', encoding='utf-8') as f:
                schema_audit = json.load(f)
            print(f"✅ schema audit: {schema_audit_path}")
        except Exception as e:
            print(f"⚠️  schema audit: {e}")
    
    # （schema audit）
    libraries = extract_all_libraries(inventory, schema_audit)
    
    # （）
    def get_relative_path(path: Path) -> str:
        if path is None:
            return None
        path = Path(path).resolve()
        try:
            rel_path = path.relative_to(PROJECT_ROOT)
            # 
            return str(rel_path).replace("\\", "/")
        except ValueError:
            # ，（）
            return str(path).replace("\\", "/")
    
    # summary
    summary = {
        "metadata": {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "source_files": [
                get_relative_path(inventory_json_path),
                get_relative_path(inventory_md_path) if inventory_md_path else None
            ],
            "scope": "inventory_only_no_heavy_compute"
        },
        "totals": {
            "total_species": inventory.get("summary", {}).get("total_species", 0),
            "total_libraries": len(libraries),
            "total_sequences": inventory.get("summary", {}).get("total_sequences", 0),
            "by_category": inventory.get("summary", {}).get("by_category", {}),
            "by_suitable_for": inventory.get("summary", {}).get("by_suitable_for", {}),
        },
        "libraries": libraries
    }
    
    return summary


def generate_markdown_report(summary: Dict[str, Any]) -> str:
    """Markdown"""
    lines = []
    
    lines.append("# Arsenal Summary v1")
    lines.append("")
    lines.append(f"****: {summary['metadata']['generated_at']}")
    lines.append(f"****: {summary['metadata']['version']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 
    lines.append("## 1. ")
    lines.append("")
    totals = summary["totals"]
    lines.append("|  |  |")
    lines.append("|------|------|")
    lines.append(f"|  | {totals['total_species']} |")
    lines.append(f"|  | {totals['total_libraries']} |")
    lines.append(f"|  | {totals['total_sequences']:,} |")
    lines.append("")
    
    # 
    lines.append("|  |  |")
    lines.append("|------|--------|")
    for category, count in sorted(totals["by_category"].items(), key=lambda x: x[1], reverse=True):
        lines.append(f"| {category} | {count:,} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 
    lines.append("## 2. ")
    lines.append("")
    use_case_map = defaultdict(list)
    for lib_id, lib_data in summary["libraries"].items():
        for use_case in lib_data.get("use_cases", []):
            use_case_map[use_case].append(lib_id)
    
    lines.append("|  |  | ID |")
    lines.append("|---------|--------|---------|")
    for use_case, lib_ids in sorted(use_case_map.items()):
        lib_list = ", ".join(lib_ids[:5])  # 5
        if len(lib_ids) > 5:
            lib_list += f" ... ({len(lib_ids)})"
        lines.append(f"| {use_case} | {len(lib_ids)} | {lib_list} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 
    lines.append("## 3. ")
    lines.append("")
    lines.append("| Library ID | Count | Type | Species | Use Cases | Readiness | Canonical Proxy Hint |")
    lines.append("|-----------|-------|------|---------|-----------|-----------|---------------------|")
    for lib_id, lib_data in sorted(summary["libraries"].items()):
        count = lib_data.get("count", 0)
        lib_type = lib_data.get("type", "unknown")
        species = lib_data.get("species") or "N/A"
        use_cases = ", ".join(lib_data.get("use_cases", [])) or "N/A"
        readiness = lib_data.get("readiness", "unknown")
        canonical_proxy = lib_data.get("key_features_claimable", {}).get("canonical_proxy", "unknown")
        lines.append(f"| {lib_id} | {count} | {lib_type} | {species} | {use_cases} | {readiness} | {canonical_proxy} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 
    lines.append("## 4. ")
    lines.append("")
    lines.append("|  |  |  |")
    lines.append("|------|------|------|")
    
    # 
    feature_status = defaultdict(lambda: {"unknown": 0, "computable": 0, "hinted": 0, "assumed": 0})
    for lib_data in summary["libraries"].values():
        features = lib_data.get("key_features_claimable", {})
        for feature_name, status in features.items():
            if "unknown" in status:
                feature_status[feature_name]["unknown"] += 1
            elif "computable" in status:
                feature_status[feature_name]["computable"] += 1
            elif "hinted" in status:
                feature_status[feature_name]["hinted"] += 1
            elif "assumed" in status:
                feature_status[feature_name]["assumed"] += 1
    
    feature_display_names = {
        "hallmark": "Hallmark Positions",
        "vernier_zone": "Vernier Zone",
        "fr_clustered": "FR Clustered",
        "cdr_canonical": "CDR Canonical",
        "cdr_boundaries": "CDR Boundaries",
        "dual_numbering_available": "Dual Numbering (IMGT↔Kabat)",
        "imgt_numberable": "IMGT Numberable",
        "canonical_proxy": "Canonical Proxy",
    }
    
    for feature_key, display_name in feature_display_names.items():
        stats = feature_status[feature_key]
        total = sum(stats.values())
        if total == 0:
            status_str = "unknown"
            desc = ""
        else:
            status_parts = []
            if stats["assumed"] > 0:
                status_parts.append(f"{stats['assumed']} assumed")
            if stats["computable"] > 0:
                status_parts.append(f"{stats['computable']} computable")
            if stats["hinted"] > 0:
                status_parts.append(f"{stats['hinted']} hinted")
            if stats["unknown"] > 0:
                status_parts.append(f"{stats['unknown']} unknown")
            status_str = ", ".join(status_parts)
            desc = f"{total}"
        
        lines.append(f"| {display_name} | {status_str} | {desc} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"****: {summary['metadata']['generated_at']}")
    lines.append("")
    
    return "\n".join(lines)


def generate_gaps_report(summary: Dict[str, Any]) -> str:
    """"""
    lines = []
    
    lines.append("# Arsenal Gaps and Next Actions v1")
    lines.append("")
    lines.append(f"****: {summary['metadata']['generated_at']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    lines.append("## Gaps（）")
    lines.append("")
    
    # 
    feature_status = defaultdict(lambda: {"unknown": 0, "computable": 0, "hinted": 0, "assumed": 0})
    for lib_data in summary["libraries"].values():
        features = lib_data.get("key_features_claimable", {})
        for feature_name, status in features.items():
            if "unknown" in status:
                feature_status[feature_name]["unknown"] += 1
            elif "computable" in status:
                feature_status[feature_name]["computable"] += 1
            elif "hinted" in status:
                feature_status[feature_name]["hinted"] += 1
            elif "assumed" in status:
                feature_status[feature_name]["assumed"] += 1
    
    # Gap 1: Hallmark
    hallmark_unknown = feature_status["hallmark"]["unknown"]
    lines.append("### Gap 1: Hallmark")
    lines.append("")
    lines.append(f"- ****: {hallmark_unknown}unknown")
    lines.append("- ****: hallmark？")
    lines.append("- ****: VHH hallmark")
    lines.append("")
    
    # Gap 2: Vernier Zone
    vernier_unknown = feature_status["vernier_zone"]["unknown"]
    lines.append("### Gap 2: Vernier Zone")
    lines.append("")
    lines.append(f"- ****: {vernier_unknown}unknown")
    lines.append("- ****: vernier zone？")
    lines.append("- ****: Vernier Zone")
    lines.append("")
    
    # Gap 3: FR Clustered
    cluster_unknown = feature_status["fr_clustered"]["unknown"]
    lines.append("### Gap 3: FR Clustered")
    lines.append("")
    lines.append(f"- ****: {cluster_unknown}unknown")
    lines.append("- ****: cluster_id / fr_cluster？")
    lines.append("- ****: FR")
    lines.append("")
    
    # Gap 4: Dual Numbering
    dual_unknown = feature_status["dual_numbering_available"]["unknown"]
    lines.append("### Gap 4: Dual Numbering Map")
    lines.append("")
    lines.append(f"- ****: {dual_unknown}unknown")
    lines.append("- ****: dual numbering map（IMGT↔Kabat）？")
    lines.append("- ****: ")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## Next Actions（）")
    lines.append("")
    
    lines.append("### 1. Schema Audit（）")
    lines.append("")
    lines.append("- ****: JSONL/JSON")
    lines.append("- ****: ")
    lines.append("- ****: ")
    lines.append("  - ")
    lines.append("  - ")
    lines.append("  - ")
    lines.append("")
    
    lines.append("### 2. Hallmark/Vernier")
    lines.append("")
    lines.append("- ****: hallmark/vernier")
    lines.append("- ****: ")
    lines.append("- ****: ")
    lines.append("  - hallmark（YAML/JSON）")
    lines.append("  - vernier zone")
    lines.append("  - ")
    lines.append("  - ")
    lines.append("")
    
    lines.append("### 3. FR")
    lines.append("")
    lines.append("- ****: ")
    lines.append("- ****: FR-onlycluster_id")
    lines.append("  - FR")
    lines.append("  - （identity0.90）")
    lines.append("  - clustercluster_id")
    lines.append("  - cluster_id")
    lines.append("")
    
    lines.append("### 4. Dual Numbering Map")
    lines.append("")
    lines.append("- ****: dual numbering map")
    lines.append("- ****: IMGT↔Kabat")
    lines.append("- ****: ")
    lines.append("  - anarcii")
    lines.append("  - IMGTKabat")
    lines.append("  - （JSON/JSONL）")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("****: ，。")
    lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Build Arsenal Summary v1")
    parser.add_argument("--inventory_json", type=Path, required=True,
                        help="Path to germline_libraries_inventory.json")
    parser.add_argument("--inventory_md", type=Path, default=None,
                        help="Path to germline_libraries_inventory.md (optional)")
    parser.add_argument("--out_dir", type=Path, required=True,
                        help="Output directory")
    
    args = parser.parse_args()
    
    # 
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # summary
    print("🔍 inventory...")
    summary = build_arsenal_summary(args.inventory_json, args.inventory_md, args.out_dir)
    
    # JSON
    json_path = args.out_dir / "arsenal_summary_v1.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON: {json_path}")
    
    # MD
    md_path = args.out_dir / "arsenal_summary_v1.md"
    md_content = generate_markdown_report(summary)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"✅ Markdown: {md_path}")
    
    # Gaps
    gaps_path = args.out_dir / "arsenal_gaps_and_next_actions_v1.md"
    gaps_content = generate_gaps_report(summary)
    with open(gaps_path, 'w', encoding='utf-8') as f:
        f.write(gaps_content)
    print(f"✅ Gaps: {gaps_path}")
    
    # summary
    print(f"\n📊 :")
    print(f"  : {summary['totals']['total_libraries']}")
    print(f"  : {summary['totals']['total_sequences']:,}")
    print(f"  :")
    print(f"    - {json_path}")
    print(f"    - {md_path}")
    print(f"    - {gaps_path}")
    print(f"\n✅ ！")


if __name__ == "__main__":
    main()

