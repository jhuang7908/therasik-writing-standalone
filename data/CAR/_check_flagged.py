import csv
path = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\reports\Virtual_Library_Validation_Report.csv'
with open(path, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
print(f"Total rows: {len(rows)}")
GOOD = {"verified","verified 100%","verified structure","patent-verified","published","unverified","needs manual review"}
flagged = [r for r in rows if "missing" in r.get('status','').lower() or "unverified" in r.get('status','').lower() or "manual" in r.get('status','').lower()]
print(f"Flagged rows: {len(flagged)}")
print()
for r in flagged:
    eid = r.get('element_id') or r.get('id') or r.get('name') or list(r.values())[0]
    desc = (r.get('description') or r.get('qa_source') or '')[:70]
    status = r.get('status','')
    seq_len = r.get('length') or r.get('seq_length') or ''
    print(f"  [{status}] {eid} | {desc}")
print()
print("--- Column names ---")
print(list(rows[0].keys()) if rows else "empty")
print()
print("--- First 3 rows ---")
for r in rows[:3]:
    print(dict(r))
