#!/usr/bin/env python3
"""
Generate functional sites mapping report YAML

Reads sequence, runs analysis, and generates structured report.
"""

import sys
import yaml
import hashlib
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.analyze_functional_sites_mapping import analyze_functional_sites_mapping, load_sequence_from_fasta


def generate_report_yaml(sequence: str, output_path: Path):
    """Generate mapping report YAML file."""
    sites_file = project_root / "kb" / "10_parameters" / "functional_sites.yaml"
    
    results = analyze_functional_sites_mapping(sites_file, sequence)
    
    if "error" in results:
        print(f"ERROR: {results['error']}", file=sys.stderr)
        sys.exit(1)
    
    # Build report structure
    report = {
        "sequence_id": results["sequence_id"],
        "sequence_hash": results["sequence_hash"],
        "scheme_source": results["scheme_source"],
        "numbering_engine": results.get("numbering_engine", {}),  # Add numbering engine info
        "dual_map_status": results["dual_map_status"],
        "dual_map_length": len(results.get("dual_map", [])),
        
        "hallmark_mapping_stats": results["hallmark_mapping_stats"],
        "vernier_mapping_stats": results["vernier_mapping_stats"],
        
        "resolved_sites": {},
        "conflicts": results["conflicts"]
    }
    
    # Add resolved sites (simplified)
    for site_id, site_info in results["resolved_sites"].items():
        report["resolved_sites"][site_id] = {
            "role": site_info["role"],
            "mapping_status": site_info["mapping_status"],
            "resolved_imgt_positions": site_info["resolved_imgt_positions"],
            "resolved_kabat_positions": site_info["resolved_kabat_positions"]
        }
    
    # Write YAML
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(report, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    print(f"Report written to: {output_path}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate functional sites mapping report from sequence"
    )
    parser.add_argument('--seq', type=str, help='Amino acid sequence')
    parser.add_argument('--seq_fasta', type=str, help='Path to FASTA file')
    parser.add_argument('--output', type=str, default=None, help='Output YAML path (default: functional_sites_mapping_report.yaml)')
    
    args = parser.parse_args()
    
    # Get sequence
    if args.seq:
        sequence = args.seq
    elif args.seq_fasta:
        fasta_path = Path(args.seq_fasta)
        if not fasta_path.exists():
            print(f"ERROR: FASTA file not found: {fasta_path}", file=sys.stderr)
            sys.exit(1)
        sequence = load_sequence_from_fasta(fasta_path)
    else:
        # Default test sequence
        sequence = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAA"
        print("WARNING: No sequence provided, using default test sequence", file=sys.stderr)
    
    # Output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = project_root / "kb" / "10_parameters" / "functional_sites_mapping_report.yaml"
    
    generate_report_yaml(sequence, output_path)


if __name__ == "__main__":
    main()










