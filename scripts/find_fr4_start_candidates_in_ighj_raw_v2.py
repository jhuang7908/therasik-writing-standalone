#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 IGHJ raw  FR4 （ motif +  + ）

 IGHJ ， motif  FR4 。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_ighj_raw(json_path: Path) -> Dict[str, Dict[str, str]]:
    """ IGHJ raw JSON"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_fr4_candidates(ighj_aa: str) -> List[Dict[str, any]]:
    """
     IGHJ  FR4 
    
    Returns:
        [{
            "tier": int,
            "candidate_idx": int,
            "motif_4aa": str,
            "fr4_11aa": str,
        }, ...]
    """
    candidates = []
    
    # Tier1: WGQG
    for match in re.finditer(r'WGQG', ighj_aa):
        idx = match.start()
        if idx + 11 <= len(ighj_aa):
            candidates.append({
                "tier": 1,
                "candidate_idx": idx,
                "motif_4aa": "WGQG",
                "fr4_11aa": ighj_aa[idx:idx+11],
            })
    
    # Tier2: WGRG
    for match in re.finditer(r'WGRG', ighj_aa):
        idx = match.start()
        if idx + 11 <= len(ighj_aa):
            candidates.append({
                "tier": 2,
                "candidate_idx": idx,
                "motif_4aa": "WGRG",
                "fr4_11aa": ighj_aa[idx:idx+11],
            })
    
    # Tier3: WG[QERK]G
    for match in re.finditer(r'WG[QERK]G', ighj_aa):
        idx = match.start()
        motif = match.group(0)
        if idx + 11 <= len(ighj_aa):
            candidates.append({
                "tier": 3,
                "candidate_idx": idx,
                "motif_4aa": motif,
                "fr4_11aa": ighj_aa[idx:idx+11],
            })
    
    # Tier4: [FW]G.G（F/W-G-X-G）
    for match in re.finditer(r'[FW]G.G', ighj_aa):
        idx = match.start()
        motif = match.group(0)
        if idx + 11 <= len(ighj_aa):
            candidates.append({
                "tier": 4,
                "candidate_idx": idx,
                "motif_4aa": motif,
                "fr4_11aa": ighj_aa[idx:idx+11],
            })
    
    # ：， tier（tier ）
    # ，key  candidate_idx，value （ tier ）
    idx_to_candidate = {}
    for cand in candidates:
        idx = cand["candidate_idx"]
        if idx not in idx_to_candidate:
            idx_to_candidate[idx] = cand
        else:
            # ， tier， tier （）
            if cand["tier"] < idx_to_candidate[idx]["tier"]:
                idx_to_candidate[idx] = cand
    
    unique_candidates = list(idx_to_candidate.values())
    
    #  tier ， candidate_idx 
    unique_candidates.sort(key=lambda x: (x["tier"], x["candidate_idx"]))
    
    return unique_candidates


def select_best_candidate(candidates: List[Dict[str, any]]) -> Tuple[Optional[Dict[str, any]], str]:
    """
    
    
    Returns:
        (best_candidate, status)
        status: "PASS_HAS_CANDIDATE" | "NO_CANDIDATE" | "MULTI_BEST_TIE"
    """
    if not candidates:
        return None, "NO_CANDIDATE"
    
    #  tier （tier ）， candidate_idx 
    candidates_sorted = sorted(candidates, key=lambda x: (x["tier"], x["candidate_idx"]))
    
    #  tier
    best_tier = candidates_sorted[0]["tier"]
    
    #  tier 
    best_tier_candidates = [c for c in candidates_sorted if c["tier"] == best_tier]
    
    if len(best_tier_candidates) == 1:
        return best_tier_candidates[0], "PASS_HAS_CANDIDATE"
    else:
        #  tier  idx（，）
        #  idx，； TIE
        if len(set(c["candidate_idx"] for c in best_tier_candidates)) == 1:
            return best_tier_candidates[0], "PASS_HAS_CANDIDATE"
        else:
            # ，（idx ）
            best = min(best_tier_candidates, key=lambda x: x["candidate_idx"])
            #  tier  idx
            other_best = [c for c in best_tier_candidates if c["candidate_idx"] != best["candidate_idx"]]
            if other_best:
                return best, "MULTI_BEST_TIE"
            else:
                return best, "PASS_HAS_CANDIDATE"


def main():
    parser = argparse.ArgumentParser(
        description=" IGHJ raw  FR4 "
    )
    parser.add_argument(
        "--ighj_json",
        type=Path,
        default=PROJECT_ROOT / "data" / "ighj_aa_raw.json",
        help="IGHJ raw JSON ",
    )
    parser.add_argument(
        "--out_dir",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="",
    )
    parser.add_argument(
        "--json_out",
        type=Path,
        default=PROJECT_ROOT / "data" / "ighj_fr4_candidates_v2.json",
        help=" JSON ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" IGHJ raw  FR4 （v2）")
    print("=" * 80)
    print()
    
    #  IGHJ raw
    ighj_json_path = Path(args.ighj_json)
    if not ighj_json_path.is_absolute():
        ighj_json_path = PROJECT_ROOT / ighj_json_path
    
    if not ighj_json_path.exists():
        print(f"❌ IGHJ JSON : {ighj_json_path}")
        return
    
    print(f"[1/4]  IGHJ raw: {ighj_json_path}")
    ighj_data = load_ighj_raw(ighj_json_path)
    print(f"  ✅  {len(ighj_data)}  IGHJ ")
    print()
    
    # 
    print(f"[2/4]  FR4 ...")
    all_candidates_detail = []  # 
    summary_data = []  # 
    json_data = {}  # JSON 
    
    for ighj_id, ighj_entry in sorted(ighj_data.items()):
        gene = ighj_entry.get("gene", "")
        allele = ighj_entry.get("allele", "")
        ighj_aa = ighj_entry.get("aa", "")
        
        if not ighj_aa:
            print(f"  ⚠️   {ighj_id}: ")
            continue
        
        # 
        candidates = find_fr4_candidates(ighj_aa)
        
        # 
        best_candidate, status = select_best_candidate(candidates)
        
        # 
        for cand in candidates:
            all_candidates_detail.append({
                "ighj_id": ighj_id,
                "gene": gene,
                "allele": allele,
                "aa_len": len(ighj_aa),
                "tier": cand["tier"],
                "candidate_idx": cand["candidate_idx"],
                "motif_4aa": cand["motif_4aa"],
                "fr4_11aa": cand["fr4_11aa"],
            })
        
        # 
        if best_candidate:
            summary_data.append({
                "ighj_id": ighj_id,
                "aa_len": len(ighj_aa),
                "n_candidates": len(candidates),
                "best_tier": best_candidate["tier"],
                "best_idx": best_candidate["candidate_idx"],
                "best_motif_4aa": best_candidate["motif_4aa"],
                "best_fr4_11aa": best_candidate["fr4_11aa"],
                "status": status,
            })
        else:
            summary_data.append({
                "ighj_id": ighj_id,
                "aa_len": len(ighj_aa),
                "n_candidates": 0,
                "best_tier": None,
                "best_idx": None,
                "best_motif_4aa": "",
                "best_fr4_11aa": "",
                "status": status,
            })
        
        # JSON 
        json_data[ighj_id] = {
            "gene": gene,
            "allele": allele,
            "aa": ighj_aa,
            "aa_len": len(ighj_aa),
            "n_candidates": len(candidates),
            "all_candidates": candidates,
            "best": best_candidate,
            "status": status,
        }
        
        # 
        if candidates:
            print(f"  ✅ {ighj_id}: {len(candidates)} , best_tier={best_candidate['tier'] if best_candidate else 'N/A'}, status={status}")
        else:
            print(f"  ❌ {ighj_id}: ")
    
    print()
    
    # 
    total_candidates = len(all_candidates_detail)
    pass_count = sum(1 for s in summary_data if s["status"] == "PASS_HAS_CANDIDATE")
    no_candidate_count = sum(1 for s in summary_data if s["status"] == "NO_CANDIDATE")
    tie_count = sum(1 for s in summary_data if s["status"] == "MULTI_BEST_TIE")
    
    print("=" * 80)
    print("")
    print("=" * 80)
    print(f": {total_candidates}")
    print(f"✅ PASS_HAS_CANDIDATE: {pass_count} ")
    print(f"❌ NO_CANDIDATE: {no_candidate_count} ")
    print(f"⚠️  MULTI_BEST_TIE: {tie_count} ")
    print()
    
    # 
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    #  1:  CSV
    detail_csv = args.out_dir / "ighj_fr4_candidates_v2.csv"
    with open(detail_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "ighj_id", "gene", "allele", "aa_len", "tier", "candidate_idx",
            "motif_4aa", "fr4_11aa"
        ])
        writer.writeheader()
        for row in all_candidates_detail:
            writer.writerow(row)
    print(f"✅ : {detail_csv}")
    
    #  2:  CSV
    summary_csv = args.out_dir / "ighj_fr4_candidates_summary_v2.csv"
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "ighj_id", "aa_len", "n_candidates", "best_tier", "best_idx",
            "best_motif_4aa", "best_fr4_11aa", "status"
        ])
        writer.writeheader()
        for row in summary_data:
            writer.writerow({
                "ighj_id": row["ighj_id"],
                "aa_len": row["aa_len"],
                "n_candidates": row["n_candidates"],
                "best_tier": row["best_tier"] if row["best_tier"] is not None else "",
                "best_idx": row["best_idx"] if row["best_idx"] is not None else "",
                "best_motif_4aa": row["best_motif_4aa"],
                "best_fr4_11aa": row["best_fr4_11aa"],
                "status": row["status"],
            })
    print(f"✅ : {summary_csv}")
    
    #  3: JSON
    json_out_path = Path(args.json_out)
    if not json_out_path.is_absolute():
        json_out_path = PROJECT_ROOT / json_out_path
    
    json_out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON : {json_out_path}")
    
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()

