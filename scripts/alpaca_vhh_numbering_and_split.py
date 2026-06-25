#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
alpaca_vhh_numbering_and_split.py

ANARCIIVHHIMGTFR/CDR
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALPACA_DIR = PROJECT_ROOT / "data" / "germlines" / "vicugna_pacos_ig_aa"
FASTA_FILE = ALPACA_DIR / "IGHV_aa.fasta"
LABEL_FILE = ALPACA_DIR / "alpaca_ighv_vhh_label.tsv"
OUTPUT_DIR = ALPACA_DIR / "vhh_numbered"
OUTPUT_JSON = OUTPUT_DIR / "vhh_numbered_and_split.json"
OUTPUT_FASTA = OUTPUT_DIR / "vhh_numbered.fasta"
OUTPUT_SUMMARY = OUTPUT_DIR / "vhh_summary.tsv"

# IMGT（IMGT）
IMGT_REGIONS = {
    "FR1": {"start": 1, "end": 26},
    "CDR1": {"start": 27, "end": 38},
    "FR2": {"start": 39, "end": 55},
    "CDR2": {"start": 56, "end": 65},
    "FR3": {"start": 66, "end": 104},
    "CDR3": {"start": 105, "end": 117},
    "FR4": {"start": 118, "end": 128},
}


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


def read_vhh_labels(fp: Path) -> List[str]:
    """VHH，VHHID"""
    vhh_ids = []
    
    if not fp.exists():
        return vhh_ids
    
    with open(fp, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("label") == "VHH":
                vhh_ids.append(row.get("id", ""))
    
    return vhh_ids


def split_regions(rows: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    IMGTFRCDR
    
    Args:
        rows: imgt_number_anarcii
    
    Returns:
        ，
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
    print("VHHIMGTFR/CDR")
    print("=" * 80)
    
    # 
    try:
        import sys
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        
        from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map, IMGTNumberingError
    except ImportError as e:
        print(f"[ERROR] IMGT: {e}")
        print(" core/numbering/imgt_anarcii.py ")
        return 1
    
    # VHH
    print(f"\n[1] VHH: {LABEL_FILE}")
    print("-" * 80)
    vhh_ids = read_vhh_labels(LABEL_FILE)
    print(f"   {len(vhh_ids)} VHH")
    
    if not vhh_ids:
        print("[ERROR] VHH")
        return 1
    
    # FASTA
    print(f"\n[2] FASTA: {FASTA_FILE}")
    print("-" * 80)
    all_seqs = read_fasta(FASTA_FILE)
    print(f"  : {len(all_seqs)}")
    
    # VHH
    vhh_seqs = {}
    for vhh_id in vhh_ids:
        if vhh_id in all_seqs:
            vhh_seqs[vhh_id] = all_seqs[vhh_id]
        else:
            print(f"  [WARN] ID: {vhh_id[:50]}")
    
    print(f"   {len(vhh_seqs)} VHH")
    
    if not vhh_seqs:
        print("[ERROR] VHH")
        return 1
    
    # 
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # VHH
    print(f"\n[3] IMGT")
    print("-" * 80)
    
    results = []
    success_count = 0
    failed_count = 0
    
    for i, (seq_id, seq) in enumerate(vhh_seqs.items(), 1):
        if i % 10 == 0:
            print(f"  : {i}/{len(vhh_seqs)}...", end="\r")
        
        try:
            # IMGT
            rows = imgt_number_anarcii(seq)
            pos_map = build_pos_to_aa_map(rows)
            
            # 
            regions = split_regions(rows)
            
            # FR2 hallmark
            hallmarks = {
                "aa37": pos_map.get(37, "-"),
                "aa44": pos_map.get(44, "-"),
                "aa45": pos_map.get(45, "-"),
                "aa47": pos_map.get(47, "-"),
            }
            
            # VHH（）
            score = 0.0
            if hallmarks["aa44"] in ("Q", "E"):
                score += 1.0
            if hallmarks["aa45"] == "R":
                score += 1.0
            if hallmarks["aa47"] in ("G", "L"):
                score += 1.0
            if hallmarks["aa37"] in ("Y", "S", "N", "T", "H", "Q"):
                score += 0.5
            
            result = {
                "id": seq_id,
                "original_sequence": seq,
                "length": len(seq),
                "numbering": rows,
                "pos_map": pos_map,
                "regions": regions,
                "hallmarks": hallmarks,
                "vhh_score": score,
                "chain_type": rows[0].get("chain_type") if rows else None,
                "scheme": rows[0].get("scheme") if rows else None,
            }
            
            results.append(result)
            success_count += 1
            
        except IMGTNumberingError as e:
            print(f"\n  [ERROR]  {seq_id[:50]}: {e}")
            failed_count += 1
        except Exception as e:
            print(f"\n  [ERROR]  {seq_id[:50]}: {e}")
            failed_count += 1
    
    print(f"\n  :  {success_count} ， {failed_count} ")
    
    # JSON
    print(f"\n[4] ")
    print("-" * 80)
    
    output_data = {
        "total_vhh": len(vhh_seqs),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results
    }
    
    OUTPUT_JSON.write_text(
        json.dumps(output_data, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    print(f"  [] JSON: {OUTPUT_JSON}")
    
    # FASTA（）
    with OUTPUT_FASTA.open('w', encoding='utf-8') as f:
        for result in results:
            seq_id = result["id"]
            regions = result["regions"]
            
            # 
            f.write(f">{seq_id}|VHH|Full\n")
            f.write(f"{result['original_sequence']}\n")
            
            # 
            for region_name, region_seq in regions.items():
                if region_seq:
                    f.write(f">{seq_id}|VHH|{region_name}|{len(region_seq)}aa\n")
                    f.write(f"{region_seq}\n")
    
    print(f"  [] FASTA: {OUTPUT_FASTA}")
    
    # TSV
    with OUTPUT_SUMMARY.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "length", "vhh_score", "aa37", "aa44", "aa45", "aa47",
                       "FR1_len", "CDR1_len", "FR2_len", "CDR2_len", "FR3_len", "CDR3_len", "FR4_len"],
            delimiter="\t"
        )
        writer.writeheader()
        
        for result in results:
            regions = result["regions"]
            writer.writerow({
                "id": result["id"],
                "length": result["length"],
                "vhh_score": result["vhh_score"],
                "aa37": result["hallmarks"]["aa37"],
                "aa44": result["hallmarks"]["aa44"],
                "aa45": result["hallmarks"]["aa45"],
                "aa47": result["hallmarks"]["aa47"],
                "FR1_len": len(regions["FR1"]),
                "CDR1_len": len(regions["CDR1"]),
                "FR2_len": len(regions["FR2"]),
                "CDR2_len": len(regions["CDR2"]),
                "FR3_len": len(regions["FR3"]),
                "CDR3_len": len(regions["CDR3"]),
                "FR4_len": len(regions["FR4"]),
            })
    
    print(f"  [] TSV: {OUTPUT_SUMMARY}")
    
    # 
    print(f"\n[5] ")
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
        print("\n  FR2 Hallmark:")
        for pos in [37, 44, 45, 47]:
            aas = [r["hallmarks"][f"aa{pos}"] for r in results if r["hallmarks"][f"aa{pos}"] != "-"]
            from collections import Counter
            aa_counts = Counter(aas)
            top_aa = aa_counts.most_common(3)
            print(f"    {pos}: {', '.join([f'{aa}({count})' for aa, count in top_aa])}")
    
    print(f"\n{'='*80}")
    print("！")
    print(f"{'='*80}")
    print(f"\n: {OUTPUT_DIR}")
    print(f"  - JSON: {OUTPUT_JSON.name}")
    print(f"  - FASTA: {OUTPUT_FASTA.name}")
    print(f"  - TSV: {OUTPUT_SUMMARY.name}")
    
    return 0


if __name__ == "__main__":
    exit(main())


















