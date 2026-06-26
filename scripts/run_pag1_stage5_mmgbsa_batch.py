#!/usr/bin/env python
"""
PAG-1 VAM Stage-5 MM/GBSA confirmation on Stage-4 shortlist (VPS / Linux).

Reads ``stage4_shortlist.json`` per clone, runs OpenMM MM/GBSA on HADDOCK3
rank-1 complexes with checkpoint/resume. Intended for GPU/CPU server batch
after local Stage-4 gates (MM/GBSA deferred).

Usage (repo root, conda env affmat):
  python scripts/run_pag1_stage5_mmgbsa_batch.py --suite-root /root/Antibody-Engineer-Suite-MVP \\
      --vam-dir /srv/projects/pag1_vam/vam_ala_scan \\
      --haddock-root /srv/projects/pag1_haddock3 --resume

  python scripts/run_pag1_stage5_mmgbsa_batch.py --clone 001 --resume --mmgbsa-steps 300
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

AB_CHAINS = ["A", "B"]
AG_CHAINS = ["C"]
CLONES = ["001", "008", "7M16"]

RANK1: dict[str, str] = {
    "001": "emref_31.pdb",
    "008": "emref_4.pdb",
    "7M16": "emref_7.pdb",
}

MMGBSA_BENEFICIAL = -0.5  # kcal/mol vs WT (align with VAM Phase 2)
PROTOCOL_VERSION = "VAM V1.6.1"
STAGE = "5_mmgbsa_confirmation"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_evoef2(suite_root: Path) -> str:
    base = suite_root / "tools" / "EvoEF2_src"
    for name in ("EvoEF2", "EvoEF2.exe"):
        p = base / name
        if p.is_file():
            return str(p)
    return str(base / "EvoEF2")


def _rank1_pdb(haddock_root: Path, clone_id: str) -> Path:
    emref = RANK1[clone_id]
    pdb = haddock_root / clone_id / "run" / "4_emref" / emref
    if not pdb.is_file():
        gz = Path(str(pdb) + ".gz")
        if gz.is_file():
            pdb.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(gz, "rb") as fin, open(pdb, "wb") as fout:
                fout.write(fin.read())
        else:
            raise FileNotFoundError(f"Missing rank-1 PDB: {pdb}")
    return pdb


def _to_mut(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "chain": row["chain"],
        "resi": int(row["pdb_resi"]),
        "wt": row["wt"],
        "mut": row["mut"],
    }


def _mut_key(row: dict[str, Any]) -> str:
    return row.get("mutation_key") or row.get("mutation") or (
        f"{row['chain']}:{row['pdb_resi']}:{row['wt']}:{row['mut']}"
    )


def _out_dir(vam_dir: Path, clone_id: str) -> Path:
    d = vam_dir / clone_id / "stage5_mmgbsa"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_shortlist(vam_dir: Path, clone_id: str) -> list[dict[str, Any]]:
    path = vam_dir / clone_id / "stage4_postfilter" / "stage4_shortlist.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing Stage-4 shortlist: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("mutations") or [])


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    fields = [
        "clone", "variant", "mutation_key", "locus", "chain", "pdb_resi", "wt", "mut",
        "evoef2_ddg", "mmgbsa_dg", "mmgbsa_ddg", "mmgbsa_tier", "mmgbsa_error",
        "elapsed_s", "updated_at",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow(r)


def _save_bundle(
    out: Path,
    *,
    clone_id: str,
    records: list[dict[str, Any]],
    meta: dict[str, Any],
) -> None:
    beneficial = [
        r for r in records
        if r.get("mmgbsa_ddg") is not None and r["mmgbsa_ddg"] <= MMGBSA_BENEFICIAL
        and not r.get("mmgbsa_error")
    ]
    payload = {
        "generated_at": _utc_now(),
        "protocol_version": PROTOCOL_VERSION,
        "stage": STAGE,
        "clone": clone_id,
        "meta": meta,
        "n_input": len(records),
        "n_completed": sum(1 for r in records if r.get("mmgbsa_ddg") is not None or r.get("mmgbsa_error")),
        "n_beneficial": len(beneficial),
        "beneficial_threshold_ddg": MMGBSA_BENEFICIAL,
        "records": records,
        "beneficial": beneficial,
    }
    (out / "stage5_mmgbsa.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (out / "stage5_mmgbsa_beneficial.json").write_text(
        json.dumps(
            {
                "generated_at": payload["generated_at"],
                "clone": clone_id,
                "n_beneficial": len(beneficial),
                "mutations": beneficial,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_csv(out / "stage5_mmgbsa.csv", records)


def _ensure_openmm_platform() -> None:
    """Prefer CUDA when present; otherwise force CPU (VPS has no GPU)."""
    try:
        from openmm import Platform

        Platform.getPlatformByName("CUDA")
        os.environ.setdefault("OPENMM_DEFAULT_PLATFORM", "CUDA")
    except Exception:
        os.environ["OPENMM_DEFAULT_PLATFORM"] = "CPU"


def process_clone(
    clone_id: str,
    *,
    suite_root: Path,
    vam_dir: Path,
    haddock_root: Path,
    evoef2: str,
    mmgbsa_steps: int,
    resume: bool,
    limit: int | None,
) -> dict[str, Any]:
    from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit

    out = _out_dir(vam_dir, clone_id)
    ck_path = out / "checkpoint.json"
    shortlist = _load_shortlist(vam_dir, clone_id)
    if limit is not None:
        shortlist = shortlist[:limit]

    records: list[dict[str, Any]] = []
    done_keys: set[str] = set()
    wt_mmgbsa_dg: float | None = None

    if resume and ck_path.is_file():
        ck = json.loads(ck_path.read_text(encoding="utf-8"))
        records = ck.get("records") or []
        done_keys = {_mut_key(r) for r in records}
        wt_mmgbsa_dg = ck.get("wt_mmgbsa_dg")

    pdb_path = _rank1_pdb(haddock_root, clone_id)
    pending = [r for r in shortlist if _mut_key(r) not in done_keys]

    tk = AffinityEnergyToolkit(
        complex_pdb=str(pdb_path),
        ab_chains=AB_CHAINS,
        ag_chains=AG_CHAINS,
        evoef2_exe=evoef2,
    )

    meta = {
        "rank1_pdb": str(pdb_path),
        "evoef2": evoef2,
        "mmgbsa_steps": mmgbsa_steps,
        "suite_root": str(suite_root),
    }

    print(f"[{clone_id}] Stage-5 MM/GBSA pending={len(pending)} done={len(done_keys)}", flush=True)

    if wt_mmgbsa_dg is None and pending:
        print(f"[{clone_id}] Computing WT MM/GBSA baseline...", flush=True)
        t0 = time.time()
        wt_res = tk.run_mmgbsa([], minimization_steps=mmgbsa_steps)
        wt_mmgbsa_dg = wt_res.get("dg")
        meta["wt_mmgbsa"] = wt_res
        print(
            f"[{clone_id}] WT MM/GBSA dg={wt_mmgbsa_dg} "
            f"({wt_res.get('elapsed')}s err={wt_res.get('error')})",
            flush=True,
        )
        if wt_res.get("error") and wt_mmgbsa_dg is None:
            raise RuntimeError(f"WT MM/GBSA failed: {wt_res['error']}")

    for i, row in enumerate(pending, 1):
        key = _mut_key(row)
        variant = row.get("variant", key)
        print(f"[{clone_id}] [{i}/{len(pending)}] {variant}", flush=True)
        t0 = time.time()
        mut = [_to_mut(row)]
        res = tk.run_mmgbsa(mut, wt_dg=wt_mmgbsa_dg, minimization_steps=mmgbsa_steps)
        ddg = res.get("ddg")
        tier = None
        if ddg is not None and not res.get("error"):
            if ddg <= MMGBSA_BENEFICIAL:
                tier = "beneficial"
            elif ddg >= 2.0:
                tier = "detrimental"
            else:
                tier = "neutral"

        rec = {
            **row,
            "clone": clone_id,
            "mutation_key": key,
            "mmgbsa_dg": res.get("dg"),
            "mmgbsa_ddg": ddg,
            "mmgbsa_tier": tier,
            "mmgbsa_error": res.get("error"),
            "mmgbsa_elapsed_s": res.get("elapsed"),
            "mmgbsa_e_complex": res.get("e_complex"),
            "mmgbsa_e_ab": res.get("e_ab"),
            "mmgbsa_e_ag": res.get("e_ag"),
            "elapsed_s": round(time.time() - t0, 2),
            "updated_at": _utc_now(),
        }
        records.append(rec)
        ck_path.write_text(
            json.dumps(
                {
                    "updated_at": _utc_now(),
                    "clone": clone_id,
                    "wt_mmgbsa_dg": wt_mmgbsa_dg,
                    "n_done": len(records),
                    "records": records,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        _save_bundle(out, clone_id=clone_id, records=records, meta=meta)

    n_ben = sum(
        1 for r in records
        if r.get("mmgbsa_ddg") is not None and r["mmgbsa_ddg"] <= MMGBSA_BENEFICIAL
        and not r.get("mmgbsa_error")
    )
    return {
        "clone": clone_id,
        "n_input": len(shortlist),
        "n_done": len(records),
        "n_beneficial": n_ben,
        "output_dir": str(out),
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="PAG-1 Stage-5 MM/GBSA batch (checkpoint/resume)")
    p.add_argument("--suite-root", type=Path, default=ROOT, help="AbEngineCore repo root on this machine")
    p.add_argument(
        "--vam-dir",
        type=Path,
        default=ROOT / "projects/PAG project/vam_ala_scan",
        help="vam_ala_scan root (shortlists + stage5 output)",
    )
    p.add_argument(
        "--haddock-root",
        type=Path,
        default=ROOT / "projects/PAG project/haddock3_results",
        help="HADDOCK3 results root ({clone}/run/4_emref/)",
    )
    p.add_argument("--clone", choices=CLONES, action="append")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--mmgbsa-steps", type=int, default=300)
    p.add_argument("--evoef2", default=None, help="EvoEF2 binary (default: auto under suite-root)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    suite_root = args.suite_root.resolve()
    if str(suite_root) not in sys.path:
        sys.path.insert(0, str(suite_root))

    evoef2 = args.evoef2 or _default_evoef2(suite_root)
    if not Path(evoef2).is_file():
        print(f"ERROR: EvoEF2 not found at {evoef2}", file=sys.stderr)
        print("On Linux VPS: cd tools/EvoEF2_src && bash build.sh", file=sys.stderr)
        return 1

    _ensure_openmm_platform()
    print(f"OpenMM platform: {os.environ.get('OPENMM_DEFAULT_PLATFORM', 'auto')}", flush=True)

    clones = args.clone or CLONES
    summary = {
        "generated_at": _utc_now(),
        "protocol_version": PROTOCOL_VERSION,
        "stage": STAGE,
        "clones": {},
    }

    for clone_id in clones:
        print(f"\n=== PAG-1 Stage-5 MM/GBSA clone {clone_id} ===", flush=True)
        summary["clones"][clone_id] = process_clone(
            clone_id,
            suite_root=suite_root,
            vam_dir=args.vam_dir.resolve(),
            haddock_root=args.haddock_root.resolve(),
            evoef2=evoef2,
            mmgbsa_steps=args.mmgbsa_steps,
            resume=args.resume,
            limit=args.limit,
        )

    out_summary = args.vam_dir.resolve() / "stage5_batch_summary.json"
    out_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nBatch summary: {out_summary}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
