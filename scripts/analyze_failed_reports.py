#!/usr/bin/env python3
"""

"""

import json
import glob
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def analyze_json_structure(json_path: Path) -> Dict[str, Any]:
    """JSON，"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    analysis = {
        "file": str(json_path),
        "has_input": "input" in data,
        "has_input_sequence": False,
        "has_input_sequence_path": False,
        "input_keys": [],
        "sequence_sources": [],
        "error": data.get("error"),
        "status": data.get("status"),
        "success": data.get("success"),
        "best_match": data.get("best_match") is not None,
        "candidates": len(data.get("candidates", [])),
    }
    
    # input
    if "input" in data:
        input_data = data["input"]
        analysis["input_keys"] = list(input_data.keys())
        
        # 
        sequence_paths = [
            ("input.sequence", input_data.get("sequence")),
            ("input_sequence", data.get("input_sequence")),
            ("sequence", data.get("sequence")),
            ("input.sequence_data", input_data.get("sequence_data")),
        ]
        
        for path, value in sequence_paths:
            if value:
                analysis["sequence_sources"].append(path)
                if path == "input.sequence":
                    analysis["has_input_sequence"] = True
                if "sequence" in path:
                    analysis["has_input_sequence_path"] = True
    
    return analysis


def main():
    """"""
    print("=" * 80)
    print("")
    print("=" * 80)
    
    # JSON
    json_files = []
    for pattern in [
        "**/result_20251217_*.json",
        "**/result_VH_20251217_*.json",
        "**/result_VL_20251217_*.json",
        "projects/**/output/result.json",
    ]:
        json_files.extend(glob.glob(pattern, recursive=True))
    
    json_files = sorted(set(json_files))
    
    print(f"\n {len(json_files)} JSON\n")
    
    # 
    failed_files = []
    success_files = []
    
    for json_path in json_files:
        json_path = Path(json_path)
        if not json_path.exists():
            continue
        
        analysis = analyze_json_structure(json_path)
        
        # 
        will_fail = False
        failure_reasons = []
        
        if not analysis["has_input_sequence"]:
            if not analysis["sequence_sources"]:
                will_fail = True
                failure_reasons.append("")
        
        if analysis["error"]:
            failure_reasons.append(f": {analysis['error']}")
        
        if will_fail or analysis["error"]:
            failed_files.append((json_path, analysis, failure_reasons))
        else:
            success_files.append((json_path, analysis))
    
    # 
    print("=" * 80)
    print("")
    print("=" * 80)
    
    if not failed_files:
        print("\n✅ ")
    else:
        print(f"\n {len(failed_files)} :\n")
        
        for json_path, analysis, reasons in failed_files:
            print(f": {json_path}")
            print(f"  : {analysis['status']} | : {analysis['success']}")
            print(f"  : {analysis['error'] or 'N/A'}")
            print(f"  : {', '.join(reasons)}")
            print(f"  : {analysis['input_keys']}")
            print(f"  : {analysis['sequence_sources'] or ''}")
            print(f"  best_match: {'' if analysis['best_match'] else ''}")
            print(f"  candidates: {analysis['candidates']}")
            print()
    
    # 
    print("=" * 80)
    print("")
    print("=" * 80)
    print(f"\n: {len(success_files)}")
    
    if success_files:
        print("\n5:")
        for json_path, analysis in success_files[:5]:
            print(f"  - {json_path}")
            print(f"    : {analysis['sequence_sources']}")
            print(f"    best_match: {'' if analysis['best_match'] else ''}")
            print(f"    candidates: {analysis['candidates']}")
    
    # 
    print("\n" + "=" * 80)
    print("")
    print("=" * 80)
    print(f": {len(json_files)}")
    print(f": {len(failed_files)}")
    print(f": {len(success_files)}")
    
    # 
    if failed_files:
        print("\n:")
        error_types = {}
        for _, _, reasons in failed_files:
            for reason in reasons:
                error_types[reason] = error_types.get(reason, 0) + 1
        
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {error_type}: {count} ")
    
    print("=" * 80)


if __name__ == "__main__":
    main()




