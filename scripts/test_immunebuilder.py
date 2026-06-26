import sys
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from ImmuneBuilder import NanoBodyBuilder2

print("Loading NanoBodyBuilder2...")
pred = NanoBodyBuilder2()
seq = 'QVQLVQSGAEVVKPGSSVKLSCKASGFNIKDTYIHWVKQRPEQGREWIGRIYPTNGYTRYDPKFQDRATITADTSTSTAYLEVSRLRSEDTAVYYCSRWGGDGFYAMDYWGQGASVTVSS'
print(f"Predicting WT VHH ({len(seq)} aa)...")
r = pred.predict({'H': seq})
out = r'd:\\InSynBio-AI-Research\\Antibody_Engineer_Suite\\test_vhh_wt.pdb'
r.save(out)
print(f"Saved to {out}")
