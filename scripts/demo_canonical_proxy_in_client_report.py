#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Canonical Proxy 
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.report_blocks.canonical_proxy_background_customer import (
    render_canonical_proxy_background_customer_block,
    get_canonical_proxy_data_for_client_report,
)
import json


def main():
    print("=" * 80)
    print(" Canonical Proxy ")
    print("=" * 80)
    print()
    
    #  result_stage12.json 
    result_path = PROJECT_ROOT / "output" / "result_stage12.json"
    
    if result_path.exists():
        print(f"[1]  {result_path.name} ...")
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        
        #  canonical proxy 
        canonical_proxy_data = get_canonical_proxy_data_for_client_report(result)
        
        if canonical_proxy_data:
            print("  ✅  canonical proxy ")
            print(f"  - CDR1: {canonical_proxy_data.get('canonical_proxy_cdr1', {}).get('proxy_score', 'N/A')}")
            print(f"  - CDR2: {canonical_proxy_data.get('canonical_proxy_cdr2', {}).get('proxy_score', 'N/A')}")
        else:
            print("  ⚠️   canonical proxy ， N/A")
    else:
        print(f"[1] {result_path.name} ，")
        canonical_proxy_data = {
            "canonical_proxy_cdr1": {
                "length": 8,
                "cluster_id": "cdr1_L8_C9",
                "proxy_score": 1.0000,
            },
            "canonical_proxy_cdr2": {
                "length": 8,
                "cluster_id": "cdr2_L8_C22",
                "proxy_score": 1.0000,
            },
        }
    
    print()
    print("=" * 80)
    print(" Canonical Proxy （）:")
    print("=" * 80)
    print()
    
    # 
    section_content = render_canonical_proxy_background_customer_block(canonical_proxy_data)
    print(section_content)
    
    print()
    print("=" * 80)
    print(":")
    print("=" * 80)
    print(f"  -  \\n\\n: {section_content.startswith(chr(10) + chr(10))}")
    print(f"  -  \\n : {section_content.endswith(chr(10))}")
    print(f"  - : {'\\n\\n' in section_content}")
    print(f"  - : {'\\n| CDR |' in section_content and section_content.endswith(chr(10))}")
    
    # 
    output_file = PROJECT_ROOT / "output" / "demo_canonical_proxy_section.md"
    output_file.write_text(section_content, encoding="utf-8")
    print()
    print(f"✅ : {output_file}")
    print()
    
    # 
    print("=" * 80)
    print(":")
    print("=" * 80)
    print()
    
    demo_report = f"""## 2. IMGT 

|  |  |  |
|------|------|------|
| FR1 | EVQLVESGGGLVQPGGSLRLSCAAS | 26 |
| CDR1 | GRTFSSYAMG | 10 |
| FR2 | WFRQAPGKEREFVAA | 15 |
| CDR2 | ISWSGGSTYYADSVK | 15 |
| FR3 | GRFTISRDNSKNTLYLQMNSLRAEDTAVYYC | 32 |
| CDR3 | AA | 2 |

---

## 3. Germline 

**：** HUMAN_VH3_SCF_10
** Scaffold：** VH3-30

**：**
- FR1 Identity: 90.0%
- FR2 Identity: 80.0%
- FR3 Identity: 85.0%
-  Identity: 85.0%

**：**  Identity (85.0%) 。

---

{section_content}---

## 9. （Tier 0–3）
"""
    
    demo_report_file = PROJECT_ROOT / "output" / "demo_client_report_with_canonical_proxy.md"
    demo_report_file.write_text(demo_report, encoding="utf-8")
    print(demo_report)
    print()
    print(f"✅ : {demo_report_file}")
    print()
    print("=" * 80)
    print("✅ ")
    print("=" * 80)


if __name__ == "__main__":
    main()













