import os
import sys
import json
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

AUTONOMOUS_JSON = ROOT / "data/sabdab_vhh_atlas/autonomous_human_vh_db.json"
MASTER_SEQ_LIST = ROOT / "data/vhh_master_seq_list.csv"
BENCHMARK_V2 = ROOT / "data/vhh_master_benchmarks_v2.csv"
BENCHMARK_V3 = ROOT / "data/vhh_master_benchmarks_v3.csv"

def extract_vh_domain(sequence):
    """Use ANARCI to extract the VH domain from a sequence (removing signal peptides)."""
    try:
        from anarcii import Anarcii
        a = Anarcii(seq_type="antibody", mode="accuracy")
        res = a.number([sequence])
        if isinstance(res, dict) and 'Sequence 1' in res:
            v = res['Sequence 1']
            if isinstance(v, dict) and 'numbering' in v and v['numbering']:
                numbering = v['numbering']
                vh_seq = "".join([aa for _, aa in numbering if aa != "-"])
                return vh_seq
    except Exception as e:
        print(f"Error extracting VH domain: {e}")
    return None

def main():
    # 1. Load autonomous VH data
    with open(AUTONOMOUS_JSON, "r", encoding="utf-8") as f:
        auto_data = json.load(f)
    
    print(f"Loaded {len(auto_data)} autonomous VH entries.")
    
    # 2. Extract unique sequences
    unique_seqs = {}
    for entry in auto_data:
        pdb = entry.get("pdb")
        chain = entry.get("chain")
        seq_id = f"{pdb}_{chain}"
        raw_seq = entry.get("sequence")
        
        if raw_seq not in unique_seqs.values():
            unique_seqs[seq_id] = raw_seq

    print(f"Found {len(unique_seqs)} unique autonomous VH sequences.")

    # 3. Add to master sequence list
    df_master = pd.read_csv(MASTER_SEQ_LIST)
    
    new_entries = []
    for seq_id, raw_seq in tqdm(unique_seqs.items(), desc="Processing autonomous VH"):
        # Check if already in master
        if seq_id in df_master["id"].values:
            continue
            
        vh_seq = extract_vh_domain(raw_seq)
        if not vh_seq:
            continue
            
        new_entries.append({
            "id": seq_id,
            "sequence": vh_seq,
            "pdb_path": None, # Will predict later
            "category": "Autonomous_Human_VH",
            "source": "Database_A"
        })
    
    if new_entries:
        df_new = pd.DataFrame(new_entries)
        df_master = pd.concat([df_master, df_new], ignore_index=True)
        df_master.to_csv(MASTER_SEQ_LIST, index=False)
        print(f"Added {len(new_entries)} new autonomous VH entries to {MASTER_SEQ_LIST}")
    else:
        print("No new autonomous VH entries to add.")

    # 4. Compute metrics for all (re-using compute_master_benchmarks logic)
    # I'll just run the compute script again, it should handle new entries
    print("\nStarting metric computation for all sequences...")
    cmd = ["conda", "run", "-n", "anarcii", "python", str(ROOT / "scripts/compute_master_benchmarks.py")]
    subprocess.run(cmd, check=True)
    
    # 5. Predict structures and compute compactness for new entries
    print("\nStarting structure prediction and compactness computation...")
    cmd = ["conda", "run", "-n", "anarcii", "python", str(ROOT / "scripts/predict_and_compute_missing_compactness.py")]
    subprocess.run(cmd, check=True)
    
    # 6. Rename v2 to v3 for clarity
    if os.path.exists(BENCHMARK_V2):
        if os.path.exists(BENCHMARK_V3):
            os.remove(BENCHMARK_V3)
        os.rename(BENCHMARK_V2, BENCHMARK_V3)
        print(f"\nFinal benchmark dataset saved to {BENCHMARK_V3}")

if __name__ == "__main__":
    main()
