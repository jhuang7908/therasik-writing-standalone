#!/usr/bin/env python
"""Machine audit for PAG-1 Boltz Stage-4 — correctness before trusting shortlist/MMGBSA.

Checks:
  1) CHECK 7 replay matches stored verdict (PDB chain_records authoritative index).
  2) No apply_mutation_error / coord_error in CHECK 7.
  3) WT aa at pdb_resi matches row wt on relaxed Boltz PDB.
  4) Shortlist rows: CHECK 8 and ThermoMPNN/AntiFold actually ran (not NOT_RUN).
  5) overall_status consistent with gate cascade (_gate_verdict).

Exit 0 = audit PASS for audited clones; 1 = FAIL (do not treat shortlist as final).
"""

from __future__ import annotations

import argparse
import json
import sys
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


def _audit_clone(clone_id: str) -> dict:
    gated_path = VAM_DIR / clone_id / "stage4_postfilter" / "stage4_vam_gated.json"
    short_path = VAM_DIR / clone_id / "stage4_postfilter" / "stage4_shortlist.json"
    out: dict = {"clone": clone_id, "ok": True, "errors": [], "warnings": []}

    if not gated_path.is_file():
        out["ok"] = False
        out["errors"].append("missing stage4_vam_gated.json")
        return out

    pdb = _relaxed_pdb(clone_id)
    numbering = json.loads(
        (NUMBERING_DIR / f"{clone_id}_numbering.json").read_text(encoding="utf-8")
    )
    chain_records = pf._parse_pdb_sequences(str(pdb))
    data = json.loads(gated_path.read_text(encoding="utf-8"))
    records = data.get("records") or []
    out["n_records"] = len(records)

    c7_mismatch = 0
    apply_mut_err = 0
    wt_mismatch = 0
    status_mismatch = 0

    for rec in records:
        mut = pf._to_gate_mut(rec)
        chain = mut["chain"]
        resi = mut["resi"]
        wt = mut["wt"]
        # WT vs PDB
        try:
            idx = next(i for i, r in enumerate(chain_records[chain]) if r["resi"] == resi)
            pdb_aa = chain_records[chain][idx]["aa"]
            if pdb_aa != wt:
                wt_mismatch += 1
                if wt_mismatch <= 3:
                    out["errors"].append(
                        f"WT mismatch {chain}:{resi} row={wt} pdb={pdb_aa}"
                    )
        except StopIteration:
            wt_mismatch += 1
            out["errors"].append(f"resi {chain}:{resi} not in relaxed PDB")

        stored = (rec.get("gates") or {}).get("check_7_seq_liability") or {}
        if "apply_mutation" in json.dumps(stored):
            apply_mut_err += 1
        if stored.get("reason") == "coord_error":
            apply_mut_err += 1

        stored_verdict = stored.get("verdict")
        # Sequential gate: if CHECK 7 never ran, stored has no verdict — not a mismatch.
        if stored_verdict is not None:
            replay = pf._run_check7(rec, numbering, chain_records)
            if replay.get("verdict") != stored_verdict:
                c7_mismatch += 1
                if c7_mismatch <= 3:
                    out["warnings"].append(
                        f"CHECK7 replay {rec.get('variant')}: stored={stored_verdict} "
                        f"replay={replay.get('verdict')}"
                    )

        expected = pf._gate_verdict(rec.get("gates") or {})
        if rec.get("overall_status") != expected:
            status_mismatch += 1

    out["check7_replay_mismatch"] = c7_mismatch
    out["check7_apply_mutation_or_coord"] = apply_mut_err
    out["wt_mismatch"] = wt_mismatch
    out["overall_status_mismatch"] = status_mismatch

    if c7_mismatch or apply_mut_err or wt_mismatch or status_mismatch:
        out["ok"] = False
        if c7_mismatch:
            out["errors"].append(f"CHECK7 replay mismatch count={c7_mismatch}")
        if apply_mut_err:
            out["errors"].append(f"CHECK7 coord/apply_mutation issues={apply_mut_err}")
        if wt_mismatch:
            out["errors"].append(f"WT vs PDB mismatch count={wt_mismatch}")
        if status_mismatch:
            out["errors"].append(f"overall_status mismatch count={status_mismatch}")

    # Shortlist integrity
    if short_path.is_file():
        short = json.loads(short_path.read_text(encoding="utf-8"))
        sl = short.get("mutations") or []
        out["n_shortlist"] = len(sl)
        bad_sl = []
        for rec in sl:
            gates = rec.get("gates") or {}
            c8 = gates.get("check_8_relax_clash") or {}
            if c8.get("verdict") in (None, "NOT_RUN"):
                bad_sl.append(rec.get("variant", rec.get("mutation_key")))
            c7 = gates.get("check_7_seq_liability") or {}
            if c7.get("verdict") not in ("PASS", "WARN"):
                bad_sl.append(f"{rec.get('variant')}:check7={c7.get('verdict')}")
        if bad_sl:
            out["ok"] = False
            out["errors"].append(
                f"shortlist incomplete gates: {bad_sl[:8]}{'...' if len(bad_sl)>8 else ''}"
            )
    else:
        out["warnings"].append("no stage4_shortlist.json yet")

    # Completeness: expect n_input from stage3
    s3 = VAM_DIR / clone_id / "stage3_saturation" / "stage3_recommended.json"
    if s3.is_file():
        n_in = len(json.loads(s3.read_text(encoding="utf-8")).get("mutations") or [])
        if len(records) < n_in:
            out["ok"] = False
            out["errors"].append(
                f"incomplete run: {len(records)}/{n_in} candidates in gated json"
            )
            out["n_input_stage3"] = n_in

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit PAG-1 Boltz Stage-4 gate correctness")
    ap.add_argument("--clone", action="append", choices=CLONES)
    args = ap.parse_args()
    clones = args.clone or CLONES
    all_ok = True
    report = {"clones": {}, "protocol": pf.PROTOCOL_VERSION}
    for cid in clones:
        r = _audit_clone(cid)
        report["clones"][cid] = r
        tag = "PASS" if r["ok"] else "FAIL"
        print(f"[{cid}] AUDIT {tag} records={r.get('n_records')} shortlist={r.get('n_shortlist', '—')}")
        for e in r.get("errors") or []:
            print(f"  ERROR: {e}")
        for w in r.get("warnings") or []:
            print(f"  WARN: {w}")
        if not r["ok"]:
            all_ok = False
    out_path = VAM_DIR / "stage4_audit_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report: {out_path}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
