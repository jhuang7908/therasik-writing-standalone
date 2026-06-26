#!/usr/bin/env python3
"""
Append Ozoralizumab arm3 (ALB8, full 117 aa) to anarcii_numbering_70.csv if missing.

Runs ABARCII on a single chain (loads model once). Then run:
  python scripts/fill_anarcii_ogrdb_germlines.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

SUITE = Path(__file__).resolve().parents[1]
RA = SUITE / "scripts/run_anarcii_numbering_70.py"


def _load_ra():
    spec = importlib.util.spec_from_file_location("run_anarcii_numbering_70", RA)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    csv_path = SUITE / "data/thera_sabdab/out/anarcii_numbering_70.csv"
    df = pd.read_csv(csv_path)
    has_vh3 = ((df["drug"].astype(str) == "Ozoralizumab") & (df["arm"] == "arm3")).any()
    if has_vh3:
        print("Ozoralizumab arm3 already present; no-op.")
        return 0

    ra = _load_ra()
    key = "Ozoralizumab|VH3"
    seq = {key: ra.OZORALIZUMAB_ALB8_VHH_AA}
    meta = {key: {"drug": "Ozoralizumab", "arm": "arm3", "chain_label": "VH3"}}

    print("Loading ABARCII (single chain) …", flush=True)
    from anarcii import Anarcii

    model = Anarcii(seq_type="antibody", mode="speed", cpu=True, batch_size=1)
    print("Numbering Ozoralizumab|VH3 …", flush=True)
    numbered = model.number(seq)
    if key not in numbered:
        print("ERROR: ABARCII did not return key", key, file=sys.stderr)
        return 1

    germline_ref = ra._load_germline_ref()
    map842 = ra._load_842_map()
    row = ra._materialize_anarcii_row(key, numbered[key], meta, germline_ref, map842)

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(csv_path, index=False)
    print(f"Appended 1 row → {csv_path.relative_to(SUITE)}")
    print("Run: python scripts/fill_anarcii_ogrdb_germlines.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
