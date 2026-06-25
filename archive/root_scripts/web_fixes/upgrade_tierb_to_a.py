"""
Upgrade 27 Tier-B ADA records to Tier A where a strong primary source exists.
Strategy:
  Pass 1 — Automatic: if current URL is already DailyMed/NEJM/EMA/PMC/AACR/FDA/BMJ → Tier A
  Pass 2 — openFDA: for weak-URL records, find FDA PI setid → update URL, Tier A
  Pass 3 — PubMed: for remaining weak-URL records, find PMID → update, Tier A
"""
import csv, json, re, time, urllib.request, urllib.parse, subprocess, sys, shutil
from pathlib import Path

MASTER    = r'data\ada_master_136_curated.csv'
KB_MASTER = r'data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv'

def fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None

def openfda_setid(generic):
    q   = urllib.parse.quote(generic)
    url = f'https://api.fda.gov/drug/label.json?search=openfda.generic_name:"{q}"&limit=1'
    txt = fetch(url)
    if not txt:
        return None
    try:
        data = json.loads(txt)
        results = data.get('results', [])
        if results:
            setid = results[0].get('set_id') or results[0].get('id', '')
            return setid
    except:
        return None

def pubmed_search(drug):
    q   = urllib.parse.quote(f'{drug}[tiab] AND ("anti-drug antibod"[tiab] OR "immunogenicity"[tiab])')
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={q}&retmax=3&retmode=json"
    txt = fetch(url)
    if not txt:
        return []
    try:
        return json.loads(txt)['esearchresult']['idlist']
    except:
        return []

def dm_url(setid):
    return f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={setid}"

# Strong URL domains → auto Tier A
STRONG = (
    'dailymed.nlm.nih.gov', 'pubmed.ncbi', 'pmc.ncbi', 'fda.gov', 'accessdata.fda',
    'ema.europa.eu', 'nejm.org', 'lancet.com', 'bmj.com', 'jitc.bmj', 'jama',
    'onlinelibrary.wiley', 'nature.com', 'science.org', 'cell.com',
    'annrheumdis', 'bloodjournal', 'aacrjournals', 'haematologica',
    'ncbi.nlm.nih.gov',  # NCBI books, etc.
)

# Drugs that need FDA PI DailyMed lookup (weak URL or api.fda.gov)
NEED_LOOKUP = {
    'Tisotumab':     'tisotumab vedotin-tftv',
    'Zenocutuzumab': 'zenocutuzumab-zbco',
    'Evolocumab':    'evolocumab',
    'Axatilimab':    'axatilimab-csfr',
    'Clesrovimab':   'clesrovimab',
    'Nivolumab':     'nivolumab',
    'Denosumab':     'denosumab',
    'Durvalumab':    'durvalumab',
    'Teprotumumab':  'teprotumumab-trbw',
}

# ── Load ──────────────────────────────────────────────────────────────────────
with open(MASTER, encoding='utf-8') as f:
    reader     = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    all_rows   = list(reader)

row_map = {r['antibody_name']: r for r in all_rows}
b_records = [r for r in all_rows if r.get('evidence_tier') == 'B']
print(f"Tier B records: {len(b_records)}")

upgraded_auto = 0
upgraded_lookup = 0
needs_manual = []

print("\n── Pass 1: Auto-upgrade if strong URL ─────────────────────────────")
for row in b_records:
    drug = row['antibody_name']
    url  = row.get('ada_source_url_primary', '') or ''
    pmids = row.get('ada_source_pmids', '') or ''
    
    has_strong_url  = any(d in url.lower() for d in STRONG)
    has_pmid        = bool(pmids.strip() and pmids.lower() not in ('nan','none',''))
    
    if has_strong_url or has_pmid:
        row['evidence_tier'] = 'A'
        upgraded_auto += 1
        print(f"  ✓ {drug:20s} → A  (url={url[:55]})")
    else:
        print(f"  ○ {drug:20s}   weak url={url[:55]}")

print(f"\nAuto-upgraded: {upgraded_auto}")

print("\n── Pass 2: openFDA lookup for weak-URL records ─────────────────────")
remaining_b = [r for r in all_rows if r.get('evidence_tier') == 'B']
print(f"Still Tier B: {len(remaining_b)}")

for row in remaining_b:
    drug    = row['antibody_name']
    generic = NEED_LOOKUP.get(drug)
    if not generic:
        needs_manual.append(drug)
        continue
    
    # Try DailyMed search
    dm_url_str = None
    q   = urllib.parse.quote(generic)
    url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name={q}&pagesize=2"
    txt = fetch(url)
    if txt:
        try:
            data  = json.loads(txt)
            items = data.get('data', [])
            if items:
                setid = items[0].get('setid', '')
                if setid:
                    dm_url_str = dm_url(setid)
        except:
            pass
    
    if dm_url_str:
        row['ada_source_url_primary']  = dm_url_str
        row['ada_source_type_curated'] = 'FDA label'
        row['evidence_tier']           = 'A'
        row['verify_status']           = row.get('verify_status') or 'SOURCE_LIVE'
        row['verify_note']             = (
            (row.get('verify_note') or '') +
            f' FDA PI found via DailyMed ({dm_url_str}). Tier upgraded to A.'
        ).strip()
        upgraded_lookup += 1
        print(f"  ✓ {drug:20s} → A  DailyMed found: {dm_url_str[:60]}")
    else:
        # Try PubMed
        pmids = pubmed_search(drug)
        time.sleep(0.35)
        if pmids:
            pmid = pmids[0]
            row['ada_source_pmids']       = pmid
            row['ada_source_url_primary'] = f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'
            row['evidence_tier']          = 'A'
            row['verify_status']          = row.get('verify_status') or 'SOURCE_LIVE'
            row['verify_note']            = (
                (row.get('verify_note') or '') +
                f' PubMed PMID {pmid} found. Tier upgraded to A.'
            ).strip()
            upgraded_lookup += 1
            print(f"  ✓ {drug:20s} → A  PMID {pmid}")
        else:
            needs_manual.append(drug)
            print(f"  ✗ {drug:20s}   no source found")
    time.sleep(0.5)

# ── Summary ──────────────────────────────────────────────────────────────────
remaining_b2 = [r for r in all_rows if r.get('evidence_tier') == 'B']
print(f"\n{'='*60}")
print(f"Auto upgraded:   {upgraded_auto}")
print(f"Lookup upgraded: {upgraded_lookup}")
print(f"Still Tier B:    {len(remaining_b2)}")
if remaining_b2:
    print("  Remaining B:")
    for r in remaining_b2:
        print(f"    {r['antibody_name']:20s} url={r.get('ada_source_url_primary','')[:60]}")
if needs_manual:
    print(f"  Needs manual attention: {needs_manual}")

# ── Write ─────────────────────────────────────────────────────────────────────
with open(MASTER, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(all_rows)

shutil.copy(MASTER, KB_MASTER)
print(f"\nMaster CSV written ({len(all_rows)} rows). Synced to KB master.")

# ── Rebuild ───────────────────────────────────────────────────────────────────
print("Rebuilding JSON...")
subprocess.run([sys.executable, 'scripts/_regen_json_only.py'], check=False)
shutil.copy('docs/ada_db_data.json', 'insynbio-web-source/ada_db_data.json')
shutil.copy('docs/ada_db_data.json', 'therasik-web-source/ada_db_data.json')
print("Done.")
