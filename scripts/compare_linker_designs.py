#!/usr/bin/env python
# -*- coding: utf-8 -*-
from Bio.SeqUtils.ProtParam import ProteinAnalysis

linkers = [
    ("(G4S)3 baseline",            "GGGGSGGGGSGGGGS"),
    ("C +3E",                "GGGGSGGGGSGGGGSEEE"),
    ("N 3E+",                "EEEGGGGSGGGGSGGGGS"),
    (" EGGGGSEGGGGSEGGGGG", "EGGGGSEGGGGSEGGGGG"),
    (" GG3SEEGG3SEG3GS",      "GGGGSEEGGGGSGGGGS"),
    ("(G4S)2+EEEGS",               "GGGGSGGGGSEEEGS"),
    ("E",                   "EGGGGSEGGGGSEGGGGGS"),
]

tnb04h9  = "EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVMGWYRQAPGKGRELVSRITLDGRPYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCKLENGGFFYYWGQGTMVTVSS"
tnb164h6 = "EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGKGREFVSAHGWIGGKEYYADSVKGRFTVSRDNSKNTLYLQMNSLRAEDTAVYYCAAHWSGDYYDSAAYNYWGQGTMVTVSS"

header = "{:40s}  {:18s}  {:>8s}  {:>8s}  {:>8s}  {:>6s}".format(
    "Linker", "", "pI", "pI", "@7", "")
print(header)
print("-"*100)
for name, lk in linkers:
    lk_pa = ProteinAnalysis(lk.upper())
    fusion = tnb04h9 + lk + tnb164h6
    fa = ProteinAnalysis(fusion.upper())
    row = "{:40s}  {:18s}  {:>8.2f}  {:>8.2f}  {:>+8.1f}  {:>6d}".format(
        name, lk, lk_pa.isoelectric_point(), fa.isoelectric_point(),
        fa.charge_at_pH(7.0), len(fusion))
    print(row)
