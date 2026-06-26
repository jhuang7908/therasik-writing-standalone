#!/usr/bin/env python
"""
PAG-1 Stage-3 CDR saturation (19-AA) with EvoEF2 on RELAXED BOLTZ structures.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit
from core.structure.cdr_fingerprint_prior import (
    design_prior_audit,
    load_fingerprint,
)

QC_DIR = ROOT / "projects/PAG project/boltz_relaxed_qc"
NUMBERING_DIR = ROOT / "projects/PAG project/numbering"
VAM_DIR = ROOT / "projects/PAG project/vam_boltz_scan"

AB_CHAINS = ["A", "B"]
AG_CHAINS = ["C"]

RELAXED_PDBS = {
    "001": "001_relaxed.pdb",
    "008": "008_relaxed.pdb",
    "7M16": "7M16_relaxed.pdb",
}

STANDARD_AA = list("ACDEFGHIKLMNPQRSTVWY")
SATURATION_AA = [aa for aa in STANDARD_AA if aa != "C"]

BENEFICIAL_DDG = -0.5


def _relaxed_pdb(clone_id: str) -> Path:
    return QC_DIR / RELAXED_PDBS[clone_id]


def _load_numbering(clone_id: str) -> dict[str, Any]:
    return json.loads((NUMBERING_DIR / f"{clone_id}_numbering.json").read_text(encoding="utf-8"))


def _load_ala_results(clone_id: str) -> dict[str, Any]:
    p = VAM_DIR / clone_id / "stage2_ala_scan" / "stage2_ala_scan.json"
    if not p.is_file():
        raise FileNotFoundError(f"Missing Ala scan for {clone_id}: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _get_top_loops(ala_data: dict[str, Any], n=2) -> list[str]:
    summary = ala_data.get("locus_summary", [])
    return [x["locus"] for x in summary[:n]]


def run_clone(
    clone_id: str,
    *,
    loops: list[str] | None,
    resume: bool,
    dry_run: bool,
    limit: int | None = None,
) -> dict[str, Any]:
    print(f"[{clone_id}] Starting saturation run...")
    pdb_path = _relaxed_pdb(clone_id)
    numbering = _load_numbering(clone_id)
    ala_data = _load_ala_results(clone_id)

    if loops is None:
        loops = _get_top_loops(ala_data)

    print(f"\n{'=' * 72}\n[{clone_id}] Saturation on {pdb_path.name} | Loops: {loops}\n{'=' * 72}")

    out_dir = VAM_DIR / clone_id / "stage3_saturation"
    out_dir.mkdir(parents=True, exist_ok=True)
    ck_path = out_dir / "checkpoint.json"

    # 1. Build mutation list
    all_muts = numbering.get("ala_scan", {}).get("mutations", [])
    
    # Group by locus to get indices for fingerprint audit
    locus_muts = defaultdict(list)
    for m in all_muts:
        locus_muts[m["locus"]].append(m)
    
    pos_map = {}
    for locus, muts in locus_muts.items():
        # Sort by pdb_resi to ensure consistent indexing
        muts.sort(key=lambda x: int(x["pdb_resi"]))
        for idx, m in enumerate(muts):
            pos_map[(locus, int(m["pdb_resi"]))] = idx

    target_sites = [m for m in all_muts if m["locus"] in loops]
    
    saturation_list = []
    for s in target_sites:
        for aa in SATURATION_AA:
            if aa == s["wt"]:
                continue
            saturation_list.append({
                "clone": clone_id,
                "locus": s["locus"],
                "chain": s["haddock_chain"],
                "pdb_resi": int(s["pdb_resi"]),
                "wt": s["wt"],
                "mut": aa,
                "mutation": f"{s['haddock_chain']}:{s['pdb_resi']}:{s['wt']}:{aa}",
                "variant": f"{s['wt']}{s['pdb_resi']}{aa}",
                "pos_idx": pos_map.get((s["locus"], int(s["pdb_resi"]))),
            })

    print(f"[{clone_id}] Total mutations to scan: {len(saturation_list)}")

    if dry_run:
        return {"clone": clone_id, "n_mutations": len(saturation_list), "loops": loops}

    # 2. Load checkpoint
    results = []
    done_keys = set()
    if resume and ck_path.is_file():
        ckpt = json.loads(ck_path.read_text(encoding="utf-8"))
        results = ckpt.get("results", [])
        done_keys = {r["mutation"] for r in results}
        print(f"[{clone_id}] Resuming: {len(done_keys)} done, {len(saturation_list) - len(done_keys)} pending")

    # 3. Setup toolkit
    tk = AffinityEnergyToolkit(
        complex_pdb=str(pdb_path),
        ab_chains=AB_CHAINS,
        ag_chains=AG_CHAINS,
    )
    wt_dg = ala_data["_meta"]["wt_evoef2_dg"]
    
    print(f"[{clone_id}] Loading fingerprint database...")
    fingerprint = load_fingerprint("vh_vl")
    print(f"[{clone_id}] Fingerprint database loaded.")

    # 4. Run loop
    pending = [m for m in saturation_list if m["mutation"] not in done_keys]
    if limit:
        pending = pending[:limit]
    
    t_start = time.time()
    
    for i, m in enumerate(pending, 1):
        if i % 10 == 0 or i == 1:
            print(f"[{clone_id}] Progress: {i}/{len(pending)} ({m['variant']})")
        
        res = tk.run_evoef2([{"chain": m["chain"], "resi": m["pdb_resi"], "wt": m["wt"], "mut": m["mut"]}], wt_dg=wt_dg)
        
        # CHECK 6: Fingerprint audit
        audit = design_prior_audit(
            fingerprint, m["locus"], m["pos_idx"], m["mut"]
        )
        
        row = {
            **m,
            "evoef2_dg": res.get("dg"),
            "evoef2_ddg": res.get("ddg"),
            "evoef2_error": res.get("error"),
            "evoef2_elapsed_s": res.get("elapsed"),
            "fingerprint_verdict": audit["verdict"],
            "fingerprint_freq": audit["freq"],
        }
        results.append(row)
        
        if i % 10 == 0 or i == len(pending):
            print(f"[{clone_id}] {len(results)}/{len(saturation_list)} done | {m['mutation']} ddg={row['evoef2_ddg']} | {row['fingerprint_verdict']}")
            ck_path.write_text(json.dumps({"results": results, "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2))

    # 5. Finalize
    beneficial = [r for r in results if r.get("evoef2_ddg") is not None and r["evoef2_ddg"] <= BENEFICIAL_DDG]
    beneficial.sort(key=lambda x: x["evoef2_ddg"])
    
    # Filter beneficial by fingerprint verdict (PASS or WARN only)
    beneficial = [r for r in beneficial if r["fingerprint_verdict"] in ["PASS", "WARN"]]
    
    payload = {
        "clone": clone_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_total": len(results),
        "n_beneficial": len(beneficial),
        "loops": loops,
        "results": results,
        "beneficial": beneficial,
    }
    
    (out_dir / "stage3_saturation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    
    # Write CSV
    fields = ["clone", "locus", "chain", "pdb_resi", "wt", "mut", "mutation", "variant", "evoef2_ddg", "fingerprint_verdict", "fingerprint_freq"]
    with (out_dir / "stage3_saturation.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
        
    print(f"[{clone_id}] Finished. Beneficial: {len(beneficial)}. Wrote to {out_dir}")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clone", nargs="+", default=["001", "008", "7M16"])
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, help="Limit mutations per clone")
    args = parser.parse_args()

    for cid in args.clone:
        run_clone(cid, loops=None, resume=args.resume, dry_run=args.dry_run, limit=args.limit)

if __name__ == "__main__":
    main()
