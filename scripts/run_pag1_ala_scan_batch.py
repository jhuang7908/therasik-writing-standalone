#!/usr/bin/env python
"""
PAG-1 Stage-2 full CDR alanine scan on HADDOCK3 rank-1 emref structures.

Reads per-clone CDR coordinates from numbering JSON (union CDR, all six loops),
runs EvoEF2 ΔΔG on each Ala substitution, aggregates impact by CDR locus, and
writes clone-level CSV/JSON under projects/PAG project/vam_ala_scan/.

Scenario A (short peptide): PRODIGY skipped per config/vam_antigen_profile.json.

Usage (repo root, conda env affmat):
  conda run -n affmat python scripts/run_pag1_ala_scan_batch.py
  conda run -n affmat python scripts/run_pag1_ala_scan_batch.py --clone 001
  conda run -n affmat python scripts/run_pag1_ala_scan_batch.py --dry-run
  conda run -n affmat python scripts/run_pag1_ala_scan_batch.py --limit 5
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

from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit  # noqa: E402

HADDOCK_RESULTS = ROOT / "projects/PAG project/haddock3_results"
NUMBERING_DIR = ROOT / "projects/PAG project/numbering"
OUT_DIR = ROOT / "projects/PAG project/vam_ala_scan"

AB_CHAINS = ["A", "B"]
AG_CHAINS = ["C"]

RANK1: dict[str, dict[str, str]] = {
    "001": {
        "emref": "emref_31.pdb",
        "capri_score": "-72.936",
        "dockq": "1.000",
    },
    "008": {
        "emref": "emref_4.pdb",
        "capri_score": "-52.291",
        "dockq": "1.000",
    },
    "7M16": {
        "emref": "emref_7.pdb",
        "capri_score": "-63.966",
        "dockq": "1.000",
    },
}

AA3_TO_1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}

HOTSPOT_DDG = 1.0  # VAM Phase 1: Ala scan hotspot threshold (kcal/mol)


def _parse_pdb_aa(pdb_path: Path) -> dict[tuple[str, int], str]:
    out: dict[tuple[str, int], str] = {}
    seen: set[tuple[str, int, str]] = set()
    for line in pdb_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("ATOM"):
            continue
        chain = line[21].strip()
        if not chain:
            continue
        try:
            resi = int(line[22:26].strip())
        except ValueError:
            continue
        icode = line[26].strip()
        key = (chain, resi, icode)
        if key in seen:
            continue
        seen.add(key)
        aa = AA3_TO_1.get(line[17:20].strip().upper(), "X")
        out[(chain, resi)] = aa
    return out


def _rank1_pdb(clone_id: str) -> Path:
    info = RANK1[clone_id]
    pdb = HADDOCK_RESULTS / clone_id / "run" / "4_emref" / info["emref"]
    if not pdb.is_file():
        gz = pdb.with_suffix(pdb.suffix + ".gz")
        if gz.is_file():
            import gzip
            pdb.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(gz, "rb") as fin, open(pdb, "wb") as fout:
                fout.write(fin.read())
        else:
            raise FileNotFoundError(f"Missing rank-1 PDB for {clone_id}: {pdb}")
    return pdb


def _load_ala_mutations(clone_id: str) -> list[dict[str, Any]]:
    num_path = NUMBERING_DIR / f"{clone_id}_numbering.json"
    data = json.loads(num_path.read_text(encoding="utf-8"))
    muts = data.get("ala_scan", {}).get("mutations", [])
    if not muts:
        raise ValueError(f"No ala_scan.mutations in {num_path}")
    return muts


def _validate_and_build(
    clone_id: str,
    pdb_path: Path,
    raw_muts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pdb_aa = _parse_pdb_aa(pdb_path)
    ready: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for m in raw_muts:
        chain = m["haddock_chain"]
        resi = int(m["pdb_resi"])
        wt = m["wt"]
        obs = pdb_aa.get((chain, resi))
        row = {
            "clone": clone_id,
            "locus": m["locus"],
            "chain": chain,
            "pdb_resi": resi,
            "wt": wt,
            "mut": "A",
            "kabat_pos": m.get("kabat_pos"),
            "imgt_pos": m.get("imgt_pos"),
            "mutation": f"{chain}:{resi}:{wt}:A",
            "boltz_cli": m.get("cli_mutation"),
        }
        if obs is None:
            row["skip_reason"] = "residue_missing_in_pdb"
            skipped.append(row)
            continue
        if obs != wt:
            row["skip_reason"] = f"wt_mismatch_pdb={obs}"
            skipped.append(row)
            continue
        ready.append(row)
    return ready, skipped


def _aggregate_by_locus(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r.get("evoef2_error"):
            continue
        buckets[r["locus"]].append(r)

    summary: list[dict[str, Any]] = []
    for locus in sorted(buckets):
        vals = [x["evoef2_ddg"] for x in buckets[locus] if x.get("evoef2_ddg") is not None]
        if not vals:
            continue
        hotspots = [v for v in vals if v > HOTSPOT_DDG]
        summary.append({
            "locus": locus,
            "n_scored": len(vals),
            "n_hotspot_ddg_gt_1": len(hotspots),
            "mean_ddg": round(sum(vals) / len(vals), 4),
            "sum_positive_ddg": round(sum(max(v, 0.0) for v in vals), 4),
            "max_ddg": round(max(vals), 4),
            "min_ddg": round(min(vals), 4),
        })
    summary.sort(key=lambda x: x["sum_positive_ddg"], reverse=True)
    for i, item in enumerate(summary, start=1):
        item["rank_by_binding_impact"] = i
    return summary


def run_clone(
    clone_id: str,
    *,
    limit: int | None,
    dry_run: bool,
) -> dict[str, Any]:
    pdb_path = _rank1_pdb(clone_id)
    raw_muts = _load_ala_mutations(clone_id)
    ready, skipped = _validate_and_build(clone_id, pdb_path, raw_muts)
    if limit is not None:
        ready = ready[:limit]

    meta = {
        "clone": clone_id,
        "pdb": str(pdb_path.relative_to(ROOT)).replace("\\", "/"),
        "pdb_absolute": str(pdb_path),
        "rank1_emref": RANK1[clone_id]["emref"],
        "capri_score": RANK1[clone_id]["capri_score"],
        "dockq": RANK1[clone_id]["dockq"],
        "ab_chains": AB_CHAINS,
        "ag_chains": AG_CHAINS,
        "vam_scenario": "A",
        "tools": ["evoef2"],
        "n_input": len(raw_muts),
        "n_ready": len(ready),
        "n_skipped": len(skipped),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if dry_run:
        return {
            **meta,
            "dry_run": True,
            "ready_preview": ready[:5],
            "skipped": skipped,
            "locus_counts": dict(
                sorted(
                    {k: sum(1 for r in ready if r["locus"] == k) for k in {r["locus"] for r in ready}}.items()
                )
            ),
        }

    out_clone = OUT_DIR / clone_id / "stage2_ala_scan"
    out_clone.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 72}\n[{clone_id}] {pdb_path.name}  mutations={len(ready)}\n{'=' * 72}", flush=True)
    tk = AffinityEnergyToolkit(
        complex_pdb=str(pdb_path),
        ab_chains=AB_CHAINS,
        ag_chains=AG_CHAINS,
    )

    print(f"[{clone_id}] WT EvoEF2 baseline...", flush=True)
    wt_res = tk.run_evoef2([])
    wt_dg = wt_res.get("dg")
    meta["wt_evoef2_dg"] = wt_dg
    meta["wt_evoef2_error"] = wt_res.get("error")
    print(f"[{clone_id}] WT dg={wt_dg}  ({wt_res.get('elapsed', 0):.1f}s)", flush=True)

    results: list[dict[str, Any]] = []
    t_batch = time.time()
    for i, row in enumerate(ready, start=1):
        mutation = [{
            "chain": row["chain"],
            "resi": row["pdb_resi"],
            "wt": row["wt"],
            "mut": "A",
        }]
        r = tk.run_evoef2(mutation, wt_dg=wt_dg)
        out = {
            **row,
            "variant": r.get("variant") or f"{row['chain']}{row['pdb_resi']}{row['wt']}>A",
            "evoef2_dg": r.get("dg"),
            "evoef2_ddg": r.get("ddg"),
            "evoef2_error": r.get("error"),
            "evoef2_elapsed_s": r.get("elapsed"),
        }
        results.append(out)
        if i == 1 or i % 10 == 0 or i == len(ready):
            ddg = out["evoef2_ddg"]
            ddg_s = f"{ddg:+.3f}" if isinstance(ddg, (int, float)) else "ERR"
            print(
                f"[{clone_id}] {i:3d}/{len(ready)}  {out['mutation']:<16}  "
                f"{out['locus']:<10}  ΔΔG={ddg_s}  ({out['evoef2_elapsed_s']:.1f}s)",
                flush=True,
            )

    locus_summary = _aggregate_by_locus(results)
    meta["batch_elapsed_s"] = round(time.time() - t_batch, 1)
    meta["n_scored"] = sum(1 for r in results if r.get("evoef2_ddg") is not None)
    meta["n_errors"] = sum(1 for r in results if r.get("evoef2_error"))
    if locus_summary:
        meta["top_cdr_for_saturation"] = locus_summary[0]["locus"]

    payload = {
        "_meta": meta,
        "skipped": skipped,
        "mutations": results,
        "locus_summary": locus_summary,
    }

    json_path = out_clone / "stage2_ala_scan.json"
    csv_path = out_clone / "stage2_ala_scan.csv"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    fieldnames = [
        "clone", "locus", "chain", "pdb_resi", "wt", "mut", "mutation",
        "kabat_pos", "imgt_pos", "variant", "evoef2_ddg", "evoef2_dg",
        "evoef2_error", "evoef2_elapsed_s",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    print(f"\n[{clone_id}] CDR loop ranking (sum_positive_ddg):")
    for item in locus_summary:
        print(
            f"  #{item['rank_by_binding_impact']} {item['locus']:<10}  "
            f"hotspots={item['n_hotspot_ddg_gt_1']}  "
            f"sum_ΔΔG+={item['sum_positive_ddg']:.3f}  mean={item['mean_ddg']:+.3f}",
            flush=True,
        )
    print(f"[{clone_id}] Wrote {json_path.relative_to(ROOT)}", flush=True)
    return payload


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--clone",
        nargs="+",
        choices=sorted(RANK1),
        default=sorted(RANK1),
        help="Clone(s) to scan (default: all three).",
    )
    p.add_argument("--limit", type=int, default=None, help="Max mutations per clone (debug).")
    p.add_argument("--dry-run", action="store_true", help="Validate PDB/mutations only; no EvoEF2.")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=OUT_DIR,
        help=f"Output root (default: {OUT_DIR.relative_to(ROOT)}).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    global OUT_DIR
    OUT_DIR = args.out_dir.resolve()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_payloads: dict[str, Any] = {}
    for clone_id in args.clone:
        all_payloads[clone_id] = run_clone(clone_id, limit=args.limit, dry_run=args.dry_run)

    master = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "clones": {
            cid: {
                "n_ready": p.get("_meta", p).get("n_ready"),
                "n_skipped": p.get("_meta", p).get("n_skipped"),
                "top_cdr": p.get("_meta", p).get("top_cdr_for_saturation"),
                "output_json": (
                    str((OUT_DIR / cid / "stage2_ala_scan" / "stage2_ala_scan.json").relative_to(ROOT)).replace("\\", "/")
                    if not args.dry_run else None
                ),
            }
            for cid, p in all_payloads.items()
        },
    }
    master_path = OUT_DIR / "batch_summary.json"
    master_path.write_text(json.dumps(master, indent=2), encoding="utf-8")
    print(f"\nMaster summary: {master_path.relative_to(ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
