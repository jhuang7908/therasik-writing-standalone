#!/usr/bin/env python3
"""
 Fab （VH+CH1 / VL+CL） IgFold 。

：
  - data/design_rules/igg_like_23_three_arm_fab.json  → 23 （Common-LC）， 2  Fab
  - data/design_rules/igg_like_50_four_arm_fab.json   → 50 （KiH/CrossMab）， 4  Fab

：
  - data/design_rules/igg_like_23_three_arm_igfold_fab/  → {antibody_id}_Arm1.pdb, _Arm2.pdb
  - data/design_rules/igg_like_50_four_arm_igfold_fab/  → {antibody_id}_H1L1.pdb, _H1L2.pdb, _H2L1.pdb, _H2L2.pdb

：
  -  --verify-only （ scripts/verify_fab_sequences_bispecific.py）
  -  --verify-sequences ， IgFold，
  -  data/design_rules/igfold_fab_manifest.json（）

：pip install igfold；Chothia  anarci （reports/anarci_compat） anarcii  ABARCII， pip install anarcii。
：PyRosetta  OpenMM  do_refine=True
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RULES = PROJECT_ROOT / "data" / "design_rules"

PATH_23_FAB = DATA_RULES / "igg_like_23_three_arm_fab.json"
PATH_50_FAB = DATA_RULES / "igg_like_50_four_arm_fab.json"
OUT_23 = DATA_RULES / "igg_like_23_three_arm_igfold_fab"
OUT_50 = DATA_RULES / "igg_like_50_four_arm_igfold_fab"
MANIFEST_PATH = DATA_RULES / "igfold_fab_manifest.json"


def iter_three_arm_fabs():
    """Yield (antibody_id, arm_id, heavy_fab, light_fab) for 23 three-arm."""
    with open(PATH_23_FAB, encoding="utf-8") as f:
        data = json.load(f)
    for rec in data["per_antibody"]:
        if rec.get("error"):
            continue
        ab_id = rec["antibody_id"]
        light_fab = rec["light_fab"]
        for arm_id, heavy_key in [("Arm1", "heavy_fab_1"), ("Arm2", "heavy_fab_2")]:
            heavy_fab = rec[heavy_key]
            yield ab_id, arm_id, heavy_fab, light_fab


def iter_four_arm_fabs():
    """Yield (antibody_id, arm_id, heavy_fab, light_fab) for 50 four-arm."""
    with open(PATH_50_FAB, encoding="utf-8") as f:
        data = json.load(f)
    for rec in data["per_antibody"]:
        if rec.get("error"):
            continue
        ab_id = rec["antibody_id"]
        for arm in rec["arms"]:
            arm_id = arm["arm_id"]
            yield ab_id, arm_id, arm["heavy_fab"], arm["light_fab"]


def _apply_torch_weights_only_fix():
    """PyTorch 2.6+ defaults to weights_only=True; IgFold checkpoints need weights_only=False."""
    try:
        import torch
        if getattr(torch.load, "_igfold_patched", False):
            return
        _orig = torch.load
        def _patched(*args, **kwargs):
            kwargs.setdefault("weights_only", False)
            return _orig(*args, **kwargs)
        _patched._igfold_patched = True
        torch.load = _patched
    except Exception:
        pass


def _install_anarci_shim():
    """Use our anarcii-backed ABARCII shim so IgFold do_renum=True works without the legacy anarci package."""
    if "anarci" in sys.modules:
        return
    shim_dir = PROJECT_ROOT / "reports" / "anarci_compat"
    if not shim_dir.exists():
        return
    sys.path.insert(0, str(shim_dir))
    try:
        import anarci as _anarci  # noqa: F401
        sys.modules["anarci"] = _anarci
    except Exception:
        sys.path.pop(0)


def _apply_transformers_trie_fix():
    """Newer transformers may not expose Trie in tokenization_utils_sentencepiece; add if missing."""
    try:
        import transformers.tokenization_utils_sentencepiece as sp
        if hasattr(sp, "Trie"):
            return
        import transformers.tokenization_utils as tu
        if hasattr(tu, "Trie"):
            sp.Trie = tu.Trie
        else:
            class _TrieStub:
                def __init__(self): pass
                def add(self, *a, **k): pass
                def split(self, text): return [text]
            sp.Trie = _TrieStub
    except Exception:
        pass


def run_igfold_one(out_path: Path, heavy_fab: str, light_fab: str, do_refine: bool = False, do_renum: bool = True):
    """Run IgFold for one Fab and write PDB to out_path."""
    _apply_torch_weights_only_fix()
    _apply_transformers_trie_fix()
    _install_anarci_shim()
    try:
        from igfold import IgFoldRunner
    except ImportError:
        raise RuntimeError("IgFold not installed. Run: pip install igfold") from None

    sequences = {"H": heavy_fab, "L": light_fab}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    runner = IgFoldRunner()
    runner.fold(
        str(out_path),
        sequences=sequences,
        do_refine=do_refine,
        do_renum=do_renum,
    )


def main():
    ap = argparse.ArgumentParser(
        description="Run IgFold on all bispecific Fab sequences (23 three-arm + 50 four-arm)."
    )
    ap.add_argument(
        "--subset",
        choices=["23", "50", "all"],
        default="all",
        help="Run only 23 three-arm, only 50 four-arm, or all (default).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list tasks and output paths, do not run IgFold.",
    )
    ap.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip PDB files that already exist.",
    )
    ap.add_argument(
        "--do-refine",
        action="store_true",
        help="Refine with PyRosetta (or OpenMM if available). Default: False.",
    )
    ap.add_argument(
        "--no-renum",
        action="store_true",
        help="Disable Chothia renumbering in output PDB.",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of Fabs to run (for testing).",
    )
    ap.add_argument(
        "--verify-only",
        action="store_true",
        help="Only run sequence verification (verify_fab_sequences_bispecific.py) and exit.",
    )
    ap.add_argument(
        "--verify-sequences",
        action="store_true",
        help="Before running IgFold, run sequence verification; exit with error if any check fails.",
    )
    args = ap.parse_args()

    if args.verify_only:
        code = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "verify_fab_sequences_bispecific.py")],
            cwd=PROJECT_ROOT,
        ).returncode
        return code

    tasks = []
    if args.subset in ("23", "all"):
        for ab_id, arm_id, h, l in iter_three_arm_fabs():
            tasks.append((OUT_23, ab_id, arm_id, h, l))
    if args.subset in ("50", "all"):
        for ab_id, arm_id, h, l in iter_four_arm_fabs():
            tasks.append((OUT_50, ab_id, arm_id, h, l))

    if args.limit is not None:
        tasks = tasks[: args.limit]

    if args.verify_sequences:
        code = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "verify_fab_sequences_bispecific.py")],
            cwd=PROJECT_ROOT,
        ).returncode
        if code != 0:
            print("Sequence verification failed; aborting run.", file=sys.stderr)
            return code

    print(f"Total Fab tasks: {len(tasks)}")
    if args.dry_run:
        for out_dir, ab_id, arm_id, _, _ in tasks[:20]:
            pdb = out_dir / f"{ab_id}_{arm_id}.pdb"
            print(f"  {pdb}")
        if len(tasks) > 20:
            print(f"  ... and {len(tasks) - 20} more")
        return 0

    do_renum = not args.no_renum
    ok, skip, err = 0, 0, 0
    subset_name = "23_three_arm" if args.subset == "23" else "50_four_arm" if args.subset == "50" else "all"
    manifest_entries = []
    run_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for i, (out_dir, ab_id, arm_id, heavy_fab, light_fab) in enumerate(tasks):
        out_path = out_dir / f"{ab_id}_{arm_id}.pdb"
        h_len, l_len = len(heavy_fab.strip()), len(light_fab.strip())
        sub = "23_three_arm" if out_dir == OUT_23 else "50_four_arm"

        if args.skip_existing and out_path.exists():
            skip += 1
            manifest_entries.append({
                "antibody_id": ab_id,
                "arm_id": arm_id,
                "subset": sub,
                "output_path": str(out_path),
                "status": "skipped",
                "heavy_len": h_len,
                "light_len": l_len,
            })
            continue
        print(f"[{i+1}/{len(tasks)}] {ab_id}_{arm_id} -> {out_path.name}")
        try:
            run_igfold_one(out_path, heavy_fab, light_fab, do_refine=args.do_refine, do_renum=do_renum)
            ok += 1
            manifest_entries.append({
                "antibody_id": ab_id,
                "arm_id": arm_id,
                "subset": sub,
                "output_path": str(out_path),
                "status": "ok",
                "heavy_len": h_len,
                "light_len": l_len,
            })
        except Exception as e:
            if do_renum and "anarci" in str(e).lower():
                try:
                    run_igfold_one(out_path, heavy_fab, light_fab, do_refine=args.do_refine, do_renum=False)
                    ok += 1
                    manifest_entries.append({
                        "antibody_id": ab_id,
                        "arm_id": arm_id,
                        "subset": sub,
                        "output_path": str(out_path),
                        "status": "ok",
                        "heavy_len": h_len,
                        "light_len": l_len,
                    })
                except Exception as e2:
                    print(f"  ERROR: {e2}", file=sys.stderr)
                    err += 1
                    manifest_entries.append({
                        "antibody_id": ab_id,
                        "arm_id": arm_id,
                        "subset": sub,
                        "output_path": str(out_path),
                        "status": "error",
                        "heavy_len": h_len,
                        "light_len": l_len,
                        "error": str(e2),
                    })
            else:
                print(f"  ERROR: {e}", file=sys.stderr)
                err += 1
                manifest_entries.append({
                    "antibody_id": ab_id,
                    "arm_id": arm_id,
                    "subset": sub,
                    "output_path": str(out_path),
                    "status": "error",
                    "heavy_len": h_len,
                    "light_len": l_len,
                    "error": str(e),
                })

    run_end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "last_run_start": run_start,
        "last_run_end": run_end,
        "subset": subset_name,
        "summary": {"total": len(tasks), "ok": ok, "skipped": skip, "errors": err},
        "entries": manifest_entries,
    }
    DATA_RULES.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Manifest written: {MANIFEST_PATH}")
    print(f"Done: {ok} written, {skip} skipped (existing), {err} errors.")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
