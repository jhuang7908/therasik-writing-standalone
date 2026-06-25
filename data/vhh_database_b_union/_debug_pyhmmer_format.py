"""Debug pyhmmer output format vs what parse_hmmer_output expects."""
import pyhmmer, os, tempfile
from pyhmmer.plan7 import HMMFile
import anarci
from anarci.anarci import parse_hmmer_output, HMM_path

HMM = os.path.join(HMM_path, 'ALL.hmm')
seq = 'DVQLVESGGGSVQAGGSLRLSCAVSGSTYSPCTTGWVRQAPGKGLEWVSSISSPGTIYYQDSVKGRFTISRDNAKNTVYLQMNSLQREDTGMYYCQIQCGSIREYWGQGTQVTVS'
seqs = [('test', seq)]

alphabet = pyhmmer.easel.Alphabet.amino()
seqs_block = [pyhmmer.easel.TextSequence(name=n.encode(), sequence=s.encode()) for n, s in seqs]
digitized = pyhmmer.easel.TextSequenceBlock(seqs_block).digitize(alphabet)

all_top_hits = []
with HMMFile(HMM) as hmm_file:
    for th in pyhmmer.hmmer.hmmscan(digitized, hmm_file, cpus=1):
        all_top_hits.append(th)

print(f'all_top_hits: {len(all_top_hits)} objects', flush=True)
for th in all_top_hits:
    print(f'  TopHits: nhits={len(th)}, attrs={[a for a in dir(th) if not a.startswith("_")][:8]}', flush=True)

# Write to temp file
out_fd, out_path = tempfile.mkstemp('.txt', text=False)
with os.fdopen(out_fd, 'wb') as fout:
    for th in all_top_hits:
        th.write(fout)

print(f'Written {os.path.getsize(out_path)} bytes to {out_path}', flush=True)

# Print first 80 lines of output
with open(out_path, 'r', errors='replace') as f:
    lines = f.readlines()
print(f'Total lines: {len(lines)}', flush=True)
for i, l in enumerate(lines[:30]):
    print(f'{i:3}: {l.rstrip()}', flush=True)

# Now try parse_hmmer_output
print('\n--- parse_hmmer_output ---', flush=True)
try:
    results = parse_hmmer_output(out_path, bit_score_threshold=80)
    print(f'results: len={len(results)}', flush=True)
    for i, r in enumerate(results):
        print(f'  result[{i}]: type={type(r)}, len(r)={len(r) if r else "N/A"}', flush=True)
        if r:
            print(f'    r[0] (hit_table)[:3]: {r[0][:3]}', flush=True)
            print(f'    r[1] (state_vectors): len={len(r[1])}', flush=True)
            print(f'    r[2] (descriptions): {r[2]}', flush=True)
except Exception as e:
    print(f'parse error: {e}', flush=True)
    import traceback; traceback.print_exc()

os.remove(out_path)
