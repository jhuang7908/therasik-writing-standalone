"""
Correct Relatlimab ADA value.

FINDING:
  Stored value: <2%  (source: "from Claude response" — AI-generated, NO primary source)
  
  FDA PI Opdualag label §12.6 Immunogenicity (RELATIVITY-047, 24-month data):
    Anti-relatlimab antibodies:  5.6% (16/286)
    Neutralizing antibodies:     0.3%  (1/286)
    "Because of the low incidence of anti-drug antibodies, the effect of these
     antibodies on PK, PD, safety, or effectiveness of OPDUALAG is unknown."
  
  Source: DailyMed setid b22c9d83-3256-4e17-85f7-f331a504adc6
          https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=b22c9d83-3256-4e17-85f7-f331a504adc6
"""
import csv, subprocess, sys

MASTER_CSV = r'data\ada_master_136_curated.csv'
rows = list(csv.DictReader(open(MASTER_CSV, encoding='utf-8')))
fieldnames = list(rows[0].keys())

for row in rows:
    if 'relatlimab' in row.get('antibody_name', '').lower():
        old = row['ada_value_display']
        row['ada_value_display'] = '5.6% (16/286); nAb 0.3%'
        row['ada_first_pct']     = '5.6'
        row['evidence_tier']     = 'A'
        row['ada_source_pmids']  = ''
        row['ada_source_url_primary'] = (
            'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm'
            '?setid=b22c9d83-3256-4e17-85f7-f331a504adc6'
        )
        row['ada_evidence_chain_excerpt'] = (
            "Opdualag (relatlimab + nivolumab) FDA PI §12.6 Immunogenicity, "
            "RELATIVITY-047 (Phase III, melanoma, 24-month data): "
            "Anti-relatlimab antibodies 5.6% (16/286); neutralizing antibodies 0.3% (1/286). "
            "Anti-nivolumab antibodies 3.8% (11/288); neutralizing 0.3% (1/288). "
            "'Because of the low incidence of anti-drug antibodies, the effect of these "
            "antibodies on the pharmacokinetics, pharmacodynamics, safety, or effectiveness "
            "of OPDUALAG is unknown.' "
            "DailyMed setid: b22c9d83-3256-4e17-85f7-f331a504adc6. "
            "CORRECTION: Previous stored value '<2%' was from an AI-generated summary "
            "with no primary source. Corrected to FDA PI data."
        )
        print(f"  Relatlimab corrected: {old} → 5.6% (16/286) [Tier B→A, FDA PI §12.6]")

with open(MASTER_CSV, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)
print("  Master CSV updated.")

# Update CORRECTIONS dict in apply_verification_to_master.py for both records
import re
script = open('apply_verification_to_master.py', encoding='utf-8').read()

# Add Relatlimab and update Olokizumab to CORRECTED status
OLD_CORRECTIONS = """CORRECTIONS = {
    'Adalimumab': {"""
NEW_CORRECTIONS = """CORRECTIONS = {
    'Relatlimab': {
        'verify_status':    'CORRECTED',
        'verify_note':      ('CORRECTED from <2% (AI-generated) to 5.6% (16/286) per FDA PI '
                             'Opdualag §12.6, RELATIVITY-047 24-month data. '
                             'Neutralizing antibodies: 0.3% (1/286). '
                             'DailyMed setid b22c9d83-3256-4e17-85f7-f331a504adc6.'),
    },
    'Olokizumab': {
        'verify_status':    'CORRECTED',
        'verify_note':      ('CORRECTED from 10-15% (AI-generated) to 3.2% (Q4W) / 7.0% (Q2W) '
                             'per PMID 36109142 (Feist et al., Ann Rheum Dis 2022;81:1661-1668, '
                             'Phase III TNFi-IR trial, n=197). No impact on clinical outcomes '
                             'in ADA+ vs ADA- patients.'),
    },
    'Adalimumab': {"""

if OLD_CORRECTIONS in script:
    script = script.replace(OLD_CORRECTIONS, NEW_CORRECTIONS, 1)
    open('apply_verification_to_master.py', 'w', encoding='utf-8').write(script)
    print("  apply_verification_to_master.py updated with Relatlimab + Olokizumab CORRECTED status")
else:
    print("  WARNING: Could not find CORRECTIONS block to update")

# Rebuild JSON
print("\nRebuilding ada_db_data.json...")
result = subprocess.run([sys.executable, 'apply_verification_to_master.py'],
                        capture_output=True, text=True, cwd='.')
print(result.stdout[-400:] if result.stdout else '')
if result.returncode != 0:
    print("ERROR:", result.stderr[-200:])
print("Done.")
