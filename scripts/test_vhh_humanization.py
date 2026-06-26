#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""VHH"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_humanization import humanize_vhh

# （VHH）
test_seq = "QVQLVQPGAELRKPGALLKVSCKASGYTFTSYYIDWVRQAPGQGLGWVGRIDPEDGGTNYAQKFQGRVTLTADTSTSTAYVELSSLRSEDTAVCYCVR"

print("=" * 80)
print("VHH")
print("=" * 80)

print(f"\n: {test_seq[:50]}...")
print(f": {len(test_seq)}aa")

print(f"\n[1] A（）")
print("-" * 80)
result = humanize_vhh(test_seq, panel='A', top_k=3)

if result['success']:
    print(f"✓ ")
    print(f"  : {result['best_match']['human_template']}")
    print(f"  : {result['best_match']['plan_name']}")
    print(f"  : {result['best_match']['humanized_length']}aa")
    print(f"  identity: {result['best_match']['alignment_scores']['framework_identity']:.1%}")
    print(f"  VHH hallmark: {result['best_match']['alignment_scores']['vhh_hallmark_score']:.1%}")
    print(f"\n  CDR:")
    for cdr_name, cdr_seq in result['cdrs'].items():
        if cdr_seq:
            print(f"    {cdr_name}: {cdr_seq}")
    
    # 
    if 'key_positions' in result:
        print(f"\n  :")
        kp = result['key_positions']
        print(f"    FR1-26: {kp.get('fr1_26', '-')} | CDR1(27): {kp.get('cdr1_start', '-')}")
        print(f"    FR2-55: {kp.get('fr2_55', '-')} | CDR2(56): {kp.get('cdr2_start', '-')}")
        print(f"    FR3-104: {kp.get('fr3_104', '-')}")
    
    # CDR
    if 'cdr_canonical' in result:
        print(f"\n  CDR:")
        for cdr_name, canonical_info in result['cdr_canonical'].items():
            if canonical_info.get('length', 0) > 0:
                print(f"    {cdr_name}: {canonical_info['canonical_class']} ({canonical_info['length']}aa, {canonical_info['confidence']:.1%})")
        
        # 
        if result['candidates']:
            best_cand = result['candidates'][0]
            if 'cdr_compatibility' in best_cand:
                compat = best_cand['cdr_compatibility']
                print(f"\n  CDR:")
                print(f"    : {compat['compatibility_score']:.1%}")
                if 'key_position_score' in compat:
                    print(f"    : {compat['key_position_score']:.1%}")
                if compat.get('warnings'):
                    print(f"    :")
                    for warning in compat['warnings']:
                        print(f"      - {warning}")
    
    print(f"\n  : {len(result['candidates'])}")
    for i, cand in enumerate(result['candidates'][:3], 1):
        scores = cand['alignment_scores']
        identity = scores.get('framework_identity', 0)
        combined = scores.get('combined_score', identity)
        cdr_compat = scores.get('cdr_compatibility_score', 1.0)
        key_pos = scores.get('key_position_score', 1.0)
        print(f"    {i}. {cand['template_id']}:")
        print(f"       identity: {identity:.1%} | CDR: {cdr_compat:.1%} | : {key_pos:.1%}")
        print(f"       : {combined:.3f}")
else:
    print(f"✗ : {result.get('error', 'Unknown error')}")

print(f"\n[2] B（）")
print("-" * 80)
result2 = humanize_vhh(test_seq, panel='B', top_k=2)
if result2['success']:
    print(f"✓ ")
    print(f"  : {result2['best_match']['human_template']}")
    print(f"  : {result2['best_match']['plan_name']}")
else:
    print(f"✗ : {result2.get('error', 'Unknown error')}")

print("\n" + "=" * 80)
print("")
print("=" * 80)

