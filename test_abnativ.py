
from core.vh2vhh.abnativ_naturalness_layer import score_naturalness_delta
import time

seq = "EVQLVESGGGLVQPGGSLRLSCAASGRTSRSYGMGWFRQAPGKEREFVAGISWRGDSTGYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAAAGSAWYGTLYEYDYWGQGTLVTVSS"
print(f"Testing sequence: {seq}")
start = time.time()
res = score_naturalness_delta(seq)
end = time.time()
print(f"Result: {res}")
print(f"Time taken: {end - start:.2f}s")
