"""
Resolve Olokizumab ADA discrepancy.
Stored: 10-15%   PMID 36109142: 3.2-7.0%

Strategy:
1. Read full PMID 36109142 abstract carefully
2. Search PubMed for ALL Olokizumab immunogenicity papers
3. Check DailyMed / EMA SmPC if available
4. Check our stored evidence chain excerpt
5. Weigh evidence and determine authoritative value
"""
import re, time, urllib.request, urllib.parse, json, csv

def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'InSynBio-Verify/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        return f"ERROR: {e}"

def pubmed_efetch(pmid):
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
           f"?db=pubmed&id={pmid}&rettype=abstract&retmode=text"
           f"&tool=InSynBio&email=info@insynbio.com")
    return fetch(url)

def pubmed_esearch(query, retmax=10):
    q = urllib.parse.quote(query)
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
           f"?db=pubmed&term={q}&retmax={retmax}&retmode=json"
           f"&tool=InSynBio&email=info@insynbio.com")
    txt = fetch(url)
    try:
        d = json.loads(txt)
        return d.get('esearchresult', {}).get('idlist', [])
    except:
        return []

ADA_CTX = re.compile(
    r'anti[\-\s]?drug\s*antibod|immunogenicit|\bADA\b|treatment[\-\s]?emerg|'
    r'immunogenic|neutraliz|anti[\-\s]?antibod|\bHAHA\b|\bHACA\b',
    re.IGNORECASE
)

def extract_ada_sentences(text):
    if not text or text.startswith('ERROR'): return []
    sents = re.split(r'(?<=[.!?])\s+', text)
    return [s for s in sents if ADA_CTX.search(s)]

def extract_pcts(sents):
    pcts = []
    for s in sents:
        found = re.findall(r'(\d+\.?\d*)\s*%', s)
        pcts.extend([float(p) for p in found if 0 < float(p) <= 100])
    return sorted(set(pcts))

# ─── Step 1: Read stored evidence chain ────────────────────────────────────
print("=" * 70)
print("STORED EVIDENCE CHAIN")
print("=" * 70)
master = list(csv.DictReader(open('data/ada_master_136_curated.csv', encoding='utf-8')))
row = next((r for r in master if 'olokizumab' in r.get('antibody_name','').lower()), None)
if row:
    print(f"  ada_value_display:      {row['ada_value_display']}")
    print(f"  ada_first_pct:          {row['ada_first_pct']}")
    print(f"  evidence_tier:          {row['evidence_tier']}")
    print(f"  ada_source_pmids:       {row['ada_source_pmids']}")
    print(f"  ada_source_url_primary: {row['ada_source_url_primary']}")
    print(f"  indication_text:        {row['indication_text']}")
    print(f"  route_curated:          {row['route_curated']}")
    print(f"  dose_mg:                {row['dose_mg']}")
    print(f"  dose_freq:              {row['dose_freq']}")
    print()
    print("  Evidence chain excerpt:")
    print(f"  {row['ada_evidence_chain_excerpt'][:800]}")
    print()

# ─── Step 2: Full abstract of PMID 36109142 ────────────────────────────────
print("=" * 70)
print("PMID 36109142 — FULL ABSTRACT")
print("=" * 70)
abs1 = pubmed_efetch('36109142')
time.sleep(0.4)
print(abs1[:2000] if abs1 and not abs1.startswith('ERROR') else f"  {abs1}")
ada_sents1 = extract_ada_sentences(abs1)
pcts1 = extract_pcts(ada_sents1)
print(f"\n  ADA-context pcts from PMID 36109142: {pcts1}")
print("  ADA sentences:")
for s in ada_sents1:
    print(f"    → {s[:200]}")

# ─── Step 3: PubMed search for all Olokizumab immunogenicity papers ──────────
print()
print("=" * 70)
print("PUBMED SEARCH: olokizumab immunogenicity ADA")
print("=" * 70)
pmids_search = pubmed_esearch('olokizumab immunogenicity anti-drug antibody', retmax=10)
time.sleep(0.4)
print(f"  Found PMIDs: {pmids_search}")

all_evidence = {}

for pmid in pmids_search[:6]:
    if pmid == '36109142':
        abs_txt = abs1
    else:
        abs_txt = pubmed_efetch(pmid)
        time.sleep(0.4)
    
    if abs_txt and not abs_txt.startswith('ERROR'):
        sents = extract_ada_sentences(abs_txt)
        pcts = extract_pcts(sents)
        title_m = re.search(r'\n\n(.+?)\n', abs_txt)
        title = title_m.group(1)[:80] if title_m else '?'
        year_m = re.search(r'(\d{4})\s+\w+\s+\d+', abs_txt)
        year = year_m.group(1) if year_m else '?'
        print(f"\n  PMID {pmid} [{year}]: {title}")
        print(f"    ADA pcts: {pcts}")
        for s in sents[:3]:
            print(f"    → {s[:200]}")
        if pcts:
            all_evidence[pmid] = {'pcts': pcts, 'title': title, 'year': year}

# ─── Step 4: DailyMed check ─────────────────────────────────────────────────
print()
print("=" * 70)
print("DAILYMED: Olokizumab")
print("=" * 70)
dm_search = fetch('https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name=olokizumab&pagesize=3')
time.sleep(0.4)
try:
    dm = json.loads(dm_search)
    spls = dm.get('data', [])
    print(f"  DailyMed entries: {len(spls)}")
    for spl in spls:
        print(f"    setid={spl.get('setid','')} title={spl.get('title','')[:60]}")
        setid = spl.get('setid', '')
        if setid:
            xml = fetch(f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml", timeout=12)
            time.sleep(0.4)
            if xml and not xml.startswith('ERROR'):
                ada_sents_dm = extract_ada_sentences(xml)
                pcts_dm = extract_pcts(ada_sents_dm)
                print(f"    ADA pcts from label: {pcts_dm}")
                for s in ada_sents_dm[:3]:
                    print(f"      → {s[:200]}")
            else:
                print(f"    Label fetch: {str(xml)[:80]}")
except Exception as e:
    print(f"  DailyMed parse error: {e}")
    print(f"  Raw: {dm_search[:200]}")

# ─── Step 5: EMA / Artlegia registration trial search ───────────────────────
print()
print("=" * 70)
print("PUBMED SEARCH: olokizumab phase 3 rheumatoid arthritis registration")
print("=" * 70)
pmids2 = pubmed_esearch('olokizumab phase 3 rheumatoid arthritis', retmax=8)
time.sleep(0.4)
print(f"  Found: {pmids2}")

for pmid in pmids2[:5]:
    if pmid in pmids_search:
        continue
    abs_txt = pubmed_efetch(pmid)
    time.sleep(0.4)
    if abs_txt and not abs_txt.startswith('ERROR'):
        sents = extract_ada_sentences(abs_txt)
        pcts = extract_pcts(sents)
        title_m = re.search(r'\n\n(.+?)\n', abs_txt)
        title = title_m.group(1)[:80] if title_m else '?'
        year_m = re.search(r'(\d{4})\s+\w+\s+\d+', abs_txt)
        year = year_m.group(1) if year_m else '?'
        if pcts or sents:
            print(f"\n  PMID {pmid} [{year}]: {title}")
            print(f"    ADA pcts: {pcts}")
            for s in sents[:3]:
                print(f"    → {s[:200]}")
            if pcts:
                all_evidence[pmid] = {'pcts': pcts, 'title': title, 'year': year}

# ─── Step 6: Verdict ────────────────────────────────────────────────────────
print()
print("=" * 70)
print("EVIDENCE SUMMARY & VERDICT")
print("=" * 70)
print(f"  Stored value: {row['ada_value_display']} (Tier {row['evidence_tier']})")
print(f"  Source: {row['ada_source_url_primary']}")
print()
print(f"  PMIDs with ADA data found ({len(all_evidence)}):")
for pmid, ev in sorted(all_evidence.items(), key=lambda x: x[1].get('year','')):
    print(f"    PMID {pmid} [{ev['year']}]: ADA = {ev['pcts']}  — {ev['title'][:60]}")
