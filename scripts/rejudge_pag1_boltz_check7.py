#!/usr/bin/env python
"""Re-judge CHECK 7 (sequence liability) on PAG-1 Boltz Stage-4 outputs.

Uses corrected chain_records index mapping in run_pag1_vam_postfilter._run_check7.
Updates check_7 verdict + overall_status + shortlist + batch summary counts.
Run validate_pag1_stage4_audit.py after this to confirm PASS.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.run_pag1_vam_postfilter as pf

VAM_DIR = ROOT / "projects/PAG project/vam_boltz_scan"
QC_DIR = ROOT / "projects/PAG project/boltz_relaxed_qc"
RELAXED_PDBS = {"001": "001_relaxed.pdb", "008": "008_relaxed.pdb", "7M16": "7M16_relaxed.pdb"}


def _relaxed_pdb(clone_id: str) -> Path:
    pdb = QC_DIR / RELAXED_PDBS[clone_id]
    if not pdb.is_file():
        raise FileNotFoundError(f"Missing relaxed Boltz PDB for {clone_id}: {pdb}")
    return pdb
NUMBERING_DIR = ROOT / "projects/PAG project/numbering"
CLONES = ["001", "008", "7M16"]


def main() -> int:
    for cid in CLONES:
        gated_path = VAM_DIR / cid / "stage4_postfilter" / "stage4_vam_gated.json"
        short_path = VAM_DIR / cid / "stage4_postfilter" / "stage4_shortlist.json"
        if not gated_path.is_file():
            print(f"[{cid}] no stage4 output")
            continue
        numbering = json.loads(
            (NUMBERING_DIR / f"{cid}_numbering.json").read_text(encoding="utf-8")
        )
        chain_records = pf._parse_pdb_sequences(str(_relaxed_pdb(cid)))
        data = json.loads(gated_path.read_text(encoding="utf-8"))
        records = data.get("records") or []
        changed = 0
        for rec in records:
            old = (rec.get("gates", {}).get("check_7_seq_liability") or {}).get("verdict")
            g7 = pf._run_check7(rec, numbering, chain_records)
            rec.setdefault("gates", {})["check_7_seq_liability"] = g7
            rec["overall_status"] = pf._gate_verdict(rec["gates"])
            rec["stopped_at_gate"] = next(
                (n for n, g in rec["gates"].items() if g.get("verdict") == "VETO"),
                None,
            )
            if old != g7.get("verdict"):
                changed += 1

        data["check7_rejudged_at"] = datetime.now(timezone.utc).isoformat()
        data["check7_rejudge_note"] = "PDB chain_records linear index; no apply_mutation_error"
        data["n_pass"] = sum(1 for r in records if r.get("overall_status") == "PASS")
        data["n_warn"] = sum(1 for r in records if r.get("overall_status") == "WARN")
        data["n_fail"] = sum(1 for r in records if r.get("overall_status") == "FAIL")
        data["n_incomplete"] = sum(
            1 for r in records if r.get("overall_status") == "INCOMPLETE"
        )
        gated_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        shortlist = [r for r in records if r.get("overall_status") in ("PASS", "WARN")]
        short_data = (
            json.loads(short_path.read_text(encoding="utf-8"))
            if short_path.is_file()
            else {}
        )
        short_data["clone"] = cid
        short_data["check7_rejudged_at"] = data["check7_rejudged_at"]
        short_data["n_shortlist"] = len(shortlist)
        short_data["mutations"] = shortlist
        short_path.write_text(json.dumps(short_data, indent=2), encoding="utf-8")
        print(
            f"[{cid}] records={len(records)} check7_changed={changed} "
            f"-> PASS={data['n_pass']} WARN={data['n_warn']} FAIL={data['n_fail']} "
            f"shortlist={len(shortlist)}"
        )
    print("done — run validate_pag1_stage4_audit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
