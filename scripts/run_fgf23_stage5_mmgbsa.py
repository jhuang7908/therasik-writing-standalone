#!/usr/bin/env python
"""
FGF23 VAM Stage-5: MM/GBSA confirmation on Stage-4 shortlist (server/GPU).

Runs OpenMM MM/GBSA binding energy for each shortlisted mutation vs WT,
with per-site baseline correction (rebaseline).

Reads  : stage4_postfilter/stage4_shortlist.json
         FGF23_relaxed.pdb
Writes : stage5_mmgbsa/stage5_mmgbsa.{json,csv}
         stage5_mmgbsa/stage5_mmgbsa_beneficial.json
         stage5_mmgbsa/checkpoint.json

Server usage (conda env affmat, GPU strongly recommended):
  OPENMM_DEFAULT_PLATFORM=CUDA conda run -n affmat python scripts/run_fgf23_stage5_mmgbsa.py \\
      --suite-root /srv/AbEngineCore --resume --steps 300

  CPU fallback (slower, ~30 min per mutant):
  OPENMM_DEFAULT_PLATFORM=CPU conda run -n affmat python scripts/run_fgf23_stage5_mmgbsa.py \\
      --suite-root /srv/AbEngineCore --resume --steps 300
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit

PROJECT_DIR  = ROOT / "projects/fgf 23"
VAM_DIR      = PROJECT_DIR / "vam_boltz_scan/FGF23"
RELAXED_PDB  = VAM_DIR / "FGF23_relaxed.pdb"
S4_JSON      = VAM_DIR / "stage4_postfilter/stage4_shortlist.json"
OUT_DIR      = VAM_DIR / "stage5_mmgbsa"

AB_CHAINS    = ["H", "L"]
AG_CHAINS    = ["A"]

MMGBSA_BENEFICIAL = -0.5    # kcal/mol vs WT
DEFAULT_STEPS     = 300     # NVT steps after minimization
PROTOCOL_VERSION  = "VAM V1.4 (FGF23 / Boltz baseline)"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite-root", type=Path, default=ROOT,
                        help="AbEngineCore root on server (default: repo ROOT).")
    parser.add_argument("--pdb",  type=Path, default=None,
                        help="Override relaxed PDB path.")
    parser.add_argument("--steps",  type=int, default=DEFAULT_STEPS)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run",action="store_true")
    parser.add_argument("--limit",  type=int, default=None)
    args = parser.parse_args(argv)

    suite_root = args.suite_root.resolve()
    if str(suite_root) not in sys.path:
        sys.path.insert(0, str(suite_root))

    relaxed_pdb = (args.pdb or RELAXED_PDB).resolve()
    for p, label in [(S4_JSON, "Stage-4 shortlist"), (relaxed_pdb, "relaxed PDB")]:
        if not p.is_file():
            if args.dry_run:
                print(f"[dry-run] Skipping (missing {label}): {p}", flush=True)
                return 0
            print(f"ERROR: Missing {label}: {p}", file=sys.stderr)
            return 1

    s4_data    = json.loads(S4_JSON.read_text(encoding="utf-8"))
    shortlist  = s4_data.get("shortlist", [])
    if not shortlist:
        print("[FGF23/s5] Stage-4 shortlist is empty.", flush=True)
        return 0
    if args.limit:
        shortlist = shortlist[:args.limit]

    print(f"[FGF23/s5] Shortlist: {len(shortlist)} mutants", flush=True)
    print(f"[FGF23/s5] PDB:       {relaxed_pdb}", flush=True)
    print(f"[FGF23/s5] Steps:     {args.steps}", flush=True)
    if args.dry_run:
        for c in shortlist[:5]:
            print(f"  {c.get('variant'):<14}  ΔΔG_evoef2={c.get('evoef2_ddg'):+.3f}")
        print("[FGF23/s5] Dry-run: no MM/GBSA.")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ck_path = OUT_DIR / "checkpoint.json"

    results: list[dict] = []
    done_keys: set[str] = set()
    if args.resume and ck_path.is_file():
        ckpt = json.loads(ck_path.read_text(encoding="utf-8"))
        results   = ckpt.get("results", [])
        done_keys = {r["mutation"] for r in results}
        print(f"[FGF23/s5] Resume: {len(done_keys)} done", flush=True)

    tk = AffinityEnergyToolkit(
        complex_pdb=str(relaxed_pdb),
        ab_chains=AB_CHAINS,
        ag_chains=AG_CHAINS,
    )

    # WT MM/GBSA baseline
    print("[FGF23/s5] WT MM/GBSA baseline ...", flush=True)
    wt_mmgbsa = tk.run_mmgbsa([], minimization_steps=args.steps)
    wt_binding = wt_mmgbsa.get("dg")
    print(f"[FGF23/s5] WT binding energy = {wt_binding}  ({wt_mmgbsa.get('elapsed', 0):.1f}s)", flush=True)

    pending = [c for c in shortlist if c.get("mutation") not in done_keys]
    t_start = time.time()
    for i, cand in enumerate(pending, 1):
        chain   = cand["chain"]
        pdb_resi= int(cand["pdb_resi"])
        wt_aa   = cand["wt"]
        mut_aa  = cand["mut"]

        res = tk.run_mmgbsa(
            [{"chain": chain, "resi": pdb_resi, "wt": wt_aa, "mut": mut_aa}],
            minimization_steps=args.steps,
            wt_dg=wt_binding,
        )
        row = {
            **cand,
            "mmgbsa_binding":       res.get("dg"),
            "mmgbsa_ddg":           res.get("ddg"),
            "mmgbsa_error":         res.get("error"),
            "mmgbsa_elapsed_s":     res.get("elapsed"),
        }
        results.append(row)

        elapsed = round(time.time() - t_start, 0)
        ddg_s = f"{row['mmgbsa_ddg']:+.3f}" if isinstance(row.get("mmgbsa_ddg"), (int, float)) else "ERR"
        print(f"[FGF23/s5] {i:3d}/{len(pending)}  {cand.get('variant'):<14}  "
              f"MM/GBSA ΔΔG={ddg_s}  EvoEF2 ΔΔG={cand.get('evoef2_ddg'):+.3f}  "
              f"{elapsed:.0f}s total", flush=True)

        ck_path.write_text(
            json.dumps({"results": results, "wt_binding": wt_binding,
                        "updated_at": _utc_now()}, indent=2))

    # Final results
    beneficial = sorted(
        [r for r in results if r.get("mmgbsa_ddg") is not None and r["mmgbsa_ddg"] <= MMGBSA_BENEFICIAL],
        key=lambda x: x["mmgbsa_ddg"],
    )

    print(f"\n[FGF23/s5] MM/GBSA beneficial: {len(beneficial)} / {len(results)}", flush=True)
    for r in beneficial[:10]:
        print(f"  {r.get('variant'):<14}  MM/GBSA ΔΔG={r['mmgbsa_ddg']:+.3f}  "
              f"EvoEF2 ΔΔG={r.get('evoef2_ddg'):+.3f}  {r.get('locus')}")

    payload: dict[str, Any] = {
        "clone": "FGF23",
        "generated_at": _utc_now(),
        "protocol_version": PROTOCOL_VERSION,
        "wt_binding_energy": wt_binding,
        "mmgbsa_steps": args.steps,
        "n_evaluated": len(results),
        "n_beneficial": len(beneficial),
        "beneficial_ddg_threshold": MMGBSA_BENEFICIAL,
        "results":    results,
        "beneficial": beneficial,
    }
    (OUT_DIR / "stage5_mmgbsa.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT_DIR / "stage5_mmgbsa_beneficial.json").write_text(
        json.dumps({"beneficial": beneficial, "generated_at": _utc_now()}, indent=2), encoding="utf-8")

    fields = ["variant", "locus", "chain", "pdb_resi", "wt", "mut",
              "evoef2_ddg", "mmgbsa_ddg", "mmgbsa_binding", "mmgbsa_error"]
    with (OUT_DIR / "stage5_mmgbsa.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
