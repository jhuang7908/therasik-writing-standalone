#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


：
    python scripts/insert_affinity_section_into_template.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

AFFINITY_SECTION_MD = """
## 9. （Affinity Optimization）

### 9.1 

，（structure-free）， VHH （Affinity Optimization）。 IMGT 、CDR 、、、/ VHH ，。

---

### 9.2 （Affinity Hotspots）

 **{{affinity.hotspot_count}}** ：

|  |  |  |  |  |
|------|---------|--------|---------|-----------|
{{affinity.hotspot_table}}

---

### 9.3 （Mutation Candidates）

 **{{affinity.candidate_count}}** ， CMC、Developability ：

|  | → |  |  |  |  |
|------|--------|---------|---------|----------|--------|
{{affinity.candidate_table}}

---

### 9.4 （Affinity Optimization Variants）

#### Mild Strategy（）
{{affinity.variant_mild_table}}

#### Moderate Strategy（）
{{affinity.variant_moderate_table}}

#### Aggressive Strategy（）
{{affinity.variant_aggressive_table}}

---

### 9.5 （Narrative Summary）

{{affinity.narrative}}

> ：。 kon/koff ， CMC  developability ，。 early lead refinement （clone rescue）。

"""


def main():
    """："""
    template_path = PROJECT_ROOT / "reports" / "templates" / "vhh_full_report_template.md"
    
    if not template_path.exists():
        print(f"❌ : {template_path}")
        return 1
    
    text = template_path.read_text(encoding="utf-8")
    
    # 
    marker = "## 9. （Affinity Optimization）"
    if marker in text:
        print("[INFO] ✅ ，。")
        return 0
    
    # ： "## 9. " 
    insert_marker = "## 9. （Back-mutation）"
    if insert_marker in text:
        # （ ## ）
        lines = text.split("\n")
        insert_idx = None
        for i, line in enumerate(lines):
            if insert_marker in line:
                #  ## 
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("## ") and not lines[j].startswith("###"):
                        insert_idx = j
                        break
                break
        
        if insert_idx is not None:
            #  insert_idx 
            new_lines = lines[:insert_idx] + [AFFINITY_SECTION_MD.strip()] + lines[insert_idx:]
            new_text = "\n".join(new_lines)
        else:
            # ，
            new_text = text.rstrip() + "\n\n" + AFFINITY_SECTION_MD.strip() + "\n"
    else:
        # ，
        new_text = text.rstrip() + "\n\n" + AFFINITY_SECTION_MD.strip() + "\n"
    
    template_path.write_text(new_text, encoding="utf-8")
    print(f"[INFO] ✅ : {template_path}")
    return 0


if __name__ == "__main__":
    exit(main())

















