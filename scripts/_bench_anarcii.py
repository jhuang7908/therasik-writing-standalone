"""Quick ABARCII benchmark: number 3 sequences with speed mode."""
import sys, time
sys.stdout.reconfigure(line_buffering=True)

from anarcii import Anarcii

seqs = {
    "test_VH": "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYWMSWVRQAPGKGLEWVSNIKQDGSEKYYVDSVKGRFTISRDNAKNSLYLQMNSLRAEDTAVYYCAR",
    "test_VL": "DIQMTQSPSSLSASVGDRVTITCRASQDVNTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGSRSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK",
    "test_VH2": "QVQLVESGGGVVQPGRSLRLSCAASGFTFSSYGMHWVRQAPGKGLEWVAFIRYDGSNKYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAR",
}

print(f"Loading Anarcii (mode=speed)...", flush=True)
t0 = time.time()
model = Anarcii(seq_type='antibody', mode='speed', cpu=True, batch_size=32)
print(f"  Loaded in {time.time()-t0:.1f}s", flush=True)

print("Numbering 3 sequences...", flush=True)
t1 = time.time()
result = model.number(seqs)
elapsed = time.time() - t1
print(f"  Done in {elapsed:.2f}s ({elapsed/len(seqs):.2f}s/seq)", flush=True)

for key, val in result.items():
    ct = val.get('chain_type', '?')
    sc = val.get('score', 0)
    n_pos = len([x for x in val.get('numbering', []) if x[1] != '-'])
    print(f"  {key}: chain={ct} score={sc:.2f} positions={n_pos}", flush=True)

print("Bench done.", flush=True)
