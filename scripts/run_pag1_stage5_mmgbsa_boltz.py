#!/usr/bin/env python
"""
PAG-1 VAM Stage-5 MM/GBSA on relaxed Boltz structures (V1.6.1, Boltz baseline).

Thin wrapper over ``run_pag1_stage5_mmgbsa_batch.py``: reuses the full batch
logic (checkpoint/resume, WT baseline, per-mutant MM/GBSA) but resolves the
complex PDB from the relaxed Boltz QC directory instead of HADDOCK emref poses.

The ``--haddock-root`` argument is repurposed as the Boltz QC directory that
holds ``{clone}_relaxed.pdb``. ``--vam-dir`` must point at ``vam_boltz_scan``.

Usage (VPS, env affmat):
  OPENMM_DEFAULT_PLATFORM=CPU python scripts/run_pag1_stage5_mmgbsa_boltz.py \
      --suite-root /root/Antibody-Engineer-Suite-MVP \
      --vam-dir /srv/projects/pag1_vam/vam_boltz_scan \
      --haddock-root /srv/projects/pag1_vam/boltz_relaxed_qc \
      --resume --mmgbsa-steps 300
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.run_pag1_stage5_mmgbsa_batch as s5

RELAXED_PDBS = {
    "001": "001_relaxed.pdb",
    "008": "008_relaxed.pdb",
    "7M16": "7M16_relaxed.pdb",
}


def _boltz_pdb(qc_root: Path, clone_id: str) -> Path:
    pdb = Path(qc_root) / RELAXED_PDBS[clone_id]
    if not pdb.is_file():
        raise FileNotFoundError(f"Missing relaxed Boltz PDB for {clone_id}: {pdb}")
    return pdb


s5._rank1_pdb = _boltz_pdb
s5.PROTOCOL_VERSION = "VAM V1.6.1 (Boltz baseline)"
s5.STAGE = "5_mmgbsa_confirmation_boltz"


if __name__ == "__main__":
    raise SystemExit(s5.main())
