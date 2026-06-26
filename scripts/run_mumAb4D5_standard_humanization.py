#!/usr/bin/env python3
"""
mumAb4D5  —  V4.4.1 
=========================================================================

【】（ +  +  + ）：
  python scripts/run_mumAb4D5_standard_humanization.py

  ：ImmuneBuilder 。，：
    $env:IMMUNEBUILDER_PYTHON = "d:\\Users\\NextVivo\\miniconda3\\python.exe"
  。

【 — 】
   ``data/sequence_cache/mumab4d5_verified.fasta``  ``muMAb4D5_VH`` /
  ``muMAb4D5_VL``（PDB 1FVC + ）。 109 aa（RCSB display
   **RT**）， 107 aa（ **…VEIK**）， V4.4 FR4 。
  ：``MUMAB4D5_VERIFIED_FASTA``  FASTA。

【 (V4.4.1)】
  VH:  IGHV3-23*01（CDR1=10 ，842 ）
  VL: （）—  step_2_1b canonical class  + CDR1  + 。
      mumAb4D5 VL CDR1 Kabat =15，L1 canonical class = L1-10-1。
      ：IGKV4-1*01（CDR1=17，2，L1-10-1 ，+10；Demcizumab ）。
      ：IGKV2-28*01（CDR1=16，1， canonical class L1-11-1 ，−20）。
      ：IGKV1-39*01（CDR1=11，4， ±2 ，）。

【CDR  (V4.4.1)】
   VL CDR1 （15 aa） 842  kappa 。
   V4.4.1 step_2_1b：CDR  ±2（ >2），canonical class 。
  IGKV4-1*01  canonical class ，CDR 。

【（ results.json ）】：
  python scripts/render_vhvl_v44_reports.py mumAb4D5 projects/mumab4d5_Redesign --write
  python scripts/package_delivery.py mumAb4D5 projects/mumab4d5_Redesign --zip

：projects/mumab4d5_Redesign/reports/mumab4d5_Client_zh.md(.pdf)、delivery_mumAb4D5/
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))


def _parse_fasta_records(path: Path) -> dict[str, str]:
    """
    Parse FASTA; ignores ';' comment lines.

    Supports non-standard multi-line headers (e.g. ``>SOURCE_1: ...`` after ``>id``)
    as used in ``mumab4d5_verified.fasta`` — those lines do **not** start a new record.
    """
    records: dict[str, str] = {}
    cur_id: str | None = None
    buf: list[str] = []

    def _is_meta_header(pline: str) -> bool:
        if not pline.startswith(">"):
            return False
        rest = pline[1:].strip()
        first = rest.split()[0] if rest else ""
        fl = first.lower()
        if ":" in first:
            return True
        return fl.startswith(("source", "germline", "note", "length", "cdr", "fr_"))

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith(">"):
            if _is_meta_header(line):
                continue
            if cur_id is not None:
                records[cur_id] = "".join(buf)
            cur_id = line[1:].split()[0]
            buf = []
        else:
            buf.append(line.replace(" ", ""))
    if cur_id is not None:
        records[cur_id] = "".join(buf)
    return records


def load_mumab4d5_verified_vh_vl() -> tuple[str, str]:
    """
    Load muMAb4D5 VH/VL from the verified cache (PISG + SAL single source of truth).
    VL 109 aa (…VEIKRT) → 107 aa for FR4 assembly in ``run_vhvl_v44_pipeline``.
    """
    env = os.environ.get("MUMAB4D5_VERIFIED_FASTA", "").strip()
    fasta = Path(env) if env else SUITE / "data" / "sequence_cache" / "mumab4d5_verified.fasta"
    if not fasta.is_file():
        raise FileNotFoundError(
            f"mumAb4D5 verified FASTA not found: {fasta}. "
            "Set MUMAB4D5_VERIFIED_FASTA or add data/sequence_cache/mumab4d5_verified.fasta."
        )
    rec = _parse_fasta_records(fasta)
    vh = rec.get("muMAb4D5_VH")
    vl = rec.get("muMAb4D5_VL")
    if not vh or not vl:
        raise KeyError(
            f"FASTA {fasta} must contain >muMAb4D5_VH and >muMAb4D5_VL sequence records."
        )
    # RCSB 1FVC display / patent SEQ ID NO:5: 109 aa = core 107 + C-terminal RT (non-CDR)
    if len(vl) == 109 and vl.endswith("RT"):
        vl = vl[:-2]

    return vh.upper(), vl.upper()


# VH  842  IGHV3-23*01（CDR  + ）
# VL  —  V4.4.1 step_2_1b canonical class 
FORCE_VH = "IGHV3-23*01"


def main() -> int:
    vh, vl = load_mumab4d5_verified_vh_vl()
    old_argv = sys.argv[:]
    sys.argv = [
        "run_vhvl_v44_pipeline.py",
        "--id", "mumAb4D5",
        "--vh", vh,
        "--vl", vl,
        "--force-germline-vh", FORCE_VH,
    ]
    try:
        from scripts.run_vhvl_v44_pipeline import main as pipeline_main
        return pipeline_main()
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    raise SystemExit(main())
