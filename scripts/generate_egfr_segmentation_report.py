#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EGFR VHH（JSONMD）

segmentation_provenance。
"""

import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.segmentation.anarcii_adapter import run_anarcii_imgt
from core.segmentation.json_validator import validate_segmentation_provenance

# EGFR VHH
EGFR_VHH_SEQ = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"

PROJECT_ID = "EGFR_7D12_VHH"
TARGET = "EGFR"


def generate_segmentation_report_json(seq: str, output_path: Path) -> dict:
    """
    provenanceJSON
    
    Returns:
        
    """
    print(f"[INFO] ...")
    print(f"  : {len(seq)} aa")
    print(f"  50: {seq[:50]}...")
    
    # 
    segmentation, numbering, provenance = run_anarcii_imgt(
        seq=seq,
        species="camelid",
        chain="H",
        allow_partial=True,
        max_mismatches=0
    )
    
    print(f"[INFO] ")
    print(f"  : {provenance['method']}")
    print(f"  : {provenance['implementation']['package']} v{provenance['implementation']['version']}")
    
    # 
    report = {
        "project_id": PROJECT_ID,
        "target": TARGET,
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input": {
            "sequence": seq,
            "length": len(seq),
            "species": "camelid",
            "chain": "H"
        },
        "segmentation": {
            "regions": segmentation,
            "numbering": numbering[:20] if len(numbering) > 20 else numbering,  # 20
            "total_numbering_positions": len(numbering)
        },
        "segmentation_provenance": provenance
    }
    
    # provenance
    print(f"[INFO] provenance...")
    is_valid, errors = validate_segmentation_provenance(report)
    if is_valid:
        print(f"  ✅ Provenance")
    else:
        print(f"  ⚠️ Provenance:")
        for error in errors:
            print(f"    - {error}")
    
    # JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"[INFO] JSON: {output_path}")
    
    return report


def generate_segmentation_report_md(report: dict, output_path: Path) -> None:
    """
    MD
    """
    seg = report["segmentation"]["regions"]
    prov = report["segmentation_provenance"]
    
    md_content = f"""# EGFR VHH 

**ID:** {report['project_id']}  
**:** {report['target']}  
**:** {report['analysis_date']}

---

## 1. 

**:**
```
{report['input']['sequence']}
```

**:**
- : {report['input']['length']} aa
- : {report['input']['species']}
- : {report['input']['chain']}

---

## 2. IMGT 

|  |  |  |
|------|------|------|
| FR1 | {seg.get('FR1', '')} | {len(seg.get('FR1', ''))} |
| CDR1 | {seg.get('CDR1', '')} | {len(seg.get('CDR1', ''))} |
| FR2 | {seg.get('FR2', '')} | {len(seg.get('FR2', ''))} |
| CDR2 | {seg.get('CDR2', '')} | {len(seg.get('CDR2', ''))} |
| FR3 | {seg.get('FR3', '')} | {len(seg.get('FR3', ''))} |
| CDR3 | {seg.get('CDR3', '')} | {len(seg.get('CDR3', ''))} |
| FR4 | {seg.get('FR4', '')} | {len(seg.get('FR4', ''))} |

**:**
```
: {report['input']['sequence']}
: {seg.get('FR1', '')}{seg.get('CDR1', '')}{seg.get('FR2', '')}{seg.get('CDR2', '')}{seg.get('FR3', '')}{seg.get('CDR3', '')}{seg.get('FR4', '')}
: {'✅ ' if report['input']['sequence'] == seg.get('FR1', '')+seg.get('CDR1', '')+seg.get('FR2', '')+seg.get('CDR2', '')+seg.get('FR3', '')+seg.get('CDR3', '')+seg.get('FR4', '') else '❌ '}
```

---

## 3.  (Segmentation Provenance)

### 3.1 

- **:** `{prov['method']}`
- **:** `{prov['scheme']}`

### 3.2 

- **:** `{prov['implementation']['package']}`
- **:** `{prov['implementation']['version']}`
- **Python:** `{prov['implementation']['python']}`
- **:** `{prov['implementation']['platform']}`
{f"- **Git Commit:** `{prov['implementation']['commit']}`" if prov['implementation'].get('commit') else ""}

### 3.3 

- **:** {prov['parameters']['species']}
- **:** {prov['parameters']['chain']}
- **:** {prov['parameters']['allow_partial']}
- **:** {prov['parameters']['max_mismatches']}
- **Fallback:** {', '.join(prov['parameters']['fallbacks'])}
{f"- **Fallback:** {', '.join(prov['parameters'].get('fallbacks_used', []))}" if prov['parameters'].get('fallbacks_used') else ""}

### 3.4  (Evidence)

#### 10

|  |  |
|------|--------|
{chr(10).join(f"| {item['pos']} | {item['aa']} |" for item in prov['evidence']['numbering_first_10'][:10])}

####  (IMGT)

|  |  |  |
|------|----------|----------|
| FR1 | {prov['evidence']['boundaries']['FR1'][0]} | {prov['evidence']['boundaries']['FR1'][1]} |
| CDR1 | {prov['evidence']['boundaries']['CDR1'][0]} | {prov['evidence']['boundaries']['CDR1'][1]} |
| FR2 | {prov['evidence']['boundaries']['FR2'][0]} | {prov['evidence']['boundaries']['FR2'][1]} |
| CDR2 | {prov['evidence']['boundaries']['CDR2'][0]} | {prov['evidence']['boundaries']['CDR2'][1]} |
| FR3 | {prov['evidence']['boundaries']['FR3'][0]} | {prov['evidence']['boundaries']['FR3'][1]} |
| CDR3 | {prov['evidence']['boundaries']['CDR3'][0]} | {prov['evidence']['boundaries']['CDR3'][1]} |
| FR4 | {prov['evidence']['boundaries']['FR4'][0]} | {prov['evidence']['boundaries']['FR4'][1]} |

---

## 4. 

**Provenance:** ✅ 

：
- ✅ `segmentation_provenance.method` 
- ✅ `segmentation_provenance.scheme == "imgt"`
- ✅ `implementation.package`  `implementation.version` 
- ✅ `evidence.boundaries` 
{f"- ✅ methodpackage" if prov['method'] == 'anarcii' and prov['implementation']['package'] == 'anarcii' else ""}

---

## 5. 

 **{prov['method']}** ， **{prov['implementation']['package']}** （ {prov['implementation']['version']}）。

7（FR1-4, CDR1-3），IMGT。

**:** ✅ JSON，。

---

*: {report['analysis_date']}*
"""
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md_content, encoding="utf-8")
    print(f"[INFO] MD: {output_path}")


def main():
    """"""
    print("=" * 80)
    print("EGFR VHH ")
    print("=" * 80)
    
    # 
    output_dir = PROJECT_ROOT / "projects" / PROJECT_ID / "segmentation_report"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON
    json_path = output_dir / f"segmentation_report_{timestamp}.json"
    report = generate_segmentation_report_json(EGFR_VHH_SEQ, json_path)
    
    # MD
    md_path = output_dir / f"segmentation_report_{timestamp}.md"
    generate_segmentation_report_md(report, md_path)
    
    print("\n" + "=" * 80)
    print("✅ ！")
    print("=" * 80)
    print(f"\n:")
    print(f"  - JSON: {json_path}")
    print(f"  - MD: {md_path}")
    print()


if __name__ == "__main__":
    main()

