import json, csv, sys
from pathlib import Path
from anarci import anarci

root = Path(r'd:/InSynBio-AI-Research/Antibody_Engineer_Suite')
seqs_raw = json.load(open(root / 'data/vhh_database_b_union/database_b_sequences.json'))['entries']
print(f'Total sequences: {len(seqs_raw)}', flush=True)

IMGT_CDR1 = (27, 38)
IMGT_CDR2 = (56, 65)
IMGT_CDR3 = (105, 117)

results = []
for e in seqs_raw:
    sid = e['safe_id']
    seq = e['sequence']
    try:
        res, _, _ = anarci([(sid, seq)], scheme='imgt', output=False)
        if res and res[0]:
            sorted_num = sorted(res[0][0][0], key=lambda x: (x[0][0], x[0][1]))
            def extract(lo, hi, sn=sorted_num):
                return ''.join(aa for (pos, ins), aa in sn if lo <= pos <= hi and aa != '-')
            r = {
                'safe_id': sid,
                'CDR1': extract(*IMGT_CDR1),
                'CDR2': extract(*IMGT_CDR2),
                'CDR3': extract(*IMGT_CDR3),
            }
            results.append(r)
            print(f"  {sid}: CDR3={r['CDR3']} (len={len(r['CDR3'])})", flush=True)
        else:
            print(f'  SKIP {sid}: no ANARCI result', flush=True)
    except Exception as ex:
        print(f'  ERROR {sid}: {ex}', flush=True)

outpath = root / 'data/vhh_database_b_union/vhh29_cdr_segments.csv'
with open(outpath, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['safe_id', 'CDR1', 'CDR2', 'CDR3'])
    w.writeheader()
    w.writerows(results)
print(f'Done. Saved {len(results)} rows to {outpath}', flush=True)
