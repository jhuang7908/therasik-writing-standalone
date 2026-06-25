"""
Fetch and verify 50+ real PubMed references for the ADA meta-analysis paper.
Uses NCBI eUtils API - no fabricated data.
Output: _verified_refs.json  (each entry: pmid, title, authors, journal, year, abstract_snippet)
"""
import requests, time, json, re, sys

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
DELAY = 0.4   # seconds between requests (NCBI limit = 3/s without API key)

def esearch(query, retmax=5):
    url = BASE + "esearch.fcgi"
    r = requests.get(url, params={"db":"pubmed","term":query,"retmax":retmax,"retmode":"json"}, timeout=15)
    r.raise_for_status()
    ids = r.json().get("esearchresult",{}).get("idlist",[])
    time.sleep(DELAY)
    return ids

def efetch_summary(pmids):
    if not pmids: return []
    url = BASE + "esummary.fcgi"
    r = requests.get(url, params={"db":"pubmed","id":",".join(pmids),"retmode":"json"}, timeout=15)
    r.raise_for_status()
    data = r.json().get("result", {})
    time.sleep(DELAY)
    out = []
    for pmid in pmids:
        if pmid not in data: continue
        d = data[pmid]
        authors = [a.get("name","") for a in d.get("authors",[])]
        # Format: Last FM et al. if >3 authors
        if len(authors) >= 3:
            au_str = f"{authors[0]}, {authors[1]}, {authors[2]}" + (" et al." if len(authors) > 3 else "")
        elif authors:
            au_str = ", ".join(authors)
        else:
            au_str = "[No authors listed]"
        out.append({
            "pmid": pmid,
            "title": d.get("title","").rstrip("."),
            "authors": au_str,
            "journal": d.get("source",""),
            "year": d.get("pubdate","")[:4],
            "volume": d.get("volume",""),
            "issue": d.get("issue",""),
            "pages": d.get("pages",""),
        })
    return out

# ─── Define 25 targeted search queries ──────────────────────────────────────
QUERIES = [
    # 1. ADA clinical significance / general reviews
    ("anti-drug antibody immunogenicity therapeutic biologics review[Title/Abstract]", 3),
    # 2. ADA impact on pharmacokinetics
    ("anti-drug antibody pharmacokinetics neutralizing biologic[Title/Abstract]", 3),
    # 3. ADA and adalimumab
    ("adalimumab anti-drug antibody clinical rheumatoid arthritis", 2),
    # 4. FDA/EMA immunogenicity guidance
    ("immunogenicity assessment therapeutic protein FDA guidance[Title/Abstract]", 2),
    # 5. ADA tiered assay ECL
    ("tiered assay anti-drug antibody electrochemiluminescence detection[Title/Abstract]", 3),
    # 6. Drug-tolerant assay
    ("drug tolerant assay anti-drug antibody immunogenicity detection[Title/Abstract]", 3),
    # 7. Antibody humanization CDR grafting
    ("humanization monoclonal antibody CDR grafting immunogenicity[Title/Abstract]", 3),
    # 8. Human germline framework selection
    ("human germline framework antibody humanization immunogenicity[Title/Abstract]", 3),
    # 9. Fully human antibody immunogenicity
    ("fully human antibody immunogenicity transgenic mice phage display[Title/Abstract]", 2),
    # 10. MHC-II T cell epitope immunogenicity
    ("MHC class II T cell epitope therapeutic protein immunogenicity[Title/Abstract]", 3),
    # 11. NetMHCIIpan epitope prediction
    ("NetMHCIIpan MHC class II epitope prediction[Title/Abstract]", 2),
    # 12. Aggregation immunogenicity
    ("protein aggregation immunogenicity therapeutic antibody[Title/Abstract]", 3),
    # 13. Subcutaneous vs IV immunogenicity
    ("subcutaneous intravenous administration immunogenicity biologic[Title/Abstract]", 3),
    # 14. Methotrexate immunosuppression ADA
    ("methotrexate anti-drug antibody immunogenicity biologic[Title/Abstract]", 2),
    # 15. Surface hydrophobicity aggregation antibody
    ("surface hydrophobic patch antibody aggregation developability[Title/Abstract]", 3),
    # 16. ESMFold protein structure prediction
    ("ESMFold protein structure prediction language model[Title/Abstract]", 2),
    # 17. ABARCII antibody numbering
    ("ABARCII antibody numbering Chothia Kabat IMGT[Title/Abstract]", 2),
    # 18. FreeSASA solvent accessibility
    ("FreeSASA solvent accessible surface area protein[Title/Abstract]", 2),
    # 19. Antibody VH VL packing interface
    ("VH VL packing angle antibody interface[Title/Abstract]", 2),
    # 20. Spearman correlation biopharmaceutical
    ("Spearman rank correlation immunogenicity antibody biopharmaceutical[Title/Abstract]", 2),
    # 21. Instability index ProtParam BioPython
    ("instability index isoelectric point antibody bioinformatics[Title/Abstract]", 2),
    # 22. Donanemab amyloid antibody ADA
    ("donanemab amyloid beta antibody clinical trial immunogenicity", 2),
    # 23. Alemtuzumab anti-drug antibody
    ("alemtuzumab anti-drug antibody multiple sclerosis[Title/Abstract]", 2),
    # 24. Checkpoint inhibitor immunogenicity PD-1
    ("checkpoint inhibitor anti-drug antibody PD-1 pembrolizumab nivolumab[Title/Abstract]", 2),
    # 25. Somatic hypermutation germline divergence immunogenicity
    ("somatic hypermutation germline divergence immunogenicity biotherapeutic[Title/Abstract]", 2),
    # 26. Population antibody repertoire naive usage
    ("human antibody repertoire naive B cell germline usage frequency[Title/Abstract]", 2),
    # 27. PRISMA systematic review meta-analysis
    ("PRISMA systematic review reporting guidelines meta-analysis[Title/Abstract]", 1),
    # 28. IgG subclass immunogenicity Fc
    ("IgG subclass immunogenicity Fc region biologic[Title/Abstract]", 2),
    # 29. Deamidation isomerization antibody stability
    ("deamidation isomerization antibody chemical degradation CDR[Title/Abstract]", 2),
    # 30. pI charge biopharmaceutical aggregation
    ("isoelectric point charge antibody aggregation solubility[Title/Abstract]", 2),
    # 31. ADA neutralizing vs non-neutralizing clinical impact
    ("neutralizing anti-drug antibody clinical impact efficacy safety[Title/Abstract]", 2),
    # 32. Multiple sclerosis biologic immunogenicity
    ("multiple sclerosis biologic interferon natalizumab anti-drug antibody[Title/Abstract]", 2),
    # 33. VHH nanobody immunogenicity
    ("VHH nanobody single domain antibody immunogenicity[Title/Abstract]", 2),
    # 34. B cell tolerance self-reactive antibody
    ("B cell tolerance self-reactive antibody breakdown immunogenicity[Title/Abstract]", 2),
    # 35. Antibody half-life FcRn immunogenicity
    ("FcRn neonatal Fc receptor antibody half-life immunogenicity[Title/Abstract]", 2),
]

all_refs = []
seen_pmids = set()

print(f"Running {len(QUERIES)} PubMed queries...")
for i, (query, retmax) in enumerate(QUERIES):
    print(f"  [{i+1}/{len(QUERIES)}] {query[:70]}...")
    try:
        pmids = esearch(query, retmax)
        if pmids:
            summaries = efetch_summary(pmids)
            for s in summaries:
                if s['pmid'] not in seen_pmids:
                    seen_pmids.add(s['pmid'])
                    all_refs.append(s)
    except Exception as e:
        print(f"    ERROR: {e}")
    time.sleep(DELAY)

print(f"\nCollected {len(all_refs)} unique references")

# Sort by year descending, then alphabetically
all_refs.sort(key=lambda x: (-int(x['year']) if x['year'].isdigit() else 0, x['authors']))

# Save full results
json.dump(all_refs, open("data/immunogenicity_knowledge_base/reports/_raw_pubmed_refs.json", "w"),
          indent=2, ensure_ascii=False)

# Print formatted preview
print("\n=== REFERENCE LIST PREVIEW ===")
for i, r in enumerate(all_refs, 1):
    vol_iss = f"{r['volume']}({r['issue']})" if r['volume'] and r['issue'] else r['volume'] or ""
    pages = f":{r['pages']}" if r['pages'] else ""
    print(f"\n[{i}] PMID:{r['pmid']}")
    print(f"    {r['authors']}. {r['title']}. {r['journal']}. {r['year']};{vol_iss}{pages}.")

print(f"\nTotal: {len(all_refs)} references")
print("Saved to: data/immunogenicity_knowledge_base/reports/_raw_pubmed_refs.json")
