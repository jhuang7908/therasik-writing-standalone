#!/usr/bin/env python
"""
FGF23 VAM Stage-2: Full CDR alanine scan (EvoEF2 ComputeBinding).

Reads  : vam_boltz_scan/FGF23/FGF23_numbering.json  (CDR positions)
         vam_boltz_scan/FGF23/FGF23_relaxed.pdb
Writes : vam_boltz_scan/FGF23/stage2_ala_scan/stage2_ala_scan.{json,csv}

Usage (conda env affmat):
  conda run -n affmat python scripts/run_fgf23_ala_scan.py
  conda run -n affmat python scripts/run_fgf23_ala_scan.py --dry-run
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit

PROJECT_DIR  = ROOT / "projects/fgf 23"
VAM_DIR      = PROJECT_DIR / "vam_boltz_scan/FGF23"
NUMBERING    = VAM_DIR / "FGF23_numbering.json"
RELAXED_PDB  = VAM_DIR / "FGF23_relaxed.pdb"
OUT_DIR      = VAM_DIR / "stage2_ala_scan"

AB_CHAINS    = ["H", "L"]
AG_CHAINS    = ["A"]
HOTSPOT_DDG  = 1.0

AA3 = {
    "ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E",
    "GLY":"G","HIS":"H","ILE":"I","LEU":"L","LYS":"K","MET":"M","PHE":"F",
    "PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V",
}


def _parse_pdb_aa(pdb_path: Path) -> dict[tuple[str, int], str]:
    out: dict[tuple[str, int], str] = {}
    seen: set[tuple[str, int]] = set()
    for line in pdb_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("ATOM"):
            continue
        chain = line[21].strip()
        try:
            resi = int(line[22:26].strip())
        except ValueError:
            continue
        key = (chain, resi)
        if key in seen:
            continue
        seen.add(key)
        out[key] = AA3.get(line[17:20].strip().upper(), "X")
    return out


def _aggregate_by_locus(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list] = defaultdict(list)
    for r in rows:
        if r.get("evoef2_error"):
            continue
        buckets[r["locus"]].append(r)
    summary: list[dict] = []
    for locus in sorted(buckets):
        vals = [x["evoef2_ddg"] for x in buckets[locus] if x.get("evoef2_ddg") is not None]
        if not vals:
            continue
        hotspots = [v for v in vals if v > HOTSPOT_DDG]
        summary.append({
            "locus":                 locus,
            "n_scored":              len(vals),
            "n_hotspot_ddg_gt_1":   len(hotspots),
            "mean_ddg":              round(sum(vals) / len(vals), 4),
            "sum_positive_ddg":      round(sum(max(v, 0.0) for v in vals), 4),
            "max_ddg":               round(max(vals), 4),
            "min_ddg":               round(min(vals), 4),
        })
    summary.sort(key=lambda x: x["sum_positive_ddg"], reverse=True)
    for i, item in enumerate(summary, start=1):
        item["rank_by_binding_impact"] = i
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit",   type=int, default=None, help="Max mutations (debug).")
    args = parser.parse_args(argv)

    # Pre-checks
    for p, label in [(NUMBERING, "numbering JSON"), (RELAXED_PDB, "relaxed PDB")]:
        if not p.is_file():
            if args.dry_run:
                print(f"[dry-run] Skipping (missing {label}): {p}", flush=True)
                return 0
            print(f"ERROR: Missing {label}: {p}", file=sys.stderr)
            return 1

    num_data = json.loads(NUMBERING.read_text(encoding="utf-8"))
    raw_muts = num_data["ala_scan"]["mutations"]
    pdb_aa   = _parse_pdb_aa(RELAXED_PDB)

    # Validate + build mutation list
    ready, skipped = [], []
    for m in raw_muts:
        chain = m["haddock_chain"]
        resi  = int(m["pdb_resi"])
        wt    = m["wt"]
        obs   = pdb_aa.get((chain, resi))
        row   = {
            "clone":    "FGF23",
            "locus":    m["locus"],
            "chain":    chain,
            "pdb_resi": resi,
            "wt":       wt,
            "mut":      "A",
            "kabat_pos": m.get("kabat_pos"),
            "mutation": f"{chain}:{resi}:{wt}:A",
        }
        if obs is None:
            row["skip_reason"] = "residue_missing_in_pdb"; skipped.append(row); continue
        if obs != wt:
            row["skip_reason"] = f"wt_mismatch_pdb={obs}"; skipped.append(row); continue
        ready.append(row)

    if args.limit:
        ready = ready[:args.limit]

    print(f"[FGF23/ala] Mutations ready={len(ready)}  skipped={len(skipped)}", flush=True)
    if args.dry_run:
        for r in ready[:8]:
            print(f"  {r['mutation']:<18}  {r['locus']}")
        print("  [dry-run] No EvoEF2 calls.")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tk = AffinityEnergyToolkit(
        complex_pdb=str(RELAXED_PDB),
        ab_chains=AB_CHAINS,
        ag_chains=AG_CHAINS,
    )

    print("[FGF23/ala] WT EvoEF2 baseline ...", flush=True)
    wt_res = tk.run_evoef2([])
    wt_dg  = wt_res.get("dg")
    print(f"[FGF23/ala] WT dg={wt_dg}  ({wt_res.get('elapsed', 0):.1f}s)", flush=True)

    results: list[dict] = []
    t_batch = time.time()
    for i, row in enumerate(ready, start=1):
        mutation = [{"chain": row["chain"], "resi": row["pdb_resi"], "wt": row["wt"], "mut": "A"}]
        r = tk.run_evoef2(mutation, wt_dg=wt_dg)
        out = {
            **row,
            "variant":          r.get("variant") or f"{row['chain']}{row['pdb_resi']}{row['wt']}>A",
            "evoef2_dg":        r.get("dg"),
            "evoef2_ddg":       r.get("ddg"),
            "evoef2_error":     r.get("error"),
            "evoef2_elapsed_s": r.get("elapsed"),
        }
        results.append(out)
        if i == 1 or i % 10 == 0 or i == len(ready):
            ddg_s = f"{out['evoef2_ddg']:+.3f}" if isinstance(out.get("evoef2_ddg"), (int, float)) else "ERR"
            print(f"[FGF23/ala] {i:3d}/{len(ready)}  {out['mutation']:<20}  "
                  f"{out['locus']:<12}  ΔΔG={ddg_s}", flush=True)

    locus_summary = _aggregate_by_locus(results)
    meta = {
        "clone": "FGF23",
        "pdb": str(RELAXED_PDB.relative_to(ROOT)).replace("\\", "/"),
        "ab_chains": AB_CHAINS,
        "ag_chains": AG_CHAINS,
        "n_input":   len(raw_muts),
        "n_ready":   len(ready),
        "n_skipped": len(skipped),
        "wt_evoef2_dg": wt_dg,
        "batch_elapsed_s": round(time.time() - t_batch, 1),
        "n_scored":  sum(1 for r in results if r.get("evoef2_ddg") is not None),
        "n_errors":  sum(1 for r in results if r.get("evoef2_error")),
        "top_cdr_for_saturation": locus_summary[0]["locus"] if locus_summary else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    payload = {"_meta": meta, "skipped": skipped, "mutations": results, "locus_summary": locus_summary}
    json_path = OUT_DIR / "stage2_ala_scan.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    fields = ["clone", "locus", "chain", "pdb_resi", "wt", "mut", "mutation",
              "kabat_pos", "variant", "evoef2_ddg", "evoef2_dg", "evoef2_error", "evoef2_elapsed_s"]
    with (OUT_DIR / "stage2_ala_scan.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    print(f"\n[FGF23/ala] CDR loop ranking (sum_positive_ΔΔG):")
    for item in locus_summary:
        print(f"  #{item['rank_by_binding_impact']} {item['locus']:<14}  "
              f"hotspots={item['n_hotspot_ddg_gt_1']}  "
              f"sum_ΔΔG+={item['sum_positive_ddg']:.3f}  mean={item['mean_ddg']:+.3f}")
    print(f"[FGF23/ala] Wrote: {json_path.relative_to(ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
