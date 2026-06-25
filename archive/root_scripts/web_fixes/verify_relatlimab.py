"""Verify Relatlimab ADA via Opdualag FDA label full text + PMID search."""
import re, time, urllib.request, json, csv

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

def pubmed_esearch(q, retmax=6):
    qu = urllib.parse.quote(q)
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
           f"?db=pubmed&term={qu}&retmax={retmax}&retmode=json"
           f"&tool=InSynBio&email=info@insynbio.com")
    import urllib.parse
    txt = fetch(url)
    try: return json.loads(txt).get('esearchresult',{}).get('idlist',[])
    except: return []

import urllib.parse

ADA_CTX = re.compile(
    r'anti[\-\s]?drug\s*antibod|immunogenicit|\bADA\b|treatment[\-\s]?emerg|'
    r'immunogenic|neutraliz|anti[\-\s]?antibod|anti[\-\s]?product',
    re.IGNORECASE
)

def ada_sents(text):
    if not text or text.startswith('ERROR'): return []
    sents = re.split(r'(?<=[.!?])\s+', re.sub(r'<[^>]+>', ' ', text))
    return [re.sub(r'\s+',' ',s).strip() for s in sents 
            if ADA_CTX.search(s) and 15 < len(s) < 500]

def pcts(sents_list):
    ps = []
    for s in sents_list:
        ps.extend([float(p) for p in re.findall(r'(\d+\.?\d*)\s*%', s) if 0 < float(p) <= 100])
    return sorted(set(ps))

# ─── 1. Try FDA accessdata for Opdualag PI ────────────────────────────────────
print("=== FDA accessdata search ===")
# Opdualag NDA: 761227 (submitted 2022)
fda_url = "https://www.accessdata.fda.gov/drugsatfda_docs/label/2022/761227s000lbl.pdf"
# Can't read PDF directly; try DailyMed HTML rendering
dm_html = fetch("https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=b22c9d83-3256-4e17-85f7-f331a504adc6", 15)
time.sleep(0.5)
if dm_html and not dm_html.startswith('ERROR'):
    sents_dm = ada_sents(dm_html)
    ps_dm = pcts(sents_dm)
    print(f"  DailyMed HTML ADA pcts: {ps_dm}")
    for s in sents_dm[:8]:
        print(f"    → {s[:200]}")
else:
    print(f"  {dm_html[:80]}")

# ─── 2. Opdualag section 6 (immunogenicity) from HIGHLIGHTS ───────────────────
print("\n=== Opdualag label section search via DailyMed full text ===")
full_label = fetch("https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=b22c9d83-3256-4e17-85f7-f331a504adc6&type=display", 15)
time.sleep(0.5)
if full_label and not full_label.startswith('ERROR'):
    sents_fl = ada_sents(full_label)
    ps_fl = pcts(sents_fl)
    print(f"  Full label ADA pcts: {ps_fl}")
    for s in sents_fl[:8]:
        print(f"    → {s[:200]}")

# ─── 3. PubMed search for Relatlimab immunogenicity ───────────────────────────
print("\n=== PubMed: relatlimab immunogenicity ===")
pmids_r = pubmed_esearch('relatlimab immunogenicity anti-drug antibody', retmax=6)
time.sleep(0.4)
print(f"  Found: {pmids_r}")
for pmid in pmids_r[:4]:
    abs_txt = pubmed_efetch(pmid)
    time.sleep(0.4)
    if abs_txt and not abs_txt.startswith('ERROR'):
        sents_p = ada_sents(abs_txt)
        ps_p = pcts(sents_p)
        title_m = re.search(r'\n\n(.+?)\n', abs_txt)
        title = title_m.group(1)[:70] if title_m else '?'
        if ps_p or sents_p:
            print(f"\n  PMID {pmid}: {title}")
            print(f"    ADA pcts: {ps_p}")
            for s in sents_p[:3]:
                print(f"    → {s[:200]}")

# ─── 4. Try RELATIVITY-047 trial paper (the Phase III registration trial) ─────
print("\n=== RELATIVITY-047 Phase III (Tawbi et al.) ===")
# PMID 35235327 = NEJM 2022 Mar 24 (RELATIVITY-047)
abs_047 = pubmed_efetch('35235327')
time.sleep(0.4)
print(abs_047[:400])
sents_047 = ada_sents(abs_047)
ps_047 = pcts(sents_047)
print(f"\n  ADA-context pcts: {ps_047}")
for s in sents_047:
    print(f"  → {s[:220]}")

# Check stored row
master = list(csv.DictReader(open('data/ada_master_136_curated.csv', encoding='utf-8')))
rrow = next((r for r in master if 'relatlimab' in r.get('antibody_name','').lower()), None)
if rrow:
    print(f"\n=== Stored Relatlimab record ===")
    print(f"  ada_value_display: {rrow['ada_value_display']}")
    print(f"  evidence_tier:     {rrow['evidence_tier']}")
    print(f"  ada_source_pmids:  {rrow['ada_source_pmids']}")
    print(f"  url:               {rrow['ada_source_url_primary']}")
    print(f"  chain: {rrow['ada_evidence_chain_excerpt'][:400]}")
