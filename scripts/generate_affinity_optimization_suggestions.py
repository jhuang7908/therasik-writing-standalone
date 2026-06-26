#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
VHH

，，
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_humanization import humanize_vhh
from core.affinity_optimization import (
    suggest_affinity_improving_mutations,
    generate_yeast_display_mutation_library
)
from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map


def main():
    """"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='VHH'
    )
    parser.add_argument(
        '--sequence', '-s',
        type=str,
        help='VHH（，EGFR VHH）'
    )
    parser.add_argument(
        '--panel', '-p',
        type=str,
        default='A',
        choices=['A', 'B', 'C', 'all'],
        help='VHH-SAFE'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('affinity_optimization_suggestions.json'),
        help='JSON'
    )
    parser.add_argument(
        '--yeast-library', '-y',
        action='store_true',
        help=''
    )
    parser.add_argument(
        '--max-mutations', '-m',
        type=int,
        default=5,
        help='（5）'
    )
    
    args = parser.parse_args()
    
    # EGFR VHH（）
    if not args.sequence:
        args.sequence = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
        print("[INFO] EGFR VHH")
    
    print("=" * 80)
    print("VHH")
    print("=" * 80)
    print(f"\n: {args.sequence[:50]}...")
    print(f": {len(args.sequence)}aa")
    print(f": {args.panel}")
    
    # 1. 
    print(f"\n[1] VHH...")
    result = humanize_vhh(args.sequence, panel=args.panel, top_k=1)
    
    if not result['success']:
        print(f"✗ : {result.get('error', 'Unknown error')}")
        return
    
    best = result['best_match']
    print(f"✓ ")
    print(f"  : {best['human_template']}")
    print(f"  identity: {best['alignment_scores']['framework_identity']:.1%}")
    print(f"  : {best['combined_score']:.3f}")
    
    # 2. （IMGT）
    print(f"\n[2] ...")
    
    # IMGT
    try:
        vhh_rows = imgt_number_anarcii(args.sequence)
        vhh_imgt_map = build_pos_to_aa_map(vhh_rows)
        
        humanized_rows = imgt_number_anarcii(best['humanized_sequence'])
        humanized_imgt_map = build_pos_to_aa_map(humanized_rows)
    except Exception as e:
        print(f"[WARN] IMGT，: {e}")
        vhh_imgt_map = None
        humanized_imgt_map = None
    
    mutation_suggestions = suggest_affinity_improving_mutations(
        vhh_sequence=args.sequence,
        humanized_sequence=best['humanized_sequence'],
        cdr_regions=result['cdrs'],
        framework_identity=best['alpaca_identity'],
        cdr_canonical=result.get('cdr_canonical'),
        vhh_imgt_map=vhh_imgt_map,
        humanized_imgt_map=humanized_imgt_map,
        use_systematic_rules=True,  # 
    )
    
    print(f"✓ ")
    print(f"  : {mutation_suggestions['strategy']}")
    print(f"  : {mutation_suggestions['summary']['total_mutations']}")
    print(f"  : {mutation_suggestions['summary'].get('systematic_count', 0)}")
    print(f"  Case by case: {mutation_suggestions['summary'].get('case_specific_count', 0)}")
    print(f"  : {mutation_suggestions['summary']['high_priority']}")
    print(f"  : {mutation_suggestions['summary']['medium_priority']}")
    print(f"  : {mutation_suggestions['summary']['low_priority']}")
    
    # 
    if mutation_suggestions.get('rules_applied'):
        print(f"\n  : {', '.join(mutation_suggestions['rules_applied'][:5])}")
        if len(mutation_suggestions['rules_applied']) > 5:
            print(f"    ...  {len(mutation_suggestions['rules_applied']) - 5} ")
    
    # 3. 
    print(f"\n[]")
    for i, mut in enumerate(mutation_suggestions['mutations'][:10], 1):
        print(f"\n  {i}. {mut['position']} ({mut['region']}): {mut['from']} → {mut['to']}")
        print(f"     : {mut['priority'].upper()}")
        print(f"     : {mut['rationale']}")
        print(f"     : {mut['expected_impact']}")
    
    if len(mutation_suggestions['mutations']) > 10:
        print(f"\n  ...  {len(mutation_suggestions['mutations']) - 10} ")
    
    # 4. （）
    yeast_library = None
    if args.yeast_library:
        print(f"\n[3] ...")
        yeast_library = generate_yeast_display_mutation_library(
            base_sequence=best['humanized_sequence'],
            mutation_suggestions=mutation_suggestions,
            max_mutations=args.max_mutations,
            strategy='targeted'
        )
        print(f"✓ ")
        print(f"  : {yeast_library['library_size']} ")
        print(f"  : {yeast_library['strategy']}")
        
        print(f"\n[]")
        for variant in yeast_library['variants']:
            print(f"\n  {variant['variant_id']}:")
            print(f"    : {len(variant['mutations'])}")
            print(f"    : {variant['priority']}")
            print(f"    :")
            for mut in variant['mutations']:
                print(f"      - {mut['position']}: {mut['from']} → {mut['to']} ({mut['region']})")
    
    # 5. 
    output_data = {
        'input': {
            'sequence': args.sequence,
            'length': len(args.sequence),
            'panel': args.panel,
        },
        'humanization_result': {
            'template': best['human_template'],
            'humanized_sequence': best['humanized_sequence'],
            'framework_identity': best['alignment_scores']['framework_identity'],
            'combined_score': best['combined_score'],
        },
        'mutation_suggestions': mutation_suggestions,
    }
    
    if yeast_library:
        output_data['yeast_display_library'] = yeast_library
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[INFO] : {args.output}")
    
    print("\n" + "=" * 80)
    print("！")
    print("=" * 80)
    print("\n：")
    print("1. ")
    print("2. ，")
    print("3. （≤3）")
    print("4. ")


if __name__ == "__main__":
    main()

