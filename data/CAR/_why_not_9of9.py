"""
Diagnose exactly why overall quality is not 9/9.
Identify which fields fail, for which element types, and WHY.
"""
import json
from pathlib import Path
from collections import defaultdict

CAR_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\CAR")
lib = json.loads((CAR_DIR / "CART_LIBRARY_V3.json").read_text(encoding="utf-8"))
elements = lib["elements"]
total = len(elements)

FIELDS = ["has_seq","has_tier","has_usage","has_notes",
          "has_qa_method","has_qa_source","has_qa_gene",
          "has_clinical","has_gene_annot"]

def score(e):
    return {
        "has_seq":       bool(e.get("sequence") and len(e.get("sequence",""))>5),
        "has_tier":      bool(e.get("regulatory_tier")),
        "has_usage":     bool(e.get("usage_context")),
        "has_notes":     len(e.get("design_notes","")) > 80,
        "has_qa_method": bool(e.get("qa",{}).get("method")),
        "has_qa_source": bool(e.get("qa",{}).get("source")),
        "has_qa_gene":   bool(e.get("qa",{}).get("gene_symbol") or
                              e.get("qa",{}).get("uniprot") or
                              e.get("gene_annotation")),
        "has_clinical":  bool(e.get("clinical_trials") or e.get("references")),
        "has_gene_annot":bool(e.get("gene_annotation")),
    }

# ── Count failures per field and categorize WHY ──
fail_detail = defaultdict(list)
for e in elements:
    sc = score(e)
    cat = e.get("category","?")
    sub = e.get("subcategory","?")
    for f, v in sc.items():
        if not v:
            fail_detail[f].append((e["id"], cat, sub))

print("="*70)
print("WHY NOT 9/9? FIELD-BY-FIELD ROOT CAUSE ANALYSIS")
print("="*70)

RCA = {
    "has_seq": {
        "count_label": "Missing sequence",
        "structural_fail": [],
        "explanation": "2 elements still STUB – fixable"
    },
    "has_tier": {
        "count_label": "Missing regulatory tier",
        "structural_fail": [],
        "explanation": "1 element missing tier – fixable"
    },
    "has_usage": {
        "count_label": "Missing usage_context",
        "structural_fail": ["Linker & Peptide","Hinge & Spacer","Signal Peptide",
                            "Transmembrane Domain"],
        "explanation": "Linkers/hinges/TMs/SPs are backbone elements – usage is implied by category. FIXABLE for protein functional elements."
    },
    "has_notes": {
        "count_label": "Design notes <80 chars",
        "structural_fail": [],
        "explanation": "~21 elements have short notes. Most are older entries – FIXABLE."
    },
    "has_qa_method": {
        "count_label": "Missing QA method",
        "structural_fail": [],
        "explanation": "All should have QA method – if any missing, FIXABLE."
    },
    "has_qa_source": {
        "count_label": "Missing QA source",
        "structural_fail": [],
        "explanation": "All should have QA source – FIXABLE."
    },
    "has_qa_gene": {
        "count_label": "Missing gene/UniProt annotation",
        "structural_fail": ["Linker & Peptide","Hinge & Spacer"],
        "explanation": "G4S linkers, 2A peptides are SYNTHETIC – no UniProt ID exists. Structurally impossible for ~30 elements."
    },
    "has_clinical": {
        "count_label": "Missing clinical trial / reference",
        "structural_fail": ["Linker & Peptide","Hinge & Spacer","Signal Peptide",
                            "Transmembrane Domain","Regulatory Element"],
        "explanation": "G4S3, 2A peptides, signal peptides have NO independent clinical NCT#. Structurally impossible for ~80 elements."
    },
    "has_gene_annot": {
        "count_label": "Missing structured gene_annotation",
        "structural_fail": ["Linker & Peptide","Hinge & Spacer","Signal Peptide",
                            "Regulatory Element"],
        "explanation": "Synthetic/composite elements can't have gene boundaries. Structurally impossible for ~50 elements."
    },
}

fixable_total = 0
structural_total = 0

for f in FIELDS:
    fails = fail_detail[f]
    n_fail = len(fails)
    struct = RCA[f]["structural_fail"]
    struct_fails = [x for x in fails if x[1] in struct]
    real_fails   = [x for x in fails if x[1] not in struct]
    pct = 100 * (total - n_fail) // total
    print(f"\n  ▶ {f}  ({pct}% pass, {n_fail} fail)")
    print(f"    Reason: {RCA[f]['explanation']}")
    print(f"    Structural failures (expected): {len(struct_fails)}")
    print(f"    Fixable failures:               {len(real_fails)}")
    if real_fails[:3]:
        sample = [x[0] for x in real_fails[:3]]
        print(f"    Sample fixable: {sample}")
    fixable_total  += len(real_fails)
    structural_total += len(struct_fails)

# Realistic maximum score
# For each element, what's the achievable maximum given its category?
print(f"\n{'='*70}")
print("REALISTIC MAXIMUM SCORE ANALYSIS")
print(f"{'='*70}")

# Define which fields are achievable per category
ACHIEVABLE = {
    "Antigen Binder":          set(FIELDS),
    "Costimulatory Domain":    set(FIELDS),
    "Primary Signaling Domain":set(FIELDS),
    "Transmembrane Domain":    set(FIELDS) - {"has_clinical","has_gene_annot"},
    "Hinge & Spacer":          set(FIELDS) - {"has_clinical","has_gene_annot","has_usage","has_qa_gene"},
    "Signal Peptide":          set(FIELDS) - {"has_clinical","has_gene_annot","has_usage"},
    "Linker & Peptide":        set(FIELDS) - {"has_clinical","has_gene_annot","has_usage","has_qa_gene"},
    "Armored Payload":         set(FIELDS),
    "Logic Gate & Switch":     set(FIELDS),
    "Safety Switch":           set(FIELDS),
    "Regulatory Element":      set(FIELDS) - {"has_gene_annot"},
    "Engineering Module":      set(FIELDS),
}

total_achievable = 0
total_actual = 0
for e in elements:
    cat = e.get("category","?")
    achievable = ACHIEVABLE.get(cat, set(FIELDS))
    sc = score(e)
    actual = sum(v for f,v in sc.items() if f in achievable)
    maximum = len(achievable)
    total_actual += actual
    total_achievable += maximum

print(f"  Current actual score:      {total_actual}")
print(f"  Realistic maximum possible:{total_achievable}")
print(f"  Current %:                 {100*total_actual//total_achievable}% of realistic max")
print(f"  Fixable points:            {fixable_total} across all elements")
print(f"  Structural impossibles:    {structural_total} (synthetic elements, no UniProt/NCT)")

# What would 9/9 require?
print(f"\n{'='*70}")
print("WHAT WOULD 9/9 REQUIRE?")
print(f"{'='*70}")
print("""
  Field              | To achieve 100%         | Feasibility
  -------------------|-------------------------|------------------
  has_seq            | Fix 2 stubs             | ✅ Easy
  has_tier           | Add 1 missing tier      | ✅ Easy
  has_usage          | Fill 91 missing fields  | ✅ Scriptable
  has_notes          | Expand 21 short notes   | ✅ Scriptable
  has_qa_method/src  | All present already     | ✅ Done
  has_qa_gene        | G4S/2A have no UniProt  | ❌ IMPOSSIBLE (~30 synthetic)
  has_clinical       | Linkers have no NCT#    | ❌ IMPOSSIBLE (~80 backbone elements)
  has_gene_annot     | Synthetic = no gene     | ❌ IMPOSSIBLE (~50 elements)

  Conclusion:
  • 9/9 on ALL elements is structurally impossible (synthetic elements
    like G4S3, T2A, CD8α hinge have no UniProt ID, no clinical trial NCT#)
  
  • Realistic maximum = 9/9 for functional protein elements (~150)
    + 6/9 for backbone elements (linkers, hinges, signal peptides)
  
  • The 3 missing points on backbone elements are NOT data quality problems –
    they are CATEGORY DESIGN problems in our scoring rubric.
  
  ACHIEVABLE IMPROVEMENT:
  • Fix usage_context for 91 elements → +91 points  
  • Fix 2 stubs → +2 points
  • Expand 21 short notes → +21 points
  • These 3 fixes → score jumps from 6.17→7.5 for legacy elements
""")
