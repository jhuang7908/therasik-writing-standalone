"""
L2b: AbLang 
 EvoEF2 L1 + ThermoMPNN L2a  AbLang 。
ΔlogP = mean_logP(mut) - mean_logP(WT) < -0.3 →  → （）

AbLang ；
 ESM-2 ：ESM-2 ，AbLang 。

Usage (from repo root):
    python scripts/affinity_maturation/ablang_l2b.py
"""

import csv
from pathlib import Path
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG     = yaml.safe_load((SCRIPT_DIR / "config.yaml").read_text(encoding="utf-8"))
WT_SEQ     = CONFIG["sequence"]["wt"]
OUTPUT_DIR = Path((SCRIPT_DIR / CONFIG["paths"]["output_dir"]).resolve())
DELTA_MIN  = CONFIG["gates_l2"]["delta_logp_min"]   # default -0.3

# Kabat → 0-based sequence index
def build_kabat_map():
    skip = {10, 31, 32, 33, 34, 60, 61, 73}
    pdb_resi = [i for i in range(1, 129) if i not in skip]
    return {kabat: idx for idx, kabat in enumerate(pdb_resi)}

KABAT_MAP = build_kabat_map()


def apply_mutation(seq, kabat_site, mut_aa):
    idx = KABAT_MAP.get(kabat_site)
    if idx is None:
        raise ValueError(f"Kabat {kabat_site} not in map")
    return seq[:idx] + mut_aa + seq[idx+1:]


def load_l2a_passed():
    """ ThermoMPNN 。"""
    csv_path = OUTPUT_DIR / "thermompnn_cross_results.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f" thermompnn_cross.py: {csv_path}")
    passed = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            if row.get("verdict", "").strip() == "PASS":
                passed.append({
                    "mutation":    row["mutation"],
                    "site":        int(row["site"]),
                    "wt_aa":       row["wt_aa"],
                    "mut_aa":      row["mut_aa"],
                    "evoef2_ddg":  float(row["evoef2_ddg"]),
                    "ddg_fold":    float(row["ddg_fold"]) if row["ddg_fold"] else None,
                })
    return passed


def run_ablang():
    import ablang
    import numpy as np

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 62)
    print("L2b: AbLang ")
    print(f"  : ΔlogP < {DELTA_MIN} → （， WARN）")
    print("=" * 62)

    candidates = load_l2a_passed()
    print(f"\nL2a : {len(candidates)}")

    # （）
    print(" AbLang heavy ...")
    model = ablang.pretrained("heavy")
    model.freeze()

    # WT 
    wt_lh    = model([WT_SEQ], mode="likelihood")
    wt_score = float(np.mean(wt_lh))
    print(f"WT AbLang score: {wt_score:.4f}\n")

    results = []
    for c in candidates:
        try:
            mut_seq   = apply_mutation(WT_SEQ, c["site"], c["mut_aa"])
            mut_lh    = model([mut_seq], mode="likelihood")
            mut_score = float(np.mean(mut_lh))
            delta     = mut_score - wt_score
        except Exception as e:
            mut_score = float("nan")
            delta     = float("nan")
            print(f"  [ERR] {c['mutation']}: {e}")

        passed_ablang = True if delta != delta else (delta >= DELTA_MIN)
        status = "PASS" if passed_ablang else "WARN"

        results.append({
            **c,
            "ablang_wt":    round(wt_score, 4),
            "ablang_mut":   round(mut_score, 4) if mut_score == mut_score else "",
            "ablang_delta": round(delta, 4)     if delta == delta else "",
            "ablang_pass":  status,
        })

    # 
    out_csv = OUTPUT_DIR / "ablang_l2b_results.csv"
    fields  = ["mutation","site","wt_aa","mut_aa","evoef2_ddg","ddg_fold",
               "ablang_wt","ablang_mut","ablang_delta","ablang_pass"]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    # 
    passed  = [r for r in results if r["ablang_pass"] == "PASS"]
    warned  = [r for r in results if r["ablang_pass"] == "WARN"]

    print(f"\n{'='*62}")
    print(f"AbLang : {len(passed)} / {len(results)}")
    print(f"AbLang : {len(warned)} / {len(results)}  (Δ < {DELTA_MIN}, )")
    print(f"{'='*62}")

    if warned:
        print("\n─── （WARN，）───")
        for r in sorted(warned, key=lambda x: x["ablang_delta"]):
            print(f"  {r['mutation']:<12s}  EvoEF2={r['evoef2_ddg']:+.3f}"
                  f"  ddG_fold={str(r['ddg_fold']):>7s}"
                  f"  ΔAbLang={r['ablang_delta']:+.4f}  WARN")

    print("\n───  AbLang （EvoEF2）───")
    print(f"{'Mutation':<12s}  {'EvoEF2':>8s}  {'ddG_fold':>9s}  "
          f"{'ΔAbLang':>9s}  {'Status'}")
    print("-" * 58)
    for r in sorted(results, key=lambda x: x["evoef2_ddg"]):
        fold  = f"{r['ddg_fold']:+.4f}" if r["ddg_fold"] is not None else "  N/A"
        delta = f"{r['ablang_delta']:+.4f}" if r["ablang_delta"] != "" else "  N/A"
        flag  = "⚠" if r["ablang_pass"] == "WARN" else " "
        print(f"{r['mutation']:<12s}  {r['evoef2_ddg']:>+8.3f}  {fold:>9s}  "
              f"{delta:>9s}  {flag}{r['ablang_pass']}")

    print(f"\n: {out_csv}")
    return results


if __name__ == "__main__":
    run_ablang()
