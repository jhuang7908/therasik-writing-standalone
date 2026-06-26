"""
V1.8.16 Structure-Based SASA QC
================================
Replaces the CDR3-length heuristic safety gate (V1.8.15-B) with structure-based
SASA measurement of VL-interface Zone 1 residues.

Pipeline per sample:
  1. Load V1.8.15 JSON → get final_seq + hallmark_positions
  2. Predict VHH structure with NanoBodyBuilder2 (ImmuneBuilder)
  3. Calculate per-residue SASA using BioPython ShrakeRupley
  4. Measure SASA for k45, k47, k37 (Zone 1 VL-interface residues)
  5. Apply V1.8.16 SASA gate:
       IF k45 is hydrophobic (L/V/I/M/A/F) AND k45 SASA > K45_SASA_THRESHOLD
       → apply Hallmark (L45R + G44E + W47G) to sequence
       → re-predict structure + re-measure SASA to confirm closure
  6. Output {name}_v1816_sasa.json with full SASA metrics and gate decisions

Physical basis (Standard V1.8.15 §1a):
  k45(L)/k47(W) are buried (BSA) in VH+VL; after VL loss they become surface-exposed
  (SASA) and form an aggregation-prone hydrophobic patch.
  SASA > threshold = the patch is open; must close via Hallmark.
"""
from __future__ import annotations
import os, sys, json, re, subprocess, tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from Bio.PDB import PDBParser
from Bio.PDB.SASA import ShrakeRupley
from Bio.SeqUtils.ProtParam import ProteinAnalysis

# ─── SASA thresholds (Å²) ────────────────────────────────────────────────────
# Based on max SASA of residue types × exposure fraction:
#   Leu max ~170 Å², threshold 30% exposure = 50 Å²
#   Trp max ~280 Å², threshold 25% exposure = 70 Å²  
#   Val max ~155 Å², threshold 30% exposure = 45 Å²
# Initial thresholds — calibrated from CD3 panel n=6 in V1.8.16 run.
K45_SASA_THRESHOLD = 50.0   # Å² — L45 exposure trigger
K47_SASA_THRESHOLD = 70.0   # Å² — W47 exposure (informational; gate uses k45)
K37_SASA_THRESHOLD = 45.0   # Å² — V37 exposure (informational)

# Hydrophobic residues that trigger the gate when found at k45
K45_HYDROPHOBIC = set("LVIMAFYW")

PREDICT_SCRIPT = ROOT / "scripts" / "_predict_vhh_with_rmsd.py"
V1815_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "v1815_reports"
OUT_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "v1816_sasa_reports"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def apply_hallmark(seq: str, hallmark_pos: Dict[str, int]) -> Tuple[str, List[Dict]]:
    """Apply L45R + G44E + W47G to sequence (only when orig != target)."""
    arr = list(seq)
    muts = []
    for label, target in [("K45", "R"), ("K44", "E"), ("K47", "G")]:
        idx = hallmark_pos.get(label)
        if idx is None or idx >= len(seq):
            continue
        orig = arr[idx]
        if orig == target or (label == "K45" and orig in ("R", "A")):
            continue
        arr[idx] = target
        muts.append({"label": label, "idx": idx, "orig": orig, "target": target})
    return "".join(arr), muts


def predict_structure(seq: str, out_pdb: Path) -> bool:
    """Run NanoBodyBuilder2 via _predict_vhh_with_rmsd.py. Returns True on success."""
    if out_pdb.exists():
        print(f"    [cache] {out_pdb.name} already exists, skipping prediction")
        return True
    payload = {"H": seq, "out_path": str(out_pdb)}
    payload_path = out_pdb.with_suffix(".payload.json")
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    env = os.environ.copy()
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    result = subprocess.run(
        [sys.executable, str(PREDICT_SCRIPT), "--json", str(payload_path)],
        capture_output=True, text=True, env=env
    )
    payload_path.unlink(missing_ok=True)
    if result.returncode != 0:
        print(f"    [NanoBodyBuilder2 WARN] {result.stderr[:300]}")
        return False
    return out_pdb.exists()


def compute_sasa_from_pdb(pdb_path: Path) -> Optional[List[Dict]]:
    """Compute per-residue SASA from a PDB using BioPython ShrakeRupley.
    Returns list of {resnum, aa, sasa} ordered by chain/resnum.
    """
    from Bio.Data.IUPACData import protein_letters_3to1_extended as three2one
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("vhh", str(pdb_path))
    sr = ShrakeRupley()
    sr.compute(structure, level="R")
    residues = []
    for model in structure:
        for chain in model:
            for res in chain.get_residues():
                if res.id[0] != " ":   # skip HETATM / water
                    continue
                aa3 = res.get_resname().strip()
                aa1 = three2one.get(aa3.capitalize(), "X")
                residues.append({
                    "resnum": res.id[1],
                    "aa": aa1,
                    "sasa": round(res.sasa, 2),
                })
    return residues


def get_zone1_sasa(sasa_list: List[Dict], seq: str, hallmark_pos: Dict[str, int]) -> Dict:
    """Extract SASA values for k45, k47, k44, k37 using their linear indices."""
    out = {}
    for label in ("K45", "K47", "K44", "K37"):
        idx = hallmark_pos.get(label)
        if idx is None or idx >= len(seq):
            out[label] = {"idx": None, "aa": None, "sasa": None}
            continue
        expected_aa = seq[idx]
        # sasa_list is ordered by residue; index = idx (0-based linear = resnum-1 usually)
        # Verify by amino acid match; fall back to scan if mismatch
        if idx < len(sasa_list) and sasa_list[idx]["aa"] == expected_aa:
            out[label] = {"idx": idx, "aa": expected_aa, "sasa": sasa_list[idx]["sasa"]}
        else:
            # Scan for first residue with matching AA near expected position
            found = None
            for j in range(max(0, idx - 3), min(len(sasa_list), idx + 4)):
                if sasa_list[j]["aa"] == expected_aa:
                    found = sasa_list[j]
                    break
            out[label] = {"idx": idx, "aa": expected_aa,
                           "sasa": found["sasa"] if found else None,
                           "note": "scan match" if found else "not found"}
    return out


def sasa_gate_triggered(zone1: Dict) -> bool:
    """V1.8.16 gate: k45 is hydrophobic AND SASA > threshold."""
    k45 = zone1.get("K45", {})
    aa = k45.get("aa")
    sasa = k45.get("sasa")
    if aa is None or sasa is None:
        return False
    return (aa in K45_HYDROPHOBIC) and (sasa > K45_SASA_THRESHOLD)


def compute_metrics(seq: str) -> Dict:
    pa = ProteinAnalysis(seq)
    return {"pI": round(pa.isoelectric_point(), 2),
            "GRAVY": round(pa.gravy(), 3),
            "length": len(seq)}


# ─── V1.8.16 hallmark_pos includes K37 ───────────────────────────────────────

def find_k37(seq: str) -> Optional[int]:
    """K37 is at FR2 start, typically ~3-4 residues before the WVKQ motif."""
    m = re.search(r'[WY][VIA][KR][QK]', seq[30:50])
    if m:
        return 30 + m.start() - 4   # V37 is 4 before the WVK anchor
    return None


# ─── Main per-sample logic ────────────────────────────────────────────────────

def process_sample(name: str, v1815_json: Path, out_dir: Path) -> Dict:
    r = json.loads(v1815_json.read_text(encoding="utf-8"))
    final_seq = r["final_seq"]
    input_seq = r["input_seq"]
    hallmark_pos = r.get("hallmark_positions", {})

    # Add k37 if not present (computed from original sequence)
    if "K37" not in hallmark_pos:
        k37 = find_k37(input_seq)
        if k37 is not None:
            hallmark_pos["K37"] = k37

    log = {
        "sample": name,
        "algorithm_version": "V1.8.16",
        "v1815_final_seq": final_seq,
        "hallmark_positions": hallmark_pos,
        "v1815_verdict": r.get("final_verdict"),
        "cdr3_len": r.get("cdr3_len"),
        "ighv_family": r.get("ighv_family"),
        "passes": []
    }

    def run_pass(seq: str, pass_label: str) -> Dict:
        """Predict structure, measure SASA, apply gate."""
        pdb_path = out_dir / f"{name}_{pass_label}.pdb"
        print(f"    [{pass_label}] Predicting structure for {name}...")

        sasa_data = None
        zone1 = {}
        prediction_ok = False

        if not predict_structure(seq, pdb_path):
            print(f"    [{pass_label}] NanoBodyBuilder2 FAILED — using sequence-only fallback")
        else:
            sasa_data = compute_sasa_from_pdb(pdb_path)
            if sasa_data:
                zone1 = get_zone1_sasa(sasa_data, seq, hallmark_pos)
                prediction_ok = True

        gate = sasa_gate_triggered(zone1) if prediction_ok else None
        metrics = compute_metrics(seq)

        pass_result = {
            "pass": pass_label,
            "sequence": seq,
            "metrics": metrics,
            "zone1_sasa": zone1,
            "k45_threshold_A2": K45_SASA_THRESHOLD,
            "sasa_gate_triggered": gate,
            "prediction_ok": prediction_ok,
        }

        if gate:
            corrected_seq, hallmark_muts = apply_hallmark(seq, hallmark_pos)
            muts_str = [m["orig"] + m["label"] + m["target"] for m in hallmark_muts]
            pass_result["sasa_gate_action"] = (
                f"k45={zone1['K45']['aa']} SASA={zone1['K45']['sasa']:.1f} A2 > {K45_SASA_THRESHOLD} A2 "
                f"-> applying Hallmark: {muts_str}"
            )
            pass_result["hallmark_corrections"] = hallmark_muts
            pass_result["corrected_seq"] = corrected_seq
            print(f"    [{pass_label}] SASA GATE TRIGGERED: {pass_result['sasa_gate_action']}")
        elif gate is False:
            pass_result["sasa_gate_action"] = (
                f"k45={zone1.get('K45',{}).get('aa','?')} SASA={zone1.get('K45',{}).get('sasa','?')} Å² "
                f"≤ {K45_SASA_THRESHOLD} Å² → Zone 1 closed, no correction needed"
            )
        else:
            pass_result["sasa_gate_action"] = "Structure prediction unavailable — gate not evaluated"

        return pass_result

    # Pass 1: V1.8.15 final sequence
    p1 = run_pass(final_seq, "pass1_v1815")
    log["passes"].append(p1)

    # If gate triggered in Pass 1 → run Pass 2 on corrected sequence
    if p1.get("sasa_gate_triggered"):
        corrected_seq = p1["corrected_seq"]
        p2 = run_pass(corrected_seq, "pass2_corrected")
        log["passes"].append(p2)
        log["v1816_final_seq"] = corrected_seq
        log["v1816_action"] = "Hallmark added by SASA gate"
        log["v1816_metrics"] = p2["metrics"]
        log["v1816_zone1_sasa"] = p2["zone1_sasa"]
    else:
        log["v1816_final_seq"] = final_seq
        log["v1816_action"] = "No SASA correction needed"
        log["v1816_metrics"] = p1["metrics"]
        log["v1816_zone1_sasa"] = p1["zone1_sasa"]

    # Summary verdict
    gate_status = p1.get("sasa_gate_triggered")
    if gate_status is None:
        log["v1816_gate_verdict"] = "UNKNOWN (prediction failed)"
    elif gate_status:
        # Check if Pass 2 closed the gate
        p2_gate = log["passes"][1].get("sasa_gate_triggered") if len(log["passes"]) > 1 else None
        log["v1816_gate_verdict"] = "CORRECTED" if (p2_gate is False) else "CORRECTED_UNVERIFIED"
    else:
        log["v1816_gate_verdict"] = "PASS (Zone 1 closed)"

    return log


# ─── Main ────────────────────────────────────────────────────────────────────

SAMPLE_NAMES = ["SP34", "Teplizumab", "OKT3", "Visilizumab", "Otelixizumab", "Foralumab"]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = []

    for name in SAMPLE_NAMES:
        j = V1815_DIR / f"{name}_v1815.json"
        if not j.exists():
            print(f"[SKIP] {name}: V1.8.15 JSON not found at {j}")
            continue

        print(f"\n[{name}] Running V1.8.16 SASA QC...")
        log = process_sample(name, j, OUT_DIR)
        (OUT_DIR / f"{name}_v1816_sasa.json").write_text(
            json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")

        # Extract k45/k47 SASA for display
        z1 = log.get("v1816_zone1_sasa", {})
        k45 = z1.get("K45", {})
        k47 = z1.get("K47", {})
        print(f"  Gate: {log['v1816_gate_verdict']}  Action: {log['v1816_action']}")
        print(f"  k45={k45.get('aa','?')} SASA={k45.get('sasa','?')} Å² | "
              f"k47={k47.get('aa','?')} SASA={k47.get('sasa','?')} Å²")

        summary.append({
            "name": name,
            "family": log["ighv_family"],
            "cdr3_len": log["cdr3_len"],
            "k45_aa": k45.get("aa"),
            "k45_sasa": k45.get("sasa"),
            "k47_aa": k47.get("aa"),
            "k47_sasa": k47.get("sasa"),
            "gate": log["v1816_gate_verdict"],
            "action": log["v1816_action"],
        })

    (OUT_DIR / "summary_v1816.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*110}")
    print(f"{'Sample':<14} {'Family':<7} {'CDR3':<5} {'k45 aa':<8} {'k45 SASA Å²':<13} "
          f"{'k47 aa':<8} {'k47 SASA Å²':<13} Gate / Action")
    print("=" * 110)
    for s in summary:
        k45s = f"{s['k45_sasa']:.1f}" if s['k45_sasa'] is not None else "N/A"
        k47s = f"{s['k47_sasa']:.1f}" if s['k47_sasa'] is not None else "N/A"
        print(f"{s['name']:<14} {s['family']:<7} {s['cdr3_len']:<5} {str(s['k45_aa']):<8} "
              f"{k45s:<13} {str(s['k47_aa']):<8} {k47s:<13} {s['gate']}")


if __name__ == "__main__":
    main()
