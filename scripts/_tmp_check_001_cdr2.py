import json

data = json.loads(open(r'projects/PAG project/numbering/001_numbering.json').read())
muts = data['ala_scan']['mutations']

print("=== 001 VL CDR2 entries in numbering JSON ===")
for m in muts:
    if 'cdr2' in m.get('locus', '') and m.get('haddock_chain') == 'B':
        print(f"  pdb_resi={m['pdb_resi']:>3}  wt={m['wt']}  kabat={m.get('kabat_pos')}  imgt={m.get('imgt_pos')}  locus={m['locus']}")

print()
print("=== All VL CDR entries ===")
for m in muts:
    if m.get('haddock_chain') == 'B':
        print(f"  pdb_resi={m['pdb_resi']:>3}  wt={m['wt']}  kabat={m.get('kabat_pos')}  imgt={m.get('imgt_pos')}  locus={m['locus']}")
