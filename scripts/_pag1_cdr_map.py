"""Map CDR positions for PAG1 7m antibody using Chothia numbering."""
from abnumber import Chain as AbChain

vh_seq = "QVQLVQSGAEVKKPGASVKVSCKASGYTFTSYVMHWVRQAPGQGLEWMGYIYPYNDGTKYNEKFKGRVTMTRDTSTSTVYMELSSLRSEDTAVYYCARYKYGQGFAYWGQGTTVTVSS"
vl_seq = "DIQMTQSPSSVSASVGDRVTITCRASENIYSNLAWYQQKPGKAPKLLIYAATNLADGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQHFWGTPWTFGGGTKLEIKR"

for label, seq, chain_id in [("VH", vh_seq, "A"), ("VL", vl_seq, "B")]:
    try:
        ab = AbChain(seq, scheme="chothia")
        print(f"{label} (chain {chain_id}) CDR positions (Chothia):")
        for cdr_name in ["cdr1", "cdr2", "cdr3"]:
            cdr_residues = []
            for pos, aa in ab:
                if pos.get_region() == cdr_name:
                    cdr_residues.append((str(pos), aa))
            if cdr_residues:
                pos_str = " ".join(f"{p}({a})" for p, a in cdr_residues)
                seq_str = "".join(a for _, a in cdr_residues)
                print(f"  {cdr_name.upper()}: {seq_str}  [{pos_str}]")
        print()
    except Exception as e:
        print(f"{label} error: {e}")

# Also map Chothia positions back to sequential PDB residue numbers
print("=" * 60)
print("Mapping Chothia -> PDB sequential residue number:")
for label, seq, chain_id in [("VH", vh_seq, "A"), ("VL", vl_seq, "B")]:
    try:
        ab = AbChain(seq, scheme="chothia")
        positions = list(ab)
        print(f"\n{label} (chain {chain_id}):")
        # Print CDR3 in detail (most important for affinity)
        cdr3 = [(str(p), aa, i+1) for i, (p, aa) in enumerate(positions) if p.get_region() == "cdr3"]
        print(f"  CDR3 residues (Chothia_pos, AA, seq_idx):")
        for cp, aa, si in cdr3:
            print(f"    Chothia {cp:5s} | AA {aa} | seq idx {si:3d}")
    except Exception as e:
        print(f"{label} error: {e}")
