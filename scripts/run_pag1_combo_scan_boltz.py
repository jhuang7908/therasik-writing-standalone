#!/usr/bin/env python
"""PAG-1 VAM combination (multi-point) scan on relaxed Boltz structures (V1.6.1).

Combines compatible single-point Stage-5 winners within one clone and RE-COMPUTES
the combined variant (epistasis is not additive). Each combo runs:
  EvoEF2 combined ΔΔG (PRIMARY)  -> ThermoMPNN -> AntiFold -> CHECK 8 relax/clash
  -> MM/GBSA self-ref (per-site WT-self repack baseline; noise-controlled).

Clone 008 only (the sole clone with >=2 clean cross-position winners):
  positions A:33 (CDR-H1), B:97 (CDR-L3), B:101 (CDR-L3).

Resume-safe: writes combo_scan.json after each stage so Cursor interrupts do not
lose completed work. Re-run with --resume to continue (skips done stages).

Usage (repo root, conda env affmat):
  conda run -n affmat python scripts/run_pag1_combo_scan_boltz.py --resume
  conda run -n affmat python scripts/run_pag1_combo_scan_boltz.py --resume --with-mmgbsa
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.structure.affinity_energy_toolkit import (  # noqa: E402
    EVOEF2_DEFAULT,
    THERMOMPNN_DEFAULT,
    AffinityEnergyToolkit,
)
from core.structure.relax_and_clash_gate import relax_and_clash_check  # noqa: E402
from scripts.affinity_energy_cli import _parse_pdb_sequences  # noqa: E402

QC_DIR = ROOT / "projects/PAG project/boltz_relaxed_qc"
VAM_DIR = ROOT / "projects/PAG project/vam_boltz_scan"
NUMBERING_DIR = ROOT / "projects/PAG project/numbering"

AB_CHAINS = ["A", "B"]
AG_CHAINS = ["C"]
THERMO_VETO = 0.5
ANTIFOLD_VETO = 0.5
PROTOCOL_VERSION = "VAM V1.6.1 (Boltz baseline, combo)"
STAGE = "4b_combination_scan_boltz"

RELAXED = {"008": "008_relaxed.pdb"}

# Combos approved by owner: 3 doubles + 1 triple, best variant per position.
# (N33I = CDR-H1, T97I = CDR-L3, R101N = CDR-L3)
COMBOS_008 = [
    [{"chain": "A", "resi": 33, "wt": "N", "mut": "I"},
     {"chain": "B", "resi": 97, "wt": "T", "mut": "I"}],
    [{"chain": "A", "resi": 33, "wt": "N", "mut": "I"},
     {"chain": "B", "resi": 101, "wt": "R", "mut": "N"}],
    [{"chain": "B", "resi": 97, "wt": "T", "mut": "I"},
     {"chain": "B", "resi": 101, "wt": "R", "mut": "N"}],
    [{"chain": "A", "resi": 33, "wt": "N", "mut": "I"},
     {"chain": "B", "resi": 97, "wt": "T", "mut": "I"},
     {"chain": "B", "resi": 101, "wt": "R", "mut": "N"}],
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _combo_id(muts: list[dict]) -> str:
    return "+".join(f"{m['chain']}:{m['resi']}:{m['wt']}{m['mut']}" for m in muts)


def _validate_wt(chain_records: dict, muts: list[dict]) -> str | None:
    for m in muts:
        recs = chain_records.get(m["chain"])
        if not recs:
            return f"chain {m['chain']} absent"
        hit = next((r for r in recs if r["resi"] == m["resi"]), None)
        if hit is None:
            return f"{m['chain']}:{m['resi']} not in PDB"
        if hit["aa"] != m["wt"]:
            return f"WT mismatch {m['chain']}:{m['resi']} pdb={hit['aa']} expected={m['wt']}"
    return None


def _relaxed_pdb(clone_id: str) -> Path:
    pdb = QC_DIR / RELAXED[clone_id]
    if not pdb.is_file():
        raise FileNotFoundError(f"Missing relaxed Boltz PDB for {clone_id}: {pdb}")
    return pdb


def process_combo(
    rec: dict,
    *,
    toolkit: AffinityEnergyToolkit,
    pdb_path: Path,
    evoef2_exe: str,
    check8_dir: Path,
    wt_antifold_logp: float | None,
    wt_evoef2_dg: float | None,
    with_mmgbsa: bool,
    mmgbsa_steps: int,
) -> dict:
    muts = rec["mutations"]
    gates = rec.setdefault("gates", {})

    # EvoEF2 combined ΔΔG (PRIMARY) — recompute if ddg missing (needs WT baseline)
    if gates.get("evoef2", {}).get("ddg") is None:
        t0 = time.time()
        er = toolkit.run_evoef2(muts, wt_dg=wt_evoef2_dg)
        gates["evoef2"] = {
            "ddg": er.get("ddg"),
            "dg": er.get("dg"),
            "wt_dg": wt_evoef2_dg,
            "error": er.get("error"),
            "elapsed_s": round(time.time() - t0, 1),
        }

    # ThermoMPNN
    if "thermompnn" not in gates:
        tr = toolkit.run_thermompnn(muts)
        ddg = tr.get("ddg")
        verdict = "ERROR" if tr.get("error") else (
            "VETO" if ddg is not None and ddg > THERMO_VETO else "PASS"
        )
        gates["thermompnn"] = {"verdict": verdict, "thermo_ddg": ddg,
                                "threshold": THERMO_VETO, "error": tr.get("error")}

    # AntiFold
    if "antifold" not in gates:
        af = toolkit.run_antifold(muts, wt_logp=wt_antifold_logp)
        ddg = af.get("ddg")
        verdict = "ERROR" if af.get("error") else (
            "VETO" if ddg is not None and ddg > ANTIFOLD_VETO else "PASS"
        )
        gates["antifold"] = {"verdict": verdict, "af_ddg": ddg,
                              "threshold": ANTIFOLD_VETO,
                              "wt_logp": af.get("wt_logp"), "mut_logp": af.get("mut_logp"),
                              "error": af.get("error")}

    # CHECK 8 relax + clash on combined mutant
    if "check_8_relax_clash" not in gates:
        import tempfile
        from core.structure.affinity_energy_toolkit import _evoef2_build
        with tempfile.TemporaryDirectory(prefix="pag1_combo_check8_") as tmp:
            mpdb = _evoef2_build(evoef2_exe, str(pdb_path), muts, AB_CHAINS[0], tmp)
            if mpdb is None:
                gates["check_8_relax_clash"] = {"verdict": "VETO",
                                                "notes": "EvoEF2 BuildMutant failed"}
            else:
                res = relax_and_clash_check(
                    pdb_path=mpdb, ab_chains=AB_CHAINS, antigen_chains=AG_CHAINS,
                    minimize=True, max_iterations=500, out_dir=str(check8_dir),
                )
                payload = dataclasses.asdict(res)
                payload["verdict"] = res.verdict
                gates["check_8_relax_clash"] = payload

    # MM/GBSA self-ref (corroboration, optional/heavy)
    if with_mmgbsa and "mmgbsa_selfref" not in gates:
        mr = toolkit.run_mmgbsa_selfref(muts, minimization_steps=mmgbsa_steps)
        gates["mmgbsa_selfref"] = {
            "dg": mr.get("dg"),
            "wt_self_dg": mr.get("wt_self_dg"),
            "ddg_selfref": mr.get("ddg_selfref"),
            "ddg_raw_vs_input": mr.get("ddg_raw_vs_input"),
            "error": mr.get("error"),
            "elapsed_s": mr.get("elapsed"),
        }

    # overall (informational; EvoEF2 primary)
    vetoes = [k for k, g in gates.items() if isinstance(g, dict) and g.get("verdict") == "VETO"]
    rec["stopped_at_gate"] = vetoes[0] if vetoes else None
    rec["overall_status"] = "FAIL" if vetoes else "PASS"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description="PAG-1 combination scan (clone 008)")
    ap.add_argument("--clone", default="008", choices=list(RELAXED))
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--with-mmgbsa", action="store_true",
                    help="Also run MM/GBSA self-ref (heavy CPU OpenMM)")
    ap.add_argument("--mmgbsa-steps", type=int, default=300)
    ap.add_argument("--evoef2", default=EVOEF2_DEFAULT)
    ap.add_argument("--thermompnn-dir", default=THERMOMPNN_DEFAULT)
    ap.add_argument("--vam-dir", default=None, help="Override VAM dir (e.g. VPS /srv path)")
    ap.add_argument("--qc-dir", default=None, help="Override relaxed-PDB QC dir")
    args = ap.parse_args()

    global VAM_DIR, QC_DIR
    if args.vam_dir:
        VAM_DIR = Path(args.vam_dir)
    if args.qc_dir:
        QC_DIR = Path(args.qc_dir)

    clone_id = args.clone
    combos = {"008": COMBOS_008}[clone_id]
    pdb_path = _relaxed_pdb(clone_id)
    chain_records = _parse_pdb_sequences(str(pdb_path))
    out_dir = VAM_DIR / clone_id / "stage4b_combo"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "combo_scan.json"
    check8_dir = out_dir / "check8_pdbs"
    check8_dir.mkdir(parents=True, exist_ok=True)

    # Load or init records
    if args.resume and out_json.is_file():
        data = json.loads(out_json.read_text(encoding="utf-8"))
        by_id = {r["combo_id"]: r for r in data.get("records", [])}
    else:
        by_id = {}

    records = []
    for muts in combos:
        cid = _combo_id(muts)
        rec = by_id.get(cid) or {"combo_id": cid, "clone": clone_id, "mutations": muts}
        err = _validate_wt(chain_records, muts)
        if err:
            rec["wt_error"] = err
            rec["overall_status"] = "INVALID"
            records.append(rec)
            print(f"[{clone_id}] {cid}: WT VALIDATION FAILED -> {err}", flush=True)
            continue
        records.append(rec)

    toolkit = AffinityEnergyToolkit(
        complex_pdb=str(pdb_path), ab_chains=AB_CHAINS, ag_chains=AG_CHAINS,
        evoef2_exe=args.evoef2, thermompnn_dir=args.thermompnn_dir,
    )
    # WT baselines only needed if some combo still lacks EvoEF2 / AntiFold.
    active = [r for r in records if r.get("overall_status") != "INVALID"]
    need_evoef2 = any(r.get("gates", {}).get("evoef2", {}).get("ddg") is None for r in active)
    need_antifold = any("antifold" not in r.get("gates", {}) for r in active)
    wt_antifold_logp = None
    if need_antifold:
        wt_antifold_logp = toolkit.run_antifold([], wt_logp=None).get("wt_logp")
    wt_evoef2_dg = None
    if need_evoef2:
        wt_evoef2_dg = toolkit.run_evoef2([]).get("dg")
        print(f"[{clone_id}] WT EvoEF2 binding dg={wt_evoef2_dg}", flush=True)
    else:
        print(f"[{clone_id}] EvoEF2/AntiFold cached; skipping WT baselines (MM/GBSA only)", flush=True)

    for i, rec in enumerate(records, 1):
        if rec.get("overall_status") == "INVALID":
            continue
        print(f"[{clone_id}] [{i}/{len(records)}] {rec['combo_id']}", flush=True)
        process_combo(
            rec, toolkit=toolkit, pdb_path=pdb_path, evoef2_exe=args.evoef2,
            check8_dir=check8_dir, wt_antifold_logp=wt_antifold_logp,
            wt_evoef2_dg=wt_evoef2_dg,
            with_mmgbsa=args.with_mmgbsa, mmgbsa_steps=args.mmgbsa_steps,
        )
        data = {
            "generated_at": _utc_now(),
            "protocol_version": PROTOCOL_VERSION,
            "stage": STAGE,
            "clone": clone_id,
            "rank1_pdb": str(pdb_path),
            "with_mmgbsa": args.with_mmgbsa,
            "mmgbsa_steps": args.mmgbsa_steps,
            "records": records,
        }
        out_json.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"[{clone_id}] combo scan written: {out_json}", flush=True)
    for rec in records:
        g = rec.get("gates", {})
        evo = (g.get("evoef2") or {}).get("ddg")
        mm = (g.get("mmgbsa_selfref") or {}).get("ddg_selfref")
        tm = (g.get("thermompnn") or {}).get("verdict")
        af = (g.get("antifold") or {}).get("verdict")
        c8 = (g.get("check_8_relax_clash") or {}).get("verdict")
        print(f"  {rec['combo_id']}: EvoEF2={evo} MMselfref={mm} "
              f"Thermo={tm} AntiFold={af} CHECK8={c8} overall={rec.get('overall_status')}",
              flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
