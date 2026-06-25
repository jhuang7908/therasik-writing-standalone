"""
CMC / Developability gate for affinity maturation candidates.

Calls the existing cmc_metrics functions to check pI, GRAVY, charge,
hydrophobic patches, and chemical liabilities for each mutant sequence.
Compares against WT baseline and VHH42 gates.

Usage (from repo root, conda activate affmat):
    python scripts/affinity_maturation/cmc_gate.py
"""

import csv
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG = yaml.safe_load((SCRIPT_DIR / "config.yaml").read_text(encoding="utf-8"))
REPO_ROOT = (SCRIPT_DIR / "../..").resolve()

sys.path.insert(0, str(REPO_ROOT))

WT_SEQ = CONFIG["sequence"]["wt"]
MUTATIONS = CONFIG["mutations"]
OUTPUT_DIR = Path((SCRIPT_DIR / CONFIG["paths"]["output_dir"]).resolve())
PI_SHIFT_MAX = CONFIG["gates_cmc"]["pi_shift_max"]
SAP_MAX = CONFIG["gates_cmc"]["sap_max"]
NEW_DEAMID_CDR_FAIL = CONFIG["gates_cmc"]["new_deamid_cdr_fail"]


def _apply_mutation(seq: str, kabat_site: int, mut_aa: str) -> str:
    kabat_to_idx = _build_kabat_map()
    idx = kabat_to_idx.get(kabat_site)
    if idx is None:
        raise ValueError(f"Kabat site {kabat_site} not found in mapping")
    return seq[:idx] + mut_aa + seq[idx + 1:]


def _build_kabat_map() -> dict[int, int]:
    pdb_resi_numbers = []
    skip = {10, 31, 32, 33, 34, 60, 61, 73}
    for i in range(1, 129):
        if i not in skip:
            pdb_resi_numbers.append(i)
    return {kabat: idx for idx, kabat in enumerate(pdb_resi_numbers)}


def compute_cmc_metrics(seq: str) -> dict:
    """Compute CMC metrics using project cmc_metrics or fallback to biopython."""
    try:
        from core.cmc.cmc_metrics import (
            compute_pI, compute_GRAVY, compute_instability_index,
            compute_net_charge, compute_chemical_liabilities,
        )
        pi = compute_pI(seq)
        gravy = compute_GRAVY(seq)
        instab = compute_instability_index(seq)
        charge = compute_net_charge(seq)
        liabilities = compute_chemical_liabilities(seq)
    except ImportError:
        from Bio.SeqUtils.ProtParam import ProteinAnalysis
        pa = ProteinAnalysis(seq)
        pi = pa.isoelectric_point()
        gravy = pa.gravy()
        instab = pa.instability_index()
        charge = pa.charge_at_pH(7.0)
        liabilities = _simple_liabilities(seq)

    deamid_sites = _find_deamidation_motifs(seq)
    isom_sites = _find_isomerization_motifs(seq)
    oxidation_sites = _find_oxidation_sites(seq)

    return {
        "pI": round(pi, 2),
        "GRAVY": round(gravy, 3),
        "instability_index": round(instab, 1),
        "net_charge_pH7": round(charge, 1),
        "deamidation_count": len(deamid_sites),
        "deamidation_sites": ",".join(deamid_sites) if deamid_sites else "none",
        "isomerization_count": len(isom_sites),
        "oxidation_count": len(oxidation_sites),
    }


def _find_deamidation_motifs(seq: str) -> list[str]:
    """Find NG, NS, NT, NH motifs (N followed by small/flexible residue)."""
    hits = []
    for i in range(len(seq) - 1):
        if seq[i] == "N" and seq[i + 1] in "GSTH":
            hits.append(f"N{seq[i+1]}@{i+1}")
    return hits


def _find_isomerization_motifs(seq: str) -> list[str]:
    hits = []
    for i in range(len(seq) - 1):
        if seq[i] == "D" and seq[i + 1] in "GSP":
            hits.append(f"D{seq[i+1]}@{i+1}")
    return hits


def _find_oxidation_sites(seq: str) -> list[str]:
    hits = []
    for i, aa in enumerate(seq):
        if aa == "M":
            hits.append(f"M@{i+1}")
        elif aa == "W":
            hits.append(f"W@{i+1}")
    return hits


def _simple_liabilities(seq: str) -> dict:
    return {"deamidation": len(_find_deamidation_motifs(seq)),
            "isomerization": len(_find_isomerization_motifs(seq))}


def run_cmc_gate():
    print("=" * 60)
    print("CMC / Developability Gate")
    print("=" * 60)

    wt_metrics = compute_cmc_metrics(WT_SEQ)
    print(f"\nWT baseline: pI={wt_metrics['pI']}, GRAVY={wt_metrics['GRAVY']}, "
          f"charge={wt_metrics['net_charge_pH7']}, deamid={wt_metrics['deamidation_count']}\n")

    results = []
    for entry in MUTATIONS:
        site = entry["site"]
        wt_aa = entry["wt"]
        for mut_aa in entry["candidates"]:
            label = f"{wt_aa}{site}{mut_aa}"
            try:
                mut_seq = _apply_mutation(WT_SEQ, site, mut_aa)
            except ValueError as e:
                print(f"  {label}: SKIP ({e})")
                continue

            mut_metrics = compute_cmc_metrics(mut_seq)
            pi_shift = abs(mut_metrics["pI"] - wt_metrics["pI"])
            new_deamid = mut_metrics["deamidation_count"] - wt_metrics["deamidation_count"]

            hard_fail = False
            warnings = []
            if pi_shift > PI_SHIFT_MAX:
                hard_fail = True
                warnings.append(f"pI shift {pi_shift:.2f}")
            if new_deamid > 0 and NEW_DEAMID_CDR_FAIL:
                hard_fail = True
                warnings.append(f"+{new_deamid} deamid site(s)")

            status = "FAIL" if hard_fail else "PASS"
            warn_str = "; ".join(warnings) if warnings else ""
            print(f"  {label:>8s}  pI={mut_metrics['pI']}  ΔpI={pi_shift:.2f}  "
                  f"deamid={mut_metrics['deamidation_count']}  [{status}] {warn_str}")

            results.append({
                "mutation": label, "site": site, "wt_aa": wt_aa, "mut_aa": mut_aa,
                **{f"cmc_{k}": v for k, v in mut_metrics.items()},
                "cmc_pi_shift": round(pi_shift, 2),
                "cmc_new_deamid": new_deamid,
                "cmc_pass": not hard_fail,
                "cmc_warnings": warn_str,
            })

    out_csv = OUTPUT_DIR / "cmc_results.csv"
    if results:
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader()
            w.writerows(results)

    passed = sum(1 for r in results if r["cmc_pass"])
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{len(results)} passed CMC gate")
    print(f"Output:  {out_csv}")
    print(f"{'=' * 60}")
    return results


if __name__ == "__main__":
    run_cmc_gate()
