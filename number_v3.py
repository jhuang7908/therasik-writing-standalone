import json
import sys
from pathlib import Path

# Add suite root to path
suite_root = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.append(str(suite_root))

from core.humanization.kabat_utils import kabat_from_anarcii
from anarci import anarci

def get_kabat(seq):
    results = anarci([("seq", seq)], scheme="kabat")
    if results[0] and results[0][0]:
        numbering = results[0][0][0][0]
        return kabat_from_anarcii(numbering)
    return None

v3_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQWLGIIWGDGTTDYNSAVKSRVTISKDSAKNTFYLQLQSLRAEETAVYYCARGGYWYATSYYFDYWGQGTSVTVSS"
kd = get_kabat(v3_vh)

if kd:
    print("V3 VH Kabat Numbering:")
    for pos, aa in sorted(kd.items()):
        # pos is (int, str)
        print(f"  {pos}: {aa}")
else:
    print("Failed to number V3 VH.")
