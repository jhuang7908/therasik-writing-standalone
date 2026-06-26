#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
VHH-SAFEdevelopability

 human_vh3_vhh_safe_templates.json，developability
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_developability import analyze_developability


def load_templates(path: Path) -> List[Dict[str, Any]]:
    """JSON"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_templates(templates: List[Dict[str, Any]], path: Path):
    """JSON"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)


def score_templates(templates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    developability
    
    Args:
        templates: 
    
    Returns:
        
    """
    total = len(templates)
    print(f"[INFO]  {total} developability...")
    
    for idx, tpl in enumerate(templates, 1):
        template_id = tpl.get('template_id', f'template_{idx}')
        
        # 
        consensus = tpl.get('consensus', {})
        framework_full = consensus.get('framework_full', '')
        fr2 = consensus.get('fr2', '')
        fr3 = consensus.get('fr3', '')
        
        if not framework_full:
            print(f"[WARN]  {template_id}  framework_full，")
            tpl['developability'] = {
                'score': 0.0,
                'liabilities': [],
                'fr2_risk': 1.0,
                'fr3_risk': 1.0,
                'notes': 'Missing framework sequence',
            }
            continue
        
        # developability
        try:
            dev_result = analyze_developability(
                framework_seq=framework_full,
                fr2_seq=fr2 if fr2 else None,
                fr3_seq=fr3 if fr3 else None,
            )
            
            tpl['developability'] = dev_result
            
            # 
            if idx % 10 == 0 or idx == total:
                print(f"[INFO] : {idx}/{total} ({idx*100//total}%) - {template_id}: score={dev_result['score']:.3f}")
        
        except Exception as e:
            print(f"[ERROR]  {template_id} developability: {e}")
            tpl['developability'] = {
                'score': 0.5,
                'liabilities': [],
                'fr2_risk': 0.5,
                'fr3_risk': 0.5,
                'notes': f'Error: {str(e)}',
            }
    
    print(f"[INFO] ！ {total} ")
    return templates


def print_statistics(templates: List[Dict[str, Any]]):
    """"""
    scores = [t.get('developability', {}).get('score', 0) for t in templates]
    liabilities_counts = [len(t.get('developability', {}).get('liabilities', [])) for t in templates]
    
    if scores:
        print(f"\n[] Developability:")
        print(f"  : {sum(scores)/len(scores):.3f}")
        print(f"  : {max(scores):.3f}")
        print(f"  : {min(scores):.3f}")
        
        # 
        high_score = sum(1 for s in scores if s >= 0.8)
        medium_score = sum(1 for s in scores if 0.6 <= s < 0.8)
        low_score = sum(1 for s in scores if s < 0.6)
        
        print(f"\n[] :")
        print(f"   (≥0.8): {high_score} ({high_score*100//len(scores)}%)")
        print(f"   (0.6-0.8): {medium_score} ({medium_score*100//len(scores)}%)")
        print(f"   (<0.6): {low_score} ({low_score*100//len(scores)}%)")
        
        # Liabilities
        total_liabilities = sum(liabilities_counts)
        templates_with_liabilities = sum(1 for c in liabilities_counts if c > 0)
        
        print(f"\n[] Liabilities:")
        print(f"  : {total_liabilities}")
        print(f"  : {templates_with_liabilities} ({templates_with_liabilities*100//len(templates)}%)")
        print(f"  : {total_liabilities/len(templates):.2f}")


def main():
    """"""
    # 
    input_path = Path("data/germlines/human_ig_aa/vh_scaffolds/human_vh3_vhh_safe_templates.json")
    output_path = input_path  # 
    
    if not input_path.exists():
        print(f"[ERROR] : {input_path}")
        return
    
    print("=" * 80)
    print("VHH-SAFEDevelopability")
    print("=" * 80)
    
    # 
    print(f"\n[INFO] : {input_path}")
    templates = load_templates(input_path)
    print(f"[INFO]  {len(templates)} ")
    
    # developability
    templates = score_templates(templates)
    
    # 
    print_statistics(templates)
    
    # 
    print(f"\n[INFO] : {output_path}")
    save_templates(templates, output_path)
    
    print("\n" + "=" * 80)
    print("！")
    print("=" * 80)


if __name__ == "__main__":
    main()


















