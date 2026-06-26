"""
Generate human-readable summary report from V2 variant library.

This script reads result_v2.json and generates a formatted text report
suitable for copying to Excel or Word documents.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.cmc.generic_cmc_scanner import scan_cmc_liabilities


def load_v2_library(input_path: str) -> Dict[str, Any]:
    """
     V2  JSON 。
    
    Args:
        input_path:  JSON 
        
    Returns:
        
        
    Raises:
        FileNotFoundError: 
        ValueError:  JSON 
    """
    input_file = Path(input_path)
    
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON file: {e}")
    
    if not isinstance(data, dict):
        raise ValueError("JSON file must contain a dictionary")
    
    if 'v2_library' not in data:
        raise ValueError("JSON file must contain a 'v2_library' key")
    
    return data


def extract_motif_from_reason(reason: str) -> str:
    """
     reason  motif。
    
    Args:
        reason:  "N82Q to remove deamidation (NS motif)"
        
    Returns:
        motif ， "NS"
    """
    if '(' in reason and 'motif' in reason:
        start = reason.find('(') + 1
        end = reason.find(' ', start)
        if end == -1:
            end = reason.find(')', start)
        if end > start:
            return reason[start:end]
    return ""


def extract_category_from_reason(reason: str) -> str:
    """
     reason 。
    
    Args:
        reason:  "N82Q to remove deamidation (NS motif)"
        
    Returns:
        ， "deamidation"
    """
    if 'deamidation' in reason.lower():
        return "deamidation"
    elif 'isomerization' in reason.lower():
        return "isomerization"
    return "unknown"


def format_mutation_table(mutations: List[Dict]) -> str:
    """
    。
    
    Args:
        mutations: 
        
    Returns:
        
    """
    if not mutations:
        return "  (No mutations)"
    
    lines = []
    lines.append("  Position | From | To | Motif | Category")
    lines.append("  " + "-" * 50)
    
    for mut in mutations:
        pos = mut.get('pos', '?')
        from_aa = mut.get('from', '?')
        to_aa = mut.get('to', '?')
        reason = mut.get('reason', '')
        motif = extract_motif_from_reason(reason)
        category = extract_category_from_reason(reason)
        
        lines.append(f"  {pos:8} | {from_aa:4} | {to_aa:2} | {motif:5} | {category}")
    
    return "\n".join(lines)


def generate_report(data: Dict[str, Any]) -> str:
    """
    。
    
    Args:
        data: V2 
        
    Returns:
        
    """
    lines = []
    
    # Header
    lines.append("=" * 80)
    lines.append("V2 Variant Library Summary Report")
    lines.append("=" * 80)
    lines.append(f"Source: {data.get('source_result', 'unknown')}")
    lines.append("")
    
    v2_library = data.get('v2_library', [])
    lines.append(f"Total parent variants: {len(v2_library)}")
    lines.append("")
    
    # Process each parent variant
    for idx, parent in enumerate(v2_library, 1):
        parent_id = parent.get('parent_id', f'variant_{idx}')
        parent_seq = parent.get('parent_sequence', '')
        cmc_summary = parent.get('cmc_summary', {})
        v2_variants = parent.get('v2_variants', {})
        
        lines.append("=" * 80)
        lines.append(f"Parent Variant {idx}: {parent_id}")
        lines.append("=" * 80)
        lines.append("")
        
        # Parent sequence info
        lines.append(f"Parent Sequence ({len(parent_seq)} aa):")
        lines.append(f"  {parent_seq}")
        lines.append("")
        
        # CMC risk profile
        lines.append("CMC Risk Profile:")
        total_flags = cmc_summary.get('total_flags', 0)
        risk_level = cmc_summary.get('risk_level', 'unknown')
        lines.append(f"  Total CMC flags: {total_flags}")
        lines.append(f"  Risk level: {risk_level}")
        
        # Count deamidation and isomerization sites from mutations
        deamidation_count = 0
        isomerization_count = 0
        
        combined_mutations = v2_variants.get('v2_combined', {}).get('mutations', [])
        for mut in combined_mutations:
            reason = mut.get('reason', '').lower()
            if 'deamidation' in reason:
                deamidation_count += 1
            elif 'isomerization' in reason:
                isomerization_count += 1
        
        lines.append(f"  Deamidation sites: {deamidation_count}")
        lines.append(f"  Isomerization sites: {isomerization_count}")
        lines.append("")
        
        # V2 variants
        lines.append("V2 Variants:")
        lines.append("")
        
        # v2_deamidation_only
        if 'v2_deamidation_only' in v2_variants:
            v2_deam = v2_variants['v2_deamidation_only']
            lines.append("-" * 80)
            lines.append("V2 Deamidation-Only Variant")
            lines.append("-" * 80)
            lines.append(f"Sequence ({len(v2_deam.get('sequence', ''))} aa):")
            lines.append(f"  {v2_deam.get('sequence', '')}")
            lines.append("")
            lines.append("Mutations:")
            lines.append(format_mutation_table(v2_deam.get('mutations', [])))
            lines.append("")
        
        # v2_isomerization_only
        if 'v2_isomerization_only' in v2_variants:
            v2_iso = v2_variants['v2_isomerization_only']
            lines.append("-" * 80)
            lines.append("V2 Isomerization-Only Variant")
            lines.append("-" * 80)
            lines.append(f"Sequence ({len(v2_iso.get('sequence', ''))} aa):")
            lines.append(f"  {v2_iso.get('sequence', '')}")
            lines.append("")
            lines.append("Mutations:")
            lines.append(format_mutation_table(v2_iso.get('mutations', [])))
            lines.append("")
        
        # v2_combined
        if 'v2_combined' in v2_variants:
            v2_comb = v2_variants['v2_combined']
            lines.append("-" * 80)
            lines.append("V2 Combined Variant (Deamidation + Isomerization)")
            lines.append("-" * 80)
            lines.append(f"Sequence ({len(v2_comb.get('sequence', ''))} aa):")
            lines.append(f"  {v2_comb.get('sequence', '')}")
            lines.append("")
            lines.append("Mutations:")
            lines.append(format_mutation_table(v2_comb.get('mutations', [])))
            lines.append("")
        
        lines.append("")
    
    # Footer
    lines.append("=" * 80)
    lines.append("End of Report")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate human-readable summary report from V2 variant library',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --input result_v2.json --output result_v2_report.txt
  %(prog)s -i result_v2.json -o report.txt
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='result_v2.json',
        help='Input V2 library JSON file path (default: result_v2.json)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='result_v2_report.txt',
        help='Output report text file path (default: result_v2_report.txt)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load input file
        print(f"Loading V2 library from: {args.input}")
        data = load_v2_library(args.input)
        
        # Generate report
        print("Generating report...")
        report = generate_report(data)
        
        # Write output file
        output_file = Path(args.output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Writing report to: {args.output}")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"Report generated successfully: {args.output}")
        print(f"Total parent variants processed: {len(data.get('v2_library', []))}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()























