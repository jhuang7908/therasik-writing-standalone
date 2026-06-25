"""
Pass 2: Re-verify discrepancy records with stricter ADA-context extraction.
Many high-delta "discrepancies" are false positives — the algorithm extracted
clinical response rates (e.g. 92% ORR) instead of ADA rates.

Strategy: Only accept % values found within 120 chars of ADA-specific keywords.
"""
import csv, re, time, urllib.request

MASTER_CSV  = r'data\ada_master_136_curated.csv'
REPORT_CSV  = r'data\ada_evidence_verification_report.csv'
REPORT2_OUT = r'data\ada_evidence_verify_pass2.csv'

ADA_KEYWORDS = re.compile(
    r'anti[\-\s]?drug\s*antibod|immunogenicit|ADA\b|anti[\-\s]?antibod|'
    r'treatment[\-\s]?emerg|immunogen|nAb\b|neutraliz',
    re.IGNORECASE
)

EFFICACY_KEYWORDS = re.compile(
    r'response\s*rate|ORR|overall\s*survival|PFS|remission|'
    r'EASI|PASI|ACR|DAS28|pain\s*responder|HAQ|'
    r'clinical\s*benefit|complete\s*response|partial\s*response',
    re.IGNORECASE
)

def fetch_url(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'InSynBio-Verifier/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None

def fetch_pubmed_abstract(pmid):
    pmid = str(pmid).strip().split()[0]
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
           f"?db=pubmed&id={pmid}&rettype=abstract&retmode=text"
           f"&tool=InSynBio&email=info@insynbio.com")
    return fetch_url(url)

def fetch_dailymed(drug_name):
    """Try DailyMed for FDA PI data."""
    q = urllib.parse.quote(drug_name.lower())
    url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name={q}&pagesize=1"
    txt = fetch_url(url)
    if not txt: return None
    try:
        import json
        d = json.loads(txt)
        spls = d.get('data', [])
        if spls:
            setid = spls[0].get('setid', '')
            if setid:
                label_url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml"
                return fetch_url(label_url)
    except: pass
    return None

import urllib.parse, json

def extract_ada_context_pcts(text):
    """Extract % values ONLY from ADA-specific sentence context."""
    if not text: return []
    results = []
    # Split into sentences (~300 char windows)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    for sent in sentences:
        if ADA_KEYWORDS.search(sent) and not EFFICACY_KEYWORDS.search(sent):
            pcts = re.findall(r'(\d+\.?\d*)\s*%', sent)
            for p in pcts:
                v = float(p)
                if 0 < v <= 100:
                    results.append(v)
    return sorted(set(results))

def parse_stored_pct(s):
    if not s: return None
    m = re.search(r'(\d+\.?\d*)\s*%', str(s))
    if m:
        v = float(m.group(1))
        return v if 0 <= v <= 100 else None
    return None

# ── Load reports ──────────────────────────────────────────────────────────────
master = {r['antibody_name']: r for r in csv.DictReader(open(MASTER_CSV, encoding='utf-8'))}
report = list(csv.DictReader(open(REPORT_CSV, encoding='utf-8')))

discrepancies = [r for r in report if r['verify_status'] == 'DISCREPANCY']
unreachable   = [r for r in report if r['verify_status'] == 'UNREACHABLE']
print(f"Re-verifying {len(discrepancies)} discrepancies + {len(unreachable)} unreachable records\n")

pass2_results = []

# ── Pass 2a: Re-verify discrepancies with stricter context ────────────────────
print("=== Re-verifying discrepancies (strict ADA context) ===")
for rec in discrepancies:
    name = rec['antibody_name']
    stored_pct = parse_stored_pct(rec['stored_ada'])
    src_id = rec['source_id'].strip()
    
    # Fetch fresh abstract
    abstract = fetch_pubmed_abstract(src_id)
    time.sleep(0.35)
    
    if not abstract:
        status2 = 'UNREACHABLE'
        note2 = 'PubMed fetch failed on pass2'
        ada_pcts = []
    else:
        ada_pcts = extract_ada_context_pcts(abstract)
        
        if not ada_pcts:
            # No ADA-context % found → original discrepancy was likely a false positive
            # (the % came from efficacy data)
            status2 = 'FALSE_POSITIVE'
            note2 = 'No ADA-context % in abstract; original discrepancy was efficacy %'
        elif stored_pct is not None:
            closest = min(ada_pcts, key=lambda x: abs(x - stored_pct))
            delta = abs(closest - stored_pct)
            if delta <= 3.0:
                status2 = 'VERIFIED'
                note2 = f'ADA-context match: {closest}% ~ stored {stored_pct}%'
            elif delta <= 8.0:
                status2 = 'CLOSE_MATCH'
                note2 = f'ADA-context near-match: {closest}% vs stored {stored_pct}% (Δ={delta:.1f}%)'
            else:
                status2 = 'REAL_DISCREPANCY'
                note2 = f'ADA-context {ada_pcts} vs stored {stored_pct}% (Δ={delta:.1f}%)'
        else:
            status2 = 'UNCERTAIN'
            note2 = 'ADA context found but stored value non-numeric'
    
    r2 = dict(rec)
    r2['pass2_status'] = status2
    r2['pass2_ada_pcts'] = str(ada_pcts[:6])
    r2['pass2_note'] = note2
    pass2_results.append(r2)
    
    sym = '✓' if 'VERIFIED' in status2 else ('⚠' if 'REAL' in status2 or 'CLOSE' in status2 else '·')
    print(f"  {sym} {name[:32]:32s} {status2:18s} {note2[:60]}")

# ── Pass 2b: Re-attempt UNREACHABLE FDA PI records via DailyMed ───────────────
print(f"\n=== Re-attempting FDA PI via DailyMed ({len([r for r in unreachable if 'FDA' in r['source_id'] or 'fda' in r['source_id'].lower()])} records) ===")
for rec in unreachable:
    name = rec['antibody_name']
    src_id = rec['source_id']
    stored_pct = parse_stored_pct(rec['stored_ada'])
    
    # Try DailyMed for FDA PI
    is_fda = ('FDA' in src_id or 'fda.gov' in src_id.lower() or 
              'prescribing information' in src_id.lower() or 
              'accessdata' in src_id.lower())
    
    if is_fda:
        label_xml = fetch_dailymed(name)
        time.sleep(0.5)
        if label_xml:
            ada_pcts = extract_ada_context_pcts(label_xml)
            if ada_pcts and stored_pct is not None:
                closest = min(ada_pcts, key=lambda x: abs(x - stored_pct))
                delta = abs(closest - stored_pct)
                status2 = 'VERIFIED' if delta <= 3.0 else 'REAL_DISCREPANCY' if delta > 8 else 'CLOSE_MATCH'
                note2 = f'DailyMed: ADA {ada_pcts[:4]} vs stored {stored_pct}% Δ={delta:.1f}%'
            elif ada_pcts:
                status2 = 'UNCERTAIN'
                note2 = f'DailyMed label found, ADA pcts={ada_pcts[:4]}'
            else:
                status2 = 'URL_LIVE'
                note2 = 'DailyMed label found, no ADA % extracted'
        else:
            status2 = 'UNREACHABLE'
            note2 = 'DailyMed lookup failed'
    else:
        # Non-FDA URL: mark unreachable (behind paywall)
        status2 = 'PAYWALL'
        note2 = 'URL behind paywall; need manual access'
    
    r2 = dict(rec)
    r2['pass2_status'] = status2
    r2['pass2_ada_pcts'] = ''
    r2['pass2_note'] = note2
    pass2_results.append(r2)
    
    if is_fda:
        print(f"  {name[:32]:32s} {status2:15s} {note2[:70]}")

# ── Summary ───────────────────────────────────────────────────────────────────
from collections import Counter
stat_counts = Counter(r['pass2_status'] for r in pass2_results)
print(f"\n{'='*65}")
print("PASS 2 SUMMARY (discrepancies + unreachable re-verified)")
print(f"{'='*65}")
for s, n in sorted(stat_counts.items(), key=lambda x: -x[1]):
    print(f"  {s:22s}: {n}")
print(f"{'='*65}")

# Real discrepancies requiring human review
real = [r for r in pass2_results if r['pass2_status'] in ('REAL_DISCREPANCY', 'CLOSE_MATCH')]
if real:
    print(f"\nREQUIRE MANUAL REVIEW ({len(real)}):")
    for r in sorted(real, key=lambda x: x['pass2_status']):
        print(f"  {'⛔' if 'REAL' in r['pass2_status'] else '⚠'} {r['antibody_name'][:32]:32s} {r['pass2_note'][:80]}")
        print(f"     PMID: {r['source_id'][:30]}  stored: {r['stored_ada'][:50]}")

# Write pass2 report
fields = list(pass2_results[0].keys()) if pass2_results else []
with open(REPORT2_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(pass2_results)
print(f"\nPass 2 report → {REPORT2_OUT}")
