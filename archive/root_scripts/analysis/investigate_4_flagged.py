"""
Manual deep-dive on 4 flagged records:
1. Adalimumab     stored=30%  DailyMed shows 6.8-9.4%
2. Enuzovimab     stored=1.5% source shows 50%
3. Fulranumab     stored=6.0% source shows 60%
4. Olokizumab     stored=15%  source shows 7%
"""
import re, time, urllib.request, json

def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'InSynBio-Verify/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        return f"ERROR: {e}"

def fetch_pubmed(pmid):
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
           f"?db=pubmed&id={pmid}&rettype=abstract&retmode=text"
           f"&tool=InSynBio&email=info@insynbio.com")
    return fetch(url)

ADA_CTX = re.compile(
    r'anti[\-\s]?drug\s*antibod|immunogenicit|ADA\b|anti[\-\s]?antibod|'
    r'treatment[\-\s]?emerg|immunogenic|nAb\b|neutraliz|HAHA|HACA|HAMA',
    re.IGNORECASE
)

def show_ada_sentences(text, drug_name, max_sents=10):
    if not text or 'ERROR' in text[:10]: return "  [fetch failed]\n"
    sents = re.split(r'(?<=[.!?])\s+', text)
    ada_sents = [s for s in sents if ADA_CTX.search(s)][:max_sents]
    pcts_in_ada = []
    for s in ada_sents:
        found = re.findall(r'(\d+\.?\d*)\s*%', s)
        pcts_in_ada.extend([float(p) for p in found if 0 < float(p) <= 100])
    lines = '\n'.join(f"    {s[:200]}" for s in ada_sents) if ada_sents else "    [no ADA-context sentences found]"
    return f"  ADA-context pcts: {sorted(set(pcts_in_ada))}\n{lines}\n"

# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("1. ADALIMUMAB  stored=30%  DailyMed=6.8-9.4%")
print("=" * 70)
# Adalimumab has many PMIDs. Our stored PMID might be a specific study
# Humira FDA PI: ADA in MTX-naive can be 26-38%, with MTX ~3-6%
# The DailyMed value 6.8-9.4% is likely WITH MTX concomitant use
# Let's check what our master says
import csv
master = list(csv.DictReader(open('data/ada_master_136_curated.csv', encoding='utf-8')))
ada_row = next((r for r in master if 'adalimumab' in r.get('antibody_name','').lower()), None)
if ada_row:
    print(f"  antibody_name:        {ada_row['antibody_name']}")
    print(f"  ada_value_display:    {ada_row['ada_value_display']}")
    print(f"  ada_first_pct:        {ada_row['ada_first_pct']}")
    print(f"  ada_source_pmids:     {ada_row['ada_source_pmids']}")
    print(f"  ada_source_url:       {ada_row['ada_source_url_primary']}")
    print(f"  fc_mutation_notes:    {ada_row['fc_mutation_notes']}")
    print(f"  mtx_comedication:     {ada_row['mtx_comedication']}")
    print(f"  immunosuppressant:    {ada_row['immunosuppressant_context']}")
    print(f"  ada_evidence_chain:   {ada_row['ada_evidence_chain_excerpt'][:500]}")
    print()

# Check PubMed for specific Adalimumab ADA study
# PMID 15846875 is the classic ARMADA trial (adalimumab + MTX)
# Let's search for current stored source
ada_pmid_raw = ada_row.get('ada_source_pmids','') if ada_row else ''
if ada_pmid_raw:
    abs_txt = fetch_pubmed(ada_pmid_raw.split(';')[0].strip())
    time.sleep(0.4)
    print("  PubMed abstract ADA sentences:")
    print(show_ada_sentences(abs_txt, 'adalimumab'))

# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("2. FULRANUMAB  stored=6.0%  PMID 24590506 shows 60%")
print("=" * 70)
fulra_row = next((r for r in master if 'fulranumab' in r.get('antibody_name','').lower()), None)
if fulra_row:
    print(f"  ada_value_display:  {fulra_row['ada_value_display']}")
    print(f"  ada_evidence_chain: {fulra_row['ada_evidence_chain_excerpt'][:400]}")
    print()
abs_txt = fetch_pubmed('24590506')
time.sleep(0.4)
print("  PubMed abstract (PMID 24590506) ADA sentences:")
print(show_ada_sentences(abs_txt, 'fulranumab'))

# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("3. ENUZOVIMAB  stored=1.5%  PMID 39793935 shows 50%")
print("=" * 70)
enuz_row = next((r for r in master if 'enuzovimab' in r.get('antibody_name','').lower()), None)
if enuz_row:
    print(f"  ada_value_display:  {enuz_row['ada_value_display']}")
    print(f"  ada_evidence_chain: {enuz_row['ada_evidence_chain_excerpt'][:400]}")
    print()
abs_txt = fetch_pubmed('39793935')
time.sleep(0.4)
print("  PubMed abstract (PMID 39793935) ADA sentences:")
print(show_ada_sentences(abs_txt, 'enuzovimab'))

# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("4. OLOKIZUMAB  stored=15%  PMID 36109142 shows 7%")
print("=" * 70)
oloki_row = next((r for r in master if 'olokizumab' in r.get('antibody_name','').lower()), None)
if oloki_row:
    print(f"  ada_value_display:  {oloki_row['ada_value_display']}")
    print(f"  ada_evidence_chain: {oloki_row['ada_evidence_chain_excerpt'][:400]}")
    print()
abs_txt = fetch_pubmed('36109142')
time.sleep(0.4)
print("  PubMed abstract (PMID 36109142) ADA sentences:")
print(show_ada_sentences(abs_txt, 'olokizumab'))
