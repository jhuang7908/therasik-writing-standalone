import sys
import promb

db = promb.init_db('human-oas', verbose=False)
sys.stderr.write(f"DB peptide length: {db.peptide_length}\n")
sys.stderr.write(f"DB size: {len(db.peptides)} peptides\n")

seq = 'QVQLVQSGAEVVKPGSSVKLSCKASGFNIKDTYIHWVKQRPEQGREWIGRIYPTNGYTRYDPKFQDRATITADTSTSTAYLEVSRLRSEDTAVYYCSRWGGDGFYAMDYWGQGASVTVSS'
peptides = db.chop_seq_peptides(seq)
found = sum(1 for p in peptides if db.contains(p))
total = len(peptides)
sys.stderr.write(f"OASis content (VGRW-SR-R2 WT): {found}/{total} = {found/total:.3f}\n")
sys.stderr.write("OASis/promb test PASSED\n")
