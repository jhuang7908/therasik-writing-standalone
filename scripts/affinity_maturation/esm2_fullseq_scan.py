"""
ESM-2 
=================================
 ESM-2  VHH （120 AA）。
 ΔlogP = log P(mut_aa | context) - log P(wt_aa | context)

： EvoEF2 
  - ΔlogP << 0 →  WT AA → 
  - ΔlogP ≈ 0  →  → 

：ESM-2 -only （），。
     EvoEF2 ：EvoEF2 （），ESM-2 （）。

Usage (from repo root):
    python scripts/affinity_maturation/esm2_fullseq_scan.py
"""

import csv
import sys
from pathlib import Path

import yaml
import torch

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG     = yaml.safe_load((SCRIPT_DIR / "config.yaml").read_text(encoding="utf-8"))
WT_SEQ     = CONFIG["sequence"]["wt"]
OUTPUT_DIR = Path((SCRIPT_DIR / CONFIG["paths"]["output_dir"]).resolve())

ALL_AA = list("ACDEFGHIKLMNPQRSTVWY")

# VHH Vernier （Kabat ，）
VHH_VERNIER_KABAT = {37, 44, 45, 47, 67, 69, 71, 78, 93, 94}

# Kabat → 0-based index
def _build_kabat_map():
    skip = {10, 31, 32, 33, 34, 60, 61, 73}
    pdb_resi = [i for i in range(1, 129) if i not in skip]
    return {kabat: idx for idx, kabat in enumerate(pdb_resi)}

KABAT_MAP    = _build_kabat_map()
IDX_TO_KABAT = {v: k for k, v in KABAT_MAP.items()}


def load_esm2():
    """ ESM-2 150M （，）。"""
    import esm
    print(" ESM-2 (esm2_t6_8M_UR50D)...")
    try:
        model, alphabet = esm.pretrained.esm2_t6_8M_UR50D()
    except Exception:
        print("  8M ， 150M...")
        model, alphabet = esm.pretrained.esm2_t12_35M_UR50D()
    model.eval()
    return model, alphabet


def get_masked_logprobs(model, alphabet, seq: str) -> list[list[float]]:
    """
     masked prediction， [L, 20]  log-prob 。
    masked_logprobs[i][j] = log P(AA_j | context without pos i)
    """
    batch_converter = alphabet.get_batch_converter()
    L = len(seq)
    mask_token = alphabet.mask_idx

    all_logprobs = []
    with torch.no_grad():
        for i in range(L):
            masked = list(seq)
            masked[i] = "<mask>"
            masked_str = "".join(masked)

            data = [("vhh", masked_str)]
            _, _, tokens = batch_converter(data)

            logits = model(tokens, repr_layers=[])["logits"]  # [1, L+2, vocab]
            pos_logits = logits[0, i + 1, :]  # +1 for <cls>

            #  20  AA  log-softmax
            aa_indices = [alphabet.get_idx(aa) for aa in ALL_AA]
            logprobs   = torch.log_softmax(pos_logits, dim=-1)
            site_lp    = [float(logprobs[idx]) for idx in aa_indices]
            all_logprobs.append(site_lp)

    return all_logprobs


def run_scan():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 68)
    print("ESM-2 ")
    print(f"  VHH: {len(WT_SEQ)} AA  |  : {len(WT_SEQ) * 19} = {len(WT_SEQ)}×19")
    print("=" * 68)

    model, alphabet = load_esm2()

    print("\n[1/2]  masked log-probabilities...")
    logprobs = get_masked_logprobs(model, alphabet, WT_SEQ)

    print("[2/2] ...\n")
    rows = []
    site_summary = []

    for idx in range(len(WT_SEQ)):
        wt_aa    = WT_SEQ[idx]
        kabat    = IDX_TO_KABAT[idx]
        is_v     = kabat in VHH_VERNIER_KABAT

        wt_aa_j  = ALL_AA.index(wt_aa) if wt_aa in ALL_AA else None
        wt_lp    = logprobs[idx][wt_aa_j] if wt_aa_j is not None else 0.0

        site_deltas = []
        for mut_aa in ALL_AA:
            if mut_aa == wt_aa:
                continue
            mut_j  = ALL_AA.index(mut_aa)
            mut_lp = logprobs[idx][mut_j]
            delta  = mut_lp - wt_lp
            rows.append({
                "kabat":      kabat,
                "seq_idx":    idx + 1,
                "wt_aa":      wt_aa,
                "mut_aa":     mut_aa,
                "mutation":   f"{wt_aa}{kabat}{mut_aa}",
                "wt_logp":    round(wt_lp, 4),
                "mut_logp":   round(mut_lp, 4),
                "delta_logp": round(delta, 4),
                "is_vernier": is_v,
            })
            site_deltas.append(delta)

        min_d  = min(site_deltas)
        mean_d = sum(site_deltas) / len(site_deltas)
        n_tol  = sum(1 for d in site_deltas if d >= -1.0)
        site_summary.append((kabat, idx+1, wt_aa, wt_lp, min_d, mean_d, n_tol, is_v))

    # 
    out_csv = OUTPUT_DIR / "esm2_fullseq_scan.csv"
    fields  = ["kabat","seq_idx","wt_aa","mut_aa","mutation",
               "wt_logp","mut_logp","delta_logp","is_vernier"]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # 
    _print_hotspot_map(site_summary, out_csv)


def _print_hotspot_map(summary, out_csv):
    #  min_delta_logp （）
    summary_sorted = sorted(summary, key=lambda x: x[4])

    lines = []
    lines.append("=" * 78)
    lines.append("ESM-2 ")
    lines.append("min_ΔlogP: （ →  → ）")
    lines.append("n_tol:     19 ΔlogP ≥ -1.0 （ → ）")
    lines.append("=" * 78)
    lines.append(f"{'Kabat':>6}  {'AA':>3}  {'WT_logP':>8}  {'min_Δ':>8}  {'mean_Δ':>8}  {'n_tol':>5}  {'V':>2}  Grade")
    lines.append("-" * 78)

    for kabat, sidx, wt_aa, wt_lp, min_d, mean_d, n_tol, is_v in summary_sorted:
        if min_d < -4.0:
            grade = "🔴 CRITICAL"
        elif min_d < -2.5:
            grade = "🟠 HIGH"
        elif min_d < -1.5:
            grade = "🟡 MODERATE"
        else:
            grade = "  flexible"
        v = "★" if is_v else " "
        lines.append(f"{kabat:>6}  {wt_aa:>3}  {wt_lp:>8.3f}  {min_d:>8.3f}  {mean_d:>8.3f}  {n_tol:>5}  {v:>2}  {grade}")

    lines.append("=" * 78)
    lines.append("★ = Vernier （VHH  CDR ）")

    # 
    interface_kabat = {49, 50, 51, 52, 55, 62, 64, 66, 67, 70, 111, 112, 113}
    lines.append("\n── （≥1 HER2 contact） ESM-2  ──")
    for kabat, sidx, wt_aa, wt_lp, min_d, mean_d, n_tol, is_v in summary_sorted:
        if kabat in interface_kabat:
            lines.append(f"  {wt_aa}{kabat}  min_Δ={min_d:+.3f}  n_tol={n_tol}")

    map_text = "\n".join(lines)
    out_map  = OUTPUT_DIR.parent / "affinity_maturation_v2" / "esm2_hotspot_map.txt"
    out_map.parent.mkdir(parents=True, exist_ok=True)
    out_map.write_text(map_text, encoding="utf-8")

    print(map_text)
    print(f"\n: {out_csv}")
    print(f": {out_map}")


if __name__ == "__main__":
    run_scan()
