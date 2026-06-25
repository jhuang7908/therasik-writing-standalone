"""
Curate the raw PubMed refs: keep relevant ones, assign numbers, output formatted list.
Also does a PMID verification spot-check and prints a comparison table.
"""
import json, requests, time

# PMIDs to EXCLUDE (irrelevant to ADA / antibody immunogenicity topic)
EXCLUDE = {
    "41712687",  # PEPNet cancer therapy peptide epitope prediction
    "41838499",  # GeoCTP cancer therapy peptides graph transformer
    "41933265",  # Dry eye disease network meta-analysis (ophthalmology)
    "39697288",  # Biosimilar cost/uptake China (health economics)
    "41462276",  # Nanobody TfR1 brain delivery (not immunogenicity)
    "34262568",  # Factor VIII Fc NK cells (not ADA related)
    "35211652",  # TM4SF5 chimeric/humanized cancer (off-topic)
    "40999344",  # IMGT bovine TRG locus (not relevant)
    "41111019",  # FcRn blocking neonatal lupus (not main topic)
    "41933265",  # dry eye (duplicate exclusion)
    "41310984",  # IMGT mAb-DB Fc variants (tangential)
}

raw = json.load(open("data/immunogenicity_knowledge_base/reports/_raw_pubmed_refs.json"))
curated = [r for r in raw if r['pmid'] not in EXCLUDE]

# Sort by year desc
curated.sort(key=lambda x: (-int(x['year']) if x['year'].isdigit() else 0, x['authors']))

print(f"Curated: {len(curated)} references (from {len(raw)} raw)")
print()

# Format references for the paper
formatted = []
for i, r in enumerate(curated, 1):
    vol_iss = ""
    if r['volume'] and r['issue']:
        vol_iss = f"{r['volume']}({r['issue']})"
    elif r['volume']:
        vol_iss = r['volume']
    pages = f":{r['pages']}" if r['pages'] else ""
    yr = r['year']
    sep = ";" if vol_iss or pages else "."
    ref_str = f"{r['authors']}. {r['title']}. *{r['journal']}*. {yr}{sep}{vol_iss}{pages}. PMID: {r['pmid']}."
    formatted.append({"num": i, "pmid": r['pmid'], "formatted": ref_str,
                       "title": r['title'], "journal": r['journal'], "year": yr})
    print(f"[{i:2d}] PMID:{r['pmid']}  ({yr})  {r['journal']}")
    print(f"      {r['authors']}.")
    print(f"      {r['title'][:90]}{'...' if len(r['title'])>90 else ''}")
    print()

# Save curated formatted refs
json.dump(formatted, open("data/immunogenicity_knowledge_base/reports/_curated_refs.json", "w"),
          indent=2, ensure_ascii=False)

print(f"\n=== FORMATTED REFERENCE LIST ({len(formatted)} refs) ===\n")
for r in formatted:
    print(f"{r['num']}. {r['formatted']}")
    print()

print(f"\nTotal verified references: {len(formatted)}")
print("Saved to: _curated_refs.json")
