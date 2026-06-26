"""
VL-Interface Hydrophobic Patch — Full SASA Audit (6 CD3 antibodies)
====================================================================
Question answered: Beyond k45/k47, which other VH residues are MASKED by VL
(low SASA in Fv) and become EXPOSED when VL is removed (high SASA in VHH)?

Three structural contexts compared:
  (A) Fv (VH+VL) ........... = BSA state (with light-chain shield)
  (B) V1.8.13 EngVH ........ = uncorrected VHH (most hydrophobic positions intact)
  (C) V1.8.15 EngVH ........ = Hallmark-rescued VHH (post-engineering)

Scanned positions (Kabat):
  W36, V37, A40, G44, L45, W47, V50, K72, L91
"""
from __future__ import annotations
import os, sys, json, re
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from pathlib import Path
from typing import Dict, Optional, List

from Bio.PDB import PDBParser
from Bio.PDB.SASA import ShrakeRupley
from Bio.Data.IUPACData import protein_letters_3to1_extended as three2one

ROOT = Path(__file__).resolve().parent.parent
PROJ = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515"
FV_DIR = PROJ / "fv_structures"
V1813_DIR = PROJ / "v1813_structures"

SAMPLES = ["SP34", "Teplizumab", "OKT3", "Visilizumab", "Otelixizumab", "Foralumab"]

ORIGINAL_VH = {
    "SP34":         "DIKLQSGAELARPGASVKMSCKTSGYTFTRYTMHWVKQRPGQGLEWIGYINPSRGYTNYNQKFKDKATLTTDKSSSTAYMQLSSLTSEDSAVYYCARYYDDHYCLDYWGQGTTLTVSS",
    "Teplizumab":   "QVQLVQSGGGVVQPGRSLRLSCKASGYTFTRYTMHWVRQAPGKGLEWIGYINPSRGYTNYNQKVKDRFTISRDNSKNTAFLQMDSLRPEDTGVYFCARYYDDHYCLDYWGQGTPVTVSS",
    "OKT3":         "QVQLQQSGAELARPGASVKMSCKASGYTFTRYTMHWVKQRPGQGLEWIGYINPSRGYTNYNQKFKDKATLTTDKSSSTAYMQLSSLTSEDSAVYYCARYYDDHYCLDYWGQGTTLTVSS",
    "Visilizumab":  "QVQLVQSGAEVKKPGASVKVSCKASGYTFISYTMHWVRQAPGQGLEWMGYINPRSGYTHYNQKLKDKATLTADKSASTAYMELSSLRSEDTAVYYCARSAYYDYDGFAYWGQGTLVTVSS",
    "Otelixizumab": "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSFPMAWVRQAPGKGLEWVSTISTSGGRTYYRDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKFRQYSGGFDYWGQGTLVTVSS",
    "Foralumab":    "QVQLVESGGGVVQPGRSLRLSCAASGFKFSGYGMHWVRQAPGKGLEWVAVIWYDGSKKYYVDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARQMGYWHFDLWGRGTLVTVSS",
}

V1813_VH = {}
for s in SAMPLES:
    jpath = PROJ / "v1813_reports" / f"{s}_v1813.json"
    if jpath.exists():
        d = json.loads(jpath.read_text())
        V1813_VH[s] = d.get("final_seq") or d.get("engineered_sequence")

V1815_VH = {}
for s in SAMPLES:
    jpath = PROJ / "v1815_reports" / f"{s}_v1815.json"
    if jpath.exists():
        d = json.loads(jpath.read_text())
        V1815_VH[s] = d.get("final_seq") or d.get("engineered_sequence")


# ─── FR2 anchor → Kabat position map ─────────────────────────────────────────

def locate_anchor(seq: str) -> Optional[int]:
    """Locate Kabat G44 by anchoring on W36 (conserved FR1/FR2 Trp).
    K45 (=Hallmark anchor) is always W36+9 in VH/VHH (no insertions in FR2).
    Returns the index of K44 (linear, 0-indexed)."""
    m = re.search(r'W[VLIA][RKLM][QHE]', seq[30:42])
    if m:
        w36 = 30 + m.start()
        return w36 + 8
    m2 = re.search(r'[GA][LRIAVE][EQGDR][WLYG]', seq[35:55])
    if m2:
        return 35 + m2.start()
    return None


def find_cdr3_start(seq: str) -> Optional[int]:
    """Find Cys92 in CARxx motif marking end of FR3."""
    m = re.search(r'C[ARKQVNG][RAVKQTNYDS]', seq[80:110])
    if m:
        return 80 + m.start()
    return None


def position_map(seq: str) -> Dict[str, Optional[int]]:
    """Return linear indices for Kabat positions of interest."""
    base = locate_anchor(seq)
    if base is None:
        return {}
    cdr3_c = find_cdr3_start(seq)
    out = {
        "W36": base - 6,
        "V37": base - 5,
        "A40": base - 2,
        "G44": base,
        "L45": base + 1,
        "W47": base + 3,
        "V50": base + 6,
    }
    if cdr3_c:
        out["L91"] = cdr3_c - 1
        out["K72"] = cdr3_c - 20
    return out


# ─── SASA per chain from PDB ─────────────────────────────────────────────────

def chain_sasa(pdb: Path, chain_id: str = None) -> List[Dict]:
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


def seq_from_chain(chain: List[Dict]) -> str:
    return "".join(r["aa"] for r in chain)


def lookup(chain: List[Dict], seq: str, idx_in_seq: int) -> Optional[Dict]:
    if idx_in_seq is None or idx_in_seq < 0 or idx_in_seq >= len(seq):
        return None
    chain_seq = seq_from_chain(chain)
    if chain_seq == seq:
        r = chain[idx_in_seq]
        return {"aa": r["aa"], "sasa": r["sasa"]}
    for off in (-2, -1, 0, 1, 2):
        j = idx_in_seq + off
        if 0 <= j < len(chain) and chain[j]["aa"] == seq[idx_in_seq]:
            return {"aa": chain[j]["aa"], "sasa": chain[j]["sasa"]}
    return None


# ─── Main ────────────────────────────────────────────────────────────────────

LABELS_ORDER = ["W36", "V37", "A40", "G44", "L45", "W47", "V50", "K72", "L91"]
HYDROPHOBIC = set("LVIMAFWY")

def is_hydrophobic(aa: str) -> bool:
    return aa in HYDROPHOBIC

def classify_exposure(aa: str, sasa: float) -> str:
    if not is_hydrophobic(aa):
        return "ok (non-hydrophobic)"
    if sasa is None: return "?"
    if sasa < 20:    return "buried (safe)"
    if sasa < 50:    return "moderate"
    if sasa < 100:   return "EXPOSED"
    return "HIGHLY EXPOSED"


def main():
    out_rows = []
    summary = {}

    for name in SAMPLES:
        print(f"\n{'='*100}\n[{name}]")
        fv_pdb = FV_DIR / f"{name}_fv.pdb"
        v1813_pdb = V1813_DIR / f"{name}_v1813_engineered.pdb"
        if not fv_pdb.exists():
            print(f"  missing {fv_pdb}"); continue
        if not v1813_pdb.exists():
            print(f"  missing {v1813_pdb}"); continue

        orig = ORIGINAL_VH[name]
        eng13 = V1813_VH.get(name, orig)

        pos_orig = position_map(orig)
        pos_eng = position_map(eng13)

        fv_h = chain_sasa(fv_pdb, "H")
        vhh = chain_sasa(v1813_pdb)

        if not pos_orig or not pos_eng:
            print("  anchor NOT FOUND"); continue

        cdr3_len_orig = "?"
        cdr3_c = find_cdr3_start(orig)
        if cdr3_c:
            mwg = re.search(r"WG[QRKE]G", orig[cdr3_c:])
            if mwg:
                cdr3_len_orig = mwg.start() - 3

        print(f"  CDR3 length: {cdr3_len_orig} aa  |  anchor at vh[{pos_orig['G44']}]={orig[pos_orig['G44']]}{orig[pos_orig['G44']+1]}{orig[pos_orig['G44']+2]}{orig[pos_orig['G44']+3]}")
        print(f"  {'Pos':<5} {'Fv aa':<8} {'Fv SASA':<10} {'EngVH aa':<10} {'EngVH SASA':<12} {'Δ(VHH-Fv)':<12} Exposure")
        print("  " + "-" * 92)

        row_summary = {"sample": name, "cdr3_len": cdr3_len_orig, "positions": {}}
        for label in LABELS_ORDER:
            idx_o = pos_orig.get(label)
            idx_e = pos_eng.get(label)
            fv_res = lookup(fv_h, orig, idx_o) if idx_o is not None else None
            vhh_res = lookup(vhh, eng13, idx_e) if idx_e is not None else None
            if not fv_res or not vhh_res:
                continue
            d = round(vhh_res["sasa"] - fv_res["sasa"], 1)
            expo = classify_exposure(vhh_res["aa"], vhh_res["sasa"])
            print(f"  {label:<5} {fv_res['aa']:<8} {fv_res['sasa']:<10} {vhh_res['aa']:<10} "
                  f"{vhh_res['sasa']:<12} {d:<+12} {expo}")
            row_summary["positions"][label] = {
                "fv_aa": fv_res["aa"], "fv_sasa": fv_res["sasa"],
                "vhh_aa": vhh_res["aa"], "vhh_sasa": vhh_res["sasa"],
                "delta_sasa": d, "exposure": expo,
            }
            out_rows.append({
                "sample": name, "position": label,
                "fv_aa": fv_res["aa"], "fv_sasa": fv_res["sasa"],
                "vhh_aa": vhh_res["aa"], "vhh_sasa": vhh_res["sasa"],
                "delta_sasa": d, "exposure": expo,
                "cdr3_len": cdr3_len_orig,
            })
        summary[name] = row_summary

    out_dir = PROJ / "vl_interface_audit"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "vl_interface_full_sasa_audit.json").write_text(
        json.dumps({"summary": summary, "rows": out_rows}, indent=2, ensure_ascii=False),
        encoding="utf-8")

    print(f"\n{'='*100}\nWRITTEN: {out_dir / 'vl_interface_full_sasa_audit.json'}")

    print("\n\n>>> CROSS-SAMPLE SUMMARY: Hydrophobic positions EXPOSED (>50 Å²) in EngVH but BURIED (<20 Å²) in Fv\n")
    print(f"  {'Position':<10} {'Avg Fv SASA':<14} {'Avg VHH SASA':<15} {'Avg ΔSASA':<12} {'#samples hydrophobic & EXPOSED'}")
    print("  " + "-" * 95)
    for label in LABELS_ORDER:
        rows = [r for r in out_rows if r["position"] == label]
        if not rows: continue
        avg_fv = round(sum(r["fv_sasa"] for r in rows) / len(rows), 1)
        avg_vhh = round(sum(r["vhh_sasa"] for r in rows) / len(rows), 1)
        avg_d = round(avg_vhh - avg_fv, 1)
        n_exp = sum(1 for r in rows if r["vhh_aa"] in HYDROPHOBIC and r["vhh_sasa"] > 50)
        print(f"  {label:<10} {avg_fv:<14} {avg_vhh:<15} {'+'+str(avg_d):<12} {n_exp}/6")


if __name__ == "__main__":
    main()
