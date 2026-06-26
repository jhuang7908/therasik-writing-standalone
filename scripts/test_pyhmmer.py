import pyhmmer
from pyhmmer.plan7 import HMMFile
import os

HMM = r"d:\Users\NextVivo\miniconda3\envs\affmat\Lib\site-packages\anarci\dat\HMMs\ALL.hmm"
seq = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAYDIYGDGAMDYWGQGTLVTVSS"

print(f"Loading HMM from {HMM}...")
alphabet = pyhmmer.easel.Alphabet.amino()
seqs_block = [pyhmmer.easel.TextSequence(name=b"seq", sequence=seq.encode())]
digitized = pyhmmer.easel.TextSequenceBlock(seqs_block).digitize(alphabet)

all_top_hits = []
try:
    with HMMFile(HMM) as hmm_file:
        print("Running hmmscan...")
        for top_hits in pyhmmer.hmmer.hmmscan(digitized, hmm_file, cpus=1):
            all_top_hits.append(top_hits)
    print(f"Found {len(all_top_hits)} hits.")
    for th in all_top_hits:
        print(f"Hit count: {len(th)}")
        if len(th) > 0:
            print(f"Top hit: {th[0].name}")
except Exception as e:
    print(f"Error: {e}")
