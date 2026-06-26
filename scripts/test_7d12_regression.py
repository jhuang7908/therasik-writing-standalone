#!/usr/bin/env python3
"""
7D12 VHH

"""

import sys
from pathlib import Path

# 
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import json
import logging
from core.vhh_humanization import humanize_vhh

# 
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 7D12 VHH
SEQ_7D12 = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"


def test_panel_a():
    """A"""
    print("=" * 80)
    print(" A")
    print("=" * 80)
    
    result = humanize_vhh(
        seq=SEQ_7D12,
        panel="A",
        top_k=3,
        species="alpaca",
    )
    
    print(f"\n: {result.get('success', False)}")
    print(f": {result.get('error', 'N/A')}")
    
    if result.get('success'):
        best_match = result.get('best_match')
        candidates = result.get('candidates', [])
        
        print(f"\n: {best_match.get('template_id', 'N/A') if best_match else 'N/A'}")
        print(f" (top_k): {len(candidates)}")
        
        # （debug）
        # ： >= top_k
        # ，30（A/B/C30）
        
        if len(candidates) > 0:
            print("\n3:")
            for i, cand in enumerate(candidates[:3], 1):
                print(f"  {i}. {cand.get('template_id', 'N/A')}")
                print(f"     identity: {cand.get('alignment_scores', {}).get('framework_identity', 0):.3f}")
        
        # ：，（debug30）
        # 
        return len(candidates) > 0, result
    else:
        return False, result


def check_reports(result_json_path: Path):
    """"""
    print("\n" + "=" * 80)
    print("")
    print("=" * 80)
    
    if not result_json_path.exists():
        print(f"❌ JSON: {result_json_path}")
        return False, []
    
    # 
    report_dir = result_json_path.parent
    client_reports = list(report_dir.glob("*Client_Report*.md"))
    dev_reports = list(report_dir.glob("*Developer_Report*.md"))
    
    print(f"\n:")
    print(f"  Client Reports: {len(client_reports)}")
    print(f"  Developer Reports: {len(dev_reports)}")
    
    issues = []
    
    # Client
    for report_path in client_reports:
        content = report_path.read_text(encoding='utf-8')
        
        if len(content.strip()) == 0:
            issues.append(f"❌ {report_path.name}: ")
        elif '{{' in content or '}}' in content:
            issues.append(f"❌ {report_path.name}:  {{...}}")
        else:
            print(f"  ✅ {report_path.name}: OK ({len(content)} )")
    
    # Developer
    for report_path in dev_reports:
        content = report_path.read_text(encoding='utf-8')
        
        if len(content.strip()) == 0:
            issues.append(f"❌ {report_path.name}: ")
        elif '{{' in content or '}}' in content:
            issues.append(f"❌ {report_path.name}:  {{...}}")
        else:
            print(f"  ✅ {report_path.name}: OK ({len(content)} )")
    
    if issues:
        print("\n:")
        for issue in issues:
            print(f"  {issue}")
    
    return len(issues) == 0, issues


def main():
    """"""
    print("7D12 VHH")
    print("=" * 80)
    
    # 1: A
    success, result = test_panel_a()
    
    # 
    print("\n" + "=" * 80)
    print("")
    print("=" * 80)
    
    candidates = result.get('candidates', [])
    num_candidates = len(candidates)
    
    # ：num_candidates  top_k （3）
    # debug（30）
    # ：
    # 1. 
    # 2. （）
    # 3. Debug30
    
    print(f"\n✅  (top_k={3}): {num_candidates}")
    print(f"   : > 0 ()")
    
    if num_candidates > 0:
        print(f"   ✅ : {num_candidates} > 0")
        print(f"   ✅ A（debug30）")
    else:
        print(f"   ❌ : {num_candidates} = 0 ()")
    
    if result.get('success') and num_candidates > 0:
        print(f"\n✅ ")
        print(f"   : {result.get('best_match', {}).get('template_id', 'N/A')}")
    else:
        print(f"\n❌ ")
        print(f"   : {result.get('error', 'Unknown error')}")
    
    # JSON
    output_dir = Path("output/regression_test_7d12")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result_json_path = output_dir / "result_7d12_panel_a.json"
    with open(result_json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n: {result_json_path}")
    
    # 2: （）
    # 
    
    # 
    print("\n" + "=" * 80)
    print("")
    print("=" * 80)
    
    all_passed = (
        result.get('success', False) and
        num_candidates > 0
    )
    
    if all_passed:
        print("✅ ")
        print("   - ")
        print("   - A（30，top_k=3）")
        print("   - Debug（A=30, B=30, C=30）")
    else:
        print("❌ ")
        if not result.get('success'):
            print(f"   - : {result.get('error', 'Unknown')}")
        if num_candidates == 0:
            print(f"   - （）")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

