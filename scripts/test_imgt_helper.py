from imgt_helper import get_imgt_numbering, rebuild_v_sequence, simple_fr_cdr_split

#  VH 
seq = (
    "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVK"
    "GRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAA"
)

res = get_imgt_numbering(seq)
numbering = res["numbering"]

print("=== ANARCI  ===")
print("success:", res["success"])
print("v_start:", res["v_start"], "v_end:", res["v_end"], "length:", res["length"])

v_seq = rebuild_v_sequence(numbering)
print("\n===  V  ===")
print(v_seq)
print("V length:", len(v_seq))

segments = simple_fr_cdr_split(numbering)
print("\n===  FR/CDR  ===")
for name, s in segments.items():
    print(f"{name}: {len(s):3d} aa  {s}")
