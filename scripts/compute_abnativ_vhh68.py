#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/compute_abnativ_vhh68.py
==================================
Computes AbNatiV scores for the 68 VHH sequences.
"""

import json
import os
import sys
import pandas as pd
from pathlib import Path
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

# Add suite root to path
SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE_ROOT))

# Import abnativ scoring
from abnativ.model.scoring_functions import abnativ_scoring

INDEX_PATH = SUITE_ROOT / "data" / "vhh_structural_union" / "vhh_structural_union_index.json"
OUT_PATH = SUITE_ROOT / "data" / "vhh_structural_union" / "abnativ_scores_vhh68.json"

def main():
    if not INDEX_PATH.exists():
        print(f"Error: {INDEX_PATH} not found.")
        return

    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    all_vhh = data.get("clinical_vhh", []) + data.get("database_b", [])
    
    seq_records = [
        SeqRecord(Seq(item["sequence"]), id=item["id"])
        for item in all_vhh
    ]
    
    print(f"Computing AbNatiV VHH2 scores for {len(all_vhh)} sequences...")
    
    # Run AbNatiV scoring
    # model_type="VHH2" uses the V2 VHH model
    df_mean, df_profile = abnativ_scoring(
        model_type="VHH2",
        seq_records=seq_records,
        batch_size=32,
        mean_score_only=True,
        do_align=True,
        is_VHH=True,
        verbose=True,
        run_parall_al=False
    )
    
    # Convert dataframe to dict
    # df_mean columns: seq_id, input_seq, aligned_seq, AbNatiV VHH2 Score, ...
    results = {}
    score_col = "AbNatiV VHH2 Score"
    for _, row in df_mean.iterrows():
        results[row["seq_id"]] = round(float(row[score_col]), 4)
        
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Done! Results saved to {OUT_PATH}")

if __name__ == "__main__":
    main()
