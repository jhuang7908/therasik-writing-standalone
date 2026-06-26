#!/usr/bin/env python
"""
PAG-1 Stage-3 CDR saturation (19-AA) with EvoEF2 on HADDOCK3 rank-1 structures.

Selects top 1–2 VH CDR loops from Stage-2 Ala scan, scans every position with
standard amino acids (excluding Cys and WT), applies VAM CHECK 6 clinical CDR
fingerprint audit (AbRef-458), and writes checkpointed JSON/CSV for long local
runs. MM/GBSA is deferred to a later server pass.

Usage (repo root, conda env affmat):
  conda run -n affmat python scripts/run_pag1_stage3_saturation_batch.py
  conda run -n affmat python scripts/run_pag1_stage3_saturation_batch.py --clone 001
  conda run -n affmat python scripts/run_pag1_stage3_saturation_batch.py --resume
  conda run -n affmat python scripts/run_pag1_stage3_saturation_batch.py --dry-run
  conda run -n affmat python scripts/run_pag1_stage3_saturation_batch.py --loops vh_cdr3 vh_cdr2
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit  # noqa: E402
from core.structure.cdr_fingerprint_prior import (  # noqa: E402
    design_prior_audit,
    load_fingerprint,
)

HADDOCK_RESULTS = ROOT / "projects/PAG project/haddock3_results"
NUMBERING_DIR = ROOT / "projects/PAG project/numbering"
VAM_DIR = ROOT / "projects/PAG project/vam_ala_scan"

AB_CHAINS = ["A", "B"]
AG_CHAINS = ["C"]

RANK1: dict[str, dict[str, str]] = {
    "001": {"emref": "emref_31.pdb", "capri_score": "-72.936", "dockq": "1.000"},
    "008": {"emref": "emref_4.pdb", "capri_score": "-52.291", "dockq": "1.000"},
    "7M16": {"emref": "emref_7.pdb", "capri_score": "-63.966", "dockq": "1.000"},
}

STANDARD_AA = list("ACDEFGHIKLMNPQRSTVWY")
SATURATION_AA = [aa for aa in STANDARD_AA if aa != "C"]  # 19 AA (no Cys)

BENEFICIAL_DDG = -0.5   # VAM Phase 2 beneficial threshold (kcal/mol)
DETRIMENTAL_DDG = 2.0   # VAM Phase 2 harmful threshold
ARTIFACT_DDG = 5.0      # |ΔΔG| above → artifact flag


def _rank1_pdb(clone_id: str) -> Path:
    info = RANK1[clone_id]
    pdb = HADDOCK_RESULTS / clone_id / "run" / "4_emref" / info["emref"]
    if not pdb.is_file():
        gz = Path(str(pdb) + ".gz")
        if gz.is_file():
            pdb.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(gz, "rb") as fin, open(pdb, "wb") as fout:
                fout.write(fin.read())
        else:
            raise FileNotFoundError(f"Missing rank-1 PDB for {clone_id}: {pdb}")
    return pdb


def _mutation_key(chain: str, resi: int, wt: str, mut: str) -> str:
    return f"{chain}:{resi}:{wt}:{mut}"


def _load_numbering(clone_id: str) -> dict[str, Any]:
    path = NUMBERING_DIR / f"{clone_id}_numbering.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_stage2(clone_id: str) -> dict[str, Any]:
    path = VAM_DIR / clone_id / "stage2_ala_scan" / "stage2_ala_scan.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing Stage-2 Ala scan: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def select_loops_from_stage2(
    stage2: dict[str, Any],
    *,
    top_n: int,
    vh_only: bool,
    manual: list[str] | None,
) -> list[str]:
    if manual:
        return manual
    summary = stage2.get("locus_summary") or []
    ordered = sorted(summary, key=lambda r: r.get("rank_by_binding_impact", 999))
    picked: list[str] = []
    for row in ordered:
        locus = row["locus"]
        if vh_only and not locus.startswith("vh_"):
            continue
        picked.append(locus)
        if len(picked) >= top_n:
            break
    if not picked:
        raise ValueError("No CDR loops selected from Stage-2 locus_summary")
    return picked


def build_saturation_jobs(
    numbering: dict[str, Any],
    loops: list[str],
    fp,
    *,
    min_freq: float,
    skip_fingerprint_veto: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build EvoEF2 jobs from vh/vl cdr_operational blocks."""
    jobs: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    chain_tables = {
        "vh": numbering.get("vh", {}),
        "vl": numbering.get("vl", {}),
    }

    for locus in loops:
        prefix = locus.split("_", 1)[0]  # vh or vl
        table = chain_tables.get(prefix, {})
        op = (table.get("cdr_operational") or {}).get(locus)
        if not op or not op.get("present"):
            skipped.append({"locus": locus, "reason": "cdr_operational_missing"})
            continue

        seq = op["sequence"]
        resi_list = op["pdb_resi_list"]
        haddock_chain = op["haddock_chain"]
        if len(seq) != len(resi_list):
            skipped.append({"locus": locus, "reason": "sequence_resi_length_mismatch"})
            continue

        for pos_idx, (resi, wt) in enumerate(zip(resi_list, seq)):
            for mut in SATURATION_AA:
                if mut == wt:
                    continue
                audit = design_prior_audit(
                    fp, locus=locus, position_index=pos_idx,
                    proposed_aa=mut, min_freq=min_freq,
                )
                row = {
                    "locus": locus,
                    "chain": haddock_chain,
                    "pdb_resi": resi,
                    "wt": wt,
                    "mut": mut,
                    "position_index": pos_idx,
                    "mutation": _mutation_key(haddock_chain, resi, wt, mut),
                    "fingerprint_verdict": audit["verdict"],
                    "fingerprint_freq": audit.get("freq"),
                    "fingerprint_min_freq": min_freq,
                    "fingerprint_source": audit.get("source"),
                }
                if skip_fingerprint_veto and audit["verdict"] == "VETO":
                    row["skip_reason"] = "fingerprint_veto_pre_scan"
                    skipped.append(row)
                    continue
                jobs.append(row)

    return jobs, skipped


def _out_paths(clone_id: str, out_root: Path) -> dict[str, Path]:
    base = out_root / clone_id / "stage3_saturation"
    base.mkdir(parents=True, exist_ok=True)
    return {
        "dir": base,
        "json": base / "stage3_saturation.json",
        "csv": base / "stage3_saturation.csv",
        "checkpoint": base / "checkpoint.json",
        "recommended": base / "stage3_recommended.json",
    }


def _load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"completed_keys": [], "results": [], "wt_evoef2_dg": None}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("completed_keys", [])
    data.setdefault("results", [])
    return data


def _save_checkpoint(
    path: Path,
    *,
    clone_id: str,
    meta: dict[str, Any],
    completed_keys: list[str],
    results: list[dict[str, Any]],
    wt_dg: float | None,
) -> None:
    payload = {
        "clone": clone_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "meta": meta,
        "wt_evoef2_dg": wt_dg,
        "n_completed": len(completed_keys),
        "completed_keys": completed_keys,
        "results": results,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _classify_recommended(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in results:
        ddg = r.get("evoef2_ddg")
        if ddg is None or r.get("evoef2_error"):
            continue
        if ddg > BENEFICIAL_DDG:
            continue
        if r.get("fingerprint_verdict") == "VETO":
            continue
        if abs(ddg) > ARTIFACT_DDG:
            r = {**r, "artifact_flag": True}
        out.append(r)
    out.sort(key=lambda x: x.get("evoef2_ddg", 0.0))
    return out


def _write_outputs(
    paths: dict[str, Path],
    payload: dict[str, Any],
    results: list[dict[str, Any]],
) -> None:
    paths["json"].write_text(json.dumps(payload, indent=2), encoding="utf-8")

    fieldnames = [
        "clone", "locus", "chain", "pdb_resi", "wt", "mut", "mutation",
        "position_index", "fingerprint_verdict", "fingerprint_freq",
        "variant", "evoef2_ddg", "evoef2_dg", "evoef2_error", "evoef2_elapsed_s",
        "vam_binding_tier", "artifact_flag",
    ]
    with paths["csv"].open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    recommended = _classify_recommended(results)
    rec_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "criteria": {
            "beneficial_ddg_max": BENEFICIAL_DDG,
            "detrimental_ddg_min": DETRIMENTAL_DDG,
            "artifact_abs_ddg": ARTIFACT_DDG,
            "fingerprint_exclude_veto": True,
            "fingerprint_database": "AbRef-458 (vh_vl)",
        },
        "n_recommended": len(recommended),
        "mutations": recommended,
    }
    paths["recommended"].write_text(json.dumps(rec_payload, indent=2), encoding="utf-8")


def run_clone(
    clone_id: str,
    *,
    out_root: Path,
    top_loops: int,
    manual_loops: list[str] | None,
    vh_only: bool,
    min_freq: float,
    skip_fingerprint_veto: bool,
    resume: bool,
    checkpoint_every: int,
    limit: int | None,
    dry_run: bool,
) -> dict[str, Any]:
    stage2 = _load_stage2(clone_id)
    numbering = _load_numbering(clone_id)
    loops = select_loops_from_stage2(
        stage2, top_n=top_loops, vh_only=vh_only, manual=manual_loops,
    )
    pdb_path = _rank1_pdb(clone_id)
    fp = load_fingerprint("vh_vl")
    jobs, pre_skipped = build_saturation_jobs(
        numbering, loops, fp,
        min_freq=min_freq, skip_fingerprint_veto=skip_fingerprint_veto,
    )
    if limit is not None:
        jobs = jobs[:limit]

    paths = _out_paths(clone_id, out_root)
    ckpt = _load_checkpoint(paths["checkpoint"]) if resume else {
        "completed_keys": [], "results": [], "wt_evoef2_dg": None,
    }
    completed = set(ckpt.get("completed_keys") or [])
    results: list[dict[str, Any]] = list(ckpt.get("results") or [])
    wt_dg = ckpt.get("wt_evoef2_dg")

    meta: dict[str, Any] = {
        "clone": clone_id,
        "stage": "3_saturation_evoef2",
        "vam_scenario": "A",
        "pdb": str(pdb_path.relative_to(ROOT)).replace("\\", "/"),
        "rank1_emref": RANK1[clone_id]["emref"],
        "ab_chains": AB_CHAINS,
        "ag_chains": AG_CHAINS,
        "selected_loops": loops,
        "loop_selection": "stage2_locus_summary_top_n" if not manual_loops else "manual",
        "top_loops": top_loops,
        "vh_only": vh_only,
        "saturation_aa_count": len(SATURATION_AA),
        "n_jobs_total": len(jobs),
        "n_pre_skipped_fingerprint_veto": sum(
            1 for s in pre_skipped if s.get("skip_reason") == "fingerprint_veto_pre_scan"
        ),
        "fingerprint_min_freq": min_freq,
        "skip_fingerprint_veto_pre_scan": skip_fingerprint_veto,
        "fingerprint_database": fp.prior_source,
        "tools": ["evoef2"],
        "mmgbsa_note": "Deferred — run on server in later phase",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "resume": resume,
        "checkpoint_every": checkpoint_every,
    }

    pending = [j for j in jobs if j["mutation"] not in completed]
    meta["n_pending"] = len(pending)
    meta["n_already_completed"] = len(completed)

    print(
        f"\n{'=' * 72}\n[{clone_id}] loops={loops}  jobs={len(jobs)}  "
        f"pending={len(pending)}  resume={resume}\n{'=' * 72}",
        flush=True,
    )

    if dry_run:
        fp_counts = {"PASS": 0, "WARN": 0, "VETO": 0}
        for j in jobs:
            fp_counts[j["fingerprint_verdict"]] = fp_counts.get(j["fingerprint_verdict"], 0) + 1
        return {
            "_meta": meta,
            "dry_run": True,
            "fingerprint_job_counts": fp_counts,
            "pre_skipped": pre_skipped[:20],
            "job_preview": jobs[:5],
        }

    tk = AffinityEnergyToolkit(
        complex_pdb=str(pdb_path),
        ab_chains=AB_CHAINS,
        ag_chains=AG_CHAINS,
    )

    if wt_dg is None:
        print(f"[{clone_id}] WT EvoEF2 baseline...", flush=True)
        wt_res = tk.run_evoef2([])
        wt_dg = wt_res.get("dg")
        meta["wt_evoef2_dg"] = wt_dg
        meta["wt_evoef2_error"] = wt_res.get("error")
        print(f"[{clone_id}] WT dg={wt_dg}  ({wt_res.get('elapsed', 0):.1f}s)", flush=True)
        _save_checkpoint(
            paths["checkpoint"], clone_id=clone_id, meta=meta,
            completed_keys=sorted(completed), results=results, wt_dg=wt_dg,
        )
    else:
        meta["wt_evoef2_dg"] = wt_dg
        print(f"[{clone_id}] Resumed WT dg={wt_dg}", flush=True)

    t0 = time.time()
    for i, job in enumerate(pending, start=1):
        mutation = [{
            "chain": job["chain"],
            "resi": job["pdb_resi"],
            "wt": job["wt"],
            "mut": job["mut"],
        }]
        r = tk.run_evoef2(mutation, wt_dg=wt_dg)
        ddg = r.get("ddg")
        tier = None
        if isinstance(ddg, (int, float)):
            if ddg <= BENEFICIAL_DDG:
                tier = "beneficial"
            elif ddg >= DETRIMENTAL_DDG:
                tier = "detrimental"
            else:
                tier = "neutral"

        row = {
            **job,
            "clone": clone_id,
            "variant": r.get("variant") or f"{job['chain']}{job['pdb_resi']}{job['wt']}>{job['mut']}",
            "evoef2_dg": r.get("dg"),
            "evoef2_ddg": ddg,
            "evoef2_error": r.get("error"),
            "evoef2_elapsed_s": r.get("elapsed"),
            "vam_binding_tier": tier,
            "artifact_flag": isinstance(ddg, (int, float)) and abs(ddg) > ARTIFACT_DDG,
        }
        results.append(row)
        completed.add(job["mutation"])

        if i == 1 or i % 10 == 0 or i == len(pending):
            ddg_s = f"{ddg:+.3f}" if isinstance(ddg, (int, float)) else "ERR"
            print(
                f"[{clone_id}] {len(completed):4d}/{len(jobs)}  {job['mutation']:<18}  "
                f"{job['locus']:<10}  fp={job['fingerprint_verdict']:<4}  "
                f"ΔΔG={ddg_s}  ({row['evoef2_elapsed_s']:.1f}s)",
                flush=True,
            )

        if i % checkpoint_every == 0 or i == len(pending):
            _save_checkpoint(
                paths["checkpoint"], clone_id=clone_id, meta=meta,
                completed_keys=sorted(completed), results=results, wt_dg=wt_dg,
            )

    meta["batch_elapsed_s"] = round(time.time() - t0, 1)
    meta["n_scored"] = sum(1 for r in results if r.get("evoef2_ddg") is not None)
    meta["n_errors"] = sum(1 for r in results if r.get("evoef2_error"))
    meta["n_beneficial"] = sum(1 for r in results if r.get("vam_binding_tier") == "beneficial")
    meta["n_fingerprint_veto_results"] = sum(
        1 for r in results if r.get("fingerprint_verdict") == "VETO"
    )

    recommended = _classify_recommended(results)
    meta["n_recommended"] = len(recommended)

    payload = {
        "_meta": meta,
        "pre_skipped": pre_skipped,
        "mutations": results,
        "recommended_preview": recommended[:25],
    }
    _write_outputs(paths, payload, results)

    print(
        f"[{clone_id}] Done — beneficial={meta['n_beneficial']}  "
        f"recommended={meta['n_recommended']}  → {paths['json'].relative_to(ROOT)}",
        flush=True,
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--clone", nargs="+", choices=sorted(RANK1), default=sorted(RANK1))
    p.add_argument("--top-loops", type=int, default=2, help="Top N loops from Stage-2 (default 2).")
    p.add_argument("--loops", nargs="+", default=None, help="Override loop names, e.g. vh_cdr3 vh_cdr2.")
    p.add_argument("--include-vl", action="store_true", help="Allow VL loops in auto loop pick.")
    p.add_argument("--fingerprint-min-freq", type=float, default=0.005, help="CHECK 6 min natural freq.")
    p.add_argument(
        "--skip-fingerprint-veto",
        action="store_true",
        default=False,
        help="Skip EvoEF2 for fingerprint VETO (freq=0) candidates before scan.",
    )
    p.add_argument("--resume", action="store_true", help="Resume from checkpoint.json per clone.")
    p.add_argument("--checkpoint-every", type=int, default=10, help="Save checkpoint every N mutations.")
    p.add_argument("--limit", type=int, default=None, help="Max mutations per clone (debug).")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out-dir", type=Path, default=VAM_DIR)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out_root = args.out_dir.resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    summaries: dict[str, Any] = {}
    for clone_id in args.clone:
        summaries[clone_id] = run_clone(
            clone_id,
            out_root=out_root,
            top_loops=args.top_loops,
            manual_loops=args.loops,
            vh_only=not args.include_vl,
            min_freq=args.fingerprint_min_freq,
            skip_fingerprint_veto=args.skip_fingerprint_veto,
            resume=args.resume,
            checkpoint_every=args.checkpoint_every,
            limit=args.limit,
            dry_run=args.dry_run,
        )

    master = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "stage": "3_saturation_evoef2",
        "clones": {
            cid: {
                "loops": p.get("_meta", p).get("selected_loops"),
                "n_jobs": p.get("_meta", p).get("n_jobs_total"),
                "n_recommended": p.get("_meta", p).get("n_recommended"),
                "output_json": (
                    str((out_root / cid / "stage3_saturation" / "stage3_saturation.json")
                        .relative_to(ROOT)).replace("\\", "/")
                    if not args.dry_run else None
                ),
            }
            for cid, p in summaries.items()
        },
    }
    master_path = out_root / "stage3_batch_summary.json"
    master_path.write_text(json.dumps(master, indent=2), encoding="utf-8")
    print(f"\nMaster summary: {master_path.relative_to(ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
