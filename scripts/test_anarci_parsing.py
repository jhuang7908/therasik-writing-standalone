import pyhmmer
from pyhmmer.plan7 import HMMFile
from Bio.SearchIO.HmmerIO import Hmmer3TextParser
import io
import os

HMM = r"d:\Users\NextVivo\miniconda3\envs\affmat\Lib\site-packages\anarci\dat\HMMs\ALL.hmm"
seq = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAYDIYGDGAMDYWGQGTLVTVSS"

alphabet = pyhmmer.easel.Alphabet.amino()
seqs_block = [pyhmmer.easel.TextSequence(name=b"seq", sequence=seq.encode())]
digitized = pyhmmer.easel.TextSequenceBlock(seqs_block).digitize(alphabet)

all_top_hits = []
with HMMFile(HMM) as hmm_file:
    for top_hits in pyhmmer.hmmer.hmmscan(digitized, hmm_file, cpus=1):
        all_top_hits.append(top_hits)

# Write to buffer
buf = io.BytesIO()
header = (
    "# HMMER 3.3.2 (Nov 2020); http://hmmer.org/\n"
    "# Copyright (C) 2020 Howard Hughes Medical Institute.\n"
    "# Freely distributed under the BSD open source license.\n"
    "# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -\n"
)
buf.write(header.encode())

for i, th in enumerate(all_top_hits):
    query_name = "seq"
    query_seq = seq
    buf.write(f"Query:       {query_name}  [L={len(query_seq)}]\n".encode())
    th.write(buf)
    buf.write(b"//\n")
buf.seek(0)

# Parse with BioPython
text_content = buf.getvalue().decode()
print(f"HMMER output length: {len(text_content)}")
print("First 500 chars of output:")
print(text_content[:500])

# Hmmer3TextParser expects a text stream
text_stream = io.StringIO(text_content)
p = Hmmer3TextParser(text_stream)
results = list(p)
print(f"Parsed {len(results)} queries.")
for query in results:
    print(f"Query ID: {query.id}")
    print(f"HSP count: {len(query.hsps)}")
