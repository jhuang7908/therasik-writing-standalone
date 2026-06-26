"""
Build V2 variants from existing result JSON file.

This script reads a result JSON file containing variants, performs CMC scanning
on each variant sequence, and generates V2 variants to mitigate CMC liabilities.
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
from core.cmc.v2_variant_builder import generate_v2_variants


def load_result_json(input_path: str) -> Dict[str, Any]:
    """
     JSON 。
    
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
    
    if 'variants' not in data:
        raise ValueError("JSON file must contain a 'variants' key")
    
    if not isinstance(data['variants'], list):
        raise ValueError("'variants' must be a list")
    
    return data


def process_variant(variant: Dict[str, Any]) -> Dict[str, Any]:
    """
    ： CMC  V2 。
    
    Args:
        variant: ， 'id'  'sequence' 
        
    Returns:
        
        
    Raises:
        ValueError: 
    """
    if 'id' not in variant:
        raise ValueError("Variant missing 'id' field")
    
    if 'sequence' not in variant:
        raise ValueError(f"Variant '{variant['id']}' missing 'sequence' field")
    
    variant_id = variant['id']
    sequence = variant['sequence']
    
    if not isinstance(sequence, str) or not sequence:
        raise ValueError(f"Variant '{variant_id}' has invalid sequence")
    
    # Perform CMC scanning
    cmc_info = scan_cmc_liabilities(sequence)
    
    # Generate V2 variants
    v2_variants = generate_v2_variants(sequence, cmc_info)
    
    return {
        "parent_id": variant_id,
        "parent_sequence": sequence,
        "cmc_summary": cmc_info.get('summary', {}),
        "v2_variants": v2_variants
    }


def build_v2_library(input_path: str, output_path: str) -> None:
    """
     JSON  V2 。
    
    Args:
        input_path:  JSON 
        output_path:  JSON 
    """
    # Load input file
    print(f"Loading input file: {input_path}")
    try:
        data = load_result_json(input_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    variants = data['variants']
    if not variants:
        print("Warning: No variants found in input file", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(variants)} variant(s) to process")
    print()
    
    # Process each variant
    v2_library = []
    processed_count = 0
    
    for i, variant in enumerate(variants, 1):
        variant_id = variant.get('id', f'variant_{i}')
        print(f"Processing variant {i}/{len(variants)}: {variant_id}")
        
        try:
            result = process_variant(variant)
            v2_library.append(result)
            processed_count += 1
            
            # Print summary for this variant
            v2_variants = result['v2_variants']
            total_mutations = (
                len(v2_variants.get('v2_deamidation_only', {}).get('mutations', [])) +
                len(v2_variants.get('v2_isomerization_only', {}).get('mutations', [])) +
                len(v2_variants.get('v2_combined', {}).get('mutations', []))
            )
            print(f"  Generated 3 V2 variants with {total_mutations} total mutations")
            
        except Exception as e:
            print(f"  Error processing variant '{variant_id}': {e}", file=sys.stderr)
            continue
    
    print()
    
    if processed_count == 0:
        print("Error: No variants were successfully processed", file=sys.stderr)
        sys.exit(1)
    
    # Build output structure
    output_data = {
        "source_result": input_path,
        "v2_library": v2_library
    }
    
    # Write output file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Writing output to: {output_path}")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Print summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Processed parent variants: {processed_count}/{len(variants)}")
    print(f"Total V2 variants generated: {processed_count * 3}")
    print(f"Output file: {output_path}")
    print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Build V2 variants from result JSON file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --input result.json --output result_v2.json
  %(prog)s -i custom_result.json -o custom_v2.json
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='result.json',
        help='Input result JSON file path (default: result.json)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='result_v2.json',
        help='Output V2 library JSON file path (default: result_v2.json)'
    )
    
    args = parser.parse_args()
    
    try:
        build_v2_library(args.input, args.output)
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























