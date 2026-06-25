import json
import sys
from pathlib import Path
from anarci import anarci

suite_root = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.append(str(suite_root))

from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys, is_in_cdr

# 1. Sequences
tanezumab_vh = "QVQLQESGPGLVRPSQTLSLTCTVSGFSLIGYDLNWVRQPPGRGLEWIGIIWGDGTTDYNSAVKSRVTMLKDTSKNQFSLRLSSVTAADTAVYYCARGGYWYATSYYFDYWGQGTLVTVSS"
tanezumab_vl = "DIQMTQSPSSLSASVGDRVTITCRASQSISNNLNWYQQKPGKAPKLLIYYTSRFHSGVPSRFSGSGSGTDFTFTISSLQPEDIATYYCQQEHTLPYTFGQGTKLEIK"

bedin_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFTFSSHGMHWVRQSPGKGLQWVAVINSGGSSTYYTDAVKGRFTISRDNAKNTVYLQMNSLRAEDTAMYYCAKESVGGWEQLVGPHFDYWGQGTLVIVSS"
bedin_vl = "QSVLTQPTSVSGSLGQRVTISCSGSTNNIGILGASWYQLFPGKAPKLLVYGNGNRPSGVPDRFSGADSGDSVTLTITGLQAEDEADYYCQSFDTTLGAHVFGGGTHLTVL"

v3_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQWLGIIWGDGTTDYNSAVKSRVTISKDSAKNTFYLQLQSLRAEETAVYYCARGGYWYATSYYFDYWGQGTSVTVSS"
v3_vl = "EIVLTQSPASLSLSQEEKVTITCRASQSISNNLNWYQQKPGQAPKLLIYYTSRFHSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQEHTLPYTFGQGTKVELK"

v4_vh = "EVQLVESGGDLVKPAGSLRLSCVASGFSLIGYDLNWVRQAPEKGLQLVAIIWGDGTTDYNSAVKSRFTISKDFAKNTVYLQMRAEDTAMYYCAKGGYWYATSYYFDYWGQGTSVTVSS"
v4_vl = "QSVLTQPTSVSGSLGQRVTISCRASQSISNNLNWYQQLPGKAPKLLVYYTSRFHSGVPDRFSGSNSGNSATLTITGLQAEDEADYYCQQEHTLPYTFGAGTKLEIK"

v5_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQLVAIIWGDGTTDYNSAVKSRFTISKDFAKNTVYLQLRAEDTAVYYCAKGGYWYATSYYFDYWGQGTLVTVSS"
v5_vl = "QSVLTQPASSVSGSLGQRVTISCRASQSISNNLNWYQQLPGKAPKLLVYYTSRFHSGVPDRFSGSGSGNSATLTISGLQAEDEADYYCQQEHTLPYTFGQGTKLEIK"

# Dog Germlines for reference
# IGHV3-9*01: EVQLVESGGDLVKPGGSLRLSCVASGFTFSSYGMHWVRQAPGKGLQWVAVISYDGSNKYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAR
# IGKV3-18*02: EIVLTQSPASLSLSQEEKVTITCRASQSVSSNLAWYQQKPGQAPKLLIYGASTRATGVPDRFSGSGSGTDFTLTISSLEPEDVAVYYC
# IGHV3-19*01: EVQLVESGGDLVKPGGSLRLSCVASGFTFSSYGMHWVRQAPGKGLQWVAVISYDGSNKYYADSVKGRFTISRDNAKNTVYLQMNSLRAEDTAMYYCAK
# IGLV1-141*01: QSVLTQPTS-VSGSLGQRVTISCSGSSSNIGNNAVSWYQQLPGKAPKLLVYYDDDLRPSGVPDRFSGSKSGTSASLTITGLQAEDEADYYC

def get_fr13_seq(seq, chain):
    kd = get_kabat_numbering(seq)
    if not kd: return ""
    # FR1-FR3 excluding CDRs (Kabat)
    # VH: 1-25, 36-49, 66-94
    # VL: 1-23, 35-49, 57-88
    if chain == "VH":
        ranges = [(1, 25), (36, 49), (66, 94)]
    else:
        ranges = [(1, 23), (35, 49), (57, 88)]
    
    fr_aa = []
    for k in sorted_keys(kd):
        pos, ins = k
        in_fr = False
        for lo, hi in ranges:
            if lo <= pos <= hi:
                in_fr = True
                break
        if in_fr:
            fr_aa.append(kd[k])
    return "".join(fr_aa)

def calculate_identity(seq1, seq2):
    matches = sum(1 for a, b in zip(seq1, seq2) if a == b)
    return (matches / max(len(seq1), len(seq2))) * 100

# 2. Analysis
variants = {
    "V3": (v3_vh, v3_vl),
    "V4": (v4_vh, v4_vl),
    "V5": (v5_vh, v5_vl)
}

bedin_fr_vh = get_fr13_seq(bedin_vh, "VH")
bedin_fr_vl = get_fr13_seq(bedin_vl, "VL")

results = {}
for name, (vh, vl) in variants.items():
    fr_vh = get_fr13_seq(vh, "VH")
    fr_vl = get_fr13_seq(vl, "VL")
    
    results[name] = {
        "vh_identity": calculate_identity(fr_vh, bedin_fr_vh),
        "vl_identity": calculate_identity(fr_vl, bedin_fr_vl)
    }

print("FR1-FR3 Identity vs Bedinvetmab:")
for name, res in results.items():
    print(f"  {name}: VH={res['vh_identity']:.1f}%, VL={res['vl_identity']:.1f}%")

# 3. Back-mutation check (Manual vs Bedinvetmab)
# Bedinvetmab VH: IGHV3-19*01. Differences from germline: CDRs + FR4. 
# V4 VH: IGHV3-19*01 + H71K, H78F. 
# Bedinvetmab at H71 is R, H78 is V. V4 at H71 is K, H78 is F. (No overlap)

# 4. pI check
# Tanezumab: 8.61
# V3: 7.94
# V4: 7.85
# V5: 7.85
# Normal dog range: VH 6.0-9.5, VL 4.5-8.5. Fv combined usually 6.0-9.0.
