
import json
import sys
import os
from pathlib import Path

# Add workspace root to sys.path
ROOT = Path("d:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.insert(0, str(ROOT))

from api.routers.vh_to_vhh import (
    _generate_conversion_candidates,
    _vh2vhh_impl,
    VhToVhhRequest,
    ENABLE_PHASE45,
    ENABLE_ABNATIV_GATE,
    ENABLE_PHASE5_QA
)
from api.job_store import jobs

def run_sp34_p45():
    # SP34 VH sequence
    seq = "DIKLQSGAELARPGASVKMSCKTSGYTFTRYTMHWVKQRPGQGLEWIGYINPSRGYTNYNQKFKDKATLTTDKSSSTAYMQLSSLTSEDSAVYYCARYYDDHYCLDYWGQGTTLTVSS"
    
    job_id = "SP34_P45_RUN_20260508"
    req = VhToVhhRequest(
        vh_sequence=seq,
        source_class="murine_mab",
        sequence_name="SP34_CD3_VH_P45"
    )
    
    # Initialize job store entry
    jobs[job_id] = {
        "id": job_id,
        "status": "running",
        "progress": 0,
        "progress_note": "Starting SP34 Phase 4.5 optimization run...",
        "result": None
    }
    
    print(f"Starting job {job_id}...")
    try:
        # This will run the full pipeline including Phase 4.5, AbNatiV, and Phase 5 QA
        _vh2vhh_impl(job_id, req)
        
        result = jobs[job_id].get("result")
        if result:
            # Save the result for the assistant to read
            out_path = ROOT / f".tmp_{job_id}_result.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"SUCCESS: Result saved to {out_path}")
            
            # Print a summary
            print("\n--- SP34 Phase 4.5 Optimization Summary ---")
            print(f"Best Strategy: {result.get('selected_strategy')}")
            print(f"Mutations Applied: {result.get('mutations_applied')}")
            
            best_cand = result.get("candidates", [{}])[0]
            print(f"Phase 4.5 Mutations: {best_cand.get('phase45_mutations')}")
            print(f"AbNatiV Delta: {result.get('best_abnativ_delta')} ({result.get('best_abnativ_tier')})")
            
            p5 = result.get("phase5_qa", {})
            print(f"Phase 5 QA Tier: {p5.get('overall_tier')}")
            print(f"Rg: {p5.get('rg', {}).get('rg_angstrom')} A")
            print(f"pLDDT Proxy: {p5.get('plddt_proxy', {}).get('plddt_proxy_mean')}")
            
            cmc = result.get("mini_cmc", {})
            print(f"pI: {cmc.get('pI')}")
            print(f"GRAVY: {cmc.get('GRAVY')}")
        else:
            print("ERROR: No result in job store.")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    # Ensure environment variables for AbNatiV/NanoBodyBuilder2 are okay
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    run_sp34_p45()
