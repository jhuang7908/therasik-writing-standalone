#!/usr/bin/env python
"""
Benchmark affinity-energy tools on a PAG1-scale AF2-Multimer complex.

Usage (repo root, conda affmat):
  python scripts/pag1_affinity_tool_benchmark.py

Outputs wall-clock seconds per tool for WT + one test mutation (A:95:Y:F on VH).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PDB = (
    ROOT
    / "projects/PAG-1 project/7m_humanPAG1/7m_humanPAG1_df5fc/"
      "7m_humanPAG1_df5fc_relaxed_rank_001_alphafold2_multimer_v3_model_5_seed_000.pdb"
)

MUT = [{"chain": "A", "resi": 95, "wt": "Y", "mut": "F"}]


def main() -> int:
    from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit

    pdb = str(DEFAULT_PDB.resolve())
    if not Path(pdb).is_file():
        print("Missing PDB:", pdb)
        return 1

    tk = AffinityEnergyToolkit(
        complex_pdb=pdb,
        ab_chains=["A", "B"],
        ag_chains=["C"],
    )

    rows: list[dict] = []

    def bench(name: str, fn) -> None:
        t0 = time.perf_counter()
        try:
            out = fn()
            dt = time.perf_counter() - t0
            rows.append(
                {
                    "tool": name,
                    "wall_s": round(dt, 2),
                    "error": out.get("error"),
                    "dg": out.get("dg"),
                    "ddg": out.get("ddg"),
                }
            )
            err = out.get("error")
            print(
                f"{name:14s}  {dt:7.2f}s  dg={out.get('dg')}  "
                f"ddg={out.get('ddg')}  err={err}"
            )
        except Exception as e:
            dt = time.perf_counter() - t0
            rows.append({"tool": name, "wall_s": round(dt, 2), "error": str(e)})
            print(f"{name:14s}  {dt:7.2f}s  EXCEPTION: {e}")

    print("PDB:", pdb)
    print("Chains: AB (VH+VL) vs C (PAG1 ~32 aa)")
    print("Mutation:", MUT)
    print("-" * 72)

    bench("EvoEF2_WT", lambda: tk.run_evoef2([]))
    wt_evo = next((r["dg"] for r in rows if r["tool"] == "EvoEF2_WT"), None)
    bench("EvoEF2_mut", lambda: tk.run_evoef2(MUT, wt_dg=wt_evo))

    bench("PRODIGY_WT", lambda: tk.run_prodigy([]))
    wt_pr = next((r["dg"] for r in rows if r["tool"] == "PRODIGY_WT"), None)
    bench("PRODIGY_mut", lambda: tk.run_prodigy(MUT, wt_dg=wt_pr))

    bench("MMGBSA_WT", lambda: tk.run_mmgbsa([], minimization_steps=100))
    wt_mm = next((r["dg"] for r in rows if r["tool"] == "MMGBSA_WT"), None)
    bench("MMGBSA_mut", lambda: tk.run_mmgbsa(MUT, wt_dg=wt_mm, minimization_steps=100))

    t0 = time.perf_counter()
    try:
        r_wt = tk.run_esm_if1([])
        wt_esm = r_wt.get("wt_logp")
        r_mut = tk.run_esm_if1(MUT, wt_logp=wt_esm)
        dt = time.perf_counter() - t0
        rows.append(
            {
                "tool": "ESMIF1_WT+mut",
                "wall_s": round(dt, 2),
                "error": r_mut.get("error") or r_wt.get("error"),
                "dg": None,
                "ddg": r_mut.get("ddg"),
            }
        )
        print(
            f"{'ESMIF1_WT+mut':14s}  {dt:7.2f}s  dg=None  ddg={r_mut.get('ddg')}  "
            f"err={r_mut.get('error') or r_wt.get('error')}"
        )
    except Exception as e:
        dt = time.perf_counter() - t0
        rows.append({"tool": "ESMIF1_WT+mut", "wall_s": round(dt, 2), "error": str(e)})
        print(f"{'ESMIF1_WT+mut':14s}  {dt:7.2f}s  SKIP: {e}")

    bench("ThermoMPNN", lambda: tk.run_thermompnn(MUT))
    bench("AntiFold", lambda: tk.run_antifold(MUT))

    out_dir = ROOT / "projects/PAG-1 project/pag1_bench_tmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "affinity_tool_benchmark_7m_humanPAG1.json"
    out_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("-" * 72)
    print("Saved:", out_json)

    print("\nPer-variant wall time (WT + mut):")
    by_tool = {r["tool"]: r["wall_s"] for r in rows}
    pairs = [
        ("EvoEF2", "EvoEF2_WT", "EvoEF2_mut"),
        ("PRODIGY", "PRODIGY_WT", "PRODIGY_mut"),
        ("MM/GBSA (100 steps)", "MMGBSA_WT", "MMGBSA_mut"),
    ]
    for label, a, b in pairs:
        ta, tb = by_tool.get(a), by_tool.get(b)
        if ta is not None and tb is not None:
            tot = ta + tb
            print(f"  {label:22s}  WT {ta:6.2f}s  + mut {tb:6.2f}s  = {tot:6.2f}s")
    if "ESMIF1_WT+mut" in by_tool:
        v = by_tool["ESMIF1_WT+mut"]
        print(f"  {'ESM-IF1 (paired)':22s}  combined {v:6.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
