import ablang
heavy_ablang = ablang.pretrained("heavy")
seq = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAYDIYGDGAMDYWGQGTLVTVSS"
results = heavy_ablang([seq], mode='rescoding', align=True)
print(results)
