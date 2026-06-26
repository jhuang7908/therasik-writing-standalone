import json
from pathlib import Path

def check_residue(clone_id, chain, pdb_resi):
    path = Path(f"projects/PAG project/numbering/{clone_id}_numbering.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    
    # Try both 'numbering' and 'numbering_list'
    numbering_list = data.get(chain, {}).get("numbering", [])
    if not numbering_list:
        numbering_list = data.get(chain, {}).get("numbering_list", [])

    for entry in numbering_list:
        if entry.get("pdb_resi") == pdb_resi:
            print(f"\n{clone_id} {chain} {pdb_resi}:")
            print(f"  AA: {entry.get('aa')}")
            print(f"  IMGT Pos: {entry.get('imgt_pos')}")
            print(f"  Kabat Pos: {entry.get('kabat_pos')}")
            print(f"  IMGT CDR: {entry.get('imgt_cdr')}")
            print(f"  Kabat CDR: {entry.get('kabat_cdr')}")
            print(f"  Chothia CDR: {entry.get('chothia_cdr')}")
            return
    print(f"\n{clone_id} {chain} {pdb_resi}: NOT FOUND")

print("=== Checking Specific Residues ===")
check_residue("001", "vl", 51)
check_residue("008", "vl", 97)
check_residue("008", "vh", 33)
check_residue("008", "vl", 101)
check_residue("7M16", "vl", 89)
