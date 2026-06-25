"""
Verify 14 high-risk ADA records (no PMID + weak URL + boilerplate chain).
Strategy:
  1. Try DailyMed API to get FDA PI label → extract ADA section
  2. Try PubMed search for drug + "anti-drug antibody" → check PMID
  3. Report findings for each drug
"""
import urllib.request, urllib.parse, json, re, time, csv

DRUGS = [
    ("Risankizumab",  "skyrizi"),
    ("Belimumab",     "benlysta"),
    ("Daratumumab",   "darzalex"),
    ("Dupilumab",     "dupixent"),
    ("Ebronucimab",   None),
    ("Ramucirumab",   "cyramza"),
    ("Secukinumab",   "cosentyx"),
    ("Tremelimumab",  "imjudo"),
    ("Eculizumab",    "soliris"),
    ("Mogamulizumab", "poteligeo"),
    ("Obinutuzumab",  "gazyva"),
    ("Ocrelizumab",   "ocrevus"),
    ("Palivizumab",   "synagis"),
    ("Pertuzumab",    "perjeta"),
]

MASTER = r'data\ada_master_136_curated.csv'
rows   = {r['antibody_name']: r for r in csv.DictReader(open(MASTER, encoding='utf-8'))}

def fetch(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return f"ERROR: {e}"

def dailymed_search(brand_name):
    """Search DailyMed for setid of a drug label."""
    q  = urllib.parse.quote(brand_name)
    url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name={q}&pagesize=3"
    txt = fetch(url)
    try:
        data = json.loads(txt)
        items = data.get('data', [])
        return [(i.get('setid',''), i.get('title','')) for i in items[:3]]
    except:
        return []

def dailymed_get_label(setid):
    """Fetch label XML text for a setid."""
    url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml"
    return fetch(url, timeout=15)

def extract_ada_section(text):
    """Extract ADA-relevant portion from FDA label XML/text."""
    # Look for IMMUNOGENICITY section
    pattern = re.compile(
        r'(immunogenicity[^<]{0,2000})',
        re.IGNORECASE | re.DOTALL
    )
    m = pattern.search(text)
    if m:
        chunk = m.group(1)[:1500]
        # Remove XML tags
        chunk = re.sub(r'<[^>]+>', ' ', chunk)
        chunk = re.sub(r'\s+', ' ', chunk).strip()
        return chunk
    return None

def extract_pct(text):
    """Extract ADA percentages from text."""
    pats = [
        r'(\d+\.?\d*)\s*%.*?(?:ADA|anti.drug|antibod)',
        r'(?:ADA|anti.drug|antibod)[^%]{0,100}?(\d+\.?\d*)\s*%',
        r'(\d+)/(\d+)\s+(?:patient|subject)',
    ]
    found = []
    for p in pats:
        for m in re.finditer(p, text, re.IGNORECASE):
            if m.lastindex == 2:
                n, d = int(m.group(1)), int(m.group(2))
                if d > 0:
                    found.append(f"{n}/{d} ({100*n/d:.1f}%)")
            else:
                found.append(m.group(1) + '%')
    return found[:5]

def pubmed_search(drug_name):
    """PubMed search for drug + ADA."""
    q  = urllib.parse.quote(f'{drug_name}[tiab] AND "anti-drug antibod"[tiab]')
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={q}&retmax=5&retmode=json&sort=relevance"
    txt = fetch(url)
    try:
        data  = json.loads(txt)
        pmids = data['esearchresult']['idlist']
        count = data['esearchresult']['count']
        return pmids, int(count)
    except:
        return [], 0

def pubmed_abstract(pmid):
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&rettype=abstract&retmode=text"
    return fetch(url)

# ─────────────────────────────────────────────────────────────────────────────
results = []
print(f"{'='*72}")
print("VERIFYING 14 HIGH-RISK ADA RECORDS")
print(f"{'='*72}\n")

for drug, brand in DRUGS:
    stored = rows.get(drug, {})
    stored_val = stored.get('ada_value_display','?')
    stored_url = stored.get('ada_source_url_primary','')
    stored_tier = stored.get('evidence_tier','?')
    
    print(f"{'─'*72}")
    print(f"▶ {drug} (brand: {brand or 'unknown'})  stored={stored_val[:40]}")
    
    result = {
        'drug': drug, 'stored_val': stored_val, 'stored_url': stored_url,
        'stored_tier': stored_tier,
        'dailymed_setid': None, 'dailymed_ada': None,
        'pubmed_count': 0, 'pubmed_pmids': [],
        'pubmed_ada_text': None,
        'verdict': 'PENDING',
        'action': '',
    }
    
    # ── 1. DailyMed ──────────────────────────────────────────────────────────
    if brand:
        sets = dailymed_search(brand)
        if sets:
            setid, title = sets[0]
            print(f"  DailyMed found: {title[:60]} (setid={setid})")
            label_xml = dailymed_get_label(setid)
            ada_sec   = extract_ada_section(label_xml)
            if ada_sec:
                pcts = extract_pct(ada_sec)
                print(f"  → ADA section found ({len(ada_sec)} chars), pcts={pcts}")
                result['dailymed_setid'] = setid
                result['dailymed_ada']   = ada_sec[:400]
                
                # Compare with stored
                stored_num = None
                m = re.search(r'(\d+\.?\d*)', stored_val.replace('<','').replace('>',''))
                if m: stored_num = float(m.group(1))
                
                match = False
                for p in pcts:
                    num_m = re.search(r'(\d+\.?\d*)', p)
                    if num_m:
                        found_num = float(num_m.group(1))
                        if stored_num and abs(found_num - stored_num) < 1.0:
                            match = True
                
                if pcts:
                    if match or stored_num is None:
                        result['verdict'] = 'CONFIRMED_BY_FDA_PI'
                        result['action']  = f'Update URL to DailyMed setid={setid}'
                    else:
                        result['verdict'] = 'DISCREPANCY'
                        result['action']  = f'Stored={stored_val} vs FDA PI found={pcts}'
                else:
                    result['verdict'] = 'FDA_PI_NO_ADA_SECTION'
                    result['action']  = 'Manual check needed'
            else:
                print(f"  → DailyMed found label but no ADA section extracted")
                result['verdict'] = 'DAILYMED_NO_ADA'
        else:
            print(f"  DailyMed: no results for '{brand}'")
            result['verdict'] = 'NO_DAILYMED'
    else:
        print(f"  DailyMed: skipped (no brand name)")
    
    # ── 2. PubMed ─────────────────────────────────────────────────────────────
    pmids, count = pubmed_search(drug)
    result['pubmed_count'] = count
    result['pubmed_pmids'] = pmids
    print(f"  PubMed: {count} results, top PMIDs: {pmids[:3]}")
    
    # Fetch first abstract to check ADA data
    if pmids and result['verdict'] in ('DAILYMED_NO_ADA', 'NO_DAILYMED', 'PENDING', 'FDA_PI_NO_ADA_SECTION'):
        ab = pubmed_abstract(pmids[0])
        pcts = extract_pct(ab)
        if pcts:
            print(f"  → PMID {pmids[0]} mentions ADA pcts: {pcts}")
            result['pubmed_ada_text'] = ab[:300]
            if result['verdict'] in ('NO_DAILYMED', 'PENDING'):
                result['verdict'] = 'CONFIRMED_BY_PMID'
                result['action']  = f'PMID={pmids[0]} found ADA {pcts}'
        else:
            print(f"  → PMID {pmids[0]}: no clear ADA % found in abstract")
        time.sleep(0.4)
    
    print(f"  ✦ VERDICT: {result['verdict']}  → {result['action'][:80]}")
    results.append(result)
    time.sleep(0.5)

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*72}")
print("SUMMARY")
print(f"{'='*72}")
verdicts = {}
for r in results:
    v = r['verdict']
    verdicts[v] = verdicts.get(v, 0) + 1
for v, n in sorted(verdicts.items()):
    print(f"  {v}: {n}")

print(f"\n{'─'*72}")
print("RECORDS NEEDING ACTION:")
for r in results:
    if r['verdict'] not in ('CONFIRMED_BY_FDA_PI',):
        print(f"  {r['drug']:20s} {r['verdict']:30s} → {r['action'][:70]}")

# Save report
out = []
for r in results:
    out.append({k: str(v)[:200] for k, v in r.items()})
with open('data/14_highrisk_verification.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("\nSaved: data/14_highrisk_verification.json")
