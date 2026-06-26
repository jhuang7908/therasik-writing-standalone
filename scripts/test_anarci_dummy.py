from anarci import anarci
import os

seq = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAYDIYGDGAMDYWGQGTLVTVSS"
hmmerpath = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\scripts"

print(f"Running anarci with hmmerpath={hmmerpath}...")
results = anarci([("seq", seq)], scheme="aho", hmmerpath=hmmerpath)
print(f"Results: {results}")
