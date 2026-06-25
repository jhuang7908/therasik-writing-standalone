#!/usr/bin/env python3
"""
Structural analysis of 84 multispecific clinical antibodies (VH-linker-VL, ESMFold PDBs).

Computes:
- Stability: pLDDT (global, VH, linker, VL), min/frac above 70/90, radius of gyration.
- Linker impact: linker pLDDT stats, linker end-to-end distance, linker–VH/VL contacts,
  linker-involved clashes, junction continuity (VH C-term to VL N-term).
- Interface: VH–VL contact count (CA < 8 Å), clash count (CA < 3.5 Å across domains).

Input:
- data/design_rules/multispecific_linker_pipeline/linker_split_results.json (VH/linker/VL lengths)
- data/design_rules/multispecific_linker_pipeline/esmfold_predictions/*.pdb

Output:
- multispecific_84_structure_metrics.csv
- multispecific_84_structure_summary.json
- multispecific_84_structure_report.md (optional)

Usage:
  python scripts/analyze_multispecific_84_esmfold.py
  python scripts/analyze_multispecific_84_esmfold.py --pdb-dir data/design_rules/multispecific_linker_pipeline/esmfold_predictions --out-dir data/design_rules/multispecific_linker_pipeline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from Bio.PDB import PDBParser
except ImportError:
    PDBParser = None

# Default paths
DEFAULT_LINKER_JSON = PROJECT_ROOT / "data/design_rules/multispecific_linker_pipeline/linker_split_results.json"
DEFAULT_PDB_DIR = PROJECT_ROOT / "data/design_rules/multispecific_linker_pipeline/esmfold_predictions"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data/design_rules/multispecific_linker_pipeline"
LINKER_LEN = 15  # (G4S)x3

# Thresholds
CLASH_CA_A = 3.5
CONTACT_CA_A = 8.0
PLDDT_HIGH = 90
PLDDT_OK = 70


def _plddt_from_bfactor(bf: float) -> float:
    """ESMFold may write pLDDT as 0-1 or 0-100 in B-factor; normalize to 0-100."""
    if bf > 2:
        return float(bf)
    return float(bf) * 100.0


def _get_ca_bfactor_arrays(structure, chain_id=None):
    """Return (res_idx_0based, coords, bfactors) for CA atoms only, single chain."""
    model = structure[0]
    chain = chain_id
    if chain is None:
        chain = next(model.get_chains())
    else:
        chain = model[chain]
    coords = []
    bfactors = []
    for res in chain:
        if res.id[0] != " ":
            continue
        if "CA" not in res:
            continue
        coords.append(res["CA"].coord)
        bfactors.append(_plddt_from_bfactor(res["CA"].bfactor))
    return np.array(coords) if coords else np.zeros((0, 3)), np.array(bfactors) if bfactors else np.zeros(0)


def _count_pairs_within(coords_a, coords_b, threshold_a):
    """Count pairs (i in A, j in B) with dist < threshold_a."""
    if len(coords_a) == 0 or len(coords_b) == 0:
        return 0
    count = 0
    for ca in coords_a:
        for cb in coords_b:
            if np.linalg.norm(ca - cb) < threshold_a:
                count += 1
    return count


def _count_clashes(coords_a, coords_b, threshold_a=CLASH_CA_A):
    """Count CA pairs between two sets with distance < threshold (clash)."""
    return _count_pairs_within(coords_a, coords_b, threshold_a)


def _radius_of_gyration(coords):
    """Radius of gyration of CA cloud."""
    if len(coords) == 0:
        return float("nan")
    centroid = np.mean(coords, axis=0)
    return float(np.sqrt(np.mean(np.sum((coords - centroid) ** 2, axis=1))))


def _end_to_end(coords):
    """Distance between first and last CA."""
    if len(coords) < 2:
        return 0.0
    return float(np.linalg.norm(coords[-1] - coords[0]))


def load_linker_map(linker_json: Path):
    """Return dict: antibody_id -> { vh_len, linker_len, vl_len, full_len } for status split_ok."""
    with open(linker_json, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for r in data.get("results", []):
        if r.get("status") != "split_ok":
            continue
        aid = r["antibody_id"]
        vh = int(r["len_before"])
        vl = int(r["len_after"])
        full = int(r["full_len"])
        linker_len = full - vh - vl
        out[aid] = {"vh_len": vh, "linker_len": linker_len, "vl_len": vl, "full_len": full}
    return out


def analyze_one_pdb(pdb_path: Path, vh_len: int, linker_len: int, vl_len: int) -> dict | None:
    """Compute structure metrics for one VH-linker-VL PDB. Uses single chain, 0-based residue indexing."""
    if PDBParser is None:
        raise ImportError("Biopython required: pip install biopython")
    parser = PDBParser(QUIET=True)
    try:
        structure = parser.get_structure("pred", pdb_path)
    except Exception:
        return None
    coords, bfactors = _get_ca_bfactor_arrays(structure)
    n_res = len(bfactors)
    expected = vh_len + linker_len + vl_len
    if n_res < expected:
        # Allow small truncation
        if n_res < vh_len + vl_len:
            return None
        # Adjust: assume linker might be shorter in model
        linker_len_actual = min(linker_len, n_res - vh_len - vl_len)
    else:
        linker_len_actual = linker_len

    i0_vh, i1_vh = 0, vh_len
    i0_linker, i1_linker = vh_len, vh_len + linker_len_actual
    i0_vl, i1_vl = vh_len + linker_len_actual, min(vh_len + linker_len_actual + vl_len, n_res)

    coords_vh = coords[i0_vh:i1_vh]
    coords_linker = coords[i0_linker:i1_linker]
    coords_vl = coords[i0_vl:i1_vl]
    bf_vh = bfactors[i0_vh:i1_vh]
    bf_linker = bfactors[i0_linker:i1_linker]
    bf_vl = bfactors[i0_vl:i1_vl]

    # pLDDT stats
    def _plddt_stats(bf):
        if len(bf) == 0:
            return {"mean": float("nan"), "min": float("nan"), "std": float("nan"), "frac_ge70": float("nan"), "frac_ge90": float("nan")}
        return {
            "mean": float(np.mean(bf)),
            "min": float(np.min(bf)),
            "std": float(np.std(bf)) if len(bf) > 1 else 0.0,
            "frac_ge70": float(np.mean(bf >= PLDDT_OK)),
            "frac_ge90": float(np.mean(bf >= PLDDT_HIGH)),
        }

    all_bf = bfactors[:n_res]
    plddt_global = _plddt_stats(all_bf)
    plddt_vh = _plddt_stats(bf_vh)
    plddt_linker = _plddt_stats(bf_linker)
    plddt_vl = _plddt_stats(bf_vl)

    # Clashes: VH-linker, linker-VL, VH-VL (excluding same-segment adjacent)
    clash_vh_linker = _count_clashes(coords_vh, coords_linker)
    clash_linker_vl = _count_clashes(coords_linker, coords_vl)
    clash_vh_vl = _count_clashes(coords_vh, coords_vl)
    clash_total = clash_vh_linker + clash_linker_vl + clash_vh_vl

    # Contacts (CA < 8 Å)
    contact_vh_vl = _count_pairs_within(coords_vh, coords_vl, CONTACT_CA_A)
    contact_vh_linker = _count_pairs_within(coords_vh, coords_linker, CONTACT_CA_A)
    contact_linker_vl = _count_pairs_within(coords_linker, coords_vl, CONTACT_CA_A)

    # Linker geometry
    linker_e2e = _end_to_end(coords_linker) if len(coords_linker) >= 2 else float("nan")
    # Junction: distance from VH C-term (last CA of VH) to VL N-term (first CA of VL)
    if len(coords_vh) and len(coords_vl):
        junction_vh_vl_a = float(np.linalg.norm(coords_vh[-1] - coords_vl[0]))
    else:
        junction_vh_vl_a = float("nan")

    # Radius of gyration
    rg_full = _radius_of_gyration(coords[:n_res])
    rg_vh = _radius_of_gyration(coords_vh)
    rg_linker = _radius_of_gyration(coords_linker)
    rg_vl = _radius_of_gyration(coords_vl)

    return {
        "mean_plddt": plddt_global["mean"],
        "min_plddt": plddt_global["min"],
        "frac_plddt_ge70": plddt_global["frac_ge70"],
        "frac_plddt_ge90": plddt_global["frac_ge90"],
        "mean_plddt_vh": plddt_vh["mean"],
        "min_plddt_vh": plddt_vh["min"],
        "mean_plddt_linker": plddt_linker["mean"],
        "min_plddt_linker": plddt_linker["min"],
        "std_plddt_linker": plddt_linker["std"],
        "frac_plddt_linker_ge70": plddt_linker["frac_ge70"],
        "mean_plddt_vl": plddt_vl["mean"],
        "min_plddt_vl": plddt_vl["min"],
        "clash_total": clash_total,
        "clash_vh_linker": clash_vh_linker,
        "clash_linker_vl": clash_linker_vl,
        "clash_vh_vl": clash_vh_vl,
        "contact_vh_vl": contact_vh_vl,
        "contact_vh_linker": contact_vh_linker,
        "contact_linker_vl": contact_linker_vl,
        "linker_end_to_end_a": linker_e2e,
        "junction_vh_vl_a": junction_vh_vl_a,
        "rg_full": rg_full,
        "rg_vh": rg_vh,
        "rg_linker": rg_linker,
        "rg_vl": rg_vl,
        "n_residues": n_res,
        "vh_len": vh_len,
        "linker_len": linker_len_actual,
        "vl_len": vl_len,
    }


def main():
    ap = argparse.ArgumentParser(description="Structure analysis for 84 multispecific VH-linker-VL ESMFold PDBs")
    ap.add_argument("--linker-json", type=Path, default=DEFAULT_LINKER_JSON, help="linker_split_results.json")
    ap.add_argument("--pdb-dir", type=Path, default=DEFAULT_PDB_DIR, help="Directory of ESMFold PDBs")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Output directory for CSV/JSON/report")
    ap.add_argument("--report", action="store_true", default=True, help="Write markdown summary report")
    ap.add_argument("--limit", type=int, default=None, help="Max number of PDBs to process (for testing)")
    args = ap.parse_args()

    linker_json = args.linker_json
    pdb_dir = args.pdb_dir
    out_dir = args.out_dir
    if not linker_json.is_file():
        raise FileNotFoundError(f"Linker JSON not found: {linker_json}")
    if not pdb_dir.is_dir():
        raise FileNotFoundError(f"PDB dir not found: {pdb_dir}")

    linker_map = load_linker_map(linker_json)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for aid, seg in linker_map.items():
        if args.limit is not None and len(results) >= args.limit:
            break
        pdb_path = pdb_dir / f"{aid}.pdb"
        if not pdb_path.is_file():
            continue
        rec = analyze_one_pdb(pdb_path, seg["vh_len"], seg["linker_len"], seg["vl_len"])
        if rec is None:
            continue
        rec["antibody_id"] = aid
        results.append(rec)

    if not results:
        print("No structures analyzed. Check PDB dir and linker JSON.")
        return

    # CSV
    import csv
    keys = ["antibody_id", "mean_plddt", "min_plddt", "frac_plddt_ge70", "frac_plddt_ge90",
            "mean_plddt_vh", "mean_plddt_linker", "min_plddt_linker", "std_plddt_linker", "frac_plddt_linker_ge70",
            "mean_plddt_vl", "clash_total", "clash_vh_linker", "clash_linker_vl", "clash_vh_vl",
            "contact_vh_vl", "contact_vh_linker", "contact_linker_vl",
            "linker_end_to_end_a", "junction_vh_vl_a",
            "rg_full", "rg_vh", "rg_linker", "rg_vl",
            "n_residues", "vh_len", "linker_len", "vl_len"]
    csv_path = out_dir / "multispecific_84_structure_metrics.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
    print(f"Wrote {len(results)} rows to {csv_path}")

    # JSON
    json_path = out_dir / "multispecific_84_structure_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"n_analyzed": len(results), "metrics": results}, f, indent=2)
    print(f"Wrote {json_path}")

    # Markdown report
    if args.report:
        report_path = out_dir / "multispecific_84_structure_report.md"
        _write_report(results, report_path)
        print(f"Wrote {report_path}")

    return 0


def _write_report(results: list, path: Path) -> None:
    """Write a short summary report (stability, linker impact, outliers)."""
    n = len(results)
    if n == 0:
        path.write_text("# Multispecific 84 structure analysis\n\nNo data.\n", encoding="utf-8")
        return

    mean_plddt = [r["mean_plddt"] for r in results if not np.isnan(r["mean_plddt"])]
    linker_plddt = [r["mean_plddt_linker"] for r in results if not np.isnan(r["mean_plddt_linker"])]
    clash = [r["clash_total"] for r in results]
    contact = [r["contact_vh_vl"] for r in results]

    lines = [
        "# Structural analysis: 84 multispecific clinical antibodies (VH–linker–VL)",
        "",
        "## 1. Structural stability",
        "",
        f"- **Mean pLDDT (global)** — mean: {np.mean(mean_plddt):.1f}, min: {np.min(mean_plddt):.1f}, max: {np.max(mean_plddt):.1f}",
        f"- **Linker pLDDT** — mean: {np.mean(linker_plddt):.1f}, min: {np.min(linker_plddt):.1f}",
        f"- **Fraction of residues with pLDDT ≥ 70** — median: {np.median([r['frac_plddt_ge70'] for r in results]):.2f}",
        "",
        "## 2. Linker impact",
        "",
        f"- **Linker end-to-end distance (Å)** — mean: {np.nanmean([r['linker_end_to_end_a'] for r in results]):.1f}",
        f"- **VH C-term ↔ VL N-term (junction, Å)** — mean: {np.nanmean([r['junction_vh_vl_a'] for r in results]):.1f}",
        f"- **Clashes involving linker (VH–linker + linker–VL)** — total across structures: {sum(r['clash_vh_linker'] + r['clash_linker_vl'] for r in results)}",
        f"- **VH–linker contacts (CA < 8 Å)** — median per structure: {np.median([r['contact_vh_linker'] for r in results]):.0f}",
        f"- **Linker–VL contacts** — median per structure: {np.median([r['contact_linker_vl'] for r in results]):.0f}",
        "",
        "## 3. VH–VL interface",
        "",
        f"- **VH–VL contacts (CA < 8 Å)** — mean: {np.mean(contact):.0f}, median: {np.median(contact):.0f}",
        f"- **VH–VL clashes (CA < 3.5 Å)** — total: {sum(r['clash_vh_vl'] for r in results)}",
        "",
        "## 4. Radius of gyration (Å)",
        "",
        f"- **Full chain** — mean: {np.nanmean([r['rg_full'] for r in results]):.1f}",
        f"- **VH** — mean: {np.nanmean([r['rg_vh'] for r in results]):.1f}",
        f"- **Linker** — mean: {np.nanmean([r['rg_linker'] for r in results]):.1f}",
        f"- **VL** — mean: {np.nanmean([r['rg_vl'] for r in results]):.1f}",
        "",
        "## 5. Outliers (low stability or high clash)",
        "",
    ]

    # Outliers: low mean_plddt or high clash
    sorted_by_plddt = sorted(results, key=lambda r: r["mean_plddt"])
    low_plddt = [r["antibody_id"] for r in sorted_by_plddt[:5]]
    high_clash = sorted(results, key=lambda r: r["clash_total"], reverse=True)[:5]
    lines.append("- **Lowest mean pLDDT (top 5):** " + ", ".join(low_plddt))
    lines.append("- **Highest clash count (top 5):** " + ", ".join(f"{r['antibody_id']}({r['clash_total']})" for r in high_clash))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("Metrics computed by `scripts/analyze_multispecific_84_esmfold.py`.")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main() or 0)
