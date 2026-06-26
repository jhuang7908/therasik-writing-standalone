#!/usr/bin/env python
"""
PAG-1 Stage-5 MM/GBSA re-baseline (per-site WT-self repack).

Root cause fixed here: ``_evoef2_build`` returns the raw HADDOCK pose for WT
(empty mutation list) but runs EvoEF2 BuildMutant discrete repacking for every
mutant. On a strained docking pose (e.g. clone 001) this gives all mutants a
spurious ~5-8 kcal/mol "repack relief" that is not a real affinity gain.

Correct control: for every unique mutated SITE (chain,resi,wt), build a WT-self
mutation (wt->wt) so the WT baseline goes through the *identical* EvoEF2
BuildMutant + PDBFixer + OpenMM minimize pipeline at the same site. Then

    ddG_corrected(mut) = mmgbsa_dg(mut) - mmgbsa_dg(WT_self @ same site)

Mutant ``mmgbsa_dg`` values are reused from the existing Stage-5 records, so we
only pay for one WT-self MM/GBSA per *unique site* (not per mutant).

Usage (VPS, env affmat):
  OPENMM_DEFAULT_PLATFORM=CPU python scripts/recalc_pag1_stage5_persite_baseline.py \
      --suite-root /root/Antibody-Engineer-Suite-MVP \
      --vam-dir /srv/projects/pag1_vam/vam_ala_scan \
      --haddock-root /srv/projects/pag1_haddock3 --resume
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
RANK1 = {"001": "emref_31.pdb", "008": "emref_4.pdb", "7M16": "emref_7.pdb"}

BENEFICIAL = -0.5
DETRIMENTAL = 2.0
PROTOCOL_VERSION = "VAM V1.6.1"
STAGE = "5_mmgbsa_rebaseline_persite"


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
    pdb = haddock_root / clone_id / "run" / "4_emref" / RANK1[clone_id]
    if not pdb.is_file():
        gz = Path(str(pdb) + ".gz")
        if gz.is_file():
            with gzip.open(gz, "rb") as fin, open(pdb, "wb") as fout:
                fout.write(fin.read())
        else:
            raise FileNotFoundError(f"Missing rank-1 PDB: {pdb}")
    return pdb


def _ensure_platform() -> str:
    try:
        from openmm import Platform

        Platform.getPlatformByName("CUDA")
        os.environ.setdefault("OPENMM_DEFAULT_PLATFORM", "CUDA")
    except Exception:
        os.environ["OPENMM_DEFAULT_PLATFORM"] = "CPU"
    return os.environ.get("OPENMM_DEFAULT_PLATFORM", "auto")


def _site_key(chain: str, resi: int, wt: str) -> str:
    return f"{chain}:{resi}:{wt}"


def _tier(ddg: float | None) -> str | None:
    if ddg is None:
        return None
    if ddg <= BENEFICIAL:
        return "beneficial"
    if ddg >= DETRIMENTAL:
        return "detrimental"
    return "neutral"


def process_clone(
    clone_id: str,
    *,
    vam_dir: Path,
    haddock_root: Path,
    evoef2: str,
    mmgbsa_steps: int,
    resume: bool,
    replicates: int,
) -> dict[str, Any]:
    from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit

    stage5 = vam_dir / clone_id / "stage5_mmgbsa" / "stage5_mmgbsa.json"
    if not stage5.is_file():
        print(
            f"[{clone_id}] no Stage-5 records ({stage5}) — skipping re-baseline",
            flush=True,
        )
        return {
            "clone": clone_id,
            "n_records": 0,
            "n_unique_sites": 0,
            "n_beneficial_corrected": 0,
            "skipped": "no_stage5_records",
        }
    records = json.loads(stage5.read_text(encoding="utf-8")).get("records", [])

    out = vam_dir / clone_id / "stage5_rebaseline"
    out.mkdir(parents=True, exist_ok=True)
    ck_path = out / "checkpoint.json"

    # Unique sites across all mutants
    sites: dict[str, dict[str, Any]] = {}
    for r in records:
        if r.get("mmgbsa_dg") is None:
            continue
        k = _site_key(r["chain"], int(r["pdb_resi"]), r["wt"])
        sites.setdefault(k, {"chain": r["chain"], "resi": int(r["pdb_resi"]), "wt": r["wt"]})

    wt_self_dg: dict[str, Any] = {}
    if resume and ck_path.is_file():
        wt_self_dg = json.loads(ck_path.read_text(encoding="utf-8")).get("wt_self_dg", {})

    pdb_path = _rank1_pdb(haddock_root, clone_id)
    tk = AffinityEnergyToolkit(
        complex_pdb=str(pdb_path), ab_chains=AB_CHAINS, ag_chains=AG_CHAINS, evoef2_exe=evoef2
    )

    pending = [k for k in sites if k not in wt_self_dg]
    print(
        f"[{clone_id}] unique sites={len(sites)} pending={len(pending)} "
        f"done={len(wt_self_dg)} replicates={replicates}",
        flush=True,
    )

    for i, k in enumerate(pending, 1):
        s = sites[k]
        print(f"[{clone_id}] [{i}/{len(pending)}] WT-self {k}", flush=True)
        dgs = []
        for _ in range(replicates):
            res = tk.run_mmgbsa(
                [{"chain": s["chain"], "resi": s["resi"], "wt": s["wt"], "mut": s["wt"]}],
                minimization_steps=mmgbsa_steps,
            )
            if res.get("error") or res.get("dg") is None:
                dgs = []
                err = res.get("error")
                break
            dgs.append(res["dg"])
            err = None
        wt_self_dg[k] = {
            "dg": round(sum(dgs) / len(dgs), 3) if dgs else None,
            "dg_replicates": dgs,
            "error": err,
        }
        ck_path.write_text(
            json.dumps(
                {"updated_at": _utc_now(), "clone": clone_id, "wt_self_dg": wt_self_dg},
                indent=2,
            ),
            encoding="utf-8",
        )

    # Recompute corrected ddG against per-site WT-self baseline
    corrected: list[dict[str, Any]] = []
    for r in records:
        if r.get("mmgbsa_dg") is None:
            corrected.append({**r, "mmgbsa_ddg_corrected": None, "mmgbsa_tier_corrected": None})
            continue
        k = _site_key(r["chain"], int(r["pdb_resi"]), r["wt"])
        base = (wt_self_dg.get(k) or {}).get("dg")
        if base is None:
            corrected.append({**r, "mmgbsa_ddg_corrected": None, "mmgbsa_tier_corrected": None})
            continue
        ddg_c = round(r["mmgbsa_dg"] - base, 3)
        corrected.append(
            {
                **r,
                "wt_self_baseline_dg": base,
                "mmgbsa_ddg_raw": r.get("mmgbsa_ddg"),
                "mmgbsa_ddg_corrected": ddg_c,
                "mmgbsa_tier_corrected": _tier(ddg_c),
            }
        )

    beneficial = [
        c for c in corrected
        if c.get("mmgbsa_ddg_corrected") is not None and c["mmgbsa_ddg_corrected"] <= BENEFICIAL
    ]
    beneficial.sort(key=lambda c: c["mmgbsa_ddg_corrected"])

    payload = {
        "generated_at": _utc_now(),
        "protocol_version": PROTOCOL_VERSION,
        "stage": STAGE,
        "clone": clone_id,
        "baseline_method": "per_site_wt_self_repack",
        "mmgbsa_steps": mmgbsa_steps,
        "replicates": replicates,
        "n_records": len(corrected),
        "n_unique_sites": len(sites),
        "beneficial_threshold_ddg": BENEFICIAL,
        "n_beneficial_corrected": len(beneficial),
        "wt_self_dg": wt_self_dg,
        "records": corrected,
        "beneficial_corrected": beneficial,
    }
    (out / "stage5_mmgbsa_corrected.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (out / "stage5_beneficial_corrected.json").write_text(
        json.dumps(
            {
                "generated_at": payload["generated_at"],
                "clone": clone_id,
                "baseline_method": "per_site_wt_self_repack",
                "n_beneficial": len(beneficial),
                "mutations": beneficial,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    fields = [
        "clone", "variant", "mutation_key", "locus", "chain", "pdb_resi", "wt", "mut",
        "evoef2_ddg", "mmgbsa_dg", "wt_self_baseline_dg",
        "mmgbsa_ddg_raw", "mmgbsa_ddg_corrected", "mmgbsa_tier_corrected",
    ]
    with (out / "stage5_mmgbsa_corrected.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for c in corrected:
            w.writerow(c)

    return {
        "clone": clone_id,
        "n_records": len(corrected),
        "n_unique_sites": len(sites),
        "n_beneficial_corrected": len(beneficial),
        "output_dir": str(out),
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="PAG-1 Stage-5 per-site WT-self re-baseline")
    p.add_argument("--suite-root", type=Path, default=ROOT)
    p.add_argument("--vam-dir", type=Path, default=ROOT / "projects/PAG project/vam_ala_scan")
    p.add_argument("--haddock-root", type=Path, default=ROOT / "projects/PAG project/haddock3_results")
    p.add_argument("--clone", choices=CLONES, action="append")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--mmgbsa-steps", type=int, default=300)
    p.add_argument("--replicates", type=int, default=1, help="WT-self MM/GBSA replicates to average (noise control)")
    p.add_argument("--evoef2", default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    suite_root = args.suite_root.resolve()
    if str(suite_root) not in sys.path:
        sys.path.insert(0, str(suite_root))

    evoef2 = args.evoef2 or _default_evoef2(suite_root)
    if not Path(evoef2).is_file():
        print(f"ERROR: EvoEF2 not found at {evoef2}", file=sys.stderr)
        return 1

    plat = _ensure_platform()
    print(f"OpenMM platform: {plat}", flush=True)

    clones = args.clone or CLONES
    summary = {
        "generated_at": _utc_now(),
        "protocol_version": PROTOCOL_VERSION,
        "stage": STAGE,
        "baseline_method": "per_site_wt_self_repack",
        "clones": {},
    }
    for clone_id in clones:
        print(f"\n=== Re-baseline clone {clone_id} ===", flush=True)
        summary["clones"][clone_id] = process_clone(
            clone_id,
            vam_dir=args.vam_dir.resolve(),
            haddock_root=args.haddock_root.resolve(),
            evoef2=evoef2,
            mmgbsa_steps=args.mmgbsa_steps,
            resume=args.resume,
            replicates=args.replicates,
        )
    out = args.vam_dir.resolve() / "stage5_rebaseline_summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nRe-baseline summary: {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
