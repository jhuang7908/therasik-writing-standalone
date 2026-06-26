#!/usr/bin/env python3
"""
 VH/VL 

FASTA，，JSON
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# 
try:
    from core.vhh_humanization_with_qa import humanize_vhh_with_qa
    HAS_HUMANIZATION = True
except ImportError:
    HAS_HUMANIZATION = False
    print("⚠️  ")


def read_fasta(fasta_path: Path) -> tuple[str, str]:
    """FASTA，(header, sequence)"""
    if not fasta_path.exists():
        raise FileNotFoundError(f"FASTA: {fasta_path}")
    
    with open(fasta_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    header = ""
    sequence = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('>'):
            header = line[1:]
        else:
            sequence += line.upper()
    
    if not sequence:
        raise ValueError(f"FASTA: {fasta_path}")
    
    return header, sequence


def main():
    parser = argparse.ArgumentParser(
        description=" VH/VL ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
:
  # VH
  python scripts/run_vh_vl_humanization.py \\
    --fasta data/benchmarks/fasta/6jbt_mouse_vh.fasta \\
    --project PD1_6JBT_VH \\
    --target PD1
  
  # VL
  python scripts/run_vh_vl_humanization.py \\
    --fasta data/benchmarks/fasta/6jbt_mouse_vl_kappa.fasta \\
    --project PD1_6JBT_VL \\
    --target PD1 \\
    --chain-type VL
        """
    )
    
    parser.add_argument(
        "--fasta",
        type=Path,
        required=True,
        help="FASTA"
    )
    
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="ID（: PD1_6JBT_VH）"
    )
    
    parser.add_argument(
        "--target",
        type=str,
        default="Unknown",
        help="（: Unknown）"
    )
    
    parser.add_argument(
        "--chain-type",
        type=str,
        choices=["VH", "VL", "VHH"],
        default="VH",
        help="（: VH）"
    )
    
    parser.add_argument(
        "--panel",
        type=str,
        default="A",
        choices=["A", "B", "C", "all"],
        help=" (A: , B: , C: VHH, all: )"
    )
    
    parser.add_argument(
        "--qa-version",
        type=str,
        default="v3.5",
        choices=["v3.4", "v3.5"],
        help="QA（: v3.5）"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="（: projects/{PROJECT}/output）"
    )
    
    parser.add_argument(
        "--species",
        type=str,
        default="mouse",
        help="（: mouse）"
    )
    
    args = parser.parse_args()
    
    if not HAS_HUMANIZATION:
        print("❌ : ")
        return 1
    
    # 
    print("=" * 80)
    print("VH/VL ")
    print("=" * 80)
    print(f"\nFASTA: {args.fasta}")
    
    try:
        header, sequence = read_fasta(args.fasta)
        print(f": {header}")
        print(f": {len(sequence)} aa")
    except Exception as e:
        print(f"❌ FASTA: {e}")
        return 1
    
    # 
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = PROJECT_ROOT / "projects" / args.project / "output"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"ID: {args.project}")
    print(f": {args.target}")
    print(f": {args.chain_type}")
    print(f": {args.panel}")
    print(f"QA: {args.qa_version}")
    print(f": {output_dir}")
    print("=" * 80)
    
    # 
    print("\n[ 1/2] ...")
    print("-" * 80)
    
    try:
        # ：humanize_vhh_with_qa VHH
        # VH/VL，
        result = humanize_vhh_with_qa(
            seq=sequence,
            panel=args.panel,
            top_k=5,
            species=args.species,
            return_all_templates=False,
            enable_safe_mode=True,
            strict_qa=True,
            qa_version=args.qa_version,
        )
        
        # 
        result["project_id"] = args.project
        result["target"] = args.target
        result["input"] = result.get("input", {})
        result["input"]["sequence"] = sequence
        result["input"]["target"] = args.target
        result["input"]["species"] = args.species
        result["input"]["chain_type"] = args.chain_type
        result["input"]["header"] = header
        
        print(f"✅ ")
        print(f"   - : {result.get('status', 'UNKNOWN')}")
        print(f"   - : {'' if result.get('success', False) else ''}")
        
        if not result.get("success", False):
            error = result.get("error", "Unknown error")
            print(f"   - : {error}")
            print(f"\n⚠️  ，...")
        
    except Exception as e:
        print(f"❌ : {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 
    print("\n[ 2/2] JSON...")
    print("-" * 80)
    
    result_json_path = output_dir / "result.json"
    with open(result_json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"✅ : {result_json_path}")
    
    print("\n" + "=" * 80)
    print("✅ ！")
    print("=" * 80)
    print(f"\n: {result_json_path}")
    print(f"\n: ")
    print(f"  python scripts/generate_6jbt_full_report.py \\")
    print(f"    --cases {args.chain_type} \\")
    print(f"    --outdir projects/{args.project}/_runs/2025-12-17_rationales_v1 \\")
    print(f"    --result-{args.chain_type.lower()}-json {result_json_path} \\")
    print(f"    --emit-json --emit-reports \\")
    print(f"    --report-pack client_full,developer_full \\")
    print(f"    --skip-validation")
    
    return 0


if __name__ == "__main__":
    exit(main())




