import json
from pathlib import Path

def verify_mutation(clone_id, chain, pdb_resi, mut_aa):
    path = Path(f"projects/PAG project/numbering/{clone_id}_numbering.json")
    if not path.exists():
        print(f"  {clone_id}: file not found")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    
    numbering_list = data.get(chain, {}).get("numbering_list", [])
    if not numbering_list:
        # Try 'numbering' if 'numbering_list' not present
        numbering_list = data.get(chain, {}).get("numbering", [])

    match = None
    for entry in numbering_list:
        if entry.get("pdb_resi") == pdb_resi:
            match = entry
            break
    
    if not match:
        print(f"  {clone_id} {chain} {pdb_resi}: PDB residue not found in numbering list")
        return
    
    wt_aa = match.get("aa")
    lin_idx = match.get("linear_idx")
    
    print(f"  {clone_id} {chain} {pdb_resi}: WT={wt_aa}, Mut={mut_aa}, Linear Index={lin_idx}")
    
    # Check CDR status
    imgt_cdr = match.get("imgt_cdr")
    kabat_cdr = match.get("kabat_cdr")
    chothia_cdr = match.get("chothia_cdr")
    
    print(f"    -> IMGT CDR: {imgt_cdr}")
    print(f"    -> Kabat CDR: {kabat_cdr}")
    print(f"    -> Chothia CDR: {chothia_cdr}")

print("=== Verifying Mutations ===")
verify_mutation("001", "vl", 51, "D")
verify_mutation("008", "vl", 97, "I")
verify_mutation("008", "vh", 33, "I")
verify_mutation("008", "vl", 101, "N")
verify_mutation("7M16", "vl", 89, "T")
