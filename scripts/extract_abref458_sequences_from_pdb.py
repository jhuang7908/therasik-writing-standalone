#!/usr/bin/env python3
"""
extract_abref458_sequences_from_pdb.py — Extract VH/VL sequences from 458 PDBs.
================================================================================
Reads structure_metrics_summary.json (pdb_path, chain_vh, chain_vl per antibody),
extracts sequences from PDBs, writes AbRef458_sequences.json for the reference build.

Usage:
  python scripts/extract_abref458_sequences_from_pdb.py

Output:
  data/reference/AbRef458_sequences.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SUITE_ROOT = Path(__file__).resolve().parents[1]
if str(_SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SUITE_ROOT))

_METRICS_PATH = _SUITE_ROOT / "data" / "humanization_assay" / "structure_metrics_summary.json"
_OUTPUT_PATH = _SUITE_ROOT / "data" / "reference" / "AbRef458_sequences.json"


def _extract_sequences_from_pdb(
    pdb_path: Path, chain_vh: str = "H", chain_vl: str = "L"
) -> Tuple[Optional[str], Optional[str], List[str]]:
    """Extract VH and VL one-letter sequences from PDB. Returns (vh_seq, vl_seq, errors)."""
    errors: List[str] = []
    try:
        from Bio.PDB import PDBParser
        from Bio.PDB.Polypeptide import is_aa
    except ImportError:
        return None, None, ["BioPython not available"]
    AA3_TO_1 = {
        "ALA": "A", "CYS": "C", "ASP": "D", "GLU": "E", "PHE": "F",
        "GLY": "G", "HIS": "H", "ILE": "I", "LYS": "K", "LEU": "L",
        "MET": "M", "ASN": "N", "PRO": "P", "GLN": "Q", "ARG": "R",
        "SER": "S", "THR": "T", "VAL": "V", "TRP": "W", "TYR": "Y",
    }
    if not pdb_path.exists():
        return None, None, [f"PDB not found: {pdb_path}"]
    parser = PDBParser(QUIET=True)
    try:
        structure = parser.get_structure("ab", str(pdb_path))
    except Exception as e:
        return None, None, [f"PDB parse: {e}"]
    model = structure[0]
    if chain_vh not in model or chain_vl not in model:
        return None, None, [f"Chains {chain_vh}/{chain_vl} not found"]

    def chain_seq(chain) -> str:
        seq_list = []
        for r in chain.get_residues():
            if not is_aa(r, standard=True):
                continue
            seq_list.append(AA3_TO_1.get(r.get_resname(), "X"))
        return "".join(seq_list)

    vh_seq = chain_seq(model[chain_vh])
    vl_seq = chain_seq(model[chain_vl])
    if not vh_seq or not vl_seq:
        return None, None, ["Empty chain sequence"]
    return vh_seq, vl_seq, []


def main() -> int:
    if not _METRICS_PATH.exists():
        print(f"[ERROR] Metrics file not found: {_METRICS_PATH}")
        return 1

    with open(_METRICS_PATH, encoding="utf-8") as f:
        metrics_list = json.load(f)

    antibodies: List[Dict[str, Any]] = []
    skipped = 0
    for i, m in enumerate(metrics_list):
        pdb_rel = m.get("pdb_path", "")
        pdb_path = (_SUITE_ROOT / pdb_rel.replace("\\", "/")).resolve()
        chain_vh = m.get("chain_vh", "H")
        chain_vl = m.get("chain_vl", "L")
        ab_id = pdb_path.stem if pdb_path else f"AB{i+1:03d}"

        vh_seq, vl_seq, errs = _extract_sequences_from_pdb(pdb_path, chain_vh, chain_vl)
        if errs:
            print(f"[WARN] {ab_id}: {errs[0]}")
            skipped += 1
            continue

        antibodies.append({
            "id": ab_id,
            "VH": vh_seq or "",
            "VL": vl_seq or "",
        })

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "dataset": "AbRef458",
        "description": "458 gene-engineered humanized antibody VH/VL sequences extracted from PDB.",
        "antibodies": antibodies,
    }
    with open(_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"[OK] Extracted {len(antibodies)} sequences → {_OUTPUT_PATH}")
    if skipped:
        print(f"[WARN] Skipped {skipped} antibodies due to extraction errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
