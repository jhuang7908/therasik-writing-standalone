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

# Bedinvetmab (from atlas)
bedin_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFTFSSHGMHWVRQSPGKGLQWVAVINSGGSSTYYTDAVKGRFTISRDNAKNTVYLQMNSLRAEDTAMYYCAKESVGGWEQLVGPHFDYWGQGTLVIVSS"
bedin_vl = "QSVLTQPTSVSGSLGQRVTISCSGSTNNIGILGASWYQLFPGKAPKLLVYGNGNRPSGVPDRFSGADSGDSVTLTITGLQAEDEADYYCQSFDTTLGAHVFGGGTHLTVL"

# V4 (Scheme B)
v4_vh = "EVQLVESGGDLVKPAGSLRLSCVASGFSLIGYDLNWVRQAPEKGLQLVAIIWGDGTTDYNSAVKSRFTISKDFAKNTVYLQMRAEDTAMYYCAKGGYWYATSYYFDYWGQGTSVTVSS"
v4_vl = "QSVLTQPTSVSGSLGQRVTISCRASQSISNNLNWYQQLPGKAPKLLVYYTSRFHSGVPDRFSGSNSGNSATLTITGLQAEDEADYYCQQEHTLPYTFGAGTKLEIK"

def compare_kabat(name1, kd1, name2, kd2):
    all_pos = sorted(set(kd1.keys()) | set(kd2.keys()))
    diffs = []
    matches = 0
    for pos in all_pos:
        aa1 = kd1.get(pos, "-")
        aa2 = kd2.get(pos, "-")
        if aa1 == aa2:
            matches += 1
        else:
            diffs.append({
                "pos": str(pos),
                "aa1": aa1,
                "aa2": aa2
            })
    identity = (matches / len(all_pos)) * 100
    return identity, diffs

kd_bedin_vh = get_kabat(bedin_vh)
kd_bedin_vl = get_kabat(bedin_vl)
kd_v4_vh = get_kabat(v4_vh)
kd_v4_vl = get_kabat(v4_vl)

vh_id, vh_diffs = compare_kabat("Bedinvetmab VH", kd_bedin_vh, "V4 VH", kd_v4_vh)
vl_id, vl_diffs = compare_kabat("Bedinvetmab VL", kd_bedin_vl, "V4 VL", kd_v4_vl)

print(f"VH Identity: {vh_id:.1f}%")
print(f"VL Identity: {vl_id:.1f}%")

comparison = {
    "vh": {"identity": vh_id, "diffs": vh_diffs},
    "vl": {"identity": vl_id, "diffs": vl_diffs}
}

with open("v4_vs_bedinvetmab_diff.json", "w") as f:
    json.dump(comparison, f, indent=2)

print("Comparison saved to v4_vs_bedinvetmab_diff.json")
