aa3to1 = {"ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E",
           "GLY":"G","HIS":"H","ILE":"I","LEU":"L","LYS":"K","MET":"M","PHE":"F",
           "PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V"}

with open(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\_1N8Z.pdb") as f:
    lines = f.readlines()

seen = {}
for l in lines:
    if l.startswith("ATOM") and l[21]=="C" and l[13:16].strip()=="CA":
        try:
            rnum = int(l[22:26].strip())
            rname = l[17:20].strip()
            if rnum not in seen:
                seen[rnum] = aa3to1.get(rname,"X")
        except:
            pass

sorted_res = sorted(seen.items())
print("1N8Z chain C: %d residues, range %d-%d" % (
    len(sorted_res), sorted_res[0][0], sorted_res[-1][0]))

# Cysteines in Domain IV (after position 480)
print("\nCysteines in Domain IV region (1N8Z pos > 480):")
cys_list = [(r, a) for r, a in sorted_res if r > 480 and a == "C"]
for r, a in cys_list:
    print("  1N8Z C-%d = NP_004439.2 aa%d" % (r, r + 22))

# First Cys anchor in Domain IV
first_cys = cys_list[0][0] if cys_list else 490
print("\nFirst Domain IV Cys at 1N8Z residue:", first_cys)

# Extract from first DomIV Cys to end of chain C (residue 607)
# This is the true minimal Domain IV with all disulfides included
idx_s = next(i for i, (r, a) in enumerate(sorted_res) if r >= first_cys)
minimal = [(r, a) for r, a in sorted_res[idx_s:]]
seq_minimal = "".join(a for r, a in minimal)
r_start = minimal[0][0]
r_end   = minimal[-1][0]

print("\n=== OPTION A: Full Domain IV from 1N8Z (all Cys included) ===")
print("1N8Z residues %d-%d = NP_004439.2 aa%d-aa%d" % (
    r_start, r_end, r_start+22, r_end+22))
print("Length: %d aa" % len(seq_minimal))
print(seq_minimal)

# Even shorter: from a bit before the epitope start (1N8Z 540) to end
idx_b = next(i for i, (r, a) in enumerate(sorted_res) if r >= 540)
seq_b = "".join(a for r, a in sorted_res[idx_b:])
rb_start = sorted_res[idx_b][0]
print("\n=== OPTION B: Minimal epitope context (1N8Z %d-607) ==="%rb_start)
print("1N8Z residues %d-%d = NP_004439.2 aa%d-aa%d" % (
    rb_start, 607, rb_start+22, 629))
print("Length: %d aa" % len(seq_b))
print(seq_b)

# Count Cys in Option B
print("Cys count in Option B:", seq_b.count("C"),
      "(must be EVEN for proper disulfide bonding)")

# ColabFold submission
VHH = "QVQLVQSGAEVVKPGSSVKLSCKASGFNIKDTYIHWVKQRPEQGREWIGRIYPTNGYTRYDPKFQDRATITADTSTSTAYLEVSRLRSEDTAVYYCSRWGGDGFYAMDYWGQGASVTVSS"
print()
print("=== RECOMMENDED ColabFold submission ===")
print("Using Option A (minimal but complete Domain IV):")
print("VHH: %d aa + HER2: %d aa = %d total" % (len(VHH), len(seq_minimal), len(VHH)+len(seq_minimal)))
print()
print("Multimer format:")
print(VHH + ":" + seq_minimal)
print()
print("Settings to use:")
print("  template_mode = pdb70   (CRITICAL - uses 1N8Z as template)")
print("  num_recycles = 6")
print("  model_type = alphafold2_multimer_v3")
