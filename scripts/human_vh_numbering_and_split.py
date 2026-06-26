#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
human_vh_numbering_and_split.py

Human IGHV（VH3）IMGTFR/CDR
ANARCII，VHHIMGT
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map, IMGTNumberingError

# IMGT（VHH）
IMGT_REGIONS = {
    "FR1": {"start": 1, "end": 26},
    "CDR1": {"start": 27, "end": 38},
    "FR2": {"start": 39, "end": 55},
    "CDR2": {"start": 56, "end": 65},
    "FR3": {"start": 66, "end": 104},
    "CDR3": {"start": 105, "end": 117},
    "FR4": {"start": 118, "end": 128},
}

INPUT_FASTA = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "IGHV_aa.fasta"
OUTPUT_DIR = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_numbered"
OUTPUT_JSON = OUTPUT_DIR / "human_vh_numbered_and_split.json"


def read_fasta(fp: Path) -> Dict[str, str]:
    """FASTA，{header: sequence}"""
    seqs = {}
    name = None
    seq = []
    
    if not fp.exists():
        return seqs
    
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


def slice_region(pos_map: Dict[int, str], start: int, end: int) -> str:
    """"""
    return "".join(pos_map.get(i, "") for i in range(start, end + 1))


def split_regions(rows: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    IMGTFRCDR（VHH）
    """
    regions = {
        "FR1": [],
        "CDR1": [],
        "FR2": [],
        "CDR2": [],
        "FR3": [],
        "CDR3": [],
        "FR4": [],
    }
    
    for row in rows:
        pos = row.get("pos")
        aa = row.get("aa")
        
        if not isinstance(pos, int) or not isinstance(aa, str) or aa == "-":
            continue
        
        # 
        if IMGT_REGIONS["FR1"]["start"] <= pos <= IMGT_REGIONS["FR1"]["end"]:
            regions["FR1"].append(aa)
        elif IMGT_REGIONS["CDR1"]["start"] <= pos <= IMGT_REGIONS["CDR1"]["end"]:
            regions["CDR1"].append(aa)
        elif IMGT_REGIONS["FR2"]["start"] <= pos <= IMGT_REGIONS["FR2"]["end"]:
            regions["FR2"].append(aa)
        elif IMGT_REGIONS["CDR2"]["start"] <= pos <= IMGT_REGIONS["CDR2"]["end"]:
            regions["CDR2"].append(aa)
        elif IMGT_REGIONS["FR3"]["start"] <= pos <= IMGT_REGIONS["FR3"]["end"]:
            regions["FR3"].append(aa)
        elif IMGT_REGIONS["CDR3"]["start"] <= pos <= IMGT_REGIONS["CDR3"]["end"]:
            regions["CDR3"].append(aa)
        elif IMGT_REGIONS["FR4"]["start"] <= pos <= IMGT_REGIONS["FR4"]["end"]:
            regions["FR4"].append(aa)
    
    # 
    return {k: "".join(v) for k, v in regions.items()}


def main():
    print("=" * 80)
    print("Human IGHV (VH3) IMGTFR/CDR")
    print("=" * 80)
    
    print(f"\n[1] FASTA: {INPUT_FASTA}")
    print("-" * 80)
    
    if not INPUT_FASTA.exists():
        print(f"[ERROR] : {INPUT_FASTA}")
        return 1
    
    all_seqs = read_fasta(INPUT_FASTA)
    print(f"  : {len(all_seqs)}")
    
    # VH3（ID：M99652|IGHV3-11*01|...）
    vh3_seqs = {name: seq for name, seq in all_seqs.items() if "|IGHV3" in name}
    print(f"  VH3: {len(vh3_seqs)}")
    
    if not vh3_seqs:
        print("[ERROR] VH3")
        return 1
    
    # 
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 
    print(f"\n[2] IMGT")
    print("-" * 80)
    
    results = []
    success_count = 0
    failed_count = 0
    
    for i, (seq_id, seq) in enumerate(vh3_seqs.items(), 1):
        if i % 20 == 0:
            print(f"  : {i}/{len(vh3_seqs)}...", end="\r")
        
        try:
            # IMGT
            rows = imgt_number_anarcii(seq)
            pos_map = build_pos_to_aa_map(rows)
            
            # 
            regions = split_regions(rows)
            
            # FR2 hallmark（VHH-SAFE）
            hallmarks = {
                "aa37": pos_map.get(37, "-"),
                "aa44": pos_map.get(44, "-"),
                "aa45": pos_map.get(45, "-"),
                "aa47": pos_map.get(47, "-"),
            }
            
            result = {
                "id": seq_id,
                "original_sequence": seq,
                "length": len(seq),
                "numbering": rows,
                "pos_map": pos_map,
                "regions": regions,
                "hallmarks": hallmarks,
                "chain_type": rows[0].get("chain_type") if rows else None,
                "scheme": rows[0].get("scheme") if rows else None,
            }
            
            results.append(result)
            success_count += 1
            
        except IMGTNumberingError as e:
            print(f"\n  [WARN]  {seq_id[:50]}: {e}")
            failed_count += 1
        except Exception as e:
            print(f"\n  [ERROR]  {seq_id[:50]}: {e}")
            failed_count += 1
    
    print(f"\n  :  {success_count} ， {failed_count} ")
    
    # 
    print(f"\n[3] ")
    print("-" * 80)
    
    output_data = {
        "total_vh3": len(vh3_seqs),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results
    }
    
    OUTPUT_JSON.write_text(
        json.dumps(output_data, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    print(f"  [] JSON: {OUTPUT_JSON}")
    
    # 
    print(f"\n[4] ")
    print("-" * 80)
    
    if results:
        # 
        region_stats = {}
        for region_name in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]:
            lengths = [len(r["regions"][region_name]) for r in results]
            if lengths:
                region_stats[region_name] = {
                    "min": min(lengths),
                    "max": max(lengths),
                    "avg": sum(lengths) / len(lengths),
                }
        
        print("  :")
        for region_name, stats in region_stats.items():
            print(f"    {region_name}: {stats['min']}-{stats['max']}aa (: {stats['avg']:.1f}aa)")
        
        # Hallmark
        print("\n  FR2 Hallmark（Human VH3）:")
        from collections import Counter
        for pos in [37, 44, 45, 47]:
            aas = [r["hallmarks"][f"aa{pos}"] for r in results if r["hallmarks"][f"aa{pos}"] != "-"]
            if aas:
                aa_counts = Counter(aas)
                top_aa = aa_counts.most_common(3)
                print(f"    {pos}: {', '.join([f'{aa}({count})' for aa, count in top_aa])}")
    
    print(f"\n{'='*80}")
    print("！")
    print(f"{'='*80}")
    print(f"\n: {OUTPUT_JSON}")
    
    return 0


if __name__ == "__main__":
    exit(main())

