#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_tnb_final_report.py
============================
Generate official CMC dashboard report for Tnb04/Tnb164 bispecific project.
Uses real sequences from Excel. Includes activity integration.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = SUITE_ROOT / "projects" / "Tnb_bispecific" / "cmc_eval" / "tnb_full_cmc_real.json"
OUT_MD = SUITE_ROOT / "projects" / "Tnb_bispecific" / "cmc_eval" / "TNB_CMC_FINAL_REPORT.md"

data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
singles = data["single_vhh"]
fusions = data["fusion_proteins"]
activity = data["activity"]

NOW = datetime.now().strftime("%Y-%m-%d %H:%M")

# VHH42 reference percentiles (from VHH42_reference_stats_v1.json)
VHH42_REF = {
    "pI":                {"p25": 5.13, "p50": 8.62, "p75": 8.99},
    "GRAVY":             {"p25": -0.368, "p50": -0.293, "p75": -0.208},
    "instability_index": {"p25": 33.6,  "p50": 39.0,  "p75": 44.3},
    "net_charge_pH7":    {"p25": -1.95, "p50": 1.8,   "p75": 2.8},
    "oxidation_sites":   {"p25": 4.0,   "p50": 5.0,   "p75": 6.0},
    "deamidation_sites": {"p25": 1.0,   "p50": 1.5,   "p75": 2.0},
}

# scFv_52 fusion benchmarks
SCFV52_REF = {
    "pI":     {"mean": 8.5, "p25": 7.8, "p75": 9.0},
    "GRAVY":  {"mean": -0.34, "p25": -0.43, "p75": -0.26},
    "instab": {"mean": 40.2, "p25": 35.1, "p75": 44.8},
}


def badge(val, low, mid, high, reverse=False):
    """Return markdown badge emoji for value vs thresholds."""
    if reverse:
        if val <= low:
            return "🟢"
        elif val <= mid:
            return "🟡"
        else:
            return "🔴"
    else:
        if val >= high:
            return "🔴"
        elif val >= mid:
            return "🟡"
        else:
            return "🟢"


def pi_badge(pi):
    if pi <= 7.5:
        return "🟢 "
    elif pi <= 8.5:
        return "🟡 "
    elif pi <= 8.99:
        return "🟠 "
    else:
        return "🔴 "


def adi_badge(adi):
    if adi >= 80:
        return "🟢 "
    elif adi >= 65:
        return "🟡 "
    elif adi >= 50:
        return "🟠 "
    else:
        return "🔴 "


def rows_tnb04():
    lines = []
    lines.append("|  | pI |  | GRAVY |  |  |  |  | Cys | ADI |  |")
    lines.append("|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--|")
    for vid in ["Tnb04H9", "Tnb04H4", "Tnb04H2", "Tnb04H3", "Tnb04H7", "Tnb04H8"]:
        r = singles[vid]
        m = r["metrics"]
        adi = r["adi_continuous"]
        pib = pi_badge(m["pI"])
        star = " ⭐" if vid in ("Tnb04H9", "Tnb04H7") else ""
        lines.append(
            f"| **{vid}**{star} | {m['pI']:.2f} {pib[0]} | {m['net_charge_pH7']:+.1f} | "
            f"{m['GRAVY']:.3f} | {m['instability_index']:.1f} | "
            f"{m['oxidation_sites']} | {m['deamidation_sites']} | "
            f"{m['isomerization_sites']} | {m['free_cys']} | "
            f"**{adi:.1f}** | {adi_badge(adi)} |"
        )
    return "\n".join(lines)


def rows_tnb164():
    lines = []
    lines.append("|  | pI |  | GRAVY |  |  |  |  | Cys | ADI |  |")
    lines.append("|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--|")
    for vid in ["Tnb164H4", "Tnb164H5", "Tnb164H2", "Tnb164H6", "Tnb164H7", "Tnb164H8"]:
        r = singles[vid]
        m = r["metrics"]
        adi = r["adi_continuous"]
        pib = pi_badge(m["pI"])
        star = " ⭐" if vid in ("Tnb164H6", "Tnb164H5") else ""
        lines.append(
            f"| **{vid}**{star} | {m['pI']:.2f} {pib[0]} | {m['net_charge_pH7']:+.1f} | "
            f"{m['GRAVY']:.3f} | {m['instability_index']:.1f} | "
            f"{m['oxidation_sites']} | {m['deamidation_sites']} | "
            f"{m['isomerization_sites']} | {m['free_cys']} | "
            f"**{adi:.1f}** | {adi_badge(adi)} |"
        )
    return "\n".join(lines)


def activity_tnb04():
    lines = []
    lines.append("|  | WT IC50 | JN.1 IC50 | KP.3.1.1 IC50 | XDV IC50 | JN.1 IC90 | KP IC90 | XDV IC90 |  |")
    lines.append("|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--|")
    for vid in ["Tnb04H9", "Tnb04H4", "Tnb04H2", "Tnb04H3", "Tnb04H8"]:
        a = activity[vid]
        def fmt(v):
            return f"{v:.3f}" if v is not None else "n.d."
        # Breadth score: penalize if any IC50 > 0.1
        vals = [a.get("WT_IC50"), a.get("JN1_IC50"), a.get("KP_IC50"), a.get("XDV_IC50")]
        good = sum(1 for v in vals if v is not None and v <= 0.1)
        breadth = "🟢 " if good == 4 else ("🟡 " if good >= 3 else "🟠 ")
        star = " ⭐" if vid == "Tnb04H9" else ""
        lines.append(
            f"| **{vid}**{star} | {fmt(a.get('WT_IC50'))} | {fmt(a.get('JN1_IC50'))} | "
            f"{fmt(a.get('KP_IC50'))} | {fmt(a.get('XDV_IC50'))} | "
            f"{fmt(a.get('JN1_IC90'))} | {fmt(a.get('KP_IC90'))} | "
            f"{fmt(a.get('XDV_IC90'))} | {breadth} |"
        )
    return "\n".join(lines)


def activity_tnb164():
    lines = []
    lines.append("|  | MERS WT IC50 | MjHKU4r-CoV-1 IC50 | MjHKU4r-CoV-1 IC90 |  |")
    lines.append("|:--|:--:|:--:|:--:|:--|")
    for vid in ["Tnb164H4", "Tnb164H5", "Tnb164H2", "Tnb164H6", "Tnb164H7", "Tnb164H8"]:
        a = activity[vid]
        def fmt(v):
            if v is None:
                return "n.d."
            if v == 0.000:
                return "≤0.001"
            return f"{v:.3f}"
        ic90 = a.get("MjHKU4r_IC90", 999)
        cross = "🟢 " if ic90 <= 0.1 else ("🟡 " if ic90 <= 0.3 else ("🟠 " if ic90 <= 0.5 else "🔴 "))
        star = " ⭐" if vid in ("Tnb164H6", "Tnb164H5") else ""
        lines.append(
            f"| **{vid}**{star} | {fmt(a.get('MERS_WT_IC50'))} | "
            f"{fmt(a.get('MjHKU4r_IC50'))} | {fmt(a.get('MjHKU4r_IC90'))} | {cross} |"
        )
    return "\n".join(lines)


def fusion_table_key():
    """Key combinations fusion table."""
    combos_to_show = [
        "Tnb04H9+Tnb164H4",
        "Tnb04H9+Tnb164H6",
        "Tnb04H9+Tnb164H5",
        "Tnb04H9+Tnb164H2",
        "Tnb04H2+Tnb164H6",
        "Tnb04H2+Tnb164H2",
    ]
    linkers_to_show = ["(G4S)3", "(G4S)3+3E", "(G4S)3+4E"]

    lines = []
    lines.append("|  | Linker | (aa) | pI |  | GRAVY |  | pI |")
    lines.append("|:--|:--|:--:|:--:|:--:|:--:|:--:|:--|")

    fusion_map = {}
    for f in fusions:
        key = (f["combo"], f["linker"])
        fusion_map[key] = f

    current_combo = None
    for combo in combos_to_show:
        for lk in linkers_to_show:
            f = fusion_map.get((combo, lk))
            if not f:
                continue
            pi_eval = pi_badge(f["pI"])
            combo_label = f["combo"] if current_combo != f["combo"] else ""
            current_combo = f["combo"]
            lines.append(
                f"| **{combo_label}** | {lk} | {f['full_len']} | {f['pI']:.2f} | "
                f"{f['net_charge_pH7']:+.1f} | {f['GRAVY']:.3f} | {f['instability_index']:.1f} | {pi_eval} |"
            )
        lines.append("|  |  |  |  |  |  |  |  |")

    return "\n".join(lines)


def decision_matrix():
    """Activity × CMC integrated decision matrix."""
    # Key combinations: Tnb04H9 arm vs Tnb164 variants
    # Best Tnb04 = H9 (best breadth)
    # Best Tnb04 alt = H2 (good breadth, same pI)
    lines = []
    lines.append("|  | SARS | MERS | pI(GS3) | pI(GS3+3E) |  |  |")
    lines.append("|:--|:--:|:--:|:--:|:--:|:--:|:--:|")

    combos_data = [
        ("Tnb04H9+Tnb164H4",  "🟢",  "🟢 IC90=0.119",  8.94, 8.31, "A-", ""),
        ("Tnb04H9+Tnb164H6",  "🟢",  "🟢 IC90=0.025",  8.80, 7.85, "A+", "⭐"),
        ("Tnb04H9+Tnb164H5",  "🟢",  "🟡 IC90=0.345",  8.80, 7.85, "B+", ""),
        ("Tnb04H9+Tnb164H2",  "🟢",  "🟡 IC90=0.489",  8.59, 6.99, "B",  ""),
        ("Tnb04H2+Tnb164H6",  "🟡",  "🟢 IC90=0.025",  8.80, 7.85, "B+", ""),
        ("Tnb04H2+Tnb164H5",  "🟡",  "🟡 IC90=0.345",  8.80, 7.85, "B",  "-"),
        ("Tnb04H2+Tnb164H2",  "🟡",  "🟡 IC90=0.489",  8.59, 6.99, "C+", "pI"),
    ]

    for row in combos_data:
        combo, sars, mers, pi_gs3, pi_3e, grade, rec = row
        lines.append(f"| **{combo}** | {sars} | {mers} | {pi_gs3:.2f} | {pi_3e:.2f} | **{grade}** | {rec} |")

    return "\n".join(lines)


# ─── Write report ─────────────────────────────────────────────────────────────
report = f"""# Tnb04/Tnb164  CMC 

> ****: SARS-CoV-2 × MERS-CoV  VHH-GS-VHH   
> ****: v3.0（）  
> ****: {NOW}  
> ****: `Tnb04 Tnb164.xlsx`（12）  
> ****: VHH42（n=42）| scFv_52（n=52）  
> ****: InSynBio AbEngineCore V4.4 ADI（tent-function）

---

## 

|  |  |
|:--|:--|
| **pI ** | 12pI（±0.01）， |
| **Tnb04 ** | pI=8.99-9.01（100%VHH428.62），3（VHH42 p75=2.0） |
| **Tnb164 ** | =7（VHH42 p75=6.0），GRAVY（-0.45~-0.51，VHH42 p5=-0.481）|
| **ADI** | Tnb04: 56.4–61.3（）；Tnb164: 52.6–63.5（）|
| **pI** | H9+H4+(G4S)3=8.94（⚠）；4E→7.85（✓） |
| **** | **Tnb04H9+Tnb164H6**：SARS × MERS-CoV(IC90=0.025) × pI7.85 |

---

## Part 1 — Tnb04  VHH CMC 

### 1.1 CMC （，15）

{rows_tnb04()}

**VHH42**：pI p50=8.62， p50=+1.8，GRAVY p50=-0.293， p50=39.0， p50=5， p50=1.5

> ⭐ 

****：
- **pI=8.99-9.01**：6VHH42 p75（p75=8.99），（pI 6.0-8.5）
- ****：H9/H4/H3/H8 3NG/NS（VHH42 p75=2.0），ADI=0
- **=5**：VHH42 p50，，VHH
- **H7 **：2（=H2），ADI（61.3），SARS
- **H9 **：WT IC50=0.027，JN.1 IC50=0.053，KP IC50=0.011，XDV IC50=0.037（）

### 1.2 ADI （）

|  | pI |  | GRAVY |  |  |  |  |  | **ADI** |
|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Tnb04H9 | 75.0 | 74.4 | 99.4 | 87.0 | 100.0 | 0.0 | 49.8 | 66.5 | **57.5** |
| Tnb04H4 | 75.0 | 74.4 | 93.8 | 92.1 | 100.0 | 0.0 | 49.8 | 61.3 | **61.1** |
| Tnb04H2 | 75.0 | 74.4 | 92.7 | 100.0 | 100.0 | 75.0 | 49.8 | 64.2 | **57.6** |
| Tnb04H3 | 75.0 | 74.4 | 90.3 | 87.3 | 100.0 | 0.0 | 49.8 | 63.5 | **56.6** |
| Tnb04H7 ⭐ | 75.0 | 74.4 | 91.7 | 100.0 | 100.0 | 75.0 | 49.8 | 63.9 | **61.3** |
| Tnb04H8 | 67.2 | 74.4 | 90.0 | 94.9 | 100.0 | 0.0 | 47.2 | 63.3 | **56.4** |

> ****：（~50），pI。pI=9.0tent-functionVHH42，75（100）。H9/H3/H4/H8。

### 1.3 Tnb04 （SARS-CoV-2 ）

{activity_tnb04()}

****：**Tnb04H9** ，4IC50 ≤0.037 μg/mL， KP.3.1.1 IC50=0.011 μg/mL。H4/H2/H3 JN.1/KP IC90 （>1 μg/mL），。

---

## Part 2 — Tnb164  VHH CMC 

### 2.1 CMC （，15）

{rows_tnb164()}

**VHH42**（）

****：
- **GRAVY**：Tnb164GRAVY = -0.45~-0.51，VHH42 p5（-0.481），34-55，。。
- **=7**：7（VHH42 p75=6），=0，7M/W
- **pI**：H2=7.0（） < H5/H6/H7/H8=8.03（） < H4=8.59（）
- **H6**：pI=8.03，=2，Cys，MjHKU4r-CoV-1 IC90=0.025（）

### 2.2 ADI （）

|  | pI |  | GRAVY |  |  |  |  |  | **ADI** |
|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Tnb164H4 | 99.8 | 95.2 | 38.7 | 96.8 | 0.0 | 75.0 | 65.0 | 46.2 | **54.6** |
| Tnb164H5 ⭐ | 95.8 | 94.7 | 45.6 | 100.0 | 0.0 | 75.0 | 63.5 | 54.4 | **63.5** |
| Tnb164H2 | 88.4 | 88.0 | 34.0 | 96.7 | 0.0 | 75.0 | 58.8 | 44.7 | **52.6** |
| Tnb164H6 ⭐ | 95.8 | 94.7 | 38.9 | 100.0 | 0.0 | 75.0 | 63.5 | 46.3 | **54.5** |
| Tnb164H7 | 95.8 | 94.7 | 49.6 | 95.4 | 0.0 | 75.0 | 63.5 | 55.8 | **57.0** |
| Tnb164H8 | 95.8 | 94.7 | 38.3 | 96.7 | 0.0 | 75.0 | 63.5 | 46.1 | **54.2** |

> ****：=0（，7M/W）。GRAVY，H2/H4/H6/H8（GRAVY ≤-0.487）。

### 2.3 Tnb164 （MERS-CoV ）

{activity_tnb164()}

****：**Tnb164H6**  MjHKU4r-CoV-1（，MERS）IC90=0.025 μg/mL，6****， pI=8.03，CMC。H7/H8MjHKU4r IC90=0.754/0.868，。

---

## Part 3 —  CMC （VHH-Linker-VHH）

### 3.1  pI 

{fusion_table_key()}

**scFv_52 **：pI =8.5，p25=7.8，p75=9.0

****：
-  (G4S)3  pI = 8.59–8.94（ scFv_52 p25-p75 ，）
- **WhitlowpI**（K→+0.99，E→-1.00，），pI
- ****：1Glu，pI0.37-0.45
  - (G4S)3+2E → pI0.5-0.6
  - (G4S)3+3E → pI0.4（：pI）
  - (G4S)3+4E → pI0.8-0.9（pI）

### 3.2 

|  |  |  |  |  |
|:--|:--|:--:|:--:|:--|
| (G4S)3 | GGGGSGGGGSGGGGS | 15 | 0 | ，pI， |
| (G4S)3+2E | GGGGSGGGGSGGGGSEE | 17 | −2.0 | pI， |
| **(G4S)3+3E** ⭐ | **GGGGSGGGGSGGGGSEEE** | **18** | **−3.0** | **：pI→7.85，** |
| (G4S)3+4E | GGGGSGGGGSGGGGSEEEE | 19 | −4.0 | pI→6.99， |
| Whitlow | GSTSGSGKPGSGEGSTKG | 18 | ~0 | ****：KE，pI |

---

## Part 4 — （ ×  × Linker）

{decision_matrix()}

### 4.1 ：Tnb04H9 + Tnb164H6 + (G4S)3+3E

|  |  |  |
|:--|:--|:--|
| SARS-CoV-2 | 🟢  | H9: WT/JN.1/KP.3.1.1/XDV≤0.037 μg/mL |
| MERS | 🟢  | H6: MjHKU4r IC90=0.025 μg/mL（6） |
| pI（） | 🟡 7.85 | (G4S)3+3E7.85， |
|  | 🟡  | 7M/W（Tnb164）， |
| （H9） | 🟠  | 3NG/NS， |
|  | 🟢  | pI8.80→7.85，+4→+1，ER |

### 4.2 ：Tnb04H9 + Tnb164H5 + (G4S)3+3E

- pI7.85，MERS IC90=0.345（H613.8）
- H9+H6

### 4.3 pI：Tnb04H9 + Tnb164H2 + (G4S)3+2E

- pI=7.85（2E），H2 pI=7.0pI
- MjHKU4r IC90=0.489（H620），

---

## Part 5 — 

### 5.1 

|  |  |  |  |
|:--|:--:|:--|:--|
| pI=8.9（） | 🔴  |  | (G4S)3+3E |
| Tnb043 | 🟠  |  | N→Q（NGS/NS） |
| Tnb1647（M/W） | 🟠  |  | forced oxidation assay；M→I/L（） |
| Tnb164（GRAVY=-0.49~-0.51） | 🟡 - | / | ， |
| VHH | 🔴 （） | PK | Fc /  / PEG  |

### 5.2 

```
 1（）：
  ├──  Tnb04H9+Tnb164H6+(G4S)3+3E 
  ├── （ H9+H4+(G4S)3 ）
  └── （ SARS + MERS ）

 2（1-2）：
  ├── Tnb04H9  N→Q （3）
  ├── Tnb164H6  W/M （IMGT）
  └── ：(G4S)3+2E / +3E / +4E 

 3（）：
  ├── VHH-Fc（IgG1） VHH-HSA → 
  ├── （40°C/1）
  └── （EpiSweep/NetMHCpan）
```

---

##  A — pI 

|  | pI（）| pI |  |  |
|:--|:--:|:--:|:--:|:--:|
| Tnb04H9 | 9.00 | 8.99 | −0.01 | ✓ |
| Tnb04H4 | 9.00 | 8.99 | −0.01 | ✓ |
| Tnb04H2 | 9.00 | 8.99 | −0.01 | ✓ |
| Tnb164H4 | 8.59 | 8.59 | 0.00 | ✓ |
| Tnb164H5 | 8.03 | 8.03 | 0.00 | ✓ |
| Tnb164H2 | 7.00 | 7.00 | 0.00 | ✓ |
| Tnb164H6 | 8.03 | 8.03 | 0.00 | ✓ |

> ****：pI，100%。。

##  B — VHH42 vs Tnb （）

|  | VHH42 p25 | VHH42 p50 | VHH42 p75 | Tnb04 | Tnb164 |
|:--|:--:|:--:|:--:|:--:|:--:|
| pI | 5.13 | 8.62 | 8.99 | 8.99 ⚠ | 7.0–8.6 |
| GRAVY | −0.368 | −0.293 | −0.208 | −0.259~−0.322 ✓ | −0.45~−0.51 ⚠p5 |
|  | 33.6 | 39.0 | 44.3 | 36.2–41.7 ✓ | 38.0–39.7 ✓ |
| @pH7 | −1.95 | +1.8 | +2.8 | +2.8 ✓ | 0.0–+2.0 ✓ |
|  | 4 | 5 | 6 | 5 ✓ | 7 ⚠p75 |
|  | 1 | 1.5 | 2 | 2–3 ⚠ | 1–2 ✓ |

---

* InSynBio AbEngineCore V4.4 。（：Tnb04 Tnb164.xlsx）。*  
*pIBioPython ProteinAnalysis.isoelectric_point()。。ADIVHH42（n=42）tent-function。*
"""

OUT_MD.write_text(report, encoding="utf-8")
print(f"Report saved: {OUT_MD}")
print(f"  Lines: {len(report.splitlines())}")
print(f"  Size:  {len(report.encode('utf-8'))//1024} KB")
