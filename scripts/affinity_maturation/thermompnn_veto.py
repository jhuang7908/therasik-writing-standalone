"""
Phase 3a — ThermoMPNN （VAM Standard Scenario C MANDATORY）

 EvoEF2 L1  ΔΔG_fold（）。
：ΔΔG_fold > +0.5 kcal/mol →  → 

：VAM Standard §3.4 + Cursor Rule:
  "ThermoMPNN measures stability, not binding — use as veto only (ΔΔG > +0.5 → exclude)"

⚠️  ThermoMPNN  MM/GBSA （PAG1 r = −0.786）
     ThermoMPNN ΔΔG 

Usage (from repo root, conda activate affmat):
    python scripts/affinity_maturation/thermompnn_veto.py
"""

import csv
import sys
import os
from pathlib import Path

import yaml

SCRIPT_DIR  = Path(__file__).resolve().parent
CONFIG      = yaml.safe_load((SCRIPT_DIR / "config.yaml").read_text(encoding="utf-8"))
COMPLEX_PDB = str((SCRIPT_DIR / CONFIG["paths"]["complex_pdb"]).resolve())
OUTPUT_DIR  = Path((SCRIPT_DIR / CONFIG["paths"]["output_dir"]).resolve())
VHH_CHAIN   = CONFIG["project"]["vhh_chain"]
DDG_FOLD_THRESHOLD = CONFIG["gates_thermompnn"]["ddg_fold_threshold"]

# ThermoMPNN 
THERMOMPNN_DIR = (SCRIPT_DIR / "../../tools/ThermoMPNN").resolve()
sys.path.insert(0, str(THERMOMPNN_DIR))

#  EvoEF2 L1 
L1_CSV = OUTPUT_DIR / "evoef2_scan_results.csv"


def load_l1_passed() -> list[dict]:
    """ EvoEF2 L1 。"""
    if not L1_CSV.exists():
        raise FileNotFoundError(f"L1 : {L1_CSV}\n evoef2_scan.py")
    passed = []
    with open(L1_CSV) as f:
        for row in csv.DictReader(f):
            if row.get("error"):
                continue
            try:
                ddg = float(row["ddg_bind"])
                if ddg < float(CONFIG["gates_l1"]["ddg_bind_threshold"]):
                    passed.append({
                        "mutation": row["mutation"],
                        "site": int(row["site"]),
                        "wt_aa": row["wt_aa"],
                        "mut_aa": row["mut_aa"],
                        "evoef2_ddg": ddg,
                    })
            except (ValueError, KeyError):
                continue
    return passed


def run_thermompnn(mutations: list[dict]) -> list[dict]:
    """
     ThermoMPNN  ΔΔG_fold。
     AffinityEnergyToolkit （），。
    """
    try:
        sys.path.insert(0, str((SCRIPT_DIR / "../../core/structure").resolve()))
        from affinity_energy_toolkit import AffinityEnergyToolkit
        tk = AffinityEnergyToolkit(
            complex_pdb=COMPLEX_PDB,
            ab_chains=[VHH_CHAIN],
            ag_chains=[CONFIG["project"]["antigen_chain"]],
        )
        results = []
        for m in mutations:
            mut_spec = [{"chain": VHH_CHAIN, "resi": m["site"],
                         "wt": m["wt_aa"], "mut": m["mut_aa"]}]
            try:
                res = tk.run_thermompnn(mut_spec)
                ddg_fold = res.get("ddg", None)
            except Exception as e:
                ddg_fold = None
                print(f"  [WARN] ThermoMPNN failed for {m['mutation']}: {e}")
            results.append({**m, "ddg_fold": ddg_fold})
        return results

    except ImportError:
        # AffinityEnergyToolkit ， ThermoMPNN predict.py
        return _run_thermompnn_direct(mutations)


def _run_thermompnn_direct(mutations: list[dict]) -> list[dict]:
    """ ThermoMPNN predict.py（AffinityEnergyToolkit ）。"""
    import subprocess, json, tempfile
    results = []
    predict_script = THERMOMPNN_DIR / "predict.py"
    if not predict_script.exists():
        print(f"[ERROR] ThermoMPNN predict.py : {predict_script}")
        return [{**m, "ddg_fold": None, "error": "predict.py not found"} for m in mutations]

    for m in mutations:
        mut_str = f"{m['wt_aa']}{m['site']}{m['mut_aa']}"
        cmd = [
            sys.executable, str(predict_script),
            "--pdb", COMPLEX_PDB,
            "--chain", VHH_CHAIN,
            "--mutation", mut_str,
        ]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            #  ddG 
            ddg_fold = None
            for line in out.stdout.splitlines():
                if "ddG" in line or "ddg" in line.lower():
                    parts = line.split()
                    for p in parts:
                        try:
                            ddg_fold = float(p)
                            break
                        except ValueError:
                            continue
            results.append({**m, "ddg_fold": ddg_fold})
        except Exception as e:
            results.append({**m, "ddg_fold": None, "error": str(e)})
    return results


def run_veto():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 65)
    print("Phase 3a: ThermoMPNN ")
    print(f"  : {COMPLEX_PDB}")
    print(f"  : ΔΔG_fold > +{DDG_FOLD_THRESHOLD} kcal/mol → ")
    print("=" * 65)

    l1_passed = load_l1_passed()
    if not l1_passed:
        print("[WARN] L1 ， ThermoMPNN。")
        return

    print(f"\nL1 : {len(l1_passed)}")
    for m in l1_passed:
        print(f"  {m['mutation']}  EvoEF2 ΔΔG={m['evoef2_ddg']:+.3f}")

    print("\n ThermoMPNN...\n")
    results = run_thermompnn(l1_passed)

    # 
    passed, vetoed = [], []
    for r in results:
        ddg_fold = r.get("ddg_fold")
        if ddg_fold is None:
            status = "UNKNOWN"
            passed.append(r)  # ，
        elif ddg_fold > DDG_FOLD_THRESHOLD:
            status = f"VETO (ΔΔG_fold={ddg_fold:+.3f} > +{DDG_FOLD_THRESHOLD})"
            vetoed.append(r)
        else:
            status = f"PASS (ΔΔG_fold={ddg_fold:+.3f})"
            passed.append(r)
        print(f"  {r['mutation']:12s}  {status}")

    # 
    out_csv = OUTPUT_DIR / "thermompnn_veto_results.csv"
    fields = ["mutation", "site", "wt_aa", "mut_aa", "evoef2_ddg", "ddg_fold",
              "thermompnn_pass", "error"]
    rows = []
    for r in results:
        ddg_fold = r.get("ddg_fold")
        if ddg_fold is None:
            tp = "UNKNOWN"
        elif ddg_fold > DDG_FOLD_THRESHOLD:
            tp = "VETO"
        else:
            tp = "PASS"
        rows.append({
            "mutation": r["mutation"],
            "site": r["site"],
            "wt_aa": r["wt_aa"],
            "mut_aa": r["mut_aa"],
            "evoef2_ddg": r["evoef2_ddg"],
            "ddg_fold": ddg_fold if ddg_fold is not None else "",
            "thermompnn_pass": tp,
            "error": r.get("error", ""),
        })
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"\n{'=' * 65}")
    print(f": {len(passed)} / {len(results)}  | : {len(vetoed)} / {len(results)}")
    print(f": {out_csv}")
    print("=" * 65)
    return rows


if __name__ == "__main__":
    run_veto()
