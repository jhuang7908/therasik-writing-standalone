"""
ADA Evidence Chain Verification Pipeline
=========================================
Protocol:
1. For each record, identify source type (PMID / FDA-PI / URL / unknown)
2. For PMID records: fetch PubMed abstract via E-utilities API
3. Extract ADA % values from abstract text using regex
4. Compare against stored ada_value_display
5. For FDA-PI records: fetch DailyMed label via RXCUI or drug name
6. Flag: VERIFIED / DISCREPANCY / UNCERTAIN / UNREACHABLE
7. Write audit report CSV + update evidence fields

Accuracy principle: "uncertain" > "wrong"
"""

import csv, json, re, time, urllib.request, urllib.parse, urllib.error
import os

MASTER_CSV = r'data\ada_master_136_curated.csv'
REPORT_OUT  = r'data\ada_evidence_verification_report.csv'
UPDATED_CSV = r'data\ada_master_verified.csv'

PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
DAILYMED_API = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json"

# ── Helpers ──────────────────────────────────────────────────────────────────

def fetch_url(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'InSynBio-ADA-Verifier/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None

def fetch_pubmed_abstract(pmid):
    """Fetch PubMed abstract text for a given PMID."""
    pmid = str(pmid).strip().split()[0]  # take first if multiple
    url = (f"{PUBMED_EFETCH}?db=pubmed&id={pmid}"
           f"&rettype=abstract&retmode=text&tool=InSynBio&email=info@insynbio.com")
    text = fetch_url(url)
    if text and len(text) > 50:
        return text
    return None

def extract_pct_values(text):
    """Extract all percentage-like values from text."""
    if not text: return []
    # Match patterns like: 5.3%, 5.3 %, 5%, ~5%, <5%, 53/100 (53%), etc.
    pcts = re.findall(r'(\d+\.?\d*)\s*%', text)
    fractions = re.findall(r'(\d+)\s*/\s*(\d+)', text)
    results = [float(p) for p in pcts if float(p) <= 100]
    for num, denom in fractions:
        try:
            pct = 100 * int(num) / int(denom)
            if 0 < pct <= 100:
                results.append(round(pct, 1))
        except: pass
    return sorted(set(results))

def parse_stored_ada(ada_display):
    """Extract numeric ADA % from the stored display string."""
    if not ada_display: return None
    # Try to find first percentage
    m = re.search(r'(\d+\.?\d*)\s*%', str(ada_display))
    if m:
        v = float(m.group(1))
        if 0 <= v <= 100:
            return v
    return None

def ada_context_match(extracted_pcts, stored_pct, window=3.0):
    """
    Check if any extracted percentage is within `window`% of the stored value.
    Returns (matched, closest_val, delta)
    """
    if stored_pct is None or not extracted_pcts:
        return False, None, None
    closest = min(extracted_pcts, key=lambda x: abs(x - stored_pct))
    delta = abs(closest - stored_pct)
    return delta <= window, closest, round(delta, 2)

def classify_source(row):
    """Determine verification source type."""
    pmids = str(row.get('ada_source_pmids', '')).strip()
    url   = str(row.get('ada_source_url_primary', '')).strip()
    tier  = str(row.get('evidence_tier', '')).strip()
    
    if pmids and pmids not in ('', 'nan', 'None'):
        return 'PMID', pmids.split(';')[0].strip().split(',')[0].strip()
    if 'fda.gov' in url.lower() or 'accessdata' in url.lower() or 'dailymed' in url.lower():
        return 'FDA_PI', url
    if url and url not in ('', 'nan', 'None'):
        return 'URL', url
    return 'NONE', ''

# ── Main verification loop ────────────────────────────────────────────────────

rows = list(csv.DictReader(open(MASTER_CSV, encoding='utf-8')))
print(f"Loaded {len(rows)} records\n")

# Source type distribution
source_dist = {}
for r in rows:
    stype, _ = classify_source(r)
    source_dist[stype] = source_dist.get(stype, 0) + 1
print("Source distribution:")
for k, v in sorted(source_dist.items()):
    print(f"  {k}: {v}")

results = []
n_verified = 0
n_discrepancy = 0
n_uncertain = 0
n_unreachable = 0
n_skipped = 0

for i, row in enumerate(rows):
    name = row.get('antibody_name', row.get('name', f'row{i}'))
    stored_display = row.get('ada_value_display', '')
    stored_pct = parse_stored_ada(stored_display)
    tier = row.get('evidence_tier', '?')
    stype, src_id = classify_source(row)
    
    status = 'PENDING'
    verified_val = None
    delta = None
    extracted = []
    source_text_snippet = ''
    note = ''

    if stype == 'PMID':
        # Fetch PubMed abstract
        abstract = fetch_pubmed_abstract(src_id)
        time.sleep(0.35)  # NCBI rate limit: 3 req/sec
        if abstract is None:
            status = 'UNREACHABLE'
            note = f'PubMed fetch failed for PMID {src_id}'
            n_unreachable += 1
        else:
            extracted = extract_pct_values(abstract)
            # Context: search ADA-related terms near percentages
            ada_context = re.findall(
                r'(?:immunogen|anti.?drug|ADA|antibod).{0,200}?(\d+\.?\d*)\s*%',
                abstract, re.IGNORECASE
            )
            context_pcts = [float(p) for p in ada_context if float(p) <= 100]
            check_pcts = context_pcts if context_pcts else extracted

            if stored_pct is None:
                # Non-numeric display (e.g. "0% or not detected")
                if any(kw in abstract.lower() for kw in ['no ada', 'not detected', '0%', 'none detected', 'negative']):
                    status = 'VERIFIED'
                    note = 'Source confirms no/zero ADA'
                    n_verified += 1
                else:
                    status = 'UNCERTAIN'
                    note = 'Stored value non-numeric; cannot auto-verify'
                    n_uncertain += 1
            else:
                matched, closest, d = ada_context_match(check_pcts, stored_pct, window=3.0)
                if matched:
                    status = 'VERIFIED'
                    verified_val = closest
                    delta = d
                    n_verified += 1
                elif check_pcts:
                    # Values found but don't match
                    status = 'DISCREPANCY'
                    verified_val = closest
                    delta = d
                    note = f'Source has {check_pcts[:4]}, stored={stored_pct}%'
                    n_discrepancy += 1
                else:
                    # No relevant % found in abstract
                    status = 'UNCERTAIN'
                    note = 'ADA % not found in abstract text'
                    n_uncertain += 1
            
            # Save snippet for report
            source_text_snippet = abstract[:300].replace('\n', ' ').strip()

    elif stype == 'FDA_PI':
        # For FDA PI sources, check URL reachability only (full text too large to parse)
        resp = fetch_url(src_id, timeout=10)
        time.sleep(0.3)
        if resp and len(resp) > 500:
            status = 'URL_LIVE'  # URL live but not deep-parsed
            note = 'FDA PI URL live; deep parse pending'
            n_skipped += 1
        else:
            status = 'UNREACHABLE'
            note = f'FDA PI URL unreachable: {src_id[:60]}'
            n_unreachable += 1

    elif stype == 'URL':
        resp = fetch_url(src_id, timeout=10)
        time.sleep(0.3)
        if resp and len(resp) > 200:
            # Try to extract ADA context from web page
            extracted = extract_pct_values(resp)
            ada_ctx = re.findall(
                r'(?:immunogen|anti.?drug|ADA|antibod).{0,200}?(\d+\.?\d*)\s*%',
                resp, re.IGNORECASE
            )
            ctx_pcts = [float(p) for p in ada_ctx if float(p) <= 100]
            check_pcts = ctx_pcts if ctx_pcts else []

            if stored_pct is not None and check_pcts:
                matched, closest, d = ada_context_match(check_pcts, stored_pct, window=3.0)
                if matched:
                    status = 'VERIFIED'
                    verified_val = closest
                    delta = d
                    n_verified += 1
                else:
                    status = 'DISCREPANCY'
                    verified_val = closest
                    delta = d
                    note = f'Source pcts: {check_pcts[:4]}, stored={stored_pct}%'
                    n_discrepancy += 1
            else:
                status = 'URL_LIVE'
                note = 'URL live; ADA % not extracted from page'
                n_skipped += 1
        else:
            status = 'UNREACHABLE'
            note = f'URL unreachable: {src_id[:60]}'
            n_unreachable += 1

    else:
        status = 'NO_SOURCE'
        note = 'No PMID or verifiable URL'
        n_uncertain += 1

    result = {
        'antibody_name':   name,
        'evidence_tier':   tier,
        'source_type':     stype,
        'source_id':       src_id[:100],
        'stored_ada':      stored_display[:80],
        'stored_pct':      stored_pct,
        'verify_status':   status,
        'source_pct':      verified_val,
        'delta':           delta,
        'extracted_pcts':  str(extracted[:8]),
        'note':            note,
        'source_snippet':  source_text_snippet[:200],
    }
    results.append(result)

    # Progress
    pct_done = 100 * (i+1) // len(rows)
    if (i+1) % 10 == 0 or (i+1) == len(rows):
        print(f"  [{i+1:3d}/{len(rows)}] {name[:30]:30s} | {status}")

# ── Write report ──────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"VERIFICATION SUMMARY")
print(f"{'='*60}")
print(f"  VERIFIED:       {n_verified:3d}")
print(f"  DISCREPANCY:    {n_discrepancy:3d}  ← requires review")
print(f"  UNCERTAIN:      {n_uncertain:3d}  ← mark as uncertain online")
print(f"  URL_LIVE/Skip:  {n_skipped:3d}  ← URL live, not deep-parsed")
print(f"  UNREACHABLE:    {n_unreachable:3d}  ← source no longer accessible")
print(f"  TOTAL:          {len(results):3d}")
print(f"{'='*60}")

fields = list(results[0].keys())
with open(REPORT_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(results)
print(f"\nReport written → {REPORT_OUT}")

# Show discrepancies for immediate review
disc = [r for r in results if r['verify_status'] == 'DISCREPANCY']
if disc:
    print(f"\n{'='*60}")
    print(f"DISCREPANCIES REQUIRING REVIEW ({len(disc)} records):")
    print(f"{'='*60}")
    for r in disc:
        print(f"  {r['antibody_name'][:35]:35s} stored={r['stored_pct']}% | source={r['source_pct']}% | Δ={r['delta']}%")
        print(f"    note: {r['note']}")
        print(f"    src:  {r['source_id'][:80]}")
        print()
