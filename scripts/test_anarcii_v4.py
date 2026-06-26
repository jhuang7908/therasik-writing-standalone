from anarcii import Anarcii
import json

a = Anarcii(seq_type="antibody", mode="accuracy")
seq = "MKYLLPTAAAGLLLLAAQPAMAMQVQLQESGGGLVQPGGSLRLSCAASGFTFSNYKMNWVRQAPGKGLEWVSDISQSGASISYTGSVKGRFTISRDNAKNTLYLQMNSLKPEDTAVYYCARCPAPFTRDCFDVTSTTYAYRGQGTQVTV"
res = a.number([seq])
if isinstance(res, dict):
    for k, v in res.items():
        print(f"Key: {k}")
        if isinstance(v, dict):
            print(f"Sub-keys: {v.keys()}")
            # It likely has keys like 'H', 'L', etc.
            for sk, sv in v.items():
                print(f"Sub-key: {sk}")
                # sv is likely (numbering, alignment_details, hit_info)
                numbering = sv[0]
                vh_seq = "".join([aa for _, aa in numbering if aa != "-"])
                print(f"VH Seq ({sk}): {vh_seq}")
