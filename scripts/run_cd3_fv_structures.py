"""
ABodyBuilder2 Fv Structure Prediction — 6 CD3 Antibodies
=========================================================
Predicts VH+VL Fv structures using ImmuneBuilder ABodyBuilder2.
Then measures SASA of k45, k47, k44 in the VH/VL context (to confirm
these residues are BURIED = BSA, not surface-exposed = SASA).

Purpose: Validate the §1a structural model — k45(L)/k47(W) are buried
(BSA) when VL is present; only become surface-exposed (SASA) after VL removal.

Sequences sourced from Thera-SAbDab (verified 2026-05-16).
"""
from __future__ import annotations
import os, sys, json, subprocess, re
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from Bio.PDB import PDBParser
from Bio.PDB.SASA import ShrakeRupley
from Bio.Data.IUPACData import protein_letters_3to1_extended as three2one

OUT_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "fv_structures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Sequences (all verified from Thera-SAbDab 2026-05-16) ───────────────────
SAMPLES = [
    {
        "name": "SP34",
        "source": "Thera-SAbDab (Blinatumomab CD3 arm / workspace FASTA)",
        "H": "DIKLQSGAELARPGASVKMSCKTSGYTFTRYTMHWVKQRPGQGLEWIGYINPSRGYTNYNQKFKDKATLTTDKSSSTAYMQLSSLTSEDSAVYYCARYYDDHYCLDYWGQGTTLTVSS",
        "L": "DIQLTQSPAIMSASPGEKVTMTCRASSSVSYMNWYQQKSGTSPKRWIYDTSKVASGVPYRFSGSGSGTSYSLTISSMEAEDAATYYCQQWSSNPLTFGAGTKLELK",
        "genetics": "murine",
    },
    {
        "name": "Teplizumab",
        "source": "Thera-SAbDab 2026-05-16",
        "H": "QVQLVQSGGGVVQPGRSLRLSCKASGYTFTRYTMHWVRQAPGKGLEWIGYINPSRGYTNYNQKVKDRFTISRDNSKNTAFLQMDSLRPEDTGVYFCARYYDDHYCLDYWGQGTPVTVSS",
        "L": "DIQMTQSPSSLSASVGDRVTITCSASSSVSYMNWYQQTPGKAPKRWIYDTSKLASGVPSRFSGSGSGTDYTFTISSLQPEDIATYYCQQWSSNPFTFGQGTKLQIT",
        "genetics": "humanized",
    },
    {
        "name": "OKT3",
        "source": "workspace payload.json (Muromonab-CD3)",
        "H": "QVQLQQSGAELARPGASVKMSCKASGYTFTRYTMHWVKQRPGQGLEWIGYINPSRGYTNYNQKFKDKATLTTDKSSSTAYMQLSSLTSEDSAVYYCARYYDDHYCLDYWGQGTTLTVSS",
        "L": "QIVLTQSPAIMSASPGEKVTMTCSASSSVSYMNWYQQKSGTSPKRWIYDTSKLASGVPAHFRGSGSGTSYSLTISGMEAEDAATYYCQQWSSNPFTFGSGTKLEIN",
        "genetics": "murine",
    },
    {
        "name": "Visilizumab",
        "source": "Thera-SAbDab 2026-05-16",
        "H": "QVQLVQSGAEVKKPGASVKVSCKASGYTFISYTMHWVRQAPGQGLEWMGYINPRSGYTHYNQKLKDKATLTADKSASTAYMELSSLRSEDTAVYYCARSAYYDYDGFAYWGQGTLVTVSS",
        "L": "DIQMTQSPSSLSASVGDRVTITCSASSSVSYMNWYQQKPGKAPKRLIYDTSKLASGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQWSSNPPTFGGGTKVEIK",
        "genetics": "humanized",
    },
    {
        "name": "Otelixizumab",
        "source": "Thera-SAbDab 2026-05-16",
        "H": "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSFPMAWVRQAPGKGLEWVSTISTSGGRTYYRDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKFRQYSGGFDYWGQGTLVTVSS",
        "L": "DIQLTQPNSVSTSLGSTVKLSCTLSSGNIENNYVHWYQLYEGRSPTTMIYDDDKRPDGVPDRFSGSIDRSSNSAFLTIHNVAIEDEAIYFCHSYVSSFNVFGGGTKLTVL",
        "genetics": "humanized",
    },
    {
        "name": "Foralumab",
        "source": "Thera-SAbDab 2026-05-16",
        "H": "QVQLVESGGGVVQPGRSLRLSCAASGFKFSGYGMHWVRQAPGKGLEWVAVIWYDGSKKYYVDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARQMGYWHFDLWGRGTLVTVSS",
        "L": "EIVLTQSPATLSLSPGERATLSCRASQSVSSYLAWYQQKPGQAPRLLIYDASNRATGIPARFSGSGSGTDFTLTISSLEPEDFAVYYCQQRSNWPPLTFGGGTKVEIK",
        "genetics": "fully_human",
    },
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def predict_fv(vh: str, vl: str, out_pdb: Path) -> bool:
    """Run ABodyBuilder2 via ImmuneBuilder directly."""
    if out_pdb.exists():
        print(f"    [cache] {out_pdb.name}")
        return True
    payload = {"H": vh, "L": vl, "out_path": str(out_pdb), "model_type": "abody"}
    payload_path = out_pdb.with_suffix(".payload.json")
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    predict_script = ROOT / "scripts" / "_predict_abody_fv.py"
    env = os.environ.copy()
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    result = subprocess.run(
        [sys.executable, str(predict_script), "--json", str(payload_path)],
        capture_output=True, text=True, env=env, timeout=600,
    )
    payload_path.unlink(missing_ok=True)
    if result.returncode != 0:
        print(f"    [ABodyBuilder2 ERROR] {result.stderr[-400:]}")
        return False
    return out_pdb.exists()


def parse_sasa_by_chain(pdb_path: Path) -> Dict[str, list]:
    """Parse SASA per residue, separated by chain H and L."""
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("fv", str(pdb_path))
    sr = ShrakeRupley()
    sr.compute(structure, level="R")
    chains = {}
    for model in structure:
        for chain in model:
            cid = chain.id
            residues = []
            for res in chain.get_residues():
                if res.id[0] != " ":
                    continue
                aa3 = res.get_resname().strip()
                aa1 = three2one.get(aa3.capitalize(), "X")
                residues.append({"resnum": res.id[1], "aa": aa1, "sasa": round(res.sasa, 2)})
            chains[cid] = residues
    return chains


def find_hallmark_pos_in_vh(vh_seq: str) -> Dict[str, Optional[int]]:
    m = re.search(r'[GA][LRA][EQ][WLY]', vh_seq[35:55])
    if m:
        base = 35 + m.start()
        return {"K44": base, "K45": base + 1, "K47": base + 3}
    return {}


def get_residue_sasa(sasa_list: list, idx: int, expected_aa: str) -> Optional[float]:
    if idx < len(sasa_list) and sasa_list[idx]["aa"] == expected_aa:
        return sasa_list[idx]["sasa"]
    for j in range(max(0, idx - 2), min(len(sasa_list), idx + 3)):
        if sasa_list[j]["aa"] == expected_aa:
            return sasa_list[j]["sasa"]
    return None


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    results = []
    for s in SAMPLES:
        name = s["name"]
        pdb = OUT_DIR / f"{name}_fv.pdb"
        print(f"\n[{name}] ({s['genetics']}) Predicting VH/VL Fv structure...")

        ok = predict_fv(s["H"], s["L"], pdb)
        entry = {
            "name": name, "genetics": s["genetics"], "source": s["source"],
            "prediction_ok": ok,
        }

        if ok:
            chains = parse_sasa_by_chain(pdb)
            h_chain = chains.get("H", [])
            hallmark = find_hallmark_pos_in_vh(s["H"])

            zone1 = {}
            for label, idx in hallmark.items():
                aa = s["H"][idx] if idx < len(s["H"]) else "?"
                sasa = get_residue_sasa(h_chain, idx, aa)
                zone1[label] = {"idx": idx, "aa": aa, "sasa_fv": sasa}

            entry["zone1_sasa_in_fv"] = zone1
            k45 = zone1.get("K45", {})
            k47 = zone1.get("K47", {})
            print(f"  k45={k45.get('aa','?')} SASA_in_Fv={k45.get('sasa_fv','?')} Å²  "
                  f"k47={k47.get('aa','?')} SASA_in_Fv={k47.get('sasa_fv','?')} Å²")
            # Compare with VHH SASA from V1.8.16 (if available)
            sasa_16 = OUT_DIR.parent / "v1816_sasa_reports" / f"{name}_v1816_sasa.json"
            if sasa_16.exists():
                r16 = json.loads(sasa_16.read_text())
                z16 = r16.get("v1816_zone1_sasa", {})
                k45_vhh = z16.get("K45", {}).get("sasa")
                k47_vhh = z16.get("K47", {}).get("sasa")
                entry["k45_sasa_fv"] = k45.get("sasa_fv")
                entry["k45_sasa_vhh"] = k45_vhh
                entry["k47_sasa_fv"] = k47.get("sasa_fv")
                entry["k47_sasa_vhh"] = k47_vhh
                delta_k45 = round(k45_vhh - k45.get("sasa_fv", 0), 1) if k45_vhh and k45.get("sasa_fv") else None
                print(f"  k45 SASA: Fv={k45.get('sasa_fv','?'):.1f} → VHH={k45_vhh} Å² (ΔSASA={delta_k45})")
        results.append(entry)
        (OUT_DIR / f"{name}_fv_sasa.json").write_text(
            json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")

    # Summary table
    print(f"\n{'='*115}")
    print(f"{'Sample':<14} {'Genotype':<11} {'k45 aa':<8} {'k45 SASA(Fv)':<15} "
          f"{'k45 SASA(VHH)':<15} {'ΔSASA k45':<12} {'k47 SASA(Fv)':<14} {'k47 SASA(VHH)'}")
    print("=" * 115)
    for r in results:
        if not r.get("prediction_ok"):
            print(f"{r['name']:<14} PREDICTION FAILED")
            continue
        k45_aa = r.get("zone1_sasa_in_fv", {}).get("K45", {}).get("aa", "?")
        k45_fv = r.get("k45_sasa_fv")
        k45_vh = r.get("k45_sasa_vhh")
        k47_fv = r.get("k47_sasa_fv")
        k47_vh = r.get("k47_sasa_vhh")
        delta = round(k45_vh - k45_fv, 1) if k45_vh and k45_fv else "N/A"
        print(f"{r['name']:<14} {r['genetics']:<11} {str(k45_aa):<8} "
              f"{str(k45_fv)+'Å²':<15} {str(k45_vh)+'Å²':<15} {str(delta):<12} "
              f"{str(k47_fv)+'Å²':<14} {str(k47_vh)+'Å²'}")


if __name__ == "__main__":
    main()
