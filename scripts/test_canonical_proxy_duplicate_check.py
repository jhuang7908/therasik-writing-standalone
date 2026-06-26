#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Canonical Proxy 
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_dual_report_v3 import _assert_canonical_proxy_section_unique


def test_single_section():
    """：（）"""
    print("[ 1]  Canonical Proxy （）")
    test_content = """## 2. IMGT 

---

{{{{germline_section}}}}

---

## CDR Canonical Proxy（）

Canonical Proxy ...

---

## 9. 
"""
    test_file = Path("output/test_single_section.md")
    test_file.write_text(test_content, encoding="utf-8")
    
    try:
        _assert_canonical_proxy_section_unique(test_file)
        print("  ✅ ：")
    except ValueError as e:
        print(f"  ❌ ：{e}")
    finally:
        test_file.unlink()


def test_duplicate_sections():
    """：（）"""
    print("\n[ 2]  Canonical Proxy （）")
    test_content = """## 2. IMGT 

---

{{{{germline_section}}}}

---

## CDR Canonical Proxy（）

Canonical Proxy ...

---

## 9. 

---

## CDR Canonical Proxy（）

...
"""
    test_file = Path("output/test_duplicate_sections.md")
    test_file.write_text(test_content, encoding="utf-8")
    
    try:
        _assert_canonical_proxy_section_unique(test_file)
        print("  ❌ ：")
    except ValueError as e:
        print(f"  ✅ ：")
        print(f"     : {str(e)[:100]}...")
    finally:
        test_file.unlink()


def main():
    print("=" * 80)
    print(" Canonical Proxy ")
    print("=" * 80)
    print()
    
    test_single_section()
    test_duplicate_sections()
    
    print()
    print("=" * 80)
    print("✅ ")
    print("=" * 80)


if __name__ == "__main__":
    main()













