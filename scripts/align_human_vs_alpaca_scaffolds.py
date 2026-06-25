#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
align_human_vs_alpaca_scaffolds.py

Human VH3 VHH-SAFEVHH scaffoldFR
identity、similarity、hydrophobicity mismatch、VHH hallmark
"""

from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 
HUMAN_TEMPLATES = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds" / "human_vh3_vhh_safe_templates.json"
ALPACA_SCAFFOLDS = PROJECT_ROOT / "data" / "germlines" / "vicugna_pacos_ig_aa" / "vhh_scaffolds" / "vhh_scaffolds.json"

# 
OUTPUT_DIR = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds"
OUTPUT_TSV = OUTPUT_DIR / "human_vs_alpaca_scaffold_alignment.tsv"
OUTPUT_JSON = OUTPUT_DIR / "human_vs_alpaca_scaffold_alignment.json"

# （BLOSUM62，）
AA_SIMILARITY = {
    # 
    "A": {"A": 1.0, "V": 0.8, "L": 0.7, "I": 0.7, "M": 0.6, "F": 0.5, "W": 0.4, "P": 0.5},
    "V": {"A": 0.8, "V": 1.0, "L": 0.9, "I": 0.9, "M": 0.7, "F": 0.5, "W": 0.3, "P": 0.4},
    "L": {"A": 0.7, "V": 0.9, "L": 1.0, "I": 0.9, "M": 0.8, "F": 0.7, "W": 0.5, "P": 0.5},
    "I": {"A": 0.7, "V": 0.9, "L": 0.9, "I": 1.0, "M": 0.8, "F": 0.6, "W": 0.4, "P": 0.4},
    "M": {"A": 0.6, "V": 0.7, "L": 0.8, "I": 0.8, "M": 1.0, "F": 0.6, "W": 0.5, "P": 0.4},
    "F": {"A": 0.5, "V": 0.5, "L": 0.7, "I": 0.6, "M": 0.6, "F": 1.0, "W": 0.7, "P": 0.4},
    "W": {"A": 0.4, "V": 0.3, "L": 0.5, "I": 0.4, "M": 0.5, "F": 0.7, "W": 1.0, "P": 0.3},
    "P": {"A": 0.5, "V": 0.4, "L": 0.5, "I": 0.4, "M": 0.4, "F": 0.4, "W": 0.3, "P": 1.0},
    # 
    "D": {"D": 1.0, "E": 0.8, "N": 0.6, "Q": 0.5, "K": 0.4, "R": 0.3, "H": 0.5, "S": 0.4, "T": 0.4, "Y": 0.3},
    "E": {"D": 0.8, "E": 1.0, "N": 0.5, "Q": 0.7, "K": 0.5, "R": 0.4, "H": 0.4, "S": 0.3, "T": 0.3, "Y": 0.2},
    "N": {"D": 0.6, "E": 0.5, "N": 1.0, "Q": 0.7, "K": 0.4, "R": 0.3, "H": 0.6, "S": 0.6, "T": 0.6, "Y": 0.5},
    "Q": {"D": 0.5, "E": 0.7, "N": 0.7, "Q": 1.0, "K": 0.6, "R": 0.5, "H": 0.7, "S": 0.5, "T": 0.5, "Y": 0.4},
    "K": {"D": 0.4, "E": 0.5, "N": 0.4, "Q": 0.6, "K": 1.0, "R": 0.7, "H": 0.5, "S": 0.4, "T": 0.4, "Y": 0.3},
    "R": {"D": 0.3, "E": 0.4, "N": 0.3, "Q": 0.5, "K": 0.7, "R": 1.0, "H": 0.6, "S": 0.3, "T": 0.3, "Y": 0.2},
    "H": {"D": 0.5, "E": 0.4, "N": 0.6, "Q": 0.7, "K": 0.5, "R": 0.6, "H": 1.0, "S": 0.5, "T": 0.5, "Y": 0.6},
    "S": {"D": 0.4, "E": 0.3, "N": 0.6, "Q": 0.5, "K": 0.4, "R": 0.3, "H": 0.5, "S": 1.0, "T": 0.8, "Y": 0.7},
    "T": {"D": 0.4, "E": 0.3, "N": 0.6, "Q": 0.5, "K": 0.4, "R": 0.3, "H": 0.5, "S": 0.8, "T": 1.0, "Y": 0.6},
    "Y": {"D": 0.3, "E": 0.2, "N": 0.5, "Q": 0.4, "K": 0.3, "R": 0.2, "H": 0.6, "S": 0.7, "T": 0.6, "Y": 1.0},
    # 
    "G": {"G": 1.0, "A": 0.5, "S": 0.5, "T": 0.4},
    "C": {"C": 1.0, "S": 0.3},
}

# 
HYDROPHOBIC = {"A", "V", "L", "I", "M", "F", "W", "P", "C"}
HYDROPHILIC = {"D", "E", "N", "Q", "K", "R", "H", "S", "T", "Y", "G"}


def get_aa_similarity(aa1: str, aa2: str) -> float:
    """"""
    if aa1 == aa2:
        return 1.0
    
    if aa1 in AA_SIMILARITY and aa2 in AA_SIMILARITY[aa1]:
        return AA_SIMILARITY[aa1][aa2]
    if aa2 in AA_SIMILARITY and aa1 in AA_SIMILARITY[aa2]:
        return AA_SIMILARITY[aa2][aa1]
    
    return 0.0


def seq_identity(a: str, b: str) -> float:
    """identity（）"""
    if not a or not b:
        return 0.0
    
    L = min(len(a), len(b))
    if L == 0:
        return 0.0
    
    same = sum(1 for i in range(L) if a[i] == b[i])
    return same / L


def seq_similarity(a: str, b: str) -> float:
    """similarity（）"""
    if not a or not b:
        return 0.0
    
    L = min(len(a), len(b))
    if L == 0:
        return 0.0
    
    total_score = sum(get_aa_similarity(a[i], b[i]) for i in range(L))
    return total_score / L


def hydrophobicity_mismatch(a: str, b: str) -> float:
    """（0-1，0）"""
    if not a or not b:
        return 1.0
    
    L = min(len(a), len(b))
    if L == 0:
        return 1.0
    
    mismatches = 0
    for i in range(L):
        aa1, aa2 = a[i], b[i]
        if aa1 in HYDROPHOBIC and aa2 in HYDROPHILIC:
            mismatches += 1
        elif aa1 in HYDROPHILIC and aa2 in HYDROPHOBIC:
            mismatches += 1
    
    return mismatches / L


def vhh_hallmark_compatibility(human_fr2: str, alpaca_fr2: str) -> Tuple[float, Dict[int, str]]:
    """
    VHH hallmark
    
    Returns:
        (, {: })
    """
    # VHH hallmark：37, 44, 45, 47
    # FR2
    # FR2IMGT 39-55，：
    # 37FR2 = 37 - 39 = -2（FR2，FR1）
    # 44FR2 = 44 - 39 = 5
    # 45FR2 = 45 - 39 = 6
    # 47FR2 = 47 - 39 = 8
    
    # ，
    # ：FR217aa，44/45/47FR2
    
    # ：
    # 
    
    compatibility = {}
    score = 0.0
    
    # VHH hallmark：37=Y, 44=Q, 45=R, 47=G
    ideal = {37: "Y", 44: "Q", 45: "R", 47: "G"}
    
    # FR2，37
    # 44、45、47
    # FR239，：
    # 44 = FR2[5] (0-indexed)
    # 45 = FR2[6]
    # 47 = FR2[8]
    
    check_positions = {44: 5, 45: 6, 47: 8}
    
    for pos, idx in check_positions.items():
        if idx < len(human_fr2) and idx < len(alpaca_fr2):
            human_aa = human_fr2[idx]
            alpaca_aa = alpaca_fr2[idx]
            ideal_aa = ideal.get(pos, "")
            
            if human_aa == ideal_aa:
                compatibility[pos] = "match"
                score += 1.0
            elif human_aa in ("Q", "E") and pos == 44:
                compatibility[pos] = "compatible"
                score += 0.8
            elif human_aa == "R" and pos == 45:
                compatibility[pos] = "compatible"
                score += 0.8
            elif human_aa == "G" and pos == 47:
                compatibility[pos] = "compatible"
                score += 0.8
            else:
                compatibility[pos] = "mismatch"
    
    # 0-1
    max_score = len(check_positions)
    normalized_score = score / max_score if max_score > 0 else 0.0
    
    return normalized_score, compatibility


def align_scaffolds(human_templates: List[Dict[str, Any]], alpaca_scaffolds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Humanscaffold，
    """
    alignments = []
    
    for human_template in human_templates:
        human_id = human_template["template_id"]
        human_consensus = human_template["consensus"]
        human_fr1 = human_consensus["fr1"]
        human_fr2 = human_consensus["fr2"]
        human_fr3 = human_consensus["fr3"]
        human_framework = human_consensus["framework_full"]
        
        for alpaca_scaffold in alpaca_scaffolds:
            alpaca_id = alpaca_scaffold["scaffold_id"]
            alpaca_consensus = alpaca_scaffold["consensus"]
            alpaca_fr1 = alpaca_consensus["fr1"]
            alpaca_fr2 = alpaca_consensus["fr2"]
            alpaca_fr3 = alpaca_consensus["fr3"]
            alpaca_framework = alpaca_consensus["framework_full"]
            
            # FR1-3identity
            fr1_identity = seq_identity(human_fr1, alpaca_fr1)
            fr2_identity = seq_identity(human_fr2, alpaca_fr2)
            fr3_identity = seq_identity(human_fr3, alpaca_fr3)
            framework_identity = seq_identity(human_framework, alpaca_framework)
            
            # similarity
            fr1_similarity = seq_similarity(human_fr1, alpaca_fr1)
            fr2_similarity = seq_similarity(human_fr2, alpaca_fr2)
            fr3_similarity = seq_similarity(human_fr3, alpaca_fr3)
            framework_similarity = seq_similarity(human_framework, alpaca_framework)
            
            # 
            fr2_hydro_mismatch = hydrophobicity_mismatch(human_fr2, alpaca_fr2)
            
            # VHH hallmark
            hallmark_score, hallmark_compat = vhh_hallmark_compatibility(human_fr2, alpaca_fr2)
            
            alignment = {
                "human_template": human_id,
                "alpaca_scaffold": alpaca_id,
                "human_plan": human_template.get("safe_plan", ""),
                "human_n_members": human_template.get("n_members", 0),
                "alpaca_n_members": alpaca_scaffold.get("n_members", 0),
                "fr1_identity": round(fr1_identity, 3),
                "fr2_identity": round(fr2_identity, 3),
                "fr3_identity": round(fr3_identity, 3),
                "framework_identity": round(framework_identity, 3),
                "fr1_similarity": round(fr1_similarity, 3),
                "fr2_similarity": round(fr2_similarity, 3),
                "fr3_similarity": round(fr3_similarity, 3),
                "framework_similarity": round(framework_similarity, 3),
                "fr2_hydrophobicity_mismatch": round(fr2_hydro_mismatch, 3),
                "vhh_hallmark_score": round(hallmark_score, 3),
                "vhh_hallmark_compatibility": hallmark_compat
            }
            
            alignments.append(alignment)
    
    return alignments


def write_tsv(alignments: List[Dict[str, Any]], path: Path):
    """TSV"""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = [
        "human_template", "alpaca_scaffold", "human_plan",
        "framework_identity", "framework_similarity",
        "fr1_identity", "fr2_identity", "fr3_identity",
        "fr2_hydrophobicity_mismatch", "vhh_hallmark_score"
    ]
    
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        
        for align in alignments:
            row = {k: align.get(k, "") for k in fieldnames}
            writer.writerow(row)


def main():
    print("=" * 80)
    print("Human VH3 VHH-SAFE vs VHH Scaffold")
    print("=" * 80)
    
    print(f"\n[1] Human VH3 VHH-SAFE: {HUMAN_TEMPLATES}")
    print("-" * 80)
    
    if not HUMAN_TEMPLATES.exists():
        print(f"[ERROR] : {HUMAN_TEMPLATES}")
        return 1
    
    with open(HUMAN_TEMPLATES, encoding="utf-8") as f:
        human_templates = json.load(f)
    
    print(f"  Human: {len(human_templates)}")
    
    print(f"\n[2] VHH scaffolds: {ALPACA_SCAFFOLDS}")
    print("-" * 80)
    
    if not ALPACA_SCAFFOLDS.exists():
        print(f"[ERROR] : {ALPACA_SCAFFOLDS}")
        return 1
    
    with open(ALPACA_SCAFFOLDS, encoding="utf-8") as f:
        alpaca_scaffolds = json.load(f)
    
    print(f"  scaffold: {len(alpaca_scaffolds)}")
    
    print(f"\n[3] ...")
    print("-" * 80)
    
    alignments = align_scaffolds(human_templates, alpaca_scaffolds)
    
    print(f"  : {len(alignments)} ({len(human_templates)} × {len(alpaca_scaffolds)})")
    
    # 
    if alignments:
        best_identity = max(alignments, key=lambda x: x["framework_identity"])
        best_similarity = max(alignments, key=lambda x: x["framework_similarity"])
        best_hallmark = max(alignments, key=lambda x: x["vhh_hallmark_score"])
        
        print(f"\n  identity:")
        print(f"    {best_identity['human_template']} vs {best_identity['alpaca_scaffold']}: {best_identity['framework_identity']:.1%}")
        print(f"\n  similarity:")
        print(f"    {best_similarity['human_template']} vs {best_similarity['alpaca_scaffold']}: {best_similarity['framework_similarity']:.1%}")
        print(f"\n  hallmark:")
        print(f"    {best_hallmark['human_template']} vs {best_hallmark['alpaca_scaffold']}: {best_hallmark['vhh_hallmark_score']:.1%}")
    
    print(f"\n[4] ")
    print("-" * 80)
    
    print(f"  [] TSV: {OUTPUT_TSV}")
    write_tsv(alignments, OUTPUT_TSV)
    
    print(f"  [] JSON: {OUTPUT_JSON}")
    OUTPUT_JSON.write_text(
        json.dumps(alignments, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    print(f"\n{'='*80}")
    print("！")
    print(f"{'='*80}")
    print(f"\n: {OUTPUT_DIR}")
    print(f"  - TSV: {OUTPUT_TSV.name}")
    print(f"  - JSON: {OUTPUT_JSON.name}")
    
    return 0


if __name__ == "__main__":
    exit(main())


















