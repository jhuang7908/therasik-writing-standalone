from anarcii import Anarcii
import json

a = Anarcii(seq_type="antibody", mode="accuracy")
seq = "MKYLLPTAAAGLLLLAAQPAMAMQVQLQESGGGLVQPGGSLRLSCAASGFTFSNYKMNWVRQAPGKGLEWVSDISQSGASISYTGSVKGRFTISRDNAKNTLYLQMNSLKPEDTAVYYCARCPAPFTRDCFDVTSTTYAYRGQGTQVTV"
res = a.number([seq])
print(f"Res type: {type(res)}")
if isinstance(res, dict):
    print(f"Keys: {res.keys()}")
    if 'numbering' in res:
        print(f"Numbering len: {len(res['numbering'])}")
        num = res['numbering'][0]
        if num:
            print(f"First num entry: {num[0]}")
            vh_seq = "".join([aa for _, aa in num if aa != "-"])
            print(f"VH Seq: {vh_seq}")
elif isinstance(res, list):
    print(f"List len: {len(res)}")
    num = res[0][0]
    if num:
        print(f"First num entry: {num[0]}")
        vh_seq = "".join([aa for _, aa in num if aa != "-"])
        print(f"VH Seq: {vh_seq}")
