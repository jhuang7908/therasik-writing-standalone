#!/usr/bin/env python3
"""
Analyze Functional Sites Mapping Status (Sequence-based)

Analyzes functional_sites.yaml against a real sequence using ANARCI dual numbering.
Provides:
1. dual_map_status: Overall IMGT/Kabat mapping consistency (full/partial/conflict/failed)
2. hallmark/vernier mapping_status statistics
3. Conflict examples (if any)
"""

import sys
import argparse
import yaml
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.numbering.dual_map import build_dual_map, resolve_functional_sites_on_sequence, DualMapError


def analyze_functional_sites_mapping(
    sites_file: Path,
    sequence: str
) -> Dict:
    """
    Analyze functional sites for IMGT/Kabat mapping status using real sequence.
    
    Args:
        sites_file: Path to functional_sites.yaml
        sequence: Amino acid sequence to analyze
        
    Returns a dictionary with:
        - sequence_id: hash of sequence
        - sequence_hash: SHA256 hash
        - scheme_source: "anarci"
        - dual_map_status: overall status (full/partial/conflict/failed)
        - dual_map: the actual dual_map result
        - hallmark_mapping_stats: statistics for hallmark sites
        - vernier_mapping_stats: statistics for vernier sites
        - resolved_sites: resolved functional sites
        - conflicts: list of conflict examples
    """
    if not sites_file.exists():
        return {"error": f"File not found: {sites_file}"}
    
    # Load functional sites
    with open(sites_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    functional_sites = data.get('functional_sites', [])
    
    # Get numbering engine info (always include, even if numbering fails)
    try:
        import anarcii
        anarcii_version = getattr(anarcii, '__version__', 'unknown')
    except ImportError:
        anarcii_version = 'unknown'
    
    numbering_engine = {
        "name": "anarcii",
        "version": anarcii_version,
        "scheme_imgt": "imgt",
        "scheme_kabat": "kabat"
    }
    
    # Build dual map from sequence
    # CRITICAL: Without ANARCII numbering, functional sites calculation is impossible or inaccurate
    # See: kb/10_parameters/functional_sites_mapping_limitations.md
    try:
        dual_map, dual_map_status, chain_type = build_dual_map(sequence)
    except DualMapError as e:
        return {
            "error": str(e),
            "dual_map_status": "failed",
            "scheme_source": "anarci",
            "numbering_engine": numbering_engine,  # Always include numbering engine info
            "warning": "ANARCII numbering failed. Functional sites calculation cannot proceed without real sequence numbering.",
            "resolved_sites": {},
            "conflicts": [],
            "hallmark_mapping_stats": {
                "total_sites": 0,
                "full_matches": 0,
                "partial_matches": 0,
                "conflicts": 0,
                "total_imgt_positions": 0,
                "total_kabat_positions": 0,
                "overlapping_positions": 0
            },
            "vernier_mapping_stats": {
                "total_sites": 0,
                "full_matches": 0,
                "partial_matches": 0,
                "conflicts": 0,
                "total_imgt_positions": 0,
                "total_kabat_positions": 0,
                "overlapping_positions": 0
            }
        }
    
    # Resolve functional sites on sequence
    # This requires a valid dual_map from ANARCII numbering
    # Filter: Skip VL_LAMBDA_* sites if chain_type is not VL or light_chain_type is not lambda
    # (This allows VL_LAMBDA_* sites to exist in KB but skip them from mapping when no λ sequences)
    filtered_sites = []
    skipped_lambda_sites = []
    
    # Normalize chain_type for comparison (ANARCII may return 'H', 'L', 'K', etc.)
    normalized_chain_type = None
    if chain_type:
        chain_type_upper = chain_type.upper()
        if chain_type_upper in ['H', 'VH', 'VHH']:
            normalized_chain_type = 'VH' if chain_type_upper != 'VHH' else 'VHH'
        elif chain_type_upper in ['L', 'K', 'VL']:
            normalized_chain_type = 'VL'
    
    for site in functional_sites:
        site_id = site.get('site_id', '')
        # Check if this is a VL_LAMBDA_* site
        if site_id.startswith('VL_LAMBDA_'):
            # Skip VL_LAMBDA_* sites from mapping if:
            # 1. chain_type is not VL (i.e., analyzing VHH/VH sequences, not VL sequences)
            # 2. OR site's light_chain_type is not 'lambda'
            # This ensures VL_LAMBDA_* sites only participate when analyzing actual VL-λ sequences
            if normalized_chain_type != 'VL' or site.get('light_chain_type') != 'lambda':
                skipped_lambda_sites.append({
                    "site_id": site_id,
                    "skipped_reason": "no_lambda_sequences_provided",
                    "note": "VL_LAMBDA_* sites excluded from mapping_status statistics"
                })
                continue
        filtered_sites.append(site)
    
    # Resolve functional sites (only non-skipped sites)
    # Pass chain_type for filtering by chain_scope
    resolved_sites, conflicts = resolve_functional_sites_on_sequence(dual_map, filtered_sites, chain_type)
    
    # Calculate statistics by role (only for non-skipped sites)
    sites_by_role = defaultdict(list)
    for site_id, site_info in resolved_sites.items():
        role = site_info.get('role', 'unknown')
        sites_by_role[role].append(site_info)
    
    hallmark_stats = calculate_role_mapping_stats(sites_by_role.get('hallmark', []))
    vernier_stats = calculate_role_mapping_stats(sites_by_role.get('vernier', []))
    
    # Generate sequence ID/hash
    seq_hash = hashlib.sha256(sequence.encode()).hexdigest()[:16]
    sequence_id = f"seq_{seq_hash}"
    
    return {
        "sequence_id": sequence_id,
        "sequence_hash": hashlib.sha256(sequence.encode()).hexdigest(),
        "scheme_source": "anarci",
        "numbering_engine": numbering_engine,  # Add numbering engine info
        "dual_map_status": dual_map_status,
        "chain_type": chain_type,  # Add chain_type to results
        "dual_map": dual_map,
        "hallmark_mapping_stats": hallmark_stats,
        "vernier_mapping_stats": vernier_stats,
        "resolved_sites": resolved_sites,  # Only non-skipped sites (VL_LAMBDA_* filtered out)
        "conflicts": conflicts,
        "skipped_lambda_sites": skipped_lambda_sites  # VL_LAMBDA_* sites skipped
    }


def calculate_role_mapping_stats(sites: List[Dict]) -> Dict:
    """Calculate mapping statistics for a specific role."""
    if not sites:
        return {
            "total_sites": 0,
            "full_matches": 0,
            "partial_matches": 0,
            "conflicts": 0,
            "total_imgt_positions": 0,
            "total_kabat_positions": 0
        }
    
    full_matches = sum(1 for s in sites if s.get('mapping_status') == 'full')
    partial_matches = sum(1 for s in sites if s.get('mapping_status') == 'partial')
    conflict_matches = sum(1 for s in sites if s.get('mapping_status') == 'conflict')
    
    all_imgt = set()
    all_kabat = set()
    
    for site in sites:
        all_imgt.update(site.get('resolved_imgt_positions', []))
        all_kabat.update(site.get('resolved_kabat_positions', []))
    
    return {
        "total_sites": len(sites),
        "full_matches": full_matches,
        "partial_matches": partial_matches,
        "conflicts": conflict_matches,
        "total_imgt_positions": len(all_imgt),
        "total_kabat_positions": len(all_kabat),
        "overlapping_positions": len(all_imgt & all_kabat)
    }


def load_sequence_from_fasta(fasta_path: Path) -> str:
    """Load sequence from FASTA file."""
    with open(fasta_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Empty FASTA file")
    
    # Skip header lines (starting with >)
    seq_lines = [line for line in lines if not line.startswith('>')]
    sequence = ''.join(seq_lines)
    
    return sequence.upper().replace(' ', '').replace('\n', '').replace('*', '')


def main():
    """Main analysis logic."""
    parser = argparse.ArgumentParser(
        description="Analyze functional sites mapping using real sequence and ANARCI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--seq',
        type=str,
        help='Amino acid sequence string'
    )
    parser.add_argument(
        '--seq_fasta',
        type=str,
        help='Path to FASTA file containing sequence'
    )
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
        # Default: use a test VHH sequence
        sequence = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAA"
        print("WARNING: No sequence provided, using default test sequence", file=sys.stderr)
    
    sites_file = project_root / "kb" / "10_parameters" / "functional_sites.yaml"
    
    results = analyze_functional_sites_mapping(sites_file, sequence)
    
    if "error" in results:
        print(f"ERROR: {results['error']}", file=sys.stderr)
        sys.exit(1)
    
    # Print results
    print("=" * 80)
    print("Functional Sites Mapping Analysis (Sequence-based)")
    print("=" * 80)
    
    # Check for errors first
    if "error" in results:
        print(f"\n❌ ERROR: {results['error']}")
        if "warning" in results:
            print(f"⚠️  WARNING: {results['warning']}")
        print("\n" + "=" * 80)
        print("\n💡 Solution: Ensure ANARCII is installed and the sequence can be numbered.")
        print("   Install: pip install anarcii")
        print("   See: kb/10_parameters/functional_sites_mapping_limitations.md")
        sys.exit(1)
    
    print(f"\nSequence ID: {results['sequence_id']}")
    print(f"Sequence hash: {results['sequence_hash']}")
    print(f"Scheme source: {results['scheme_source']}")
    print(f"Sequence length: {len(sequence)}")
    
    # Dual map status
    print("\n📊 Dual Map Status (IMGT ↔ Kabat):")
    print("-" * 80)
    status = results['dual_map_status']
    print(f"Status: {status.upper()}")
    
    dual_map = results['dual_map']
    total_positions = len(dual_map)
    positions_with_both = sum(1 for entry in dual_map if entry["imgt_pos"] and entry["kabat_pos"])
    imgt_gaps = sum(1 for entry in dual_map if "imgt_gap" in entry.get("flags", []))
    kabat_gaps = sum(1 for entry in dual_map if "kabat_gap" in entry.get("flags", []))
    insertions = sum(1 for entry in dual_map if "imgt_insertion" in entry.get("flags", []) or "kabat_insertion" in entry.get("flags", []))
    
    print(f"Total sequence positions: {total_positions}")
    print(f"Positions with both IMGT and Kabat: {positions_with_both} ({positions_with_both/total_positions*100:.1f}%)")
    print(f"IMGT gaps: {imgt_gaps}")
    print(f"Kabat gaps: {kabat_gaps}")
    print(f"Insertions detected: {insertions}")
    
    # Hallmark mapping stats
    print("\n🏷️  Hallmark Sites Mapping Statistics:")
    print("-" * 80)
    h_stats = results['hallmark_mapping_stats']
    print(f"Total hallmark sites: {h_stats['total_sites']}")
    print(f"Full matches: {h_stats['full_matches']}")
    print(f"Partial matches: {h_stats['partial_matches']}")
    print(f"Conflicts: {h_stats['conflicts']}")
    print(f"IMGT positions covered: {h_stats['total_imgt_positions']}")
    print(f"Kabat positions covered: {h_stats['total_kabat_positions']}")
    print(f"Overlapping positions: {h_stats['overlapping_positions']}")
    
    # Show resolved hallmark sites
    hallmark_sites = [s for s in results['resolved_sites'].values() if s['role'] == 'hallmark']
    if hallmark_sites:
        print("\n  Resolved hallmark sites:")
        for site in hallmark_sites:
            print(f"    - {site['site_id']}: {site['mapping_status']}")
            print(f"      IMGT: {site['resolved_imgt_positions']}")
            print(f"      Kabat: {site['resolved_kabat_positions']}")
    
    # Vernier mapping stats
    print("\n⚙️  Vernier Sites Mapping Statistics:")
    print("-" * 80)
    v_stats = results['vernier_mapping_stats']
    print(f"Total vernier sites: {v_stats['total_sites']}")
    print(f"Full matches: {v_stats['full_matches']}")
    print(f"Partial matches: {v_stats['partial_matches']}")
    print(f"Conflicts: {v_stats['conflicts']}")
    print(f"IMGT positions covered: {v_stats['total_imgt_positions']}")
    print(f"Kabat positions covered: {v_stats['total_kabat_positions']}")
    print(f"Overlapping positions: {v_stats['overlapping_positions']}")
    
    # Show resolved vernier sites
    vernier_sites = [s for s in results['resolved_sites'].values() if s['role'] == 'vernier']
    if vernier_sites:
        print("\n  Resolved vernier sites:")
        for site in vernier_sites:
            print(f"    - {site['site_id']}: {site['mapping_status']}")
            print(f"      IMGT: {site['resolved_imgt_positions']}")
            print(f"      Kabat: {site['resolved_kabat_positions']}")
    
    # Show skipped VL-λ sites
    if results.get('skipped_lambda_sites'):
        print("\n⚠️  Skipped VL-λ sites (no λ sequences provided):")
        for skipped in results['skipped_lambda_sites']:
            print(f"    - {skipped['site_id']}: {skipped['skipped_reason']}")
            if 'note' in skipped:
                print(f"      Note: {skipped['note']}")
    
    # Conflicts
    if results['conflicts']:
        print("\n⚠️  Conflict Examples:")
        print("-" * 80)
        for i, conflict in enumerate(results['conflicts'][:5], 1):  # Show up to 5
            print(f"\nConflict #{i}:")
            print(f"  Site ID: {conflict['site_id']}")
            print(f"  Missing scheme: {conflict['missing_scheme']}")
            print(f"  Missing position: {conflict['missing_pos']}")
            print(f"  Present scheme: {conflict['present_scheme']}")
            print(f"  Present position: {conflict['present_pos']}")
            print(f"  Description: {conflict['description']}")
    else:
        print("\n✅ No conflicts detected - all sites have consistent IMGT/Kabat mappings")
    
    print("\n" + "=" * 80)
    
    # Output structured data
    print("\n📋 Structured Output (for programmatic use):")
    print("-" * 80)
    import json
    # Remove dual_map from output (too large)
    output_data = {k: v for k, v in results.items() if k != 'dual_map'}
    output_data['dual_map_length'] = len(results.get('dual_map', []))
    print(json.dumps(output_data, indent=2, default=str))


if __name__ == "__main__":
    main()










