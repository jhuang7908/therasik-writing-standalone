"""
L2: AbLang pseudo-likelihood scoring for antibody nativeness.

For each candidate mutant sequence, computes the AbLang pseudo-log-likelihood
and compares to wild-type. Mutations that push the sequence away from the
natural antibody distribution are flagged.

Usage (from repo root, conda activate affmat):
    python scripts/affinity_maturation/ablang_score.py
"""

import csv
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG = yaml.safe_load((SCRIPT_DIR / "config.yaml").read_text(encoding="utf-8"))

WT_SEQ = CONFIG["sequence"]["wt"]
MUTATIONS = CONFIG["mutations"]
OUTPUT_DIR = Path((SCRIPT_DIR / CONFIG["paths"]["output_dir"]).resolve())
DELTA_LOGP_MIN = CONFIG["gates_l2"]["delta_logp_min"]


def _apply_mutation(seq: str, kabat_site: int, mut_aa: str) -> str:
    """Map Kabat numbering to 0-based sequence index and apply mutation.

    The PDB uses Kabat numbering with gaps. We build a mapping from the
    PDB ATOM records to handle this, but for a simpler approximation we
    use the known VHH Kabat→sequence-index mapping for VGRW_SR_R2.
    """
    kabat_to_idx = _build_kabat_map()
    idx = kabat_to_idx.get(kabat_site)
    if idx is None:
        raise ValueError(f"Kabat site {kabat_site} not found in mapping")
    return seq[:idx] + mut_aa + seq[idx + 1:]


def _build_kabat_map() -> dict[int, int]:
    """Build Kabat number → 0-based index for VGRW_SR_R2 (120 aa).

    Derived from PDB chain A residue numbering (1-128 with gaps).
    The PDB skips positions: 10, 31, 32, 33, 34, 60, 61, 73.
    """
    pdb_resi_numbers = []
    skip = {10, 31, 32, 33, 34, 60, 61, 73}
    for i in range(1, 129):
        if i not in skip:
            pdb_resi_numbers.append(i)
    assert len(pdb_resi_numbers) == 120, f"Expected 120, got {len(pdb_resi_numbers)}"
    return {kabat: idx for idx, kabat in enumerate(pdb_resi_numbers)}


def score_with_ablang(sequences: dict[str, str]) -> dict[str, float]:
    """Score sequences using AbLang pseudo-log-likelihood.

    Returns dict of {name: mean_residue_logP}.
    """
    try:
        import ablang
    except ImportError:
        print("WARNING: ablang not installed. Using placeholder scores.", file=sys.stderr)
        return {name: 0.0 for name in sequences}

    model = ablang.pretrained("heavy")
    model.freeze()

    scores = {}
    for name, seq in sequences.items():
        try:
            likelihoods = model([seq], mode="likelihood")
            mean_logp = float(likelihoods.mean())
            scores[name] = mean_logp
        except Exception as e:
            print(f"  AbLang error for {name}: {e}", file=sys.stderr)
            scores[name] = float("nan")
    return scores


def run_ablang_scoring():
    print("=" * 60)
    print("L2: AbLang Pseudo-Likelihood Nativeness Scoring")
    print("=" * 60)

    sequences = {"WT": WT_SEQ}
    mutation_info = []

    for entry in MUTATIONS:
        site = entry["site"]
        wt_aa = entry["wt"]
        for mut_aa in entry["candidates"]:
            label = f"{wt_aa}{site}{mut_aa}"
            try:
                mut_seq = _apply_mutation(WT_SEQ, site, mut_aa)
                sequences[label] = mut_seq
                mutation_info.append({"mutation": label, "site": site, "wt_aa": wt_aa, "mut_aa": mut_aa})
            except ValueError as e:
                print(f"  Skipping {label}: {e}")

    print(f"\nScoring {len(sequences)} sequences (1 WT + {len(sequences)-1} mutants)...\n")
    scores = score_with_ablang(sequences)

    wt_score = scores.get("WT", 0.0)
    print(f"  WT AbLang score: {wt_score:.4f}")

    results = []
    for info in mutation_info:
        label = info["mutation"]
        mut_score = scores.get(label, float("nan"))
        delta = mut_score - wt_score
        passed = delta >= DELTA_LOGP_MIN
        status = "PASS" if passed else "fail"
        print(f"  {label:>8s}  score={mut_score:.4f}  Δ={delta:+.4f}  [{status}]")
        results.append({
            **info,
            "ablang_wt": round(wt_score, 4),
            "ablang_mut": round(mut_score, 4),
            "ablang_delta": round(delta, 4),
            "ablang_pass": passed,
        })

    out_csv = OUTPUT_DIR / "ablang_scores.csv"
    fields = ["mutation", "site", "wt_aa", "mut_aa", "ablang_wt", "ablang_mut", "ablang_delta", "ablang_pass"]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    passed_count = sum(1 for r in results if r["ablang_pass"])
    print(f"\n{'=' * 60}")
    print(f"Results: {passed_count}/{len(results)} passed (Δ ≥ {DELTA_LOGP_MIN})")
    print(f"Output:  {out_csv}")
    print(f"{'=' * 60}")
    return results


if __name__ == "__main__":
    run_ablang_scoring()
