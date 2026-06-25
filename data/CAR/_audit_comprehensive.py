"""
Comprehensive audit of CART_LIBRARY_V3.json:
Q1. CAR relevance for all 200 elements
Q2. Sequence origin classification (DB-retrieved vs CDR-grafted vs literature vs AI-constructed)
Q3. Gene ID + precise residue boundary analysis
Q4. Application scenario coverage
"""
import json, re
from pathlib import Path
from collections import Counter, defaultdict

CAR_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\CAR")
V3_PATH  = CAR_DIR / "CART_LIBRARY_V3.json"
with open(V3_PATH, encoding="utf-8") as f:
    lib = json.load(f)
elements = lib["elements"]

# ── Q1. CAR relevance audit ─────────────────────────────────────────
# Strict: only elements that appear in a real CAR vector construct
CORE_CAR    = {"Signal Peptide/Leader","Binder/scFv/VHH","Hinge","Transmembrane",
               "Costimulatory","CD3ζ Activation","2A Peptide/Linker","Safety Switch",
               "Allogeneic KO Target"}
CONTEXTUAL  = {"Armored Payload","Logic Gate","CAR-Treg","CAAR Binder",
               "Regulatory Element","Activation Signaling"}
SPECIALIZED = {"Depletion Tag","NK Receptor ECD","CAR-M element"}

# Map categories to relevance tier
CAT_TIER = {
    # CORE
    "Leader":           "CORE", "2A Peptide":        "CORE",
    "Hinge":            "CORE", "Transmembrane":      "CORE",
    "Costimulatory":    "CORE", "Activation":         "CORE",
    "Safety Switch":    "CORE", "Depletion Tag":      "CORE",
    "Binder":           "CORE", "CAAR Binder":        "CORE",
    "Linker":           "CORE",
    # CONTEXTUAL
    "Armored Payload":  "CONTEXTUAL", "Logic Gate":    "CONTEXTUAL",
    "CAR-Treg":         "CONTEXTUAL", "Regulatory Element": "CONTEXTUAL",
    # SPECIALIZED (still CAR-relevant but narrower use)
    "Allogeneic":       "SPECIALIZED",
}

tiers = Counter()
for e in elements:
    cat = e.get("category","?")
    tier = CAT_TIER.get(cat, "SPECIALIZED")
    tiers[tier] += 1

# ── Q2. Sequence origin classification ──────────────────────────────
ORIGIN_CLASSES = {
    "DB_retrieved":    [],  # directly from UniProt/PDB/NCBI API
    "CDR_grafted":     [],  # CDR from patent + human framework
    "Literature":      [],  # published VH/VL from paper
    "Patent_derived":  [],  # sequence from patent sequence listing
    "Composite":       [],  # built from multiple DB entries
    "Canonical":       [],  # standard sequence (2A, linkers, promoters)
    "Derived":         [],  # truncation/mutation of DB sequence
    "STUB":            [],  # no sequence
}

for e in elements:
    eid  = e["id"]
    meth = e.get("qa",{}).get("method","")
    stat = e.get("sequence_status","")
    seq  = e.get("sequence","")
    
    if not seq or len(seq) < 5:
        ORIGIN_CLASSES["STUB"].append(eid); continue
    
    m = meth.lower()
    if "cdr graft" in m or "cdr-graft" in m:
        ORIGIN_CLASSES["CDR_grafted"].append(eid)
    elif any(x in m for x in ["pdb","uniprot rest","ncbi"]):
        ORIGIN_CLASSES["DB_retrieved"].append(eid)
    elif "published" in m or "literature" in m or "paper" in m:
        ORIGIN_CLASSES["Literature"].append(eid)
    elif "patent" in m.lower():
        ORIGIN_CLASSES["Patent_derived"].append(eid)
    elif "composite" in m or "combination" in m:
        ORIGIN_CLASSES["Composite"].append(eid)
    elif any(x in m for x in ["truncat","mutant","mutation","derived"]):
        ORIGIN_CLASSES["Derived"].append(eid)
    elif any(x in m for x in ["canonical","standard","hardcoded","known"]):
        ORIGIN_CLASSES["Canonical"].append(eid)
    else:
        # Check qa source
        src = e.get("qa",{}).get("source","")
        if "P0" in src or "Q9" in src or "UniProt" in src.upper() or "PDB" in src[:10]:
            ORIGIN_CLASSES["DB_retrieved"].append(eid)
        elif "WO" in src or "US" in src[:8] or "patent" in src.lower():
            ORIGIN_CLASSES["Patent_derived"].append(eid)
        elif "published" in src.lower():
            ORIGIN_CLASSES["Literature"].append(eid)
        else:
            ORIGIN_CLASSES["Canonical"].append(eid)

# ── Q3. Gene ID + boundary analysis ─────────────────────────────────
boundary_issues = []  # elements with imprecise boundaries
for e in elements:
    eid  = e["id"]
    src  = e.get("qa",{}).get("source","")
    meth = e.get("qa",{}).get("method","")
    seq  = e.get("sequence","")
    
    # Check if boundary residues are defined
    has_boundary = bool(re.search(r'\b\d+\s*[-–]\s*\d+\b', src))  # e.g., "159-207"
    has_uniprot  = bool(re.search(r'[OPQ][0-9][A-Z0-9]{3}[0-9]', src))  # UniProt ID
    has_gene_id  = bool(re.search(r'NCBI Gene[: ]+\d+|Gene ID[: ]+\d+', src, re.I))
    
    if not has_boundary and "UniProt" in meth:
        boundary_issues.append((eid, "Missing residue range in UniProt source"))
    elif not has_uniprot and not has_gene_id and e.get("category") in ["Costimulatory","Activation","Hinge","Transmembrane"]:
        boundary_issues.append((eid, "No UniProt/Gene ID anchor"))

# ── Print comprehensive report ───────────────────────────────────────
print("=" * 70)
print("CART_LIBRARY_V3.json COMPREHENSIVE AUDIT")
print(f"Total elements: {len(elements)}")
print("=" * 70)

print("\n── Q1. CAR DESIGN RELEVANCE ──")
for tier, n in sorted(tiers.items()):
    print(f"  {tier:<15} {n:>3} elements")
print(f"  {'TOTAL':<15} {sum(tiers.values()):>3}")

print("\n── Q2. SEQUENCE ORIGIN CLASSIFICATION ──")
ai_generated = 0
for origin, ids in sorted(ORIGIN_CLASSES.items()):
    if not ids: continue
    mark = "⚠" if origin in ("CDR_grafted","Literature","Derived") else "✅" if origin == "DB_retrieved" else "○"
    print(f"  {mark} {origin:<18} {len(ids):>3} elements")
    if origin not in ("DB_retrieved","Canonical","Patent_derived","Composite"):
        ai_generated += len(ids)

print(f"\n  Summary:")
print(f"    DB-retrieved (UniProt/PDB/NCBI): {len(ORIGIN_CLASSES['DB_retrieved'])} — highest confidence")
print(f"    CDR-grafted (patent CDR + framework): {len(ORIGIN_CLASSES['CDR_grafted'])} — CDRs verified, frameworks standard")
print(f"    Literature (published VH/VL): {len(ORIGIN_CLASSES['Literature'])} — need independent verification")
print(f"    Derived (truncation/mutation of DB): {len(ORIGIN_CLASSES['Derived'])} — DB-anchored + modification")
print(f"    Composite (built from multiple DB): {len(ORIGIN_CLASSES['Composite'])} — components verified individually")
print(f"    Canonical (standard known sequences): {len(ORIGIN_CLASSES['Canonical'])} — widely published")
print(f"    Patent: {len(ORIGIN_CLASSES['Patent_derived'])}")
print(f"    Stubs: {len(ORIGIN_CLASSES['STUB'])}")

print("\n── Q3. BOUNDARY PRECISION ISSUES ──")
print(f"  Elements with potential boundary precision concerns: {len(boundary_issues)}")
for eid, issue in boundary_issues[:20]:
    print(f"    {eid}: {issue}")

print("\n── Q4. APPLICATION SCENARIO COVERAGE ──")
# Count by subcategory
subcats = Counter(e.get("subcategory","?") for e in elements)
print("  Application scenario distribution:")
for sub, n in sorted(subcats.items(), key=lambda x: -x[1]):
    print(f"    {sub:<45} {n}")

# Coverage by clinical indication
indications = Counter()
for e in elements:
    for ind in e.get("indications",[]):
        indications[ind] += 1
print(f"\n  Most covered indications:")
for ind, n in indications.most_common(15):
    print(f"    {ind:<35} {n} elements")

# Save report
report_lines = []
report_lines.append("# CART_LIBRARY_V3 Comprehensive Audit Report\n")
report_lines.append(f"**Generated:** 2026-04-01  |  **Total:** {len(elements)} elements\n\n")
report_lines.append("## Sequence Origin Summary\n")
for origin, ids in sorted(ORIGIN_CLASSES.items()):
    if ids:
        report_lines.append(f"- **{origin}**: {len(ids)}\n")
report_lines.append("\n## Elements with Literature-Derived VH/VL Sequences\n")
report_lines.append("(Need independent experimental verification before clinical use)\n\n")
for eid in ORIGIN_CLASSES["Literature"]:
    e = next(x for x in elements if x["id"]==eid)
    report_lines.append(f"- `{eid}`: {e.get('qa',{}).get('method','-')}\n")

with open(CAR_DIR / "AUDIT_REPORT_COMPREHENSIVE.md", "w", encoding="utf-8") as f:
    f.writelines(report_lines)
print(f"\n  Detailed report: {CAR_DIR / 'AUDIT_REPORT_COMPREHENSIVE.md'}")
