"""
Second batch of targeted PubMed searches for key known papers in ADA field.
"""
import requests, time, json, os

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
DELAY = 0.4

def esearch(query, retmax=3):
    r = requests.get(BASE + "esearch.fcgi",
                     params={"db":"pubmed","term":query,"retmax":retmax,"retmode":"json"}, timeout=15)
    r.raise_for_status()
    time.sleep(DELAY)
    return r.json().get("esearchresult",{}).get("idlist",[])

def efetch_summary(pmids):
    if not pmids: return []
    r = requests.get(BASE + "esummary.fcgi",
                     params={"db":"pubmed","id":",".join(pmids),"retmode":"json"}, timeout=15)
    r.raise_for_status()
    data = r.json().get("result", {})
    time.sleep(DELAY)
    out = []
    for pmid in pmids:
        if pmid not in data: continue
        d = data[pmid]
        authors = [a.get("name","") for a in d.get("authors",[])]
        if len(authors) >= 3:
            au_str = f"{authors[0]}, {authors[1]}, {authors[2]}" + (" et al." if len(authors) > 3 else "")
        elif authors:
            au_str = ", ".join(authors)
        else:
            au_str = "[No authors listed]"
        out.append({"pmid": pmid, "title": d.get("title","").rstrip("."),
                    "authors": au_str, "journal": d.get("source",""),
                    "year": d.get("pubdate","")[:4],
                    "volume": d.get("volume",""), "issue": d.get("issue",""),
                    "pages": d.get("pages","")})
    return out

# Load existing PMIDs to avoid duplicates
existing = json.load(open("data/immunogenicity_knowledge_base/reports/_raw_pubmed_refs.json"))
seen = {r['pmid'] for r in existing}
print(f"Existing: {len(seen)} PMIDs")

QUERIES2 = [
    # Core ADA / immunogenicity reviews
    ("Harding FA CDR immunogenicity humanized fully human antibody MAbs 2010", 2),
    ("Shankar G immunoassay anti-drug antibody validation 2008", 2),
    ("Jawa V immunogenicity risk factors biotherapeutic 2013", 2),
    ("Deehan M immunogenicity biopharmaceutical risk factors 2015", 2),
    ("van Schouwenburg anti-drug antibody formation mechanisms 2013", 2),
    ("Baker MP Jones TD CDR sequence T cell epitopes immunogenicity", 2),
    ("Presta LG engineering therapeutic antibodies minimize immunogenicity optimize function 2006", 2),
    ("De Groot AS Scott DW immunogenicity protein therapeutics Trends Immunol 2007", 2),
    ("Rosenberg AS effects protein aggregates immunologic perspective AAPS 2006", 2),
    ("Fathallah AM subcutaneous immunogenicity mechanistic perspective", 2),
    # Assay and detection
    ("Mire-Sluis AR recommendations testing biologics anti-drug antibodies 2004", 2),
    ("Koren E recommendations bioanalytical methods anti-drug antibodies 2008", 2),
    ("Gunn GR 3 three tier testing paradigm immunogenicity 2011", 2),
    ("Wadhwa M Thorpe R anti-drug antibody isotyping clinical relevance 2018", 2),
    # Germline identity humanization
    ("Jones PT humanization antibody CDR grafting Nature 1986", 2),
    ("Verhoeyen M reshaping antibody humanizing anti-lysozyme 1988", 2),
    ("Hwang WY Foote J humanization antibodies current status 2005", 2),
    # MHC-II and T cell epitopes
    ("Larsen MV Lundegaard C NetMHCIIpan MHC class II pan-specific 2010", 2),
    ("Reynisson B NetMHCIIpan-4.0 MHC-II peptide binding prediction 2020", 2),
    ("Mauldin IS cross-reactive T cells anti-drug antibodies 2016", 2),
    # Surface/hydrophobicity/aggregation
    ("Chennamsetty N aggregation prone regions antibody 2009", 2),
    ("Haberger M assessment aggregation prone regions antibody variants 2014", 2),
    ("van der Kant R prediction aggregation colloidal stability antibodies", 2),
    # Clinical specific
    ("Bartelds GM antidrug antibody adalimumab JAMA 2011", 2),
    ("Vultaggio A mechanisms consequences anti-drug antibodies biologics 2012", 2),
    ("Nanda SK Bhatt DL monoclonal antibody biologic therapy outcomes 2018", 2),
    # Structure/interface
    ("Abhinandan KR Martin AC analysis antibody VH-VL domain packing 2010", 2),
    # Computational tools
    ("Dunbar J Deane CM ABARCII antibody numbering recognition common immunoglobulin", 2),
    ("Mitternacht S FreeSASA calculating accessible surface areas free open-source", 2),
    # IMGT
    ("Lefranc MP IMGT the international ImMunoGeneTics information system", 2),
    # Population repertoire
    ("Soto C Bombardi RG naive antibody germline gene usage human repertoire", 2),
    ("Glanville J Zhai W common antibody germline gene features", 2),
]

new_refs = []
for i, (query, retmax) in enumerate(QUERIES2):
    print(f"  [{i+1}/{len(QUERIES2)}] {query[:65]}...")
    try:
        pmids = [p for p in esearch(query, retmax) if p not in seen]
        if pmids:
            summaries = efetch_summary(pmids)
            for s in summaries:
                seen.add(s['pmid'])
                new_refs.append(s)
    except Exception as e:
        print(f"    ERROR: {e}")

print(f"\nNew references: {len(new_refs)}")

# Merge and save
all_refs = existing + new_refs
all_refs.sort(key=lambda x: (-int(x['year']) if x['year'].isdigit() else 0, x['authors']))

json.dump(all_refs, open("data/immunogenicity_knowledge_base/reports/_raw_pubmed_refs.json", "w"),
          indent=2, ensure_ascii=False)

print(f"Total combined: {len(all_refs)} references")
for i, r in enumerate(new_refs, 1):
    vol_iss = f"{r['volume']}({r['issue']})" if r['volume'] and r['issue'] else r['volume'] or ""
    pages = f":{r['pages']}" if r['pages'] else ""
    print(f"\n[NEW {i}] PMID:{r['pmid']}")
    print(f"  {r['authors']}. {r['title']}. {r['journal']}. {r['year']};{vol_iss}{pages}.")
