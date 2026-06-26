#!/usr/bin/env python
"""
PAG-1 VAM Stage-4 sequential post-filter on relaxed Boltz structures (V1.6.1).

Same gate order as ``run_pag1_vam_postfilter.py``, but reads Stage-3 outputs from
``projects/PAG project/vam_boltz_scan`` and uses ``boltz_relaxed_qc/*_relaxed.pdb``.

Usage (repo root, conda env affmat):
  python scripts/run_pag1_vam_postfilter_boltz.py
  python scripts/run_pag1_vam_postfilter_boltz.py --clone 001 --resume
  python scripts/run_pag1_vam_postfilter_boltz.py --skip-check8
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.run_pag1_vam_postfilter as pf

QC_DIR = ROOT / "projects/PAG project/boltz_relaxed_qc"

RELAXED_PDBS = {
    "001": "001_relaxed.pdb",
    "008": "008_relaxed.pdb",
    "7M16": "7M16_relaxed.pdb",
}

pf.VAM_DIR = ROOT / "projects/PAG project/vam_boltz_scan"
pf.STAGE = "4_sequential_postfilter_boltz"
pf.PROTOCOL_VERSION = "VAM V1.6.1 (Boltz baseline)"


def _relaxed_pdb(clone_id: str) -> Path:
    pdb = QC_DIR / RELAXED_PDBS[clone_id]
    if not pdb.is_file():
        raise FileNotFoundError(f"Missing relaxed Boltz PDB for {clone_id}: {pdb}")
    return pdb


pf._rank1_pdb = _relaxed_pdb


if __name__ == "__main__":
    raise SystemExit(pf.main())
