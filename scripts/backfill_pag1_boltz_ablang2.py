#!/usr/bin/env python
"""Backfill AbLang2 scores on PAG-1 Boltz Stage-4 shortlists."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.affinity_energy_cli import _parse_pdb_sequences
from scripts.run_pag1_vam_postfilter import (
    _compute_ablang2_score,
    _mutate_fv_sequences,
)

VAM_DIR = ROOT / "projects/PAG project/vam_boltz_scan"
QC_DIR = ROOT / "projects/PAG project/boltz_relaxed_qc"
NUMBERING_DIR = ROOT / "projects/PAG project/numbering"

RELAXED = {
    "001": "001_relaxed.pdb",
    "008": "008_relaxed.pdb",
    "7M16": "7M16_relaxed.pdb",
}
ABL_VETO = -0.5


def main() -> int:
    for cid in ["001", "008", "7M16"]:
        sl_path = VAM_DIR / cid / "stage4_postfilter" / "stage4_shortlist.json"
        if not sl_path.is_file():
            continue
        data = json.loads(sl_path.read_text(encoding="utf-8"))
        muts = data.get("mutations") or []
        if not muts:
            print(f"[{cid}] no shortlist")
            continue

        numbering = json.loads(
            (NUMBERING_DIR / f"{cid}_numbering.json").read_text(encoding="utf-8")
        )
        wt_vh = numbering["sequences"]["vh"]
        wt_vl = numbering["sequences"]["vl"]
        wt_score, wt_err = _compute_ablang2_score(wt_vh, wt_vl)
        print(f"[{cid}] WT AbLang2={wt_score} err={wt_err}")

        chain_records = _parse_pdb_sequences(str(QC_DIR / RELAXED[cid]))
        for m in muts:
            vh, vl = _mutate_fv_sequences(chain_records, m)
            mut_score, mut_err = _compute_ablang2_score(vh, vl)
            delta = (
                round(mut_score - wt_score, 3)
                if mut_score is not None and wt_score is not None
                else None
            )
            verdict = "VETO" if delta is not None and delta < ABL_VETO else "PASS"
            gate = m["gates"]["cmc_ablang"]
            gate["ablang_score"] = mut_score
            gate["ablang_delta"] = delta
            gate["ablang_error"] = mut_err
            gate["ablang_verdict"] = verdict
            if verdict == "VETO":
                gate["verdict"] = "VETO"
                m["overall_status"] = "FAIL"
                m["stopped_at_gate"] = "cmc_ablang"
            elif gate.get("verdict") == "NOT_RUN":
                gate["verdict"] = "PASS"
            print(f"  {m['mutation_key']} delta={delta} -> {verdict}")

        data["ablang_backfill_at"] = datetime.now(timezone.utc).isoformat()
        data["wt_ablang2_baseline"] = wt_score
        sl_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
