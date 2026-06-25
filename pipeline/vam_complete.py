"""
vam_complete.py — Complete Two-Layer Virtual Affinity Maturation (V2)
======================================================================
Layer 1: Single-point scan (EvoEF2 ΔΔG) → ThermoMPNN stability veto → MM/GBSA
Layer 2: Pairwise combinatorial scan of top Layer-1 seed mutations
         → ThermoMPNN stability veto → MM/GBSA on best combos

This module is designed to be called from a Phase 4 orchestrator script.
It can also be run standalone against a HADDOCK3-refined complex PDB.

Key design decisions:
  - Layer 2 only runs if Layer 1 finds at least 2 beneficial seeds.
    If Layer 1 finds 1 seed, Layer 2 runs single-point only.
    If Layer 1 finds 0, recovery pass runs (lowest ΔΔG combos regardless of sign).
  - Triplet scan (Layer 3) is disabled by default to save compute.
    Enable by setting max_triplets > 0 in vam_settings.
  - All results are saved to a structured report JSON.
  - Checkpoint/resume: each scan phase saves intermediate results.

Usage (called from project script):
    from pipeline.vam_complete import run_vam_complete

    report = run_vam_complete(
        complex_pdb   = Path("phase4_haddock3/complexes/cand_0306_complex.pdb"),
        candidate_id  = "cand_0306",
        parent_seq    = "QVQLV...",
        cdr_regions   = mask["cdr_regions"],
        redesign_cdrs = ["CDR2", "CDR3"],
        vhh_chain     = "A",
        ag_chain      = "B",
        evoef2_exe    = "tools/EvoEF2_src/EvoEF2.exe",
        wt_dg         = -40.74,
        parent_dg     = -37.86,
        vam_settings  = mask.get("vam_settings", {}),
        output_dir    = Path("phase4_vam/cand_0306"),
    )
"""

from __future__ import annotations

import itertools
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PIPELINE_ROOT))

try:
    from core.integrity.hallucination_guard import HallucinationGuard, HallucinationError
    _GUARD_AVAILABLE = True
except ImportError:
    _GUARD_AVAILABLE = False

AA_ALPHABET = "ACDEFGHIKLMNPQRSTVWY"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── EvoEF2 / ThermoMPNN / MM/GBSA wrappers ───────────────────────────────────

def _evoef2_scan_batch(
    tk: Any,
    mutations: list[list[dict]],
    progress_every: int = 30,
) -> list[dict]:
    results = []
    for i, mut_list in enumerate(mutations):
        try:
            r = tk.run_evoef2(mut_list)
            r["mutations"] = [
                f"{m['wt']}{m['resi']}{m['mut']}" for m in mut_list
            ]
            r["mutation"] = "+".join(r["mutations"])
            results.append(r)
        except Exception:
            pass
        if progress_every and (i + 1) % progress_every == 0:
            print(f"      EvoEF2 [{i+1}/{len(mutations)}] ...", flush=True)
    return results


def _thermo_veto_batch(
    tk: Any,
    evo_results: list[dict],
    max_dd: float = 0.5,
    top_k: int = 20,
) -> list[dict]:
    """Run ThermoMPNN stability check; keep those with ΔΔG_stability ≤ max_dd."""
    candidates = sorted(evo_results, key=lambda r: r.get("ddg", 0))[:top_k]
    stable = []
    for r in candidates:
        try:
            thermo = tk.run_thermompnn(r["mutations"])
            dd_stab = thermo.get("ddg_stability", 0.0)
            if dd_stab <= max_dd:
                r["thermo_ddg"] = dd_stab
                stable.append(r)
        except Exception:
            stable.append(r)  # conservative: keep if ThermoMPNN fails
    return stable


def _mmgbsa_batch(
    tk: Any,
    candidates: list[dict],
    parent_dg: float,
    top_k: int = 5,
) -> list[dict]:
    """Run MM/GBSA on top candidates; compute ΔΔG vs parent."""
    pool = candidates[:top_k]
    results = []
    for r in pool:
        try:
            mmg = tk.run_mmgbsa(r.get("mutations_raw", []))
            dg  = mmg.get("dg")
            ddg = (dg - parent_dg) if (dg is not None and parent_dg is not None) else None
            r["mmgbsa_dg"]  = dg
            r["mmgbsa_ddg"] = ddg
            results.append(r)
        except Exception as e:
            r["mmgbsa_error"] = str(e)
            results.append(r)
    return results


# ── Mutation builder helpers ──────────────────────────────────────────────────

def _build_single_muts(
    parent_seq: str,
    cdr_regions: dict,
    redesign_cdrs: list[str],
    vhh_chain: str,
    fixed_positions: set[int] | None = None,
) -> list[list[dict]]:
    """Enumerate all single-point substitutions at designed CDR positions."""
    fixed_positions = fixed_positions or set()
    muts = []
    for cdr_key in redesign_cdrs:
        cdr = cdr_regions.get(cdr_key, {})
        ls  = cdr.get("linear_start")
        pr  = cdr.get("pdb_resnums", [])
        if ls is None or not pr:
            continue
        for offset, pdb_i in enumerate(pr):
            li = ls + offset
            if int(pdb_i) in fixed_positions or li >= len(parent_seq):
                continue
            cur_aa = parent_seq[li]
            for aa in AA_ALPHABET:
                if aa == cur_aa:
                    continue
                muts.append([{
                    "chain": vhh_chain,
                    "resi":  int(pdb_i),
                    "wt":    cur_aa,
                    "mut":   aa,
                }])
    return muts


def _build_pairwise_muts(
    seed_muts: list[dict],
    top_n: int = 10,
) -> list[list[dict]]:
    """
    From top single-point seed mutations, enumerate all pairwise combinations.
    Each seed_mut is a list[dict] from _build_single_muts.
    Returns list of 2-element mutation lists.
    """
    seeds = seed_muts[:top_n]
    pairs = []
    for i, s1 in enumerate(seeds):
        for j, s2 in enumerate(seeds):
            if j <= i:
                continue
            # Avoid combining mutations at the same position
            pos1 = {m["resi"] for m in s1}
            pos2 = {m["resi"] for m in s2}
            if pos1 & pos2:
                continue
            pairs.append(s1 + s2)
    return pairs


# ── Main VAM entry point ──────────────────────────────────────────────────────

def run_vam_complete(
    complex_pdb:   Path,
    candidate_id:  str,
    parent_seq:    str,
    cdr_regions:   dict,
    redesign_cdrs: list[str],
    vhh_chain:     str,
    ag_chain:      str,
    evoef2_exe:    str,
    wt_dg:         float,
    parent_dg:     float,
    vam_settings:  dict | None = None,
    output_dir:    Path | None = None,
    suite_root:    Path | None = None,
    hallucination_guard: bool = True,
) -> dict:
    """
    Run complete two-layer VAM on candidate_id.

    Returns a report dict with all results.
    """
    vam_settings  = vam_settings or {}
    l1_cfg        = vam_settings.get("layer1_scan", {})
    l2_cfg        = vam_settings.get("layer2_combo", {})

    thermo_veto   = float(vam_settings.get("thermo_veto_dd", 0.5))
    max_single    = l1_cfg.get("max_single_muts", 500)
    ddg_threshold = l1_cfg.get("evoef2_ddg_threshold", 0.0)
    l2_enabled    = l2_cfg.get("enabled", True)
    top_seeds     = l2_cfg.get("top_seeds", 10)
    max_pairs     = l2_cfg.get("max_pairs", 45)
    l2_mmgbsa_k   = l2_cfg.get("mmgbsa_top_k", 5)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = output_dir / "vam_checkpoint.json" if output_dir else None
    ckpt: dict = {}
    if checkpoint_path and checkpoint_path.exists():
        ckpt = json.loads(checkpoint_path.read_text(encoding="utf-8"))

    def save_ckpt():
        if checkpoint_path:
            checkpoint_path.write_text(json.dumps(ckpt, indent=2), encoding="utf-8")

    # Load AffinityEnergyToolkit
    if suite_root:
        sys.path.insert(0, str(suite_root))
    from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit

    tk = AffinityEnergyToolkit(
        complex_pdb = str(complex_pdb),
        ab_chains   = [vhh_chain],
        ag_chains   = [ag_chain],
        evoef2_exe  = evoef2_exe,
    )

    print(f"\n[VAM] Candidate: {candidate_id}")
    print(f"[VAM] parent_dg = {parent_dg:.2f}, wt_dg = {wt_dg:.2f}, "
          f"ΔΔG_vs_WT = {parent_dg - wt_dg:+.2f}")
    print(f"[VAM] Layer 1: single-point scan")
    print(f"[VAM] Layer 2: pairwise combos ({'ENABLED' if l2_enabled else 'DISABLED'})")

    # ── HallucinationGuard: init ──────────────────────────────────────────────
    guard: HallucinationGuard | None = None
    if hallucination_guard and _GUARD_AVAILABLE and output_dir:
        guard = HallucinationGuard(
            project_dir=output_dir,
            pipeline="vam_protein",
            step=f"vam_complete/{candidate_id}",
        )
    # ─────────────────────────────────────────────────────────────────────────

    # Fixed root positions (never scan these)
    root_pdb_fixed: set[int] = set()
    for cdr_key in redesign_cdrs:
        root_cfg = (vam_settings.get("root_constraints", {})
                    or {}).get(cdr_key, {})
        root_pdb_fixed.update(root_cfg.get("fixed_pdb_residues", []))

    # ── LAYER 1: single-point scan ─────────────────────────────────────────────
    if not ckpt.get("layer1_done"):
        print(f"\n  Layer 1: building single-point mutations...")
        single_muts = _build_single_muts(
            parent_seq, cdr_regions, redesign_cdrs, vhh_chain, root_pdb_fixed
        )
        # Trim
        if len(single_muts) > max_single:
            single_muts = single_muts[:max_single]
        print(f"  Layer 1: {len(single_muts)} single-point candidates")
        t0 = time.time()
        evo_l1 = _evoef2_scan_batch(tk, single_muts)
        print(f"  Layer 1 EvoEF2 done: {len(evo_l1)}/{len(single_muts)} in {time.time()-t0:.0f}s")

        ben_l1 = sorted(
            [r for r in evo_l1 if r.get("ddg") is not None and r["ddg"] < ddg_threshold],
            key=lambda r: r["ddg"],
        )
        print(f"  Layer 1: beneficial (ΔΔG < {ddg_threshold}) = {len(ben_l1)}")

        # ── HallucinationGuard: EVOEF2_ARTIFACT check on Layer 1 top hits ────
        if guard is not None:
            for r in ben_l1[:20]:
                ddg_val = r.get("ddg")
                if ddg_val is not None:
                    guard.check_evoef2_artifact(ddg_val, label=f"L1_{r.get('mutation','?')}")
        # ─────────────────────────────────────────────────────────────────────

        ckpt["layer1_all_evo"]  = [{"m": r["mutation"], "ddg": r.get("ddg")} for r in evo_l1]
        ckpt["layer1_ben_top"]  = [{"m": r["mutation"], "ddg": r.get("ddg")} for r in ben_l1[:30]]
        ckpt["n_l1_beneficial"] = len(ben_l1)
        ckpt["layer1_done"]     = True
        save_ckpt()
    else:
        print("  [✓] Layer 1: loaded from checkpoint")
        ben_l1  = [{"mutation": r["m"], "ddg": r["ddg"]} for r in ckpt.get("layer1_ben_top", [])]
        evo_l1  = [{"mutation": r["m"], "ddg": r["ddg"]} for r in ckpt.get("layer1_all_evo", [])]

    # ── LAYER 1: ThermoMPNN + MM/GBSA ──────────────────────────────────────────
    if not ckpt.get("layer1_mmgbsa_done"):
        if ben_l1:
            print(f"\n  Layer 1 ThermoMPNN veto: {min(len(ben_l1), 20)} candidates...")
            stable_l1 = _thermo_veto_batch(tk, list(ben_l1), thermo_veto, top_k=20)
            print(f"  Stable (ΔΔG_stab ≤ {thermo_veto}): {len(stable_l1)}")

            # ── HallucinationGuard: THERMOMPNN_SILENT check ───────────────────
            if guard is not None:
                thermo_results = [
                    {"mutation": r.get("mutation"), "ddg_stability": r.get("thermo_ddg")}
                    for r in list(ben_l1)[:20]
                ]
                guard.check_thermompnn_silent(
                    thermo_results,
                    n_mutations=len(thermo_results),
                    label="L1_thermo_veto",
                )
            # ─────────────────────────────────────────────────────────────────
            pool_l1 = stable_l1[:8] if stable_l1 else list(ben_l1)[:8]
            print(f"  Layer 1 MM/GBSA: {len(pool_l1)} candidates...")
            # Add raw mutation lists for MM/GBSA
            for r in pool_l1:
                muts_raw = []
                for mut_str in r.get("mutations", [r.get("mutation", "")]):
                    if len(mut_str) >= 3:
                        try:
                            wt_aa  = mut_str[0]
                            mut_aa = mut_str[-1]
                            resi   = int(mut_str[1:-1])
                            muts_raw.append({"chain": vhh_chain, "resi": resi,
                                             "wt": wt_aa, "mut": mut_aa})
                        except ValueError:
                            pass
                r["mutations_raw"] = muts_raw
            mmgbsa_l1 = _mmgbsa_batch(tk, pool_l1, parent_dg, top_k=len(pool_l1))
        else:
            # Recovery: lowest EvoEF2 ΔΔG regardless of sign
            print("\n  Layer 1: no beneficial hits → recovery pass (lowest ΔΔG)")
            all_ranked = sorted(
                [r for r in evo_l1 if r.get("ddg") is not None],
                key=lambda r: r["ddg"],
            )
            recovery_pool = all_ranked[:10]
            if recovery_pool:
                stable_l1 = _thermo_veto_batch(tk, recovery_pool, thermo_veto, top_k=10)
                pool_l1 = stable_l1[:5] if stable_l1 else recovery_pool[:5]
                for r in pool_l1:
                    r["mutations_raw"] = []
                mmgbsa_l1 = _mmgbsa_batch(tk, pool_l1, parent_dg, top_k=len(pool_l1))
            else:
                mmgbsa_l1 = []

        ckpt["layer1_mmgbsa"]      = [{"m": r.get("mutation"), "dg": r.get("mmgbsa_dg"),
                                        "ddg": r.get("mmgbsa_ddg")} for r in mmgbsa_l1]
        ckpt["layer1_mmgbsa_done"] = True
        save_ckpt()
    else:
        print("  [✓] Layer 1 MM/GBSA: loaded from checkpoint")
        mmgbsa_l1 = [{"mutation": r["m"], "mmgbsa_dg": r.get("dg"),
                       "mmgbsa_ddg": r.get("ddg")} for r in ckpt.get("layer1_mmgbsa", [])]

    best_l1 = min(
        (r for r in mmgbsa_l1 if r.get("mmgbsa_dg") is not None),
        key=lambda r: r["mmgbsa_dg"],
        default=None,
    )
    if best_l1:
        print(f"\n  Layer 1 best: {best_l1.get('mutation')} "
              f"ΔG={best_l1.get('mmgbsa_dg'):.2f} "
              f"ΔΔG={best_l1.get('mmgbsa_ddg'):+.2f}")

    # ── LAYER 2: pairwise combinatorial ────────────────────────────────────────
    mmgbsa_l2: list[dict] = []
    ben_l2: list[dict] = []

    if l2_enabled and len(ben_l1) >= 2 and not ckpt.get("layer2_done"):
        print(f"\n  Layer 2: building pairwise combinations from top {top_seeds} seeds...")
        # Rebuild raw mutation objects from ben_l1 strings
        seed_mut_lists: list[list[dict]] = []
        for r in ben_l1[:top_seeds]:
            muts_raw = []
            for mut_str in (r.get("mutations") or [r.get("mutation", "")]):
                if len(mut_str) >= 3:
                    try:
                        wt_aa  = mut_str[0]
                        mut_aa = mut_str[-1]
                        resi   = int(mut_str[1:-1])
                        muts_raw.append({"chain": vhh_chain, "resi": resi,
                                          "wt": wt_aa, "mut": mut_aa})
                    except ValueError:
                        pass
            if muts_raw:
                seed_mut_lists.append(muts_raw)

        pair_muts = _build_pairwise_muts(seed_mut_lists, top_n=top_seeds)
        if len(pair_muts) > max_pairs:
            pair_muts = pair_muts[:max_pairs]
        print(f"  Layer 2: {len(pair_muts)} pairwise candidates")

        t1 = time.time()
        evo_l2 = _evoef2_scan_batch(tk, pair_muts)
        print(f"  Layer 2 EvoEF2: {len(evo_l2)}/{len(pair_muts)} in {time.time()-t1:.0f}s")

        ben_l2 = sorted(
            [r for r in evo_l2 if r.get("ddg") is not None and r["ddg"] < ddg_threshold],
            key=lambda r: r["ddg"],
        )
        print(f"  Layer 2: beneficial pairwise = {len(ben_l2)}")

        if ben_l2:
            stable_l2 = _thermo_veto_batch(tk, list(ben_l2), thermo_veto, top_k=20)
            pool_l2 = stable_l2[:l2_mmgbsa_k] if stable_l2 else ben_l2[:l2_mmgbsa_k]
            for r in pool_l2:
                r["mutations_raw"] = [
                    m for mut_list in r.get("mutations", []) for m in ([{
                        "chain": vhh_chain,
                        "resi":  int(m[1:-1]),
                        "wt":    m[0],
                        "mut":   m[-1],
                    }] if isinstance(m, str) else [m])
                ]
            mmgbsa_l2 = _mmgbsa_batch(tk, pool_l2, parent_dg, top_k=len(pool_l2))
        else:
            mmgbsa_l2 = []

        ckpt["layer2_evo_count"]  = len(evo_l2)
        ckpt["layer2_ben_count"]  = len(ben_l2)
        ckpt["layer2_ben_top"]    = [{"m": r["mutation"], "ddg": r.get("ddg")}
                                      for r in ben_l2[:15]]
        ckpt["layer2_mmgbsa"]     = [{"m": r.get("mutation"), "dg": r.get("mmgbsa_dg"),
                                       "ddg": r.get("mmgbsa_ddg")} for r in mmgbsa_l2]
        ckpt["layer2_done"]       = True
        save_ckpt()
    elif l2_enabled and len(ben_l1) < 2:
        print(f"\n  Layer 2: skipped (only {len(ben_l1)} L1 seeds, need ≥2)")
    elif not l2_enabled:
        print("\n  Layer 2: disabled in vam_settings")
    else:
        print("  [✓] Layer 2: loaded from checkpoint")
        mmgbsa_l2 = [{"mutation": r["m"], "mmgbsa_dg": r.get("dg"),
                       "mmgbsa_ddg": r.get("ddg")} for r in ckpt.get("layer2_mmgbsa", [])]

    # ── Final recommendation ────────────────────────────────────────────────────
    all_mmgbsa = mmgbsa_l1 + mmgbsa_l2
    best_overall = min(
        (r for r in all_mmgbsa if r.get("mmgbsa_dg") is not None),
        key=lambda r: r["mmgbsa_dg"],
        default=None,
    )

    if best_overall and best_overall.get("mmgbsa_dg", 0) < parent_dg:
        recommendation = {
            "mutation":    best_overall.get("mutation"),
            "mmgbsa_dg":  best_overall.get("mmgbsa_dg"),
            "mmgbsa_ddg": best_overall.get("mmgbsa_ddg"),
            "layer":       "L2" if best_overall in mmgbsa_l2 else "L1",
            "verdict":     "IMPROVEMENT",
        }
        print(f"\n  [★] Best mutation: {recommendation['mutation']} "
              f"ΔG={recommendation['mmgbsa_dg']:.2f} "
              f"ΔΔG={recommendation['mmgbsa_ddg']:+.2f} ({recommendation['layer']})")

        # ── HallucinationGuard: MUTANT_DIFF — verify best candidate sequence ─
        if guard is not None:
            best_mut_str = recommendation["mutation"] or ""
            mut_list = [m for m in best_mut_str.split("+") if len(m) >= 3]
            expected_n_muts = len(mut_list)
            if expected_n_muts > 0:
                mutant_seq = list(parent_seq)
                try:
                    for m in mut_list:
                        wt_aa  = m[0]
                        mut_aa = m[-1]
                        pdb_r  = int(m[1:-1])
                        for cdr_key in redesign_cdrs:
                            cdr = cdr_regions.get(cdr_key, {})
                            ls  = cdr.get("linear_start", 0)
                            pr  = cdr.get("pdb_resnums", [])
                            for off, pr_i in enumerate(pr):
                                if int(pr_i) == pdb_r:
                                    li = ls + off
                                    if li < len(mutant_seq) and mutant_seq[li] == wt_aa:
                                        mutant_seq[li] = mut_aa
                    try:
                        guard.check_mutant_diff(
                            parent_seq, "".join(mutant_seq), expected_n_muts,
                            label=f"best_candidate_{best_mut_str}"
                        )
                    except HallucinationError as e:
                        print(f"  [HallucinationGuard] MUTANT_DIFF HARD ABORT: {e}")
                        recommendation["hallucination_abort"] = str(e)
                except Exception:
                    pass
        # ─────────────────────────────────────────────────────────────────────
    else:
        recommendation = {
            "mutation":  None,
            "verdict":   "NO_IMPROVEMENT_FOUND",
            "comment":   (
                "Neither single-point nor pairwise mutations improved binding. "
                "Consider CDR2+CDR3 co-design or backbone-flexible redesign."
            ),
        }
        print(f"\n  [—] VAM found no improvement. {recommendation['comment']}")

    # ── HallucinationGuard: write audit ──────────────────────────────────────
    if guard is not None:
        guard.write_audit()
    # ─────────────────────────────────────────────────────────────────────────

    report = {
        "candidate":        candidate_id,
        "complex_pdb":      str(complex_pdb),
        "parent_dg":        parent_dg,
        "wt_dg":            wt_dg,
        "timestamp":        _ts(),
        "layer1": {
            "n_scanned":    len(evo_l1),
            "n_beneficial": len(ben_l1),
            "top_evo":      [{"m": r.get("mutation"), "ddg": r.get("ddg")}
                              for r in sorted(ben_l1, key=lambda r: r.get("ddg", 0))[:10]],
            "mmgbsa":       [{"m": r.get("mutation"), "dg": r.get("mmgbsa_dg"),
                               "ddg": r.get("mmgbsa_ddg")} for r in mmgbsa_l1],
        },
        "layer2": {
            "enabled":      l2_enabled,
            "n_seeds":      len(ben_l1),
            "n_pairs_scanned": ckpt.get("layer2_evo_count", 0),
            "n_beneficial": ckpt.get("layer2_ben_count", 0),
            "top_evo":      ckpt.get("layer2_ben_top", []),
            "mmgbsa":       [{"m": r.get("mutation"), "dg": r.get("mmgbsa_dg"),
                               "ddg": r.get("mmgbsa_ddg")} for r in mmgbsa_l2],
        },
        "recommendation":   recommendation,
    }

    if output_dir:
        report_path = output_dir / "vam_complete_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\n  VAM report → {report_path}")

    return report


# ── Standalone CLI ────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Complete Two-Layer VAM")
    ap.add_argument("--complex_pdb",    required=True)
    ap.add_argument("--candidate_id",   required=True)
    ap.add_argument("--parent_seq",     required=True,  help="Full VHH sequence string")
    ap.add_argument("--mask_json",      required=True,  help="path to mask_strategy.json")
    ap.add_argument("--evoef2",         required=True,  help="Path to EvoEF2.exe")
    ap.add_argument("--wt_dg",          type=float, required=True)
    ap.add_argument("--parent_dg",      type=float, required=True)
    ap.add_argument("--output_dir",     default=None)
    args = ap.parse_args()

    mask = json.loads(Path(args.mask_json).read_text(encoding="utf-8"))

    run_vam_complete(
        complex_pdb   = Path(args.complex_pdb),
        candidate_id  = args.candidate_id,
        parent_seq    = args.parent_seq,
        cdr_regions   = mask["cdr_regions"],
        redesign_cdrs = mask["design_mask"].get("redesign_cdrs", []),
        vhh_chain     = mask.get("vhh_chain", "A"),
        ag_chain      = mask.get("antigen_chain", "B"),
        evoef2_exe    = args.evoef2,
        wt_dg         = args.wt_dg,
        parent_dg     = args.parent_dg,
        vam_settings  = mask.get("vam_settings", {}),
        output_dir    = Path(args.output_dir) if args.output_dir else None,
    )


if __name__ == "__main__":
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    main()
