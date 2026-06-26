#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""panel='all'A、B、C"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_humanization import humanize_vhh

# 
test_seq = "QVQLVQPGAELRKPGALLKVSCKASGYTFTSYYIDWVRQAPGQGLGWVGRIDPEDGGTNYAQKFQGRVTLTADTSTSTAYVELSSLRSEDTAVCYCVR"

print("=" * 80)
print(" panel='all' A、B、C")
print("=" * 80)

result = humanize_vhh(test_seq, panel='all', top_k=10)

if result['success']:
    candidates = result.get('candidates', [])
    print(f"\n✓ ")
    print(f": {len(candidates)}")
    
    # 
    plans = {}
    for cand in candidates:
        plan = cand.get('safe_plan', 'unknown')
        if plan not in plans:
            plans[plan] = []
        plans[plan].append(cand)
    
    print(f"\n:")
    for plan in sorted(plans.keys()):
        count = len(plans[plan])
        best = plans[plan][0]
        print(f"  {plan}: {count}")
        print(f"    : {best['template_id']}")
        print(f"    : {best['alignment_scores'].get('combined_score', 0):.3f}")
    
    print(f"\n（）:")
    best = result['best_match']
    print(f"  : {best['human_template']}")
    print(f"  : {best['safe_plan']} ({best['plan_name']})")
    print(f"  : {best.get('combined_score', 0):.3f}")
    
    # 
    if len(plans) >= 3:
        print(f"\n✓ （A、B、C）")
    else:
        print(f"\n⚠  {len(plans)} : {sorted(plans.keys())}")
    
    # （）
    if 'best_by_plan' in result:
        print(f"\n:")
        for plan in ['A', 'B', 'C']:
            if plan in result['best_by_plan']:
                best = result['best_by_plan'][plan]
                print(f"  {plan} ({best['plan_name']}):")
                print(f"    : {best['template_id']}")
                print(f"    : {best['combined_score']:.3f}")
                print(f"    identity: {best['alignment_scores'].get('framework_identity', 0):.1%}")
else:
    print(f"✗ : {result.get('error', 'Unknown error')}")

