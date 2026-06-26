#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
：
  - Clinical：data/vhh_clinical_39_union/immunebuilder_models/<name>/
  - Database B：data/vhh_database_b_union/immunebuilder_models/<safe_id>/

：data/vhh_structural_union/vhh_structural_union_index.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
CLINICAL = REPO / "data" / "vhh_clinical_39_union" / "immunebuilder_models"
DB_B = REPO / "data" / "vhh_database_b_union"
OUT = REPO / "data" / "vhh_structural_union" / "vhh_structural_union_index.json"


def _clinical_entries() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not CLINICAL.is_dir():
        return out
    for d in sorted(CLINICAL.iterdir()):
        if not d.is_dir():
            continue
        meta = d / "meta.json"
        pdb = d / "rank0_unrefined.pdb"
        if not pdb.is_file():
            continue
        row: Dict[str, Any] = {
            "source_set": "clinical_vhh_immunbuilder",
            "id": d.name,
            "pdb_model": str(pdb.relative_to(REPO)),
        }
        if meta.is_file():
            try:
                m = json.loads(meta.read_text(encoding="utf-8"))
                row["sequence"] = m.get("sequence", "")
                row["seq_len"] = m.get("seq_len", len(row.get("sequence") or ""))
            except Exception:
                pass
        out.append(row)
    return out


def _db_b_entries() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seq_path = DB_B / "database_b_sequences.json"
    if not seq_path.is_file():
        return out
    data = json.loads(seq_path.read_text(encoding="utf-8"))
    for ent in data.get("entries", []):
        sid = ent.get("safe_id", "")
        pred = ent.get("predicted_pdb")
        if not pred:
            p = DB_B / "immunebuilder_models" / sid / "rank0_unrefined.pdb"
            if p.is_file():
                pred = str(p.relative_to(REPO))
        if not pred:
            continue
        out.append(
            {
                "source_set": "database_b_humanized_camelid_nanobuilder",
                "id": sid,
                "pdb": ent.get("pdb"),
                "Hchain": ent.get("Hchain"),
                "sequence": ent.get("sequence", ""),
                "pdb_model": pred,
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    clinical = _clinical_entries()
    db_b = _db_b_entries()
    idx = {
        "_meta": {
            "description": "ImmuneBuilder clinical + NanoBodyBuilder2 Database B; unified for spatial microenv scripts",
            "clinical_n": len(clinical),
            "database_b_n": len(db_b),
            "total_n": len(clinical) + len(db_b),
        },
        "clinical_vhh": clinical,
        "database_b": db_b,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {args.out}  clinical={len(clinical)}  database_b={len(db_b)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
