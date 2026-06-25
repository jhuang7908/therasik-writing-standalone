"""
Update all MD files in immunogenicity_knowledge_base to reflect the new
138-entry database state (Tier C cleared, Etesevimab removed, 3 new drugs added).

Run from: D:\\InSynBio-AI-Research\\Antibody_Engineer_Suite
"""
import re
import os
from datetime import date

BASE   = "Antibody_Engineer_Suite/data/immunogenicity_knowledge_base"
TODAY  = date.today().isoformat()   # 2026-04-03

# ══════════════════════════════════════════════════════════════════════════════
# Helper
# ══════════════════════════════════════════════════════════════════════════════
def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"  Wrote {path}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. INDEX.md
# ══════════════════════════════════════════════════════════════════════════════
p = f"{BASE}/INDEX.md"
t = read(p)

t = t.replace("136-antibody ADA panel", "138-antibody ADA panel")
t = t.replace("**Panel size**: 136 antibodies", "**Panel size**: 138 antibodies")
t = t.replace("Master table (136 antibodies, all fields)", "Master table (138 antibodies, all fields)")
t = t.replace("136 antibodies", "138 antibodies")  # catch-all

# Tier stats line (94/136 69%, 36/136 26%, 6/136 4%)
t = t.replace("**Tier A** (94/136, 69%)", "**Tier A** (99/138, 72%)")
t = t.replace("**Tier B** (36/136, 26%)", "**Tier B** (39/138, 28%)")
t = t.replace("**Tier C** (6/136, 4%): Known data quality issues — exclude from quantitative analyses",
              "**Tier C**: 0 — all formerly-Tier-C entries were upgraded (Tier A/B) or removed (Etesevimab, revoked EUA)")

# Update "Last updated" date
t = re.sub(r"\*\*Last updated\*\*: \d{4}-\d{2}-\d{2}",
           f"**Last updated**: {TODAY}", t)

# Update scope note
t = t.replace("**Scope**: 136-antibody ADA panel", f"**Scope**: 138-antibody ADA panel")

write(p, t)


# ══════════════════════════════════════════════════════════════════════════════
# 2. ADA_Master_136_Evidence_Report.md
# ══════════════════════════════════════════════════════════════════════════════
p = f"{BASE}/reports/ADA_Master_136_Evidence_Report.md"
t = read(p)

# Header
t = t.replace("**Generated**: 2026-04-03 07:27", f"**Generated**: {TODAY} (updated)")
t = t.replace("**Panel size**: 136 antibodies", "**Panel size**: 138 antibodies")
t = t.replace("`data/ada_master_136_curated.csv`",
              "`data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv`")

# Tier breakdown
t = t.replace("- **Tier A**: 94 (69%)", "- **Tier A**: 99 (72%)")
t = t.replace("- **Tier B**: 36 (26%)", "- **Tier B**: 39 (28%)")
t = t.replace("- **Tier C**: 6 (4%)", "- **Tier C**: 0 — all entries verified or removed (see §4)")

# Column Coverage — replace 136 counts
t = t.replace("| 136/136 | 100% |", "| 138/138 | 100% |")
t = t.replace("| 135/136 | 99% |", "| 137/138 | 99% |")  # 1 still missing (Bezlotoxumab)
t = t.replace("| 130/136 | 96% |", "| 130/138 | 94% |")  # structural data

# Section 4: Known Gaps
old_gaps = """### Missing Primary ADA Source URLs (6 antibodies)

- Naxitamab
- Retifanlimab
- Etesevimab
- Relatlimab
- Olokizumab
- Rozanolixizumab"""

new_gaps = """### Missing Primary ADA Source URLs (0 antibodies)

All previously unverified entries have been resolved:

| Antibody | Resolution |
|---|---|
| Naxitamab | Upgraded → **Tier A** (8%, FDA PI DANYELZA) |
| Rozanolixizumab | Upgraded → **Tier A** (37% corrected from 15%, RYSTIGGO PI §12.6) |
| Retifanlimab | Upgraded → **Tier B** (ZYNYZ DailyMed URL confirmed) |
| Relatlimab | Upgraded → **Tier B** (OPDUALAG DailyMed URL confirmed) |
| Olokizumab | Upgraded → **Tier B** (CREDO 3, ARD 2022, PMID 36109142) |
| Etesevimab | **Deleted** — EUA-only (revoked 2022), no standard FDA PI |"""

t = t.replace(old_gaps, new_gaps)

# Remove Tier C recommendation section
old_tier_c = """### Tier C Entries (Recommended Exclusion from Quantitative Analysis)

- Naxitamab (reported: 8%)
- Retifanlimab (reported: 2.8%)
- Etesevimab (reported: 1.7%)
- Relatlimab (reported: <2%)
- Olokizumab (reported: 10-15%)
- Rozanolixizumab (reported: 10-15%)"""

new_tier_c = """### Tier C Entries

None. The database contains no Tier C entries as of 2026-04-03.
All formerly-Tier-C entries have been upgraded to Tier A/B or removed.
The CLEAN analysis set is now **CLEAN-130** (138 entries minus 8 lacking complete structural/CMC data)."""

t = t.replace(old_tier_c, new_tier_c)

# Update panel references in Coverage Summary
t = re.sub(r"\| (\d+)/136 \|", lambda m: f"| {m.group(1)}/138 |", t)

# Add new entries note
if "Nipocalimab" not in t:
    t += f"""

---

## 7. Database Expansion Log (2026-04-03)

Three new antibody entries were added from 2023–2025 approvals:

| Antibody | Target | ADA | Tier | Source |
|---|---|---|---|---|
| Nipocalimab | FcRn (FCGRT) | 10% | A | FDA PI (IMAAVY, BLA 761332) |
| Epcoritamab | CD3 × CD20 bispecific | 5.4% | A | FDA PI (EPKINLY, BLA 761283) |
| Elranatamab | CD3 × BCMA bispecific | 7.4% | A | FDA PI (ELREXFIO, BLA 761286) |

One entry removed: **Etesevimab** (bamlanivimab + etesevimab COVID-19 EUA, authorization revoked 2022).

*Total: 139 → 138 entries.*
"""

write(p, t)


# ══════════════════════════════════════════════════════════════════════════════
# 3. ADA_Review_Discussion_Notes.md
# ══════════════════════════════════════════════════════════════════════════════
p = f"{BASE}/reports/ADA_Review_Discussion_Notes.md"
t = read(p)

t = t.replace("136-panel analysis (V2 scorer", "138-panel analysis (V2 scorer")
t = t.replace("expanded 136-panel", "expanded 138-panel")
t = t.replace("V2 scorer (136-panel, CLEAN-129)", "V2 scorer (138-panel, CLEAN-130)")
t = t.replace("CLEAN-129 dataset", "CLEAN-130 dataset")
t = t.replace("CLEAN-129", "CLEAN-130")

# Update date
t = re.sub(r"\*\*Date\*\*: \d{4}-\d{2}-\d{2}",
           f"**Date**: {TODAY}", t)

write(p, t)


# ══════════════════════════════════════════════════════════════════════════════
# 4. ADA_V2_Prediction_Results.md
# ══════════════════════════════════════════════════════════════════════════════
p = f"{BASE}/reports/ADA_V2_Prediction_Results.md"
t = read(p)

# Header
t = t.replace("****: 136-Panel ( 131 )",
              "****: 138-Panel ( 130 )")

# Naxitamab tier C → A
t = t.replace("| Naxitamab | 0.711 | 8.0% | engineered | Tier C |",
              "| Naxitamab | 0.711 | 8.0% | engineered | **Tier A** |")
# Also plain text version
t = t.replace("| Naxitamab | 0.711 | 8.0% | engineered | Tier C",
              "| Naxitamab | 0.711 | 8.0% | engineered | **Tier A**")

write(p, t)


# ══════════════════════════════════════════════════════════════════════════════
# 5. ada_evidence_consistency_final_report.md
# ══════════════════════════════════════════════════════════════════════════════
p = f"{BASE}/ada_evidence/ada_evidence_consistency_final_report.md"
t = read(p)

# Append resolution note at bottom (historical audit preserved)
resolution = f"""

---

## ✅ 2026-04-03 ：Tier C 

 2026-03-30 。：

|  |  |  |  |
|------|--------|----------|----------|
| **Naxitamab** | Tier C， URL | FDA PI (DANYELZA BLA 761183)  8% | **Tier A** ✅ |
| **Rozanolixizumab** | Tier C，AI  15% | FDA PI §12.6  = **37%** (n=133) | **Tier A** ✅ () |
| **Retifanlimab** | Tier C， URL | ZYNYZ DailyMed URL  | **Tier B** ✅ |
| **Relatlimab** | Tier C， URL | OPDUALAG DailyMed URL  | **Tier B** ✅ |
| **Olokizumab** | Tier C， URL | CREDO 3 ARD 2022 (PMID 36109142) | **Tier B** ✅ |
| **Etesevimab** | Tier C，EUA  |  | **** ✅ |

**** (2026-04-03)：138 ，Tier A = 99 (72%)，Tier B = 39 (28%)，Tier C = 0。

> 。。
"""

if "2026-04-03 " not in t:
    t += resolution

write(p, t)


# ══════════════════════════════════════════════════════════════════════════════
# 6. confirmed_ada.md  — update header stats, add note about 3 new drugs
# ══════════════════════════════════════════════════════════════════════════════
p = f"{BASE}/ada_evidence/confirmed_ada.md"
t = read(p)

# Update "Generated" date in header
t = re.sub(r"\*\*Generated\*\*: \d{4}-\d{2}-\d{2}",
           f"**Generated**: {TODAY} (updated)", t)

# Update the note about tier_b_ai if present
if "**Scope note (2026-04-03)**" not in t:
    scope_note = f"""
> **Scope note ({TODAY}):** The master database has been expanded to 138 entries (Tier A=99, Tier B=39,
> Tier C=0). Three new antibodies (Nipocalimab, Epcoritamab, Elranatamab) were added from 2023–2025
> approvals; Etesevimab was removed (revoked EUA). The 80 entries in this confirmed file represent the
> fully-verified subset; the three new entries will be added after additional evidence chain review.

"""
    # Insert after first line (title)
    lines = t.split('\n')
    lines.insert(3, scope_note)
    t = '\n'.join(lines)

write(p, t)


# ══════════════════════════════════════════════════════════════════════════════
# 7. clinical_ada_full_evidence_report.md  — update header
# ══════════════════════════════════════════════════════════════════════════════
p = f"{BASE}/reports/clinical_ada_full_evidence_report.md"
t = read(p)

t = re.sub(r"Generated on: \d{4}-\d{2}-\d{2}",
           f"Generated on: {TODAY} (updated)", t)

# Replace single "136" reference if related to panel
t = t.replace("from 136-panel", "from 138-panel")
t = t.replace("136-antibody", "138-antibody")

if "**Note (2026-04-03)**" not in t:
    note = f"""
> **Note ({TODAY}):** The master database has been updated to 138 entries (Tier A=99, Tier B=39, Tier C=0).
> Etesevimab was removed (revoked EUA). Naxitamab upgraded to Tier A (8%, FDA PI).
> Rozanolixizumab upgraded to Tier A (ADA corrected to 37%, RYSTIGGO PI §12.6).
> Retifanlimab, Relatlimab, Olokizumab upgraded to Tier B with verified PI/paper URLs.
> Three new entries (Nipocalimab, Epcoritamab, Elranatamab) added — see master CSV for details.

"""
    lines = t.split('\n')
    lines.insert(3, note)
    t = '\n'.join(lines)

write(p, t)


# ══════════════════════════════════════════════════════════════════════════════
# 8. clinical_ada_engineered_evidence_report.md  — update header
# ══════════════════════════════════════════════════════════════════════════════
p = f"{BASE}/reports/clinical_ada_engineered_evidence_report.md"
t = read(p)

t = re.sub(r"Generated on: \d{4}-\d{2}-\d{2}",
           f"Generated on: {TODAY} (updated)", t)

t = t.replace("from 136-panel", "from 138-panel")
t = t.replace("136-antibody", "138-antibody")

if "**Note (2026-04-03)**" not in t:
    note = f"""
> **Note ({TODAY}):** The master database has been updated to 138 entries (Tier A=99, Tier B=39, Tier C=0).
> Etesevimab removed (revoked EUA). Naxitamab upgraded to Tier A (8%, FDA PI DANYELZA).
> Rozanolixizumab upgraded to Tier A (ADA corrected to 37%). Retifanlimab, Relatlimab, Olokizumab
> upgraded to Tier B. Epcoritamab and Elranatamab added as new engineered bispecifics.

"""
    lines = t.split('\n')
    lines.insert(3, note)
    t = '\n'.join(lines)

write(p, t)


print("\n✅ All 8 MD files updated successfully.")
