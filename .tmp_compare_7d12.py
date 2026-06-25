import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, Any

# Setup path to import from project root
sys.path.insert(0, os.getcwd())

from api.models import VHHRequest
from api.routers.humanization import _humanize_vhh_impl, jobs

# 7D12 WT Sequence
SEQ_7D12 = "QVKLEESGGGSVQTGGSLRLTCAASGRTSRSYGMGWFRQAPGKEREFVSGISWRGDSTGYADSVKGRFTISRDNAKNTVDLQMNSLKPEDTAIYYCAAAAGSAWYGTLYEYDYWGQGTQVTVSS"

def run_mode(mode_name: str, strategy: str):
    print(f"\n--- Running Mode: {mode_name} (strategy={strategy}) ---")
    job_id = f"test-7d12-{mode_name}-{int(time.time())}"
    jobs[job_id] = {"status": "queued", "progress": 0}
    
    req = VHHRequest(
        vhh_sequence=SEQ_7D12,
        source_species="alpaca",
        strategy=strategy,
        top_k=1,
        report_format="html",
        project_name="7D12_Comparison",
        sequence_name=f"7D12_{mode_name}"
    )
    
    # Execute the implementation
    status = _humanize_vhh_impl(job_id, req)
    
    if status.status == "done" and status.result:
        res = status.result
        return {
            "mode": mode_name,
            "seq": res.get("humanized_sequence"),
            "fr2_id": res.get("fr2_identity"),
            "vh3_id": res.get("human_vh3_identity"),
            "rmsd_h3": res.get("cdr_rmsd", {}).get("H3"),
            "instability": res.get("mini_cmc", {}).get("instability_index"),
            "sap": res.get("mini_cmc", {}).get("SAP_proxy"),
            "pI": res.get("mini_cmc", {}).get("pI"),
            "abnativ_vh": res.get("abnativ_vh_score"),
            "abnativ_vhh_delta": res.get("abnativ_vhh_delta"),
            "hpr": res.get("hpr", {}).get("humanized", {}).get("vh", {}).get("score") if res.get("hpr") else None,
            "route": res.get("strategy_applied")
        }
    else:
        print(f"Error in {mode_name}: {status.error}")
        return None

# Run the three modes
results = []
results.append(run_mode("Quick Preview", "C"))
results.append(run_mode("Standard Delivery", "auto"))
results.append(run_mode("Enhanced Rescue", "A"))

print("\n--- FINAL COMPARISON ---")
print(json.dumps(results, indent=2))
