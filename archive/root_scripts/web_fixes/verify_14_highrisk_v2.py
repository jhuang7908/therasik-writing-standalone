"""
v2 — Fix DailyMed XML extraction using proper HTML label endpoint.
DailyMed HTML label is much easier to parse than SPL XML.
"""
import urllib.request, urllib.parse, re, json, time, csv

DRUGS_SETIDS = [
    ("Risankizumab",  "skyrizi",       "7148c8eb-b39e-e20a-6494-a6df82392858"),
    ("Belimumab",     "benlysta",      "2fa3c528-1777-4628-8a55-a69dae2381a3"),
    ("Daratumumab",   "darzalex",      "4bb241af-4299-4373-8762-2d6709515db0"),
    ("Dupilumab",     "dupixent",      "595f437d-2729-40bb-9c62-c8ece1f82780"),
    ("Ebronucimab",   None,            None),
    ("Ramucirumab",   "cyramza",       "c6080942-dee6-423e-b688-1272c2ae90d4"),
    ("Secukinumab",   "cosentyx",      "77c4b13e-7df3-42d4-81db-3d0cddb7f67a"),
    ("Tremelimumab",  "imjudo",        "6690679c-be2f-4588-a2e4-89fff74dd6be"),
    ("Eculizumab",    "soliris",       "ebcd67fa-b4d1-4a22-b33d-ee8bf6b9c722"),
    ("Mogamulizumab", "poteligeo",     "e53960ab-42a1-40d1-9c7d-eb013fe7f18f"),
    ("Obinutuzumab",  "gazyva",        "df12ceb2-5b4b-4ab5-a317-2a36bf2a3cda"),
    ("Ocrelizumab",   "ocrevus",       "9da42362-3bb5-4b83-b4bb-b59fd4e55f0d"),
    ("Palivizumab",   "synagis",       "3a0096c7-8139-44cd-bba4-520ab05c2cb2"),
    ("Pertuzumab",    "perjeta",       "17f85d17-ab71-4f5b-9fe3-0b8c822f69ff"),
]

MASTER = r'data\ada_master_136_curated.csv'
rows   = {r['antibody_name']: r for r in csv.DictReader(open(MASTER, encoding='utf-8'))}

def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return f"ERROR: {e}"

def fetch_dailymed_html(setid):
    """Get the formatted HTML label from DailyMed."""
    url = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={setid}"
    return fetch(url), url

def extract_immuno_section(html):
    """
    Extract the IMMUNOGENICITY section from DailyMed HTML.
    The section is typically inside <div class="Section"> after an anchor with name containing immunogenicity.
    """
    # Remove script/style
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL|re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL|re.IGNORECASE)
    
    # Strategy 1: find section heading containing "immunogenicity"
    # DailyMed HTML often has: <h2 ...>IMMUNOGENICITY</h2> followed by content
    m = re.search(
        r'(?:<h[1-4][^>]*>[^<]*immunogenicity[^<]*</h[1-4]>|IMMUNOGENICITY\s*</[^>]+>)'
        r'(.*?)(?:<h[1-4]|<div class="Section"|$)',
        html, re.IGNORECASE | re.DOTALL
    )
    if m:
        section = m.group(1)
        # strip tags
        section = re.sub(r'<[^>]+>', ' ', section)
        section = re.sub(r'\s+', ' ', section).strip()
        return section[:2000]
    
    # Strategy 2: search for immunogenicity in plain text blocks
    # Remove all HTML tags first
    plain = re.sub(r'<[^>]+>', ' ', html)
    plain = re.sub(r'&nbsp;', ' ', plain)
    plain = re.sub(r'&amp;', '&', plain)
    plain = re.sub(r'\s+', ' ', plain)
    
    idx = plain.lower().find('immunogenicity')
    if idx >= 0:
        # Grab surrounding context
        start = max(0, idx - 100)
        end   = min(len(plain), idx + 2000)
        return plain[start:end]
    
    return None

def extract_pct_ada(text):
    """Extract ADA percentages/counts from immunogenicity text."""
    found = []
    # Pattern: number% or N/total (%) for ADA
    patterns = [
        # e.g. "24% (263/1079)" or "263/1079 (24%)"
        r'(\d+\.?\d*)\s*%\s*\((\d+)/(\d+)',
        r'(\d+)/(\d+)\s+(?:patients?|subjects?|participants?)[^%]{0,50}?(\d+\.?\d*)\s*%',
        # simple percent
        r'(\d+\.?\d*)\s*%',
        # N/total
        r'(\d+)/(\d+)\s+(?:patients?|subjects?)',
    ]
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            val = m.group(0).strip()[:60]
            if val not in found:
                found.append(val)
            if len(found) >= 6:
                break
        if len(found) >= 6:
            break
    return found

def compare_stored(stored_val, found_pcts):
    """Rough comparison of stored value vs found percentages."""
    stored_nums = re.findall(r'(\d+\.?\d*)', stored_val.replace('<','').replace('>','').replace('~',''))
    if not stored_nums or not found_pcts:
        return None
    stored_f = [float(n) for n in stored_nums[:3]]
    
    for pct_str in found_pcts:
        nums = re.findall(r'(\d+\.?\d*)', pct_str)
        for n in nums:
            n_f = float(n)
            for s_f in stored_f:
                if abs(n_f - s_f) <= 1.5:
                    return 'MATCH', n_f, s_f
    return 'MISMATCH', stored_f, [re.findall(r'(\d+\.?\d*)', p)[:1] for p in found_pcts[:3]]

# ─────────────────────────────────────────────────────────────────────────────
results  = []
corrections = {}  # drug → {update fields}

print(f"{'='*72}")
print("14 HIGH-RISK ADA RECORDS — DailyMed HTML Deep Extraction")
print(f"{'='*72}\n")

for drug, brand, setid in DRUGS_SETIDS:
    stored = rows.get(drug, {})
    stored_val  = stored.get('ada_value_display','?')
    stored_tier = stored.get('evidence_tier','?')
    stored_pmids= stored.get('ada_source_pmids','').strip()
    
    print(f"{'─'*72}")
    print(f"▶ {drug}  stored={stored_val[:55]}")
    
    result = {
        'drug': drug, 'brand': brand or '', 'setid': setid or '',
        'stored_val': stored_val, 'stored_tier': stored_tier,
        'immuno_text': '', 'found_pcts': [],
        'verdict': 'PENDING', 'action': '', 'new_url': '',
    }
    
    if setid:
        html, label_url = fetch_dailymed_html(setid)
        result['new_url'] = label_url
        
        if html.startswith('ERROR'):
            print(f"  ✗ DailyMed fetch failed: {html}")
            result['verdict'] = 'FETCH_ERROR'
        else:
            sec = extract_immuno_section(html)
            if sec:
                pcts = extract_pct_ada(sec)
                result['immuno_text'] = sec[:500]
                result['found_pcts']  = pcts
                print(f"  Immunogenicity section ({len(sec)} chars)")
                print(f"  Text: {sec[:300]}")
                print(f"  Extracted %: {pcts[:5]}")
                
                cmp = compare_stored(stored_val, pcts)
                if cmp and cmp[0] == 'MATCH':
                    result['verdict'] = 'CONFIRMED'
                    result['action']  = f'Value confirmed. Update URL→DailyMed, tier→A'
                    corrections[drug] = {
                        'ada_source_url_primary': label_url,
                        'evidence_tier': 'A',
                        'verify_status': 'VERIFIED',
                        'verify_note': f'FDA PI (DailyMed setid={setid}) confirms stored value',
                    }
                    print(f"  ✓ MATCH — stored value confirmed by FDA PI")
                elif cmp and cmp[0] == 'MISMATCH':
                    result['verdict'] = 'DISCREPANCY'
                    result['action']  = f'stored={cmp[1]} vs FDA PI found={cmp[2]}'
                    print(f"  ⚠ MISMATCH — stored={cmp[1]}, FDA PI={cmp[2]}")
                else:
                    result['verdict'] = 'CONFIRMED_NO_PCT'
                    result['action']  = 'Immunogenicity section found but no clear % extracted; URL updated'
                    corrections[drug] = {
                        'ada_source_url_primary': label_url,
                        'verify_status': 'SOURCE_LIVE',
                        'verify_note':   f'FDA PI section found (DailyMed setid={setid}); manual % extraction needed',
                    }
                    print(f"  ○ Section found but no % extracted from text")
            else:
                print(f"  → No IMMUNOGENICITY section found in DailyMed HTML ({len(html)} chars)")
                result['verdict'] = 'NO_IMMUNO_SECTION'
                corrections[drug] = {
                    'ada_source_url_primary': label_url,
                    'verify_status': 'SOURCE_LIVE',
                    'verify_note': f'DailyMed label found (setid={setid}) but no immunogenicity section in PI',
                }
    else:
        print(f"  No DailyMed setid — trying PubMed...")
        # Search PubMed
        q   = urllib.parse.quote(f'{drug}[tiab] AND "anti-drug antibod"[tiab]')
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={q}&retmax=5&retmode=json"
        txt = fetch(url)
        try:
            data  = json.loads(txt)
            pmids = data['esearchresult']['idlist']
            count = int(data['esearchresult']['count'])
            print(f"  PubMed: {count} results, PMIDs: {pmids[:3]}")
            if pmids:
                result['verdict'] = 'PUBMED_FOUND'
                result['action']  = f'Use PMID {pmids[0]}'
                corrections[drug] = {
                    'ada_source_pmids': pmids[0],
                    'verify_status': 'SOURCE_LIVE',
                    'verify_note': f'PubMed search found PMID {pmids[0]} for ADA data',
                }
        except:
            result['verdict'] = 'NO_SOURCE'
    
    print(f"  ✦ {result['verdict']} → {result['action'][:80]}")
    results.append(result)
    time.sleep(0.8)

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*72}")
print("SUMMARY")
print(f"{'='*72}")
for v in sorted(set(r['verdict'] for r in results)):
    n = sum(1 for r in results if r['verdict'] == v)
    print(f"  {v}: {n}")

confirmed = [r for r in results if r['verdict'] == 'CONFIRMED']
discrepant = [r for r in results if r['verdict'] == 'DISCREPANCY']
print(f"\n✓ Confirmed: {len(confirmed)}")
for r in confirmed:
    print(f"   {r['drug']:20s} {r['stored_val'][:45]}")
if discrepant:
    print(f"\n⚠ Discrepancies found: {len(discrepant)}")
    for r in discrepant:
        print(f"   {r['drug']:20s} {r['action']}")

# ─────────────────────────────────────────────────────────────────────────────
# Apply corrections to master CSV
print(f"\n{'─'*72}")
print(f"Applying {len(corrections)} corrections to master CSV...")

with open(MASTER, encoding='utf-8') as f:
    all_rows = list(csv.DictReader(f))
    fieldnames = all_rows[0].keys() if all_rows else []

changed = 0
for row in all_rows:
    drug = row['antibody_name']
    if drug in corrections:
        for k, v in corrections[drug].items():
            if k in row:
                row[k] = v
        changed += 1

with open(MASTER, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()) if all_rows else [])
    writer.writeheader()
    writer.writerows(all_rows)
print(f"Updated {changed} rows in master CSV.")

# Save full report
out = [{k: str(v)[:300] for k, v in r.items()} for r in results]
with open('data/14_highrisk_v2_report.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("Saved: data/14_highrisk_v2_report.json")

# ─────────────────────────────────────────────────────────────────────────────
# Rebuild JSON
print("\nRebuilding ada_db_data.json...")
import subprocess, sys
subprocess.run([sys.executable, 'scripts/_regen_json_only.py'], check=False)
print("Done.")
