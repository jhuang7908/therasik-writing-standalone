#!/usr/bin/env python3
"""
Schema Audit v1
，（schema），
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from collections import Counter, defaultdict

# 
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ID
TARGET_LIBRARY_IDS = [
    "human_vh3_vhh_safe_templates",
    "vhh_scaffold_library_v1",
    "vhh_special_fr_templates_v1",
    "human_vh3_scaffolds",
]

# （）
SEQUENCE_FIELD_CANDIDATES = [
    "sequence", "aa_sequence", "amino_acid_sequence", "seq", "aa_seq",
    "variable_domain_sequence", "v_sequence", "fr_sequence", "cdr_sequence"
]

NUMBERING_FIELD_CANDIDATES = [
    "imgt_numbering", "kabat_numbering", "numbering", "imgt_positions",
    "kabat_positions", "imgt_map", "kabat_map", "numbering_map"
]

CANONICAL_PROXY_FIELD_CANDIDATES = [
    "canonical_proxy", "canonical_class", "cdr_canonical", "canonical",
    "canonical_structure", "canonical_type"
]

HALLMARK_FIELD_CANDIDATES = [
    "hallmark", "hallmark_positions", "vh_hallmark", "hallmark_sites",
    "hallmark_residues", "hallmark_annotations"
]

VERNIER_FIELD_CANDIDATES = [
    "vernier", "vernier_zone", "vernier_positions", "vernier_residues",
    "vernier_annotations", "vernier_sites"
]

CLUSTER_FIELD_CANDIDATES = [
    "cluster_id", "fr_cluster", "cluster", "cluster_index", "cluster_name",
    "fr_cluster_id", "scaffold_cluster"
]

DUAL_NUMBERING_FIELD_CANDIDATES = [
    "dual_numbering", "dual_map", "imgt_kabat_map", "numbering_dual_map",
    "dual_numbering_map", "imgt_to_kabat", "kabat_to_imgt"
]


def normalize_path(file_path: str) -> Path:
    """"""
    if not file_path:
        return None
    # 
    file_path = file_path.replace("\\", "/")
    # ，
    if Path(file_path).is_absolute():
        return Path(file_path)
    # 
    return PROJECT_ROOT / file_path


def detect_file_format(file_path: Path) -> str:
    """"""
    if not file_path or not file_path.exists():
        return "unknown"
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        return "json"
    elif suffix == ".jsonl":
        return "jsonl"
    elif suffix in [".fasta", ".fa", ".fas"]:
        return "fasta"
    else:
        return "unknown"


def parse_json_file(file_path: Path, sample_size: int) -> tuple[bool, Optional[str], Optional[Any], str]:
    """JSON"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 
        if isinstance(data, dict):
            top_level_type = "dict"
            # dict，
            records = None
            for key in ["records", "data", "libraries", "templates", "scaffolds"]:
                if key in data and isinstance(data[key], list):
                    records = data[key]
                    break
            if records is None:
                # ，dict
                records = [data]
        elif isinstance(data, list):
            top_level_type = "list"
            records = data
        else:
            return False, f"Unsupported top-level type: {type(data)}", None, "unknown"
        
        # 
        sampled = records[:sample_size] if len(records) > sample_size else records
        
        return True, None, sampled, top_level_type
    except json.JSONDecodeError as e:
        return False, f"JSON decode error: {str(e)}", None, "unknown"
    except Exception as e:
        return False, f"Parse error: {str(e)}", None, "unknown"


def parse_jsonl_file(file_path: Path, sample_size: int) -> tuple[bool, Optional[str], Optional[List[Dict]], str]:
    """JSONL"""
    try:
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= sample_size:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError as e:
                    continue  # 
        
        return True, None, records, "jsonl_records"
    except Exception as e:
        return False, f"Parse error: {str(e)}", None, "unknown"


def parse_fasta_file(file_path: Path, sample_size: int) -> tuple[bool, Optional[str], Optional[List[Dict]], str]:
    """FASTA（，）"""
    try:
        records = []
        current_header = None
        current_sequence = ""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('>'):
                    # 
                    if current_header and current_sequence:
                        if len(records) < sample_size:
                            records.append({
                                "header": current_header,
                                "sequence_length": len(current_sequence),
                                "sequence": current_sequence[:50] + "..." if len(current_sequence) > 50 else current_sequence  # 50
                            })
                    # 
                    current_header = line[1:].strip()
                    current_sequence = ""
                else:
                    current_sequence += line
            
            # 
            if current_header and current_sequence:
                if len(records) < sample_size:
                    records.append({
                        "header": current_header,
                        "sequence_length": len(current_sequence),
                        "sequence": current_sequence[:50] + "..." if len(current_sequence) > 50 else current_sequence
                    })
        
        return True, None, records, "fasta_records"
    except Exception as e:
        return False, f"Parse error: {str(e)}", None, "unknown"


def extract_fields_from_record(record: Any, prefix: str = "") -> Set[str]:
    """"""
    fields = set()
    
    if isinstance(record, dict):
        for key, value in record.items():
            full_key = f"{prefix}.{key}" if prefix else key
            fields.add(full_key)
            # 
            if isinstance(value, dict):
                fields.update(extract_fields_from_record(value, full_key))
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # ，
                fields.update(extract_fields_from_record(value[0], full_key))
    elif isinstance(record, list) and record:
        # ，
        if isinstance(record[0], dict):
            fields.update(extract_fields_from_record(record[0], prefix))
    
    return fields


def detect_field_candidates(records: List[Dict], candidates: List[str]) -> List[str]:
    """"""
    found = []
    all_fields = set()
    
    for record in records:
        if isinstance(record, dict):
            fields = extract_fields_from_record(record)
            all_fields.update(fields)
    
    # （， "numbering.imgt"）
    for candidate in candidates:
        # 
        if candidate in all_fields:
            found.append(candidate)
        # （ "numbering.imgt"）
        for field in all_fields:
            if candidate in field.lower() or field.lower().endswith(f".{candidate}"):
                if field not in found:
                    found.append(field)
    
    return sorted(found)


def get_sequence_length(record: Any) -> Optional[int]:
    """"""
    if isinstance(record, dict):
        # 
        for field in SEQUENCE_FIELD_CANDIDATES:
            if field in record:
                seq = record[field]
                if isinstance(seq, str):
                    return len(seq)
        # 
        for key, value in record.items():
            if isinstance(value, dict):
                length = get_sequence_length(value)
                if length is not None:
                    return length
    return None


def get_record_id(record: Any) -> Optional[str]:
    """ID"""
    if isinstance(record, dict):
        for key in ["id", "name", "identifier", "template_id", "scaffold_id", "library_id"]:
            if key in record:
                return str(record[key])
        # 
        if "metadata" in record and isinstance(record["metadata"], dict):
            for key in ["id", "name", "identifier"]:
                if key in record["metadata"]:
                    return str(record["metadata"][key])
    elif isinstance(record, dict) and "header" in record:
        return record["header"]
    return None


def audit_library(library_id: str, file_path: Path, file_format: str, sample_size: int) -> Dict[str, Any]:
    """"""
    result = {
        "file_path": str(file_path),
        "format": file_format,
        "exists": file_path.exists() if file_path else False,
        "parse_success": False,
        "parse_error": None,
        "record_count_scanned": 0,
        "top_level_type": "unknown",
        "field_union": [],
        "field_frequency": {},
        "has_sequence_field": False,
        "sequence_field_candidates": [],
        "has_numbering": False,
        "numbering_field_candidates": [],
        "has_canonical_proxy": False,
        "canonical_proxy_field_candidates": [],
        "has_hallmark": False,
        "hallmark_field_candidates": [],
        "has_vernier": False,
        "vernier_field_candidates": [],
        "has_cluster_id": False,
        "cluster_field_candidates": [],
        "has_dual_numbering_map": False,
        "dual_numbering_field_candidates": [],
        "sample_records_slim": []
    }
    
    if not file_path or not file_path.exists():
        result["parse_error"] = "File not found"
        return result
    
    # 
    if file_format == "json":
        success, error, records, top_type = parse_json_file(file_path, sample_size)
    elif file_format == "jsonl":
        success, error, records, top_type = parse_jsonl_file(file_path, sample_size)
    elif file_format == "fasta":
        success, error, records, top_type = parse_fasta_file(file_path, sample_size)
    else:
        result["parse_error"] = f"Unsupported format: {file_format}"
        return result
    
    if not success:
        result["parse_error"] = error
        return result
    
    if not records:
        result["parse_error"] = "No records found"
        return result
    
    result["parse_success"] = True
    result["record_count_scanned"] = len(records)
    result["top_level_type"] = top_type
    
    # 
    all_fields = set()
    field_counter = Counter()
    
    for record in records:
        if isinstance(record, dict):
            fields = extract_fields_from_record(record)
            all_fields.update(fields)
            for field in fields:
                field_counter[field] += 1
    
    result["field_union"] = sorted(all_fields)
    result["field_frequency"] = dict(field_counter.most_common())
    
    # 
    if file_format != "fasta":
        # （）
        seq_candidates = detect_field_candidates(records, SEQUENCE_FIELD_CANDIDATES)
        #  consensus.framework_full
        has_consensus_framework_full = any("consensus.framework_full" in field for field in all_fields)
        #  consensus.fr1/fr2/fr3/fr4 
        has_fr1 = any("consensus.fr1" in field for field in all_fields)
        has_fr2 = any("consensus.fr2" in field for field in all_fields)
        has_fr3 = any("consensus.fr3" in field for field in all_fields)
        has_fr4 = any("consensus.fr4" in field for field in all_fields)
        has_all_fr_segments = has_fr1 and has_fr2 and has_fr3 and has_fr4
        
        if has_consensus_framework_full:
            seq_candidates.append("consensus.framework_full")
        if has_all_fr_segments:
            seq_candidates.extend(["consensus.fr1", "consensus.fr2", "consensus.fr3", "consensus.fr4"])
        
        result["sequence_field_candidates"] = sorted(set(seq_candidates))
        result["has_sequence_field"] = len(seq_candidates) > 0 or has_consensus_framework_full or has_all_fr_segments
        
        # 
        num_candidates = detect_field_candidates(records, NUMBERING_FIELD_CANDIDATES)
        result["numbering_field_candidates"] = num_candidates
        result["has_numbering"] = len(num_candidates) > 0
        
        # Canonical proxy
        canon_candidates = detect_field_candidates(records, CANONICAL_PROXY_FIELD_CANDIDATES)
        result["canonical_proxy_field_candidates"] = canon_candidates
        result["has_canonical_proxy"] = len(canon_candidates) > 0
        
        # Hallmark
        hallmark_candidates = detect_field_candidates(records, HALLMARK_FIELD_CANDIDATES)
        result["hallmark_field_candidates"] = hallmark_candidates
        result["has_hallmark"] = len(hallmark_candidates) > 0
        
        # Vernier
        vernier_candidates = detect_field_candidates(records, VERNIER_FIELD_CANDIDATES)
        result["vernier_field_candidates"] = vernier_candidates
        result["has_vernier"] = len(vernier_candidates) > 0
        
        # Cluster ID
        cluster_candidates = detect_field_candidates(records, CLUSTER_FIELD_CANDIDATES)
        result["cluster_field_candidates"] = cluster_candidates
        result["has_cluster_id"] = len(cluster_candidates) > 0
        
        # Dual numbering（）
        dual_num_candidates = detect_field_candidates(records, DUAL_NUMBERING_FIELD_CANDIDATES)
        #  imgt_map  kabat_map
        has_imgt_map = "imgt_map" in all_fields or any("imgt_map" in field for field in all_fields)
        has_kabat_map = "kabat_map" in all_fields or any("kabat_map" in field for field in all_fields)
        has_dual_via_maps = has_imgt_map and has_kabat_map
        
        if has_dual_via_maps:
            if "imgt_map" not in dual_num_candidates:
                dual_num_candidates.append("imgt_map")
            if "kabat_map" not in dual_num_candidates:
                dual_num_candidates.append("kabat_map")
        
        result["dual_numbering_field_candidates"] = sorted(set(dual_num_candidates))
        result["has_dual_numbering_map"] = len(dual_num_candidates) > 0 or has_dual_via_maps
    
    # （）
    for record in records[:2]:  # 2
        slim_record = {
            "keys": list(record.keys()) if isinstance(record, dict) else [],
            "sequence_len": get_sequence_length(record),
            "id": get_record_id(record)
        }
        result["sample_records_slim"].append(slim_record)
    
    return result


def generate_markdown_report(audit_result: Dict[str, Any]) -> str:
    """Markdown"""
    lines = []
    
    lines.append("# Schema Audit v1")
    lines.append("")
    lines.append(f"****: {audit_result['metadata']['generated_at']}")
    lines.append(f"****: {audit_result['metadata']['version']}")
    lines.append(f"****: {audit_result['metadata']['sample_size']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 
    lines.append("## 1. ")
    lines.append("")
    lines.append("| Library ID | Exists | Parse Success | Sample Size | Has Sequence | Has Numbering | Has Canonical Proxy | Has Hallmark | Has Vernier | Has Cluster ID | Has Dual Numbering |")
    lines.append("|-----------|--------|---------------|-------------|--------------|---------------|---------------------|--------------|-------------|----------------|-------------------|")
    
    for lib_id, lib_data in audit_result["libraries"].items():
        exists = "✓" if lib_data["exists"] else "✗"
        parse_success = "✓" if lib_data["parse_success"] else "✗"
        sample_size = lib_data["record_count_scanned"]
        has_seq = "✓" if lib_data["has_sequence_field"] else "✗"
        has_num = "✓" if lib_data["has_numbering"] else "✗"
        has_canon = "✓" if lib_data["has_canonical_proxy"] else "✗"
        has_hallmark = "✓" if lib_data["has_hallmark"] else "✗"
        has_vernier = "✓" if lib_data["has_vernier"] else "✗"
        has_cluster = "✓" if lib_data["has_cluster_id"] else "✗"
        has_dual = "✓" if lib_data["has_dual_numbering_map"] else "✗"
        
        lines.append(f"| {lib_id} | {exists} | {parse_success} | {sample_size} | {has_seq} | {has_num} | {has_canon} | {has_hallmark} | {has_vernier} | {has_cluster} | {has_dual} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 
    for lib_id, lib_data in audit_result["libraries"].items():
        lines.append(f"## 2. {lib_id}")
        lines.append("")
        lines.append(f"****: `{lib_data['file_path']}`")
        lines.append(f"****: {lib_data['format']}")
        lines.append(f"****: {'' if lib_data['exists'] else ''}")
        lines.append(f"****: {'' if lib_data['parse_success'] else ''}")
        
        if not lib_data["exists"]:
            lines.append(f"****: ")
            lines.append("")
            continue
        
        if not lib_data["parse_success"]:
            lines.append(f"****: {lib_data.get('parse_error', 'Unknown error')}")
            lines.append("")
            continue
        
        lines.append(f"****: {lib_data['record_count_scanned']}")
        lines.append(f"****: {lib_data['top_level_type']}")
        lines.append("")
        
        # （20）
        lines.append("### （20）")
        lines.append("")
        if lib_data["field_frequency"]:
            lines.append("|  |  |")
            lines.append("|--------|------|")
            for field, count in list(lib_data["field_frequency"].items())[:20]:
                lines.append(f"| `{field}` | {count} |")
        else:
            lines.append("")
        lines.append("")
        
        # 
        lines.append("### ")
        lines.append("")
        lines.append(f"- ****: {'' if lib_data['has_sequence_field'] else ''}")
        if lib_data["sequence_field_candidates"]:
            lines.append(f"  - : {', '.join(lib_data['sequence_field_candidates'])}")
        lines.append("")
        
        lines.append(f"- ****: {'' if lib_data['has_numbering'] else ''}")
        if lib_data["numbering_field_candidates"]:
            lines.append(f"  - : {', '.join(lib_data['numbering_field_candidates'])}")
        lines.append("")
        
        lines.append(f"- **Canonical Proxy**: {'' if lib_data['has_canonical_proxy'] else ''}")
        if lib_data["canonical_proxy_field_candidates"]:
            lines.append(f"  - : {', '.join(lib_data['canonical_proxy_field_candidates'])}")
        lines.append("")
        
        lines.append(f"- **Hallmark**: {'' if lib_data['has_hallmark'] else ''}")
        if lib_data["hallmark_field_candidates"]:
            lines.append(f"  - : {', '.join(lib_data['hallmark_field_candidates'])}")
        lines.append("")
        
        lines.append(f"- **Vernier Zone**: {'' if lib_data['has_vernier'] else ''}")
        if lib_data["vernier_field_candidates"]:
            lines.append(f"  - : {', '.join(lib_data['vernier_field_candidates'])}")
        lines.append("")
        
        lines.append(f"- **Cluster ID**: {'' if lib_data['has_cluster_id'] else ''}")
        if lib_data["cluster_field_candidates"]:
            lines.append(f"  - : {', '.join(lib_data['cluster_field_candidates'])}")
        lines.append("")
        
        lines.append(f"- **Dual Numbering Map**: {'' if lib_data['has_dual_numbering_map'] else ''}")
        if lib_data["dual_numbering_field_candidates"]:
            lines.append(f"  - : {', '.join(lib_data['dual_numbering_field_candidates'])}")
        lines.append("")
        
        # 
        lines.append("### （）")
        lines.append("")
        for i, sample in enumerate(lib_data["sample_records_slim"][:2], 1):
            lines.append(f"** {i}**:")
            lines.append(f"- Keys: {', '.join(sample['keys'][:10])}{' ...' if len(sample['keys']) > 10 else ''}")
            lines.append(f"- : {sample['sequence_len'] if sample['sequence_len'] else 'N/A'}")
            lines.append(f"- ID: {sample['id'] if sample['id'] else 'N/A'}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    lines.append(f"****: {audit_result['metadata']['generated_at']}")
    lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Schema Audit v1")
    parser.add_argument("--summary_json", type=Path, required=True,
                        help="Path to arsenal_summary_v1.json")
    parser.add_argument("--out_dir", type=Path, required=True,
                        help="Output directory")
    parser.add_argument("--sample_size", type=int, default=50,
                        help="Sample size for each library (default: 50)")
    
    args = parser.parse_args()
    
    # 
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # summary JSON
    summary_json_path = args.summary_json
    if not summary_json_path.is_absolute():
        summary_json_path = PROJECT_ROOT / summary_json_path
    
    # summary JSON
    print("🔍 arsenal summary...")
    with open(summary_json_path, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    # ID
    library_map = {}
    for lib_id, lib_data in summary.get("libraries", {}).items():
        if lib_id in TARGET_LIBRARY_IDS:
            file_path_str = lib_data.get("file_path", "")
            library_map[lib_id] = {
                "file_path": normalize_path(file_path_str),
                "format": lib_data.get("format", "unknown").lower()
            }
    
    # summary JSON
    summary_json_path = args.summary_json
    if not summary_json_path.is_absolute():
        summary_json_path = PROJECT_ROOT / summary_json_path
    
    # （metadata）
    try:
        source_summary_rel = str(summary_json_path.relative_to(PROJECT_ROOT))
    except ValueError:
        source_summary_rel = str(summary_json_path)
    
    # 
    audit_result = {
        "metadata": {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "sample_size": args.sample_size,
            "source_summary": source_summary_rel
        },
        "libraries": {}
    }
    
    # 
    print(f"📊  {len(TARGET_LIBRARY_IDS)} ...")
    for lib_id in TARGET_LIBRARY_IDS:
        print(f"  : {lib_id}")
        if lib_id not in library_map:
            print(f"    ⚠️  :  {lib_id} summary")
            audit_result["libraries"][lib_id] = {
                "file_path": "unknown",
                "format": "unknown",
                "exists": False,
                "parse_success": False,
                "parse_error": "Library not found in summary"
            }
            continue
        
        lib_info = library_map[lib_id]
        file_path = lib_info["file_path"]
        file_format = lib_info["format"] or detect_file_format(file_path)
        
        result = audit_library(lib_id, file_path, file_format, args.sample_size)
        audit_result["libraries"][lib_id] = result
        
        if result["exists"] and result["parse_success"]:
            print(f"    ✅ :  {result['record_count_scanned']} ")
        elif not result["exists"]:
            print(f"    ❌ : {file_path}")
        else:
            print(f"    ❌ : {result.get('parse_error', 'Unknown')}")
    
    # JSON
    json_path = args.out_dir / "schema_audit_v1.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(audit_result, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON: {json_path}")
    
    # MD
    md_path = args.out_dir / "schema_audit_v1.md"
    md_content = generate_markdown_report(audit_result)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"✅ Markdown: {md_path}")
    
    # 
    print(f"\n📊 :")
    for lib_id, lib_data in audit_result["libraries"].items():
        status = "✅" if lib_data.get("parse_success") else "❌"
        print(f"  {status} {lib_id}: {lib_data.get('record_count_scanned', 0)} ")
    print(f"\n✅ ！")


if __name__ == "__main__":
    main()

