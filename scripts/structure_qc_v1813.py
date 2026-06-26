"""
Path B: NanoBodyBuilder2 structure QC on 6 V1.8.13 engineered VHH sequences.

For each engineered sequence:
  - Predict VHH structure with NanoBodyBuilder2
  - Save .pdb file
  - Extract per-residue B-factor (pLDDT proxy used by ImmuneBuilder)
  - Compute mean pLDDT, FR vs CDR pLDDT
  - Flag residues with B-factor < threshold
"""
from __future__ import annotations
import os
import sys
import site
import json
import re
import subprocess
from pathlib import Path

# Ensure ImmuneBuilder can find anarci_compat
ROOT = Path(__file__).resolve().parent.parent
_anarci_compat = ROOT / "reports" / "anarci_compat"
if _anarci_compat.exists():
    sys.path.insert(0, str(_anarci_compat))
sys.path.append(str(ROOT))

V1813_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "v1813_reports"
OUT_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "v1813_structures"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def find_cdr_ranges(seq: str):
    """Approximate Kabat CDR boundaries via sequence pattern matching."""
    # CDR1: after C in FR1 to W in FR2 (between Kabat ~26-35)
    m1 = re.search(r'C[A-Z]{0,5}([A-Z]{5,12})W', seq[:40])
    if m1:
        cdr1_start = m1.start(1)
        cdr1_end = m1.end(1)
    else:
        cdr1_start, cdr1_end = 25, 34
    # CDR3: between C[AS][KR] and WG.G
    m3s = re.search(r'C[AS][KR]', seq[80:120])
    if m3s:
        cdr3_start = 80 + m3s.start() + 3
        m3e = re.search(r'WG.G', seq[cdr3_start:])
        if m3e:
            cdr3_end = cdr3_start + m3e.start()
        else:
            cdr3_end = cdr3_start + 12
    else:
        cdr3_start, cdr3_end = 95, 110
    # CDR2: rough — between FR2 end (after W) and FR3 start
    m_fr2 = re.search(r'W[VI][RGS]Q', seq[30:55])
    if m_fr2:
        cdr2_start = 30 + m_fr2.end() + 8
    else:
        cdr2_start = 49
    cdr2_end = cdr2_start + 16
    return [(cdr1_start, cdr1_end, "CDR1"), (cdr2_start, cdr2_end, "CDR2"), (cdr3_start, cdr3_end, "CDR3")]


def parse_pdb_bfactors(pdb_path: Path):
    """Return [{'resnum': int, 'resname': str, 'mean_b': float}, ...]"""
    residues = {}
    with pdb_path.open() as f:
        for line in f:
            if not line.startswith("ATOM"):
                continue
            try:
                resnum = int(line[22:26])
                resname = line[17:20].strip()
                b = float(line[60:66])
            except ValueError:
                continue
            residues.setdefault(resnum, {"resname": resname, "bs": []})["bs"].append(b)
    out = []
    for resnum in sorted(residues.keys()):
        r = residues[resnum]
        out.append({"resnum": resnum, "resname": r["resname"], "mean_b": sum(r["bs"])/len(r["bs"])})
    return out


def run_nanobodybuilder(seq: str, out_pdb: Path) -> bool:
    """Spawn predict_one_immunebuilder.py as subprocess in anarcii env."""
    payload = {"H": seq, "L": "", "out_path": str(out_pdb), "model_type": "nanobody"}
    payload_path = out_pdb.parent / f"_payload_{out_pdb.stem}.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    cmd = ["conda", "run", "-n", "anarcii", "python",
           str(ROOT / "scripts" / "_predict_vhh_with_rmsd.py"),
           "--json", str(payload_path)]
    env = os.environ.copy()
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    print(f"  → Running NanoBodyBuilder2 for {out_pdb.stem}...")
    try:
        result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                                timeout=900, env=env)
        if result.returncode != 0:
            print(f"    FAILED: {result.stderr[-500:]}")
            return False
        return out_pdb.exists()
    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT after 15 min")
        return False
    finally:
        try: payload_path.unlink()
        except: pass


def main():
    samples = ["SP34", "Teplizumab", "OKT3", "Visilizumab", "Otelixizumab", "Foralumab"]
    qc_summary = []
    for name in samples:
        json_path = V1813_DIR / f"{name}_v1813.json"
        if not json_path.exists():
            print(f"[SKIP] {name}: JSON not found")
            continue
        d = json.loads(json_path.read_text(encoding="utf-8"))
        eng_seq = d.get("final_seq", d["input_seq"])
        orig_seq = d["input_seq"]
        out_pdb = OUT_DIR / f"{name}_v1813_engineered.pdb"

        if not out_pdb.exists():
            ok = run_nanobodybuilder(eng_seq, out_pdb)
            if not ok:
                print(f"[FAIL] {name}: prediction failed")
                qc_summary.append({"name": name, "status": "FAIL_PREDICT"})
                continue
        else:
            print(f"[CACHED] {name}: structure exists, skipping prediction")

        # Parse pdb
        residues = parse_pdb_bfactors(out_pdb)
        if not residues:
            print(f"[FAIL] {name}: PDB empty")
            continue

        # ImmuneBuilder writes ensemble RMSD (Å) as B-factor: LOWER = more confident
        mean_rmsd = sum(r["mean_b"] for r in residues) / len(residues)
        cdr_ranges = find_cdr_ranges(eng_seq)
        cdr_rmsd = {}
        fr_residues = list(residues)
        for cs, ce, name_cdr in cdr_ranges:
            inside = [r for r in residues if cs < r["resnum"] <= ce + 5]
            if inside:
                cdr_rmsd[name_cdr] = sum(r["mean_b"] for r in inside) / len(inside)
            fr_residues = [r for r in fr_residues if not (cs < r["resnum"] <= ce + 5)]
        fr_mean = sum(r["mean_b"] for r in fr_residues) / len(fr_residues) if fr_residues else mean_rmsd
        # high RMSD residues (low confidence): > 1.0 Å warns, > 1.5 Å flags
        warn_residues = [r for r in residues if r["mean_b"] > 1.0]
        flag_residues = [r for r in residues if r["mean_b"] > 1.5]

        qc = {
            "name": name,
            "ighv": d["ighv_family"],
            "engineered_seq_len": len(eng_seq),
            "predicted_pdb": str(out_pdb.relative_to(ROOT)),
            "n_residues": len(residues),
            "metric_type": "ensemble_rmsd_A_lower_is_better",
            "mean_rmsd_A": round(mean_rmsd, 4),
            "FR_mean_rmsd_A": round(fr_mean, 4),
            "CDR_rmsd_A": {k: round(v, 4) for k, v in cdr_rmsd.items()},
            "n_warn_residues_rmsd_gt_1": len(warn_residues),
            "n_flag_residues_rmsd_gt_1p5": len(flag_residues),
            "flag_residues": [
                {"resnum": r["resnum"], "resname": r["resname"], "rmsd_A": round(r["mean_b"], 4)}
                for r in flag_residues
            ],
            "structure_verdict": (
                "EXCELLENT" if mean_rmsd <= 0.4 else
                "GOOD" if mean_rmsd <= 0.7 else
                "ACCEPTABLE" if mean_rmsd <= 1.2 else
                "POOR"
            ),
        }
        qc_summary.append(qc)
        cdr3_str = f"{cdr_rmsd.get('CDR3', float('nan')):.3f}"
        print(f"  [{name}] mean RMSD = {mean_rmsd:.3f} Å ({qc['structure_verdict']})  "
              f"FR = {fr_mean:.3f}  CDR3 = {cdr3_str}  "
              f"flag(>1.5Å) = {len(flag_residues)} residues")

    out_path = OUT_DIR / "structure_qc_summary.json"
    out_path.write_text(json.dumps(qc_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved → {out_path}")

    # Print summary
    print("\n" + "=" * 120)
    print(f"{'Sample':<14} {'IGHV':<5} {'mean_RMSD_A':>12} {'FR':>7} {'CDR1':>7} {'CDR2':>7} {'CDR3':>7} {'flag_>1.5A':>11} {'Verdict':<12}")
    print("=" * 120)
    for q in qc_summary:
        if q.get("status") == "FAIL_PREDICT":
            continue
        cdr1 = q["CDR_rmsd_A"].get("CDR1", float('nan'))
        cdr2 = q["CDR_rmsd_A"].get("CDR2", float('nan'))
        cdr3 = q["CDR_rmsd_A"].get("CDR3", float('nan'))
        print(f"{q['name']:<14} {q['ighv']:<5} {q['mean_rmsd_A']:>12.4f} "
              f"{q['FR_mean_rmsd_A']:>7.3f} {cdr1:>7.3f} {cdr2:>7.3f} {cdr3:>7.3f} "
              f"{q['n_flag_residues_rmsd_gt_1p5']:>11} {q['structure_verdict']:<12}")


if __name__ == "__main__":
    main()
