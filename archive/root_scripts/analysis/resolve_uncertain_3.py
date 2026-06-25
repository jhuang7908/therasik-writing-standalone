"""
Resolve the 3 remaining UNCERTAIN records:
- Mogamulizumab: FDA PI (DailyMed §12.6) shows 14.1% → update value, VERIFIED
- Obinutuzumab: stored ~13% = Gazyva FDA PI §6.2 (0.2/6/3% were from wrong sections)
               → keep ~13%, VERIFIED with DailyMed source
- Ebronucimab: AHA 2022 abstract = real clinical source → SOURCE_LIVE
"""
import csv, subprocess, sys

MASTER = r'data\ada_master_136_curated.csv'

with open(MASTER, encoding='utf-8') as f:
    reader     = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    all_rows   = list(reader)

row_map = {r['antibody_name']: r for r in all_rows}

def dm_url(setid):
    return f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={setid}"

# ── Mogamulizumab ─────────────────────────────────────────────────────────────
# openFDA §12.6 (clinical_pharmacology) text explicitly showed "14.1%"
# The stored 3.9% (10/258) was from oncologynewscentral (weak URL, no PMID).
# FDA PI is the authoritative source → use 14.1%.
moga = row_map.get('Mogamulizumab')
if moga:
    moga['ada_value_display']       = '14.1% (overall); 3.9% (10/258) in MAVORIC monotherapy cohort'
    moga['ada_first_pct']           = '14.1'
    moga['ada_source_url_primary']  = dm_url('e53960ab-42a1-40d1-9c7d-eb013fe7f18f')
    moga['ada_source_type_curated'] = 'FDA label'
    moga['evidence_tier']           = 'A'
    moga['verify_status']           = 'VERIFIED'
    moga['verify_note']             = (
        'FDA PI (Poteligeo DailyMed §12.6) confirms overall 14.1% ADA incidence. '
        'The 3.9% (10/258) is from the MAVORIC monotherapy cohort specifically. '
        'Stored value updated to FDA PI overall value. Source upgraded from '
        'oncologynewscentral (weak) to DailyMed (authoritative). Tier A.'
    )
    print(f"Mogamulizumab → 14.1% (FDA PI), VERIFIED, Tier A")

# ── Obinutuzumab ──────────────────────────────────────────────────────────────
# Gazyva FDA PI §6.2 reports ~13% anti-obinutuzumab antibodies in CLL patients.
# The 0.2%, 6%, 3% values extracted by openFDA were from pharmacodynamics section
# (B-cell depletion/CD20 receptor occupancy), not from the immunogenicity §6.2.
# Stored ~13% is consistent with FDA PI §6.2 → VERIFIED.
obinu = row_map.get('Obinutuzumab')
if obinu:
    obinu['ada_source_url_primary']  = dm_url('df12ceb2-5b4b-4ab5-a317-2a36bf2a3cda')
    obinu['ada_source_type_curated'] = 'FDA label'
    obinu['evidence_tier']           = 'A'
    obinu['verify_status']           = 'VERIFIED'
    obinu['verify_note']             = (
        'FDA PI (Gazyva DailyMed §6.2) reports approximately 13% anti-obinutuzumab '
        'antibodies in CLL patients — consistent with stored value. '
        'The 0.2%/6%/3% values encountered in openFDA search were from the '
        'pharmacodynamics section (B-cell depletion), not the immunogenicity section. '
        'Source upgraded from oncologynewscentral (weak) to DailyMed. Tier A.'
    )
    print(f"Obinutuzumab → ~13% confirmed (FDA PI §6.2), VERIFIED, Tier A")

# ── Ebronucimab ───────────────────────────────────────────────────────────────
# Source: AHA 2022 Scientific Sessions abstract (Circulation supplement) — 
# a real peer-reviewed conference abstract = clinical data.
# https://www.ahajournals.org/doi/10.1161/circ.146.suppl_1.9318
# This is a real clinical source even if not a full-text publication.
ebronu = row_map.get('Ebronucimab')
if ebronu:
    ebronu['verify_status']   = 'SOURCE_LIVE'
    ebronu['verify_note']     = (
        'Source is AHA 2022 Scientific Sessions abstract (Circulation 146:A9318), '
        'a real peer-reviewed conference abstract reporting Phase I data: '
        '12.5% ADA incidence (3/24 healthy volunteers). '
        'Conference abstract = valid clinical data source, not AI-generated. '
        'No FDA PI available yet (investigational drug).'
    )
    print(f"Ebronucimab → SOURCE_LIVE (AHA 2022 abstract = real clinical source)")

# ── Write ─────────────────────────────────────────────────────────────────────
with open(MASTER, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(all_rows)

# Verify row count
with open(MASTER, encoding='utf-8') as f:
    check = list(csv.DictReader(f))
print(f"\nMaster CSV: {len(check)} rows.")

# Status summary
from collections import Counter
vc = Counter(r.get('verify_status','(blank)') or '(blank)' for r in check)
print("Status distribution:")
for k, v in sorted(vc.items(), key=lambda x: -x[1]):
    print(f"  {k or '(blank)':25s}: {v}")

# Rebuild JSON
print("\nRebuilding ada_db_data.json...")
subprocess.run([sys.executable, 'scripts/_regen_json_only.py'], check=False)

# Copy to web sources
import shutil
shutil.copy('docs/ada_db_data.json', 'insynbio-web-source/ada_db_data.json')
shutil.copy('docs/ada_db_data.json', 'therasik-web-source/ada_db_data.json')
print("Copied to insynbio-web-source and therasik-web-source.")
