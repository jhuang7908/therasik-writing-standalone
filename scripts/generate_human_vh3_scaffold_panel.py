#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
generate_human_vh3_scaffold_panel.py

Human VH3，scaffold
VHH，IMGT
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_JSON = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_numbered" / "human_vh_numbered_and_split.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds"
OUTPUT_JSON = OUTPUT_DIR / "human_vh3_scaffolds.json"
OUTPUT_FASTA = OUTPUT_DIR / "human_vh3_scaffolds.fasta"

# （VHH）
IDENTITY_THRESHOLD = 0.90


def load_vh_segments(path: Path) -> List[Dict[str, Any]]:
    """Human VH，FR"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    
    # results
    records = []
    for rec in data.get("results", []):
        regions = rec.get("regions", {})
        fr1 = regions.get("FR1", "")
        fr2 = regions.get("FR2", "")
        fr3 = regions.get("FR3", "")
        fr4 = regions.get("FR4", "")
        
        # FR（FR4）
        if not (fr1 and fr2 and fr3):
            continue
        
        # 
        rec["_framework_full"] = fr1 + fr2 + fr3 + fr4
        rec["_fr1"] = fr1
        rec["_fr2"] = fr2
        rec["_fr3"] = fr3
        rec["_fr4"] = fr4
        
        records.append(rec)
    
    return records


def seq_identity(a: str, b: str) -> float:
    """
    ：。
    IMGT FR，。
    """
    if not a or not b:
        return 0.0
    
    L = min(len(a), len(b))
    if L == 0:
        return 0.0
    
    same = sum(1 for i in range(L) if a[i] == b[i])
    return same / L


def greedy_cluster(records: List[Dict[str, Any]], identity_threshold: float = 0.9) -> List[Dict[str, Any]]:
    """
    （VHH）
    """
    clusters = []
    if not records:
        return clusters
    
    # ，
    for idx, rec in enumerate(records):
        seq = rec.get("_framework_full", "")
        if not seq:
            continue
        
        if not clusters:
            clusters.append({"seed_idx": idx, "member_indices": [idx]})
            continue
        
        assigned = False
        for cluster in clusters:
            seed_idx = cluster["seed_idx"]
            seed_seq = records[seed_idx].get("_framework_full", "")
            
            if not seed_seq:
                continue
            
            ident = seq_identity(seq, seed_seq)
            if ident >= identity_threshold:
                cluster["member_indices"].append(idx)
                assigned = True
                break
        
        if not assigned:
            clusters.append({"seed_idx": idx, "member_indices": [idx]})
    
    return clusters


def consensus_from_segment(seqs: List[str]) -> str:
    """
    FR（VHH）
    """
    if not seqs:
        return ""
    
    # 
    seqs = [s for s in seqs if s]
    if not seqs:
        return ""
    
    max_len = max(len(s) for s in seqs)
    padded = [s.ljust(max_len, "-") for s in seqs]
    
    consensus_chars = []
    for i in range(max_len):
        col = [s[i] for s in padded]
        # gap
        col = [aa for aa in col if aa != "-"]
        if not col:
            consensus_chars.append("-")
            continue
        
        counter = Counter(col)
        aa, _ = counter.most_common(1)[0]
        consensus_chars.append(aa)
    
    # '-'
    return "".join(consensus_chars).rstrip("-")


def build_scaffold_panel(records: List[Dict[str, Any]], clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    scaffold（VHH）
    """
    scaffolds = []
    
    for i, cluster in enumerate(clusters, start=1):
        member_indices = cluster["member_indices"]
        members = [records[idx] for idx in member_indices]
        
        fr1_seqs = [m.get("_fr1", "") for m in members]
        fr2_seqs = [m.get("_fr2", "") for m in members]
        fr3_seqs = [m.get("_fr3", "") for m in members]
        fr4_seqs = [m.get("_fr4", "") for m in members]
        
        c_fr1 = consensus_from_segment(fr1_seqs)
        c_fr2 = consensus_from_segment(fr2_seqs)
        c_fr3 = consensus_from_segment(fr3_seqs)
        c_fr4 = consensus_from_segment(fr4_seqs)
        
        scaffold_id = f"HUMAN_VH3_SCF_{i:02d}"
        member_ids = [records[idx].get("id", f"idx_{idx}") for idx in member_indices]
        
        scaffolds.append({
            "scaffold_id": scaffold_id,
            "n_members": len(member_indices),
            "member_ids": member_ids,
            "consensus": {
                "fr1": c_fr1,
                "fr2": c_fr2,
                "fr3": c_fr3,
                "fr4": c_fr4,
                "framework_full": c_fr1 + c_fr2 + c_fr3 + c_fr4
            }
        })
    
    return scaffolds


def write_scaffolds_json(scaffolds: List[Dict[str, Any]], path: Path):
    """JSON"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scaffolds, f, indent=2, ensure_ascii=False)


def write_scaffolds_fasta(scaffolds: List[Dict[str, Any]], path: Path):
    """FASTA"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for scaf in scaffolds:
            sid = scaf["scaffold_id"]
            n = scaf["n_members"]
            fr1 = scaf["consensus"]["fr1"]
            fr2 = scaf["consensus"]["fr2"]
            fr3 = scaf["consensus"]["fr3"]
            fr4 = scaf["consensus"]["fr4"]
            full = scaf["consensus"]["framework_full"]
            
            header = (
                f">{sid} | n_members={n} | "
                f"fr_len=({len(fr1)},{len(fr2)},{len(fr3)},{len(fr4)})"
            )
            f.write(header + "\n")
            
            # wrap，60aa
            for i in range(0, len(full), 60):
                f.write(full[i:i+60] + "\n")


def main():
    print("=" * 80)
    print("Human VH3Scaffold")
    print("=" * 80)
    
    print(f"\n[1] VH: {INPUT_JSON}")
    print("-" * 80)
    
    if not INPUT_JSON.exists():
        print(f"[ERROR] : {INPUT_JSON}")
        return 1
    
    records = load_vh_segments(INPUT_JSON)
    print(f"  : {len(records)}")
    
    if not records:
        print("[ERROR] ")
        return 1
    
    print(f"\n[2]  {IDENTITY_THRESHOLD:.2f} ...")
    print("-" * 80)
    
    clusters = greedy_cluster(records, identity_threshold=IDENTITY_THRESHOLD)
    print(f"  : {len(clusters)} scaffold cluster")
    
    # cluster
    cluster_sizes = [len(c["member_indices"]) for c in clusters]
    print(f"  Cluster: ={min(cluster_sizes)}, ={max(cluster_sizes)}, ={sum(cluster_sizes)/len(cluster_sizes):.1f}")
    
    print(f"\n[3] scaffold...")
    print("-" * 80)
    
    scaffolds = build_scaffold_panel(records, clusters)
    
    print(f"   {len(scaffolds)} scaffold")
    
    print(f"\n[4] ")
    print("-" * 80)
    
    print(f"  [] JSON: {OUTPUT_JSON}")
    write_scaffolds_json(scaffolds, OUTPUT_JSON)
    
    print(f"  [] FASTA: {OUTPUT_FASTA}")
    write_scaffolds_fasta(scaffolds, OUTPUT_FASTA)
    
    # scaffold
    print(f"\n[5] Scaffold（5）")
    print("-" * 80)
    for scaf in scaffolds[:5]:
        sid = scaf["scaffold_id"]
        n = scaf["n_members"]
        full = scaf["consensus"]["framework_full"]
        print(f"  {sid}: {n}, ={len(full)}aa")
        print(f"    : {full[:50]}...")
    
    print(f"\n{'='*80}")
    print("Human VH3 scaffold panel！")
    print(f"{'='*80}")
    print(f"\n: {OUTPUT_DIR}")
    print(f"  - JSON: {OUTPUT_JSON.name}")
    print(f"  - FASTA: {OUTPUT_FASTA.name}")
    
    return 0


if __name__ == "__main__":
    exit(main())


















