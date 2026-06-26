"""Verify V4b VL sequence - checking for conserved Cys and similarity calculation."""
import sys
from pathlib import Path
suite_root = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.append(str(suite_root))

from anarci import anarci

import json
from pathlib import Path
import sys
suite_root = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.append(str(suite_root))

from anarci import anarci

bedin_vl = "QSVLTQPTSVSGSLGQRVTISCSGSTNNIGILGASWYQLFPGKAPKLLVYGNGNRPSGVPDRFSGADSGDSVTLTITGLQAEDEADYYCQSFDTTLGAHVFGGGTHLTVL"
v4_vl   = "QSVLTQPTSVSGSLGQRVTISCRASQSISNNLNWYQQLPGKAPKLLVYYTSRFHSGVPDRFSGSNSGNSATLTITGLQAEDEADYYCQQEHTLPYTFGGGTHLTVL"
with open(suite_root / "v4b_design_results.json") as f:
    v4b_vl = json.load(f)["vl"]

print("=" * 80)
print("CONSERVED CYS CHECK (Kabat 88 of VL — disulfide partner of Cys 23)")
print("=" * 80)

for name, seq in [("Bedinvetmab", bedin_vl), ("V4", v4_vl), ("V4b", v4b_vl)]:
    n_cys = seq.count("C")
    print(f"\n{name}: total Cys = {n_cys}")
    # Kabat numbering
    res = anarci([("seq", seq)], scheme="kabat")
    if res[0] and res[0][0]:
        numbering = res[0][0][0][0]
        c_positions = [(p, ins, aa) for (p, ins), aa in numbering if aa == "C"]
        print(f"  Cys positions (Kabat): {c_positions}")
        # Check what's at Kabat 88
        for (p, ins), aa in numbering:
            if p == 88:
                marker = " [CONSERVED DISULFIDE — MUST BE C]" if aa != "C" else " [OK]"
                print(f"  Kabat 88 = '{aa}'{marker}")
            if p == 23:
                marker = " [OK]" if aa == "C" else " [BAD]"
                print(f"  Kabat 23 = '{aa}'{marker}")

print("\n" + "=" * 80)
print("RAW LENGTH CHECK")
print("=" * 80)
for name, seq in [("Bedinvetmab", bedin_vl), ("V4", v4_vl), ("V4b", v4b_vl)]:
    print(f"{name:15s} len={len(seq):3d}  tail='...{seq[-30:]}'")

# Compare V4 and V4b residue by residue around the FR3/CDR3 junction
print("\n" + "=" * 80)
print("ALIGNMENT around FR3/CDR3 junction (positions 80-100 of seq)")
print("=" * 80)
print(f"V4  : {v4_vl[80:]}")
print(f"V4b : {v4b_vl[80:]}")
