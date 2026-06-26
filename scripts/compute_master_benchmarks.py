import json
import pandas as pd
from pathlib import Path
import sys
import queue
import threading
from tqdm import tqdm

# Add root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Import tools
from core.vh2vhh.abnativ_naturalness_layer import score_naturalness_delta
from core.humanization.hpr_index import compute_hpr_index
from core.cmc.cmc_metrics import compute_pI, compute_GRAVY

# Mock/Load nanoBERT if possible
def load_nanobert_fn():
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import run_dog_petization_qc as rdp
        return rdp.calc_nanobert_pll
    except ImportError:
        return None

def compute_metrics():
    df_master = pd.read_csv(ROOT / "data/vhh_master_seq_list.csv")
    calc_nanobert_pll = load_nanobert_fn()
    
    results = []
    
    print(f"Processing {len(df_master)} sequences...")
    
    # Batch NanoBERT if available
    nanobert_scores = {}
    if calc_nanobert_pll:
        print("Computing nanoBERT PLL (batch)...")
        seq_dict = {row["id"]: row["sequence"] for _, row in df_master.iterrows()}
        nanobert_scores, err = calc_nanobert_pll(seq_dict)
        if err:
            print(f"Warning: nanoBERT error: {err}")

    for _, row in tqdm(df_master.iterrows(), total=len(df_master)):
        seq_id = row["id"]
        seq = row["sequence"]
        
        # 1. AbNatiV (VH2 / VHH2 / Delta)
        ab_res = score_naturalness_delta(seq, seq_id=seq_id)
        
        # 2. HPR Index
        hpr_res = compute_hpr_index(seq, "")
        
        # 3. NanoBERT
        nb_score = nanobert_scores.get(seq_id)
        
        # 4. CMC Metrics (pI, GRAVY)
        pi = compute_pI(seq)
        gravy = compute_GRAVY(seq)
        
        # 5. Compactness (if PDB available)
        compactness = None
        if pd.notna(row["pdb_path"]):
            try:
                from core.cmc.vhh_cmc_engine import compute_vhh_structural_metrics
                struct_res = compute_vhh_structural_metrics(row["pdb_path"])
                compactness = struct_res.get("cdr3_compactness_ca_dist")
            except Exception:
                pass

        results.append({
            "id": seq_id,
            "category": row["category"],
            "source": row["source"],
            "hpr_index": hpr_res.get("combined", {}).get("score"),
            "nanobert_pll": nb_score,
            "abnativ_vh2": ab_res.vh2_score,
            "abnativ_vhh2": ab_res.vhh2_score,
            "abnativ_delta": ab_res.delta,
            "abnativ_tier": ab_res.tier,
            "pI": pi,
            "GRAVY": gravy,
            "compactness_A": compactness
        })

    return results

if __name__ == "__main__":
    data = compute_metrics()
    df = pd.DataFrame(data)
    df.to_csv(ROOT / "data/vhh_master_benchmarks_v1.csv", index=False)
    print(f"Saved {len(df)} records to data/vhh_master_benchmarks_v1.csv")
