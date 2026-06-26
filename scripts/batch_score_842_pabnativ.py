#!/usr/bin/env python3
"""
Batch score the 842 antibody library (AbRef-458 + Natural-384) using p-AbNatiV2.
Extracts sequences from PDBs for AbRef-458 and uses CSV for Natural-384.

Processing order: **engineered_458 (gene-engineered clinical IgG, n=458) first**, then
natural_384, so AbRef baselines complete before the natural cohort. Resume still skips
any antibody_id already present in the output JSON.

Outputs:
  data/humanization_assay/pabnativ2_scores_842.json
"""

import csv
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add suite root to path
SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE_ROOT))

from Bio.PDB import PDBParser
from Bio.PDB.Polypeptide import is_aa
from Bio.SeqUtils import seq1
from core.humanization.p_abnativ_layer import score_paired_humanness

_842_CSV = SUITE_ROOT / "data" / "humanization_assay" / "842_combined_assessment.csv"
_384_SEQ_CSV = SUITE_ROOT / "data" / "humanization_assay" / "384_natural_sequences.csv"
_OUT_JSON = SUITE_ROOT / "data" / "humanization_assay" / "pabnativ2_scores_842.json"

def seq_from_chain(model, chain_id: str) -> str:
    if chain_id not in model:
        return ""
    out = []
    for r in model[chain_id]:
        if is_aa(r, standard=False):
            out.append(seq1(r.get_resname(), custom_map={"MSE": "M"}))
    return "".join(out)

def main():
    print("Script started...")
    if not _842_CSV.exists():
        print(f"Error: {_842_CSV} not found")
        return

    # Load 384 sequences
    seq_384 = {}
    if _384_SEQ_CSV.exists():
        with open(_384_SEQ_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                seq_384[row["ab_id"]] = (row["vh_seq"], row["vl_seq"])

    # Load 842 metadata; prioritize gene-engineered AbRef-458 over natural_384
    with open(_842_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows.sort(
        key=lambda r: (0 if r.get("origin") == "engineered_458" else 1),
    )

    results = {}
    if _OUT_JSON.exists():
        try:
            results = json.loads(_OUT_JSON.read_text(encoding="utf-8"))
            print(f"Loaded {len(results)} existing results.")
        except:
            pass

    parser = PDBParser(QUIET=True)

    total = len(rows)
    n_eng = sum(1 for r in rows if r.get("origin") == "engineered_458")
    print(f"Order: {n_eng} engineered_458 first, then {total - n_eng} other origins.")

    for idx, row in enumerate(rows, start=1):
        ab_id = row["antibody_id"]
        if ab_id in results:
            continue
            
        origin = row["origin"]
        vh, vl = "", ""
        
        if origin == "engineered_458":
            pdb_path = row["pdb_path"]
            if not pdb_path or not os.path.exists(pdb_path):
                # Try relative path
                fname = Path(pdb_path).name
                pdb_path = SUITE_ROOT / "data" / "structures" / "engineered" / fname
                
            if os.path.exists(pdb_path):
                try:
                    structure = parser.get_structure(ab_id, str(pdb_path))
                    model = structure[0]
                    vh = seq_from_chain(model, "H")
                    vl = seq_from_chain(model, "L")
                except Exception as e:
                    print(f"Error reading PDB for {ab_id}: {e}")
            else:
                print(f"PDB not found for {ab_id}: {pdb_path}")
        else:
            # Natural 384
            if ab_id in seq_384:
                vh, vl = seq_384[ab_id]
            else:
                print(f"Sequence not found for {ab_id} (Natural 384)")

        if vh and vl:
            print(f"[{idx}/{total}] Scoring {ab_id} ({origin})...")
            res = score_paired_humanness(vh, vl, seq_id=ab_id)
            if res.error:
                print(f"  Error scoring {ab_id}: {res.error}")
                results[ab_id] = {"error": res.error}
            else:
                entry = {
                    "vh_humanness": res.vh_humanness,
                    "vl_humanness": res.vl_humanness,
                    "paired_humanness": res.paired_humanness,
                    "pairing_likelihood": res.pairing_likelihood,
                    "origin": origin,
                    "timestamp": datetime.now().isoformat(),
                }
                if getattr(res, "warning", None):
                    entry["warning"] = res.warning
                results[ab_id] = entry
            
            # Save every 10 results
            if len(results) % 10 == 0:
                _OUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")

    _OUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Done. Total scored: {len(results)}")

if __name__ == "__main__":
    main()
