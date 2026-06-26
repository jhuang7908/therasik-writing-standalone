import os
import sys
import json
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import subprocess
import hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Output directories
STRUCTURE_DIR = ROOT / "data/vhh_master_predicted_structures"
STRUCTURE_DIR.mkdir(parents=True, exist_ok=True)

SEQ_LIST_PATH = ROOT / "data/vhh_master_seq_list.csv"
BENCHMARK_V1_PATH = ROOT / "data/vhh_master_benchmarks_v1.csv"
BENCHMARK_V2_PATH = ROOT / "data/vhh_master_benchmarks_v2.csv"

def get_safe_filename(seq_id):
    """Generate a safe filename by hashing if the ID is too long or contains invalid characters."""
    # Windows max path is ~260, but let's keep filenames under 100
    if len(seq_id) > 100 or any(c in '<>:"/\\|?*' for c in seq_id):
        return hashlib.md5(seq_id.encode()).hexdigest()
    return seq_id

def predict_structure(seq_id, sequence):
    """Predict structure using ImmuneBuilder (NanoBodyBuilder2) via subprocess."""
    safe_id = get_safe_filename(seq_id)
    out_path = STRUCTURE_DIR / f"{safe_id}.pdb"
    if out_path.exists():
        return str(out_path)
    
    payload = {
        "out_path": str(out_path),
        "H": sequence,
        "model_type": "nanobody"
    }
    payload_json = STRUCTURE_DIR / f"{safe_id}_payload.json"
    try:
        with open(payload_json, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        
        # Using the existing predict_one_immunebuilder.py script
        cmd = [
            "conda", "run", "-n", "anarcii", "python",
            str(ROOT / "scripts/predict_one_immunebuilder.py"),
            "--json", str(payload_json)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if out_path.exists():
            return str(out_path)
    except Exception as e:
        print(f"Error predicting {seq_id} (safe_id: {safe_id}): {e}")
        if hasattr(e, 'stderr'):
            print(e.stderr)
    finally:
        if payload_json.exists():
            payload_json.unlink()
    return None

def compute_compactness(pdb_path):
    """Compute CDR3 compactness (Cα distance between first and last CDR3 residue) using IMGT numbering."""
    if not pdb_path or not os.path.exists(pdb_path):
        return None
    
    try:
        from Bio.PDB import PDBParser
        parser = PDBParser(QUIET=True)
        structure = parser.get_structure("query", pdb_path)
        model = structure[0]
        # Find the first chain (H or A usually)
        chain = list(model.get_chains())[0]
        
        # IMGT CDR3 range: 105-117
        cdr3_lo, cdr3_hi = 105, 117
        
        # Get residues in CDR3 range with CA atoms
        cdr3_residues = [
            r for r in chain.get_residues()
            if cdr3_lo <= r.id[1] <= cdr3_hi and r.id[0] == " " and "CA" in r
        ]
        
        if len(cdr3_residues) >= 2:
            ca_first = cdr3_residues[0]["CA"].get_vector()
            ca_last  = cdr3_residues[-1]["CA"].get_vector()
            dist = (ca_last - ca_first).norm()
            return round(float(dist), 2)
    except Exception as e:
        print(f"Error computing compactness for {pdb_path}: {e}")
    return None

def main():
    # 1. Load sequence list
    df_seqs = pd.read_csv(SEQ_LIST_PATH)
    
    # 2. Predict missing structures
    print("Step 1: Predicting missing structures...")
    updated_seqs = []
    for _, row in tqdm(df_seqs.iterrows(), total=len(df_seqs)):
        pdb_path = row["pdb_path"]
        if pd.isna(pdb_path) or pdb_path == "" or not os.path.exists(str(pdb_path)):
            # Predict
            new_path = predict_structure(row["id"], row["sequence"])
            if new_path:
                row["pdb_path"] = new_path
        updated_seqs.append(row.to_dict())
    
    df_seqs_updated = pd.DataFrame(updated_seqs)
    df_seqs_updated.to_csv(SEQ_LIST_PATH, index=False)
    
    # 3. Load benchmarks
    df_bench = pd.read_csv(BENCHMARK_V1_PATH)
    
    # 4. Compute missing compactness
    print("\nStep 2: Computing missing compactness...")
    # Merge pdb_path from seq list to benchmark
    df_bench = df_bench.drop(columns=["pdb_path"], errors="ignore")
    df_bench = df_bench.merge(df_seqs_updated[["id", "pdb_path"]], on="id", how="left")
    
    results = []
    for _, row in tqdm(df_bench.iterrows(), total=len(df_bench)):
        compactness = row.get("compactness_A")
        if pd.isna(compactness) or compactness is None:
            pdb_path = row.get("pdb_path")
            if pdb_path and os.path.exists(str(pdb_path)):
                # We need to run this in anarcii env as well for BioPython
                # But for simplicity, we'll just try to import Bio here
                # If it fails, we'll skip and tell the user to run the script in anarcii
                try:
                    compactness = compute_compactness(str(pdb_path))
                    row["compactness_A"] = compactness
                except ImportError:
                    print("BioPython not found in current environment. Please run this script in 'anarcii' env.")
                    break
        results.append(row.to_dict())
    
    df_bench_v2 = pd.DataFrame(results)
    df_bench_v2.to_csv(BENCHMARK_V2_PATH, index=False)
    print(f"\nSaved updated benchmarks to {BENCHMARK_V2_PATH}")

if __name__ == "__main__":
    main()
