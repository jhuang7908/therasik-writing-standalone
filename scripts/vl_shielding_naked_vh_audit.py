"""
VL-Shielding Audit — Original VH (no engineering) vs Fv
========================================================
Strict double-gate to identify true VL-shielded hydrophobic patches:

  Gate 1: residue is hydrophobic (L/V/I/M/A/F/W/Y)
  Gate 2: SASA_Fv < SASA_threshold_buried  (buried by VL)
          AND SASA_VH_naked > SASA_threshold_exposed (exposed without VL)

The comparison uses the SAME amino acid in both contexts (the original VH
sequence) — no V1.8.x mutations — so the SASA change reflects ONLY the
structural effect of removing VL.

Workflow:
  1. Predict each original VH alone as a single-domain (NanoBodyBuilder2)
  2. Reuse VH/VL Fv structures from fv_structures/
  3. Per-residue SASA in both, position-by-position
  4. Apply double gate
"""
from __future__ import annotations
import os, sys, json, subprocess, re
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from pathlib import Path
from typing import Dict, Optional, List

from Bio.PDB import PDBParser
from Bio.PDB.SASA import ShrakeRupley
from Bio.Data.IUPACData import protein_letters_3to1_extended as three2one

ROOT = Path(__file__).resolve().parent.parent
PROJ = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515"
FV_DIR = PROJ / "fv_structures"
NAKED_DIR = PROJ / "naked_vh_structures"
NAKED_DIR.mkdir(exist_ok=True)
OUT_DIR = PROJ / "vl_interface_audit"
OUT_DIR.mkdir(exist_ok=True)

ORIGINAL_VH = {
    "SP34":         "DIKLQSGAELARPGASVKMSCKTSGYTFTRYTMHWVKQRPGQGLEWIGYINPSRGYTNYNQKFKDKATLTTDKSSSTAYMQLSSLTSEDSAVYYCARYYDDHYCLDYWGQGTTLTVSS",
    "Teplizumab":   "QVQLVQSGGGVVQPGRSLRLSCKASGYTFTRYTMHWVRQAPGKGLEWIGYINPSRGYTNYNQKVKDRFTISRDNSKNTAFLQMDSLRPEDTGVYFCARYYDDHYCLDYWGQGTPVTVSS",
    "OKT3":         "QVQLQQSGAELARPGASVKMSCKASGYTFTRYTMHWVKQRPGQGLEWIGYINPSRGYTNYNQKFKDKATLTTDKSSSTAYMQLSSLTSEDSAVYYCARYYDDHYCLDYWGQGTTLTVSS",
    "Visilizumab":  "QVQLVQSGAEVKKPGASVKVSCKASGYTFISYTMHWVRQAPGQGLEWMGYINPRSGYTHYNQKLKDKATLTADKSASTAYMELSSLRSEDTAVYYCARSAYYDYDGFAYWGQGTLVTVSS",
    "Otelixizumab": "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSFPMAWVRQAPGKGLEWVSTISTSGGRTYYRDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKFRQYSGGFDYWGQGTLVTVSS",
    "Foralumab":    "QVQLVESGGGVVQPGRSLRLSCAASGFKFSGYGMHWVRQAPGKGLEWVAVIWYDGSKKYYVDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARQMGYWHFDLWGRGTLVTVSS",
}

HYDROPHOBIC = set("LVIMAFWY")
BURIED_FV_THRESHOLD = 20.0
EXPOSED_NAKED_THRESHOLD = 40.0


# ─── Predict single-domain VHH from VH (no mutation) ─────────────────────────

def predict_naked_vh(name: str, seq: str) -> Optional[Path]:
    out_pdb = NAKED_DIR / f"{name}_nakedVH.pdb"
    if out_pdb.exists():
        return out_pdb
    payload = {
        "name": name, "H": seq, "out_path": str(out_pdb),
    }
    payload_path = out_pdb.with_suffix(".payload.json")
    payload_path.write_text(json.dumps(payload))
    script = ROOT / "scripts" / "_predict_vhh_with_rmsd.py"
    env = os.environ.copy()
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    res = subprocess.run(
        [sys.executable, str(script), "--json", str(payload_path)],
        capture_output=True, text=True, env=env, timeout=600,
    )
    payload_path.unlink(missing_ok=True)
    if not out_pdb.exists():
        print(f"  [predict ERROR] {res.stderr[-400:]}")
        return None
    return out_pdb


# ─── SASA helpers ────────────────────────────────────────────────────────────

def chain_sasa(pdb: Path, chain_id: Optional[str] = None) -> List[Dict]:
    parser = PDBParser(QUIET=True)
    struct = parser.get_structure("s", str(pdb))
    sr = ShrakeRupley()
    sr.compute(struct, level="R")
    residues = []
    for model in struct:
        for chain in model:
            if chain_id and chain.id != chain_id:
                continue
            for r in chain.get_residues():
                if r.id[0] != " ":
                    continue
                aa3 = r.get_resname().strip()
                aa1 = three2one.get(aa3.capitalize(), "X")
                residues.append({"resnum": r.id[1], "aa": aa1, "sasa": round(r.sasa, 2)})
            if chain_id:
                break
        break
    return residues


# ─── Main: per-residue dual-gate scan ────────────────────────────────────────

def main():
    summary = {"samples": {}, "global_table": []}

    for name, vh_seq in ORIGINAL_VH.items():
        print(f"\n{'='*100}\n[{name}]  CDR3 will be flagged in table\n")
        fv_pdb = FV_DIR / f"{name}_fv.pdb"
        if not fv_pdb.exists():
            print(f"  Fv missing: {fv_pdb}"); continue
        naked_pdb = predict_naked_vh(name, vh_seq)
        if not naked_pdb:
            continue

        fv_h = chain_sasa(fv_pdb, "H")
        naked = chain_sasa(naked_pdb)

        fv_seq_h = "".join(r["aa"] for r in fv_h)
        naked_seq = "".join(r["aa"] for r in naked)

        if fv_seq_h != vh_seq:
            print(f"  WARN: Fv H chain seq diff (len={len(fv_seq_h)} vs vh={len(vh_seq)})")
        if naked_seq != vh_seq:
            print(f"  WARN: naked VH seq diff (len={len(naked_seq)} vs vh={len(vh_seq)})")

        cdr3_match = re.search(r"C[ARKQVNG][RAVKQTNYDS]", vh_seq[80:110])
        cdr3_start = (80 + cdr3_match.start() + 2) if cdr3_match else None
        wg_match = re.search(r"WG[QRKE]G", vh_seq[cdr3_start:] if cdr3_start else "")
        cdr3_end = (cdr3_start + wg_match.start() - 1) if (cdr3_start and wg_match) else None

        flagged = []
        for i, aa in enumerate(vh_seq):
            in_cdr3 = (cdr3_start and cdr3_end and cdr3_start <= i <= cdr3_end)
            fv_sasa = fv_h[i]["sasa"] if i < len(fv_h) and fv_h[i]["aa"] == aa else None
            n_sasa = naked[i]["sasa"] if i < len(naked) and naked[i]["aa"] == aa else None
            if fv_sasa is None or n_sasa is None:
                continue
            is_hydro = aa in HYDROPHOBIC
            gate1 = is_hydro
            gate2 = (fv_sasa < BURIED_FV_THRESHOLD) and (n_sasa > EXPOSED_NAKED_THRESHOLD)
            if gate1 and gate2:
                delta = round(n_sasa - fv_sasa, 1)
                flagged.append({
                    "linear_idx": i, "aa": aa, "in_cdr3": bool(in_cdr3),
                    "fv_sasa": fv_sasa, "naked_sasa": n_sasa, "delta_sasa": delta,
                })

        print(f"  CDR3: {vh_seq[cdr3_start:cdr3_end+1] if cdr3_start and cdr3_end else '?'} "
              f"(idx {cdr3_start}..{cdr3_end})")
        print(f"  {'Idx':<5} {'AA':<4} {'in_CDR3':<9} {'SASA_Fv':<10} {'SASA_VH_naked':<15} {'ΔSASA':<10}")
        print("  " + "-" * 65)
        for r in flagged:
            print(f"  {r['linear_idx']:<5} {r['aa']:<4} {str(r['in_cdr3']):<9} "
                  f"{r['fv_sasa']:<10} {r['naked_sasa']:<15} {r['delta_sasa']:+.1f}")

        summary["samples"][name] = {
            "vh_seq": vh_seq, "cdr3_idx": [cdr3_start, cdr3_end],
            "n_flagged_total": len(flagged),
            "n_flagged_framework": sum(1 for f in flagged if not f["in_cdr3"]),
            "flagged_residues": flagged,
        }
        for r in flagged:
            summary["global_table"].append({"sample": name, **r})

    out_json = OUT_DIR / "vl_shielding_naked_vh_audit.json"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{'='*100}\nWritten: {out_json}\n")

    print(f"\n>>> CROSS-SAMPLE: per-position frequency of true VL-shielded hydrophobic residues\n")
    pos_freq = {}
    for r in summary["global_table"]:
        if r["in_cdr3"]:
            continue
        key = r["linear_idx"]
        pos_freq.setdefault(key, []).append((r["sample"], r["aa"], r["delta_sasa"]))
    sorted_keys = sorted(pos_freq.keys(), key=lambda k: -len(pos_freq[k]))
    print(f"  {'Idx':<5} {'#samples':<10} {'AAs':<25} {'ΔSASA range':<15} Samples")
    print("  " + "-" * 90)
    for k in sorted_keys:
        rows = pos_freq[k]
        aas = ",".join(sorted({a for _,a,_ in rows}))
        deltas = [d for _,_,d in rows]
        d_range = f"{min(deltas):.0f}..{max(deltas):.0f}"
        smps = ",".join(s for s,_,_ in rows)
        print(f"  {k:<5} {len(rows):<10} {aas:<25} {d_range:<15} {smps}")


if __name__ == "__main__":
    main()
