#!/usr/bin/env python3
"""Smoke-test VH/VL humanization run modes against local API (console-compatible payloads).

Default is FAST: mouse + rat × Quick Preview only (~1–3 min total).

Full matrix (6 jobs, structure modeling ×4) is slow by design — use --full and run locally:

  conda run -n anarcii python scripts/smoke_vhvl_console_modes.py --full
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8000"

MOUSE_VH = (
    "QVQLQQSGPELVKPGASLKLSCTASGFNIKDTYIHWVKQRPEQGLEWIGRIYPTNGYTRYDPKFQDKATITADTSSNTAYLQVSRLTSEDTAVYYCSRWGGDGFYAMDYWGQGASVTVSS"
)
MOUSE_VL = (
    "DIQMTQSPSSLSASVGDRVTITCRASQDVNTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK"
)
RAT_VH = (
    "EVKLLESGGGLVQPGGSMRLSCAGSGFTFTDFYMNWIRQPAGKAPEWLGFIRDKAKGYTTEYNPSVKGRFTISRDNTQNMLYLQMNTLRAEDTATYYCAREGHTAAPFDYWGQGVMVTVSS"
)
RAT_VL = (
    "DIKMTQSPSFLSASVGDRVTLNCKASQNIDKYLNWYQQKLGESPKLLIYNTNNLQTGIPSRFSGSGSGTDFTLTISSLQPEDVATYFCLQHISRPRTFGTGTKLELK"
)

MODES_QUICK = [
    ("quick_preview", {"repair_mode": "standard", "dry_run_structure": True, "surface_reshape_on_qc_fail": False}),
]
MODES_FULL = [
    ("quick_preview", {"repair_mode": "standard", "dry_run_structure": True, "surface_reshape_on_qc_fail": False}),
    ("standard_delivery", {"repair_mode": "standard", "dry_run_structure": False, "surface_reshape_on_qc_fail": True}),
    ("enhanced_rescue", {"repair_mode": "rescue", "dry_run_structure": False, "surface_reshape_on_qc_fail": True}),
]


def post_json(base: str, path: str, data: dict) -> dict:
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        base + path,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def get_json(base: str, path: str) -> dict:
    with urllib.request.urlopen(base + path, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def run_case(
    base: str,
    label: str,
    species: str,
    vh: str,
    vl: str,
    mode_name: str,
    flags: dict,
    poll_sec: float,
) -> dict:
    payload = {
        "vh_sequence": vh,
        "vl_sequence": vl,
        "project_name": f"smoke_{label}_{mode_name}",
        "source_species": species,
        "report_format": "html",
        "report_language": "en",
        "back_mutation_strategy": "auto",
        "skip_iedb": True,
        **flags,
    }
    t0 = time.time()
    j = post_json(base, "/humanize/vh_vl/async", payload)
    job_id = j.get("job_id")
    if not job_id:
        return {"label": label, "mode": mode_name, "error": "no job_id", "raw": j}
    max_wait = 2400 if not flags.get("dry_run_structure") else 360
    deadline = time.time() + max_wait
    last = None
    while time.time() < deadline:
        st = get_json(base, f"/jobs/{job_id}")
        last = st
        if st.get("status") in ("done", "failed"):
            break
        time.sleep(poll_sec)
    elapsed = time.time() - t0
    if not last or last.get("status") not in ("done", "failed"):
        return {
            "label": label,
            "mode": mode_name,
            "job_id": job_id,
            "error": "timeout",
            "elapsed_sec": round(elapsed, 1),
        }
    res = last.get("result") or {}
    ex = res.get("execution_route") or {}
    qm = res.get("quality_metrics") if isinstance(res.get("quality_metrics"), dict) else {}
    p_ab = qm.get("p_abnativ2") if isinstance(qm.get("p_abnativ2"), dict) else {}
    return {
        "label": label,
        "mode": mode_name,
        "job_id": job_id,
        "status": last.get("status"),
        "elapsed_sec": round(elapsed, 1),
        "error": (last.get("error") or "")[:500] if last.get("status") == "failed" else None,
        "report_url": last.get("report_url"),
        "dry_run_structure": res.get("dry_run_structure"),
        "repair_mode": res.get("repair_mode"),
        "run_mode": ex.get("run_mode"),
        "final_route": ex.get("final_route"),
        "surface_fallback_applied": (ex.get("surface_fallback") or {}).get("applied"),
        "t20_error": qm.get("t20_error") or res.get("t20_error"),
        "p_abnativ_status": p_ab.get("paired_humanness_status"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="VH/VL console run-mode smoke (local API).")
    ap.add_argument("--base", default=DEFAULT_BASE, help=f"API base URL (default {DEFAULT_BASE})")
    ap.add_argument(
        "--full",
        action="store_true",
        help="Run all 6 cases (mouse/rat × quick/standard/rescue). Slow — tens of minutes.",
    )
    ap.add_argument(
        "--species",
        choices=("both", "mouse", "rat"),
        default="both",
        help="Donor pair(s) to run (default: both).",
    )
    ap.add_argument("--poll", type=float, default=1.0, help="Seconds between job polls (default 1).")
    args = ap.parse_args()

    mode_list = MODES_FULL if args.full else MODES_QUICK
    cases = []
    if args.species in ("both", "mouse"):
        cases.append(("mouse", MOUSE_VH, MOUSE_VL, "mouse"))
    if args.species in ("both", "rat"):
        cases.append(("rat", RAT_VH, RAT_VL, "rat"))

    if not args.full:
        print(
            "FAST smoke: Quick Preview only. Use --full for Standard/Enhanced (slow).\n",
            flush=True,
        )

    rows = []
    for label, vh, vl, sp in cases:
        for mode_name, flags in mode_list:
            print(f"--- {label} {mode_name} ...", flush=True)
            rows.append(run_case(args.base, label, sp, vh, vl, mode_name, flags, args.poll))

    print(json.dumps(rows, indent=2, ensure_ascii=False))
    ok = sum(1 for r in rows if r.get("status") == "done")
    print(f"\nSUMMARY: {ok}/{len(rows)} done", flush=True)
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
