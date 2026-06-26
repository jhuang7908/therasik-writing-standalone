#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
prepare_vhh_v1_raw_fasta.py

 VHH v1  FASTA ：
1.  VH3-like / VHH-compatible germline/
2. Camelid VHH germline/

 data/germlines/vhh_v1/raw_fasta/
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# （）
HUMAN_VH3_SCAFFOLDS_FASTA = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds" / "human_vh3_scaffolds.fasta"
HUMAN_IGHV_AA_FASTA = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "IGHV_aa.fasta"

CAMELID_VHH_SCAFFOLDS_FASTA = PROJECT_ROOT / "data" / "germlines" / "vicugna_pacos_ig_aa" / "vhh_scaffolds" / "vhh_scaffolds.fasta"
CAMELID_IGHV_AA_FASTA = PROJECT_ROOT / "data" / "germlines" / "vicugna_pacos_ig_aa" / "IGHV_aa.fasta"

# 
OUTPUT_DIR = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "raw_fasta"
OUTPUT_HUMAN_SCAFFOLDS = OUTPUT_DIR / "human_vh3_scaffolds.fasta"
OUTPUT_HUMAN_GERMLINES = OUTPUT_DIR / "human_vh3_germlines.fasta"
OUTPUT_CAMELID_SCAFFOLDS = OUTPUT_DIR / "camelid_vhh_scaffolds.fasta"
OUTPUT_CAMELID_GERMLINES = OUTPUT_DIR / "camelid_vhh_germlines.fasta"


def read_fasta(fp: Path) -> Dict[str, str]:
    """ FASTA ， {header: sequence} """
    seqs = {}
    if not fp.exists():
        return seqs
    
    name = None
    seq = []
    
    with open(fp, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    seqs[name] = "".join(seq)
                name = line[1:]
                seq = []
            else:
                seq.append(line)
        if name is not None:
            seqs[name] = "".join(seq)
    
    return seqs


def write_fasta(fp: Path, seqs: Dict[str, str]):
    """ FASTA """
    with open(fp, "w", encoding="utf-8") as f:
        for header, seq in seqs.items():
            f.write(f">{header}\n")
            #  80 
            for i in range(0, len(seq), 80):
                f.write(f"{seq[i:i+80]}\n")


def extract_vh3_from_human_ighv(fasta_path: Path) -> Dict[str, str]:
    """ IGHV FASTA  VH3 """
    all_seqs = read_fasta(fasta_path)
    vh3_seqs = {}
    
    for header, seq in all_seqs.items():
        #  VH3 family
        # ：M99652|IGHV3-11*01|...
        if "|IGHV3-" in header or "IGHV3-" in header:
            vh3_seqs[header] = seq
    
    return vh3_seqs


def main():
    print("=" * 80)
    print(" VHH v1  FASTA ")
    print("=" * 80)
    
    # 
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n[1] : {OUTPUT_DIR}")
    
    # 1.  VH3 scaffold（）
    print(f"\n[2]  VH3 scaffold...")
    if HUMAN_VH3_SCAFFOLDS_FASTA.exists():
        shutil.copy2(HUMAN_VH3_SCAFFOLDS_FASTA, OUTPUT_HUMAN_SCAFFOLDS)
        seqs = read_fasta(HUMAN_VH3_SCAFFOLDS_FASTA)
        print(f"  ✅ : {len(seqs)}  scaffold ")
        print(f"     : {HUMAN_VH3_SCAFFOLDS_FASTA}")
        print(f"     : {OUTPUT_HUMAN_SCAFFOLDS}")
    else:
        print(f"  ⚠️  : {HUMAN_VH3_SCAFFOLDS_FASTA}")
    
    # 2.  IGHV FASTA  VH3 germline（ germline ）
    print(f"\n[3]  VH3 germline...")
    if HUMAN_IGHV_AA_FASTA.exists():
        vh3_seqs = extract_vh3_from_human_ighv(HUMAN_IGHV_AA_FASTA)
        if vh3_seqs:
            write_fasta(OUTPUT_HUMAN_GERMLINES, vh3_seqs)
            print(f"  ✅ : {len(vh3_seqs)}  VH3 germline ")
            print(f"     : {HUMAN_IGHV_AA_FASTA}")
            print(f"     : {OUTPUT_HUMAN_GERMLINES}")
        else:
            print(f"  ⚠️   VH3 ")
    else:
        print(f"  ⚠️  : {HUMAN_IGHV_AA_FASTA}")
    
    # 3.  Camelid VHH scaffold（）
    print(f"\n[4]  Camelid VHH scaffold...")
    if CAMELID_VHH_SCAFFOLDS_FASTA.exists():
        shutil.copy2(CAMELID_VHH_SCAFFOLDS_FASTA, OUTPUT_CAMELID_SCAFFOLDS)
        seqs = read_fasta(CAMELID_VHH_SCAFFOLDS_FASTA)
        print(f"  ✅ : {len(seqs)}  scaffold ")
        print(f"     : {CAMELID_VHH_SCAFFOLDS_FASTA}")
        print(f"     : {OUTPUT_CAMELID_SCAFFOLDS}")
    else:
        print(f"  ⚠️  : {CAMELID_VHH_SCAFFOLDS_FASTA}")
    
    # 4.  Camelid IGHV FASTA（ germline ）
    print(f"\n[5]  Camelid VHH germline...")
    if CAMELID_IGHV_AA_FASTA.exists():
        shutil.copy2(CAMELID_IGHV_AA_FASTA, OUTPUT_CAMELID_GERMLINES)
        seqs = read_fasta(CAMELID_IGHV_AA_FASTA)
        print(f"  ✅ : {len(seqs)}  germline ")
        print(f"     : {CAMELID_IGHV_AA_FASTA}")
        print(f"     : {OUTPUT_CAMELID_GERMLINES}")
    else:
        print(f"  ⚠️  : {CAMELID_IGHV_AA_FASTA}")
    
    # 
    print(f"\n" + "=" * 80)
    print("✅ ")
    print("=" * 80)
    print(f"\n: {OUTPUT_DIR}")
    print("\n:")
    for f in sorted(OUTPUT_DIR.glob("*.fasta")):
        seqs = read_fasta(f)
        print(f"  - {f.name}: {len(seqs)} ")


if __name__ == "__main__":
    main()













