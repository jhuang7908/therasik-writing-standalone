#!/usr/bin/env python3
"""
Validate Dual Map Consistency for Antibody Chains

Validates IMGT/Kabat dual mapping consistency for antibody chains only.
Filters out non-antibody chains (e.g., antigen chains like PD-1).

Only processes chains with chain_type in {VHH, VH, VL} (or 'H', 'L', 'K').
"""

import sys
import argparse
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.numbering.dual_map import build_dual_map, DualMapError


def get_numbering_engine_info() -> Dict[str, Any]:
    """
    Get numbering engine information.
    
    Returns:
        Dict with:
        - name: Engine name (e.g., "anarcii")
        - version: Engine version (or "unknown" if not available)
        - scheme_imgt: IMGT scheme identifier
        - scheme_kabat: Kabat scheme identifier
    """
    try:
        import anarcii
        version = getattr(anarcii, '__version__', 'unknown')
    except ImportError:
        version = 'unknown'
    
    return {
        "name": "anarcii",
        "version": version,
        "scheme_imgt": "imgt",
        "scheme_kabat": "kabat"
    }


# Valid antibody chain types
VALID_ANTIBODY_CHAIN_TYPES = {'H', 'L', 'K', 'VHH', 'VH', 'VL'}

# Map chain_type to normalized form
CHAIN_TYPE_MAP = {
    'H': 'VH',
    'L': 'VL',
    'K': 'VL',  # Kappa is also light chain
    'VHH': 'VHH',
    'VH': 'VH',
    'VL': 'VL'
}


def normalize_chain_type(chain_type: Optional[str]) -> Optional[str]:
    """Normalize chain_type to VHH/VH/VL."""
    if chain_type is None:
        return None
    chain_type_upper = chain_type.upper()
    # Check direct match
    if chain_type_upper in VALID_ANTIBODY_CHAIN_TYPES:
        return CHAIN_TYPE_MAP.get(chain_type, chain_type_upper)
    # Check if it starts with valid prefix
    for valid_type in VALID_ANTIBODY_CHAIN_TYPES:
        if chain_type_upper.startswith(valid_type):
            return CHAIN_TYPE_MAP.get(valid_type, valid_type)
    return None


def is_antibody_chain(chain_type: Optional[str]) -> bool:
    """Check if chain_type indicates an antibody chain."""
    normalized = normalize_chain_type(chain_type)
    return normalized in {'VHH', 'VH', 'VL'}


def load_fasta(fasta_path: Path) -> Dict[str, str]:
    """Load sequences from FASTA file."""
    sequences = {}
    current_header = None
    current_seq = []
    
    with open(fasta_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('>'):
                # Save previous sequence
                if current_header and current_seq:
                    sequences[current_header] = ''.join(current_seq)
                
                # Start new sequence
                current_header = line[1:].strip()
                current_seq = []
            else:
                current_seq.append(line)
        
        # Save last sequence
        if current_header and current_seq:
            sequences[current_header] = ''.join(current_seq)
    
    return sequences


def validate_sequence(
    seq_id: str,
    sequence: str
) -> Dict[str, Any]:
    """
    Validate dual map for a single sequence.
    
    Returns validation result with chain_type filtering.
    """
    # Get numbering engine info (always include, even if numbering fails)
    numbering_engine = get_numbering_engine_info()
    
    result = {
        "seq_id": seq_id,
        "sequence_length": len(sequence),
        "chain_type": None,
        "is_antibody": False,
        "dual_map_status": None,
        "error": None,
        "numbering_engine": numbering_engine,  # Always include numbering engine info
        "statistics": {}
    }
    
    try:
        dual_map, status, chain_type = build_dual_map(sequence)
        
        result["chain_type"] = chain_type
        result["dual_map_status"] = status
        
        # Check if this is an antibody chain
        normalized_chain_type = normalize_chain_type(chain_type)
        result["is_antibody"] = is_antibody_chain(chain_type)
        result["normalized_chain_type"] = normalized_chain_type
        
        if not result["is_antibody"]:
            result["error"] = f"Non-antibody chain (chain_type={chain_type}). Excluded from validation."
            result["statistics"] = {
                "excluded": True,
                "reason": "non_antibody_chain"
            }
            return result
        
        # Calculate statistics for antibody chains only
        total_positions = len(dual_map)
        positions_with_both = sum(1 for entry in dual_map if entry["imgt_pos"] and entry["kabat_pos"])
        imgt_gaps = sum(1 for entry in dual_map if "imgt_gap" in entry.get("flags", []))
        kabat_gaps = sum(1 for entry in dual_map if "kabat_gap" in entry.get("flags", []))
        insertions = sum(1 for entry in dual_map 
                        if "imgt_insertion" in entry.get("flags", []) or 
                           "kabat_insertion" in entry.get("flags", []))
        
        result["statistics"] = {
            "excluded": False,
            "total_positions": total_positions,
            "positions_with_both": positions_with_both,
            "positions_with_both_percentage": round(positions_with_both / total_positions * 100, 2) if total_positions > 0 else 0,
            "imgt_gaps": imgt_gaps,
            "kabat_gaps": kabat_gaps,
            "insertions": insertions,
            "dual_map_length": len(dual_map)
        }
        
    except DualMapError as e:
        result["error"] = str(e)
        result["dual_map_status"] = "failed"
        result["statistics"] = {
            "excluded": True,
            "reason": "numbering_failed"
        }
    
    return result


def validate_fasta_file(fasta_path: Path) -> Dict[str, Any]:
    """
    Validate all sequences in a FASTA file.
    
    Only includes antibody chains (VHH/VH/VL) in the validation report.
    """
    sequences = load_fasta(fasta_path)
    
    if not sequences:
        return {
            "error": f"No sequences found in {fasta_path}",
            "total_sequences": 0,
            "antibody_chains": 0,
            "non_antibody_chains": 0,
            "failed_sequences": 0,
            "results": []
        }
    
    results = []
    antibody_chains = []
    non_antibody_chains = []
    failed_sequences = []
    
    for seq_id, sequence in sequences.items():
        result = validate_sequence(seq_id, sequence)
        results.append(result)
        
        if result.get("error") and "numbering_failed" in result.get("statistics", {}).get("reason", ""):
            failed_sequences.append(seq_id)
        elif result.get("is_antibody"):
            antibody_chains.append(seq_id)
        else:
            non_antibody_chains.append(seq_id)
    
    # Summary statistics (only for antibody chains)
    antibody_results = [r for r in results if r.get("is_antibody")]
    
    summary = {
        "total_sequences": len(sequences),
        "antibody_chains": len(antibody_chains),
        "non_antibody_chains": len(non_antibody_chains),
        "failed_sequences": len(failed_sequences),
        "antibody_chain_types": defaultdict(int),
        "dual_map_status_summary": defaultdict(int),
        "overall_statistics": {}
    }
    
    # Count chain types
    for result in antibody_results:
        chain_type = result.get("normalized_chain_type") or result.get("chain_type") or "unknown"
        summary["antibody_chain_types"][chain_type] += 1
        status = result.get("dual_map_status") or "unknown"
        summary["dual_map_status_summary"][status] += 1
    
    # Overall statistics (only for antibody chains)
    if antibody_results:
        total_pos = sum(r["statistics"].get("total_positions", 0) for r in antibody_results)
        total_both = sum(r["statistics"].get("positions_with_both", 0) for r in antibody_results)
        total_imgt_gaps = sum(r["statistics"].get("imgt_gaps", 0) for r in antibody_results)
        total_kabat_gaps = sum(r["statistics"].get("kabat_gaps", 0) for r in antibody_results)
        total_insertions = sum(r["statistics"].get("insertions", 0) for r in antibody_results)
        
        summary["overall_statistics"] = {
            "total_positions": total_pos,
            "total_positions_with_both": total_both,
            "overall_both_percentage": round(total_both / total_pos * 100, 2) if total_pos > 0 else 0,
            "total_imgt_gaps": total_imgt_gaps,
            "total_kabat_gaps": total_kabat_gaps,
            "total_insertions": total_insertions
        }
    
    # Get numbering engine info
    numbering_engine = get_numbering_engine_info()
    
    return {
        "source_file": str(fasta_path),
        "numbering_engine": numbering_engine,  # Add numbering engine info
        "summary": summary,
        "results": results,
        "antibody_chain_results": antibody_results,  # Only antibody chains
        "non_antibody_chains": [r for r in results if not r.get("is_antibody")],
        "failed_sequences": [r for r in results if r.get("error") and "numbering_failed" in r.get("statistics", {}).get("reason", "")]
    }


def main():
    """Main validation logic."""
    parser = argparse.ArgumentParser(
        description="Validate dual map consistency for antibody chains only",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate single FASTA file
  python tools/validate_dual_map_consistency.py \\
    --seq_fasta data/benchmarks/fasta/egfr_7d12_vhh.fasta \\
    --out reports/mapping/egfr_7d12_vhh_dual_map_report.json
  
  # Validate mouse Fab (VH + VL)
  python tools/validate_dual_map_consistency.py \\
    --seq_fasta data/benchmarks/fasta/pd1_6jbt_mouse_fab_vhvl.fasta \\
    --out reports/mapping/pd1_6jbt_mouse_fab_vhvl_dual_map_report.json

Note: Only chains with chain_type in {VHH, VH, VL} are included in validation.
      Non-antibody chains (e.g., antigen chains) are excluded.
        """
    )
    parser.add_argument(
        '--seq_fasta',
        type=str,
        required=True,
        help='Path to FASTA file containing sequences'
    )
    parser.add_argument(
        '--out',
        type=str,
        required=True,
        help='Output JSON report path'
    )
    
    args = parser.parse_args()
    
    fasta_path = Path(args.seq_fasta)
    if not fasta_path.exists():
        print(f"ERROR: FASTA file not found: {fasta_path}", file=sys.stderr)
        sys.exit(1)
    
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Validate sequences
    print(f"Validating sequences from: {fasta_path}")
    print("=" * 80)
    
    report = validate_fasta_file(fasta_path)
    
    # Print summary
    summary = report["summary"]
    print(f"\n📊 Validation Summary:")
    print(f"  Total sequences: {summary['total_sequences']}")
    print(f"  Antibody chains (VHH/VH/VL): {summary['antibody_chains']}")
    print(f"  Non-antibody chains (excluded): {summary['non_antibody_chains']}")
    print(f"  Failed sequences: {summary['failed_sequences']}")
    
    if summary['antibody_chain_types']:
        print(f"\n  Chain type distribution:")
        for chain_type, count in sorted(summary['antibody_chain_types'].items()):
            print(f"    {chain_type}: {count}")
    
    if summary['dual_map_status_summary']:
        print(f"\n  Dual map status:")
        for status, count in sorted(summary['dual_map_status_summary'].items()):
            print(f"    {status}: {count}")
    
    if summary.get('overall_statistics'):
        stats = summary['overall_statistics']
        print(f"\n  Overall statistics (antibody chains only):")
        print(f"    Total positions: {stats['total_positions']}")
        print(f"    Positions with both IMGT and Kabat: {stats['total_positions_with_both']} ({stats['overall_both_percentage']}%)")
        print(f"    IMGT gaps: {stats['total_imgt_gaps']}")
        print(f"    Kabat gaps: {stats['total_kabat_gaps']}")
        print(f"    Insertions: {stats['total_insertions']}")
    
    # Show excluded chains
    if report.get('non_antibody_chains'):
        print(f"\n⚠️  Excluded non-antibody chains:")
        for result in report['non_antibody_chains']:
            print(f"    - {result['seq_id']}: {result.get('error', 'Non-antibody chain')}")
    
    # Show failed sequences
    if report.get('failed_sequences'):
        print(f"\n❌ Failed sequences:")
        for result in report['failed_sequences']:
            print(f"    - {result['seq_id']}: {result.get('error', 'Numbering failed')}")
    
    # Write report
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n✅ Report written to: {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()










