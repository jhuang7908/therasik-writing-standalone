import sys
from anarcii import Anarcii

n = Anarcii()
seq = 'QVQLVQSGAEVVKPGSSVKLSCKASGFNIKDTYIHWVKQRPEQGREWIGRIYPTNGYTRYDPKFQDRATITADTSTSTAYLEVSRLRSEDTAVYYCSRWGGDGFYAMDYWGQGASVTVSS'
result = n.number(seq)
sys.stderr.write(f"Type: {type(result)}\n")
sys.stderr.write(f"Keys: {list(result.keys())}\n")

for k, v in result.items():
    sys.stderr.write(f"Key: {k}, Value type: {type(v)}, Value: {str(v)[:200]}\n")
