#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""developability"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_humanization import humanize_vhh

# 
test_seq = "QVQLVQPGAELRKPGALLKVSCKASGYTFTSYYIDWVRQAPGQGLGWVGRIDPEDGGTNYAQKFQGRVTLTADTSTSTAYVELSSLRSEDTAVCYCVR"

print("=" * 80)
print("Developability")
print("=" * 80)

result = humanize_vhh(test_seq, panel='A', top_k=5)

if result['success']:
    print(f"\n✓ ")
    print(f"\n:")
    best = result['best_match']
    print(f"  : {best['human_template']}")
    print(f"  identity: {best['alignment_scores']['framework_identity']:.1%}")
    print(f"  Developability: {best.get('developability_score', 0):.3f}")
    print(f"  : {best.get('combined_score', 0):.3f}")
    
    print(f"\n5（）:")
    for i, cand in enumerate(result['candidates'][:5], 1):
        scores = cand['alignment_scores']
        print(f"  {i}. {cand['template_id']}")
        print(f"     identity: {scores.get('framework_identity', 0):.1%}")
        print(f"     Developability: {scores.get('developability_score', 0.5):.3f}")
        print(f"     : {scores.get('combined_score', 0):.3f}")
        print()
else:
    print(f"✗ : {result.get('error', 'Unknown error')}")


















