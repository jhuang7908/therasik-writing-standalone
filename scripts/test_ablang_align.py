import ablang
heavy_ablang = ablang.pretrained("heavy")
seq = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAYDIYGDGAMDYWGQGTLVTVSS"
results = heavy_ablang([seq], mode='sequence_aligning')
print(results)
