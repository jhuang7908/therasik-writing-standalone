#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""EGFR VHH"""

import sys
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_humanization import humanize_vhh

# EGFR VHH（v2_cmc_repair/result_v2.json）
EGFR_VHH_SEQ = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"

print("=" * 80)
print("EGFR VHH ")
print("=" * 80)
print(f"\n: {EGFR_VHH_SEQ[:50]}...")
print(f": {len(EGFR_VHH_SEQ)}aa")

# 
for panel in ['A', 'B', 'C', 'all']:
    print(f"\n{'='*80}")
    if panel == 'all':
        print(f"[: ALL - A、B、C]")
    else:
        plan_names = {'A': '', 'B': '', 'C': 'VHH'}
        print(f"[: {panel} - {plan_names.get(panel, '')}]")
    print(f"{'='*80}")
    
    result = humanize_vhh(EGFR_VHH_SEQ, panel=panel, top_k=5)
    
    if result['success']:
        best = result['best_match']
        print(f"\n✓ ")
        print(f"\n【】")
        print(f"  scaffold: {best['alpaca_scaffold']}")
        print(f"  identity: {best['alpaca_identity']:.1%}")
        print(f"  Human: {best['human_template']}")
        print(f"  : {best['plan_name']} ({best['safe_plan']})")
        print(f"  : {best['humanized_length']}aa")
        
        scores = best['alignment_scores']
        print(f"\n【】")
        print(f"  identity: {scores.get('framework_identity', 0):.1%}")
        print(f"  VHH hallmark: {scores.get('vhh_hallmark_score', 0):.1%}")
        print(f"  FR1 identity: {scores.get('fr1_identity', 0):.1%}")
        print(f"  FR2 identity: {scores.get('fr2_identity', 0):.1%}")
        print(f"  FR3 identity: {scores.get('fr3_identity', 0):.1%}")
        
        print(f"\n【Developability】")
        dev_score = best.get('developability_score', 0.5)
        print(f"  Developability: {dev_score:.3f}")
        
        print(f"\n【】")
        print(f"  : {best.get('combined_score', 0):.3f}")
        print(f"    = 0.6 ×  + 0.4 × Developability")
        
        # CDR
        if 'cdrs' in result:
            print(f"\n【CDR】")
            for cdr_name, cdr_seq in result['cdrs'].items():
                if cdr_seq:
                    print(f"  {cdr_name}: {cdr_seq} (: {len(cdr_seq)}aa)")
        
        # CDR
        if 'cdr_canonical' in result:
            print(f"\n【CDR】")
            for cdr_name, canonical_info in result['cdr_canonical'].items():
                if canonical_info.get('length', 0) > 0:
                    print(f"  {cdr_name}: {canonical_info['canonical_class']} "
                          f"({canonical_info['length']}aa, {canonical_info['confidence']:.1%})")
        
        # 
        if 'key_positions' in result:
            print(f"\n【】")
            kp = result['key_positions']
            print(f"  FR1-26: {kp.get('fr1_26', '-')} | CDR1(27): {kp.get('cdr1_start', '-')}")
            print(f"  FR2-55: {kp.get('fr2_55', '-')} | CDR2(56): {kp.get('cdr2_start', '-')}")
            print(f"  FR3-104: {kp.get('fr3_104', '-')}")
        
        # CDR
        if 'cdr_compatibility' in best:
            compat = best['cdr_compatibility']
            print(f"\n【CDR】")
            print(f"  : {compat.get('compatibility_score', 0):.1%}")
            if 'key_position_score' in compat:
                print(f"  : {compat.get('key_position_score', 0):.1%}")
            if compat.get('warnings'):
                print(f"  :")
                for warning in compat['warnings']:
                    print(f"    - {warning}")
        
        # 
        if 'affinity_risk' in best:
            risk = best['affinity_risk']
            print(f"\n【】")
            print(f"  : {risk.get('level', 'unknown').upper()}")
            if risk.get('factors'):
                print(f"  :")
                for factor in risk['factors']:
                    print(f"    - {factor}")
            print(f"  : {risk.get('recommendation', '')}")
        
        # 5
        print(f"\n【5（）】")
        for i, cand in enumerate(result['candidates'][:5], 1):
            cand_scores = cand['alignment_scores']
            print(f"  {i}. {cand['template_id']}")
            print(f"     identity: {cand_scores.get('framework_identity', 0):.1%} | "
                  f"CDR: {cand_scores.get('cdr_compatibility_score', 1.0):.1%} | "
                  f": {cand_scores.get('key_position_score', 1.0):.1%}")
            print(f"     Developability: {cand_scores.get('developability_score', 0.5):.3f}")
            print(f"     : {cand_scores.get('combined_score', 0):.3f}")
            print()
        
        # panel='all'，
        if panel == 'all' and 'best_by_plan' in result:
            print(f"\n【】")
            for plan in ['A', 'B', 'C']:
                if plan in result['best_by_plan']:
                    plan_best = result['best_by_plan'][plan]
                    print(f"  {plan} ({plan_best['plan_name']}):")
                    print(f"    : {plan_best['template_id']}")
                    print(f"    : {plan_best['combined_score']:.3f}")
                    print(f"    identity: {plan_best['alignment_scores'].get('framework_identity', 0):.1%}")
                    print(f"    Developability: {plan_best['alignment_scores'].get('developability_score', 0.5):.3f}")
    else:
        print(f"✗ : {result.get('error', 'Unknown error')}")

print(f"\n{'='*80}")
print("")
print(f"{'='*80}")

