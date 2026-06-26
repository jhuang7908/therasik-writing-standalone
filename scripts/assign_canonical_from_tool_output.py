#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/assign_canonical_from_tool_output.py

Parses canonical tool output (TSV) and updates framework YAML files.
"""

import sys
import os
import yaml
import json
import hashlib
import argparse
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]

def get_file_hash(path: Path) -> str:
    if not path or not path.exists():
        return "not_found"
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def load_yaml(path: Path) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def write_yaml(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

def parse_tsv_results(tsv_path: Path, valid_framework_ids: Set[str]) -> Tuple[Dict[str, Dict[str, Dict[str, str]]], List[str]]:
    """
    Parses TSV and returns a nested dict: {framework_id: {cdr_name: {class: ..., confidence: ...}}}
    Also returns list of unknown_ids (ids in TSV but not in valid_framework_ids).
    
    P0 Contract: TSV must have exactly 4 columns: id, cdr, class, confidence.
    """
    if not tsv_path.exists():
        return {}, []
    
    # P0: Required columns = 4 (minimal contract)
    df = pd.read_csv(tsv_path, sep='\t')
    required = ["id", "cdr", "class", "confidence"]
    for col in required:
        if col not in df.columns:
            raise RuntimeError(f"CRITICAL: TSV {tsv_path.name} missing required column: {col}. Minimal contract requires: {required}")
            
    results = {}
    unknown_ids = []
    seen_ids = set()
    
    for _, row in df.iterrows():
        # id is framework_id (first part of header, normalized)
        full_id = str(row['id']).split('|')[0].strip()
        if not full_id:
            continue  # Skip empty IDs
            
        # Track unknown IDs (fail-fast check)
        if full_id not in valid_framework_ids and full_id not in seen_ids:
            unknown_ids.append(full_id)
        seen_ids.add(full_id)
        
        cdr = str(row['cdr']).upper()
        cls = str(row['class'])
        # P0: confidence column must exist, but cell can be empty/NaN -> "unknown"
        conf_val = row['confidence']
        if pd.isna(conf_val) or str(conf_val).strip() == '':
            conf = "unknown"
        else:
            conf = str(conf_val)
        
        if full_id not in results:
            results[full_id] = {}
        
        results[full_id][cdr] = {
            "class": cls,
            "confidence": conf
        }
    
    return results, unknown_ids

def process_chain(yaml_path: Path, tsv_results: Dict[str, Dict[str, Dict[str, str]]], 
                  chain: str, tool_meta: Dict[str, str], audit: Dict[str, Any]) -> List[Dict[str, Any]]:
    
    data = load_yaml(yaml_path)
    frameworks = data.get('frameworks', [])
    updated_frameworks = []
    
    # CDR mapping
    cdr1_key = "H1" if chain == "VH" else "L1"
    cdr2_key = "H2" if chain == "VH" else "L2"
    cdr3_key = "H3" if chain == "VH" else "L3"
    
    missing_required_cdrs = []
    
    for entry in frameworks:
        fw_id = entry.get('framework_id')
        
        # P0: framework_id missing/empty -> fail-fast
        if not fw_id or str(fw_id).strip() == '':
            raise RuntimeError(f"CRITICAL: Entry in {yaml_path.name} has missing or empty 'framework_id'. Library corruption detected.")
        
        res = tsv_results.get(fw_id, {})
        
        # Initialize canonical block
        entry['canonical'] = {
            "scheme": "North",
            "status": "ASSIGNED_BY_TOOL",
            "tool": tool_meta,
            "notes": {
                "synthetic_cdr3_placeholder": True
            }
        }
        
        # Check required CDRs
        missing = []
        if cdr1_key not in res: missing.append(cdr1_key)
        if cdr2_key not in res: missing.append(cdr2_key)
        
        if missing:
            entry['canonical']['status'] = "FAILED"
            reason = f"Missing results for: {', '.join(missing)}"
            entry['canonical']['error'] = {"reason": reason}
            audit['failures'].append({
                "framework_id": fw_id,
                "reason": reason,
                "status": "FAILED"
            })
            missing_required_cdrs.append({
                "framework_id": fw_id,
                "missing_cdrs": missing
            })
            audit['overall_success'] = False
        else:
            entry['canonical']['cdr1'] = res[cdr1_key]
            entry['canonical']['cdr2'] = res[cdr2_key]
            
            # Optional L3/H3
            if cdr3_key in res:
                if 'cdr3' not in entry['canonical']:
                    entry['canonical']['cdr3'] = {}
                entry['canonical']['cdr3']['class'] = res[cdr3_key]['class']
            
            audit['success_count'] += 1
            
        updated_frameworks.append(entry)
        audit['total_count'] += 1
    
    # Append missing_required_cdrs to audit (merge with existing)
    if 'missing_required_cdrs' not in audit:
        audit['missing_required_cdrs'] = []
    audit['missing_required_cdrs'].extend(missing_required_cdrs)
        
    return updated_frameworks

def main():
    parser = argparse.ArgumentParser(description="Assign canonical classes from tool output to YAML library")
    parser.add_argument("--vh_yaml", required=True)
    parser.add_argument("--vl_yaml", required=True)
    parser.add_argument("--vh_tsv", required=True)
    parser.add_argument("--vl_tsv", required=True)
    parser.add_argument("--tool_name", required=True)
    parser.add_argument("--tool_version", required=True)
    parser.add_argument("--run_id", default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--out_dir", help="Output directory for assigned YAMLs and audit")
    
    args = parser.parse_args()
    
    run_id = args.run_id
    tool_meta = {
        "name": args.tool_name,
        "version": args.tool_version,
        "run_id": run_id
    }
    
    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = PROJECT_ROOT / "output" / "framework_library" / "canonical"
    
    out_dir.mkdir(parents=True, exist_ok=True)
    
    audit = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_meta,
        "inputs": {
            "vh_yaml": str(args.vh_yaml),
            "vh_yaml_hash": get_file_hash(Path(args.vh_yaml)),
            "vl_yaml": str(args.vl_yaml),
            "vl_yaml_hash": get_file_hash(Path(args.vl_yaml)),
            "vh_tsv": str(args.vh_tsv),
            "vh_tsv_hash": get_file_hash(Path(args.vh_tsv)),
            "vl_tsv": str(args.vl_tsv),
            "vl_tsv_hash": get_file_hash(Path(args.vl_tsv))
        },
        "total_count": 0,
        "success_count": 0,
        "failures": [],
        "overall_success": True,
        "unknown_ids": [],  # P0: TSV ids not found in YAML
        "missing_required_cdrs": []  # P0: Frameworks missing H1/H2 or L1/L2
    }
    
    try:
        # Load YAMLs to get valid framework_ids (for unknown_id detection)
        vh_data = load_yaml(Path(args.vh_yaml))
        vl_data = load_yaml(Path(args.vl_yaml))
        valid_vh_ids = {entry.get('framework_id') for entry in vh_data.get('frameworks', []) if entry.get('framework_id')}
        valid_vl_ids = {entry.get('framework_id') for entry in vl_data.get('frameworks', []) if entry.get('framework_id')}
        
        # Parse TSVs (with unknown_id detection)
        vh_results, vh_unknown_ids = parse_tsv_results(Path(args.vh_tsv), valid_vh_ids)
        vl_results, vl_unknown_ids = parse_tsv_results(Path(args.vl_tsv), valid_vl_ids)
        
        # P0: Fail-fast on unknown_ids
        all_unknown_ids = list(set(vh_unknown_ids + vl_unknown_ids))
        if all_unknown_ids:
            preview = all_unknown_ids[:20]
            preview_str = ', '.join(preview)
            total_count = len(all_unknown_ids)
            raise RuntimeError(
                f"CRITICAL: TSV contains {total_count} unknown framework_id(s) not found in YAML. "
                f"First 20: {preview_str}. "
                f"TSV file(s): {Path(args.vh_tsv).name}, {Path(args.vl_tsv).name}"
            )
        
        # Store in audit (even if empty)
        audit['unknown_ids'] = all_unknown_ids
        
        # Process VH
        vh_updated = process_chain(Path(args.vh_yaml), vh_results, "VH", tool_meta, audit)
        write_yaml(out_dir / "vh_frameworks.canonical_assigned.yaml", {"frameworks": vh_updated})
        
        # Process VL
        vl_updated = process_chain(Path(args.vl_yaml), vl_results, "VL", tool_meta, audit)
        write_yaml(out_dir / "vl_frameworks.canonical_assigned.yaml", {"frameworks": vl_updated})
        
        # Write Audit
        audit_path = out_dir / "assign_canonical_audit.json"
        with open(audit_path, 'w', encoding='utf-8') as f:
            json.dump(audit, f, indent=2)
            
        if not audit['overall_success']:
            print(f"❌ Completed with failures. See audit: {audit_path}")
            sys.exit(1)
            
        print(f"✅ Successfully updated {audit['success_count']}/{audit['total_count']} entries.")
        print(f"✅ Outputs in {out_dir}")
        
    except Exception as e:
        print(f"❌ FATAL ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
