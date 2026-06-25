"""
Use openFDA drug label API to get structured immunogenicity sections.
Endpoint: https://api.fda.gov/drug/label.json?search=openfda.brand_name:<brand>&limit=1
Section field: clinical_pharmacology (section 12.6 usually)
or immunogenicity (sometimes standalone field)
"""
import urllib.request, urllib.parse, json, re, time, csv

DRUGS = [
    ("Risankizumab",  "risankizumab"),
    ("Belimumab",     "belimumab"),
    ("Daratumumab",   "daratumumab"),
    ("Dupilumab",     "dupilumab"),
    ("Ebronucimab",   "ebronucimab"),
    ("Ramucirumab",   "ramucirumab"),
    ("Secukinumab",   "secukinumab"),
    ("Tremelimumab",  "tremelimumab"),
    ("Eculizumab",    "eculizumab"),
    ("Mogamulizumab", "mogamulizumab"),
    ("Obinutuzumab",  "obinutuzumab"),
    ("Ocrelizumab",   "ocrelizumab"),
    ("Palivizumab",   "palivizumab"),
    ("Pertuzumab",    "pertuzumab"),
]

MASTER = r'data\ada_master_136_curated.csv'
rows   = {r['antibody_name']: r for r in csv.DictReader(open(MASTER, encoding='utf-8'))}

DAILYMED_SETIDS = {
    "Risankizumab":  "7148c8eb-b39e-e20a-6494-a6df82392858",
    "Belimumab":     "2fa3c528-1777-4628-8a55-a69dae2381a3",
    "Daratumumab":   "4bb241af-4299-4373-8762-2d6709515db0",
    "Dupilumab":     "595f437d-2729-40bb-9c62-c8ece1f82780",
    "Ramucirumab":   "c6080942-dee6-423e-b688-1272c2ae90d4",
    "Secukinumab":   "77c4b13e-7df3-42d4-81db-3d0cddb7f67a",
    "Tremelimumab":  "6690679c-be2f-4588-a2e4-89fff74dd6be",
    "Eculizumab":    "ebcd67fa-b4d1-4a22-b33d-ee8bf6b9c722",
    "Mogamulizumab": "e53960ab-42a1-40d1-9c7d-eb013fe7f18f",
    "Obinutuzumab":  "df12ceb2-5b4b-4ab5-a317-2a36bf2a3cda",
    "Ocrelizumab":   "9da42362-3bb5-4b83-b4bb-b59fd4e55f0d",
    "Palivizumab":   "3a0096c7-8139-44cd-bba4-520ab05c2cb2",
    "Pertuzumab":    "17f85d17-ab71-4f5b-9fe3-0b8c822f69ff",
}

def fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None, str(e)

def openfda_label(generic_name):
    q   = urllib.parse.quote(generic_name)
    url = f'https://api.fda.gov/drug/label.json?search=openfda.generic_name:"{q}"&limit=1'
    txt = fetch(url)
    if not txt or isinstance(txt, tuple):
        return None
    try:
        return json.loads(txt)
    except:
        return None

def get_immuno_section(label_data):
    """Extract immunogenicity text from openFDA label result."""
    if not label_data:
        return None
    results = label_data.get('results', [])
    if not results:
        return None
    r = results[0]
    
    # Check known section fields
    for field in ['immunogenicity', 'immunogenicity_table',
                  'clinical_pharmacology', 'clinical_studies',
                  'adverse_reactions']:
        val = r.get(field)
        if val:
            text = ' '.join(val) if isinstance(val, list) else str(val)
            # Check if this section contains immunogenicity info
            if re.search(r'immun|ADA|anti.drug', text, re.IGNORECASE):
                # Find the relevant chunk
                idx = text.lower().find('immun')
                if idx >= 0:
                    return text[max(0,idx-50):idx+1500]
    return None

def extract_pct_ada(text):
    found = []
    patterns = [
        r'(\d+\.?\d*)\s*%\s*\((\d+)/(\d+)',
        r'(\d+)/(\d+)\s+(?:patients?|subjects?)[^%]{0,80}(\d+\.?\d*)\s*%',
        r'(\d+\.?\d*)\s*%\s+(?:of\s+)?(?:patients?|subjects?)',
        r'incidence[^%]{0,100}?(\d+\.?\d*)\s*%',
        r'(\d+\.?\d*)\s*%',
    ]
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            v = m.group(0).strip()[:80]
            if v not in found:
                found.append(v)
        if len(found) >= 5:
            break
    return found[:5]

def compare_stored(stored_val, found_pcts):
    stored_nums = [float(n) for n in re.findall(r'(\d+\.?\d*)', 
                   stored_val.replace('<','').replace('>','').replace('~','').replace('≤',''))][:3]
    if not stored_nums or not found_pcts:
        return None
    for pct_str in found_pcts:
        nums = re.findall(r'(\d+\.?\d*)', pct_str)
        for n in nums:
            n_f = float(n)
            if n_f > 70:  # skip year-like numbers
                continue
            for s_f in stored_nums:
                if abs(n_f - s_f) <= 2.0:
                    return 'MATCH', n_f, s_f
    return 'MISMATCH', stored_nums, [re.findall(r'(\d+\.?\d*)', p)[:1] for p in found_pcts[:3]]

# ─────────────────────────────────────────────────────────────────────────────
print(f"{'='*72}")
print("openFDA Drug Label Verification — 14 High-Risk Records")
print(f"{'='*72}\n")

corrections = {}
results = []

for drug, generic in DRUGS:
    stored     = rows.get(drug, {})
    stored_val = stored.get('ada_value_display', '?')
    setid      = DAILYMED_SETIDS.get(drug, '')
    dm_url     = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={setid}" if setid else ''
    
    print(f"{'─'*60}")
    print(f"▶ {drug}  stored: {stored_val[:55]}")
    
    result = {'drug': drug, 'stored_val': stored_val, 'verdict': 'PENDING',
              'immuno_text': '', 'found_pcts': [], 'action': '', 'dm_url': dm_url}
    
    label = openfda_label(generic)
    sec   = get_immuno_section(label)
    
    if sec:
        pcts = extract_pct_ada(sec)
        result['immuno_text'] = sec[:400]
        result['found_pcts']  = pcts
        print(f"  Section found ({len(sec)} chars):")
        print(f"  {sec[:280]}")
        print(f"  Pcts found: {pcts[:5]}")
        
        cmp = compare_stored(stored_val, pcts)
        if cmp and cmp[0] == 'MATCH':
            result['verdict'] = 'CONFIRMED'
            result['action']  = f'FDA PI confirms. DailyMed URL added. Tier→A'
            corrections[drug] = {
                'ada_source_url_primary': dm_url,
                'evidence_tier': 'A',
                'verify_status': 'VERIFIED',
                'verify_note': f'FDA PI (openFDA/DailyMed) confirms stored value. '
                               f'Found: {pcts[0] if pcts else ""}',
            }
            print(f"  ✓ CONFIRMED — stored value matches FDA PI")
        elif cmp and cmp[0] == 'MISMATCH':
            result['verdict'] = 'DISCREPANCY'
            result['action']  = f'Stored={cmp[1]} vs PI found pcts={cmp[2]}'
            print(f"  ⚠ DISCREPANCY — stored={cmp[1]}, PI found={cmp[2]}")
        else:
            # Section found but no parseable % — still a source upgrade
            result['verdict'] = 'SOURCE_UPGRADED'
            result['action']  = 'Immuno section found, no clear %; URL upgraded to DailyMed'
            corrections[drug] = {
                'ada_source_url_primary': dm_url,
                'verify_status': 'SOURCE_LIVE',
                'verify_note': f'FDA PI section found via openFDA; pcts not auto-extracted',
            }
            print(f"  ○ Section found but % not extracted")
    else:
        print(f"  openFDA: no immunogenicity section found")
        # Still upgrade URL to DailyMed if setid known
        if setid:
            result['verdict'] = 'URL_UPGRADED'
            result['action']  = 'No immuno section via openFDA; DailyMed URL still added'
            corrections[drug] = {
                'ada_source_url_primary': dm_url,
                'verify_status': 'SOURCE_LIVE',
                'verify_note': f'DailyMed label available (setid={setid}); immuno section not in structured API',
            }
        else:
            result['verdict'] = 'NO_SOURCE'
    
    print(f"  ✦ {result['verdict']} → {result['action'][:80]}")
    results.append(result)
    time.sleep(0.6)

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*72}")
print("FINAL SUMMARY")
print(f"{'='*72}")
for v in sorted(set(r['verdict'] for r in results)):
    n = sum(1 for r in results if r['verdict'] == v)
    print(f"  {v}: {n}")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\nApplying {len(corrections)} corrections to master CSV...")
with open(MASTER, encoding='utf-8') as f:
    all_rows  = list(csv.DictReader(f))
    fieldnames = list(all_rows[0].keys()) if all_rows else []

changed = 0
for row in all_rows:
    drug = row['antibody_name']
    if drug in corrections:
        for k, v in corrections[drug].items():
            if k in row:
                row[k] = v
        changed += 1

with open(MASTER, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)
print(f"Updated {changed} rows.")

# ─────────────────────────────────────────────────────────────────────────────
print("\nRebuilding ada_db_data.json...")
import subprocess, sys
subprocess.run([sys.executable, 'scripts/_regen_json_only.py'], check=False)
print("Complete.")
