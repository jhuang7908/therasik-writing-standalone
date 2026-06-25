from anarci import anarci
import json

seq = 'DVQLVESGGGSVQAGGSLRLSCAVSGSTYSPCTTGWVRQAPGKGLEWVSSISSPGTIYYQDSVKGRFTISRDNAKNTVYLQMNSLQREDTGMYYCQIQCGSIREYWGQGTQVTVS'
res, hit_tables, details = anarci([('test', seq)], scheme='imgt', output=False)

print('len(res):', len(res), flush=True)
if res:
    r0 = res[0]
    print('type(res[0]):', type(r0), flush=True)
    print('res[0]:', r0, flush=True)
    
    if r0 is not None and len(r0) > 0:
        r00 = r0[0]
        print('type(res[0][0]):', type(r00), flush=True)
        print('res[0][0]:', r00, flush=True)
