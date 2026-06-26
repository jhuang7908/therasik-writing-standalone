#!/usr/bin/env python3
"""
Batch compute 5 TAP metrics for CSV datasets and append as new columns.

TAP Metrics: total_cdr_length, psh, ppc, pnc, sfvcsp
(requires valid Kabat CDRs — from CSV vh_cdr* / vl_cdr* columns, or from Anarcii
Kabat numbering (no HMMER) on sequences read from the PDB Fv chains when
those columns are absent, e.g. 842 file.)

Usage:
  conda run -n anarcii python scripts/batch_compute_tap_metrics.py
  conda run -n anarcii python scripts/batch_compute_tap_metrics.py --max-rows 5
  conda run -n anarcii python scripts/batch_compute_tap_metrics.py --only data/natural_380_atlas/master_table.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))

from Bio.PDB import PDBParser  # noqa: E402
from Bio.PDB.Polypeptide import is_aa
from Bio.SeqUtils import seq1

from core.evaluation.tap import TAP_Analyzer  # noqa: E402
from core.humanization.kabat_utils import (  # noqa: E402
    CDR_RANGES_VH,
    CDR_RANGES_VL,
    cdr_span,
    get_kabat_numbering,
)

CSV_DEFAULTS = [
    SUITE / "data" / "natural_380_atlas" / "master_table.csv",
    SUITE / "data" / "humanization_assay" / "842_combined_assessment.csv",
]

NEW_COLS = ["total_cdr_length", "psh", "ppc", "pnc", "sfvcsp"]


def find_pdb(pdb_path_str: str) -> Optional[Path]:
    if not pdb_path_str:
        return None
    fname = Path(pdb_path_str.replace("\\", "/")).name
    direct_path = Path(pdb_path_str)
    if direct_path.exists():
        return direct_path
    for p in (SUITE / "data" / "structures").rglob(fname):
        return p
    return None


def _seq1_from_chain(model, chain_id: str) -> str:
    if chain_id not in model:
        return ""
    out: List[str] = []
    for r in model[chain_id]:
        if is_aa(r, standard=False):
            out.append(seq1(r.get_resname(), custom_map={"MSE": "M"}))
    return "".join(out)


def _cdrs_from_seqs_anarcii(
    vh_seq: str,
    vl_seq: str,
    anarcii_engine: Any,
) -> Optional[Dict[str, str]]:
    """Kabat CDRs via Anarcii (no HMMER) + kabat_utils cdr_span."""
    kd_h = get_kabat_numbering(vh_seq, anarcii_engine)
    kd_l = get_kabat_numbering(vl_seq, anarcii_engine)
    if not kd_h or not kd_l:
        return None
    cdr_h_names: Tuple[str, str, str] = ("H1", "H2", "H3")
    cdr_l_names: Tuple[str, str, str] = ("L1", "L2", "L3")
    out: Dict[str, str] = {}
    for n, (lo, hi) in zip(cdr_h_names, CDR_RANGES_VH):
        out[n] = cdr_span(kd_h, lo, hi)
    for n, (lo, hi) in zip(cdr_l_names, CDR_RANGES_VL):
        out[n] = cdr_span(kd_l, lo, hi)
    if not any(out.values()):
        return None
    return out


def cdr_seqs_from_row_or_pdb(
    row: Dict[str, str],
    pdb_path: Path,
    *,
    anarcii_engine: Any,
) -> Optional[Dict[str, str]]:
    h1 = (row.get("vh_cdr1") or "").strip()
    if h1 and row.get("vh_cdr2") and row.get("vh_cdr3"):
        return {
            "H1": row.get("vh_cdr1", ""),
            "H2": row.get("vh_cdr2", ""),
            "H3": row.get("vh_cdr3", ""),
            "L1": row.get("vl_cdr1", ""),
            "L2": row.get("vl_cdr2", ""),
            "L3": row.get("vl_cdr3", ""),
        }

    parser = PDBParser(QUIET=True)
    struct = parser.get_structure("m", str(pdb_path))
    model = struct[0]
    _h = (row.get("chain_vh") or "H").strip()
    _l = (row.get("chain_vl") or "L").strip()
    vh_ch, vl_ch = (_h[0] if _h else "H"), (_l[0] if _l else "L")
    vh_seq = _seq1_from_chain(model, vh_ch)
    vl_seq = _seq1_from_chain(model, vl_ch)
    if len(vh_seq) < 50 or len(vl_seq) < 40:
        return None
    return _cdrs_from_seqs_anarcii(vh_seq, vl_seq, anarcii_engine)


def process_csv(
    csv_path: Path,
    *,
    max_rows: Optional[int] = None,
) -> None:
    print(f"--- Processing {csv_path.name} ---", flush=True)
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        return

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, str]] = list(reader)
        fieldnames = list(reader.fieldnames or [])

    for col in NEW_COLS:
        if col not in fieldnames:
            fieldnames.append(col)

    from anarcii import Anarcii  # noqa: PLC0415  (env-specific; heavy init once)

    an_engine: Any = Anarcii()
    processed = 0
    errors = 0
    skipped = 0
    t0 = time.time()
    n_limit = max_rows

    for i, row in enumerate(rows):
        if n_limit is not None and processed >= n_limit:
            break

        if all(str(row.get(c) or "").strip() for c in NEW_COLS):
            skipped += 1
            continue

        pdb_path_str = row.get("pdb_path", "") or ""
        pdb_file = find_pdb(pdb_path_str)
        if not pdb_file:
            print(
                f"[{i+1}/{len(rows)}] PDB not found: "
                f"{row.get('antibody_id', 'unknown')}"
            )
            errors += 1
            continue

        cdr_seqs = cdr_seqs_from_row_or_pdb(
            row, pdb_file, anarcii_engine=an_engine
        )
        if not cdr_seqs or not any(cdr_seqs.values()):
            print(
                f"[{i+1}/{len(rows)}] No CDRs (add columns or Anarcii+Kabat): "
                f"{row.get('antibody_id', 'unknown')}"
            )
            errors += 1
            continue

        _hr = (row.get("chain_vh") or "H").strip()
        _lr = (row.get("chain_vl") or "L").strip()
        vhc, vlc = (
            _hr[0] if _hr else "H",
            _lr[0] if _lr else "L",
        )
        try:
            tap = TAP_Analyzer(
                pdb_path=str(pdb_file),
                vh_chain=vhc,
                vl_chain=vlc,
                cdr_seqs=cdr_seqs,
            )
            res = tap.analyze()
            for col in NEW_COLS:
                v = res.get(col)
                row[col] = v if v is not None and v != "" else ""
            processed += 1
            if processed % 20 == 0:
                dt = (time.time() - t0) / max(processed, 1)
                print(
                    f"[{i+1}/{len(rows)}] TAP ok×{processed}  ({dt:.1f}s/row)"
                )
        except Exception as e:
            print(
                f"[{i+1}/{len(rows)}] Error {pdb_file.name}: {e!r}"
            )
            errors += 1

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=fieldnames, extrasaction="ignore"
        )
        w.writeheader()
        w.writerows(rows)

    print(
        f"Done. TAP computed: {processed}, errors: {errors}, "
        f"already-filled skipped: {skipped}, {time.time()-t0:.1f}s",
        flush=True,
    )
    print(flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Append TAP metrics columns to master / 842 CSVs."
    )
    ap.add_argument(
        "--only",
        type=str,
        default="",
        help="Single CSV path relative to suite or absolute",
    )
    ap.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Process at most this many new TAP rows (smoke test)",
    )
    args = ap.parse_args()

    if args.only:
        p = Path(args.only)
        if not p.is_absolute():
            p = SUITE / p
        targets = [p]
    else:
        targets = list(CSV_DEFAULTS)

    for p in targets:
        process_csv(p, max_rows=args.max_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
