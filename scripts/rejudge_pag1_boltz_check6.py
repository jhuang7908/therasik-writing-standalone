#!/usr/bin/env python
"""Re-judge CHECK 6 (CDR fingerprint design-prior) on PAG-1 Boltz Stage-4 outputs.

Uses the corrected IMGT-segmented index mapping in run_pag1_vam_postfilter._run_check6.
Updates check_6 verdict + overall_status in both stage4_vam_gated.json and
stage4_shortlist.json, and recomputes the batch summary counts.
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
NUMBERING_DIR = ROOT / "projects/PAG project/numbering"
CLONES = ["001", "008", "7M16"]


def _load_numbering(cid: str) -> dict:
    return json.loads(
        (NUMBERING_DIR / f"{cid}_numbering.json").read_text(encoding="utf-8")
    )


def main() -> int:
    fp = pf.load_fingerprint("vh_vl")
    for cid in CLONES:
        gated_path = VAM_DIR / cid / "stage4_postfilter" / "stage4_vam_gated.json"
        short_path = VAM_DIR / cid / "stage4_postfilter" / "stage4_shortlist.json"
        if not gated_path.is_file():
            print(f"[{cid}] no stage4 output")
            continue
        numbering = _load_numbering(cid)
        data = json.loads(gated_path.read_text(encoding="utf-8"))
        records = data.get("records") or []
        changed = 0
        for rec in records:
            old = (rec.get("gates", {}).get("check_6_design_prior") or {}).get("verdict")
            g6 = pf._run_check6(rec, fp, numbering)
            rec.setdefault("gates", {})["check_6_design_prior"] = g6
            new_overall = pf._gate_verdict(rec["gates"])
            rec["overall_status"] = new_overall
            rec["stopped_at_gate"] = next(
                (n for n, g in rec["gates"].items() if g.get("verdict") == "VETO"),
                None,
            )
            if old != g6["verdict"]:
                changed += 1

        data["check6_rejudged_at"] = datetime.now(timezone.utc).isoformat()
        data["check6_rejudge_note"] = "IMGT-segmented index mapping; out-of-CDR -> NOT_RUN"
        data["n_pass"] = sum(1 for r in records if r.get("overall_status") == "PASS")
        data["n_warn"] = sum(1 for r in records if r.get("overall_status") == "WARN")
        data["n_fail"] = sum(1 for r in records if r.get("overall_status") == "FAIL")
        data["n_incomplete"] = sum(
            1 for r in records if r.get("overall_status") == "INCOMPLETE"
        )
        gated_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        shortlist = [
            r for r in records if r.get("overall_status") in ("PASS", "WARN")
        ]
        short_data = (
            json.loads(short_path.read_text(encoding="utf-8"))
            if short_path.is_file()
            else {}
        )
        short_data["clone"] = cid
        short_data["check6_rejudged_at"] = data["check6_rejudged_at"]
        short_data["n_shortlist"] = len(shortlist)
        short_data["mutations"] = shortlist
        short_path.write_text(json.dumps(short_data, indent=2), encoding="utf-8")

        c6 = {}
        for r in records:
            v = (r["gates"]["check_6_design_prior"]).get("verdict")
            c6[v] = c6.get(v, 0) + 1
        print(
            f"[{cid}] records={len(records)} check6_changed={changed} "
            f"check6_dist={c6} -> PASS={data['n_pass']} WARN={data['n_warn']} "
            f"FAIL={data['n_fail']} INCOMPLETE={data['n_incomplete']} "
            f"shortlist={len(shortlist)}"
        )
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
