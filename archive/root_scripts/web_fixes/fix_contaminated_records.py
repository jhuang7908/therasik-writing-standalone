"""
Fix two AI-contaminated ADA records:
1. Olokizumab  stored=10-15% (AI-generated) → correct to 3.2%/7.0% per PMID 36109142
2. Relatlimab  stored=<2%   (AI-generated) → verify via DailyMed

Olokizumab evidence:
  PMID 36109142, Ann Rheum Dis 2022;81:1661–1668 (Phase III, TNFi-IR, n=197 randomized)
  OKZ 64mg Q2W + MTX: 7.0% ADA
  OKZ 64mg Q4W + MTX: 3.2% ADA
  No difference in clinical response or safety in ADA+ vs ADA- patients
  (PMC9664111 full text confirms this)
"""
import re, time, urllib.request, json, csv

def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'InSynBio-Verify/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        return f"ERROR: {e}"

ADA_CTX = re.compile(
    r'anti[\-\s]?drug\s*antibod|immunogenicit|\bADA\b|treatment[\-\s]?emerg|'
    r'immunogenic|neutraliz|anti[\-\s]?antibod',
    re.IGNORECASE
)

# ─── Verify Relatlimab via DailyMed ─────────────────────────────────────────
print("=" * 65)
print("RELATLIMAB — DailyMed verification")
print("=" * 65)
# Relatlimab is approved as Opdualag (relatlimab + nivolumab)
# DailyMed setid from URL: b22c9d83-3256-4e17-85f7...
dm_url = 'https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/b22c9d83-3256-4e17-85f7-5f6f9b7c7b1a.xml'
dm_txt = fetch(dm_url, timeout=15)
time.sleep(0.5)

# Try search instead
dm_search = fetch('https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name=relatlimab&pagesize=3')
time.sleep(0.5)
try:
    dm = json.loads(dm_search)
    spls = dm.get('data', [])
    print(f"DailyMed entries for relatlimab: {len(spls)}")
    for spl in spls:
        print(f"  setid={spl.get('setid','')} title={spl.get('title','')[:70]}")
        setid = spl.get('setid', '')
        if setid:
            xml = fetch(f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml", timeout=12)
            time.sleep(0.5)
            if xml and not xml.startswith('ERROR') and len(xml) > 100:
                sents = re.split(r'(?<=[.!?])\s+', xml)
                ada_sents = [s for s in sents if ADA_CTX.search(s) and 10 < len(s) < 500][:8]
                pcts = []
                for s in ada_sents:
                    found = re.findall(r'(\d+\.?\d*)\s*%', s)
                    pcts.extend([float(p) for p in found if 0 < float(p) <= 100])
                print(f"  ADA pcts: {sorted(set(pcts))}")
                for s in ada_sents[:5]:
                    clean = re.sub(r'<[^>]+>', ' ', s)
                    clean = re.sub(r'\s+', ' ', clean).strip()
                    if len(clean) > 20:
                        print(f"    → {clean[:220]}")
                
                if pcts:
                    print(f"\n  ✓ Relatlimab DailyMed confirms ADA rates: {sorted(set(pcts))}")
            else:
                print(f"  XML fetch failed: {str(xml)[:60]}")
except Exception as e:
    print(f"Error: {e}")
    print(f"Raw: {dm_search[:200]}")

# ─── Apply corrections to master CSV ─────────────────────────────────────────
print()
print("=" * 65)
print("APPLYING CORRECTIONS TO MASTER CSV + JSON")
print("=" * 65)

MASTER_CSV = r'data\ada_master_136_curated.csv'
rows = list(csv.DictReader(open(MASTER_CSV, encoding='utf-8')))
fieldnames = list(rows[0].keys())

corrections_applied = []

for row in rows:
    name = row.get('antibody_name', '')
    
    if 'olokizumab' in name.lower():
        # Correct value based on PMID 36109142 Phase III trial
        old_val = row.get('ada_value_display', '')
        row['ada_value_display'] = '3.2% (Q4W) / 7.0% (Q2W)'
        row['ada_first_pct'] = '7.0'  # use higher of the two regimens
        row['evidence_tier'] = 'A'  # PMID-anchored Phase III trial
        row['ada_source_pmids'] = '36109142'
        row['ada_source_url_primary'] = 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9664111/'
        # Replace AI-generated chain with factual note
        row['ada_evidence_chain_excerpt'] = (
            "Olokizumab Phase III trial (PMID 36109142, Ann Rheum Dis 2022;81:1661–1668, "
            "Feist et al., n=197 randomized, TNFi-inadequate responders). "
            "OKZ 64mg Q2W + MTX: 7.0% treatment-emergent ADA. "
            "OKZ 64mg Q4W + MTX: 3.2% treatment-emergent ADA. "
            "No difference in clinical response or safety outcomes between ADA+ and ADA- patients. "
            "CORRECTION: Previous stored value '10-15%' was from an AI-generated summary with no "
            "primary source citation. Corrected to Phase III trial data."
        )
        corrections_applied.append(f"Olokizumab: {old_val} → 3.2% (Q4W) / 7.0% (Q2W) [Tier B→A, PMID 36109142]")
        print(f"  ✓ Olokizumab corrected: {old_val} → 3.2% (Q4W) / 7.0% (Q2W)")

# Write corrected CSV
with open(MASTER_CSV, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)
print(f"\n  Master CSV updated.")

# ─── Rebuild JSON (re-run enrich script logic) ────────────────────────────────
import subprocess, sys
print("\nRebuilding ada_db_data.json...")
result = subprocess.run([sys.executable, 'apply_verification_to_master.py'], 
                        capture_output=True, text=True, cwd='.')
print(result.stdout[-600:] if result.stdout else '')
if result.returncode != 0:
    print("ERROR:", result.stderr[-200:])

print("\nCorrections applied:")
for c in corrections_applied:
    print(f"  {c}")
