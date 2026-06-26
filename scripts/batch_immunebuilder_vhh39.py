#!/usr/bin/env python3
"""
Batch structure prediction for 39 clinical VHH using ImmuneBuilder NanoBodyBuilder2.

Reads: data/vhh_clinical_39_union/vhh_39_sequences_clinical_validated.json
Writes: data/vhh_clinical_39_union/immunebuilder_models/<safe_name>/
  - rank0_unrefined.pdb
  - rank0_unrefined_contig.pdb  (residues 1..N for ChimeraX)
  - meta.json

Uses the same anarci shim and renumber logic as reports/predict_nanobody_rank0_contig_from_therasabd_ab.py.
Run from repo root or with PROJECT_ROOT set; supports skip-if-exists for resumability.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "vhh_clinical_39_union"
JSON_PATH = DATA_DIR / "vhh_39_sequences_clinical_validated.json"
OUTPUT_BASE = DATA_DIR / "immunebuilder_models"

# Reports dir for anarci_compat and renumber_pdb_contiguous
REPORTS_DIR = PROJECT_ROOT / "reports"


def _insert_anarci_shim() -> None:
    shim_dir = REPORTS_DIR / "anarci_compat"
    if shim_dir.exists():
        sys.path.insert(0, str(shim_dir))


def _safe_name(name: str, index: int) -> str:
    """Filesystem-safe folder name from VHH Name."""
    s = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(name).strip())
    # collapse multiple underscores
    while "__" in s:
        s = s.replace("__", "_")
    s = s.strip("_") or f"vhh_{index}"
    return s[:120]  # cap length


def run_batch(
    *,
    numbering_scheme: str = "imgt",
    skip_existing: bool = True,
    limit: int | None = None,
) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    log = logging.getLogger(__name__)

    if not JSON_PATH.exists():
        log.error("JSON not found: %s", JSON_PATH)
        raise SystemExit(1)

    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    entries: list[dict[str, Any]] = data.get("vhh") or data.get("entries") or []
    if not entries:
        log.error("No 'vhh' (or 'entries') list in %s", JSON_PATH)
        raise SystemExit(1)

    to_run = []
    for i, rec in enumerate(entries):
        name = rec.get("Name") or rec.get("name") or f"VHH_{i}"
        seq = (rec.get("Sequence") or rec.get("sequence") or "").strip()
        if not seq:
            log.warning("Skip %s: empty sequence", name)
            continue
        to_run.append((i, name, seq))
    if limit is not None:
        to_run = to_run[: limit]
    total = len(to_run)
    log.info("Loaded %d VHH with non-empty sequence (limit=%s)", total, limit)

    _insert_anarci_shim()
    sys.path.insert(0, str(REPORTS_DIR))
    from ImmuneBuilder import NanoBodyBuilder2  # type: ignore
    from renumber_pdb_contiguous import renumber_pdb_text  # noqa: E402

    builder = NanoBodyBuilder2(numbering_scheme=numbering_scheme)
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    success = 0
    fail = 0
    t0 = time.time()
    for k, (idx, name, seq) in enumerate(to_run):
        safe = _safe_name(name, idx)
        out_dir = OUTPUT_BASE / safe
        unref = out_dir / "rank0_unrefined.pdb"
        if skip_existing and unref.exists():
            success += 1
            log.info("[%d/%d] (cached) %s", k + 1, total, safe)
            continue

        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            nb = builder.predict({"H": seq})
            best_idx = nb.ranking[0]
            nb.save_single_unrefined(str(unref), index=best_idx)
            contig = out_dir / "rank0_unrefined_contig.pdb"
            contig.write_text(
                renumber_pdb_text(
                    unref.read_text(encoding="utf-8", errors="ignore"),
                    renumber_atoms=True,
                    start_resseq=1,
                ),
                encoding="utf-8",
            )
            meta = {
                "name": name,
                "safe_name": safe,
                "sequence": seq,
                "seq_len": len(seq),
                "ranking": list(nb.ranking),
                "error_mean_by_model": [
                    float(nb.error_estimates[i].mean().item()) for i in range(len(nb.error_estimates))
                ],
                "numbering_scheme": numbering_scheme,
            }
            for key in ("Target", "Clinical_Phase", "In_Paper_Table1"):
                if key in rec and rec[key] not in (None, ""):
                    meta[key] = rec[key]
            (out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
            success += 1
            log.info("[%d/%d] [OK] %s -> %s", k + 1, total, name, out_dir)
        except Exception as e:
            fail += 1
            log.exception("[%d/%d] [FAIL] %s: %s", k + 1, total, safe, e)
        if (k + 1) % 5 == 0:
            elapsed = time.time() - t0
            avg = elapsed / (k + 1)
            remain = avg * (total - (k + 1))
            log.info(">>> Progress: %d/%d | OK=%d | FAIL=%d | ETA %.1f min", k + 1, total, success, fail, remain / 60)

    elapsed = time.time() - t0
    log.info("Done in %.1f min | success=%d | fail=%d | out=%s", elapsed / 60, success, fail, OUTPUT_BASE)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Batch ImmuneBuilder NanoBodyBuilder2 for 39 clinical VHH")
    ap.add_argument("--numbering_scheme", default="imgt", help="Numbering scheme for ImmuneBuilder")
    ap.add_argument("--no-skip", action="store_true", help="Re-run even if rank0_unrefined.pdb exists")
    ap.add_argument("--limit", type=int, default=None, help="Max number of VHH to process (default: all)")
    args = ap.parse_args()
    run_batch(
        numbering_scheme=args.numbering_scheme,
        skip_existing=not args.no_skip,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
