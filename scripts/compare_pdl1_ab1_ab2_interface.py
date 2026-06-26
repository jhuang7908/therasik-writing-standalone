#!/usr/bin/env python3
"""
PDL1_Ab1 vs PDL1_Ab2 ：BSA、、。
 2–5 （SASA ）。
"""
import re
import sys
from pathlib import Path

def _res_num(s: str) -> int:
    m = re.search(r"\d+", s)
    return int(m.group()) if m else 0

SCRIPT_DIR = Path(__file__).resolve().parent
SUITE_ROOT = SCRIPT_DIR.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from core.evaluation.interface_metrics import compute_interface_metrics

PDB1 = r"C:\Users\NextVivo\Dropbox\PC (2)\Downloads\dongxiao\pdl1_ab1_a7c2a.result\pdl1_ab_a7c2a\pdl1_ab_a7c2a_relaxed_rank_001_alphafold2_multimer_v3_model_4_seed_000.pdb"
PDB2 = r"C:\Users\NextVivo\Dropbox\PC (2)\Downloads\dongxiao\PDL1_Ab2_dec04.result\PDL1_Ab2_dec04\PDL1_Ab2_dec04_relaxed_rank_001_alphafold2_multimer_v3_model_3_seed_000.pdb"

print("Computing Ab1 interface (may take 1-2 min)...")
r1 = compute_interface_metrics(pdb_path=PDB1, vh_chain="A", vl_chain="B", ag_chain="C")

print("Computing Ab2 interface (may take 1-2 min)...")
r2 = compute_interface_metrics(pdb_path=PDB2, vh_chain="A", vl_chain="B", ag_chain="C")

print("\n" + "=" * 60)
print("PDL1_Ab1 vs PDL1_Ab2 ")
print("=" * 60)

def _detail(r, name: str) -> None:
    para = r.get("paratope_residues") or []
    epi = r.get("epitope_residues") or []
    vh_list = sorted([p for p in para if p.startswith("A")], key=_res_num)
    vl_list = sorted([p for p in para if p.startswith("B")], key=_res_num)
    epi_sorted = sorted(epi, key=_res_num)
    print(f"\n--- {name}  ---")
    print(f"  BSA (Å²):     {r.get('bsa_total_A2') or r.get('bsa_A2') or '—'}")
    print(f"  SC :     {r.get('sc_score', '—')}")
    print(f"  VH :     {r.get('paratope_vh_count')}  ({r.get('paratope_vh_pct')}%)")
    print(f"  VL :     {r.get('paratope_vl_count')}  ({r.get('paratope_vl_pct')}%)")
    print(f"  H-:        {r.get('hbond_count', 0)} ")
    print(f"  :        {r.get('salt_bridge_count', 0)} ")
    print(f"  :    {r.get('hydrophobic_contact_count', 0)}")
    print(f"  : {r.get('interface_atom_contacts', '—')}")
    print(f"  Paratope (VH  A): {vh_list}")
    print(f"  Paratope (VL  B): {vl_list}")
    print(f"  Epitope (PD-L1 , ): {epi_sorted}")
    if r.get("hbond_list"):
        print(f"  H-:    {r['hbond_list'][:8]}")
    if r.get("salt_bridge_list"):
        print(f"  :        {r['salt_bridge_list']}")
    if r.get("hydrophobic_residue_pairs"):
        print(f"  :  {r['hydrophobic_residue_pairs'][:10]}")

_detail(r1, "PDL1_Ab1")
_detail(r2, "PDL1_Ab2")

ep1 = set(r1.get("epitope_residues", []))
ep2 = set(r2.get("epitope_residues", []))

print("\n--- PD-L1  ---")
print(f"  Ab1 :   {ep1 - ep2}")
print(f"  Ab2 :   {ep2 - ep1}")
print(f"  :   {ep1 & ep2}")
