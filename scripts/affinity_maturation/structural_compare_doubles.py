"""
G49A+F112L vs WT 
==========================
1.  EvoEF2 BuildMutant  PDB
2.  A， CA-RMSD（ / ）
3.  F112/L112  G49/A49  HER2 
4.  B-factor （ B-factor ）

Usage (from repo root):
    python scripts/affinity_maturation/structural_compare_doubles.py
"""
import os, shutil, subprocess, tempfile
from pathlib import Path
import numpy as np
import yaml
from Bio.PDB import PDBParser, Superimposer, NeighborSearch

SCRIPT_DIR  = Path(__file__).resolve().parent
CONFIG      = yaml.safe_load((SCRIPT_DIR / "config.yaml").read_text(encoding="utf-8"))
EVOEF2      = str((SCRIPT_DIR / CONFIG["paths"]["evoef2_exe"]).resolve())
COMPLEX_PDB = str((SCRIPT_DIR / CONFIG["paths"]["complex_pdb"]).resolve())
OUTPUT_DIR  = Path((SCRIPT_DIR / CONFIG["paths"]["output_dir"]).resolve())
VHH_CHAIN   = CONFIG["project"]["vhh_chain"]
AG_CHAIN    = CONFIG["project"]["antigen_chain"]

DOUBLE_MUT = [
    {"site": 49,  "wt_aa": "G", "mut_aa": "A"},
    {"site": 112, "wt_aa": "F", "mut_aa": "L"},
]
LABEL = "G49A+F112L"

INTERFACE_CUTOFF = 5.0  # Å


def build_double_mutant(tmp_dir: str) -> str:
    """Build G49A+F112L mutant PDB with EvoEF2 BuildMutant."""
    pdb_name = os.path.basename(COMPLEX_PDB)
    shutil.copy2(COMPLEX_PDB, os.path.join(tmp_dir, pdb_name))
    mut_str = ",".join(f"{m['wt_aa']}{VHH_CHAIN}{m['site']}{m['mut_aa']}" for m in DOUBLE_MUT) + ";"
    with open(os.path.join(tmp_dir, "ind.txt"), "w") as f:
        f.write(mut_str + "\n")
    subprocess.run(
        [EVOEF2, "--command=BuildMutant", f"--pdb={pdb_name}", "--mutant_file=ind.txt"],
        capture_output=True, text=True, cwd=tmp_dir, timeout=120
    )
    stem = Path(pdb_name).stem
    out = os.path.join(tmp_dir, f"{stem}_Model_0001.pdb")
    if not os.path.exists(out):
        raise RuntimeError("EvoEF2 BuildMutant failed — check EvoEF2 exe path")
    return out


def get_chain_atoms(structure, chain_id, atom_name="CA"):
    return [
        atom
        for chain in structure[0].get_chains()
        if chain.id == chain_id
        for res in chain.get_residues()
        for atom in res.get_atoms()
        if atom.name == atom_name and res.id[0] == " "
    ]


def aligned_ca_rmsd(wt_struct, mut_struct, chain_id, label=""):
    """Superimpose mut onto wt on chain_id CAs, return RMSD."""
    wt_cas  = get_chain_atoms(wt_struct, chain_id)
    mut_cas = get_chain_atoms(mut_struct, chain_id)
    # Match by residue number
    wt_idx  = {a.get_parent().id[1]: a for a in wt_cas}
    mut_idx = {a.get_parent().id[1]: a for a in mut_cas}
    common  = sorted(set(wt_idx) & set(mut_idx))
    if not common:
        return None, None
    ref = [wt_idx[r] for r in common]
    mob = [mut_idx[r] for r in common]
    sup = Superimposer()
    sup.set_atoms(ref, mob)
    sup.apply(mut_struct.get_atoms())
    return sup.rms, len(common)


def nearest_contact(struct, vhh_res_id, ag_chain_id, cutoff=8.0):
    """Return distance from any atom in VHH resi to nearest HER2 atom."""
    ag_atoms = list(
        a for chain in struct[0].get_chains()
        if chain.id == ag_chain_id
        for res in chain.get_residues()
        for a in res.get_atoms()
        if a.element not in ("H", None)
    )
    vhh_res = None
    for chain in struct[0].get_chains():
        if chain.id == VHH_CHAIN:
            for res in chain.get_residues():
                if res.id[1] == vhh_res_id:
                    vhh_res = res
                    break

    if vhh_res is None or not ag_atoms:
        return None, None

    ns = NeighborSearch(ag_atoms)
    min_d = np.inf
    min_pair = ("?", "?")
    for atom in vhh_res.get_atoms():
        if atom.element in ("H", None):
            continue
        coord = atom.coord.tolist()
        hits = ns.search(coord, cutoff, level="A")
        for ag_atom in hits:
            d = float(np.linalg.norm(atom.coord - ag_atom.coord))
            if d < min_d:
                min_d = d
                min_pair = (atom.name, ag_atom.get_parent().id[1])
    return (round(min_d, 2), min_pair) if min_d < np.inf else (None, None)


def main():
    parser = PDBParser(QUIET=True)
    wt_struct  = parser.get_structure("WT", COMPLEX_PDB)

    print("=" * 62)
    print(f": WT  vs  {LABEL}")
    print(f" PDB: {COMPLEX_PDB}")
    print("=" * 62)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="struct_cmp_") as tmp:
        print(f"\n[1] EvoEF2 BuildMutant → {LABEL}...")
        mut_pdb = build_double_mutant(tmp)
        out_dest = OUTPUT_DIR / f"complex_{LABEL.replace('+','_')}.pdb"
        shutil.copy2(mut_pdb, out_dest)
        print(f"  → {out_dest}")

        mut_struct = parser.get_structure(LABEL, str(out_dest))

    # CA-RMSD 
    print("\n[2] Cα RMSD（ A）")
    rmsd_all, n_all = aligned_ca_rmsd(wt_struct, mut_struct, VHH_CHAIN, "")
    print(f"   VHH Cα RMSD = {rmsd_all:.3f} Å  ({n_all} )")

    # ：WT  HER2 5 Å  VHH 
    all_ag = [
        a for chain in wt_struct[0].get_chains()
        if chain.id == AG_CHAIN
        for res in chain.get_residues()
        for a in res.get_atoms()
        if a.element not in ("H", None)
    ]
    ns_ag = NeighborSearch(all_ag)
    iface_resi = set()
    for chain in wt_struct[0].get_chains():
        if chain.id != VHH_CHAIN:
            continue
        for res in chain.get_residues():
            for a in res.get_atoms():
                if ns_ag.search(a.coord.tolist(), INTERFACE_CUTOFF, level="A"):
                    iface_resi.add(res.id[1])

    print(f"\n[3]  Cα RMSD（VHH  {len(iface_resi)} ，{INTERFACE_CUTOFF} Å ）")
    # 
    wt_cas_iface  = [a for a in get_chain_atoms(wt_struct, VHH_CHAIN) if a.get_parent().id[1] in iface_resi]
    mut_cas_iface = []
    wt_idx = {a.get_parent().id[1]: a for a in wt_cas_iface}
    for chain in mut_struct[0].get_chains():
        if chain.id != VHH_CHAIN:
            continue
        for res in chain.get_residues():
            if res.id[1] in wt_idx:
                for a in res.get_atoms():
                    if a.name == "CA":
                        mut_cas_iface.append(a)
    if wt_cas_iface and mut_cas_iface:
        sup2 = Superimposer()
        sup2.set_atoms(wt_cas_iface[:len(mut_cas_iface)], mut_cas_iface)
        print(f"   Cα RMSD = {sup2.rms:.3f} Å  ({len(mut_cas_iface)} )")
    else:
        print("   Cα RMSD （）")

    #  → HER2 
    print("\n[4]  HER2 （8 Å ）")
    for name, struct, resi_list in [("WT", wt_struct, [49, 112]), (LABEL, mut_struct, [49, 112])]:
        print(f"\n  [{name}]")
        for resi in resi_list:
            d, pair = nearest_contact(struct, resi, AG_CHAIN, cutoff=8.0)
            if d is not None:
                print(f"    resi {resi:3d}: {d:.2f} Å  (VHH atom {pair[0]} → HER2 resi {pair[1]})")
            else:
                print(f"    resi {resi:3d}: > 8 Å ()")

    #  F112/L112 HER2 
    print("\n[5] F112/L112  HER2 （< 5 Å）")
    for name, struct in [("WT (F112)", wt_struct), (f"{LABEL} (L112)", mut_struct)]:
        print(f"\n  [{name}]")
        for chain in struct[0].get_chains():
            if chain.id != VHH_CHAIN:
                continue
            for res in chain.get_residues():
                if res.id[1] != 112:
                    continue
                for atom in res.get_atoms():
                    if atom.name in ("N","CA","C","O"):
                        continue
                    hits = ns_ag.search(atom.coord.tolist(), 5.0, level="A") if name.startswith("WT") else []
                    # rebuild ns for mut
                    if not name.startswith("WT"):
                        ag_atoms_mut = [
                            a for ch in struct[0].get_chains()
                            if ch.id == AG_CHAIN
                            for r in ch.get_residues()
                            for a in r.get_atoms()
                            if a.element not in ("H", None)
                        ]
                        ns_mut = NeighborSearch(ag_atoms_mut)
                        hits = ns_mut.search(atom.coord.tolist(), 5.0, level="A")
                    for ag_atom in hits:
                        d = round(float(np.linalg.norm(atom.coord - ag_atom.coord)), 2)
                        print(f"    {atom.name:<4} → HER2 resi {ag_atom.get_parent().id[1]:>4} {ag_atom.get_parent().resname} {ag_atom.name:<4}  {d:.2f} Å")

    print("\n" + "=" * 62)
    print(f" PDB : {out_dest}")
    print("=" * 62)


if __name__ == "__main__":
    main()
