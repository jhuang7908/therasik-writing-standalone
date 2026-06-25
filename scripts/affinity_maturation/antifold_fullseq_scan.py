"""
 AntiFold 
=====================================
 VHH （120 AA） 19 ，
 ΔlogP = log P(mut) - log P(wt)，。

： EvoEF2 ：
  - Vernier （ CDR ）
  - （/CDR ）
  - （）

：
  affinity_maturation_v2/antifold_fullseq_scan.csv  —  120×19 
  affinity_maturation_v2/antifold_hotspot_map.txt   — ，

Usage (from repo root):
    wsl python3 scripts/affinity_maturation/antifold_fullseq_scan.py
"""

import csv
import sys
from pathlib import Path

import yaml

# ──  ──────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
CONFIG       = yaml.safe_load((SCRIPT_DIR / "config.yaml").read_text(encoding="utf-8"))
WT_SEQ       = CONFIG["sequence"]["wt"]          # 120 AA
OUTPUT_DIR   = Path((SCRIPT_DIR / CONFIG["paths"]["output_dir"]).resolve())
COMPLEX_PDB  = str((SCRIPT_DIR / CONFIG["paths"]["complex_pdb"]).resolve())

ANTIFOLD_DIR = (SCRIPT_DIR / "../../tools/AntiFold").resolve()
sys.path.insert(0, str(ANTIFOLD_DIR))

# Kabat→0-based index（ ablang_score.py ）
def _build_kabat_map() -> dict[int, int]:
    skip = {10, 31, 32, 33, 34, 60, 61, 73}
    pdb_resi = [i for i in range(1, 129) if i not in skip]
    assert len(pdb_resi) == 120
    return {kabat: idx for idx, kabat in enumerate(pdb_resi)}

KABAT_MAP  = _build_kabat_map()
IDX_TO_KABAT = {v: k for k, v in KABAT_MAP.items()}

ALL_AA = list("ACDEFGHIKLMNPQRSTVWY")

# Vernier  Kabat （VHH ， CDR ）
VHH_VERNIER = {37, 44, 45, 47, 67, 69, 71, 78, 93, 94}

# ── AntiFold  ─────────────────────────────────────────────────────
def score_sequence_antifold(seq: str) -> float:
    """ mean per-residue log-likelihood（AntiFold ）。"""
    from antifold.main import AntiFoldModel
    import torch, tempfile, os

    model = AntiFoldModel()
    model.eval()

    # AntiFold ； PDB（VHH chain A）
    with torch.no_grad():
        try:
            score = model.score_sequence(
                pdb_path=COMPLEX_PDB,
                sequence=seq,
                chain="A",
            )
            return float(score)
        except Exception:
            # ， score_pdb
            pass

    # ： fasta  predict 
    try:
        from antifold.main import predict_logits
        logits = predict_logits(
            pdb_path=COMPLEX_PDB,
            chain_heavy="A",
            chain_light="",
        )
        # logits shape: [L, 20]  —  log-softmax 
        import torch.nn.functional as F
        log_probs = F.log_softmax(logits, dim=-1)
        aa_idx = [ALL_AA.index(aa) for aa in seq if aa in ALL_AA]
        total = sum(float(log_probs[i, j]) for i, j in enumerate(aa_idx))
        return total / max(len(aa_idx), 1)
    except Exception as e:
        raise RuntimeError(f"AntiFold scoring failed: {e}")


def run_full_scan():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 68)
    print("AntiFold （120  × 19 AA = 2280 ）")
    print(f"  : {COMPLEX_PDB}")
    print(f"  VHH : {len(WT_SEQ)} AA")
    print("=" * 68)

    # 1.  WT baseline
    print("\n[1/3]  WT  log-likelihood...")
    wt_score = score_sequence_antifold(WT_SEQ)
    print(f"  WT score: {wt_score:.4f}")

    # 2. 
    print("\n[2/3]  2280 ...\n")
    rows = []
    for idx in range(len(WT_SEQ)):
        wt_aa  = WT_SEQ[idx]
        kabat  = IDX_TO_KABAT[idx]
        is_vernier = kabat in VHH_VERNIER

        site_best = None
        for mut_aa in ALL_AA:
            if mut_aa == wt_aa:
                continue
            mut_seq  = WT_SEQ[:idx] + mut_aa + WT_SEQ[idx+1:]
            try:
                mut_score = score_sequence_antifold(mut_seq)
                delta     = mut_score - wt_score
            except Exception as e:
                mut_score = float("nan")
                delta     = float("nan")
                print(f"  [WARN] {wt_aa}{kabat}{mut_aa}: {e}")

            rows.append({
                "kabat":      kabat,
                "seq_idx":    idx + 1,
                "wt_aa":      wt_aa,
                "mut_aa":     mut_aa,
                "mutation":   f"{wt_aa}{kabat}{mut_aa}",
                "wt_score":   round(wt_score, 4),
                "mut_score":  round(mut_score, 4) if not (mut_score != mut_score) else "",
                "delta_logp": round(delta, 4)     if not (delta != delta) else "",
                "is_vernier": is_vernier,
            })
            if site_best is None or (isinstance(delta, float) and isinstance(
                    (site_best or {}).get("delta_logp", -999), float)
                    and delta > site_best.get("delta_logp", -999)):
                site_best = {"delta_logp": delta}

        #  10 
        if (idx + 1) % 10 == 0:
            print(f"  ... {idx+1}/120 ")

    # 3. 
    out_csv = OUTPUT_DIR / "antifold_fullseq_scan.csv"
    fields  = ["kabat","seq_idx","wt_aa","mut_aa","mutation",
               "wt_score","mut_score","delta_logp","is_vernier"]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\n: {out_csv}")

    # 4. （ delta_logp — ）
    print("\n[3/3] ...")
    _write_hotspot_map(rows, wt_score)

    print("=" * 68)
    print("。")
    print("=" * 68)


def _write_hotspot_map(rows: list[dict], wt_score: float):
    """： min/mean delta_logp，。"""
    from collections import defaultdict
    site_deltas = defaultdict(list)
    for r in rows:
        d = r["delta_logp"]
        if isinstance(d, float) and d == d:
            site_deltas[(r["kabat"], r["wt_aa"], r["is_vernier"])].append(d)

    out_map = OUTPUT_DIR / "antifold_hotspot_map.txt"
    lines   = []
    lines.append("=" * 72)
    lines.append("AntiFold   (ΔlogP < -0.5 → )")
    lines.append(f"WT baseline: {wt_score:.4f}")
    lines.append("=" * 72)
    lines.append(f"{'Kabat':>6}  {'WT':>3}  {'min_ΔlogP':>10}  {'mean_ΔlogP':>11}  {'n_pass':>6}  {'Vernier':>7}  Grade")
    lines.append("-" * 72)

    summary = []
    for (kabat, wt_aa, is_v), deltas in sorted(site_deltas.items()):
        min_d  = min(deltas)
        mean_d = sum(deltas) / len(deltas)
        n_pass = sum(1 for d in deltas if d >= -0.3)   # tolerant substitutions
        # ：min_delta_logp  →  → 
        if min_d < -2.0:
            grade = "🔴 CRITICAL"
        elif min_d < -1.0:
            grade = "🟠 HIGH"
        elif min_d < -0.5:
            grade = "🟡 MODERATE"
        else:
            grade = "  flexible"
        summary.append((kabat, wt_aa, min_d, mean_d, n_pass, is_v, grade))

    #  min_delta_logp （）
    summary.sort(key=lambda x: x[2])
    for kabat, wt_aa, min_d, mean_d, n_pass, is_v, grade in summary:
        v_tag = "★" if is_v else " "
        lines.append(f"{kabat:>6}  {wt_aa:>3}  {min_d:>10.3f}  {mean_d:>11.3f}  {n_pass:>6}  {v_tag:>7}  {grade}")

    lines.append("=" * 72)
    lines.append("★ = Vernier ")
    lines.append("n_pass = 19 AA  ΔlogP ≥ -0.3 （→）")

    map_text = "\n".join(lines)
    out_map.write_text(map_text, encoding="utf-8")
    print(map_text)
    print(f"\n: {out_map}")


if __name__ == "__main__":
    run_full_scan()
