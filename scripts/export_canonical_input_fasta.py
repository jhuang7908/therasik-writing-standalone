#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/export_canonical_input_fasta.py

Exports VH and VL frameworks from YAML to FASTA for canonical structure tools.
Header format: >{framework_id}|{germline}|{chain_type}
Sequence: canonical_input.sequence_ungapped
"""

import sys
import yaml
import argparse
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]

def export_fasta(yaml_path: Path, output_path: Path, chain_type: str):
    """
    Reads a framework YAML and writes a FASTA file.
    """
    if not yaml_path.exists():
        print(f"Warning: Input YAML not found: {yaml_path}")
        return 0

    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    frameworks = data.get('frameworks', [])
    count = 0
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in frameworks:
            fw_id = entry.get('framework_id')
            germline = entry.get('germline')
            canonical_input = entry.get('canonical_input')
            
            if not canonical_input or 'sequence_ungapped' not in canonical_input:
                raise RuntimeError(f"CRITICAL: Entry {fw_id} is missing 'canonical_input.sequence_ungapped'")
            
            seq = canonical_input['sequence_ungapped']
            
            # Acceptance criteria: length > 90
            if len(seq) <= 90:
                print(f"Warning: Sequence for {fw_id} is too short ({len(seq)} aa), expected > 90 aa.")
            
            # Header: >{framework_id}|{germline}|{chain_type}
            header = f">{fw_id}|{germline}|{chain_type}"
            f.write(f"{header}\n{seq}\n")
            count += 1
            
    if count != len(frameworks):
        raise RuntimeError(f"Mismatch: YAML has {len(frameworks)} entries but only {count} were exported to FASTA.")
    
    return count

def main():
    parser = argparse.ArgumentParser(description="Export VH/VL frameworks to FASTA for canonical tools")
    parser.add_argument("--vh_yaml", help="Path to VH framework YAML")
    parser.add_argument("--vl_yaml", help="Path to VL framework YAML")
    parser.add_argument("--out_dir", help="Output directory for FASTA files")
    
    args = parser.parse_args()

    vh_input = Path(args.vh_yaml) if args.vh_yaml else PROJECT_ROOT / "core" / "data" / "framework_library" / "vh_frameworks.with_cdr12.canonical_input.yaml"
    vl_input = Path(args.vl_yaml) if args.vl_yaml else PROJECT_ROOT / "core" / "data" / "framework_library" / "vl_frameworks.with_cdr12.canonical_input.yaml"
    
    out_dir = Path(args.out_dir) if args.out_dir else PROJECT_ROOT / "output" / "framework_library" / "canonical"
    vh_output = out_dir / "framework_vh_canonical_input.fasta"
    vl_output = out_dir / "framework_vl_canonical_input.fasta"
    
    print(f"--- Exporting Canonical Input FASTA ---")
    
    try:
        vh_count = export_fasta(vh_input, vh_output, "VH")
        print(f"✅ VH: Exported {vh_count} entries to {vh_output}")
        
        vl_count = export_fasta(vl_input, vl_output, "VL")
        print(f"✅ VL: Exported {vl_count} entries to {vl_output}")
        
        print("\n[SUCCESS] Export complete.")
        
    except Exception as e:
        print(f"\n❌ [ERROR] {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
