import urllib.request, math

url = "https://files.rcsb.org/download/1N8Z.pdb"
with urllib.request.urlopen(url, timeout=30) as r:
    pdb_text = r.read().decode("utf-8")
lines = pdb_text.split("\n")

# Parse all heavy atoms (not H)
atoms = {}
for l in lines:
    if not l.startswith("ATOM"):
        continue
    aname = l[12:16].strip()
    if aname.startswith("H"):
        continue
    ch = l[21]
    try:
        resnum = int(l[22:26].strip())
        resname = l[17:20].strip()
        x = float(l[30:38])
        y = float(l[38:46])
        z = float(l[46:54])
        atoms.setdefault(ch, []).append((resnum, resname, aname, x, y, z))
    except:
        pass

# All-atom contacts < 4.5 A between VH(B) and HER2(C), and VL(A) and HER2(C)
THRESH = 4.5

def find_contacts_allatom(ch_ab, ch_ag, thresh=4.5):
    contacts = set()
    for r1, n1, a1, x1, y1, z1 in atoms.get(ch_ab, []):
        for r2, n2, a2, x2, y2, z2 in atoms.get(ch_ag, []):
            d = math.sqrt((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2)
            if d < thresh:
                contacts.add((r1, n1, r2, n2))
    return contacts

print("=== All-atom contacts < 4.5 A ===\n")

# VH (chain B) contacts HER2 (chain C)
vh_contacts = find_contacts_allatom("B", "C")
vh_her2_residues = sorted(set(c[2] for c in vh_contacts))
vh_ab_residues   = sorted(set(c[0] for c in vh_contacts))
print("VH (chain B) contacts HER2 (chain C):")
print("  VH residues at interface:", vh_ab_residues)
print("  HER2 (1N8Z numbering) residues at interface:", vh_her2_residues)

# VL (chain A) contacts HER2 (chain C)
vl_contacts = find_contacts_allatom("A", "C")
vl_her2_residues = sorted(set(c[2] for c in vl_contacts))
vl_ab_residues   = sorted(set(c[0] for c in vl_contacts))
print("\nVL (chain A) contacts HER2 (chain C):")
print("  VL residues at interface:", vl_ab_residues)
print("  HER2 (1N8Z numbering) residues at interface:", vl_her2_residues)

# Combined epitope on HER2
all_her2 = sorted(set(vh_her2_residues + vl_her2_residues))
print("\nCombined HER2 epitope residues (1N8Z numbering):", all_her2)
print("Epitope range: %d - %d (%d residues)" % (min(all_her2), max(all_her2), len(all_her2)))

# Map to full precursor numbering (1N8Z chain C residue 1 = mature ECD = full precursor aa 23)
# So 1N8Z residue n = NP_004439.2 aa (n + 22)
print()
print("=== Mapping to NP_004439.2 (full precursor) ===")
print("1N8Z ECD residue 1 = full precursor aa 23")
for r in all_her2:
    full_aa = r + 22
    print("  1N8Z C-%d  =  NP_004439.2 aa%d" % (r, full_aa))

fp_range = [(r + 22) for r in all_her2]
print("\nFull precursor epitope: aa %d - %d" % (min(fp_range), max(fp_range)))

# Get actual residue names from 1N8Z chain C
her2_res_names = {}
for resnum, resname, aname, x, y, z in atoms.get("C", []):
    her2_res_names[resnum] = resname

aa3to1 = {'ALA':'A','ARG':'R','ASN':'N','ASP':'D','CYS':'C','GLN':'Q','GLU':'E',
           'GLY':'G','HIS':'H','ILE':'I','LEU':'L','LYS':'K','MET':'M','PHE':'F',
           'PRO':'P','SER':'S','THR':'T','TRP':'W','TYR':'Y','VAL':'V'}

print("\nEpitope residue identities (1N8Z):")
epitope_seq = []
for r in all_her2:
    name3 = her2_res_names.get(r, "???")
    name1 = aa3to1.get(name3, "?")
    is_vh = r in vh_her2_residues
    is_vl = r in vl_her2_residues
    contact_chains = ("VH" if is_vh else "") + ("+" if is_vh and is_vl else "") + ("VL" if is_vl else "")
    epitope_seq.append(name1)
    print("  1N8Z C-%d (%s = %s) contacted by: %s" % (r, name3, name1, contact_chains))

print("\nEpitope sequence:", "".join(epitope_seq))

# Also extract the HER2 chain C sequence from 1N8Z
print("\n=== HER2 Chain C (1N8Z) full sequence ===")
# Get unique residues in order
all_res = sorted(set((r, n) for r, n, a, x, y, z in atoms.get("C", [])))
seq_1n8z = "".join(aa3to1.get(n, "?") for r, n in all_res)
print("1N8Z HER2 ECD (%d residues, 1N8Z res 1-%d):" % (len(seq_1n8z), all_res[-1][0]))
print(seq_1n8z)
print()
# Show domain IV context
epitope_start_idx = min(all_her2) - all_res[0][0]
epitope_end_idx   = max(all_her2) - all_res[0][0] + 1
print("Domain IV context (residues %d-%d):" % (min(all_her2)-20, max(all_her2)+20))
start = max(0, epitope_start_idx - 20)
end   = min(len(seq_1n8z), epitope_end_idx + 20)
context = seq_1n8z[start:end]
marker  = " " * 20 + "^" * (epitope_end_idx - epitope_start_idx)
print(context)
print(marker + "  <- epitope")
