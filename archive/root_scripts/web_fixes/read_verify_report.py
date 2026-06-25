import csv

rows = list(csv.DictReader(open('data/ada_evidence_verification_report.csv', encoding='utf-8')))

src_dist = {}
for r in rows:
    src_dist[r['source_type']] = src_dist.get(r['source_type'], 0) + 1
print('Source distribution:', src_dist)

disc = [r for r in rows if r['verify_status'] == 'DISCREPANCY']
disc_sorted = sorted(disc, key=lambda x: float(x['delta'] or 0), reverse=True)
print(f'\nAll {len(disc)} DISCREPANCIES (sorted by delta):')
for r in disc_sorted:
    name = r['antibody_name'][:32]
    stored = r['stored_pct']
    src = r['source_pct']
    d = r['delta']
    pmid = r['source_id'][:20]
    note = r['note'][:100]
    print(f'  {name:32s} stored={stored}% src_val={src}% delta={d}%  id={pmid}')
    print(f'    {note}')

unreach = [r for r in rows if r['verify_status'] == 'UNREACHABLE']
print(f'\nUNREACHABLE ({len(unreach)}):')
for r in unreach:
    name = r['antibody_name'][:32]
    stype = r['source_type']
    sid = r['source_id'][:70]
    print(f'  {name:32s} | {stype:6s} | {sid}')

uncertain = [r for r in rows if r['verify_status'] == 'UNCERTAIN']
print(f'\nUNCERTAIN ({len(uncertain)}):')
for r in uncertain:
    print(f'  {r["antibody_name"][:35]:35s} | {r["note"][:80]}')
