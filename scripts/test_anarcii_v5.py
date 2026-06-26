from anarcii import Anarcii
import json

a = Anarcii(seq_type="antibody", mode="accuracy")
seq = "MKYLLPTAAAGLLLLAAQPAMAMQVQLQESGGGLVQPGGSLRLSCAASGFTFSNYKMNWVRQAPGKGLEWVSDISQSGASISYTGSVKGRFTISRDNAKNTLYLQMNSLKPEDTAVYYCARCPAPFTRDCFDVTSTTYAYRGQGTQVTV"
res = a.number([seq])
if isinstance(res, dict):
    v = res['Sequence 1']
    if isinstance(v, dict):
        # In this version, it seems numbering is a dict or list of dicts
        # Let's just print it
        print(f"Numbering: {v['numbering'][:5]}")
