"""Test pyhmmer path directly to identify error."""
import pyhmmer, os, sys, tempfile
from pyhmmer.plan7 import HMMFile

# Find the HMM path
import anarci
pkg = os.path.dirname(anarci.__file__)
HMM_path = os.path.join(pkg, 'dat', 'HMMs')
HMM = os.path.join(HMM_path, 'ALL.hmm')
print(f'HMM path: {HMM}', flush=True)
print(f'HMM exists: {os.path.exists(HMM)}', flush=True)

seqs = [('test', 'DVQLVESGGGSVQAGGSLRLSCAVSGSTYSPCTTGWVRQAPGKGLEWVSSISSPGTIYYQDSVKGRFTISRDNAKNTVYLQMNSLQREDTGMYYCQIQCGSIREYWGQGTQVTVS')]

alphabet = pyhmmer.easel.Alphabet.amino()
seqs_block = [
    pyhmmer.easel.TextSequence(name=name.encode(), sequence=seq.encode())
    for name, seq in seqs
]
digitized = pyhmmer.easel.TextSequenceBlock(seqs_block).digitize(alphabet)
print('digitized OK', flush=True)

all_top_hits = []
try:
    with HMMFile(HMM) as hmm_file:
        print('HMM file opened', flush=True)
        for top_hits in pyhmmer.hmmer.hmmscan(digitized, hmm_file, cpus=1):
            print(f'  got top_hits: nhits={len(top_hits)}', flush=True)
            all_top_hits.append(top_hits)
    print(f'Total top_hits objects: {len(all_top_hits)}', flush=True)
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}', flush=True)
    import traceback; traceback.print_exc()

# Try writing to tempfile
if all_top_hits:
    out_fd, out_path = tempfile.mkstemp('.txt', text=False)
    with os.fdopen(out_fd, 'wb') as fout:
        for th in all_top_hits:
            th.write(fout)
    print(f'Written to {out_path}, size={os.path.getsize(out_path)}', flush=True)
    os.remove(out_path)
    print('PYHMMER PATH WORKS', flush=True)
else:
    print('No top_hits, cannot continue', flush=True)
