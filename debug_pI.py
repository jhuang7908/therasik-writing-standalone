from api.routers.vh_to_vhh import _apply_phase45_sdab_adapt
from anarcii import Anarcii
from core.humanization.kabat_utils import kabat_from_anarcii, sorted_keys

seq = "EVQLQESGGGLVQPGGSLRLSCAASGYTFTRYTMYWLRQAPGKGLEWVSSINPSRGYTYYRDSVKGRFTISRDNAKNTLYLQMNSLKSEDTAVYYCARYYDDHYSLDYKGQGTQVTVSS"
a = Anarcii(seq_type="antibody", mode="accuracy")
a.number([seq])
entry = a.to_scheme("kabat").get("Sequence 1", {})
kd = kabat_from_anarcii(entry["numbering"])
keys = sorted_keys(kd)
p2i = {k: i for i, k in enumerate(keys)}

res = _apply_phase45_sdab_adapt(seq, kd, p2i, "murine_mab", mini_pI=8.86)
print(res["mutations_applied"])
print(res["sequence"])
print(kd.get((19, "")))
print(kd.get((13, "")))
print(kd.get((73, "")))
print(kd.get((83, "")))
