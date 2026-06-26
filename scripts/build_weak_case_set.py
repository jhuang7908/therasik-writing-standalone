#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 AbEvaluator  WARN / FAIL ，“”（Algorithmic Rejects）。
， CMC / Developability / Structural QC 。

：
- 
- （）

：projects/*/output/*_qc_bundle.json 
：data/vhh_weak_cases/auto_flagged.csv
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any

REPO = Path(__file__).resolve().parents[1]
PROJECTS_DIR = REPO / "projects"
OUT_DIR = REPO / "data" / "vhh_weak_cases"
OUT_CSV = OUT_DIR / "auto_flagged.csv"


def find_qc_bundles() -> List[Path]:
    """ qc_bundle / result.json"""
    bundles = []
    #  projects  json ，
    for p in PROJECTS_DIR.rglob("*.json"):
        if "qc_bundle" in p.name or "result" in p.name or "report" in p.name:
            bundles.append(p)
    return bundles


def extract_failures(bundle_path: Path) -> List[Dict[str, Any]]:
    """ JSON  FAIL/WARN """
    failures = []
    try:
        data = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception:
        return failures

    if not isinstance(data, dict):
        return failures

    # 
    seq = data.get("sequence", "")
    if not seq and "input" in data and isinstance(data["input"], dict):
        seq = data["input"].get("sequence", "")
    if not seq and "vhh_sequence" in data:
        seq = data["vhh_sequence"]
        
    project_id = bundle_path.parent.parent.name if bundle_path.parent.name == "output" else bundle_path.parent.name
    
    flags = []
    #  1:  flags
    if "flags" in data and isinstance(data["flags"], list):
        flags = data["flags"]
    #  2: _qa_audit
    elif "_qa_audit" in data and "flags" in data["_qa_audit"]:
        flags = data["_qa_audit"]["flags"]
    #  3: _qa 
    elif "_qa" in data and isinstance(data["_qa"], dict) and "flags" in data["_qa"]:
        flags = data["_qa"]["flags"]
    #  4:  evaluation_result 
    elif "evaluation_result" in data and isinstance(data["evaluation_result"], dict):
        er = data["evaluation_result"]
        if "flags" in er:
            flags = er["flags"]
        elif "_qa_audit" in er and "flags" in er["_qa_audit"]:
            flags = er["_qa_audit"]["flags"]
    #  5: ab_evaluator  overall_flags
    elif "ab_evaluator" in data and isinstance(data["ab_evaluator"], dict):
        flags = data["ab_evaluator"].get("overall_flags", [])
            
    for flag in flags:
        # flag  "module:level:message"
        parts = flag.split(":", 2)
        if len(parts) >= 3:
            module, level, msg = parts[0], parts[1], parts[2]
            if level in ("FAIL", "WARN"):
                failures.append({
                    "sequence": seq,
                    "project_id": project_id,
                    "file_source": bundle_path.name,
                    "module": module,
                    "level": level,
                    "message": msg.strip(),
                    "label_type": "algorithmic_reject"
                })
                
    return failures


def main() -> int:
    bundles = find_qc_bundles()
    print(f"Found {len(bundles)} potential result JSONs.")
    
    all_failures = []
    for b in bundles:
        fails = extract_failures(b)
        all_failures.extend(fails)
        
    if not all_failures:
        print("No FAIL/WARN records found in historical runs.")
        return 0
        
    #  ( sequence + message)
    unique_failures = []
    seen = set()
    for f in all_failures:
        k = (f["sequence"], f["message"])
        if k not in seen:
            seen.add(k)
            unique_failures.append(f)
            
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "sequence", "project_id", "file_source", "module", "level", "message", "label_type"
        ])
        writer.writeheader()
        writer.writerows(unique_failures)
        
    print(f"Extracted {len(unique_failures)} unique FAIL/WARN records to {OUT_CSV}")
    
    #  Markdown 
    md_path = OUT_DIR / "README.md"
    md_content = f"""# VHH Weak Cases (Algorithmic Rejects)

 `AbEvaluator`  `WARN`  `FAIL` 。

- ****: {len(unique_failures)}
- ****: `scripts/build_weak_case_set.py`
- ****: 、。

## 
"""
    
    # 
    stats = {}
    for f in unique_failures:
        mod_lvl = f"{f['module']}:{f['level']}"
        stats[mod_lvl] = stats.get(mod_lvl, 0) + 1
        
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        md_content += f"- **{k}**: {v} \n"
        
    md_path.write_text(md_content, encoding="utf-8")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
