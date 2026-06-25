"""Run SASA on Teplizumab V1.8.13 output (k45=L, uncorrected) for calibration reference."""
import os, sys, json, subprocess
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PREDICT_SCRIPT = ROOT / "scripts" / "_predict_vhh_with_rmsd.py"
j13 = ROOT / "projects/CD3_VH2VHH_Batch_20260515/v1813_reports/Teplizumab_v1813.json"
OUT_PDB = ROOT / "projects/CD3_VH2VHH_Batch_20260515/v1816_sasa_reports/Teplizumab_v1813_ref.pdb"
OUT_PDB.parent.mkdir(parents=True, exist_ok=True)

r = json.loads(j13.read_text())
seq = r["final_seq"]  # V1.8.13 final: k45=L (never changed)
hallmark_pos = {}
import re
m = re.search(r'[GA][LRA][EQ][WLY]', seq[35:55])
if m:
    base = 35 + m.start()
    hallmark_pos = {"K44": base, "K45": base + 1, "K47": base + 3}
print(f"V1.8.13 Teplizumab seq: {seq[:50]}...")
print(f"k45 idx={hallmark_pos.get('K45')} aa={seq[hallmark_pos.get('K45',0)] if hallmark_pos.get('K45') else '?'}")

if not OUT_PDB.exists():
    payload = {"H": seq, "out_path": str(OUT_PDB)}
    pj = OUT_PDB.with_suffix(".payload.json")
    pj.write_text(json.dumps(payload))
    env = os.environ.copy()
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    subprocess.run([sys.executable, str(PREDICT_SCRIPT), "--json", str(pj)], env=env)
    pj.unlink(missing_ok=True)

if OUT_PDB.exists():
    from Bio.PDB import PDBParser
    from Bio.PDB.SASA import ShrakeRupley
    from Bio.Data.IUPACData import protein_letters_3to1_extended as three2one
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("ref", str(OUT_PDB))
    sr = ShrakeRupley()
    sr.compute(structure, level="R")
    residues = []
    for model in structure:
        for chain in model:
            for res in chain.get_residues():
                if res.id[0] != " ": continue
                aa3 = res.get_resname().strip()
                aa1 = three2one.get(aa3.capitalize(), "X")
                residues.append({"resnum": res.id[1], "aa": aa1, "sasa": round(res.sasa, 2)})

    for label, idx in hallmark_pos.items():
        if idx < len(residues):
            print(f"  {label}: aa={residues[idx]['aa']} SASA={residues[idx]['sasa']:.1f} A2")
