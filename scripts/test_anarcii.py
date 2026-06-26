from anarcii import Anarcii
import json

a = Anarcii(seq_type="antibody", mode="accuracy")
seq = "MKYLLPTAAAGLLLLAAQPAMAMQVQLQESGGGLVQPGGSLRLSCAASGFTFSNYKMNWVRQAPGKGLEWVSDISQSGASISYTGSVKGRFTISRDNAKNTLYLQMNSLKPEDTAVYYCARCPAPFTRDCFDVTSTTYAYRGQGTQVTV"
res = a.number([seq])
print(f"Res type: {type(res)}")
print(f"Res len: {len(res)}")
if res[0]:
    print(f"Res[0] type: {type(res[0])}")
    print(f"Res[0] len: {len(res[0])}")
    if res[0][0]:
        numbering = res[0][0][0]
        print(f"Numbering type: {type(numbering)}")
        vh_seq = "".join([aa for _, aa in numbering if aa != "-"])
        print(f"VH Seq: {vh_seq}")
else:
    print("No numbering found")
