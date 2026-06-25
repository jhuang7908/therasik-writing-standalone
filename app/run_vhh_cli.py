"""
Command-line entry point for VHH engineering pipeline.

This module provides a CLI interface for running the VHH engineering pipeline
with various configuration options.
"""

import argparse
import json
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engines.vhh_engineering.pipeline_vhh import VHHEngineeringPipeline


def read_fasta_sequence(fasta_path):
    """
    Read the first sequence from a FASTA file.
    
    Args:
        fasta_path: Path to FASTA file
        
    Returns:
        str: Amino acid sequence (uppercase, no whitespace)
        
    Raises:
        FileNotFoundError: If FASTA file doesn't exist
        ValueError: If FASTA file is empty or invalid
    """
    fasta_path = Path(fasta_path)
    
    if not fasta_path.exists():
        raise FileNotFoundError(f"FASTA file not found: {fasta_path}")
    
    try:
        # Try using BioPython if available
        try:
            from Bio import SeqIO
            with open(fasta_path, 'r') as f:
                record = next(SeqIO.parse(f, 'fasta'))
                sequence = str(record.seq).upper().replace('-', '').replace(' ', '')
                if not sequence:
                    raise ValueError("FASTA file contains empty sequence")
                return sequence
        except ImportError:
            # Fallback: simple FASTA parser
            with open(fasta_path, 'r') as f:
                lines = f.readlines()
                sequence = ""
                in_sequence = False
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('>'):
                        if in_sequence:
                            break  # Stop after first sequence
                        in_sequence = True
                    elif in_sequence and line:
                        sequence += line.upper().replace('-', '').replace(' ', '')
                
                if not sequence:
                    raise ValueError("FASTA file contains no valid sequence")
                return sequence
    except Exception as e:
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise
        raise ValueError(f"Error reading FASTA file: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='VHH Engineering Pipeline - Command Line Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -f input.fasta --source llama --strategy balanced
  %(prog)s -f input.fasta --source alpaca --target human --out result.json
        """
    )
    
    parser.add_argument(
        '--fasta', '-f',
        type=str,
        required=True,
        help='Input FASTA file path (first sequence will be used)'
    )
    
    parser.add_argument(
        '--source',
        type=str,
        default='llama',
        choices=['llama', 'alpaca', 'synthetic', 'transgenic'],
        help='VHH source species (default: llama)'
    )
    
    parser.add_argument(
        '--target',
        type=str,
        default='human',
        help='Target species for engineering (default: human)'
    )
    
    parser.add_argument(
        '--strategy',
        type=str,
        default='balanced',
        choices=['conservative', 'balanced', 'aggressive'],
        help='Engineering strategy (default: balanced)'
    )
    
    parser.add_argument(
        '--out', '-o',
        type=str,
        default=None,
        help='Output JSON file path (if not provided, print to stdout)'
    )
    
    args = parser.parse_args()
    
    try:
        # Read sequence from FASTA
        print(f"Reading sequence from {args.fasta}...", file=sys.stderr)
        sequence = read_fasta_sequence(args.fasta)
        print(f"Sequence length: {len(sequence)} amino acids", file=sys.stderr)
        
        # Initialize pipeline
        print(f"Initializing pipeline (source: {args.source}, target: {args.target}, strategy: {args.strategy})...", 
              file=sys.stderr)
        pipeline = VHHEngineeringPipeline(
            sequence=sequence,
            source=args.source,
            target=args.target,
            strategy=args.strategy
        )
        
        # Run pipeline
        print("Running VHH engineering pipeline...", file=sys.stderr)
        result = pipeline.run()
        
        # Output results
        result_json = json.dumps(result, indent=2, ensure_ascii=False)
        
        if args.out:
            output_path = Path(args.out)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result_json)
            print(f"Results written to {output_path}", file=sys.stderr)
        else:
            print(result_json)
            
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

