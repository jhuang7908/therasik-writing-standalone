#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/canonical_pipeline.py

Reproducible pipeline for canonical structure analysis of framework library and therapeutics.

Commands:
1. export-lib: Export VH/VL canonical input sequences from YAML library to FASTA.
2. export-thera: Export Thera-SAbDab sequences (from CSV) to FASTA for canonical tools.
3. update-lib: Parse canonical tool output (e.g. SCALOP CSV) and update YAML library.
4. report-comparison: Compare canonical distributions between library and therapeutics.
"""

import sys
import os
import yaml
import hashlib
import uuid
import argparse
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.append(str(PROJECT_ROOT))

# Try to import core components
try:
    from core.numbering.anarcii_adapter import get_engine_info, _get_anarcii_obj
    from core.vhh_humanization import split_regions
except ImportError:
    print("Warning: Core components not found. Some numbering features may be disabled.")

PIPELINE_VERSION = "1.0.0"

def get_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_") + str(uuid.uuid4())[:8]

def get_file_hash(path: Path) -> str:
    if not path or not Path(path).exists():
        return "not_found"
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def load_yaml(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def write_yaml(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

def export_lib_cmd(args):
    vh_yaml = Path(args.vh_yaml)
    vl_yaml = Path(args.vl_yaml)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    run_id = get_run_id()
    vh_fasta = output_dir / f"vh_lib_canonical_input_{run_id}.fasta"
    vl_fasta = output_dir / f"vl_lib_canonical_input_{run_id}.fasta"
    
    vh_data = load_yaml(vh_yaml)
    vl_data = load_yaml(vl_yaml)
    
    def write_fasta(data, path, chain):
        count = 0
        with open(path, 'w', encoding='utf-8') as f:
            for entry in data.get('frameworks', []):
                fid = entry.get('framework_id')
                ci = entry.get('canonical_input', {})
                seq = ci.get('sequence_ungapped')
                if not fid or not seq:
                    # Fail-fast
                    raise ValueError(f"CRITICAL: Missing framework_id or canonical_input.sequence_ungapped for an entry in {chain} YAML")
                f.write(f">{fid}\n{seq}\n")
                count += 1
        return count

    vh_count = write_fasta(vh_data, vh_fasta, "VH")
    vl_count = write_fasta(vl_data, vl_fasta, "VL")
    
    meta = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "version": PIPELINE_VERSION,
        "vh_input_hash": get_file_hash(vh_yaml),
        "vl_input_hash": get_file_hash(vl_yaml),
        "vh_output": str(vh_fasta),
        "vl_output": str(vl_fasta)
    }
    write_yaml(output_dir / f"export_lib_meta_{run_id}.yaml", meta)
    
    print(f"✅ Exported {vh_count} VH frameworks to {vh_fasta}")
    print(f"✅ Exported {vl_count} VL frameworks to {vl_fasta}")

def export_thera_cmd(args):
    csv_path = Path(args.csv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    run_id = get_run_id()
    df = pd.read_csv(csv_path)
    
    # Required columns: Therapeutic, Heavy Chain, Light Chain
    required = ["Therapeutic", "Heavy Chain", "Light Chain"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"CRITICAL: Missing required column '{col}' in {csv_path}")

    vh_fasta = output_dir / f"thera_vh_{run_id}.fasta"
    vl_fasta = output_dir / f"thera_vl_{run_id}.fasta"
    
    vh_count = 0
    vl_count = 0
    
    with open(vh_fasta, 'w', encoding='utf-8') as fvh, open(vl_fasta, 'w', encoding='utf-8') as fvl:
        for idx, row in df.iterrows():
            name = str(row["Therapeutic"]).replace(" ", "_")
            vh_seq = str(row["Heavy Chain"]).strip()
            vl_seq = str(row["Light Chain"]).strip()
            
            if vh_seq and vh_seq.upper() != "NAN":
                fvh.write(f">{name}_VH\n{vh_seq}\n")
                vh_count += 1
            if vl_seq and vl_seq.upper() != "NAN":
                fvl.write(f">{name}_VL\n{vl_seq}\n")
                vl_count += 1
                
    meta = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "input_csv": str(csv_path),
        "input_hash": get_file_hash(csv_path),
        "vh_output": str(vh_fasta),
        "vl_output": str(vl_fasta)
    }
    write_yaml(output_dir / f"export_thera_meta_{run_id}.yaml", meta)
    
    print(f"✅ Exported {vh_count} Thera-VH to {vh_fasta}")
    print(f"✅ Exported {vl_count} Thera-VL to {vl_fasta}")

def update_lib_cmd(args):
    vh_yaml = Path(args.vh_yaml)
    vl_yaml = Path(args.vl_yaml)
    tool_csv = Path(args.tool_csv)
    
    if not tool_csv.exists():
        raise FileNotFoundError(f"Tool output CSV not found: {tool_csv}")
        
    df = pd.read_csv(tool_csv)
    # Expected: id, H1, H2 (or L1, L2)
    # We'll use id as key.
    results = df.set_index(df.columns[0]).to_dict('index')
    
    vh_data = load_yaml(vh_yaml)
    vl_data = load_yaml(vl_yaml)
    
    def update_entries(data, chain_type):
        updated = 0
        for entry in data.get('frameworks', []):
            fid = entry.get('framework_id')
            if fid in results:
                res = results[fid]
                if 'canonical' not in entry or entry.get('canonical') in (None, "", "TODO", "PROXY", "PENDING"):
                    entry['canonical'] = {
                        'cdr1': {'length_mode': 'TODO', 'length_range': 'TODO', 'class': 'TODO'},
                        'cdr2': {'length_mode': 'TODO', 'length_range': 'TODO', 'class': 'TODO'}
                    }
                
                # Mapping logic: look for H1/H2 or L1/L2 or generic cdr1/cdr2
                c1 = res.get('H1') or res.get('L1') or res.get('cdr1')
                c2 = res.get('H2') or res.get('L2') or res.get('cdr2')
                
                if c1 and str(c1).upper() not in ("TODO", "PROXY", "PENDING", "NAN"):
                    entry['canonical']['cdr1']['class'] = str(c1)
                if c2 and str(c2).upper() not in ("TODO", "PROXY", "PENDING", "NAN"):
                    entry['canonical']['cdr2']['class'] = str(c2)
                updated += 1
        return updated

    vhu = update_entries(vh_data, "VH")
    vlu = update_entries(vl_data, "VL")
    
    if args.inplace:
        write_yaml(vh_yaml, vh_data)
        write_yaml(vl_yaml, vl_data)
        print(f"✅ In-place update: {vhu} VH, {vlu} VL.")
    else:
        run_id = get_run_id()
        out_vh = vh_yaml.parent / f"{vh_yaml.stem}_updated_{run_id}.yaml"
        out_vl = vl_yaml.parent / f"{vl_yaml.stem}_updated_{run_id}.yaml"
        write_yaml(out_vh, vh_data)
        write_yaml(out_vl, vl_data)
        print(f"✅ Created updated YAMLs: {out_vh}, {out_vl}")

def report_comparison_cmd(args):
    lib_results = Path(args.lib_tool_csv)
    thera_results = Path(args.thera_tool_csv)
    output_md = Path(args.output or f"canonical_comparison_report_{get_run_id()}.md")
    
    df_lib = pd.read_csv(lib_results)
    df_thera = pd.read_csv(thera_results)
    
    def get_dist(df, col):
        if col not in df.columns: return pd.Series()
        return df[col].value_counts(normalize=True) * 100

    # Strong comparison for H1, H2, L1, L2
    regions = ["H1", "H2", "L1", "L2"]
    
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write("# Antibody Canonical Structure Distribution Report\n\n")
        f.write(f"- Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- Lib Results: `{lib_results.name}` (hash: {get_file_hash(lib_results)})\n")
        f.write(f"- Thera Results: `{thera_results.name}` (hash: {get_file_hash(thera_results)})\n\n")
        
        for reg in regions:
            dist_lib = get_dist(df_lib, reg)
            dist_thera = get_dist(df_thera, reg)
            
            f.write(f"## {reg} Distribution Comparison\n\n")
            f.write("| Class | Library % | Thera-SAbDab % | Diff |\n")
            f.write("| --- | --- | --- | --- |\n")
            
            all_classes = sorted(list(set(dist_lib.index) | set(dist_thera.index)))
            for cls in all_classes:
                p_lib = dist_lib.get(cls, 0)
                p_thera = dist_thera.get(cls, 0)
                f.write(f"| {cls} | {p_lib:.1f}% | {p_thera:.1f}% | {p_lib-p_thera:+.1f}% |\n")
            f.write("\n")
            
        f.write("## Notes\n")
        f.write("- L3 is marked as CAUTION due to high diversity.\n")
        f.write("- H3 is excluded from canonical structure classification.\n")

    print(f"✅ Comparison report saved to {output_md}")

def main():
    parser = argparse.ArgumentParser(description="Canonical Pipeline for Antibody Engineer Suite")
    subparsers = parser.add_subparsers(dest="command")
    
    # export-lib
    p1 = subparsers.add_parser("export-lib", help="Export library frameworks to FASTA")
    p1.add_argument("--vh-yaml", default="core/data/framework_library/vh_frameworks.with_cdr12.canonical_input.yaml")
    p1.add_argument("--vl-yaml", default="core/data/framework_library/vl_frameworks.with_cdr12.canonical_input.yaml")
    p1.add_argument("--output-dir", default="output/canonical_input")
    
    # export-thera
    p2 = subparsers.add_parser("export-thera", help="Export Thera-SAbDab CSV to FASTA")
    p2.add_argument("--csv", required=True, help="Thera-SAbDab CSV file")
    p2.add_argument("--output-dir", default="output/thera_input")
    
    # update-lib
    p3 = subparsers.add_parser("update-lib", help="Update library YAML from tool output")
    p3.add_argument("--tool-csv", required=True, help="Canonical tool output CSV")
    p3.add_argument("--vh-yaml", default="core/data/framework_library/vh_frameworks.yaml")
    p3.add_argument("--vl-yaml", default="core/data/framework_library/vl_frameworks.yaml")
    p3.add_argument("--inplace", action="store_true")
    
    # report-comparison
    p4 = subparsers.add_parser("report-comparison", help="Generate comparison report")
    p4.add_argument("--lib-tool-csv", required=True)
    p4.add_argument("--thera-tool-csv", required=True)
    p4.add_argument("--output", help="Output MD file path")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
        
    try:
        if args.command == "export-lib":
            export_lib_cmd(args)
        elif args.command == "export-thera":
            export_thera_cmd(args)
        elif args.command == "update-lib":
            update_lib_cmd(args)
        elif args.command == "report-comparison":
            report_comparison_cmd(args)
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
