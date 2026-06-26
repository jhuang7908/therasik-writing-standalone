"""
extract_human_vh3_frameworks.py

：
-  IMGT Homo_sapiens IGHV_aa FASTA  VH3 family 
-  ANARCI  IMGT  →  FR1/FR2/FR3/FR4
-  core/data/human_VH3_frameworks.json

：
- pip install anarci
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List
from anarci import run_anarci


PROJECT_ROOT = Path(__file__).resolve().parents[1]

#  FASTA 
POSSIBLE_FASTA_PATHS = [
    # ：data/germlines/IMGT_V-/IMGT_V-QUEST_reference_directory/Homo_sapiens/IG/ ( IGHV.fasta)
    PROJECT_ROOT / "data" / "germlines" / "IMGT_V-" / "IMGT_V-QUEST_reference_directory" / "Homo_sapiens" / "IG",
    # ：data/germlines/IMGT_V-/IMGT_V-QUEST_reference_directory/Homo_sapiens/IG_aa/
    PROJECT_ROOT / "data" / "germlines" / "IMGT_V-" / "IMGT_V-QUEST_reference_directory" / "Homo_sapiens" / "IG_aa",
    # ：data/germlines/IMGT_V-QUEST_reference_directory/Homo_sapiens/IG_aa/
    PROJECT_ROOT / "data" / "germlines" / "IMGT_V-QUEST_reference_directory" / "Homo_sapiens" / "IG_aa",
    # ：core/data/germline/...
    PROJECT_ROOT / "core" / "data" / "germline" / "IMGT_V-QUEST_reference_directory" / "Homo_sapiens" / "IG_aa" / "IGHV_aa",
    Path(r"D:\InSynBio-AI-Research\antibody_engineering\core\data\germline\IMGT_V-QUEST_reference_directory\Homo_sapiens\IG_aa"),
    PROJECT_ROOT / "core" / "data" / "germline" / "IMGT_V-QUEST_reference_directory" / "Homo_sapiens" / "IG_aa",
]

OUTPUT_JSON = PROJECT_ROOT / "core" / "data" / "human_VH3_frameworks.json"


def load_fasta_multi(path: Path) -> Dict[str, str]:
    """ FASTA"""
    seqs = {}
    header = None
    buf = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                seqs[header] = "".join(buf)
            header = line[1:].strip()
            buf = []
        else:
            buf.append(line)
    if header is not None:
        seqs[header] = "".join(buf)
    return seqs


def extract_frameworks_from_imgt(seq: str) -> Dict:
    """ ANARCI  IMGT ， FR/CDR 。"""
    result = run_anarci(
        sequences=[("vh3", seq)],
        scheme="imgt",
        output=False,
        assign_germline=False,
    )

    numbering, _, _ = result
    numbering = numbering[0][1]  #  residue_table

    #  region
    regions = {"FR1": "", "CDR1": "", "FR2": "", "CDR2": "", "FR3": "", "CDR3": "", "FR4": ""}

    for pos in numbering:
        aa = pos[1]
        region = pos[3]
        if region in regions:
            regions[region] += aa

    return regions


def find_fasta_directory() -> Path:
    """ IGHV_aa FASTA """
    for path in POSSIBLE_FASTA_PATHS:
        if path.exists():
            fasta_files = list(path.glob("*.fasta")) + list(path.glob("*.fa")) + list(path.glob("IGHV*"))
            if fasta_files:
                print(f"[INFO]  FASTA ：{path}")
                return path
    return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description=" Human VH3 Framework ")
    parser.add_argument(
        "--fasta-dir",
        type=str,
        help=" FASTA （）",
    )
    args = parser.parse_args()
    
    #  FASTA 
    if args.fasta_dir:
        fasta_dir = Path(args.fasta_dir)
        if not fasta_dir.exists():
            raise FileNotFoundError(f"：{fasta_dir}")
    else:
        fasta_dir = find_fasta_directory()
        if not fasta_dir:
            print("\n[ERROR]  IGHV_aa FASTA ！")
            print("\n：")
            print("1.  IMGT ：https://www.imgt.org/vquest/refseqh.html")
            print("2. ：")
            for path in POSSIBLE_FASTA_PATHS:
                print(f"   - {path}")
            print("\n3.  --fasta-dir ")
            raise FileNotFoundError(" FASTA ")

    print(f"[INFO]  IGHV_aa FASTA：{fasta_dir}")

    #  FASTA 
    fasta_files = []
    #  IGHV_aa.fasta, IGHV_aa.fa, IGHV.fasta, IGHV.fa
    for name in ["IGHV_aa.fasta", "IGHV_aa.fa", "IGHV.fasta", "IGHV.fa"]:
        candidate = fasta_dir / name
        if candidate.exists():
            fasta_files.append(candidate)
            print(f"[INFO] ：{candidate}")
            break
    
    # ， .fasta  .fa 
    if not fasta_files:
        fasta_files = list(fasta_dir.glob("*.fasta")) + list(fasta_dir.glob("*.fa"))
        if fasta_files:
            print(f"[INFO]  {len(fasta_files)}  FASTA ")
    
    # ， IGHV 
    if not fasta_files:
        fasta_files = list(fasta_dir.glob("*IGHV*"))
        if fasta_files:
            print(f"[INFO]  {len(fasta_files)}  IGHV ")
    
    if not fasta_files:
        raise FileNotFoundError(f" {fasta_dir}  FASTA ")

    final_entries = []

    for fasta in fasta_files:
        print(f"[LOAD] {fasta}")
        seqs = load_fasta_multi(fasta)

        for header, seq in seqs.items():
            #  VH3 family
            # ： IGHV3-23*01
            if "|IGHV3-" not in header and "IGHV3-" not in header:
                continue

            print(f"[VH3]  → {header[:50]}...")
            regions = extract_frameworks_from_imgt(seq)

            entry = {
                "id": header.split("|")[0],
                "raw_header": header,
                "sequence_aa": seq,
                "frameworks": regions
            }
            final_entries.append(entry)

    data = {
        "library_name": "human_VH3_frameworks",
        "version": "auto_extract_MVP1",
        "entries": final_entries,
    }

    OUTPUT_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"[OK] ：{OUTPUT_JSON}")
    print(f"[INFO]  {len(final_entries)}  VH3 ")


if __name__ == "__main__":
    main()




















