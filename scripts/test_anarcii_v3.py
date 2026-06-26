from anarcii import Anarcii
import json

a = Anarcii(seq_type="antibody", mode="accuracy")
seq = "MKYLLPTAAAGLLLLAAQPAMAMQVQLQESGGGLVQPGGSLRLSCAASGFTFSNYKMNWVRQAPGKGLEWVSDISQSGASISYTGSVKGRFTISRDNAKNTLYLQMNSLKPEDTAVYYCARCPAPFTRDCFDVTSTTYAYRGQGTQVTV"
res = a.number([seq])
print(f"Res type: {type(res)}")
if isinstance(res, dict):
    for k, v in res.items():
        print(f"Key: {k}")
        print(f"Value type: {type(v)}")
        if v:
            print(f"Value[0] type: {type(v[0])}")
            print(f"Value[0] len: {len(v[0])}")
            # Usually it's (numbering, alignment_details, hit_info)
            numbering = v[0][0]
            print(f"Numbering type: {type(numbering)}")
            vh_seq = "".join([aa for _, aa in numbering if aa != "-"])
            print(f"VH Seq: {vh_seq}")
