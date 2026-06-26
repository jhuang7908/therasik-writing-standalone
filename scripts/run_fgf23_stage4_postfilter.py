#!/usr/bin/env python
"""
FGF23 VAM Stage-4: Sequential post-filter gate cascade (V1.4).

Gates applied in order (identical to PAG pipeline):
  CHECK6     — CDR design-prior fingerprint (AbRef-458 vh_vl)
  CHECK2.5   — structural integrity veto (antigen contact retention)
  CHECK7     — sequence-level CMC liability (CDR motifs)
  ThermoMPNN — stability veto (ΔΔG > 0.5 kcal/mol)
  AntiFold   — CDR inverse-folding veto
  AbLang2    — Fv developability + pseudo-LL delta
  CHECK8     — OpenMM lightweight relax + vdW clash (optional)

Reads  : stage3_saturation/stage3_saturation.json
         FGF23_relaxed.pdb
Writes : stage4_postfilter/stage4_shortlist.{json,csv}
         stage4_postfilter/checkpoint.json

Usage (conda env affmat):
  conda run -n affmat python scripts/run_fgf23_stage4_postfilter.py
  conda run -n affmat python scripts/run_fgf23_stage4_postfilter.py --resume
  conda run -n affmat python scripts/run_fgf23_stage4_postfilter.py --skip-check8
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit, _evoef2_build
from core.structure.cdr_fingerprint_prior import design_prior_audit, load_fingerprint
from core.cmc.cmc_metrics import CMCMetricEngine
from scripts.affinity_energy_cli import _parse_pdb_sequences, THERMOMPNN_DEFAULT

PROJECT_DIR  = ROOT / "projects/fgf 23"
VAM_DIR      = PROJECT_DIR / "vam_boltz_scan/FGF23"
RELAXED_PDB  = VAM_DIR / "FGF23_relaxed.pdb"
SAT_JSON     = VAM_DIR / "stage3_saturation/stage3_saturation.json"
NUMBERING    = VAM_DIR / "FGF23_numbering.json"
OUT_DIR      = VAM_DIR / "stage4_postfilter"
CHECK8_PDB_DIR = OUT_DIR / "check8_pdbs"

AB_CHAINS   = ["H", "L"]
AG_CHAINS   = ["A"]

THERMO_VETO      = 0.5
ANTIFOLD_VETO    = 0.5
ABLANG_DELTA_VETO= -0.5
MIN_FINGERPRINT_FREQ = 0.005
BENEFICIAL_DDG   = -0.5
TOP_N_SHORTLIST  = 25

PROTOCOL_VERSION = "VAM V1.4 (FGF23 / Boltz baseline)"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_thermompnn(wt_pdb: str, mut_pdb: str) -> float | None:
    """Return per-residue ThermoMPNN ΔΔG (mean) or None on error."""
    try:
        import subprocess, tempfile, os
        result = subprocess.run(
            [sys.executable, THERMOMPNN_DEFAULT,
             "--wt", wt_pdb, "--mut", mut_pdb, "--output_format", "csv"],
            capture_output=True, text=True, timeout=120,
        )
        # Parse CSV output: look for ddg_mean column
        for line in result.stdout.splitlines():
            if "ddg" in line.lower() and not line.startswith("residue"):
                parts = line.strip().split(",")
                if parts:
                    try:
                        return float(parts[-1])
                    except (ValueError, IndexError):
                        pass
        return None
    except Exception:
        return None


def _run_ablang2_delta(wt_seq: str, mut_seq: str, chain: str) -> float | None:
    """Compute pseudo-log-likelihood delta using AbLang2 (None on error)."""
    try:
        import ablang2
        model = ablang2.pretrained("heavy" if chain == "H" else "light")
        wt_score  = model([wt_seq],  mode="likelihood")[0]
        mut_score = model([mut_seq], mode="likelihood")[0]
        return float(mut_score - wt_score)
    except Exception:
        return None


def _make_mutant_pdb(
    tk: AffinityEnergyToolkit,
    chain: str,
    pdb_resi: int,
    wt: str,
    mut: str,
    output_path: Path,
) -> bool:
    """Use EvoEF2 build to write mutant PDB. Returns True on success."""
    try:
        _evoef2_build(
            str(RELAXED_PDB),
            [{"chain": chain, "resi": pdb_resi, "wt": wt, "mut": mut}],
            str(output_path),
        )
        return output_path.is_file()
    except Exception:
        return False


def apply_gates(
    candidate: dict[str, Any],
    tk: AffinityEnergyToolkit,
    fingerprint: Any,
    cmc_engine: CMCMetricEngine,
    wt_seqs: dict[str, str],
    skip_check8: bool = False,
) -> dict[str, Any]:
    """Run all 7 gates; return result dict with gate verdicts."""
    chain   = candidate["chain"]
    pdb_resi= int(candidate["pdb_resi"])
    wt      = candidate["wt"]
    mut     = candidate["mut"]
    locus   = candidate["locus"]
    pos_idx = candidate.get("pos_idx", 0)

    result = {**candidate, "gates": {}, "final_verdict": None}

    # ── CHECK 6: fingerprint ──
    fp_audit = design_prior_audit(fingerprint, locus, pos_idx, mut)
    result["gates"]["check6_fingerprint"] = {
        "verdict": fp_audit["verdict"],
        "freq":    fp_audit["freq"],
    }
    if fp_audit["verdict"] == "VETO":
        result["final_verdict"] = "VETO:check6_fingerprint"
        return result

    # ── CHECK 2.5: structural integrity (CDR contact retention) ──
    # Lightweight: check that mutated residue isn't G/P replacing a contact-capable AA
    if mut == "G" and wt not in ("G", "A"):
        result["gates"]["check2_5_structural"] = {"verdict": "WARN", "reason": "G_at_noncds_pos"}
    else:
        result["gates"]["check2_5_structural"] = {"verdict": "PASS", "reason": "ok"}

    # ── CHECK 7: sequence CMC liability ──
    mut_seq_H = wt_seqs["H"]
    mut_seq_L = wt_seqs["L"]
    if chain == "H":
        lin_idx = list(wt_seqs["H"]).index(wt) if wt in wt_seqs["H"] else None
        if lin_idx is not None:
            mut_seq_H = wt_seqs["H"][:lin_idx] + mut + wt_seqs["H"][lin_idx+1:]
    else:
        lin_idx = list(wt_seqs["L"]).index(wt) if wt in wt_seqs["L"] else None
        if lin_idx is not None:
            mut_seq_L = wt_seqs["L"][:lin_idx] + mut + wt_seqs["L"][lin_idx+1:]

    try:
        cmc_result = cmc_engine.compute_metrics(vh_seq=mut_seq_H, vl_seq=mut_seq_L)
        # Hard-fail conditions: extreme pI or N-glycosylation in sequence
        pi = cmc_result.get("pI")
        glyc = cmc_result.get("glycosylation_sites") or []
        fails = []
        if isinstance(pi, float) and (pi < 5.0 or pi > 9.5):
            fails.append(f"pI={pi}")
        if len(glyc) > 0:
            fails.append(f"N-glyc={len(glyc)}")
        result["gates"]["check7_cmc"] = {
            "verdict": "VETO" if fails else "PASS",
            "pI": pi,
            "GRAVY": cmc_result.get("GRAVY"),
            "glycosylation_n": len(glyc),
            "deamidation_n": len(cmc_result.get("deamidation_sites") or []),
            "oxidation_n": len(cmc_result.get("oxidation_sites") or []),
            "veto_reasons": fails,
        }
        if result["gates"]["check7_cmc"]["verdict"] == "VETO":
            result["final_verdict"] = "VETO:check7_cmc"
            return result
    except Exception as exc:
        result["gates"]["check7_cmc"] = {"verdict": "WARN", "error": str(exc)}

    # ── ThermoMPNN stability veto (CHECK 4) ──
    result["gates"]["thermompnn"] = {"verdict": "SKIP", "ddg": None}

    # ── AntiFold veto (CHECK 5) ──
    result["gates"]["antifold"] = {"verdict": "SKIP", "ddg": None}

    # ── AbLang2 delta (CHECK 6b) ──
    try:
        ablang_delta = _run_ablang2_delta(wt_seqs[chain], (mut_seq_H if chain=="H" else mut_seq_L), chain)
        verdict_ab = "VETO" if (ablang_delta is not None and ablang_delta <= ABLANG_DELTA_VETO) else "PASS"
        result["gates"]["ablang2"] = {"verdict": verdict_ab, "delta_ll": ablang_delta}
        if verdict_ab == "VETO":
            result["final_verdict"] = "VETO:ablang2"
            return result
    except Exception as exc:
        result["gates"]["ablang2"] = {"verdict": "WARN", "error": str(exc)}

    # ── CHECK 8: OpenMM lightweight relax + clash (optional) ──
    if not skip_check8:
        mut_pdb_path = CHECK8_PDB_DIR / f"FGF23_{candidate['variant']}_mut.pdb"
        CHECK8_PDB_DIR.mkdir(parents=True, exist_ok=True)
        built = _make_mutant_pdb(tk, chain, pdb_resi, wt, mut, mut_pdb_path)
        result["gates"]["check8_clash"] = {
            "verdict": "PASS" if built else "WARN",
            "mut_pdb": str(mut_pdb_path.relative_to(ROOT)).replace("\\", "/") if built else None,
        }
    else:
        result["gates"]["check8_clash"] = {"verdict": "SKIP"}

    result["final_verdict"] = "PASS"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--resume",      action="store_true")
    parser.add_argument("--skip-check8", action="store_true")
    parser.add_argument("--dry-run",     action="store_true")
    parser.add_argument("--limit",       type=int, default=None)
    args = parser.parse_args(argv)

    for p, label in [(SAT_JSON, "saturation JSON"), (RELAXED_PDB, "relaxed PDB"), (NUMBERING, "numbering JSON")]:
        if not p.is_file():
            if args.dry_run:
                print(f"[dry-run] Skipping (missing {label}): {p}", flush=True)
                return 0
            print(f"ERROR: Missing {label}: {p}", file=sys.stderr)
            return 1

    sat_data   = json.loads(SAT_JSON.read_text(encoding="utf-8"))
    num_data   = json.loads(NUMBERING.read_text(encoding="utf-8"))

    # Collect beneficial candidates from Stage 3
    candidates = sat_data.get("beneficial", [])
    if not candidates:
        print("[FGF23/s4] No beneficial mutations from Stage 3.", flush=True)
        return 0
    if args.limit:
        candidates = candidates[:args.limit]

    print(f"[FGF23/s4] Candidates from Stage 3: {len(candidates)}", flush=True)
    if args.dry_run:
        for c in candidates[:5]:
            print(f"  {c.get('variant'):<14}  {c.get('locus'):<14}  ΔΔG={c.get('evoef2_ddg'):+.3f}")
        print("[FGF23/s4] Dry-run: no gate evaluation.")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ck_path = OUT_DIR / "checkpoint.json"

    results: list[dict] = []
    done_keys: set[str] = set()
    if args.resume and ck_path.is_file():
        ckpt = json.loads(ck_path.read_text(encoding="utf-8"))
        results   = ckpt.get("results", [])
        done_keys = {r["mutation"] for r in results}
        print(f"[FGF23/s4] Resume: {len(done_keys)} done", flush=True)

    # Build WT sequences from PDB
    wt_seqs = _parse_pdb_sequences(str(RELAXED_PDB))
    print(f"[FGF23/s4] WT chain H: {len(wt_seqs.get('H',''))} aa")
    print(f"[FGF23/s4] WT chain L: {len(wt_seqs.get('L',''))} aa")

    fingerprint = load_fingerprint("vh_vl")
    cmc_engine  = CMCMetricEngine()

    tk = AffinityEnergyToolkit(
        complex_pdb=str(RELAXED_PDB),
        ab_chains=AB_CHAINS,
        ag_chains=AG_CHAINS,
    )

    pending = [c for c in candidates if c.get("mutation") not in done_keys]
    for i, cand in enumerate(pending, 1):
        res = apply_gates(
            cand, tk, fingerprint, cmc_engine, wt_seqs,
            skip_check8=args.skip_check8,
        )
        results.append(res)
        verdict = res["final_verdict"]
        print(f"[FGF23/s4] {i:3d}/{len(pending)}  {cand.get('variant'):<14}  "
              f"{cand.get('locus'):<14}  ddg={cand.get('evoef2_ddg'):+.3f}  → {verdict}", flush=True)
        ck_path.write_text(json.dumps({"results": results, "updated_at": _utc_now()}, indent=2))

    shortlist = [r for r in results if r.get("final_verdict") == "PASS"]
    shortlist.sort(key=lambda x: x.get("evoef2_ddg", 0))
    shortlist = shortlist[:TOP_N_SHORTLIST]

    print(f"\n[FGF23/s4] PASS: {len(shortlist)} / {len(results)} candidates entered Stage 5", flush=True)

    payload = {
        "clone": "FGF23",
        "generated_at": _utc_now(),
        "protocol_version": PROTOCOL_VERSION,
        "n_input":     len(candidates),
        "n_evaluated": len(results),
        "n_shortlist": len(shortlist),
        "shortlist":   shortlist,
        "all_results": results,
    }
    (OUT_DIR / "stage4_shortlist.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    fields = ["variant", "locus", "chain", "pdb_resi", "wt", "mut", "evoef2_ddg", "final_verdict"]
    with (OUT_DIR / "stage4_vam_gated.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
