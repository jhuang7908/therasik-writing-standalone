"""
Test: Y91/F91 SASA vs CDR3 Length (n>=70 single-domain VHH cohort)
====================================================================
Hypothesis (CDR3-drape, Vincke 2009): As CDR3 length grows, the long
loop drapes over the former VL interface region, including Y91/F91
which sits at the FR3 tail just before Cys92.

Prediction: SASA(Y91/F91) should ANTI-CORRELATE with CDR3 length
(longer CDR3 -> more shielding -> lower SASA).

Cohort: data/vhh_master_benchmarks_v3.csv (160 entries, 159 with PDBs)
  Use only VHH-like single-domain entries (Clinical_VHH, Engineered_Human_VH,
  Autonomous_Human_VH, Transgenic_sdAb, plus Database_B if VHH-format).

For each:
  1. Read sequence + PDB
  2. Locate Y91/F91 by anchoring on Cys92 (last C in C..[CDR3]..WG[QRKE]G motif)
  3. Compute per-residue SASA (Bio.PDB ShrakeRupley)
  4. Measure CDR3 length from Cys92+1 to WG[QRKE]G-1
  5. Plot/correlate SASA vs CDR3 length
"""
from __future__ import annotations
import os, sys, re, json
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from pathlib import Path
import pandas as pd
from typing import Optional, Dict, List

from Bio.PDB import PDBParser
from Bio.PDB.SASA import ShrakeRupley
from Bio.Data.IUPACData import protein_letters_3to1_extended as three2one

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "vhh_master_benchmarks_v3.csv"
META_DIR = ROOT / "data" / "vhh_clinical_39_union" / "immunebuilder_models"
OUT_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "vl_interface_audit"


def chain_sasa(pdb: Path) -> List[Dict]:
    parser = PDBParser(QUIET=True)
    struct = parser.get_structure("s", str(pdb))
    sr = ShrakeRupley()
    sr.compute(struct, level="R")
    out = []
    for model in struct:
        for chain in model:
            for r in chain.get_residues():
                if r.id[0] != " ":
                    continue
                aa3 = r.get_resname().strip()
                aa1 = three2one.get(aa3.capitalize(), "X")
                out.append({"aa": aa1, "sasa": round(r.sasa, 2)})
            break
        break
    return out


def find_cys92_and_cdr3(seq: str):
    """Return (cys92_idx, cdr3_start, cdr3_end, cdr3_seq, cdr3_len).
    Uses C..WG[QRKE]G end motif. cdr3 = seq[cys92+1:wg_start]."""
    for m in re.finditer(r"C", seq[80:110]):
        cys = 80 + m.start()
        wg = re.search(r"WG[QRKEAS]G", seq[cys + 1:cys + 35])
        if wg:
            cdr3_start = cys + 1
            cdr3_end = cdr3_start + wg.start() - 1
            cdr3_seq = seq[cdr3_start:cdr3_end + 1]
            return cys, cdr3_start, cdr3_end, cdr3_seq, len(cdr3_seq)
    return None, None, None, None, None


def measure(entry, sasa_residues, sasa_anchor_aa, sasa_anchor_idx):
    """Return SASA at given idx if AA matches; else search nearby."""
    target_aa = entry["target_aa"]
    if sasa_anchor_idx < len(sasa_residues) and sasa_residues[sasa_anchor_idx]["aa"] == target_aa:
        return sasa_residues[sasa_anchor_idx]["sasa"]
    for off in (-2, -1, 1, 2):
        j = sasa_anchor_idx + off
        if 0 <= j < len(sasa_residues) and sasa_residues[j]["aa"] == target_aa:
            return sasa_residues[j]["sasa"]
    return None


def main():
    df = pd.read_csv(CSV)
    df = df[df["pdb_path"].notna()].copy()
    rows = []

    for _, row in df.iterrows():
        name = row["id"]
        cat = row["category"]
        pdb_path = Path(row["pdb_path"])
        if not pdb_path.exists():
            continue

        meta_path = META_DIR / name / "meta.json"
        seq = None
        if meta_path.exists():
            try:
                seq = json.loads(meta_path.read_text())["sequence"]
            except Exception:
                seq = None
        if not seq:
            for cand in pdb_path.parent.glob("*.json"):
                try:
                    data = json.loads(cand.read_text())
                    if "sequence" in data:
                        seq = data["sequence"]; break
                    if "H" in data:
                        seq = data["H"]; break
                except Exception:
                    pass
        if not seq:
            sasa = chain_sasa(pdb_path)
            seq = "".join(r["aa"] for r in sasa)

        cys, cdr3_s, cdr3_e, cdr3_aa, cdr3_len = find_cys92_and_cdr3(seq)
        if cdr3_len is None:
            continue

        pos91_idx = cys - 1
        pos91_aa = seq[pos91_idx] if pos91_idx >= 0 else None
        if pos91_aa not in ("Y", "F"):
            continue

        try:
            sasa = chain_sasa(pdb_path)
        except Exception as e:
            continue
        sasa_seq = "".join(r["aa"] for r in sasa)
        if sasa_seq != seq:
            j = sasa_seq.find(seq[pos91_idx - 3:pos91_idx + 3])
            if j >= 0:
                pos91_in_sasa = j + 3
            else:
                continue
        else:
            pos91_in_sasa = pos91_idx
        if pos91_in_sasa >= len(sasa):
            continue
        if sasa[pos91_in_sasa]["aa"] != pos91_aa:
            found = None
            for off in (-2, -1, 0, 1, 2):
                j = pos91_in_sasa + off
                if 0 <= j < len(sasa) and sasa[j]["aa"] == pos91_aa:
                    found = j; break
            if found is None:
                continue
            pos91_in_sasa = found

        sasa91 = sasa[pos91_in_sasa]["sasa"]

        rows.append({
            "id": name, "category": cat, "cdr3_len": cdr3_len,
            "cdr3_aa": cdr3_aa, "pos91_aa": pos91_aa, "sasa_pos91": sasa91,
            "is_VHH_clinical": cat == "Clinical_VHH",
        })

    res = pd.DataFrame(rows)
    print(f"\nTotal Y91/F91-bearing entries with usable structure: {len(res)}")
    print(f"  Clinical_VHH: {res['is_VHH_clinical'].sum()}")
    print(f"  Other (VH/engineered): {(~res['is_VHH_clinical']).sum()}")

    print("\nCDR3 length distribution:")
    print(res["cdr3_len"].describe().round(1).to_string())

    bins = [(0,8),(9,12),(13,16),(17,20),(21,30)]
    print(f"\n{'CDR3 bin':<10} {'n':<5} {'mean Y91/F91 SASA':<22} {'median':<10} {'std'}")
    print("-" * 65)
    for lo, hi in bins:
        sub = res[(res["cdr3_len"] >= lo) & (res["cdr3_len"] <= hi)]
        if len(sub) == 0: continue
        print(f"{lo}-{hi:<7} {len(sub):<5} {sub['sasa_pos91'].mean():<22.2f} "
              f"{sub['sasa_pos91'].median():<10.2f} {sub['sasa_pos91'].std():.2f}")

    print("\nBy category:")
    for cat in res["category"].unique():
        sub = res[res["category"] == cat]
        print(f"  {cat:<25} n={len(sub):<3} cdr3_len_mean={sub['cdr3_len'].mean():.1f}  "
              f"sasa_mean={sub['sasa_pos91'].mean():.2f}")

    pearson_r = res["cdr3_len"].corr(res["sasa_pos91"], method="pearson")
    spearman_r = res["cdr3_len"].corr(res["sasa_pos91"], method="spearman")
    print(f"\n>>> Correlation (CDR3 length vs Y91/F91 SASA):")
    print(f"    Pearson  r = {pearson_r:+.3f}")
    print(f"    Spearman r = {spearman_r:+.3f}")

    print("\nClinical_VHH only (purest VHH-evolved cohort):")
    sub = res[res["is_VHH_clinical"]]
    if len(sub) > 5:
        pr = sub["cdr3_len"].corr(sub["sasa_pos91"], method="pearson")
        sr = sub["cdr3_len"].corr(sub["sasa_pos91"], method="spearman")
        print(f"    n = {len(sub)}, Pearson r = {pr:+.3f}, Spearman r = {sr:+.3f}")

    print("\nTop 10 longest CDR3 entries:")
    print(res.nlargest(10, "cdr3_len")[["id","category","cdr3_len","pos91_aa","sasa_pos91"]].to_string(index=False))
    print("\nTop 10 shortest CDR3 entries:")
    print(res.nsmallest(10, "cdr3_len")[["id","category","cdr3_len","pos91_aa","sasa_pos91"]].to_string(index=False))

    OUT_DIR.mkdir(exist_ok=True, parents=True)
    out_csv = OUT_DIR / "y91_sasa_vs_cdr3_length.csv"
    res.to_csv(out_csv, index=False)
    print(f"\nWritten: {out_csv}")


if __name__ == "__main__":
    main()
