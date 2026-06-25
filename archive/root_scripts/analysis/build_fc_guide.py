"""
Build Fc mutation reference section for the Antibody Engineering Guide.
Sources: ADA master fc_mutation_notes + fc_effector_status, plus curated knowledge.
Output: HTML block to inject into Therasik_Antibody_Guide.html
"""
import csv, json

MASTER = r'data\ada_master_136_curated.csv'
rows = list(csv.DictReader(open(MASTER, encoding='utf-8')))

# Tally which Fc engineering types appear in our ADA database
fc_counts = {}
for r in rows:
    fe = (r.get('fc_engineering') or '').strip
    fs = (r.get('fc_effector_status') or '').strip
    if fe and fe.lower not in ('nan','none','n/a',''):
        key = fe[:80]
        fc_counts[key] = fc_counts.get(key, 0) + 1

print("Top Fc engineering patterns in ADA master:")
for k,v in sorted(fc_counts.items, key=lambda x:-x[1])[:20]:
    print(f"  {v:3d}x  {k}")

# ── Curated Fc mutation knowledge base ─────────────────────────────────────
FC_MUTATIONS = [
    # ── ADCC/CDC silencing ──────────────────────────────────────────────────
    {
        "mut": "L234A/L235A (LALA)",
        "func": "ADCC/CDC ",
        "func_en": "ADCC/CDC silencing",
        "mechanism": " FcγR ， ADCC  CDC ，",
        "clinical_examples": ["Durvalumab", "Nivolumab*", "Ipilimumab*", "Atezolizumab"],
        "isotype_basis": "IgG1",
        "ada_count": sum(1 for r in rows if 'lala' in (r.get('fc_mutation_notes','') or '').lower or 'lala' in (r.get('fc_engineering','') or '').lower),
        "risk_notes": " Fc ， FcRn ",
        "category": ""
    },
    {
        "mut": "N297A / N297G / N297Q",
        "func": " / ADCC ",
        "func_en": "Aglycosylation",
        "mechanism": " CH2 ， FcγR  ADCC；",
        "clinical_examples": [""],
        "isotype_basis": "IgG1",
        "ada_count": 0,
        "risk_notes": "，",
        "category": ""
    },
    {
        "mut": "P329G (LALA-PG  LALA )",
        "func": "FcγR ",
        "func_en": "Complete FcγR ablation",
        "mechanism": " LALA  >99.99% FcγR （Roche/Genentech ）",
        "clinical_examples": ["Emicizumab (IgG4 + P329G)"],
        "isotype_basis": "IgG1/IgG4",
        "ada_count": 0,
        "risk_notes": "， IND",
        "category": ""
    },
    # ── ADCC  ────────────────────────────────────────────────────────────
    {
        "mut": "S239D/I332E (GASDALIE: G236A+S239D+A330L+I332E)",
        "func": "ADCC ",
        "func_en": "Enhanced ADCC",
        "mechanism": " FcγRIIIa (CD16a) ，ADCC  100 ",
        "clinical_examples": ["Mogamulizumab", "Ublituximab"],
        "isotype_basis": "IgG1",
        "ada_count": sum(1 for r in rows if 's239' in (r.get('fc_mutation_notes','') or '').lower or 'gasdalie' in (r.get('fc_mutation_notes','') or '').lower),
        "risk_notes": "； B ",
        "category": ""
    },
    {
        "mut": "（afucosylation）",
        "func": "ADCC ",
        "func_en": "Afucosylation",
        "mechanism": " Asn297 ，FcγRIIIa  40–50 ",
        "clinical_examples": ["Obinutuzumab", "Mogamulizumab"],
        "isotype_basis": "IgG1",
        "ada_count": 0,
        "risk_notes": "（FUT8 KO），",
        "category": ""
    },
    # ── FcRn  /  ──────────────────────────────────────────────────
    {
        "mut": "M252Y/S254T/T256E (YTE)",
        "func": "FcRn ↑ / ",
        "func_en": "Half-life extension (YTE)",
        "mechanism": " pH 6  FcRn ， 2–4 ",
        "clinical_examples": ["Motavizumab-YTE ", " IgG1 "],
        "isotype_basis": "IgG1",
        "ada_count": sum(1 for r in rows if 'yte' in (r.get('fc_mutation_notes','') or '').lower or 'm252' in (r.get('fc_mutation_notes','') or '').lower),
        "risk_notes": "； ADCC/CDC",
        "category": ""
    },
    {
        "mut": "M428L/N434S (LS)",
        "func": "FcRn ↑ / ",
        "func_en": "Half-life extension (LS)",
        "mechanism": "FcRn  11 （pH 6）， 2–3 ",
        "clinical_examples": ["Nirsevimab (RSV mAb)", "MEDI1912"],
        "isotype_basis": "IgG1",
        "ada_count": 0,
        "risk_notes": "",
        "category": ""
    },
    {
        "mut": "H433K/N434F (XTEND™)",
        "func": "FcRn ↑↑",
        "func_en": "FcRn ultra-extension",
        "mechanism": " FcRn ，；Halozyme/Xencor ",
        "clinical_examples": [""],
        "isotype_basis": "IgG1",
        "ada_count": 0,
        "risk_notes": " FcRn ",
        "category": ""
    },
    # ──  Fc ────────────────────────────────────────────────────────
    {
        "mut": "Knob-into-Hole (T366W / T366S+L368A+Y407V)",
        "func": " Fc ",
        "func_en": "Bispecific Fc heterodimerization",
        "mechanism": "Knob （T366W） Hole （T366S+L368A+Y407V）， Fc ",
        "clinical_examples": ["Blinatumomab ", ""],
        "isotype_basis": "IgG1/IgG4",
        "ada_count": 0,
        "risk_notes": " S354C/Y349C ",
        "category": ""
    },
    {
        "mut": "F405L/K409R (Fab-arm exchange, DuoBody)",
        "func": " Fab ",
        "func_en": "Controlled Fab-arm exchange",
        "mechanism": " IgG4-like ，",
        "clinical_examples": ["Faricimab", "Biclonics® "],
        "isotype_basis": "IgG4/IgG1 hybrid",
        "ada_count": sum(1 for r in rows if 'fab-arm exchange' in (r.get('fc_mutation_notes','') or '').lower or 'duobody' in (r.get('fc_mutation_notes','') or '').lower),
        "risk_notes": " >95%； FDA ",
        "category": ""
    },
    # ── IgG  ────────────────────────────────────────────────────────
    {
        "mut": "IgG1 ",
        "func": " ADCC/CDC ",
        "func_en": "Standard effector function",
        "mechanism": " FcγRIIIa ； CDC ；",
        "clinical_examples": ["Trastuzumab", "Rituximab", "Cetuximab"],
        "isotype_basis": "IgG1",
        "ada_count": sum(1 for r in rows if 'wild-type igg1' in (r.get('fc_engineering','') or '').lower),
        "risk_notes": "ADA  ADCC ，",
        "category": ""
    },
    {
        "mut": "IgG2 ",
        "func": "",
        "func_en": "Reduced effector function",
        "mechanism": "IgG2 ，FcγRIIIa ；ADCC/CDC ；",
        "clinical_examples": ["Denosumab", "Panitumumab", "Trebananib"],
        "isotype_basis": "IgG2",
        "ada_count": sum(1 for r in rows if r.get('fc_isotype','') == '2'),
        "risk_notes": "IgG2 ；",
        "category": ""
    },
    {
        "mut": "IgG4  + S228P",
        "func": " / ",
        "func_en": "IgG4 + S228P stabilization",
        "mechanism": "S228P  IgG4 ， Fab ；",
        "clinical_examples": ["Pembrolizumab", "Nivolumab", "Dupilumab"],
        "isotype_basis": "IgG4",
        "ada_count": sum(1 for r in rows if r.get('fc_isotype','') == '4'),
        "risk_notes": "IgG4  <5% ；S228P ",
        "category": ""
    },
]

print(f"\nFc mutation entries: {len(FC_MUTATIONS)}")
for entry in FC_MUTATIONS:
    ada_n = entry['ada_count']
    if ada_n > 0:
        print(f"  {entry['mut'][:40]}: {ada_n} ADA records with this modification")

# Save as JSON for potential later use
with open('data/reference/fc_mutations_guide.json', 'w', encoding='utf-8') as f:
    import os; os.makedirs('data/reference', exist_ok=True)
    json.dump(FC_MUTATIONS, f, ensure_ascii=False, indent=2)

print("\nSaved: data/reference/fc_mutations_guide.json")
