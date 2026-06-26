#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def verify_reports():
    """"""
    json_path = PROJECT_ROOT / "output/regression_test_7d12/classic_panel_rulebook_v1/vhh_classic_panel.json"
    client_report_path = PROJECT_ROOT / "output/7D12/7D12_VHH_Client_CRO_Report.md"
    dev_report_path = PROJECT_ROOT / "output/7D12/7D12_VHH_Developer_Audit_Report.md"
    
    print("=" * 80)
    print("")
    print("=" * 80)
    print()
    
    # JSON
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    
    # 
    client_content = client_report_path.read_text(encoding="utf-8")
    dev_content = dev_report_path.read_text(encoding="utf-8")
    
    all_passed = True
    
    # 1. 
    print("1. ")
    if client_report_path.exists():
        print("  ✓ Client CRO Report")
    else:
        print("  ✗ Client CRO Report")
        all_passed = False
    
    if dev_report_path.exists():
        print("  ✓ Developer Audit Report")
    else:
        print("  ✗ Developer Audit Report")
        all_passed = False
    print()
    
    # 2. 
    print("2. ")
    sensitive_keywords = ["sha256", "mutations_rules", "core/", "tests/", "byte-level", "unit test"]
    client_lower = client_content.lower()
    issues = []
    for keyword in sensitive_keywords:
        if keyword in client_lower:
            issues.append(keyword)
    
    if not issues:
        print("  ✓ ")
    else:
        print(f"  ✗ : {issues}")
        all_passed = False
    print()
    
    # 3. 
    print("3. ")
    required_keywords = ["Hallmark", "Vernier"]
    dev_lower = dev_content.lower()
    missing = []
    for keyword in required_keywords:
        if keyword.lower() not in dev_lower:
            missing.append(keyword)
    
    if not missing:
        print("  ✓ ")
    else:
        print(f"  ✗ : {missing}")
        all_passed = False
    print()
    
    # 4. CDR
    print("4. CDR")
    cdr_features = data.get("cdr_features", {})
    cdr1_seq = cdr_features.get("cdr1_seq", "")
    cdr2_seq = cdr_features.get("cdr2_seq", "")
    cdr1_len = str(cdr_features.get("cdr1_len", ""))
    cdr2_len = str(cdr_features.get("cdr2_len", ""))
    
    checks = [
        ("CDR1", cdr1_seq, client_content, dev_content),
        ("CDR2", cdr2_seq, client_content, dev_content),
        ("CDR1", cdr1_len, client_content, dev_content),
        ("CDR2", cdr2_len, client_content, dev_content),
    ]
    
    for name, value, client, dev in checks:
        client_ok = value in client
        dev_ok = value in dev
        if client_ok and dev_ok:
            print(f"  ✓ {name}: ")
        else:
            print(f"  ✗ {name}: ={'✓' if client_ok else '✗'}, ={'✓' if dev_ok else '✗'}")
            all_passed = False
    print()
    
    # 5. variant
    print("5. Variant")
    variant_count = len(data.get("classic_panel", []))
    expected = 8
    
    if variant_count == expected:
        print(f"  ✓ Variant: {variant_count}")
    else:
        print(f"  ✗ Variant: {variant_count} (: {expected})")
        all_passed = False
    
    # variant
    scaffold_count_client = len(re.findall(r"IGHV3-\d+\*01", client_content))
    scaffold_count_dev = len(re.findall(r"### 4\.\d+", dev_content))
    
    if scaffold_count_dev == variant_count:
        print(f"  ✓ variant: {scaffold_count_dev}")
    else:
        print(f"  ✗ variant: {scaffold_count_dev} (: {variant_count})")
        all_passed = False
    print()
    
    # 
    print("=" * 80)
    if all_passed:
        print("✅ ！")
    else:
        print("❌ ，")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    import sys
    success = verify_reports()
    sys.exit(0 if success else 1)

