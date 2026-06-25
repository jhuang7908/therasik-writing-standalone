import urllib.request

# Download 1N8Z
url = "https://files.rcsb.org/download/1N8Z.pdb"
print("Downloading 1N8Z from RCSB...")
with urllib.request.urlopen(url, timeout=30) as r:
    pdb_text = r.read().decode("utf-8")
lines = pdb_text.split("\n")
print("Downloaded: %d lines" % len(lines))

# Parse chains from SEQRES
print("\n=== CHAIN SUMMARY (SEQRES) ===")
seqres = {}
for l in lines:
    if l.startswith("SEQRES"):
        ch = l[11]
        residues = l[19:].split()
        seqres.setdefault(ch, []).extend(residues)
for ch, res in sorted(seqres.items()):
    print("  Chain %s: %d residues, first=%s, last=%s" % (ch, len(res), res[0], res[-1]))

# Parse COMPND to identify chains
print("\n=== COMPND ===")
for l in lines:
    if l.startswith("COMPND"):
        print(l.rstrip())

# Parse ATOM records - get unique chains and residue ranges
print("\n=== ATOM RESIDUE RANGES ===")
chain_residues = {}
for l in lines:
    if l.startswith("ATOM"):
        ch = l[21]
        try:
            resnum = int(l[22:26].strip())
            chain_residues.setdefault(ch, []).append(resnum)
        except:
            pass
for ch in sorted(chain_residues):
    resnums = chain_residues[ch]
    print("  Chain %s: residues %d-%d (n=%d unique)" % (
        ch, min(resnums), max(resnums), len(set(resnums))))

# Find interface: contacts between antibody chains (B/C = Fab?) and antigen (A = HER2?)
print("\n=== INTERFACE ANALYSIS (contacts < 5.0 A) ===")
import math

# Parse CA atoms only for speed
atoms = {}
for l in lines:
    if l.startswith("ATOM") and l[13:15].strip() == "CA":
        ch = l[21]
        try:
            resnum = int(l[22:26].strip())
            resname = l[17:20].strip()
            x = float(l[30:38])
            y = float(l[38:46])
            z = float(l[46:54])
            atoms.setdefault(ch, []).append((resnum, resname, x, y, z))
        except:
            pass

chains_list = sorted(atoms.keys())
print("Chains with CA atoms:", chains_list)

# Contact threshold
THRESH = 8.0  # Angstroms (CA-CA, so use 8A for loose contacts)

# Find contacts between each pair of chains
def find_contacts(ch1, ch2, thresh=8.0):
    contacts = []
    for r1, n1, x1, y1, z1 in atoms.get(ch1, []):
        for r2, n2, x2, y2, z2 in atoms.get(ch2, []):
            d = math.sqrt((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2)
            if d < thresh:
                contacts.append((r1, n1, r2, n2, round(d, 1)))
    return contacts

# For each pair of chains, report if they have contacts
for i, c1 in enumerate(chains_list):
    for c2 in chains_list[i+1:]:
        contacts = find_contacts(c1, c2)
        if contacts:
            r1_set = sorted(set(c[0] for c in contacts))
            r2_set = sorted(set(c[2] for c in contacts))
            print("  Chain %s <-> Chain %s: %d contacts" % (c1, c2, len(contacts)))
            print("    %s residues: %s...%s (range %d-%d)" % (c1, r1_set[:5], r1_set[-3:], min(r1_set), max(r1_set)))
            print("    %s residues: %s...%s (range %d-%d)" % (c2, r2_set[:5], r2_set[-3:], min(r2_set), max(r2_set)))
