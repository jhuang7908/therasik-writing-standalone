import pandas as pd
import json
import os
import csv
from collections import defaultdict
import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite")
sys.path.insert(0, str(PROJECT_ROOT))

from core.numbering.imgt_anarcii import imgt_number_anarcii

# Paths
slice3_numbering_path = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "anarcii_numbering_slice_3_vhh_design.parquet"
cdr1_summary_path = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "clusters" / "cdr1_cluster_summary.csv"
cdr2_summary_path = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "clusters" / "cdr2_cluster_summary.csv"

def extract_cdrs_v2(sequence):
    """Run internal imgt_number_anarcii and extract IMGT CDRs."""
    try:
        rows = imgt_number_anarcii(sequence)
        
        def get_range(start, end):
            seq = ""
            for r in rows:
                if start <= r["pos"] <= end:
                    seq += r["aa"]
            return seq

        cdr1 = get_range(27, 38)
        cdr2 = get_range(56, 65)
        cdr3 = get_range(105, 117)
        return cdr1, cdr2, cdr3
    except Exception as e:
        print(f"Error numbering: {e}")
        return None, None, None

def calculate_identity(seq1, seq2):
    if not seq1 or not seq2 or len(seq1) != len(seq2):
        return 0.0
    matches = sum(1 for a, b in zip(seq1, seq2) if a == b)
    return matches / len(seq1)

def run_slice3_cdr_canonical():
    # 1. Load Cluster Summaries
    print("Loading cluster summaries...")
    cdr_refs = {"CDR1": [], "CDR2": []}
    for cdr_name, path in [("CDR1", cdr1_summary_path), ("CDR2", cdr2_summary_path)]:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cdr_refs[cdr_name].append({
                    "cluster_id": row["cluster_id"],
                    "length": int(row["length"]),
                    "representative": row["representative"],
                    "proxy_score": float(row["proxy_score"]),
                    "percentile": float(row["cluster_percentile"])
                })

    # 2. Load Slice 3 Sequences
    print("Loading Slice 3 sequences...")
    df = pd.read_parquet(slice3_numbering_path)
    
    results = []
    
    print(f"{'Antibody ID':<15} | {'CDR1 Cluster':<12} | {'CDR1 Score':<10} | {'CDR2 Cluster':<12} | {'CDR2 Score':<10}")
    print("-" * 75)
    
    for _, row in df.iterrows():
        ab_id = row['antibody_id']
        seq = row['vh_sequence']
        if not seq: continue
        
        cdr1, cdr2, cdr3 = extract_cdrs_v2(seq)
        
        if not cdr1 or not cdr2:
            print(f"{ab_id:<15} | {'ERROR':<12} | {'-':<10} | {'ERROR':<12} | {'-'}")
            continue
            
        # Match CDR1
        best_cdr1 = {"id": "unknown", "score": 0.0}
        max_id1 = -1
        for ref in cdr_refs["CDR1"]:
            if ref["length"] == len(cdr1):
                identity = calculate_identity(cdr1, ref["representative"])
                if identity > max_id1:
                    max_id1 = identity
                    score = round(0.6 * ref["percentile"] + 0.4 * identity, 4)
                    best_cdr1 = {"id": ref["cluster_id"], "score": score}
        
        # Match CDR2
        best_cdr2 = {"id": "unknown", "score": 0.0}
        max_id2 = -1
        for ref in cdr_refs["CDR2"]:
            if ref["length"] == len(cdr2):
                identity = calculate_identity(cdr2, ref["representative"])
                if identity > max_id2:
                    max_id2 = identity
                    score = round(0.6 * ref["percentile"] + 0.4 * identity, 4)
                    best_cdr2 = {"id": ref["cluster_id"], "score": score}
                    
        print(f"{ab_id:<15} | {best_cdr1['id']:<12} | {best_cdr1['score']:<10.4f} | {best_cdr2['id']:<12} | {best_cdr2['score']:<10.4f}")
        
        results.append({
            "antibody_id": ab_id,
            "cdr1": cdr1,
            "cdr2": cdr2,
            "cdr3": cdr3,
            "cdr1_cluster": best_cdr1["id"],
            "cdr1_score": best_cdr1["score"],
            "cdr2_cluster": best_cdr2["id"],
            "cdr2_score": best_cdr2["score"]
        })

    # Save to JSON
    output_path = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "slice3_vhh_canonical_config.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")

if __name__ == "__main__":
    run_slice3_cdr_canonical()
