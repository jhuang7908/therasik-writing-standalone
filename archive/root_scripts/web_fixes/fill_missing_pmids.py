"""
Task D: For 68 records with no ada_source_pmids, search PubMed for
the drug name + "anti-drug antibod" or "immunogenicity".
Only fill if a high-confidence PMID is found (drug name in title/abstract + ADA context).
"""
import csv, json, re, time, urllib.request, urllib.parse, subprocess, sys, shutil

MASTER    = r'data\ada_master_136_curated.csv'
KB_MASTER = r'data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv'

def fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='ignore')
    except:
        return None

def pubmed_search_ada(drug):
    """Search PubMed for drug ADA/immunogenicity paper."""
    # Strategy: drug name in title + immunogenicity/ADA in any field
    queries = [
        f'{drug}[ti] AND ("anti-drug antibod"[tiab] OR "immunogenicity"[tiab]) AND clinical[sb]',
        f'{drug}[tiab] AND "anti-drug antibod"[tiab]',
        f'{drug}[tiab] AND "immunogenicity"[tiab] AND "clinical trial"[pt]',
    ]
    for q in queries:
        url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
               f"?db=pubmed&term={urllib.parse.quote(q)}&retmax=5&retmode=json&sort=relevance")
        txt = fetch(url)
        if not txt:
            continue
        try:
            data  = json.loads(txt)
            pmids = data['esearchresult']['idlist']
            count = int(data['esearchresult']['count'])
            if pmids:
                return pmids[0], count
        except:
            pass
        time.sleep(0.2)
    return None, 0

def fetch_abstract(pmid):
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
           f"?db=pubmed&id={pmid}&rettype=abstract&retmode=text")
    return fetch(url) or ''

# ── Load ──────────────────────────────────────────────────────────────────────
with open(MASTER, encoding='utf-8') as f:
    reader     = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    all_rows   = list(reader)
row_map = {r['antibody_name']: r for r in all_rows}

no_pmid = [r for r in all_rows
           if not r.get('ada_source_pmids','').strip() or
           r['ada_source_pmids'].strip() in ('','nan','None')]

print(f"Records missing PMID: {len(no_pmid)}")
print()

filled  = 0
skipped = 0

for row in no_pmid:
    drug = row['antibody_name']
    pmid, count = pubmed_search_ada(drug)
    time.sleep(0.35)
    
    if not pmid:
        print(f"  ○ {drug:25s}  no PMID found")
        skipped += 1
        continue
    
    # Verify PMID mentions the drug name in abstract
    ab = fetch_abstract(pmid)
    time.sleep(0.25)
    drug_lower = drug.lower()
    if drug_lower not in ab.lower():
        print(f"  ✗ {drug:25s}  PMID {pmid} abstract doesn't mention drug")
        skipped += 1
        continue
    
    # Check abstract mentions ADA-related text
    ada_keywords = ('anti-drug', 'immunogenicity', 'antibod', 'ADA', 'neutraliz')
    if not any(k.lower() in ab.lower() for k in ada_keywords):
        print(f"  ✗ {drug:25s}  PMID {pmid} no ADA content")
        skipped += 1
        continue
    
    row['ada_source_pmids'] = pmid
    filled += 1
    print(f"  ✓ {drug:25s}  PMID {pmid} (total hits={count})")

print(f"\nFilled PMIDs: {filled}")
print(f"Skipped/not found: {skipped}")

# Remaining
still_no_pmid = [r['antibody_name'] for r in all_rows
                 if not r.get('ada_source_pmids','').strip() or
                 r['ada_source_pmids'].strip() in ('','nan','None')]
print(f"Still without PMID: {len(still_no_pmid)}")
print(f"  {still_no_pmid}")

# Write
with open(MASTER, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(all_rows)
shutil.copy(MASTER, KB_MASTER)
print(f"\nWritten {len(all_rows)} rows.")

# Rebuild JSON
print("Rebuilding JSON...")
subprocess.run([sys.executable, 'scripts/_regen_json_only.py'], check=False)
shutil.copy('docs/ada_db_data.json', 'insynbio-web-source/ada_db_data.json')
shutil.copy('docs/ada_db_data.json', 'therasik-web-source/ada_db_data.json')
print("Done.")
