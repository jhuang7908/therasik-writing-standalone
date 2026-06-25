import csv
path = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\reports\Virtual_Library_Validation_Report.csv'
with open(path, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
print(f"Total rows: {len(rows)}")
# Count by QA_Status
from collections import Counter
counts = Counter(r['QA_Status'] for r in rows)
for s, c in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {c:3d}  {s}")

# Find rows with issues
flagged = [r for r in rows if r.get('Validation_Issues','PASS').upper() != 'PASS']
print(f"\nFlagged (non-PASS): {len(flagged)}")
for r in flagged:
    print(f"  [{r['QA_Status']}] {r['Element_Name']} | {r['Validation_Issues']}")
