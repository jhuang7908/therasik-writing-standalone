#!/usr/bin/env python3
"""
Library Loader Diagnostic Tool

"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter
import sys

# 
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# （）
SEQUENCE_FIELD_CANDIDATES = [
    "sequence",
    "aa_sequence",
    "sequence_aa",  # IMGT
    "v_sequence",
    "seq",
    "aa",
    "consensus.framework_full",
    "fr_sequence",
    "consensus.fr1",
    "consensus.fr2",
    "consensus.fr3",
    "consensus.fr4",
]


def extract_all_keys(record: Any, prefix: str = "") -> List[str]:
    """"""
    keys = []
    
    if isinstance(record, dict):
        for key, value in record.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.append(full_key)
            # 
            if isinstance(value, dict):
                keys.extend(extract_all_keys(value, full_key))
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # ，
                keys.extend(extract_all_keys(value[0], full_key))
    elif isinstance(record, list) and record:
        # ，
        if isinstance(record[0], dict):
            keys.extend(extract_all_keys(record[0], prefix))
    
    return keys


def get_nested_value(record: Dict[str, Any], key_path: str) -> Any:
    """（）"""
    keys = key_path.split(".")
    value = record
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value


def extract_sequence(record: Dict[str, Any], candidates: List[str]) -> Optional[Tuple[str, str]]:
    """（）"""
    for candidate in candidates:
        value = get_nested_value(record, candidate)
        if value and isinstance(value, str) and len(value) > 0:
            # （）
            if any(aa in value.upper() for aa in "ACDEFGHIKLMNPQRSTVWY"):
                return (candidate, value)
    
    # ，consensus.fr1-4
    if "consensus" in record and isinstance(record["consensus"], dict):
        fr_parts = []
        for fr in ["fr1", "fr2", "fr3", "fr4"]:
            if fr in record["consensus"]:
                part = record["consensus"][fr]
                if isinstance(part, str) and part:
                    fr_parts.append(part)
        if len(fr_parts) == 4:
            return ("consensus.fr1+fr2+fr3+fr4", "".join(fr_parts))
    
    return None


def load_library(lib_path: Path, lib_format: str) -> Tuple[str, List[Dict[str, Any]]]:
    """，(, )"""
    records = []
    top_level_type = "unknown"
    
    if not lib_path.exists():
        return top_level_type, records
    
    try:
        if lib_format.lower() == "jsonl":
            top_level_type = "jsonl"
            with open(lib_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if isinstance(record, dict):
                            records.append(record)
                    except json.JSONDecodeError:
                        continue
        elif lib_format.lower() in ["json", "amino_acid"]:
            with open(lib_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    top_level_type = "list"
                    records = data
                elif isinstance(data, dict):
                    top_level_type = "dict"
                    # 
                    for key in ["entries", "records", "data", "libraries", "templates", "scaffolds", "sequences"]:
                        if key in data and isinstance(data[key], list):
                            records = data[key]
                            break
                    if not records:
                        records = [data]
        elif lib_format.lower() in ["fasta", "fa", "fas"]:
            top_level_type = "fasta"
            # FASTA
            pass
    except Exception as e:
        print(f"⚠️  : {e}")
    
    return top_level_type, records


def diagnose_library(library_id: str, summary: Dict[str, Any]) -> Dict[str, Any]:
    """"""
    result = {
        "library_id": library_id,
        "file_path": None,
        "exists": False,
        "file_size": 0,
        "top_level_type": "unknown",
        "sample_records": [],
        "field_candidates_hit_rate": {},
        "n_records_total": 0,
        "n_sequences_extracted": 0,
        "top_sequence_key": None
    }
    
    # 
    if library_id not in summary.get("libraries", {}):
        print(f"❌  {library_id} summary")
        return result
    
    lib_data = summary["libraries"][library_id]
    file_path_str = lib_data.get("file_path", "")
    lib_format = lib_data.get("format", "unknown")
    
    # 
    if not file_path_str:
        print(f"❌  {library_id} file_path")
        return result
    
    file_path = PROJECT_ROOT / file_path_str
    result["file_path"] = str(file_path)
    result["exists"] = file_path.exists()
    
    if not result["exists"]:
        print(f"❌ : {file_path}")
        return result
    
    # 
    result["file_size"] = file_path.stat().st_size
    
    # 
    top_level_type, records = load_library(file_path, lib_format)
    result["top_level_type"] = top_level_type
    result["n_records_total"] = len(records)
    
    if not records:
        print(f"⚠️  ")
        return result
    
    # 5
    sample_records = records[:5]
    for i, record in enumerate(sample_records, 1):
        if isinstance(record, dict):
            keys = extract_all_keys(record)
            result["sample_records"].append({
                "index": i,
                "keys": sorted(set(keys))[:20]  # 20keys
            })
    
    # 
    candidate_hits = Counter()
    sequence_extractions = []
    
    for record in records:
        if not isinstance(record, dict):
            continue
        
        seq_result = extract_sequence(record, SEQUENCE_FIELD_CANDIDATES)
        if seq_result:
            candidate_key, seq_value = seq_result
            candidate_hits[candidate_key] += 1
            sequence_extractions.append({
                "key": candidate_key,
                "length": len(seq_value)
            })
    
    # 
    for candidate in SEQUENCE_FIELD_CANDIDATES:
        hit_count = candidate_hits.get(candidate, 0)
        hit_rate = hit_count / len(records) if records else 0.0
        result["field_candidates_hit_rate"][candidate] = {
            "hits": hit_count,
            "rate": hit_rate
        }
    
    result["n_sequences_extracted"] = len(sequence_extractions)
    
    # 
    if sequence_extractions:
        top_key_counter = Counter(ext["key"] for ext in sequence_extractions)
        result["top_sequence_key"] = top_key_counter.most_common(1)[0][0]
    
    return result


def print_diagnosis(result: Dict[str, Any]):
    """"""
    print(f"\n{'='*60}")
    print(f": {result['library_id']}")
    print(f"{'='*60}")
    
    print(f"\n📁 :")
    print(f"  : {result['file_path']}")
    print(f"  : {'✓' if result['exists'] else '✗'}")
    if result['exists']:
        file_size_mb = result['file_size'] / (1024 * 1024)
        print(f"  : {file_size_mb:.2f} MB ({result['file_size']:,} bytes)")
    print(f"  : {result['top_level_type']}")
    
    print(f"\n📊 :")
    print(f"  : {result['n_records_total']:,}")
    print(f"  : {result['n_sequences_extracted']:,}")
    if result['top_sequence_key']:
        print(f"  : {result['top_sequence_key']}")
    
    if result['sample_records']:
        print(f"\n🔍  (5):")
        for sample in result['sample_records']:
            print(f"   #{sample['index']}:")
            keys = sample['keys']
            print(f"    Keys ({len(keys)}): {', '.join(keys[:10])}{' ...' if len(keys) > 10 else ''}")
    
    print(f"\n🧬 :")
    print(f"  {'':<30} {'':<10} {'':<10}")
    print(f"  {'-'*30} {'-'*10} {'-'*10}")
    for candidate, stats in result['field_candidates_hit_rate'].items():
        hits = stats['hits']
        rate = stats['rate']
        if hits > 0:
            print(f"  {candidate:<30} {hits:<10} {rate:.1%}")
    
    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Library Loader Diagnostic Tool")
    parser.add_argument("--library_id", type=str, required=True,
                        help="Library ID (e.g., human_IGKV)")
    parser.add_argument("--summary_json", type=Path, required=True,
                        help="Path to arsenal_summary_v1.json")
    
    args = parser.parse_args()
    
    # summary
    print(f"🔍 arsenal summary...")
    with open(args.summary_json, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    # 
    result = diagnose_library(args.library_id, summary)
    
    # 
    print_diagnosis(result)
    
    # JSON
    summary_output = {
        "library_id": result["library_id"],
        "n_records_total": result["n_records_total"],
        "n_sequences_extracted": result["n_sequences_extracted"],
        "top_sequence_key": result["top_sequence_key"],
        "file_exists": result["exists"],
        "top_level_type": result["top_level_type"]
    }
    
    print("📋 JSON:")
    print(json.dumps(summary_output, indent=2, ensure_ascii=False))
    print()


if __name__ == "__main__":
    main()

