#!/usr/bin/env python
"""
FGF23 VAM Stage-3: 19-AA CDR saturation scan (EvoEF2, resume-safe).

Reads top-N CDR loops from Stage-2 ala scan, then runs all 19 non-Cys
substitutions at each hotspot position.

Reads  : stage2_ala_scan/stage2_ala_scan.json
         FGF23_numbering.json
         FGF23_relaxed.pdb
Writes : stage3_saturation/stage3_saturation.{json,csv}
         stage3_saturation/checkpoint.json (resume token)

Usage (conda env affmat):
  conda run -n affmat python scripts/run_fgf23_saturation.py
  conda run -n affmat python scripts/run_fgf23_saturation.py --resume
  conda run -n affmat python scripts/run_fgf23_saturation.py --loops vh_cdr3 vl_cdr3
"""

from __future__ import annotations

import argparse
import csv
import json
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
NUMBERING    = VAM_DIR / "FGF23_numbering.json"
RELAXED_PDB  = VAM_DIR / "FGF23_relaxed.pdb"
ALA_JSON     = VAM_DIR / "stage2_ala_scan/stage2_ala_scan.json"
OUT_DIR      = VAM_DIR / "stage3_saturation"

AB_CHAINS    = ["H", "L"]
AG_CHAINS    = ["A"]

STANDARD_AA   = list("ACDEFGHIKLMNPQRSTVWY")
SATURATION_AA = [aa for aa in STANDARD_AA if aa != "C"]
BENEFICIAL_DDG = -0.5
TOP_LOOPS      = 2          # how many top-ΔΔG CDR loops to saturate by default


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--loops",  nargs="+", default=None,
                        help="CDR locus names to saturate (default: top-2 from ala scan).")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run",action="store_true")
    parser.add_argument("--limit",  type=int, default=None)
    args = parser.parse_args(argv)

    for p, label in [(NUMBERING, "numbering JSON"), (RELAXED_PDB, "relaxed PDB"), (ALA_JSON, "ala scan JSON")]:
        if not p.is_file():
            if args.dry_run:
                print(f"[dry-run] Skipping (missing {label}): {p}", flush=True)
                return 0
            print(f"ERROR: Missing {label}: {p}", file=sys.stderr)
            return 1

    num_data    = json.loads(NUMBERING.read_text(encoding="utf-8"))
    ala_data    = json.loads(ALA_JSON.read_text(encoding="utf-8"))
    wt_dg       = ala_data["_meta"]["wt_evoef2_dg"]
    all_cdr_muts= num_data["ala_scan"]["mutations"]

    # Determine loops to saturate
    loops = args.loops or [x["locus"] for x in ala_data["locus_summary"][:TOP_LOOPS]]
    print(f"[FGF23/sat] Loops selected: {loops}", flush=True)

    # Build saturation list
    target = [m for m in all_cdr_muts if m["locus"] in loops]
    sat_list: list[dict] = []
    for s in target:
        for aa in SATURATION_AA:
            if aa == s["wt"]:
                continue
            sat_list.append({
                "locus":    s["locus"],
                "chain":    s["haddock_chain"],
                "pdb_resi": int(s["pdb_resi"]),
                "wt":       s["wt"],
                "mut":      aa,
                "mutation": f"{s['haddock_chain']}:{s['pdb_resi']}:{s['wt']}:{aa}",
                "variant":  f"{s['wt']}{s['pdb_resi']}{aa}",
                "kabat_pos": s.get("kabat_pos"),
            })

    print(f"[FGF23/sat] Total mutations: {len(sat_list)}", flush=True)

    if args.dry_run:
        print("[FGF23/sat] Dry-run: no EvoEF2 calls.")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ck_path = OUT_DIR / "checkpoint.json"

    # Resume
    results: list[dict] = []
    done_keys: set[str] = set()
    if args.resume and ck_path.is_file():
        ckpt = json.loads(ck_path.read_text(encoding="utf-8"))
        results   = ckpt.get("results", [])
        done_keys = {r["mutation"] for r in results}
        print(f"[FGF23/sat] Resume: {len(done_keys)} done, "
              f"{len(sat_list) - len(done_keys)} pending", flush=True)

    tk = AffinityEnergyToolkit(
        complex_pdb=str(RELAXED_PDB),
        ab_chains=AB_CHAINS,
        ag_chains=AG_CHAINS,
    )

    pending = [m for m in sat_list if m["mutation"] not in done_keys]
    if args.limit:
        pending = pending[:args.limit]

    t_start = time.time()
    for i, m in enumerate(pending, 1):
        res = tk.run_evoef2(
            [{"chain": m["chain"], "resi": m["pdb_resi"], "wt": m["wt"], "mut": m["mut"]}],
            wt_dg=wt_dg,
        )
        row = {
            **m,
            "evoef2_dg":        res.get("dg"),
            "evoef2_ddg":       res.get("ddg"),
            "evoef2_error":     res.get("error"),
            "evoef2_elapsed_s": res.get("elapsed"),
        }
        results.append(row)

        if i % 20 == 0 or i == 1 or i == len(pending):
            ddg_s = f"{row['evoef2_ddg']:+.3f}" if isinstance(row.get("evoef2_ddg"), (int, float)) else "ERR"
            elapsed = round(time.time() - t_start, 0)
            print(f"[FGF23/sat] {i:4d}/{len(pending)}  {m['mutation']:<22}  "
                  f"ΔΔG={ddg_s}  {elapsed:.0f}s total", flush=True)
            ck_path.write_text(
                json.dumps({"results": results,
                            "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2))

    beneficial = sorted(
        [r for r in results if r.get("evoef2_ddg") is not None and r["evoef2_ddg"] <= BENEFICIAL_DDG],
        key=lambda x: x["evoef2_ddg"],
    )

    payload: dict[str, Any] = {
        "clone": "FGF23",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "loops":        loops,
        "n_total":      len(results),
        "n_beneficial": len(beneficial),
        "beneficial_ddg_threshold": BENEFICIAL_DDG,
        "results":      results,
        "beneficial":   beneficial,
    }
    (OUT_DIR / "stage3_saturation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    fields = ["locus", "chain", "pdb_resi", "wt", "mut", "mutation", "variant",
              "kabat_pos", "evoef2_ddg", "evoef2_dg", "evoef2_error", "evoef2_elapsed_s"]
    with (OUT_DIR / "stage3_saturation.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    print(f"\n[FGF23/sat] Done. Beneficial: {len(beneficial)} / {len(results)}", flush=True)
    print(f"[FGF23/sat] Top beneficial:")
    for r in beneficial[:10]:
        print(f"  {r['variant']:<14}  ΔΔG={r['evoef2_ddg']:+.3f}  {r['locus']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
