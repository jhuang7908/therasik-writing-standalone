from anarci import anarci

AA3 = {'ALA':'A','ARG':'R','ASN':'N','ASP':'D','CYS':'C','GLN':'Q','GLU':'E',
       'GLY':'G','HIS':'H','ILE':'I','LEU':'L','LYS':'K','MET':'M','PHE':'F',
       'PRO':'P','SER':'S','THR':'T','TRP':'W','TYR':'Y','VAL':'V'}

pdb_path = r'projects/PAG project/boltz_relaxed_qc/001_relaxed.pdb'
chain_seq = {}
seen = set()
with open(pdb_path) as f:
    for line in f:
        if not line.startswith('ATOM'):
            continue
        chain = line[21]
        resi = int(line[22:26])
        key = (chain, resi)
        if key in seen:
            continue
        seen.add(key)
        aa = AA3.get(line[17:20].strip(), 'X')
        chain_seq.setdefault(chain, []).append((resi, aa))

vl_seq = ''.join(aa for _, aa in sorted(chain_seq.get('B', [])))
print(f"VL seq (chain B): {vl_seq}")
print(f"Length: {len(vl_seq)}")
print()

# Show context around CDR2 for both schemes
for scheme, cdr2_lo, cdr2_hi, context_lo, context_hi in [
    ('kabat', 50, 56, 46, 60),
    ('imgt',  56, 65, 52, 69),
]:
    results, _, _ = anarci([('vl', vl_seq)], scheme=scheme,
                            assign_germline=False, allowed_species=None)
    numbering = results[0][0][0]

    print(f"=== {scheme.upper()} CDR-L2 ({cdr2_lo}-{cdr2_hi}) + flanking context ===")
    for (pos, ins), aa in numbering:
        if aa == '-':
            continue
        ins_s = ins.strip()
        full_pos = f"{pos}{ins_s}"
        if context_lo <= pos <= context_hi:
            in_cdr = "  <-- CDR2" if cdr2_lo <= pos <= cdr2_hi else ""
            print(f"  {scheme.upper()} {full_pos:>4}  {aa}{in_cdr}")
    print()
