"""Targeted PMID search for the 20 remaining drugs."""
import csv, json, re, time, urllib.request, urllib.parse, subprocess, sys, shutil, math

MASTER    = r'data\ada_master_136_curated.csv'
KB_MASTER = r'data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv'

def is_empty(v):
    s = str(v or '').strip()
    return s in ('', 'nan', 'None', 'none', 'NaN', '0', '0.0')

def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='ignore')
    except: return None

def search(q, retmax=5):
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
           f"?db=pubmed&term={urllib.parse.quote(q)}&retmax={retmax}&retmode=json&sort=relevance")
    txt = fetch(url)
    if not txt: return [], 0
    try:
        d = json.loads(txt)
        return d['esearchresult']['idlist'], int(d['esearchresult']['count'])
    except: return [], 0

def abstract(pmid):
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
           f"?db=pubmed&id={pmid}&rettype=abstract&retmode=text")
    return fetch(url) or ''

# Known trial names / alternative search terms for hard cases
TARGETED = {
    "Anifrolumab":    [
        'anifrolumab immunogenicity "anti-drug antibod"',
        '"TULIP" anifrolumab immunogenicity',
    ],
    "Bezlotoxumab":   [
        'bezlotoxumab "anti-drug antibod"',
        'MODIFY bezlotoxumab immunogenicity Wilcox',
    ],
    "Brodalumab":     [
        'brodalumab anti-drug antibod immunogenicity',
        '"AMAGINE" brodalumab immunogenicity psoriasis',
    ],
    "Erenumab":       [
        'erenumab anti-drug antibod immunogenicity migraine',
        '"STRIVE" OR "ARISE" erenumab anti-drug antibod',
    ],
    "Teprotumumab":   [
        'teprotumumab immunogenicity anti-drug',
        '"tepezza" immunogenicity anti-drug antibod',
        'teprotumumab thyroid eye immunogenicity',
    ],
    "Brolucizumab":   [
        'brolucizumab immunogenicity anti-drug antibod',
        '"HAWK" OR "HARRIER" brolucizumab immunogenicity',
    ],
    "Naxitamab":      [
        'naxitamab anti-drug antibod immunogenicity neuroblastoma',
    ],
    "Reslizumab":     [
        'reslizumab anti-drug antibod immunogenicity asthma',
    ],
    "Retifanlimab":   [
        'retifanlimab immunogenicity anti-drug antibod',
        '"Zynyz" retifanlimab anti-drug antibod',
    ],
    "Romosozumab":    [
        'romosozumab immunogenicity anti-drug antibod',
        '"ARCH" OR "FRAME" romosozumab immunogenicity',
    ],
    "Atoltivimab":    [
        'atoltivimab immunogenicity anti-drug antibod Ebola',
    ],
    "Clesrovimab":    [
        'clesrovimab immunogenicity anti-drug antibod RSV',
    ],
    "Evolocumab":     [
        'evolocumab immunogenicity anti-drug antibod PCSK9',
        '"FOURIER" OR "OSLER" evolocumab immunogenicity',
        '"evolocumab" "neutralizing antibod" PCSK9',
    ],
    "Relatlimab":     [
        'relatlimab anti-drug antibod immunogenicity LAG-3 melanoma',
        '"RELATIVITY" relatlimab immunogenicity anti-drug',
    ],
    "Axatilimab":     [
        'axatilimab anti-drug antibod immunogenicity GvHD',
        '"AGAVE" axatilimab immunogenicity',
    ],
    "Crizanlizumab":  [
        'crizanlizumab anti-drug antibod immunogenicity sickle cell',
        '"SUSTAIN" crizanlizumab immunogenicity',
    ],
    "Elotuzumab":     [
        'elotuzumab anti-drug antibod immunogenicity myeloma',
        '"ELOQUENT" elotuzumab immunogenicity anti-drug',
    ],
    "Obinutuzumab":   [
        'obinutuzumab anti-drug antibod immunogenicity lymphoma CLL',
        '"CLL11" OR "GALLIUM" obinutuzumab immunogenicity',
    ],
    "Satralizumab":   [
        'satralizumab anti-drug antibod immunogenicity NMOSD',
        '"SAkuraSky" OR "SAkuraStar" satralizumab immunogenicity',
    ],
    "Elranatamab":    [
        'elranatamab anti-drug antibod immunogenicity myeloma',
        '"MAGNETISMM" elranatamab immunogenicity anti-drug',
    ],
}

with open(MASTER, encoding='utf-8') as f:
    reader     = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    all_rows   = list(reader)
row_map = {r['antibody_name']: r for r in all_rows}

filled = 0
for drug, queries in TARGETED.items():
    row = row_map.get(drug)
    if not row or not is_empty(row.get('ada_source_pmids', '')):
        continue  # already has PMID

    found = False
    for q in queries:
        pmids, count = search(q)
        time.sleep(0.3)
        if not pmids:
            continue
        for pmid in pmids[:3]:
            ab = abstract(pmid)
            time.sleep(0.25)
            drug_lower = drug.lower()
            # Check drug name variations
            name_variants = [drug_lower, drug_lower.replace('mab', ''), drug_lower[:6]]
            if not any(v in ab.lower() for v in name_variants if len(v) > 4):
                continue
            ada_kw = ('anti-drug', 'immunogenicity', 'ADA', 'antibod', 'neutraliz')
            if not any(k.lower() in ab.lower() for k in ada_kw):
                continue
            row['ada_source_pmids'] = pmid
            print(f"  ✓ {drug:25s}  PMID {pmid} (q: {q[:40]}...)")
            filled += 1
            found = True
            break
        if found:
            break
    if not found:
        print(f"  ○ {drug:25s}  no PMID found")

print(f"\nFilled: {filled}")
still_no = [r['antibody_name'] for r in all_rows if is_empty(r.get('ada_source_pmids',''))]
pct = 100*(len(all_rows)-len(still_no))/len(all_rows)
print(f"PMID coverage: {len(all_rows)-len(still_no)}/138 ({pct:.0f}%)")
print(f"Remaining (likely FDA PI only): {still_no}")

with open(MASTER, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(all_rows)
shutil.copy(MASTER, KB_MASTER)

print("Rebuilding JSON...")
subprocess.run([sys.executable, 'scripts/_regen_json_only.py'], check=False)
shutil.copy('docs/ada_db_data.json', 'insynbio-web-source/ada_db_data.json')
shutil.copy('docs/ada_db_data.json', 'therasik-web-source/ada_db_data.json')
print("Done.")
