import json, sys
data = json.load(open('data/vhh_database_b_union/database_b_sequences.json'))
print('top-level keys:', list(data.keys()), flush=True)
entries = data.get('entries', data.get('sequences', []))
print(f'n entries = {len(entries)}', flush=True)
if entries:
    e0 = entries[0]
    print('first entry keys:', list(e0.keys()), flush=True)
    for e in entries[:4]:
        sid = e.get('safe_id', e.get('id', '?'))
        seq = e.get('sequence', e.get('seq', ''))
        print(f'  {sid}: len={len(seq)} seq={seq[:60]}', flush=True)
